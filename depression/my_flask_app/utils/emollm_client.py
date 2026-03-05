#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EmoLLM API客户端
用于调用心理咨询服务（支持硅基流动API）
"""

import re
import requests
import logging
import os
import json
from typing import Dict, List, Optional, Tuple
import time

# 配置日志
logger = logging.getLogger(__name__)


class EmoLLMClient:
    """心理咨询API客户端（兼容EmoLLM接口，实际调用硅基流动API）"""
    
    def __init__(self, 
                 api_url: str = None,
                 timeout: int = 120,  # 默认超时时间增加到120秒
                 max_retries: int = 3,
                 api_key: str = None,
                 model: str = None):
        """
        初始化客户端
        
        Args:
            api_url: API服务地址（硅基流动默认为 https://api.siliconflow.cn/v1/chat/completions）
            timeout: 请求超时时间（秒），默认120秒
            max_retries: 最大重试次数
            api_key: 硅基流动API密钥（可从环境变量 SILICONFLOW_API_KEY 读取）
            model: 模型名称（可从环境变量 SILICONFLOW_MODEL 读取，默认使用 Qwen/Qwen2.5-7B-Instruct）
        """
        # 硅基流动API配置
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY', '')
        self.model = model or os.getenv('SILICONFLOW_MODEL', 'deepseek-chat')  # 默认使用DeepSeek
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        
        # Tavily API配置
        self.tavily_api_key = os.getenv('TAVILY_API_KEY', '')
        self.tavily_api_url = 'https://api.tavily.com/search'

        # ====== 官方RAG配置 ======
        self.rag_enabled = os.getenv("RAG_ENABLED", "0") == "1"
        self.rag_api_url = os.getenv("RAG_API_URL", "")
        self.rag_kb = os.getenv("RAG_KB", "merged_depression_kb")
        self.rag_retrieval_num = int(os.getenv("RAG_RETRIEVAL_NUM", "10"))
        self.rag_select_num = int(os.getenv("RAG_SELECT_NUM", "5"))
        
        self.timeout = timeout or 120  # 默认超时时间120秒
        self.max_retries = max_retries
        self.session = self._create_session()
        
        if not self.api_key:
            logger.warning("未设置硅基流动API密钥，请设置环境变量 SILICONFLOW_API_KEY 或在代码中配置")
        
        if not self.tavily_api_key:
            logger.warning("未设置Tavily API密钥，联网搜索功能将不可用。请设置环境变量 TAVILY_API_KEY")
        
        logger.info(f"心理咨询客户端初始化: 模型={self.model}, API地址={self.api_url}")
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话（支持连接池）"""
        session = requests.Session()
        # 配置连接池
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 我们自己处理重试
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # 设置默认请求头（硅基流动API需要）
        if self.api_key:
            session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
        
        return session
    
    def chat(self, 
             prompt: str,
             history: Optional[List[Tuple[str, str]]] = None,
             max_length: int = 2048,
             top_p: float = 0.8,
             temperature: float = 0.7,
             emotion_context: Optional[Dict] = None,
             enable_web_search: bool = False,
             timeout: Optional[int] = None) -> Tuple[str, List]:
        """
        进行心理咨询对话（兼容EmoLLM接口）
        
        Args:
            prompt: 用户输入的问题
            history: 历史对话记录 [(用户消息, AI回复), ...]
            max_length: 最大生成长度（转换为max_tokens）
            top_p: Top-p采样参数
            temperature: 温度参数
            emotion_context: 情绪上下文（表情、语音等数据）
            enable_web_search: 是否启用联网搜索功能
            timeout: 请求超时时间（秒），如果为None则使用默认值
            
        Returns:
            (response, updated_history): AI回复和更新后的历史记录
        """
        if history is None:
            history = []
        
        # 如果有情绪上下文，增强prompt
        enhanced_prompt = self._enhance_prompt_with_emotion(prompt, emotion_context)

        # ====== 净化 + 结构模板 ======
        retrieval_content = self._rag_retrieve(prompt)
        rag_text = self._format_retrieval_content(retrieval_content)
        enhanced_prompt = self._build_detailed_user_prompt(enhanced_prompt, rag_text)

        # 加这一行！打印出来看看净化后的内容
        logger.info(f"\n[调试] 喂给大模型的干净RAG资料:\n{rag_text}\n")
        
        # 构建系统提示词
        system_prompt = """你是一个由aJupyter、Farewell、jujimeizuo、Smiling&Weeping研发（排名按字母顺序排序，不分先后）、散步提供技术支持、上海人工智能实验室提供支持开发的心理健康大模型。现在你是一个心理专家，我有一些心理问题，请你用专业的知识帮我解决。

当用户询问心理相关问题时：
- 以温暖、共情的方式回应
- 提供专业的心理建议和支持
- 在必要时建议寻求专业帮助

当用户询问一般性问题时（如日期、天气、新闻、最新事件、实时数据等）：
- 如果问题需要实时信息或最新数据，请使用tavily_search函数进行联网搜索
- 直接、准确地回答问题

请用中文回复，语气自然、友好且富有同理心。"""
        
        # 如果有情绪上下文，添加到系统提示词中
        if emotion_context:
            emotion_info = []
            if 'facial_emotion' in emotion_context:
                emotion_info.append(f"面部表情: {emotion_context['facial_emotion']}")
            if 'depression_score' in emotion_context:
                emotion_info.append(f"抑郁评分: {emotion_context['depression_score']}")
            if emotion_info:
                system_prompt += f"\n\n注意：用户当前状态 - {', '.join(emotion_info)}"
        
        # 将history转换为messages格式（硅基流动使用OpenAI格式）
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        for user_msg, ai_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": enhanced_prompt})
        
        # 构建硅基流动API请求数据
        # 增加max_tokens以获得更长的回复（默认2048太小，改为至少4096）
        # 如果max_length小于4096，使用4096；否则使用max_length，但不超过8192
        # 默认更长一点，但不强行 4096（对吞吐更友好）
        default_max = int(os.getenv("LLM_MAX_TOKENS_DEFAULT", "1200"))
        effective_max_tokens = max(256, min(int(max_length or default_max), 4096))
        
        # 获取函数定义（仅当 API Key 存在 且 用户开启了搜索时）
        tools = None
        if self.tavily_api_key and enable_web_search:
            tools = self._get_function_definitions()
        
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": effective_max_tokens,
            "stream": False
        }

        logger.info(
            "[LLM] request prepared stream=%s model=%s prompt_len=%d history_turns=%d rag_hits=%d web_search=%s",
            False,
            self.model,
            len(prompt),
            len(history),
            len(retrieval_content),
            bool(enable_web_search),
        )
        
        # 如果启用了Function Calling，添加到请求中
        if tools:
            request_data["tools"] = tools
            request_data["tool_choice"] = "auto"  # 让模型自动决定是否调用函数
        
        # 使用传入的timeout或默认timeout
        request_timeout = timeout if timeout is not None else self.timeout
        
        # 发送请求（带重试）
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = self.session.post(
                    self.api_url,
                    json=request_data,
                    timeout=request_timeout
                )
                logger.info(
                    "[LLM] response status=%s stream=%s url=%s",
                    response.status_code,
                    False,
                    self.api_url,
                )
                response.raise_for_status()
                
                result = response.json()
                elapsed_time = time.time() - start_time
                
                # 解析硅基流动API响应
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    message = choice.get('message', {})
                    
                    # 检查是否有function call
                    if message.get('tool_calls'):
                        # 处理function call
                        tool_calls = message.get('tool_calls', [])
                        function_results = []
                        
                        for tool_call in tool_calls:
                            function_name = tool_call.get('function', {}).get('name', '')
                            function_args = tool_call.get('function', {}).get('arguments', '')
                            
                            if function_name == 'tavily_search':
                                try:
                                    args = json.loads(function_args) if isinstance(function_args, str) else function_args
                                    search_query = args.get('query', '')
                                    max_results = args.get('max_results', 5)
                                    
                                    logger.info(f"执行Function Call: tavily_search(query={search_query}, max_results={max_results})")
                                    
                                    # 调用Tavily搜索
                                    search_result = self._tavily_search(search_query, max_results)
                                    
                                    # 添加function call结果到messages
                                    function_results.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.get('id', ''),
                                        "content": search_result if search_result else "未找到相关信息"
                                    })
                                    
                                except Exception as e:
                                    logger.error(f"执行Function Call失败: {e}", exc_info=True)
                                    function_results.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call.get('id', ''),
                                        "content": f"搜索失败: {str(e)}"
                                    })
                        
                        # 如果有function call结果，需要再次调用API获取最终回复
                        if function_results:
                            # 添加assistant的function call消息
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": tool_calls
                            })
                            
                            # 添加function call结果
                            messages.extend(function_results)
                            
                            # 再次调用API获取最终回复
                            request_data_final = {
                                "model": self.model,
                                "messages": messages,
                                "temperature": temperature,
                                "top_p": top_p,
                                "max_tokens": effective_max_tokens,
                                "stream": False
                            }
                            
                            if tools:
                                request_data_final["tools"] = tools
                                request_data_final["tool_choice"] = "auto"
                            
                            response_final = self.session.post(
                                self.api_url,
                                json=request_data_final,
                                timeout=request_timeout
                            )
                            logger.info(
                                "[LLM] tool-followup response status=%s stream=%s url=%s",
                                response_final.status_code,
                                False,
                                self.api_url,
                            )
                            response_final.raise_for_status()
                            result_final = response_final.json()
                            
                            if 'choices' in result_final and len(result_final['choices']) > 0:
                                ai_response = result_final['choices'][0].get('message', {}).get('content', '')
                            else:
                                ai_response = "抱歉，处理搜索结果时出现错误。"
                        else:
                            ai_response = message.get('content', '')
                    else:
                        # 没有function call，直接获取回复
                        ai_response = message.get('content', '')
                else:
                    ai_response = ""
                
                if not ai_response:
                    logger.warning("API返回空响应")
                    ai_response = "抱歉，我暂时无法理解您的意思，请重新表述一下。"
                
                # 更新历史记录
                updated_history = history + [(enhanced_prompt, ai_response)]
                
                logger.info(f"心理咨询响应成功 (耗时: {elapsed_time:.2f}s)")
                
                return ai_response, updated_history
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return "抱歉，我现在响应有点慢，请稍后再试。", history
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"连接失败 (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return "抱歉，心理咨询服务暂时不可用，但其他功能正常。", history
                    
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP错误: {e}"
                if hasattr(e.response, 'text'):
                    try:
                        error_detail = e.response.json()
                        error_msg = error_detail.get('error', {}).get('message', error_msg)
                    except:
                        error_msg = e.response.text[:200]
                logger.error(f"请求异常: {error_msg} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return f"抱歉，服务出现异常: {error_msg}", history
                    
            except Exception as e:
                logger.error(f"请求异常: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return f"抱歉，服务出现异常: {str(e)}", history
            
            # 重试前等待
            time.sleep(1)
        
        return "服务繁忙，请稍后再试。", history
    
    def chat_stream(self,
                    prompt: str,
                    history: Optional[List[Tuple[str, str]]] = None,
                    max_length: int = 2048,
                    top_p: float = 0.8,
                    temperature: float = 0.7,
                    emotion_context: Optional[Dict] = None,
                    enable_web_search: bool = False,
                    timeout: Optional[int] = None):
        """流式心理咨询对话（强制搜索版：完美绕过本地模型的工具调用缺陷）"""
        
        # 1. 智能前置联网搜索（关键词拦截法，防止网络信息污染心理学专业知识！）
        search_result = ""
        if self.tavily_api_key and enable_web_search:
            # 定义触发搜索的“时效性/客观性”关键词
            search_keywords = [ '几号', '星期', '日期', '天气', '新闻', '最新', '实时', '时间','查询']
            # 如果提问里包含这些词，才去搜；否则坚决不搜
            needs_search = any(kw in prompt for kw in search_keywords)
            
            if needs_search:
                logger.info(f"🔵 检测到时效性提问，触发联网搜索: {prompt}")
                yield "🔍 **正在请求 Tavily 联网搜索最新信息...**\n\n"
                try:
                    search_result = self._tavily_search(prompt, max_results=3)
                    if search_result:
                        yield "✅ **搜索完成，正在结合最新信息组织语言...**\n\n"
                except Exception as e:
                    logger.error(f"强制搜索出错: {e}")
                    yield f"⚠️ 搜索失败: {e}\n\n"
            else:
                logger.info(f"🟢 专业询问或情感倾诉，跳过网络搜索，保护本地资料纯净度")

        # 2. 准备提示词和上下文
        if history is None:
            history = []
        enhanced_prompt = self._enhance_prompt_with_emotion(prompt, emotion_context)

        # ====== 净化 RAG ======
        retrieval_content = self._rag_retrieve(prompt)
        rag_text = self._format_retrieval_content(retrieval_content)
        
        # 【核心魔法】：把搜索结果和 RAG 知识库无缝融合！
        if search_result:
            if rag_text:
                rag_text = f"【最新联网搜索结果】\n{search_result}\n\n【本地专业知识】\n{rag_text}"
            else:
                rag_text = f"【最新联网搜索结果】\n{search_result}"

        enhanced_prompt = self._build_detailed_user_prompt(enhanced_prompt, rag_text)
                
        # 强制系统提示词（精简版，因为不需要教它怎么调工具了）
        system_prompt = """你是一个由aJupyter、Farewell、jujimeizuo、Smiling&Weeping等研发的心理健康大模型。现在你是一个心理专家。
当用户询问心理相关问题时：
- 以温暖、共情的方式回应并提供专业支持

当用户询问一般性问题时（如日期、天气、新闻、最新事件等）：
- 直接根据我提供给你的【最新联网搜索结果】进行极其准确的客观回答，不要过度发散。

请用中文回复，语气自然、友好且富有同理心。"""
        
        if emotion_context:
            emotion_info = []
            if 'facial_emotion' in emotion_context:
                emotion_info.append(f"面部表情: {emotion_context['facial_emotion']}")
            if 'depression_score' in emotion_context:
                emotion_info.append(f"抑郁评分: {emotion_context['depression_score']}")
            if emotion_info:
                system_prompt += f"\n\n注意：用户当前状态 - {', '.join(emotion_info)}"
        
        messages = [{"role": "system", "content": system_prompt}]
        for user_msg, ai_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
        messages.append({"role": "user", "content": enhanced_prompt})
        
        # 3. 发起请求（去掉了所有 tools 相关的参数，把它当普通聊天发出去）
        default_max = int(os.getenv("LLM_MAX_TOKENS_DEFAULT", "1200"))
        effective_max_tokens = max(256, min(int(max_length or default_max), 4096))
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": effective_max_tokens,
            "stream": True
        }

        logger.info(
            "[LLM] request prepared stream=%s model=%s prompt_len=%d history_turns=%d rag_hits=%d web_search=%s",
            True,
            self.model,
            len(prompt),
            len(history),
            len(retrieval_content),
            bool(enable_web_search),
        )

        request_timeout = timeout if timeout is not None else max(self.timeout, 120)
        
        try:
            response = self.session.post(
                self.api_url,
                json=request_data,
                timeout=(10, request_timeout),
                stream=True
            )
            logger.info(
                "[LLM] response status=%s stream=%s url=%s",
                response.status_code,
                True,
                self.api_url,
            )
            response.raise_for_status()

            has_yielded_real_content = False
            generated_chars = 0

            # 4. 极简解析流数据（代码大幅缩减，因为不需要解析 tool_calls 了）
            for line in response.iter_lines():
                if not line: continue
                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '): continue
                
                try:
                    data = json.loads(line_str[6:])
                    if not data.get('choices'): continue
                    
                    delta = data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    
                    if content:
                        # 过滤起手式的空白字符
                        if not has_yielded_real_content and not content.strip():
                            continue
                        has_yielded_real_content = True
                        generated_chars += len(content)
                        yield content
                        
                except Exception as e:
                    logger.warning(f"解析流式数据失败: {e}")
                    continue

            logger.info("[LLM] stream completed chars=%d", generated_chars)

        except requests.exceptions.Timeout as e:
            logger.error(f"流式请求超时: {e}", exc_info=True)
            yield f"\n\n抱歉，请求超时，AI服务响应较慢，请稍后重试"
        except Exception as e:
            logger.error(f"流式请求异常: {e}", exc_info=True)
            yield f"\n\n抱歉，服务异常: {str(e)}"
    
    def _build_detailed_user_prompt(self, user_prompt: str, rag_text: str) -> str:
        """
        自然深度版：彻底抛弃死板模板，优先直击问题核心，根据内容逻辑自然展开。
        """
        base = user_prompt.strip()

        if rag_text:
            prompt = (
                f"【专业知识库】\n{rag_text}\n\n"
                f"【用户提问】\n{base}\n\n"
                f"你是一位经验丰富的资深心理专家。请结合知识库，以专业且自然流畅的风格进行解答：\n"
                f"1. **分类响应**：\n"
                f"   - **日常琐事**（如日期、天气）：请**极其简练**地一句话回答，不废话，不提心理建议。\n"
                f"   - **专业问询**（如量表内容、名词解释、心理问题）：请开启“专家深度解答”模式。**严禁使用固定的模板套话**（如“核心定义”、“实际应用场景”等死板标题）。\n"
                f"2. **直接回答**：首先必须正面、直接地回答用户最核心的诉求（例如：问清单就先列清单，问定义就先给定义）。\n"
                f"3. **逻辑展开**：在直接回答后，根据内容本身的逻辑，自然地延伸相关背景、原理或注意事项。字数要充实，展现专业深度。\n"
                f"4. **灵活排版**：充分使用 ### 标题 和 **加粗** 来增强可读性，但标题名称应根据内容灵活撰写，不要千篇一律。\n"
                f"5. **人文关怀**：仅在结尾针对心理问题提供一段温暖、自然的建议，不要写得像操作手册。"
            )
        else:
            prompt = (
                f"你是一名专业温暖的心理专家。用户提问：{base}\n\n"
                f"要求：琐事请直接简练回答；心理或情感问题请根据你的专业沉淀，深入浅出地进行逻辑严密的论述，展示专业深度与关怀。"
            )
            
        return prompt

    def _format_retrieval_content(self, retrieval_content: List[str]) -> str:
        """
        极简安全版：绝不删除任何一行资料，防止上下文断裂。
        只是把生硬的 JSON 键值对替换成大模型容易理解的自然语言。
        """
        if not retrieval_content:
            return ""

        cleaned = []
        for s in retrieval_content:
            if not s:
                continue
            
            s = str(s).strip()
            
            # 把代码格式的 input/output 翻译成提示词
            s = s.replace('"input":', '【参考问题】').replace('"output":', '【参考解答】')
            
            # 去掉两端多余的引号和逗号，让文本更干净
            s = s.strip('", \n\t')
            
            if s:
                cleaned.append(f"- {s}")

        return "\n".join(cleaned)
    
    def _rag_retrieve(self, query: str):
        """调用 EmoLLM 官方RAG服务，返回 demo 里那种 retrieval_content（list）"""
        if not self.rag_enabled or not self.rag_api_url:
            return []
        try:
            logger.info(
                "[RAG] request url=%s kb=%s retrieval_num=%d select_num=%d query_len=%d",
                self.rag_api_url,
                self.rag_kb,
                self.rag_retrieval_num,
                self.rag_select_num,
                len(query),
            )
            r = requests.post(
                self.rag_api_url,
                json={
                    "query": query,
                    "kb": self.rag_kb,
                    "retrieval_num": self.rag_retrieval_num,
                    "select_num": self.rag_select_num
                },
                timeout=(3, 15)
            )
            r.raise_for_status()
            data = r.json()
            content = data.get("content", []) or []
            logger.info("[RAG] response status=%s hits=%d", r.status_code, len(content))
            # 关键：返回 content(list)，这样拼 prompt 的表现最接近 demo
            return content
        except Exception as e:
            logger.warning(f"[RAG] retrieve failed: {e}")
            return []
    
    def _tavily_search(self, query: str, max_results: int = 5) -> str:
        """
        使用Tavily API进行联网搜索
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            
        Returns:
            str: 格式化后的搜索结果文本，如果搜索失败返回空字符串
        """
        if not self.tavily_api_key:
            logger.warning("Tavily API密钥未设置，无法进行搜索")
            return ""
        
        try:
            search_data = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False
            }
            
            response = self.session.post(
                self.tavily_api_url,
                json=search_data,
                timeout=(5, 15)  # (connect_timeout, read_timeout)
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # 提取直接答案（如果存在）
            if data.get('answer'):
                results.append(f"直接答案: {data['answer']}")
            
            # 提取搜索结果
            if data.get('results'):
                results.append("\n搜索结果:")
                for idx, result in enumerate(data['results'][:max_results], 1):
                    title = result.get('title', '')
                    content = result.get('content', '')
                    url = result.get('url', '')
                    
                    if title or content:
                        results.append(f"\n{idx}. {title}")
                        if content:
                            # 限制内容长度，避免过长
                            content_short = content[:300] + "..." if len(content) > 300 else content
                            results.append(f"   {content_short}")
                        if url:
                            results.append(f"   来源: {url}")
            
            if results:
                search_result = "\n".join(results)
                logger.info(f"Tavily搜索成功: {query[:50]}... (结果长度: {len(search_result)})")
                return search_result
            else:
                logger.warning(f"Tavily搜索无结果: {query[:50]}...")
                return ""
                
        except requests.exceptions.Timeout as e:
            logger.warning(f"Tavily搜索超时: {query[:50]}... (错误: {str(e)})")
            return ""
        except requests.exceptions.RequestException as e:
            logger.warning(f"Tavily搜索请求失败: {query[:50]}... (错误: {str(e)})")
            return ""
        except Exception as e:
            logger.warning(f"Tavily搜索异常: {query[:50]}... (错误: {str(e)})")
            return ""
    
    def _get_function_definitions(self) -> List[Dict]:
        """
        获取Function Calling的函数定义
        
        Returns:
            List[Dict]: 函数定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "tavily_search",
                    "description": "使用Tavily API进行联网搜索，获取最新的网络信息。当用户询问需要实时信息的问题（如当前日期、新闻、最新事件、实时数据等）时，应该调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索查询关键词，应该简洁明确"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数，默认为5",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def _enhance_prompt_with_emotion(self, 
                                     prompt: str, 
                                     emotion_context: Optional[Dict]) -> str:
        """
        根据情绪上下文增强提示词
        
        Args:
            prompt: 原始提示
            emotion_context: 情绪上下文数据
            
        Returns:
            增强后的提示词
        """
        if not emotion_context:
            return prompt
        
        emotion_info = []
        
        # 添加表情信息
        if 'facial_emotion' in emotion_context:
            emotion = emotion_context['facial_emotion']
            confidence = emotion_context.get('facial_confidence', 0)
            emotion_info.append(f"面部表情: {emotion} (置信度: {confidence:.2f})")
        
        # 添加语音情绪信息
        if 'speech_emotion' in emotion_context:
            emotion = emotion_context['speech_emotion']
            emotion_info.append(f"语音情绪: {emotion}")
        
        # 添加抑郁评分
        if 'depression_score' in emotion_context:
            score = emotion_context['depression_score']
            emotion_info.append(f"抑郁评分: {score}")
        
        # 添加脑电数据
        if 'eeg_data' in emotion_context:
            eeg = emotion_context['eeg_data']
            emotion_info.append(f"脑电状态: {eeg}")
        
        if emotion_info:
            emotion_str = "、".join(emotion_info)
            enhanced = f"[用户当前状态: {emotion_str}]\n\n用户说: {prompt}"
            return enhanced
        
        return prompt
    
    def check_health(self) -> bool:
        """
        检查服务健康状态
        
        Returns:
            True if healthy, False otherwise
        """
        if not self.api_key:
            logger.warning("未设置API密钥，健康检查失败")
            return False
            
        try:
            # 发送简单测试请求
            test_data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个助手。"},
                    {"role": "user", "content": "你好"}
                ],
                "max_tokens": 10
            }
            response = self.session.post(
                self.api_url,
                json=test_data,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def close(self):
        """关闭客户端会话"""
        self.session.close()
        logger.info("心理咨询客户端已关闭")


# 全局客户端实例（单例模式）
_emollm_client = None


def get_emollm_client(api_url: str = None, 
                     api_key: str = None,
                     model: str = None) -> EmoLLMClient:
    """
    获取心理咨询客户端实例（单例，兼容EmoLLM接口）
    
    Args:
        api_url: API服务地址（可选，默认使用硅基流动）
        api_key: API密钥（可选，优先从环境变量读取）
        model: 模型名称（可选，优先从环境变量读取）
    
    Returns:
        EmoLLMClient实例
    """
    global _emollm_client
    
    if _emollm_client is None:
        _emollm_client = EmoLLMClient(
            api_url=api_url,
            api_key=api_key,
            model=model
        )
        logger.info("创建心理咨询客户端实例（硅基流动）")
    
    return _emollm_client


# 便捷函数
def ask_emollm(prompt: str, 
               history: Optional[List] = None,
               emotion_context: Optional[Dict] = None) -> Tuple[str, List]:
    """
    便捷函数：向EmoLLM提问
    
    Args:
        prompt: 用户问题
        history: 对话历史
        emotion_context: 情绪上下文
        
    Returns:
        (response, history): AI回复和历史记录
    """
    client = get_emollm_client()
    return client.chat(prompt, history, emotion_context=emotion_context)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("心理咨询客户端测试（硅基流动API）")
    print("=" * 60)
    
    # 检查API密钥
    api_key = os.getenv('SILICONFLOW_API_KEY')
    if not api_key:
        print("⚠ 警告: 未设置 SILICONFLOW_API_KEY 环境变量")
        print("请设置环境变量: export SILICONFLOW_API_KEY='your-api-key'")
        api_key = input("或者直接输入API密钥（测试用）: ").strip()
        if not api_key:
            print("✗ 无法继续测试，需要API密钥")
            exit(1)
    
    # 创建客户端
    client = EmoLLMClient(api_key=api_key)
    
    # 健康检查
    print("\n1. 健康检查...")
    if client.check_health():
        print("✓ 心理咨询服务正常")
    else:
        print("✗ 心理咨询服务不可用，请检查API密钥和网络连接")
        exit(1)
    
    # 简单对话测试
    print("\n2. 简单对话测试...")
    response, history = client.chat("你好，我最近感觉很焦虑")
    print(f"AI回复: {response}")
    
    # 带情绪上下文的对话
    print("\n3. 带情绪上下文的对话...")
    emotion_ctx = {
        'facial_emotion': 'sad',
        'facial_confidence': 0.85,
        'depression_score': 65
    }
    response, history = client.chat(
        "我该怎么办？",
        history=history,
        emotion_context=emotion_ctx
    )
    print(f"AI回复: {response}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
