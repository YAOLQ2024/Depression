# `risk-assessment（风险评估与安全建议模块）` 详细设计方案（V1）

更新时间：2026-04-01

文档文件名：`risk_assessment_module_design_v1_20260401.md`

## 1. 文档定位

本文档用于细化 `risk-assessment（风险评估与安全建议模块）` 的职责、输入输出、风险挡位、阈值逻辑和接口设计。

这份文档主要解决以下问题：

1. `risk-assessment（风险评估与安全建议模块）` 到底评估什么
2. 它和 `text-dialogue（文本对话与引导问诊模块）`、`intervention（个性化调控与执行模块）` 的边界怎么划
3. 初步风险分层怎么做才符合当前项目定位
4. 高风险用户是否拦截，还是提示后允许继续
5. 后续接口和代码应该按什么结构落地

本文档是当前 `V1（第一版）` 方案，目标是先形成一个可实现、可联调、可逐步替换的工程基线。

## 2. 模块在主链中的位置

当前系统主链统一按下面这条逻辑理解：

```text
assessment（量表评估模块）
-> risk-assessment（风险评估与安全建议模块）
-> text-dialogue（文本对话与引导问诊模块）
-> intervention（个性化调控与执行模块）
-> history-report（历史记录与报告模块）
```

更细一点就是：

```text
scale-screening（结构化量表筛查能力）
-> risk-stratification（初步风险分层与安全建议能力）
-> guided-conversation（引导问诊与画像补全能力）
-> intervention-decision（个性化调控决策能力）
-> intervention execution（调控执行）
```

其中：

1. `risk-stratification（初步风险分层与安全建议能力）` 只负责初步风险判断和安全建议。
2. `guided-conversation（引导问诊与画像补全能力）` 是后续必经步骤，不是可选步骤。
3. `intervention-decision（个性化调控决策能力）` 才负责最终选音乐、视频、文字故事等内容。

## 3. 模块目标与边界

### 3.1 模块目标

`risk-assessment（风险评估与安全建议模块）` 的目标不是做临床诊断，也不是替代专业治疗，而是：

1. 基于当前已收集信息给出 `initial risk stratification（初步风险分层）`
2. 给出 `safety advisory（安全建议）`
3. 判断是否达到 `referral threshold（就医建议阈值）`
4. 判断是否达到 `emergency threshold（紧急提示阈值）`
5. 在不强行阻断流程的前提下，为后续页面显示和流程优先级提供依据

### 3.2 当前不属于本模块的事情

以下内容不由 `risk-assessment（风险评估与安全建议模块）` 负责：

1. 不负责最终个性化调控内容选择
2. 不负责和用户展开长对话补全画像
3. 不负责播放音乐、视频、文字故事
4. 不负责做正式医学诊断
5. 不负责硬性阻断用户继续体验系统

### 3.3 和其他模块的边界

和 `assessment（量表评估模块）` 的边界：

1. `assessment` 负责量表作答、计分、保存原始量表结果
2. `risk-assessment（风险评估与安全建议模块）` 只消费量表摘要结果，不重新计分

和 `text-dialogue（文本对话与引导问诊模块）` 的边界：

1. `risk-assessment（风险评估与安全建议模块）` 给出初步风险分层和安全提醒
2. `text-dialogue（文本对话与引导问诊模块）` 根据前一步结果做有目的的追问和画像补全

和 `intervention（个性化调控与执行模块）` 的边界：

1. `risk-assessment（风险评估与安全建议模块）` 决定“风险高不高、是否优先建议外部帮助”
2. `intervention（个性化调控与执行模块）` 决定“选什么调控方式、推什么内容、怎么执行”

## 4. 当前项目场景下的核心设计原则

结合你们项目当前定位，`risk-assessment（风险评估与安全建议模块）` 必须满足以下原则：

1. `community-oriented（面向社区场景）`
   这不是医院临床诊疗系统，更偏社区场景下的早筛、提醒、辅助支持。
