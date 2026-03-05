import json
import pickle
import os
import torch
from typing import List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        self._reranker = None  # 缓存 rerank 模型，避免重复加载
        self._embeddings = None  # 初始化缓存占位
        
        # 【服务预温】启动时直接加载到显存
        self.load_embedding_model(device='cuda')
        self.load_rerank_model()
        
    def load_embedding_model(self, model_name=embedding_model_name, device=None, normalize_embeddings=True):
        """
        加载嵌入模型（动态设备适配版）。
        
        修改要点：
        1. 移除 pickle 序列化：防止跨设备/环境时的 ordinal 报错。
        2. 动态设备检测：如果未手动指定 device，自动选择 cuda (优先) 或 cpu。
        3. 内存级缓存：模型加载后驻留显存/内存，实现后续请求秒回。
        """
        # 1. 检查内存缓存
        if hasattr(self, '_embeddings') and self._embeddings is not None:
            return self._embeddings

        # 2. 自动判定设备
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)

        # 本地路径优先逻辑
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info(f'Loading embedding model on {device}...')
        try:
            # 3. 直接从原始权重初始化（不再使用 pickle.load）
            # 由于你 export CUDA_VISIBLE_DEVICES=1，这里的 'cuda' 会精准映射到物理 GPU 1
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            
            logger.info('Embedding model loaded successfully.')
            
            # 4. 存入内存缓存，供后续 retrieve 调用
            self._embeddings = embeddings
            return embeddings

        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
    
    def load_rerank_model(self, model_name=rerank_model_name, device: str = "cuda:0"):
        """
        加载重排模型（内存缓存 + 单卡固定 + 禁止pickle序列化）。

        关键点：
        - 只做内存级缓存 self._reranker，避免重复加载；
        - 强制使用逻辑设备 cuda:0（在 export CUDA_VISIBLE_DEVICES=1 的情况下，物理GPU1=逻辑cuda:0）；
        - 若被 DataParallel 包装，拆成单卡 module；
        - 不对模型对象 pickle.dump / pickle.load（避免 CUDA 设备状态冲突）。
        """
        if self._reranker is not None:
            return self._reranker

        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)

        # 优先使用本地目录（避免联网下载），否则用模型名让它自动下载
        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                   for f in ["config.json", "model.safetensors", "pytorch_model.bin", "modules.json"])
        model_name_or_path = rerank_path if local_ok else model_name    

        logger.info(f"Loading rerank model from {model_name_or_path} on {device}...")

        try:
            import torch
            from FlagEmbedding import FlagReranker

            # 1. 初始化时去掉 device 参数，只保留核心参数
            reranker_model = FlagReranker(
                model_name_or_path,
                use_fp16=True
            )

            # 2. 手动将底层模型移动到指定设备 (cuda:0)
            # 这里的 device 依然是 "cuda:0"，对应你 export 的物理 GPU 1
            if hasattr(reranker_model, "model"):
                reranker_model.model.to(device)
                logger.info(f"Manually moved rerank model to {device}")

            # 3. 拆除 DataParallel（如果存在）
            if isinstance(reranker_model.model, torch.nn.DataParallel):
                reranker_model.model = reranker_model.model.module

            self._reranker = reranker_model
            logger.info("Rerank model loaded and cached in memory.")
            return reranker_model

        except Exception as e:
            logger.error(f"Failed to load rerank model: {e}")
            raise
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                # loader_cls=TextLoader,
                # loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model, vector_db_path: Optional[str] = None):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        target_dir = vector_db_path or vector_db_dir
        os.makedirs(target_dir, exist_ok=True)
        db.save_local(target_dir)
        return db
        
    def load_vector_db(
        self,
        knowledge_pkl_path=knowledge_pkl_path,
        doc_dir=doc_dir,
        qa_dir=qa_dir,
        vector_db_path: Optional[str] = None,
    ):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        target_dir = vector_db_path or vector_db_dir
        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            db = self.create_vector_db(emb_model, vector_db_path=target_dir)
        else:
            db = FAISS.load_local(
                target_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)
