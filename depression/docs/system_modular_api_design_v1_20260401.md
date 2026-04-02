# 抑郁症辅助干预系统模块化接口设计草案（V1）

更新时间：2026-04-01

文档文件名：`system_modular_api_design_v1_20260401.md`

## 1. 文档定位

本文档用于明确当前系统的模块划分、接口边界、命名规则和接入规范。

这不是“最终定稿”，而是当前 V1 阶段的工程设计草案，目标是先把系统设计成：

1. 模块解耦
2. 接口统一
3. 返回结构统一
4. 方便多人并行开发
5. 方便后续新增模态或替换算法

本文档优先服务以下场景：

1. 给老师汇报当前系统设计思路
2. 给组员分工和约定模块边界
3. 给后续 FastAPI 化或服务化改造提供统一依据

## 2. 设计目标与边界

### 2.1 当前目标

当前阶段的核心目标不是一次性重写整个系统，而是先建立一套可扩展、可联调、可替换的模块化接口标准。

当前 V1 采用：

1. `11 个一级模块`
2. `12 个二级能力模块`

说明：

1. 一级模块表示业务域边界。
2. 二级能力模块表示当前可独立接入、独立调试、独立替换的能力单元。
3. 当前划分为 V1 草案，后续允许增加、合并、拆分。
4. 后续即使模块数量变化，也应尽量保持接口契约稳定。

### 2.2 当前不追求的目标

以下内容不作为本阶段的强制目标：

1. 一次性把现有 Flask 全部重写为 FastAPI
2. 一次性把所有旧页面完全替换
3. 所有模态都在 V1 阶段形成稳定闭环
4. 所有原始音频、视频、脑电数据全部落库

## 3. 总体架构原则

### 3.1 核心原则

系统设计遵循以下原则：

1. `前端只认接口，不认内部实现`
2. `模块之间只通过标准 JSON 契约交互`
3. `一个模块只负责一个清晰职责`
4. `算法未完成时，也要先提供 Mock 接口`
5. `允许模块演进，但尽量不破坏接口`

### 3.2 总体链路

```text
用户/UI
-> 入口网关或 Web 层
-> 一级业务模块
-> 二级能力模块
-> 风险分层模块
-> 引导问诊补全画像
-> 个性化调控模块
-> 历史记录与再评估闭环
```

### 3.3 五模态在主链中的位置

当前系统面向的五模态结果输入为：

1. 量表模态
2. 文本模态
3. 语音模态
4. 表情模态
5. 脑电模态

其中：

1. 量表模态是当前最稳定的主判定基础。
2. 文本模态用于补全语义画像和风险线索，不能删除。
3. 语音模态分为“语音转写”和“语音情绪识别”两条能力。
4. 表情模态和脑电模态当前属于增强输入，不建议在 V1 阶段作为唯一主判定依据。

推荐主链逻辑：

```text
基础建档信息
+ 虚拟医生偏好
+ 量表结果
+ 作答过程多模态结果
-> 初步风险分层与安全建议
-> 引导问诊补全画像
-> 个性化调控决策
-> 调控执行
-> 历史记录与再评估
```

## 4. 一级模块定义（11 个）

