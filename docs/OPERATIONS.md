# 运维、停止与登录恢复

## 日常命令

```powershell
.\scripts\status.ps1
.\scripts\health-check.ps1
.\scripts\restart-all.ps1 -Service grok
.\scripts\stop-all.ps1
```

本机也可打开 `http://127.0.0.1:8090` 查看三平台状态、密钥和审计；页面中的“重启 / 恢复”只
操作所选平台。

PID 文件记录启动时间；停止脚本检测 PID 重用，避免误杀无关进程。日志按平台分开保存在 `logs/<platform>`。网关日志按天轮转，默认保留 14 个文件；Gemini 媒体默认保留 7 天，清理周期为 1 小时。

## 故障隔离

每个平台有独立数据库、队列、日志和受管进程。停止一个平台只操作对应 PID 文件，不会停止另两个平台。上游进程绑定环回地址，网关绑定局域网地址。

服务启动时，平台 SQLite 中遗留的 `queued`/`running` 任务统一标记 `interrupted`，不会自动重放。调用方应检查业务结果后决定是否重新提交。

## Grok 登录态恢复

1. `stop-service.ps1 -Service grok`。
2. 只在服务器本机启动上游并访问本地管理端。
3. 检查 Provider 账号状态；对 Web/Console SSO 重新授权。Build OAuth 按上游流程续期。
4. 验证上游本机 `/v1/models`，再启动网关。
5. 用内部测试密钥执行一条低成本请求。

不要把上游 `g2a_` 客户端密钥或管理员 Token 发给同事。

## Gemini Cookie 恢复

1. `stop-service.ps1 -Service gemini`。
2. 在服务器浏览器正常登录 `gemini.google.com`。
3. 按上游说明重新取得 `__Secure-1PSID`、`__Secure-1PSIDTS`，更新 `config/gemini-cookies.local.json`。
4. 启动 Gemini；`/health` 必须从 `degraded` 变为 `ok`。
5. 验证 `/v1/models` 与非流式文本请求。

## ChatGPT 图片登录态恢复

1. `stop-service.ps1 -Service chatgpt-image`。
2. 在本机上游管理端检查账号状态，按获准方式重新登录或导入。
3. 不启用自动换号、验证码绕过或未获批准的代理池。
4. 启动服务并先验证 `/v1/models`，再做单图生成。

## 备份与回滚

备份前先停止服务。至少保留 `.env`、`config/*.local.*`、`upstream/grok2api/config.yaml`、平台数据目录和根仓库 commit。备份介质应加密并限制访问。

回滚时检出已验收的根仓库 commit，并把每个上游检出恢复到 `docs/UPSTREAM-AUDIT.md` 记录的 commit。不要只回滚编排层而保留未经验证的新上游。
