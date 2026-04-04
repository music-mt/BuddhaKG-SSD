"""
embed_usage.py — BuddhaSSD Phase 2
基線版語境化嵌入：共現向量 + TF-IDF
為每筆 usage 建立語境向量，供後續聚類分析使用
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
import jieba
import jieba.analyse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

USAGE_DIR = Path(str(config.USAGE_DIR))
EMBED_DIR = Path(str(config.EMBED_DIR))
EMBED_DIR.mkdir(exist_ok=True)

DICT_FILE  = Path("C:/buddhassd/buddhist_dict.txt")
TARGET_TERMS = _corpus.target_terms

WORKS = {wid: {"title": t.title, "juans": t.juans}
         for wid, t in _corpus.texts.items()
         if wid in _corpus.get_ssd_work_ids()}

# 停用詞
STOPWORDS = set([
    "之", "也", "者", "所", "而", "以", "於", "其", "為", "則",
    "有", "是", "此", "若", "即", "故", "謂", "云", "及", "與",
    "彼", "諸", "亦", "乃", "非", "無", "不", "得", "能", "應",
    "當", "復", "又", "更", "由", "從", "在", "中", "上", "下",
    "何", "如", "或", "雖", "但", "因", "成", "名", "稱", "說",
])

def setup_jieba():
    if DICT_FILE.exists():
        jieba.load_userdict(str(DICT_FILE))
        log.info("jieba 佛教術語詞典載入完成")

def load_usages(term):
    file = USAGE_DIR / f"{term}_usage.jsonl"
    if not file.exists():
        log.error(f"找不到：{file}")
        return []
    usages = []
    with open(file, encoding="utf-8") as f:
        for line in f:
            usages.append(json.loads(line.strip()))
    log.info(f"載入「{term}」usage：{len(usages)} 筆")
    return usages

def tokenize(text, term):
    tokens = jieba.cut(text)
    result = []
    for t in tokens:
        t = t.strip()
        if t and t != term and t not in STOPWORDS and len(t) >= 2:
            result.append(t)
    return result

def build_cooccur_vectors(usages, term, vocab_size=200):
    # 建立詞彙表
    all_tokens = []
    for u in usages:
        tokens = tokenize(u.get("context", ""), term)
        all_tokens.extend(tokens)

    vocab_counter = Counter(all_tokens)
    vocab = [w for w, _ in vocab_counter.most_common(vocab_size)]
    vocab_index = {w: i for i, w in enumerate(vocab)}

    log.info(f"  詞彙表大小：{len(vocab)} 個詞")

    # 為每筆 usage 建立向量
    vectors = []
    for u in usages:
        tokens = tokenize(u.get("context", ""), term)
        vec = np.zeros(len(vocab))
        for t in tokens:
            if t in vocab_index:
                vec[vocab_index[t]] += 1
        # L2 正規化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors.append(vec)

    return np.array(vectors), vocab

def compute_work_centroids(usages, vectors):
    centroids = {}
    for work_id, work_zh in WORKS.items():
        indices = [i for i, u in enumerate(usages) if u["work"] == work_id]
        if indices:
            centroid = vectors[indices].mean(axis=0)
            centroids[work_id] = centroid
            log.info(f"  {work_zh}（{work_id}）：{len(indices)} 筆")
    return centroids

def cosine_similarity(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

def compute_pairwise_similarity(centroids):
    works = list(centroids.keys())
    results = {}
    for i in range(len(works)):
        for j in range(i+1, len(works)):
            w1, w2 = works[i], works[j]
            sim = cosine_similarity(centroids[w1], centroids[w2])
            key = f"{w1}_vs_{w2}"
            results[key] = round(sim, 4)
            log.info(f"  {WORKS[w1]} vs {WORKS[w2]}：相似度 = {sim:.4f}")
    return results

def get_top_context_words(usages, term, work_id, top_n=10):
    tokens_all = []
    for u in usages:
        if u["work"] == work_id:
            tokens = tokenize(u.get("context", ""), term)
            tokens_all.extend(tokens)
    counter = Counter(tokens_all)
    return counter.most_common(top_n)

def main():
    setup_jieba()
    log.info("=== BuddhaSSD Phase 2：語境化嵌入（基線版）===\n")

    all_results = {}

    for term in TARGET_TERMS:
        log.info(f"\n── 術語：「{term}」 ──────────────────────")
        usages = load_usages(term)
        if not usages:
            continue

        # 建立共現向量
        log.info("  建立共現向量...")
        vectors, vocab = build_cooccur_vectors(usages, term)

        # 計算各論典重心
        log.info("  計算論典語境重心：")
        centroids = compute_work_centroids(usages, vectors)

        # 計算論典間相似度
        log.info("  論典間語境相似度：")
        similarities = compute_pairwise_similarity(centroids)

        # 各論典高頻共現詞
        top_words = {}
        for work_id in WORKS:
            words = get_top_context_words(usages, term, work_id, top_n=10)
            top_words[work_id] = words
            if words:
                words_str = "、".join(f"{w}({c})" for w, c in words[:5])
                log.info(f"  {WORKS[work_id]} 高頻共現詞：{words_str}")

        # 儲存結果
        result = {
            "term"        : term,
            "total_usages": len(usages),
            "by_work"     : {w: len([u for u in usages if u["work"]==w]) for w in WORKS},
            "similarities": similarities,
            "top_words"   : {w: top_words.get(w, []) for w in WORKS},
            "vocab_size"  : len(vocab),
        }
        all_results[term] = result

        # 儲存向量
        np.save(str(EMBED_DIR / f"{term}_vectors.npy"), vectors)
        with open(EMBED_DIR / f"{term}_usages_index.jsonl", "w", encoding="utf-8") as f:
            for u in usages:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

        log.info(f"  ✅ 向量已儲存：{term}_vectors.npy")

    # 儲存總結
    with open(EMBED_DIR / "embed_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 語義位移初步指標
    log.info("\n══ 跨論典語境相似度總覽 ════════════════════")
    log.info(f"  {'術語':10} {'T1579_vs_T1585':>16} {'T1579_vs_T1594':>16} {'T1585_vs_T1594':>16}")
    log.info(f"  {'─'*62}")
    for term, r in all_results.items():
        s = r["similarities"]
        s1 = s.get("T1579_vs_T1585", 0)
        s2 = s.get("T1579_vs_T1594", 0)
        s3 = s.get("T1585_vs_T1594", 0)
        log.info(f"  {term:10} {s1:>16.4f} {s2:>16.4f} {s3:>16.4f}")

    log.info("\n  注意：相似度越低，表示跨論典語境差異越大，")
    log.info("        越可能存在語義位移（需 KWIC 進一步驗證）")
    log.info("\n  embed_summary.json 已儲存")

if __name__ == "__main__":
    main()