| 一级模块英文名 | 一级模块中文名 | 核心职责 | 当前状态 |
| --- | --- | --- | --- |
| `auth-profile` | 身份认证与用户建档模块 | 登录、注册、用户基础信息、患者画像基础档案 | 部分已有 |
| `persona` | 虚拟医生与交互角色模块 | 虚拟医生选择、交互风格设定、语音播报偏好 | 规划中 |
| `assessment` | 量表评估模块 | PHQ-9、GAD-7、SDS 等量表的填写、评分、结果保存 | 已有基础 |
| `text-dialogue` | 文本对话与引导问诊模块 | 在初步风险分层之后进行必经式问诊，补全画像、提取语义线索、生成结构化摘要 | 部分已有 |
| `speech` | 语音处理模块 | 语音输入相关能力的统一业务归口 | 部分已有 |
| `emotion` | 表情识别模块 | 摄像头采集、表情分析、情绪统计摘要 | 已有基础 |
| `eeg` | 脑电信号模块 | EEG 接入、特征获取、分类与状态输出 | 部分已有 |
| `risk-assessment` | 风险评估与安全建议模块 | 聚合建档信息、量表结果和作答过程多模态摘要，进行初步风险分层、阈值判断和安全建议 | 规划中 |
| `intervention` | 个性化调控与执行模块 | 基于补全后的用户画像和风险分层结果生成调控决策、内容推荐与执行反馈 | 规划中 |
| `history-report` | 历史记录与报告模块 | 历史记录、评估结果、趋势、报告生成 | 部分已有 |
| `admin-settings` | 后台管理与系统设置模块 | 后台管理、研究数据查看、系统配置、调试开关 | 部分已有 |

## 5. 二级能力模块定义（12 个）

说明：二级能力模块是当前建议给组员独立对接和独立开发的最小能力单元。

| 所属一级模块 | 二级能力英文名 | 二级能力中文名 | 说明 |
| --- | --- | --- | --- |
| `auth-profile` | `identity-access` | 身份认证与档案能力 | 负责登录、注册、患者基础档案 |
| `persona` | `virtual-clinician` | 虚拟医生选择能力 | 负责角色选择、风格偏好、播报偏好 |
| `assessment` | `scale-screening` | 结构化量表筛查能力 | 负责量表填写、计分、结果输出 |
| `text-dialogue` | `guided-conversation` | 引导式文本问诊能力 | 负责在初步风险分层之后补全画像、提取语义线索并生成摘要 |
| `speech` | `speech-transcribe` | 语音转写能力 | 负责普通话与方言转文字 |
| `speech` | `speech-emotion` | 语音情绪识别能力 | 负责语音语气、情绪、声学特征分析 |
| `emotion` | `facial-affect` | 面部表情情绪识别能力 | 负责摄像头表情识别与摘要 |
| `eeg` | `eeg-sensing` | 脑电采集与分析能力 | 负责 EEG 波形、特征和分类 |
| `risk-assessment` | `risk-stratification` | 初步风险分层与安全建议能力 | 聚合初始结果并输出风险等级、阈值命中情况和就医建议 |
| `intervention` | `intervention-decision` | 个性化调控决策能力 | 基于补全后的画像输出适合当前状态的调控方式与方案 |
| `history-report` | `record-reporting` | 记录与报告能力 | 负责历史、趋势、阶段总结和报告 |
| `admin-settings` | `system-ops` | 系统管理与配置能力 | 负责后台、设置、调试、审计开关 |

## 6. 为什么文本模态必须保留

文本模态不是多余模态，而是系统中的“语义模态”。

它的来源包括：

1. 用户键盘输入的文字
2. 用户语音经转写后的文字
3. 系统引导问诊得到的文字回答
4. 大模型生成的结构化摘要

文本模态的主要作用：

1. 补全量表无法覆盖的细节信息
2. 获取近期事件、睡眠、饮食、学习、工作、人际等上下文
3. 识别风险表达，如绝望、自伤、失控、失眠恶化等
4. 为后续调控决策提供更细粒度语义依据

因此，文本模态在当前主链中的关键位置是：

`初步风险分层之后 -> 引导问诊补全画像 -> 个性化调控决策之前`

也就是说：

1. `text-dialogue` 不是可有可无的闲聊模块，而是当前主链中的必经步骤。
2. 它不负责最终风险分层，而是负责为后续个性化调控决策补全画像。

## 7. 统一接口设计规范

### 7.1 接口协议

当前建议统一采用：

1. HTTP/HTTPS
2. JSON 作为主返回格式
3. 实时连续流场景允许使用 SSE

仅以下场景允许例外：

1. 实时聊天流式输出
2. EEG 实时流
3. 摄像头实时流

