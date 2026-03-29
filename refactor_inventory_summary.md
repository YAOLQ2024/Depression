# 重构前代码盘点摘要

说明：以下仅记录当前仓库里有代码证据的内容；未列入的内容应视为未来设想或未发现代码证据。

## 1. 项目当前技术栈
- Web：Flask + Jinja2 + SQLite，主代码在 [depression/my_flask_app](/home/ZR/data2/Depression/depression/my_flask_app) 和 [depression/new_features](/home/ZR/data2/Depression/depression/new_features)
- 前端：服务端模板 + 原生 JS/Alpine.js + Tailwind CDN + Chart.js + marked.js，模板在 [templates](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates)
- LLM 接入：OpenAI 兼容聊天接口封装，见 [emollm_client.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py)
- RAG：FastAPI + FAISS 检索，见 [rag_official_api.py](/home/ZR/data2/Depression/EmoLLM/rag_official_api.py) 和 [EmoLLM/rag/src](/home/ZR/data2/Depression/EmoLLM/rag/src)
- 语音：浏览器语音输入 + 浏览器 TTS + Dolphin ASR，见 [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html) 和 [speech_recognition_dolphin.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/speech_recognition_dolphin.py)
- 视觉：ONNX Runtime GPU 表情识别，见 [emotion_recognition_gpu.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emotion_recognition_gpu.py)
- 脑电：串口 EEG 接收与规则分类，见 [eeg_receiver.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/utils/eeg_receiver.py)
- 模型/训练资产：本地模型、数据集、xtuner 配置在 [EmoLLM/model](/home/ZR/data2/Depression/EmoLLM/model)、[EmoLLM/datasets](/home/ZR/data2/Depression/EmoLLM/datasets)、[EmoLLM/xtuner_config](/home/ZR/data2/Depression/EmoLLM/xtuner_config)

## 2. 可复用资产清单
| 资产 | 说明 | 关键路径 |
|---|---|---|
| 结构化量表模块 | PHQ-9/GAD-7 定义、评分、落库完整 | [scale_assessment](/home/ZR/data2/Depression/depression/new_features/scale_assessment) |
| 评估上下文聚合层 | 可把 SDS + 结构化量表拼成统一上下文 | [assessment_context/service.py](/home/ZR/data2/Depression/depression/new_features/assessment_context/service.py) |
| LLM 接口封装 | 已封装流式聊天、路由、RAG、联网搜索开关 | [emollm_client.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py) |
| 会话总结技能 | 独立技能模块，带 DB fallback | [session_summary_skill](/home/ZR/data2/Depression/depression/new_features/session_summary_skill) |
| 聊天 UI 原型 | 已有流式、语音输入、浏览器 TTS | [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html) |
| 历史/详情 UI 原型 | 可作为结果展示参考，不建议直接继承逻辑 | [history.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/history.html) / [detail.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/detail.html) |
| Dolphin ASR 接入 | 本地音频转文本已接通 | [speech_recognition_dolphin.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/speech_recognition_dolphin.py) |
| ONNX 表情识别接入 | 本地模型与接口都在 | [emotion_recognition_gpu.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emotion_recognition_gpu.py) |
| RAG 服务与向量库 | 已形成独立服务边界 | [rag_official_api.py](/home/ZR/data2/Depression/EmoLLM/rag_official_api.py) / [EmoLLM/rag](/home/ZR/data2/Depression/EmoLLM/rag) |
| 本地联调脚本 | 可直接用于启动 LLM/RAG/App | [depression/scripts](/home/ZR/data2/Depression/depression/scripts) |

## 3. 仅有壳子的功能清单
| 功能 | 现状 | 关键路径 |
|---|---|---|
| 综合报告页 | 页面可打开，但核心分数和情绪分布含硬编码 | [comprehensive_detail.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/comprehensive_detail.html) |
| 首页 AI 洞察 | 文案型展示，非真实分析链路 | [main2.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/main2.html) |
| 心理科普卡片 | 主要是静态卡片/占位链接 | [main2.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/main2.html) |
| 多模态综合评分主链路 | 有采集痕迹，但当前活跃流程未真正落库闭环 | [SDS_working2.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/SDS_working2.html) / [test.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/test.py) |
| 小程序端 | 仅原型资料，不是可运行代码 | [EmoLLM原型图.md](/home/ZR/data2/Depression/EmoLLM/front/Wechat%20small%20program%20prototype%20design/EmoLLM原型图.md) |

