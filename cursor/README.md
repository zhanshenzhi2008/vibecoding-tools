# `cursor/` —— Cursor 配置单一真实源

> 所有 Cursor 规则、Skills、MCP 配置的**唯一编辑位置**。
> 仓库根目录的 `.cursor/` 是 `cursor/` 的 symlink，全局 `~/.cursor/skills/` 也是它的 symlink。
> **任何位置修改 = 修改同一个物理目录**，永远不用担心漂移。

📖 团队协作流程？见 [`REVIEW.md`](./REVIEW.md) — 三层防线：本地自查 + CI 扫描 + CODEOWNERS 强制 review。

---

## 📐 目录结构

```
vibecoding-tools/
├── cursor/                      ← 🎯 真实唯一源（所有修改在这里）
│   ├── rules/                   ← Cursor Rules（.mdc）
│   ├── skills/                  ← Cursor Agent Skills
│   │   ├── agent-debug/
│   │   ├── deploy/
│   │   └── github-cicd-template/
│   ├── mcps/                    ← MCP 服务配置
│   │   └── db-tools/
│   └── README.md                ← 你正在看的这个文件
│
├── .cursor/  ─────────symlink──→  cursor/
│   （仓库根目录下的 symlink，让 Cursor 在 vibecoding-tools 项目内也能识别这些配置）
│
└── （本仓库就是源，不再有副本）
```

---

## 🔗 三层 symlink 关系

Cursor 实际只扫描**两个固定位置**：
- 项目内：`<project>/.cursor/`
- 全局：`~/.cursor/`

我们用 symlink 让所有路径指向同一个物理目录：

```
┌─────────────────────────────────────────────────────────┐
│           cursor/   ← 真实物理文件（唯一源）              │
│           ├── rules/                                   │
│           ├── skills/                                  │
│           └── mcps/                                    │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
            │ symlink                 │ symlink
            │                         │
            ▼                         ▼
┌─────────────────────┐   ┌──────────────────────────┐
│ .cursor/            │   │ ~/.cursor/skills/        │
│ （项目内）           │   │ （用户全局，所有项目生效）│
└─────────────────────┘   └──────────────────────────┘
```

> ⚠️ **注意区分两个目录**，名字相似但用途完全不同：
>
> | 路径 | 谁在管 | 能不能改 |
> |------|--------|---------|
> | `~/.cursor/skills/` | **你**（通过 symlink 指向 `cursor/skills`） | ✅ 改这里 |
> | `~/.cursor/skills-cursor/` | **Cursor 官方**（自动同步更新，自带 19 个 skill） | ❌ 不要手动改 |
>
> 如果你看到 `skills-cursor` 里有 `deploy` / `agent-debug` 等自定义 skill，那是误拷——请删掉，只保留在 `cursor/skills/` 下。

**效果**：在任何路径下修改 rules / skills / mcps，全部生效，没有"副本漂移"问题。

---

## ✅ 工作流：怎么编辑？

### 1. **唯一原则**：所有修改都在 `cursor/` 下进行

```bash
# ✅ 正确
vi cursor/rules/agent_rules_index.mdc
vi cursor/skills/deploy/SKILL.md
vi cursor/mcps/db-tools/tools/db-tools.json

# ❌ 错误（虽然也能编辑，因为是 symlink，但保持习惯统一）
vi .cursor/rules/agent_rules_index.mdc
vi ~/.cursor/skills/deploy/SKILL.md
```

> 推荐 IDE 收藏夹直接固定 `cursor/` 路径。

### 2. **新增 Skill**

```bash
# 创建目录
mkdir cursor/skills/<skill-name>

# 创建 SKILL.md（必须）
cat > cursor/skills/<skill-name>/SKILL.md << 'EOF'
---
name: <skill-name>
description: 一句话说明这个 skill 干什么、什么时候用
---

# <Skill Name>

<详细文档>
EOF

# 完成！Cursor 自动识别（无需重启，下次启动时加载）
```

### 3. **新增 Rule**

```bash
# rules 直接是 .mdc 文件，没有目录包装
cat > cursor/rules/<rule-name>.mdc << 'EOF'
---
description: 这个规则的说明
globs: src/**/*.py    # 可选：限定作用范围
alwaysApply: false    # 可选：是否始终启用
---

<规则内容>
EOF
```

### 4. **新增 MCP**

```bash
mkdir -p cursor/mcps/<mcp-name>/tools
# 写 db-tools.json 等配置 + 服务端代码
# Cursor → Settings → MCP → 同步配置
```

### 5. **删除**

```bash
rm -rf cursor/skills/<skill-name>
rm cursor/rules/<rule-name>.mdc
# 提交 git 即可
```

---

## 🛠️ 安装 / 部署到本机

如果换了新机器或重新克隆仓库：

```bash
# 1. 克隆本仓库
git clone git@github.com:zhanshenzhi2008/vibecoding-tools.git \
    ~/Documents/mine-repository/vibecoding-tools
cd ~/Documents/mine-repository/vibecoding-tools

# 2. 仓库根目录的 .cursor/ → cursor/（已在仓库里，clone 即可获得 symlink）
ls -la .cursor   # 应该看到 → cursor 的 symlink

# 3. 全局 ~/.cursor/skills/ → cursor/skills/（手动建一次）
ln -sfn ~/Documents/mine-repository/vibecoding-tools/cursor/skills \
    ~/.cursor/skills

# 4. 验证
ls ~/.cursor/skills/    # 应该看到所有 skill
```

