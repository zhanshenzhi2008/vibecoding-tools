# 团队 Review 流程

适用于 `vibecoding-tools/` 仓库的所有改动。

## 🛡️ 三层防线

```
第 1 层：本地自查（提交前）
         ↓
第 2 层：GitHub Actions 自动扫描（PR 时）
         ↓
第 3 层：人类 Review（CODEOWNERS 强制）
```

---

## 1️⃣ 本地自查（最快反馈）

提交前在仓库根目录跑：

```bash
bash .github/scripts/check-cursor-secrets.sh
```

或直接跑 grep：

```bash
# 真实 IP
grep -rE "(\d{1,3}\.){3}\d{1,3}" cursor/ | \
  grep -v "your.server.ip" | grep -v "0.0.0.0"

# 真实邮箱
grep -rE "[a-zA-Z0-9_]+@[a-zA-Z0-9]+\.[a-zA-Z]+" cursor/ | \
  grep -v "example.com" | grep -v "your-email"

# API Key（OpenAI / Anthropic）
grep -rE "(sk-[a-zA-Z0-9]{20,}|ant-[a-zA-Z0-9-]{20,})" cursor/

# GitHub Token
grep -rE "ghp_[a-zA-Z0-9]{36}" cursor/

# 私钥
grep -rE "BEGIN .* PRIVATE KEY" cursor/
```

---

## 2️⃣ GitHub Actions 自动扫描

每个 PR 都会触发 `.github/workflows/cursor-security-scan.yml`：

- ✅ 自动跑（无人工成本）
- ❌ 失败则**无法 merge**（分支保护强制）
- ⏱️ 通常 < 1 分钟出结果

它会扫描：
- 真实 IP / 域名 / 邮箱
- API Key / Token / 私钥
- 硬编码密码字段

---

## 3️⃣ CODEOWNERS 强制 Review

任何对 `cursor/` 的修改，**必须 @zhanshenzhi2008 approve**：

| 改动内容 | 必须 review 的人 | 备注 |
|---------|----------------|------|
| `cursor/rules/*` | @zhanshenzhi2008 | 规则影响 Agent 行为 |
| `cursor/skills/*` | @zhanshenzhi2008 | Skill 是行为脚本 |
| `cursor/mcps/*` | @zhanshenzhi2008 | MCP 是可执行代码 |
| `cursor/rules/agent_rules_index.mdc` | @zhanshenzhi2008 | 索引文件，影响全局 |
| `README.md` / `LICENSE` / `.gitignore` | @zhanshenzhi2008 | 项目级 |
| 其他文件 | 不强制 owner | |

> 💡 添加新 owner：编辑 `CODEOWNERS` 文件，本节表格同步更新。

---

## 🔄 修改流程（推荐路径）

```bash
# 1. 切分支
git checkout -b feat/<描述>

# 2. 本地修改
vi cursor/skills/<skill>/SKILL.md

# 3. 本地自查
bash .github/scripts/check-cursor-secrets.sh

# 4. 提交（粒度：一次提交一件事）
git add cursor/
git commit -m "feat(skill): 新增 XXX skill"

# 5. 推送 & 开 PR
git push -u origin HEAD
gh pr create --title "feat(skill): 新增 XXX" \
             --body "$(cat .github/PULL_REQUEST_TEMPLATE.md)"

# 6. 等 CI 通过 + owner review
gh pr checks                  # 看 CI 状态
gh pr review --approve        # owner 评论

# 7. merge
gh pr merge --squash
```

---

## ⚠️ 例外情况：紧急修复

如果遇到线上 bug 必须立刻修：

```bash
# 临时绕开流程（仅限紧急）
git checkout master
git pull
# 直接改 → commit → push
# 之后必须开 PR 走完整流程补 review
```

> ⚠️ **强烈不建议**：没有 review 的修改等于把仓库拱手让人。

---

## 🆕 多人协作：如何加新成员

1. **仓库协作者**：GitHub → Settings → Collaborators → Add people
2. **CODEOWNERS**：把对方 GitHub 用户名加进去：
   ```
   /cursor/   @zhanshenzhi2008 @newmember
   ```
3. **分支保护**：建议限制仓库 push 权限，只允许 owner 直接 push

---

## 📊 当前防线状态

| 层 | 已实现 | 文件 |
|----|-------|------|
| 1. 本地自查清单 | ✅ | `PULL_REQUEST_TEMPLATE.md` |
| 2. GitHub Actions | ✅ | `.github/workflows/cursor-security-scan.yml` |
| 3. CODEOWNERS | ✅ | `CODEOWNERS` |
| 4. 分支保护 | ⚠️ 需 GitHub 网页手动开启 | （见下） |

### ⚠️ 还需要在 GitHub 网页手动做的事：

1. **Settings → Branches → Add rule**
   - Branch name pattern: `master`
   - ✅ Require a pull request before merging
   - ✅ Require approvals: 1
   - ✅ Require status checks: `Cursor Security Scan`
   - ✅ Do not allow bypassing the above settings

2. **Settings → General → Pull Requests**
   - ✅ Allow squash merging

---

## 🔗 跨工具规则共享

Claude / Codex 加载 `cursor/rules/` 的方式见
[`cursor/rules/agent_rules_index.mdc`](cursor/rules/agent_rules_index.mdc)。
