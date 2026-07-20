# WK-80 验收清单

ChatGPT 图片平台的 WK-77 专属容器、熔断、接入与现场记录见
[`CHATGPT-IMAGE.md`](CHATGPT-IMAGE.md)。

## 已由仓库自动化验证

- [x] 三个平台使用独立设置、SQLite、队列、日志和启动入口。
- [x] API Key 只保存盐和 PBKDF2 哈希，支持启用/停用、到期和最后调用时间。
- [x] 每个平台 FIFO 单 worker；队列满返回 429。
- [x] 成功、失败或超时后 worker 继续下一任务。
- [x] `execution_id` 条件更新阻止迟到结果覆盖超时终态。
- [x] 重启时遗留 queued/running 任务标记 interrupted，不自动重复执行。
- [x] 日志过滤 Authorization、Cookie、Token、API Key 和长 Base64。
- [x] 大请求与 Gemini 编辑上传使用项目内临时文件排队，并限制为默认 32 MiB。
- [x] 媒体清理限制在配置目录内。
- [x] 三个 FastAPI 应用可生成 `/docs` 和 `/openapi.json`。
- [x] PowerShell 提供安装、独立/全部启停、重启、状态、健康、防火墙和开机任务脚本。
- [x] `ruff` 检查通过；12 个单元/异步/接口测试通过。

## 必须在目标公司电脑现场完成

- [ ] 记录 Windows、CPU、内存、磁盘、Git、Python、Node、pnpm、Go 版本。
- [ ] 由 IT 确认固定/DHCP 保留内网 IP 与允许的 CIDR。
- [ ] 完成 Grok Go 1.26 构建与本机账号导入。
- [ ] 完成 Gemini Cookie 登录并确认 `/health` 为 `ok`。
- [ ] 完成 ChatGPT2API 账号导入；法务/信息安全先批准其使用限制。
- [ ] 验证三个 `/v1/models`。
- [ ] 验证 Grok chat、responses、图片生成、图片编辑、视频提交/查询/下载。
- [ ] 验证 Gemini chat、图片生成、单图/多图编辑、视频提交/查询/下载。
- [ ] 验证 ChatGPT 图片生成、单图/多图编辑及项目支持的 chat/responses 场景。
- [ ] 两个以上并发请求验证 FIFO；队列满验证 429。
- [ ] 人工制造失败和超时，确认下一任务执行且迟到结果不改终态。
- [ ] 停止每个平台一次，确认另外两个不受影响。
- [ ] 从另一台公司电脑验证防火墙、`/health`、`/v1/models`。
- [ ] 在 Cherry Studio 完成三个 Provider 的 Base URL、个人密钥和模型加载测试。
- [ ] Windows 重启后验证计划任务自动恢复。
- [ ] 抽查 SQLite 与日志，确认无完整密钥、Cookie 或上传 Base64。

只有现场项全部通过后，才能把 WK-80 标记为完成。当前仓库交付的是可部署实现与自动化验证，不代表账号、网络和上游服务已经生产验收。