> 💡 仓库里的 `.cursor` 已经是 symlink，**git 会跟踪 symlink 本身**，跨机器 clone 即用。
> 全局 `~/.cursor/skills/` 不在仓库里，需要在每台机器手动建一次。

---

## 🚨 故障排查

### ❌ Cursor 在 vibecoding-tools 项目里看不到某些 skill

**症状**：在仓库根目录打开 Cursor，输入 `/` 只看到部分 skill。

**原因**：`.cursor/skills/` 不是 symlink，或者 symlink 断了。

**修复**：
```bash
cd ~/Documents/mine-repository/vibecoding-tools
ls -la .cursor
# 应该是 .cursor -> cursor，不是目录

# 如果断了，重建：
rm -rf .cursor
ln -s cursor .cursor
```

### ❌ 全局 Cursor（其他项目）看不到这些 skill

**症状**：在 cogniforge 等项目打开 Cursor，看不到 deploy / agent-debug。

**原因**：`~/.cursor/skills/` symlink 没建或断了。

**修复**：
```bash
ls -la ~/.cursor/skills
# 应该是 -> /path/to/vibecoding-tools/cursor/skills

# 重建：
rm -rf ~/.cursor/skills
ln -sfn ~/Documents/mine-repository/vibecoding-tools/cursor/skills \
    ~/.cursor/skills
```

### ❌ Cursor 重启后 symlink 失效

**已知 Cursor bug**：极少数版本重启后不跟随 symlink。

**兜底方案**（放弃 symlink，用拷贝模式）：
```bash
# 切到 copy 模式（见 ~/.cursor/skills-sync/switch-mode.sh）
bash ~/.cursor/skills-sync/switch-mode.sh copy
```

> 💡 如果发现这个问题，请在 Cursor 版本号备注下反馈给 Cursor 团队。

---

## 🤝 多工具共享

同一份 `cursor/` 也能给 Claude Code / Codex 等用：

```bash
# Claude Code
ln -sfn ~/Documents/mine-repository/vibecoding-tools/cursor/skills \
    ~/.claude/skills

# Codex
ln -sfn ~/Documents/mine-repository/vibecoding-tools/cursor/skills \
    ~/.codex/skills
```

三个工具共享同一份 skill，**零副本**。

---

## 📚 当前内容索引

### Rules（`cursor/rules/`）

| 文件 | 用途 |
|------|------|
| `agent_rules_index.mdc` | Agent 规则索引 |
| `agent_comment_tags_rules.mdc` | Agent 脚本注释标签规则 |
| `agent_feedback_rules.mdc` | Agent 反馈规则 |
| `agent_file_encoding_rules.mdc` | Agent 文件编码规则 |
| `create-agent-script.mdc` | 创建 Agent 脚本的规则 |
| `database_upgrade_rules.mdc` | 数据库升级规则 |
| `java-development-rules.mdc` | Java 开发规则 |
| `java_code_edit_rules.mdc` | Java 代码编辑规则 |
| `java_comment_naming_rules.mdc` | Java 注释命名规则 |
| `llm-agent-logs.mdc` | LLM Agent 日志规则 |
| `windows-shell-rules.mdc` | Windows Shell 规则 |

### Skills（`cursor/skills/`）

| Skill | 触发词 |
|-------|--------|
| `agent-debug` | 排查 agent 脚本异常、检查语法逻辑 |
| `deploy` | 部署 Docker 项目（Traefik + Portainer） |
| `github-cicd-template` | 生成 GitHub Actions CI/CD 模板 |

### MCPs（`cursor/mcps/`）

| MCP | 用途 |
|-----|------|
| `db-tools` | 数据库查询 MCP 服务 |

---

## 📝 提交规范

修改后正常 `git add + commit + push`：

```bash
git status
git add cursor/        # 永远只 add cursor/
git commit -m "feat(skills): 新增 XXX skill"

# === 推送走 PR 流程 ===
git push -u origin HEAD
gh pr create --title "feat(skill): 新增 XXX" \
             --body "$(cat .github/PULL_REQUEST_TEMPLATE.md)"
gh pr checks           # 看 CI 扫描结果
gh pr merge --squash   # owner review 通过后 merge
```

> 📖 完整 review 流程见 [`REVIEW.md`](./REVIEW.md)。

新机器 clone 后会自动获得 `.cursor` symlink，无需手动重建。

---

## ⚠️ 不要做的事

| ❌ | 原因 |
|----|------|
| 直接在 `.cursor/` 或 `~/.cursor/skills/` 编辑并跳过 commit | 物理上是同一文件，但 git 只跟踪 `cursor/`，编辑会被覆盖 |
| 用 `cp` 复制 skill 到其他位置 | 立刻产生副本漂移 |
| 把 `cursor/` 子目录单独 symlink 到别处 | 嵌套 symlink 容易出问题 |
| 在 `~/.cursor/skills/` 单独放 skill | 它只是个视图，不是源 |

---

> 💡 **记住**：一切修改都在 `cursor/`。
