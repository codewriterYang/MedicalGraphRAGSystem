#!/usr/bin/env python3
# coding: utf-8
"""
医药知识图谱数据爬虫 — CLI 入口

用法:
    python main.py                          # 爬取全部 1-11000
    python main.py --start 1 --end 100      # 指定范围
    python main.py --resume                  # 断点续爬
    python main.py --start 1 --end 5 --test  # 测试模式，打印不写文件
"""

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录和当前目录都在 sys.path 中
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_current_dir = str(Path(__file__).resolve().parent)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from config import OUTPUT_PATH
from spider import MedicalSpider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(description="医药知识图谱数据爬虫")
    parser.add_argument("--start", type=int, default=1, help="起始页码 (默认 1)")
    parser.add_argument("--end", type=int, default=11000, help="结束页码 (默认 11000)")
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH), help="输出文件路径")
    parser.add_argument("--resume", action="store_true", help="断点续爬")
    parser.add_argument("--delay", type=float, default=0.3, help="请求间隔秒数 (默认 0.3)")
    parser.add_argument("--test", action="store_true", help="测试模式：只打印不写文件")
    args = parser.parse_args()

    spider = MedicalSpider(
        output_path=args.output,
        start_page=args.start,
        end_page=args.end,
        delay=args.delay,
        test_mode=args.test,
    )
    spider.crawl(resume=args.resume)


if __name__ == "__main__":
    main()
