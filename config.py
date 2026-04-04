"""
config.py — BuddhaKG-SSD v3.0 統一設定檔

設計原則：
  1. 語料定義與分析邏輯分離（語料在 corpora/*.py）
  2. 版本追蹤內建（KGE_VERSIONS）
  3. 三分類框架前置（TRI_CLASS_DEFINITIONS）
  4. 單一真理來源（論文引用數字由 verify 自動比對）
"""

import os
from pathlib import Path

import corpora

# ── 路徑設定 ──────────────────────────────────────────────────

PROJECT_DIR   = Path(os.environ.get("BUDDHAKGSSD_DIR", "C:/buddhakgssd_v3"))
BUDDHA_DIR    = Path(os.environ.get("BUDDHANL_DIR", "C:/buddha"))
BUDDHASSD_DIR = Path(os.environ.get("BUDDHASSD_DIR", "C:/buddhassd"))

CORPUS_CACHE_DIR = BUDDHA_DIR / "corpus_cache"
USAGE_DIR        = PROJECT_DIR / "usage_corpus"
EMBED_DIR        = PROJECT_DIR / "embeddings"
CLUSTER_DIR      = PROJECT_DIR / "clusters"
KWIC_DIR         = PROJECT_DIR / "kwic_results"
KG_DIR           = PROJECT_DIR / "kg_output"
QA_DIR           = PROJECT_DIR / "qa_output"
REPORT_DIR       = PROJECT_DIR / "reports"
LOG_DIR          = PROJECT_DIR / "logs"

DICT_FILE = PROJECT_DIR / "utils" / "buddhist_dict.txt"

# ── Neo4j 設定 ────────────────────────────────────────────────

NEO4J_URI  = os.environ.get("NEO4J_URI",  "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "")

# ── CBETA API ─────────────────────────────────────────────────

CBETA_BASE = "https://cbdata.dila.edu.tw/stable"

# ── 語料集 ────────────────────────────────────────────────────

ACTIVE_CORPUS_NAME = os.environ.get("BUDDHAKGSSD_CORPUS", "yogacara")

def load_corpus(name: str = None):
    return corpora.load(name or ACTIVE_CORPUS_NAME)

# ── KGE 版本追蹤 ─────────────────────────────────────────────

KGE_VERSIONS = {
    "v1.0": {
        "desc": "混合實體策略", "triples": 142218, "entities": 23564,
        "mrr": 0.0000, "hits1": 0.0000, "hits10": 0.0000,
        "human_prec": None,
        "note": "實體規模過大",
    },
    "v1.1": {
        "desc": "純 Term ID（帶 work 前綴）", "triples": 52855, "entities": 1801,
        "mrr": 0.0198, "hits1": None, "hits10": 0.0208,
        "human_prec": None,       # ⚠️ 未實測
        "note": "ID 粒度過細",
    },
    "v1.2": {
        "desc": "跨論典術語合併", "triples": 17604, "entities": 237,
        "mrr": 0.3712,            # ✅ MRR 最高版本
        "hits1": 0.3486, "hits3": 0.3616, "hits10": 0.4009,
        "human_prec": 0.21,       # ✅ 21%
        "note": "MRR 最高，但語境錯位",
    },
    "v1.3": {
        "desc": "雜訊過濾 + 語料純化", "triples": 13023, "entities": 201,
        "mrr": 0.3284,            # ✅ MRR 低於 v1.2
        "hits1": 0.2869, "hits3": 0.3226, "hits10": 0.4086,
        "human_prec": 0.74,       # ✅ 74%
        "note": "系統性背離核心證據",
    },
}

CURRENT_KGE_VERSION = "v1.3"

# ── 三分類框架定義 ────────────────────────────────────────────

TRI_CLASS_DEFINITIONS = {
    "genuine_shift": {
        "zh": "真語義位移", "en": "Genuine Semantic Shift",
        "definition": "術語在不同文本中的概念功能、義理位置或解釋範圍出現穩定且可解釋的變化",
        "criteria": {
            "statistical": "聚類結果呈現特定論典獨佔群組",
            "structural": "知識圖譜存在 EVOLVES_INTO 或方向性橋接",
            "textual": "KWIC 驗證顯示義理框架根本不同",
        },
    },
    "contextual_variation": {
        "zh": "僅語境改變", "en": "Contextual Variation Only",
        "definition": "術語核心義涵未發生實質改變，差異主要反映論述焦點或搭配詞的轉移",
        "criteria": {
            "statistical": "聚類高度混合，輪廓係數低（< 0.40）",
            "structural": "DOCTRINAL_PARALLEL 橋接穩定",
            "textual": "KWIC 驗證顯示核心定義一致",
        },
    },
    "pseudo_shift": {
        "zh": "技術性偽位移", "en": "Technical Pseudo-shift",
        "definition": "模型偵測到的差異實際上來自資料品質、分詞錯誤或語境污染",
        "criteria": {
            "statistical": "離群樣本過多或聚類結構不穩定",
            "structural": "知識圖譜候選邊的義理方向錯置",
            "textual": "KWIC 發現異常或已識別雜訊類型",
        },
    },
}

# ── 已確認分類結果 ────────────────────────────────────────────

CONFIRMED_CLASSIFICATIONS = {
    "阿賴耶識": {"class": "genuine_shift", "subtype": "局部語義位移",
                  "note": "核心穩定但局部擴展"},
    "種子":     {"class": "contextual_variation", "subtype": None,
                  "note": "核心義涵穩定，搭配語境差異"},
    "習氣":     {"class": "genuine_shift", "subtype": "完全語義位移",
                  "note": "從修行障礙到識論功能單位"},
    "依他起":   {"class": "contextual_variation", "subtype": None,
                  "note": "三性架構核心元素，定義穩定"},
    "轉依":     {"class": "genuine_shift", "subtype": "三重語義位移",
                  "note": "修行方向→修行位階→本體轉換"},
}

# ── RotatE 訓練參數 ───────────────────────────────────────────

ROTATE_CONFIG = {
    "epochs": 500, "dim": 256, "neg_samples": 64,
    "model": "RotatE", "optimizer": "Adam", "lr": 0.001,
}

# ── SSD 分析參數 ──────────────────────────────────────────────

WINDOW_SIZE  = 60
MAX_USAGE    = 200
TARGET_USAGE = 150
VOCAB_SIZE   = 200
K_RANGE      = range(2, 6)

# ── 古漢語停用詞 ─────────────────────────────────────────────

BASE_STOPWORDS = set([
    "之", "也", "者", "所", "而", "以", "於", "其", "為", "則",
    "有", "是", "此", "若", "即", "故", "謂", "云", "及", "與",
    "彼", "諸", "亦", "乃", "非", "無", "不", "得", "能", "應",
    "當", "復", "又", "更", "由", "從", "在", "中", "上", "下",
])

def get_stopwords(corpus_name: str = None) -> set:
    stops = BASE_STOPWORDS.copy()
    try:
        c = load_corpus(corpus_name)
        stops.update(c.extra_stopwords)
    except Exception:
        pass
    return stops
