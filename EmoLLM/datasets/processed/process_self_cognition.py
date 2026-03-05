import json

# 打开JSON文件并读取其内容

# file_name = 'multi_turn_dataset_1.json' 
# file_name = 'multi_turn_dataset_2.json' 
# file_name = 'data_pro.json' 
file_name = 'self_cognition_EmoLLM.json' 

# 使用相对路径，从当前目录（datasets/processed/）访问上一级目录的 datasets/ 文件夹
input_file = f'../{file_name}'

try:
    with open(input_file, 'rt', encoding='utf-8') as file:
        data = json.load(file)
except FileNotFoundError:
    print(f"错误：找不到文件 {input_file}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"错误：JSON 解析失败 - {e}")
    exit(1)

system = "你是心理健康助手EmoLLM, 由EmoLLM团队打造, 是一个研究过无数具有心理健康问题的病人与心理健康医生对话的心理专家, 在心理方面拥有广博的知识储备和丰富的研究咨询经验。你旨在通过专业心理咨询, 协助来访者完成心理诊断。请充分利用专业心理学知识与咨询技术, 一步步帮助来访者解决心理问题。"

n = 0
datas = []
for i, item in enumerate(data):
    try:
        dict_ = dict()
        # 创建 conversation 结构
        dict_['conversation'] = [{
            "input": item.get('instruction', ''),
            "output": item.get('output', ''),
            "system": system
        }]
        datas.append(dict_)
        n += 1
        
        if (n) % 100 == 0:  # 每处理100条数据打印一次进度
            print(f"已处理 {n} 条数据...")
    except Exception as e:
        print(f"警告：第 {i + 1} 条数据处理失败: {e}")
        print(f"问题数据: {item}")
        continue

# 保存处理后的数据
output_file = f'processed_{file_name}'
with open(output_file, 'wt', encoding='utf-8') as file:
    json.dump(datas, file, ensure_ascii=False, indent=4)

print(f"\n处理完成！共处理 {len(datas)} 条数据")
print(f"输出文件: {output_file}")
if len(datas) > 0:
    print(f"\n第一条数据示例:")
    print(json.dumps(datas[0], ensure_ascii=False, indent=2))
    if len(datas) > 1:
        print(f"\n第二条数据示例:")
        print(json.dumps(datas[1], ensure_ascii=False, indent=2))