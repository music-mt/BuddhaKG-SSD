"""
corpora/tiantai.py — 天台宗語料定義（擴展示範）
"""

from .base import CorpusDef, TextDef, RelationDef


def build() -> CorpusDef:

    return CorpusDef(
        name="tiantai",
        name_zh="天台宗",
        name_en="Tiantai",
        description="以智顗三大部為核心的天台宗教判與止觀體系",

        texts={
            "T1911": TextDef(
                work_id="T1911", title="摩訶止觀",
                title_en="Mohe Zhiguan",
                juans=10, role="core", school="tiantai",
            ),
            "T1716": TextDef(
                work_id="T1716", title="法華玄義",
                title_en="Fahua Xuanyi",
                juans=10, role="core", school="tiantai",
            ),
            "T1718": TextDef(
                work_id="T1718", title="法華文句",
                title_en="Fahua Wenju",
                juans=10, role="elaboration", school="tiantai",
            ),
            "T0262": TextDef(
                work_id="T0262", title="妙法蓮華經",
                title_en="Saddharmapuṇḍarīka-sūtra",
                juans=7, role="source", school="tiantai",
                translator="鳩摩羅什",
            ),
        },

        ssd_works=["T1911", "T1716", "T1718"],
        target_terms=["一念三千", "三諦", "止觀", "實相", "性具"],
        seed_terms=[
            "一念三千", "三諦", "三觀", "止觀", "實相",
            "性具", "圓教", "藏教", "通教", "別教",
            "五時八教", "十如是", "佛性", "法界",
            "煩惱即菩提", "生死即涅槃", "中道",
        ],
        relation_types=[
            RelationDef("DOCTRINAL_PARALLEL", "教義平行", directed=False, doctrinal=True),
            RelationDef("EVOLVES_INTO", "義理演化", directed=True, doctrinal=True),
            RelationDef("SYSTEMATIZES", "體系化", directed=True, doctrinal=True),
            RelationDef("PRECEDES", "前後繼承", directed=True, doctrinal=False),
            RelationDef("CO_OCCURS_IN_JUAN", "同卷共現", directed=False, doctrinal=False),
        ],
        kg_blacklist=[
            "如何", "云何", "何等", "不能", "永不",
            "是故", "如是", "是名", "一切", "一分",
        ],
    )
