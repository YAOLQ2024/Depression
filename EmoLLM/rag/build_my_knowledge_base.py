"""
快速构建自定义知识库脚本

功能：
1. 自动创建必要的目录结构
2. 从指定位置复制TXT文件到数据目录
3. 构建向量库
4. 提供使用说明

使用方法：
    python build_my_knowledge_base.py [TXT文件路径或目录]
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.src.data_processing import Data_process
from rag.src.config.config import doc_dir, qa_dir, vector_db_dir, data_dir


def create_directory_structure():
    """创建必要的目录结构"""
    logger.info("正在创建目录结构...")
    
    directories = [
        data_dir,
        doc_dir,
        qa_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"  ✓ {directory}")
    
    logger.info("目录结构创建完成！")


def copy_txt_files(source_path, target_dir):
    """
    复制TXT文件到目标目录
    
    参数:
        source_path: 源文件或目录路径
        target_dir: 目标目录
    """
    source_path = Path(source_path)
    target_dir = Path(target_dir)
    
    txt_files = []
    
    if source_path.is_file():
        # 如果是单个文件
        if source_path.suffix.lower() == '.txt':
            txt_files.append(source_path)
        else:
            logger.warning(f"文件 {source_path} 不是TXT格式，跳过")
    elif source_path.is_dir():
        # 如果是目录，递归查找所有TXT文件
        txt_files = list(source_path.rglob('*.txt'))
    else:
        logger.error(f"路径不存在: {source_path}")
        return False
    
    if not txt_files:
        logger.warning("未找到任何TXT文件")
        return False
    
    logger.info(f"找到 {len(txt_files)} 个TXT文件")
    
    # 复制文件
    copied_count = 0
    for txt_file in txt_files:
        try:
            target_file = target_dir / txt_file.name
            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base_name = txt_file.stem
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base_name}_{counter}{txt_file.suffix}"
                    counter += 1
            
            shutil.copy2(txt_file, target_file)
            logger.info(f"  ✓ 复制: {txt_file.name} -> {target_file.name}")
            copied_count += 1
        except Exception as e:
            logger.error(f"  ✗ 复制失败 {txt_file.name}: {e}")
    
    logger.info(f"成功复制 {copied_count}/{len(txt_files)} 个文件")
    return copied_count > 0


def build_vector_db(custom_db_path=None, include_json=False):
    """
    构建向量库
    
    参数:
        custom_db_path: 自定义向量库保存路径（如果为None，使用配置文件中的路径）
    """
    logger.info("=" * 60)
    logger.info("开始构建向量库...")
    logger.info("=" * 60)
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    json_files = list(Path(qa_dir).glob('*.json')) if include_json else []
    
    if not txt_files and not json_files:
        logger.error("错误：数据目录中没有找到任何文件！")
        logger.info(f"请将TXT文件放入: {doc_dir}")
        return False
    
    if include_json:
        logger.info(f"找到 {len(txt_files)} 个TXT文件和 {len(json_files)} 个JSON文件")
    else:
        logger.info(f"找到 {len(txt_files)} 个TXT文件（忽略 JSON 文件）")
    
    # 初始化数据处理对象
    try:
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return False
        
        # 构建向量库
        logger.info("正在处理文档并构建向量库...")
        split_doc = dp.split_document(doc_dir)
        split_qa = dp.split_conversation(qa_dir) if include_json else []
        
        if include_json:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块, {len(split_qa)} 个QA块")
        else:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块（未加载 JSON）")
        
        # 创建向量库
        from langchain_community.vectorstores import FAISS
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        
        # 保存向量库
        save_path = custom_db_path if custom_db_path else vector_db_dir
        os.makedirs(save_path, exist_ok=True)
        db.save_local(save_path)
        
        logger.info(f"向量库构建完成！")
        logger.info(f"保存路径: {save_path}")
        logger.info(f"包含 {db.index.ntotal} 个向量")
        
        return True
        
    except Exception as e:
        logger.error(f"构建向量库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自定义知识库构建工具")
    logger.info("=" * 60)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # 创建目录结构
    create_directory_structure()
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        logger.info(f"从以下位置复制TXT文件: {source_path}")
        
        if not copy_txt_files(source_path, doc_dir):
            logger.error("文件复制失败，退出")
            return
    else:
        logger.info("未指定源文件路径，跳过文件复制步骤")
        logger.info("提示：可以将TXT文件直接放入以下目录：")
        logger.info(f"  {doc_dir}")
    
    # 询问是否构建向量库
    logger.info("")
    logger.info("是否现在构建向量库？")
    logger.info("提示：如果数据目录中已有文件，可以直接构建")
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    if not txt_files:
        logger.warning("数据目录为空，无法构建向量库")
        logger.info("请先添加TXT文件到数据目录")
        return
    
    # 设置自定义向量库路径
    custom_db_path = os.path.join(current_dir, "myDD_knowledge_txt", "vector_db")
    
    # 构建向量库
    if build_vector_db(custom_db_path, include_json=False):
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 知识库构建完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步操作：")
        logger.info("  1. 使用 merge_vector_db.py 合并你的知识库与官方知识库")
        logger.info("  2. 或直接修改 rag/src/config/config.py 中的 vector_db_dir")
        logger.info(f"     将路径设置为: {custom_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("知识库构建失败！")


if __name__ == "__main__":
    main()

