# 项目交接摘要（2026-03-08）

本文档用于给新开的 Codex 对话快速补全上下文，避免重复翻聊天记录。

## 1. 项目定位

这是一个端侧本地部署的抑郁情绪筛查与调控系统，目标不是单纯聊天，而是形成闭环：

`量表筛查 -> 自动问诊 -> 多模态分析 -> 结果反馈 -> 干预 -> 再评估`

当前代码层面主要由两个项目联合实现：

- `depression`：Flask 应用、本地 UI、咨询页、数据库、脚本、技能接入、量表模块
- `EmoLLM`：本地 LLM 模型、RAG 服务、相关数据与部署脚本

注意：

- 当前版本运行在 GPU 上
- 项目中的 NPU 文件属于旧版本残留，当前工作中不需要考虑

## 2. 当前运行方式

### 2.1 三个服务

1. LLM 服务
- conda 环境：`lmdeploy`
- 命令：

```bash
lmdeploy serve api_server ./model/EmoLLM_Qwen2-7B-Instruct_lora \
  --server-name 0.0.0.0 \
  --server-port 8000 \
  --model-name emollm-qwen2-7b \
  --api-keys sk-local
```

2. RAG 服务
- conda 环境：`emo311`
- 命令：

```bash
export CUDA_VISIBLE_DEVICES=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
uvicorn rag_official_api:app --host 0.0.0.0 --port 8001
```

3. Flask 应用
- conda 环境：`depression`
- 命令：

```bash
cd /home/ZR/data2/Depression/depression
export CUDA_VISIBLE_DEVICES=1
python3 start_app_gpu.py
```

### 2.2 标准化启动脚本

已完成本地推理服务标准化，相关脚本位于：

- `depression/scripts/start_stack.sh`
- `depression/scripts/stop_stack.sh`
- `depression/scripts/check_stack.sh`
- `depression/scripts/watch_stack_logs.sh`
- `depression/scripts/start_llm_gpu.sh`
- `depression/scripts/start_rag.sh`
- `depression/scripts/_common.sh`

已修复过的问题包括：

- 多 conda 环境分别启动
- 健康检查
- 日志落盘
- `stop_stack.sh` 只停包装进程、不停子进程的问题
- LLM/RAG/app 的日志查看
- `conda run --no-capture-output` 带来的日志可见性

### 2.3 访问方式

由于服务运行在 Linux 主机，不应在 Windows 浏览器中访问 `127.0.0.1:5000`，而应访问局域网 IP，例如：

```text
http://10.101.6.118:5000
```

## 3. 已完成的重要功能

### 3.1 会话总结 Skill

已实现“用户在咨询页输入总结类指令时自动总结当前会话”的功能。

目录：

- `depression/new_features/session_summary_skill/`

主要文件：

- `api.py`
- `service.py`
- `chat_skill.py`
- `skills/session-summary/SKILL.md`

能力：

- 当用户在咨询页输入类似：
  - `总结会话`
  - `总结对话`
  - `总结上述对话`
  - `帮我总结一下`
- 系统自动命中 Skill
- 汇总当前聊天历史
- 通过 LLM 生成结构化总结
- 作为一条普通 AI 消息返回给前端
- 同时写入数据库

数据库位置：

- `depression/my_flask_app/depression.db`

会话记录表：

- `counseling_records`

### 3.2 Skill Router

已将单个 Skill 的手工 if/else 触发改造成统一路由框架。

目录：

- `depression/new_features/skill_router/`

主要文件：

- `base.py`
- `registry.py`
- `router.py`

当前接入的第一个 Skill：

- `session-summary`

意义：

- 以后新增 Skill，不需要继续把逻辑硬塞进 `psychological_counseling.py`
- 只需要在 `new_features/<skill_name>/` 下写适配类并注册

### 3.3 聊天意图分流

已修复“所有问题都走 RAG、普通闲聊被回答成心理学百科”的问题。

新增目录：

- `depression/new_features/chat_intent_router/`

主要逻辑文件：

- `depression/my_flask_app/utils/emollm_client.py`
- `depression/new_features/chat_intent_router/policy.py`

当前已支持的意图：

- `casual`：寒暄
- `identity`：你是谁
- `realtime`：日期、天气、新闻、最新信息
- `psychology`：抑郁、焦虑、PHQ-9 等心理相关问题
- `general`：普通问题

当前策略：

- `casual / identity`：直接短答，不走 RAG
- `realtime`：
  - 未开启联网搜索时直接拒答，提示需要联网搜索
  - 开启联网时先给搜索状态提示，再组织回答
- `psychology`：走 RAG
- `general`：普通 LLM 回答，不强制走心理知识库

### 3.4 联网搜索状态与实时信息修复

已修复的问题：

- 联网搜索时前端没有明显状态提示
- 流式输出时总结 Skill 不是逐步显示
- 日期类问题被 Tavily 旧结果误导

已完成的效果：

- 搜索中先显示：

```text
🔍 正在请求 Tavily 联网搜索最新信息...
```

- 搜索完成后显示：

```text
✅ 搜索完成，正在结合最新信息组织语言...
```

- 状态消息随后消失，再进入正式回复
- 对“今天几号 / 星期几 / 现在几点”这类问题增加了更稳定的处理
- 流式解析中的 `[DONE]` 噪声警告已修复

