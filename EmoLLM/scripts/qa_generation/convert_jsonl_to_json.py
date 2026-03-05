import os
import json
import glob
import argparse
from typing import Optional

def convert_jsonl_to_json(jsonl_dir, output_dir, pattern: Optional[str] = None):
    """
    将jsonl文件转换为JSON格式，供向量库使用
    """
    os.makedirs(output_dir, exist_ok=True)
    pattern = pattern or '*.jsonl'
    
    # 查找所有jsonl文件
    jsonl_files = glob.glob(os.path.join(jsonl_dir, pattern))
    
    for jsonl_file in jsonl_files:
        qa_list = []
        
        # 读取jsonl文件
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        qa_data = json.loads(line)
                        # 转换为向量库需要的格式
                        # 每个QA对作为一个conversation
                        qa_list.append({
                            "conversation": [
                                {
                                    "input": qa_data.get("question", ""),
                                    "output": qa_data.get("answer", "")
                                }
                            ]
                        })
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line in {jsonl_file}: {e}")
                        continue
        
        # 保存为JSON文件
        if qa_list:
            base_name = os.path.splitext(os.path.basename(jsonl_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(qa_list, f, ensure_ascii=False, indent=2)
            print(f"Converted {jsonl_file} -> {output_file} ({len(qa_list)} QA pairs)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="将 jsonl QA 文件转换为向量库所需的 json 格式。")
    parser.add_argument(
        '--pattern',
        default=None,
        help="可选，glob 模式，仅转换匹配的 jsonl 文件，例如 \"*SDS*.jsonl\"。"
    )
    parser.add_argument(
        '--input-dir',
        default='./data/cleaned',
        help="待转换的 jsonl 所在目录。默认 ./data/cleaned。"
    )
    parser.add_argument(
        '--output-dir',
        default='../../rag/data/json',
        help="输出 json 目录。默认 ../../rag/data/json。"
    )
    args = parser.parse_args()

    convert_jsonl_to_json(args.input_dir, args.output_dir, args.pattern)
    print("Conversion completed!")
