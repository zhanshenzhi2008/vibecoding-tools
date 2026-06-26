---
name: agent-debug
description: 排查agent脚本问题及检查语法逻辑。分析agent脚本的执行步骤，通过MCP查询日志，验证每个步骤的返回结果与后续逻辑的匹配性。用于排查agent运行异常、逻辑错误、API调用失败等问题。
---

# Agent 脚本调试与逻辑检查

## 使用场景

当用户需要：
- 排查agent运行异常
- 检查agent脚本逻辑是否正确
- 验证某个步骤的返回结果是否符合预期
- 分析agent执行链路

**核心关联**：`log_llm_task_detail.agentName` → `llm_agent_store.agent_name` → agent脚本代码

---

## MCP工具集成

使用 `db-tools` MCP 进行日志查询。

### 环境切换

```javascript
// 查看当前环境
current_env()

// 切换环境 (local/dev/uat/prod)
switch_env({ env: "dev" })
```

### 查询Agent日志 (MongoDB)

```javascript
// 查询任务步骤
query_mongodb({
  collection: "log_llm_task_step",
  filter: { "requestId": "xxx" },
  projection: { "step": 1, "template": 1, "input": 1, "output": 1, "success": 1, "endTime": 1 },
  limit: 50
})

// 查询任务详情
query_mongodb({
  collection: "log_llm_task_detail",
  filter: { "requestId": { "$in": ["req1", "req2"] } },
  projection: { "taskName": 1, "input": 1, "output": 1, "success": 1 },
  limit: 100
})

// 查询Agent主日志
query_mongodb({
  collection: "log_llm_agent_main",
  filter: { "bizId": "265167532119162880" },
  projection: { "requestId": 1, "agentName": 1, "status": 1, "createTime": 1 },
  limit: 50
})

// 查询HTTP请求日志
query_mongodb({
  collection: "log_llm_http_request",
  filter: { "requestId": { "$in": ["req1", "req2"] } },
  projection: { "url": 1, "method": 1, "requestBody": 1, "responseBody": 1, "success": 1 },
  limit: 100
})
```

### 查询API配置 (MySQL)

```javascript
// 查询 llm_tool_api 表
query({
  sql: "SELECT code, name, url_server, url_path, method FROM llm_tool_api WHERE name = ? LIMIT 10",
  params: ["api名称"]
})
```

### 查询Agent Instance (MySQL)

```javascript
// 根据 ID 查询 Agent Instance
query({
  sql: "SELECT t.* FROM llm_agent_instance t WHERE ID = ?",
  params: ["277267362927394816"]
})

// 根据 Instance ID 查询 Agent Store
query({
  sql: "SELECT t.* FROM llm_agent_store t JOIN llm_agent_instance i ON i.agent_store_id = t.id WHERE i.ID = ?",
  params: ["277267362927394816"]
})

// 查询 Agent Result
query({
  sql: "SELECT t.* FROM llm_agent_result t WHERE biz_id = ?",
  params: ["277267362927394816"]
})

// 查询 Dynamic Plan
query({
  sql: "SELECT t.* FROM llm_dynamic_plan t WHERE biz_id = ?",
  params: ["277267362927394816"]
})

// 查询 Dynamic Plan Detail
query({
  sql: "SELECT d.* FROM llm_dynamic_plan_detail d JOIN llm_dynamic_plan t ON d.dynamic_plan_id = t.id WHERE t.biz_id = ?",
  params: ["277267362927394816"]
})

// 查询 Reuse Cache Data
query({
  sql: "SELECT t.* FROM llm_reuse_cache_data t WHERE biz_id = ?",
  params: ["277267362927394816"]
})

// 查询 Agent Plan
query({
  sql: "SELECT t.* FROM llm_agent_plan t JOIN llm_agent_instance i ON i.agent_store_id = t.agent_store_id WHERE i.ID = ?",
  params: ["277267362927394816"]
})
```

---

## 排查流程

### 1. 收集信息

排查前需要收集：
- **requestId** - 用于查询日志（**优先**）
- **traceId** - 用于在日志文件中搜索
- **问题描述** - 期望行为 vs 实际行为

### 2. 根据 requestId/traceId 查找日志

**优先使用 requestId 直接查询 MongoDB**：

```javascript
// 查询任务详情（包含 agentName）
query_mongodb({
  collection: "log_llm_task_detail",
  filter: { "requestId": "019ece6da8547a6b866c1e0e05a74994" },
  projection: { "agentName": 1, "taskName": 1, "success": 1, "result": 1 },
  limit: 100
})
```

**备选：使用 traceId 在日志文件中搜索**：

```bash
# 使用 Grep 工具搜索日志文件
grep "traceId=abc123" F:/gientech-repository/logs/agent-service.log
```

