# 上游核对记录

核对日期：2026-07-20。检出均位于项目内 `upstream` 目录。

| 项目 | Commit | Commit 时间 | 实际运行环境 | 许可证 |
| --- | --- | --- | --- | --- |
| chenyme/grok2api | `d74b15396686ae68b88c5a52e4e538d058c41d98` (`v3.0.5`) | 2026-07-20 | Go 1.26 + React 19 管理端 | MIT |
| HanaokaYuzu/Gemini-API | `fbe0790599ac8ee77692dabdce88a96110a33294` | 2026-04-13 10:50 -05:00 | Python 3.10+ SDK | AGPL-3.0 |
| basketikun/chatgpt2api | `1f96b49b2bf35e607a2c587e3fb9d40c5acb475d` | 2026-07-05 12:04 +08:00 | Python 3.13 + 可选前端 | MIT + README 使用限制 |

## 与 WK-80 原描述的差异

1. Grok2API 主分支已不是旧版 Python/Granian 应用，而是 Go 网关；安装脚本按 Go 源码构建。
2. Grok 视频创建的当前上游路径为 `/v1/videos/generations`；公司网关提供 `/v1/videos` 别名。
3. Gemini-API 仍是 SDK，不直接提供 OpenAI API；本仓库通过 `tool.uv.sources` 固定使用项目内检出，而不是不受控地安装 PyPI 最新版。
4. ChatGPT2API 当前要求 Python 3.13，本地运行用 Uvicorn 显式绑定 18003。
5. ChatGPT2API README 的额外限制可能阻止公司内部规模化使用，必须在上线前解决。

更新任何上游后重新执行：静态检查、单元测试、接口契约测试、登录恢复、单图/多图/视频和 FIFO/超时现场测试，并更新本文件。
