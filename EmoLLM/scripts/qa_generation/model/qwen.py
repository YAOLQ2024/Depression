import time
import random
import dashscope
from http import HTTPStatus
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role

from config.config import DASHSCOPE_API_KEY
from util.logger import get_logger
from util.prompt_loader import load_system_prompt, load_wash_prompt


dashscope.api_key = DASHSCOPE_API_KEY

logger = get_logger()


def _call_qwen_with_retry(messages,
                          model: str = "qwen-max",
                          max_retries: int = 5,
                          base_delay: float = 1.0) -> str:
    """
    通用 Qwen 调用封装：
    - 自动处理 429 限流（Throttling.RateQuota），用指数退避重试
    - 对网络异常做重试
    - 对配额/余额问题只打 log，不死循环重试
    """
    delay = base_delay

    for attempt in range(1, max_retries + 1):
        try:
            response = Generation.call(
                model=model,
                messages=messages,
                result_format='message',
                stream=False,
                incremental_output=False
            )
        except Exception as e:
            # SDK / 网络错误
            logger.error(
                f"[Qwen] 调用异常，第 {attempt}/{max_retries} 次尝试失败：{e}"
            )
            if attempt == max_retries:
                return ""
            time.sleep(delay)
            delay *= 2
            continue

        if response.status_code == HTTPStatus.OK:
            # 正常返回
            try:
                return response.output.choices[0]['message']['content']
            except Exception as e:
                logger.error(f"[Qwen] 解析返回结果异常：{e}")
                return ""

        # 非 200 返回，统一做 log
        code = getattr(response, "code", "")
        message = getattr(response, "message", "")
        logger.warning(
            "[Qwen] 第 %s/%s 次调用失败，status=%s, code=%s, message=%s, request_id=%s",
            attempt,
            max_retries,
            response.status_code,
            code,
            message,
            getattr(response, "request_id", "N/A"),
        )

        # 1）限流：429 + Throttling.RateQuota → 适合重试
        if response.status_code == 429 and "Throttling" in str(code):
            if attempt == max_retries:
                logger.error("[Qwen] 多次重试仍然限流，停止重试。")
                return ""
            # 指数退避 + 随机抖动，避免一窝蜂再撞上去
            sleep_time = delay + random.random()
            logger.info(f"[Qwen] 遇到限流，等待 {sleep_time:.2f} 秒后重试……")
            time.sleep(sleep_time)
            delay *= 2
            continue

        # 2）配额/余额问题：这类一般充钱或等配额刷新才行，不要死命重试
        if any(key in str(code) for key in ["Quota", "Insufficient", "Balance", "Payment", "AccessDenied"]):
            logger.error("[Qwen] 看起来是配额/余额/权限相关问题，请检查阿里云控制台与账户余额。")
            return ""

        # 3）其他错误：可以小范围重试几次
        if attempt == max_retries:
            logger.error("[Qwen] 已达到最大重试次数，仍未成功。")
            return ""

        logger.info(f"[Qwen] 遇到错误，{delay:.2f} 秒后重试……")
        time.sleep(delay)
        delay *= 2

    return ""


def call_qwen_single_turn(query: str) -> str:
    messages = [
        {
            'role': Role.SYSTEM,
            'content': load_system_prompt()
        },
        {
            'role': Role.USER,
            'content': query
        }
    ]
    return _call_qwen_with_retry(messages)


def call_qwen_Psychology_QA_Pairs(query: str) -> str:
    messages = [
        {
            'role': Role.SYSTEM,
            'content': load_wash_prompt()
        },
        {
            'role': Role.USER,
            'content': query
        }
    ]
    return _call_qwen_with_retry(messages)