即便使用 SSE，事件体也应尽量保持 JSON 结构。

### 7.2 URL 命名规则

统一前缀：

```text
/api/v1/
```

推荐路径规则：

```text
/api/v1/{一级模块}/{二级能力}/{动作}
```

示例：

```text
/api/v1/assessment/scale-screening/submit
/api/v1/speech/speech-transcribe/run
/api/v1/speech/speech-emotion/analyze
/api/v1/risk-assessment/risk-stratification/score
/api/v1/text-dialogue/guided-conversation/run
/api/v1/history-report/record-reporting/generate
```

说明：

1. `v1` 表示版本。
2. 一级模块用于表达业务域。
3. 二级能力用于表达具体接入能力。
4. 动作名建议从固定词表中选择，不要自由发挥。

推荐动作词表：

1. `create` 创建
2. `get` 获取单项
3. `list` 获取列表
4. `update` 更新
5. `delete` 删除
6. `submit` 提交
7. `run` 执行
8. `analyze` 分析
9. `score` 评分
10. `plan` 规划
11. `generate` 生成
12. `health` 健康检查
13. `meta` 元信息

### 7.3 标准返回结构

所有普通 JSON 接口统一返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "b7fbb8e7-4a23-4c85-a95c-bf7d8c4d91be",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

约定：

1. `code=0` 表示成功
2. `message` 用于人类可读说明
3. `data` 用于业务结果
4. `request_id` 用于联调和日志追踪
5. `timestamp` 统一使用带时区的 ISO 8601 字符串

### 7.4 标准错误结构

```json
{
  "code": 4001,
  "message": "missing required field: audio_url",
  "data": null,
  "request_id": "b7fbb8e7-4a23-4c85-a95c-bf7d8c4d91be",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

建议错误码分段：

1. `1xxx` 通用成功与提醒
2. `4xxx` 客户端请求错误
3. `5xxx` 服务内部错误
4. `6xxx` 外部依赖错误
5. `7xxx` 算法或模型不可用

建议初始保留以下通用错误码：

| 错误码 | 含义 |
| --- | --- |
| `4001` | 缺少必填字段 |
| `4002` | 字段格式非法 |
| `4003` | 用户未登录或鉴权失败 |
| `4004` | 资源不存在 |
| `4009` | 当前状态不允许该操作 |
| `5001` | 服务内部异常 |
| `6001` | 外部模型服务不可用 |
| `7001` | 当前算法模块未加载 |
| `7002` | 当前模块仅支持 Mock 模式 |

### 7.5 必备辅助接口

每个二级能力模块都必须提供两个辅助接口：

1. `health` 健康检查接口
2. `meta` 元信息接口

示例：

```text
GET /api/v1/speech/speech-transcribe/health
GET /api/v1/speech/speech-transcribe/meta
```

`health` 建议返回：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "up",
    "mode": "mock",
    "model_loaded": false
  },
  "request_id": "req-001",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

`meta` 建议返回：

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
  "request_id": "req-001",
  "timestamp": "2026-04-01T15:30:00+08:00"
}
```

### 7.6 请求头建议

推荐统一传递以下请求头：

1. `X-Request-Id` 请求唯一标识
2. `X-Trace-Id` 链路追踪标识
3. `X-User-Id` 用户 ID
4. `X-User-Role` 用户角色
5. `X-Source-System` 请求来源系统

说明：

1. 前端可以只传 `X-Request-Id`
2. 网关层负责补齐其余头信息
3. 后续切换 FastAPI、微服务或消息队列时，这套头信息仍然可复用

## 8. 各模块建议接口清单

说明：以下清单是 V1 推荐接口，不要求一次性全部做完，但建议后续都按这个风格补齐。

### 8.1 `auth-profile` 身份认证与用户建档模块

二级能力：`identity-access` 身份认证与档案能力

建议接口：

