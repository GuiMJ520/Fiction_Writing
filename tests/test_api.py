"""API 端点测试 - 通过 HTTP 请求验证路由"""
import json
import urllib.request
import time

BASE = "http://127.0.0.1:8000"


def api(method: str, path: str, data: dict | None = None) -> dict:
    """发送 HTTP 请求"""
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    # 等待服务启动
    for _ in range(10):
        try:
            api("GET", "/api/health")
            break
        except Exception:
            time.sleep(0.5)

    print("=== API 端点测试 ===\n")

    # 1. 创建项目
    print("[1] POST /api/projects - 创建项目")
    project = api("POST", "/api/projects", {
        "name": "API测试小说",
        "description": "通过API创建",
        "genre": "奇幻",
    })
    pid = project["id"]
    print(f"  ✓ 创建成功: id={pid}, name={project['name']}")

    # 2. 获取项目
    print("[2] GET /api/projects/{id} - 获取项目")
    p = api("GET", f"/api/projects/{pid}")
    assert p["name"] == "API测试小说"
    print(f"  ✓ 获取成功: {p['name']}")

    # 3. 列出项目
    print("[3] GET /api/projects - 列出项目")
    projects = api("GET", "/api/projects")
    print(f"  ✓ 列出 {len(projects)} 个项目")

    # 4. 更新项目
    print("[4] PUT /api/projects/{id} - 更新项目")
    p = api("PUT", f"/api/projects/{pid}", {"name": "修改后的标题"})
    assert p["name"] == "修改后的标题"
    print(f"  ✓ 更新成功: {p['name']}")

    # 5. 创建章节
    print("[5] POST /api/projects/{id}/chapters - 创建章节")
    ch1 = api("POST", f"/api/projects/{pid}/chapters", {"title": "第一章"})
    ch2 = api("POST", f"/api/projects/{pid}/chapters", {"title": "第二章"})
    print(f"  ✓ 创建: {ch1['title']}(order={ch1['chapter_order']}), {ch2['title']}(order={ch2['chapter_order']})")

    # 6. 列出章节
    print("[6] GET /api/projects/{id}/chapters - 列出章节")
    chapters = api("GET", f"/api/projects/{pid}/chapters")
    assert len(chapters) == 2
    print(f"  ✓ 列出 {len(chapters)} 个章节")

    # 7. 更新章节内容
    print("[7] PUT /api/chapters/{id} - 更新章节内容")
    ch = api("PUT", f"/api/chapters/{ch1['id']}", {
        "content": "这是正文内容。",
        "status": "writing",
    })
    assert ch["word_count"] > 0
    print(f"  ✓ 更新成功，字数: {ch['word_count']}")

    # 8. 重新排序
    print("[8] PUT /api/projects/{id}/chapters/reorder - 重新排序")
    api("PUT", f"/api/projects/{pid}/chapters/reorder", [ch2["id"], ch1["id"]])
    chapters = api("GET", f"/api/projects/{pid}/chapters")
    assert chapters[0]["id"] == ch2["id"]
    print(f"  ✓ 顺序: {[c['title'] for c in chapters]}")

    # 9. 删除章节
    print("[9] DELETE /api/chapters/{id} - 删除章节")
    api("DELETE", f"/api/chapters/{ch1['id']}")
    chapters = api("GET", f"/api/projects/{pid}/chapters")
    assert len(chapters) == 1
    print(f"  ✓ 删除后剩余 {len(chapters)} 个")

    # 10. 删除项目
    print("[10] DELETE /api/projects/{id} - 删除项目")
    api("DELETE", f"/api/projects/{pid}")
    try:
        api("GET", f"/api/projects/{pid}")
        assert False, "应返回404"
    except urllib.error.HTTPError as e:
        assert e.code == 404
    print(f"  ✓ 删除成功，后续访问返回404")

    print("\n✅ 所有 API 端点测试通过")


if __name__ == "__main__":
    main()
