"""
corpora/__init__.py — 語料集註冊表
"""

import importlib
from typing import Dict, List
from .base import CorpusDef

_REGISTRY: Dict[str, str] = {
    "yogacara": "corpora.yogacara",
    "tiantai": "corpora.tiantai",
    "madhyamaka": "corpora.madhyamaka",
}


def load(name: str) -> CorpusDef:
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(f"未知語料集 '{name}'，可用語料集：{available}")
    module = importlib.import_module(_REGISTRY[name])
    corpus = module.build()
    errors = corpus.validate()
    if errors:
        raise ValueError(f"語料集 '{name}' 驗證失敗：\n" + "\n".join(errors))
    return corpus


def list_available() -> List[str]:
    return list(_REGISTRY.keys())


def register(name: str, module_path: str):
    _REGISTRY[name] = module_path
