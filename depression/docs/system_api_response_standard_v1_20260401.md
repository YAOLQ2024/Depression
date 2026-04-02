# 抑郁症辅助干预系统统一返回结构表（V1）

更新时间：2026-04-01

文档文件名：`system_api_response_standard_v1_20260401.md`

## 1. 文档定位

本文档用于统一当前系统所有接口的返回结构，作为后续 `OpenAPI（接口描述标准）`、前后端联调、组员独立接入和日志排查的公共约束。

本文档重点回答以下问题：

1. 所有接口是否必须有统一外层结构
2. 成功返回和失败返回应该长什么样
3. `health（健康检查）` 和 `meta（元信息）` 应该怎么返回
4. 列表接口、分页接口应该怎么返回
5. 流式接口 `SSE（服务器发送事件）` 应该怎么返回
6. `HTTP Status Code（HTTP 状态码）` 和业务 `code（业务码）` 应该如何配合使用

## 2. 统一返回设计原则

当前阶段统一遵循以下原则：

1. 所有普通接口统一返回 `JSON（结构化数据）`
2. 所有普通接口统一使用“外层包裹结构”
3. 所有模块都必须保留 `code / message / data / request_id / timestamp`
4. 业务结果只允许放在 `data` 中，不允许散落在顶层
5. `HTTP Status Code（HTTP 状态码）` 表达传输层结果，`code（业务码）` 表达业务层结果
6. 模块之间允许 `data` 内部字段不同，但外层结构必须保持一致
7. 流式接口可以例外，但事件体仍建议保持统一 JSON 风格

## 3. 标准外层返回结构

### 3.1 顶层结构定义

所有普通接口统一返回以下结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "b7fbb8e7-4a23-4c85-a95c-bf7d8c4d91be",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

### 3.2 顶层字段说明表

| 字段名 | 是否必填 | 类型 | 含义 | 示例 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `code` | 是 | `integer（整数）` | 业务状态码 | `0` | `0` 表示成功，非 `0` 表示失败或提醒 |
| `message` | 是 | `string（字符串）` | 人类可读说明 | `"ok"` | 面向前端开发、测试和日志排查 |
| `data` | 是 | `object（对象）` 或 `null` | 业务结果主体 | `{}` | 成功时通常为对象，失败时通常为 `null` |
| `request_id` | 是 | `string（字符串）` | 单次请求唯一标识 | `"req-20260401-001"` | 用于日志检索、链路追踪、联调对齐 |
| `timestamp` | 是 | `string（字符串）` | 响应时间 | `"2026-04-01T15:30:00+08:00"` | 统一使用 `ISO 8601（国际时间格式）` |

## 4. 成功返回结构表

### 4.1 通用成功返回

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "result": "success"
  },
  "request_id": "req-20260401-001",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

### 4.2 成功返回字段约束表

| 字段 | 约束 |
| --- | --- |
| `code` | 必须为 `0` |
| `message` | 推荐固定为 `"ok"` 或明确成功说明 |
| `data` | 必须存在，哪怕为空对象也要返回 |
| `request_id` | 必须可追踪到网关或模块日志 |
| `timestamp` | 必须由服务端生成，不由客户端传入 |

### 4.3 空结果成功返回

