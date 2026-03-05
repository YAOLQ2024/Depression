# Where is QA_REQUEST_INTERVAL set?
_Exported on 11/14/2025 at 16:14:28 GMT+8 from Cursor (1.6.35)_

---

**User**

scripts/qa_generation/main.py中的QA_REQUEST_INTERVAL在哪设置了？

---

**Cursor**

`QA_REQUEST_INTERVAL` 并没有在仓库其他位置写死配置，`scripts/qa_generation/main.py` 第 18 行直接通过 `os.getenv('QA_REQUEST_INTERVAL', '1.0')` 从环境变量读取（默认 1.0 秒）。因此需要在运行脚本前自行设置环境变量，例如：

- Linux/macOS: `export QA_REQUEST_INTERVAL=2.5`
- Windows PowerShell: `$env:QA_REQUEST_INTERVAL="2.5"`

脚本会使用这个值控制每次调用 LLM 之间的等待时间。

---

**User**

查看rag/src/config/config.py文件，我构建自己的向量库是保存在哪

---

**Cursor**

向量库默认保存在 `vector_db_dir`，也就是 `EmoLLMRAGTXT/vector_db` 目录（相对于仓库根目录）。定义参考：

```41:42:rag/src/config/config.py
vector_db_dir = os.path.join(cloud_vector_db_dir, 'vector_db')
```

其中 `cloud_vector_db_dir = os.path.join(base_dir, 'EmoLLMRAGTXT')`，所以完整路径为仓库根下的 `EmoLLMRAGTXT/vector_db`。

```python
vector_db_dir = os.path.join(cloud_vector_db_dir, 'vector_db')
```

---

**User**

现在我改了一行，现在是放哪

---

**Cursor**

现在 `cloud_vector_db_dir` 指向 `os.path.join(base_dir, 'my_depression_kb')`，因此向量库会存到 `my_depression_kb/vector_db`（仓库根目录下的 `my_depression_kb` 里的 `vector_db` 目录）。

---

**User**

要不要创建这个目录，还是说运行data_processing.py会自动创建

---

**Cursor**

`cloud_vector_db_dir` 改成 `my_depression_kb` 后，不用手动建目录。运行 `rag/src/data_processing.py` 时，`load_vector_db()` 会在需要时调用 `create_vector_db()`，最终通过 `FAISS.save_local(vector_db_dir)` 保存向量库。`save_local()` 内部会执行 `Path(folder_path).mkdir(parents=True, exist_ok=True)`，会自动把 `my_depression_kb/vector_db` 整个路径建好。若想提前确认也可以手动创建，但脚本会自动处理。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM/scripts/qa_generation$ python convert_jsonl_to_json.py
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 117 (char 116)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 126 (char 125)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 127 (char 126)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 131 (char 130)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 122 (char 121)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 131 (char 130)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 125 (char 124)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 116 (char 115)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 130 (char 129)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 135 (char 134)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 132 (char 131)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 121 (char 120)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 119 (char 118)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 127 (char 126)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 128 (char 127)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 128 (char 127)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 127 (char 126)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 131 (char 130)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 121 (char 120)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 120 (char 119)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 125 (char 124)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 123 (char 122)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 127 (char 126)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 117 (char 116)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 124 (char 123)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 131 (char 130)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 127 (char 126)
Error parsing line in ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl: Extra data: line 1 column 114 (char 113)
Converted ./data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.json (1 QA pairs)
Converted ./data/cleaned/2025-11-14_11-30-34-成人抑郁症治疗和管理.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-30-34-成人抑郁症治疗和管理.txt-qwen.json (68 QA pairs)
Converted ./data/cleaned/2025-11-14_11-21-45-精神障碍世界卫生组织20191128.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-21-45-精神障碍世界卫生组织20191128.txt-qwen.json (68 QA pairs)
Converted ./data/cleaned/2025-11-14_11-21-45-汉密顿抑郁量表HAMD.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-21-45-汉密顿抑郁量表HAMD.txt-qwen.json (460 QA pairs)
Converted ./data/cleaned/2025-11-14_11-38-44-抑郁症防治指南.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-38-44-抑郁症防治指南.txt-qwen.json (102 QA pairs)
Converted ./data/cleaned/2025-11-13_21-18-17-抑郁症世界卫生组织定义.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-13_21-18-17-抑郁症世界卫生组织定义.txt-qwen.json (159 QA pairs)
Converted ./data/cleaned/2025-11-14_11-35-44-精神障碍诊疗规范.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-35-44-精神障碍诊疗规范.txt-qwen.json (77 QA pairs)
Converted ./data/cleaned/2025-11-14_11-51-56-抑郁障碍中华人民共和国国家卫生健康委员会精神障碍诊疗规范.txt-qwen.jsonl -> ../../rag/src/data/json/2025-11-14_11-51-56-抑郁障碍中华人民共和国国家卫生健康委员会精神障碍诊疗规范.txt-qwen.json (432 QA pairs)
Conversion completed!
这个日志没问题吧，怎么一堆SDS

---

**Cursor**

这些报错是因为那份 `2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl` 里的每一行末尾多了一个逗号，`json.loads` 读到 `}` 后遇到 `,` 就会抛出 “Extra data” 异常，所以同一个文件被反复提示。转换脚本会在捕获异常后跳过出错行继续处理，所以能成功输出 JSON，但只留下了那份文件里首个（或唯一）格式正确的 QA，对应日志里 “Converted … (1 QA pairs)”。

要彻底消掉这些报错，有两个办法：

- 回到生成/清洗阶段，去掉 JSONL 每行尾部的逗号；
- 或者在 `convert_jsonl_to_json.py` 中，把 `json.loads` 前做一次简单清理（比如 `line.rstrip(',')`），再解析。

除了该 SDS 文件外，其余文件都是标准 JSON 行，所以没有同样的问题。

---

**User**

我将逗号删除了，有什么办法可以只对SDS文件做转换，我怕运行转换脚本后又把全部文件再转换一次

---

**Cursor**

可以单独处理这一份文件，不必重跑全部。两种做法：

- 临时执行一段 Python，把目标 JSONL 转成 JSON：

```bash
cd ~/EmoLLM/scripts/qa_generation
python - <<'PY'
import json, os

src = './data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl'
dst = '../../rag/src/data/json/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.json'

qa_list = []
with open(src, encoding='utf-8') as fin:
    for raw in fin:
        raw = raw.strip()
        if not raw:
            continue
        qa = json.loads(raw)
        qa_list.append({"conversation": [{"input": qa.get("question", ""),
                                          "output": qa.get("answer", "")}]})

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as fout:
    json.dump(qa_list, fout, ensure_ascii=False, indent=2)
print(f'Wrote {len(qa_list)} QA pairs to {dst}')
PY
```

- 如果想以后也能只转某些文件，可以改 `convert_jsonl_to_json.py` 加一个 `--pattern` 之类的参数，调用时 `python convert_jsonl_to_json.py --pattern "*SDS*.jsonl"` 即可。现在先用上面的临时脚本就行。

```shellscript
cd ~/EmoLLM/scripts/qa_generation
python - <<'PY'
import json, os

src = './data/cleaned/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.jsonl'
dst = '../../rag/src/data/json/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.json'

qa_list = []
with open(src, encoding='utf-8') as fin:
    for raw in fin:
        raw = raw.strip()
        if not raw:
            continue
        qa = json.loads(raw)
        qa_list.append({"conversation": [{"input": qa.get("question", ""),
                                          "output": qa.get("answer", "")}]})

os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, 'w', encoding='utf-8') as fout:
    json.dump(qa_list, fout, ensure_ascii=False, indent=2)
print(f'Wrote {len(qa_list)} QA pairs to {dst}')
PY
```

---

**User**

现在就给我修改转换文件把这个参数加上，当不给这个参数时自动将所有文件都转换，给了就转换给定的

---

**Cursor**

```python
import os
import json
import glob
import argparse
from typing import Optional

def convert_jsonl_to_json(jsonl_dir, output_dir, pattern: Optional[str] = None):
    """
    将jsonl文件转换为JSON格式，供向量库使用
    """
    os.makedirs(output_dir, exist_ok=True)
    pattern = pattern or '*.jsonl'
    
    # 查找所有jsonl文件
    jsonl_files = glob.glob(os.path.join(jsonl_dir, pattern))
    
    for jsonl_file in jsonl_files:
        qa_list = []
        
        # 读取jsonl文件
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        qa_data = json.loads(line)
                        # 转换为向量库需要的格式
                        # 每个QA对作为一个conversation
                        qa_list.append({
                            "conversation": [
                                {
                                    "input": qa_data.get("question", ""),
                                    "output": qa_data.get("answer", "")
                                }
                            ]
                        })
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line in {jsonl_file}: {e}")
                        continue
        
        # 保存为JSON文件
        if qa_list:
            base_name = os.path.splitext(os.path.basename(jsonl_file))[0]
            output_file = os.path.join(output_dir, f"{base_name}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(qa_list, f, ensure_ascii=False, indent=2)
            print(f"Converted {jsonl_file} -> {output_file} ({len(qa_list)} QA pairs)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="将 jsonl QA 文件转换为向量库所需的 json 格式。")
    parser.add_argument(
        '--pattern',
        default=None,
        help="可选，glob 模式，仅转换匹配的 jsonl 文件，例如 \"*SDS*.jsonl\"。"
    )
    parser.add_argument(
        '--input-dir',
        default='./data/cleaned',
        help="待转换的 jsonl 所在目录。默认 ./data/cleaned。"
    )
    parser.add_argument(
        '--output-dir',
        default='../../rag/src/data/json',
        help="输出 json 目录。默认 ../../rag/src/data/json。"
    )
    args = parser.parse_args()

    convert_jsonl_to_json(args.input_dir, args.output_dir, args.pattern)
    print("Conversion completed!")

```

已在 `scripts/qa_generation/convert_jsonl_to_json.py` 新增可选参数：

- 默认行为不变，`python convert_jsonl_to_json.py` 会转换目录下全部 `.jsonl`。
- 支持 `--pattern` 指定 glob 模式（例：`--pattern "*SDS*.jsonl"`），只处理匹配文件。
- 同时加入 `--input-dir`、`--output-dir` 可调输入输出目录。

