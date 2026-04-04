"""
ssd/build_usage.py — Usage Corpus 建構（包裝 BuddhaSSD build_usage_corpus.py）

用法：
    python ssd/build_usage.py
    python ssd/build_usage.py --corpus yogacara
    python ssd/build_usage.py --terms 阿賴耶識 種子
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORIGINAL = Path(r"C:\buddhassd\build_usage_corpus.py")


def main():
    parser = argparse.ArgumentParser(description="Usage Corpus 建構")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--terms", nargs="+", help="指定術語")
    args = parser.parse_args()

    corpus_def = config.load_corpus(args.corpus)
    terms = args.terms or corpus_def.target_terms

    log.info(f"=== Usage Corpus 建構：{corpus_def.name_zh} ===")
    log.info(f"  術語：{terms}")
    log.info(f"  SSD 文本：{corpus_def.get_ssd_work_ids()}")

    cmd = [sys.executable, str(ORIGINAL)]
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent))

    if result.returncode == 0:
        log.info("✅ Usage Corpus 建構完成")
    else:
        log.error("❌ 建構失敗")


if __name__ == "__main__":
    main()
