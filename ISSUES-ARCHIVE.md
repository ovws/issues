# GitHub Issues 文本归档

- 仓库：`ovws/issues`
- 快照日期：2026-10-09（Asia/Shanghai）
- Git 源快照：`7aabd7ff5502dd8dab0e9cc089d283911f5f4358`
- Issue 数量：92
- 评论数量：103
- 状态统计：open 16，closed 76

> 这是该日期的文本快照。GitHub 上的 Issue/评论仍是主记录；此文件用于仓库备份和离线检索。

## Issue #3

```json
{
  "id": 4925962375,
  "number": 3,
  "title": "Cherry Studio 多模态消息被聊天请求 Schema 拒绝",
  "url": "https://github.com/ovws/issues/issues/3",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-20T05:07:05Z",
  "updated_at": "2026-07-27T01:16:54Z",
  "closed_at": "2026-07-20T06:51:45Z",
  "labels": [
    "priority: P2",
    "component: gateway",
    "故障"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 2
}
```

### 正文

````text
## 现象

Cherry Studio 1.9.12 通过自定义 OpenAI 服务商调用 Gemini 网关时，`POST /v1/chat/completions` 返回 HTTP 400。请求中的 `messages[0].content` 是 OpenAI 多模态内容块数组，第二个内容块不是 `text`，当前 Pydantic Schema 因此拒绝整个请求。

脱敏后的错误响应：

```json
{
  "error": {
    "message": "invalid request: body.messages.0.content.str: Input should be a valid string; body.messages.0.content.list[ChatContentPart].1.type: Input should be 'text'; body.messages.0.content.list[ChatContentPart].1.text: Field required",
    "type": "invalid_request",
    "code": null
  }
}
```

## 影响范围与紧急度

- 影响 Cherry Studio 1.9.12 的多模态消息、图片或附件上下文调用。
- 纯文本调用有临时绕过方案，因此定为 `priority: P2`。
- 根因位于共享 FastAPI/OpenAI-compatible 网关请求 Schema，归属 `component: gateway`。

## 复现条件

- 时间：2026-07-20（Asia/Shanghai）
- 服务：Gemini OpenAI-compatible 网关，端口 8002
- 客户端：Cherry Studio 1.9.12，自定义服务商类型为 OpenAI
- 模型：`gemini-3-flash` 或 `gemini-3-pro`
- 请求：`messages[].content` 使用数组形式，且包含非 `text` 内容块
- 结果：HTTP 400，`type=invalid_request`

请求中的 API Key、Cookie、Authorization Header 和附件内容均未记录。

## 期望结果

- 兼容 OpenAI Chat Completions 常见的 `text` 与 `image_url` 内容块。
- 将受支持的图片安全地转换为 Gemini-API 的文件输入。
- 对不支持的内容块返回明确、稳定的错误码和说明，而不是 Pydantic 联合类型内部错误。
- 保持纯文本和多轮对话兼容性。

## 初步实施计划

1. 扩展 `src/internal_ai_api/gemini_schemas.py` 的消息内容块联合类型，至少支持 `text`、`image_url`。
2. 在聊天适配层提取文本与图片输入，传入 `GeminiBackend.generate(..., files=...)`。
3. 对远程 URL、Data URL、MIME、文件大小、重定向和下载超时实施限制，避免 SSRF 与超大请求。
4. 增加 Cherry Studio 风格的多模态请求回归测试，以及不支持内容块的错误响应测试。
5. 实机验证 Cherry Studio 文本、多轮、单图和多图消息。

## 关联

- Linear：WK-76
- 工作分支：`ws/wk-76-部署-gemini-api-公司内网-openai-兼容服务`
````

### 评论（2）

#### 评论 1

```json
{
  "index": 1,
  "id": 5018966602,
  "url": "https://github.com/ovws/issues/issues/3#issuecomment-5018966602",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T05:07:09Z",
  "updated_at": "2026-07-20T05:07:09Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-87/cherry-studio-多模态消息被聊天请求-schema-拒绝">WK-87</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5019460615,
  "url": "https://github.com/ovws/issues/issues/3#issuecomment-5019460615",
  "author": "ovws",
  "created_at": "2026-07-20T06:39:35Z",
  "updated_at": "2026-07-20T06:39:35Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
修复已包含在提交 `e85d244`，分支 `ws/wk-87-cherry-studio-多模态消息被聊天请求-schema-拒绝` 已推送；统一在 Draft PR #6 审阅。

已覆盖 Cherry Studio 风格的 `text`/`image_url` 内容块、Data URL/远程图片限制、SSRF 防护和不支持内容块的稳定错误响应。自动化测试通过；真实 Cherry Studio 单图/多图仍待账号环境验证，因此保持打开。
```

---

## Issue #4

```json
{
  "id": 4926439735,
  "number": 4,
  "title": "部署 Gemini-API 公司内网 OpenAI 兼容服务 (WK-76)",
  "url": "https://github.com/ovws/issues/issues/4",
  "state": "closed",
  "state_reason": "duplicate",
  "author": "ovws",
  "created_at": "2026-07-20T06:38:20Z",
  "updated_at": "2026-07-20T06:44:18Z",
  "closed_at": "2026-07-20T06:41:40Z",
  "labels": [
    "enhancement",
    "priority: P1",
    "component: gateway",
    "component: deployment"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 2
}
```

### 正文

```text
## 目标

部署 Gemini-API 公司内网 OpenAI 兼容服务，并提供文本、图片、图片编辑、视频和 OpenAPI 接口。

## 关联

- Linear：https://linear.app/cvm/issue/WK-76/部署-gemini-api-公司内网-openai-兼容服务
- 分支：`ws/wk-76-部署-gemini-api-公司内网-openai-兼容服务`
- Cherry Studio 多模态兼容：#3

## 已实现

- FastAPI/OpenAI-compatible 网关、Docker 与 Windows 任务脚本
- Gemini Cookie/运行目录隔离、并发队列、幂等视频任务和熔断处理
- Cherry Studio 风格的 `text`/`image_url` 多模态消息转换与 SSRF/大小限制
- 自动化验证：28 个 pytest、Ruff、PowerShell 解析均通过

## 尚需实机验证

- 配置真实 Gemini Cookie 与账号权限
- 公司内网 DNS、防火墙和固定 IP
- Cherry Studio 文本、图片编辑、视频提交/查询/下载端到端验证

代码已推送；完成实机验证前保持 Issue 打开。
```

### 评论（2）

#### 评论 1

```json
{
  "index": 1,
  "id": 5019454208,
  "url": "https://github.com/ovws/issues/issues/4#issuecomment-5019454208",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T06:38:25Z",
  "updated_at": "2026-07-20T06:38:25Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-88/部署-gemini-api-公司内网-openai-兼容服务-wk-76">WK-88</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5019460419,
  "url": "https://github.com/ovws/issues/issues/4#issuecomment-5019460419",
  "author": "ovws",
  "created_at": "2026-07-20T06:39:33Z",
  "updated_at": "2026-07-20T06:44:18Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
代码已推送：

- 分支：`ws/wk-76-部署-gemini-api-公司内网-openai-兼容服务`
- 提交：`e85d244`
- Draft PR：#6
- 验证：28 个 pytest、Ruff、PowerShell 解析通过

本 Issue 创建后，GitHub→Linear 集成自动生成了 WK-88；WK-88 已标记为既有 WK-76 的 Duplicate，因此本 Issue 同步以 Duplicate 原因关闭。实际工作继续由 Linear WK-76 与 Draft PR #6 跟踪，尚需真实 Gemini Cookie/账号、内网 DNS/防火墙及客户端端到端验证。
```

---

## Issue #5

```json
{
  "id": 4926439908,
  "number": 5,
  "title": "部署 ChatGPT2API 公司内网图片兼容服务 (WK-77)",
  "url": "https://github.com/ovws/issues/issues/5",
  "state": "closed",
  "state_reason": "duplicate",
  "author": "ovws",
  "created_at": "2026-07-20T06:38:22Z",
  "updated_at": "2026-07-20T06:44:21Z",
  "closed_at": "2026-07-20T06:41:44Z",
  "labels": [
    "enhancement",
    "priority: P2",
    "component: gateway",
    "component: deployment"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 2
}
```

### 正文

```text
## 目标

部署 ChatGPT2API 公司内网图片兼容服务，供支持自定义 OpenAI Provider 的 Agent 调用图片生成与图片编辑 API。

## 关联

- Linear：https://linear.app/cvm/issue/WK-77/部署-chatgpt2api-公司内网图片兼容服务
- 分支：`ws/wk-77-部署-chatgpt2api-公司内网图片兼容服务`

## 已实现

- `GET /v1/models`、图片生成/编辑及项目支持的聊天/Responses 图片场景兼容层
- API Key 隔离、串行队列、超时、连续失败/401/403/429 熔断与报告
- 轻量 Windows 本地运行方案；Docker 仅为可选部署方式
- 本地管理页面依赖已构建，网关监听 8003，上游监听 18003
- 自动化验证：28 个 pytest、Ruff、PowerShell 解析均通过

## 尚需实机验证

- 添加真实 ChatGPT 网页账号；当前健康检查显示无活动账号
- 公司内网 DNS、防火墙和固定 IP
- Agent 文生图、单图/多图编辑、返回格式和连续任务端到端验证

代码已推送；完成真实账号与客户端验证前保持 Issue 打开。
```

### 评论（2）

#### 评论 1

```json
{
  "index": 1,
  "id": 5019454397,
  "url": "https://github.com/ovws/issues/issues/5#issuecomment-5019454397",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T06:38:26Z",
  "updated_at": "2026-07-20T06:38:26Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-89/部署-chatgpt2api-公司内网图片兼容服务-wk-77">WK-89</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5019460751,
  "url": "https://github.com/ovws/issues/issues/5#issuecomment-5019460751",
  "author": "ovws",
  "created_at": "2026-07-20T06:39:36Z",
  "updated_at": "2026-07-20T06:44:21Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
代码已推送：

- 分支：`ws/wk-77-部署-chatgpt2api-公司内网图片兼容服务`
- 功能提交：`c6b6aad`
- Codex GitHub 工作流配置：`cf561ac`、`ae00bdf`
- Draft PR：#7
- 验证：28 个 pytest、Ruff、PowerShell 解析通过

本 Issue 创建后，GitHub→Linear 集成自动生成了 WK-89；WK-89 已标记为既有 WK-77 的 Duplicate，因此本 Issue 同步以 Duplicate 原因关闭。实际工作继续由 Linear WK-77 与 Draft PR #7 跟踪。服务支持轻量 Windows 本地运行，当前仍需活动 ChatGPT 账号和真实 Agent 图片端到端验证。
```

---

## Issue #8

```json
{
  "id": 4926507713,
  "number": 8,
  "title": "ChatGPT2API 本地管理密钥文件与运行配置不一致",
  "url": "https://github.com/ovws/issues/issues/8",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-20T06:51:06Z",
  "updated_at": "2026-07-27T01:16:46Z",
  "closed_at": "2026-07-20T08:41:08Z",
  "labels": [
    "priority: P2",
    "component: deployment",
    "component: config",
    "故障"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 现象

在本机打开 `http://127.0.0.1:18003`，使用 `D:\WEB2API\config\chatgpt-image-admin.local.key` 登录时，页面提示“密钥无效或已失效，请重新登录”。

## 影响

管理员无法使用交付的本地密钥文件进入 ChatGPT2API 管理页面，因而无法添加或恢复 ChatGPT 网页账号。8003 网关虽然可以运行，但没有活动账号时不能完成真实图片生成与编辑。

存在可行绕过方式，因此优先级为 P2。

## 已脱敏证据

复现时间：2026-07-20（Asia/Shanghai）

- 密钥文件读取成功，但与根目录 `.env` 的 `CHATGPT_IMAGE_UPSTREAM_API_KEY` 不一致。
- 使用密钥文件内容调用 `POST http://127.0.0.1:18003/auth/login` 返回 HTTP 401。
- 使用当前 `.env` 中的上游密钥调用同一接口返回 HTTP 200，身份为管理员。
- 18003 启动脚本会把 `.env` 的 `CHATGPT_IMAGE_UPSTREAM_API_KEY` 注入为进程级 `CHATGPT2API_AUTH_KEY`。
- `prepare-chatgpt-image-native.ps1` 当前会生成或复用 `.env` 主密钥，但不会创建或同步 `chatgpt-image-admin.local.key`。

未记录或上传任何密钥、Authorization Header、Cookie 或账号 Token。

## 根因

本地管理密钥存在两个不一致的来源：运行进程使用 `.env`，交付给管理员的 `.local.key` 文件没有由原生部署脚本同步维护，因此成为过期或孤立文件。

## 期望修复

1. 原生准备脚本以 `.env` 主密钥为唯一来源，原子写入 `config/chatgpt-image-admin.local.key`。
2. 密钥文件使用无 BOM、无额外前后空白的 UTF-8，并沿用本地敏感文件 ACL 保护。
3. 启动前检查密钥文件与 `.env` 一致；不一致时安全修复或给出明确错误，不输出密钥。
4. 增加回归测试：使用密钥文件调用 `/auth/login` 必须返回 200 管理员身份。
5. 更新 ChatGPT 图片服务文档中的首次登录与密钥轮换说明。

## 验收标准

- [ ] 重新运行原生准备脚本后，密钥文件与进程实际密钥一致
- [ ] 使用该文件登录 18003 成功
- [ ] 文件及日志不泄露密钥
- [ ] 密钥轮换后文件、进程和网关同步更新
- [ ] 自动化测试覆盖不一致检测与登录验证

## 关联

- Linear：WK-77
- Draft PR：#7
- 分支：`ws/wk-77-部署-chatgpt2api-公司内网图片兼容服务`
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5019528158,
  "url": "https://github.com/ovws/issues/issues/8#issuecomment-5019528158",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T06:51:09Z",
  "updated_at": "2026-07-20T06:51:09Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-90/chatgpt2api-本地管理密钥文件与运行配置不一致">WK-90</a></p>
