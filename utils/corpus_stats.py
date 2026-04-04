"""
utils/corpus_stats.py — 語料統計（生成論文表一）
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger(__name__)


def count_chars_from_cache(cache_dir: Path, work_id: str) -> Optional[int]:
    cache_file = cache_dir / f"{work_id}_corpus.json"
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        juans = data.get("juans", {})
        total = sum(len(text) for text in juans.values()
                    if isinstance(text, str) and len(text) > 50)
        return total if total > 0 else None
    except Exception:
        return None


def print_table1(corpus_def, cache_dir: Path):
    print(f"\n表一　研究語料一覽（{corpus_def.name_zh}）\n")
    print(f"{'文本':<20} {'編號':<8} {'卷數':>4} {'定義字數':>10} {'快取字數':>10} {'一致':>4}")
    print("-" * 70)
    for wid, t in corpus_def.texts.items():
        dc = f"{t.char_count:,}" if t.char_count else "—"
        cc_val = count_chars_from_cache(cache_dir, wid)
        cc = f"{cc_val:,}" if cc_val else "—"
        match_val = (t.char_count == cc_val) if (t.char_count and cc_val) else None
        match = "✅" if match_val else ("❌" if match_val is False else "—")
        print(f"{t.title:<18} {wid:<8} {t.juans:>4} {dc:>10} {cc:>10} {match:>4}")
    print("-" * 70)
    print()


def export_table1_markdown(corpus_def) -> str:
    lines = []
    lines.append("| 文本 | 編號 | 語料規模（字數） | 研究定位 |")
    lines.append("|------|------|-----------------|---------|")
    for wid, t in corpus_def.texts.items():
        cc = f"{t.char_count:,}" if t.char_count else "待統計"
        lines.append(f"| {t.title}（{t.title_en}） | {wid} | {cc} | {t.role} |")
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import argparse, config
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=None)
    args = parser.parse_args()
    corpus = config.load_corpus(args.corpus)
    print_table1(corpus, config.CORPUS_CACHE_DIR)
