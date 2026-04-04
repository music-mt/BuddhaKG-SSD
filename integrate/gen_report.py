"""
integrate/gen_report.py — 整合報告生成器
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def generate_report(config_module, corpus_def) -> str:
    lines = []
    lines.append(f"# BuddhaKG-SSD v3.0 整合研究報告")
    lines.append(f"")
    lines.append(f"語料集：{corpus_def.name_zh}（{corpus_def.name_en}）")
    lines.append(f"生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"KGE 版本：{config_module.CURRENT_KGE_VERSION}")
    lines.append(f"")

    lines.append(f"## KGE 版本演進")
    lines.append(f"")
    lines.append(f"| 版本 | 三元組 | MRR | 人工精確率 |")
    lines.append(f"|------|--------|-----|----------|")
    for ver, v in config_module.KGE_VERSIONS.items():
        prec = f"{v['human_prec']:.0%}" if v.get('human_prec') is not None else "未實測"
        lines.append(f"| {ver} | {v['triples']:,} | {v['mrr']:.4f} | {prec} |")
    lines.append(f"")

    confirmed = getattr(config_module, 'CONFIRMED_CLASSIFICATIONS', {})
    if confirmed:
        lines.append(f"## 三分類結果")
        lines.append(f"")
        lines.append(f"| 術語 | 分類 | 備註 |")
        lines.append(f"|------|------|------|")
        for term, info in confirmed.items():
            cls_def = config_module.TRI_CLASS_DEFINITIONS.get(info["class"], {})
            lines.append(f"| {term} | {cls_def.get('zh', '')} | {info.get('note', '')} |")

    from utils.corpus_stats import export_table1_markdown
    lines.append(f"\n## 語料統計\n")
    lines.append(export_table1_markdown(corpus_def))
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import argparse, config
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=None)
    args = parser.parse_args()
    corpus_def = config.load_corpus(args.corpus)
    report = generate_report(config, corpus_def)
    out = config.REPORT_DIR / f"integrated_report_{corpus_def.name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
