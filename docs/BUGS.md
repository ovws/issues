# Bug 记录

## BUG-20260721-001：Grok 视频模型通过 `grok.loser.dev` 访问时报端点不兼容

- **状态**：已修复、已部署并通过 Cherry Studio 真实图生视频验证
- **发现日期**：2026-07-21
- **服务**：Grok 网关（`https://grok.loser.dev/v1`）
- **模型**：`grok-imagine-video-1.5`
- **影响**：无法创建视频；使用该模型的请求直接返回 400，不会生成任务。

### 现象

使用 Grok 网关密钥访问 `grok.loser.dev` 时返回：

```json
{
  "code": "invalid-argument",
  "error": "The model grok-imagine-video-1.5 is a video model and is therefore not available on this endpoint. Please use a compatible endpoint such as https://api.x.ai/v1/videos/generations. For more information, see https://docs.x.ai/docs/api-reference#video-generation"
}
```

### 复现条件

1. API Base URL 配置为 `https://grok.loser.dev/v1`。
2. 使用有效的 Grok 网关密钥。
3. 请求中指定模型 `grok-imagine-video-1.5`。
4. 通过当前客户端实际使用的非视频端点发送请求，或确认网关没有将视频创建请求映射到 `/v1/videos/generations`。

### 初步判断

上游明确表示该模型只能用于视频生成端点。项目网关当前仅对 `POST /v1/videos` 做 `/v1/videos/generations` 映射；如果客户端（例如 Cherry Studio）把视频模型作为聊天/图片请求发送，或者请求未命中该映射，就会出现此错误。需要结合网关访问日志确认实际请求路径，并验证视频端点的请求体是否被完整透传。

### 处理结果

- [x] 日志确认 Cherry 先后使用了 `POST /v1/chat/completions` 和 `POST /v1/responses`。
- [x] 验证 `POST /v1/videos` 到上游 `/v1/videos/generations` 的映射链路。
- [x] `/v1/models` 隐藏原始视频模型，改为返回 Cherry 兼容别名 `grok-imagine-video-1.5-vision`。
- [x] 兼容别名支持 Chat Completions 与 Responses SSE，自动传递最新图片并返回签名视频链接。
- [x] Cherry Studio 实测返回生成进度、完成状态及可用的视频内容（HTTP 200）。

### 使用方式

在 Cherry Studio 的 `Me` 服务商中选择 `grok-imagine-video-1.5-vision`。原始模型
`grok-imagine-video-1.5` 仍仅用于直接调用 `POST /v1/videos` 的 API 客户端。

### 本次处理

网关对原始 Grok 视频模型的误用仍返回 `400 unsupported`，同时为 Cherry
提供独立兼容别名，将聊天或 Responses 请求转换为真实视频任务。视频生成期间使用
SSE 心跳和进度事件，完成后返回不依赖 Cherry API Key 请求头的签名内容链接。
