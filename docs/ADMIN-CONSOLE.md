# 三平台本机管理台

管理台以 WK-78 的鉴权和运行风控为中心，把 Grok、Gemini、ChatGPT 图片的状态、个人密钥、
独立启停、队列熔断和审计记录放在同一个页面。它固定监听 `127.0.0.1:8090`，不会发布到公司
局域网，也不会代理任何上游管理页面。

## 启停与访问

```powershell
.\scripts\start-admin.ps1
Start-Process http://127.0.0.1:8090

.\scripts\stop-admin.ps1
```

`start-all.ps1`、`stop-all.ps1` 和登录时计划任务已经包含管理台。端口可通过
`INTERNAL_AI_ADMIN_PORT` 修改，但监听地址在启动脚本中固定为回环地址。应用层还会检查客户端
地址；即使误把进程绑定到其他网卡，非回环请求也返回 403。

## 可以执行的操作

- 同时查看三个平台的在线、暂停或离线状态，以及运行中和排队任务数；
- 单独启动、停止或重启某个平台；重启是熔断原因处理完毕后的显式恢复方式；
- 按人员和平台创建、停用、启用、轮换和永久删除 API Key；Grok 调用原生 Client Key API，ChatGPT 调用原生 User Key API，Gemini 使用网关 Key；
- 永久删除只对已停用密钥开放，删除前需要再次确认，审计记录继续保留；
- 查看最近任务元数据和管理动作审计，不展示请求正文、Cookie 或上游凭据；
- 新密钥和轮换密钥的明文只显示一次，关闭提示框后无法找回。

所有改变状态的 HTTP 请求都要求页面启动时取得的同源动作令牌。管理台不启用 CORS，并发送
严格的 CSP、`frame-ancestors 'none'` 和 `no-store`，用于降低本机浏览器受到跨站请求诱导的风险。

## 持久化选择

管理台不建立共享数据库。Grok/ChatGPT 密钥由各自上游原生存储管理；三个网关 SQLite 继续保存任务、幂等和审计数据，其中只有 Gemini SQLite 保存网关 Key：

```text
data/grok.db
data/gemini.db
data/chatgpt-image.db
```

三份文件保存任务元数据、幂等键摘要和最近 500 条管理审计；`gemini.db` 另存网关 Key 的
PBKDF2 盐和摘要。它们不保存个人密钥明文、请求正文、图片 Base64、网页登录凭据或 Cookie。

备份和恢复必须在对应平台停止后进行。三个数据库文件均位于受 ACL 保护且不提交 Git 的
`data/`。ChatGPT2API 和 Grok 上游自己的存储位于各自回环隔离运行目录；8090 只从本机服务端
调用其受保护管理 API，不把管理 API 暴露到局域网。
