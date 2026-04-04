"""
kg/build_kg.py — 知識圖譜建構（包裝 BuddhaNLP build_kg.py）

用法：
    python kg/build_kg.py init
    python kg/build_kg.py build T1585 10
    python kg/build_kg.py bridge
    python kg/build_kg.py stats
    python kg/build_kg.py --corpus yogacara --build-all
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ORIGINAL = Path(r"C:\buddha\build_kg.py")


def run_original(args_list):
    """呼叫原始 build_kg.py，傳入環境變數"""
    env = dict(os.environ)
    env["NEO4J_PASS"] = config.NEO4J_PASS
    cmd = [sys.executable, str(ORIGINAL)] + args_list
    log.info(f"  執行：{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ORIGINAL.parent), env=env)
    return result.returncode == 0


def build_all(corpus_def):
    """依據語料集定義，建構全部論典的知識圖譜"""
    log.info(f"=== 建構知識圖譜：{corpus_def.name_zh} ===")

    log.info("\n[1/3] 初始化...")
    if not run_original(["init"]):
        return False

    log.info("\n[2/3] 建構各論典...")
    for i, (wid, t) in enumerate(corpus_def.texts.items()):
        log.info(f"\n  ({i+1}/{len(corpus_def.texts)}) {t.title}（{wid}）{t.juans} 卷")
        if not run_original(["build", wid, str(t.juans)]):
            log.error(f"  ❌ {wid} 建構失敗")
            return False

    log.info("\n[3/3] 建立跨論典橋接...")
    if not run_original(["bridge"]):
        return False

    log.info("\n✅ 知識圖譜建構完成")
    run_original(["stats"])
    return True


def main():
    parser = argparse.ArgumentParser(description="知識圖譜建構")
    parser.add_argument("--corpus", default=None, help="語料集名稱")
    parser.add_argument("--build-all", action="store_true", help="建構全部論典")
    parser.add_argument("cmd", nargs="*", help="直接傳給原始 build_kg.py 的指令")
    args = parser.parse_args()

    corpus_def = config.load_corpus(args.corpus)

    if args.build_all:
        build_all(corpus_def)
    elif args.cmd:
        run_original(args.cmd)
    else:
        log.info(f"語料集：{corpus_def.name_zh}")
        log.info(f"論典：{list(corpus_def.texts.keys())}")
        log.info(f"\n用法：")
        log.info(f"  python kg/build_kg.py --build-all           全部建構")
        log.info(f"  python kg/build_kg.py init                  初始化")
        log.info(f"  python kg/build_kg.py build T1585 10        單部建構")
        log.info(f"  python kg/build_kg.py bridge                跨論典橋接")
        log.info(f"  python kg/build_kg.py stats                 統計")


if __name__ == "__main__":
    main()
