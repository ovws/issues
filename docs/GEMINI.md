# Gemini 内网 OpenAI-compatible 服务

本页对应 Linear `WK-76`。服务入口为 `internal_ai_api.gemini_app:app`，默认监听
`0.0.0.0:8002`；Gemini Cookie 仅保存在服务器本地文件中，同事只获得各自的
`sk-internal-*` API Key。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/v1/models` | 返回当前账号实际发现的 Gemini 模型 |
| POST | `/v1/chat/completions` | 非流式文本和多轮消息 |
| POST | `/v1/images/generations` | 图片生成，支持 URL 或 `b64_json` |
| POST | `/v1/images/edits` | `multipart/form-data` 单图或多图编辑 |
| POST | `/v1/videos` | 提交异步视频任务 |
| GET | `/v1/videos/{task_id}` | 查询视频任务 |
| GET | `/v1/videos/{task_id}/content` | 下载已完成视频 |

`/docs` 和 `/openapi.json` 可直接供 OpenAPI 工具导入。OpenAPI 定义包含 HTTP Bearer
安全方案以及明确的聊天、图片和视频请求 schema。`stream=true` 和工具调用当前明确返回
`400 unsupported`，避免客户端误以为请求已被完整执行。

视频生成默认使用 `GEMINI_VIDEO_MODEL=gemini-3-pro`，与上游 Gemini-API 的视频能力要求
一致；文本与图片继续使用 `GEMINI_DEFAULT_MODEL=gemini-3-flash`。调用方仍可在请求体中显式
指定模型。

## Cookie 与账号检查

1. 将 `config/gemini-cookies.example.json` 复制为
   `config/gemini-cookies.local.json`。
2. 只在服务器本机填写 `__Secure-1PSID` 和 `__Secure-1PSIDTS`。
3. 运行 `scripts/protect-local-data.ps1` 限制本地 ACL。
4. 启动后读取 `GET /health`。`account` 字段会记录账号状态、地区/权限状态、可用模型、
   能力等级、Cookie 文件更新时间和最近一次刷新时间，但不会返回 Cookie。

服务默认每 600 秒主动轮换 Cookie，并以临时文件加原子替换方式持久化。可通过
`GEMINI_REFRESH_INTERVAL_SECONDS` 调整，最小有效间隔为 60 秒。
上游 SDK 的轮换缓存被定向到 Gemini 独立媒体目录下的 `.cookie-cache`，不会写到用户级
临时目录；`protect-local-data.ps1` 会与其他 Gemini 数据一起限制其 ACL。

- Cookie 刷新无结果、401、403 或未认证状态会立即打开鉴权熔断并关闭 Gemini 会话；
  队列停止派发，恢复 Cookie 后必须重启 Gemini 服务。
- 429、IP 临时封禁或账号用量限制会暂停 Gemini 队列，不会换号，也不会自动重放；
  管理员确认配额和账号状态后重启 Gemini 服务。
- Grok 和 ChatGPT 图片服务使用独立进程、SQLite、队列、日志和端口，不受 Gemini
  熔断或暂停影响。

## 视频幂等提交

视频调用方应在 `POST /v1/videos` 中携带稳定的 `Idempotency-Key`：

```http
Idempotency-Key: project-42-shot-7-v1
```

服务仅保存该值的 SHA-256 摘要。同一 API Key、同一路径和同一幂等键只创建一个任务；
重复请求返回相同 `id`，并设置 `idempotent_replay: true`。任务状态统一映射为
`queued`、`in_progress`、`completed` 或 `failed`。

## 独立容器部署与内网接入

```powershell
Copy-Item config/gemini.env.example config/gemini.local.env
Copy-Item config/gemini-cookies.example.json config/gemini-cookies.local.json
.\scripts\prepare-gemini-container.ps1
.\scripts\protect-local-data.ps1
docker compose -f compose.gemini.yml build
docker compose -f compose.gemini.yml up -d
docker compose -f compose.gemini.yml ps
```

镜像只包含根 FastAPI 兼容层和固定版本的 `HanaokaYuzu/Gemini-API` 检出。Compose 不读取
根 `.env`，因此不会把 Grok 或 ChatGPT 凭据注入 Gemini 容器；Cookie、SQLite/媒体和日志
分别使用服务器绑定文件、`internal-ai-gemini-data` 与 `internal-ai-gemini-logs`。根文件系统
只读，临时目录使用受限 `tmpfs`，容器以非 root 用户运行。

为同事生成独立密钥：

```powershell
docker compose -f compose.gemini.yml exec gemini-api `
  internal-ai-key --platform gemini create --owner "同事姓名" --department "部门"
```

