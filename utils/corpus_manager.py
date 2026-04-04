"""
utils/corpus_manager.py — 語料管理模組
CBETA 語料擷取、快取管理與語料驗證
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


class CorpusManager:

    def __init__(self, cache_dir: Path, cbeta_base: str):
        self.cache_dir = Path(cache_dir)
        self.cbeta_base = cbeta_base
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, work_id: str) -> Path:
        return self.cache_dir / f"{work_id}_corpus.json"

    def is_cached(self, work_id: str) -> bool:
        path = self.get_cache_path(work_id)
        if not path.exists():
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            juans = data.get("juans", {})
            if juans:
                first_val = next(iter(juans.values()))
                return isinstance(first_val, str) and len(first_val) > 100
            return False
        except Exception:
            return False

    def load_cached(self, work_id: str) -> Optional[Dict]:
        path = self.get_cache_path(work_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _strip_html(self, html: str) -> str:
        html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*class="lb"[^>]*>[^<]*</span>', '', html)
        html = re.sub(r'<[^>]+>', '', html)
        html = re.sub(r'\[＊\]', '', html)
        html = re.sub(r'\s+', '', html)
        return html.strip()

    def fetch_juan(self, work_id: str, juan: int) -> Optional[str]:
        try:
            import requests
        except ImportError:
            log.error("需安裝 requests：pip install requests")
            return None
        headers = {"Referer": "https://cbetaonline.dila.edu.tw/"}
        url = f"{self.cbeta_base}/juans?work={work_id}&juan={juan}"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            juans = data.get("juans", {})
            if juans:
                text = next(iter(juans.values()))
                if isinstance(text, str) and len(text) > 100:
                    return self._strip_html(text)
            return None
        except Exception as e:
            log.error(f"擷取 {work_id} 卷{juan} 失敗：{e}")
            return None

    def fetch_and_cache(self, work_id: str, total_juans: int,
                        start_juan: int = 1, delay: float = 0.5):
        cache_path = self.get_cache_path(work_id)
        existing = {}
        if cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        juans = existing.get("juans", {})
        total_chars = 0
        for j in range(start_juan, total_juans + 1):
            key = str(j)
            if key in juans and len(juans[key]) > 100:
                total_chars += len(juans[key])
                continue
            log.info(f"  擷取 {work_id} 卷 {j}/{total_juans}...")
            text = self.fetch_juan(work_id, j)
            if text:
                juans[key] = text
                total_chars += len(text)
            time.sleep(delay)
        data = {
            "work_id": work_id, "total_juans": total_juans,
            "juans": juans, "total_chars": total_chars,
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"  ✅ {work_id} 完成，{len(juans)} 卷，{total_chars:,} 字")

    def ensure_cached(self, corpus_def) -> Dict[str, bool]:
        status = {}
        for wid, text_def in corpus_def.texts.items():
            if self.is_cached(wid):
                status[wid] = True
                log.info(f"  ✅ {text_def.title}（{wid}）已快取")
            else:
                status[wid] = False
                log.warning(f"  ⚠️  {text_def.title}（{wid}）未快取")
        return status

    def search_term(self, work_id: str, term: str, window: int = 60) -> List[Dict]:
        results = []
        data = self.load_cached(work_id)
        if not data:
            return results
        for juan_num, text in data.get("juans", {}).items():
            if not isinstance(text, str) or len(text) < 100:
                continue
            start = 0
            while True:
                idx = text.find(term, start)
                if idx == -1:
                    break
                left = max(0, idx - window)
                right = min(len(text), idx + len(term) + window)
                results.append({
                    "work_id": work_id, "juan": int(juan_num),
                    "position": idx,
                    "left_context": text[left:idx],
                    "term": term,
                    "right_context": text[idx + len(term):right],
                })
                start = idx + 1
        return results
