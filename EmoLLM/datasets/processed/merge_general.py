import json
import os

# General 类数据集列表
general_files = [
    # 已处理好的
    # '../data_pro.json',
    '../data.json',  # 需要检查格式
    
    # 处理后的
    # 'processed_single_turn_dataset_1.json',
    # 'processed_single_turn_dataset_2.json',
    'processed_self_cognition_EmoLLM.json',
    'ruozhiba_format_emo.json', 
    # 'processed_multi_turn_dataset_1.json',
    # 'processed_multi_turn_dataset_2.json',
]

combined_data = []
for file_path in general_files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                combined_data.extend(data)
            else:
                combined_data.append(data)
        print(f"已加载: {file_path}, 数据量: {len(data) if isinstance(data, list) else 1}")

with open('combined_general.json', 'w', encoding='utf-8') as f:
    json.dump(combined_data, f, ensure_ascii=False, indent=4)

print(f"\nGeneral 类数据合并完成！总数据量: {len(combined_data)}")