由公司 IT 为服务器分配固定 IP 或 DHCP 保留地址，并将
`gemini-api.internal` 解析到该地址。确认公司 CIDR 后，以管理员身份运行：

```powershell
.\scripts\configure-firewall.ps1 -LanCidr 192.168.10.0/24
```

然后从另一台公司电脑验证：

```powershell
$headers = @{ Authorization = 'Bearer sk-internal-...' }
Invoke-RestMethod http://gemini-api.internal:8002/health
Invoke-RestMethod http://gemini-api.internal:8002/v1/models -Headers $headers
```

若公司反向代理把 `http://gemini-api.internal/v1` 转发到 `8002`，客户端使用无端口的
目标 Base URL；否则使用 `http://<固定内网 IP>:8002/v1`。DNS、固定 IP 和反向代理由
公司 IT 按内部规范配置，仓库不会猜测或占用地址。

若目标机暂时不能使用 Docker，仓库仍保留
`.\scripts\start-service.ps1 -Service gemini` 的 Windows 原生应急运行方式；WK-76 的正式
隔离部署以 `compose.gemini.yml` 为准。

需要让原生服务随登录常驻时，以实际运行服务的 Windows 账户打开 PowerShell：

```powershell
# 如凭据目录曾由其他账户初始化，先在管理员 PowerShell 中补齐运行账户权限
.\scripts\grant-gemini-runtime-access.ps1

# 注册并立即启动仅包含 Gemini 的登录任务
.\scripts\register-gemini-task.ps1

# 日常查看、停止与启动
Get-ScheduledTask -TaskName 'Internal AI API - Gemini'
Stop-ScheduledTask -TaskName 'Internal AI API - Gemini'
Start-ScheduledTask -TaskName 'Internal AI API - Gemini'
```

计划任务以普通用户权限运行，不会连带启动 Grok 或 ChatGPT 图片服务。启动诊断写入
`logs/gemini/task-bootstrap.log`，业务日志写入 `logs/gemini/service.log`。

## 验收记录

在目标电脑完成以下项目后，再关闭 WK-76：

| 项目 | 结果 | 耗时/备注 |
| --- | --- | --- |
| Cookie 初始化、持久化、自动刷新 | 本机通过 | 登录可用；刷新时间与文件更新时间已更新，未记录值 |
| 文本单轮与多轮 | 本机通过 | Flash 实测精确返回预期内容；多轮由自动化回归覆盖 |
| 图片生成 URL / Base64 | 本机部分通过 | URL 实测 58,196-byte JPEG；Base64 由自动化回归覆盖 |
| 单图、多图编辑 | 本机部分通过 | 单图实测 49,168-byte JPEG；多图由自动化回归覆盖 |
| 视频提交、重复提交、轮询、下载 | 上游阻塞 | 幂等 ID 与轮询通过；Google 静默中止，尚无产物可下载 |
| 账号套餐、地区与模型权限 | 本机通过 | `AVAILABLE`；Flash/Pro 可用；视频能力仍受上游限制 |
| 常用 Agent 文本与图片调用 | 待现场验证 | 记录客户端名称和版本 |
| OpenAPI 工具导入 | 待现场验证 | 导入 `/openapi.json` |
| 另一台公司电脑访问与防火墙边界 | 待现场验证 | 记录网段，不记录个人信息 |

自动化回归命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
```
