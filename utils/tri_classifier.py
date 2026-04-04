"""
utils/tri_classifier.py — 三分類義理驗證框架判定引擎
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass
class StatisticalEvidence:
    silhouette_score: Optional[float] = None
    dominant_cluster_ratio: Optional[float] = None
    cross_text_similarity: Optional[float] = None
    cluster_count: Optional[int] = None
    usage_count: Optional[int] = None
    notes: str = ""

    @property
    def signal_strength(self) -> str:
        if self.silhouette_score is None:
            return "insufficient"
        if self.silhouette_score >= 0.50:
            return "strong"
        elif self.silhouette_score >= 0.35:
            return "moderate"
        return "weak"


@dataclass
class StructuralEvidence:
    a_grade_edges: int = 0
    evolves_into_found: bool = False
    doctrinal_parallel_found: bool = False
    direction_consistent: bool = True
    edge_details: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class KWICEvidence:
    framework_different: bool = False
    core_definition_stable: bool = True
    noise_detected: bool = False
    representative_examples: List[str] = field(default_factory=list)
    reviewer: str = ""
    review_date: str = ""
    notes: str = ""


@dataclass
class ClassificationResult:
    term: str
    classification: str
    classification_zh: str
    subtype: Optional[str] = None
    confidence: str = "low"
    stat_evidence: Optional[StatisticalEvidence] = None
    struct_evidence: Optional[StructuralEvidence] = None
    kwic_evidence: Optional[KWICEvidence] = None
    reasoning: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class TriClassifier:

    CLASS_MAP = {
        "genuine_shift": "真語義位移",
        "contextual_variation": "僅語境改變",
        "pseudo_shift": "技術性偽位移",
    }

    def classify(self, term, stat, struct, kwic) -> ClassificationResult:
        parts = []

        if kwic.noise_detected and not kwic.framework_different:
            cls, confidence = "pseudo_shift", "moderate" if kwic.review_date else "low"
            parts.append("KWIC 發現明確雜訊來源")
        elif (kwic.framework_different and struct.evolves_into_found
              and stat.signal_strength in ("strong", "moderate")):
            cls, confidence = "genuine_shift", "high"
            parts.append("三層證據一致指向概念重構")
        elif kwic.framework_different and (struct.evolves_into_found or stat.signal_strength == "strong"):
            cls, confidence = "genuine_shift", "moderate"
            parts.append("KWIC + 至少一層計算證據支持語義位移")
        elif (kwic.core_definition_stable and stat.signal_strength == "weak"
              and not struct.evolves_into_found):
            cls, confidence = "contextual_variation", "high" if kwic.review_date else "moderate"
            parts.append("核心定義穩定，差異主要在搭配語境")
        elif kwic.core_definition_stable and stat.signal_strength in ("weak", "moderate"):
            cls, confidence = "contextual_variation", "moderate"
            parts.append("核心定義穩定，統計差異不足以判定為位移")
        else:
            cls, confidence = "contextual_variation", "low"
            parts.append("證據層間存在矛盾或不足，暫判為語境改變")

        if stat.signal_strength != "insufficient":
            parts.append(f"統計信號：{stat.signal_strength}（輪廓係數={stat.silhouette_score:.3f}）")
        if struct.a_grade_edges > 0:
            parts.append(f"KG A 級邊：{struct.a_grade_edges} 條")
        if kwic.review_date:
            parts.append(f"人工審查：{kwic.reviewer} ({kwic.review_date})")

        return ClassificationResult(
            term=term, classification=cls, classification_zh=self.CLASS_MAP[cls],
            confidence=confidence, stat_evidence=stat, struct_evidence=struct,
            kwic_evidence=kwic, reasoning="；".join(parts),
            timestamp=datetime.now().isoformat(),
        )

    def batch_classify(self, evidence_map: Dict) -> Dict[str, ClassificationResult]:
        results = {}
        for term, ev in evidence_map.items():
            results[term] = self.classify(
                term,
                ev.get("stat", StatisticalEvidence()),
                ev.get("struct", StructuralEvidence()),
                ev.get("kwic", KWICEvidence()),
            )
        return results

    def save_results(self, results, output_path: Path):
        data = {
            "framework": "tri_classification_v3.0",
            "timestamp": datetime.now().isoformat(),
            "term_count": len(results),
            "results": {t: r.to_dict() for t, r in results.items()},
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def summary_table(self, results) -> str:
        lines = [f"{'術語':<10} {'分類':<12} {'信度':<8} {'推理依據'}", "-" * 80]
        for term, r in results.items():
            lines.append(f"{term:<8} {r.classification_zh:<10} {r.confidence:<6} {r.reasoning[:50]}")
        return "\n".join(lines)