找到后从日志行中提取：
- `requestId=xxx`
- `bizId=xxx`

### 3. 从日志中获取 agentName

`log_llm_task_detail` 表中每个任务都有 `agentName` 字段：

```javascript
// 示例返回
[
  { "agentName": "agt_hello", "taskName": "n_result", "success": true },
  { "agentName": "agt_hello", "taskName": "n_confirm", "success": false }
]
```

### 4. 根据 agentName 定位 agent 代码

**方式1：查 MySQL 获取脚本内容**

```javascript
query({
  sql: "SELECT id, agent_name, agent_content FROM llm_agent_store WHERE agent_name = ?",
  params: ["agt_hello"]
})
```

**方式2：根据 agentName 推断文件路径**

agent 文件系统存储路径：`{data_path}/system/agt/{package}/{agent_name}.txt`

| agentName | 文件路径 |
|-----------|----------|
| `agt_hello` | `.../agt/assistant/agt_hello.txt` |
| `agt_build_project` | `.../agt/smart_build_deploy/agt_build_project.txt` |
| `agt_xxx.chatdoc.demo` | `.../agt/chatdoc/demo/agt_xxx.txt` |

### 5. 解析Agent脚本

读取脚本，识别执行步骤：

```groovy
// 工具调用
act_api.xxx?参数=值
act_kb.xxx?参数=值
act_memory.write?...

// 子Agent调用
agt_xxx?参数=值

// 条件分支
when('n_result', {...})
assign('n_xxx', ...)
```

### 6. 查询详细日志

使用 `db-tools` MCP 查询：

```javascript
// 查询任务步骤
query_mongodb({
  collection: "log_llm_task_step",
  filter: { "requestId": "请求ID" },
  limit: 100
})

// 查询HTTP请求
query_mongodb({
  collection: "log_llm_http_request",
  filter: { "requestId": "请求ID" },
  limit: 100
})
```

### 7. 分析步骤结果

对每个步骤检查：
- 执行是否成功（`success`字段）
- 返回结果结构（`output`字段）
- 是否有空值/异常
- 后续逻辑是否正确处理

详细返回结构请查看 [reference.md](reference.md)。

### 8. 验证逻辑分支

重点关注 `when()` 条件：
- 变量是否被正确赋值？
- 条件是否覆盖所有情况？
- 空值是否有处理？

### 9. act_api 特殊处理

当遇到 `act_api.xxx` 时：

1. **查API配置**（MySQL）：
   ```javascript
   query({
     sql: "SELECT * FROM llm_tool_api WHERE name = ?",
     params: ["xxx"]
   })
   ```

2. **判断API类型**：
   - `url_server` 为空 → 内部动态API
   - `url_server` 含本系统域名 → 内部HTTP API
   - 第三方域名 → 第三方API

3. **内部API分析**：
   - 根据 `url_server + url_path` 定位Controller
   - 分析返回结构

---

## 常用日志表

| 表名 | 数据库 | 说明 | 关联字段 |
|------|--------|------|----------|
| `log_llm_task_step` | MongoDB | 任务步骤执行日志 | requestId |
| `log_llm_task_detail` | MongoDB | 任务详情（**含 agentName**） | requestId |
| `log_llm_http_request` | MongoDB | HTTP请求日志 | requestId |
| `log_llm_agent_main` | MongoDB | Agent主日志（含 bizId → requestId 关联） | requestId/bizId |
| `log_llm_agent_context` | MongoDB | Agent上下文日志 | requestId |
| `llm_tool_api` | MySQL | API配置表 | name/code |
| `llm_agent_instance` | MySQL | Agent实例表（ID = bizId） | ID |
| `llm_agent_store` | MySQL | Agent配置表（**含 agent_content**） | agent_name |
| `llm_agent_result` | MySQL | Agent执行结果 | biz_id |
| `llm_dynamic_plan` | MySQL | 动态计划 | biz_id |
| `llm_dynamic_plan_detail` | MySQL | 动态计划详情 | dynamic_plan_id |
| `llm_reuse_cache_data` | MySQL | 重用缓存数据 | biz_id |

### 查询链路

```
traceId → agent-service.log → requestId + bizId
                    ↓
              log_llm_agent_main
                    ↓
         log_llm_task_detail / log_llm_task_step
```

### 根据 bizId 获取 requestIds

```javascript
// 1. 先查询 log_llm_agent_main 获取 requestIds
query_mongodb({
  collection: "log_llm_agent_main",
  filter: { "bizId": "265167532119162880" },
  projection: { "requestId": 1 },
  limit: 100
})

// 2. 再用 requestIds 查询其他日志表
query_mongodb({
  collection: "log_llm_task_detail",
  filter: { "requestId": { "$in": ["req1", "req2"] } },
  projection: { "taskName": 1, "input": 1, "output": 1, "success": 1 },
  limit: 100
})
```

