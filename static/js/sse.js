// SSE 流式读取工具 - 用 fetch + ReadableStream 处理 POST 请求的流式响应
// EventSource 只支持 GET，对话接口用 POST，所以需要自己解析 SSE

async function streamSSE(url, body, callbacks) {
    const { onChunk, onDone, onError, signal } = callbacks;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: signal,
        });

        if (!response.ok) {
            const errText = await response.text();
            onError?.(`请求失败 (${response.status}): ${errText}`);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            // SSE 事件以空行分隔
            const events = buffer.split('\n\n');
            buffer = events.pop();

            for (const event of events) {
                const lines = event.split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.content) {
                                onChunk?.(data.content);
                            }
                            if (data.done) {
                                onDone?.();
                                return;
                            }
                            if (data.error) {
                                onError?.(data.error);
                                return;
                            }
                        } catch (e) {
                            // JSON 解析失败，跳过
                        }
                    }
                }
            }
        }
        onDone?.();
    } catch (err) {
        if (err.name === 'AbortError') {
            onDone?.();
        } else {
            onError?.(err.message || '网络错误');
        }
    }
}
