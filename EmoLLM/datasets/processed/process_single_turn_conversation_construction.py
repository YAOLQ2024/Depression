import json

# 打开JSON文件并读取其内容
# file_name = 'single_turn_dataset_1.json'
file_name = 'single_turn_dataset_2.json'

# 使用相对路径，从当前目录（datasets/processed/）访问上一级目录的 datasets/ 文件夹
input_file = f'../{file_name}'

try:
    with open(input_file, 'rt', encoding='utf-8') as file:
        format1_data = json.load(file)
except FileNotFoundError:
    print(f"错误：找不到文件 {input_file}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"错误：JSON 解析失败 - {e}")
    exit(1)

system = "你是心理健康助手EmoLLM，由EmoLLM团队打造。你旨在通过专业心理咨询，协助来访者完成心理诊断。请充分利用专业心理学知识与咨询技术，一步步帮助来访者解决心理问题。"

# 转换为格式2的数据
format2_data = []
for i, item in enumerate(format1_data):
    try:
        conversation = {
            "system": system,
            "input": item.get("prompt", ""),
            "output": item.get("completion", "")
        }
        format2_data.append({"conversation": [conversation]})
        
        if (i + 1) % 100 == 0:  # 每处理100条数据打印一次进度
            print(f"已处理 {i + 1} 条数据...")
    except Exception as e:
        print(f"警告：第 {i + 1} 条数据处理失败: {e}")
        continue

# 将转换后的数据转换为JSON格式
output_file = f'processed_{file_name}'
with open(output_file, 'wt', encoding='utf-8') as file:
    json.dump(format2_data, file, ensure_ascii=False, indent=4)

print(f"\n处理完成！共处理 {len(format2_data)} 条数据")
print(f"输出文件: {output_file}")
if len(format2_data) > 0:
    print(f"\n第一条数据示例:")
    print(json.dumps(format2_data[0], ensure_ascii=False, indent=2))