## 4. 建议废弃的模块清单
| 模块 | 原因 | 关键路径 |
|---|---|---|
| 聊天中的旧情绪上下文查询 | 访问不存在的表和方法 | [psychological_counseling.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/psychological_counseling.py) |
| 失配的 EEG 路由/测试脚本 | 路由调用的方法与接收器实现不一致 | [test.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/test.py) / [test_eeg.py](/home/ZR/data2/Depression/depression/my_flask_app/test_eeg.py) |
| 当前综合报告实现 | 混合真实数据与硬编码演示值 | [comprehensive_detail.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/comprehensive_detail.html) |
| 未引用的前端脚本 | 当前主模板未使用 | [emotion-recognition.js](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/static/js/emotion-recognition.js) / [enhanced-video-player.js](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/static/js/enhanced-video-player.js) |
| 一次性迁移脚本 | 硬编码旧路径，工程价值低 | [db_migration_emotion.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/db_migration_emotion.py) |
| NPU 旧分支 | 当前项目已明确按 GPU 路线运行 | [start_app_npu.py](/home/ZR/data2/Depression/depression/start_app_npu.py) / [emotion_recognition_npu.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emotion_recognition_npu.py) |
| 已提交的本机配置 | 含真实密钥和本机地址，不应直接继承 | [depression/.env](/home/ZR/data2/Depression/depression/.env) |
| EmoLLM 多个 demo 启动器 | 多为实验性入口，不是当前主系统 | [EmoLLM/app.py](/home/ZR/data2/Depression/EmoLLM/app.py) / [EmoLLM/deploy](/home/ZR/data2/Depression/EmoLLM/deploy) |

## 5. 真实存在的输入/输出能力
已有输入能力：
- 文本输入：聊天输入框，见 [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html)
- 浏览器语音输入：见 [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html) 和 [SDS_working2.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/SDS_working2.html)
- 音频上传/后端 ASR：见 [test.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/test.py)
- 摄像头输入：见 [SDS_working2.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/SDS_working2.html)
- EEG 串口输入：见 [eeg_receiver.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/utils/eeg_receiver.py)

已有输出能力：
- 文本页面/历史/报告展示：见 [templates](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates)
- 流式聊天文本输出：见 [psychological_counseling.py](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/views/psychological_counseling.py)
- 浏览器 TTS：见 [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html)
- 图片/视频资源展示：见 [static](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/static)

未发现代码证据：
- 音乐播放
- 人脸身份识别
- 数字人驱动/动作/角色动画

## 6. 真实存在的模型/API调用
- 本地 OpenAI 兼容聊天接口：配置见 [depression/.env](/home/ZR/data2/Depression/depression/.env)，调用封装见 [emollm_client.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py)
- 本地 vLLM 启动链路：见 [start_llm_gpu.sh](/home/ZR/data2/Depression/depression/scripts/start_llm_gpu.sh)
- 本地 RAG API：见 [rag_official_api.py](/home/ZR/data2/Depression/EmoLLM/rag_official_api.py) 和 [start_rag.sh](/home/ZR/data2/Depression/depression/scripts/start_rag.sh)
- 本地 Dolphin ASR 模型：见 [small.pt](/home/ZR/data2/Depression/depression/models/dolphin/small.pt) 和 [speech_recognition_dolphin.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/speech_recognition_dolphin.py)
- 本地 ONNX 表情模型：见 [faceDetection.onnx](/home/ZR/data2/Depression/depression/models/faceDetection.onnx) / [onnx_model_48.onnx](/home/ZR/data2/Depression/depression/models/onnx_model_48.onnx)
- 可选联网搜索：代码已接，配置依赖 [depression/.env](/home/ZR/data2/Depression/depression/.env) 和 [emollm_client.py](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py)

说明：以上表示“仓库中有真实接入代码”，不表示这些服务当前一定在线或可直接交付。

## 7. 最适合从哪里开始重构
- 首选起点：[`scale_assessment`](/home/ZR/data2/Depression/depression/new_features/scale_assessment) + [`assessment_context/service.py`](/home/ZR/data2/Depression/depression/new_features/assessment_context/service.py) + [`emollm_client.py`](/home/ZR/data2/Depression/depression/my_flask_app/utils/emollm_client.py)
- 原因：这三块边界相对清楚，已有真实能力，且最少依赖摄像头/EEG/旧页面假流程
- UI 仅建议把 [counseling.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/counseling.html)、[history.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/history.html)、[detail.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/detail.html)、[base.html](/home/ZR/data2/Depression/depression/my_flask_app/flask_app/templates/base.html) 当作原型参考
- 不建议从多模态综合报告、旧 EEG 链路、NPU 分支或 EmoLLM demo 入口开始