---

## 日志表字段

### log_llm_task_step (MongoDB)

| 字段 | 说明 |
|------|------|
| `step` | 步骤类型：template/rag/parser/verifier/action/result |
| `template` | 表达式 |
| `input` | 输入参数(JSON) |
| `output` | 输出结果(JSON) |
| `success` | 是否成功 |
| `resultType` | 结果类型 |
| `endTime` | 结束时间 |
| `requestId` | 请求ID |

### log_llm_http_request (MongoDB)

| 字段 | 说明 |
|------|------|
| `url` | 请求URL |
| `method` | HTTP方法 |
| `requestBody` | 请求体 |
| `responseBody` | 响应体 |
| `success` | 是否成功 |

---

## 源码查询指引

遇到不明确的返回结构时，查看源码：
- `llm-agent-core/.../action/` - 各类Tool实现
- `llm-agent-core/.../action/api/APITool.java`
- `llm-agent-core/.../action/KBTool.java`
- `llm-agent-core/.../action/MemoryTool.java`
- `llm-agent-core/.../action/func/FunctionTool.java`
- `llm-agent-core/.../action/PlanTool.java`
- `llm-agent-core/.../action/FlowTool.java`
- `llm-agent-core/.../action/ac/ACTool.java`

---

## act_plan.run 调用结果判断（重要！）

### TaskResult 返回结构

`act_plan.run` 底层返回的是 `TaskResult.java` 对象，序列化后格式如下：

```json
{"status":"SUCCESS","result":null,"source":"agt_xxx.assistant"}
```

| 字段 | 说明 |
|-----|------|
| `status` | 执行状态：`SUCCESS` / `FAIL` |
| `result` | **业务结果**，即被调用 agent 的 `resultPlan` 变量值 |
| `source` | 被调用的 agent 名称 |

**关键**：act_plan.run 返回的对象**没有 `success` 字段**，只有 `status` 字段！

### 常见错误

```groovy
// ❌ 错误：act_plan.run 没有 success 字段
when('n_tool_exec.success == true', { ... })
when('n_tool_exec.success == "true"', { ... })

// ❌ 错误：访问不存在的 result.size() 会报错
when('n_tool_exec.result.size() > 0', { ... })
```

### 正确写法

```groovy
// ✅ 正确：使用 status 字段判断
when("n_tool_exec.status == 'SUCCESS'", {
    // 成功逻辑
}, {
    // 失败逻辑
})

// ✅ 正确：判断 result 是否有值（需先判断不为null）
when('fn.hasValue(n_tool_exec.result)', {
    // 有业务结果
})
```

### 如果需要子 agent 返回执行成功/失败状态

被调用 agent 的 `resultPlan` 是**业务结果**，不包含执行状态。需要在脚本中主动包装返回值：

```groovy
// ✅ 方式1：被调用方主动包装返回值
// agt_xxx.txt 最后一句
assign("n_return_result", '{"status":"SUCCESS","result":"{{n_deploy_result}}","is_plan_break":"false"}')

// ✅ 方式2：调用方使用 on_failure 捕获异常
on_failure({
    assign('resultTip', '{"status":"FAIL","result":{{n_plan_run_tool_exec.result}},"source":"{{confirmed_tool.name}}"}')
    act_flow.go?plan=end
})
```

### 死循环排查

如果遇到 `agt_opsclaw_tool` 相关死循环问题，首先检查：
1. `act_plan.run` 后的 `when()` 条件是否使用了正确的 `status` 字段
2. 是否正确设置了 `done=true` 以退出循环

---

## 输出格式

排查完成后输出报告：

```
## Agent 排查报告

### 基本信息
- requestId：xxx
- traceId：xxx（可选）
- 问题描述：xxx

### Agent 链路
- 顶层Agent：agt_xxx
- 子Agent：agt_yyy, agt_zzz

### 执行步骤分析
#### 步骤1: n_result, act_xxx.yyy (agent: agt_xxx)
- 执行结果：✅成功 / ❌失败
- 返回结构：{...}
- 逻辑检查：xxx

### 结论
- 问题根因：xxx
- 建议修复：xxx
```

---

## 快速检查清单

- [ ] agent脚本是否UTF-8 without BOM编码
- [ ] act_xxx.yyy 对应的Tool类方法是否存在
- [ ] 日志中每个步骤的success状态
- [ ] when()条件的变量是否在之前被正确赋值
- [ ] act_api调用需要查询 llm_tool_api 确认API类型
- [ ] 第三方API只能通过日志分析返回结构
- [ ] act_plan.run 调用后判断条件是否使用 `status` 字段（不是 `success`）
- [ ] 循环类agent是否正确设置 `done=true` 以退出循环
