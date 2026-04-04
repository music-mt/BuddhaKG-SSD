"""
ssd/cluster_analysis.py — K-means 聚類分析（包裝 BuddhaSSD cluster_usage.py）

用法：
    python ssd/cluster_analysis.py
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORIGINAL = Path(r"C:\buddhassd\cluster_usage.py")


def main():
    log.info("=== K-means 聚類分析 ===")
    cmd = [sys.executable, str(ORIGINAL)]
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent))
    if result.returncode == 0:
        log.info("✅ 聚類分析完成")
    else:
        log.error("❌ 聚類失敗")


if __name__ == "__main__":
    main()
