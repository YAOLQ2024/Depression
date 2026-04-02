# 抑郁症辅助干预系统模块总表（V1）

更新时间：2026-04-01

文档文件名：`system_module_master_table_v1_20260401.md`

## 1. 文档定位

本文档用于固定当前 V1 阶段的模块命名，并给出后续接口规范、组员分工、联调接入所需的最小公共表。

本文档解决以下问题：

1. 当前系统到底有哪些一级模块
2. 当前系统到底有哪些二级能力模块
3. 每个模块分别负责什么
4. 每个模块后续接口应该挂在哪个路径前缀下
5. 后续模块变更时，哪些内容可以改，哪些内容尽量不要改

说明：

1. 本文档中的模块命名为 `V1 暂定冻结命名`
2. 当前阶段允许后续增加新模块，但不建议随意重命名已有模块
3. 若后续确实要调整名称，优先采用“新增别名或新增能力”方式，而不是直接推翻原命名

## 2. 模块命名冻结原则

为了降低后续接口文档、前后端联调、组员协作的变更成本，当前建议采用以下冻结原则：

1. 一级模块英文名用于业务域标识，后续尽量不改
2. 二级能力英文名用于能力单元标识，后续尽量不改
3. 中文名可以随着汇报场景微调，但不应改变其核心含义
4. 路由路径优先使用英文名，不直接使用中文名
5. 所有新接口统一挂在 `/api/v1/` 前缀下

## 3. 一级模块总表（11 个）

| 序号 | 一级模块英文名 | 一级模块中文名 | 模块类型 | 核心职责 | 典型接口前缀 | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `auth-profile` | 身份认证与用户建档模块 | 平台基础模块 | 登录、注册、身份识别、患者基础档案、用户画像基础信息 | `/api/v1/auth-profile/` | 部分已有 |
| 2 | `persona` | 虚拟医生与交互角色模块 | 交互体验模块 | 虚拟医生选择、人格风格选择、交互偏好、语音播报偏好 | `/api/v1/persona/` | 规划中 |
| 3 | `assessment` | 量表评估模块 | 核心业务模块 | 量表展示、量表作答、量表评分、量表结果保存 | `/api/v1/assessment/` | 已有基础 |
| 4 | `text-dialogue` | 文本对话与引导问诊模块 | 核心业务模块 | 在初步风险分层之后进行必经式引导问诊，补全用户画像、提取语义线索、生成结构化摘要 | `/api/v1/text-dialogue/` | 部分已有 |
| 5 | `speech` | 语音处理模块 | 多模态输入模块 | 统一管理语音相关能力，包括语音转写和语音情绪识别 | `/api/v1/speech/` | 部分已有 |
| 6 | `emotion` | 表情识别模块 | 多模态输入模块 | 摄像头采集、面部表情识别、情绪摘要输出 | `/api/v1/emotion/` | 已有基础 |
| 7 | `eeg` | 脑电信号模块 | 多模态输入模块 | 脑电采集、脑电特征提取、分类结果输出 | `/api/v1/eeg/` | 部分已有 |
| 8 | `risk-assessment` | 风险评估与安全建议模块 | 核心评估模块 | 聚合建档信息、量表结果和作答过程多模态摘要，输出初步风险分层、阈值判断、就医建议和继续体验标记 | `/api/v1/risk-assessment/` | 规划中 |
| 9 | `intervention` | 个性化调控与执行模块 | 核心业务模块 | 基于补全后的用户画像、风险分层结果和偏好信息生成个性化调控决策、内容推荐和执行反馈 | `/api/v1/intervention/` | 规划中 |
| 10 | `history-report` | 历史记录与报告模块 | 数据闭环模块 | 历史记录查询、阶段性趋势查看、结果报告生成 | `/api/v1/history-report/` | 部分已有 |
| 11 | `admin-settings` | 后台管理与系统设置模块 | 支撑管理模块 | 系统配置、权限控制、调试开关、研究数据管理、审计管理 | `/api/v1/admin-settings/` | 部分已有 |

## 4. 二级能力模块总表（12 个）

说明：二级能力模块是当前建议给组员独立开发、独立联调、独立替换的最小能力单元。

