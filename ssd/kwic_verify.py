"""
ssd/kwic_verify.py — KWIC 驗證（包裝 BuddhaSSD kwic_verify.py）

用法：
    python ssd/kwic_verify.py
    python ssd/kwic_verify.py --term 習氣
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

ORIGINAL = Path(r"C:\buddhassd\kwic_verify.py")


def main():
    parser = argparse.ArgumentParser(description="KWIC 驗證")
    parser.add_argument("--term", default=None, help="指定術語")
    args = parser.parse_args()

    log.info("=== KWIC 驗證 ===")
    cmd = [sys.executable, str(ORIGINAL)]
    if args.term:
        cmd.extend(["--term", args.term])
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent))
    if result.returncode == 0:
        log.info("✅ KWIC 驗證完成")
    else:
        log.error("❌ 驗證失敗")


if __name__ == "__main__":
    main()
