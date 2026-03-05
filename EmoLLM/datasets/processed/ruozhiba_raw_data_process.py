import json
import os

# 打开JSON文件并读取其内容

file_name = '../ruozhiba_raw.jsonl' 

n = 0
datas = []

with open(file_name, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:  # 跳过空行
            continue
            
        try:
            json_data = json.loads(line)
            
            dict_ = dict()
            # 创建 conversation 结构
            dict_['conversation'] = [{
                "input": json_data.get('instruction', ''),
                "output": json_data.get('output', ''),
                "system": "你是心理健康助手EmoLLM, 由EmoLLM团队打造, 是一个研究过无数具有心理健康问题的病人与心理健康医生对话的心理专家, 在心理方面拥有广博的知识储备和丰富的研究咨询经验。你旨在通过专业心理咨询, 协助来访者完成心理诊断。请充分利用专业心理学知识与咨询技术, 一步步帮助来访者解决心理问题。"
            }]
            
            datas.append(dict_)
            n += 1
            if n % 100 == 0:  # 每处理100条数据打印一次进度
                print(f"已处理 {n} 条数据...")
        except Exception as e:
            print(f"第 {n+1} 行处理失败: {e}")
            print(f"问题行内容: {line[:100]}...")  # 只打印前100个字符
            n += 1
            continue

# 保存处理后的数据到当前文件夹
output_file = 'ruozhiba_format_emo.json'
with open(output_file, 'wt', encoding='utf-8') as file:
    json.dump(datas, file, ensure_ascii=False, indent=4)

print(f"\n处理完成！共处理 {len(datas)} 条数据")
print(f"输出文件: {output_file}")
if len(datas) > 0:
    print(f"\n第一条数据示例:")
    print(json.dumps(datas[0], ensure_ascii=False, indent=2))