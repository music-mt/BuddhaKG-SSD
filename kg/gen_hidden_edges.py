#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_hidden_edges.py  BuddhaNLP Phase 4
從 pykeen_output/ 載入已訓練的 RotatE 模型，產生隱性邊。

隱性邊定義：模型預測分數高，但原始圖中不存在的三元組。
重點針對種子術語對與橋接關係類型。
"""
import json, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TRIPLES_TSV  = "triples.tsv"
OUTPUT_TSV   = "hidden_edges.tsv"
PYKEEN_DIR   = "pykeen_output"
N_EDGES      = 100

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# 從語料集載入種子術語
_corpus = config.load_corpus()
SEED_TERMS = _corpus.seed_terms

_ORIGINAL_SEED_TERMS = [
    "阿賴耶識", "末那識", "阿陀那識", "藏識", "異熟識",
    "遍計所執", "依他起", "圓成實",
    "種子", "熏習", "現行", "習氣",
    "真如", "法界", "轉依", "轉識成智",
    "波羅蜜多", "菩提分法", "菩薩地",
    "資糧位", "加行位", "通達位", "修習位", "究竟位",
    "四念住", "八聖道", "涅槃", "解脫",
    "唯識", "所知依", "所知相",
    "三摩地", "靜慮",
]


def load_triples(path):
    triples = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                triples.add(tuple(parts))
    return triples


def main():
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # ── 載入既有三元組（用於過濾）────────────────────────────
    existing = load_triples(TRIPLES_TSV)
    logger.info(f"既有三元組: {len(existing):,} 條")

    # ── 載入 PyKEEN 模型 ──────────────────────────────────────
    model_path = Path(PYKEEN_DIR) / "trained_model.pkl"
    if not model_path.exists():
        logger.error(f"找不到模型: {model_path}")
        logger.info("pykeen_output/ 內容:")
        for p in Path(PYKEEN_DIR).rglob("*"):
            logger.info(f"  {p}")
        return

    logger.info(f"載入模型: {model_path}")
    model = torch.load(str(model_path), map_location=device)
    model = model.to(device)
    model.eval()

    # ── 取得實體與關係對照表（直接讀壓縮 TSV）──────────────────
    import gzip, pandas as pd
    tf_dir = Path(PYKEEN_DIR) / "training_triples"

    with gzip.open(str(tf_dir / "entity_to_id.tsv.gz"), "rt", encoding="utf-8") as f:
        ent_df = pd.read_csv(f, sep="\t")
    cols = ent_df.columns.tolist()
    if "id" in cols and "label" in cols:
        entity_to_id = dict(zip(ent_df["label"], ent_df["id"].astype(int)))
    else:
        entity_to_id = dict(zip(ent_df.iloc[:, 0].astype(str), ent_df.iloc[:, 1].astype(int)))

    with gzip.open(str(tf_dir / "relation_to_id.tsv.gz"), "rt", encoding="utf-8") as f:
        rel_df = pd.read_csv(f, sep="\t")
    cols = rel_df.columns.tolist()
    if "id" in cols and "label" in cols:
        relation_to_id = dict(zip(rel_df["label"], rel_df["id"].astype(int)))
    else:
        relation_to_id = dict(zip(rel_df.iloc[:, 0].astype(str), rel_df.iloc[:, 1].astype(int)))

    id_to_entity   = {v: k for k, v in entity_to_id.items()}
    id_to_relation = {v: k for k, v in relation_to_id.items()}

    n_ent = len(entity_to_id)
    n_rel = len(relation_to_id)
    logger.info(f"實體數: {n_ent}  關係數: {n_rel}")
    logger.info(f"關係類型: {list(relation_to_id.keys())}")

    # ── 篩選種子術語 ──────────────────────────────────────────
    seed_ids = [entity_to_id[t] for t in SEED_TERMS if t in entity_to_id]
    logger.info(f"種子術語（圖中存在）: {len(seed_ids)} 個")

    # ── 目標關係（橋接關係優先）──────────────────────────────
    target_rels = []
    for rel_name in ["DOCTRINAL_PARALLEL", "EVOLVES_INTO", "PRECEDES",
                     "SEED_CO_OCCURS", "CO_OCCURS", "CROSS_WORK_CO_OCCURS"]:
        if rel_name in relation_to_id:
            target_rels.append((rel_name, relation_to_id[rel_name]))
    if not target_rels:
        target_rels = [(name, rid) for name, rid in relation_to_id.items()]

    logger.info(f"目標關係: {[r for r, _ in target_rels]}")

    # ── 預測隱性邊 ────────────────────────────────────────────
    logger.info(f"\n預測隱性邊（目標 {N_EDGES} 條）...")
    candidates = []
    all_t = torch.arange(n_ent, dtype=torch.long, device=device)

    with torch.no_grad():
        for rel_name, r_id in target_rels:
            r_t = torch.tensor([r_id], dtype=torch.long, device=device)
            for h_id in seed_ids:
                h_t = torch.tensor([h_id], dtype=torch.long, device=device)
                h_ent = id_to_entity[h_id]

                # 使用 PyKEEN model 的 score_t 方法
                try:
                    scores = model.score_t(
                        hr_batch=torch.stack([h_t, r_t], dim=1)
                    ).squeeze()
                except AttributeError:
                    # 舊版 PyKEEN API
                    scores = model.predict_scores_all_tails(
                        hr_batch=torch.stack([h_t, r_t], dim=1)
                    ).squeeze()

                # 取 top-k 候選
                topk_vals, topk_idx = scores.topk(min(30, n_ent))
                for score_val, t_id in zip(topk_vals.tolist(), topk_idx.tolist()):
                    t_ent = id_to_entity[t_id]
                    if t_ent == h_ent:
                        continue
                    triple = (h_ent, rel_name, t_ent)
                    if triple not in existing:
                        candidates.append((score_val, triple))

    # 去重排序
    seen = set()
    unique_candidates = []
    for score, triple in sorted(candidates, key=lambda x: -x[0]):
        if triple not in seen:
            seen.add(triple)
            unique_candidates.append((score, triple))

    top_hidden = unique_candidates[:N_EDGES]
    logger.info(f"找到候選隱性邊: {len(unique_candidates):,} 條，取前 {len(top_hidden)} 條")

    # ── 輸出 ──────────────────────────────────────────────────
    with open(OUTPUT_TSV, "w", encoding="utf-8") as f:
        f.write("score\thead\trelation\ttail\n")
        for score, (h, r, t) in top_hidden:
            f.write(f"{score:.4f}\t{h}\t{r}\t{t}\n")

    logger.info(f"\n✔ 隱性邊已儲存: {OUTPUT_TSV}")

    # ── 摘要統計 ──────────────────────────────────────────────
    rel_counts = {}
    for _, (h, r, t) in top_hidden:
        rel_counts[r] = rel_counts.get(r, 0) + 1

    logger.info("\n── 隱性邊摘要 ─────────────────────────────────")
    logger.info(f"  總計: {len(top_hidden)} 條")
    logger.info("  各關係分布:")
    for r, c in sorted(rel_counts.items(), key=lambda x: -x[1]):
        logger.info(f"    {r}: {c} 條")
    logger.info("\n  前 20 條隱性邊:")
    logger.info(f"  {'分數':>8}  {'頭術語':<12}  {'關係':<25}  尾術語")
    logger.info(f"  {'-'*70}")
    for score, (h, r, t) in top_hidden[:20]:
        logger.info(f"  {score:>8.4f}  {h:<12}  {r:<25}  {t}")


# 覆蓋為語料集定義
# SEED_TERMS 已在上方從 config 載入

if __name__ == "__main__":
    main()
