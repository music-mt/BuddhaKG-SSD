"""
integrate/review_db.py — 審查資料庫
系統性記錄人工義理審查結果
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class ReviewDB:

    def __init__(self, report_dir: Path):
        self.db_file = Path(report_dir) / "review_db.json"
        self.data = self._load()

    def _load(self) -> Dict:
        if self.db_file.exists():
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "3.0", "reviews": {}, "summary": {},
                "created_at": datetime.now().isoformat()}

    def _save(self):
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_review(self, kge_version, edge_id, grade, reasoning,
                   reviewer="", head="", tail="", relation=""):
        if kge_version not in self.data["reviews"]:
            self.data["reviews"][kge_version] = []
        self.data["reviews"][kge_version].append({
            "edge_id": edge_id, "grade": grade.upper(),
            "reasoning": reasoning, "reviewer": reviewer,
            "head": head, "tail": tail, "relation": relation,
            "reviewed_at": datetime.now().isoformat(),
        })
        self._save()

    def compute_precision(self, kge_version: str) -> Optional[Dict]:
        reviews = self.data["reviews"].get(kge_version, [])
        if not reviews:
            return None
        total = len(reviews)
        a_count = sum(1 for r in reviews if r["grade"] == "A")
        b_count = sum(1 for r in reviews if r["grade"] == "B")
        result = {
            "version": kge_version, "total_reviewed": total,
            "a_count": a_count, "b_count": b_count,
            "a_precision": a_count / total if total > 0 else 0,
        }
        self.data["summary"][kge_version] = result
        self._save()
        return result

    def verify_paper_numbers(self, kge_versions: Dict) -> List[str]:
        errors = []
        for ver, ver_config in kge_versions.items():
            claimed = ver_config.get("human_prec")
            if claimed is None:
                continue
            actual = self.compute_precision(ver)
            if actual is None:
                errors.append(f"⚠️  {ver} 聲稱 {claimed:.0%}，但資料庫無記錄")
        return errors
