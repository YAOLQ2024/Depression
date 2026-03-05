from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from transformers.utils import logging

from typing import Optional

from rag.src.data_processing import Data_process
from rag.src.config.config import prompt_template, retrieval_num as default_retrieval_num, select_num as default_select_num
logger = logging.get_logger(__name__)


class EmoLLMRAG(object):
    """
        EmoLLM RAG Pipeline
            1. 根据 query 进行 embedding
            2. 从 vector DB 中检索数据
            3. rerank 检索后的结果
            4. 将 query 和检索回来的 content 传入 LLM 中
    """

    def __init__(self, model, retrieval_num=None, rerank_flag=False, select_num=None, vector_db_path: Optional[str] = None) -> None:
        """
            输入 Model 进行初始化 

            DataProcessing obj: 进行数据处理，包括数据 embedding/rerank
            vectorstores: 加载vector DB。如果没有应该重新创建
            system prompt: 获取预定义的 system prompt
            prompt template: 定义最后的输入到 LLM 中的 template
            
            参数:
                model: LLM模型
                retrieval_num: 从向量库检索的文档数量，如果为None则使用config.py中的默认值
                rerank_flag: 是否启用重排，默认为False
                select_num: 重排后选择的文档数量，如果为None则使用config.py中的默认值
                vector_db_path: 向量数据库路径，如果为None则使用config.py中的默认路径

        """
        self.model = model
        self.data_processing_obj = Data_process()
        self.vector_db_path = vector_db_path
        self.vectorstores = self._load_vector_db()
        self.prompt_template = prompt_template
        # 如果未指定，则使用config.py中的默认值
        self.retrieval_num = retrieval_num if retrieval_num is not None else default_retrieval_num
        self.rerank_flag = rerank_flag
        self.select_num = select_num if select_num is not None else default_select_num

    def _load_vector_db(self):
        """
            调用 embedding 模块给出接口 load vector DB
        """
        vectorstores = self.data_processing_obj.load_vector_db(vector_db_path=self.vector_db_path)

        return vectorstores 

    def get_retrieval_content(self, query) -> str:
        """
            Input: 用户提问, 是否需要rerank
            output: 检索后并且 rerank 的内容        
        """
    
        content = []
        documents = self.vectorstores.similarity_search(query, k=self.retrieval_num)

        for doc in documents:
            content.append(doc.page_content)

        # 如果需要rerank，调用接口对 documents 进行 rerank
        if self.rerank_flag:
            documents, _ = self.data_processing_obj.rerank(query, documents, self.select_num)

            content = []
            for doc in documents:
                content.append(doc.page_content)
        logger.info(f'Retrieval data: {content}')
        return content
    
    def generate_answer(self, query, content) -> str:
        """
            Input: 用户提问， 检索返回的内容
            Output: 模型生成结果
        """

        # 构建 template 
        # 第一版不涉及 history 信息，因此将 system prompt 直接纳入到 template 之中
        prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["query", "content"],
                )

        # 定义 chain
        # output格式为 string
        rag_chain = prompt | self.model | StrOutputParser()

        # Run
        generation = rag_chain.invoke(
                {
                    "query": query,
                    "content": content,
                }
            )
        return generation
    
    def main(self, query) -> str:
        """
            Input: 用户提问
            output: LLM 生成的结果

            定义整个 RAG 的 pipeline 流程，调度各个模块
            TODO:
                加入 RAGAS 评分系统
        """
        content = self.get_retrieval_content(query)
        response = self.generate_answer(query, content)

        return response