```

---

## Issue #9

```json
{
  "id": 4927215688,
  "number": 9,
  "title": "建立公司内网 AI API 鉴权与运行风控规范 (WK-78)",
  "url": "https://github.com/ovws/issues/issues/9",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-20T08:37:24Z",
  "updated_at": "2026-07-22T03:53:01Z",
  "closed_at": "2026-07-22T03:53:01Z",
  "labels": [
    "enhancement",
    "priority: P1",
    "security",
    "component: gateway",
    "component: deployment",
    "component: config",
    "linear-sync"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 3
}
```

### 正文

```text
## 目标

为 Grok、Gemini、ChatGPT 三套公司内网 OpenAI-compatible API 建立统一的访问控制、并发和故障处理规范，并提供只在服务器本机开放的统一管理台。

## 关联

- Linear：[WK-78](https://linear.app/cvm/issue/WK-78/建立公司内网-ai-api-鉴权与运行风控规范)
- 工作分支：`ws/wk-78-建立公司内网-ai-api-鉴权与运行风控规范`
- 当前状态：进行中（Linear 状态类型为 started）

## 网络与权限

- 服务仅允许公司局域网访问
- 第一阶段不开放公网，也不使用内网穿透
- 管理后台仅服务器本机访问
- 普通同事仅使用 `/v1/*`、`/health` 和只读接口文档

## API Key

- 即使只在内网，也必须启用 API Key
- 每位同事使用独立密钥
- 三个平台使用相互独立的密钥
- 支持按人员单独创建、停用、更新和删除已停用密钥
- 不向同事提供项目主密钥或网页账号凭据

## 调度

- Grok、Gemini、ChatGPT 分别使用独立执行锁
- 每个平台默认总生成并发为 1
- 三个平台可以各自同时执行一个任务
- 图片和视频任务排队执行
- 使用唯一任务 ID 防止重复提交
- 视频任务提交后只查询状态，不重复创建同一任务

## 错误处理

- 401 / 403：停止对应服务并人工检查
- 429：暂停对应平台队列
- 5xx / 网络错误：延迟重试，最多 1–2 次
- 连续失败达到阈值后，仅熔断对应平台
- 单个平台异常不得影响另外两个平台

## 日志

日志可记录请求 ID、使用人标识、平台、模型、状态码、耗时和脱敏错误信息。

日志不得记录完整 API Key、网页登录凭据、Authorization Header、Cookie 或其他敏感认证信息。

## 服务隔离

- 三个服务使用独立端口、配置、数据目录和日志
- 不建立必须经过同一个统一网关才能运行的强耦合依赖
- 飞书和 n8n 如继续使用，也只作为调用方访问同一套内网 API

## 当前进展（2026-07-20）

- 已实现本机管理台、独立人员/平台密钥管理、队列状态和运行报告
- 运行状态使用各平台独立 SQLite 文件保存，不依赖外部数据库服务
- 已支持停用密钥的永久删除，同时禁止直接删除仍启用的密钥
- 已修复 Grok 管理页面 Windows IANA 时区校验及 18001 启动卡住问题
- Grok 上游 18001 与网关 8001 已通过正式启动脚本和健康检查验证
- Python 自动化测试、Ruff、PowerShell 解析及相关 Go 测试已通过

## 尚需验证

- 公司局域网 DNS、固定 IP 和防火墙白名单
- 为真实测试用户分发三平台独立密钥并完成轮换/停用演练
- Gemini 与 ChatGPT Image 的真实账号和端到端生成验证
- 三个平台故障隔离、队列暂停/恢复及连续失败熔断演练
- 日志脱敏抽查和管理后台本机访问限制验收

## 完成标准

- [ ] 三个 API 仅允许公司内网访问
- [ ] 每位测试用户获得独立 API Key
- [ ] 管理后台仅服务器本机访问
- [ ] 三个平台分别实现总生成并发 1
- [ ] 已实现任务 ID 和重复提交保护
- [ ] 已验证常见错误的暂停与恢复流程
- [ ] 日志不存在完整密钥和网页账号凭据
- [ ] 某个平台停止时另外两个平台仍可使用

在真实账号、公司局域网和调用端完成端到端验收前，保持 Issue 打开。
```

### 评论（3）

#### 评论 1

```json
{
  "index": 1,
  "id": 5020297489,
  "url": "https://github.com/ovws/issues/issues/9#issuecomment-5020297489",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T08:37:28Z",
  "updated_at": "2026-07-20T12:02:56Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-91/建立公司内网-ai-api-鉴权与运行风控规范-wk-78">WK-91</a></p>
<p><a href="https://linear.app/cvm/issue/WK-93/建立公司内网-ai-api-鉴权与运行风控规范-wk-78">WK-93</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5020308602,
  "url": "https://github.com/ovws/issues/issues/9#issuecomment-5020308602",
  "author": "ovws",
  "created_at": "2026-07-20T08:39:01Z",
  "updated_at": "2026-07-20T08:39:01Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
重新打开：GitHub #9 是代码侧持续跟踪 Issue；Linear 规范记录为 WK-78。GitHub 集成自动生成的 WK-91 仅作为重复项关闭，不代表 WK-78 已完成。真实账号、公司局域网和三平台端到端验收完成前，本 Issue 保持打开。
```

#### 评论 3

```json
{
  "index": 3,
  "id": 5021939807,
  "url": "https://github.com/ovws/issues/issues/9#issuecomment-5021939807",
  "author": "ovws",
  "created_at": "2026-07-20T11:55:18Z",
  "updated_at": "2026-07-20T11:55:18Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
Implementation is now published on branch `ws/wk-78-建立公司内网-ai-api-鉴权与运行风控规范` at commit `2bd2b5b`.

The 8090 console now controls real Grok2API Client Keys and ChatGPT2API User Keys, while Gemini remains explicitly gateway-managed because its upstream has no native key API. Real create/list/use/disable/delete E2E passed for Grok and ChatGPT, and the full Python suite reports 38 passed.

Reopening until the implementation PR is reviewed and merged. Linear: https://linear.app/cvm/issue/WK-78/建立公司内网-ai-api-鉴权与运行风控规范
```

---

## Issue #11

```json
{
  "id": 4928706914,
  "number": 11,
  "title": "补充公司内网 AI API 一键启动 BAT (WK-81)",
  "url": "https://github.com/ovws/issues/issues/11",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-20T11:59:51Z",
  "updated_at": "2026-07-22T03:52:55Z",
  "closed_at": "2026-07-22T03:52:55Z",
  "labels": [
    "enhancement",
    "priority: P2",
    "component: deployment",
    "component: config",
    "linear-sync"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 2
}
```

### 正文

````text
## Goal

Add a pure Windows, Docker-free one-click launcher for the company LAN Grok, Gemini, and ChatGPT OpenAI-compatible APIs plus the loopback-only 8090 control console.

Final entry point:

```text
start-ai-api.bat
```

The launcher must perform preflight checks, repair/diagnose runtime ACLs without deleting databases, start each platform independently, remain idempotent, and report Chinese health results without printing credentials.

## Scope

- Grok API: 8001
- Gemini API: 8002
- ChatGPT Image: 8003
- Admin Console: 8090, loopback only
- no Docker dependency
- linked-worktree runtime-root discovery
- explicit `-RuntimeRoot`, `-PreflightOnly`, and unattended support
- a failed platform must not stop healthy platforms

## Acceptance

- [ ] double-clicking `start-ai-api.bat` starts all four local processes
- [ ] missing files, configuration, directory/SQLite ACLs, and port conflicts are reported precisely
- [ ] repeated runs do not create duplicate processes
- [ ] failure returns non-zero; success returns zero
- [ ] no API Key, Cookie, or account token is printed
- [ ] deployment and troubleshooting documentation is updated

Depends on #9 / WK-78.

Linear: https://linear.app/cvm/issue/WK-81/补充公司内网-ai-api-一键启动-bat

````

### 评论（2）

#### 评论 1

```json
{
  "index": 1,
  "id": 5021977788,
  "url": "https://github.com/ovws/issues/issues/11#issuecomment-5021977788",
  "author": "linear-code[bot]",
  "created_at": "2026-07-20T11:59:56Z",
  "updated_at": "2026-07-20T12:02:58Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-92/补充公司内网-ai-api-一键启动-bat-wk-81">WK-92</a></p>
<p><a href="https://linear.app/cvm/issue/WK-94/补充公司内网-ai-api-一键启动-bat-wk-81">WK-94</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5021982785,
  "url": "https://github.com/ovws/issues/issues/11#issuecomment-5021982785",
  "author": "ovws",
  "created_at": "2026-07-20T12:00:32Z",
  "updated_at": "2026-07-20T12:00:32Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
Implementation published:

- branch: `ws/wk-81-补充公司内网-ai-api-一键启动-bat`
- commit: `1006251` (`feat: add Windows one-click AI API startup (WK-81)`)
- Draft PR: #12
- stacked dependency: #10 (WK-78)

Validation: 45 Python tests passed on the stacked branch, including 7 launcher-specific tests; PowerShell parser, Ruff, Node syntax, and diff checks passed. Real server double-click acceptance and Gemini upstream Cookie recovery remain open, so this issue stays open.

Linear: https://linear.app/cvm/issue/WK-81/补充公司内网-ai-api-一键启动-bat
```

---

## Issue #14

```json
{
  "id": 4935069617,
  "number": 14,
  "title": "[2026-07-21] Grok 视频模型被误发到聊天端点导致 400",
  "url": "https://github.com/ovws/issues/issues/14",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:23:53Z",
  "updated_at": "2026-07-22T03:19:17Z",
  "closed_at": "2026-07-22T03:19:17Z",
  "labels": [
    "bug",
    "priority: P2",
    "component: gateway",
    "故障",
    "工作验证"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 3
}
```

### 正文

```text
现象：2026-07-21 使用 grok-imagine-video-1.5 通过 grok.loser.dev/v1 访问时，客户端把视频模型发送到 /v1/responses 等非视频端点，上游返回 HTTP 400 invalid-argument。影响：Cherry Studio 等普通 OpenAI-compatible 客户端无法创建视频，直接 POST /v1/videos 是临时绕过。根因：上游要求视频模型只能走视频生成端点，而 /v1/models 没有标准能力字段，客户端会把模型当聊天模型。处理：网关隐藏 /v1/models 中的视频模型，对错误端点返回明确 unsupported 400，并保留 /v1/videos 到上游 /v1/videos/generations 的映射；已补充 docs/API.md 与回归测试。待验证：部署后确认 Cherry Studio 不再把视频模型当聊天模型，并完成视频提交、查询、下载回归。来源：docs/BUGS.md 的 BUG-20260721-001。
```

### 评论（3）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029812434,
  "url": "https://github.com/ovws/issues/issues/14#issuecomment-5029812434",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:23:57Z",
  "updated_at": "2026-07-21T03:23:57Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-95/2026-07-21-grok-视频模型被误发到聊天端点导致-400">WK-95</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5029824393,
  "url": "https://github.com/ovws/issues/issues/14#issuecomment-5029824393",
  "author": "ovws",
  "created_at": "2026-07-21T03:26:18Z",
  "updated_at": "2026-07-21T03:26:18Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
Canonical Linear issue: WK-95. The duplicate Linear/GitHub records created by the automatic sync were consolidated into this issue.
```

#### 评论 3

```json
{
  "index": 3,
  "id": 5041436388,
  "url": "https://github.com/ovws/issues/issues/14#issuecomment-5041436388",
  "author": "ovws",
  "created_at": "2026-07-22T03:19:15Z",
  "updated_at": "2026-07-22T03:19:15Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
已由 PR #24（commit e0762b2）完成并合并。已验证 Cherry Studio 实际请求可成功生成并打开 4 秒 MP4；回归测试 `pytest -q`（27 passed）、`ruff check src tests` 和 `git diff --check` 均通过。关联 Linear：WK-95。
```

---

## Issue #15

```json
{
  "id": 4935070910,
  "number": 15,
  "title": "[2026-07-21] Gemini API Cookie 过期导致账号未认证并服务降级",
  "url": "https://github.com/ovws/issues/issues/15",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:24:08Z",
  "updated_at": "2026-07-22T03:52:49Z",
  "closed_at": "2026-07-22T03:52:49Z",
  "labels": [
    "bug",
    "priority: P1",
    "security",
    "component: deployment",
    "故障",
    "工作验证",
    "linear-sync"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 3
}
```

### 正文

```text
现象：2026-07-21 11:11（Asia/Shanghai）Gemini 服务启动后检测到 Account status: UNAUTHENTICATED，提示 session 未认证或 cookies 已过期，随后出现 Gemini returned no generated image 和上游临时错误。影响：Gemini OpenAI-compatible API 的真实生成能力不可用；Grok 与 ChatGPT 图片服务不应受影响。根因：本地 Gemini Cookie/会话已过期或失效，日志未记录 Cookie 内容。处理与验收：在服务器本机重新完成 Gemini Cookie 登录/导入；重启服务并确认 /health 为 ok；用脱敏请求验证 /v1/models、文本生成和图片生成；补充 Cookie 失效后的管理提示与现场恢复文档；确认单个平台故障不影响 Grok/ChatGPT。验收前不得把账号未认证状态视为部署完成。
```

### 评论（3）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029813825,
  "url": "https://github.com/ovws/issues/issues/15#issuecomment-5029813825",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:24:13Z",
  "updated_at": "2026-07-21T03:24:13Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-96/2026-07-21-gemini-api-cookie-过期导致账号未认证并服务降级">WK-96</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5029824585,
  "url": "https://github.com/ovws/issues/issues/15#issuecomment-5029824585",
  "author": "ovws",
  "created_at": "2026-07-21T03:26:20Z",
  "updated_at": "2026-07-21T03:26:20Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
Canonical Linear issue: WK-96. The duplicate Linear/GitHub records created by the automatic sync were consolidated into this issue.
```

#### 评论 3

```json
{
  "index": 3,
  "id": 5029863802,
  "url": "https://github.com/ovws/issues/issues/15#issuecomment-5029863802",
  "author": "ovws",
  "created_at": "2026-07-21T03:33:50Z",
  "updated_at": "2026-07-21T03:33:50Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
补充证据：2026-07-20 Gemini Cookie 缓存文件也出现 PermissionError，2026-07-21 账号检测为 UNAUTHENTICATED；Cookie/缓存 ACL 与账号恢复统一在本 Issue 跟踪。
```

---

## Issue #16

```json
{
  "id": 4935073101,
  "number": 16,
  "title": "[2026-07-21] Grok 视频模型被误发到聊天端点导致 400",
  "url": "https://github.com/ovws/issues/issues/16",
  "state": "closed",
  "state_reason": "duplicate",
  "author": "ovws",
  "created_at": "2026-07-21T03:24:35Z",
  "updated_at": "2026-07-21T03:26:00Z",
  "closed_at": "2026-07-21T03:26:00Z",
  "labels": [
    "bug",
    "priority: P2",
    "component: gateway",
    "故障",
    "工作验证"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 现象

2026-07-21 使用 `grok-imagine-video-1.5` 通过 `grok.loser.dev/v1` 访问时，客户端把视频模型发送到 `/v1/responses` 等非视频端点，上游返回 HTTP 400 `invalid-argument`。

影响：Cherry Studio 等普通 OpenAI-compatible 客户端无法创建视频；直接调用 `POST /v1/videos` 是临时绕过。

## 根因

上游要求视频模型只能走视频生成端点，而 `/v1/models` 没有标准能力字段，客户端会把模型当成聊天模型。

## 已处理

网关隐藏 `/v1/models` 中的视频模型，对错误端点返回明确 `unsupported` 400，并保留 `/v1/videos` 到上游 `/v1/videos/generations` 的映射；已补充 `docs/API.md` 与回归测试。

## 待验收

部署后确认 Cherry Studio 不再把视频模型当聊天模型，并完成视频提交、查询、下载回归。

GitHub: [https://github.com/ovws/internal-ai-api-config/issues/14](<https://github.com/ovws/internal-ai-api-config/issues/14>)<br>来源：`docs/BUGS.md` 的 `BUG-20260721-001`。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029815922,
  "url": "https://github.com/ovws/issues/issues/16#issuecomment-5029815922",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:24:37Z",
  "updated_at": "2026-07-21T03:24:37Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-97/2026-07-21-grok-视频模型被误发到聊天端点导致-400">WK-97</a></p>
```

---

## Issue #17

```json
{
  "id": 4935073639,
  "number": 17,
  "title": "[2026-07-21] Gemini API Cookie 过期导致账号未认证并服务降级",
  "url": "https://github.com/ovws/issues/issues/17",
  "state": "closed",
  "state_reason": "duplicate",
  "author": "ovws",
  "created_at": "2026-07-21T03:24:41Z",
  "updated_at": "2026-07-21T03:26:04Z",
  "closed_at": "2026-07-21T03:26:04Z",
  "labels": [
    "bug",
    "priority: P1",
    "security",
    "component: deployment",
    "故障",
    "工作验证"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 现象

2026-07-21 11:11（Asia/Shanghai）Gemini 服务启动后检测到 `Account status: UNAUTHENTICATED`，提示 session 未认证或 cookies 已过期；随后出现 `Gemini returned no generated image` 和上游临时错误。

影响：Gemini OpenAI-compatible API 的真实生成能力不可用；Grok 与 ChatGPT 图片服务不应受影响。

## 根因

本地 Gemini Cookie/会话已过期或失效，日志未记录 Cookie 内容。

## 处理与验收

* 在服务器本机重新完成 Gemini Cookie 登录/导入
* 重启服务并确认 `/health` 为 `ok`
* 用脱敏请求验证 `/v1/models`、文本生成和图片生成
* 补充 Cookie 失效后的管理提示与现场恢复文档
* 确认单个平台故障不影响 Grok/ChatGPT

验收前不得把账号未认证状态视为部署完成。

GitHub: [https://github.com/ovws/internal-ai-api-config/issues/15](<https://github.com/ovws/internal-ai-api-config/issues/15>)
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029816351,
  "url": "https://github.com/ovws/issues/issues/17#issuecomment-5029816351",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:24:42Z",
  "updated_at": "2026-07-21T03:24:42Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-98/2026-07-21-gemini-api-cookie-过期导致账号未认证并服务降级">WK-98</a></p>
```

---

## Issue #18

```json
{
  "id": 4935112317,
  "number": 18,
  "title": "[2026-07-20] Grok 上游连续 503 导致生成队列熔断暂停",
  "url": "https://github.com/ovws/issues/issues/18",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:31:55Z",
  "updated_at": "2026-07-27T01:15:59Z",
  "closed_at": "2026-07-21T03:39:58Z",
  "labels": [
    "priority: P1",
    "component: gateway",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-20 17:37（Asia/Shanghai）Grok 网关连续收到上游 HTTP 503，触发安全重试后连续失败阈值，队列被暂停并要求人工复核。影响：Grok 图片/视频等生成能力整体不可用，需人工恢复，Grok 单平台故障不应影响 Gemini 和 ChatGPT。证据：logs/grok/grok-gateway.20260720-083244-725.err.log 与 logs/grok/service.log.2026-07-20。待处理：确认上游 503 的根因和恢复条件；验证熔断/恢复状态不会丢任务、不重复提交；补充运维告警和人工恢复步骤；完成 Grok 端到端回归。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029853608,
  "url": "https://github.com/ovws/issues/issues/18#issuecomment-5029853608",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:31:58Z",
  "updated_at": "2026-07-21T03:31:58Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-99/2026-07-20-grok-上游连续-503-导致生成队列熔断暂停">WK-99</a></p>
```

---

## Issue #19

```json
{
  "id": 4935112428,
  "number": 19,
  "title": "[2026-07-20] ChatGPT2API SQLite 与媒体目录权限导致启动和图片写入失败",
  "url": "https://github.com/ovws/issues/issues/19",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:31:57Z",
  "updated_at": "2026-08-25T00:28:33Z",
  "closed_at": "2026-07-21T03:39:28Z",
  "labels": [
    "priority: P1",
    "component: deployment",
    "component: config",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-20 ChatGPT2API 上游和 8003 网关多次出现 sqlite3.OperationalError: unable to open database file；图片生成后写入 data/images 和 logs.jsonl 又出现 PermissionError，网关同时出现 RemoteProtocolError，客户端收到不完整响应。影响：服务无法稳定启动，图片生成/编辑结果无法保存或响应中断。证据：logs/chatgpt-image/chatgpt-image-upstream.20260720-085331-221.err.log、chatgpt-image-upstream.20260720-090316-229.err.log、chatgpt-image-gateway.20260720-090318-387.err.log 和 chatgpt-image-gateway.20260720-090918-076.err.log。待处理：统一确认运行账户、数据目录和 SQLite 文件 ACL；启动前检查目录可读写；验证图片、日志和数据库写入；补充权限失败时的明确错误和回归测试。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029853745,
  "url": "https://github.com/ovws/issues/issues/19#issuecomment-5029853745",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:32:00Z",
  "updated_at": "2026-07-21T03:32:00Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-100/2026-07-20-chatgpt2api-sqlite-与媒体目录权限导致启动和图片写入失败">WK-100</a></p>
```

---

## Issue #20

```json
{
  "id": 4935112922,
  "number": 20,
  "title": "[2026-07-20] Gemini 上游生成被静默中止并触发服务降级",
  "url": "https://github.com/ovws/issues/issues/20",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:32:00Z",
  "updated_at": "2026-07-27T01:14:29Z",
  "closed_at": "2026-07-21T03:39:58Z",
  "labels": [
    "priority: P2",
    "component: gateway",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-20 Gemini 多次出现 Gemini upstream operation failed，底层提示 Google 可能静默中止原始请求；服务随后进入 gemini_backend_degraded。2026-07-21 又出现 Unknown API error code 1100 与 Gemini returned no generated image。影响：Gemini 文本/图片生成存在间歇性失败，当前账号 Cookie 过期另见 GitHub ovws/internal-ai-api-config#15。证据：logs/gemini/service.log.2026-07-20、logs/gemini/gemini-gateway.20260720-085320-725.err.log 和 logs/gemini/service.log。待处理：区分账号失效、上游临时错误和无结果响应；统一返回可诊断错误；确认失败后队列继续；补充有限重试、降级状态和真实账号回归测试。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029854181,
  "url": "https://github.com/ovws/issues/issues/20#issuecomment-5029854181",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:32:04Z",
  "updated_at": "2026-07-21T03:32:04Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-101/2026-07-20-gemini-上游生成被静默中止并触发服务降级">WK-101</a></p>
```

---

## Issue #21

```json
{
  "id": 4935113252,
  "number": 21,
  "title": "[2026-07-20] 管理后台缺少静态前端入口导致页面 500",
  "url": "https://github.com/ovws/issues/issues/21",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:32:02Z",
  "updated_at": "2026-07-27T01:14:21Z",
  "closed_at": "2026-07-21T03:40:06Z",
  "labels": [
    "priority: P2",
    "component: deployment",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-20 管理后台请求首页时反复报 FileNotFoundError，缺少 src/internal_ai_api/admin_ui/index.html，页面返回 500。影响：管理员无法打开本机 8090 管理后台；服务 API 进程本身可能仍在运行。证据：logs/admin/internal-ai-admin.20260720-235201-687.err.log。待处理：启动前检查 admin_ui/index.html、assets 和运行根目录；缺失时输出明确部署路径错误；验证资源随部署包/启动脚本正确定位；补充管理后台首页回归测试。相关启动前预检：GitHub #11 / Linear WK-81。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029854512,
  "url": "https://github.com/ovws/issues/issues/21#issuecomment-5029854512",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:32:07Z",
  "updated_at": "2026-07-21T03:32:07Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-102/2026-07-20-管理后台缺少静态前端入口导致页面-500">WK-102</a></p>
```

---

## Issue #22

```json
{
  "id": 4935122942,
  "number": 22,
  "title": "[2026-07-20] Gemini 网关重启时 8002 端口被占用导致启动失败",
  "url": "https://github.com/ovws/issues/issues/22",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:33:40Z",
  "updated_at": "2026-07-27T01:14:11Z",
  "closed_at": "2026-07-21T03:40:08Z",
  "labels": [
    "priority: P2",
    "component: deployment",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-21 07:52 启动 Gemini 网关时，Uvicorn 报 WinError 10048，无法绑定 0.0.0.0:8002。影响：Gemini 网关重启/恢复失败，旧进程或端口占用状态会阻断服务启动。证据：logs/gemini/gemini-gateway.20260720-235146-574.err.log。待处理：启动前检查 8002 端口及所属进程；区分旧实例、重复启动和其他程序占用；启动脚本输出明确处理建议；验证停止、重启和故障恢复不会误杀其他平台。关联启动预检：GitHub #11 / Linear WK-81。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029863263,
  "url": "https://github.com/ovws/issues/issues/22#issuecomment-5029863263",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:33:45Z",
  "updated_at": "2026-07-21T03:33:45Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-103/2026-07-20-gemini-网关重启时-8002-端口被占用导致启动失败">WK-103</a></p>
```

---

## Issue #23

```json
{
  "id": 4935123109,
  "number": 23,
  "title": "[2026-07-20] 管理后台 SQLite 数据库无法打开导致管理接口异常",
  "url": "https://github.com/ovws/issues/issues/23",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-21T03:33:42Z",
  "updated_at": "2026-07-27T01:14:03Z",
  "closed_at": "2026-07-21T05:45:17Z",
  "labels": [
    "priority: P1",
    "component: deployment",
    "component: config",
    "故障",
    "工作验证"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
现象：2026-07-20 管理后台多次报 sqlite3.OperationalError: unable to open database file。影响：管理后台无法稳定读取或写入运行状态、密钥和审计数据，管理员操作会失败；普通 API 也可能因共用运行目录权限受到影响。证据：logs/admin/internal-ai-admin.err.log 与 logs/admin/internal-ai-admin.20260720-085404-022.err.log。待处理：确认管理进程运行账户、SQLite 文件父目录和 WAL/临时文件 ACL；启动前执行可写性检查；输出脱敏且可操作的错误；增加管理员数据库读写回归测试。关联启动预检：GitHub #11 / Linear WK-81。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5029863371,
  "url": "https://github.com/ovws/issues/issues/23#issuecomment-5029863371",
  "author": "linear-code[bot]",
  "created_at": "2026-07-21T03:33:46Z",
  "updated_at": "2026-07-21T03:33:46Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-104/2026-07-20-管理后台-sqlite-数据库无法打开导致管理接口异常">WK-104</a></p>
```

---

## Issue #26

```json
{
  "id": 4947974559,
  "number": 26,
  "title": "制定并部署本地仓库方案（AList + Eagle）",
  "url": "https://github.com/ovws/issues/issues/26",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-22T10:28:10Z",
  "updated_at": "2026-08-31T11:27:32Z",
  "closed_at": "2026-07-23T00:02:01Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "自动化",
    "文件上传"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

搭建本地仓库与素材管理方案：使用 AList 提供统一文件访问，使用 Eagle 整理图片及相关素材，并将成果导出至指定目录。

## 工作项

- [ ] 梳理本地仓库目录结构、存储位置与访问需求
- [ ] 安装并配置 AList，建立文件库、挂载与访问权限
- [ ] 安装并配置 Eagle，制定图片/素材导入、标签、分类与去重规则
- [ ] 明确 AList 与 Eagle 的协作边界及备份策略
- [ ] 按约定格式导出图片等内容至指定目录
- [ ] 验证导出内容完整性、可访问性与后续维护流程

## 待确认

* 指定导出目录的绝对路径
* 本地仓库的实际来源、容量与操作系统环境
* 是否需要局域网/公网访问，以及权限和备份要求

## 验收标准

* AList 可稳定访问计划中的本地仓库内容
* Eagle 中图片等素材已完成约定分类与标签整理
* 导出文件位于已确认目录，结构清晰且可复核
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5044717772,
  "url": "https://github.com/ovws/issues/issues/26#issuecomment-5044717772",
  "author": "linear-code[bot]",
  "created_at": "2026-07-22T10:28:11Z",
  "updated_at": "2026-07-22T10:28:11Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-105/制定并部署本地仓库方案alist-eagle">WK-105</a></p>
```

---

## Issue #27

```json
{
  "id": 4960797008,
  "number": 27,
  "title": "补充 Grok 会员和 ChatGPT 会员",
  "url": "https://github.com/ovws/issues/issues/27",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-23T16:20:27Z",
  "updated_at": "2026-07-24T02:16:59Z",
  "closed_at": "2026-07-24T02:16:32Z",
  "labels": [
    "订阅到期"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
明天补充 Gluca 会员和 ChatGPT 会员。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5060785399,
  "url": "https://github.com/ovws/issues/issues/27#issuecomment-5060785399",
  "author": "linear-code[bot]",
  "created_at": "2026-07-23T16:20:28Z",
  "updated_at": "2026-07-23T16:20:28Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-106/补充-gluca-会员和-chatgpt-会员">WK-106</a></p>
```

---

## Issue #29

```json
{
  "id": 4964752178,
  "number": 29,
  "title": "将四个 AI API 仓库合并为单仓库",
  "url": "https://github.com/ovws/issues/issues/29",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-24T02:57:47Z",
  "updated_at": "2026-07-24T03:16:02Z",
  "closed_at": "2026-07-24T03:16:02Z",
  "labels": [
    "工作验证",
    "Improvement",
    "自动化"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

将以下四个仓库整合到 `ovws/internal-ai-api-config`，让使用者只需克隆一个仓库即可获得网关、部署脚本和三套上游完整源码：

* `ovws/internal-ai-api-config`
* `ovws/internal-ai-grok2api`
* `ovws/internal-ai-gemini-api`
* `ovws/internal-ai-chatgpt2api`

## 实施方案

采用最简单的 vendoring 单仓库方案：

* 三套上游完整源码直接纳入 `internal-ai-api-config/upstream/`。
* 移除安装和容器准备脚本中的嵌套 Git clone、fetch、checkout 流程。
* 在 `config/upstreams.json` 保留原始上游、私有镜像和导入 commit，便于审计。
* 本地凭据、Cookie、数据库、日志、缓存和生成文件继续由 `.gitignore` 排除。
* 为 Gemini 增加脱离嵌套 `.git` 后所需的确定版本 fallback。

## 已完成

- [X] 导入 Grok2API `9d4bba4`
- [X] 导入 Gemini-API `143814a`
- [X] 导入 ChatGPT2API `1f96b49`
- [X] 改造单仓库安装流程
- [X] 更新 README 和部署文档
- [X] 完成敏感信息扫描
- [X] 推送分支与提交
- [X] 创建 Draft PR

## 验证

* 单仓库安装脚本成功执行，无需克隆其他仓库。
* Grok 后端 `go test ./...` 全部通过。
* Python lint 和编译检查通过。
* 根项目 pytest：45 通过、2 个 `main` 既有基线失败；本次未修改对应 `src/` 和 `tests/`。
* 未发现真实 API Key、Cookie、Token、数据库或日志进入提交。

## 待完成 / 验收

- [X] 审核并合并 Draft PR ovws/internal-ai-api-config#28 到 `main`
- [X] 合并后从 `main` 全新克隆并复核单仓库安装
- [X] 视需要单独处理根项目现存的 2 个测试基线失败
- [X] 真实账号、局域网和防火墙端到端验证仍依赖部署机环境

三个旧私有镜像暂时保留作历史参考，本任务不删除仓库。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5065700017,
  "url": "https://github.com/ovws/issues/issues/29#issuecomment-5065700017",
  "author": "linear-code[bot]",
  "created_at": "2026-07-24T02:57:49Z",
  "updated_at": "2026-07-24T02:57:49Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-107/将四个-ai-api-仓库合并为单仓库">WK-107</a></p>
```

---

## Issue #30

```json
{
  "id": 4981300458,
  "number": 30,
  "title": "Jira 双向同步测试 SYNC-726A",
  "url": "https://github.com/ovws/issues/issues/30",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-26T15:45:27Z",
  "updated_at": "2026-07-27T00:23:04Z",
  "closed_at": "2026-07-27T00:23:04Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
用于验证 Linear ↔ Jira 双向同步。

创建来源：Linear<br>测试完成后可删除。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5084196436,
  "url": "https://github.com/ovws/issues/issues/30#issuecomment-5084196436",
  "author": "linear-code[bot]",
  "created_at": "2026-07-26T15:45:30Z",
  "updated_at": "2026-07-26T15:45:30Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-109/jira-双向同步测试-sync-726a">WK-109</a></p>
```

---

## Issue #31

```json
{
  "id": 4984626127,
  "number": 31,
  "title": "协助运营批量生图",
  "url": "https://github.com/ovws/issues/issues/31",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-07-27T05:26:16Z",
  "updated_at": "2026-07-28T02:53:38Z",
  "closed_at": "2026-07-28T02:53:38Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
(无正文)
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5087586306,
  "url": "https://github.com/ovws/issues/issues/31#issuecomment-5087586306",
  "author": "linear-code[bot]",
  "created_at": "2026-07-27T05:26:17Z",
  "updated_at": "2026-07-27T05:26:17Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-110/协助运营批量生图">WK-110</a></p>
```

---

## Issue #32

```json
{
  "id": 4994364542,
  "number": 32,
  "title": "AList 多人选片共享工具（Windows 单文件版）",
  "url": "https://github.com/ovws/issues/issues/32",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-07-28T02:52:50Z",
  "updated_at": "2026-07-28T02:58:11Z",
  "closed_at": null,
  "labels": [
    "component: deployment",
    "工作验证",
    "自动化",
    "特性"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

````text
## 背景

AList 作为团队图片库时，同事一次需要浏览大量图片，但原页面无法直观看出图片是否已被其他同事选用；通过文件重命名表达用途又可能在后续导出时出现不同文件名并存。

## 已完成

- [X] 在 AList 图片卡片右上角增加快速“选用/取消选用”
- [X] 支持备选、封面、内页、社媒、已下载等用途标签
- [X] 显示选用人数、具体选用人及每个人的标签
- [X] 提供局域网共享状态服务，约 3 秒自动同步
- [X] 打包为 Windows 单文件 PowerShell，不依赖 Docker、Node 或数据库
- [X] 支持开机任务、防火墙规则、状态查看、保留数据卸载
- [X] 支持通过覆盖单个脚本并重启完成后续更新
- [X] 增加 20%–100% 标记透明度设置，默认 70%，按浏览器保存
- [X] 支持离线写入回滚、服务恢复自动重连、数据持久化与备份

## 使用方法

### 管理员首次安装

1. 将 `alist-picker-windows.ps1` 放到固定目录，例如 `D:\AListPicker\alist-picker-windows.ps1`。
2. 在该目录打开 PowerShell，运行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\alist-picker-windows.ps1
   ```
3. 选择 `1. 首次安装 / 重新安装`，并确认管理员权限。
4. 脚本会注册 Windows 开机任务、开放专用/域网络的 TCP `5245` 端口、启动共享服务，并把 AList 自定义头部代码复制到剪贴板。
5. 将剪贴板内容粘贴到 AList 后台的“自定义头部”，保存后刷新 AList 页面。

### 同事日常选片

1. 打开 AList：`http://192.168.1.26:5244/`。
2. 首次使用时输入自己的姓名；右上角“选片”状态按钮可随时切换身份。
3. 点击图片右上角的 `＋ 选用` 进行选用，再次点击可取消自己的选用。
4. 点击 `🏷` 可设置“备选、封面、内页、社媒、已下载”等用途标签，并查看该图片的所有选用人和标签。
5. 在标签面板的“显示设置”中，可把标记透明度调到 20%–100%；设置仅保存在当前浏览器，不影响其他同事。
6. 页面右上角显示 `选片 · 已同步` 时代表操作已保存。若显示“离线”，未保存的操作会自动回滚；服务恢复后会自动重连。
7. 多人状态通常在约 3 秒内同步，无需通过重命名文件来表达选用状态。

### 更新与维护

1. 用新版覆盖原路径下的 `alist-picker-windows.ps1`。
2. 重新运行脚本，选择 `2. 重启服务（覆盖新脚本后选这个）`。
3. AList 自定义头部无需重新粘贴，历史选片数据不会被覆盖。
4. 选片数据位于脚本目录的 `alist-picker-data.json`，并自动维护 `alist-picker-data.json.bak` 备份。
5. 运行脚本可选择查看状态、重新复制自定义头部，或卸载服务并保留数据。
6. 该服务只适用于可信局域网，请勿把端口 `5245` 暴露到公网。

## 验证

* 两个独立用户之间选用状态和标签可互相同步
* 12 人并发写入通过
* 服务重启后数据恢复通过
* 非法网页来源被 CORS 拒绝
* JavaScript、PowerShell 5.1 语法和单文件重新构建通过
* 低透明度、刷新保留、交互恢复清晰通过

## 交付

* GitHub: [https://github.com/ovws/alist-picker-windows](<https://github.com/ovws/alist-picker-windows>)
* 默认分支: `main`
* 初始提交: `3e76ce6`
* 当前版本: `v1.1.0`

## 运维说明

* AList: `http://192.168.1.26:5244`
* 共享服务默认端口: `5245`
* 运行数据保存为 `alist-picker-data.json`，更新脚本不会覆盖
* 服务仅面向可信局域网，不应将 `5245` 暴露公网
````

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5099381732,
  "url": "https://github.com/ovws/issues/issues/32#issuecomment-5099381732",
  "author": "linear-code[bot]",
  "created_at": "2026-07-28T02:52:51Z",
  "updated_at": "2026-07-28T02:52:51Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-111/完成-alist-多人选片共享工具windows-单文件版">WK-111</a></p>
```

---

## Issue #33

```json
{
  "id": 5086162692,
  "number": 33,
  "title": "修复图片文字变形并恢复原文“永久”",
  "url": "https://github.com/ovws/issues/issues/33",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-07T02:05:35Z",
  "updated_at": "2026-08-31T11:27:19Z",
  "closed_at": "2026-08-17T06:34:24Z",
  "labels": [
    "故障",
    "工作验证",
    "商品主图",
    "图像编辑"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源日期

2026-08-07

## 聊天上下文摘要

今天对一张图片进行整体质量优化时，生成结果出现了明显文字变形；同时把原图中的“永久”错误改成了“永不过期”。用户明确要求：图片整体质量可以优化，但画面上的文字必须严格保持正确，不能擅自改写原文。

## 下一步

重新处理该图片：

* 提升整体清晰度和真实感；
* 所有原有文字逐字保持正确，不变形、不缺字、不新增内容；
* 将错误的“永不过期”恢复为原本的“永久”；
* 输出前重点检查文字区域，确认与原图一致后再交付。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5211240219,
  "url": "https://github.com/ovws/issues/issues/33#issuecomment-5211240219",
  "author": "linear-code[bot]",
  "created_at": "2026-08-07T02:05:37Z",
  "updated_at": "2026-08-07T02:05:37Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-112/修复图片文字变形并恢复原文永久">WK-112</a></p>
```

---

## Issue #34

```json
{
  "id": 5299542665,
  "number": 34,
  "title": "沉淀眼镜商品主图批量生产与验收规范",
  "url": "https://github.com/ovws/issues/issues/34",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:20:32Z",
  "updated_at": "2026-09-01T11:06:28Z",
  "closed_at": "2026-09-01T11:06:28Z",
  "labels": [
    "工作验证",
    "Improvement",
    "商品主图",
    "图像编辑",
    "AI 工具"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮商品主图/模特佩戴图生成与返工记录。

## 目标

把反复出现的主图要求固化为可复用生产规范，减少“人物歪、眼镜歪、AI 感、商品变形”等返工。

## 固定约束

* 商品眼镜结构、颜色、镜片、鼻托、镜腿不得擅自改变。
* 人物正面/近正面时头部保持正，不能明显侧歪；眼镜水平、居中。
* 人物左右边距协调，商品主图优先 1:1；需要时使用 960×960 等平台尺寸。
* 真人质感优先：保留皮肤纹理、自然光影和正常面部比例，避免塑料脸/过度磨皮。
* 手指数量、镜腿穿模、鼻托悬空、镜片左右不一致等属于必须返工问题。
* 夏季服装替换时只改服装，不改变人物核心长相、眼镜和场景关系。
* 同一组要求“同一个人/同一场景”时，人物身份、发型、背景和整体光线要稳定。

## 典型场景

* 商品主图模特展示
* 户外/登山/骑行
* 居家/车内/机场/高铁
* 同一人物多动作、多张独立输出

## 验收

形成检查清单，并与 [WK-113](https://linear.app/cvm/issue/WK-113/制作主图检查器)「制作主图检查器」的自动检测项保持一致。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477571637,
  "url": "https://github.com/ovws/issues/issues/34#issuecomment-5477571637",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:20:34Z",
  "updated_at": "2026-08-31T11:20:34Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-119/沉淀眼镜商品主图批量生产与验收规范">WK-119</a></p>
```

---

## Issue #35

```json
{
  "id": 5299544604,
  "number": 35,
  "title": "完善竞品链接图包克隆 Skill（A15 实测）",
  "url": "https://github.com/ovws/issues/issues/35",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:20:48Z",
  "updated_at": "2026-09-01T10:36:39Z",
  "closed_at": "2026-09-01T10:36:39Z",
  "labels": [
    "自动化",
    "特性",
    "商品主图",
    "图像编辑",
    "AI 工具",
    "电商运营",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 背景

基于现有网站克隆 Skill 的能力，改造成“输入竞品商品链接 → 获取竞品图包/页面视觉结构 → 结合自有商品素材生成可用图包”的电商工作流。

## 参考与约束

* 参考模板：IndieSkills/ai-website-cloner-template。
* 自有 Skill 仓库：ovws/skills。
* 实测竞品：淘宝商品 A15，item id 1005389220375。
* 不修改上游参考仓库本身，只在自有 Skill 中实现。
* 竞品链接应能在平台/任务参数中维护，而不是写死。
* 输出文件路径需要清晰可见，便于 Codex/人工继续使用。
* 对接现有 Prism 图片生成工作流时，产物必须遵循平台图片规范和商品真实性要求。

## 交付

* Skill 目录、SKILL.md、必要脚本/说明。
* 竞品链接解析/采集策略与失败兜底。
* A15 素材的完整实测结果。
* 结果目录、文件命名、日志和验收说明。

## 验收

能从竞品链接和自有素材出发生成一套可继续编辑/上架的商品视觉素材，并且不会擅自改变自有眼镜商品结构。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477574494,
  "url": "https://github.com/ovws/issues/issues/35#issuecomment-5477574494",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:20:52Z",
  "updated_at": "2026-08-31T11:20:53Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-121/完善竞品链接图包克隆-skilla15-实测">WK-121</a></p>
<p><a href="https://linear.app/cvm/issue/WK-120/完善竞品链接图包克隆-skilla15-实测">WK-120</a></p>
```

---

## Issue #36

```json
{
  "id": 5299546207,
  "number": 36,
  "title": "搭建淘宝/天猫竞品商品抓取 Skill",
  "url": "https://github.com/ovws/issues/issues/36",
  "state": "closed",
  "state_reason": "not_planned",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:00Z",
  "updated_at": "2026-09-01T10:37:42Z",
  "closed_at": "2026-09-01T10:37:42Z",
  "labels": [
    "工作验证",
    "自动化",
    "特性",
    "电商运营",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

把日常竞品调研从手工浏览整理成可复用 Skill：输入淘宝/天猫商品链接或店铺目标后，抓取并结构化商品基础信息、SKU、主图/详情视觉、标题卖点等可公开获取信息。

## 第一版范围

* 商品标题、价格区间、SKU/规格展示。
* 主图、详情页图片与可见卖点结构。
* 店铺/商品基础公开信息。
* 输出 JSON/Markdown 等便于后续分析的数据。
* 支持手动浏览器操作作为网页反爬/登录场景的兜底，不要求绕过平台安全机制。

## 与现有工作的关系

* 为 [WK-118](https://linear.app/cvm/issue/WK-118/学习天猫日常运营) 天猫日常运营学习提供竞品数据。
* 为 ovws/internal-ai-api-config#35 竞品图包克隆 Skill 提供结构化来源。

## 验收

至少能对一个真实淘宝/天猫商品完成采集、结构化输出和人工复核；失败时能明确提示需要登录、验证或手动操作。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477575995,
  "url": "https://github.com/ovws/issues/issues/36#issuecomment-5477575995",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:02Z",
  "updated_at": "2026-08-31T11:21:02Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-122/搭建淘宝天猫竞品商品抓取-skill">WK-122</a></p>
```

---

## Issue #37

```json
{
  "id": 5299547368,
  "number": 37,
  "title": "开发抖音商城评论图片批量下载工具",
  "url": "https://github.com/ovws/issues/issues/37",
  "state": "closed",
  "state_reason": "not_planned",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:09Z",
  "updated_at": "2026-10-08T01:33:21Z",
  "closed_at": "2026-10-08T01:33:21Z",
  "labels": [
    "工作验证",
    "自动化",
    "特性",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 背景

日常商品运营需要批量整理抖音商城店铺评论中的买家秀图片，手工逐张保存效率低。

## 目标

形成一个面向自有/有权访问店铺页面的批量下载工具，能够在浏览器正常访问评论内容的前提下，提取并保存评论图片。

## 第一版

* 指定商品/评论页面后扫描当前可见评论图片。
* 支持滚动加载和去重。
* 按商品、日期或评论 ID 建目录并保留必要元数据。
* 保持原图或可获取的最高质量版本。
* 对登录、验证码、风控等场景停止自动化并提示人工处理，不绕过平台安全控制。

## 验收

对至少一个可正常访问的商品评论页完成批量下载，图片去重正确，文件命名和目录可直接用于后续素材筛选。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477577309,
  "url": "https://github.com/ovws/issues/issues/37#issuecomment-5477577309",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:10Z",
  "updated_at": "2026-08-31T11:21:10Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-123/开发抖音商城评论图片批量下载工具">WK-123</a></p>
```

---

## Issue #38

```json
{
  "id": 5299548564,
  "number": 38,
  "title": "完善 dydownloader Windows EXE 与 GitHub Release 交付",
  "url": "https://github.com/ovws/issues/issues/38",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:18Z",
  "updated_at": "2026-09-01T10:36:33Z",
  "closed_at": "2026-09-01T10:36:33Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "自动化",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

将 ovws/dydownloader 整理为可直接交付给 Windows 用户的“抖音批量下载工具”。

## 要求

* 按用户名/账号组织下载目录，避免多账号素材混在一起。
* 完成 Windows 单文件或尽量少依赖的 EXE 构建。
* 中文产品名统一为“抖音批量下载工具”。
* 验证常见下载场景、异常链接、重复任务和目录写入。
* GitHub Release 中上传可执行文件，写明版本、使用方式和已知限制。
* 不在 Release 或日志中包含账号 Cookie、Token 等敏感信息。

## 验收

全新 Windows 环境能按说明启动并完成至少一次批量下载；Release 可直接获取对应构建产物。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477578777,
  "url": "https://github.com/ovws/issues/issues/38#issuecomment-5477578777",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:20Z",
  "updated_at": "2026-08-31T11:21:20Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-124/完善-dydownloader-windows-exe-与-github-release-交付">WK-124</a></p>
```

---

## Issue #39

```json
{
  "id": 5299550185,
  "number": 39,
  "title": "Proxy Config Studio：多客户端代理配置转换与校验",
  "url": "https://github.com/ovws/issues/issues/39",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:30Z",
  "updated_at": "2026-09-01T10:36:31Z",
  "closed_at": "2026-09-01T10:36:31Z",
  "labels": [
    "component: config",
    "Improvement",
    "自动化",
    "特性",
    "GitHub",
    "网络代理"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

在 ovws/Proxy 中集成代理配置转换工具，形成可直接使用的配置转换与语法检查入口。

## 输入/输出

重点支持以 Surge-CN 等现有配置为输入，转换到：

* Stash
* Loon
* Quantumult X
* Clash Meta / Mihomo
* Party
* Egern

同时保留/适配 Snell 节点版本差异，对不兼容字段给出明确降级提示，而不是静默丢配置。

## 功能

* 自动识别输入格式。
* 规则、策略组、节点、DNS/MITM/Rewrite 等尽量进行语义映射。
* 语法检查与错误定位。
* 转换结果左右分栏查看与复制/下载。
* 对目标客户端不支持的能力输出警告。
* 保持现有常用区域策略和 Automatic/AllServer 等组结构的可读性。

## 参考

可借鉴 Zephyruso/zashboard 的界面/交互思路，但自有实现和代码落在 ovws/Proxy。

## 验收

用真实 Surge-CN 配置分别生成多个客户端配置，并在至少 3 个目标客户端/解析器中完成语法验证。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477580730,
  "url": "https://github.com/ovws/issues/issues/39#issuecomment-5477580730",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:32Z",
  "updated_at": "2026-08-31T11:21:32Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-125/proxy-config-studio多客户端代理配置转换与校验">WK-125</a></p>
```

---

## Issue #40

```json
{
  "id": 5299552138,
  "number": 40,
  "title": "部署 Proxy Config Studio 独立 Web 版并完成端到端验收",
  "url": "https://github.com/ovws/issues/issues/40",
  "state": "closed",
  "state_reason": "not_planned",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:45Z",
  "updated_at": "2026-09-01T10:37:06Z",
  "closed_at": "2026-09-01T10:37:06Z",
  "labels": [
    "component: deployment",
    "GitHub",
    "网络代理",
    "网站/前端",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

将代理配置转换能力部署为独立 Web 工具，方便 Windows/手机等设备直接访问，而不依赖本地开发环境。

## 要求

* 保持简洁专业的工具型 UI，转换成功有明确状态反馈。
* 支持粘贴/上传配置和结果复制/下载。
* 重点验证 Surge → Stash/Loon/Quantumult X/Clash Meta/Party/Egern。
* Snell 节点需要识别版本差异并提示兼容性。
* 转换失败时保留原始错误位置与不支持字段说明。
* Vercel 部署后用真实配置进行浏览器端到端测试。

## 验收

线上地址可访问，至少 3 类目标配置通过实际解析/客户端验证；移动端和桌面端均可完成完整转换。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477583092,
  "url": "https://github.com/ovws/issues/issues/40#issuecomment-5477583092",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:47Z",
  "updated_at": "2026-08-31T11:21:47Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-126/部署-proxy-config-studio-独立-web-版并完成端到端验收">WK-126</a></p>
```

---

## Issue #41

```json
{
  "id": 5299553576,
  "number": 41,
  "title": "Cindy / Pi 微信 Relay 多模型远程 Agent 接入",
  "url": "https://github.com/ovws/issues/issues/41",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:21:56Z",
  "updated_at": "2026-09-01T11:06:23Z",
  "closed_at": "2026-09-01T11:06:23Z",
  "labels": [
    "component: deployment",
    "component: config",
    "自动化",
    "特性",
    "AI 工具",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

打通“个人微信插件 → Cindy Relay → Windows 本地 Agent”的远程链路，并在 Cindy 内支持选择不同模型/Agent。

## 架构

* 微信端：作为消息入口。
* Relay：计划部署到 Cloudflare 等可持续访问环境。
* Windows：运行 Cindy/Pi Agent，与 Relay 建立连接。
* 模型：支持现有 GPT 系列，并接入自有 Gemini API。

## 本月讨论的具体要求

* Relay 配置流程要有明确第一步总结。
* 插件中提供“测试链接是否可用”的按钮/检查能力。
* 支持多个 API Key/Provider，而不是只写死单一模型。
* 将 `ovws/internal-ai-gemini-api` 暴露为 Cindy 可选择的 Gemini 模型来源，覆盖 Gemini 2.5/3 等实际可用模型。
* 后续考虑 Skill 选择/调用能力。
* 配置与日志不得泄露 API Key、Cookie 或微信敏感数据。

## 验收

微信发送请求后可稳定经 Relay 到达本地 Agent；至少 GPT 与自有 Gemini 两类 Provider 可切换；断线/重连有明确状态。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477584837,
  "url": "https://github.com/ovws/issues/issues/41#issuecomment-5477584837",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:21:58Z",
  "updated_at": "2026-08-31T11:21:58Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-127/cindy-pi-微信-relay-多模型远程-agent-接入">WK-127</a></p>
```

---

## Issue #42

```json
{
  "id": 5299555358,
  "number": 42,
  "title": "修复 Cindy Relay 连接关闭 1006 并补充重连诊断",
  "url": "https://github.com/ovws/issues/issues/42",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:22:11Z",
  "updated_at": "2026-09-01T10:36:47Z",
  "closed_at": "2026-09-01T10:36:47Z",
  "labels": [
    "bug",
    "component: deployment",
    "故障",
    "AI 工具",
    "GitHub",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 现象

Cindy/微信 Relay 链路出现 `Relay 连接关闭 (1006)`，属于非正常 WebSocket 关闭，影响微信 → Relay → 本地 Agent 的稳定通信。

## 排查

* Cloudflare/反向代理是否正确支持 WebSocket Upgrade。
* Relay 服务进程是否重启、崩溃或被平台休眠。
* Windows Agent 到 Relay 的网络、代理、TLS 与心跳状态。
* 客户端和服务端协议/认证参数是否一致。
* 长连接空闲超时、心跳间隔和重连退避。

## 改进

* UI 展示连接阶段和最近错误，而非只有 1006。
* 增加连接测试/健康检查。
* 自动重连采用指数退避并避免重复会话。
* 日志使用请求/连接 ID 方便串联排障，不输出密钥。

## 验收

能够稳定复现并定位 1006 根因；修复后长时间连接与断网恢复测试通过。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477587285,
  "url": "https://github.com/ovws/issues/issues/42#issuecomment-5477587285",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:22:13Z",
  "updated_at": "2026-08-31T11:22:13Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-128/修复-cindy-relay-连接关闭-1006-并补充重连诊断">WK-128</a></p>
```

---

## Issue #43

```json
{
  "id": 5299556780,
  "number": 43,
  "title": "统一近视镜千牛 SKU 导入模板、价格与库存校验",
  "url": "https://github.com/ovws/issues/issues/43",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:22:23Z",
  "updated_at": "2026-09-30T01:12:09Z",
  "closed_at": "2026-09-30T01:12:09Z",
  "labels": [
    "工作验证",
    "自动化",
    "电商运营",
    "商品/SKU",
    "文件上传"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮千牛 SKU 快捷导入表格制作与价格修正。

## 目标

把近视镜商品的多颜色、多折射率、左右眼度数 SKU 生成逻辑统一，避免价格、库存、商家编码和规格错位。

## 已涉及商品/文件

* `26827A99_千牛SKU导入_价格修正版.xlsx`
* `近视镜015_5色21规格_千牛快速上传.xlsx`
* 后续同逻辑的近视镜商品可复用。

## 规则

* 折射率至少覆盖 1.56 / 1.61 / 1.67 等实际商品规格。
* 左右眼度数按商品要求生成完整组合，常用区间按 25 度步进。
* 库存按当前约定统一为 10000（如商品另有要求则显式覆盖）。
* 价格必须严格按镜片类型映射，生成后做全表一致性检查。
* 不应把“配色/包装”误识别成折射率等其他规格维度。
* 商家编码如当前模板要求删除，则不得残留旧值。
* 上架时间、配送方式等字段以对应模板和当前商品规则为准。

## 验收

生成文件能被千牛正确识别；随机抽查和程序校验均不存在规格错列、价格错配、库存异常和冗余编码。

## 2026-09-09 近视镜商品表排序要求

* 近视镜表中商品/款式名称需要按名称末尾编号进行自然升序整理，例如 `半框01`、`半框02`、`xx框03`、`xx框04`；缺失编号直接跳过，不强行补号。
* 排序时必须整行/整组迁移，保证该款式下方及同行关联的价格、库存、镜片配置等所有字段随款式一起移动，禁止只排序名称列造成数据错位。
* 仅处理“近视镜”工作表/区域，不改动其他品类。
* 文件属于业务敏感资料，处理过程中不得外传或上传到非必要外部服务。

## 追加验收

排序后逐项核对编号顺序和行数据完整性，确保任一款式的镜片配置、价格、库存及其他关联字段未串行。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477589088,
  "url": "https://github.com/ovws/issues/issues/43#issuecomment-5477589088",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:22:24Z",
  "updated_at": "2026-08-31T11:22:24Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-129/统一近视镜千牛-sku-导入模板价格与库存校验">WK-129</a></p>
```

---

## Issue #44

```json
{
  "id": 5299558226,
  "number": 44,
  "title": "老花镜单层 SKU 展示模板与标题素材标准化",
  "url": "https://github.com/ovws/issues/issues/44",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-08-31T11:22:34Z",
  "updated_at": "2026-08-31T11:22:36Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "电商运营",
    "商品/SKU",
    "文件上传",
    "内容文案"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 老花镜商品上架模板与标题批量生成工作。

## 已完成范围

* 老花镜 SKU 使用单层展示逻辑：同一副眼镜双眼使用相同度数，不按左右眼拆分组合。
* 规格/配色严格按原商品定义解释，避免把包装、配色误当成折射率。
* 保留模板原有必要选项和库存规则；根据当前要求清理不需要的上架时间等字段。
* 补充/保留正确配送方式字段。
* 商品标题仅从给定词库/已有关键词组合，不擅自造类似“老光眼镜”等错误新词。
* 标题长度和批量数量按平台要求生成并人工抽查。

## 代表模板

* SKU 模板商品 ID 50011898 / 1787989102563（老花镜单层展示逻辑）。
* 0229 老花镜相关商品配置与标题批次。

## 验收结论

相关模板与标题批量素材已完成本轮整理；后续新老花镜商品沿用同一规则。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477590947,
  "url": "https://github.com/ovws/issues/issues/44#issuecomment-5477590947",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:22:36Z",
  "updated_at": "2026-08-31T11:22:36Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-130/老花镜单层-sku-展示模板与标题素材标准化">WK-130</a></p>
```

---

## Issue #45

```json
{
  "id": 5299559975,
  "number": 45,
  "title": "批量产出户外运动护目镜登山/骑行双场景文案",
  "url": "https://github.com/ovws/issues/issues/45",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-08-31T11:22:48Z",
  "updated_at": "2026-08-31T11:22:49Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "电商运营",
    "内容文案",
    "短视频"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮户外护目镜、运动墨镜商品文案批量生产。

## 已完成内容

* 户外护目镜：31 条标题 + 抖音口播风格描述，登山/骑行双场景。
* 白框运动护目镜：20 条并追加 5 条，保持登山/骑行双场景。
* 其他运动护目镜批次：按 23 条等数量继续输出。
* 标题强调强吸引力，但避免与正文脱节；描述以短视频口播语言展开。
* 单条长文案按任务要求不少于约 100 字时保持完整卖点和场景逻辑。
* 输出采用 JSON 等便于批量导入/二次处理的结构。

## 统一卖点方向

运动佩戴稳定、视野、防风、防晒/减眩、轻量舒适、登山与骑行适配等；不虚构产品未提供的参数或认证。

## 验收结论

本月已完成多批内容生产，后续按同一结构扩展新的运动眼镜款式。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477593121,
  "url": "https://github.com/ovws/issues/issues/45#issuecomment-5477593121",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:22:49Z",
  "updated_at": "2026-08-31T11:22:49Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-131/批量产出户外运动护目镜登山骑行双场景文案">WK-131</a></p>
```

---

## Issue #46

```json
{
  "id": 5299561243,
  "number": 46,
  "title": "批量产出猫眼墨镜与黑色大框眼镜商品文案",
  "url": "https://github.com/ovws/issues/issues/46",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-08-31T11:22:58Z",
  "updated_at": "2026-08-31T11:22:59Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "电商运营",
    "内容文案",
    "短视频"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮猫眼墨镜、黑色大框眼镜标题与口播文案生成。

## 已完成内容

* 猫眼墨镜多批次：20 条、15 条及追加批次。
* 黑色大框眼镜独立批次。
* 驾驶、户外、日常穿搭等场景化表达。
* 标题优先提高点击吸引力，正文保持抖音口播/小红书自然表达。
* 不随意创造用户词库中不存在的商品术语；涉及指定词库时严格从给定词中组合。

## 质量规则

* 不夸大未提供的功能参数。
* 避免标题同质化和重复句式。
* 产品风格、脸型修饰、穿搭氛围等主观卖点用自然体验表达。

## 验收结论

本月相关批次已完成，作为后续猫眼/大框眼镜内容模板沉淀。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477594757,
  "url": "https://github.com/ovws/issues/issues/46#issuecomment-5477594757",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:22:59Z",
  "updated_at": "2026-08-31T11:22:59Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-132/批量产出猫眼墨镜与黑色大框眼镜商品文案">WK-132</a></p>
```

---

## Issue #47

```json
{
  "id": 5299580658,
  "number": 47,
  "title": "评估 internal-ai-gemini-api Dependabot PR #5/#6/#7 并决定合并顺序",
  "url": "https://github.com/ovws/issues/issues/47",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:25:21Z",
  "updated_at": "2026-09-30T01:12:52Z",
  "closed_at": "2026-09-30T01:12:52Z",
  "labels": [
    "component: config",
    "工作验证",
    "Improvement",
    "GitHub",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

对 `ovws/internal-ai-gemini-api` 当前 3 个 Dependabot PR 做兼容性评估，给出合并/暂缓决策，并在合并前跑最小回归。

## 当前 PR（2026-08-31 核对）

* #5：`pypa/gh-action-pypi-publish` 1.14.0 → 1.14.2；GitHub Actions 发布链路更新，当前 open、mergeable。
* #6：放宽/更新 `curl-cffi` 依赖以允许最新版本；0.16.0 涉及 curl/curl-impersonate、HTTP/3、WebSocket 等较多底层变化，当前 open、mergeable，兼容风险高于纯 CI Action 更新。
* #7：`orjson` 从 `~=3.11.7` 调整为 `>=3.11.7,<3.13.0`；3.12.0 序列化实现有较大改写，当前 open、mergeable。

## 建议验证

1. #5 可优先：主要影响发布工作流，先验证 workflow YAML 和发布/构建 job。
2. #7 次之：跑 JSON 序列化/响应体/缓存等测试，尤其关注字节级输出差异。
3. #6 最后：重点验证 Gemini 请求、Cookie/会话、HTTP/2/3、代理、流式/WS 场景，避免 TLS 指纹或底层 curl 行为变化影响网页接口稳定性。
4. 每个 PR 单独合并并回归，不建议一次性三单叠加后再定位问题。

## 验收

每个 PR 有明确的“合并 / 暂缓”结论及测试证据；最终 main 分支服务启动、文本/图片核心请求和关键网络链路无回归。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477617728,
  "url": "https://github.com/ovws/issues/issues/47#issuecomment-5477617728",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:25:22Z",
  "updated_at": "2026-08-31T11:25:22Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-144/评估-internal-ai-gemini-api-dependabot-pr-567-并决定合并顺序">WK-144</a></p>
```

---

## Issue #48

```json
{
  "id": 5299583246,
  "number": 48,
  "title": "重构个人 Portfolio 作品集并部署 Vercel",
  "url": "https://github.com/ovws/issues/issues/48",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:25:39Z",
  "updated_at": "2026-09-01T10:38:02Z",
  "closed_at": "2026-09-01T10:38:02Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "GitHub",
    "网站/前端",
    "简历/作品集"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 作品集多轮改版与部署需求。

## 目标

将 `ovws/portfolio` 调整为更专业、偏工程师作品集的展示站，并完成 Vercel 生产部署与回归。

## 本月要求汇总

* 整体视觉更深色、克制、专业，减少过多圆角和“模板感”。
* 项目列表支持清晰的筛选/分类入口。
* 项目详情使用完整页面呈现，而不只是轻量弹窗卡片。
* 项目来源优先使用真实已有 GitHub 项目，不虚构项目经历。
* 展示重点覆盖云、AI、全栈/运维、自动化等实际作品。
* 桌面端与移动端均需验证导航、项目详情和外链。

## 状态

站点已进行多轮实现/部署讨论，当前设为 In Review：需要以生产地址和最新仓库版本做一次最终验收后再标 Done。

## 验收

Vercel 生产站可访问；项目数据与 GitHub 一致；关键页面无布局/控制台错误；简历/主页外链统一。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477620735,
  "url": "https://github.com/ovws/issues/issues/48#issuecomment-5477620735",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:25:40Z",
  "updated_at": "2026-08-31T11:25:40Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-145/重构个人-portfolio-作品集并部署-vercel">WK-145</a></p>
```

---

## Issue #49

```json
{
  "id": 5299585236,
  "number": 49,
  "title": "更新经典版技术简历并同步线上版本",
  "url": "https://github.com/ovws/issues/issues/49",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:25:53Z",
  "updated_at": "2026-09-01T10:38:06Z",
  "closed_at": "2026-09-01T10:38:06Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "GitHub",
    "网站/前端",
    "简历/作品集"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮简历改版、内容更新与部署需求。

## 目标

保持经典、稳定、面试友好的版式，更新最近工作经历和真实项目，并同步 GitHub/线上版本。

## 本月内容要求

* 不再使用过度 Bento / Apple 产品页式简历布局，回归招聘场景易读的经典结构。
* 删除不再需要的学校/教育条目。
* 工作经历重点体现容器平台、CI/CD、镜像管理平台等业务运维职责。
* 技术方向围绕 Kubernetes、Linux、Helm、Go、Node.js/TypeScript，并自然体现云与 AI 工程能力。
* 项目只使用实际存在或可验证的项目，优先从 GitHub 最新仓库补充。
* 避免把代理类项目作为简历核心项目；作品侧更偏云、AI、自动化和开发工作流。
* 减少留白并稳定在面试可阅读的页数/信息密度。

## 状态

本月已有经典版 V13 等产物，但线上仓库/部署和最终内容一致性需要再做一次验收，因此设为 In Review。

## 验收

仓库、导出的最终简历和线上版本内容一致；无虚构项目、无旧教育信息残留，链接均可访问。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477624773,
  "url": "https://github.com/ovws/issues/issues/49#issuecomment-5477624773",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:26:06Z",
  "updated_at": "2026-08-31T11:26:06Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-146/更新经典版技术简历并同步线上版本">WK-146</a></p>
```

---

## Issue #50

```json
{
  "id": 5299587290,
  "number": 50,
  "title": "移除插件付费/试用限制，制作纯免费基础功能测试版",
  "url": "https://github.com/ovws/issues/issues/50",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:26:08Z",
  "updated_at": "2026-09-01T11:06:32Z",
  "closed_at": "2026-09-01T11:06:32Z",
  "labels": [
    "component: config",
    "工作验证",
    "Improvement",
    "特性",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08-28 插件基础功能回归需求。

## 目标

在不破坏核心功能的前提下，暂时移除付费模块和试用限制，得到一个纯免费测试版本，用来验证客户最基本的使用链路是否稳定。

## 要求

* 删除/禁用付费相关 UI、接口、授权判断和跳转逻辑。
* 暂时取消试用次数/时间/功能限制。
* 不因移除收费逻辑而影响插件启动、核心操作、配置读写和数据处理。
* 保留清晰的代码边界，后续可重新接回付费模块，而不是大面积破坏性删除。
* 对原压缩包/版本做备份，不覆盖唯一可恢复源。

## 回归

* 全新环境首次安装。
* 已有配置升级安装。
* 核心功能完整跑通。
* 无付费弹窗、试用到期阻断或残留不可达入口。

## 验收

免费版核心功能可稳定使用，客户基础操作不再受付费/试用模块影响；任何收费相关能力均不应误触发。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477625830,
  "url": "https://github.com/ovws/issues/issues/50#issuecomment-5477625830",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:26:12Z",
  "updated_at": "2026-08-31T11:26:12Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-147/移除插件付费试用限制制作纯免费基础功能测试版">WK-147</a></p>
```

---

## Issue #51

```json
{
  "id": 5299594075,
  "number": 51,
  "title": "跟踪 DESKTOP-O41U6SU 反复离线/上线的设备稳定性",
  "url": "https://github.com/ovws/issues/issues/51",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:26:56Z",
  "updated_at": "2026-09-01T10:36:13Z",
  "closed_at": "2026-09-01T10:36:13Z",
  "labels": [
    "故障",
    "工作验证",
    "测试",
    "工作环境"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

Cindy Slack DM 的设备状态告警与 2026-08-31 监控任务。

## 现象

`DESKTOP-O41U6SU` 在近期出现多次“offline → back online”往复。离线时 Cindy 提示任务会排队，恢复连接后自动执行。这已经不是单次偶发告警，应按稳定性模式跟踪。

## 当前状态

最近一条检索到的状态为 back online，但此前存在多轮离线/恢复，因此任务保持 In Progress，而不是标 Done。

## 跟踪项

* 每次 offline / back-online 的时间、持续时长和频率。
* 是否与 Windows 睡眠、网络切换、代理、Cindy/Pi Agent 重启或 Relay 断开有关。
* 离线期间排队任务在恢复后是否全部执行且无重复。
* 如果继续出现，结合本地 Agent/Relay 日志定位连接中断原因。

## 验收

连续观察期内不再高频掉线；若再次发生，能够给出时间线、可能根因和可执行的修复措施。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477633979,
  "url": "https://github.com/ovws/issues/issues/51#issuecomment-5477633979",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:27:00Z",
  "updated_at": "2026-08-31T11:27:00Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-148/跟踪-desktop-o41u6su-反复离线上线的设备稳定性">WK-148</a></p>
```

---

## Issue #52

```json
{
  "id": 5299619985,
  "number": 52,
  "title": "StockView：轻量 TradingView 风格行情站与 Cloudflare 部署",
  "url": "https://github.com/ovws/issues/issues/52",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:30:13Z",
  "updated_at": "2026-09-01T10:36:21Z",
  "closed_at": "2026-09-01T10:36:21Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "特性",
    "网站/前端"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08-13 StockView 轻量股票行情网站需求。

## 目标

实现一个 TradingView 风格但明显精简的行情网站，并以 Cloudflare 为部署方向。首版定位为看盘工具，不做交易平台或社区。

## 首版功能范围

* 股票/标的搜索。
* 自选列表。
* 实时/准实时价格展示。
* K 线与成交量。
* 周期切换、缩放、十字光标。
* 技术指标：MA、EMA、MACD、RSI、BOLL。
* 图表优先采用 Lightweight Charts 等轻量方案。
* 数据源评估/接入 Finnhub、Twelve Data。
* 深色、专业、移动端可用的界面，减少过度圆角和消费级卡片感。

## 首版明确不做

* 实际交易下单。
* 社区/社交功能。
* 复杂画线与重型专业终端能力。

## 部署与验收

* 以 Cloudflare 部署为目标，明确静态前端、API/缓存与密钥边界。
* API Key 不暴露在浏览器端；需要代理时使用服务端/Worker。
* 至少验证搜索、自选、价格、K线、成交量、周期切换和 5 类指标。
* 桌面端与手机端完成基础回归。

## 关联说明

当前 GitHub 中未检索到名为 StockView 的 `ovws/*` 仓库，因此不猜测仓库地址；待实际仓库创建/确认后再关联。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477665302,
  "url": "https://github.com/ovws/issues/issues/52#issuecomment-5477665302",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:30:15Z",
  "updated_at": "2026-08-31T11:30:15Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-149/stockview轻量-tradingview-风格行情站与-cloudflare-部署">WK-149</a></p>
```

---

## Issue #53

```json
{
  "id": 5299622553,
  "number": 53,
  "title": "维护多客户端代理生产配置与 Snell 兼容策略",
  "url": "https://github.com/ovws/issues/issues/53",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:30:32Z",
  "updated_at": "2026-09-30T01:12:05Z",
  "closed_at": "2026-09-30T01:12:05Z",
  "labels": [
    "component: config",
    "工作验证",
    "Improvement",
    "GitHub",
    "网络代理"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 多轮 Surge / Stash / Loon / Quantumult X / Egern / Clash Meta(Mihomo) / Snell 配置调整与兼容讨论。

## 目标

维护一套可实际长期使用的代理生产配置矩阵，与 ovws/internal-ai-api-config#39“配置转换工具”区分：本任务关注现网配置本身的正确性、稳定性和客户端兼容，而不是开发转换器。

## 配置范围

* Surge-CN / Snell-CN 作为主要维护来源之一。
* 同步维护 Stash、Loon、Quantumult X、Egern、Clash Meta / Mihomo 等客户端版本。
* Snell v6 与仅支持 v5 的客户端之间明确兼容/降级策略，不假设协议版本可直接互通。
* 工作常用服务规则覆盖 X、Google、Slack、ChatGPT、Grok、Linear、Telegram、GitHub/GitLab 等。
* Douyin/抖音规则需要确保按当前要求正确走代理，而不是误落 DIRECT。
* 区域策略包含常用节点组，并维护 KR / UK / DE 等区域；Automatic 与 AllServer 的组关系保持清晰。
* 保留必要的 URL Rewrite、MITM、局域网控制面板/API 等既有能力时，确认不同客户端的等价实现与安全边界。

## DNS / 网络

* 对 DoH / DoT / DoQ 的实际办公网络适用性进行选择，优先稳定与长期运行。
* 已使用/评估的加密 DNS 包括 AliDNS 与腾讯 DNSPod 公共解析等；QUIC/DoQ 能力按客户端真实支持情况配置。
* 不把管理 API、控制面板或敏感配置无保护暴露公网。

## 版本与文件

本月已有 Stash-CN、Loon-CN、QuantumultX-CN、Egern-CN、Snell-cn-optimized 等配置产物/版本，后续更新需保持规则语义一致，并记录无法等价转换的差异。

## 验收

至少在主力客户端完成：规则命中、DNS、常用工作服务、抖音代理、Snell 节点、策略组切换与长时间稳定性验证；配置更新同步到 `ovws/Proxy`。

## 2026-09-02 DNS 配额与 [gladns.com](<http://gladns.com>) 排查

* Surge 中观察到 `*.gladns.com` 相关 DNS 请求量偏高，需要避免这些查询消耗付费 DNS 服务额度；目标是将适合的解析请求切换到公共免费 DNS，同时不影响正常域名解析。
* 本地排查中 `gladns.com` 的 NS 指向 Cloudflare nameserver，但 `_dns._tcp.gladns.com`、`dns.gladns.com` 等尝试未得到可用的自托管 DNS 服务记录，因此不能把不存在的 gladns DNS 主机直接写进配置。
* 后续 DNS 配置应明确区分：公共递归 DNS、DoH/DoT/DoQ 端点、权威 DNS/NS，不因域名 NS 使用 Cloudflare 就误认为该域名提供公共递归 DNS。
* 对高频或特殊域名规则，优先使用 Surge 可验证的域名级 DNS 策略/公共解析方案，并检查是否确实降低付费额度消耗。

## 追加验收

在实际网络环境中确认 [gladns.com](<http://gladns.com>) 相关解析正常、无循环/大量失败重试，并通过 DNS 请求统计验证付费解析量确实下降。

## 2026-09-17 ～ 2026-09-18 Surge 配置更新

* `AI Auto` 策略组只包含 `[Proxy]` 中的自建节点，不混入机场/公共节点；后续新增自建节点时同步维护该组。
* `WireGuard` 策略组图标更新为 `https://cdn.jsdelivr.net/gh/ovws/Proxy@master/icon/IBKR/red-logo-broken-outline-108.png`。
* `AI Auto` 策略组图标更新为 `https://cdn.jsdelivr.net/gh/ovws/Proxy@master/icon/IBKR/claude.png`。
* 节点命名：`Snell` → `Oracle-JP`，`Snell-JP` → `Oracle-Tokyo`；`SG-FREE` → `US-FREE`。
* TikTok 规则继续沿用此前 ByteDance 配置，不因本轮策略组优化而改写。
* 2026-09-18 Windows 以太网环境排查可作为代理/DNS 联调背景：Intel X550-T2，10Gbps 链路，DHCP 开启；后续如遇解析/网关异常需优先核对 Windows 网络详情的实际网关/DNS显示是否正常。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477668318,
  "url": "https://github.com/ovws/issues/issues/53#issuecomment-5477668318",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:30:33Z",
  "updated_at": "2026-08-31T11:30:33Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-150/维护多客户端代理生产配置与-snell-兼容策略">WK-150</a></p>
```

---

## Issue #54

```json
{
  "id": 5299629668,
  "number": 54,
  "title": "3D-Web：Bruno Simon 风格 3D 个人主页复刻与部署验收",
  "url": "https://github.com/ovws/issues/issues/54",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:31:22Z",
  "updated_at": "2026-09-01T10:38:10Z",
  "closed_at": "2026-09-01T10:38:10Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "特性",
    "GitHub",
    "网站/前端",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08-09 ~ 2026-08-10 的 3D 个人主页复刻工作。

## 目标

制作一个高度贴近 Bruno Simon 交互体验的 3D 个人网站，但将场景中的内容、文字、项目与社交链接替换为个人信息。

## 本月范围

* 以 `bruno-simon.com` 的 3D 驾驶/场景交互为主要视觉与交互参考。
* 替换原站内容为个人项目、介绍与社交入口，而不是简单做静态仿站。
* 删除不需要的 Circuit / Whisper 等内容模块。
* 页面内容进行中文化/个人化。
* 社交入口按本月要求映射到 Twitch、LinkedIn、GitHub、Discord、YouTube、X/Twitter、OnlyFans 等对应个人入口，并使用新标签页打开外链。
* 完成 WebGL / Three.js 首屏初始化、资源加载和浏览器兼容性处理。
* 与 [WK-143](https://linear.app/cvm/issue/WK-143/修复-3d-web-持续灰屏并完成浏览器回归验证) 的灰屏故障修复保持关联。

## 部署与验收

* 代码仓库以 `ovws/3D-Web` 为准。
* 完成生产部署后，从真实浏览器验证：首屏不长期灰屏、3D 场景可进入、核心交互可用、个人内容与外链正确。
* 旧部署/异常构建需要清理后再验证当前版本，避免以缓存或历史版本作为验收依据。

## 当前状态

核心开发与灰屏修复已有完成记录，但最终生产站与仓库当前版本的一致性仍需一次验收，因此设为 In Review。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477677209,
  "url": "https://github.com/ovws/issues/issues/54#issuecomment-5477677209",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:31:24Z",
  "updated_at": "2026-08-31T11:31:24Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-151/3d-webbruno-simon-风格-3d-个人主页复刻与部署验收">WK-151</a></p>
```

---

## Issue #55

```json
{
  "id": 5299632161,
  "number": 55,
  "title": "Rust/WASM 粒子个人主页与 20 万粒子性能实验",
  "url": "https://github.com/ovws/issues/issues/55",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:31:39Z",
  "updated_at": "2026-09-01T10:35:59Z",
  "closed_at": "2026-09-01T10:35:59Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "Improvement",
    "特性",
    "网站/前端",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08-11 Rust + WebAssembly 粒子主页实验。

## 目标

构建一个纯静态个人主页，同时作为 JavaScript 与 Rust/WASM 粒子模拟的浏览器性能对比实验。视觉目标不是普通粒子背景，而是能形成更有辨识度的大型主视觉，例如大树/建筑等结构。

## 技术方案

* Vite / TypeScript / Three.js。
* Rust + WebAssembly，使用 Web Worker 承载模拟计算。
* 支持 10K / 50K / 100K / 200K 粒子档位。
* 对比 JavaScript 与 Rust/WASM 的 FPS、frame time、simulation time 等指标，保持两种实现的输出策略尽量一致以保证公平。
* Rust 侧通过 WASM memory 暴露 position 数据并减少不必要拷贝。

## 交互

* 鼠标吸引。
* Shift 排斥。
* 单击涟漪。
* 双击爆炸。
* Cloud / Sphere / Torus / Helix 等形态切换。
* 页面结构包含 Home / About / Projects / Skills / Contact。
* WebGL 不可用时提供降级提示/方案。

## 部署

* 静态构建命令 `npm run build`，输出 `dist`。
* 可部署至 Vercel 或 Cloudflare Pages；若云构建环境缺少 Rust/wasm-pack，则使用预构建 `public/wasm/` 产物。
* 本月曾出现线上访问不可用/效果未达到“大树/大建筑”主视觉预期，因此保持 In Progress。

## 关联说明

当前 GitHub `ovws` 下未检索到明确对应的 particle/WASM 仓库，因此不猜测仓库地址；确认仓库后再补关联。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477680811,
  "url": "https://github.com/ovws/issues/issues/55#issuecomment-5477680811",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:31:41Z",
  "updated_at": "2026-08-31T11:31:41Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-152/rustwasm-粒子个人主页与-20-万粒子性能实验">WK-152</a></p>
```

---

## Issue #56

```json
{
  "id": 5299638003,
  "number": 56,
  "title": "批量生产眼镜商品模特佩戴图与主图变体",
  "url": "https://github.com/ovws/issues/issues/56",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-08-31T11:32:20Z",
  "updated_at": "2026-10-08T13:05:19Z",
  "closed_at": "2026-10-07T05:37:03Z",
  "labels": [
    "工作验证",
    "商品主图",
    "图像编辑",
    "AI 工具",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08 下旬大量眼镜商品主图、模特佩戴图、换脸、换装、动作变体与场景变体生成任务的统一生产单。

## 目标

持续产出可直接用于抖音/天猫等商品展示的高真实度模特图，同时把“同款眼镜绝不能被 AI 改形”和“人物必须自然真实”作为硬约束。

## 本月反复出现的生产要求

* 商品眼镜以实物参考为准，镜框、镜片、鼻托、镜腿、颜色、比例不得擅自变化。
* 眼镜佩戴位置自然，鼻托落在鼻梁，镜腿与耳朵/头发遮挡关系真实，不穿模。
* 人物为真实感强的东亚/亚洲面孔；不同批次需要差异时更换长相、衣服、背包与动作，不得只是同一张脸微调。
* 指定“同一个女生/同一场景”时必须保持身份、发型、背景和光线一致，只做允许的动作/服装变化。
* 夏季服装替换只改变衣服，不改变人物核心长相和商品。
* 人物正面展示时头部不能明显歪，眼镜也必须保持水平、居中。
* 真实感优先于过度精致：保留皮肤纹理、自然光影，避免塑料皮肤、错误手指和明显 AI 感。
* 上半身/肩膀以上等构图按商品主图用途执行；主图常用 1:1。
* 多张输出必须逐张独立，不拼接成九宫格/大图。

## 本月覆盖场景

居家、户外、骑行/登山、公园、车内、机场/高铁、海边/草地等商品展示场景，以及同一人物多动作、小幅变化、多脸型差异批次。

## 验收

每批生成完成后按 ovws/internal-ai-api-config#34 的人工规范检查，并逐步接入 [WK-113](https://linear.app/cvm/issue/WK-113/%E5%88%B6%E4%BD%9C%E4%B8%BB%E5%9B%BE%E6%A3%80%E6%9F%A5%E5%99%A8) 主图检查器；不合格项明确返工原因，而不是直接进入上架素材库。

## 2026-09-01 ～ 2026-09-05 本周新增生产要求

* 持续批量生成中年/中老年男女模特、商品主图和生活抓拍风佩戴图；人物需直视镜头时不得侧脸，年龄感、衣着、背景需要明显差异化。
* 多图任务继续坚持“每张独立输出、禁止拼接”。
* 眼镜替换继续以实物参考图为唯一结构依据；仅更换眼镜时不得改脸、姿势和场景，镜框弧度与结构尽量严格还原。
* 图片优化重点转向 iPhone 后置摄像头式真实感：降低 AI 塑料皮肤、干黄肤色、假发丝、僵硬眼神和不自然手部；允许同步优化衣服纹理以增强整体真实感。
* 商品主图人物尽量居中，扩图后保持头部和胸部以上完整，背景需能突出人物且与人物光线/色调协调。
* 新增“送眼镜”生活故事视觉：普通中国家庭、父母/中老年人物、克制真实的情绪，不使用夸张表情；眼镜和眼镜盒作为故事中的实物贯穿。
* 图片组/故事组要求人物身份与眼镜一致，场景变化必须保持连续性。

## 2026-09-07 ～ 2026-09-08 新增生产要求

* 淘宝主图方向进一步明确：保持参考图的核心商业摄影风格，但人物长相、服装和局部背景需要有明显差异，不能只是同一张脸轻微变化。
* “变化不要过度”与“差异化”同时成立：保留主图的构图、光线和商品展示逻辑，主要通过人物五官、发型、衣服款式、动作和少量环境细节拉开重复度。
* 人物批次中尤其强调相貌重复度低；男生/女生批量任务不得连续生成高度相似脸型。
* 户外眼镜场景可变化，但不能脱离户外范畴；服装应在运动、登山、骑行、城市户外等合理范围内做明显变化。
* 淘宝商品主图优先人物端正、平视镜头、主体清晰、商业感强；生活抓拍感任务则保留自然动作，但不能牺牲商品展示。
* 所有批量任务继续执行“每张独立发送、禁止拼接”；输出纯图时去除文字、Logo、水印等非商品主体元素。
* 单独编辑动作/服装/场景时，严格遵守用户指定的不变量，例如仅改衣服时不改脸、仅改动作时保持人物和场景一致。

## 2026-09-09 新增视觉生产规范

* 通用参考图生成进一步强调“元素类型保持一致，但具体元素必须重新设计”：例如雪山仍为雪山、户外仍为户外，但不能复刻原山体、人物、服装或具体画面；用于批量生成时要保持统一视觉语言，同时每张存在明确差异。
* 商业摄影参考任务需保留原图的构图逻辑、光影氛围、质感与产品展示逻辑，但重新设计人物、服装、场景细节，避免生成“同一个人物换造型”或与参考图相似度过高。
* 高冷/高级杂志感人物方向：重点控制眼神、人物主体状态、自然真实皮肤与柔和高级光影；需要换脸时优先保持姿态、眼神方向和商业摄影氛围。
* 户外雪山系列继续要求人物相貌差异显著、衣服款式明显变化；男模任务保持户外/运动/机能风，不脱离原有元素范畴。
* 商品编辑继续遵循严格不变量：仅替换眼镜时保持人物、动作、场景不变；指定镜片透明时不得生成深色/镜面镜片；指定眼镜盒时眼镜盒结构和眼镜本体均不得变化。
* 纯背景/素材清理任务中，按要求去除手、眼镜、Logo、文字等元素，不额外改变背景视觉语言。

## 2026-09-10 商业主图新增方向

* 夜间驾驶眼镜主图新增明确商业摄影方向：年轻亚洲男性坐在汽车驾驶位，近距离半身构图，人物与眼镜作为视觉中心，城市夜景和车身/车窗形成自然框架；画面采用真实电影感光影，但仍需保持电商主图的产品可读性。
* 黄色镜片飞行员眼镜等具体商品展示时，镜片颜色、框型和佩戴结构以商品参考为准，不因夜景光效而变形或改色。
* 商业主图允许在参考构图基础上自由优化，但需保持单张独立输出、禁止拼接；近期常用 3:4 竖版，并继续优先增强真实摄影感。
* 高端眼镜女性人像方向进一步明确：银色细金属椭圆/小框透明镜片，人物端正居中、肩膀水平、直视镜头，清冷克制、高智感/高级杂志感；避免甜美化、过度微笑和过度磨皮。
* 通用“升级原图”任务应保留原图的商品展示逻辑、核心卖点、主体位置和视觉层次，但重新优化人物状态、光影、背景层次和商业摄影质感；不得为了差异化而降低原图有效卖点。
* 参考图生成仍遵循：相似的是视觉语言与元素类别，不是具体人物/服装/山体/场景细节；批量图之间要有可见差异。

## 2026-09-11 模特佩戴图生产补充

* 女生眼镜佩戴图新增“同场景、同人物、不同动作”的五张组图需求；仍坚持每张独立输出、禁止拼接。
* 人物真实感继续作为最高优先级：目标接近真实手机/商业摄影，不要求过度精致网红脸，普通自然长相也可用于商品展示。
* 多视角生成时需要保持同一副商品眼镜的框型、比例、颜色、镜片和镜腿结构稳定，不因侧脸/转头产生结构漂移。
* 当用户要求更换人物脸型/长相方向时，只调整人物身份与五官气质，商品眼镜仍保持参考图一致；不同批次继续控制人物重复度。

## 2026-09-14 ～ 2026-09-18 商品图生产补充

* 手持商品图进入高精度编辑阶段：参考图中的手势、手指位置、握持关系、构图和眼镜遮挡关系在指定“不变”时必须锁定，仅优化手部质感、修长比例、美甲或袖子；尤其避免中指过短、手指畸形和握持穿模。
* 手臂进入画面的方向可作为硬约束：指定从左下角拐角进入时，不得改成从画面正下方进入，拐角弯折度需贴近参考。
* 眼镜替换继续以白底实物图为唯一结构依据；图一/图二互换时严格遵循用户指定的不变量，不能连带改变背景、手势、人物或商品结构。
* 背景替换任务新增“四图统一到指定参考背景”等批量要求；只换背景时保留人物、眼镜、手势与主体光影关系。
* 图片清理继续覆盖镜架文字/标签、Logo、水印、镜面白点等；不得误删商品结构。
* 自拍/户外人物批次进一步区分前置与后置 iPhone 原相机质感；人物、衣服、长相需要明显变化并降低批次重复度，头部完整、坐姿/头部尽量端正，禁止手部托脸。
* 雪山/户外女性方向可切换冲锋衣等合理穿搭；人脸替换任务只替换脸部身份，不改变场景、服装、眼镜和构图。
* 淘宝/天猫主图常用 1:1 与 3:4；近期 3:4 单图需求增加，仍坚持每张独立输出、禁止拼接。

## 2026-09-19 淘宝主图整套设计补充

* 淘宝首图可使用人物佩戴图，后续四张不再重复人物展示，转为纯商品/功能/细节/场景卖点图，形成完整五图销售链路。
* 后四张必须“各有各的卖点”，禁止五张反复使用相同构图、相同卖点或重复元素；参考竞品只学习信息密度、层级和商业感，不做雷同复刻。
* 近期主图输出优先 3:4 竖版，每张独立发送、禁止拼接；整体元素需要更克制，避免卖点和装饰元素过多导致画面拥挤。
* 本轮允许眼镜局部视觉适配和结构美化，不要求像素级保持原眼镜，但商品结构必须合理、美观、可信，不能出现明显 AI 变形或错误零件。
* 五图建议形成差异化职责：首图负责佩戴/第一视觉，后续分别承担核心功能、痛点对比、佩戴舒适/结构细节、使用场景或购买理由，避免内容重复。

## 2026-09-20 ～ 2026-09-21 主图与儿童户外系列补充

* 老花镜五图进一步明确为同一色系完整销售链路：仅第一张出现真人，后四张不得重复人物；每张承担不同卖点，并根据卖点重新设计构图，避免第 2/3/4 张都采用相似的眼镜摆放结构。
* 五图整体优先黑、白、灰、商务蓝等统一色系；减少无关手机、电脑等装饰元素，画面不过度“海报化”，通常仅保留一个主标题 + 一个副标题；3:4 竖版为当前重点规格。
* 儿童户外运动眼镜新增稳定生产方向：8–12 岁东亚儿童，高山草甸/雪山等真实户外环境；儿童五官必须保持真实比例、不成人化、不网红脸，皮肤保留真实纹理。
* 儿童人物图继续强调头部完整、人物端正、肩膀自然、正面或轻微侧面；批量图需明显更换人物长相、服装和环境细节，差异化增大但保持统一的高端户外品牌摄影语言。
* 雪山/儿童护目镜方向要求镜面、雪山与自然光更真实，人物不得明显歪头；正面与微侧面批次均需保证商品结构稳定。
* 背景替换/局部编辑继续执行“只改指定区域”：例如只替换雪景、只优化雪山真实度、只更换背景时不得连带修改人物和商品。

## 2026-09-22 护目镜主图新增方向

* 新护目镜链接进入深秋/初冬主图生产阶段，图片以 3:4 竖版独立输出为主，禁止拼接。
* 首图优先人物图，强调真实 iPhone 后置相机实拍感，同时保留足够视觉冲击力，避免 AI 插画感和过度棚拍海报感。
* 搜索/场景方向重点覆盖登山、户外、运动、防风、徒步，并按需求延展骑行、驾驶等场景；单张图只承担一个核心卖点。
* 同一批主图之间必须有明显构图、场景和卖点差异，不能只换背景或人物动作；需要加入更有创意的摄影表达，但真实性优先。
* 冬季氛围使用真实雪山、草甸、冷空气、自然光等环境，避免不真实雪景和无意义装饰元素。
* 人物图继续要求头部完整、姿态自然端正、商品佩戴关系合理；近距离自拍可保留轻微手机广角，但不得造成明显脸部/眼镜畸变。
* 参考图生成时允许重新设计人物、服装和环境以降低相似度，但商品结构和用户明确要求保留的关键元素不得随意改变。

## 2026-09-23 追加：商品图结构保真与冬季主图

* 基于多张白底实物参考生成佩戴/场景图时，方形镜框的几何轮廓必须保持，不能被模型圆润化、拉成长方形或改变框角比例。
* 参考图用于锁定镜框、镜片、鼻梁、镜腿等商品结构；人物、服装、场景可以重新设计，但不得以“更自然”为由牺牲商品外形准确性。
* 护目镜/滑雪镜主图继续强调初冬/冬日户外真实感；画面中的雪、衣服积雪和飘雪应按实际需求控制，避免为了氛围堆砌过量雪景元素。
* 老花镜阅读功能图需保持真实书页连续关系：镜片内文字清晰，镜片外自然失焦；字号、排版和位置对应，不做硬贴字或夸张放大镜效果。

## 2026-09-24 追加｜初冬户外防风镜 / 徒步主图

* 人物方向进一步收敛到 20–24 岁东亚女性，清纯、自然、温柔、生活化的“小白花”气质；黑色长发、中分、双麻花辫，轻微闭嘴微笑，避免明显网红脸与过度商业修图。
* 场景可使用深圳梅沙尖等干净户外徒步环境；初冬氛围、元素少、背景不过度虚化，保留真实环境信息。
* 构图优先胸部以上，人物主体明确，同时为天猫主图文案预留负空间；要求视觉冲击力与点击吸引力，但真实性优先。
* 穿搭方向使用整齐的藏蓝色/深色户外冲锋衣；骑行场景若影响整体美感，可切换为更自然的户外徒步场景。
* 眼镜可切换为骑行/户外一体式防风护目镜；商品结构、镜片反射、佩戴关系必须自然，不因换场景或换背景改变商品结构。
* 单图独立输出，禁止拼接；整体继续以 iPhone 后置相机真实实拍感为硬约束。

## 2026-09-23 ～ 2026-09-24 初冬户外护目镜主图补充

* 年轻女性户外主图进一步收敛为清纯、自然、生活感方向：20–24 岁东亚女性，小巧鹅蛋脸、自然淡妆、黑色长发/双麻花辫，轻微闭嘴表情，避免明显网红脸和过度商业棚拍。
* 穿搭可使用整洁藏蓝色冲锋衣等初冬户外服装；人物以胸部以上中近景为主，头部完整，构图需要兼顾天猫主图后续排版留白。
* 场景可采用深圳梅沙尖等干净山野徒步环境，减少无意义背景元素和过强景深；骑行场景若影响人物美观与商品展示，可优先切换为徒步/普通户外。
* 防风镜/骑行护目镜替换继续执行商品结构锁定：只换眼镜时不得连带改变人物、脸、服装和背景；镜框、镜片、镜腿关系自然，避免新增侧边异物。
* 整体视觉目标为“电商主图点击力 + 小红书式清新生活感 + iPhone 后置原相机真实感”，允许有视觉冲击力，但禁止明显 AI 味、过度磨皮和夸张商业大片感。
* 背景替换任务以指定参考背景的环境语言为准，只修改背景；人物和商品保持不变。

## 2026-09-27 ～ 2026-09-28 雪山/护目镜主图生产补充

* 雪山、雪地、冰湖等冬季户外人物主图继续以 3:4 竖版和胸部以上近景为主；人物优先正中或接近正中，头部完整，为淘宝/天猫后续标题与卖点排版保留干净空间。
* 人物真实感进一步锁定为 iPhone 原相机/手机实拍方向：减少棚拍、过度磨皮、网红脸和明显 AI 味；面部可更柔和圆润、自然耐看，发丝与皮肤保留真实细节。
* 雪山背景需要干净、元素少、景深不过度；既保留冬季户外层次，又避免复杂山体、游客和杂物抢夺商品视觉焦点。
* 服装允许根据主图效果微调厚薄和款式，但人物、眼镜与场景关系必须合理；参考服装/背景/长相的局部替换任务继续执行“只改指定对象”的锁定原则。
* 护目镜/墨镜以商品参考图为唯一结构来源，尤其锁定方框轮廓、镜片左右一致、鼻托/镜腿关系；不得把方框生成成圆润框或改变镜框比例。
* 多图生产继续要求每张独立输出、禁止拼接；同批五张需在姿态、构图或场景细节上有可见差异，但保持统一商品视觉语言。
* 人物姿态优先头部放正、肩部自然、视线合理；电商主图的视觉冲击力建立在真实、干净、商品可读性基础上，不依赖夸张特效。

## 2026-09-28 ～ 2026-09-29 商品图编辑补充

* 镜面反射编辑进入更严格的“局部替换”模式：只替换镜片内反射景色时，镜框、人物、脸部、姿态、服装、背景和镜片形状全部锁定；反射内容需与目标参考景一致，并符合当前环境的透视、亮度、色温和曲面反射逻辑。
* 新增“从镜片中单独提取反射景色并输出 3:4 素材”的生产需求，提取结果用于后续镜面替换/合成，不应混入镜框、人物或原图文字。
* 眼镜佩戴合成继续执行商品结构锁定：将参考眼镜戴到另一人物脸上时，镜面内容可按要求保持不变；鼻梁、镜腿、耳侧遮挡、左右镜片比例必须自然。
* 图片清理任务继续覆盖文字、水印、Logo，但不得误删镜框、镜腿、鼻托或真实反射细节。
* 参考图反推提示词进一步要求尽可能还原原图：除场景/构图外，需要完整描述人物五官、妆造、核心动作、穿搭、色调、镜头/真实摄影质感与背景层次，方便后续稳定复现。
* 多人物图优化允许人物外观变化幅度更大，但同一组仍需保证整体风格、构图与商品展示协调。

## 2026-09-29 ～ 2026-09-30 户外护目镜生产补充

* 雪山/高海拔户外护目镜人物图进一步强化“站位可执行性”：明确区分脸部朝向与躯干朝向，使用人物自身左右肩描述前后关系，避免模型把“身子微朝右、头朝左/回看镜头”等要求误解成大侧脸。
* 人物正面商品展示时，优先保证两侧脸颊宽度接近、鼻梁接近脸中线、视线平视镜头；身体可保持约 20° 左右轻微转向以增加层次，但头部不得歪斜。
* 户外服装继续向浅蓝/天蓝色机能冲锋衣方向扩展，机能感增强但元素保持克制，避免复杂配件抢占护目镜视觉中心。
* 防风镜/一体式银灰镜面护目镜继续作为视觉中心；跨图替换时严格锁定镜片、鼻梁、镜框和镜腿结构，尤其避免左右镜片反光不一致、侧边异物、镜腿穿模。
* 镜面反射允许做局部场景协调：只调整左右镜块中的环境反射，不改鼻梁连接区和商品主体；如需出现摄影者倒影，应保持尺度合理并符合当前拍摄环境。
* 人物发型/妆造可做明显差异化，例如双垂落麻花辫；只改发型时不得连带修改脸型、服装、商品和背景。
* 参考图提示词提炼继续执行“主人物 + 背景”原则：默认删除右侧产品拼图、白底静物、分栏、文字、Logo、价格和卖点条；保留氛围、构图、站位关系、产品结构和光线气质，但替换具体五官、发丝形状和可识别背景细节，避免过度相似。
* 当前批次继续以 3:4 竖版独立单图为主，真实手机后置拍摄感优先，禁止拼接。

## 2026-10-01 ～ 2026-10-02 本周补充

* 即时图片清理继续覆盖去除文字、水印、Logo、图标等非商品主体元素；处理时不得误改人物、商品结构或背景关系。
* 商品/人物局部编辑继续遵循“只改指定项”：例如只换衣服颜色时锁定人物五官、姿势、眼镜和背景；颜色微调按明确色值或两色之间的中间色执行。
* 本周的动漫/巫师风家庭照片属于个人娱乐图片，不并入本 Work 商品图生产单。

## 2026-10-04 ～ 10-05 补充｜参考图差异化批量生产

* 新增参考图批量扩图工作流：先读取人物动作、表情、构图、氛围与摄影风格，再生成同类但明显不同的新图。
* 动作/姿态允许保持较高相似度，但人物长相、发型、穿搭需要明显差异化，不能只替换背景造成“同图换景”感。
* 男女人物均优先东亚面孔；当前批次以 3:4 竖版电商人物图为主。
* 单批常见交付为 10 张；每张必须独立输出，禁止拼接。
* 真实感继续优先：降低 AI 塑料感、过度磨皮和棚拍假感；同风格批次仍需保证人物身份和服装变化足够大。
* 商品编辑继续遵循局部锁定：换眼镜、镜面光或背景时，仅修改指定维度，其他人物/商品结构保持稳定。

## 2026-10-06 补充｜纯文字复刻提示词与佩戴修正

* 参考图反推提示词新增“纯文字可独立生成”要求：提示词本身不得依赖“参考图/原图/保持一致”等图像输入措辞，需要完整写明人物、动作、神态、构图、环境、光线、色调与摄影质感，使生成模型仅凭文字即可复现视觉结构。
* 对复刻任务，动作、构图、神态和整体氛围保持高相似；但按具体需求允许微调头部朝向，例如仅转动约 2–3°，避免过度侧脸。
* 雪场/冬季人物图可明确排除滑雪板等不需要的道具，减少模型因附加物导致构图漂移。
* 眼镜编辑继续执行“佩戴到眼睛上”的局部锁定：只调整眼镜位置与真实佩戴关系，人物五官、姿态、服装和背景不随之变化。
* 图片清理新增去除画面中央异常红色光圈等生成瑕疵；修复时只处理异常元素，不连带改变商品或人物。
* 当外部生成平台因提示词过长或复杂而拒绝生成时，优先压缩冗余描述、保留硬约束和关键视觉信息，形成更短、更可执行的提示词版本。

## 2026-10-07 ～ 2026-10-08｜人物动作精修与图像提示词

* 人物参考图复刻需对肩部高低、头部微倾和身体朝向作细粒度控制；例如左肩仅略高于右肩，避免因夸张耸肩造成姿态不自然。修改动作时尽量锁定其余视觉元素。
* 冬季女性户外人像新增“朋友近距离拍摄”而非自拍的镜头逻辑；动作可以稍活泼、头部轻微侧倾，冲锋衣穿搭需与雪地/户外环境自然协调，不出现自拍手势或不合理服饰。
* 参考图解析提示词继续要求详细覆盖五官妆造、发型、核心动作、服装、构图、色彩、背景和摄影质感；交付纯文字完整版本，便于在外部 AI 生图工具直接使用。
* 图片清理/局部删除任务只移除指定的图像或文字元素，不牵连人物、眼镜和背景结构。若要求无文字纯图，禁止添加 Logo、水印、宣传文案。
* 以上均并入现有商品图生产流程，不因单次局部修图另建 issue。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477688704,
  "url": "https://github.com/ovws/issues/issues/56#issuecomment-5477688704",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:32:22Z",
  "updated_at": "2026-08-31T11:32:22Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-153/批量生产眼镜商品模特佩戴图与主图变体">WK-153</a></p>
```

---

## Issue #57

```json
{
  "id": 5299644883,
  "number": 57,
  "title": "跨平台以图搜同款 MCP：淘宝 / 抖音 / 京东 / 1688",
  "url": "https://github.com/ovws/issues/issues/57",
  "state": "closed",
  "state_reason": "not_planned",
  "author": "ovws",
  "created_at": "2026-08-31T11:33:09Z",
  "updated_at": "2026-09-01T10:37:15Z",
  "closed_at": "2026-09-01T10:37:15Z",
  "labels": [
    "工作验证",
    "自动化",
    "特性",
    "AI 工具",
    "电商运营",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-08-17 的跨平台以图搜同款工具需求。

## 目标

参考此前 `joybuy-mcp` 的同类能力，实现面向淘宝、抖音、京东、1688 的商品以图搜同款/相似款能力，并为后续竞品分析、货源查找和商品运营工作流提供可调用接口。

## 输入

* 商品图片或图片 URL。
* 可选关键词、类目、目标平台等辅助条件。

## 输出

* 区分“完全同款 / 高度相似 / 同类竞品”。
* 商品名、店铺名、平台、商品链接。
* 可获取时记录价格、销量/评论等公开信息。
* 提取主要卖点/标题关键词。
* 1688 结果额外关注货源/供应商信息。

## 平台范围

首版明确覆盖：

* 淘宝 / 天猫
* 抖音商城
* 京东
* 1688

后续可评估拼多多等平台，但不作为首版阻塞项。

## 实现要求

* 优先封装为可被 Agent/Codex 调用的 MCP/工具接口。
* 对登录、验证码和平台风控使用人工登录/浏览器兜底，不绕过平台安全机制。
* 统一结果 Schema，便于接入 ovws/internal-ai-api-config#36 竞品抓取与 ovws/internal-ai-api-config#35 图包克隆流程。
* 对完全同款与相似款给出可解释的匹配依据/置信度，而不是只返回混合结果。

## 参考

用户在 2026-08-17 提供过 `https://github.com/yoouuio/joybuy-mcp/issues/2` 作为能力参考；当前 GitHub 连接器查询该地址返回 404，因此仅作为历史参考链接保留，不把其当前可访问性视为已验证。

## 验收

至少用一张真实商品图完成淘宝、京东、1688 中 2 个以上平台的端到端检索和结构化输出；结果可继续被竞品分析工作流消费。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5477697737,
  "url": "https://github.com/ovws/issues/issues/57#issuecomment-5477697737",
  "author": "linear-code[bot]",
  "created_at": "2026-08-31T11:33:11Z",
  "updated_at": "2026-08-31T11:33:11Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-154/跨平台以图搜同款-mcp淘宝-抖音-京东-1688">WK-154</a></p>
```

---

## Issue #58

```json
{
  "id": 5310850975,
  "number": 58,
  "title": "AI做图或者创新流程整理与标准化",
  "url": "https://github.com/ovws/issues/issues/58",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:22Z",
  "updated_at": "2026-10-07T05:37:29Z",
  "closed_at": "2026-10-07T05:37:29Z",
  "labels": [
    "工作验证",
    "Improvement",
    "商品主图",
    "图像编辑",
    "AI 工具",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
整理 AI 做图与链接创新相关方法，形成可复用的电商图片生产流程。

目标：

* 将 AI 图片生成、优化、扩图、清晰化流程标准化。
* 明确从原图分析 → 提示词整理 → AI生成 → 筛选优化 → 电商主图应用的完整链路。
* 沉淀创新链接图片时的思考方式与执行规范。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492752219,
  "url": "https://github.com/ovws/issues/issues/58#issuecomment-5492752219",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:23Z",
  "updated_at": "2026-09-01T10:45:23Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-155/ai做图或者创新流程整理与标准化">WK-155</a></p>
```

---

## Issue #59

```json
{
  "id": 5310851472,
  "number": 59,
  "title": "非每日固定工作流程整理",
  "url": "https://github.com/ovws/issues/issues/59",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:25Z",
  "updated_at": "2026-10-07T05:37:03Z",
  "closed_at": "2026-10-07T05:37:03Z",
  "labels": [
    "工作验证",
    "Improvement",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
整理非每日执行但需要周期性处理的店铺运营流程。

包含：

* 链接维护
* 销量运营
* 活动报名

目标：形成标准 SOP，降低遗漏风险。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492752790,
  "url": "https://github.com/ovws/issues/issues/59#issuecomment-5492752790",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:26Z",
  "updated_at": "2026-09-01T10:45:26Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-156/非每日固定工作流程整理">WK-156</a></p>
```

---

## Issue #60

```json
{
  "id": 5310851999,
  "number": 60,
  "title": "链接制作思路与经验沉淀",
  "url": "https://github.com/ovws/issues/issues/60",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:29Z",
  "updated_at": "2026-10-07T05:37:29Z",
  "closed_at": "2026-10-07T05:37:29Z",
  "labels": [
    "工作验证",
    "Improvement",
    "商品主图",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
沉淀商品链接制作完整方法论。

流程：
找图 → 主图版选择 → 详情/SKU完善 → 美工交付 → 上架前检查。

目标：建立可复制的新链接制作标准。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492753469,
  "url": "https://github.com/ovws/issues/issues/60#issuecomment-5492753469",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:30Z",
  "updated_at": "2026-09-01T10:45:30Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-157/链接制作思路与经验沉淀">WK-157</a></p>
```

---

## Issue #61

```json
{
  "id": 5310852415,
  "number": 61,
  "title": "每日工作内容标准化",
  "url": "https://github.com/ovws/issues/issues/61",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:32Z",
  "updated_at": "2026-10-07T05:37:03Z",
  "closed_at": "2026-10-07T05:37:03Z",
  "labels": [
    "工作验证",
    "Improvement",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
整理每日店铺运营工作内容，形成日常执行清单。

覆盖：

* 排单
* 店铺维护
* 内容发布
* 评价管理
* 数据观察
* 找图与竞品分析
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492753905,
  "url": "https://github.com/ovws/issues/issues/61#issuecomment-5492753905",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:33Z",
  "updated_at": "2026-09-01T10:45:33Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-158/每日工作内容标准化">WK-158</a></p>
```

---

## Issue #62

```json
{
  "id": 5310853052,
  "number": 62,
  "title": "上链接流程标准化",
  "url": "https://github.com/ovws/issues/issues/62",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:35Z",
  "updated_at": "2026-10-07T05:37:03Z",
  "closed_at": "2026-10-07T05:37:03Z",
  "labels": [
    "工作验证",
    "Improvement",
    "电商运营",
    "商品/SKU"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
整理商品从准备、发布、完善到检查的完整上链接流程。

流程：
素材检查 → 千牛发布 → 基础信息填写 → SKU配置 → 上架后优化 → 活动报名与检查。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492754439,
  "url": "https://github.com/ovws/issues/issues/62#issuecomment-5492754439",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:36Z",
  "updated_at": "2026-09-01T10:45:36Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-159/上链接流程标准化">WK-159</a></p>
```

---

## Issue #63

```json
{
  "id": 5310853782,
  "number": 63,
  "title": "AI做图流程",
  "url": "https://github.com/ovws/issues/issues/63",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:39Z",
  "updated_at": "2026-09-30T01:12:42Z",
  "closed_at": "2026-09-30T01:12:42Z",
  "labels": [
    "工作验证",
    "商品主图",
    "图像编辑",
    "AI 工具",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# AI做图流程

## 目标

建立标准化 AI 图片生产流程，将优秀竞品图片转化为可用于电商链接的高质量素材。

## 核心逻辑

原图 → 图片分析 → 文字提示词 → AI生成 → 筛选优化 → 电商适配。

## 详细流程

### 1. 原图分析

当发现大盘热销链接或优秀图片素材时，将图片上传至 AI 工具进行分析。

需要提取：

* 人物特征
* 核心动作姿势
* 穿搭妆造
* 构图方式
* 场景背景
* 产品展示方式

分析完成后删除无关内容，例如：

* 原图文字
* 品牌 Logo
* 不需要复刻的特殊元素

### 2. 提示词整理

根据 AI 输出内容进行人工优化：

* 删除无法复现或者影响生成效果的信息。
* 保留人物、动作、场景、构图等核心信息。
* 根据电商需求补充人物年龄、气质、产品展示要求。

### 3. AI生成图片

使用图片生成模型进行多轮生成：

* 同一提示词多次生成，筛选最佳结果。
* 如果效果不符合要求，修改提示词重新生成。
* 也可以重新上传原图，让 AI 重新分析。

优化方向包括：

* 人物角度调整。
* 姿势微调。
* 场景优化。
* 产品展示效果优化。

### 4. 图片扩图与清晰化

如果生成图片放入800主图后存在人物占比过大、无法裁剪的问题：

使用即梦画布进行扩图：

* 新建项目。
* 上传图片。
* 使用扩图功能。
* 选择合适结果下载。

如果扩图后图片清晰度不足：

* 使用美图秀秀 AI 清晰功能优化。

### 5. 电商适配检查

最终图片需要满足：

* 放入800主图后构图合理。
* 产品为视觉中心。
* 人物与产品适配。
* 图片质量满足链接使用要求。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492755208,
  "url": "https://github.com/ovws/issues/issues/63#issuecomment-5492755208",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:41Z",
  "updated_at": "2026-09-01T10:45:41Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-160/ai做图流程">WK-160</a></p>
```

---

## Issue #64

```json
{
  "id": 5310854527,
  "number": 64,
  "title": "链接创新图片方法",
  "url": "https://github.com/ovws/issues/issues/64",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:44Z",
  "updated_at": "2026-10-07T05:37:10Z",
  "closed_at": "2026-10-07T05:37:10Z",
  "labels": [
    "Improvement",
    "商品主图",
    "图像编辑",
    "AI 工具",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 链接创新图片方法

## 目标

用于链接优化阶段，当发现已有图片存在提升空间时，通过 AI 创新方式制作新的视觉方案。

## 适用场景

* 链接制作过程中发现某个卖点展示方式不够突出。
* 原图片视觉效果普通，希望提升点击率和转化能力。
* 希望在保持产品核心信息的情况下产生新的图片方向。

## 执行流程

### 1. 明确创新方向

将原图上传 AI，并说明优化想法，例如：

* 产品展示方式优化。
* 卖点表达方式优化。
* 场景变化。
* 构图优化。

### 2. AI生成方案

根据需求生成多个不同方向图片：

* 不局限单次生成。
* 多方案比较后选择最佳效果。
* 保证产品展示逻辑正确。

### 3. 筛选标准

选择图片时重点判断：

* 是否比原图更有吸引力。
* 是否符合电商主图要求。
* 是否突出核心卖点。
* 是否保持产品真实效果。

## 注意事项

AI创新图片不得为了新颖而降低质量，最终效果必须不低于原图。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492756159,
  "url": "https://github.com/ovws/issues/issues/64#issuecomment-5492756159",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:46Z",
  "updated_at": "2026-09-01T10:45:46Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-161/链接创新图片方法">WK-161</a></p>
```

---

## Issue #65

```json
{
  "id": 5310855045,
  "number": 65,
  "title": "洗链接流程",
  "url": "https://github.com/ovws/issues/issues/65",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:48Z",
  "updated_at": "2026-09-30T01:12:40Z",
  "closed_at": "2026-09-30T01:12:40Z",
  "labels": [
    "工作验证",
    "电商运营",
    "商品/SKU"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 洗链接流程

## 目标

通过重新调整 SKU 结构，解决活动价格校验、历史成交价格限制等问题，使链接恢复正常运营能力。

## 核心逻辑

删除旧 SKU → 创建/调整新 SKU → 刷新平台价格状态。

## 适用场景

### 情况一：活动报名价格校验失败

平台识别当前填写的活动价高于校验周期内 SKU 最低普惠价，导致无法报名活动。

### 情况二：历史链接需要提升价格

旧链接已有 SKU 成交记录，希望调整商品价格。

## 操作流程

1. 连续打开两次需要处理的商品编辑页面。
2. 情况一处理：

* 在先打开的编辑页面删除无法通过校验的 SKU。
* 如果删除全部 SKU 导致商品数量归零，可填写临时数量（例如 10）。
* 提交先打开页面。
* 再切换到后打开页面提交，刷新状态。

3. 情况二处理：

* 在先打开页面删除需要改价的 SKU。
* 如数量归零，填写临时数量。
* 在后打开页面修改对应 SKU 价格。
* 按顺序先提交前一个页面，再提交后一个页面。

## 注意事项

如果链接已经报名活动：

* 第一步操作前需要先退出活动。
* 完成洗链接后重新提交活动。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492756845,
  "url": "https://github.com/ovws/issues/issues/65#issuecomment-5492756845",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:50Z",
  "updated_at": "2026-09-01T10:45:50Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-162/洗链接流程">WK-162</a></p>
```

---

## Issue #66

```json
{
  "id": 5310855915,
  "number": 66,
  "title": "刷销量流程",
  "url": "https://github.com/ovws/issues/issues/66",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:54Z",
  "updated_at": "2026-09-01T11:04:47Z",
  "closed_at": "2026-09-01T11:04:47Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 刷销量流程

## 目标

针对有潜力的新链接，通过合理销量积累降低新品无销量数据带来的竞争劣势。

## 使用位置

千牛工作台 → 私域 → 粉丝运营 → 粉丝内购会。

## 准备工具

* 刷单手机（绿壳设备，用于检查淘宝历史操作）。

## 执行流程

### 1. 创建粉丝内购会活动

设置：

* 活动名称：自定义。
* 活动时间：当天开始，第二天结束。
* 选择人群：粉丝人群。

商品优惠设置：

* 手动选择商品。
* 搜索链接 ID 或名称。
* 至少选择三个商品，不足时使用店铺滞销链接补足。
* 优惠方式选择减价。
* 减少金额 = 原价格 - 0.1 元。

创建活动后投放，生成二维码。

### 2. 手机端操作

使用刷单手机扫描二维码：

* 进入粉丝内购会。
* 选择目标链接。
* 数量设置 1000 单。
* 支付金额固定 100 元。
* 完成下单。

完成后电脑重新进入粉丝运营，结束活动。

### 3. 订单处理

电脑登录千牛客户端：

* 进入交易 → 已卖出宝贝。
* 找到对应订单。
* 添加备注：不打单。
* 所有刷销量订单均需备注。

随后：

* 点击协商发货。
* 日期设置为当年最后一天。
* 手机端确认协商发货。

### 4. 数据记录

完成后记录：

* 订单号。
* 链接 800 主图。
* 开始时间。
* 结束时间。

如需取消刷销量：

* 手机端退款对应订单。
* 修改记录表结束时间。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492757861,
  "url": "https://github.com/ovws/issues/issues/66#issuecomment-5492757861",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:56Z",
  "updated_at": "2026-09-01T10:45:56Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-163/刷销量流程">WK-163</a></p>
```

---

## Issue #67

```json
{
  "id": 5310856434,
  "number": 67,
  "title": "活动报名流程",
  "url": "https://github.com/ovws/issues/issues/67",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:45:58Z",
  "updated_at": "2026-09-01T11:04:45Z",
  "closed_at": "2026-09-01T11:04:45Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 活动报名流程

## 目标

规范大促及日常营销活动报名流程，避免商品遗漏或错误报名。

## 操作流程

### 大促活动报名

1. 进入大促活动页面。
2. 旧链接：

* 可以导入历史报名商品。
* 批量导入后进入选择商品页面。
* 除配件外，其余商品全部提交。
* 选择使用该价格提报。
* 按默认比例报名。

3. 新链接：

* 不使用历史导入。
* 在可报名商品中搜索新链接。
* 提交商品。
* 后续流程与旧链接一致。

### 配件链接处理

* 提交不生效立减的非活动商品。
* 导入历史商品。
* 确认所有配件链接均提交。
* 如果配件误参加活动，需要撤销报名。

## 注意事项

活动状态优先级：
参加活动生效 > 参加活动不生效。

例如：同一个商品同时被提交到生效活动和不生效活动，平台会按照生效活动处理。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492758504,
  "url": "https://github.com/ovws/issues/issues/67#issuecomment-5492758504",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:45:59Z",
  "updated_at": "2026-09-01T10:45:59Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-164/活动报名流程">WK-164</a></p>
```

---

## Issue #68

```json
{
  "id": 5310857004,
  "number": 68,
  "title": "找图与选品分析流程",
  "url": "https://github.com/ovws/issues/issues/68",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:02Z",
  "updated_at": "2026-09-30T01:12:43Z",
  "closed_at": "2026-09-30T01:12:43Z",
  "labels": [
    "工作验证",
    "商品主图",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 找图与选品分析流程

## 目标

通过大盘、竞店、社交平台寻找适合制作的新链接图片素材。

## 流程

大盘竞品分析 → 寻找图片素材 → 判断是否跟做 → PS测试800主图效果 → 确定方案。

## 大盘找图

重点关注：

* 大盘新起链接。
* 竞店新起链接。

判断：

* 主图、详情优秀：可以直接参考制作。
* 有独特人物、Logo 等元素：需要替换。
* 产品存在细微差异：需要重新渲染。

## 社交平台找图

平台：小红书、抖音等。

标准：

* 人物好看、有网感。
* 人物与产品适配。
* 姿势自然。
* 产品展示效果好。

找到图片后导入 PS 800 画板测试，通过调整大小、角度确认是否适合作为主图。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492759212,
  "url": "https://github.com/ovws/issues/issues/68#issuecomment-5492759212",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:04Z",
  "updated_at": "2026-09-01T10:46:04Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-165/找图与选品分析流程">WK-165</a></p>
```

---

## Issue #69

```json
{
  "id": 5310857689,
  "number": 69,
  "title": "主图版与详情设计流程",
  "url": "https://github.com/ovws/issues/issues/69",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:06Z",
  "updated_at": "2026-10-07T05:37:08Z",
  "closed_at": "2026-10-07T05:37:08Z",
  "labels": [
    "工作验证",
    "商品主图",
    "图像编辑",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 主图版与详情设计流程

## 目标

根据产品特点选择或创新视觉方案，提高链接整体展示效果。

## 主图版选择

### 套版

来源：

* 大盘优秀链接。
* 店铺历史优秀模板。

要求：

* 根据产品特点修改卖点文字。
* 不直接复制低价竞品版式。
* 保证图片与卖点匹配。

### 原创新版

包括：

* 从0到1：创造新的主图版。
* 从1到2：基于已有版式优化创新。

## 其他图片

### 详情页

参考优秀竞品：

* 学习卖点展示方式。
* 优化内容结构。
* 尽量制作通用模板。

### SKU图

按照类目固定结构制作，也可优化更好的展示方式。

## 输出

完成渲染表格后交付美工制作。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492759885,
  "url": "https://github.com/ovws/issues/issues/69#issuecomment-5492759885",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:08Z",
  "updated_at": "2026-09-01T10:46:08Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-166/主图版与详情设计流程">WK-166</a></p>
```

---

## Issue #70

```json
{
  "id": 5310858226,
  "number": 70,
  "title": "美工交付与质量检查",
  "url": "https://github.com/ovws/issues/issues/70",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:10Z",
  "updated_at": "2026-09-30T01:12:00Z",
  "closed_at": "2026-09-30T01:12:00Z",
  "labels": [
    "工作验证",
    "商品主图",
    "图像编辑",
    "电商运营",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 美工交付与质量检查

## 流程

图片方案确认 → 提交图片与渲染需求 → 美工制作 → 检查 → 修改反馈。

## 提交要求

交付美工时需要提供：

* 图片文件。
* 渲染文件。
* 链接整体效果说明。

## 检查重点

重点检查第一张主图：

* 产品展示自然。
* Logo、文字无错误。
* 图片逻辑合理。
* 镜片、镜框效果符合真实情况。

禁止出现：

* 镜片黑色但镜框异常亮。
* 整体明亮但产品过黑。
* 亮面产品没有亮面效果。

发现问题及时反馈修改。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492760554,
  "url": "https://github.com/ovws/issues/issues/70#issuecomment-5492760554",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:11Z",
  "updated_at": "2026-09-01T10:46:11Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-167/美工交付与质量检查">WK-167</a></p>
```

---

## Issue #71

```json
{
  "id": 5310858873,
  "number": 71,
  "title": "上链接前最终检查",
  "url": "https://github.com/ovws/issues/issues/71",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:14Z",
  "updated_at": "2026-09-01T11:07:47Z",
  "closed_at": "2026-09-01T11:07:47Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 上链接前最终检查

## 目标

确保图片、详情、SKU、价格、编码等全部正确后再发布商品。

## 检查内容

* 图片是否完整。
* 主图是否符合方案。
* 详情页是否存在错误。
* SKU 图片是否对应。
* 商品价格是否正确。
* 商家编码是否正确。

## 流程

美工交付图包 → 全量检查 → 修正问题 → 确认无误 → 进入上链接流程。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492761312,
  "url": "https://github.com/ovws/issues/issues/71#issuecomment-5492761312",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:16Z",
  "updated_at": "2026-09-01T10:46:16Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-168/上链接前最终检查">WK-168</a></p>
```

---

## Issue #72

```json
{
  "id": 5310859696,
  "number": 72,
  "title": "每日排单与刷单计划",
  "url": "https://github.com/ovws/issues/issues/72",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:19Z",
  "updated_at": "2026-09-01T11:07:19Z",
  "closed_at": "2026-09-01T11:07:19Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 每日排单与刷单计划

## 目标

建立每日订单规划流程，确保刷销量任务按照计划执行，并持续记录执行结果。

## 执行流程

确定刷单链接 → 确认商品 SKU → 确定执行数量 → 确定执行方式 → 输出排单表 → 跟进执行结果。

## 详细步骤

### 1. 确认执行链接

根据当前运营计划确定需要提升数据的商品链接：

* 新链接冷启动。
* 重点推广链接。
* 需要提升销量基础的链接。

### 2. 确认 SKU 信息

检查：

* 对应商品 SKU。
* 商品价格。
* 当前库存状态。
* 是否存在活动限制。

### 3. 制定执行计划

记录：

* 执行数量。
* 执行时间。
* 执行方式。
* 负责人。

### 4. 输出排单表

将每日计划整理成表格，方便后续跟进：

* 已完成任务。
* 未完成任务。
* 异常情况。

## 注意事项

所有执行数据需要及时记录，避免后续无法追踪链接变化。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492762171,
  "url": "https://github.com/ovws/issues/issues/72#issuecomment-5492762171",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:20Z",
  "updated_at": "2026-09-01T10:46:20Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-169/每日排单与刷单计划">WK-169</a></p>
```

---

## Issue #73

```json
{
  "id": 5310860163,
  "number": 73,
  "title": "店铺基础维护与评价管理",
  "url": "https://github.com/ovws/issues/issues/73",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:23Z",
  "updated_at": "2026-09-01T11:07:14Z",
  "closed_at": "2026-09-01T11:07:14Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 店铺基础维护与评价管理

## 目标

保持店铺基础状态稳定，及时处理评价、售后以及日常维护事项。

## 日常维护内容

### 1. 评价管理

处理：

* 买家评价回复。
* 异常评价反馈。
* 影响链接表现的问题评价。

### 2. 店铺检查

每日检查：

* 店铺基础状态。
* 商品状态。
* 是否存在异常提醒。
* 是否存在需要处理的售后问题。

### 3. 问题处理

发现异常后：

* 记录问题原因。
* 判断影响范围。
* 及时处理并跟踪结果。

## 输出

保证店铺处于正常运营状态，减少因基础问题影响商品表现。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492762795,
  "url": "https://github.com/ovws/issues/issues/73#issuecomment-5492762795",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:24Z",
  "updated_at": "2026-09-01T10:46:24Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-170/店铺基础维护与评价管理">WK-170</a></p>
```

---

## Issue #74

```json
{
  "id": 5310860666,
  "number": 74,
  "title": "光合平台视频运营",
  "url": "https://github.com/ovws/issues/issues/74",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:27Z",
  "updated_at": "2026-09-01T11:07:11Z",
  "closed_at": "2026-09-01T11:07:11Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 光合平台视频运营

## 目标

通过视频内容持续提升商品曝光，并建立视频生产和发布流程。

## 执行流程

视频分类 → 粗剪/精剪 → AI生成标题文案 → 发布视频 → 关联商品。

## 详细步骤

### 1. 视频分类

根据素材类型判断处理方式：

* 商品展示视频。
* 使用场景视频。
* 竞品参考视频。

### 2. 视频剪辑

根据视频质量选择：

* 粗剪：快速整理内容结构。
* 精剪：优化节奏、画面和展示效果。

### 3. 标题文案生成

使用 AI 辅助生成：

* 视频标题。
* 描述文案。
* 核心卖点表达。

### 4. 发布与关联

发布完成后：

* 绑定对应商品。
* 检查商品关联是否正确。
* 记录发布结果。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492763463,
  "url": "https://github.com/ovws/issues/issues/74#issuecomment-5492763463",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:28Z",
  "updated_at": "2026-09-01T10:46:28Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-171/光合平台视频运营">WK-171</a></p>
```

---

## Issue #75

```json
{
  "id": 5310861372,
  "number": 75,
  "title": "大盘观察与竞品分析",
  "url": "https://github.com/ovws/issues/issues/75",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:31Z",
  "updated_at": "2026-09-30T01:12:45Z",
  "closed_at": "2026-09-30T01:12:45Z",
  "labels": [
    "工作验证",
    "电商运营",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 大盘观察与竞品分析

## 目标

通过持续观察市场变化，发现潜在商品机会和链接优化方向。

## 执行流程

查看市场排行 → 分析竞品变化 → 发现新链接机会 → 输出跟进方向。

## 分析内容

### 1. 市场排行观察

关注：

* 热销商品变化。
* 新出现的增长链接。
* 商品趋势变化。

### 2. 竞品分析

分析竞品：

* 主图设计。
* 商品卖点。
* 详情页结构。
* 视频内容。
* 价格策略。

### 3. 输出结果

整理：

* 值得跟进链接。
* 可优化方向。
* 图片制作方向。
* 运营策略建议。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492764221,
  "url": "https://github.com/ovws/issues/issues/75#issuecomment-5492764221",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:33Z",
  "updated_at": "2026-09-01T10:46:33Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-172/大盘观察与竞品分析">WK-172</a></p>
```

---

## Issue #76

```json
{
  "id": 5310862122,
  "number": 76,
  "title": "上链接前准备阶段",
  "url": "https://github.com/ovws/issues/issues/76",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:35Z",
  "updated_at": "2026-09-01T11:06:03Z",
  "closed_at": "2026-09-01T11:06:03Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 上链接前准备阶段

## 目标

在商品正式发布前，完成所有素材准备工作，确保上传流程顺利。

## 执行流程

下载图包 → 检查素材完整性 → 规范命名 → 上传素材中心。

## 详细步骤

### 1. 下载图包

获取商品相关素材：

* 主图。
* 详情图。
* SKU图。
* 视频素材。

### 2. 检查素材

确认：

* 文件是否完整。
* 图片是否清晰。
* 图片顺序是否正确。
* 是否存在错误版本。

### 3. 规范命名

按照统一规则整理文件名称，方便后续查找和维护。

### 4. 上传素材中心

完成素材归档，为商品发布流程提供素材支持。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492764947,
  "url": "https://github.com/ovws/issues/issues/76#issuecomment-5492764947",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:37Z",
  "updated_at": "2026-09-01T10:46:37Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-173/上链接前准备阶段">WK-173</a></p>
```

---

## Issue #77

```json
{
  "id": 5310862706,
  "number": 77,
  "title": "商品发布与信息配置",
  "url": "https://github.com/ovws/issues/issues/77",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:40Z",
  "updated_at": "2026-09-01T11:06:12Z",
  "closed_at": "2026-09-01T11:06:12Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 商品发布与信息配置

## 目标

完成商品从素材上传到基础信息配置的完整发布流程。

## 执行流程

选择类目 → 上传图片视频 → 填写标题属性 → 配置 SKU → 设置价格库存 → 入仓。

## 详细步骤

### 1. 选择商品类目

根据产品类型选择正确类目，避免后续流量和审核问题。

### 2. 上传素材

上传：

* 商品主图。
* 详情图片。
* 商品视频。

### 3. 填写基础信息

配置：

* 商品标题。
* 属性信息。
* 商品描述。

### 4. 配置 SKU

检查：

* SKU 名称。
* SKU 图片。
* SKU 对应关系。

### 5. 设置价格库存

完成：

* 商品价格设置。
* 库存数量填写。
* 编码信息配置。

### 6. 入仓

确认所有信息无误后提交商品。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492765744,
  "url": "https://github.com/ovws/issues/issues/77#issuecomment-5492765744",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:41Z",
  "updated_at": "2026-09-01T10:46:41Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-174/商品发布与信息配置">WK-174</a></p>
```

---

## Issue #78

```json
{
  "id": 5310863357,
  "number": 78,
  "title": "上架后优化与活动报名",
  "url": "https://github.com/ovws/issues/issues/78",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-01T10:46:44Z",
  "updated_at": "2026-09-01T11:07:09Z",
  "closed_at": "2026-09-01T11:07:09Z",
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# 上架后优化与活动报名

## 目标

商品发布完成后，通过持续优化和活动运营提升链接表现。

## 执行流程

上传商品素材 → 完善卖点 → 报名活动 → 检查链接 → 新品推广。

## 详细步骤

### 1. 上传并完善素材

检查：

* 主图是否符合最终方案。
* 详情页是否完整。
* 卖点表达是否清晰。

### 2. 优化商品卖点

根据产品特点完善：

* 核心优势。
* 使用场景。
* 用户痛点解决方案。

### 3. 活动报名

选择适合商品的营销活动：

* 确认报名条件。
* 设置活动价格。
* 提交商品。
* 检查报名状态。

### 4. 链接检查

发布后持续观察：

* 商品状态。
* 图片展示效果。
* 活动状态。
* 数据变化。

### 5. 新品推广

根据链接表现继续优化运营策略，提升商品曝光和转化。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5492766403,
  "url": "https://github.com/ovws/issues/issues/78#issuecomment-5492766403",
  "author": "linear-code[bot]",
  "created_at": "2026-09-01T10:46:45Z",
  "updated_at": "2026-09-01T10:46:45Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-175/上架后优化与活动报名">WK-175</a></p>
```

---

## Issue #79

```json
{
  "id": 5322426742,
  "number": 79,
  "title": "整理近视-A-069评论图子文件夹",
  "url": "https://github.com/ovws/issues/issues/79",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-02T09:55:07Z",
  "updated_at": "2026-09-02T10:12:10Z",
  "closed_at": null,
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
已完成（2026-09-02）

* 全部 25 个子文件夹按图片与视频总数从多到少排序。
* 统一命名为 `近视-A-069-001` 至 `近视-A-069-025`。
* 文件总数核对：处理前后均为 165，未改动文件内容。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5507750039,
  "url": "https://github.com/ovws/issues/issues/79#issuecomment-5507750039",
  "author": "linear-code[bot]",
  "created_at": "2026-09-02T09:55:08Z",
  "updated_at": "2026-09-02T09:55:08Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-176/整理近视-a-069评论图子文件夹">WK-176</a></p>
```

---

## Issue #80

```json
{
  "id": 5322427448,
  "number": 80,
  "title": "评论图目录批量规范化",
  "url": "https://github.com/ovws/issues/issues/80",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-02T09:55:10Z",
  "updated_at": "2026-09-02T10:12:10Z",
  "closed_at": null,
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
已完成（2026-09-02）

对近视镜与老花镜评论图目录进行批量标准命名，并按图片+视频数量重排子文件夹。详见两个已完成子任务。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5507750965,
  "url": "https://github.com/ovws/issues/issues/80#issuecomment-5507750965",
  "author": "linear-code[bot]",
  "created_at": "2026-09-02T09:55:12Z",
  "updated_at": "2026-09-02T09:55:12Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-177/评论图目录批量规范化">WK-177</a></p>
```

---

## Issue #81

```json
{
  "id": 5322429772,
  "number": 81,
  "title": "重排并命名评论图素材子文件夹",
  "url": "https://github.com/ovws/issues/issues/81",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-02T09:55:25Z",
  "updated_at": "2026-09-02T10:12:11Z",
  "closed_at": null,
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
已完成（2026-09-02）

* 在 40 个产品目录中，按图片与视频总数降序重排子文件夹，并以 `品类-A-编号-子编号` 连续命名。
* 首批完成 39 个目录、1,366 个未用子文件夹；名称含“已用”的 4 个子文件夹保持不变。
* `近视-A-009` 随后单独补处理：全部 52 个子文件夹已命名为 `近视-A-009-001` 至 `近视-A-009-052`，包含原“21文字已用”文件夹。
* 文件数校验：`近视-A-009` 共 394 个文件，处理前后无变化。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5507753655,
  "url": "https://github.com/ovws/issues/issues/81#issuecomment-5507753655",
  "author": "linear-code[bot]",
  "created_at": "2026-09-02T09:55:26Z",
  "updated_at": "2026-09-02T09:55:26Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-178/重排并命名评论图素材子文件夹">WK-178</a></p>
```

---

## Issue #82

```json
{
  "id": 5322430317,
  "number": 82,
  "title": "标准化命名 41 个评论图产品目录",
  "url": "https://github.com/ovws/issues/issues/82",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-02T09:55:28Z",
  "updated_at": "2026-09-02T10:12:11Z",
  "closed_at": null,
  "labels": [],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
已完成（2026-09-02）

* 40 个目录完成重命名并逐个核对文件数一致。
* 近视镜目录命名为 `近视-A-002` 至 `近视-A-036`；老花镜目录命名为 `老花-A-001` 至 `老花-A-005`。
* 因 `近视-A-001` 已被未列出的目录占用，`01款近视镜男` 按确认保持原名。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5507754368,
  "url": "https://github.com/ovws/issues/issues/82#issuecomment-5507754368",
  "author": "linear-code[bot]",
  "created_at": "2026-09-02T09:55:30Z",
  "updated_at": "2026-09-02T09:55:30Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-179/标准化命名-41-个评论图产品目录">WK-179</a></p>
```

---

## Issue #83

```json
{
  "id": 5354784579,
  "number": 83,
  "title": "搜索结果页重构：Kagi 风格 UI、字体与无刷新筛选",
  "url": "https://github.com/ovws/issues/issues/83",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-05T01:44:40Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "故障",
    "Improvement",
    "GitHub",
    "网站/前端",
    "测试"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-02 搜索结果页连续改版与交互修复。

## 目标

重构现有搜索结果页的视觉和交互，整体采用 Kagi 式克制、清晰、高信息密度的搜索产品语言，同时保留现有结果内容宽度，不机械照搬局部组件导致页面失衡。

## 本周要求

* 字体改为 PingFangSC-Light / 苹方轻字重方向，避免页面显得过粗。
* 页面间距、行距、按钮、筛选栏、搜索框等整体参考成熟搜索产品；结果区域原有较宽的内容宽度保持不变。
* 顶部搜索区域需要与全页协调；可以高度参考 Kagi，但重点是统一视觉体系而不是只复制单个块。
* Google 产品类结果链接/卡片显示异常需要修复，保证普通结果和产品结果的结构一致、可读。
* 点击搜索框下方筛选项时，不应整页刷新；仅更新结果区域和必要状态，保持搜索框、顶部 UI 与页面上下文稳定。
* 曾出现“改成局部刷新后筛选点击完全无响应”的回归，需要恢复事件绑定并做完整筛选回归。

## 验收

* 桌面端搜索、切换筛选、返回结果全过程无整页闪烁。
* 所有筛选项均可点击并正确更新结果。
* 顶部与结果区视觉统一，字体不再过粗。
* Google 产品结果等特殊结果类型不破版。
* 浏览器控制台无因局部更新造成的明显 JS 错误。

## 关联仓库

* 实际项目仓库：`ovws/luxirty-search`。
* 后续 UI、筛选交互、字体与特殊结果卡片修复均应以该仓库当前 `main` 为准，避免只在临时产物上改动。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5548508421,
  "url": "https://github.com/ovws/issues/issues/83#issuecomment-5548508421",
  "author": "linear-code[bot]",
  "created_at": "2026-09-05T01:44:41Z",
  "updated_at": "2026-09-05T01:44:41Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-180/搜索结果页重构kagi-风格-ui字体与无刷新筛选">WK-180</a></p>
```

---

## Issue #84

```json
{
  "id": 5354785174,
  "number": 84,
  "title": "制作 PingFangUI HK 430 / 450 / 470 自定义字重",
  "url": "https://github.com/ovws/issues/issues/84",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-05T01:44:46Z",
  "updated_at": "2026-09-05T01:44:48Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "Improvement",
    "网站/前端"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-02 字体处理任务。

## 目标

基于用户提供的 `PingFangUI.tahoe.26.4.1.wght.wdth.ttc` 可变字体资源，制作介于系统现有 400 与 500 之间的 HK 字重版本，用于网页/UI 精细字重控制。

## 输出目标

* PingFangUI-HK-430
* PingFangUI-HK-450
* PingFangUI-HK-470

## 要求

* 不重复制作已有的 400 / 500。
* 确认源字体中 HK 相关字体实例/字形覆盖情况。
* 输出版本需可被常用网页/设计工具识别，并保持中文与拉丁字符显示正常。

## 状态

本周已完成该字体处理批次，作为后续搜索 UI 字重调优的字体资产记录。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5548509119,
  "url": "https://github.com/ovws/issues/issues/84#issuecomment-5548509119",
  "author": "linear-code[bot]",
  "created_at": "2026-09-05T01:44:48Z",
  "updated_at": "2026-09-05T01:44:48Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-181/制作-pingfangui-hk-430-450-470-自定义字重">WK-181</a></p>
```

---

## Issue #85

```json
{
  "id": 5354785931,
  "number": 85,
  "title": "眼镜短视频对话脚本与 10 秒分段生成规范",
  "url": "https://github.com/ovws/issues/issues/85",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-05T01:44:55Z",
  "updated_at": "2026-10-08T01:33:12Z",
  "closed_at": "2026-10-08T01:33:12Z",
  "labels": [
    "Improvement",
    "AI 工具",
    "电商运营",
    "内容文案",
    "短视频",
    "视频编辑"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-03 ～ 2026-09-04 多轮老花镜/眼镜真人对话视频生成需求。

## 目标

沉淀适用于眼镜电商真人种草视频的 10 秒分段脚本与视频提示词规范，使人物、眼镜、对白和镜头关系在短时长内稳定可生成。

## 本周规则

* 原 15～20 秒脚本优先拆成两段，每段约 10 秒，分别生成首帧/视频。
* 真人生活化、手机后置摄像头质感、轻微手持感，避免棚拍和明显 AI 感。
* 对话严格一人一句，不能抢话、重叠说话。
* 眼镜全程佩戴在脸上时，不增加摘眼镜、手持眼镜等未要求动作。
* 中老年产品优先使用年龄明确的中老年中国女性/男性，不把人物生成得过年轻。
* 第二段需要品牌露出时明确强调“帝格勒”，但对白仍保持自然，不做生硬口播堆砌。
* 首帧必须与后续视频人物、场景、眼镜一致；眼镜以上传实物款为结构依据。
* 视频提示词除了对白，还必须包含人物动作、镜头、环境、表情和时序，不能只交付台词。

## 验收

至少形成可复用的“第一段 10 秒 + 第二段 10 秒”模板，并用于老花镜/近视镜等真实对话种草场景。

## 2026-09-04 ～ 2026-09-08 追加规则

* Google Flow / 视频生成场景中，眼镜实物结构约束优先于风格化：除镜片外，镜框、镜腿、连接件等全部为纯黑色，不允许额外出现白色线条、白色小部件、金属亮条或装饰件。
* 为降低模型幻觉，提示词不再反复描述“不要白线”等具体错误形态，改为正向锁定“整副眼镜除镜片外只有黑色、没有第二种颜色、没有附加零件”。
* 眼镜全程佩戴时不得自动生成摘镜动作；需要展示商品时也不得改变眼镜结构、颜色、镜腿粗细和连接方式。
* 将上传的眼镜参考图视为唯一商品结构来源；人物、场景可以变化，但眼镜本体必须稳定。
* 真人效果继续强调真实皮肤、自然动作和生活化镜头，避免人物因视频模型重绘而出现明显 AI 感。
* 对已有视频做提示词反推/镜头拆解时，推广镜头与非推广镜头要分开处理，优先保留可复用的非推广镜头生成逻辑。

## 2026-09-09 三人对话与短时长新增规则

* 老花镜种草对话新增三人场景：必须在提示词中明确角色 A / B / C 的身份、位置、每句台词归属，避免模型把台词分配给错误人物。
* 戴眼镜的角色在三人对话中作为最后发言者时，需要明确写出“佩戴产品眼镜的人最后说话”，并保持全程佩戴，不临时换人或摘镜。
* 超短视频可拆成两段、每段约 8 秒；即使时长紧张，用户提供的全部对白也必须完整念出，不能自行删句、改写或省略。
* 眼镜盒展示类视频可控制在约 4 秒：人物拿着指定眼镜盒并打开，眼镜盒和眼镜均严格使用参考图结构，禁止自动换款、改色或增加装饰。
* Vlog / 生活记录类视频避免商业广告式表演和过度强调“正在录视频”，镜头保持自然、克制、真实。

## 2026-09-10 功能展示短视频补充

* 偏光/清晰度功能演示新增“穿针引线”超短镜头：视频约 6 秒，只表现手部完成穿针引线这一动作，不需要人物对白，也不需要在该动作镜头中出现眼镜。
* 镜片清晰度对比镜头需要明确空间关系：透过眼镜镜框/镜片覆盖区域观察时内容清晰，镜框外的同一背景保持不清晰；过渡应自然，不能做成生硬的左右分屏或后期贴图。
* 这类功能演示提示词优先短、明确、单动作，通常两句即可，避免加入无关商品动作导致模型分散注意力。

## 2026-09-14 ～ 2026-09-18 老花镜视频生产补充

* 老花镜真人对话继续覆盖两人/三人版本，并开始按 Google Flow、豆包等不同模型压缩提示词；角色位置和台词归属必须明确，避免串词。
* 两人男性版本：A 夸 B 老花镜质感 → B 说明帝格勒新款、高清护目、价格实在 → A 询价 → B 强调轻、舒服、看字清晰 → A 问购买渠道 → B 引导左下角链接与活动优惠。
* 单人约 15 秒版本：围绕“不会挑老花镜 → TIGLR 时尚老花镜 → 显年轻 → 国庆促销 → 实际到手价”形成完整短口播；提示词需要控制节奏，避免模型因台词过长漏句。
* 父亲/女儿无对白故事扩展为约 20 秒或两段约 10 秒：父亲看不清 → 女儿送老花镜 → 戴上后保持佩戴并继续生活动作；明确禁止眼镜盒、禁止第三人、禁止倒车等指定元素，人物与摩托出画方向按分镜锁定。
* 无对白生活故事不局限于骑摩托，可扩展到看孩子作业等场景；人物刻画和场景差异要明显，同时保持真实手机拍摄感。
* 图片转视频继续要求人物仅做轻微自然动作，不微笑、不说话时不得擅自增加对白或夸张表演。
* 穿针引线类短镜头人物可设为 55–65 岁中年/老年女性，保持单动作、真实手部与自然光。

## 2026-09-21 六宫格眼镜视频动态补充

* 基于上传的六宫格商品眼镜生成视频时，商品眼镜仍作为核心参考，结构和视觉识别保持稳定。
* 视频动态幅度需要处于“静态感过强”和“动作变化过大”之间：不能只有几乎不可见的微动，也不能大幅改变镜头、商品姿态或场景导致商品失真。
* 优先采用中等幅度的镜头推进/轻微视角变化、自然光影移动和适度商品运动，使视频明显有变化但仍保持电商展示稳定性。

## 2026-09-22 视频生成补充

* 六宫格/商品参考图转视频继续以商品结构稳定为第一优先级，正面展示版本尽量不露出侧面，减少模型自行补全错误结构的机会。
* Google Flow 版本采用真实手机拍摄质感、自然轻微动作和适度镜头变化；动态幅度控制在中等偏小，避免画面几乎静止，也避免大幅转身、换场或商品结构漂移。
* 中年男性等人物版本可扩展新的生活化场景，但人物动作、镜头运动和环境变化必须服务于商品展示，禁止无意义戏剧化动作。

## 2026-09-23 追加：滑雪与连续单镜头视频

* 滑雪/户外视频中的绑带按商品要求保持纯黑、无品牌标识，不额外生成其他颜色或装饰。
* 动作可以更有力量感和速度感，但整条视频保持一段连续镜头，不做剪辑、跳切或蒙太奇。
* 商品结构在人物大动作、转身和镜头运动中仍需稳定，避免眼镜/护目镜颜色、绑带、镜框发生漂移。
* 视频提示词继续优先简洁可执行：明确人物核心动作、镜头连续性、商品锁定和真实拍摄质感，不堆叠无关描述。

## 2026-09-27 ～ 2026-09-28 Google Flow / 抖音 15 秒补充

* 当前优先继续使用 Google Flow；当其他模型额度受限时，不改变既有对白和商品约束，只针对 Flow 的稳定性重写提示词结构。
* 两人老花镜对话新增“阿姨/年轻女性”生活化场景版本；用户提供的对白视为不可改写内容，提示词精简或换场景时必须逐句保留原台词与人物归属。
* 对较长对白，Flow 第二段容易出现角色错乱、漏句和动作失控；因此分段提示词必须让每段独立自洽，重新声明角色身份、位置、眼镜佩戴者、当前段台词顺序和商品锁定，不能依赖上一段隐含上下文。
* 生成抖音约 15 秒版本时，应优先压缩动作、停顿和环境描述，而不是擅自删改用户对白；若完整台词客观超过可稳定口播时长，提示词仍以台词完整性和角色正确性为优先。
* 视频必须参考指定商品眼镜：眼镜结构、颜色、框型、镜片与镜腿以参考图为准；纯黑框版本锁定为纯黑结构，不新增白点、白色侧边件或其他装饰。
* 画面继续采用真实手机后置摄像头、自然光、轻微手持的生活感；禁止字幕，禁止人物擅自摘眼镜。

## 2026-09-30 视频提示词提取与场景迁移补充

* 新增“从现有成片反推/提取生视频提示词”的复用流程：先识别人物、动作、镜头运动、对白/节奏、商品结构和拍摄质感，再整理成可直接用于视频模型的生成提示词。
* 对原视频做场景迁移时，只替换用户指定维度；例如将原背景改为公园生活场景时，优先保持人物关系、核心动作、商品眼镜、镜头节奏与对白逻辑不变。
* 公园版本继续采用真实生活化手机拍摄，不做棚拍广告式布景；背景元素控制简洁，避免新增元素干扰人物和眼镜展示。
* 提示词交付优先短而可执行，保留影响生成稳定性的角色一致性、商品锁定、镜头和动作约束，删除重复修饰。

## 2026-10-07｜近视篮球眼镜短视频素材

新增篮球运动眼镜内容方向：

* 开场卖点：面向爱打篮球但近视的人群，突出近视篮球眼镜的运动适配性。
* 痛点对照组：普通男性眼镜在篮球冲撞/快速移动时容易飞出，出汗后容易下滑。
* 对照镜头只需约 5 秒，无台词，以动作直接表现“冲撞易掉、出汗易滑”的问题。
* 人物参考可从现有篮球眼镜视频抽取单帧，但对照组眼镜替换为随机普通男性日常眼镜，避免误用运动护目镜结构。
* 产品讲解版本：年轻男性抱篮球站在篮球场进行自然解说；产品眼镜必须严格参考指定实物款，锁定镜框结构、颜色与佩戴位置。
* 保持真实篮球场、手机后置拍摄感，避免棚拍、夸张广告镜头与无关动作。

## 2026-10-07｜近视篮球眼镜短视频素材

新增篮球运动眼镜内容方向：制作约 5 秒无台词痛点对照镜头，用普通男性日常眼镜表现篮球快速移动时容易滑落；另制作年轻男性抱篮球在篮球场自然解说的产品版本。产品版必须严格参考指定实物眼镜，锁定镜框结构、颜色与佩戴位置。整体保持真实篮球场与手机后置拍摄感，避免棚拍和无关动作。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5548509969,
  "url": "https://github.com/ovws/issues/issues/85#issuecomment-5548509969",
  "author": "linear-code[bot]",
  "created_at": "2026-09-05T01:44:57Z",
  "updated_at": "2026-09-05T01:44:57Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-182/眼镜短视频对话脚本与-10-秒分段生成规范">WK-182</a></p>
```

---

## Issue #86

```json
{
  "id": 5354786645,
  "number": 86,
  "title": "维护眼镜镜片配置、报价与商品标题批量素材",
  "url": "https://github.com/ovws/issues/issues/86",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-05T01:45:03Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "工作验证",
    "电商运营",
    "商品/SKU",
    "内容文案"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-03 ～ 2026-09-04 商品报价、SKU 文本与标题批量整理。

## 目标

维护眼镜商品可配镜片规格、价格和标题素材的统一口径，减少不同链接之间价格/度数/品牌系列写错。

## 本周价格口径示例

* 无度数：镜框 + 平光防蓝光镜片 39。
* 高性价比：1.56 防蓝光（0-300 度）76；1.61（0-500 度）89；1.67（0-800 度）149；1.74（0-1200 度）429。
* 依视路万新系列：1.56 高清 129；1.61 高清 149；1.67 高清 249；1.74 高清 549。
* 商品页面需清楚区分无度数、高性价比、舒适进阶/品牌系列等层级，品牌包装/真伪承诺文案按实际商品规则使用。

## 标题素材

本周继续批量整理木纹黑框、大黑框、TR90 冷茶色/方圆框等近视眼镜标题；标题围绕人群、脸型、框型、颜色、可配度数、防蓝光、轻量等真实卖点组合，避免重复堆词和虚构属性。

## 验收

新报价/标题进入商品配置前进行一次规格、度数范围、价格、品牌系列和标题属性一致性检查。

## 2026-09-07 ～ 2026-09-08 文案补充

* 继续维护运动护目镜批量文案，重点覆盖登山 / 骑行双场景与纯骑行场景；批次通常为 10～23 条 JSON 输出。
* 猫眼墨镜、黑色大框眼镜继续按不同批次补充标题/口播，要求批次之间降低重复句式和卖点堆叠。
* 商品标题继续围绕真实属性组合：框型、颜色、脸型适配、可配度数、防蓝光、轻量、素颜/穿搭等；不写未确认的材质或认证。
* 新品标题明确避免误写“钛 / 纯钛”等并非真实材质的卖点。
* 价格单、镜片系列和标题素材输出时保持结构化，便于复制进千牛、表格或后续自动化流程。

## 2026-09-09 文案批次补充

* 运动护目镜继续按登山 / 骑行双场景批量生产文案，本周新增多轮 23 条批次；每轮需与历史批次拉开标题和口播句式差异，不能只是同义替换。
* 输出继续保持结构化 JSON，方便直接进入内容生产/自动化流程。
* 猫眼墨镜、黑色大框眼镜等其他品类继续沿用真实属性优先、避免虚构材质和重复堆词的规则。

## 2026-09-10 商品命名与卖点补充

* 商品颜色/框型四字命名需要同时体现颜色与框型，且指定以“框”结尾时严格保持四个汉字；例如玳瑁猫眼、黑银配色等命名不能只做颜色堆叠。
* 卖点探索开始减少行业已经高度同质化的常规词（轻、显脸小、防蓝光等单一表述），优先寻找更具体的佩戴体验、场景问题或视觉差异点；但仍不得虚构材质、认证和功能。
* 小标题优化要求前后语义关联，避免“复古时髦 / 高智气质感”这类两个独立概念机械并列；保持原有字数/节奏时优先统一气质方向。

## 2026-09-11 商品标题规则补充

* 滑雪眼镜/护目镜标题继续严格控制在 30 字以内，并优先从已确认的真实商品词中重组，不擅自加入“可配度数”等未要求属性。
* 标题中的高频同质词需要主动替换优化，例如在不改变真实功能的前提下减少重复使用“防雾”等词，保持搜索覆盖同时提升标题差异度。
* 用户给出多条候选标题时，以候选中的真实词库为边界做组合与精简，不额外创造可能造成商品属性误导的新卖点。

## 2026-09-14 ～ 2026-09-18 商品卖点与标识补充

* TR 镜框商品卖点文案需避免与主图已有“轻盈”重复；新增标语保持指定 4+5 字节奏，并围绕 TR 实际材质体验表达，不误写纯钛等材质。
* 颜色/款式命名继续采用简洁商业化方向；近期已有“星河银、气质黑、轻奢金”等命名体系，可作为同系列语感参考。
* 视特耐蔡司相关视觉新增镭射激光防伪标/S 字符 Logo 素材需求；输出以清晰、可用于电商图的透明标识为目标，并可提供 SVG 矢量版本。
* 驾驶通勤卖点围绕山洞/强光切换等真实痛点，短文案优先控制在约 8–10 字；避免重复堆砌泛化功能词。

## 2026-09-20 ～ 2026-09-21 内容批次补充

* 新增大框墨镜批量文案生产，单批可达约 58 条；继续要求批次内标题/口播差异明显，避免只做同义词替换。
* 新增防风骑行护目镜约 12 条批次；文案聚焦骑行、防风、户外运动等已确认场景，不擅自加入未确认功能。
* 运动护目镜仍按登山/骑行不同侧重点拆分批次，保持结构化输出，方便直接进入后续内容生产流程。

## 2026-09-23 追加：卖点短句口径

* 老花镜/阅读镜卖点短句避免反复使用“高清”作为泛化词；优先改为“清晰镜片、阅读更清楚、视野清楚”等与实际功能一致的表达。
* 需要固定字数节奏时按指定结构执行，例如 4+5+4，不因追求押韵擅自增加未经确认的功能属性。
* 批量标题/卖点继续执行去重，功能词、舒适词、场景词分别组合，避免同一页面连续重复相同核心词。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5548510742,
  "url": "https://github.com/ovws/issues/issues/86#issuecomment-5548510742",
  "author": "linear-code[bot]",
  "created_at": "2026-09-05T01:45:05Z",
  "updated_at": "2026-09-05T01:45:05Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-183/维护眼镜镜片配置报价与商品标题批量素材">WK-183</a></p>
```

---

## Issue #87

```json
{
  "id": 5387994078,
  "number": 87,
  "title": "同步 Rime Moran 主配置到 iOS 分支并发布可下载 Release",
  "url": "https://github.com/ovws/issues/issues/87",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-08T14:28:24Z",
  "updated_at": "2026-09-30T01:12:56Z",
  "closed_at": "2026-09-30T01:12:56Z",
  "labels": [
    "component: deployment",
    "component: config",
    "工作验证",
    "Improvement",
    "GitHub"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-08 Rime Moran / iOS 配置同步与简繁问题排查。

## 目标

把当前已调整到合理状态的主配置同步到 iOS 使用分支，同时保证默认输入结果以简体中文为主，不因上游配置覆盖而退化为仅繁体；完成后提供手机端可直接下载的 Release 压缩包。

## 关键要求

* 自有仓库：`ovws/rime-moran`。
* 上游参考：`rimeinn/rime-moran`，当前 GitHub 默认分支为 `main`；聊天中曾以 Master 指代主配置分支。
* 同步流程要求：先拉取主配置最新状态，再处理 iOS 分支；iOS 分支的改动不反向合并覆盖主配置。
* 默认候选应为简体；繁体只能在用户显式切换对应配置后出现，不能默认只出繁体。
* 修复/保留原有输入体验：拆分显示、表情候选、拼音显示等能力不能因同步丢失。
* 避免简单替换上游文件导致 OpenCC / simplification / switches 等关键配置被覆盖。
* iOS 产物需要打包成 Release 压缩包，便于手机端直接下载。

## 验收

* 主配置与 iOS 分支关系清晰，无错误反向合并。
* iOS 端默认简体输出正常；繁体切换可控。
* 拆分显示、表情候选、拼音显示正常。
* GitHub Release 中存在对应可下载压缩包，并与当前 iOS 配置一致。

## 当前状态

已完成多轮排查与配置调整，当前设为 In Review，保留最终 iOS 实机验证与 Release 一致性检查。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5586737975,
  "url": "https://github.com/ovws/issues/issues/87#issuecomment-5586737975",
  "author": "linear-code[bot]",
  "created_at": "2026-09-08T14:28:26Z",
  "updated_at": "2026-09-08T14:28:26Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-184/同步-rime-moran-主配置到-ios-分支并发布可下载-release">WK-184</a></p>
```

---

## Issue #88

```json
{
  "id": 5387997653,
  "number": 88,
  "title": "修复 Google Flow 眼镜侧边白色部件幻觉",
  "url": "https://github.com/ovws/issues/issues/88",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-08T14:28:46Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "故障",
    "工作验证",
    "Improvement",
    "AI 工具",
    "测试",
    "短视频"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-04 ～ 2026-09-08 Google Flow 眼镜视频生成连续调优。

## 现象

上传的眼镜实物除镜片外应为全黑结构，但 Flow 在视频里反复在镜框/镜腿侧边生成额外白色线条或白色小部件；直接在提示词中反复强调“不要白线”有时反而会强化该幻觉。

## 当前策略

* 眼镜参考图作为唯一商品结构来源。
* 使用正向约束：除镜片外，整副眼镜只有纯黑色；镜框、镜腿、连接件全部黑色；没有第二种颜色，没有任何额外装饰或附加零件。
* 不再把错误形态详细写进提示词，减少模型对“白线/白色部件”概念的注意力。
* 视频全程保持眼镜佩戴，禁止模型自动增加摘镜、变形、换款或侧边结构变化。
* 人物和场景允许更换，但眼镜结构、颜色、比例必须固定。

## 测试

* 使用同一眼镜参考图对比旧提示词与新正向约束提示词。
* 检查正面、侧面、人物转头和镜头运动时是否出现额外白色部件。
* 如果仍出现，继续缩短商品描述，只保留结构锁定和颜色锁定，避免对错误元素做负向描写。

## 验收

连续多次生成中，眼镜侧边不再出现参考图中不存在的白色/银色零件，且眼镜本体结构与上传实物一致。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5586742929,
  "url": "https://github.com/ovws/issues/issues/88#issuecomment-5586742929",
  "author": "linear-code[bot]",
  "created_at": "2026-09-08T14:28:48Z",
  "updated_at": "2026-09-08T14:28:48Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-185/修复-google-flow-眼镜侧边白色部件幻觉">WK-185</a></p>
```

---

## Issue #89

```json
{
  "id": 5388000500,
  "number": 89,
  "title": "设计“安视清”老花眼镜品牌 Logo 与中英文商业版本",
  "url": "https://github.com/ovws/issues/issues/89",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-09-08T14:29:04Z",
  "updated_at": "2026-09-08T14:29:06Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "Improvement",
    "图像编辑",
    "电商运营"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-07 安视清老花眼镜品牌 Logo 多轮生成与筛选。

## 目标

为“安视清老花眼镜”建立可用于商品主图、店铺视觉和包装延展的简洁品牌标识，重点突出商业感与眼镜品类识别。

## 本周迭代

* 第一轮探索“安视清 / 安视清眼镜 / 安视清老花眼镜”等中文文字标识。
* 后续明确不使用眼镜图形，只保留文字 Logo。
* 去除 ® 等不需要的注册标识。
* 增加英文 `AnShiQing` 方向，形成中文、英文各自可独立使用的版本。
* 最终进一步提升商业感，避免普通字体排字感，要求更像正式品牌字标。

## 输出规范

* 中文与英文均需可单独使用。
* 适合白底商品主图、店铺页、包装和视频角标等电商场景。
* 不依赖复杂图标，优先通过字体结构、字距、比例和识别度体现品牌感。

## 状态

本轮 Logo 探索和多批次输出已完成，后续如确定最终商标版本可再拆独立定稿/商标规范任务。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5586746663,
  "url": "https://github.com/ovws/issues/issues/89#issuecomment-5586746663",
  "author": "linear-code[bot]",
  "created_at": "2026-09-08T14:29:06Z",
  "updated_at": "2026-09-08T14:29:06Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-186/设计安视清老花眼镜品牌-logo-与中英文商业版本">WK-186</a></p>
```

---

## Issue #90

```json
{
  "id": 5412509659,
  "number": 90,
  "title": "开发 Chrome 淘宝商品主图本地替换预览插件",
  "url": "https://github.com/ovws/issues/issues/90",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-10T13:01:41Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "Improvement",
    "商品主图",
    "电商运营",
    "网站/前端"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-09 淘宝商品页主图替换插件开发与 DOM 定位排查。

## 目标

开发一个 Chrome 扩展，在本地浏览淘宝商品详情页时，将页面展示的商品主图临时替换为用户自己的图片，用于快速预览/对比主图效果，不修改淘宝线上商品数据。

## 当前定位

淘宝放大预览区域包含 `div.js-image-zoom__zoomed-image`，实际图片通过元素内联样式 `background-image: url(...)` 设置；初版仅替换普通 `<img src>` 无法覆盖该区域。

## 实现要求

* 支持用户选择/载入自己的主图。
* 替换商品主图显示，并同步处理放大镜区域的 `background-image`。
* 页面因 React/Vue/淘宝脚本重新渲染 DOM 后，替换结果仍可自动恢复，可考虑 MutationObserver。
* 不向淘宝服务器提交图片，不修改商品真实素材，只作用于当前浏览器页面。
* 对淘宝图片懒加载、缩略图切换和放大预览做回归测试。
* 最终以可直接加载的 Chrome 扩展文件形式交付，而不是只提供代码片段。

## 验收

打开淘宝商品页后可选择本地主图，主展示图、缩略图/放大预览中的目标图片均能稳定替换；鼠标触发放大镜时不会重新显示原始 [gw.alicdn.com](<http://gw.alicdn.com>) 图片。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5619095370,
  "url": "https://github.com/ovws/issues/issues/90#issuecomment-5619095370",
  "author": "linear-code[bot]",
  "created_at": "2026-09-10T13:01:43Z",
  "updated_at": "2026-09-10T13:01:43Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-187/开发-chrome-淘宝商品主图本地替换预览插件">WK-187</a></p>
```

---

## Issue #91

```json
{
  "id": 5487878830,
  "number": 91,
  "title": "Oracle Cloud 实例成本与 SSH 登录环境整理",
  "url": "https://github.com/ovws/issues/issues/91",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-17T13:17:51Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "security",
    "component: deployment",
    "工作验证",
    "AWS"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-17 Oracle Cloud 开通、实例费用和 SSH 登录排查。

## 内容

* 检查 Oracle Cloud Free Tier / Always Free 实例规格与实际计费。
* 排查 E5.Flex、VM.Standard.A1.Flex 等实例成本差异。
* 处理 SSH 私钥权限问题：Windows ACL、Bad permissions、Permission denied。
* 记录 OCI 实例创建、停止、删除、费用估算和免费额度限制。

## 验收

* 能稳定 SSH 登录实例。
* 明确实例是否产生费用。
* 保留安全的密钥权限设置流程。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5715000656,
  "url": "https://github.com/ovws/issues/issues/91#issuecomment-5715000656",
  "author": "linear-code[bot]",
  "created_at": "2026-09-17T13:17:53Z",
  "updated_at": "2026-09-17T13:17:53Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-188/oracle-cloud-实例成本与-ssh-登录环境整理">WK-188</a></p>
```

---

## Issue #92

```json
{
  "id": 5563039822,
  "number": 92,
  "title": "TreeLess｜重做 Typeless 风格 iOS 语音输入客户端（VivaDicta 仅作底层参考）",
  "url": "https://github.com/ovws/issues/issues/92",
  "state": "closed",
  "state_reason": "not_planned",
  "author": "ovws",
  "created_at": "2026-09-24T04:16:28Z",
  "updated_at": "2026-09-24T10:47:43Z",
  "closed_at": "2026-09-24T10:47:43Z",
  "labels": [
    "工作验证",
    "特性",
    "AI 工具",
    "GitHub",
    "开源项目评估"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 2
}
```

### 正文

````text
## 当前定义（以此版本为唯一执行基线）

实际项目：**TreeLess**  
代码仓库：https://github.com/ovws/TreeLess  
参考项目：https://github.com/n0an/VivaDicta

**不要继续沿用或修补 VivaDicta 的产品交互。** VivaDicta 只用于参考/复用底层实现；TreeLess 的 Keyboard UI、导航、状态机和用户流程按 Typeless 风格重新设计。

此前基于旧方案已经完成的 UI、Provider、脚本和提交 **不默认视为最终方案**。Codex 接手后必须先重新审计，能复用则保留，会造成跳 App 或复杂交互则替换。

## 唯一核心体验

```
当前 App 输入框
→ 切到 TreeLess 键盘
→ 点麦克风
→ 直接录音
→ 停止/自动结束
→ ASR
→ AI Polish
→ 自动上屏
```

日常输入过程中必须做到：
- 不跳回 TreeLess 主 App
- 不跳设置页
- 不要求复制 / 粘贴 / 确认
- 不打断当前微信、ChatGPT、Safari 等输入场景
- 可连续重复多次语音输入

主 App 仅用于首次权限、API/Provider、语言和少量设置。

## 第一优先级：先做“不跳 App” POC

在继续做 UI 和附加功能前，先验证 Keyboard Extension 能否在目标 iOS 版本下完成：

1. 当前 App 内直接开始/结束录音
2. ASR 请求
3. AI Polish
4. UITextDocumentProxy 自动插入
5. 连续多轮输入稳定

如果系统限制导致任何一步必须离开当前 App，必须先记录：
- 具体 iOS / Extension 限制
- 触发限制的 API
- 可行替代方案
- 最少跳转方案

**禁止未经验证直接沿用 VivaDicta 当前的跳转流程。**

## 可复用范围

优先评估：
- Audio / Recording
- ASR Provider
- Cloud / Local Transcription
- AI Provider / Polish
- Keychain
- App Group / IPC
- Keyboard Extension 中纯底层逻辑

不要照搬：
- VivaDicta 页面结构
- 导航
- Keyboard 交互
- 状态机
- Notes / RAG / Watch 等外围能力

## Provider

ASR：
- Volcengine
- GLM-ASR
- OpenAI / Groq
- Custom OpenAI-Compatible
- Local Whisper（确认不会拖累键盘体验再保留）

AI Polish：
- DeepSeek
- OpenAI / Gemini
- Custom OpenAI-Compatible

AI 失败必须 fallback Raw Transcript。API Key 使用 Keychain。

## Keyboard UI

Voice First，极简：
- Mic / Stop
- Listening / Transcribing / Polishing
- Delete
- Return
- Undo
- 系统键盘切换

不要完整 QWERTY，不要把复杂设置塞进 Keyboard。

## 执行顺序

1. 审计当前 TreeLess 源码与已有提交，区分“可复用 / 需返工 / 应删除”。
2. 对照 VivaDicta，仅抽取值得复用的底层能力。
3. 完成不跳 App 的 Keyboard POC。
4. POC 通过后接完整 ASR / AI fallback。
5. 重写 Keyboard UI。
6. 极简化主 App / Settings。
7. 真机测试微信、ChatGPT、Safari、Notes、Messages 等。

## 验收标准

> **在任意输入框切到 TreeLess 后，可以连续完成“点麦克风 → 说话 → 转写 → 自动上屏”，整个过程中不离开当前 App。**

这一条没有通过之前，不继续堆 UI、首页、附加功能或无关 Provider。

Linear: https://linear.app/cvm/issue/WK-189/treeless重做-typeless-风格-ios-语音输入客户端vivadicta-仅作底层参考
````

### 评论（2）

#### 评论 1

```json
{
  "index": 1,
  "id": 5807556898,
  "url": "https://github.com/ovws/issues/issues/92#issuecomment-5807556898",
  "author": "linear-code[bot]",
  "created_at": "2026-09-24T04:16:29Z",
  "updated_at": "2026-09-24T04:16:29Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-189/基于-vivadicta-改造-typeless-风格-ios-语音输入客户端">WK-189</a></p>
```

#### 评论 2

```json
{
  "index": 2,
  "id": 5810482374,
  "url": "https://github.com/ovws/issues/issues/92#issuecomment-5810482374",
  "author": "ovws",
  "created_at": "2026-09-24T08:18:00Z",
  "updated_at": "2026-09-24T08:18:00Z",
  "author_association": "OWNER",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
## 执行方向已整体重置

当前以 **TreeLess** 为实际项目，VivaDicta 仅作底层参考。此前“在 VivaDicta UX 上继续改”的方向已废弃。

后续第一优先级：先验证 **Keyboard Extension 不跳 App** 的完整 POC（录音 → ASR → AI Polish → 自动上屏 → 连续再次输入）。POC 未通过前，不继续堆 UI 和附加功能。

Linear： https://linear.app/cvm/issue/WK-189/treeless重做-typeless-风格-ios-语音输入客户端vivadicta-仅作底层参考  
TreeLess： https://github.com/ovws/TreeLess
```

---

## Issue #93

```json
{
  "id": 5567176158,
  "number": 93,
  "title": "AI 语音输入法｜Typeless UI + 国产 ASR/LLM + BYOK",
  "url": "https://github.com/ovws/issues/issues/93",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-24T10:52:34Z",
  "updated_at": "2026-10-07T05:36:27Z",
  "closed_at": "2026-10-07T05:36:27Z",
  "labels": [
    "工作验证",
    "特性",
    "AI 工具",
    "GitHub",
    "开源项目评估"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
# ovws/internal-ai-api-config#93｜AI 语音输入法 — Codex 执行规范

## 1. 任务目标

实现一款 iOS 纯 AI Voice Keyboard。

产品方向：

* Voice First / AI First
* 中文优先
* UI / 交互高度参考 Typeless iOS
* 支持国内 ASR / LLM
* 支持 BYOK / Custom API
* Session 已准备好时，连续语音输入不应反复跳回主 App
* 说话结束后自动完成：录音 → ASR → AI 整理 → 当前输入框上屏
* 做完整产品，不做 Demo

注意：

> 本项目的核心工作不是重新发明 iOS Voice Keyboard 底层，而是 **复用成熟开源底层，然后重点完成 Typeless UI、国产 API、中文 AI 输入体验和产品化功能。**

---

# 2. Codex 必须遵守的原则

## MUST

* 优先复用成熟 MIT 开源实现
* 底层能用就保留
* 只对不满足目标的模块做最小修改
* 主要精力投入 UI、国产 Provider、中文 AI 体验
* 每阶段必须 Build
* 真机相关功能必须在真实 iPhone 验证后才能标记完成
* 每阶段都更新 ovws/internal-ai-api-config#93 进展

## DO NOT

* 不要从空工程重新造 Keyboard Extension
* 不要重新造已经存在的 App Group / Audio Session / IPC
* 不要再基于 VivaDicta UI 继续改
* 不要一开始研究 5\~6 个仓库
* 不要先做复杂架构重构
* 不要把 Simulator 可运行当作功能完成
* 不要每次语音都跳主 App
* 不要因为 LLM 失败导致整次输入失败

开发优先级：

> Reuse → Adapt → Replace only when necessary

---

# 3. 首选底座

## 首选：Muesli iOS

仓库：
[https://github.com/Muesli-HQ/muesli-ios](<https://github.com/Muesli-HQ/muesli-ios>)

License：
MIT

优先原因：

* Main App + Keyboard Extension + Shared 已完整
* 已有 App Group
* 已有 Keyboard handoff
* 已有 Keyboard Session Mode
* 已有 History
* 已有 Personal Dictionary
* Swift / SwiftUI
* 有测试
* MIT 可直接 fork 和修改

### Codex 第一步

只做快速验证，不做长期调研：

1. clone Muesli
2. build
3. 真机安装
4. 启用 Keyboard Extension
5. 验证 Keyboard Session Mode
6. 连续 Speak 5\~10 次
7. 记录是否每次都跳主 App

如果：

* Keyboard 能正常工作
* Session Mode 能基本支持连续使用
* 工程结构没有严重阻碍

则：

> **直接采用 Muesli 作为主工程，不再继续研究其他底座。**

如果 Muesli 底层明显不满足，再进入“Session 层替换”，而不是推倒整个工程。

---

# 4. 其他开源项目只作为定向参考

## VocaPhone

[https://github.com/VocaHQ/vocaphone](<https://github.com/VocaHQ/vocaphone>)

用途：

* Quick Dictation
* Session keep-alive
* 10 min / 20 min / until-close Session
* Session warm 后减少重复跳 App

License：
AGPL-3.0

要求：

* 不直接复制源码到闭源项目
* 只参考行为、状态机和产品交互
* 如果 Muesli Session 不够好，再 clean-room 独立实现同类机制

## Dictus iOS

[https://github.com/getdictus/dictus-ios](<https://github.com/getdictus/dictus-ios>)

用途：

* MIT
* cold-start audio bridge
* App / Keyboard / Core 分层

只有遇到 cold-start 问题时再参考。

## Vox.md

[https://github.com/CodyBontecou/vox.md](<https://github.com/CodyBontecou/vox.md>)

用途：

* persistent listening
* iOS 26+ SpeechAnalyzer / SpeechTranscriber
* streaming transcript

只有以后做 streaming / persistent mode 时再参考。

## Open Voice Typer

[https://github.com/cosmicshuai/open_voice_typer](<https://github.com/cosmicshuai/open_voice_typer>)

用途：

* GLM-ASR
* DeepSeek
* OpenAI-compatible API
* BYOK
* Provider 配置设计

License 未确认前，不直接复制源码。

---

# 5. Phase 0｜底座确认

目标：

> 快速决定是否直接 fork Muesli。

完成以下内容即可：

* Muesli build 成功
* Keyboard Extension 可安装
* 真机可输入
* Session Mode 可测试
* 连续语音基本可用

输出：

docs/base-selection.md

内容只需要：

* 是否采用 Muesli
* 哪些模块直接保留
* 哪些模块删除
* 哪些模块准备重写
* 已发现的关键问题

### Gate

如果 Muesli 可以满足基础使用：

> 立即进入 Phase 1。

不要继续做额外底座调研。

---

# 6. Phase 1｜清理底座 + 重做 Typeless Keyboard UI

这是第一核心开发阶段。

## 保留

* Keyboard Extension
* App Group
* Audio Session
* Keyboard / Main App 通信
* UITextDocumentProxy 插入逻辑
* History 基础能力
* Dictionary 基础能力
* 安全存储能力
* 可复用测试

## 删除 / 隐藏

所有和纯 AI 输入法无关的功能，例如：

* Meeting
* Notes
* Summary
* RAG
* Watch
* 非必要 Dashboard
* 不相关生产力功能

## Keyboard UI

重点重做成 Typeless 风格。

必须包含以下状态：

### Ready

* 主 Speak 按钮
* Session Ready / Cold 状态
* Globe
* Delete
* Return
* Undo

### Listening

* 明确录音状态
* 波形 / 音量反馈
* Stop
* Cancel

### Processing

* Transcribing
* Polishing

### Success

* 自动插入
* 返回 Ready

### Error

* Retry
* 明确错误
* 不弹复杂 Alert

## UI 要求

高度参考 Typeless：

* Keyboard 高度
* 主按钮位置
* Mic 大小
* 圆角
* 间距
* 字号
* 状态切换
* Light / Dark
* 动画节奏

开发前输出：

docs/typeless-ui-spec.md

禁止直接提取 Typeless 品牌资源。

---

# 7. Phase 2｜国产 ASR Provider

这是第二核心开发阶段。

统一协议：

SpeechProvider

## P0 必须完成

### Volcengine

支持：

* App ID
* Access Token / Secret
* Endpoint
* Model / resource id
* timeout
* 自定义配置

### GLM-ASR

支持：

* API Key
* Base URL
* Model
* timeout

### Custom OpenAI-Compatible

支持：

* Base URL
* API Key
* Model
* Headers
* Query params
* timeout

## P1

后续增加：

* 豆包
* 阿里 / 通义
* 腾讯 ASR
* 百度 ASR

## P2

可兼容：

* OpenAI
* Groq
* Deepgram
* ElevenLabs

所有凭证使用 Keychain。

禁止硬编码 API Key。

---

# 8. Phase 3｜国产 LLM Provider

统一协议：

AIProvider

## P0

必须支持：

* DeepSeek
* 豆包
* 通义千问
* GLM
* Custom OpenAI-Compatible

## P1

增加：

* Kimi / Moonshot
* MiniMax

## P2

兼容：

* OpenAI
* Gemini
* Claude
* OpenRouter

用户可配置：

* Base URL
* API Key
* Model
* Temperature
* Max Tokens
* Custom Headers
* System Prompt

---

# 9. Phase 4｜中文 AI 输入体验

这是本项目的核心差异化功能。

Default 模式必须做到：

* 去掉“嗯、呃、那个、就是”等无意义口语
* 去重复
* 理解自我纠正
* 自动中文标点
* 合理分段
* 中英混输
* 保持原意
* 不擅自增加事实
* 不做无关扩写

示例：

输入：

“明天下午三点，不对，四点开会，然后那个你帮我提醒一下”

输出：

“明天下午四点开会，帮我提醒一下。”

必须提供：

* Original
* Default
* Professional
* Translate
* Custom Prompt

AI Polish 失败：

> 直接把 Raw Transcript 上屏。

绝不能整次输入失败。

---

# 10. Phase 5｜Personal Dictionary

必须支持：

* 人名
* 品牌
* 商品名
* 公司名
* 专业术语
* 常用英文
* 自定义替换

支持：

* Prompt 注入
* ASR hot words（Provider 支持时）
* 本地持久化

---

# 11. Phase 6｜History / Settings / 产品化

## History

保存：

* Raw Transcript
* Final Text
* 时间
* ASR Provider
* LLM Provider
* Model
* ASR latency
* AI latency
* Mode

默认不保存音频。

支持：

* Search
* Copy
* Re-run
* Delete
* Clear
* 7 / 30 / 90 天自动清理
* 完全关闭 History

## Settings

至少：

* ASR Provider
* AI Provider
* API 配置
* Language
* Mode
* Session Mode
* Haptic
* Auto Stop
* Auto Insert
* History
* Privacy
* Dictionary
* Debug

---

# 12. Session 行为

不要把 Session 优化作为第一开发重点。

先复用现有底层。

只有真实使用发现跳转体验仍然差时，再做 Session 优化。

目标行为：

## Cold

Speak
→ 必要时短暂打开主 App
→ 建立 Audio Session
→ 返回 Host App

## Warm

Speak
→ 直接录音
→ 不跳 App

## Stop

Stop
→ 停止录音
→ ASR
→ AI Polish
→ insertText
→ Session 保持 Ready

## Idle

Session Ready 不等于持续录音。

空闲状态不得持续采集用户语音。

可提供：

* Standard
* 10 min Quick Session
* 20 min Quick Session
* Until App Closed

---

# 13. 如果 Session 体验仍然差，再做以下优化

仅在需要时处理：

* heartbeat
* stale session cleanup
* requestId / sessionId
* versioned IPC
* cold-start bridge
* controller rebuild recovery
* App killed recovery
* Extension killed recovery
* PiP Skip App Switching
* iOS 26+ streaming

不要在项目一开始先重写这些东西。

---

# 14. Speak to Edit

P1 功能。

支持语音命令：

* 改短一点
* 更正式
* 翻译成英文
* 改成小红书风格
* 更礼貌
* 重新整理

实现前必须先验证 public API：

* selectedText / selection 能力
* documentContextBeforeInput
* documentContextAfterInput

只使用公开 API。

---

# 15. 真机硬验收

必须在真实 iPhone 测试。

至少覆盖：

* 微信
* ChatGPT
* Safari
* Notes
* Messages
* 小红书
* 抖音
* Telegram
* Mail / Gmail

核心测试：

 1. 打开微信输入框
 2. 切到本输入法
 3. 必要时初始化一次 Session
 4. 连续执行 10 次：
    Speak → 说话 → Stop → ASR → AI → 自动上屏
 5. 10 次不能每次都跳主 App
 6. 切换到 ChatGPT 后继续使用
 7. 无重复插入
 8. 无永久 Starting
 9. Session 失效后能明确恢复
10. LLM 失败时 Raw Transcript 正常上屏

还必须覆盖：

* 中文
* 中英混输
* 长语音
* AirPods
* 蓝牙切换
* 电话中断
* 锁屏恢复
* Wi‑Fi / Cellular 切换
* ASR timeout
* LLM timeout
* App 被杀
* Extension 被杀

---

# 16. Codex 每阶段交付格式

每完成一个 Phase，必须：

* Build
* 能真机验证的必须真机验证
* Commit
* 更新 docs
* 更新 ovws/internal-ai-api-config#93

Linear 进展必须明确分成：

### 已完成

实际已实现的代码。

### 已验证

真实 Build / 真机验证通过的内容。

### 未验证

代码存在，但当前没有真实环境证明。

### 已知问题

明确列出。

### 下一步

只写下一阶段实际动作。

禁止使用：

* “应该可以”
* “理论上可用”
* “基本完成”

来代替真实验证。

---

# 17. License 规则

可直接 fork / 修改：

* MIT 项目
* 保留原 License / attribution

如果项目是：

* GPL
* AGPL
* 无明确 License

则：

* 不直接复制源码进入闭源工程
* 只研究公开行为 / 架构
* 需要时 clean-room 独立实现

---

# 18. 最终验收

最终产品必须满足：

* Typeless 风格 Keyboard UI 高度还原
* Voice First
* 中文输入体验优秀
* Volcengine / GLM-ASR 可用
* DeepSeek / 豆包 / 通义 / GLM 可用
* Custom OpenAI-Compatible
* BYOK
* 中文 AI Polish
* Personal Dictionary
* History
* Modes
* Provider Settings
* Session warm 时不反复跳 App
* AI 失败有 Raw fallback
* 微信 / ChatGPT 等真实 App 长期可用
* 不依赖 VivaDicta
* 不使用私有 API

# 执行重点

> **80% 精力做 Typeless UI + 国产 API + 中文 AI 输入体验。**

> **20% 精力维护和适配现成底层。**

> **只在现有底层确实不满足目标时，才重写 Audio Session / IPC。**

## 2026-09-24 当周整理补充

* 已确认 ovws/internal-ai-api-config#92 与本任务属于同一产品方向；ovws/internal-ai-api-config#92 保持搁置，仅作为 TreeLess / VivaDicta 旧方案与验证记录，本任务作为后续唯一主执行单，避免双线重复开发。
* 产品实现策略进一步明确：优先复用成熟开源 Voice Keyboard 底层，核心投入放在 Typeless 风格 UI、国产 ASR/LLM Provider、BYOK 和中文 AI 整理体验，不从零重造 Keyboard Extension。
* 首选底座为 Muesli iOS；先完成 build、真机 Keyboard Extension、Session Mode 与连续语音验证，通过后直接进入 UI / Provider 改造，不继续无边界调研。
* TreeLess 仓库继续作为实际代码承载之一；开发过程中保持 GitHub issue / Linear 进度同步，真机未验证的能力不得标记完成。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5812688497,
  "url": "https://github.com/ovws/issues/issues/93#issuecomment-5812688497",
  "author": "linear-code[bot]",
  "created_at": "2026-09-24T10:52:36Z",
  "updated_at": "2026-09-24T10:52:36Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-190/ai-语音输入法纯-ai-voice-keyboardtypeless-11-ui-国内模型自定义">WK-190</a></p>
```

---

## Issue #94

```json
{
  "id": 5631001731,
  "number": 94,
  "title": "Kaku Windows｜参考 tw93/Kaku 开发 Windows 客户端并发布 Release",
  "url": "https://github.com/ovws/issues/issues/94",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-09-29T13:03:21Z",
  "updated_at": "2026-10-07T05:36:49Z",
  "closed_at": "2026-10-07T05:36:49Z",
  "labels": [
    "component: deployment",
    "工作验证",
    "特性",
    "GitHub",
    "网站/前端",
    "开源项目评估"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-09-28：要求参考开源项目 `tw93/Kaku`，制作 Windows 版本，并将完整项目源代码上传 GitHub、编译后的 Windows 可执行文件上传到 GitHub Releases。

## 目标

在尊重上游开源许可证与署名要求的前提下，将 Kaku 的核心体验适配到 Windows，形成可持续维护的独立仓库与可直接安装/运行的 Release。

## 上游参考

* GitHub：[https://github.com/tw93/Kaku](<https://github.com/tw93/Kaku>)
* 开发前先核对上游许可证、技术栈、功能边界和可复用代码；保留必要 LICENSE / attribution。

## 执行

* 梳理 Kaku 当前核心功能、交互和技术架构，区分可直接跨平台复用与 macOS 专属实现。
* 设计 Windows 对应实现，优先保持原项目轻量、快捷的产品体验，而不是机械复制 macOS API。
* 完成 Windows 构建、启动、基础功能、快捷键/窗口行为等适配与回归。
* 建立独立 GitHub 仓库并推送完整可构建源码、README、构建说明和许可证信息。
* 配置可复现的 Windows 构建流程；如适合，使用 GitHub Actions 自动构建。
* GitHub Releases 上传 Windows 可执行产物，并附版本、安装/启动方式、已知限制。

## 验收

* 全新 Windows 环境可按 README 构建或直接运行 Release。
* GitHub 仓库包含完整源码，不只上传二进制文件。
* Release 可直接下载 Windows 构建产物。
* 上游许可证与署名处理正确。
* Windows 关键交互经过实际回归，无明显 macOS 专属残留。

## 2026-09-29 ～ 2026-09-30 构建执行状态补充

* GitHub Actions 已触发多次，但近期构建任务未能正常启动/完成；需要区分代码/工作流失败与 GitHub 账户 Billing / spending limit 导致的 job 未启动。
* 已观察到提示：`The job was not started because recent account payments have failed or your spending limit needs to be increased.`；该类情况不应继续通过反复重跑 Actions 排查代码。
* 云端构建受 Billing 阻塞时，执行路径切换为 Windows 本地构建：拉取仓库 → 安装依赖 → 执行 Windows 构建 → 运行产物做基础回归 → 修复错误 → 重新构建。
* 本地验证通过后再推送必要源码/工作流修复，并在 GitHub Releases 上传最终 Windows 可执行产物。
* 最终验收前必须自行再检查一遍：仓库源码是否完整、构建说明是否可复现、Release 资产是否存在且可启动、上游许可证/署名是否保留。
* 如交由本地 Agent 执行，应提供可直接执行的任务单，包含仓库拉取、环境检查、构建命令、错误处理、回归检查、Git push 与 Release 发布步骤。

## 2026-10-01 补充｜Windows 安装包交付

* Windows 版本最终交付除可执行文件外，补充标准安装程序，优先采用 Inno Setup 一类成熟 Windows Installer 方案。
* 安装界面与常见 Windows 软件保持一致：应用图标、安装路径、开始菜单/桌面快捷方式、卸载入口、版本信息等基础项完整。
* 安装器制作应纳入本地构建与 GitHub Release 最终验收，避免只发布裸 EXE。
* 安装器图标和应用图标保持统一，发布前检查无临时 Logo、测试资源或错误品牌信息。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5890862663,
  "url": "https://github.com/ovws/issues/issues/94#issuecomment-5890862663",
  "author": "linear-code[bot]",
  "created_at": "2026-09-29T13:03:23Z",
  "updated_at": "2026-09-29T13:03:23Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-191/kaku-windows参考-tw93kaku-开发-windows-客户端并发布-release">WK-191</a></p>
```

---

## Issue #95

```json
{
  "id": 5712694118,
  "number": 95,
  "title": "Hermes Agent + MEMOH｜双 Agent 协作与本地/云端部署验证",
  "url": "https://github.com/ovws/issues/issues/95",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-10-05T13:17:18Z",
  "updated_at": "2026-10-08T06:46:53Z",
  "closed_at": "2026-10-08T06:46:53Z",
  "labels": [
    "自动化",
    "AI 工具",
    "测试",
    "工作环境",
    "开源项目评估"
  ],
  "assignees": [
    "ovws"
  ],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源

2026-10-03：围绕 Hermes Agent 与 MEMOH 的部署、远程控制、双机器人协作和云端网络环境进行了集中评估。

## 目标

验证一套“本地主力 Agent + 云端补充 Agent”的稳定工作流：本地 macOS M1（8 核 CPU / 8GB 内存）优先运行 Hermes，MEMOH 云端实例作为网络环境更好、长期在线的补充执行节点；同时验证开发 Agent → 测试 Agent → 自动反馈返工的闭环。

## 当前方案

* Hermes 作为主力，优先部署在本地 macOS M1（8 核 / 8GB）。
* MEMOH 暂不作为主力；保留云端补充角色，用于需要公网/不同网络环境/长期在线的任务。
* 用户侧关注 MEMOH 约 33 元/月、8 核 16GB VPS 方案的性价比；正式采用前需核验实际套餐与资源限制。
* 远程触达可围绕 Telegram Bot 等入口设计，但需要把公网入口、反向代理/隧道、鉴权和安全边界单独验证，不能默认本地 Hermes 可直接从公网访问。

## 双 Agent 自动化验证

设计最小闭环：

1. 开发 Agent 接收任务并完成实现。
2. 测试 Agent 自动拉取/运行结果，执行测试和验收。
3. 测试失败时把结构化失败信息、日志和修改要求回传开发 Agent。
4. 开发 Agent 修复后再次触发测试，直到通过或达到人工介入阈值。
5. 保留每轮执行记录，避免两个 Bot 只是相互独立、没有任务依赖关系。

## 待验证

* Hermes 本地部署在 M1/8GB 下的长期资源占用与稳定性。
* Telegram → 本地 Hermes 的安全远程入口方案。
* MEMOH 云实例是否允许作为通用代理/出口节点使用，以及服务条款、端口和流量限制。
* Hermes 约 20 美元方案的实际 VPS 规格与限制。
* 双 Agent 的任务队列、状态机、测试失败回传和重试机制。
* Tailscale 仅作为组网/远程访问能力评估，不默认等同于公网代理服务。

## 验收

完成一条真实开发任务的端到端演练：开发 → 自动测试 → 失败回传 → 修复 → 再测试 → 通过，并确认本地/云端两个 Agent 的职责边界、远程访问方式和安全策略。

## 2026-10-07｜多 Agent 团队协作方案补充

* 优先采用“共享任务板 + Agent 主动领取任务”的低复杂度方案；Linear 负责任务状态与责任分配，GitHub Issue / PR / commit 负责代码交付。
* Developer Agent 查询分配给自己的 Todo / Fix Required，调用 Codex ACP 在 workspace 开发，完成后提交 PR 并推进到 Ready for Test。
* Tester Agent 验证 Ready for Test；失败时回写 Fix Required 与复现信息，形成开发 → 测试 → 返工闭环。
* PM Agent 作为可选层，主要负责拆任务、分配、阻塞追踪和汇总；若这些职责已由人工或 Linear 自动化覆盖，可先不部署 PM。
* API 负责查询、状态修改、评论、PR 等确定性动作；AI Agent 负责理解需求、编码、测试判断与修复方案。
* MEMOH 当前确认可运行 Codex 并支持其他 ACP，但尚未确认存在专用外部调度 API；实现时以实际可用的 ACP、workspace 与任务板能力为准。

## Paperclip 同步

* 来源：KUB-6（Paperclip Issue ID：ebd55b3d-9535-45c0-b2b5-0d6b88188958）
* 当前状态：done
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 5995246614,
  "url": "https://github.com/ovws/issues/issues/95#issuecomment-5995246614",
  "author": "linear-code[bot]",
  "created_at": "2026-10-05T13:17:20Z",
  "updated_at": "2026-10-05T13:17:20Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-192/hermes-agent-memoh双-agent-协作与本地云端部署验证">WK-192</a></p>
```

---

## Issue #96

```json
{
  "id": 5757257676,
  "number": 96,
  "title": "[KUB-1] Paperclip onboarding",
  "url": "https://github.com/ovws/issues/issues/96",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-08T06:45:36Z",
  "updated_at": "2026-10-08T13:05:45Z",
  "closed_at": null,
  "labels": [
    "工作验证",
    "自动化",
    "AI 工具"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
Use the `first-task` skill (/first-task) for this onboarding task. Read its SKILL.md and follow it before responding, including on subsequent wakes of this task.

Single-task proposal mode: `confirmation`.

---

Paperclip 同步元数据

* Paperclip 编号：KUB-1
* Paperclip Issue ID：eb6f3bad-d12b-4f77-afe8-74ddd85b5ce3
* 当前状态：done
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6054146215,
  "url": "https://github.com/ovws/issues/issues/96#issuecomment-6054146215",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T06:45:37Z",
  "updated_at": "2026-10-08T06:45:37Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-193/kub-1-paperclip-onboarding">WK-193</a></p>
```

---

## Issue #97

```json
{
  "id": 5757258764,
  "number": 97,
  "title": "[KUB-2] 创建团队",
  "url": "https://github.com/ovws/issues/issues/97",
  "state": "closed",
  "state_reason": "completed",
  "author": "ovws",
  "created_at": "2026-10-08T06:45:42Z",
  "updated_at": "2026-10-08T06:54:41Z",
  "closed_at": "2026-10-08T06:54:41Z",
  "labels": [],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
创建一个

---

Paperclip 同步元数据

* Paperclip 编号：KUB-2
* Paperclip Issue ID：2baaee1d-afdc-4bcd-b624-7c8862545729
* 当前状态：todo（Paperclip 中已隐藏）
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6054147817,
  "url": "https://github.com/ovws/issues/issues/97#issuecomment-6054147817",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T06:45:43Z",
  "updated_at": "2026-10-08T06:45:43Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-194/kub-2-创建团队">WK-194</a></p>
```

---

## Issue #98

```json
{
  "id": 5757259521,
  "number": 98,
  "title": "[KUB-3] Kaku-Windows：处理设置按钮审查意见并验证",
  "url": "https://github.com/ovws/issues/issues/98",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-08T06:45:45Z",
  "updated_at": "2026-10-08T13:05:51Z",
  "closed_at": null,
  "labels": [
    "Improvement",
    "GitHub",
    "网站/前端",
    "测试"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

处理 Kaku-Windows PR #2 中 Codex 提出的两项高优先级意见，并将可验证的修改推送到该 PR。

PR: ovws/Kaku-Windows#2
仓库: [https://github.com/ovws/Kaku-Windows](<https://github.com/ovws/Kaku-Windows>)

## 工作范围

1. 检查仓库关于标签栏绘制控件的约定。修正设置按钮在复古标签栏的默认显示/渲染行为，避免不符合现有设计约定或挤压标签宽度。保留用户可配置性及 Fancy 标签栏中按钮的正常行为。
2. 增加回归测试，覆盖设置按钮的显示配置组合、标签宽度/按钮命中区域，以及窄窗口布局。
3. 运行适当的测试和 CI 检查，修复本次改动引起的问题，并更新 PR #2。
4. 在本任务汇报改动、测试结果、剩余限制；不要只在父任务留言。

## 验收标准

* 复古栏行为遵守仓库现有约定，默认配置不造成标签宽度问题。
* 新回归测试覆盖上述组合和边界。
* 修改已推送到 PR #2，相关 CI 通过，或在本任务明确列出失败项及原因。

## 参考

Codex 在 PR #2 的审查指出：

* 复古标签栏默认显示设置控件会影响绘制和标签标题宽度。
* 现有测试没有验证 SettingsButton 的显示组合、位置和命中区域，尤其是窄窗口。

---

Paperclip 同步元数据

* Paperclip 编号：KUB-3
* Paperclip Issue ID：a28679ea-c93b-4924-9106-7a48c65a55e0
* 当前状态：done
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6054148805,
  "url": "https://github.com/ovws/issues/issues/98#issuecomment-6054148805",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T06:45:47Z",
  "updated_at": "2026-10-08T06:45:47Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-195/kub-3-kaku-windows处理设置按钮审查意见并验证">WK-195</a></p>
```

---

## Issue #99

```json
{
  "id": 5757260346,
  "number": 99,
  "title": "[KUB-4] 测试任务",
  "url": "https://github.com/ovws/issues/issues/99",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-08T06:45:49Z",
  "updated_at": "2026-10-08T13:05:57Z",
  "closed_at": null,
  "labels": [
    "自动化",
    "AI 工具",
    "测试"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
测试多个Agent节点之间是否能正常通信

---

Paperclip 同步元数据

* Paperclip 编号：KUB-4
* Paperclip Issue ID：04ed66a8-eee9-4621-8def-967922b98240
* 当前状态：done
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6054149681,
  "url": "https://github.com/ovws/issues/issues/99#issuecomment-6054149681",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T06:45:50Z",
  "updated_at": "2026-10-08T06:45:50Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-196/kub-4-测试任务">WK-196</a></p>
```

---

## Issue #100

```json
{
  "id": 5757260934,
  "number": 100,
  "title": "[KUB-5] KUB-4 节点通信回执测试",
  "url": "https://github.com/ovws/issues/issues/100",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-08T06:45:52Z",
  "updated_at": "2026-10-08T13:06:00Z",
  "closed_at": null,
  "labels": [
    "自动化",
    "AI 工具",
    "测试"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
这是 KUB-4 的有界通信测试。请只在本任务评论中回复：‘收到，节点通信正常’，然后将本任务标记为 done；不要执行其他操作。

---

Paperclip 同步元数据

* Paperclip 编号：KUB-5
* Paperclip Issue ID：7537a37f-12ab-4143-a032-323bcd5278a3
* 当前状态：done
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6054150561,
  "url": "https://github.com/ovws/issues/issues/100#issuecomment-6054150561",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T06:45:53Z",
  "updated_at": "2026-10-08T06:45:53Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-197/kub-5-kub-4-节点通信回执测试">WK-197</a></p>
```

---

## Issue #101

```json
{
  "id": 5762304630,
  "number": 101,
  "title": "Paperclip｜接入 Slack / Telegram / 微信远程下达 Agent 任务",
  "url": "https://github.com/ovws/issues/issues/101",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-08T13:05:09Z",
  "updated_at": "2026-10-08T13:05:11Z",
  "closed_at": null,
  "labels": [
    "component: deployment",
    "工作验证",
    "自动化",
    "特性",
    "AI 工具",
    "GitHub"
  ],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 来源与目标

2026-10-07：希望直接在 Slack、Telegram（TG）或微信中向 Paperclip 下达命令，而不是每次打开 Paperclip 控制台。目标是让消息可转为有权限约束的 Paperclip 任务，并能在原聊天渠道查询状态、收到执行结果。

## 执行方案与待办

1. 先核对正在运行的 Paperclip 版本、实例部署方式及聊天连接器/Agent Chat 功能开关。优先验证官方 Slack / Telegram 连接器的现有能力，不重复开发已支持的集成。
2. 打通一个最小闭环：聊天发送任务 → 鉴权并识别目标组织/Agent → 创建或指派 Paperclip 任务 → 触发执行/心跳 → 返回任务编号、状态与结果。
3. Slack：验证 Bot/App 权限、事件订阅/消息入口、指定频道与用户白名单、回复和错误处理。
4. Telegram：验证 Bot Token、Webhook 或长轮询方案、私聊/群聊白名单、回执与结果推送。
5. 微信：不要假设 Paperclip 原生支持。优先复用现有 Cindy / Pi 微信 Relay 经验，评估微信入口 → 安全中转 → Paperclip API/受控适配器；确认稳定性与平台限制后再实施。
6. 处理重复消息幂等、权限边界、审批/敏感操作确认、凭据安全、离线重试、执行日志与超时。
7. 先选一种渠道完成端到端验证，再按稳定性扩展其余渠道；不要同时开工三个入口。

## 验收

* 至少一个聊天渠道可发送自然语言命令并在 Paperclip 中生成可追踪任务，回传任务 ID、执行状态及最终结果。
* 不允许未经授权的群成员直接触发 Agent 或跨组织访问。
* 故障和重复投递不会产生失控执行或重复任务。
* 对尚未验证的微信通道，保留待验证状态，不声称已实现。

## 关联

* Paperclip 上游：[https://github.com/paperclipai/paperclip](<https://github.com/paperclipai/paperclip>)
* 已有 Paperclip onboarding：ovws/internal-ai-api-config#96（KUB-1）
* 多 Agent 协作方案：ovws/internal-ai-api-config#95
* 现有微信 Relay：ovws/internal-ai-api-config#41，仓库 [https://github.com/ovws/wechat-cindy-relay](<https://github.com/ovws/wechat-cindy-relay>)
* 关联的 GitHub 工作记录：[https://github.com/ovws/internal-ai-api-config/issues/95](<https://github.com/ovws/internal-ai-api-config/issues/95>)

说明：这是新的“聊天指令入口”交付项，区别于 ovws/internal-ai-api-config#95 的 Agent 协作架构及 ovws/internal-ai-api-config#41 的 Cindy 专用微信 Relay，不重复建这两个已有任务。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6060513069,
  "url": "https://github.com/ovws/issues/issues/101#issuecomment-6060513069",
  "author": "linear-code[bot]",
  "created_at": "2026-10-08T13:05:11Z",
  "updated_at": "2026-10-08T13:05:11Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-198/paperclip接入-slack-telegram-微信远程下达-agent-任务">WK-198</a></p>
```

---

## Issue #102

```json
{
  "id": 5775003052,
  "number": 102,
  "title": "OpenTypeless P0 运行验收（按 Linear 测试规范）",
  "url": "https://github.com/ovws/issues/issues/102",
  "state": "open",
  "state_reason": null,
  "author": "ovws",
  "created_at": "2026-10-09T08:09:52Z",
  "updated_at": "2026-10-09T08:21:42Z",
  "closed_at": null,
  "labels": [],
  "assignees": [],
  "milestone": null,
  "locked": false,
  "comments": 1
}
```

### 正文

```text
## 目标

对 OpenTypeless P0 当前交付执行独立验证，按 Linear 可执行任务的测试标准给出可复核证据。结论必须区分通过、失败、未验证；静态检查不能代替构建、设备或真实服务验证。

## 被测交付

* 最新修复提交：`f7191c20226ac7815424ae84924a285d4aacd7fc`
* Paperclip 交付：KUB-21；完整 Git bundle 附件 ID `f3c9d537-3e67-493e-b6f2-6b410df52e49`；源码归档附件 ID `a26c0166-216c-4f2d-b504-0fedae4945bf`；最新开发验证报告 `docs/verification-report.md`。
* 父任务验收标准：KUB-20。
  先确认检出的 HEAD、文件清单和报告版本；若 Linear 执行环境无法访问 Paperclip 附件或仓库，请明确列出访问阻塞及需要提供的源文件/仓库入口，不要改用旧版本冒充最新交付。

## 执行配置阻塞

首次指派给 Linear Agent 被工作区拒绝：Linear 返回 coding sessions 需要由 workspace admin 在 AI settings 中启用，并配置 GitHub code access。请在该能力启用后再执行代码/设备任务。未启用前，先报告阻塞；不要声称已开始运行验证。

## 验收测试清单

1. **环境与构建**
   * 记录 macOS、Xcode、Swift、iOS SDK 版本及目标设备/模拟器型号。
   * 执行并保留完整日志：Xcode 项目解析、iOS Simulator 构建、测试计划/自动化测试；能运行的测试均执行，新增测试前先说明覆盖范围。
   * 在真实 iPhone 安装并启动主应用和 Custom Keyboard Extension。不得把 Linux 静态检查写成 iOS 构建通过。
2. **键盘端到端**
   * 启用键盘及 Allow Full Access；在至少两个宿主应用验证普通输入、删除、空格、换行、Shift、123/ABC。
   * 验证键盘麦克风入口能打开主应用并开始录音；成功识别后返回键盘，识别文本通过 App Group 一次性传递并插入当前输入框，而不是只复制到剪贴板。
   * 覆盖拒绝麦克风权限、取消/失败识别、键盘切换和扩展重启等错误/恢复路径。录屏或截图需遮盖个人信息。
3. **服务集成与安全**
   * 在获授权的测试账号下验证豆包 ASR（默认优先）、阿里云/讯飞配置选择，以及 OpenAI-compatible LLM 的原文、智能优化、深度润色三种模式和连通性测试。
   * 保存经脱敏的请求/响应元数据、HTTP 状态和服务状态码；确认服务端失败不会显示原始响应正文。不要提交或评论密钥、访问令牌、音频原文或个人数据；只使用获批的 secret 配置。
   * 验证凭证在 Keychain 的读写/删除、App Group 待插入文本的生命周期与键盘 Full Access 限制；注明动态验证方法及结果。
4. **UI 与交付**
   * 提供主应用关键页面、键盘常态/录音状态的真实运行截图，并逐项对照官方 Typeless UI Reference；标明参考图和本项目运行图，不得把参考图冒充运行截图。
   * 检查 README、MIT 许可证、安全配置示例、Provider 配置、错误处理与 iOS 键盘录音限制是否与实际源码一致。
   * 报告发现的缺陷，提供复现步骤、日志/截图证据、影响和修复建议；结论逐项对应本任务清单及 KUB-20 标准。

## 完成条件

提交环境版本、命令与日志、设备端到端证据、真实 ASR/LLM 脱敏调用证据、UI 对照截图及逐项结论。任何因缺少 macOS runner、设备、源文件访问或获授权凭证而无法执行的测试，列为“未验证”并说明原因；不得推测通过。若现有环境不具备运行测试条件，请先报告阻塞和所需访问/资源，不要生成模拟证据或把 mock 标为真实调用。

## 源码仓库

* 新建的私有 GitHub 仓库：[ovws/OpenTypeless](<https://github.com/ovws/OpenTypeless>)。
* 已导入完整历史；`main` 当前 HEAD：`f7191c20226ac7815424ae84924a285d4aacd7fc`。远端 `refs/heads/main` 已核对为同一提交。
* Linear Agent 执行前，workspace admin 仍需启用 coding sessions 并确认 Agent 有权访问此私有仓库。原 `ovws/internal-ai-api-config#102` 是任务跟踪 issue，不是源码仓库。
* 检出方式：`git clone https://github.com/ovws/OpenTypeless.git`。
```

### 评论（1）

#### 评论 1

```json
{
  "index": 1,
  "id": 6077059782,
  "url": "https://github.com/ovws/issues/issues/102#issuecomment-6077059782",
  "author": "linear-code[bot]",
  "created_at": "2026-10-09T08:09:54Z",
  "updated_at": "2026-10-09T08:09:54Z",
  "author_association": "NONE",
  "reactions": {
    "total_count": 0,
    "plus_1": 0,
    "minus_1": 0,
    "laugh": 0,
    "hooray": 0,
    "confused": 0,
    "heart": 0,
    "rocket": 0,
    "eyes": 0
  }
}
```

```text
<!-- linear-linkback -->
<p><a href="https://linear.app/cvm/issue/WK-200/opentypeless-p0-运行验收按-linear-测试规范">WK-200</a></p>
```

---
