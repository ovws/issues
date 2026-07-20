# 公司内网 AI OpenAI 兼容 API

本项目对应 Linear `WK-80`，用于在一台公司 Windows 电脑上以本地原生进程运行三套相互独立的 AI 服务：

| 平台 | 局域网 Base URL | 本地上游 | 主要能力 |
| --- | --- | --- | --- |
| Grok | `http://<内网IP>:8001/v1` | `127.0.0.1:18001` | 文本、图片、编辑、视频 |
| Gemini | `http://<内网IP>:8002/v1` | 本进程内 `Gemini-API` SDK | 文本、图片、编辑、视频 |
| ChatGPT 图片 | `http://<内网IP>:8003/v1` | `127.0.0.1:18003` | 图片生成、多图编辑、有限文本场景 |

上游管理页面与凭据只在本机环回地址上可用。局域网端口由本项目网关占用，统一实施每平台 FIFO 单并发队列、独立 SQLite 任务状态、超时保护和日志脱敏。本机管理台位于 `http://127.0.0.1:8090`：Grok/ChatGPT 密钥直接写入上游原生后台并由上游鉴权，Gemini 因没有原生 Key 系统而使用网关密钥。

部署脚本默认从 `ovws/internal-ai-grok2api`、`ovws/internal-ai-gemini-api`、`ovws/internal-ai-chatgpt2api` 三个私有镜像拉取固定 commit；原始开源上游地址保留在 `config/upstreams.json` 的 `upstream` 字段中用于审计。

## 快速开始

需要 Windows 10/11、PowerShell 5.1+、Git、`uv`、Python 3.13、Node.js/pnpm，以及 Grok 当前版本要求的 Go 1.26。所有项目文件、虚拟环境、上游源码、数据和日志均位于本项目目录内。

```powershell
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

随后完成以下本机配置：

1. 编辑 `.env`，设置 Grok 与 ChatGPT2API 的本地上游密钥。
2. 将 `config/gemini-cookies.example.json` 复制为 `config/gemini-cookies.local.json`，只在本机填写 Gemini Cookie。
3. 编辑 `upstream/grok2api/config.yaml`，替换所有标记为“必须修改”的管理员和加密密钥。
4. 分别在 Grok、ChatGPT2API 本地管理端导入获准使用的账号凭据。
5. 启动服务，在服务器本机打开 `http://127.0.0.1:8090`，为同事生成各平台独立密钥。Grok 和 ChatGPT 会写入真实上游；Gemini 写入网关数据库。CLI 仅保留给 Gemini 应急管理：

```powershell
.\.venv\Scripts\python.exe .\scripts\generate-api-key.py --platform gemini create --owner "张三" --department "设计部"
```

明文密钥只显示一次。Gemini SQLite 只保存盐和 PBKDF2 哈希；Grok/ChatGPT 的 Key 元数据和哈希由各自上游保存。

```powershell
.\scripts\start-all.ps1
.\scripts\status.ps1
.\scripts\health-check.ps1
```

单独管理服务：

```powershell
.\scripts\start-service.ps1 -Service gemini
.\scripts\stop-service.ps1 -Service gemini
.\scripts\restart-all.ps1 -Service gemini
```

## 客户端配置

```text
Provider: OpenAI Compatible
Base URL: http://<本机内网IP>:8001/v1
API Key: <从 8090 为该平台创建的个人密钥>
Model: 通过 GET /v1/models 获取
```

Gemini 和 ChatGPT 图片只需改为端口 `8002`、`8003`，并使用对应平台的个人密钥。

## 目录

```text
config/                 本地凭据模板与上游配置说明
data/                   网关 SQLite 与 Gemini 媒体（不提交）
docs/                   部署、安全、接口、运维和验收文档
logs/                   每个平台独立日志（不提交）
run/                    受管进程 PID 记录（不提交）
scripts/                安装、启停、健康检查、防火墙、自启动、密钥管理
src/internal_ai_api/    共享基础层和三个服务入口
tests/                  鉴权、持久化、FIFO、超时、脱敏与清理测试
upstream/               三个独立上游 Git 仓库（根项目忽略）
```

## 安全与适用范围

- 仅供经公司授权的局域网低并发使用，不开放公网，不提供规避验证码、风控或账号限制的功能。
- `.env`、Cookie、本地数据库、日志、媒体和上游检出目录不会进入根 Git 仓库。
- `scripts/configure-firewall.ps1 -LanCidr <公司网段>` 只接受 RFC1918 网段；需管理员自行执行。
- 上游均属于非官方网页接口实现，可能随登录态、网页接口或服务条款变化失效。
- ChatGPT2API 当前 README 明确限制商业、批量、盈利和规模化用途。公司内部使用前必须由法务/信息安全确认许可和 OpenAI 服务条款；未确认前不得上线。

详见 [部署说明](docs/DEPLOYMENT.md)、[三平台本机管理台](docs/ADMIN-CONSOLE.md)、[API 与错误码](docs/API.md)、[运维恢复](docs/OPERATIONS.md)、[安全与上游风险](docs/SECURITY.md) 和 [现场验收清单](docs/ACCEPTANCE.md)。
