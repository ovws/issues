# ChatGPT 图片内网兼容服务（WK-77）

本页对应 Linear `WK-77`。正式入口定位为 **ChatGPT 图片 API**，只宣传图片生成、图片编辑
以及上游明确支持的图片兼容场景，不把它描述为通用文本 ChatGPT 服务。

```text
首选 Base URL：http://chatgpt-image.internal/v1
备用 Base URL：http://<内网固定IP>:8003/v1
```

首选域名需要公司 DNS 和反向代理把 `chatgpt-image.internal:80` 转发到部署机 `8003`；若尚未
配置反向代理，客户端直接使用固定内网 IP 与端口。仓库不会自动修改公司 DNS。

## 架构与边界

内存受限的 Windows 部署机以两个本地 Python 进程为正式方案：

1. `chatgpt-image-upstream`：固定检出的 `basketikun/chatgpt2api`，只监听
   `127.0.0.1:18003`，供管理员在服务器本机登录和恢复账号。
2. `chatgpt-image-api`：公司 OpenAI-compatible 网关，发布 `8003`，保存个人 API Key 哈希、
   FIFO 任务状态和脱敏日志，只通过环回地址调用上游。

两个进程使用独立虚拟环境、端口、凭据、数据目录、日志和 PID 文件。停止 ChatGPT 图片服务
不会停止 Grok 或 Gemini。Docker Compose 保留为可选的强隔离部署方式，不是低内存机器的
前置条件。

## 首次部署

前提：Windows 10/11、Node.js/npm、根项目虚拟环境，以及公司 IT 已确认法务与信息安全允许
使用该上游，并为部署机分配固定 IP 或 DHCP 保留地址。

```powershell
# 安装项目内 Python 3.13、上游依赖和本机管理前端；主密钥不会打印
.\scripts\prepare-chatgpt-image-native.ps1 `
  -PublicBaseUrl http://<固定内网IP>:8003

# 限制 .env、config、data、logs 的本机 ACL
.\scripts\protect-local-data.ps1

.\scripts\start-service.ps1 -Service chatgpt-image
.\scripts\status.ps1
```

确认手动启停正常后，可注册只启动 ChatGPT 图片平台的登录任务，不会连带启动 Grok/Gemini：

```powershell
.\scripts\register-chatgpt-image-task.ps1
```

若不使用域名，把 `PublicBaseUrl` 设置为 `http://<固定内网 IP>:8003`。该值不能带 `/v1`，
因为上游用它生成 `/images/...` 下载 URL。

本地生成且不提交的数据：

| 文件 | 用途 |
| --- | --- |
| `.env` | 上游主密钥、公开图片 origin、端口、超时和熔断阈值 |
| `upstream/chatgpt2api/config.json` | 上游单并发、账号与图片保存策略 |
| `upstream/chatgpt2api/data` | 上游账号、图片与 SQLite 数据 |
| `data/chatgpt-image.db` | 个人 Key 哈希和网关任务记录 |
| `logs/chatgpt-image` | 上游、网关和脱敏业务日志 |

准备脚本强制 `image_account_concurrency=1`、`image_parallel_generation=false`，关闭限流账号自动删除、
无效账号自动删除、自动重新登录、代理运行时和第三方画布入口。不配置账号池轮换或验证码绕过。

## 本机账号初始化与个人密钥

只在部署服务器浏览器打开 `http://127.0.0.1:18003`，完成获准账号的登录/导入。不要把该
地址映射到局域网，也不要把 `CHATGPT2API_AUTH_KEY` 发给同事。

每位同事单独创建网关密钥：

```powershell
.\.venv\Scripts\python.exe .\scripts\generate-api-key.py `
  --platform chatgpt-image create --owner "同事姓名" --department "部门"
```

数据库仅保存随机盐与 PBKDF2-SHA256 派生值；明文个人密钥只显示一次。停用离职或异常密钥：

```powershell
.\.venv\Scripts\python.exe .\scripts\generate-api-key.py --platform chatgpt-image list

.\.venv\Scripts\python.exe .\scripts\generate-api-key.py `
  --platform chatgpt-image disable <key_id>
```

## 接口与客户端接入

| 方法 | 路径 | 第一阶段验证范围 |
| --- | --- | --- |
| GET | `/v1/models` | 返回上游当前图片模型 |
| POST | `/v1/images/generations` | `n`、`size`、URL / `b64_json` |
| POST | `/v1/images/edits` | multipart 单图、多图与可选 mask |
| POST | `/v1/chat/completions` | 只验证上游支持的图片兼容请求 |
| POST | `/v1/responses` | 只验证上游支持的图片兼容请求 |

