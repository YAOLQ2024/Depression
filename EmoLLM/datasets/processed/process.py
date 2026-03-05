import json

# 打开JSON文件并读取其内容

# file_name = 'multi_turn_dataset_1.json' 
# file_name = 'multi_turn_dataset_2.json' 
# file_name = 'data_pro.json' 
file_name = 'data.json' 

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

system = "你是心理健康助手EmoLLM，由EmoLLM团队打造。你旨在通过专业心理咨询，协助来访者完成心理诊断。请充分利用专业心理学知识与咨询技术，一步步帮助来访者解决心理问题。"

n = 0
success_count = 0
error_count = 0

for i, item in enumerate(data):
    try:
        # 检查数据格式
        if not isinstance(item, dict):
            print(f"警告：第 {i + 1} 条数据不是字典格式，跳过")
            error_count += 1
            continue
            
        if 'conversation' not in item:
            print(f"警告：第 {i + 1} 条数据缺少 conversation 字段，跳过")
            error_count += 1
            continue
            
        if not isinstance(item['conversation'], list) or len(item['conversation']) == 0:
            print(f"警告：第 {i + 1} 条数据的 conversation 不是有效列表，跳过")
            error_count += 1
            continue
        
        # 只给第一个 turn 添加 system（如果还没有的话）
        if 'system' not in item['conversation'][0]:
            item['conversation'][0]['system'] = system
            success_count += 1
        else:
            # 如果已有 system，可以选择更新或跳过
            # item['conversation'][0]['system'] = system  # 取消注释以强制更新
            pass
        
        n += 1
        if n % 100 == 0:  # 每处理100条数据打印一次进度
            print(f"已处理 {n} 条数据...")
            
    except KeyError as e:
        print(f"警告：第 {i + 1} 条数据缺少必要的字段: {e}")
        error_count += 1
        continue
    except Exception as e:
        print(f"警告：第 {i + 1} 条数据处理失败: {e}")
        print(f"问题数据: {item}")
        error_count += 1
        continue

# 保存处理后的数据
output_file = f'processed_{file_name}'
with open(output_file, 'wt', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)

print(f"\n处理完成！")
print(f"总数据量: {len(data)}")
print(f"成功处理: {success_count} 条")
print(f"错误/跳过: {error_count} 条")
print(f"输出文件: {output_file}")
if len(data) > 0:
    print(f"\n第一条数据示例:")
    print(json.dumps(data[0], ensure_ascii=False, indent=2))