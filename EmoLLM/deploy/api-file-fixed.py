from fastapi import FastAPI, Request
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import uvicorn
import json
import datetime
import torch
import os


# 设置设备参数
DEVICE = "cuda"  # 使用CUDA
DEVICE_ID = "0"  # CUDA设备ID，如果未设置则为空
CUDA_DEVICE = f"{DEVICE}:{DEVICE_ID}" if DEVICE_ID else DEVICE  # 组合CUDA设备信息

# 加载模型
from transformers.utils import logging

logger = logging.get_logger(__name__)

# 模型路径 - 选择可用的模型
# 优先级: Qwen1.5 (小模型快速) > Qwen2 (大模型效果好) > InternLM
available_models = [
    "model/EmoLLM_Qwen1_5-0_5B-Chat_full_sft",  # 小模型，加载快
    "model/EmoLLM_Qwen2-7B-Instruct_lora",       # 大模型，效果好
    "model/EmoLLM_PT_InternLM1_8B-chat",         # InternLM
]

MODEL_PATH = None
for model_path in available_models:
    if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
        MODEL_PATH = model_path
        print(f"✓ 找到可用模型: {MODEL_PATH}")
        break

if MODEL_PATH is None:
    print("❌ 未找到可用的模型！")
    print("请检查以下目录是否存在config.json:")
    for model_path in available_models:
        print(f"  - {model_path}")
    exit(1)

# 清理GPU内存函数
def torch_gc():
    if torch.cuda.is_available():  # 检查是否可用CUDA
        with torch.cuda.device(CUDA_DEVICE):  # 指定CUDA设备
            torch.cuda.empty_cache()  # 清空CUDA缓存
            torch.cuda.ipc_collect()  # 收集CUDA内存碎片


# 创建FastAPI应用
app = FastAPI()


# 处理POST请求的端点
@app.post("/")
async def create_item(request: Request):
    global model, tokenizer  # 声明全局变量以便在函数内部使用模型和分词器
    json_post_raw = await request.json()  # 获取POST请求的JSON数据
    json_post = json.dumps(json_post_raw)  # 将JSON数据转换为字符串
    json_post_list = json.loads(json_post)  # 将字符串转换为Python对象
    prompt = json_post_list.get('prompt')  # 获取请求中的提示
    history = json_post_list.get('history')  # 获取请求中的历史记录
    max_length = json_post_list.get('max_length')  # 获取请求中的最大长度
    top_p = json_post_list.get('top_p')  # 获取请求中的top_p参数
    temperature = json_post_list.get('temperature')  # 获取请求中的温度参数
    
    # 调用模型进行对话生成
    response, history = model.chat(
        tokenizer,
        prompt,
        history=history,
        max_length=max_length if max_length else 2048,  # 如果未提供最大长度，默认使用2048
        top_p=top_p if top_p else 0.7,  # 如果未提供top_p参数，默认使用0.7
        temperature=temperature if temperature else 0.95  # 如果未提供温度参数，默认使用0.95
    )
    now = datetime.datetime.now()  # 获取当前时间
    time = now.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间为字符串
    
    # 构建响应JSON
    answer = {
        "response": response,
        "history": history,
        "status": 200,
        "time": time
    }
    
    # 构建日志信息
    log = "[" + time + "] " + '", prompt:"' + prompt + '", response:"' + repr(response) + '"'
    print(log)  # 打印日志
    torch_gc()  # 执行GPU内存清理
    return answer  # 返回响应

# 主函数入口
if __name__ == '__main__':
    print("=" * 60)
    print("正在加载EmoLLM模型...")
    print("=" * 60)
    
    # 加载预训练的分词器和模型
    print(f"从 {MODEL_PATH} 加载分词器...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    
    print(f"从 {MODEL_PATH} 加载模型...")
    model = (
        AutoModelForCausalLM.from_pretrained(MODEL_PATH, device_map="auto", trust_remote_code=True)
        .to(torch.bfloat16)
        .cuda()
    )
    
    model.generation_config = GenerationConfig(max_length=2048, top_p=0.7, temperature=0.95)
    model.eval()  # 设置模型为评估模式
    
    print("=" * 60)
    print("✓ 模型加载完成！")
    print("=" * 60)
    
    # 启动FastAPI应用
    # 用6006端口可以将autodl的端口映射到本地，从而在本地使用api
    print("启动API服务...")
    uvicorn.run(app, host='127.0.0.1', port=6006, workers=1)