| 序号 | 所属一级模块 | 二级能力英文名 | 二级能力中文名 | 核心职责 | 典型主接口 | 当前定位 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `auth-profile` | `identity-access` | 身份认证与档案能力 | 登录、注册、登出、患者基础档案读写 | `POST /api/v1/auth-profile/identity-access/login` | 基础公共能力 |
| 2 | `persona` | `virtual-clinician` | 虚拟医生选择能力 | 角色选择、角色风格、播报风格、交互偏好设置 | `POST /api/v1/persona/virtual-clinician/select` | 交互配置能力 |
| 3 | `assessment` | `scale-screening` | 结构化量表筛查能力 | PHQ-9、GAD-7、SDS 等量表的作答、计分和结果返回 | `POST /api/v1/assessment/scale-screening/submit` | 核心主入口能力 |
| 4 | `text-dialogue` | `guided-conversation` | 引导式文本问诊能力 | 在初步风险分层后执行必经式问诊，补全用户画像、提取关键语义线索、生成问诊摘要 | `POST /api/v1/text-dialogue/guided-conversation/run` | 核心补全能力 |
| 5 | `speech` | `speech-transcribe` | 语音转写能力 | 普通话与方言音频转文本 | `POST /api/v1/speech/speech-transcribe/run` | 语音输入能力 |
| 6 | `speech` | `speech-emotion` | 语音情绪识别能力 | 音频情绪、语气、声学特征分析 | `POST /api/v1/speech/speech-emotion/analyze` | 多模态增强能力 |
| 7 | `emotion` | `facial-affect` | 面部表情情绪识别能力 | 摄像头图像中的表情和情绪分析 | `POST /api/v1/emotion/facial-affect/analyze` | 多模态增强能力 |
| 8 | `eeg` | `eeg-sensing` | 脑电采集与分析能力 | EEG 数据接入、特征提取、状态分类、波形摘要 | `POST /api/v1/eeg/eeg-sensing/analyze` | 多模态增强能力 |
| 9 | `risk-assessment` | `risk-stratification` | 初步风险分层与安全建议能力 | 聚合建档信息、量表结果和作答过程多模态摘要，输出风险等级、阈值命中情况、就医建议和继续体验标记 | `POST /api/v1/risk-assessment/risk-stratification/score` | 核心安全分层能力 |
| 10 | `intervention` | `intervention-decision` | 个性化调控决策能力 | 基于补全后的用户画像、虚拟医生偏好和风险分层结果选择最适合的调控方式、内容和执行方案 | `POST /api/v1/intervention/intervention-decision/plan` | 核心输出能力 |
| 11 | `history-report` | `record-reporting` | 记录与报告能力 | 历史查询、趋势统计、阶段总结、报告生成 | `POST /api/v1/history-report/record-reporting/generate` | 闭环输出能力 |
| 12 | `admin-settings` | `system-ops` | 系统管理与配置能力 | 配置管理、调试控制、数据审计、后台运维相关能力 | `POST /api/v1/admin-settings/system-ops/update` | 支撑保障能力 |

## 5. 一级模块与二级能力映射表

| 一级模块英文名 | 一级模块中文名 | 对应二级能力英文名 | 对应二级能力中文名 |
| --- | --- | --- | --- |
| `auth-profile` | 身份认证与用户建档模块 | `identity-access` | 身份认证与档案能力 |
| `persona` | 虚拟医生与交互角色模块 | `virtual-clinician` | 虚拟医生选择能力 |
| `assessment` | 量表评估模块 | `scale-screening` | 结构化量表筛查能力 |
| `text-dialogue` | 文本对话与引导问诊模块 | `guided-conversation` | 引导式文本问诊能力 |
| `speech` | 语音处理模块 | `speech-transcribe` | 语音转写能力 |
| `speech` | 语音处理模块 | `speech-emotion` | 语音情绪识别能力 |
| `emotion` | 表情识别模块 | `facial-affect` | 面部表情情绪识别能力 |
| `eeg` | 脑电信号模块 | `eeg-sensing` | 脑电采集与分析能力 |
| `risk-assessment` | 风险评估与安全建议模块 | `risk-stratification` | 初步风险分层与安全建议能力 |
| `intervention` | 个性化调控与执行模块 | `intervention-decision` | 个性化调控决策能力 |
| `history-report` | 历史记录与报告模块 | `record-reporting` | 记录与报告能力 |
| `admin-settings` | 后台管理与系统设置模块 | `system-ops` | 系统管理与配置能力 |

