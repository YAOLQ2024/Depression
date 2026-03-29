#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EmoLLM API客户端
用于调用心理咨询服务（支持硅基流动API）
"""

import requests
import logging
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time
from urllib.parse import urlparse

from new_features.chat_intent_router.policy import (
    GREETING_REPLY,
    INTENT_GENERAL,
    INTENT_CASUAL,
    INTENT_IDENTITY,
    INTENT_PSYCHOLOGY,
    IDENTITY_REPLY,
    REALTIME_REFUSAL,
    REALTIME_UNAVAILABLE,
    THANKS_REPLY,
    ChatIntentDecision,
    classify_chat_intent,
)

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
        self.llm_router_enabled = os.getenv("CHAT_ROUTER_LLM_ENABLED", "1") == "1"
        self.llm_router_timeout = max(3, int(os.getenv("CHAT_ROUTER_LLM_TIMEOUT", "8")))
        self.llm_router_max_tokens = max(64, min(int(os.getenv("CHAT_ROUTER_LLM_MAX_TOKENS", "160")), 512))
        
        self.timeout = timeout or 120  # 默认超时时间120秒
        self.max_retries = max_retries
        self.session = self._create_session()
        self.local_session = self._create_session(trust_env=False)
        self.direct_session = self._create_session(trust_env=False, include_auth=False)
        
        if not self.api_key:
            logger.warning("未设置硅基流动API密钥，请设置环境变量 SILICONFLOW_API_KEY 或在代码中配置")
        
        if not self.tavily_api_key:
            logger.warning("未设置Tavily API密钥，联网搜索功能将不可用。请设置环境变量 TAVILY_API_KEY")
        
        logger.info(f"心理咨询客户端初始化: 模型={self.model}, API地址={self.api_url}")
    
    def _create_session(self, trust_env: bool = True, include_auth: bool = True) -> requests.Session:
        """创建HTTP会话（支持连接池）"""
        session = requests.Session()
        session.trust_env = trust_env
        # 配置连接池
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 我们自己处理重试
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # 设置默认请求头（硅基流动API需要）
        if include_auth and self.api_key:
            session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
        
        return session

    def _uses_local_url(self, url: str) -> bool:
        try:
            host = (urlparse(str(url or "")).hostname or "").lower()
        except Exception:
            return False
        return host in {"127.0.0.1", "localhost", "0.0.0.0"}

    def _session_for_url(self, url: str) -> requests.Session:
        return self.local_session if self._uses_local_url(url) else self.session

    def _post(self, url: str, **kwargs):
        return self._session_for_url(url).post(url, **kwargs)

    def _tavily_timeouts(self) -> Tuple[int, int]:
        """Keep Tavily slightly looser than local inference endpoints."""
        return (5, 20)

    def _request_tavily(self, search_data: Dict, session: requests.Session) -> Dict:
        connect_timeout, read_timeout = self._tavily_timeouts()
        response = session.post(
            self.tavily_api_url,
            json=search_data,
            timeout=(connect_timeout, read_timeout),
        )
        response.raise_for_status()
        return response.json()

    def _classify_intent(self, prompt: str, enable_web_search: bool) -> ChatIntentDecision:
        """Classify the current user message before building prompts."""
        decision = classify_chat_intent(
            prompt,
            enable_web_search=enable_web_search,
            search_available=bool(self.tavily_api_key),
        )
        logger.info(
            "[Route] intent=%s rag=%s web_search=%s direct=%s reason=%s",
            decision.intent,
            decision.use_rag,
            decision.use_web_search,
            bool(decision.direct_response),
            decision.reason,
        )
        return decision

    def _decide_route(
        self,
        prompt: str,
        *,
        enable_web_search: bool,
        assessment_context: Optional[str] = None,
    ) -> ChatIntentDecision:
        decision = self._classify_intent(prompt, enable_web_search)
        decision = self._adjust_decision_for_assessment_context(decision, assessment_context)
        decision = self._refine_decision_with_llm(prompt, enable_web_search, decision)
        return decision

    def _adjust_decision_for_assessment_context(
        self,
        decision: ChatIntentDecision,
        assessment_context: Optional[str],
    ) -> ChatIntentDecision:
        """Upgrade vague requests with attached assessment data into psychology routing."""
        if not assessment_context or decision.intent != INTENT_GENERAL:
            return decision

        adjusted = ChatIntentDecision(
            intent=INTENT_PSYCHOLOGY,
            use_rag=True,
            use_web_search=False,
            direct_response=None,
            response_style="psychology",
            reason="assessment-context",
        )
        logger.info(
            "[Route] intent override=%s->%s rag=%s reason=%s",
            decision.intent,
            adjusted.intent,
            adjusted.use_rag,
            adjusted.reason,
        )
        return adjusted

    def _refine_decision_with_llm(
        self,
        prompt: str,
        enable_web_search: bool,
        decision: ChatIntentDecision,
    ) -> ChatIntentDecision:
        if decision.reason != "default-general":
            return decision
        if not self.llm_router_enabled:
            return decision

        llm_decision = self._classify_intent_with_llm(prompt, enable_web_search)
        if not llm_decision:
            fallback_decision = self._fallback_to_search_when_user_enabled(prompt, enable_web_search, decision)
            if fallback_decision:
                logger.info(
                    "[Route] search-toggle fallback intent=%s rag=%s web_search=%s reason=%s",
                    fallback_decision.intent,
                    fallback_decision.use_rag,
                    fallback_decision.use_web_search,
                    fallback_decision.reason,
                )
                return fallback_decision
            logger.info("[Route] llm-refine skipped: no upgrade for prompt=%s", str(prompt or "")[:60])
            return decision

        logger.info(
            "[Route] llm-refine intent=%s rag=%s web_search=%s direct=%s reason=%s",
            llm_decision.intent,
            llm_decision.use_rag,
            llm_decision.use_web_search,
            bool(llm_decision.direct_response),
            llm_decision.reason,
        )
        return llm_decision

    def _classify_intent_with_llm(
        self,
        prompt: str,
        enable_web_search: bool,
    ) -> Optional[ChatIntentDecision]:
        text = str(prompt or "").strip()
        if not text:
            return None

        system_prompt = (
            "你是聊天路由分类器，不负责回答用户，只负责输出路由决策。"
            "请只输出单行 JSON，不要使用 markdown，不要补充说明。\n"
            "JSON 字段固定为："
            '{"intent":"casual|identity|realtime|psychology|general",'
            '"realtime_kind":"none|local_datetime|calendar_lunar|latest_fact",'
            '"confidence":"high|medium|low",'
            '"reason":"简短英文短语"}\n'
            "判定规则：\n"
            "1. psychology：心理、情绪、压力、咨询、量表、报告解读、自我状态分析。\n"
            "2. realtime/local_datetime：问今天几号、现在几点、星期几、当前时间等，系统时间可直接回答。\n"
            "3. realtime/calendar_lunar：问农历、阴历、黄历、初几、节气、法定节假日等，需要结合当前日期查询。\n"
            "4. realtime/latest_fact：问天气、新闻、最新事件、股价、汇率、比分、现任身份、近期政策等需要最新外部事实的问题。\n"
            "5. identity：问你是谁、你能做什么。\n"
            "6. casual：打招呼、感谢、寒暄。\n"
            "7. general：其他稳定知识、写作、解释、通用问答。\n"
            "如果不确定，只有在明显依赖当前外部世界状态时才判为 realtime。"
        )
        request_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户问题：{text}"},
            ],
            "temperature": 0.0,
            "top_p": 0.1,
            "max_tokens": self.llm_router_max_tokens,
            "stream": False,
        }

        try:
            response = self._post(
                self.api_url,
                json=request_data,
                timeout=(3, self.llm_router_timeout),
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                logger.info("[Route] llm router returned no choices for prompt=%s", text[:60])
                return None
            content = (choices[0].get("message") or {}).get("content", "")
            logger.info("[Route] llm router raw=%s", str(content or "").strip()[:300])
            parsed = self._parse_router_json(content)
            if not parsed:
                return None
            return self._build_llm_router_decision(
                prompt=text,
                parsed=parsed,
                enable_web_search=enable_web_search,
            )
        except Exception as exc:
            logger.warning("[Route] llm router failed: %s", exc)
            return None

    def _parse_router_json(self, content: str) -> Optional[Dict[str, str]]:
        text = str(content or "").strip()
        if not text:
            return None

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

            parsed = self._parse_router_text_fallback(text)
            if parsed:
                return parsed

            logger.warning("[Route] llm router parse failed: %s", text[:200])
            return None

    def _parse_router_text_fallback(self, text: str) -> Optional[Dict[str, str]]:
        raw = str(text or "").strip()
        if not raw:
            return None

        intent = self._extract_enum_value(raw.lower(), ("casual", "identity", "realtime", "psychology", "general"))
        realtime_kind = self._extract_enum_value(raw.lower(), ("local_datetime", "calendar_lunar", "latest_fact", "none"))
        confidence = self._extract_enum_value(raw.lower(), ("high", "medium", "low"))

        if not intent and "心理" in raw:
            intent = "psychology"
        if not intent and ("实时" in raw or "联网" in raw or "最新" in raw):
            intent = "realtime"
        if not realtime_kind and ("农历" in raw or "黄历" in raw or "阴历" in raw):
            realtime_kind = "calendar_lunar"
        if not realtime_kind and ("时间" in raw or "日期" in raw or "几点" in raw or "星期" in raw):
            realtime_kind = "local_datetime"
        if not realtime_kind and ("票房" in raw or "天气" in raw or "新闻" in raw or "汇率" in raw or "股价" in raw):
            realtime_kind = "latest_fact"
        if not confidence:
            confidence = "medium"

        if not intent and realtime_kind and realtime_kind != "none":
            intent = "realtime"

        if not intent:
            return None

        reason = raw.splitlines()[0].strip()[:48] or intent
        return {
            "intent": intent,
            "realtime_kind": realtime_kind or "none",
            "confidence": confidence,
            "reason": reason,
        }

    def _extract_enum_value(self, text: str, candidates) -> Optional[str]:
        for candidate in candidates:
            if re.search(rf"\b{re.escape(candidate)}\b", text):
                return candidate
        return None

    def _fallback_to_search_when_user_enabled(
        self,
        prompt: str,
        enable_web_search: bool,
        decision: ChatIntentDecision,
    ) -> Optional[ChatIntentDecision]:
        if not enable_web_search or not self.tavily_api_key:
            return None
        if decision.reason != "default-general":
            return None
        if not self._looks_like_information_query(prompt):
            return None

        return ChatIntentDecision(
            intent="realtime",
            use_rag=False,
            use_web_search=True,
            direct_response=None,
            response_style="realtime",
            reason="search-toggle-fallback",
        )

    def _looks_like_information_query(self, prompt: str) -> bool:
        text = str(prompt or "").strip()
        if not text:
            return False
        lowered = text.lower()

        if any(token in lowered for token in ("写一篇", "写一个", "写个", "润色", "翻译", "总结", "改写", "生成", "代码")):
            return False

        info_markers = (
            "谁",
            "什么",
            "哪",
            "哪个",
            "多少",
            "几",
            "多久",
            "如何",
            "为什么",
            "吗",
            "？",
            "?",
            "最近",
            "最新",
            "当前",
            "现任",
            "现在",
        )
        return any(marker in text for marker in info_markers)

    def _build_llm_router_decision(
        self,
        *,
        prompt: str,
        parsed: Dict[str, str],
        enable_web_search: bool,
    ) -> Optional[ChatIntentDecision]:
        intent = str(parsed.get("intent") or "").strip().lower()
        realtime_kind = str(parsed.get("realtime_kind") or "none").strip().lower()
        confidence = str(parsed.get("confidence") or "low").strip().lower()
        reason = str(parsed.get("reason") or intent or "llm").strip().lower().replace(" ", "-")
        router_reason = f"llm-router:{reason or 'unknown'}"

        if confidence not in {"high", "medium"}:
            logger.info(
                "[Route] llm-refine ignored due to low confidence: intent=%s realtime_kind=%s confidence=%s reason=%s",
                intent or "unknown",
                realtime_kind,
                confidence,
                router_reason,
            )
            return None

        if intent == INTENT_PSYCHOLOGY:
            return ChatIntentDecision(
                intent=INTENT_PSYCHOLOGY,
                use_rag=True,
                use_web_search=False,
                direct_response=None,
                response_style="psychology",
                reason=router_reason,
            )

        if intent == INTENT_IDENTITY:
            return ChatIntentDecision(
                intent=INTENT_IDENTITY,
                use_rag=False,
                use_web_search=False,
                direct_response=IDENTITY_REPLY,
                response_style="identity",
                reason=router_reason,
            )

        if intent == INTENT_CASUAL:
            reply = THANKS_REPLY if any(token in prompt for token in ("谢谢", "感谢", "多谢")) else GREETING_REPLY
            return ChatIntentDecision(
                intent=INTENT_CASUAL,
                use_rag=False,
                use_web_search=False,
                direct_response=reply,
                response_style="casual",
                reason=router_reason,
            )

        if intent == "realtime" or realtime_kind != "none":
            return self._build_llm_realtime_decision(
                prompt=prompt,
                realtime_kind=realtime_kind,
                enable_web_search=enable_web_search,
                reason=router_reason,
            )

        if intent == INTENT_GENERAL:
            return ChatIntentDecision(
                intent=INTENT_GENERAL,
                use_rag=False,
                use_web_search=False,
                direct_response=None,
                response_style="general",
                reason=router_reason,
            )

        return None

    def _build_llm_realtime_decision(
        self,
        *,
        prompt: str,
        realtime_kind: str,
        enable_web_search: bool,
        reason: str,
    ) -> ChatIntentDecision:
        search_available = bool(self.tavily_api_key)
        kind = realtime_kind if realtime_kind in {"local_datetime", "calendar_lunar", "latest_fact"} else "latest_fact"

        if kind == "local_datetime":
            if enable_web_search and search_available:
                return ChatIntentDecision(
                    intent="realtime",
                    use_rag=False,
                    use_web_search=True,
                    direct_response=None,
                    response_style="realtime",
                    reason=reason,
                )
            return ChatIntentDecision(
                intent="realtime",
                use_rag=False,
                use_web_search=False,
                direct_response=self._build_datetime_answer(prompt),
                response_style="realtime",
                reason=reason,
            )

        if enable_web_search and search_available:
            return ChatIntentDecision(
                intent="realtime",
                use_rag=False,
                use_web_search=True,
                direct_response=None,
                response_style="realtime",
                reason=reason,
            )

        return ChatIntentDecision(
            intent="realtime",
            use_rag=False,
            use_web_search=False,
            direct_response=REALTIME_UNAVAILABLE if enable_web_search else REALTIME_REFUSAL,
            response_style="realtime",
            reason=reason,
        )

    def _is_datetime_query(self, prompt: str) -> bool:
        text = str(prompt or "")
        keywords = ("今天几号", "今天星期几", "星期几", "周几", "几月几号", "日期", "几号", "现在几点", "几点", "当前时间")
        return any(keyword in text for keyword in keywords)

    def _is_lunar_query(self, prompt: str) -> bool:
        text = str(prompt or "")
        keywords = ("农历", "阴历", "黄历", "老黄历")
        return any(keyword in text for keyword in keywords)

    def _is_weather_query(self, prompt: str) -> bool:
        text = str(prompt or "")
        return "天气" in text or "气温" in text or "温度" in text

    def _normalize_web_search_query(self, prompt: str) -> str:
        text = str(prompt or "").strip()
        text = re.sub(r"\s+", "", text)

        cleanup_phrases = [
            "你说错了",
            "重新搜索",
            "重新查",
            "重新查询",
            "再搜索一遍",
            "再查一遍",
            "确认一下",
            "确认",
            "请问",
            "请你",
            "帮我",
            "麻烦你",
            "告诉我",
            "查一下",
            "查询一下",
            "搜索一下",
        ]
        for phrase in cleanup_phrases:
            text = text.replace(phrase, "")
        text = text.strip("：:，,。！？? ")

        if self._is_lunar_query(prompt):
            return "今天 农历 日期 黄历"

        if self._is_datetime_query(prompt):
            return "北京时间 当前日期 星期几 现在时间"

        if self._is_weather_query(prompt):
            location_match = re.search(r"(.{1,12}?)(?:今天|今日|现在)?(?:的)?天气", text)
            location = location_match.group(1).strip("的") if location_match else ""
            if location and location not in ("今天", "今日", "现在"):
                return f"{location} 今天天气 实时 气温 风力"
            return f"{text or '当前地区'} 实时天气"

        return text or str(prompt or "").strip()

    def _build_realtime_context(self, prompt: str) -> str:
        if not self._is_datetime_query(prompt):
            return ""

        now = datetime.now()
        weekday_map = "一二三四五六日"
        weekday_text = f"星期{weekday_map[now.weekday()]}"
        return (
            "【系统时间（Asia/Shanghai）】\n"
            f"当前日期: {now:%Y-%m-%d}\n"
            f"当前星期: {weekday_text}\n"
            f"当前时间: {now:%H:%M:%S}"
        )

    def _build_datetime_answer(self, prompt: str) -> str:
        now = datetime.now()
        weekday_map = "一二三四五六日"
        weekday_text = f"星期{weekday_map[now.weekday()]}"

        if "几点" in prompt or "时间" in prompt:
            return f"根据当前系统时间（Asia/Shanghai），现在是 {now:%Y-%m-%d %H:%M:%S}，{weekday_text}。"

        return f"根据当前系统时间（Asia/Shanghai），今天是 {now:%Y年%m月%d日}，{weekday_text}。"

    def _build_datetime_fallback_after_search(self, prompt: str) -> str:
        local_answer = self._build_datetime_answer(prompt)
        return f"联网搜索未返回有效时间结果，以下改用系统时间回答。\n\n{local_answer}"

    def _build_response_meta(
        self,
        *,
        prompt: str,
        decision: ChatIntentDecision,
        search_result: str = "",
        direct_response: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        is_datetime_query = self._is_datetime_query(prompt) or "local_datetime" in decision.reason
        is_lunar_query = self._is_lunar_query(prompt) or "calendar_lunar" in decision.reason
        if decision.intent != "realtime" or not (is_datetime_query or is_lunar_query):
            return None

        if decision.use_web_search and search_result:
            return {
                "badge": "联网日历" if is_lunar_query else "联网时间",
                "source": "web_search",
                "detail": "当前回答优先依据联网搜索结果。",
            }

        if is_datetime_query and decision.use_web_search and direct_response:
            return {
                "badge": "本地时间",
                "source": "system_time_fallback",
                "detail": "联网搜索失败，已回退为系统时间。",
            }

        if is_lunar_query:
            return None

        return {
            "badge": "本地时间",
            "source": "system_time",
            "detail": "当前回答依据系统时间。",
        }

    def _perform_web_search(self, prompt: str, max_results: int = 3) -> str:
        search_query = self._normalize_web_search_query(prompt)
        logger.info("[WebSearch] normalized query=%s original=%s", search_query, str(prompt or "")[:80])
        return self._tavily_search(search_query, max_results=max_results)

    def _extract_focus_term(self, prompt: str) -> str:
        text = str(prompt or "").strip()
        if not text:
            return ""

        parts = re.split(r"(?:是什么|是啥|什么意思|代表什么)", text, maxsplit=1)
        if not parts:
            return ""

        candidate = parts[0].strip("：:，,。！？? ")
        for prefix in (
            "请问",
            "请你",
            "帮我解释一下",
            "帮我解释",
            "帮我介绍一下",
            "帮我介绍",
            "帮我说一下",
            "告诉我",
            "帮我",
            "请解释一下",
            "请解释",
            "解释一下",
            "解释",
        ):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix):].strip("：:，,。！？? ")

        if not candidate or len(candidate) > 24 or "\n" in candidate:
            return ""
        return candidate

    def _maybe_bold_focus_term(self, prompt: str, response: str) -> str:
        focus_term = self._extract_focus_term(prompt)
        if not focus_term:
            return response
        if f"**{focus_term}**" in response:
            return response
        return re.sub(re.escape(focus_term), lambda _: f"**{focus_term}**", response, count=1)

    def _postprocess_response(self, prompt: str, decision: ChatIntentDecision, response: str) -> str:
        if not response:
            return response
        if decision.intent == INTENT_PSYCHOLOGY:
            return self._maybe_bold_focus_term(prompt, response)
        return response

    def _iter_local_response_chunks(self, response: str, chunk_size: int = 24):
        text = str(response or "")
        if not text:
            return
        for idx in range(0, len(text), chunk_size):
            yield text[idx:idx + chunk_size]

    def _build_system_prompt_for_intent(
        self,
        decision: ChatIntentDecision,
        emotion_context: Optional[Dict] = None,
    ) -> str:
        """Build a route-specific system prompt."""
        if decision.intent == INTENT_PSYCHOLOGY:
            system_prompt = (
                "你是一个心理健康咨询助手。面对心理、情绪、量表相关问题时，"
                "请先直接回应用户当前最核心的诉求，再给出必要的专业解释和温和建议。"
                "不要把普通问题回答成心理学名词百科，也不要输出与当前问题无关的术语清单。"
                "如果用户明确询问某个量表、术语或缩写，首次提到核心名词时请用 Markdown 加粗。"
                "请用中文回复，语气自然、友好、共情。"
            )
        elif decision.intent == "realtime":
            system_prompt = (
                "你是一个信息整理助手。优先依据我提供的【最新联网搜索结果】回答。"
                "如果搜索结果不足以支撑结论，再结合我额外提供的【系统时间（Asia/Shanghai）】作为补充或回退。"
                "不要依赖过时记忆，不要补充心理建议。请用中文简洁作答。"
            )
        else:
            system_prompt = (
                "你是一个中文助手。请针对用户问题直接、简洁、具体地回答。"
                "除非用户明确询问心理学或量表，否则不要扩展成心理学名词解释、量表说明或泛泛的心理建议。"
                "请用中文自然作答。"
            )

        if emotion_context and decision.intent == INTENT_PSYCHOLOGY:
            emotion_info = []
            if 'facial_emotion' in emotion_context:
                emotion_info.append(f"面部表情: {emotion_context['facial_emotion']}")
            if 'depression_score' in emotion_context:
                emotion_info.append(f"抑郁评分: {emotion_context['depression_score']}")
            if emotion_info:
                system_prompt += f"\n\n注意：用户当前状态 - {', '.join(emotion_info)}"

        return system_prompt

    def _build_user_prompt_for_intent(
        self,
        prompt: str,
        decision: ChatIntentDecision,
        rag_text: str = "",
        search_result: str = "",
        realtime_context: str = "",
        assessment_context: str = "",
    ) -> str:
        """Build the final user prompt according to the selected route."""
        base = str(prompt or "").strip()
        assessment_block = ""
        if assessment_context and decision.intent in (INTENT_PSYCHOLOGY, INTENT_GENERAL):
            assessment_block = f"【最近评估背景】\n{assessment_context.strip()}\n\n"

        if decision.intent == INTENT_PSYCHOLOGY:
            if rag_text:
                return (
                    assessment_block +
                    f"【专业知识库】\n{rag_text}\n\n"
                    f"【用户提问】\n{base}\n\n"
                    "请先直接回答用户当前最核心的问题，再在必要时补充专业解释。"
                    "如果用户在问明确的量表、术语或缩写，回答开头首次出现该名词时请用 Markdown 加粗。"
                    "仅围绕当前问题展开，不要输出无关的心理学术语清单。"
                    "除非用户明确要求列表或量表条目，否则不要堆砌长列表。"
                )
            return (
                assessment_block +
                f"【用户提问】\n{base}\n\n"
                "请先共情，再直接回应当前问题。不要输出无关的心理学名词解释。"
                "如果用户在问明确的量表、术语或缩写，回答开头首次出现该名词时请用 Markdown 加粗。"
            )

        if decision.intent == "realtime":
            context_parts = []
            if realtime_context:
                context_parts.append(realtime_context)
            context_parts.append(f"【最新联网搜索结果】\n{search_result}")
            context_parts.append(f"【用户问题】\n{base}")
            return (
                "\n\n".join(context_parts)
                + "\n\n"
                "请优先基于上面的最新搜索结果作答；如果搜索结果不足以支持结论，且提供了系统时间，可以明确说明后将系统时间作为补充。"
            )

        return (
            assessment_block +
            f"【用户问题】\n{base}\n\n"
            "请直接、简洁、准确回答。除非用户明确询问心理学，否则不要扩展为心理学名词解释、量表说明或泛泛的心理建议。"
        )

    def _prepare_chat_request(
        self,
        *,
        prompt: str,
        history: Optional[List[Tuple[str, str]]],
        emotion_context: Optional[Dict],
        assessment_context: Optional[str],
        enable_web_search: bool,
        decision: Optional[ChatIntentDecision] = None,
        search_result_override: Optional[str] = None,
    ) -> Dict:
        """Prepare routed prompts, RAG, and optional search results for a chat request."""
        history = history or []
        decision = decision or self._decide_route(
            prompt,
            enable_web_search=enable_web_search,
            assessment_context=assessment_context,
        )

        if decision.direct_response:
            return {
                "decision": decision,
                "history": history,
                "direct_response": decision.direct_response,
                "messages": [],
                "retrieval_content": [],
                "search_result": "",
                "final_prompt": prompt,
            }

        search_result = ""
        if decision.use_web_search:
            search_result = (
                search_result_override
                if search_result_override is not None
                else self._perform_web_search(prompt, max_results=3)
            )
            if not search_result:
                direct_response = None
                if decision.intent == "realtime" and self._is_datetime_query(prompt):
                    direct_response = self._build_datetime_fallback_after_search(prompt)
                return {
                    "decision": decision,
                    "history": history,
                    "direct_response": direct_response or "联网搜索未返回有效结果，暂时无法准确回答这个最新信息问题。",
                    "messages": [],
                    "retrieval_content": [],
                    "search_result": "",
                    "final_prompt": prompt,
                }

        if decision.intent == "realtime" and self._is_datetime_query(prompt):
            if decision.use_web_search and search_result:
                logger.info("[Route] realtime datetime will prefer web search over system time")
            else:
                return {
                    "decision": decision,
                    "history": history,
                    "direct_response": self._build_datetime_answer(prompt),
                    "messages": [],
                    "retrieval_content": [],
                    "search_result": search_result,
                    "final_prompt": prompt,
                }

        routed_prompt = (
            self._enhance_prompt_with_emotion(prompt, emotion_context)
            if decision.intent == INTENT_PSYCHOLOGY
            else prompt
        )
        retrieval_content = self._rag_retrieve(prompt) if decision.use_rag else []
        rag_text = self._format_retrieval_content(retrieval_content) if retrieval_content else ""
        realtime_context = ""
        if not (decision.intent == "realtime" and decision.use_web_search and search_result):
            realtime_context = self._build_realtime_context(prompt)

        system_prompt = self._build_system_prompt_for_intent(decision, emotion_context)
        final_prompt = self._build_user_prompt_for_intent(
            routed_prompt,
            decision,
            rag_text=rag_text,
            search_result=search_result,
            realtime_context=realtime_context,
            assessment_context=assessment_context or "",
        )

        messages = [{"role": "system", "content": system_prompt}]
        history_to_use = [] if decision.intent == "realtime" else history
        for user_msg, ai_msg in history_to_use:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": ai_msg})
        messages.append({"role": "user", "content": final_prompt})

        return {
            "decision": decision,
            "history": history_to_use,
            "direct_response": None,
            "messages": messages,
            "retrieval_content": retrieval_content,
            "search_result": search_result,
            "final_prompt": final_prompt,
        }
    
    def chat(self, 
             prompt: str,
             history: Optional[List[Tuple[str, str]]] = None,
             max_length: int = 2048,
             top_p: float = 0.8,
             temperature: float = 0.7,
             emotion_context: Optional[Dict] = None,
             assessment_context: Optional[str] = None,
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
        prepared = self._prepare_chat_request(
            prompt=prompt,
            history=history,
            emotion_context=emotion_context,
            assessment_context=assessment_context,
            enable_web_search=enable_web_search,
        )
        history = prepared["history"]
        decision = prepared["decision"]
        retrieval_content = prepared["retrieval_content"]
        response_meta = self._build_response_meta(
            prompt=prompt,
            decision=decision,
            search_result=prepared.get("search_result", ""),
            direct_response=prepared.get("direct_response"),
        )

        if prepared["direct_response"]:
            ai_response = self._postprocess_response(prompt, decision, prepared["direct_response"])
            updated_history = history + [(prompt, ai_response)]
            logger.info("[Route] direct response intent=%s", decision.intent)
            return ai_response, updated_history

        messages = prepared["messages"]
        
        # 构建硅基流动API请求数据
        # 增加max_tokens以获得更长的回复（默认2048太小，改为至少4096）
        # 如果max_length小于4096，使用4096；否则使用max_length，但不超过8192
        # 默认更长一点，但不强行 4096（对吞吐更友好）
        default_max = int(os.getenv("LLM_MAX_TOKENS_DEFAULT", "1200"))
        effective_max_tokens = max(256, min(int(max_length or default_max), 4096))
        
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
            decision.use_web_search,
        )
        
        # 使用传入的timeout或默认timeout
        request_timeout = timeout if timeout is not None else self.timeout
        
        # 发送请求（带重试）
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = self._post(
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
                    ai_response = message.get('content', '')
                else:
                    ai_response = ""
                
                if not ai_response:
                    logger.warning("API返回空响应")
                    ai_response = "抱歉，我暂时无法理解您的意思，请重新表述一下。"

                ai_response = self._postprocess_response(prompt, decision, ai_response)
                
                # 更新历史记录
                updated_history = history + [(prompt, ai_response)]
                
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
                    assessment_context: Optional[str] = None,
                    enable_web_search: bool = False,
                    timeout: Optional[int] = None):
        """流式心理咨询对话（带意图分流与按需 RAG/联网搜索）"""

        decision = self._decide_route(
            prompt,
            enable_web_search=enable_web_search,
            assessment_context=assessment_context,
        )
        history = history or []
        search_result = None

        if decision.direct_response:
            logger.info("[Route] direct stream response intent=%s", decision.intent)
            direct_response = self._postprocess_response(prompt, decision, decision.direct_response)
            response_meta = self._build_response_meta(
                prompt=prompt,
                decision=decision,
                search_result="",
                direct_response=decision.direct_response,
            )
            if response_meta:
                yield {"meta": response_meta}
            for piece in self._iter_local_response_chunks(direct_response):
                yield piece
            return

        if decision.use_web_search:
            yield {"status": "🔍 **正在请求 Tavily 联网搜索最新信息...**"}
            search_result = self._perform_web_search(prompt, max_results=3)
            if not search_result:
                yield {"status": "⚠️ **联网搜索未返回有效结果。**"}
                time.sleep(0.15)
                yield {"status_clear": True}
                fallback_response = (
                    self._build_datetime_answer(prompt)
                    if self._is_datetime_query(prompt)
                    else "联网搜索未返回有效结果，暂时无法准确回答这个最新信息问题。"
                )
                for piece in self._iter_local_response_chunks(fallback_response):
                    yield piece
                return

            yield {"status": "✅ **搜索完成，正在结合最新信息组织语言...**"}
            time.sleep(0.2)
            yield {"status_clear": True}

        prepared = self._prepare_chat_request(
            prompt=prompt,
            history=history,
            emotion_context=emotion_context,
            assessment_context=assessment_context,
            enable_web_search=enable_web_search,
            decision=decision,
            search_result_override=search_result,
        )
        history = prepared["history"]
        decision = prepared["decision"]
        retrieval_content = prepared["retrieval_content"]
        response_meta = self._build_response_meta(
            prompt=prompt,
            decision=decision,
            search_result=prepared.get("search_result", ""),
            direct_response=prepared.get("direct_response"),
        )

        if prepared["direct_response"]:
            logger.info("[Route] direct stream response intent=%s", decision.intent)
            direct_response = self._postprocess_response(prompt, decision, prepared["direct_response"])
            if response_meta:
                yield {"meta": response_meta}
            for piece in self._iter_local_response_chunks(direct_response):
                yield piece
            return

        messages = prepared["messages"]
        if response_meta:
            yield {"meta": response_meta}

        # 3. 发起请求
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
            decision.use_web_search,
        )

        request_timeout = timeout if timeout is not None else max(self.timeout, 120)
        
        try:
            response = self._post(
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
            full_response = ""

            # 4. 极简解析流数据（代码大幅缩减，因为不需要解析 tool_calls 了）
            for line in response.iter_lines():
                if not line: continue
                line_str = line.decode('utf-8')
                if not line_str.startswith('data: '): continue
                payload = line_str[6:].strip()
                if payload == '[DONE]':
                    break
                
                try:
                    data = json.loads(payload)
                    if not data.get('choices'): continue
                    
                    delta = data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    
                    if content:
                        # 过滤起手式的空白字符
                        if not has_yielded_real_content and not content.strip():
                            continue
                        has_yielded_real_content = True
                        generated_chars += len(content)
                        full_response += content
                        yield content
                        
                except Exception as e:
                    logger.warning(f"解析流式数据失败: {e}")
                    continue

            postprocessed_response = self._postprocess_response(prompt, decision, full_response)
            if postprocessed_response != full_response:
                yield {"replace_full_response": postprocessed_response}
            logger.info("[LLM] stream completed chars=%d", generated_chars)

        except requests.exceptions.Timeout as e:
            logger.error(f"流式请求超时: {e}", exc_info=True)
            yield f"\n\n抱歉，请求超时，AI服务响应较慢，请稍后重试"
        except Exception as e:
            logger.error(f"流式请求异常: {e}", exc_info=True)
            yield f"\n\n抱歉，服务异常: {str(e)}"
    
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
            r = self._post(
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

            try:
                data = self._request_tavily(
                    search_data,
                    self._session_for_url(self.tavily_api_url),
                )
            except requests.exceptions.ProxyError as e:
                logger.warning(
                    "Tavily搜索命中代理错误，改为直连重试: %s",
                    str(e),
                )
                data = self._request_tavily(
                    search_data,
                    self.direct_session,
                )
            except requests.exceptions.Timeout as e:
                logger.warning(
                    "Tavily搜索首轮超时，等待后改为直连重试: %s",
                    str(e),
                )
                time.sleep(1)
                data = self._request_tavily(
                    search_data,
                    self.direct_session,
                )
            
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
            connect_timeout, read_timeout = self._tavily_timeouts()
            logger.warning(
                "Tavily搜索超时: %s... (connect_timeout=%s, read_timeout=%s, 错误: %s)",
                query[:50],
                connect_timeout,
                read_timeout,
                str(e),
            )
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
            response = self._post(
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
        self.local_session.close()
        self.direct_session.close()
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
