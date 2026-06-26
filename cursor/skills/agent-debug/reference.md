# Agent Tool 返回结构参考

本文档详细列出每个Tool类的方法及其返回类型，用于分析agent执行结果。

---

## 目录

1. [KBTool](#kbtool) - 知识库操作
2. [MemoryTool](#memorytool) - 变量内存管理
3. [FunctionTool](#functiontool) - 函数执行/文件操作
4. [PlanTool](#plantool) - 计划任务管理
5. [FlowTool](#flowtool) - 流程控制
6. [APITool](#apitool) - API调用
7. [ACTool](#acttool) - 执行节点调用
8. [Java实体类](#java实体类) - 日志表对应的Java DTO

---

## KBTool

**源码路径**: `llm-agent-core/.../action/KBTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `search` | requirement, name, column, outputFields, top... | `List<Map>` | 知识库向量搜索 |
| `select` | name, column, where, order, maxSize | `List<Map>` | DB数据查询 |
| `selectBy` | sql, parameters | `IVerifyResult` | SQL查询，返回`TaskResult` |
| `importData` | data, name, uniqueKey... | `Boolean` | 数据导入 |
| `delete` | name, where, maxSize | `Integer` | 删除数据条数 |
| `merge` / `update` | name, columnValues, where | `Boolean` | 更新数据 |
| `hasKB` | name | `IVerifyResult` | 检查KB是否存在 |
| `getKBCatalog` | schema, name | `String` | 查询KB目录 |
| `getKBDefinition` | schema, name | `String` | 查询KB定义 |
| `readCfg` | type, key | `String` | 读取系统配置 |
| `searchQA` | name, requirement, isRerank, bm25Weight | `String` | 问答知识库查询 |
| `searchGraph` | cypher | `List<Map>` | 图谱查询 |
| `searchGraphShortPath` | label, filterKey, start, passThrough, end | `Map<String, Object>` | 最短路径查询 |

### 返回结构示例

#### search 返回
```json
[
  {"column1": "value1", "column2": "value2"},
  {"column1": "value3", "column2": "value4"}
]
```

#### selectBy 返回（IVerifyResult/TaskResult）
```java
// 成功
TaskResult.builder().success(true).result(List<Map>).build()

// 失败
TaskResult.builder().success(false).build().setSystemReason("错误原因")
```

#### importData 返回
```java
true   // 成功
false  // 失败或无数据
```

---

## MemoryTool

**源码路径**: `llm-agent-core/.../action/MemoryTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `assign` | var, value, type, planName, index, global | `TaskResult` | 写入变量 |
| `retrieve` | var, global | `TaskResult` | 读取变量 |
| `forget` | names | `Boolean` | 遗忘变量 |
| `hasValue` | name | `Boolean` | 检查变量是否有值 |
| `increase` | var, max | `String` | 变量计数，返回`var=count` |
| `addAgentHint` | success, thought, feedback | `Boolean` | 增加hint |

### 返回结构示例

#### assign 返回
```java
TaskResult.builder()
    .success(true)
    .result(Object)  // 写入的值
    .build()
```

#### retrieve 返回
```java
TaskResult.builder()
    .success(true)
    .result(Object)  // 读取的值
    .build()
```

#### increase 返回
```java
"varName=5"     // 成功，返回 变量名=计数值
"已经达到最大次数限制"  // 失败
```

---

## FunctionTool

**源码路径**: `llm-agent-core/.../action/func/FunctionTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `doExecute` | funcFolder, name, script, js | `IVerifyResult` | 执行函数 |
| `run` | funcFolder, expression, script, js | `IVerifyResult` | 运行代码 |
| `read` | filename | `String` | 读文件 |
| `write` | filename, data, append, display, syncKbs | `Boolean` | 写文件 |
| `search` | query, filepath, maxResults, ignoreCase | `List<FileSearchResult>` | 文件搜索 |
| `readLines` | filename, startLine, endLine | `String` | 按行读取 |
| `list` | filepath, maxDepth | `List<String>` | 列出目录 |
| `unzip` | fileRelativePath, destRelativeDirectory | `List<String>` | 解压文件 |
| `word` | template, rootVar, output, syncKbs | `String` | 生成Word |
| `replaceLines` | filename, startLine, endLine, data | `Boolean` | 替换文件行 |

### 返回结构示例

#### 文件搜索 search 返回
```java
List<FileSearchResult>  // 包含 lineNumber, content, filePath 等
```

#### write 返回
```java
true   // 成功
false  // 失败
```

---

## PlanTool

**源码路径**: `llm-agent-core/.../action/PlanTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `parse` | task | `PlanListInfo` | 解析计划 |
| `convert` | var, callback, showUI, maxConcurrent | `PlanListInfo` | 转换计划 |
| `runPlan` | agent, var, index, executor, async... | `IVerifyResult` | 执行计划 |
| `run` | toolType, code, parameters, async... | `TaskResult` | 执行工具/Agent |
| `check` | type, agent, script, checkTool | `TaskResult` | 检查脚本语法 |
| `runScript` | type, script, parameters | `IVerifyResult` | 运行脚本 |
| `update` | agent, var, index, plan | `Map<String, Object>` | 更新计划 |
| `add` | agent, var, index, plan | `Map<String, Object>` | 添加计划 |
| `change` | agent, var, index, plan, operation | `Map<String, Object>` | 调整计划 |
| `remove` | agent, var, index | `Map<String, Object>` | 删除计划 |
| `index` | agent, var, index | `Map<String, Object>` | 切换索引 |
| `assignAgent` | agent, var, index, executor, parameter | `Map<String, Object>` | 分配执行器 |
| `agent` | agent, var, index | `LlmPlanExecutorBo` | 获取执行器 |
| `getStepResult` | agentName, taskName | `List<LogLlmTaskStepDTO>` | 查询步骤结果 |

### 返回结构示例

#### run 返回（TaskResult）
```java
// 成功
TaskResult.builder().success(true).result(Object).build()

// 失败
TaskResult.builder().success(false).result("错误信息").build()
```

#### update/add/change 返回（Map）
```java
{
    "success": true,
    "details": [...],      // PlanListInfo.getDetails()
    "index": 0,
    "planId": 123
}
```

#### check 返回
```java
// 语法检查成功
TaskResult.builder().success(true).result("校验通过的源码").build()

// 语法检查失败
TaskResult.builder().success(false).result("错误信息").build()
```

---

## FlowTool

**源码路径**: `llm-agent-core/.../action/FlowTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `go` | agent, plan, step, suspend, hintError | `TaskResult` | 跳转计划 |
| `suspend` | - | `Boolean` | 暂停任务 |
| `resumeChat` | - | `Boolean` | 恢复对话 |
| `wait` | second | `Object` | 等待秒数 |
| `page` | pageCode, params, noWait | `IVerifyResult` | 打开页面 |
| `pageConfirm` | confirmTool, toolType, toolCode, params | `IVerifyResult` | 确认页面 |
| `message` | params | `IVerifyResult` | 发送SSE消息 |
| `showDialog` | message | `Boolean` | 显示对话框 |
| `iframe` | uri, pageCode, urlParams | `IVerifyResult` | 显示iframe |
| `fail` | result, message | `IVerifyResult` | 流程失败 |
| `success` | result | `IVerifyResult` | 流程成功 |
| `switchRunMode` | mode | `Boolean` | 切换模式 |
| `changeView` | field, value | `Boolean` | 改变视图 |
| `debug` | var | `Boolean` | 调试变量 |

### 返回结构示例

#### go 返回
```java
// 成功
TaskResult.builder().success(true).result("next/end/continue/break").build()

// 失败
TaskResult.builder().success(false).systemReason("错误原因").build()
```

#### page/pageConfirm 返回
```java
TaskResult.builder()
    .success(true)
    .result(UiMetaDataDTO)  // UI配置对象
    .type(TaskResult.TYPE_UI)
    .build()
```

---

## APITool

**源码路径**: `llm-agent-core/.../action/api/APITool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `run` / `doExecute` | name, parameters, fileNames, requestHeaders | `Object` | 执行API |
| `doExecuteDynamic` | name, dynamicParamData | `Object` | 动态执行API |
| `search` | query, size, toolType | `List` | 查询可用工具 |
| `searchToolset` | query, size | `List<ToolSetSearchRecord>` | 查询工具集 |
| `defineToolset` | code, name, description, toolcodes, personal | `BaseResult` | 定义工具集 |

### 返回结构示例

#### run/doExecute 返回
```java
// 成功 - 返回String（API响应的字符串化结果）
String result = "API响应内容"

// 失败
TaskResult.builder().success(false).systemReason("错误原因").build()

// 上传文件时返回Map
{"success": false, "msg": "错误信息"}
```

### act_api 调用分析流程

1. **查询API配置**：
   ```sql
   SELECT * FROM llm_tool_api WHERE name = 'xxx' OR code = 'xxx'
   ```

2. **判断API类型**：
   - `url_server` 为空/null → 内部动态API
   - `url_server` 含本系统域名 → 内部HTTP API
   - 第三方域名 → 第三方API

3. **内部API分析**：
   - 根据 `url_server + url_path` 定位Controller
   - 分析返回结构

---

## ACTool

**源码路径**: `llm-agent-core/.../action/ac/ACTool.java`

### 常用方法

| 方法 | 参数 | 返回类型 | 说明 |
|------|------|----------|------|
| `exec` | acName, type, code, parameters, timeout, async | `IVerifyResult` | 执行代码 |
| `send` | acName, command, name, parameters | `IVerifyResult` | 发送指令(兼容) |
| `list` | - | `List<AcDescriptor>` | 获取AC列表 |
| `describe` | acName | `AcDescriptor` | 获取AC详情 |

### 返回结构示例

#### exec 返回
```java
// 成功
TaskResult.builder().success(true).result(Object).build()

// 失败
TaskResult.builder().success(false).result("错误信息").build()
```

#### list 返回
```java
[
    {
        "name": "Native",
        "type": "LOCAL",
        "status": "AVAILABLE",
        "runtimes": ["SHELL", "PYTHON", "RUBY", "NODE"]
    },
    {
        "name": "sandbox",
        "type": "SANDBOX",
        "status": "AVAILABLE",
        "runtimes": ["SHELL", "PYTHON"]
    }
]
```

---

## IVerifyResult / TaskResult

所有Tool方法返回的 `IVerifyResult` 最终都会转换为 `TaskResult`：

### TaskResult 结构

```java
TaskResult.builder()
    .success(Boolean)           // 是否成功
    .result(Object)            // 结果数据
    .type(Integer)             // 结果类型
    .thought(String)           // 思考过程
    .systemReason(String)      // 系统错误原因
    .build()
```

### TaskResult 类型常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `TYPE_TEXT` | 1 | 普通文本 |
| `TYPE_PYTHON` | 2 | Python文件 |
| `TYPE_PLAN_INFO` | 3 | 计划列表 |
| `TYPE_CSV` | 4 | CSV文件 |
| `TYPE_REFERENCE` | 5 | 引用文本 |
| `TYPE_MANUAL_INPUT` | 10 | 手工输入 |
| `TYPE_UI` | 20 | UI界面 |
| `TYPE_WORD` | 30 | Word文件 |
| `TYPE_IFRAME` | 40 | iframe |

---

## 日志表字段

> **注意**：日志表存储在 **MongoDB** 中，使用 `db-tools` MCP 的 `query_mongodb` 查询。

### log_llm_task_step (MongoDB)

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `requestId` | String | 请求ID |
| `step` | Integer | 步骤类型：template/rag/parser/verifier/action/result |
| `template` | String | 表达式 |
| `input` | String | 输入参数(JSON) |
| `output` | String | 输出结果(JSON) |
| `success` | Boolean | 是否成功 |
| `resultType` | Integer | 结果类型 |
| `endTime` | DateTime | 结束时间 |
| `chatMessageId` | Long | 关联的chat message id |

### log_llm_task_detail (MongoDB)

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `requestId` | String | 请求ID |
| `logLlmAgentMainId` | Long | Agent主日志ID |
| `resultType` | Integer | 结果类型 |
| `input` | String | 输入 |
| `output` | String | 输出 |
| `success` | Boolean | 是否成功 |
| `taskName` | String | **任务名称（agent脚本中每个步骤开头的变量名，如 `n_tool_confirm`、`n_map_list`）** |
| `dynamicPlanDetailId` | Long | 动态计划详情ID |

> **taskName 说明**：agent脚本中每行开头的第一个标识符。
>
> **规则**：
> - 有变量赋值：`n_result, act_api.xxx` → taskName = `n_result`
> - 纯模板调用：`tpl_extract_params, psr_json` → taskName = `tpl_extract_params`
> - 无变量纯函数：`psr_json` → taskName = `psr_json`
>
> **示例**：
> | 脚本写法 | taskName |
> |---------|----------|
> | `n_agt_result, agt_build_project.assistant?os={{n_os}}` | `n_agt_result` |
> | `n_params, tpl_extract_params` | `n_params` |
> | `psr_json` | `psr_json` |
> | `when('n_result', {...})` | `n_result` |

### log_llm_http_request (MongoDB)

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `requestId` | String | 请求ID |
| `url` | String | 请求URL |
| `method` | String | HTTP方法 |
| `requestHeaders` | String | 请求头 |
| `requestBody` | String | 请求体 |
| `responseHeaders` | String | 响应头 |
| `responseBody` | String | 响应体 |
| `success` | Boolean | 是否成功 |
| `duration` | Long | 执行时长(ms) |
| `createTime` | DateTime | 创建时间 |

### log_llm_agent_main (MongoDB)

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `requestId` | String | 请求ID |
| `bizId` | String | 业务ID |
| `agentId` | Long | Agent ID |
| `agentName` | String | Agent名称 |
| `logLlmAgentContextId` | Long | Agent上下文ID |
| `status` | Integer | 状态 |
| `createTime` | DateTime | 创建时间 |

### log_llm_agent_context (MongoDB)

| 字段 | 类型 | 说明 |
|------|------|------|
| `_id` | ObjectId | 主键 |
| `requestId` | String | 请求ID |
| `userId` | Long | 用户ID |
| `taskName` | String | 任务名称 |
| `contextData` | String | 上下文数据(JSON) |

### llm_tool_api (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `code` | String | API编码 |
| `name` | String | API名称 |
| `description` | String | API描述 |
| `url_server` | String | 服务器地址 |
| `url_path` | String | URL路径 |
| `url` | String | 完整URL |
| `method` | String | HTTP方法 |
| `parameters` | String | 参数定义(JSON) |
| `request_body` | String | 请求体 |
| `response_body` | String | 响应体 |
| `status` | Integer | 状态(0-不可用,1-可用) |

### llm_agent_instance (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `ID` | Long | 主键 = bizId |
| `agent_store_id` | Long | Agent Store ID |
| `instance_source` | Integer | 实例来源 |
| `requestId` | String | 请求ID |
| `status` | Integer | 状态 |
| `result_` | Text | 执行结果 |

### llm_agent_store (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `agent_name` | String | Agent名称 |
| `agent_content` | Text | Agent脚本内容 |
| `model_type` | String | 模型类型 |

### llm_agent_result (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `biz_id` | Long | 业务ID |
| `dynamic_plan_detail_id` | Long | 动态计划详情ID |
| `result_content` | Text | 结果内容 |

### llm_dynamic_plan (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `biz_id` | Long | 业务ID |

### llm_dynamic_plan_detail (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `dynamic_plan_id` | Long | 动态计划ID |
| `node_name` | String | 节点名称 |
| `node_content` | Text | 节点内容 |

### llm_reuse_cache_data (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `biz_id` | Long | 业务ID |
| `cache_key` | String | 缓存key |
| `cache_data` | Text | 缓存数据 |

### llm_agent_plan (MySQL)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `agent_store_id` | Long | Agent Store ID |
| `plan_name` | String | 计划名称 |

---

## 关联关系

```
llm_agent_instance (ID = bizId)
    ├── agent_store_id → llm_agent_store.id
    ├── requestId → log_llm_agent_main.requestId
    └── instance_source → 区分来源

llm_agent_result
    ├── biz_id → llm_agent_instance.ID
    └── dynamic_plan_detail_id → llm_dynamic_plan_detail.id

llm_dynamic_plan
    └── biz_id → llm_agent_instance.ID

llm_dynamic_plan_detail
    └── dynamic_plan_id → llm_dynamic_plan.id
```

## MCP查询示例

---

## 常见问题排查要点

### 1. when() 条件判断失败

检查点：
- 变量是否被正确赋值（查看 assign/retrieve 的 result）
- 变量值是否为 null 或空字符串
- when() 中使用的是哪个变量名

### 2. 取不到预期字段

检查点：
- Tool 返回的实际结构（查看日志 output）
- 字段名是否拼写正确
- 第三方API返回结构可能变化

### 3. 空值未处理

检查点：
- act_xxx 返回 null 时的处理
- 使用 `?.size()` 替代 `.size()`
- 使用 `?:` 提供默认值

### 4. 异步结果未等待

检查点：
- act_plan.run?async=true 返回 FutureValue
- 需要使用 fn.wait 或 .value 等待结果

---

## 根据 traceId 查找 requestId/bizId

traceId 是前端传入的链路追踪ID。

### 步骤1: 在日志中搜索 traceId

使用 Grep 工具搜索 agent-service.log：

```bash
# 搜索 traceId
grep "traceId=abc123" F:/gientech-repository/logs/agent-service.log
```

### 步骤2: 从日志中提取关键ID

从匹配的日志行提取：
- `requestId=xxx`
- `bizId=xxx`（可能为 `bizId=123` 或 `instanceId=123`）

### 示例日志行

```
2026-06-16 10:30:15.123 [INFO] traceId=abc123 | requestId=019ecb16... | bizId=265167532119162880 | agentName=agt_xxx
```

### 步骤3: 用提取的ID查询MongoDB

```javascript
// 切换环境
switch_env({ env: "dev" })

// 查询 log_llm_agent_main
query_mongodb({
  collection: "log_llm_agent_main",
  filter: { "requestId": "019ecb16..." },
  limit: 50
})

// 查询所有关联的 requestIds
query_mongodb({
  collection: "log_llm_agent_main",
  filter: { "bizId": "265167532119162880" },
  projection: { "requestId": 1, "agentName": 1, "createTime": 1 },
  limit: 100
})
```

---

## MCP查询示例

### 查询某个请求的所有步骤

```javascript
// 1. 切换环境
switch_env({ env: "dev" })

// 2. 查询步骤日志
query_mongodb({
  collection: "log_llm_task_step",
  filter: { "requestId": "请求ID" },
  projection: { "step": 1, "template": 1, "success": 1, "endTime": 1 },
  limit: 50
})
```

### 查询HTTP请求详情

```javascript
query_mongodb({
  collection: "log_llm_http_request",
  filter: { "requestId": "请求ID" },
  projection: { "url": 1, "method": 1, "requestBody": 1, "responseBody": 1, "success": 1 },
  limit: 100
})
```

### 查询API配置

```javascript
// 根据名称查询
query({
  sql: "SELECT code, name, url_server, url_path, method FROM llm_tool_api WHERE name = ? LIMIT 10",
  params: ["API名称"]
})

// 根据编码查询
query({
  sql: "SELECT * FROM llm_tool_api WHERE code = ?",
  params: ["api_code"]
})
```

### 查看日志表结构

```javascript
// MySQL
describe_table({ table: "llm_tool_api" })

// MongoDB - 查询一条记录看结构
query_mongodb({
  collection: "log_llm_task_step",
  filter: {},
  limit: 1
})
```

---

## 常用查询模式

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

### 根据 requestIds 批量查询

```javascript
// 查询任务详情
query_mongodb({
  collection: "log_llm_task_detail",
  filter: { "requestId": { "$in": ["req1", "req2", "req3"] } },
  limit: 200
})

// 查询执行步骤
query_mongodb({
  collection: "log_llm_task_step",
  filter: { "requestId": { "$in": ["req1", "req2"] } },
  limit: 200
})
```

### 根据 taskName 过滤步骤

```javascript
// 查询特定taskName的执行记录
query_mongodb({
  collection: "log_llm_task_detail",
  filter: {
    "requestId": { "$in": ["req1", "req2"] },
    "taskName": { "$in": ["n_tool_confirm", "n_map_list", "n_result"] }
  },
  projection: { "taskName": 1, "input": 1, "output": 1, "success": 1, "endTime": 1 },
  limit: 100
})
```

### 根据 logLlmAgentContextId 查询上下文

```javascript
// 1. 先获取 logLlmAgentContextId
query_mongodb({
  collection: "log_llm_agent_main",
  filter: { "bizId": "277267362927394816" },
  projection: { "logLlmAgentContextId": 1 },
  limit: 50
})

// 2. 查询上下文详情
query_mongodb({
  collection: "log_llm_agent_context",
  filter: { "_id": { "$in": [123, 456] } },
  limit: 50
})
```

### 查询失败的步骤

```javascript
query_mongodb({
  collection: "log_llm_task_detail",
  filter: {
    "requestId": { "$in": ["req1", "req2"] },
    "success": false
  },
  projection: { "taskName": 1, "input": 1, "output": 1 },
  limit: 50
})
```

---

## Java 实体类

日志表对应的 Java DTO，源码位于 `llm-agent-core/src/main/java/com/llm/agentcore/service/bo/log/`。

### LogLlmTaskDetailDto

**文件路径**: `llm-agent-core/.../service/bo/log/LogLlmTaskDetailDto.java`

**核心字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `requestId` | String | 请求ID |
| `agentName` | String | **任务所在的Agent名称**（用于定位agent代码） |
| `taskName` | String | 任务名称（agent脚本每行开头的变量名） |
| `taskUniqueName` | String | 任务的唯一名字 |
| `taskType` | String | 任务类型：expression/foreach/when |
| `fullPath` | String | 任务的完整路径 |
| `dynamicPlanDetailId` | Long | 动态计划详情ID |
| `taskIndex` | Integer | 任务执行步数 |
| `success` | Boolean | 是否成功 |
| `result` | String | 任务结果 |
| `resultType` | Integer | 结果类型 |

**关键说明**：
- `agentName` 字段可直接用于查询 `llm_agent_store.agent_name`
- `taskName` 对应 agent 脚本中每行的第一个标识符

### LogLlmAgentMainDto

**文件路径**: `llm-agent-core/.../service/bo/log/LogLlmAgentMainDto.java`

**核心字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long | 主键 |
| `agentId` | Long | Agent运行ID |
| `requestId` | String | 请求ID |
| `bizId` | String | 业务ID = LLMAgentInstance.id |
| `topAgentName` | String | 顶层agent名 |
| `entranceAgent` | Boolean | 是否为入口agent |
| `taskStatus` | Integer | 任务状态：1-运行中, 3-挂起, 5-结束 |
| `agentStatus` | Integer | 全局agent状态 |
| `success` | Boolean | 是否成功 |
| `createTime` | LocalDateTime | 创建时间 |
| `agentEndTime` | LocalDateTime | 结束时间 |

**关键说明**：
- `bizId` = `llm_agent_instance.ID`
- 一条 requestId 可能有多条 agentId 记录（agent调起agent）

### 关联关系图

```
requestId (请求)
    │
    ├── agentId=1 (顶层Agent)
    │       │
    │       └── agentName="agt_xxx"
    │           ├── taskName="n_step1"
    │           ├── taskName="n_step2"
    │           └── taskName="n_result"
    │
    ├── agentId=2 (子Agent)
    │       │
    │       └── agentName="agt_sub_yyy"
    │           ├── taskName="n_sub1"
    │           └── taskName="n_sub2"
    │
    └── agentId=3 (另一个顶层Agent)
            │
            └── agentName="agt_zzz"
                └── taskName="n_zzz1"
```

### agentName 定位代码流程

1. **查询日志获取 agentName**：

```javascript
query_mongodb({
  collection: "log_llm_task_detail",
  filter: { "requestId": "019ece6da8547a6b866c1e0e05a74994" },
  projection: { "agentName": 1, "taskName": 1, "success": 1 },
  limit: 100
})
```

2. **根据 agentName 查询 agent 脚本**：

```javascript
// 方式1: 从 llm_agent_store 查
query({
  sql: "SELECT id, agent_name, agent_content FROM llm_agent_store WHERE agent_name = ?",
  params: ["查到的agentName"]
})

// 方式2: 从 bizId 查 instance 再查 store
query({
  sql: """
    SELECT s.id, s.agent_name, s.agent_content 
    FROM llm_agent_store s 
    JOIN llm_agent_instance i ON i.agent_store_id = s.id 
    WHERE i.ID = ?
  """,
  params: ["bizId"]
})
```

3. **定位 agent 脚本文件**：

根据 agent 存储路径规范：
- **数据库存储**：`llm_agent_store.agent_content`
- **文件系统**：`{data_path}/system/agt/{package}/{agent_name}.txt`

示例：
- agentName = `agt_hello` → 文件路径 = `.../agt/assistant/agt_hello.txt`
- agentName = `agt_build_project` → 文件路径 = `.../agt/smart_build_deploy/agt_build_project.txt`

### taskName 定位代码行

`taskName` 对应 agent 脚本中每行开头的第一个标识符：

| 脚本写法 | taskName | 说明 |
|---------|----------|------|
| `n_result, act_api.xxx` | `n_result` | 有变量赋值 |
| `tpl_extract_params, psr_json` | `tpl_extract_params` | 模板调用 |
| `psr_json` | `psr_json` | 无变量函数 |
| `when('n_result', {...})` | `n_result` | 条件分支 |
| `foreach('n_item', {{n_list}})` | `n_item` | 循环遍历 |