2. `safety-first（安全优先）`
   当风险较高时，要优先给出专业帮助建议，而不是把系统调控包装成治疗方案。
3. `non-blocking flow（不阻断流程）`
   即使达到高风险阈值，也不强制阻止用户继续体验后续调控内容，只是要把提示和优先级调整到位。
4. `assessment-dominant（量表主导）`
   在 `V1（第一版）`，量表结果是主判定基础，语音、表情、脑电更像增强证据。
5. `replaceable core（内核可替换）`
   外部接口先稳定，内部规则后面可以从 `rule engine（规则引擎）` 演进到 `machine learning（机器学习）` 或混合方案。

## 5. 模块输入

### 5.1 输入来源

当前建议 `risk-assessment（风险评估与安全建议模块）` 接收以下几类输入：

1. `intake profile（建档基础信息）`
2. `persona preference（虚拟医生与交互偏好）`
3. `assessment summary（量表结果摘要）`
4. `speech summary（语音摘要）`
5. `emotion summary（表情摘要）`
6. `eeg summary（脑电摘要）`
7. `optional text summary（可选文本摘要）`

说明：

1. 这里的 `text summary（文本摘要）` 不是后续 `guided-conversation（引导问诊）` 的结果。
2. 它只表示当前阶段如果已经有文本输入，例如建档备注、量表补充说明、语音转写结果，就可以一起送入。

### 5.2 输入字段原则

所有多模态输入建议统一使用摘要结构，而不是原始文件：

```json
{
  "available": true,
  "score": 0.72,
  "level": "medium",
  "confidence": 0.81,
  "summary": "作答过程中整体表现出明显低落与疲惫倾向"
}
```

关键原则：

1. 未接入的模态不要省略，统一返回 `available=false`
2. 不要求所有模态都齐全
3. 缺失模态不能直接判失败
4. 不能依赖原始音频、视频、脑电流文件作为主接口输入

## 6. 模块输出

### 6.1 必须输出的核心字段

`risk-stratification（初步风险分层与安全建议能力）` 建议至少输出：

1. `risk_level（风险等级）`
2. `risk_score（风险分数）`
3. `severity_band（分层挡位）`
4. `triggered_rules（触发规则）`
5. `evidence_summary（证据摘要）`
6. `referral_recommended（是否建议就医）`
7. `emergency_notice（是否紧急提示）`
8. `allow_continue（是否允许继续体验）`
9. `recommended_next_step（推荐下一步）`
10. `assessment_confidence（评估置信度）`

### 6.2 推荐下一步字段

`recommended_next_step（推荐下一步）` 建议来自固定枚举，不要自由发挥：

1. `continue_to_dialogue（继续进入引导问诊）`
2. `continue_with_strong_warning（带强提示继续）`
3. `seek_professional_help_first（优先建议寻求专业帮助）`
4. `seek_emergency_support_now（建议立即寻求紧急帮助）`

## 7. 风险分层挡位设计

当前建议采用 4 档：

### 7.1 `low（低风险）`

定义：

1. 当前量表结果整体较轻
2. 未出现明显危险信号
3. 多模态异常不集中

系统策略：

1. 正常展示结果分析
2. 正常进入 `guided-conversation（引导问诊与画像补全）`
3. 后续调控内容可以作为主路径

### 7.2 `medium（中风险）`

定义：

1. 量表提示存在持续情绪困扰
2. 可能伴随睡眠、压力、自我评价下降等问题
3. 但尚未达到强烈安全警报

系统策略：

1. 明确提示持续关注
2. 继续进入 `guided-conversation（引导问诊与画像补全）`
3. 后续调控内容可继续使用，但建议更密切跟踪

### 7.3 `high（高风险）`

定义：

1. 量表结果已经达到明显异常区间
2. 或出现自伤、自杀、极端绝望等高危线索
3. 或多模态证据集中指向明显异常

系统策略：

