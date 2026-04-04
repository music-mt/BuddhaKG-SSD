"""
kg/train_rotate.py — RotatE 訓練（包裝 BuddhaNLP train_rotate.py）

用法：
    python kg/train_rotate.py
    python kg/train_rotate.py --epochs 500 --dim 256
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

ORIGINAL = Path(r"C:\buddha\train_rotate.py")


def main():
    parser = argparse.ArgumentParser(description="RotatE 訓練")
    parser.add_argument("--epochs", type=int, default=config.ROTATE_CONFIG["epochs"])
    parser.add_argument("--dim", type=int, default=config.ROTATE_CONFIG["dim"])
    parser.add_argument("--neg-samples", type=int, default=config.ROTATE_CONFIG["neg_samples"])
    args = parser.parse_args()

    log.info(f"=== RotatE 訓練 ===")
    log.info(f"  epochs={args.epochs}, dim={args.dim}, neg_samples={args.neg_samples}")

    env = dict(os.environ)
    env["NEO4J_PASS"] = config.NEO4J_PASS

    cmd = [
        sys.executable, str(ORIGINAL),
        "--epochs", str(args.epochs),
        "--dim", str(args.dim),
        "--neg-samples", str(args.neg_samples),
    ]
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent), env=env)

    if result.returncode == 0:
        log.info("✅ 訓練完成")
    else:
        log.error("❌ 訓練失敗")


if __name__ == "__main__":
    main()
