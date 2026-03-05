# /home/ZR/data2/Depression/EmoLLM/rag_official_api.py
import os
import time
import logging
from fastapi import FastAPI
from pydantic import BaseModel

from rag.src.pipeline import EmoLLMRAG
from rag.src.config.config import vector_db_presets, default_vector_db_key, rerank_flag

app = FastAPI()
rag_cache = {}
logger = logging.getLogger("rag_official_api")

class Req(BaseModel):
    query: str
    kb: str = default_vector_db_key
    # 可选：想覆盖默认检索数/重排数时再用
    retrieval_num: int | None = None
    select_num: int | None = None

@app.get("/health")
def health():
    return {"status": "ok", "loaded_kbs": list(rag_cache.keys())}

def get_rag(kb: str, retrieval_num=None, select_num=None):
    kb = kb or default_vector_db_key
    if kb not in vector_db_presets:
        kb = default_vector_db_key
    if kb not in rag_cache:
        # 和 web_internlm2.py 一样：用 vector_db_presets[kb] 作为 vector_db_path，并启用 rerank_flag
        rag_cache[kb] = EmoLLMRAG(
            model=None,
            vector_db_path=vector_db_presets[kb],
            rerank_flag=rerank_flag,
            retrieval_num=retrieval_num,
            select_num=select_num
        )
    return rag_cache[kb]

@app.post("/retrieve")
def retrieve(req: Req):
    start_time = time.time()
    rag = get_rag(req.kb, req.retrieval_num, req.select_num)
    content_list = rag.get_retrieval_content(req.query)  # 官方接口：返回若干段 text
    merged_text = "\n\n".join([f"[{i+1}] {c}" for i, c in enumerate(content_list)])
    elapsed = time.time() - start_time
    logger.info(
        "retrieve ok kb=%s query_len=%d hits=%d elapsed=%.3fs",
        req.kb,
        len(req.query or ""),
        len(content_list),
        elapsed,
    )
    return {"kb": req.kb, "content": content_list, "merged_text": merged_text}