1. 页面优先展示 `referral recommendation（就医建议）`
2. 仍允许进入后续问诊和调控流程
3. 但系统调控只能定位为辅助支持，不可暗示替代专业帮助

### 7.4 `urgent（紧急风险）`

定义：

1. 出现明确紧急危险线索
2. 当前状态已不适合只依赖系统辅助

系统策略：

1. 强提示立即寻求紧急帮助
2. 仍不强行阻断页面操作
3. 后续系统内容仅可作为陪伴性支持，不作为主要建议

## 8. `V1（第一版）` 阈值逻辑建议

### 8.1 总体策略

当前最适合的 `V1（第一版）` 做法不是 `LLM（大语言模型）` 直接拍板，而是：

`rule engine（规则引擎） + weighted scoring（加权评分）`

原因：

1. 可解释
2. 好联调
3. 好改阈值
4. 适合现在的工程阶段
5. 不会把医疗安全判断直接交给 `LLM（大语言模型）`

### 8.2 评分逻辑建议

建议把总风险分数统一映射到 `0-100`。

当前代码实现采用：

`assessment-first（量表主导） + hard rules（硬规则兜底） + conservative uplift（保守升档）`

具体含义：

1. 先根据量表类型和量表分数得到 `base band（基础风险挡位）`
2. 再用 `PHQ-9（患者健康问卷）` 第 9 题、自伤高危词、紧急词做安全覆盖
3. 最后仅允许多模态结果在满足严格条件时，把风险上调 `1` 档

`V1（第一版）` 当前配置权重大致如下：

1. `assessment summary（量表结果摘要）`：`0.70`
2. `text summary（文本摘要）`：`0.075`
3. `speech summary（语音摘要）`：`0.075`
4. `emotion summary（表情摘要）`：`0.075`
5. `eeg summary（脑电摘要）`：`0.075`

说明：

1. 这套权重主要用于 `assessment_confidence（评估置信度）` 和 `contributions（贡献说明）` 的展示，不直接替代主规则判断
2. 多模态在 `V1（第一版）` 只能做保守升档，不能把明显高风险降回去
3. 在 `V1（第一版）`，量表仍然是主导输入

### 8.3 建议阈值

建议使用下面这套分层阈值：

量表主阈值：

1. `PHQ-9（患者健康问卷）`
2. `0-9`：`low（低风险）`
3. `10-14`：`medium（中风险）`
4. `>=15`：`high（高风险）`

1. `GAD-7（广泛性焦虑量表）`
2. `0-9`：`low（低风险）`
3. `10-14`：`medium（中风险）`
4. `>=15`：`high（高风险）`

1. `SDS（抑郁自评量表）`
2. `<53`：`low（低风险）`
3. `53-62`：`medium（中风险）`
4. `>=63`：`high（高风险）`

统一风险分数显示区间：

1. `0-34`：`low（低风险）`
2. `35-59`：`medium（中风险）`
3. `60-79`：`high（高风险）`
4. `80-100`：`urgent（紧急风险）`

说明：

1. `PHQ-9（患者健康问卷）` 和 `SDS（抑郁自评量表）` 都指向抑郁风险，不做简单相加
2. 当前实现中，量表先决定 `base band（基础风险挡位）`
3. `SDS（抑郁自评量表）` 按旧系统口径使用 `standard score（标准分）`
4. 当前前端真正打通多模态采集的样板仍然是 `SDS（抑郁自评量表）` 旧链路；`PHQ-9（患者健康问卷）` 与 `GAD-7（广泛性焦虑量表）` 后续将按同样模式补齐

### 8.4 强规则优先于分数

以下情况建议采用 `hard rules（硬规则）` 覆盖，不要只看总分：

1. `PHQ-9（患者健康问卷）` 第 9 题出现明确阳性
2. 文本或语音中出现明确自伤、自杀表达
3. 至少两个非量表模态同时达到高异常且高置信度

建议规则示例：