客户端选择 `OpenAI Compatible`，填首选或备用 Base URL、个人 `sk-internal-*` 密钥，并从
`GET /v1/models` 选择图片模型。不要把本服务设为团队默认通用聊天 Provider。

最小探测：

```powershell
$headers = @{ Authorization = 'Bearer sk-internal-...' }
Invoke-RestMethod http://chatgpt-image.internal/v1/models -Headers $headers

$body = @{
  model = 'gpt-image-2'
  prompt = '一只放在白色桌面上的蓝色陶瓷杯，产品摄影'
  n = 1
  size = '1024x1024'
  response_format = 'url'
} | ConvertTo-Json
Invoke-RestMethod http://chatgpt-image.internal/v1/images/generations `
  -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

图片 URL 返回指向同一个局域网 origin 的 `/images/...`，网关只公开该只读路径，不公开
`/api/accounts`、`/api/settings` 等管理接口。Base64 内容只在响应中转发，不写入任务表或
网关日志。

## 单并发、超时与停止规则

所有生成、编辑、chat 和 responses POST 请求进入 ChatGPT 平台自己的单 worker FIFO。
默认图片生成超时 15 分钟、编辑 20 分钟、文本兼容场景 5 分钟；超时不自动重试。

- 上游返回 401、403 或 429：当前任务失败，平台立即进入 `paused`，等待队列被标记失败并
  返回 503，必须通知管理员。
- 上游连续 3 次返回 5xx 或发生传输错误：同样进入 `paused`。任意成功响应会清零连续失败
  计数。
- `/health` 在熔断时返回 `status=paused`、`operator_action_required=true` 和脱敏原因。
- 恢复账号、额度或网络后重启该平台；服务不会自动换号、自动重放或自行解除暂停。

```powershell
Get-Content -Tail 100 .\logs\chatgpt-image\service.log
.\scripts\restart-all.ps1 -Service chatgpt-image
```

## 登录态恢复

1. 停止平台：`.\scripts\stop-service.ps1 -Service chatgpt-image`。
2. 只在服务器本机打开 `http://127.0.0.1:18003`，检查账号状态；对 401/403 重新登录，对
   429 等待额度/限流恢复并人工确认。
3. 不启用账号池自动轮换、自动重新登录、验证码/Cloudflare 绕过或代理池。
4. 启动网关，先用管理员自己的个人测试 Key 调 `/v1/models`，再执行一条低成本图片请求。
5. 确认 `/health` 为 `ok`；若仍为 `paused`，检查日志后再次停止，不连续突发提交。

## 指标与验收记录

查看最近 100 个任务的成功率、平均执行耗时、最长连续成功次数、状态和端点分布：

```powershell
.\.venv\Scripts\python.exe -m internal_ai_api.reporting `
  --platform chatgpt-image --limit 100
```

## 可选 Docker 部署

目标机资源充足且需要更强隔离时，可改用
`prepare-chatgpt-image-container.ps1` 与 `compose.chatgpt-image.yml`。原生与 Docker 模式不得
同时启动，以免占用相同的 `8003/18003` 端口。

自动化已经覆盖路由、个人密钥隔离、URL/Base64 透传、多图 multipart、单 worker、超时、
401/403/429 熔断、连续失败熔断和日志脱敏。以下项目必须在目标公司电脑与真实获准账号上记录：

| 项目 | 结果 | 耗时/备注 |
| --- | --- | --- |
| 固定 IP、DNS、反向代理、公司 CIDR 防火墙 | 待现场 | 记录配置责任人，不记录敏感网段到公开仓库 |
| `/v1/models` 返回图片模型 | 待现场 | 记录模型 ID 与日期 |
| 文生图 URL、Base64、数量与尺寸 | 待现场 | 各保存一份非敏感样例 |
| 单图编辑 | 待现场 | 记录输入数、输出格式、耗时 |
| 多图编辑 | 待现场 | 至少两张输入，记录耗时 |
| chat / responses 图片兼容场景 | 待现场 | 只记录项目实际支持场景 |
| 常用 Agent 或图片客户端接入 | 待现场 | 记录客户端名称、版本和 Provider 配置 |
| 两个并发请求 FIFO | 待现场 | 第二个必须等待第一个完成 |
| 401/403/429 与连续失败人工恢复 | 待现场 | 验证 paused、通知与重启步骤 |
| 停止 ChatGPT 后 Grok/Gemini 不受影响 | 待现场 | 分别探测另外两个 `/health` |
| 最近 100 个任务指标 | 待现场 | 保存脱敏 JSON 或内部运维记录 |

真实账号、公司 DNS、防火墙和客户端现场项全部通过前，不应把 WK-77 标记为完成。
