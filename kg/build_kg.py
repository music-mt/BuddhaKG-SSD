"""
kg/build_kg.py — 知識圖譜建構（自包含版）

從 CBETA 語料建構 Neo4j 知識圖譜，支援任意語料集

用法：
    python kg/build_kg.py init
    python kg/build_kg.py build T1585 10
    python kg/build_kg.py build T1585 10 --start 1
    python kg/build_kg.py bridge
    python kg/build_kg.py stats
    python kg/build_kg.py clear T1585
    python kg/build_kg.py --build-all
    python kg/build_kg.py --corpus tiantai --build-all
"""

import os, sys, json, re, logging, argparse
from pathlib import Path
from collections import Counter
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from utils.neo4j_client import Neo4jClient
from utils.corpus_manager import CorpusManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    import jieba
    jieba.setLogLevel(logging.WARNING)
except ImportError:
    raise ImportError("pip install jieba")

BRIDGE_RULES = [
    # 術語演變
    ("阿陀那識", "T1579", "阿賴耶識", "T1585", "EVOLVES_INTO",   "術語發展"),
    ("阿賴耶識", "T1579", "阿賴耶識", "T1585", "DOCTRINAL_PARALLEL", "同一概念"),
    # 概念平行
    ("真如",     "T1579", "所知依",   "T1594", "DOCTRINAL_PARALLEL", "概念對應"),
    ("依他起",   "T1579", "依他起",   "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
    ("圓成實",   "T1579", "圓成實",   "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
    ("遍計所執", "T1579", "遍計所執", "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
    # 解深密經→瑜伽師地論
    ("阿陀那識", "T0676", "阿賴耶識", "T1579", "PRECEDES",        "先行概念"),
    ("依他起",   "T0676", "依他起",   "T1579", "DOCTRINAL_PARALLEL", "三性同用"),
    # Phase 2 橋接（阿含→唯識）
    # T1579 使用「四念住」「八聖道」（非「四念處」「八正道」）
    ("四念住", "T1579", "四念住", "雜阿含", "SYSTEMATIZES", "系統化阿含"),
    ("八聖道", "T1579", "八聖道", "雜阿含", "SYSTEMATIZES", "系統化阿含"),
    # 解深密經→成唯識論 三性橋接
    ("依他起",   "T0676", "依他起",   "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
    ("圓成實",   "T0676", "圓成實",   "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
    ("遍計所執", "T0676", "遍計所執", "T1585", "DOCTRINAL_PARALLEL", "三性同用"),
]

def extract_terms(juan_texts: dict, work: str) -> tuple:
    """
    從卷文字中擷取術語。
    回傳:
      term_rows  : [{id, name, work, freq, is_seed, juans}, ...]
      rel_rows   : [{term_id, juan_id, count}, ...]
    """
    min_len  = CONFIG["MIN_TERM_LEN"]
    min_freq = CONFIG["MIN_TERM_FREQ"]

    # 載入佛教術語自定義詞典（若存在）
    dict_path = Path("buddhist_dict.txt")
    if dict_path.exists():
        jieba.load_userdict(str(dict_path))
        logger.info("  ✔ 佛教術語詞典已載入")
    else:
        logger.warning("  ⚠ 未找到 buddhist_dict.txt，使用預設詞典")

    # 過濾規則：排除空字串、純符號、含雜訊字元
    NOISE = re.compile(r'[a-zA-Z0-9\[\]＊◎○、。，：；？！「」【】（）\s]')

    # 全書詞頻統計
    global_counter: Counter = Counter()
    juan_counters: dict = {}

    logger.info(f"  分詞中（{len(juan_texts)} 卷）...")
    for juan, text in juan_texts.items():
        words = [
            w for w in jieba.cut(text)
            if w                          # 非空字串
            and w.strip()                 # 非純空白
            and len(w) >= min_len         # 最短長度
            and not NOISE.search(w)       # 無雜訊字元
        ]
        counter = Counter(words)
        juan_counters[juan] = counter
        global_counter.update(counter)

    # 過濾低頻詞，保留種子術語
    kept_terms = {
        term for term, freq in global_counter.items()
        if freq >= min_freq or term in YOGACARA_TERMS
    }

    # 建立節點資料
    term_rows = []
    for term in kept_terms:
        freq  = global_counter[term]
        juans = sorted([j for j, c in juan_counters.items() if c.get(term, 0) > 0])
        term_rows.append({
            "id":      f"{work}_{term}",
            "name":    term,
            "work":    work,
            "freq":    freq,
            "is_seed": term in YOGACARA_TERMS,
            "juans":   juans,
        })

    # 建立術語-卷關係
    rel_rows = []
    for term in kept_terms:
        for juan, counter in juan_counters.items():
            count = counter.get(term, 0)
            if count > 0:
                rel_rows.append({
                    "term_id": f"{work}_{term}",
                    "juan_id": f"{work}_j{juan}",
                    "count":   count,
                })

    seed_count = sum(1 for r in term_rows if r["is_seed"])
    logger.info(f"  ✔ 術語: {len(term_rows):,} 個（種子術語: {seed_count} 個）")
    logger.info(f"  ✔ 術語-卷關係: {len(rel_rows):,} 條")
    return term_rows, rel_rows



def build_work(neo4j: Neo4jManager, cache: CorpusCache,
               work: str, juan_start: int, juan_end: int, mode: str):
    """
    完整建圖流程：
      1. 取得語料（快取優先，無快取則從 API 擷取）
      2. 寫入 Text + Juan 節點
      3. 擷取術語，寫入 Term 節點
      4. 建立 Term-Juan、Term-Text 關係
    """
    if work not in WORK_META:
        logger.error(f"未知 work: {work}，支援: {list(WORK_META.keys())}")
        sys.exit(1)

    meta = WORK_META[work]
    logger.info(f"\n{'='*55}")
    logger.info(f"  建圖: {meta['title']}（{work}）卷{juan_start}～{juan_end}")
    logger.info(f"  模式: {mode}")
    logger.info(f"{'='*55}")

    if mode == "replace":
        logger.info("  清除舊節點...")
        neo4j.clear_work(work)

    # ── Step 1: 取得語料 ──────────────────────────────────────
    juan_texts: dict = {}

    if cache.exists(work) and mode == "append":
        cached = cache.load(work)
        if cached:
            # 只取需要的卷次範圍
            for j in range(juan_start, juan_end + 1):
                if j in cached:
                    juan_texts[j] = cached[j]

    # 不足的卷次從 API 補取
    missing = [j for j in range(juan_start, juan_end + 1) if j not in juan_texts]
    if missing:
        logger.info(f"  從 CBETA API 擷取 {len(missing)} 卷...")
        client: CBETAClient = create_client()
        for j in missing:
            logger.info(f"    卷{j:>3}...", )
            try:
                text = client.get_juan_text(work, j)
                juan_texts[j] = text
                logger.info(f" OK {len(text):,} 字")
                time.sleep(CONFIG["RATE_LIMIT"])
            except Exception as e:
                logger.warning(f" FAIL {e}")
                juan_texts[j] = ""

        # 更新快取
        existing = cache.load(work) or {}
        existing.update({str(k): v for k, v in juan_texts.items()})
        cache.save(work, existing)

    if not juan_texts:
        logger.error("  語料為空，中止")
        return

    total_chars = sum(len(v) for v in juan_texts.values())
    logger.info(f"  語料就緒: {len(juan_texts)} 卷，{total_chars:,} 字")

    # ── Step 2: 寫入論典與卷節點 ──────────────────────────────
    logger.info("  寫入 Text / Juan 節點...")
    neo4j.upsert_work(work, meta)
    neo4j.upsert_juans_batch(work, juan_texts)

    # ── Step 3: 術語擷取 ──────────────────────────────────────
    logger.info("  術語擷取中...")
    term_rows, rel_rows = extract_terms(juan_texts, work)

    # ── Step 4: 寫入術語節點與關係 ────────────────────────────
    logger.info("  寫入 Term 節點...")
    neo4j.upsert_terms_batch(term_rows)

    logger.info("  寫入術語-卷關係...")
    neo4j.upsert_term_juan_rels(rel_rows)

    logger.info("  寫入術語-論典關係...")
    neo4j.upsert_term_text_rels(work, [r["id"] for r in term_rows])

    logger.info(f"\n  ✅ {meta['title']} 建圖完成")




def build_all(corpus_def):
    """建構語料集中所有論典的知識圖譜"""
    neo = Neo4jClient()
    cm = CorpusManager(config.CORPUS_CACHE_DIR, config.CBETA_BASE)

    log.info(f"=== 建構知識圖譜：{corpus_def.name_zh} ===")

    log.info("[1/4] 初始化 Schema...")
    neo.init_schema()

    log.info("[2/4] 建構各論典...")
    for i, (wid, t) in enumerate(corpus_def.texts.items()):
        log.info(f"  ({i+1}/{len(corpus_def.texts)}) {t.title}（{wid}）{t.juans} 卷")
        cache = type("Cache", (), {
            "cache_dir": config.CORPUS_CACHE_DIR,
            "cache_file": lambda self, w: Path(self.cache_dir) / f"{w}_corpus.json",
            "load": lambda self, w: cm.load_cached(w),
            "exists": lambda self, w: cm.is_cached(w),
        })()
        build_work(neo, cache, wid, 1, t.juans, "rebuild")

    log.info("[3/4] 建立跨論典橋接...")
    neo.build_bridges()

    log.info("[4/4] 統計...")
    neo.stats()
    neo.close()
    log.info("\n完成")


def main():
    parser = argparse.ArgumentParser(description="知識圖譜建構")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--build-all", action="store_true")
    parser.add_argument("cmd", nargs="?", choices=["init", "build", "bridge", "stats", "clear"])
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    corpus_def = config.load_corpus(args.corpus)

    if args.build_all:
        build_all(corpus_def)
        return

    neo = Neo4jClient()
    cm = CorpusManager(config.CORPUS_CACHE_DIR, config.CBETA_BASE)

    if args.cmd == "init":
        neo.init_schema()
        log.info("Schema 初始化完成")
    elif args.cmd == "build":
        if len(args.args) < 2:
            print("用法: python kg/build_kg.py build <WORK_ID> <JUANS> [--start N]")
            return
        work = args.args[0]
        juans = int(args.args[1])
        start = 1
        if "--start" in args.args:
            idx = args.args.index("--start")
            start = int(args.args[idx + 1])
        cache = type("Cache", (), {
            "cache_dir": config.CORPUS_CACHE_DIR,
            "cache_file": lambda self, w: Path(self.cache_dir) / f"{w}_corpus.json",
            "load": lambda self, w: cm.load_cached(w),
            "exists": lambda self, w: cm.is_cached(w),
        })()
        build_work(neo, cache, work, start, juans, "append")
    elif args.cmd == "bridge":
        neo.build_bridges()
    elif args.cmd == "stats":
        neo.stats()
    elif args.cmd == "clear":
        if args.args:
            neo.clear_work(args.args[0])
        else:
            print("用法: python kg/build_kg.py clear <WORK_ID>")
    else:
        print(f"語料集：{corpus_def.name_zh}")
        print(f"論典：{list(corpus_def.texts.keys())}")
        print(f"\n用法：")
        print(f"  python kg/build_kg.py --build-all           全部建構")
        print(f"  python kg/build_kg.py init                  初始化 Schema")
        print(f"  python kg/build_kg.py build T1585 10        建構單部論典")
        print(f"  python kg/build_kg.py bridge                跨論典橋接")
        print(f"  python kg/build_kg.py stats                 統計")
        print(f"  python kg/build_kg.py clear T1585            清除")

    neo.close()


if __name__ == "__main__":
    main()
