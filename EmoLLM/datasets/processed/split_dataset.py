import json
import random
import os

def split_data(input_file, train_file, test_file, split_ratio=0.7, seed=42):
    # 读取原始的jsonl文件
    # with open(input_file, 'r', encoding='utf-8') as f:
    #     data = [json.loads(line.strip()) for line in f]
        
    with open(input_file, 'rt', encoding='utf-8') as file:
        data = json.load(file)

    # 设置随机种子，确保每次划分结果一致
    random.seed(seed)
    # 打乱数据
    random.shuffle(data)

    # 计算训练集和测试集的划分点
    split_point = int(len(data) * split_ratio)

    # 划分数据
    train_data = data[:split_point]
    test_data = data[split_point:]

    # 确保输出目录存在
    train_dir = os.path.dirname(train_file)
    test_dir = os.path.dirname(test_file)
    if train_dir and not os.path.exists(train_dir):
        os.makedirs(train_dir, exist_ok=True)
    if test_dir and not os.path.exists(test_dir):
        os.makedirs(test_dir, exist_ok=True)
    
    # 保存训练集
    with open(train_file, 'w', encoding='utf-8') as file:
        json.dump(train_data, file, ensure_ascii=False, indent=4)
        
    # 保存测试集
    with open(test_file, 'w', encoding='utf-8') as file:
        json.dump(test_data, file, ensure_ascii=False, indent=4)
        
    print(f"原始数据量: {len(data)}")
    print(f"训练集: {len(train_data)} ({len(train_data)/len(data)*100:.1f}%)")
    print(f"测试集: {len(test_data)} ({len(test_data)/len(data)*100:.1f}%)")
    print(f"训练集保存至: {train_file}")
    print(f"测试集保存至: {test_file}")


def main():
    # 创建主输出目录
    output_dir = 'final_datasets'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"创建输出目录: {output_dir}")
    
    # ========== General 类数据 ==========
    general_dir = os.path.join(output_dir, 'general')
    if not os.path.exists(general_dir):
        os.makedirs(general_dir, exist_ok=True)
        print(f"创建 General 类输出目录: {general_dir}")
    
    input_file = 'dedup_general/dedup_combined_general.json'
    train_file = os.path.join(general_dir, 'train.json')
    test_file = os.path.join(general_dir, 'test.json')

    print("\n========== 处理 General 类数据 ==========")
    # 划分数据集，按照 7:3 的比例（70% 训练，30% 测试）
    split_data(input_file, train_file, test_file, split_ratio=0.7, seed=42)
    
    # ========== Role-play 类数据 ==========
    roleplay_dir = os.path.join(output_dir, 'roleplay')
    if not os.path.exists(roleplay_dir):
        os.makedirs(roleplay_dir, exist_ok=True)
        print(f"\n创建 Role-play 类输出目录: {roleplay_dir}")
    
    input_file = 'dedup_roleplay/dedup_combined_roleplay.json'
    train_file = os.path.join(roleplay_dir, 'train.json')
    test_file = os.path.join(roleplay_dir, 'test.json')

    print("\n========== 处理 Role-play 类数据 ==========")
    # 划分数据集，按照 7:3 的比例（70% 训练，30% 测试）
    split_data(input_file, train_file, test_file, split_ratio=0.7, seed=42)
    
    print("\n========== 处理完成 ==========")
    print(f"所有文件已保存到 {output_dir}/ 目录下")


if __name__== "__main__" :
    main()
    


