import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def inspect(path: Path, n: int = 2):
    print(f"\n==== 查看文件: {path} ====")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"样本总数: {len(data)}")
    for i, sample in enumerate(data[:n]):
        print(f"\n--- sample {i} ---")
        if "conversation" in sample:
            conv = sample["conversation"]
            print(f"  对话轮数: {len(conv)}")
            for turn in conv:
                # 兼容可能存在的字段
                if "system" in turn:
                    print("  [SYSTEM]:", turn["system"][:60], "...")
                if "input" in turn:
                    print("  [USER ]:", turn["input"][:60], "...")
                if "output" in turn:
                    print("  [ASSIS]:", turn["output"][:60], "...")
        else:
            # 兼容 single_turn 等其他格式
            print("  keys:", list(sample.keys()))
            for k, v in sample.items():
                if isinstance(v, str):
                    print(f"  {k}:", v[:60], "...")
                else:
                    print(f"  {k} 类型:", type(v))

def main():
    backup_dir = ROOT / "backup"
    inspect(backup_dir / "data_pro.json")
    inspect(backup_dir / "multi_turn_dataset_1.json")
    inspect(backup_dir / "single_turn_dataset_1.json")

if __name__ == "__main__":
    main()
