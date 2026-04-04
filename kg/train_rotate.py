"""
kg/train_rotate.py — RotatE 訓練（自包含版）

從 Neo4j 匯出三元組，訓練 RotatE 模型

用法：
    python kg/train_rotate.py
    python kg/train_rotate.py --epochs 500 --dim 256 --neg-samples 64
    python kg/train_rotate.py --triples-only    只匯出三元組不訓練
"""

import os, sys, json, time, math, random, argparse, logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    raise ImportError("pip install numpy")


def export_triples(uri, user, password, output_path: str) -> list:
    """
    從 Neo4j 匯出所有關係為三元組 (head, relation, tail)。
    同時包含：
      - Term-Term 橋接關係（DOCTRINAL_PARALLEL 等）
      - Term-Juan APPEARS_IN
      - Term-Text FROM_TEXT
      - Juan-Text HAS_JUAN（方向反轉為 Text-HAS_JUAN-Juan）
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        raise ImportError("pip install neo4j")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    triples = []

    # ── v1.2 實體正規化策略 ────────────────────────────────────
    # 問題：v1.2 的實體 ID 含 work 前綴（T1579_阿賴耶識）
    #       同名術語在不同論典被視為不同實體，語義空間碎片化
    # 修正：改用術語「名稱」作為實體 ID，合併跨論典同名術語
    #       同一術語在不同論典的出現被視為同一實體
    # 效果：實體空間進一步壓縮，跨文本語義對齊
    queries = [
        # 1. 跨文本橋接（使用 name 作為實體）
        ("MATCH (a:Term)-[r:DOCTRINAL_PARALLEL|EVOLVES_INTO|PRECEDES|SYSTEMATIZES]->(b:Term) "
         "RETURN a.name AS h, type(r) AS r, b.name AS t"),
        # 2. 種子術語同卷共現（使用 name）
        ("MATCH (a:Term)-[:APPEARS_IN]->(j:Juan)<-[:APPEARS_IN]-(b:Term) "
         "WHERE a.name < b.name AND a.is_seed = true AND b.is_seed = true "
         "RETURN a.name AS h, 'SEED_CO_OCCURS' AS r, b.name AS t"),
        # 3. 高頻術語同卷共現（使用 name，freq>=20 提高門檻）
        ("MATCH (a:Term)-[:APPEARS_IN]->(j:Juan)<-[:APPEARS_IN]-(b:Term) "
         "WHERE a.name < b.name AND a.freq >= 20 AND b.freq >= 20 "
         "RETURN a.name AS h, 'CO_OCCURS' AS r, b.name AS t LIMIT 80000"),
        # 4. 跨論典種子術語共現（使用 name，自動合併同名）
        ("MATCH (a:Term)-[:FROM_TEXT]->(tx:Text)<-[:FROM_TEXT]-(b:Term) "
         "WHERE a.name < b.name AND a.is_seed = true AND b.is_seed = true "
         "RETURN a.name AS h, 'CROSS_WORK_CO_OCCURS' AS r, b.name AS t"),
    ]

    logger.info("從 Neo4j 匯出精煉三元組（v1.2 實體正規化模式）...")
    with driver.session() as s:
        for q in queries:
            result = s.run(q).data()
            for row in result:
                if row["h"] and row["t"] and row["h"] != row["t"]:
                    triples.append((str(row["h"]), str(row["r"]), str(row["t"])))
            logger.info(f"  累計: {len(triples):,} 條")

    driver.close()

    # 去重
    triples = list(set(triples))
    logger.info(f"✔ 去重後三元組: {len(triples):,} 條")

    # 寫入 TSV
    with open(output_path, "w", encoding="utf-8") as f:
        for h, r, t in triples:
            f.write(f"{h}\t{r}\t{t}\n")
    logger.info(f"✔ 三元組已存入: {output_path}")
    return triples



def load_triples(path: str) -> list:
    triples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                triples.append(tuple(parts))
    logger.info(f"✔ 從 TSV 載入三元組: {len(triples):,} 條")
    return triples



def split_triples(triples, val_ratio=0.1, test_ratio=0.1, seed=42):
    random.seed(seed)
    data = list(triples)
    random.shuffle(data)
    n = len(data)
    n_test = max(1, int(n * test_ratio))
    n_val  = max(1, int(n * val_ratio))
    test  = data[:n_test]
    val   = data[n_test:n_test + n_val]
    train = data[n_test + n_val:]
    logger.info(f"  train={len(train):,}  val={len(val):,}  test={len(test):,}")
    return train, val, test



def build_maps(triples):
    """建立 entity/relation → index 對照表"""
    entities  = sorted({h for h, r, t in triples} | {t for h, r, t in triples})
    relations = sorted({r for h, r, t in triples})
    ent2id = {e: i for i, e in enumerate(entities)}
    rel2id = {r: i for i, r in enumerate(relations)}
    return ent2id, rel2id, entities, relations



def train_pykeen(train, val, test, params: dict, config: dict):
    """使用 PyKEEN 訓練 RotatE"""
    import torch
    import pykeen.triples as pt
    from pykeen.pipeline import pipeline

    # 明確設定 device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device_str = str(device)  # "cuda" or "cpu"

    logger.info("使用 PyKEEN 訓練 RotatE...")
    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info(f"使用 GPU: {gpu_name}（VRAM {vram:.1f} GB）")
    else:
        logger.info("使用 CPU 訓練（未偵測到 CUDA GPU）")

    def to_tf(triples_list):
        import pandas as pd
        df = pd.DataFrame(triples_list, columns=["head", "relation", "tail"])
        return pt.TriplesFactory.from_labeled_triples(df.values)

    train_tf = to_tf(train)
    val_tf   = to_tf(val)   if val   else None
    test_tf  = to_tf(test)  if test  else None

    result = pipeline(
        model="RotatE",
        training=train_tf,
        validation=val_tf,
        testing=test_tf,
        model_kwargs=dict(
            embedding_dim=params["dim"],
        ),
        training_kwargs=dict(
            num_epochs=params["epochs"],
            batch_size=params["batch_size"],
        ),
        negative_sampler="basic",
        negative_sampler_kwargs=dict(
            num_negs_per_pos=params["neg_samples"],
        ),
        optimizer="Adam",
        optimizer_kwargs=dict(lr=params["lr"]),
        random_seed=params["seed"],
        device=device_str,
    )

    # ── 評估結果（PyKEEN 1.11 正確 key 路徑）────────────────
    metrics = result.metric_results.to_dict()
    both_realistic = metrics.get("both", {}).get("realistic", {})

    # PyKEEN 1.11: MRR = inverse_harmonic_mean_rank
    mrr    = both_realistic.get("inverse_harmonic_mean_rank", 0)
    hits1  = both_realistic.get("hits_at_1",  0)
    hits3  = both_realistic.get("hits_at_3",  0)
    hits10 = both_realistic.get("hits_at_10", 0)

    logger.info(f"\n{'='*50}")
    logger.info(f"  Phase 4 RotatE 評估結果（v1.2 精煉語料）")
    logger.info(f"{'='*50}")
    logger.info(f"  MRR（inv_harmonic）: {mrr:.4f}  （Phase 2 基準: 0.1176）")
    logger.info(f"  Hits@1  : {hits1:.4f}")
    logger.info(f"  Hits@3  : {hits3:.4f}")
    logger.info(f"  Hits@10 : {hits10:.4f}  （Phase 2 基準: 0.700）")
    if mrr > 0.1176:
        logger.info(f"  🎉 MRR 超越 Phase 2！+{mrr-0.1176:.4f}")
    if hits10 > 0.700:
        logger.info(f"  🎉 Hits@10 超越 Phase 2！+{hits10-0.700:.4f}")
    logger.info(f"{'='*50}\n")

    # 儲存 checkpoint
    result.save_to_directory("pykeen_output")
    logger.info("✔ PyKEEN 模型已儲存至 pykeen_output/")

    return result.model, {"mrr": mrr, "hits@1": hits1, "hits@3": hits3, "hits@10": hits10}



def generate_hidden_edges(model, ent2id, rel2id, entities, relations,
                          existing_triples, n_edges=100, output_path="hidden_edges.tsv"):
    """
    從嵌入空間中找出模型預測分數高但實際不存在的三元組（隱性邊）。
    重點針對種子術語對與橋接關係。
    """
    import torch
    logger.info(f"\n生成隱性邊（目標 {n_edges} 條）...")

    existing = set(existing_triples)

    # 優先考察種子術語（is_seed 節點）
    # 從 entity ID 中過濾出術語節點（格式：work_術語名）
    term_entities = [e for e in entities if "_" in e and len(e.split("_")[-1]) >= 2]
    seed_terms_partial = [
        "阿賴耶識", "末那識", "阿陀那識", "遍計所執", "依他起", "圓成實",
        "真如", "種子", "熏習", "轉依", "波羅蜜多", "菩提分法",
        "四念住", "八聖道", "涅槃", "解脫",
    ]
    seed_ents = [e for e in term_entities
                 if any(s in e for s in seed_terms_partial)]
    if not seed_ents:
        seed_ents = term_entities[:200]

    logger.info(f"  種子術語實體: {len(seed_ents)} 個")

    bridge_rels = [r for r in relations
                   if r in ("DOCTRINAL_PARALLEL", "EVOLVES_INTO", "PRECEDES",
                            "SYSTEMATIZES", "CO_OCCURS", "APPEARS_IN")]
    if not bridge_rels:
        bridge_rels = relations[:5]

    model.ent_emb.eval()
    model.rel_emb.eval()
    device = model.device
    candidates = []

    with torch.no_grad():
        for rel in bridge_rels:
            if rel not in rel2id:
                continue
            r_idx = rel2id[rel]
            for h_ent in seed_ents[:100]:
                if h_ent not in ent2id:
                    continue
                h_idx = ent2id[h_ent]
                all_t = torch.arange(len(entities), dtype=torch.long, device=device)
                h_t   = torch.tensor([h_idx], dtype=torch.long, device=device).expand(len(entities))
                r_t   = torch.tensor([r_idx], dtype=torch.long, device=device).expand(len(entities))
                scores = model.score(h_t, r_t, all_t)

                # 取前 K 個候選，排除已存在的三元組
                topk = min(20, len(entities))
                top_idx = scores.topk(topk).indices.tolist()
                for t_idx in top_idx:
                    t_ent = entities[t_idx]
                    if t_ent == h_ent:
                        continue
                    triple = (h_ent, rel, t_ent)
                    if triple not in existing:
                        candidates.append((scores[t_idx].item(), triple))

    # 去重並排序
    candidates = sorted(set((s, t) for s, t in candidates), key=lambda x: -x[0])
    top_hidden = candidates[:n_edges]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("score\thead\trelation\ttail\n")
        for score, (h, r, t) in top_hidden:
            f.write(f"{score:.4f}\t{h}\t{r}\t{t}\n")

    logger.info(f"✔ 隱性邊已儲存: {output_path}（{len(top_hidden)} 條）")

    # 摘要
    rel_counts = {}
    for _, (h, r, t) in top_hidden:
        rel_counts[r] = rel_counts.get(r, 0) + 1
    logger.info("  各關係類型分布:")
    for r, c in sorted(rel_counts.items(), key=lambda x: -x[1]):
        logger.info(f"    {r}: {c} 條")

    return top_hidden



def save_embeddings(model, entities, relations, embed_dir: str):
    import torch, json
    Path(embed_dir).mkdir(exist_ok=True)

    ent_path = Path(embed_dir) / "entity_embeddings.json"
    rel_path = Path(embed_dir) / "relation_embeddings.json"

    ent_emb = model.ent_emb.weight.data.tolist()
    rel_emb = model.rel_emb.weight.data.tolist()

    with open(ent_path, "w", encoding="utf-8") as f:
        json.dump({e: ent_emb[i] for i, e in enumerate(entities)}, f,
                  ensure_ascii=False, indent=None)
    with open(rel_path, "w", encoding="utf-8") as f:
        json.dump({r: rel_emb[i] for i, r in enumerate(relations)}, f,
                  ensure_ascii=False, indent=None)

    logger.info(f"✔ 嵌入向量已儲存: {embed_dir}/")




def main():
    parser = argparse.ArgumentParser(description="RotatE 訓練")
    parser.add_argument("--epochs", type=int, default=config.ROTATE_CONFIG["epochs"])
    parser.add_argument("--dim", type=int, default=config.ROTATE_CONFIG["dim"])
    parser.add_argument("--neg-samples", type=int, default=config.ROTATE_CONFIG["neg_samples"])
    parser.add_argument("--triples-only", action="store_true", help="只匯出三元組")
    parser.add_argument("--backend", choices=["pykeen", "pytorch"], default="pykeen")
    args = parser.parse_args()

    output_dir = str(config.KG_DIR)
    triples_path = os.path.join(output_dir, "triples.tsv")

    # 匯出三元組
    log.info("=== 從 Neo4j 匯出三元組 ===")
    export_triples(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASS, triples_path)

    if args.triples_only:
        log.info(f"三元組已匯出至 {triples_path}")
        return

    # 載入與分割
    triples = load_triples(triples_path)
    if not triples:
        log.error("無三元組可訓練")
        return

    train, val, test = split_triples(triples)
    log.info(f"三元組：train={len(train)} val={len(val)} test={len(test)}")

    params = {
        "epochs": args.epochs,
        "dim": args.dim,
        "neg_samples": args.neg_samples,
    }
    train_config = {
        "output_dir": output_dir,
    }

    if args.backend == "pykeen":
        train_pykeen(train, val, test, params, train_config)
    else:
        log.info("PyTorch backend 需要手動執行原始 train_rotate.py")

    log.info("訓練完成")


if __name__ == "__main__":
    main()
