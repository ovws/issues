# `ovws/issues`：GitHub Issues 与 Linear 同步备份

本仓库现专门保留 GitHub Issues、评论及 Linear 状态同步工作流。项目源码已迁移到 [ovws/internal-ai](https://github.com/ovws/internal-ai)（私有仓库，默认分支为 `master`）。

## 本仓库保留内容

- GitHub Issues 与评论：属于 GitHub 的 Issue 数据，不是 Git 文件。本次仅清理代码文件，没有删除或修改 Issue、评论、标签或状态。
- `.github/workflows/linear-issue-sync.yml`：每小时同步带 `linear-sync` 标签的 Issue，也支持手动运行。
- `docs/LINEAR-GITHUB-SYNC.md`：Linear 同步规则与配置说明。
- `ISSUES-ARCHIVE.md`：截至 2026-10-09 的全部 Issue 正文、元数据及评论文本快照。
- 本文件：仓库用途与备份说明。

## 保持同步正常运行

不要删除或停用同步工作流；继续保留仓库 Actions secret `LINEAR_API_KEY`，并保持 GitHub Issues 功能启用。工作流只处理本仓库里带 `linear-sync` 标签的打开 Issue。

## 源码回溯

当前 `main` 仅保留 Issues 备份、Linear 同步工作流及其说明、Issue 文本归档和备份说明。清理前的项目源码仍可从本仓库 Git 历史回溯；正式迁移版本可在 `ovws/internal-ai` 主分支的迁移提交中查看。
