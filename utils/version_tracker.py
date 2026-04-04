"""
utils/version_tracker.py — 版本追蹤與論文數據驗證
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

log = logging.getLogger(__name__)

PAPER_CLAIMS = {
    "abstract_initial_prec": 0.21,
    "abstract_final_prec": 0.74,
    "sec42_v12_mrr": 0.3712,
    "sec42_v13_mrr": 0.3284,
    "table1_T0676": 31145,
    "table1_T1579": 1053602,
    "table1_T1585": 106000,
    "table1_T1594": 31145,
}


def verify_paper_numbers(config_module) -> Tuple[bool, List[str]]:
    errors, warnings = [], []
    kge = config_module.KGE_VERSIONS

    if kge["v1.2"]["mrr"] != PAPER_CLAIMS["sec42_v12_mrr"]:
        errors.append(f"v1.2 MRR 不一致：config={kge['v1.2']['mrr']} vs 論文={PAPER_CLAIMS['sec42_v12_mrr']}")
    if kge["v1.3"]["mrr"] != PAPER_CLAIMS["sec42_v13_mrr"]:
        errors.append(f"v1.3 MRR 不一致：config={kge['v1.3']['mrr']} vs 論文={PAPER_CLAIMS['sec42_v13_mrr']}")
    if kge["v1.2"]["human_prec"] != PAPER_CLAIMS["abstract_initial_prec"]:
        errors.append(f"v1.2 人工精確率不一致")
    if kge["v1.3"]["human_prec"] != PAPER_CLAIMS["abstract_final_prec"]:
        errors.append(f"v1.3 人工精確率不一致")
    if kge["v1.1"]["human_prec"] is not None:
        warnings.append(f"⚠️  v1.1 human_prec 設為 {kge['v1.1']['human_prec']}，但未有實測記錄")

    try:
        corpus = config_module.load_corpus()
        for wid, key in [("T0676","table1_T0676"),("T1579","table1_T1579"),
                          ("T1585","table1_T1585"),("T1594","table1_T1594")]:
            if wid in corpus.texts:
                actual = corpus.texts[wid].char_count
                if actual and actual != PAPER_CLAIMS[key]:
                    errors.append(f"表一字數不一致 {wid}：{actual} vs {PAPER_CLAIMS[key]}")
    except Exception as e:
        warnings.append(f"無法載入語料集：{e}")

    return len(errors) == 0, errors + warnings


def print_verification_report(config_module):
    print("\n" + "=" * 60)
    print("  BuddhaKG-SSD 論文數據一致性驗證")
    print("=" * 60)
    is_valid, messages = verify_paper_numbers(config_module)
    if is_valid and not messages:
        print("\n  ✅ 所有數字一致\n")
    else:
        for msg in messages:
            print(f"  {'❌' if not msg.startswith('⚠️') else ''} {msg}")
    kge = config_module.KGE_VERSIONS
    print(f"\n  確認數字：")
    print(f"    v1.2 MRR = {kge['v1.2']['mrr']}  人工精確率 = {kge['v1.2']['human_prec']:.0%}")
    print(f"    v1.3 MRR = {kge['v1.3']['mrr']}  人工精確率 = {kge['v1.3']['human_prec']:.0%}")
    print(f"    系統性背離：v1.2 MRR ({kge['v1.2']['mrr']}) > v1.3 MRR ({kge['v1.3']['mrr']})")
    print(f"    但人工精確率 v1.3 ({kge['v1.3']['human_prec']:.0%}) >> v1.2 ({kge['v1.2']['human_prec']:.0%})")
    print()
    return is_valid


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import config
    print_verification_report(config)