1. 如果 `PHQ-9（患者健康问卷）` 第 9 题得分 `=1`，则 `risk_level（风险等级）` 至少为 `high（高风险）`
2. 如果 `PHQ-9（患者健康问卷）` 第 9 题得分 `>=2`，则直接升为 `urgent（紧急风险）`
3. 如果文本或语音中出现明确紧急表达，例如“现在就想死”“结束生命”，则直接升为 `urgent（紧急风险）`
4. 如果文本或语音中出现高危但非迫近表达，例如“绝望”“活不下去”“撑不住”，则至少升为 `high（高风险）`
5. 如果 `text / speech / emotion / eeg（文本 / 语音 / 表情 / 脑电）` 中至少 `2` 个模态满足：
6. `score >= 70`
7. `confidence >= 0.70`
8. 则允许在当前基础上保守升高 `1` 档，最高只升到 `high（高风险）`

### 8.5 就医建议阈值

建议单独定义：

1. `referral threshold（就医建议阈值）`
2. `emergency threshold（紧急提示阈值）`

推荐初始策略：

1. `risk_level >= high（高风险）` 时：`referral_recommended=true`
2. `risk_level == urgent（紧急风险）` 时：`emergency_notice=true`
3. 无论哪一档：`allow_continue=true`

也就是说：

1. 高风险和紧急风险不会阻断流程
2. 但页面上必须把“优先建议外部帮助”放在更显著位置
3. 即使用户继续完成后续调控体验，系统也不能把调控内容表述为对高风险状态的替代治疗

## 9. 推荐接口设计

### 9.1 主接口

```text
POST /api/v1/risk-assessment/risk-stratification/score
```

职责：

1. 接收当前阶段已收集到的摘要结果
2. 执行初步风险分层
3. 返回风险等级、安全建议和后续流程提示

### 9.2 健康检查接口

```text
GET /api/v1/risk-assessment/risk-stratification/health
```

职责：

1. 检查规则引擎是否可用
2. 检查阈值配置是否加载完成
3. 检查是否处于 `mock mode（模拟模式）`

### 9.3 元信息接口

```text
GET /api/v1/risk-assessment/risk-stratification/meta
```

职责：

1. 返回模块名、能力名、版本号
2. 返回当前阈值版本
3. 返回当前是否支持 `mock（模拟）`

## 10. 请求与返回示例

### 10.1 请求示例

```json
{
  "user_id": "user-1001",
  "user_profile": {
    "age_group": "18-25",
    "gender": "female"
  },
  "persona_preference": {
    "style": "warm"
  },
  "assessment_summary": {
    "available": true,
    "scale_type": "PHQ-9",
    "total_score": 16,
    "severity": "moderately_severe",
    "self_harm_item_score": 1,
    "confidence": 0.95,
    "summary": "PHQ-9 得分较高，近期抑郁症状较明显"
  },
  "speech_summary": {
    "available": true,
    "score": 0.62,
    "level": "medium",
    "confidence": 0.78,
    "summary": "语音整体低沉，语速偏慢"
  },
  "emotion_summary": {
    "available": true,
    "score": 0.58,
    "level": "medium",
    "confidence": 0.72,
    "summary": "表情整体偏消极"
  },
  "eeg_summary": {
    "available": false,
    "score": null,
    "level": null,
    "confidence": null,
    "summary": null
  },
  "decision_context": {
    "source_page": "assessment_result",
    "threshold_version": "v1"
  }
}
```

