import json
import os

# Role-play 类数据集列表
roleplay_files = [
    '../aiwei.json',
    '../mother_v1.json',
    '../mother_v2.json',
    # 如果有其他角色扮演数据，添加到这里
]

combined_data = []
for file_path in roleplay_files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                combined_data.extend(data)
            else:
                combined_data.append(data)
        print(f"已加载: {file_path}, 数据量: {len(data) if isinstance(data, list) else 1}")

with open('combined_roleplay.json', 'w', encoding='utf-8') as f:
    json.dump(combined_data, f, ensure_ascii=False, indent=4)

print(f"\nRole-play 类数据合并完成！总数据量: {len(combined_data)}")