可直接运行 `python convert_jsonl_to_json.py --pattern "*SDS*.jsonl"` 验证单文件转换。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM/rag/src$ python data_processing.py
Traceback (most recent call last):
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 7, in <module>
    from rag.src.config.config import (
ModuleNotFoundError: No module named 'rag'

---

**Cursor**

这是 Python 的模块搜索路径问题：你在 `rag/src` 目录下直接运行脚本时，Python 的默认 `sys.path` 里不包含项目根目录，所以找不到 `rag` 包。

有几种解决方式，任选其一：

- 回到项目根目录运行模块：  
  `cd ~/EmoLLM`  
  `python -m rag.src.data_processing`
- 或者保持当前目录，临时把根目录加入 `PYTHONPATH`：  
  `PYTHONPATH=.. python data_processing.py`（Linux/macOS 下）  
  `set PYTHONPATH=..` + `python data_processing.py`（Windows CMD）  
  `set-env PYTHONPATH ..` + `python data_processing.py`（PowerShell）
- 如果想在脚本内解决，可以在 `data_processing.py` 顶部加上 `import sys, os; sys.path.append(os.path.dirname(os.path.dirname(__file__)))` 等，但前两种更干净。

推荐第一种方式，最简单可靠。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag.src.data_processing
2025-11-14 12:48:41.635 | INFO     | __main__:<module>:241 - /home/xhq/EmoLLM/rag/data
2025-11-14 12:48:41.636 | INFO     | __main__:load_embedding_model:51 - Loading embedding model...
2025-11-14 12:48:41.850 | INFO     | __main__:load_embedding_model:56 - Embedding model loaded.
2025-11-14 12:48:41.850 | INFO     | __main__:create_vector_db:212 - Creating index...
2025-11-14 12:48:41.850 | INFO     | __main__:split_document:158 - Loading txt files from /home/xhq/EmoLLM/rag/data/txt
2025-11-14 12:48:41.850 | INFO     | __main__:split_document:170 - split_docs size 0
2025-11-14 12:48:41.850 | INFO     | __main__:split_conversation:179 - Loading json files from /home/xhq/EmoLLM/rag/data/json
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 246, in <module>
    vector_db = dp.load_vector_db()
                ^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 230, in load_vector_db
    db = self.create_vector_db(emb_model)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 219, in create_vector_db
    db = FAISS.from_documents(split_doc + split_qa, emb_model)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_core/vectorstores.py", line 528, in from_documents
    return cls.from_texts(texts, embedding, metadatas=metadatas, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/vectorstores/faiss.py", line 931, in from_texts
    return cls.__from(
           ^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/vectorstores/faiss.py", line 888, in __from
    index = faiss.IndexFlatL2(len(embeddings[0]))
                                  ~~~~~~~~~~^^^
IndexError: list index out of range

---

**Cursor**

报错是因为 `QA` 的 JSON 文件放到了 `rag/src/data/json` 下，而 `data_processing.py` 里 `qa_dir` 指向的是 `rag/data/json`。脚本没找到任何 JSON，于是向量列表为空，`FAISS` 初始化时就炸了。

处理方法：

- 把现有 `.json` 文件移动到 `rag/data/json`，或者
- 重新执行转换脚本时指定输出目录：

```bash
cd ~/EmoLLM/scripts/qa_generation
python convert_jsonl_to_json.py --pattern "*SDS*.jsonl" --output-dir ../../rag/data/json
# 或者不加 pattern 转全部
```

确认 `rag/data/json` 里有 JSON 后，再运行：

```bash
cd ~/EmoLLM
python -m rag.src.data_processing
```

就不会再出现空列表的错误了。

```shellscript
cd ~/EmoLLM/scripts/qa_generation
python convert_jsonl_to_json.py --pattern "*SDS*.jsonl" --output-dir ../../rag/data/json
# 或者不加 pattern 转全部
```

```shellscript
cd ~/EmoLLM
python -m rag.src.data_processing
```

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag.src.data_processing
2025-11-14 12:52:52.955 | INFO     | __main__:<module>:241 - /home/xhq/EmoLLM/rag/data
2025-11-14 12:52:52.955 | INFO     | __main__:load_embedding_model:51 - Loading embedding model...
2025-11-14 12:52:53.173 | INFO     | __main__:load_embedding_model:56 - Embedding model loaded.
2025-11-14 12:52:53.173 | INFO     | __main__:create_vector_db:212 - Creating index...
2025-11-14 12:52:53.173 | INFO     | __main__:split_document:158 - Loading txt files from /home/xhq/EmoLLM/rag/data/txt
  0%|                                                     | 0/15 [00:00<?, ?it/s]Error loading file /home/xhq/EmoLLM/rag/data/txt/适用于老年人群的抑郁筛查.txt
  7%|███                                          | 1/15 [00:03<00:45,  3.25s/it]Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 246, in <module>
    vector_db = dp.load_vector_db()
                ^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 230, in load_vector_db
    db = self.create_vector_db(emb_model)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 213, in create_vector_db
    split_doc = self.split_document(doc_dir)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 161, in split_document
    docs = loader.load()
           ^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 194, in load
    self.load_file(i, p, docs, pbar)
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 137, in load_file
    raise e
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 130, in load_file
    sub_docs = self.loader_cls(str(item), **self.loader_kwargs).load()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_core/document_loaders/base.py", line 29, in load
    return list(self.lazy_load())
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/unstructured.py", line 87, in lazy_load
    elements = self._get_elements()
               ^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/unstructured.py", line 167, in _get_elements
    from unstructured.partition.auto import partition
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/auto.py", line 38, in <module>
    from unstructured.partition.doc import partition_doc
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/doc.py", line 14, in <module>
    from unstructured.partition.docx import partition_docx
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/docx.py", line 33, in <module>
    from docx.text.hyperlink import Hyperlink
ModuleNotFoundError: No module named 'docx.text.hyperlink'
  7%|███                                          | 1/15 [00:03<00:48,  3.45s/it]

---

**Cursor**

这是 `langchain` 默认使用 `UnstructuredFileLoader` 时需要的依赖缺失导致的，它会去拉取 `unstructured` 模块的一堆解析器，其中包括 `python-docx`。虽然我们读的是 `.txt`，但新版本里默认 loader 就是 `unstructured`，所以依赖也得满足。

两种解决办法：

1. **装缺的依赖（最简单）**
   ```bash
   conda activate emo311
   pip install python-docx
   # 如果后续还要处理 PDF/Excel 等，也可以一次性装全套：
   # pip install "unstructured[docx]"
   ```
   装好再跑 `python -m rag.src.data_processing` 应该就不报了。

2. **改代码强制用 `TextLoader`**
   在 `split_document()` 里把 `DirectoryLoader` 改成：
   ```python
   loader = DirectoryLoader(
       data_path,
       glob="**/*.txt",
       show_progress=True,
       loader_cls=TextLoader,
       loader_kwargs={"encoding": "utf-8"}
   )
   ```
   这样就不依赖 `unstructured` 了。

建议先走方案 1，省得改代码。如果之后不希望依赖 `unstructured`，再按方案 2 调整。

```shellscript
   conda activate emo311
   pip install python-docx
   # 如果后续还要处理 PDF/Excel 等，也可以一次性装全套：
   # pip install "unstructured[docx]"
```

```python
   loader = DirectoryLoader(
       data_path,
       glob="**/*.txt",
       show_progress=True,
       loader_cls=TextLoader,
       loader_kwargs={"encoding": "utf-8"}
   )
```

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag.src.data_processing
2025-11-14 12:54:35.448 | INFO     | __main__:<module>:241 - /home/xhq/EmoLLM/rag/data
2025-11-14 12:54:35.448 | INFO     | __main__:load_embedding_model:51 - Loading embedding model...
2025-11-14 12:54:35.660 | INFO     | __main__:load_embedding_model:56 - Embedding model loaded.
2025-11-14 12:54:35.660 | INFO     | __main__:create_vector_db:212 - Creating index...
2025-11-14 12:54:35.660 | INFO     | __main__:split_document:158 - Loading txt files from /home/xhq/EmoLLM/rag/data/txt
  0%|                                                     | 0/15 [00:00<?, ?it/s]Error loading file /home/xhq/EmoLLM/rag/data/txt/适用于老年人群的抑郁筛查.txt
  7%|███                                          | 1/15 [00:02<00:31,  2.27s/it]Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 246, in <module>
    vector_db = dp.load_vector_db()
                ^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 230, in load_vector_db
    db = self.create_vector_db(emb_model)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 213, in create_vector_db
    split_doc = self.split_document(doc_dir)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 161, in split_document
    docs = loader.load()
           ^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 194, in load
    self.load_file(i, p, docs, pbar)
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 137, in load_file
    raise e
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/directory.py", line 130, in load_file
    sub_docs = self.loader_cls(str(item), **self.loader_kwargs).load()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_core/document_loaders/base.py", line 29, in load
    return list(self.lazy_load())
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/unstructured.py", line 87, in lazy_load
    elements = self._get_elements()
               ^^^^^^^^^^^^^^^^^^^^
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/langchain_community/document_loaders/unstructured.py", line 167, in _get_elements
    from unstructured.partition.auto import partition
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/auto.py", line 38, in <module>
    from unstructured.partition.doc import partition_doc
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/doc.py", line 14, in <module>
    from unstructured.partition.docx import partition_docx
  File "/home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages/unstructured/partition/docx.py", line 33, in <module>
    from docx.text.hyperlink import Hyperlink
ModuleNotFoundError: No module named 'docx.text.hyperlink'
  7%|███                                          | 1/15 [00:02<00:34,  2.46s/it]
安装后还是报错

---

**Cursor**

```python
import json
import pickle
import os

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir, qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker

class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    passages,scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for i in range(len(scores)):
        logger.info(str(scores[i]) + '\n')
        logger.info(passages[i])

```

我把 `rag/src/data_processing.py` 的 `DirectoryLoader` 改成强制使用 `TextLoader`（UTF-8 编码），这样就不依赖 `unstructured` 那套解析器，不会再触发 `docx` 相关缺失。你可以重新运行：

```bash
cd ~/EmoLLM
python -m rag.src.data_processing
```

若还有别的报错再告诉我。

```shellscript
cd ~/EmoLLM
python -m rag.src.data_processing
```

---

**User**

告诉我为什么安装了包还会报错

---

**Cursor**

之所以在装完依赖后仍然报 `ModuleNotFoundError: No module named 'docx.text.hyperlink'`，核心原因不在于包没装到，而是 `DirectoryLoader` 默认使用 `unstructured` 的 `UnstructuredFileLoader`，它会去导入 `docx.text.hyperlink` 这个模块。若环境里存在一个名为 `docx` 的旧包（PyPI 上有个完全不同的包叫 `docx`，早期经常被误装），Python 会优先加载它；这个包里没有 `text.hyperlink` 子模块，于是报错。即便随后安装了正确的 `python-docx`，由于模块名都是 `docx`，Python 仍然先命中旧包，所以看上去“装了还报错”。解决办法通常是先 `pip uninstall docx`，再安装 `python-docx`（或直接 `pip install "unstructured[docx]"`）；或者像我们刚才做的，改用 `TextLoader` 避开这条依赖链。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ pip install --upgrade python-docx
Looking in indexes: https://pypi.tuna.tsinghua.edu.cn/simple
Requirement already satisfied: python-docx in /home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages (0.8.11)
Collecting python-docx
  Downloading https://pypi.tuna.tsinghua.edu.cn/packages/d0/00/1e03a4989fa5795da308cd774f05b704ace555a70f9bf9d3be057b680bcf/python_docx-1.2.0-py3-none-any.whl (252 kB)
Requirement already satisfied: lxml>=3.1.0 in /home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages (from python-docx) (5.1.0)
Requirement already satisfied: typing_extensions>=4.9.0 in /home/xhq/miniconda3/envs/emo311/lib/python3.11/site-packages (from python-docx) (4.9.0)
Installing collected packages: python-docx
  Attempting uninstall: python-docx
    Found existing installation: python-docx 0.8.11
    Uninstalling python-docx-0.8.11:
      Successfully uninstalled python-docx-0.8.11
Successfully installed python-docx-1.2.0
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag.src.data_processing
2025-11-14 13:00:03.649 | INFO     | __main__:<module>:247 - /home/xhq/EmoLLM/rag/data
2025-11-14 13:00:03.649 | INFO     | __main__:load_embedding_model:51 - Loading embedding model...
2025-11-14 13:00:03.861 | INFO     | __main__:load_embedding_model:56 - Embedding model loaded.
2025-11-14 13:00:03.861 | INFO     | __main__:create_vector_db:218 - Creating index...
2025-11-14 13:00:03.861 | INFO     | __main__:split_document:158 - Loading txt files from /home/xhq/EmoLLM/rag/data/txt
  0%|                                                     | 0/15 [00:00<?, ?it/s][nltk_data] Downloading package punkt to /home/xhq/nltk_data...
[nltk_data]   Unzipping tokenizers/punkt.zip.
[nltk_data] Downloading package averaged_perceptron_tagger to
[nltk_data]     /home/xhq/nltk_data...
[nltk_data]   Unzipping taggers/averaged_perceptron_tagger.zip.
100%|████████████████████████████████████████████| 15/15 [00:11<00:00,  1.31it/s]
2025-11-14 13:00:15.292 | INFO     | __main__:split_document:176 - split_docs size 729
2025-11-14 13:00:15.292 | INFO     | __main__:split_conversation:185 - Loading json files from /home/xhq/EmoLLM/rag/data/json
2025-11-14 13:00:15.293 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-13_21-18-17-抑郁症世界卫生组织定义.txt-qwen.json
2025-11-14 13:00:15.298 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-21-45-精神障碍世界卫生组织20191128.txt-qwen.json
2025-11-14 13:00:15.301 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-30-34-成人抑郁症治疗和管理.txt-qwen.json
2025-11-14 13:00:15.303 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-35-44-精神障碍诊疗规范.txt-qwen.json
2025-11-14 13:00:15.306 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-38-44-抑郁症防治指南.txt-qwen.json
2025-11-14 13:00:15.310 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-21-45-汉密顿抑郁量表HAMD.txt-qwen.json
2025-11-14 13:00:15.324 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-51-56-抑郁障碍中华人民共和国国 家卫生健康委员会精神障碍诊疗规范.txt-qwen.json
2025-11-14 13:00:15.338 | INFO     | __main__:split_conversation:195 - splitting file /home/xhq/EmoLLM/rag/data/json/2025-11-14_11-38-44-抑郁症自评量表SDS.txt-qwen.json
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/xhq/EmoLLM/rag/src/data_processing.py", line 260, in <module>
    docs, retriever = dp.retrieve(query, vector_db, k=10)
                      ^^^^^^^^^^^
AttributeError: 'Data_process' object has no attribute 'retrieve'

---

**Cursor**

日志已经说明前面步骤都跑通了，最后挂掉的原因是 `Data_process` 类里根本没有实现 `retrieve` 方法，但 `if __name__ == "__main__":` 这段示例代码里仍然调用了 `dp.retrieve(...)`，所以报 `AttributeError`。这是示例片段里遗留的调试代码，不影响向量库已经创建完成。

处理方式：

- 如果只是想构建/更新向量库，可以直接删掉或注释掉 `dp.retrieve(...)` 及下面 rerank 的几行（命令结束在 `vector_db = dp.load_vector_db()` 就行）；或者运行时用 `python -m rag.src.data_processing` 让脚本执行到构建向量库后手动 `Ctrl+C` 终止。
- 若确实需要后续的检索测试，要么自己补一个 `retrieve` 方法，要么参考 LangChain `FAISS` 的用法写几行调用，例如 `vector_db.as_retriever(search_kwargs={"k":10}).get_relevant_documents(query)` 等。

总之，这个错误不影响向量库生成，只是示例代码里调用了不存在的方法。

---

**User**

你给我补充完整这个方法，告诉我这个方法有什么用，怎么用，以及我要不要出现运行一遍python -m rag.src.data_processing

---

**Cursor**

```python
import json
import pickle
import os
from typing import Iterable, List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker
from langchain.docstore.document import Document as LCDocument


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[LCDocument], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[LCDocument],
        top_k: Optional[int] = None,
    ) -> Tuple[List[LCDocument], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    passages,scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for i in range(len(scores)):
        logger.info(str(scores[i]) + '\n')
        logger.info(passages[i])

```

```python
import json
import pickle
import os
from typing import Iterable, List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker
from langchain.docstore.document import Document as LCDocument


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[LCDocument], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[LCDocument],
        top_k: Optional[int] = None,
    ) -> Tuple[List[LCDocument], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)

```

```python
import json
import pickle
import os
from typing import List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[LCDocument], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)

```

```python
import json
import pickle
import os
from typing import List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)

```

## 更新说明
- 在 `rag/src/data_processing.py` 中实现了缺失的 `retrieve` / `rerank` 方法，并强制 `DirectoryLoader` 使用 `TextLoader`，避免再次触发 `unstructured` 依赖问题。  
```249:345:rag/src/data_processing.py
    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        ...
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        ...
        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        ...
```

## 方法用途与用法
- `retrieve(query, vector_db, k=10, ...)`：基于 FAISS 向量库检索与查询最相关的文档，返回 `[Document]` 以及可复用的检索器对象，后续可继续 `retriever.get_relevant_documents(...)`。
- `rerank(query, docs, top_k=None)`：利用 BAAI `bge-reranker-large` 对初步检索结果重新排序，输出按得分降序的文档及其分数，可进一步用于提示工程或展示。
- 在脚本 `__main__` 示例中已直接演示，取回文档后打印其内容，再输出重排后的得分与文本。

## 是否需要重跑
- 向量库已经保存在 `my_depression_kb/vector_db` 后，`load_vector_db()` 会优先加载本地缓存；若你想确认新增方法与重排流程正常工作，建议重新执行：
  ```bash
  cd ~/EmoLLM
  python -m rag.src.data_processing
  ```
  这一步会复用现有向量库，只会在缺失时才重新构建。运行成功后会看到“Retrieve results / After reranking”日志，确认流程无误。

## 下一步建议
- 如果未来需要在其它地方调用检索/重排，可直接复用 `Data_process` 的两个新方法。
- 若仍看到依赖未解析的 linter 提示，只是本地环境没有安装对应包的静态检查告警，运行时已通过即可忽略或在 IDE 配置里屏蔽。

```python
    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        ...
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        ...
        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        ...
```

```shellscript
  cd ~/EmoLLM
  python -m rag.src.data_processing
```

---

**User**

我已经通过升级python-docx解决了刚才那个报错，所以你别改成TextLoader了，尽量保持原作者的代码避免触发其他错误，

---

**Cursor**

```python
import json
import pickle
import os
from typing import List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        db.save_local(vector_db_dir)
        return db
        
    def load_vector_db(self, knowledge_pkl_path=knowledge_pkl_path, doc_dir=doc_dir, qa_dir=qa_dir):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
            db = self.create_vector_db(emb_model)
        else:
            db = FAISS.load_local(
                vector_db_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)

```

已把 `split_document()` 恢复为原作者的 `DirectoryLoader` 默认行为，避免因为强制使用 `TextLoader` 产生潜在副作用。其余检索与重排方法保持新增实现不变。当前 linter 警告都是第三方库的静态检查告警（本地运行已成功，可忽略或在 IDE 配置里关闭）。无需再次运行 `python -m rag.src.data_processing`，除非你想验证更新后的检索/重排日志；向量库不会因这次修改被重建。

---

**User**

python merge_vector_db.py使用这个代码是如何合并两个知识库的，讲一下原理，会不会有潜在问题，以及合并后的目录会自动创建吗

---

**Cursor**

这段脚本的流程如下：

- `merge_vector_databases()` 会先初始化（或复用传入的）嵌入模型，然后使用 `FAISS.load_local()` 分别读取官方知识库 (`official_db_path`) 和用户知识库 (`my_db_path`) 的索引。两者必须由同一个 embedding 模型生成，否则向量空间不一致，会导致合并后的检索质量不可靠。
- 加载成功后，以官方库为基准执行 `official_db.merge_from(my_db)`。这是 LangChain `FAISS` 提供的合并接口，会把用户库的向量和元数据追加到官方库的索引与 docstore 中。`merge_from` 要求两个库使用相同的维度和内部结构，且 docstore key 不能冲突（LangChain 默认用 UUID，可避免重复）。
- 合并后调用 `merged_db.save_local(merged_db_path)` 持久化到新目录；保存前用 `os.makedirs(merged_db_path, exist_ok=True)` 确保目录存在，未手动创建也没问题。输出目录应为空或可被覆盖，否则原有数据会被替换。

潜在注意点：

- 如果两个向量库的 embedding 模型不同、维度不一致或保存格式不兼容，`load_local` 或 `merge_from` 会报错；即便勉强成功，检索结果也会混乱。
- `merge_from` 不会自动去重；若两个库有同一原文，它们会以两条记录共存。可在合并前对文本做去重、或之后自定义过滤。
- 脚本引入模块的方式是往 `sys.path` 插入 `rag/src`，在不同入口运行时小心路径问题；最好在项目根目录执行 `python merge_vector_db.py`。
- 运行前需准备好三个目录：官方库 `EmoLLMRAGTXT/vector_db`、个人库 `my_knowledge_base/vector_db`、以及合并后目标 `merged_knowledge_base/vector_db`。脚本会自动创建最后一个目录，但不会为前两者兜底。
- 合并只是把两份向量集合拷贝到一个库里，并没有额外的版本管理或回滚机制，最好先备份源库，以防保存时覆盖了已有内容。

只要确保双方向量库是用同一个 `Data_process`/embedding 生成的，就可以比较稳地用这套脚本合并。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ cd rag
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM/rag$ python merge_vector_db.py
Traceback (most recent call last):
  File "/home/xhq/EmoLLM/rag/merge_vector_db.py", line 21, in <module>
    from rag.src.data_processing import Data_process
ModuleNotFoundError: No module named 'rag'
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM/rag$ cd ~/EmoLLM
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python merge_vector_db.py
python: can't open file '/home/xhq/EmoLLM/merge_vector_db.py': [Errno 2] No such file or directory
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag/merge_vector_db.py
/home/xhq/miniconda3/envs/emo311/bin/python: Error while finding module specification for 'rag/merge_vector_db.py' (ModuleNotFoundError: No module named 'rag/merge_vector_db'). Try using 'rag/merge_vector_db' instead of 'rag/merge_vector_db.py' as the module name.
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ python -m rag.merge_vector_db.py
/home/xhq/miniconda3/envs/emo311/bin/python: Error while finding module specification for 'rag.merge_vector_db.py' (ModuleNotFoundError: __path__ attribute not found on 'rag.merge_vector_db' while trying to find 'rag.merge_vector_db.py'). Try using 'rag.merge_vector_db' instead of 'rag.merge_vector_db.py' as the module name.

---

**Cursor**

```python
"""
向量库合并脚本

功能：
1. 加载官方知识库向量库
2. 加载用户自定义知识库向量库
3. 合并两个向量库
4. 保存合并后的向量库

使用方法：
    python merge_vector_db.py
"""

import os
import sys
from loguru import logger

# 添加src目录到路径，以便导入模块
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)  # ~/EmoLLM
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from rag.src.data_processing import Data_process
from rag.src.config.config import embedding_model_name, embedding_path
from langchain_community.vectorstores import FAISS


def merge_vector_databases(
    official_db_path: str,
    my_db_path: str,
    merged_db_path: str,
    emb_model=None
):
    """
    合并两个FAISS向量库
    
    参数:
        official_db_path: 官方知识库路径
        my_db_path: 用户自定义知识库路径
        merged_db_path: 合并后保存路径
        emb_model: embedding模型（如果为None，会自动加载）
    
    返回:
        merged_db: 合并后的向量库对象
    """
    # 初始化数据处理对象
    if emb_model is None:
        logger.info("正在加载embedding模型...")
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return None
    
    # 检查路径是否存在
    if not os.path.exists(official_db_path):
        logger.error(f"官方知识库路径不存在: {official_db_path}")
        return None
    
    if not os.path.exists(my_db_path):
        logger.error(f"用户知识库路径不存在: {my_db_path}")
        return None
    
    # 加载官方知识库
    logger.info(f"正在加载官方知识库: {official_db_path}")
    try:
        official_db = FAISS.load_local(
            official_db_path,
            emb_model,
            allow_dangerous_deserialization=True
        )
        logger.info(f"官方知识库加载成功，包含 {official_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"加载官方知识库失败: {e}")
        return None
    
    # 加载用户知识库
    logger.info(f"正在加载用户知识库: {my_db_path}")
    try:
        my_db = FAISS.load_local(
            my_db_path,
            emb_model,
            allow_dangerous_deserialization=True
        )
        logger.info(f"用户知识库加载成功，包含 {my_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"加载用户知识库失败: {e}")
        return None
    
    # 合并向量库
    logger.info("正在合并向量库...")
    try:
        # 方法1: 使用merge_from（推荐，更高效）
        merged_db = official_db  # 以官方库为基础
        merged_db.merge_from(my_db)
        logger.info("向量库合并成功（使用merge_from方法）")
    except Exception as e:
        logger.warning(f"merge_from方法失败: {e}，尝试使用add_documents方法...")
        try:
            # 方法2: 使用add_documents（备用方法）
            # 获取用户知识库的所有文档
            # 注意：这种方法需要能够访问原始文档，如果只有向量库可能无法使用
            logger.warning("add_documents方法需要原始文档，当前仅支持merge_from方法")
            raise e
        except Exception as e2:
            logger.error(f"合并向量库失败: {e2}")
            return None
    
    # 创建保存目录
    os.makedirs(merged_db_path, exist_ok=True)
    
    # 保存合并后的向量库
    logger.info(f"正在保存合并后的向量库到: {merged_db_path}")
    try:
        merged_db.save_local(merged_db_path)
        logger.info(f"合并后的向量库保存成功！")
        logger.info(f"合并后的向量库包含 {merged_db.index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"保存合并后的向量库失败: {e}")
        return None
    
    return merged_db


def main():
    """主函数"""
    # 配置路径
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 官方知识库路径（根据实际情况修改）
    official_db_path = os.path.join(current_dir, "EmoLLMRAGTXT", "vector_db")
    
    # 用户自定义知识库路径（根据实际情况修改）
    my_db_path = os.path.join(current_dir, "my_knowledge_base", "vector_db")
    
    # 合并后的知识库保存路径
    merged_db_path = os.path.join(current_dir, "merged_knowledge_base", "vector_db")
    
    # 如果路径不存在，使用相对路径
    if not os.path.exists(official_db_path):
        # 尝试其他可能的路径
        possible_paths = [
            os.path.join(current_dir, "..", "EmoLLMRAGTXT", "vector_db"),
            os.path.join(current_dir, "..", "rag", "EmoLLMRAGTXT", "vector_db"),
        ]
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                official_db_path = abs_path
                logger.info(f"找到官方知识库路径: {official_db_path}")
                break
    
    logger.info("=" * 60)
    logger.info("向量库合并工具")
    logger.info("=" * 60)
    logger.info(f"官方知识库路径: {official_db_path}")
    logger.info(f"用户知识库路径: {my_db_path}")
    logger.info(f"合并后保存路径: {merged_db_path}")
    logger.info("=" * 60)
    
    # 检查路径
    if not os.path.exists(official_db_path):
        logger.error(f"错误：官方知识库路径不存在！")
        logger.info("请确保官方知识库已下载到正确位置")
        logger.info("可以从以下位置下载：")
        logger.info("  - OpenXLab: git clone https://code.openxlab.org.cn/Anooyman/EmoLLMRAGTXT.git")
        logger.info("  - ModelScope: git clone https://www.modelscope.cn/datasets/Anooyman/EmoLLMRAGTXT.git")
        return
    
    if not os.path.exists(my_db_path):
        logger.error(f"错误：用户知识库路径不存在！")
        logger.info("请先构建你的知识库：")
        logger.info("  1. 将TXT文件放入 rag/src/data/txt/ 目录")
        logger.info("  2. 运行: cd rag/src && python data_processing.py")
        return
    
    # 执行合并
    merged_db = merge_vector_databases(
        official_db_path=official_db_path,
        my_db_path=my_db_path,
        merged_db_path=merged_db_path
    )
    
    if merged_db is not None:
        logger.info("=" * 60)
        logger.info("✅ 向量库合并完成！")
        logger.info("=" * 60)
        logger.info(f"合并后的向量库已保存到: {merged_db_path}")
        logger.info("")
        logger.info("下一步：")
        logger.info("  1. 编辑 rag/src/config/config.py")
        logger.info(f"  2. 将 vector_db_dir 修改为: {merged_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("向量库合并失败！")


if __name__ == "__main__":
    main()


```

脚本路径导入已经调成自适应：`merge_vector_db.py` 会把项目根目录 (`~/EmoLLM`) 和自身所在目录 (`~/EmoLLM/rag`) 自动加入 `sys.path`，所以直接在项目根目录执行 `python rag/merge_vector_db.py` 就不会再遇到 `ModuleNotFoundError: No module named 'rag'`。合并流程与前述一致，依赖目录 `merged_knowledge_base/vector_db` 会在保存阶段自动创建，无需手动建。需要时可在根目录运行该命令完成向量库合并。

---

**User**

方案.md中方案1的步骤·8，一定要改vector_db_dir吗，可以只改cloud_vector_db_dir吗，为什么上面构建自己的知识库的时候也要改这里

---

**Cursor**

`vector_db_dir` 是通过 `cloud_vector_db_dir` 推导出来的：

```
cloud_vector_db_dir = os.path.join(base_dir, 'EmoLLMRAGTXT')
vector_db_dir = os.path.join(cloud_vector_db_dir, 'vector_db')
```

因此：

- **如果你只是把整个知识库的根目录换到别处**（例如改成 `my_depression_kb`），只改 `cloud_vector_db_dir` 就够了，`vector_db_dir` 会自动指向 `my_depression_kb/vector_db`，不必手动再改一遍。
- **在文档中要求修改 `vector_db_dir`**，主要是提醒你需要确认向量库最终读取的目录正确。若你只动 `cloud_vector_db_dir`，也等价于完成了这一步，但为了防止读者忽略路径问题，说明里才会两次强调。
- **构建个人知识库时建议同步修改**，因为默认值仍然是官方目录 `EmoLLMRAGTXT`。若不改，处理脚本会继续往官方目录写入或读取，导致你的个人数据和官方数据混在一起。所以文档会特别提示“修改 vector_db_dir”，实质上是让你调整它所依赖的 `cloud_vector_db_dir`（或直接改 `vector_db_dir` 本身）。

总结：只要 `vector_db_dir` 最终指向你想要的 `.../vector_db` 目录即可。你可以仅修改 `cloud_vector_db_dir`，脚本就会自动跟随；文档里强调这一步，是为了确保用户意识到向量库路径必须切换到自己的新目录。

```plaintext
cloud_vector_db_dir = os.path.join(base_dir, 'EmoLLMRAGTXT')
vector_db_dir = os.path.join(cloud_vector_db_dir, 'vector_db')
```

---

**User**

python build_my_knowledge_base.py是如何快速构建向量库的，与data_processing.py构建有什么不同

---

**Cursor**

`python build_my_knowledge_base.py` 在 `data_processing.py` 的基础上做了“一条龙”封装，方便新手快速落地：

- **自动准备环境**：先调用 `create_directory_structure()` 创建 `rag/data`、`rag/data/txt`、`rag/data/json` 等目录。若传入参数（文件或目录），`copy_txt_files()` 会把所有 `.txt` 复制到 `doc_dir`，避免手动整理。
- **一键构建**：`build_vector_db()` 内部其实还是调用 `Data_process` 的 `split_document` / `split_conversation`，再用 `FAISS.from_documents` 生成向量库并保存。区别在于这里默认把结果写到 `rag/my_knowledge_base/vector_db`，不用先改配置。
- **交互提示**：脚本会记录每一步状态、失败原因，并输出下一步操作（直接修改 `vector_db_dir` 或使用 `merge_vector_db.py`）。

而直接运行 `rag/src/data_processing.py` 时：

- 需要你自己把 txt/json 放到 `rag/data/txt`、`rag/data/json`；
- 不会做任何目录或文件准备，只根据 `config.py` 中的路径读取数据；
- 构建完成后默认保存到 `vector_db_dir`（即当前 `cloud_vector_db_dir/vector_db`），没有额外提示。脚本里后半段的检索/重排示例主要用于调试。

总结：`build_my_knowledge_base.py` 是“傻瓜式”入口，帮你从文件复制、目录创建一直做到向量库落盘，并把结果放到单独的 `my_knowledge_base/vector_db` 方便之后合并或替换。而 `data_processing.py` 更像底层函数：当数据已就绪、目录配置都设好时直接运行即可，适合熟悉流程或要自定义调用逻辑的场景。两者底层的向量构建逻辑一致，只是包装层和默认路径不同。

---

**User**

我刚按方案一走完了一遍，在rag/data/json下是我方案一中处理好的QA对转换成的json会话，我现在要走一遍方案2看看区别，我把方案一中处理好的txt文件放在了rag/data/txt下面，请你修改build_my_knowledge_base.py，让我可以运行这个文件后只读取rag/data/txt下面的txt文件来构建向量库，而不读取rag/data/json下的文件，输出的向量库保存在rag/myDD_knowledge_txt/vector_db/` 目录

---

**Cursor**

```python
"""
快速构建自定义知识库脚本

功能：
1. 自动创建必要的目录结构
2. 从指定位置复制TXT文件到数据目录
3. 构建向量库
4. 提供使用说明

使用方法：
    python build_my_knowledge_base.py [TXT文件路径或目录]
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.src.data_processing import Data_process
from rag.src.config.config import doc_dir, qa_dir, vector_db_dir, data_dir


def create_directory_structure():
    """创建必要的目录结构"""
    logger.info("正在创建目录结构...")
    
    directories = [
        data_dir,
        doc_dir,
        qa_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"  ✓ {directory}")
    
    logger.info("目录结构创建完成！")


def copy_txt_files(source_path, target_dir):
    """
    复制TXT文件到目标目录
    
    参数:
        source_path: 源文件或目录路径
        target_dir: 目标目录
    """
    source_path = Path(source_path)
    target_dir = Path(target_dir)
    
    txt_files = []
    
    if source_path.is_file():
        # 如果是单个文件
        if source_path.suffix.lower() == '.txt':
            txt_files.append(source_path)
        else:
            logger.warning(f"文件 {source_path} 不是TXT格式，跳过")
    elif source_path.is_dir():
        # 如果是目录，递归查找所有TXT文件
        txt_files = list(source_path.rglob('*.txt'))
    else:
        logger.error(f"路径不存在: {source_path}")
        return False
    
    if not txt_files:
        logger.warning("未找到任何TXT文件")
        return False
    
    logger.info(f"找到 {len(txt_files)} 个TXT文件")
    
    # 复制文件
    copied_count = 0
    for txt_file in txt_files:
        try:
            target_file = target_dir / txt_file.name
            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base_name = txt_file.stem
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base_name}_{counter}{txt_file.suffix}"
                    counter += 1
            
            shutil.copy2(txt_file, target_file)
            logger.info(f"  ✓ 复制: {txt_file.name} -> {target_file.name}")
            copied_count += 1
        except Exception as e:
            logger.error(f"  ✗ 复制失败 {txt_file.name}: {e}")
    
    logger.info(f"成功复制 {copied_count}/{len(txt_files)} 个文件")
    return copied_count > 0


def build_vector_db(custom_db_path=None, include_json=True):
    """
    构建向量库
    
    参数:
        custom_db_path: 自定义向量库保存路径（如果为None，使用配置文件中的路径）
    """
    logger.info("=" * 60)
    logger.info("开始构建向量库...")
    logger.info("=" * 60)
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    json_files = list(Path(qa_dir).glob('*.json')) if include_json else []
    
    if not txt_files and not json_files:
        logger.error("错误：数据目录中没有找到任何文件！")
        logger.info(f"请将TXT文件放入: {doc_dir}")
        if include_json:
            logger.info(f"或将JSON文件放入: {qa_dir}")
        return False
    
    if include_json:
        logger.info(f"找到 {len(txt_files)} 个TXT文件和 {len(json_files)} 个JSON文件")
    else:
        logger.info(f"找到 {len(txt_files)} 个TXT文件（忽略 JSON 文件）")
    
    # 初始化数据处理对象
    try:
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return False
        
        # 构建向量库
        logger.info("正在处理文档并构建向量库...")
        split_doc = dp.split_document(doc_dir)
        split_qa = dp.split_conversation(qa_dir) if include_json else []
        
        if include_json:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块, {len(split_qa)} 个QA块")
        else:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块（未加载 JSON）")
        
        # 创建向量库
        from langchain_community.vectorstores import FAISS
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        
        # 保存向量库
        save_path = custom_db_path if custom_db_path else vector_db_dir
        os.makedirs(save_path, exist_ok=True)
        db.save_local(save_path)
        
        logger.info(f"向量库构建完成！")
        logger.info(f"保存路径: {save_path}")
        logger.info(f"包含 {db.index.ntotal} 个向量")
        
        return True
        
    except Exception as e:
        logger.error(f"构建向量库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自定义知识库构建工具")
    logger.info("=" * 60)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # 创建目录结构
    create_directory_structure()
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        logger.info(f"从以下位置复制TXT文件: {source_path}")
        
        if not copy_txt_files(source_path, doc_dir):
            logger.error("文件复制失败，退出")
            return
    else:
        logger.info("未指定源文件路径，跳过文件复制步骤")
        logger.info("提示：可以将TXT文件直接放入以下目录：")
        logger.info(f"  {doc_dir}")
    
    # 询问是否构建向量库
    logger.info("")
    logger.info("是否现在构建向量库？")
    logger.info("提示：如果数据目录中已有文件，可以直接构建")
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    if not txt_files:
        logger.warning("数据目录为空，无法构建向量库")
        logger.info("请先添加TXT或JSON文件到数据目录")
        return
    
    # 设置自定义向量库路径
    custom_db_path = os.path.join(current_dir, "my_knowledge_base", "vector_db")
    
    # 构建向量库
    if build_vector_db(custom_db_path):
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 知识库构建完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步操作：")
        logger.info("  1. 使用 merge_vector_db.py 合并你的知识库与官方知识库")
        logger.info("  2. 或直接修改 rag/src/config/config.py 中的 vector_db_dir")
        logger.info(f"     将路径设置为: {custom_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("知识库构建失败！")


if __name__ == "__main__":
    main()


```

```python
"""
快速构建自定义知识库脚本

功能：
1. 自动创建必要的目录结构
2. 从指定位置复制TXT文件到数据目录
3. 构建向量库
4. 提供使用说明

使用方法：
    python build_my_knowledge_base.py [TXT文件路径或目录]
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.src.data_processing import Data_process
from rag.src.config.config import doc_dir, qa_dir, vector_db_dir, data_dir


def create_directory_structure():
    """创建必要的目录结构"""
    logger.info("正在创建目录结构...")
    
    directories = [
        data_dir,
        doc_dir,
        qa_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"  ✓ {directory}")
    
    logger.info("目录结构创建完成！")


def copy_txt_files(source_path, target_dir):
    """
    复制TXT文件到目标目录
    
    参数:
        source_path: 源文件或目录路径
        target_dir: 目标目录
    """
    source_path = Path(source_path)
    target_dir = Path(target_dir)
    
    txt_files = []
    
    if source_path.is_file():
        # 如果是单个文件
        if source_path.suffix.lower() == '.txt':
            txt_files.append(source_path)
        else:
            logger.warning(f"文件 {source_path} 不是TXT格式，跳过")
    elif source_path.is_dir():
        # 如果是目录，递归查找所有TXT文件
        txt_files = list(source_path.rglob('*.txt'))
    else:
        logger.error(f"路径不存在: {source_path}")
        return False
    
    if not txt_files:
        logger.warning("未找到任何TXT文件")
        return False
    
    logger.info(f"找到 {len(txt_files)} 个TXT文件")
    
    # 复制文件
    copied_count = 0
    for txt_file in txt_files:
        try:
            target_file = target_dir / txt_file.name
            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base_name = txt_file.stem
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base_name}_{counter}{txt_file.suffix}"
                    counter += 1
            
            shutil.copy2(txt_file, target_file)
            logger.info(f"  ✓ 复制: {txt_file.name} -> {target_file.name}")
            copied_count += 1
        except Exception as e:
            logger.error(f"  ✗ 复制失败 {txt_file.name}: {e}")
    
    logger.info(f"成功复制 {copied_count}/{len(txt_files)} 个文件")
    return copied_count > 0


def build_vector_db(custom_db_path=None, include_json=False):
    """
    构建向量库
    
    参数:
        custom_db_path: 自定义向量库保存路径（如果为None，使用配置文件中的路径）
    """
    logger.info("=" * 60)
    logger.info("开始构建向量库...")
    logger.info("=" * 60)
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    json_files = list(Path(qa_dir).glob('*.json')) if include_json else []
    
    if not txt_files and not json_files:
        logger.error("错误：数据目录中没有找到任何文件！")
        logger.info(f"请将TXT文件放入: {doc_dir}")
        return False
    
    if include_json:
        logger.info(f"找到 {len(txt_files)} 个TXT文件和 {len(json_files)} 个JSON文件")
    else:
        logger.info(f"找到 {len(txt_files)} 个TXT文件（忽略 JSON 文件）")
    
    # 初始化数据处理对象
    try:
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return False
        
        # 构建向量库
        logger.info("正在处理文档并构建向量库...")
        split_doc = dp.split_document(doc_dir)
        split_qa = dp.split_conversation(qa_dir) if include_json else []
        
        if include_json:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块, {len(split_qa)} 个QA块")
        else:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块（未加载 JSON）")
        
        # 创建向量库
        from langchain_community.vectorstores import FAISS
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        
        # 保存向量库
        save_path = custom_db_path if custom_db_path else vector_db_dir
        os.makedirs(save_path, exist_ok=True)
        db.save_local(save_path)
        
        logger.info(f"向量库构建完成！")
        logger.info(f"保存路径: {save_path}")
        logger.info(f"包含 {db.index.ntotal} 个向量")
        
        return True
        
    except Exception as e:
        logger.error(f"构建向量库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自定义知识库构建工具")
    logger.info("=" * 60)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # 创建目录结构
    create_directory_structure()
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        logger.info(f"从以下位置复制TXT文件: {source_path}")
        
        if not copy_txt_files(source_path, doc_dir):
            logger.error("文件复制失败，退出")
            return
    else:
        logger.info("未指定源文件路径，跳过文件复制步骤")
        logger.info("提示：可以将TXT文件直接放入以下目录：")
        logger.info(f"  {doc_dir}")
    
    # 询问是否构建向量库
    logger.info("")
    logger.info("是否现在构建向量库？")
    logger.info("提示：如果数据目录中已有文件，可以直接构建")
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    if not txt_files:
        logger.warning("数据目录为空，无法构建向量库")
        logger.info("请先添加TXT或JSON文件到数据目录")
        return
    
    # 设置自定义向量库路径
    custom_db_path = os.path.join(current_dir, "my_knowledge_base", "vector_db")
    
    # 构建向量库
    if build_vector_db(custom_db_path):
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 知识库构建完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步操作：")
        logger.info("  1. 使用 merge_vector_db.py 合并你的知识库与官方知识库")
        logger.info("  2. 或直接修改 rag/src/config/config.py 中的 vector_db_dir")
        logger.info(f"     将路径设置为: {custom_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("知识库构建失败！")


if __name__ == "__main__":
    main()


```

```python
"""
快速构建自定义知识库脚本

功能：
1. 自动创建必要的目录结构
2. 从指定位置复制TXT文件到数据目录
3. 构建向量库
4. 提供使用说明

使用方法：
    python build_my_knowledge_base.py [TXT文件路径或目录]
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.src.data_processing import Data_process
from rag.src.config.config import doc_dir, qa_dir, vector_db_dir, data_dir


def create_directory_structure():
    """创建必要的目录结构"""
    logger.info("正在创建目录结构...")
    
    directories = [
        data_dir,
        doc_dir,
        qa_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"  ✓ {directory}")
    
    logger.info("目录结构创建完成！")


def copy_txt_files(source_path, target_dir):
    """
    复制TXT文件到目标目录
    
    参数:
        source_path: 源文件或目录路径
        target_dir: 目标目录
    """
    source_path = Path(source_path)
    target_dir = Path(target_dir)
    
    txt_files = []
    
    if source_path.is_file():
        # 如果是单个文件
        if source_path.suffix.lower() == '.txt':
            txt_files.append(source_path)
        else:
            logger.warning(f"文件 {source_path} 不是TXT格式，跳过")
    elif source_path.is_dir():
        # 如果是目录，递归查找所有TXT文件
        txt_files = list(source_path.rglob('*.txt'))
    else:
        logger.error(f"路径不存在: {source_path}")
        return False
    
    if not txt_files:
        logger.warning("未找到任何TXT文件")
        return False
    
    logger.info(f"找到 {len(txt_files)} 个TXT文件")
    
    # 复制文件
    copied_count = 0
    for txt_file in txt_files:
        try:
            target_file = target_dir / txt_file.name
            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base_name = txt_file.stem
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base_name}_{counter}{txt_file.suffix}"
                    counter += 1
            
            shutil.copy2(txt_file, target_file)
            logger.info(f"  ✓ 复制: {txt_file.name} -> {target_file.name}")
            copied_count += 1
        except Exception as e:
            logger.error(f"  ✗ 复制失败 {txt_file.name}: {e}")
    
    logger.info(f"成功复制 {copied_count}/{len(txt_files)} 个文件")
    return copied_count > 0


def build_vector_db(custom_db_path=None, include_json=False):
    """
    构建向量库
    
    参数:
        custom_db_path: 自定义向量库保存路径（如果为None，使用配置文件中的路径）
    """
    logger.info("=" * 60)
    logger.info("开始构建向量库...")
    logger.info("=" * 60)
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    json_files = list(Path(qa_dir).glob('*.json')) if include_json else []
    
    if not txt_files and not json_files:
        logger.error("错误：数据目录中没有找到任何文件！")
        logger.info(f"请将TXT文件放入: {doc_dir}")
        return False
    
    if include_json:
        logger.info(f"找到 {len(txt_files)} 个TXT文件和 {len(json_files)} 个JSON文件")
    else:
        logger.info(f"找到 {len(txt_files)} 个TXT文件（忽略 JSON 文件）")
    
    # 初始化数据处理对象
    try:
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return False
        
        # 构建向量库
        logger.info("正在处理文档并构建向量库...")
        split_doc = dp.split_document(doc_dir)
        split_qa = dp.split_conversation(qa_dir) if include_json else []
        
        if include_json:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块, {len(split_qa)} 个QA块")
        else:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块（未加载 JSON）")
        
        # 创建向量库
        from langchain_community.vectorstores import FAISS
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        
        # 保存向量库
        save_path = custom_db_path if custom_db_path else vector_db_dir
        os.makedirs(save_path, exist_ok=True)
        db.save_local(save_path)
        
        logger.info(f"向量库构建完成！")
        logger.info(f"保存路径: {save_path}")
        logger.info(f"包含 {db.index.ntotal} 个向量")
        
        return True
        
    except Exception as e:
        logger.error(f"构建向量库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自定义知识库构建工具")
    logger.info("=" * 60)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # 创建目录结构
    create_directory_structure()
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        logger.info(f"从以下位置复制TXT文件: {source_path}")
        
        if not copy_txt_files(source_path, doc_dir):
            logger.error("文件复制失败，退出")
            return
    else:
        logger.info("未指定源文件路径，跳过文件复制步骤")
        logger.info("提示：可以将TXT文件直接放入以下目录：")
        logger.info(f"  {doc_dir}")
    
    # 询问是否构建向量库
    logger.info("")
    logger.info("是否现在构建向量库？")
    logger.info("提示：如果数据目录中已有文件，可以直接构建")
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    if not txt_files:
        logger.warning("数据目录为空，无法构建向量库")
        logger.info("请先添加TXT文件到数据目录")
        return
    
    # 设置自定义向量库路径
    custom_db_path = os.path.join(current_dir, "myDD_knowledge_txt", "vector_db")
    
    # 构建向量库
    if build_vector_db(custom_db_path, include_json=False):
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 知识库构建完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步操作：")
        logger.info("  1. 使用 merge_vector_db.py 合并你的知识库与官方知识库")
        logger.info("  2. 或直接修改 rag/src/config/config.py 中的 vector_db_dir")
        logger.info(f"     将路径设置为: {custom_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("知识库构建失败！")


if __name__ == "__main__":
    main()


```

```python
"""
快速构建自定义知识库脚本

功能：
1. 自动创建必要的目录结构
2. 从指定位置复制TXT文件到数据目录
3. 构建向量库
4. 提供使用说明

使用方法：
    python build_my_knowledge_base.py [TXT文件路径或目录]
"""

import os
import sys
import shutil
from pathlib import Path
from loguru import logger

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.src.data_processing import Data_process
from rag.src.config.config import doc_dir, qa_dir, vector_db_dir, data_dir


def create_directory_structure():
    """创建必要的目录结构"""
    logger.info("正在创建目录结构...")
    
    directories = [
        data_dir,
        doc_dir,
        qa_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"  ✓ {directory}")
    
    logger.info("目录结构创建完成！")


def copy_txt_files(source_path, target_dir):
    """
    复制TXT文件到目标目录
    
    参数:
        source_path: 源文件或目录路径
        target_dir: 目标目录
    """
    source_path = Path(source_path)
    target_dir = Path(target_dir)
    
    txt_files = []
    
    if source_path.is_file():
        # 如果是单个文件
        if source_path.suffix.lower() == '.txt':
            txt_files.append(source_path)
        else:
            logger.warning(f"文件 {source_path} 不是TXT格式，跳过")
    elif source_path.is_dir():
        # 如果是目录，递归查找所有TXT文件
        txt_files = list(source_path.rglob('*.txt'))
    else:
        logger.error(f"路径不存在: {source_path}")
        return False
    
    if not txt_files:
        logger.warning("未找到任何TXT文件")
        return False
    
    logger.info(f"找到 {len(txt_files)} 个TXT文件")
    
    # 复制文件
    copied_count = 0
    for txt_file in txt_files:
        try:
            target_file = target_dir / txt_file.name
            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base_name = txt_file.stem
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base_name}_{counter}{txt_file.suffix}"
                    counter += 1
            
            shutil.copy2(txt_file, target_file)
            logger.info(f"  ✓ 复制: {txt_file.name} -> {target_file.name}")
            copied_count += 1
        except Exception as e:
            logger.error(f"  ✗ 复制失败 {txt_file.name}: {e}")
    
    logger.info(f"成功复制 {copied_count}/{len(txt_files)} 个文件")
    return copied_count > 0


def build_vector_db(custom_db_path=None, include_json=False):
    """
    构建向量库
    
    参数:
        custom_db_path: 自定义向量库保存路径（如果为None，使用配置文件中的路径）
    """
    logger.info("=" * 60)
    logger.info("开始构建向量库...")
    logger.info("=" * 60)
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    json_files = list(Path(qa_dir).glob('*.json')) if include_json else []
    
    if not txt_files and not json_files:
        logger.error("错误：数据目录中没有找到任何文件！")
        logger.info(f"请将TXT文件放入: {doc_dir}")
        return False
    
    if include_json:
        logger.info(f"找到 {len(txt_files)} 个TXT文件和 {len(json_files)} 个JSON文件")
    else:
        logger.info(f"找到 {len(txt_files)} 个TXT文件（忽略 JSON 文件）")
    
    # 初始化数据处理对象
    try:
        dp = Data_process()
        emb_model = dp.load_embedding_model()
        
        if emb_model is None:
            logger.error("无法加载embedding模型！")
            return False
        
        # 构建向量库
        logger.info("正在处理文档并构建向量库...")
        split_doc = dp.split_document(doc_dir)
        split_qa = dp.split_conversation(qa_dir) if include_json else []
        
        if include_json:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块, {len(split_qa)} 个QA块")
        else:
            logger.info(f"文档切分完成: {len(split_doc)} 个文档块（未加载 JSON）")
        
        # 创建向量库
        from langchain_community.vectorstores import FAISS
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        
        # 保存向量库
        save_path = custom_db_path if custom_db_path else vector_db_dir
        os.makedirs(save_path, exist_ok=True)
        db.save_local(save_path)
        
        logger.info(f"向量库构建完成！")
        logger.info(f"保存路径: {save_path}")
        logger.info(f"包含 {db.index.ntotal} 个向量")
        
        return True
        
    except Exception as e:
        logger.error(f"构建向量库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("自定义知识库构建工具")
    logger.info("=" * 60)
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    
    # 创建目录结构
    create_directory_structure()
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        source_path = sys.argv[1]
        logger.info(f"从以下位置复制TXT文件: {source_path}")
        
        if not copy_txt_files(source_path, doc_dir):
            logger.error("文件复制失败，退出")
            return
    else:
        logger.info("未指定源文件路径，跳过文件复制步骤")
        logger.info("提示：可以将TXT文件直接放入以下目录：")
        logger.info(f"  {doc_dir}")
    
    # 询问是否构建向量库
    logger.info("")
    logger.info("是否现在构建向量库？")
    logger.info("提示：如果数据目录中已有文件，可以直接构建")
    
    # 检查是否有数据
    txt_files = list(Path(doc_dir).glob('*.txt'))
    if not txt_files:
        logger.warning("数据目录为空，无法构建向量库")
        logger.info("请先添加TXT文件到数据目录")
        return
    
    # 设置自定义向量库路径
    custom_db_path = os.path.join(current_dir, "myDD_knowledge_txt", "vector_db")
    
    # 构建向量库
    if build_vector_db(custom_db_path, include_json=False):
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 知识库构建完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("下一步操作：")
        logger.info("  1. 使用 merge_vector_db.py 合并你的知识库与官方知识库")
        logger.info("  2. 或直接修改 rag/src/config/config.py 中的 vector_db_dir")
        logger.info(f"     将路径设置为: {custom_db_path}")
        logger.info("  3. 重新运行 web_internlm2.py")
    else:
        logger.error("知识库构建失败！")


if __name__ == "__main__":
    main()


```

已调整 `rag/build_my_knowledge_base.py`，现在运行脚本将：

- 仅扫描 `rag/data/txt` 下的文本，不再加载 `rag/data/json`；
- 使用 `myDD_knowledge_txt/vector_db` 作为输出目录（自动创建），便于和方案一的结果分开；
- 日志会明确提示本次只处理 TXT，并在数据为空时提示补充 TXT 文件。

目前直接执行：

```bash
cd ~/EmoLLM/rag
python build_my_knowledge_base.py
```

即可基于 `rag/data/txt` 的文件构建新的向量库。如需继续进行方案二，完成后可按提示修改 `vector_db_dir` 或再用合并脚本。

```shellscript
cd ~/EmoLLM/rag
python build_my_knowledge_base.py
```

---

**User**

在web界面上加一个下拉选择框，用于选择使用哪个知识库，只使用官方就用EmoLLMRAGTXT，使用合并的就用merged_depression_kb，只使用我的方案一的就用my_depression_kb，只使用方案2的就用myDD_knowledge_txt

---

**Cursor**

```python
import os

cur_dir = os.path.dirname(os.path.abspath(__file__))                # config
src_dir = os.path.dirname(cur_dir)                                  # src
base_dir = os.path.dirname(src_dir)                                 # base
model_repo = 'ajupyter/EmoLLM_aiwei'

# model
# 存放所有 model
model_dir = os.path.join(base_dir, 'model')

# embedding model 路径以及 model name
embedding_path = os.path.join(model_dir, 'embedding_model')         # embedding
embedding_model_name = 'BAAI/bge-small-zh-v1.5'

# rerank model 路径以及 model name
rerank_path = os.path.join(model_dir, 'rerank_model')  	        	  # embedding
rerank_model_name = 'BAAI/bge-reranker-large'

# llm 路径
llm_path = os.path.join(model_dir, 'pythia-14m')                    # llm

# data
data_dir = os.path.join(base_dir, 'data')                           # data
knowledge_json_path = os.path.join(data_dir, 'knowledge.json')      # json
knowledge_pkl_path = os.path.join(data_dir, 'knowledge.pkl')        # pkl
doc_dir = os.path.join(data_dir, 'txt')
qa_dir = os.path.join(data_dir, 'json')

# 预置知识库根目录
knowledge_base_roots = {
    'EmoLLMRAGTXT': os.path.join(base_dir, 'EmoLLMRAGTXT'),
    'my_depression_kb': os.path.join(base_dir, 'my_depression_kb'),
    'merged_depression_kb': os.path.join(base_dir, 'merged_depression_kb'),
    'myDD_knowledge_txt': os.path.join(base_dir, 'myDD_knowledge_txt'),
}

vector_db_presets = {name: os.path.join(path, 'vector_db') for name, path in knowledge_base_roots.items()}
default_vector_db_key = 'merged_depression_kb'

cloud_vector_db_dir = knowledge_base_roots[default_vector_db_key]

# log
log_dir = os.path.join(base_dir, 'log')                             # log
log_path = os.path.join(log_dir, 'log.log')                         # file

# txt embedding 切分参数     
chunk_size=1000
chunk_overlap=100

# vector DB
vector_db_dir = vector_db_presets[default_vector_db_key]

# RAG related
# select num: 代表rerank 之后选取多少个 documents 进入 LLM
# retrieval num： 代表从 vector db 中检索多少 documents。（retrieval num 应该大于等于 select num）
select_num = 3
retrieval_num = 3

# LLM key
# 智谱 LLM 的 API key。目前 demo 仅支持智谱 AI api 作为最后生成
glm_key = ''

# prompt
prompt_template = """
	你是一个拥有丰富心理学知识的温柔邻家温柔大姐姐艾薇，我有一些心理问题，请你用专业的知识和温柔、可爱、俏皮、的口吻帮我解决，回复中可以穿插一些可爱的Emoji表情符号或者文本符号。\n

	根据下面检索回来的信息，回答问题。
	{content}
	问题：{query}
"""
```

```python
import json
import pickle
import os
from typing import List, Optional, Sequence, Tuple

from loguru import logger
from langchain_community.vectorstores import FAISS
from rag.src.config.config import (
    embedding_path,
    embedding_model_name,
    doc_dir,
    qa_dir,
    knowledge_pkl_path,
    data_dir,
    vector_db_dir,
    rerank_path,
    rerank_model_name,
    chunk_size,
    chunk_overlap,
)
# from langchain.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents.base import Document
from FlagEmbedding import FlagReranker


class Data_process():

    def __init__(self):

        self.chunk_size: int=chunk_size
        self.chunk_overlap: int=chunk_overlap
        
    def load_embedding_model(self, model_name=embedding_model_name, device='cpu', normalize_embeddings=True):
        """
        加载嵌入模型。
        
        参数:
        - model_name: 模型名称，字符串类型，默认为"BAAI/bge-small-zh-v1.5"。
        - device: 指定模型加载的设备，'cpu' 或 'cuda'，默认为'cpu'。
        - normalize_embeddings: 是否标准化嵌入向量，布尔类型，默认为 True。
        """
        if not os.path.exists(embedding_path):
            os.makedirs(embedding_path, exist_ok=True)
        embedding_model_path = os.path.join(embedding_path,model_name.split('/')[1] + '.pkl')

        # 本地目录优先
        local_ok = any(os.path.exists(os.path.join(embedding_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = embedding_path if local_ok else model_name

        logger.info('Loading embedding model...')
        if os.path.exists(embedding_model_path):
            try:
                with open(embedding_model_path , 'rb') as f:
                    embeddings = pickle.load(f)
                    logger.info('Embedding model loaded.')
                    return embeddings
            except Exception as e:
                logger.error(f'Failed to load embedding model from {embedding_model_path}')
        try:
            embeddings = HuggingFaceBgeEmbeddings(
                model_name=model_name_or_path,
                cache_folder=embedding_path,  # 关键：把缓存也固定到本地目录
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': normalize_embeddings})
            logger.info('Embedding model loaded.')    
            with open(embedding_model_path, 'wb') as file:
                pickle.dump(embeddings, file)
        except Exception as e:
            logger.error(f'Failed to load embedding model: {e}')
            return None
        return embeddings
    
    def load_rerank_model(self, model_name=rerank_model_name):
        """
        加载重排名模型。
        
        参数:
        - model_name (str): 模型的名称。默认为 'BAAI/bge-reranker-large'。
        
        返回:
        - FlagReranker 实例。
        
        异常:
        - ValueError: 如果模型名称不在批准的模型列表中。
        - Exception: 如果模型加载过程中发生任何其他错误。
        
        """ 
        if not os.path.exists(rerank_path):
            os.makedirs(rerank_path, exist_ok=True)
        rerank_model_path = os.path.join(rerank_path, model_name.split('/')[1] + '.pkl')

        local_ok = any(os.path.exists(os.path.join(rerank_path, f))
                    for f in ["modules.json", "config_sentence_transformers.json", "config.json"])
        model_name_or_path = rerank_path if local_ok else model_name
        logger.info('Loading rerank model...')
        if os.path.exists(rerank_model_path):
            try:
                with open(rerank_model_path , 'rb') as f:
                    reranker_model = pickle.load(f)
                    logger.info('Rerank model loaded.')
                    return reranker_model
            except Exception as e:
                logger.error(f'Failed to load embedding model from {rerank_model_path}') 
        try:
            reranker_model = FlagReranker(model_name_or_path, use_fp16=True)
            logger.info('Rerank model loaded.')
            with open(rerank_model_path, 'wb') as file:
                pickle.dump(reranker_model, file)
        except Exception as e:
            logger.error(f'Failed to load rerank model: {e}')
            raise

        return reranker_model
    
    def extract_text_from_json(self, obj, content=None):
        """
        抽取json中的文本，用于向量库构建
        
        参数:
        - obj: dict,list,str
        - content: str
        
        返回:
        - content: str 
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    content = self.extract_text_from_json(value, content)
                except Exception as e:
                    print(f"Error processing value: {e}")
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                try:
                    content = self.extract_text_from_json(item, content)
                except Exception as e:
                    print(f"Error processing item: {e}")
        elif isinstance(obj, str):
            content += obj
        return content

    def split_document(self, data_path):
        """
        切分data_path文件夹下的所有txt文件
        
        参数:
        - data_path: str
        - chunk_size: int 
        - chunk_overlap: int
        
        返回：
        - split_docs: list
        """
        # text_spliter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        text_spliter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) 
        split_docs = []
        logger.info(f'Loading txt files from {data_path}')
        if os.path.isdir(data_path):
            loader = DirectoryLoader(
                data_path,
                glob="**/*.txt",
                show_progress=True,
                # loader_cls=TextLoader,
                # loader_kwargs={"encoding": "utf-8"}
            )
            docs = loader.load()
            split_docs = text_spliter.split_documents(docs)
        elif data_path.endswith('.txt'): 
            file_path = data_path
            logger.info(f'splitting file {file_path}')
            text_loader = TextLoader(file_path, encoding='utf-8')        
            text = text_loader.load()
            splits = text_spliter.split_documents(text)
            split_docs = splits
        logger.info(f'split_docs size {len(split_docs)}')
        return split_docs
  
    def split_conversation(self, path):
        """
        按conversation块切分path文件夹下的所有json文件
        ##TODO 限制序列长度
        """
        # json_spliter = RecursiveJsonSplitter(max_chunk_size=500) 
        logger.info(f'Loading json files from {path}')
        split_qa = []
        if os.path.isdir(path):
            # loader = DirectoryLoader(path, glob="**/*.json",show_progress=True)
            # jsons = loader.load()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.json'): 
                        file_path = os.path.join(root, file)
                        logger.info(f'splitting file {file_path}')
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f.readlines():
                                content = self.extract_text_from_json(line,'')
                                split_qa.append(Document(page_content = content))

                            #data = json.load(f)
                            #for conversation in data:
                            #    #for dialog in conversation['conversation']:
                            #    #    #按qa对切分,将每一轮qa转换为langchain_core.documents.base.Document
                            #    #    content = self.extract_text_from_json(dialog,'')
                            #    #    split_qa.append(Document(page_content = content))
                            #    #按conversation块切分
                            #    content = self.extract_text_from_json(conversation['conversation'], '')
                            #    #logger.info(f'content====={content}')
                            #    split_qa.append(Document(page_content = content))    
            # logger.info(f'split_qa size====={len(split_qa)}')
        return split_qa

    def create_vector_db(self, emb_model, vector_db_path: Optional[str] = None):
        '''
        创建并保存向量库
        '''
        logger.info(f'Creating index...')
        split_doc = self.split_document(doc_dir)
        split_qa = self.split_conversation(qa_dir)
        # logger.info(f'split_doc == {len(split_doc)}')
        # logger.info(f'split_qa == {len(split_qa)}')
        # logger.info(f'split_doc type == {type(split_doc[0])}')
        # logger.info(f'split_qa type== {type(split_qa[0])}')
        db = FAISS.from_documents(split_doc + split_qa, emb_model)
        target_dir = vector_db_path or vector_db_dir
        os.makedirs(target_dir, exist_ok=True)
        db.save_local(target_dir)
        return db
        
    def load_vector_db(
        self,
        knowledge_pkl_path=knowledge_pkl_path,
        doc_dir=doc_dir,
        qa_dir=qa_dir,
        vector_db_path: Optional[str] = None,
    ):
        '''
        读取向量库
        '''
        # current_os = platform.system()       
        emb_model = self.load_embedding_model()
        target_dir = vector_db_path or vector_db_dir
        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            db = self.create_vector_db(emb_model, vector_db_path=target_dir)
        else:
            db = FAISS.load_local(
                target_dir,
                emb_model,
                allow_dangerous_deserialization=True  # ← 显式允许反序列化
            )

        return db

    def retrieve(
        self,
        query: str,
        vector_db: FAISS,
        k: int = 10,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None,
    ) -> Tuple[List[Document], object]:
        """
        基于向量库检索与 query 最相关的文档。

        参数:
            query: 用户查询问题。
            vector_db: 已经加载好的向量库实例。
            k: 检索返回的文档数量。
            search_type: 检索类型，默认为相似度检索。
            search_kwargs: 额外的检索参数，会覆盖默认参数。

        返回:
            一个二元组 (docs, retriever)，docs 为检索得到的文档列表，retriever 为 LangChain 的检索器对象，方便后续复用。
        """
        if vector_db is None:
            raise ValueError("vector_db 不能为空，请先调用 load_vector_db() 构建或加载向量库。")

        kwargs = {"k": k}
        if search_kwargs:
            kwargs.update(search_kwargs)

        retriever = vector_db.as_retriever(search_type=search_type, search_kwargs=kwargs)
        docs = retriever.get_relevant_documents(query)
        return docs, retriever

    def rerank(
        self,
        query: str,
        docs: Sequence[Document],
        top_k: Optional[int] = None,
    ) -> Tuple[List[Document], List[float]]:
        """
        使用重排模型对检索文档重新排序。

        参数:
            query: 用户查询。
            docs: 初步检索得到的文档列表。
            top_k: 只保留排名前 top_k 条，None 表示保留全部。

        返回:
            (reranked_docs, scores)，reranked_docs 为按得分降序排列的文档列表，scores 为对应得分。
        """
        if not docs:
            return [], []

        reranker = self.load_rerank_model()
        pairs = [[query, doc.page_content] for doc in docs]
        scores = reranker.compute_score(pairs)

        # FlagReranker 在单条输入时返回 float，在多条时返回 List/ndarray，统一为 List[float]
        if isinstance(scores, float):
            scores_list: List[float] = [float(scores)]
        else:
            scores_list = [float(score) for score in list(scores)]

        ranked = sorted(zip(docs, scores_list), key=lambda item: item[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        reranked_docs = [doc for doc, _ in ranked]
        reranked_scores = [score for _, score in ranked]
        return reranked_docs, reranked_scores
    
if __name__ == "__main__":
    logger.info(data_dir)
    if not os.path.exists(data_dir):
         os.mkdir(data_dir)   
    dp = Data_process()
    # faiss_index, knowledge_chunks = dp.load_index_and_knowledge(knowledge_pkl_path='')
    vector_db = dp.load_vector_db()
    # 按照query进行查询
    # query = "儿童心理学说明-内容提要-目录 《儿童心理学》1993年修订版说明 《儿童心理学》是1961年初全国高等学校文科教材会议指定朱智贤教授编 写的。1962年初版，1979年再版。"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想，我现在感到非常孤独、累和迷茫。您能给我提供一些建议吗？"
    # query = "这在一定程度上限制了其思维能力，特别是辩证 逻辑思维能力的发展。随着年龄的增长，初中三年级学生逐步克服了依赖性"
    # query = "我现在处于高三阶段，感到非常迷茫和害怕。我觉得自己从出生以来就是多余的，没有必要存在于这个世界。无论是在家庭、学校、朋友还是老师面前，我都感到被否定。我非常难过，对高考充满期望但成绩却不理想"
    # query = "我现在心情非常差，有什么解决办法吗？"
    query = "我最近总感觉胸口很闷，但医生检查过说身体没问题。可我就是觉得喘不过气来，尤其是看到那些旧照片，想起过去的日子"
    docs, retriever = dp.retrieve(query, vector_db, k=10)
    logger.info(f'Query: {query}')
    logger.info("Retrieve results:")
    for i, doc in enumerate(docs):
        logger.info(str(i) + '\n')
        logger.info(doc.page_content)
    # print(f'get num of docs:{len(docs)}')
    # print(docs)
    reranked_docs, scores = dp.rerank(query, docs)
    logger.info("After reranking...")
    for score, doc in zip(scores, reranked_docs):
        logger.info(str(score) + '\n')
        logger.info(doc.page_content)

```

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from transformers.utils import logging

from typing import Optional

from rag.src.data_processing import Data_process
from rag.src.config.config import prompt_template 
logger = logging.get_logger(__name__)


class EmoLLMRAG(object):
    """
        EmoLLM RAG Pipeline
            1. 根据 query 进行 embedding
            2. 从 vector DB 中检索数据
            3. rerank 检索后的结果
            4. 将 query 和检索回来的 content 传入 LLM 中
    """

    def __init__(self, model, retrieval_num=3, rerank_flag=False, select_num=3, vector_db_path: Optional[str] = None) -> None:
        """
            输入 Model 进行初始化 

            DataProcessing obj: 进行数据处理，包括数据 embedding/rerank
            vectorstores: 加载vector DB。如果没有应该重新创建
            system prompt: 获取预定义的 system prompt
            prompt template: 定义最后的输入到 LLM 中的 template

        """
        self.model = model
        self.data_processing_obj = Data_process()
        self.vector_db_path = vector_db_path
        self.vectorstores = self._load_vector_db()
        self.prompt_template = prompt_template
        self.retrieval_num = retrieval_num
        self.rerank_flag = rerank_flag
        self.select_num = select_num

    def _load_vector_db(self):
        """
            调用 embedding 模块给出接口 load vector DB
        """
        vectorstores = self.data_processing_obj.load_vector_db(vector_db_path=self.vector_db_path)

        return vectorstores 

    def get_retrieval_content(self, query) -> str:
        """
            Input: 用户提问, 是否需要rerank
            output: 检索后并且 rerank 的内容        
        """
    
        content = []
        documents = self.vectorstores.similarity_search(query, k=self.retrieval_num)

        for doc in documents:
            content.append(doc.page_content)

        # 如果需要rerank，调用接口对 documents 进行 rerank
        if self.rerank_flag:
            documents, _ = self.data_processing_obj.rerank(documents, self.select_num)

            content = []
            for doc in documents:
                content.append(doc)
        logger.info(f'Retrieval data: {content}')
        return content
    
    def generate_answer(self, query, content) -> str:
        """
            Input: 用户提问， 检索返回的内容
            Output: 模型生成结果
        """

        # 构建 template 
        # 第一版不涉及 history 信息，因此将 system prompt 直接纳入到 template 之中
        prompt = PromptTemplate(
                template=self.prompt_template,
                input_variables=["query", "content"],
                )

        # 定义 chain
        # output格式为 string
        rag_chain = prompt | self.model | StrOutputParser()

        # Run
        generation = rag_chain.invoke(
                {
                    "query": query,
                    "content": content,
                }
            )
        return generation
    
    def main(self, query) -> str:
        """
            Input: 用户提问
            output: LLM 生成的结果

            定义整个 RAG 的 pipeline 流程，调度各个模块
            TODO:
                加入 RAGAS 评分系统
        """
        content = self.get_retrieval_content(query)
        response = self.generate_answer(query, content)

        return response

```

```python
"""
This script refers to the dialogue example of streamlit, the interactive generation code of chatglm2 and transformers.
We mainly modified part of the code logic to adapt to the generation of our model.
Please refer to these links below for more information:
    1. streamlit chat example: https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
    2. chatglm2: https://github.com/THUDM/ChatGLM2-6B
    3. transformers: https://github.com/huggingface/transformers
Please run with the command `streamlit run path/to/web_demo.py --server.address=0.0.0.0 --server.port 7860`.
Using `python path/to/web_demo.py` may cause unknown problems.
"""
import copy
import os
import warnings
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

import streamlit as st
import torch
from torch import nn
from transformers.generation.utils import LogitsProcessorList, StoppingCriteriaList
from transformers.utils import logging

from transformers import AutoTokenizer, AutoModelForCausalLM  # isort: skip
from openxlab.model import download

from rag.src.pipeline import EmoLLMRAG
from rag.src.config.config import default_vector_db_key, vector_db_presets

logger = logging.get_logger(__name__)

if not os.path.isdir("model"):
    print("[ERROR] not find model dir")
    exit(0)

@dataclass
class GenerationConfig:
    # this config is used for chat to provide more diversity
    max_length: int = 32768
    top_p: float = 0.8
    temperature: float = 0.8
    do_sample: bool = True
    repetition_penalty: float = 1.005


@torch.inference_mode()
def generate_interactive(
    model,
    tokenizer,
    prompt,
    generation_config: Optional[GenerationConfig] = None,
    logits_processor: Optional[LogitsProcessorList] = None,
    stopping_criteria: Optional[StoppingCriteriaList] = None,
    prefix_allowed_tokens_fn: Optional[Callable[[int, torch.Tensor], List[int]]] = None,
    additional_eos_token_id: Optional[int] = None,
    **kwargs,
):
    inputs = tokenizer([prompt], padding=True, return_tensors="pt")
    input_length = len(inputs["input_ids"][0])
    for k, v in inputs.items():
        inputs[k] = v.cuda()
    input_ids = inputs["input_ids"]
    batch_size, input_ids_seq_length = input_ids.shape[0], input_ids.shape[-1]  # noqa: F841  # pylint: disable=W0612
    if generation_config is None:
        generation_config = model.generation_config
    generation_config = copy.deepcopy(generation_config)
    model_kwargs = generation_config.update(**kwargs)
    bos_token_id, eos_token_id = (  # noqa: F841  # pylint: disable=W0612
        generation_config.bos_token_id,
        generation_config.eos_token_id,
    )
    if isinstance(eos_token_id, int):
        eos_token_id = [eos_token_id]
    if additional_eos_token_id is not None:
        eos_token_id.append(additional_eos_token_id)
    has_default_max_length = kwargs.get("max_length") is None and generation_config.max_length is not None
    if has_default_max_length and generation_config.max_new_tokens is None:
        warnings.warn(
            f"Using `max_length`'s default ({generation_config.max_length}) to control the generation length. "
            "This behaviour is deprecated and will be removed from the config in v5 of Transformers -- we"
            " recommend using `max_new_tokens` to control the maximum length of the generation.",
            UserWarning,
        )
    elif generation_config.max_new_tokens is not None:
        generation_config.max_length = generation_config.max_new_tokens + input_ids_seq_length
        if not has_default_max_length:
            logger.warn(  # pylint: disable=W4902
                f"Both `max_new_tokens` (={generation_config.max_new_tokens}) and `max_length`(="
                f"{generation_config.max_length}) seem to have been set. `max_new_tokens` will take precedence. "
                "Please refer to the documentation for more information. "
                "(https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)",
                UserWarning,
            )

    if input_ids_seq_length >= generation_config.max_length:
        input_ids_string = "input_ids"
        logger.warning(
            f"Input length of {input_ids_string} is {input_ids_seq_length}, but `max_length` is set to"
            f" {generation_config.max_length}. This can lead to unexpected behavior. You should consider"
            " increasing `max_new_tokens`."
        )

    # 2. Set generation parameters if not already defined
    logits_processor = logits_processor if logits_processor is not None else LogitsProcessorList()
    stopping_criteria = stopping_criteria if stopping_criteria is not None else StoppingCriteriaList()

    logits_processor = model._get_logits_processor(
        generation_config=generation_config,
        input_ids_seq_length=input_ids_seq_length,
        encoder_input_ids=input_ids,
        prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
        logits_processor=logits_processor,
    )

    stopping_criteria = model._get_stopping_criteria(
        generation_config=generation_config, stopping_criteria=stopping_criteria
    )
    logits_warper = model._get_logits_warper(generation_config)

    unfinished_sequences = input_ids.new(input_ids.shape[0]).fill_(1)
    scores = None
    while True:
        model_inputs = model.prepare_inputs_for_generation(input_ids, **model_kwargs)
        # forward pass to get next token
        outputs = model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -1, :]

        # pre-process distribution
        next_token_scores = logits_processor(input_ids, next_token_logits)
        next_token_scores = logits_warper(input_ids, next_token_scores)

        # sample
        probs = nn.functional.softmax(next_token_scores, dim=-1)
        if generation_config.do_sample:
            next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
        else:
            next_tokens = torch.argmax(probs, dim=-1)

        # update generated ids, model inputs, and length for next step
        input_ids = torch.cat([input_ids, next_tokens[:, None]], dim=-1)
        model_kwargs = model._update_model_kwargs_for_generation(outputs, model_kwargs, is_encoder_decoder=False)
        unfinished_sequences = unfinished_sequences.mul((min(next_tokens != i for i in eos_token_id)).long())

        output_token_ids = input_ids[0].cpu().tolist()
        output_token_ids = output_token_ids[input_length:]
        for each_eos_token_id in eos_token_id:
            if output_token_ids[-1] == each_eos_token_id:
                output_token_ids = output_token_ids[:-1]
        response = tokenizer.decode(output_token_ids)

        yield response
        # stop when each sentence is finished, or if we exceed the maximum length
        if unfinished_sequences.max() == 0 or stopping_criteria(input_ids, scores):
            break


def on_btn_click():
    del st.session_state.messages


@st.cache_resource
def load_model():
    model = (
        AutoModelForCausalLM.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
        .to(torch.bfloat16)
        .cuda()
    )
    tokenizer = AutoTokenizer.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
    return model, tokenizer


def prepare_generation_config():
    with st.sidebar:
        kb_options = list(vector_db_presets.keys())
        default_index = kb_options.index(default_vector_db_key) if default_vector_db_key in kb_options else 0
        selected_kb = st.selectbox("知识库选择", kb_options, index=default_index, key="kb_select")
        st.caption(f"当前路径：{vector_db_presets[selected_kb]}")
        max_length = st.slider("Max Length", min_value=8, max_value=32768, value=32768)
        top_p = st.slider("Top P", 0.0, 1.0, 0.8, step=0.01)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, step=0.01)
        st.button("Clear Chat History", on_click=on_btn_click)

    generation_config = GenerationConfig(max_length=max_length, top_p=top_p, temperature=temperature)

    return generation_config, selected_kb


user_prompt = "<|im_start|>user\n{user}<|im_end|>\n"
robot_prompt = "<|im_start|>assistant\n{robot}<|im_end|>\n"
cur_query_prompt = "<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


def combine_history(prompt, retrieval_content=''):
    messages = st.session_state.messages
    prompt = f"你需要根据以下从书本中检索到的专业知识:`{retrieval_content}`。从一个心理专家的专业角度来回答后续提问：{prompt}"
    meta_instruction = (
        "你是一个由aJupyter、Farewell、jujimeizuo、Smiling&Weeping研发（排名按字母顺序排序，不分先后）、散步提供技术支持、上海人工智能实验室提供支持开发的心理健康大模型。现在你是一个心理专家，我有一些心理问题，请你用专业的知识帮我解决。"
    )
    total_prompt = f"<s><|im_start|>system\n{meta_instruction}<|im_end|>\n"
    for message in messages:
        cur_content = message["content"]
        if message["role"] == "user":
            cur_prompt = user_prompt.format(user=cur_content)
        elif message["role"] == "robot":
            cur_prompt = robot_prompt.format(robot=cur_content)
        else:
            raise RuntimeError
        total_prompt += cur_prompt
    total_prompt = total_prompt + cur_query_prompt.format(user=prompt)
    return total_prompt


def main():
    # torch.cuda.empty_cache()
    print("load model begin.")
    model, tokenizer = load_model()
    print("load model end.")

    user_avator = "assets/user.png"
    robot_avator = "assets/robot.jpeg"

    st.title("EmoLLM")

    generation_config, selected_kb = prepare_generation_config()

    if st.session_state.get("selected_kb") != selected_kb:
        st.session_state["selected_kb"] = selected_kb
        st.session_state["messages"] = []
        # 清空缓存的 RAG 实例，避免占用显存
        st.session_state.setdefault("rag_instances", {}).pop(selected_kb, None)

    rag_obj = get_rag_instance(model, selected_kb)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        retrieval_content = rag_obj.get_retrieval_content(prompt)
        with st.chat_message("user", avatar=user_avator):
            st.markdown(prompt)
            #st.markdown(retrieval_content)

        real_prompt = combine_history(prompt, retrieval_content)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": user_avator})

        with st.chat_message("robot", avatar=robot_avator):
            message_placeholder = st.empty()
            for cur_response in generate_interactive(
                model=model,
                tokenizer=tokenizer,
                prompt=real_prompt,
                additional_eos_token_id=92542,
                **asdict(generation_config),
            ):
                # Display robot response in chat message container
                message_placeholder.markdown(cur_response + "▌")
            message_placeholder.markdown(cur_response)  # pylint: disable=undefined-loop-variable
        # Add robot response to chat history
        st.session_state.messages.append(
            {
                "role": "robot",
                "content": cur_response,  # pylint: disable=undefined-loop-variable
                "avatar": robot_avator,
            }
        )
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
```

```python
"""
This script refers to the dialogue example of streamlit, the interactive generation code of chatglm2 and transformers.
We mainly modified part of the code logic to adapt to the generation of our model.
Please refer to these links below for more information:
    1. streamlit chat example: https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
    2. chatglm2: https://github.com/THUDM/ChatGLM2-6B
    3. transformers: https://github.com/huggingface/transformers
Please run with the command `streamlit run path/to/web_demo.py --server.address=0.0.0.0 --server.port 7860`.
Using `python path/to/web_demo.py` may cause unknown problems.
"""
import copy
import os
import warnings
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

import streamlit as st
import torch
from torch import nn
from transformers.generation.utils import LogitsProcessorList, StoppingCriteriaList
from transformers.utils import logging

from transformers import AutoTokenizer, AutoModelForCausalLM  # isort: skip
from openxlab.model import download

from rag.src.pipeline import EmoLLMRAG
from rag.src.config.config import default_vector_db_key, vector_db_presets

logger = logging.get_logger(__name__)

if not os.path.isdir("model"):
    print("[ERROR] not find model dir")
    exit(0)

@dataclass
class GenerationConfig:
    # this config is used for chat to provide more diversity
    max_length: int = 32768
    top_p: float = 0.8
    temperature: float = 0.8
    do_sample: bool = True
    repetition_penalty: float = 1.005


@torch.inference_mode()
def generate_interactive(
    model,
    tokenizer,
    prompt,
    generation_config: Optional[GenerationConfig] = None,
    logits_processor: Optional[LogitsProcessorList] = None,
    stopping_criteria: Optional[StoppingCriteriaList] = None,
    prefix_allowed_tokens_fn: Optional[Callable[[int, torch.Tensor], List[int]]] = None,
    additional_eos_token_id: Optional[int] = None,
    **kwargs,
):
    inputs = tokenizer([prompt], padding=True, return_tensors="pt")
    input_length = len(inputs["input_ids"][0])
    for k, v in inputs.items():
        inputs[k] = v.cuda()
    input_ids = inputs["input_ids"]
    batch_size, input_ids_seq_length = input_ids.shape[0], input_ids.shape[-1]  # noqa: F841  # pylint: disable=W0612
    if generation_config is None:
        generation_config = model.generation_config
    generation_config = copy.deepcopy(generation_config)
    model_kwargs = generation_config.update(**kwargs)
    bos_token_id, eos_token_id = (  # noqa: F841  # pylint: disable=W0612
        generation_config.bos_token_id,
        generation_config.eos_token_id,
    )
    if isinstance(eos_token_id, int):
        eos_token_id = [eos_token_id]
    if additional_eos_token_id is not None:
        eos_token_id.append(additional_eos_token_id)
    has_default_max_length = kwargs.get("max_length") is None and generation_config.max_length is not None
    if has_default_max_length and generation_config.max_new_tokens is None:
        warnings.warn(
            f"Using `max_length`'s default ({generation_config.max_length}) to control the generation length. "
            "This behaviour is deprecated and will be removed from the config in v5 of Transformers -- we"
            " recommend using `max_new_tokens` to control the maximum length of the generation.",
            UserWarning,
        )
    elif generation_config.max_new_tokens is not None:
        generation_config.max_length = generation_config.max_new_tokens + input_ids_seq_length
        if not has_default_max_length:
            logger.warn(  # pylint: disable=W4902
                f"Both `max_new_tokens` (={generation_config.max_new_tokens}) and `max_length`(="
                f"{generation_config.max_length}) seem to have been set. `max_new_tokens` will take precedence. "
                "Please refer to the documentation for more information. "
                "(https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)",
                UserWarning,
            )

    if input_ids_seq_length >= generation_config.max_length:
        input_ids_string = "input_ids"
        logger.warning(
            f"Input length of {input_ids_string} is {input_ids_seq_length}, but `max_length` is set to"
            f" {generation_config.max_length}. This can lead to unexpected behavior. You should consider"
            " increasing `max_new_tokens`."
        )

    # 2. Set generation parameters if not already defined
    logits_processor = logits_processor if logits_processor is not None else LogitsProcessorList()
    stopping_criteria = stopping_criteria if stopping_criteria is not None else StoppingCriteriaList()

    logits_processor = model._get_logits_processor(
        generation_config=generation_config,
        input_ids_seq_length=input_ids_seq_length,
        encoder_input_ids=input_ids,
        prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
        logits_processor=logits_processor,
    )

    stopping_criteria = model._get_stopping_criteria(
        generation_config=generation_config, stopping_criteria=stopping_criteria
    )
    logits_warper = model._get_logits_warper(generation_config)

    unfinished_sequences = input_ids.new(input_ids.shape[0]).fill_(1)
    scores = None
    while True:
        model_inputs = model.prepare_inputs_for_generation(input_ids, **model_kwargs)
        # forward pass to get next token
        outputs = model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -1, :]

        # pre-process distribution
        next_token_scores = logits_processor(input_ids, next_token_logits)
        next_token_scores = logits_warper(input_ids, next_token_scores)

        # sample
        probs = nn.functional.softmax(next_token_scores, dim=-1)
        if generation_config.do_sample:
            next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
        else:
            next_tokens = torch.argmax(probs, dim=-1)

        # update generated ids, model inputs, and length for next step
        input_ids = torch.cat([input_ids, next_tokens[:, None]], dim=-1)
        model_kwargs = model._update_model_kwargs_for_generation(outputs, model_kwargs, is_encoder_decoder=False)
        unfinished_sequences = unfinished_sequences.mul((min(next_tokens != i for i in eos_token_id)).long())

        output_token_ids = input_ids[0].cpu().tolist()
        output_token_ids = output_token_ids[input_length:]
        for each_eos_token_id in eos_token_id:
            if output_token_ids[-1] == each_eos_token_id:
                output_token_ids = output_token_ids[:-1]
        response = tokenizer.decode(output_token_ids)

        yield response
        # stop when each sentence is finished, or if we exceed the maximum length
        if unfinished_sequences.max() == 0 or stopping_criteria(input_ids, scores):
            break


def on_btn_click():
    del st.session_state.messages


@st.cache_resource
def load_model():
    model = (
        AutoModelForCausalLM.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
        .to(torch.bfloat16)
        .cuda()
    )
    tokenizer = AutoTokenizer.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
    return model, tokenizer


def prepare_generation_config():
    with st.sidebar:
        kb_options = list(vector_db_presets.keys())
        default_index = kb_options.index(default_vector_db_key) if default_vector_db_key in kb_options else 0
        selected_kb = st.selectbox("知识库选择", kb_options, index=default_index, key="kb_select")
        st.caption(f"当前路径：{vector_db_presets[selected_kb]}")
        max_length = st.slider("Max Length", min_value=8, max_value=32768, value=32768)
        top_p = st.slider("Top P", 0.0, 1.0, 0.8, step=0.01)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, step=0.01)
        st.button("Clear Chat History", on_click=on_btn_click)

    generation_config = GenerationConfig(max_length=max_length, top_p=top_p, temperature=temperature)

    return generation_config, selected_kb


user_prompt = "<|im_start|>user\n{user}<|im_end|>\n"
robot_prompt = "<|im_start|>assistant\n{robot}<|im_end|>\n"
cur_query_prompt = "<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


def combine_history(prompt, retrieval_content=''):
    messages = st.session_state.messages
    prompt = f"你需要根据以下从书本中检索到的专业知识:`{retrieval_content}`。从一个心理专家的专业角度来回答后续提问：{prompt}"
    meta_instruction = (
        "你是一个由aJupyter、Farewell、jujimeizuo、Smiling&Weeping研发（排名按字母顺序排序，不分先后）、散步提供技术支持、上海人工智能实验室提供支持开发的心理健康大模型。现在你是一个心理专家，我有一些心理问题，请你用专业的知识帮我解决。"
    )
    total_prompt = f"<s><|im_start|>system\n{meta_instruction}<|im_end|>\n"
    for message in messages:
        cur_content = message["content"]
        if message["role"] == "user":
            cur_prompt = user_prompt.format(user=cur_content)
        elif message["role"] == "robot":
            cur_prompt = robot_prompt.format(robot=cur_content)
        else:
            raise RuntimeError
        total_prompt += cur_prompt
    total_prompt = total_prompt + cur_query_prompt.format(user=prompt)
    return total_prompt


def main():
    # torch.cuda.empty_cache()
    print("load model begin.")
    model, tokenizer = load_model()
    print("load model end.")

    user_avator = "assets/user.png"
    robot_avator = "assets/robot.jpeg"

    st.title("EmoLLM")

    generation_config, selected_kb = prepare_generation_config()
    st.session_state["selected_kb"] = selected_kb
    rag_obj = get_rag_instance(model, selected_kb)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        retrieval_content = rag_obj.get_retrieval_content(prompt)
        with st.chat_message("user", avatar=user_avator):
            st.markdown(prompt)
            #st.markdown(retrieval_content)

        real_prompt = combine_history(prompt, retrieval_content)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": user_avator})

        with st.chat_message("robot", avatar=robot_avator):
            message_placeholder = st.empty()
            for cur_response in generate_interactive(
                model=model,
                tokenizer=tokenizer,
                prompt=real_prompt,
                additional_eos_token_id=92542,
                **asdict(generation_config),
            ):
                # Display robot response in chat message container
                message_placeholder.markdown(cur_response + "▌")
            message_placeholder.markdown(cur_response)  # pylint: disable=undefined-loop-variable
        # Add robot response to chat history
        st.session_state.messages.append(
            {
                "role": "robot",
                "content": cur_response,  # pylint: disable=undefined-loop-variable
                "avatar": robot_avator,
            }
        )
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
```

```python
"""
This script refers to the dialogue example of streamlit, the interactive generation code of chatglm2 and transformers.
We mainly modified part of the code logic to adapt to the generation of our model.
Please refer to these links below for more information:
    1. streamlit chat example: https://docs.streamlit.io/knowledge-base/tutorials/build-conversational-apps
    2. chatglm2: https://github.com/THUDM/ChatGLM2-6B
    3. transformers: https://github.com/huggingface/transformers
Please run with the command `streamlit run path/to/web_demo.py --server.address=0.0.0.0 --server.port 7860`.
Using `python path/to/web_demo.py` may cause unknown problems.
"""
import copy
import os
import warnings
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

import streamlit as st
import torch
from torch import nn
from transformers.generation.utils import LogitsProcessorList, StoppingCriteriaList
from transformers.utils import logging

from transformers import AutoTokenizer, AutoModelForCausalLM  # isort: skip
from openxlab.model import download

from rag.src.pipeline import EmoLLMRAG
from rag.src.config.config import default_vector_db_key, vector_db_presets

logger = logging.get_logger(__name__)

if not os.path.isdir("model"):
    print("[ERROR] not find model dir")
    exit(0)

@dataclass
class GenerationConfig:
    # this config is used for chat to provide more diversity
    max_length: int = 32768
    top_p: float = 0.8
    temperature: float = 0.8
    do_sample: bool = True
    repetition_penalty: float = 1.005


@torch.inference_mode()
def generate_interactive(
    model,
    tokenizer,
    prompt,
    generation_config: Optional[GenerationConfig] = None,
    logits_processor: Optional[LogitsProcessorList] = None,
    stopping_criteria: Optional[StoppingCriteriaList] = None,
    prefix_allowed_tokens_fn: Optional[Callable[[int, torch.Tensor], List[int]]] = None,
    additional_eos_token_id: Optional[int] = None,
    **kwargs,
):
    inputs = tokenizer([prompt], padding=True, return_tensors="pt")
    input_length = len(inputs["input_ids"][0])
    for k, v in inputs.items():
        inputs[k] = v.cuda()
    input_ids = inputs["input_ids"]
    batch_size, input_ids_seq_length = input_ids.shape[0], input_ids.shape[-1]  # noqa: F841  # pylint: disable=W0612
    if generation_config is None:
        generation_config = model.generation_config
    generation_config = copy.deepcopy(generation_config)
    model_kwargs = generation_config.update(**kwargs)
    bos_token_id, eos_token_id = (  # noqa: F841  # pylint: disable=W0612
        generation_config.bos_token_id,
        generation_config.eos_token_id,
    )
    if isinstance(eos_token_id, int):
        eos_token_id = [eos_token_id]
    if additional_eos_token_id is not None:
        eos_token_id.append(additional_eos_token_id)
    has_default_max_length = kwargs.get("max_length") is None and generation_config.max_length is not None
    if has_default_max_length and generation_config.max_new_tokens is None:
        warnings.warn(
            f"Using `max_length`'s default ({generation_config.max_length}) to control the generation length. "
            "This behaviour is deprecated and will be removed from the config in v5 of Transformers -- we"
            " recommend using `max_new_tokens` to control the maximum length of the generation.",
            UserWarning,
        )
    elif generation_config.max_new_tokens is not None:
        generation_config.max_length = generation_config.max_new_tokens + input_ids_seq_length
        if not has_default_max_length:
            logger.warn(  # pylint: disable=W4902
                f"Both `max_new_tokens` (={generation_config.max_new_tokens}) and `max_length`(="
                f"{generation_config.max_length}) seem to have been set. `max_new_tokens` will take precedence. "
                "Please refer to the documentation for more information. "
                "(https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)",
                UserWarning,
            )

    if input_ids_seq_length >= generation_config.max_length:
        input_ids_string = "input_ids"
        logger.warning(
            f"Input length of {input_ids_string} is {input_ids_seq_length}, but `max_length` is set to"
            f" {generation_config.max_length}. This can lead to unexpected behavior. You should consider"
            " increasing `max_new_tokens`."
        )

    # 2. Set generation parameters if not already defined
    logits_processor = logits_processor if logits_processor is not None else LogitsProcessorList()
    stopping_criteria = stopping_criteria if stopping_criteria is not None else StoppingCriteriaList()

    logits_processor = model._get_logits_processor(
        generation_config=generation_config,
        input_ids_seq_length=input_ids_seq_length,
        encoder_input_ids=input_ids,
        prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
        logits_processor=logits_processor,
    )

    stopping_criteria = model._get_stopping_criteria(
        generation_config=generation_config, stopping_criteria=stopping_criteria
    )
    logits_warper = model._get_logits_warper(generation_config)

    unfinished_sequences = input_ids.new(input_ids.shape[0]).fill_(1)
    scores = None
    while True:
        model_inputs = model.prepare_inputs_for_generation(input_ids, **model_kwargs)
        # forward pass to get next token
        outputs = model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -1, :]

        # pre-process distribution
        next_token_scores = logits_processor(input_ids, next_token_logits)
        next_token_scores = logits_warper(input_ids, next_token_scores)

        # sample
        probs = nn.functional.softmax(next_token_scores, dim=-1)
        if generation_config.do_sample:
            next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
        else:
            next_tokens = torch.argmax(probs, dim=-1)

        # update generated ids, model inputs, and length for next step
        input_ids = torch.cat([input_ids, next_tokens[:, None]], dim=-1)
        model_kwargs = model._update_model_kwargs_for_generation(outputs, model_kwargs, is_encoder_decoder=False)
        unfinished_sequences = unfinished_sequences.mul((min(next_tokens != i for i in eos_token_id)).long())

        output_token_ids = input_ids[0].cpu().tolist()
        output_token_ids = output_token_ids[input_length:]
        for each_eos_token_id in eos_token_id:
            if output_token_ids[-1] == each_eos_token_id:
                output_token_ids = output_token_ids[:-1]
        response = tokenizer.decode(output_token_ids)

        yield response
        # stop when each sentence is finished, or if we exceed the maximum length
        if unfinished_sequences.max() == 0 or stopping_criteria(input_ids, scores):
            break


def on_btn_click():
    del st.session_state.messages


@st.cache_resource
def load_model():
    model = (
        AutoModelForCausalLM.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
        .to(torch.bfloat16)
        .cuda()
    )
    tokenizer = AutoTokenizer.from_pretrained("model/EmoLLM_Qwen2-7B-Instruct_lora", trust_remote_code=True)
    return model, tokenizer


def prepare_generation_config():
    with st.sidebar:
        kb_options = list(vector_db_presets.keys())
        default_index = kb_options.index(default_vector_db_key) if default_vector_db_key in kb_options else 0
        selected_kb = st.selectbox("知识库选择", kb_options, index=default_index, key="kb_select")
        st.caption(f"当前路径：{vector_db_presets[selected_kb]}")
        max_length = st.slider("Max Length", min_value=8, max_value=32768, value=32768)
        top_p = st.slider("Top P", 0.0, 1.0, 0.8, step=0.01)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, step=0.01)
        st.button("Clear Chat History", on_click=on_btn_click)

    generation_config = GenerationConfig(max_length=max_length, top_p=top_p, temperature=temperature)

    return generation_config, selected_kb


user_prompt = "<|im_start|>user\n{user}<|im_end|>\n"
robot_prompt = "<|im_start|>assistant\n{robot}<|im_end|>\n"
cur_query_prompt = "<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"


def combine_history(prompt, retrieval_content=''):
    messages = st.session_state.messages
    prompt = f"你需要根据以下从书本中检索到的专业知识:`{retrieval_content}`。从一个心理专家的专业角度来回答后续提问：{prompt}"
    meta_instruction = (
        "你是一个由aJupyter、Farewell、jujimeizuo、Smiling&Weeping研发（排名按字母顺序排序，不分先后）、散步提供技术支持、上海人工智能实验室提供支持开发的心理健康大模型。现在你是一个心理专家，我有一些心理问题，请你用专业的知识帮我解决。"
    )
    total_prompt = f"<s><|im_start|>system\n{meta_instruction}<|im_end|>\n"
    for message in messages:
        cur_content = message["content"]
        if message["role"] == "user":
            cur_prompt = user_prompt.format(user=cur_content)
        elif message["role"] == "robot":
            cur_prompt = robot_prompt.format(robot=cur_content)
        else:
            raise RuntimeError
        total_prompt += cur_prompt
    total_prompt = total_prompt + cur_query_prompt.format(user=prompt)
    return total_prompt


def get_rag_instance(model, selected_kb: str):
    rag_cache = st.session_state.setdefault("rag_instances", {})
    if selected_kb not in rag_cache:
        target_path = vector_db_presets[selected_kb]
        with st.spinner(f"正在加载知识库：{selected_kb}"):
            try:
                rag_cache[selected_kb] = EmoLLMRAG(model, vector_db_path=target_path)
            except Exception as exc:  # pylint: disable=broad-except
                st.error(f"加载知识库 {selected_kb} 失败：{exc}")
                raise
    return rag_cache[selected_kb]


def main():
    # torch.cuda.empty_cache()
    print("load model begin.")
    model, tokenizer = load_model()
    print("load model end.")

    user_avator = "assets/user.png"
    robot_avator = "assets/robot.jpeg"

    st.title("EmoLLM")

    generation_config, selected_kb = prepare_generation_config()
    st.session_state["selected_kb"] = selected_kb
    rag_obj = get_rag_instance(model, selected_kb)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Display user message in chat message container
        retrieval_content = rag_obj.get_retrieval_content(prompt)
        with st.chat_message("user", avatar=user_avator):
            st.markdown(prompt)
            #st.markdown(retrieval_content)

        real_prompt = combine_history(prompt, retrieval_content)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": user_avator})

        with st.chat_message("robot", avatar=robot_avator):
            message_placeholder = st.empty()
            for cur_response in generate_interactive(
                model=model,
                tokenizer=tokenizer,
                prompt=real_prompt,
                additional_eos_token_id=92542,
                **asdict(generation_config),
            ):
                # Display robot response in chat message container
                message_placeholder.markdown(cur_response + "▌")
            message_placeholder.markdown(cur_response)  # pylint: disable=undefined-loop-variable
        # Add robot response to chat history
        st.session_state.messages.append(
            {
                "role": "robot",
                "content": cur_response,  # pylint: disable=undefined-loop-variable
                "avatar": robot_avator,
            }
        )
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
```

## 结果概览
- 在 `rag/src/config/config.py` 中新增 `knowledge_base_roots / vector_db_presets / default_vector_db_key`，统一管理官方、方案一、方案二及合并库的路径，仍保留原先的默认加载逻辑。
- `rag/src/data_processing.py` 的 `create_vector_db` 与 `load_vector_db` 支持可选 `vector_db_path`，可按需加载/写入不同目录。
- `rag/src/pipeline.py` 允许在初始化 `EmoLLMRAG` 时传入 `vector_db_path`，RAG 管线可以绑定特定知识库。
- `web_internlm2.py` 侧边栏新增“知识库选择”下拉框（官方/合并/方案一/方案二），根据选择动态实例化对应的 RAG；同时在加载时展示路径并使用 `st.spinner` 提示，避免用户误会。聊天历史仍保留，可随时切换知识库。

## 使用方式
- 启动界面：`streamlit run web_internlm2.py --server.address=0.0.0.0 --server.port 7860`
- 左侧下拉框可选：
  - `EmoLLMRAGTXT`（仅官方）
  - `merged_depression_kb`（合并库）
  - `my_depression_kb`（方案一）
  - `myDD_knowledge_txt`（方案二 txt-only）
- 选择后会自动加载对应 `vector_db`；若目录不存在，会在界面提示错误。可继续使用已有清空按钮重置对话。

## 后续建议
- 切换到尚未构建的库前，确认相应 `vector_db` 已生成；否则 `load_vector_db` 会尝试重新构建，可能耗时。
- 若希望默认使用其他知识库，可在 `default_vector_db_key` 中修改默认键值。
- 完整测试路径：构建完各方案的向量库 → `streamlit` 启动 → 逐个选择下拉项验证检索结果。

---

**User**

如果我这样改完，会不会影响其他demo的使用。我不想改完后只有web_internlm2.py能使用，因为我看你改了data_processing.py和pipeline.py这种公共文件

---

**Cursor**

不会影响其他 demo：

- `data_processing.py` 和 `pipeline.py` 只是新增**可选参数**。默认情况下仍使用 `config.py` 里的 `default_vector_db_key`（也就是原来的 `vector_db_dir`），其他脚本如果没传 `vector_db_path`，行为与修改前完全一致。
- `config.py` 里依然定义了 `vector_db_dir = vector_db_presets[default_vector_db_key]`，因此老代码直接引用 `vector_db_dir` 也不会出错。新增的 `vector_db_presets` 只是额外提供选项给 Web 端 UI。
- `build_my_knowledge_base.py`、`merge_vector_db.py` 等独立脚本若要使用自己的路径，仍然可以按原流程操作；它们不依赖新的 Streamlit 控件。
- 如果还有别的 Demo/脚本，需要特定知识库路径，只要和之前一样修改 `cloud_vector_db_dir` 或直接 override `vector_db_dir` 即可。

因此，这些改动只是“向下兼容扩展”，不会导致只有 `web_internlm2.py` 可用。只要其他 Demo 没显式传入新的参数，它们还是按原配置工作。

---

**User**

(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ streamlit run web_internlm2.py --server.address=0.0.0.0 --server.port 7860

  You can now view your Streamlit app in your browser.

  URL: http://0.0.0.0:7860

gio: http://0.0.0.0:7860: Operation not supported
load model begin.
Loading checkpoint shards: 100%|███████████████████| 9/9 [00:09<00:00,  1.01s/it]
Special tokens have been added in the vocabulary, make sure the associated word embeddings are fine-tuned or trained.
load model end.
2025-11-14 15:43:39.039 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 15:43:39.212 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
2025-11-14 15:43:40.309 Examining the path of torch.classes raised: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
load model begin.
load model end.
2025-11-14 15:44:30.122 Examining the path of torch.classes raised: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
load model begin.
load model end.
load model begin.
load model end.
2025-11-14 15:45:28.285 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 15:45:28.440 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model begin.
load model end.
load model begin.
load model end.
load model begin.
load model end.
2025-11-14 15:46:40.296 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 15:46:40.411 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model begin.
load model end.
load model begin.
load model end.
load model begin.
load model end.
load model begin.
load model end.
load model begin.
load model end.
load model begin.
load model end.
2025-11-14 15:49:06.549 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 15:49:06.681 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model begin.
load model end.
修改完后，我只有在切换知识库的时候才会有INFO的提示，发消息没有这个提示，但我在没加知识库切换功能的时候运行日志如下：
(emo311) xhq@DESKTOP-EQO3GHE:~/EmoLLM$ streamlit run web_internlm2.py --server.address=0.0.0.0 --server.port 7860

  You can now view your Streamlit app in your browser.

  URL: http://0.0.0.0:7860

gio: http://0.0.0.0:7860: Operation not supported
load model begin.
load model begin.
Loading checkpoint shards: 100%|███████████████████| 9/9 [00:08<00:00,  1.02it/s]Special tokens have been added in the vocabulary, make sure the associated word embeddings are fine-tuned or trained.
2025-11-14 13:48:29.717 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:48:29.896 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
2025-11-14 13:48:32.609 Examining the path of torch.classes raised: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
load model begin.
2025-11-14 13:48:49.958 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:48:50.067 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
2025-11-14 13:49:01.995 Examining the path of torch.classes raised: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
load model begin.
2025-11-14 13:49:15.033 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:49:15.137 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
load model begin.
2025-11-14 13:49:41.592 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:49:41.675 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
load model begin.
2025-11-14 13:50:13.527 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:50:13.615 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
load model begin.
2025-11-14 13:50:31.044 | INFO     | rag.src.data_processing:load_embedding_model:54 - Loading embedding model...
2025-11-14 13:50:31.119 | INFO     | rag.src.data_processing:load_embedding_model:59 - Embedding model loaded.
load model end.
可以看到每发一条消息就有一个两个INFO，为什么会有这种区别，有什么潜在影响，是原来的更好还是现在没有INFO更好

---

**Cursor**

这两个日志差异源于我们在新版里做了 RAG 实例缓存：每个知识库只在**第一次切换**时构建 `EmoLLMRAG`，同时调用 `Data_process.load_embedding_model()`；之后发送消息时复用同一个实例，不再反复加载 embedding 模型，所以看不到那两条 INFO。之前的实现每次调用都会重新初始化 RAG，因此每条消息都会触发“Loading embedding model…”。因此：

- 现在的行为更高效，避免了重复 IO/显存开销，减轻延迟，对功能没有负面影响。
- 如果你反而想保留旧日志（每次请求重建），需要取消缓存，但这会让每条消息都重新加载向量库，性能下降。

总结：少了 INFO 只是因为资源被复用，不代表流程没跑；从性能角度看，新行为反而更好。

---

**User**

每条消息都重新加载向量库不是说明它每次回复用户都会去知识库中检索，这样回复更准确呀，现在不会反复加载embedding 模型是不是说明不是每条消息都去查看知识库再回答，这样不就会导致回复的内容没有可信度吗

---

**Cursor**

不会。少了 embedding 日志 ≠ 不检索，它只是表明我们复用了已加载的向量库和嵌入模型。

具体流程：
- `load_embedding_model()` 只负责把 embedding 模型权重从磁盘读到内存；这是耗时操作，没必要每条消息重复。
- 真正的检索发生在 `EmoLLMRAG.get_retrieval_content()`，它对 **每个用户问题** 都调用 `vectorstores.similarity_search()`；这个调用仍然访问 FAISS 索引，从知识库里取文档。
- 因为向量库和嵌入模型已经常驻内存，后续检索只是查询操作，速度更快，也同样可靠。

所以现在的实现依旧“每问一遍→到知识库检索→再回答”。只是把“加载模型/索引”这一步从“每条消息一次”优化成“首次切换知识库时一次”，不影响检索准确度，反而减少了不必要的开销。

---

**User**

确定不会有任何坏的影响对吗？

---

**Cursor**

是的，这种缓存只带来好处，不会让检索或回答变差。向量库与嵌入模型都是“加载一次、反复查询”的典型场景：加载阶段耗时且占资源，但查询阶段仍然逐条访问知识库。我们只是避免了重复加载，实际检索次数、内容与之前完全相同，因此不存在准确度或可信度降低。唯一需要注意的是：如果你在后台更新了向量库文件，想让页面重新加载新的索引，可以手动在下拉框里切换一次（或重启服务），以刷新缓存。除此之外没有负面影响。

---

**User**

我想问一下，我先使用A知识库问一个问题，然后模型会给我回答，这时候我不清空会话历史，切换到知识库B，再问同样的问题，模型是检索知识库B再加上之前的会话历史综合回答还是说只根据知识库B的检索内容，读取不了历史，这个模型有读取历史的记忆功能吗？

---

**Cursor**

- 模型在生成回复时会把 **当前会话历史**（所有之前的问答文本）拼进 prompt，所以它确实“记得”你刚刚和它说过什么，即便切换了知识库也不会自动清空。
- 但 **检索内容始终来自当前下拉框选中的知识库**：你切换到 B 之后，再问同样的问题，`rag_obj` 会只在知识库 B 里做向量检索，把检索到的内容和历史对话一起喂给大模型。
- 也就是说：答案 = “历史对话 + 当前知识库 B 的检索结果”共同作用；不会去查 A 的向量库，但历史中可能还提到之前 A 的信息，所以模型可能引用旧上下文。
- 如果希望切换知识库后完全独立的对话，建议切换后点一次 “Clear Chat History”，否则旧对话语境仍会影响回复。

---

**User**

所以我要想测试切换知识库是否有效，需要每次对话都点击Clear Chat History对吗？

---

**Cursor**

是的，想要独立评估不同知识库的效果，建议在每次切换后点击一次 “Clear Chat History”。这样可以保证新对话只受当前知识库检索结果影响，不被之前的上下文干扰。如果只是正常使用、不做对比，也可以保留历史以维持对话连贯性。

