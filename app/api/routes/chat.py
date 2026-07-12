"""对话路由 - SSE 流式响应"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models import ChatRequest, Message
from app.llm.base import GenerateParams
from app.services.chat_service import ChatService
from app.services.project_service import ProjectService
from app.api.dependencies import get_chat_service, get_project_service, get_llm_client

router = APIRouter()


def _sse(data: dict) -> str:
    """格式化 SSE 数据行"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/projects/{project_id}/messages", response_model=list[Message], tags=["对话"])
async def get_messages(
    project_id: int,
    chapter_id: int | None = None,
    limit: int = 50,
    svc: ChatService = Depends(get_chat_service),
):
    """获取对话历史"""
    return await svc.get_history(project_id, chapter_id, limit)


@router.post("/projects/{project_id}/chat", tags=["对话"])
async def chat(
    project_id: int,
    body: ChatRequest,
    svc: ChatService = Depends(get_chat_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """对话接口 - SSE 流式响应

    请求体：{"message": "用户输入", "chapter_id": null, "temperature": 0.8}
    响应：text/event-stream，每行 data: {"content": "..."}\n\n
    """
    # 校验项目存在
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    # 构建生成参数
    params = None
    if body.temperature is not None or body.max_tokens is not None:
        params = GenerateParams(
            temperature=body.temperature or 0.8,
            max_tokens=body.max_tokens or 2048,
        )

    async def event_stream():
        try:
            async for chunk in svc.generate(
                project_id, body.message, body.chapter_id, params,
                context_window=body.context_window,
            ):
                yield _sse({"content": chunk})
            yield _sse({"done": True})
        except Exception as e:
            yield _sse({"error": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@router.delete("/projects/{project_id}/messages", tags=["对话"])
async def clear_messages(
    project_id: int,
    chapter_id: int | None = None,
    svc: ChatService = Depends(get_chat_service),
):
    """清空对话历史"""
    count = await svc.clear_history(project_id, chapter_id)
    return {"message": f"已清空 {count} 条消息"}


@router.get("/projects/{project_id}/context-info", tags=["对话"])
async def get_context_info(
    project_id: int,
    chapter_id: int | None = None,
    svc: ChatService = Depends(get_chat_service),
):
    """获取上下文信息：消息数、压缩阈值、是否有摘要"""
    msg_count = await svc.context_manager._count_messages(project_id, chapter_id)
    threshold = svc.context_config.compress_threshold
    has_summary = await svc.context_manager._get_latest_summary(project_id, chapter_id)
    return {
        "message_count": msg_count,
        "compress_threshold": threshold,
        "has_summary": bool(has_summary),
        "near_threshold": msg_count >= threshold - 5,
    }


@router.post("/projects/{project_id}/compress", tags=["对话"])
async def compress_context(
    project_id: int,
    chapter_id: int | None = None,
    svc: ChatService = Depends(get_chat_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """手动触发上下文压缩"""
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    msg_count = await svc.context_manager._count_messages(project_id, chapter_id)
    threshold = svc.context_config.compress_threshold

    if msg_count < threshold:
        return {
            "compressed": False,
            "message": f"消息数 {msg_count} 未达阈值 {threshold}，无需压缩",
            "current_count": msg_count,
        }

    compressed = await svc.context_manager.maybe_compress(project_id, chapter_id)
    new_count = await svc.context_manager._count_messages(project_id, chapter_id)

    if compressed:
        message = f"已压缩 {msg_count - new_count} 条旧消息为摘要"
    else:
        message = "压缩失败，请检查 LLM 是否在线后重试"

    return {
        "compressed": compressed,
        "message": message,
        "current_count": new_count,
    }


@router.get("/llm/health", tags=["LLM"])
async def llm_health(llm_client=Depends(get_llm_client)):
    """检查 LLM 服务是否在线"""
    healthy = await llm_client.health_check()
    return {"online": healthy, "status": "online" if healthy else "offline"}
