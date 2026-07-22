# API、队列与错误码

## 通用规则

除 `/health`、`/docs`、`/openapi.json`、Grok/ChatGPT 返回的局域网媒体 URL 和 Gemini 带签名媒体 URL 外，API 使用：

```http
Authorization: Bearer <该平台个人密钥>
```

生成请求进入平台自己的 FIFO 队列。Grok、Gemini、ChatGPT 图片各有一个 worker，因此每个平台真实并发为 1，三个平台可同时各执行一个任务。队列默认最多等待 100 个请求。

默认执行超时：文本 5 分钟、图片生成 15 分钟、图片编辑 20 分钟、视频 60 分钟、状态查询 60 秒。超时不自动重试；worker 立即取下一个任务。SQLite 使用 `execution_id` 条件更新，已经超时的任务不会被迟到结果改回成功。

每个生成响应都带 `X-Internal-Job-ID`。调用方可为生成 POST 传递 1–200 字符的
`Idempotency-Key`；同一人员密钥、路径和幂等键只会创建一个任务。重复图片/文本生成返回 409，
重复视频创建在原任务已有上游任务 ID 后返回该 ID。视频创建必须提供 `Idempotency-Key`，状态
查询只使用第一次创建返回的 ID。

GET/HEAD 等只读请求遇到 5xx 或网络错误时默认延迟后重试 1 次，最多可配置为 2 次。生成 POST
不会因网络错误自动重放，以免上游实际已受理却重复生成。Grok/ChatGPT 的 401、403、429 属于
当前上游个人 Key，不暂停共享队列；连续 5xx/网络失败达到阈值只熔断对应平台。

请求体默认上限为 32 MiB。大于 1 MiB 的代理请求和 Gemini 编辑上传会暂存到项目内 `data/media/<platform>/.requests`，避免 100 个排队请求同时常驻内存；执行结束后立即删除，异常遗留文件由保留期清理任务处理。

## 接口

| 方法 | 路径 | Grok | Gemini | ChatGPT 图片 |
| --- | --- | --- | --- | --- |
| GET | `/health` | 网关状态 | 网关与 SDK 状态 | 网关状态 |
| GET | `/v1/models` | 透传并用 Cherry 兼容别名替换原始视频模型 | 原生转换 | 透传 |
| POST | `/v1/chat/completions` | 透传；视频别名自动转换到视频任务 | 支持非流式和 OpenAI SSE 兼容流式 | 透传，限图片/上游支持场景 |
| POST | `/v1/responses` | 透传；视频别名支持 Responses SSE 转换 | 未实现 | 透传上游有限场景 |
| POST | `/v1/images/generations` | 透传 | 支持 URL/Base64 | 透传 |
| POST | `/v1/images/edits` | 透传 | multipart/JSON Base64、多图 | 透传 |
| POST | `/v1/videos` | 映射到上游 generations | 返回异步任务 | 不支持 |
| GET | `/v1/videos/{id}` | 透传 | 本地任务状态 | 不支持 |
| GET | `/v1/videos/{id}/content` | 透传（按上游支持） | 下载本地视频 | 不支持 |

Grok 的原始视频模型 `grok-imagine-video-1.5` 不会出现在 `/v1/models` 的聊天模型列表中。
网关会改为返回 Cherry 可直接使用的别名 `grok-imagine-video-1.5-vision`：它接收
`/v1/chat/completions` 或 `/v1/responses` 请求，取最后一张图片和最新提示词创建真实视频任务，
并用 SSE 返回进度和带签名的“打开或下载视频”链接。

在 Cherry Studio 中，选择 `Me` 服务商，点击“获取模型列表”后选用
`grok-imagine-video-1.5-vision`。对话里先放入图片，再输入“让这个女生动起来”即可。

直接调用 API 的客户端仍可使用原始视频端点：

```json
POST /v1/videos
{"model":"grok-imagine-video-1.5","prompt":"让这个女生动起来","image":{"url":"data:image/jpeg;base64,<base64>"}}
```

Gemini SDK 原生不支持流式生成。对于 `stream=true`，网关会先完成一次非流式生成，再以 OpenAI SSE 格式发送兼容事件；客户端可以使用流式接口，但不会在 Gemini 生成期间提前收到 token。Gemini SDK 无法提供可靠 token 计数，`usage` 字段返回 0。

Gemini 图片编辑支持原有的 `multipart/form-data`，也支持 JSON Base64 请求：

```json
{
  "model": "gemini-3-pro",
  "image": "data:image/png;base64,<base64>",
  "prompt": "保持构图不变，只替换眼镜",
  "n": 1,
  "response_format": "url"
}
```

如果客户端只能调用聊天接口，可选择网关额外提供的兼容模型 `gemini-3-pro-image`。它会把
`POST /v1/chat/completions` 转换为图片生成，并以 Markdown 图片链接返回；普通聊天仍使用
`gemini-3-pro` 等原始模型。

## 示例

```powershell
$headers = @{ Authorization = 'Bearer sk-internal-...' }
Invoke-RestMethod http://127.0.0.1:8002/v1/models -Headers $headers

$body = @{
    model = 'gemini-3-flash'
    messages = @(@{ role = 'user'; content = '用三句话说明量子隧穿' })
} | ConvertTo-Json -Depth 5
Invoke-RestMethod http://127.0.0.1:8002/v1/chat/completions `
    -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

## 错误码

| HTTP | type | 含义 | 是否自动重试 |
| --- | --- | --- | --- |
| 400 | `unsupported` | 参数或兼容能力不支持；原始 Grok 视频模型需用 `POST /v1/videos`，Cherry 聊天需改选 `grok-imagine-video-1.5-vision` | 否，修改请求或模型 |
| 413 | `request_too_large` | 请求体或上传图片超过上限 | 否，缩小输入 |
| 401 | — | 密钥缺失、错误、停用或到期 | 否，联系管理员 |
| 404 | — | 任务或媒体不存在 | 否 |
| 410 | — | 媒体已按保留期清理 | 否 |
| 429 | `queue_full` | 本平台队列已满 | 客户端退避后人工决定 |
| 409 | `duplicate_request` | 同一幂等请求已经提交 | 否，使用原任务结果/ID |
| 502 | `upstream_error` | 上游不可用或登录态失效 | 只读请求最多安全重试 1–2 次 |
| 503 | `queue_paused` | 401/403/429 或连续失败触发平台暂停 | 人工恢复后重启平台 |
| 503 | — | Gemini 未初始化 | 恢复 Cookie 后重启 |
| 504 | `timeout` | 执行超时并已释放 worker | 不自动重试 |

服务不会自动换号、绕过验证码或在 401/403/429 时无条件重放生成请求。