1. `POST /api/v1/auth-profile/identity-access/register`
2. `POST /api/v1/auth-profile/identity-access/login`
3. `POST /api/v1/auth-profile/identity-access/logout`
4. `GET /api/v1/auth-profile/identity-access/profile/{user_id}`
5. `PUT /api/v1/auth-profile/identity-access/profile/{user_id}`
6. `GET /api/v1/auth-profile/identity-access/health`
7. `GET /api/v1/auth-profile/identity-access/meta`

### 8.2 `persona` 虚拟医生与交互角色模块

二级能力：`virtual-clinician` 虚拟医生选择能力

建议接口：

1. `GET /api/v1/persona/virtual-clinician/options`
2. `POST /api/v1/persona/virtual-clinician/select`
3. `GET /api/v1/persona/virtual-clinician/current/{user_id}`
4. `GET /api/v1/persona/virtual-clinician/health`
5. `GET /api/v1/persona/virtual-clinician/meta`

### 8.3 `assessment` 量表评估模块

二级能力：`scale-screening` 结构化量表筛查能力

建议接口：

1. `GET /api/v1/assessment/scale-screening/list`
2. `POST /api/v1/assessment/scale-screening/submit`
3. `GET /api/v1/assessment/scale-screening/result/{record_id}`
4. `GET /api/v1/assessment/scale-screening/latest`
5. `GET /api/v1/assessment/scale-screening/draft/{scale_slug}`
6. `POST /api/v1/assessment/scale-screening/draft/save`
7. `GET /api/v1/assessment/scale-screening/health`
8. `GET /api/v1/assessment/scale-screening/meta`

说明：

1. `PHQ-9（患者健康问卷）` 与 `GAD-7（广泛性焦虑量表）` 当前也已支持服务端草稿暂存与恢复，不再只有 `SDS（抑郁自评量表）` 支持进度保存。
2. 草稿接口用于 `save draft（保存草稿） / resume later（下次继续）`，未完成量表草稿不参与 `risk-assessment（风险评估与安全建议模块）`。

### 8.4 `text-dialogue` 文本对话与引导问诊模块

二级能力：`guided-conversation` 引导式文本问诊能力

建议接口：

1. `POST /api/v1/text-dialogue/guided-conversation/run`
2. `POST /api/v1/text-dialogue/guided-conversation/summary`
3. `GET /api/v1/text-dialogue/guided-conversation/history/{user_id}`
4. `GET /api/v1/text-dialogue/guided-conversation/health`
5. `GET /api/v1/text-dialogue/guided-conversation/meta`

说明：

1. 该模块在当前主链中位于 `risk-stratification` 之后、`intervention-decision` 之前。
2. 当前默认它是必经步骤，不再单独评估“画像是否足够完整”。
3. 其核心目标是让 `LLM（大语言模型）` 围绕信息缺口进行有目的追问，而不是自由聊天。

### 8.5 `speech` 语音处理模块

#### 8.5.1 `speech-transcribe` 语音转写能力

建议接口：

1. `POST /api/v1/speech/speech-transcribe/run`
2. `GET /api/v1/speech/speech-transcribe/health`
3. `GET /api/v1/speech/speech-transcribe/meta`

#### 8.5.2 `speech-emotion` 语音情绪识别能力

建议接口：

1. `POST /api/v1/speech/speech-emotion/analyze`
2. `GET /api/v1/speech/speech-emotion/health`
3. `GET /api/v1/speech/speech-emotion/meta`

说明：

1. 两个二级能力建议分开开发、分开部署、分开调试。
2. 上层如果需要，也可以增加一个聚合接口：

```text
POST /api/v1/speech/run
```

由语音模块在内部同时调用转写和情绪两个能力，再统一输出。

### 8.6 `emotion` 表情识别模块

二级能力：`facial-affect` 面部表情情绪识别能力

建议接口：

