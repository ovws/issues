# Windows 本地部署

## 1. 环境确认

在目标公司电脑执行：

```powershell
.\scripts\environment-check.ps1
```

最低建议为 4 核 CPU、8 GB 内存、100 GB 可用 SSD；无需本地 GPU。当前上游实际要求如下：

- Grok2API：Go 1.26；管理前端构建还需要 Node.js 与 pnpm。
- Gemini-API：Python 3.10+；本项目统一使用 Python 3.13。
- ChatGPT2API：Python 3.13。
- 编排层：Python 3.11+，安装脚本统一选择 3.13。

向公司 IT 申请 DHCP 保留地址或按公司规范设置固定 IPv4。不要自行占用未经分配的静态地址。

## 2. 项目内安装

所有内容保存在项目树中：根虚拟环境为 `.venv`，ChatGPT2API 虚拟环境位于其上游目录，三个上游检出位于 `upstream`。安装脚本还把 uv Python、uv/npm/pnpm/Go 构建缓存分别定向到项目内的隐藏目录，不写入用户级缓存目录。

```powershell
Copy-Item .env.example .env
.\scripts\install.ps1
```

可选参数：

```powershell
.\scripts\install.ps1 -SkipGrokBuild
.\scripts\install.ps1 -SkipChatGPTFrontend
```

生产变更前不要直接更新上游。先记录 commit，在测试机执行回归测试，再更新现场版本。

## 3. 凭据配置

### Grok

安装脚本从上游模板生成 `upstream/grok2api/config.yaml` 并把监听地址改为 `127.0.0.1:18001`。必须替换：

- `secrets.jwtSecret`
- `secrets.credentialEncryptionKey`
- `bootstrapAdmin.password`

首次登录后在本机管理端导入授权账号，创建只供网关使用的 Grok 客户端密钥，并写入 `.env` 的 `GROK_UPSTREAM_API_KEY`。不要把上游管理密钥发给同事。

在 Grok 本机管理端的运行设置中，将公开 API Base URL 设置为 `http://<服务器内网IP>:8001`，使图片/视频链接经过局域网网关；不要填 18001。

### Gemini

```powershell
Copy-Item .\config\gemini-cookies.example.json .\config\gemini-cookies.local.json
```

在本机填写 `__Secure-1PSID` 与 `__Secure-1PSIDTS`。文件被 Git 忽略。服务会在 Cookie 刷新后原子范围内重写这两个字段；不要将 Cookie 放入 `.env`、README 或工单评论。

### ChatGPT 图片

在 `.env` 设置一个长随机 `CHATGPT_IMAGE_UPSTREAM_API_KEY`，并把 `CHATGPT_IMAGE_PUBLIC_BASE_URL` 设置为 `http://<服务器内网IP>:8003`。启动脚本仅把上游密钥注入本地进程，同时网关用同一密钥访问 `127.0.0.1:18003`。账号导入在本机上游后台完成。

三个平台凭据配置完成后执行 `.\scripts\protect-local-data.ps1`，将本地凭据、数据库与日志 ACL 限制为当前用户、SYSTEM 和本机 Administrators。若计划任务改用其他服务账号，必须先把该账号加入 ACL。

## 4. 启动与首个个人密钥

```powershell
.\scripts\start-all.ps1
.\scripts\status.ps1
.\scripts\health-check.ps1
```

服务器本机打开 `http://127.0.0.1:8090` 创建三把独立密钥。Grok/ChatGPT 密钥会直接写入对应
上游原生后台，Gemini 密钥写入网关数据库；明文均只显示一次。管理台也可轮换、停用密钥并执行
单平台启停与恢复，不能从其他公司电脑访问。

### Windows 一键启动

`start-ai-api.bat` 面向已完成三套服务安装和凭据配置的 Windows 服务器。它不会替代首次部署：Grok 使用已安装的本地二进制和网关，Gemini 与 ChatGPT Image 使用各自的本地 Python 环境，同时启动仅监听 `127.0.0.1:8090` 的管理工具；整个启动流程不需要 Docker。首次使用前完成：