### 3.5 量表解析：PHQ-9 / GAD-7

这是老师明确要求优先做的部分，目前已经开始并完成了第一版结构化实现。

目录：

- `depression/new_features/scale_assessment/`

主要文件：

- `definitions.py`
- `engine.py`
- `repository.py`
- `api.py`

模板文件：

- `depression/my_flask_app/flask_app/templates/scale_assessment/index.html`
- `depression/my_flask_app/flask_app/templates/scale_assessment/fill.html`
- `depression/my_flask_app/flask_app/templates/scale_assessment/result.html`

已完成内容：

1. 量表定义
- PHQ-9
- GAD-7

2. 规则计分
- 完全由程序规则实现
- 不依赖 LLM 算分

3. 分级输出
- PHQ-9 分级
- GAD-7 分级

4. 风险项
- PHQ-9 第 9 题单独风险标记

5. 结构化落库
- 新表：`scale_assessment_records`

6. 页面流程
- 量表列表页
- 填写页
- 结果页

### 3.6 量表模块最近一次修复

最近一次已修复的问题：

1. `scale_assessment/api.py`
- 补了结果页中 `scale_def` 为空时的保护
- 修正了管理员权限判断

2. `scale_assessment/fill.html`
- 修复了 Jinja 中 `scale.items` 与 Python `dict.items` 方法冲突的问题
- 当前统一改成显式字典取值，如：
  - `scale["items"]`
  - `scale["options"]`
  - `scale["slug"]`

## 4. 关键文件位置

### 4.1 Flask 主应用

- `depression/my_flask_app/flask_app/__init__.py`

说明：

- 已注册 `session_summary_skill`
- 已注册 `scale_assessment`

### 4.2 咨询主逻辑

- `depression/my_flask_app/flask_app/views/psychological_counseling.py`

说明：

- 这里接入了 Skill Router
- 普通聊天仍走原链路

### 4.3 LLM 客户端

- `depression/my_flask_app/utils/emollm_client.py`

说明：

- 这里已经做了聊天意图分流
- 这里也做了 Tavily 搜索状态消息和实时信息处理

### 4.4 本地数据库

- `depression/my_flask_app/depression.db`

重要表：

- `userinfo`
- `counseling_records`
- `scale_assessment_records`

## 5. Git 与仓库整理

之前已经做过一次仓库整理判断，结论是：

- 可以在 `Depression` 根目录做 git 仓库
- 需要忽略模型文件、隐私文件、日志、数据库、缓存等
- 当前项目核心目录主要是：
  - `depression`
  - `EmoLLM`

注意：

- 不要把大型模型权重和隐私配置直接推 GitHub
- RAG 向量库、模型目录、`.env`、日志、数据库都应该忽略

## 6. 开发环境经验教训

### 6.1 之前的问题

这次对话大部分编辑是通过：

- Linux 主机
- Windows 侧 `SSHFS-Win + WinFsp` 挂载到 `Z:` 盘

这种方式进行的。

结果：

- 目录可创建
- 文件可能能创建但后续不能稳定读取/修改
- 会出现“已拒绝”“Access denied”“半写入”的情况

### 6.2 当前结论

用户现在已经找到在 SSH 中使用 Codex 的方法。

后续建议：

- 优先直接在 SSH 环境中继续开发
- 如果仍在挂载盘编辑，每次改代码前先补 ACL 权限

之前为避免挂载问题，已经形成一个约定：

- 每次执行代码修改前，先做一次权限添加

## 7. 当前未完成但最自然的下一步

当前最合理的后续工作有两个方向：

### 方向 A：把量表结果接入系统主流程

建议顺序：

1. 将 `scale_assessment_records` 接入历史页
2. 将最近一次 PHQ-9 / GAD-7 结果注入自动问诊上下文
3. 让咨询页能够读取最近量表结果作为前置背景

### 方向 B：继续补闭环

建议顺序：

1. 结果页 / 历史页展示结构化总结
2. 干预建议模块
3. 再评估流程

## 8. 当前如果要继续开发，建议先验证的点

1. 重启应用后访问：

```text
/scales
/scales/phq9
/scales/gad7
```

2. 检查：

- PHQ-9 提交后是否能正常生成结果页
- GAD-7 提交后是否能正常生成结果页
- `scale_assessment_records` 是否成功写入

3. 咨询页验证：

- 普通问答是否正常
- `总结上述对话` 是否还能正确触发 `session-summary` Skill
- 联网搜索状态消息是否正常显示

## 9. 供新对话快速阅读的最短摘要

如果新对话只需要 30 秒接手，可以直接看这几条：

1. 这是一个本地部署的抑郁筛查与调控系统，核心是 `depression + EmoLLM`
2. 当前运行在 GPU，不要管 NPU 旧文件
3. 本地三服务标准化启动已经完成：LLM / RAG / Flask
4. 已完成：
   - 会话总结 Skill
   - Skill Router
   - 聊天意图分流
   - 联网搜索状态提示
   - PHQ-9 / GAD-7 第一版量表解析
5. 最近刚修过：
   - `scale_assessment/api.py`
   - `scale_assessment/fill.html`
6. 下一步优先建议：
   - 把量表结果接入历史页和问诊上下文

