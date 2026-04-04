import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

_corpus = config.load_corpus()

import os
"""
build_usage_corpus.py — BuddhaSSD Phase 1
針對五個核心術語，從三部論典抽取含上下文的 usage corpus
每術語每論典目標：100-200 筆
"""

import json
import sys
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── 設定 ──────────────────────────────────────────────────────
BUDDHA_DIR = Path(str(config.BUDDHA_DIR))
CACHE_DIR = Path(str(config.CORPUS_CACHE_DIR))
OUTPUT_DIR   = Path("C:/buddhassd/usage_corpus")
OUTPUT_DIR.mkdir(exist_ok=True)

# 三部論典
WORKS = {wid: {"title": t.title, "juans": t.juans}
         for wid, t in _corpus.texts.items()
         if wid in _corpus.get_ssd_work_ids()}

# 五個核心術語
TARGET_TERMS = _corpus.target_terms

# 上下文窗口（字數）
WINDOW_SIZE = 60

# ── 語料載入 ──────────────────────────────────────────────────
def load_corpus(work_id):
    cache_file = CACHE_DIR / f"{work_id}_corpus.json"
    if not cache_file.exists():
        log.error(f"快取不存在：{cache_file}")
        return {}
    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)

    # 合併所有卷次文字
    juans = {}
    if "juans" in data:
        juans = data["juans"]
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and "text" in v:
                juans[k] = v["text"]
            elif isinstance(v, str) and len(v) > 100:
                juans[k] = v

    log.info(f"載入 {WORKS[work_id]}（{work_id}）：{len(juans)} 卷")
    return juans

def load_all_corpus():
    corpus = {}
    for work_id in WORKS:
        juans = load_corpus(work_id)
        if juans:
            corpus[work_id] = juans
    return corpus

# ── Neo4j 補充卷次資訊 ────────────────────────────────────────
def get_term_juans_from_neo4j(term):
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", os.environ.get("NEO4J_PASS", ""))
        )
        with driver.session() as s:
            rows = s.run("""
                MATCH (t:Term {name: $name})
                RETURN t.work AS work, t.juans AS juans,
                       t.freq AS freq
                ORDER BY t.freq DESC
            """, name=term)
            result = {}
            for row in rows:
                work = row["work"]
                if work in WORKS:
                    result[work] = {
                        "juans": row["juans"] or [],
                        "freq" : row["freq"] or 0
                    }
        driver.close()
        return result
    except Exception as e:
        log.warning(f"Neo4j 查詢失敗（{e}），使用全文搜尋")
        return {}

# ── Usage 抽取 ────────────────────────────────────────────────
def extract_usages(term, work_id, juans, max_per_work=200):
    usages = []
    idx    = 0

    for juan_key, text in juans.items():
        if not isinstance(text, str) or len(text) < 10:
            continue

        # 清理 CBETA 標記
        clean = re.sub(r'\[.*?\]', '', text)
        clean = re.sub(r'【.*?】', '', clean)
        clean = re.sub(r'\(.*?\)', '', clean)

        # 找術語位置
        pos = 0
        while True:
            pos = clean.find(term, pos)
            if pos == -1:
                break

            # 擷取前後文
            start  = max(0, pos - WINDOW_SIZE)
            end    = min(len(clean), pos + len(term) + WINDOW_SIZE)
            before = clean[start:pos]
            after  = clean[pos + len(term):end]

            # 取完整句子（以句號、分號為界）
            before_clean = re.split(r'[。；？！]', before)[-1]
            after_clean  = re.split(r'[。；？！]', after)[0]

            usage = {
                "id"      : f"{work_id}_{term}_{idx:04d}",
                "term"    : term,
                "work"    : work_id,
                "work_zh" : WORKS[work_id],
                "juan"    : juan_key,
                "before"  : before_clean.strip(),
                "target"  : term,
                "after"   : after_clean.strip(),
                "context" : f"{before_clean.strip()}{term}{after_clean.strip()}",
                "char_pos": pos,
            }
            usages.append(usage)
            idx += 1
            pos += len(term)

            if len(usages) >= max_per_work:
                break

        if len(usages) >= max_per_work:
            break

    return usages

# ── 統計與平衡 ────────────────────────────────────────────────
def balance_usages(all_usages, target=150):
    from collections import defaultdict
    by_work = defaultdict(list)
    for u in all_usages:
        by_work[u["work"]].append(u)

    balanced = []
    for work_id, items in by_work.items():
        selected = items[:target]
        balanced.extend(selected)
        log.info(f"  {WORKS[work_id]:10}：{len(items):3d} 筆 → 選取 {len(selected):3d} 筆")

    return balanced

# ── 主程式 ────────────────────────────────────────────────────
def main():
    log.info("=== BuddhaSSD Phase 1：Usage Corpus 建構 ===\n")

    corpus = load_all_corpus()
    if not corpus:
        log.error("無法載入語料，請確認 C:\\buddha\\corpus_cache\\ 存在")
        sys.exit(1)

    summary = {}

    for term in TARGET_TERMS:
        log.info(f"\n── 術語：「{term}」 ──────────────────────")

        # 查詢 Neo4j 獲取術語分布
        neo4j_info = get_term_juans_from_neo4j(term)
        if neo4j_info:
            log.info("  Neo4j 術語分布：")
            for w, info in neo4j_info.items():
                log.info(f"    {WORKS[w]:10}：freq={info['freq']:4d}  juans={len(info['juans'])}卷")

        # 從各論典抽取 usage
        all_usages = []
        for work_id, juans in corpus.items():
            usages = extract_usages(term, work_id, juans, max_per_work=200)
            log.info(f"  {WORKS[work_id]:10}：找到 {len(usages):3d} 筆 usage")
            all_usages.extend(usages)

        # 平衡抽樣
        log.info(f"  平衡抽樣（目標每論典 150 筆）：")
        balanced = balance_usages(all_usages, target=150)

        # 儲存
        output_file = OUTPUT_DIR / f"{term}_usage.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for u in balanced:
                f.write(json.dumps(u, ensure_ascii=False) + "\n")

        summary[term] = {
            "total"   : len(balanced),
            "by_work" : {
                w: len([u for u in balanced if u["work"] == w])
                for w in WORKS
            }
        }
        log.info(f"  ✅ 儲存：{output_file}（{len(balanced)} 筆）")

    # 總結
    log.info("\n══ Usage Corpus 建構完成 ════════════════════")
    log.info(f"  {'術語':10} {'T1579':>6} {'T1585':>6} {'T1594':>6} {'總計':>6}")
    log.info(f"  {'─'*40}")
    for term, info in summary.items():
        t1579 = info["by_work"].get("T1579", 0)
        t1585 = info["by_work"].get("T1585", 0)
        t1594 = info["by_work"].get("T1594", 0)
        total = info["total"]
        log.info(f"  {term:10} {t1579:>6} {t1585:>6} {t1594:>6} {total:>6}")

    # 儲存 summary
    with open("usage_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info("\n  統計已儲存：usage_summary.json")

if __name__ == "__main__":
    main()
