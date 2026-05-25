# Skills OF BaiXian

这是白弦日常使用的 Codex skill 收藏仓库。

## Collections

### Superpowers

`skills/superpowers/` 收录了 14 个 Superpowers skill，保留本机 Codex 中的 `superpowers-*` 目录名和 `SKILL.md` frontmatter 名称，便于后续同步、安装和定位。

分类如下：

| 分类 | 路径 | 用途 |
| --- | --- | --- |
| Planning | `skills/superpowers/planning/` | 需求澄清、计划编写、按计划执行 |
| Development | `skills/superpowers/development/` | TDD、系统调试、Git worktree 隔离工作区 |
| Review and Delivery | `skills/superpowers/review-and-delivery/` | 完成前验证、代码审查、分支收尾 |
| Orchestration | `skills/superpowers/orchestration/` | 并行 agent、子 agent 分工执行 |
| Skill Maintenance | `skills/superpowers/skill-maintenance/` | Superpowers 使用说明和 skill 编写维护 |

详细索引见：

- `collections/superpowers.md`
- `catalog.yaml`

## Layout

```text
skills/
  superpowers/
    planning/
    development/
    review-and-delivery/
    orchestration/
    skill-maintenance/
collections/
  superpowers.md
catalog.yaml
```

## Usage

单个 skill 目录可以复制到本机 Codex skills 目录中使用，例如：

```powershell
Copy-Item -Recurse .\skills\superpowers\planning\superpowers-writing-plans C:\Users\15039\.codex\skills\
```

复制后，确保目标目录中存在 `SKILL.md`，并且文件 frontmatter 中的 `name:` 与目录名一致。
