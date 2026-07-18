# Cursor 配置审查

任何对 `cursor/` 的修改需要满足以下条件才能 merge 到 `master`：

## 检查项

- [ ] **规则 (.mdc)**
  - 描述写在 frontmatter 的 `description`
  - 内容具体、可执行，不写空话
  - 不引入新的 frontmatter 字段除非在 `cursor/rules/agent_rules_index.mdc` 登记

- [ ] **Skill**
  - 包含 `SKILL.md`（必备）
  - 触发词清单（description 或正文）
  - 没有硬编码：IP、邮箱、API Key、Token、私钥
  - 用 `{{VARIABLE}}` 占位，提示在 GitHub Secrets 配置
  - 没有执行任意 shell 命令的 `scripts/`（除非明确说明）

- [ ] **MCP**
  - 配置 + 服务端代码 + tests 三件套齐全
  - 不连接未经验证的外部服务器
  - 读写权限最小化

- [ ] **提交粒度**
  - 一个 commit 一件事（不要 "改 skill + 改 mcp + 改 README"）
  - 标题：`feat(skill): / fix(skill): / docs(rules):` 等

## 自查命令

提交前本地跑一遍：

```bash
# 查真实 IP
grep -rE "(\d{1,3}\.){3}\d{1,3}" cursor/ | grep -v "your\.server\.ip" | grep -v "0\.0\.0.0"

# 查真实邮箱
grep -rE "[a-zA-Z0-9_]+@[a-zA-Z0-9]+\.[a-zA-Z]+" cursor/ | grep -v "example\.com" | grep -v "your-email"

# 查 OpenAI Key
grep -rE "sk-[a-zA-Z0-9]{20,}" cursor/

# 查 GitHub Token
grep -rE "ghp_[a-zA-Z0-9]{36}" cursor/

# 查私钥
grep -rE "BEGIN .* PRIVATE KEY" cursor/

# 查密码字段赋值（防止误提交）
grep -rE "(password|secret|token|api_key)\s*[:=]\s*['\"][^'\"]+['\"]" cursor/ | grep -v "{{" | grep -v "EXAMPLE"
```

## Review SLA

- 普通修改（docs/typo）：24 小时内
- 新增 skill/mcp：48 小时内
- 影响全局行为（rules 修改 `agent_rules_index.mdc`）：需要 2 人以上 review
