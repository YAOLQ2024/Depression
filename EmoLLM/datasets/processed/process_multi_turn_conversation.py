import json

# 打开JSON文件并读取其内容
# file_name = 'multi_turn_dataset_1.json'
file_name = 'multi_turn_dataset_2.json'

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
        # 检查数据格式：如果是多轮对话格式（已有 conversation 字段）
        if 'conversation' in item and isinstance(item['conversation'], list):
            # 为每个对话轮次添加 system 字段
            conversation_list = []
            for idx, turn in enumerate(item['conversation']):
                turn_dict = {
                    "input": turn.get('input', ''),
                    "output": turn.get('output', '')
                }
                # 只给第一个 turn 添加 system
                if idx == 0:
                    turn_dict["system"] = system
                conversation_list.append(turn_dict)
            
            dict_ = {
                "conversation": conversation_list
            }
            datas.append(dict_)
            n += 1
            
            if n % 100 == 0:  # 每处理100条数据打印一次进度
                print(f"已处理 {n} 条数据...")
        else:
            print(f"警告：第 {i + 1} 条数据格式不正确，跳过")
            continue
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