## 6. 推荐的模块分层理解

为了方便后续汇报和工程分工，当前建议把 11 个一级模块再按职责分成 5 个层次理解：

### 6.1 平台基础层

1. `auth-profile` 身份认证与用户建档模块
2. `persona` 虚拟医生与交互角色模块

### 6.2 多模态采集与理解层

1. `assessment` 量表评估模块
2. `text-dialogue` 文本对话与引导问诊模块
3. `speech` 语音处理模块
4. `emotion` 表情识别模块
5. `eeg` 脑电信号模块

### 6.3 初步安全分层层

1. `risk-assessment` 风险评估与安全建议模块

### 6.4 个性化调控层

1. `intervention` 个性化调控与执行模块

### 6.5 闭环支撑层

1. `history-report` 历史记录与报告模块
2. `admin-settings` 后台管理与系统设置模块

## 7. 当前建议冻结的关键命名

以下字段建议从现在开始尽量固定，不要频繁改：

1. 一级模块英文名
2. 二级能力英文名
3. 一级模块到二级能力的归属关系
4. 每个模块的接口前缀
5. 核心主接口动作名

当前建议固定的主接口动作名如下：

| 二级能力英文名 | 建议动作名 | 完整示例 |
| --- | --- | --- |
| `identity-access` | `login` | `/api/v1/auth-profile/identity-access/login` |
| `virtual-clinician` | `select` | `/api/v1/persona/virtual-clinician/select` |
| `scale-screening` | `submit` | `/api/v1/assessment/scale-screening/submit` |
| `guided-conversation` | `run` | `/api/v1/text-dialogue/guided-conversation/run` |
| `speech-transcribe` | `run` | `/api/v1/speech/speech-transcribe/run` |
| `speech-emotion` | `analyze` | `/api/v1/speech/speech-emotion/analyze` |
| `facial-affect` | `analyze` | `/api/v1/emotion/facial-affect/analyze` |
| `eeg-sensing` | `analyze` | `/api/v1/eeg/eeg-sensing/analyze` |
| `risk-stratification` | `score` | `/api/v1/risk-assessment/risk-stratification/score` |
| `intervention-decision` | `plan` | `/api/v1/intervention/intervention-decision/plan` |
| `record-reporting` | `generate` | `/api/v1/history-report/record-reporting/generate` |
| `system-ops` | `update` | `/api/v1/admin-settings/system-ops/update` |

## 8. 后续允许变更的内容

以下内容后续允许调整：

1. 中文展示名
2. 模块说明文字
3. 模块内部算法实现
4. 模块部署方式
5. 二级能力下的附属接口数量

以下内容后续如非必要，不建议调整：

1. 一级模块英文名
2. 二级能力英文名
3. 已经对组员公开的路径前缀
4. 已经写入接口文档的标准返回结构

## 9. 当前主链口径

为避免后续把“初步风险判断”和“最终调控选择”混在一起，当前 V1 统一按下面这条链理解：

```text
assessment（量表评估）
-> risk-assessment / risk-stratification（初步风险分层与安全建议）
-> text-dialogue / guided-conversation（引导问诊与画像补全）
-> intervention / intervention-decision（个性化调控决策）
-> intervention（调控执行与反馈）
-> history-report（记录与报告）
```

说明：

1. `risk-stratification` 只负责初步风险分层、阈值判断和安全建议，不直接给出最终调控内容。
2. `guided-conversation` 是当前主链中的必经步骤，用于在初步结果之后补全画像。
3. `intervention-decision` 才负责基于补全后的画像选择音乐、视频、文字故事等调控方式。

## 10. 建议你下一步立刻继续做的事

基于这份模块总表，下一步最适合继续产出这 3 份内容：

1. `统一返回结构表`
2. `OpenAPI（接口描述标准）草稿`
3. `组员接入说明表`

其中优先级最高的是：

`先把每个一级模块至少写出 health / meta / 主接口 三类接口`
