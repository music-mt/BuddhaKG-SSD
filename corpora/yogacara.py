"""
corpora/yogacara.py — 瑜伽行派語料定義（Pilot Corpus）
"""

from .base import CorpusDef, TextDef, RelationDef


def build() -> CorpusDef:

    return CorpusDef(
        name="yogacara",
        name_zh="瑜伽行派",
        name_en="Yogācāra",
        description="以唯識學為核心的瑜伽行派四部論典",

        texts={
            "T0676": TextDef(
                work_id="T0676", title="解深密經",
                title_en="Saṃdhinirmocana-sūtra",
                juans=5, char_count=42325, role="source",
                school="yogacara", translator="玄奘",
                notes="義理源頭",
            ),
            "T1579": TextDef(
                work_id="T1579", title="瑜伽師地論",
                title_en="Yogācārabhūmi-śāstra",
                juans=100, char_count=1053602, role="core",
                school="yogacara", translator="玄奘",
                notes="體系核心",
            ),
            "T1585": TextDef(
                work_id="T1585", title="成唯識論",
                title_en="Vijñaptimātratāsiddhi",
                juans=10, char_count=106000, role="elaboration",
                school="yogacara", translator="玄奘",
                notes="識論細化",
            ),
            "T1594": TextDef(
                work_id="T1594", title="攝大乘論本",
                title_en="Mahāyānasaṃgraha",
                juans=3, char_count=31145, role="summary",
                school="yogacara", translator="玄奘",
                notes="三性綱要",
            ),
        },

        ssd_works=["T1579", "T1585", "T1594"],

        target_terms=["阿賴耶識", "種子", "習氣", "依他起", "轉依"],

        seed_terms=[
            "阿賴耶識", "末那識", "阿陀那識", "藏識", "異熟識",
            "種子", "現行", "熏習", "習氣", "轉依",
            "依他起", "遍計所執", "圓成實", "真如", "所知依",
            "唯識", "三性", "三無性", "勝義諦",
        ],

        relation_types=[
            RelationDef("DOCTRINAL_PARALLEL", "教義平行",
                        directed=False, doctrinal=True),
            RelationDef("EVOLVES_INTO", "義理演化",
                        directed=True, doctrinal=True),
            RelationDef("SYSTEMATIZES", "體系化",
                        directed=True, doctrinal=True),
            RelationDef("PRECEDES", "前後繼承",
                        directed=True, doctrinal=False),
            RelationDef("CO_OCCURS_IN_JUAN", "同卷共現",
                        directed=False, doctrinal=False),
            RelationDef("CROSS_WORK_CO_OCCURS", "跨論典共現",
                        directed=False, doctrinal=False),
        ],

        extra_stopwords=[
            "何", "如", "或", "雖", "但", "因", "成", "名", "稱", "說",
            "已", "將", "對", "等", "至", "令", "使", "可", "皆", "各",
        ],

        kg_blacklist=[
            "如何", "云何", "何等", "不能", "永不", "由斯", "相故",
            "為業", "是故", "如是", "是名", "十一", "十二", "三種",
            "一切", "一分", "無別", "財團", "資料", "成唯識論",
            "大德", "互相", "展轉", "論說", "大正", "乃至", "一類",
            "不然", "不成", "編輯",
        ],
    )