当接口执行成功，但没有具体业务结果时，建议返回空对象，不建议省略 `data`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req-20260401-002",
  "timestamp": "2026-04-01T15:31:00+08:00"
}
```

适用场景：

1. 登出成功
2. 删除成功
3. 配置更新成功但无额外返回值

### 4.4 成功但带提醒的返回

对于 `risk-stratification（初步风险分层与安全建议能力）` 这类接口，可能会出现“请求成功，但需要优先提醒用户采取其他举措”的情况。

这类情况不建议当成错误返回，建议：

1. `HTTP Status Code（HTTP 状态码）` 仍返回 `200`
2. 业务 `code（业务码）` 使用 `1xxx`
3. 在 `data` 中明确给出 `referral_recommended（建议就医）`、`emergency_notice（紧急提示）`、`allow_continue（允许继续）`

示例：

```json
{
  "code": 1001,
  "message": "referral_recommended",
  "data": {
    "result": {
      "risk_level": "high",
      "risk_score": 82,
      "referral_recommended": true,
      "allow_continue": true
    }
  },
  "request_id": "req-20260401-002A",
  "timestamp": "2026-04-01T15:31:30+08:00"
}
```

## 5. 错误返回结构表

### 5.1 通用错误返回

```json
{
  "code": 4001,
  "message": "missing required field: audio_url",
  "data": null,
  "request_id": "req-20260401-003",
  "timestamp": "2026-04-01T15:32:00+08:00"
}
```

### 5.2 错误返回字段约束表

| 字段 | 约束 |
| --- | --- |
| `code` | 必须为非 `0` 的业务错误码 |
| `message` | 必须给出明确可读原因 |
| `data` | 失败时建议固定为 `null` |
| `request_id` | 必须保留，便于问题排查 |
| `timestamp` | 必须保留，便于定位时间点 |

### 5.3 建议错误码分段

| 错误码段 | 含义 | 说明 |
| --- | --- | --- |
| `0` | 成功 | 正常完成请求 |
| `1xxx` | 成功但带提醒 | 请求成功，但需要额外提示 |
| `4xxx` | 客户端请求错误 | 参数缺失、格式错误、鉴权失败等 |
| `5xxx` | 服务内部错误 | 代码异常、数据库异常、未捕获错误 |
| `6xxx` | 外部依赖错误 | 外部模型、外部服务、设备桥接不可用 |
| `7xxx` | 算法或模型错误 | 算法未加载、当前仅支持 `mock（模拟）` 模式 |

### 5.4 初始通用错误码表

| 错误码 | 名称 | 中文含义 | 推荐使用场景 |
| --- | --- | --- | --- |
| `4001` | `missing_required_field` | 缺少必填字段 | 请求体字段缺失 |
| `4002` | `invalid_field_format` | 字段格式非法 | 类型错误、时间格式错误、枚举值非法 |
| `4003` | `auth_failed` | 用户未登录或鉴权失败 | 未登录、令牌失效、权限不足 |
| `4004` | `resource_not_found` | 资源不存在 | 用户、记录、模型资源不存在 |
| `4009` | `operation_not_allowed` | 当前状态不允许该操作 | 流程未到达、状态冲突 |
| `5001` | `internal_service_error` | 服务内部异常 | 代码抛错、数据库内部报错 |
| `6001` | `upstream_service_unavailable` | 外部服务不可用 | LLM、RAG、设备代理服务不可用 |
| `7001` | `model_not_loaded` | 当前算法模块未加载 | 模型尚未初始化 |
| `7002` | `mock_only_mode` | 当前模块仅支持模拟模式 | 功能未正式接入，仅能返回模拟数据 |

## 6. HTTP 状态码与业务码对照表

工程上建议同时使用：

1. `HTTP Status Code（HTTP 状态码）`
2. `code（业务码）`

推荐对照关系如下：

| HTTP 状态码 | 名称 | 建议业务码范围 | 使用说明 |
| --- | --- | --- | --- |
| `200` | `OK` | `0` 或 `1xxx` | 请求被正常处理，业务成功 |
| `400` | `Bad Request` | `4001`、`4002` | 参数缺失、参数格式错误 |
| `401` | `Unauthorized` | `4003` | 未登录或鉴权失败 |
| `404` | `Not Found` | `4004` | 资源不存在 |
| `409` | `Conflict` | `4009` | 状态冲突、流程不允许 |
| `500` | `Internal Server Error` | `5001` | 服务内部异常 |
| `502` | `Bad Gateway` | `6001` | 依赖服务异常 |
| `503` | `Service Unavailable` | `6001`、`7001` | 服务未就绪、模型未加载 |

补充说明：

1. 不建议所有错误都返回 `200`
2. 也不建议只靠 `HTTP 状态码` 判断业务成败
3. 前端应同时判断 `HTTP 状态码` 和 `code`

## 7. 常见接口类型返回结构表

### 7.1 主业务接口返回

这是最常见的接口类型，例如评分、分析、生成、规划、执行等。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "task-001",
    "result": {
      "risk_level": "medium"
    }
  },
  "request_id": "req-20260401-004",
  "timestamp": "2026-04-01T15:33:00+08:00"
}
```

### 7.2 列表接口返回

列表接口建议统一使用 `items（数据项列表）` 和 `pagination（分页信息）`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "record_id": "r-001"
      },
      {
        "record_id": "r-002"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 2,
      "has_more": false
    }
  },
  "request_id": "req-20260401-005",
  "timestamp": "2026-04-01T15:34:00+08:00"
}
```

列表接口字段建议：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `items` | `array（数组）` | 当前页数据列表 |
| `pagination.page` | `integer（整数）` | 当前页码 |
| `pagination.page_size` | `integer（整数）` | 每页条数 |
| `pagination.total` | `integer（整数）` | 总条数 |
| `pagination.has_more` | `boolean（布尔值）` | 是否还有下一页 |

### 7.3 health 健康检查接口返回

所有二级能力模块必须提供：

1. `GET /health`

建议结构如下：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "up",
    "mode": "mock",
    "model_loaded": false,
    "version": "v1"
  },
  "request_id": "req-20260401-006",
  "timestamp": "2026-04-01T15:35:00+08:00"
}
```

`health（健康检查）` 建议字段表：

