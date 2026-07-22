# Linear → GitHub Issue 状态同步

此仓库通过 `.github/workflows/linear-issue-sync.yml` 定时将**明确启用同步**的 GitHub Issue 与对应的 Linear Issue 对齐。

## 映射规则

| Linear 状态 | GitHub 动作 |
| --- | --- |
| `In Review` | 保持 Issue 打开，添加 `needs-review` 标签，并留一条带 Linear 链接的审查评论。 |
| `Done`（completed） | 留一条带 Linear 链接的完成评论，然后以 `completed` 原因关闭 Issue。 |
| 其他状态 | 保持 Issue 打开；若此前有 `needs-review`，则移除该标签。 |

工作流只读取带有 `linear-sync` 标签的**打开** GitHub Issue。它会从 Issue 标题、正文或评论中寻找 Linear 标识符，例如 `WK-78`；找不到或在 Linear 中不存在时会跳过，不会关闭 Issue。

## 一次性配置

1. 在 GitHub 仓库 Settings → Secrets and variables → Actions 新建 `LINEAR_API_KEY`。该值是只读范围即可的 Linear personal API key；不要提交到仓库或写进 Issue/评论。
2. 为需要同步的 GitHub Issue 添加 `linear-sync` 标签。工作流会在首次运行时自动创建 `linear-sync` 和 `needs-review` 两个标签；也可由维护者提前创建。
3. 在 Actions 页面手动运行 **Sync Linear issue status to GitHub**，验证结果后等待每小时的定时运行。

## 已关联任务

以下 Issue 可在完成上述配置后加入 `linear-sync`：

| GitHub Issue | Linear Issue |
| --- | --- |
| #9 | WK-78 |
| #11 | WK-81 |
| #15 | WK-96 |

## 边界

- Linear 的 `In Review` 在 GitHub 没有同名状态，因此使用标签和评论表示，而非关闭 Issue。
- `Done` 是关闭 Issue 的唯一自动条件。若现场验收尚未结束，请勿将对应 Linear Issue 标记为 Done。
- 同步是 Linear → GitHub；GitHub 端手动关闭不会反写 Linear。
