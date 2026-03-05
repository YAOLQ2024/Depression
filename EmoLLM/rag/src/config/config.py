import os

cur_dir = os.path.dirname(os.path.abspath(__file__))                # config
src_dir = os.path.dirname(cur_dir)                                  # src
base_dir = os.path.dirname(src_dir)                                 # base
model_repo = 'ajupyter/EmoLLM_aiwei'

# model
# 存放所有 model
model_dir = os.path.join(base_dir, 'model')

# embedding model 路径以及 model name
embedding_path = os.path.join(model_dir, 'embedding_model')         # embedding
embedding_model_name = 'BAAI/bge-small-zh-v1.5'

# rerank model 路径以及 model name
rerank_path = os.path.join(model_dir, 'rerank_model')  	        	  # embedding
rerank_model_name = 'BAAI/bge-reranker-large'

# llm 路径
llm_path = os.path.join(model_dir, 'pythia-14m')                    # llm

# data
data_dir = os.path.join(base_dir, 'data')                           # data
knowledge_json_path = os.path.join(data_dir, 'knowledge.json')      # json
knowledge_pkl_path = os.path.join(data_dir, 'knowledge.pkl')        # pkl
doc_dir = os.path.join(data_dir, 'txt')
qa_dir = os.path.join(data_dir, 'json')

# 预置知识库根目录
knowledge_base_roots = {
    'EmoLLMRAGTXT': os.path.join(base_dir, 'EmoLLMRAGTXT'),
    'my_depression_kb': os.path.join(base_dir, 'my_depression_kb'),
    'merged_depression_kb': os.path.join(base_dir, 'merged_depression_kb'),
    'myDD_knowledge_txt': os.path.join(base_dir, 'myDD_knowledge_txt'),
}

vector_db_presets = {name: os.path.join(path, 'vector_db') for name, path in knowledge_base_roots.items()}
default_vector_db_key = 'merged_depression_kb'

cloud_vector_db_dir = knowledge_base_roots[default_vector_db_key]

# log
log_dir = os.path.join(base_dir, 'log')                             # log
log_path = os.path.join(log_dir, 'log.log')                         # file

# txt embedding 切分参数     
chunk_size=1000
chunk_overlap=100

# vector DB
vector_db_dir = vector_db_presets[default_vector_db_key]

# RAG related
# select num: 代表rerank 之后选取多少个 documents 进入 LLM
# retrieval num： 代表从 vector db 中检索多少 documents。（retrieval num 应该大于等于 select num）
# rerank_flag: 是否启用重排功能，True 表示启用，False 表示不启用
select_num = 5
retrieval_num = 10
rerank_flag = True

# LLM key
# 智谱 LLM 的 API key。目前 demo 仅支持智谱 AI api 作为最后生成
glm_key = ''

# prompt
prompt_template = """
	你是一个拥有丰富心理学知识的温柔邻家温柔大姐姐艾薇，我有一些心理问题，请你用专业的知识和温柔、可爱、俏皮、的口吻帮我解决，回复中可以穿插一些可爱的Emoji表情符号或者文本符号。\n

	根据下面检索回来的信息，回答问题。
	{content}
	问题：{query}
"""