1. `POST /api/v1/emotion/facial-affect/analyze`
2. `GET /api/v1/emotion/facial-affect/statistics/{session_id}`
3. `POST /api/v1/emotion/facial-affect/reset`
4. `GET /api/v1/emotion/facial-affect/health`
5. `GET /api/v1/emotion/facial-affect/meta`

### 8.7 `eeg` 脑电信号模块

二级能力：`eeg-sensing` 脑电采集与分析能力

建议接口：

1. `GET /api/v1/eeg/eeg-sensing/channels`
2. `GET /api/v1/eeg/eeg-sensing/classification`
3. `GET /api/v1/eeg/eeg-sensing/history`
4. `GET /api/v1/eeg/eeg-sensing/stream`
5. `GET /api/v1/eeg/eeg-sensing/health`
6. `GET /api/v1/eeg/eeg-sensing/meta`

说明：

1. `stream` 可使用 SSE。
2. 即便使用 SSE，单条事件体也建议输出 JSON。

### 8.8 `risk-assessment` 风险评估与安全建议模块

二级能力：`risk-stratification` 初步风险分层与安全建议能力

建议接口：

1. `POST /api/v1/risk-assessment/risk-stratification/score`
2. `GET /api/v1/risk-assessment/risk-stratification/health`
3. `GET /api/v1/risk-assessment/risk-stratification/meta`

说明：

1. 这是后续最关键的聚合节点。
2. 它不直接采集原始数据，而是只接收建档信息、量表结果和作答过程的多模态摘要结果。
3. 它负责的是“初步风险分层、阈值判断和安全建议”，不直接做最终调控内容选择。
4. 即使风险超过就医建议阈值，也建议通过返回字段表达“优先建议外部帮助，但允许继续体验系统调控”。

### 8.9 `intervention` 个性化调控与执行模块

二级能力：`intervention-decision` 个性化调控决策能力

建议接口：

1. `POST /api/v1/intervention/intervention-decision/plan`
2. `POST /api/v1/intervention/intervention-decision/execute`
3. `POST /api/v1/intervention/intervention-decision/feedback`
4. `GET /api/v1/intervention/intervention-decision/health`
5. `GET /api/v1/intervention/intervention-decision/meta`

### 8.10 `history-report` 历史记录与报告模块

二级能力：`record-reporting` 记录与报告能力

建议接口：

1. `GET /api/v1/history-report/record-reporting/timeline/{user_id}`
2. `GET /api/v1/history-report/record-reporting/report/{record_id}`
3. `POST /api/v1/history-report/record-reporting/generate`
4. `GET /api/v1/history-report/record-reporting/health`
5. `GET /api/v1/history-report/record-reporting/meta`

### 8.11 `admin-settings` 后台管理与系统设置模块

二级能力：`system-ops` 系统管理与配置能力

建议接口：

1. `GET /api/v1/admin-settings/system-ops/config`
2. `PUT /api/v1/admin-settings/system-ops/config`
3. `GET /api/v1/admin-settings/system-ops/audit`
4. `GET /api/v1/admin-settings/system-ops/health`
5. `GET /api/v1/admin-settings/system-ops/meta`

## 9. 风险分层与个性化调控输入结构

### 9.1 `risk-stratification` 初步风险分层模块推荐输入结构

后续建档信息、量表结果和作答过程多模态摘要建议先汇总为统一结构，再送入 `risk-assessment` 模块。

建议输入示例：

```json
{
  "user_profile": {
    "user_id": 1001,
    "gender": "female",
    "age_group": "18-25",
    "persona_preference": "warm"
  },
  "assessment": {
    "available": true,
    "scale_type": "PHQ-9",
    "score": 14,
    "severity": "moderate"
  },
  "speech": {
    "available": true,
    "transcript": "我最近总是睡不好，感觉什么都不想做。",
    "emotion": {
      "label": "sad",
      "confidence": 0.82
    }
  },
  "emotion": {
    "available": true,
    "dominant_emotion": "sad",
    "confidence": 0.77
  },
  "eeg": {
    "available": false,
    "classification": null
  }
}
```

