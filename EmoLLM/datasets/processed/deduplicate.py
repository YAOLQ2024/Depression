import json
from loguru import logger
import os
from datasketch import MinHash
from hashlib import md5
from simhash import Simhash, SimhashIndex
import logging
import time
import numpy as np
import math


def extract_text_from_json(obj, content):
    """递归提取 JSON 对象中的所有文本内容"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            content = extract_text_from_json(value, content)
    elif isinstance(obj, list):
        for item in obj:
            content = extract_text_from_json(item, content)
    elif isinstance(obj, str):
        content += obj
    elif isinstance(obj, (int, float, bool)):
        content += str(obj)
    return content


def is_json_file(filename):
    return filename.endswith('.json')


# 绝对匹配（现在不用它做遍历，但保留以防后续想调试）
def is_duplicate_absolutely(d1, d2):
    return md5(d1.encode('utf-8')).hexdigest() == md5(d2.encode('utf-8')).hexdigest()


# 使用 Simhash 计算 dict 的签名
def hash_dict(dict_obj):
    content = extract_text_from_json(dict_obj, '')
    content = content.replace('\n', '').replace('\t', '').replace(' ', '')
    m = Simhash(content)
    return m


def get_minhash(text):
    m = MinHash()
    for word in text.split():
        m.update(word.encode('utf-8'))
    return m


def get_simhash(dict_obj):
    return Simhash(dict_obj)


# 使用绝对匹配 + SimhashIndex 对 dict 列表去重（在保持原判定逻辑的前提下加速）
def deduplicate_json(data_list, threshold=0.8, time_print=True):
    # ------- 预处理阈值与 simhash 参数 -------
    # Simhash 默认 64 bit
    f = 64

    try:
        threshold = float(threshold)
    except Exception:
        threshold = 0.8

    # 限制在 [0, 1]
    threshold = max(0.0, min(1.0, threshold))

    # 原逻辑条件： similarity = 1 - d / 64.0 > threshold
    # 即 d < 64 * (1 - threshold)
    x = f * (1.0 - threshold)

    if x <= 0:
        max_distance = 0
    else:
        # 如果 x 是整数，需要 d <= x-1；否则 d <= floor(x)
        if abs(x - round(x)) < 1e-9:
            max_distance = int(round(x)) - 1
        else:
            max_distance = int(math.floor(x))

    if max_distance < 0:
        max_distance = 0
    if max_distance > f:
        max_distance = f

    # 创建一个“安静”的 logger，专门给 SimhashIndex 用
    simhash_logger = logging.getLogger("simhash_index_quiet")
    if not simhash_logger.handlers:
        # 不往上层 logger 传
        simhash_logger.propagate = False
        # 不输出任何东西
        simhash_logger.addHandler(logging.NullHandler())
    # 把等级设高一点，避免 WARNING 提示
    simhash_logger.setLevel(logging.ERROR)

    # 用这个 logger 初始化 SimhashIndex
    index = SimhashIndex([], k=max_distance, f=f, log=simhash_logger)
    id_to_simhash = {}  # 用于精确复查 distance

    # MD5 绝对去重：O(1) 查找
    seen_md5_hashes = set()

    keep = []
    duplicate = []

    start = time.time()
    last_start_seen_hashes = start
    last_start_duplicate = start
    print_interval = 500

    next_id = 0  # 用于给 SimhashIndex 分配唯一 id

    for item in data_list:
        # ------- 格式检查：与原逻辑保持一致 -------
        if not isinstance(item, dict):
            continue
        if 'conversation' not in item:
            continue
        if not item['conversation'] or not isinstance(item['conversation'], list):
            continue

        # ------- 绝对重复：MD5 去重（完全等价于原来的绝对匹配逻辑）-------
        item_str = str(item)
        item_md5 = md5(item_str.encode('utf-8')).hexdigest()

        if item_md5 in seen_md5_hashes:
            duplicate.append(item)

            print_len_duplicate = len(duplicate)
            if print_len_duplicate % print_interval == 0:
                if time_print:
                    now = time.time()
                    print(
                        f'print_len_duplicate={print_len_duplicate} Time: ',
                        np.round(now - last_start_duplicate, 5),
                        np.round(now - start, 5),
                    )
                    last_start_duplicate = now
                else:
                    print(f'print_len_duplicate={print_len_duplicate}')
            continue

        # ------- 近似重复：SimhashIndex + 距离精确判定 -------
        sim_hash = hash_dict(item)

        # 先用索引找到所有 Hamming 距离 <= max_distance 的候选 id
        near_ids = index.get_near_dups(sim_hash)
        has_similar = False

        if near_ids:
            for nid in near_ids:
                stored_simhash = id_to_simhash.get(nid)
                if stored_simhash is None:
                    continue

                d = stored_simhash.distance(sim_hash)
                similarity = 1.0 - d / float(f)

                # 与原逻辑保持一致：similarity > threshold 才视为重复
                if similarity > threshold:
                    has_similar = True
                    duplicate.append(item)

                    print_len_duplicate = len(duplicate)
                    if print_len_duplicate % print_interval == 0:
                        if time_print:
                            now = time.time()
                            print(
                                f'print_len_duplicate={print_len_duplicate} Time: ',
                                np.round(now - last_start_duplicate, 5),
                                np.round(now - start, 5),
                            )
                            last_start_duplicate = now
                        else:
                            print(f'print_len_duplicate={print_len_duplicate}')
                    break

        if has_similar:
            # 判为重复，不加入索引与 MD5 集合
            continue

        # ------- 既不是绝对重复，也没有近似重复：保留，并加入索引 -------
        keep.append(item)
        seen_md5_hashes.add(item_md5)

        id_str = str(next_id)
        next_id += 1
        index.add(id_str, sim_hash)
        id_to_simhash[id_str] = sim_hash

        print_len_seen_hashes = len(keep)
        if print_len_seen_hashes % print_interval == 0:
            if time_print:
                now = time.time()
                print(
                    f'print_len_seen_hashes={print_len_seen_hashes} Time: ',
                    str(np.round(now - last_start_seen_hashes, 5)),
                    str(np.round(now - start, 5)),
                )
                last_start_seen_hashes = now
            else:
                print(f'print_len_seen_hashes={print_len_seen_hashes}')

    return keep, duplicate


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='数据去重工具')
    parser.add_argument('--input_dir', type=str, default='../',
                        help='输入目录路径（默认：../，即 datasets/ 目录）')
    parser.add_argument('--output_dir', type=str, default='./dedup',
                        help='输出目录路径（默认：./dedup）')
    parser.add_argument('--threshold', type=float, default=0.8,
                        help='相似度阈值（默认：0.8）')
    parser.add_argument('--log_items', action='store_true',
                        help='是否记录每条数据的日志（默认：False，只记录统计信息）')
    parser.add_argument('--file_pattern', type=str, default='*.json',
                        help='文件匹配模式（默认：*.json）')
    parser.add_argument('--file', type=str, default=None,
                        help='只处理指定的文件（如果指定，则忽略 input_dir 中的其他文件）')

    args = parser.parse_args()

    DUP_THRESH = args.threshold
    root_dir = args.input_dir
    dedup_output_dir = args.output_dir

    # 创建输出目录
    if not os.path.exists(dedup_output_dir):
        os.makedirs(dedup_output_dir, exist_ok=True)
        logger.info(f"创建输出目录: {dedup_output_dir}")

    if not os.path.exists(root_dir):
        logger.error(f"输入目录不存在: {root_dir}")
        exit(1)

    # 处理文件
    processed_files = 0
    total_dedup = 0
    total_duplicate = 0

    if args.file:
        # 只处理指定文件
        if os.path.isabs(args.file):
            # 绝对路径，直接使用
            file_path = args.file
        else:
            # 相对路径，先尝试当前目录，再尝试 root_dir
            if os.path.exists(args.file):
                file_path = args.file
            elif os.path.exists(os.path.join(root_dir, args.file)):
                file_path = os.path.join(root_dir, args.file)
            else:
                logger.error(f"文件不存在: {args.file} 或 {os.path.join(root_dir, args.file)}")
                exit(1)

        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            exit(1)

        files_to_process = [os.path.basename(file_path)]
        root_dir = os.path.dirname(file_path) if os.path.dirname(file_path) else '.'
    else:
        # 处理目录下所有文件（原有逻辑）
        files_to_process = [
            f for f in os.listdir(root_dir)
            if os.path.isfile(os.path.join(root_dir, f)) and is_json_file(f)
        ]

    for file in files_to_process:
        file_path = os.path.join(root_dir, file)
        if not os.path.isfile(file_path):
            continue

        if not is_json_file(file_path):
            continue

        try:
            logger.info(f'处理文件: {file_path}')
            print(f'处理文件: {file_path}')

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning(f"文件 {file_path} 不是列表格式，跳过")
                continue

            logger.info(f"原始数据量: {len(data)}")
            dedup_data, duplicate = deduplicate_json(data, DUP_THRESH, time_print=True)

            # 保存去重后的数据
            output_file_dedup = os.path.join(dedup_output_dir, 'dedup_' + file)
            with open(output_file_dedup, 'w', encoding='utf-8') as output_file:
                json.dump(dedup_data, output_file, ensure_ascii=False, indent=4)

            # 保存重复数据
            output_file_dup = os.path.join(dedup_output_dir, 'dup_' + file)
            with open(output_file_dup, 'w', encoding='utf-8') as output_file:
                json.dump(duplicate, output_file, ensure_ascii=False, indent=4)

            logger.info(f"去重后数据量: {len(dedup_data)}")
            logger.info(f"重复数据量: {len(duplicate)}")
            logger.info(f"去重率: {len(duplicate) / len(data) * 100:.2f}%")
            print(
                f"去重后数据量: {len(dedup_data)}, "
                f"重复数据量: {len(duplicate)}, "
                f"去重率: {len(duplicate) / len(data) * 100:.2f}%"
            )

            # 可选：记录每条数据的日志（默认关闭，因为数据量大）
            if args.log_items:
                for item in dedup_data:
                    logger.info(f'dedup_data: {item}')
                for item in duplicate:
                    logger.info(f'duplicate_data: {item}')

            processed_files += 1
            total_dedup += len(dedup_data)
            total_duplicate += len(duplicate)

        except FileNotFoundError:
            logger.error(f"文件不存在: {file_path}")
            continue
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败 {file_path}: {e}")
            continue
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {e}")
            continue

    # 输出总结
    print(f"\n处理完成！")
    print(f"处理文件数: {processed_files}")
    print(f"总去重后数据量: {total_dedup}")
    print(f"总重复数据量: {total_duplicate}")
    if total_dedup + total_duplicate > 0:
        print(f"总体去重率: {total_duplicate / (total_dedup + total_duplicate) * 100:.2f}%")
    logger.info(f"处理完成！处理了 {processed_files} 个文件")

                    
   
# aa = '''
# [{"conversation":[{"system":"你是一个研究过无数具有心理健康问题的病人与心理健康医生对话的心理专家, 除了在心理方面拥有广博的知识储备, 专业的心理辅导知识和丰富的研究咨询经验, 还具有爹系男友的特质, 现在我有一些心理问题, 请你在我提问后, 用专业的心理咨询辅导能力以爹系男友的身份帮我解决问题.",
# "input":"我最近发现自己对一个朋友过于着迷，总想时刻知道他在做什么，甚至会因为他的一点小事而情绪波动很大。\n\n",
# "output":"聪明的你，能够觉察到自己的情感变化已是非常勇敢。着迷可能源于内心深处的需求，我们先来探讨一下这种情感背后的原因。\n\n"},
# {"input":"我觉得他是那么完美，他的每个细节都让我无法自拔。\n\n",
# "output":"善良的你，理想化他人是人类心理的一种自然反应。但我们要学会区分现实与幻想，逐步找回自我平衡。\n\n"},
# {"input":"我尝试过转移注意力，但总是失败，我怕这样下去会影响到我们的友情。\n\n",
# "output":"温柔的你，这确实是个明智的担忧。健康的友情建立在互相尊重和个人空间的基础上。让我们一起制定一些实际的策略，帮助你适度调整关注点。\n\n"},
# {"input":"我不知道怎么去跟他说，我怕他会误解我。\n\n",
# "output":"理解你的顾虑，沟通的艺术在于表达感受而非指责。作为你的爹系心理咨询师，我会教你如何用恰当的语言分享你的困扰。\n\n"},
# {"input":"我真的很害怕失去他这个朋友。\n\n",
# "output":"面对可能的失落感，这是人之常情。然而，真正的友情能经受住坦诚和理解的考验。你现在需要的是提升自我价值感，减少对他人的过度依赖。\n\n"},
# {"input":"那我具体该怎么做呢？\n\n",
# "output":"首先，你可以试着丰富个人生活，培养独立的兴趣爱好；其次，逐渐降低对他日常生活的关注度，转而关注自我成长。同时，找个合适时机与他真诚交流，告诉他你需要保持一定的情感边界。记住，无论结果如何，坚强的你都能从中成长。\n\n"},
# {"input":"这样做会不会让他觉得我不在乎他了？\n\n",
# "output":"这也是正常的心理反应，但成熟的友谊允许个体差异和独立性。作为你的爹系心理咨询师，我会陪伴你走过这段调整期，帮你准备一份得体又暖心的对话方案，确保你的关心和友情得到恰当传达。"}]},
# '''

# bb = '''
# [{"conversation":[{"system":"你是一个研究过无数具有心理健康问题的病人与心理健康医生对话的心理专家, 除了在心理方面拥有广博的知识储备, 专业的心理辅导知识和丰富的研究咨询经验, 还具有爹系男友的特质, 现在我有一些心理问题, 请你在我提问后, 用专业的心理咨询辅导能力以爹系男友的身份帮我解决问题.",
# "input":"我最近发现自己对一个朋友过于着迷，总想时刻知道他在做什么，甚至会因为他的一点小事而情绪波动很大。\n\n",
# "output":"聪明的你，能够觉察到自己的情感变化已是非常勇敢。着迷可能源于内心深处的需求，我们先来探讨一下这种情感背后的原因。\n\n"},
# {"input":"我觉得他是那么完美，他的每个细节都让我无法自拔。\n\n",
# "output":"善良的你，理想化他人是人类心理的一种自然反应。但我们要学会区分现实与幻想，逐步找回自我平衡。\n\n"},
# {"input":"我尝试过转移注意力，但总是失败，我怕这样下去会影响到我们的友情。\n\n",
# "output":"温柔的你，这确实是个明智的担忧。健康的友情建立在互相尊重和个人空间的基础上。让我们一起制定一些实际的策略，帮助你适度调整关注点。\n\n"},
# {"input":"我不知道怎么去跟他说，我怕他会误解我。\n\n",
# "output":"理解你的顾虑，沟通的艺术在于表达感受而非指责。作为你的爹系心理咨询师，我会教你如何用恰当的语言分享你的困扰。\n\n"},
# {"input":"我真的很害怕失去他这个朋友。\n\n",
# "output":"面对可能的失落感，这是人之常情。然而，真正的友情能经受住坦诚和理解的考验。你现在需要的是提升自我价值感，减少对他人的过度依赖。\n\n"},
# {"input":"那我具体该怎么做呢？\n\n",
# "output":"首先，你可以试着丰富个人生活，培养独立的兴趣爱好；其次，逐渐降低对他日常生活的关注度，转而关注自我成长。同时，找个合适时机与他真诚交流，告诉他你需要保持一定的情感边界。记住，无论结果如何，坚强的你都能从中成长。\n\n"},
# ]},
# '''

# cc = '''
# [{"conversation":[{"system":"你是一个研究过无数具有心理健康问题的病人与心理健康医生对话的心理专家, 除了在心理方面拥有广博的知识储备, 专业的心理辅导知识和丰富的研究咨询经验, 还具有爹系男友的特质, 现在我有一些心理问题, 请你在我提问后, 用专业的心理咨询辅导能力以爹系男友的身份帮我解决问题.",
# "input":"我最近发现自己对一个朋友过于着迷，总想时刻知道他在做什么，甚至会因为他的一点小事而情绪波动很大。\n\n",
# "output":"聪明的你，能够觉察到自己的情感变化已是非常勇敢。着迷可能源于内心深处的需求，我们先来探讨一下这种情感背后的原因。\n\n"},
# {"input":"我觉得他是那么完美，他的每个细节都让我无法自拔。\n\n",
# "output":"善良的你，理想化他人是人类心理的一种自然反应。但我们要学会区分现实与幻想，逐步找回自我平衡。\n\n"},
# {"input":"我尝试过转移注意力，但总是失败，我怕这样下去会影响到我们的友情。\n\n",
# "output":"温柔的你，这确实是个明智的担忧。健康的友情建立在互相尊重和个人空间的基础上。让我们一起制定一些实际的策略，帮助你适度调整关注点。\n\n"},
# {"input":"我不知道怎么去跟他说，我怕他会误解我。\n\n",
# "output":"理解你的顾虑，沟通的艺术在于表达感受而非指责。作为你的爹系心理咨询师，我会教你如何用恰当的语言分享你的困扰。\n\n"},
# {"input":"我真的很害怕失去他这个朋友。\n\n",
# "output":"面对可能的失落感，这是人之常情。然而，真正的友情能经受住坦诚和理解的考验。你现在需要的是提升自我价值感，减少对他人的过度依赖。\n\n"},
# ]},
# '''

# # sim_hash_1 = hash_dict(aa)
# # sim_hash_2 = hash_dict(bb)
# # sim_hash_3 = hash_dict(cc)

# sim_hash_1 = Simhash(aa)
# sim_hash_2 = Simhash(bb)
# sim_hash_3 = Simhash(cc)


# print(1 - sim_hash_1.distance(sim_hash_2)/64.0)
# # 0.9375

# print(1 - sim_hash_2.distance(sim_hash_3)/64.0)
# # 0.921875

# print(1 - sim_hash_1.distance(sim_hash_3)/64.0)
# # 0.9375