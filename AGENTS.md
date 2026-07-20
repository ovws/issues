# WEB2API Codex 工作区规则

本文件适用于 `D:\WEB2API` 及其全部子目录。Codex 在本项目中处理任何任务时，必须遵守以下 GitHub Issue 工作流。

## 新问题自动登记

遇到新的、可执行的项目问题时，Codex 必须主动创建或关联 GitHub Issue，无需再次征求用户同意。包括：

- 故障、报错、回归、安全问题；
- 新功能、配置或部署变更；
- 需要调查、修改代码或提交仓库的改进请求。

以下情况不得重复创建 Issue：

- 仅询问进度、补充同一问题的证据或要求关闭已有 Issue；
- 对已登记问题的继续排查、修复、测试、提交或发布；
- 纯确认、致谢或与 WEB2API 无关的一般知识问答。

创建前必须搜索目标仓库的 Open Issue 和最近关闭的 Issue：

- 命中同一问题的 Open Issue：继续使用该 Issue，并按需补充评论和标签；
- 同一故障再次出现且已有 Closed Issue：优先重新打开并补充复现信息；
- 只有确认没有重复项时才新建 Issue。

Issue 应在确认目标仓库和完成查重后尽早创建，原则上早于代码修改。紧急恢复服务时可以先执行最小化止血操作，但必须在继续深入修改前补建 Issue。

## 仓库路由

根据问题的实际代码归属选择且只选择一个主仓库：

| 范围 | GitHub 仓库 | 组件标签 |
| --- | --- | --- |
| 根目录网关、`src/`、`scripts/`、公共配置、Windows 部署 | `ovws/internal-ai-api-config` | `component: gateway`、`component: deployment` 或 `component: config` |
| `upstream/grok2api/`、Grok 文本/图片/视频适配 | `ovws/internal-ai-grok2api` | `component: grok` |
| `upstream/gemini-api/`、Gemini 服务 | `ovws/internal-ai-gemini-api` | `component: gemini` |
| `upstream/chatgpt2api/`、ChatGPT 图片服务 | `ovws/internal-ai-chatgpt2api` | `component: chatgpt-image` |

跨仓库问题以根因为准创建主 Issue；如确实需要多个仓库分别修改，再创建相互链接的子 Issue，禁止为同一修改机械复制 Issue。

## 标签与紧急度

每个新 Issue 必须至少包含：

1. 一个类型标签；
2. 一个且仅一个 `priority: P0` 至 `priority: P3`；
3. 一个最贴近根因的 `component:*` 标签。

类型标签选择：

- `bug`：故障、错误响应、回归或行为不符合预期；
- `enhancement`：新功能或行为改进；
- `documentation`：仅文档变更；
- `maintenance`：依赖、重构、清理、监控或运维维护；
- `security`：凭据、权限、敏感数据、网络暴露或其他安全风险；安全问题可以同时加 `bug`。

紧急度判定：

- `priority: P0`：正在发生的凭据/敏感数据泄露、不可恢复的数据损坏，或公司范围全部核心服务不可用；必须立即止血；
- `priority: P1`：核心功能中断、持续 5xx、多人受影响且没有可行绕过方案，或高风险安全隐患；
- `priority: P2`：部分功能异常、有临时绕过方案、单一服务受影响，或正常优先级的新功能/配置变更；这是无法明确判断时的默认值；
- `priority: P3`：文档、清理、轻微体验、非阻塞优化或低影响问题。

若所需标准标签在仓库中不存在，Codex 应创建标签后再关联 Issue，保持上述名称、含义和颜色体系一致。

## Issue 内容要求

标题使用简洁中文，描述具体症状或目标。正文至少包含：

- 现象或目标；
- 影响范围与紧急度理由；
- 已知复现条件、关键错误码和时间；
- 期望结果；
- 初步排查或实施计划；
- 与已有 Issue、提交或外部任务的关联（如有）。

禁止把 API Key、Cookie、访问令牌、完整 Authorization Header、Base64 图片/视频、私密账号信息或其他凭据写入 GitHub。日志和请求体必须先脱敏，只保留定位所需的尺寸、哈希、错误摘要和元数据。

## GitHub 与 Linear

- GitHub 是新问题的唯一入口；不要为同一事项直接新建 Linear 任务；
- 依靠 GitHub 与 Linear 的双向同步传播状态；
- 除非用户明确要求，不要对同步生成的 Linear 任务重复评论或改状态；
- GitHub 连接器可访问仓库时优先使用连接器；私有仓库返回 404 或连接器不可用时，使用已登录的 `gh` CLI；
- GitHub 操作失败时应保留本地工作并报告失败原因，不得声称 Issue 已创建或已关闭。

## 完成与关闭

修复或变更完成后，先进行与风险相称的测试和实机验证，再在 Issue 中记录：

- 根因或最终设计；
- 修改摘要；
- 测试命令与结果；
- 实机验证结果；
- 提交 SHA、分支和相关文件/产物位置（不得包含凭据）。

只有在目标已达成且没有剩余必需工作时，才以 `completed` 关闭 Issue。若用户仅要求关闭一个已有 Issue，直接检查并关闭该 Issue，不要为关闭操作再创建新 Issue。
