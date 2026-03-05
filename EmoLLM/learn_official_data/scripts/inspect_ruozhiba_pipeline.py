import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read_jsonl(path: Path, n: int = 2):
    print(f"\n==== 查看 JSONL: {path} ====")
    samples = []
    with path.open("r", encoding="utf-8") as f:
        content = f.read().strip()
        
        # 尝试作为 JSON 数组解析（整个文件是一个数组）
        try:
            data = json.loads(content)
            if isinstance(data, list):
                samples = data[:n]
            else:
                samples = [data]
        except json.JSONDecodeError:
            # 如果不是 JSON 数组，尝试按 JSONL 格式逐行解析
            f.seek(0)
            for i, line in enumerate(f):
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                if i >= n:
                    break
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"警告: 第 {i+1} 行解析失败: {e}")
                    continue
    
    print(f"示例条数: {len(samples)}")
    for i, s in enumerate(samples):
        print(f"\n--- sample {i} ---")
        for k, v in s.items():
            if isinstance(v, str):
                print(f"{k}:", v[:80], "...")
            else:
                print(f"{k} 类型:", type(v))

def main():
    backup = ROOT / "backup"
    read_jsonl(backup / "ruozhiba_raw.jsonl")
    read_jsonl(backup / "ruozhiba_format_emo.jsonl")

if __name__ == "__main__":
    main()
