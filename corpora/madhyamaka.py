"""
corpora/madhyamaka.py — 中觀學派語料定義（擴展示範）
"""

from .base import CorpusDef, TextDef, RelationDef


def build() -> CorpusDef:

    return CorpusDef(
        name="madhyamaka",
        name_zh="中觀學派",
        name_en="Madhyamaka",
        description="以龍樹《中論》為核心的中觀學派空觀體系",

        texts={
            "T1564": TextDef(
                work_id="T1564", title="中論",
                title_en="Mūlamadhyamakakārikā",
                juans=4, role="source", school="madhyamaka",
                translator="鳩摩羅什",
            ),
            "T1569": TextDef(
                work_id="T1569", title="十二門論",
                title_en="Dvādaśanikāya-śāstra",
                juans=1, role="summary", school="madhyamaka",
                translator="鳩摩羅什",
            ),
            "T1509": TextDef(
                work_id="T1509", title="大智度論",
                title_en="Mahāprajñāpāramitā-śāstra",
                juans=100, role="core", school="madhyamaka",
                translator="鳩摩羅什",
            ),
            "T1824": TextDef(
                work_id="T1824", title="中觀論疏",
                title_en="Zhongguan Lunshu",
                juans=10, role="elaboration", school="madhyamaka",
            ),
        },

        ssd_works=["T1564", "T1509", "T1824"],
        target_terms=["空", "中道", "二諦", "因緣", "假名"],
        seed_terms=[
            "空", "中道", "二諦", "因緣", "假名",
            "自性", "無自性", "八不", "戲論",
            "勝義諦", "世俗諦", "涅槃", "般若",
            "緣起", "性空", "不生不滅",
        ],
        relation_types=[
            RelationDef("DOCTRINAL_PARALLEL", "教義平行", directed=False, doctrinal=True),
            RelationDef("EVOLVES_INTO", "義理演化", directed=True, doctrinal=True),
            RelationDef("REFUTES", "論破", directed=True, doctrinal=True,
                        description="概念間的破斥與否定關係"),
            RelationDef("PRECEDES", "前後繼承", directed=True, doctrinal=False),
            RelationDef("CO_OCCURS_IN_JUAN", "同卷共現", directed=False, doctrinal=False),
        ],
        kg_blacklist=[
            "如何", "云何", "何等", "不能", "永不",
            "是故", "如是", "是名", "一切", "一分",
        ],
    )
