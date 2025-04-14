"""
Author: zihao zihao-lee@outlook.com
Date: 2025-04-14 14:15:31
LastEditors: zihao zihao-lee@outlook.com
LastEditTime: 2025-04-14 14:15:40
FilePath: \MT-HumanEval\raw2json.py
Description:

Copyright (c) 2025 by zihao, All Rights Reserved.
"""

import os
import json

root_dir = "human_eval"

for subdir in os.listdir(root_dir):
    sub_path = os.path.join(root_dir, subdir)
    if os.path.isdir(sub_path):
        src_file = os.path.join(sub_path, f"{subdir}.src")
        tgt_file = os.path.join(sub_path, f"{subdir}.tgt")
        output_file = os.path.join(sub_path, f"{subdir}.json")

        with open(src_file, "r", encoding="utf-8") as f_src, open(
            tgt_file, "r", encoding="utf-8"
        ) as f_tgt:
            src_lines = f_src.read().strip().split("\n")
            tgt_lines = f_tgt.read().strip().split("\n")

        if len(src_lines) != len(tgt_lines):
            print(
                f"Line count mismatch in {subdir}: {len(src_lines)} vs {len(tgt_lines)}"
            )
            continue

        data = [
            {"source": src, "hypothesis": tgt} for src, tgt in zip(src_lines, tgt_lines)
        ]

        with open(output_file, "w", encoding="utf-8") as f_out:
            json.dump(data, f_out, ensure_ascii=False, indent=2)

        print(f"Processed {subdir} -> {output_file}")
