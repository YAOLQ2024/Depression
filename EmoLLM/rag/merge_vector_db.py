"""
向量库合并脚本

功能：
1. 加载官方知识库向量库
2. 加载用户自定义知识库向量库
3. 合并两个向量库
4. 保存合并后的向量库

使用方法：
    python merge_vector_db.py
"""

import os
import sys
from loguru import logger

# 添加src目录到路径，以便导入模块
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)  # ~/EmoLLM
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from rag.src.data_processing import Data_process
from rag.src.config.config import embedding_model_name, embedding_path
from langchain_community.vectorstores import FAISS


def merge_vector_databases(
    official_db_path: str,
    my_db_path: str,
    merged_db_path: str,
    emb_model=None
):
    """
    合并两个FAISS向量库
    
    参数:
        official_db_path: 官方知识库路径
        my_db_path: 用户自定义知识库路径
        merged_db_path: 合并后保存路径
        emb_model: embedding模型（如果为None，会自动加载）
    
    返回:
        merged_db: 合并后的向量库对象
    """
    # 初始化数据处理对象
    if emb_model is None:
        logger.info("正在加载embedding模型...")
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return None
    
    # 检查路径是否存在
    if not os.path.exists(official_db_path):
        logger.error(f"官方知识库路径不存在: {official_db_path}")
        return None
    
    if not os.path.exists(my_db_path):
        logger.error(f"用户知识库路径不存在: {my_db_path}")
        return None
    
    # 加载官方知识库
    logger.info(f"正在加载官方知识库: {official_db_path}")
    try:
        official_db = FAISS.load_local(
            official_db_path,
            emb_model,
            allow_dangerous_deserialization=True
        )
        logger.info(f"官方知识库加载成功，包含 {official_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"加载官方知识库失败: {e}")
        return None
    
    # 加载用户知识库
    logger.info(f"正在加载用户知识库: {my_db_path}")
    try:
        my_db = FAISS.load_local(
            my_db_path,
            emb_model,
            allow_dangerous_deserialization=True
        )
        logger.info(f"用户知识库加载成功，包含 {my_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"加载用户知识库失败: {e}")
        return None
    
    # 合并向量库
    logger.info("正在合并向量库...")
    try:
        # 方法1: 使用merge_from（推荐，更高效）
        merged_db = official_db  # 以官方库为基础
        merged_db.merge_from(my_db)
        logger.info("向量库合并成功（使用merge_from方法）")
    except Exception as e:
        logger.warning(f"merge_from方法失败: {e}，尝试使用add_documents方法...")
        try:
            # 方法2: 使用add_documents（备用方法）
            # 获取用户知识库的所有文档
            # 注意：这种方法需要能够访问原始文档，如果只有向量库可能无法使用
            logger.warning("add_documents方法需要原始文档，当前仅支持merge_from方法")
            raise e
        except Exception as e2:
            logger.error(f"合并向量库失败: {e2}")
            return None
    
    # 创建保存目录
    os.makedirs(merged_db_path, exist_ok=True)
    
    # 保存合并后的向量库
    logger.info(f"正在保存合并后的向量库到: {merged_db_path}")
    try:
        merged_db.save_local(merged_db_path)
        logger.info(f"合并后的向量库保存成功！")
        logger.info(f"合并后的向量库包含 {merged_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"保存合并后的向量库失败: {e}")
        return None
    
    return merged_db


def main():
    """主函数"""
    # 配置路径
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 官方知识库路径（根据实际情况修改）
    official_db_path = os.path.join(current_dir, "EmoLLMRAGTXT", "vector_db")
    
    # 用户自定义知识库路径（根据实际情况修改）
    my_db_path = os.path.join(current_dir, "my_depression_kb", "vector_db")

    # 合并后的知识库保存路径
    merged_db_path = os.path.join(current_dir, "merged_depression_kb", "vector_db")
    
    # 如果路径不存在，使用相对路径
    if not os.path.exists(official_db_path):
        # 尝试其他可能的路径
        possible_paths = [
            os.path.join(current_dir, "..", "EmoLLMRAGTXT", "vector_db"),
            os.path.join(current_dir, "..", "rag", "EmoLLMRAGTXT", "vector_db"),
        ]
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                official_db_path = abs_path
                logger.info(f"找到官方知识库路径: {official_db_path}")
                break
    
    logger.info("=" * 60)
    logger.info("向量库合并工具")
    logger.info("=" * 60)
    logger.info(f"官方知识库路径: {official_db_path}")
    logger.info(f"用户知识库路径: {my_db_path}")
    logger.info(f"合并后保存路径: {merged_db_path}")
    logger.info("=" * 60)
    
    # 检查路径
    if not os.path.exists(official_db_path):
        logger.error(f"错误：官方知识库路径不存在！")
        logger.info("请确保官方知识库已下载到正确位置")
        logger.info("可以从以下位置下载：")
        logger.info("  - OpenXLab: git clone https://code.openxlab.org.cn/Anooyman/EmoLLMRAGTXT.git")
        logger.info("  - ModelScope: git clone https://www.modelscope.cn/datasets/Anooyman/EmoLLMRAGTXT.git")
        return
    
    if not os.path.exists(my_db_path):
        logger.error(f"错误：用户知识库路径不存在！")
        logger.info("请先构建你的知识库：")
        logger.info("  1. 将TXT文件放入 rag/src/data/txt/ 目录")
        logger.info("  2. 运行: cd rag/src && python data_processing.py")
        return
    
    # 执行合并
    merged_db = merge_vector_databases(
        official_db_path=official_db_path,
        my_db_path=my_db_path,
        merged_db_path=merged_db_path
    )
    
    if merged_db is not None:
        logger.info("=" * 60)
        logger.info("✅ 向量库合并完成！")
        logger.info("=" * 60)
        logger.info(f"合并后的向量库已保存到: {merged_db_path}")
        logger.info("")
        logger.info("下一步：")
        logger.info("  1. 编辑 rag/src/config/config.py")
        logger.info(f"  2. 将 vector_db_dir 修改为: {merged_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("向量库合并失败！")


if __name__ == "__main__":
    main()