关键原则：

1. 未接入的模态不要省略，统一使用 `available=false`
2. 初步风险分层模块不要依赖原始音视频文件
3. 统一传摘要、标签、分值、置信度

### 9.2 `intervention-decision` 个性化调控决策模块推荐输入结构

在完成 `guided-conversation` 之后，建议把补全后的画像、初步风险分层结果和偏好信息送入 `intervention` 模块。

建议输入示例：

```json
{
  "user_profile": {
    "user_id": 1001,
    "gender": "female",
    "age_group": "18-25"
  },
  "persona_preference": {
    "style": "warm",
    "voice": "female_soft"
  },
  "risk_summary": {
    "risk_level": "high",
    "risk_score": 78,
    "referral_recommended": true,
    "allow_continue": true
  },
  "guided_conversation_summary": {
    "summary": "用户最近连续两周睡眠变差，学习压力显著升高，希望先尝试安静陪伴和放松类内容。",
    "needs": ["陪伴", "减压", "助眠"],
    "contraindications": []
  },
  "preferences": {
    "preferred_modalities": ["music", "story"],
    "avoid_modalities": ["intense_video"]
  }
}
```

## 10. 数据与隐私建议

当前阶段建议默认遵循“轻量保存”原则：

1. 默认保存结果摘要，不长期保存大体量原始音视频
2. 原始脑电窗口数据不建议直接长期落库
3. 保存最终评分、标签、摘要、关键特征和时间戳
4. 调试阶段如果需要留原始数据，必须显式标明开关和用途

建议增加以下字段：

1. `consent_flags` 用户授权信息
2. `data_retention_level` 数据保留级别
3. `source_device` 设备来源
4. `algorithm_version` 算法版本

## 11. 版本与兼容策略

为避免后续模块变化导致联调混乱，建议从 V1 开始就采用以下策略：

1. 所有接口统一带版本号：`/api/v1/...`
2. 字段增加优先，字段删除慎用
3. 字段改名必须先保留旧字段一段时间
4. 一级模块允许后续增删合并
5. 二级能力允许继续拆分
6. 但通用返回格式不应轻易变化

一句话总结：

`模块可演进，契约尽量稳定。`

## 12. 给组员的接入要求

任意组员要接入某个模块，至少要交付以下内容：

1. 模块说明
2. `health` 接口
3. `meta` 接口
4. 主业务接口
5. 一份请求示例
6. 一份返回示例
7. Mock 模式
8. 错误码说明

建议组员接入清单：

1. 先实现 Mock 接口，保证前后端可联调
2. 再替换为真实算法
3. 不要等算法完全做完才开始接接口

## 13. 当前阶段建议落地顺序

按工程优先级，建议先做：

1. `assessment` 量表评估模块
2. `risk-assessment` 风险评估与安全建议模块
3. `text-dialogue` 文本对话与引导问诊模块
4. `intervention` 个性化调控与执行模块
5. `speech` 语音处理模块
6. `emotion` 表情识别模块
7. `eeg` 脑电信号模块
8. `history-report` 历史记录与报告模块

原因：

1. 量表是当前主链最稳定的基础
2. 初步风险分层模块决定安全提示、阈值判断和后续页面分流
3. 文本引导问诊是补全画像和接入大模型的必经步骤
4. 个性化调控决策模块承接最终的音乐、视频、文字故事等内容选择
5. 语音、表情、脑电可以先用摘要或 Mock 接口接入

## 14. 本文档的最终口径

当前系统在 V1 阶段，暂定采用：

1. `11 个一级模块`
2. `12 个二级能力模块`

这套划分不是永久不变的终稿，而是当前用于：

1. 系统设计汇报
2. 模块责任划分
3. 接口规范统一
4. 后续 FastAPI 化与服务化改造

后续随着新模态、新页面、新任务链路加入，模块数量允许变化；但统一接口规范、通用返回结构、健康检查和元信息接口应尽量保持稳定。
