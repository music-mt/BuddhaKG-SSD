"""
cluster_usage.py — BuddhaSSD Phase 3
對五個術語的 usage vectors 進行聚類分析
觀察是否形成可分辨群組，以及群組是否對應特定論典
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

_corpus = config.load_corpus()

import json
import logging
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EMBED_DIR = Path(str(config.EMBED_DIR))
CLUSTER_DIR = Path(str(config.CLUSTER_DIR))
CLUSTER_DIR.mkdir(exist_ok=True)

TARGET_TERMS = _corpus.target_terms
WORKS = {wid: {"title": t.title, "juans": t.juans}
         for wid, t in _corpus.texts.items()
         if wid in _corpus.get_ssd_work_ids()}

def load_vectors_and_usages(term):
    vec_file   = EMBED_DIR / f"{term}_vectors.npy"
    usage_file = EMBED_DIR / f"{term}_usages_index.jsonl"
    if not vec_file.exists():
        log.error(f"找不到向量：{vec_file}")
        return None, []
    vectors = np.load(str(vec_file))
    usages  = []
    with open(usage_file, encoding="utf-8") as f:
        for line in f:
            usages.append(json.loads(line.strip()))
    return vectors, usages

def find_best_k(vectors, k_range=range(2, 6)):
    best_k     = 2
    best_score = -1
    scores     = {}
    for k in k_range:
        if k >= len(vectors):
            continue
        km    = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(vectors, labels)
        scores[k] = round(score, 4)
        if score > best_score:
            best_score = score
            best_k     = k
    return best_k, best_score, scores

def analyze_cluster(cluster_id, usages, labels, vectors):
    indices = [i for i, l in enumerate(labels) if l == cluster_id]
    cluster_usages = [usages[i] for i in indices]

    work_dist = Counter(u["work"] for u in cluster_usages)
    dominant_work = work_dist.most_common(1)[0][0] if work_dist else "?"

    contexts = [u.get("context","") for u in cluster_usages]
    all_chars = "".join(contexts)

    import jieba
    tokens = [t for t in jieba.cut(all_chars)
              if len(t) >= 2 and t not in {"一切","如是","當知","所謂","謂","此","彼"}]
    top_words = Counter(tokens).most_common(8)

    return {
        "cluster_id"    : cluster_id,
        "size"          : len(indices),
        "work_dist"     : dict(work_dist),
        "dominant_work" : dominant_work,
        "top_words"     : top_words,
    }

def compute_work_cluster_overlap(usages, labels, n_clusters):
    result = defaultdict(lambda: defaultdict(int))
    for i, (u, l) in enumerate(zip(usages, labels)):
        result[u["work"]][l] += 1
    return dict(result)

def main():
    log.info("=== BuddhaSSD Phase 3：聚類分析 ===\n")
    all_results = {}

    for term in TARGET_TERMS:
        log.info(f"\n── 術語：「{term}」 ──────────────────────")
        vectors, usages = load_vectors_and_usages(term)
        if vectors is None or len(vectors) < 5:
            log.warning(f"  樣本不足，跳過")
            continue

        # 選最佳 K
        log.info("  選擇最佳聚類數 K...")
        best_k, best_score, all_scores = find_best_k(vectors)
        log.info(f"  最佳 K={best_k}，輪廓係數={best_score:.4f}")
        log.info(f"  各K輪廓係數：{all_scores}")

        # K-means 聚類
        km     = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)

        # 分析各群
        log.info(f"\n  聚類結果（K={best_k}）：")
        clusters = []
        for k in range(best_k):
            info = analyze_cluster(k, usages, labels, vectors)
            clusters.append(info)

            work_str = " / ".join(
                f"{WORKS.get(w,w)}:{c}" for w,c in info["work_dist"].items()
            )
            words_str = "、".join(f"{w}({c})" for w,c in info["top_words"][:5])
            dominant  = WORKS.get(info["dominant_work"], info["dominant_work"])

            log.info(f"  群 {k}（{info['size']}筆）主要論典：{dominant}")
            log.info(f"    論典分布：{work_str}")
            log.info(f"    高頻詞：{words_str}")

        # 論典-聚類交叉分析
        overlap = compute_work_cluster_overlap(usages, labels, best_k)
        log.info(f"\n  論典×聚類交叉分布：")
        log.info(f"  {'論典':12} " + " ".join(f"群{k:>4}" for k in range(best_k)))
        for work_id, work_zh in WORKS.items():
            row = overlap.get(work_id, {})
            counts = [row.get(k, 0) for k in range(best_k)]
            log.info(f"  {work_zh:12} " + " ".join(f"{c:>5}" for c in counts))

        # 初步語義位移判斷
        log.info(f"\n  初步判斷：")
        work_cluster_ratio = {}
        for work_id in WORKS:
            row = overlap.get(work_id, {})
            total = sum(row.values())
            if total == 0:
                continue
            dominant_cluster = max(row, key=row.get)
            ratio = row[dominant_cluster] / total
            work_cluster_ratio[work_id] = (dominant_cluster, ratio)
            log.info(f"    {WORKS[work_id]}：主要落在群{dominant_cluster}（{ratio:.1%}）")

        all_results[term] = {
            "best_k"             : best_k,
            "silhouette"         : best_score,
            "clusters"           : clusters,
            "work_cluster_ratio" : {w: list(v) for w, v in work_cluster_ratio.items()},
            "overlap"            : {w: dict(v) for w, v in overlap.items()},
        }

        # 儲存聚類標籤
        with open(CLUSTER_DIR / f"{term}_labels.json", "w", encoding="utf-8") as f:
            json.dump({
                "term"   : term,
                "labels" : labels.tolist(),
                "best_k" : best_k,
            }, f, ensure_ascii=False, indent=2)

    # 總結
    with open(CLUSTER_DIR / "cluster_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    log.info("\n══ 聚類分析總覽 ════════════════════════════")
    log.info(f"  {'術語':10} {'最佳K':>6} {'輪廓係數':>10} 初步語義位移判斷")
    log.info(f"  {'─'*55}")
    for term, r in all_results.items():
        k    = r["best_k"]
        sc   = r["silhouette"]
        flag = "🔴 高差異" if sc > 0.15 else "🟡 中差異" if sc > 0.08 else "🟢 低差異"
        log.info(f"  {term:10} {k:>6} {sc:>10.4f} {flag}")

    log.info("\n  cluster_summary.json 已儲存")

if __name__ == "__main__":
    main()
