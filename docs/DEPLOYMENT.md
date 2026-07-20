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
.\scripts\install.ps1 -UpdateUpstreams
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
