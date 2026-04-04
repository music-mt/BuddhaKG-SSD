"""
integrate/cross_validate.py — 橫向 × 縱向交叉驗證
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)


def load_ssd_results(cluster_dir: Path, term: str) -> Optional[Dict]:
    for name in [f"{term}_clusters.json", f"cluster_{term}.json"]:
        path = cluster_dir / name
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def cross_validate_term(term, ssd_result, kg_result, confirmed_class=None) -> Dict:
    result = {"term": term, "ssd_available": ssd_result is not None,
              "kg_available": kg_result is not None, "consistency": "unknown"}
    if confirmed_class:
        result["confirmed_class"] = confirmed_class.get("class")
        result["note"] = confirmed_class.get("note", "")
    return result


def run_cross_validation(config_module, corpus_def) -> Dict:
    log.info("=== BuddhaKG-SSD 整合交叉驗證 ===")
    results = {}
    confirmed = getattr(config_module, 'CONFIRMED_CLASSIFICATIONS', {})
    for term in corpus_def.target_terms:
        log.info(f"\n── 術語：「{term}」{'─' * 30}")
        ssd = load_ssd_results(config_module.CLUSTER_DIR, term)
        conf = confirmed.get(term)
        result = cross_validate_term(term, ssd, None, conf)
        results[term] = result
        if conf:
            cls_def = config_module.TRI_CLASS_DEFINITIONS.get(conf["class"], {})
            log.info(f"  三分類：{cls_def.get('zh', conf['class'])}")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import argparse, config
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=None)
    args = parser.parse_args()
    corpus_def = config.load_corpus(args.corpus)
    results = run_cross_validation(config, corpus_def)