```powershell
Copy-Item .\config\gemini-cookies.example.json .\config\gemini-cookies.local.json
.\scripts\install.ps1
```

填写 Gemini Cookie 并确认本地主密钥配置后，双击 `start-ai-api.bat`，或在命令行执行：

```cmd
set AI_API_NO_PAUSE=1
start-ai-api.bat -StartupTimeoutSeconds 180
```

脚本执行顺序如下：

1. 检查三套服务和管理工具的本地可执行文件、Python 环境、配置文件，以及数据/日志目录和现有 SQLite 文件是否可写。
2. 探测 8001、8002、8003、8090；健康服务标记为“已运行”，被其他进程占用的端口仅阻止对应项目。
3. 幂等启动每个平台；单个平台失败时继续处理后续平台。
4. 优先检查 `/health`，端点不存在或需要鉴权时回退 `/v1/models`。回退鉴权仅从 `AI_API_<平台>_HEALTH_KEY` 进程环境变量读取个人密钥，控制台不打印密钥。
5. 显示状态、Base URL 和日志位置；全部成功返回 0，任一失败返回 1。

脚本默认使用 BAT 所在项目目录。如果 BAT 位于不含本地运行资产的 linked worktree，它会通过 Git common directory 自动找到主工作树。也可显式指定：

```cmd
start-ai-api.bat -RuntimeRoot D:\WEB2API
```

仅执行启动前检查：

```cmd
set AI_API_NO_PAUSE=1
start-ai-api.bat -PreflightOnly
```

常见故障：

| 现象 | 处理 |
| --- | --- |
| 本地可执行文件或 Python 环境缺失 | 重新运行 `scripts\install.ps1`，并按具体缺失路径检查安装结果 |
| 配置文件缺失或仍为占位值 | 按报错路径补齐本地配置；不要把凭据内容粘贴到日志或工单 |
| 目录或 SQLite 文件不可写 | 使用实际部署账号修复报错路径的 ACL；不要删除现有数据库来绕过权限问题 |
| 端口已被非健康服务占用 | 用 `Get-NetTCPConnection -LocalPort <端口>` 定位进程，确认归属后再停止或改端口 |
| 健康检查超时 | 按汇总中的本地日志目录查看日志；只修复失败平台，不停止另外两个平台 |
| `/v1/models` 返回 401/403 | 使用该平台的个人 API Key 设置本次进程的健康检查变量，禁止使用项目主密钥 |

若历史 SQLite 或缓存文件的 ACL 已损坏，普通终端无法接管时，在“以管理员身份运行”的 PowerShell 中执行：

```powershell
powershell -ExecutionPolicy Bypass -File `
  D:\WEB2API-WK81\scripts\repair-runtime-permissions.ps1 `
  -RuntimeRoot D:\WEB2API
```

该脚本仅重设 ChatGPT 网关数据库、ChatGPT2API 数据目录、ChatGPT 日志和 Gemini 缓存的 ACL，不读取、删除或替换数据库内容。修复后重新运行 `start-ai-api.bat`。

## 5. 防火墙与开机启动

由管理员在确认公司局域网 CIDR 后执行：

```powershell
.\scripts\configure-firewall.ps1 -LanCidr 192.168.10.0/24
.\scripts\register-startup-task.ps1
```

防火墙脚本只接受 RFC1918 IPv4 CIDR，只开放 TCP 8001–8003 的 Domain/Private 入站访问。18001、18003、8090 与管理后台保持环回监听，不创建防火墙规则。

## 6. 其他电脑验证

```powershell
Invoke-RestMethod http://<服务器内网IP>:8001/health
Invoke-RestMethod http://<服务器内网IP>:8002/health
Invoke-RestMethod http://<服务器内网IP>:8003/health
```

`/v1/models` 需要对应平台个人 Bearer 密钥。完成后在 Cherry Studio 新增三个 OpenAI Compatible Provider。
