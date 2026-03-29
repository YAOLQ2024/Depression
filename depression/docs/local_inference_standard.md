# Local Inference Standard (GPU, Linux)

This document defines a reproducible local startup standard for your current stack:

- LLM service: `127.0.0.1:8000`
- RAG service: `127.0.0.1:8001`
- Flask app: `127.0.0.1:5000`

It is **additive only**. Existing workflows are unchanged:

- You can still run `python3 start_app_gpu.py` directly.
- These scripts only apply when you choose to use them.

## Added Scripts

Under `depression/scripts/`:

- `start_llm_gpu.sh`: Start and health-check local LLM service.
- `start_rag.sh`: Start and health-check local RAG service.
- `start_stack.sh`: Start LLM -> RAG -> APP in order.
- `check_stack.sh`: Health-check all services.
- `stop_stack.sh`: Stop services started by these scripts (PID-based).

## One-Time Setup

```bash
cd /home/ZR/data2/Depression/depression
chmod +x scripts/*.sh
```

## Default Behavior

1. `start_llm_gpu.sh`

- Checks `http://127.0.0.1:8000/v1/models`
- If unhealthy, starts vLLM on GPU using:
  - model path default: `../EmoLLM/model/EmoLLM_Qwen2-7B-Instruct_lora`
  - served model default: `${SILICONFLOW_MODEL}` from `.env`
  - low-memory defaults:
    - `LLM_MAX_MODEL_LEN=2048`
    - `LLM_GPU_MEMORY_UTILIZATION=0.60`
    - `LLM_MAX_NUM_SEQS=2`

2. `start_rag.sh`

- Checks `http://127.0.0.1:8001/health`
- If unhealthy, starts:
  - `uvicorn rag_official_api:app --host 127.0.0.1 --port 8001`
  - working dir default: `../EmoLLM`

3. `start_stack.sh`

- Runs:
  - `start_llm_gpu.sh`
  - `start_rag.sh`
  - `python3 start_app_gpu.py`
- Waits for app health on `http://127.0.0.1:5000/api/chat/health`

## Daily Commands

```bash
# Start all in standard order
./scripts/start_stack.sh

# Check health
./scripts/check_stack.sh

# Stop all started by scripts
./scripts/stop_stack.sh
```

## Logs and PID Files

All files are under `depression/logs/stack/`:

- Logs: `llm.log`, `rag.log`, `app.log`
- PIDs: `llm.pid`, `rag.pid`, `app.pid`

## Optional Overrides (.env)

If your host setup differs, define these in `.env`:

```dotenv
# Optional override examples
LLM_START_CMD=python3 -m vllm.entrypoints.openai.api_server --host 127.0.0.1 --port 8000 --model /your/model/path --served-model-name emollm-qwen2-7b
RAG_START_CMD=python3 -m uvicorn rag_official_api:app --host 127.0.0.1 --port 8001
APP_START_CMD=python3 start_app_gpu.py

EMOLLM_ROOT=/home/ZR/data2/Depression/EmoLLM
LLM_MODEL_PATH=/home/ZR/data2/Depression/EmoLLM/model/EmoLLM_Qwen2-7B-Instruct_lora
LLM_DTYPE=auto
LLM_MAX_MODEL_LEN=2048
LLM_GPU_MEMORY_UTILIZATION=0.60
LLM_MAX_NUM_SEQS=2

LLM_HEALTH_URL=http://127.0.0.1:8000/v1/models
RAG_HEALTH_URL=http://127.0.0.1:8001/health
APP_HEALTH_URL=http://127.0.0.1:5000/api/chat/health
```

## Non-Impact Guarantee

This standardization does not modify your existing API, DB schema, or frontend behavior.
It only standardizes local service orchestration and health checks.