| 字段 | 类型 | 含义 | 示例 |
| --- | --- | --- | --- |
| `status` | `string（字符串）` | 服务状态 | `"up"` |
| `mode` | `string（字符串）` | 当前模式 | `"mock"`、`"prod"` |
| `model_loaded` | `boolean（布尔值）` | 模型是否加载成功 | `true` |
| `version` | `string（字符串）` | 当前模块版本 | `"v1"` |

### 7.4 meta 元信息接口返回

所有二级能力模块必须提供：

1. `GET /meta`

建议结构如下：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "module": "speech",
    "capability": "speech-transcribe",
    "module_zh": "语音处理模块",
    "capability_zh": "语音转写能力",
    "version": "v1",
    "owner": "team-a",
    "input_schema_version": "1.0.0",
    "output_schema_version": "1.0.0",
    "supports_mock": true
  },
  "request_id": "req-20260401-007",
  "timestamp": "2026-04-01T15:36:00+08:00"
}
```

`meta（元信息）` 建议字段表：

| 字段 | 类型 | 含义 | 示例 |
| --- | --- | --- | --- |
| `module` | `string（字符串）` | 一级模块英文名 | `"speech"` |
| `capability` | `string（字符串）` | 二级能力英文名 | `"speech-transcribe"` |
| `module_zh` | `string（字符串）` | 一级模块中文名 | `"语音处理模块"` |
| `capability_zh` | `string（字符串）` | 二级能力中文名 | `"语音转写能力"` |
| `version` | `string（字符串）` | 接口版本 | `"v1"` |
| `owner` | `string（字符串）` | 当前模块负责人或小组 | `"team-a"` |
| `input_schema_version` | `string（字符串）` | 输入结构版本 | `"1.0.0"` |
| `output_schema_version` | `string（字符串）` | 输出结构版本 | `"1.0.0"` |
| `supports_mock` | `boolean（布尔值）` | 是否支持模拟模式 | `true` |

## 8. data 字段内部结构建议

统一返回结构只固定外层，不强行固定所有业务字段，但建议遵循下面的约定：

### 8.1 单结果接口

适用场景：

1. 单次量表评分
2. 单次语音转写
3. 单次表情分析
4. 单次脑电分析

建议：

```json
{
  "data": {
    "result": {}
  }
}
```

### 8.2 聚合型接口

适用场景：

1. 初步风险分层模块
2. 个性化调控决策模块
3. 报告生成模块

建议：

```json
{
  "data": {
    "inputs": {},
    "result": {},
    "explanation": {}
  }
}
```

### 8.3 任务型接口

如果后续有异步任务，例如长时间报告生成、批量分析，建议返回：

```json
{
  "code": 0,
  "message": "accepted",
  "data": {
    "task_id": "task-001",
    "status": "queued"
  },
  "request_id": "req-20260401-008",
  "timestamp": "2026-04-01T15:37:00+08:00"
}
```

## 9. SSE 流式返回结构建议

对于聊天流、脑电流、摄像头分析流等实时场景，可以使用 `SSE（服务器发送事件）`，但事件体仍建议保持 JSON 风格。

建议事件格式：

```text
event: message
data: {"code":0,"message":"ok","data":{"chunk":"你好"},"request_id":"req-20260401-009","timestamp":"2026-04-01T15:38:00+08:00"}
```

建议约束：

1. 流式事件体也保留 `code / message / data / request_id / timestamp`
2. 流式分片内容放进 `data`
3. 最后一条事件建议包含 `done=true`

结束事件示例：

```text
event: done
data: {"code":0,"message":"ok","data":{"done":true},"request_id":"req-20260401-009","timestamp":"2026-04-01T15:38:30+08:00"}
```

## 10. 模块实现时禁止出现的情况

为了保证统一性，以下做法当前不允许：

1. 有的接口返回顶层 `status`，有的返回顶层 `success`
2. 有的接口省略 `request_id`
3. 有的接口成功时返回字符串，失败时返回对象
4. 有的接口把业务字段直接放在顶层，不放进 `data`
5. 有的接口错误时返回 `HTML（网页错误页）`
6. 不同模块同一种错误却使用完全不同的错误码

## 11. 当前建议冻结的最小公共结构

从现在开始，建议所有模块最少固定以下公共结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "req-xxx",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

也就是说：

1. 允许模块内部的 `data` 继续细化
2. 不允许删掉顶层五个公共字段

## 12. 建议你下一步继续做的事

基于这份统一返回结构表，下一步最适合继续产出：

1. `OpenAPI（接口描述标准）` 草稿
2. `health / meta / 主接口` 模板清单
3. `组员接入说明`

如果只继续做一件事，优先级最高的是：

`把 11 个一级模块的 health / meta / 主接口 先写进 OpenAPI 草稿`
