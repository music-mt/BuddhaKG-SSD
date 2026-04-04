"""
kwic_verify.py — BuddhaSSD Phase 5
針對三分類判斷，抽取代表性 usage 進行 KWIC 驗證
重點術語：習氣（真位移）、轉依（真位移）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

_corpus = config.load_corpus()

import json
import sys
import logging
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, "C:/buddha")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

USAGE_DIR = Path(str(config.USAGE_DIR))
KWIC_DIR = Path(str(config.KWIC_DIR))
KWIC_DIR.mkdir(exist_ok=True)

WORKS = {wid: {"title": t.title, "juans": t.juans}
         for wid, t in _corpus.texts.items()
         if wid in _corpus.get_ssd_work_ids()}

# 重點驗證術語與抽樣策略
VERIFY_PLAN = {
    "習氣": {
        "priority": "高",
        "hypothesis": "真語義位移：T1579煩惱殘餘 vs T1585識的功能差別",
        "sample_per_work": 5,
        "focus_keywords": {
            "T1579": ["煩惱", "隨眠", "永害", "業"],
            "T1585": ["二取", "功能", "熏習", "所熏"],
        }
    },
    "轉依": {
        "priority": "高",
        "hypothesis": "真語義位移：T1579修行目標 vs T1585菩薩十地證得",
        "sample_per_work": 5,
        "focus_keywords": {
            "T1579": ["涅槃", "一切", "當知"],
            "T1585": ["證得", "菩薩", "十地", "藏識"],
            "T1594": ["熏習", "依他起"],
        }
    },
    "依他起": {
        "priority": "中",
        "hypothesis": "僅語境改變：三性架構穩定但T1585側重識變面向",
        "sample_per_work": 3,
        "focus_keywords": {
            "T1579": ["自性", "遍計所執", "圓成實"],
            "T1585": ["分別", "識變", "起性"],
        }
    },
    "阿賴耶識": {
        "priority": "中",
        "hypothesis": "局部語義位移：T1579功能描述 vs T1585修行論脈絡",
        "sample_per_work": 3,
        "focus_keywords": {
            "T1579": ["種子", "轉識", "建立"],
            "T1585": ["成就", "阿羅漢", "自內"],
        }
    },
}

def load_usages(term):
    f = USAGE_DIR / f"{term}_usage.jsonl"
    usages = []
    if f.exists():
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                usages.append(json.loads(line.strip()))
    return usages

def select_representative(usages, work_id, focus_keywords, n=5):
    work_usages = [u for u in usages if u["work"] == work_id]
    if not work_usages:
        return []

    keywords = focus_keywords.get(work_id, [])

    # 優先選含焦點關鍵字的 usage
    scored = []
    for u in work_usages:
        ctx   = u.get("context", "")
        score = sum(1 for kw in keywords if kw in ctx)
        scored.append((score, u))

    scored.sort(key=lambda x: -x[0])
    return [u for _, u in scored[:n]]

def format_kwic(u):
    before = u.get("before", "")[-40:]
    target = u.get("target", "")
    after  = u.get("after",  "")[:40]
    juan   = u.get("juan",   "")
    return f"[{juan}] ...{before}【{target}】{after}..."

def main():
    log.info("=== BuddhaSSD Phase 5：KWIC 驗證 ===\n")
    all_results = {}

    for term, plan in VERIFY_PLAN.items():
        log.info(f"\n══ 術語：「{term}」（優先度：{plan['priority']}）════════")
        log.info(f"  假設：{plan['hypothesis']}")

        usages  = load_usages(term)
        results = {"term": term, "hypothesis": plan["hypothesis"], "by_work": {}}

        for work_id, work_zh in WORKS.items():
            keywords  = plan["focus_keywords"].get(work_id, [])
            n         = plan["sample_per_work"]
            selected  = select_representative(usages, work_id, plan["focus_keywords"], n)

            if not selected:
                log.info(f"\n  {work_zh}（{work_id}）：無樣本")
                continue

            log.info(f"\n  {work_zh}（{work_id}）── 代表性 usage（{len(selected)}筆）")
            log.info(f"  焦點關鍵字：{keywords}")

            kwic_list = []
            for u in selected:
                kwic = format_kwic(u)
                log.info(f"    {kwic}")
                kwic_list.append({
                    "id"     : u["id"],
                    "juan"   : u["juan"],
                    "kwic"   : kwic,
                    "context": u.get("context", ""),
                    "shift_type": "",
                    "note"   : "",
                })

            results["by_work"][work_id] = {
                "work_zh" : work_zh,
                "keywords": keywords,
                "samples" : kwic_list,
            }

        all_results[term] = results

        # 儲存單術語結果
        out = KWIC_DIR / f"{term}_kwic.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log.info(f"\n  ✅ 儲存：{out}")

    # 儲存總結
    with open(KWIC_DIR / "kwic_summary.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    log.info("\n══ KWIC 驗證完成 ════════════════════════════")
    log.info("  下一步：開啟 kwic_results/*.json")
    log.info("  在 shift_type 欄填入：真位移 / 語境差異 / 技術偽位移")
    log.info("  在 note 欄填入義理說明")

if __name__ == "__main__":
    main()