### 10.2 正常返回示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "result": {
      "risk_level": "medium",
      "risk_score": 57,
      "severity_band": "medium",
      "referral_recommended": false,
      "emergency_notice": false,
      "allow_continue": true,
      "recommended_next_step": "continue_to_dialogue",
      "assessment_confidence": 0.84,
      "triggered_rules": [],
      "evidence_summary": [
        "量表结果提示持续情绪困扰",
        "语音和表情存在一定低落倾向"
      ]
    }
  },
  "request_id": "req-20260401-risk-001",
  "timestamp": "2026-04-01T20:00:00+08:00"
}
```

### 10.3 高风险但允许继续示例

```json
{
  "code": 1001,
  "message": "referral_recommended",
  "data": {
    "result": {
      "risk_level": "high",
      "risk_score": 78,
      "severity_band": "high",
      "referral_recommended": true,
      "emergency_notice": false,
      "allow_continue": true,
      "recommended_next_step": "continue_with_strong_warning",
      "assessment_confidence": 0.88,
      "triggered_rules": [
        "phq9_high_score",
        "multimodal_negative_consensus"
      ],
      "evidence_summary": [
        "量表结果已达到较高风险区间",
        "多模态结果共同提示明显异常"
      ]
    }
  },
  "request_id": "req-20260401-risk-002",
  "timestamp": "2026-04-01T20:01:00+08:00"
}
```

## 11. 页面流转建议

### 11.1 结果分析页

量表结果页之后，建议先请求：

```text
POST /api/v1/risk-assessment/risk-stratification/score
```

页面应展示：

1. 当前风险等级
2. 风险依据摘要
3. 是否建议尽快寻求专业帮助
4. “继续进入引导问诊”按钮

如果 `referral_recommended=true`：

1. 页面顶部优先展示提醒
2. 但保留继续按钮

### 11.2 引导问诊页

无论风险高低，当前 `V1（第一版）` 都进入：

`guided-conversation（引导问诊与画像补全能力）`

区别只是：

1. 高风险用户提示更强
2. 问诊问题更偏安全确认和当前支持系统了解

### 11.3 调控决策页

只有在 `guided-conversation（引导问诊与画像补全能力）` 结束后，才调用：

`intervention-decision（个性化调控决策能力）`

## 12. `V1（第一版）` 实现建议

### 12.1 推荐实现方式

当前建议：

1. 先用 `rule engine（规则引擎）`
2. 把阈值写成独立配置
3. 统一输出固定结构
4. 先支持 `mock（模拟）` 数据和真实量表结果

### 12.2 代码结构建议

建议后续按下面的方式建目录：

```text
depression/new_features/risk_assessment/
  api.py
  engine.py
  rules.py
  schemas.py
  constants.py
```

职责建议：

1. `api.py`：接口入口
2. `engine.py`：总评分流程
3. `rules.py`：硬规则与阈值逻辑
4. `schemas.py`：输入输出结构定义
5. `constants.py`：风险挡位、业务码、提示文案常量

## 13. 测试建议

`risk-assessment（风险评估与安全建议模块）` 至少准备以下测试样例：

1. `low（低风险）` 样例
2. `medium（中风险）` 样例
3. `high（高风险）` 样例
4. `urgent（紧急风险）` 样例
5. 缺失部分模态样例
6. 量表正常但多模态明显异常样例
7. 量表较高但用户仍允许继续体验样例

重点验证：

1. 挡位是否正确
2. `referral_recommended（建议就医）` 是否正确
3. `allow_continue（允许继续）` 是否始终正确
4. `triggered_rules（触发规则）` 是否可解释

## 14. 当前版本建议冻结的内容

为了方便你下一步写接口和代码，建议先冻结下面这些内容：

1. 一级模块名：`risk-assessment`
2. 二级能力名：`risk-stratification`
3. 主接口路径：`POST /api/v1/risk-assessment/risk-stratification/score`
4. 4 档风险分层：`low / medium / high / urgent`
5. 高风险不阻断，只强提示：`allow_continue=true`
6. `V1（第一版）` 先用 `rule engine（规则引擎） + weighted scoring（加权评分）`

## 15. 下一步建议

在这份方案文档基础上，下一步最适合继续做两件事：

1. 把 [openapi_v1.yaml](/home/ZR/data2/Depression/depression/docs/openapi_v1.yaml) 中 `risk-assessment（风险评估与安全建议模块）` 的请求体和返回示例继续细化
2. 开始落 `risk_assessment/api.py` 和 `risk_assessment/engine.py` 的 `mock（模拟）` 版骨架
