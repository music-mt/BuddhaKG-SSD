"""
corpora/base.py — 語料定義基礎類
所有佛典語料集繼承此類，確保統一介面
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TextDef:
    """單一文本定義"""
    work_id: str
    title: str
    title_en: str
    juans: int
    role: str
    school: str
    tradition: str = "chinese"
    char_count: Optional[int] = None
    translator: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RelationDef:
    """知識圖譜關係類型定義"""
    name: str
    name_en: str
    directed: bool = True
    doctrinal: bool = True
    description: str = ""


@dataclass
class CorpusDef:
    """語料集定義基礎類"""

    name: str
    name_zh: str
    name_en: str
    description: str = ""

    texts: Dict[str, TextDef] = field(default_factory=dict)
    ssd_works: List[str] = field(default_factory=list)
    target_terms: List[str] = field(default_factory=list)
    seed_terms: List[str] = field(default_factory=list)
    relation_types: List[RelationDef] = field(default_factory=list)
    extra_stopwords: List[str] = field(default_factory=list)
    kg_blacklist: List[str] = field(default_factory=list)

    def get_all_work_ids(self) -> List[str]:
        return list(self.texts.keys())

    def get_ssd_work_ids(self) -> List[str]:
        return self.ssd_works if self.ssd_works else self.get_all_work_ids()

    def get_text(self, work_id: str) -> TextDef:
        if work_id not in self.texts:
            raise KeyError(f"Work ID '{work_id}' 不在語料集 '{self.name}' 中")
        return self.texts[work_id]

    def total_char_count(self) -> int:
        return sum(t.char_count for t in self.texts.values() if t.char_count)

    def total_juans(self) -> int:
        return sum(t.juans for t in self.texts.values())

    def summary_table(self) -> str:
        lines = []
        lines.append(f"語料集：{self.name_zh}（{self.name_en}）")
        lines.append("")
        lines.append(f"{'文本':<20} {'編號':<8} {'卷數':>6} {'字數':>12} {'研究定位':<12}")
        lines.append("-" * 70)
        for wid, t in self.texts.items():
            cc = f"{t.char_count:,}" if t.char_count else "待統計"
            lines.append(f"{t.title:<18} {wid:<8} {t.juans:>6} {cc:>12} {t.role:<12}")
        lines.append("-" * 70)
        total = self.total_char_count()
        lines.append(f"{'合計':<18} {'':<8} {self.total_juans():>6} {total:>12,}")
        return "\n".join(lines)

    def validate(self) -> List[str]:
        errors = []
        if not self.texts:
            errors.append("語料集無任何文本定義")
        for wid in self.ssd_works:
            if wid not in self.texts:
                errors.append(f"SSD 文本 '{wid}' 不在 texts 中")
        for term in self.target_terms:
            if not term:
                errors.append("target_terms 中有空字串")
        seed_set = set(self.seed_terms)
        for term in self.target_terms:
            if term not in seed_set:
                errors.append(f"target_term '{term}' 不在 seed_terms 中")
        return errors
