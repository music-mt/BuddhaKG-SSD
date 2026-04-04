"""
tests/test_config.py — 27 項數據一致性測試
python tests\test_config.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import corpora


class TestKGEVersions:
    def test_v12_mrr(self):
        assert config.KGE_VERSIONS["v1.2"]["mrr"] == 0.3712
    def test_v13_mrr(self):
        assert config.KGE_VERSIONS["v1.3"]["mrr"] == 0.3284
    def test_systematic_divergence(self):
        v12, v13 = config.KGE_VERSIONS["v1.2"], config.KGE_VERSIONS["v1.3"]
        assert v12["mrr"] > v13["mrr"]
        assert v12["human_prec"] < v13["human_prec"]
    def test_v12_human_prec(self):
        assert config.KGE_VERSIONS["v1.2"]["human_prec"] == 0.21
    def test_v13_human_prec(self):
        assert config.KGE_VERSIONS["v1.3"]["human_prec"] == 0.74
    def test_v11_no_human_prec(self):
        assert config.KGE_VERSIONS["v1.1"]["human_prec"] is None
    def test_v10_no_human_prec(self):
        assert config.KGE_VERSIONS["v1.0"]["human_prec"] is None


class TestTriClassification:
    def test_three_classes(self):
        assert len(config.TRI_CLASS_DEFINITIONS) == 3
    def test_class_keys(self):
        assert set(config.TRI_CLASS_DEFINITIONS.keys()) == \
               {"genuine_shift", "contextual_variation", "pseudo_shift"}
    def test_criteria_layers(self):
        for cls_key, cls_def in config.TRI_CLASS_DEFINITIONS.items():
            for layer in ["statistical", "structural", "textual"]:
                assert layer in cls_def["criteria"], f"{cls_key} 缺少 {layer}"
    def test_five_confirmed(self):
        assert len(config.CONFIRMED_CLASSIFICATIONS) == 5
    def test_xiqi(self):
        assert config.CONFIRMED_CLASSIFICATIONS["習氣"]["class"] == "genuine_shift"
    def test_zhuanyi(self):
        assert config.CONFIRMED_CLASSIFICATIONS["轉依"]["class"] == "genuine_shift"
    def test_yitaqi(self):
        assert config.CONFIRMED_CLASSIFICATIONS["依他起"]["class"] == "contextual_variation"
    def test_zhongzi(self):
        assert config.CONFIRMED_CLASSIFICATIONS["種子"]["class"] == "contextual_variation"


class TestCorpusDefinitions:
    def test_yogacara_loads(self):
        assert corpora.load("yogacara").name == "yogacara"
    def test_four_texts(self):
        assert len(corpora.load("yogacara").texts) == 4
    def test_char_counts(self):
        c = corpora.load("yogacara")
        assert c.texts["T0676"].char_count == 31145
        assert c.texts["T1579"].char_count == 1053602
        assert c.texts["T1585"].char_count == 106000
        assert c.texts["T1594"].char_count == 31145
    def test_five_terms(self):
        assert len(corpora.load("yogacara").target_terms) == 5
    def test_terms_in_seeds(self):
        c = corpora.load("yogacara")
        seed_set = set(c.seed_terms)
        for t in c.target_terms:
            assert t in seed_set
    def test_validates(self):
        assert len(corpora.load("yogacara").validate()) == 0
    def test_tiantai(self):
        assert corpora.load("tiantai").name == "tiantai"
    def test_madhyamaka(self):
        assert corpora.load("madhyamaka").name == "madhyamaka"
    def test_all_validate(self):
        for name in corpora.list_available():
            assert len(corpora.load(name).validate()) == 0
    def test_unknown_raises(self):
        try:
            corpora.load("nonexistent")
            assert False
        except ValueError:
            pass


class TestPaperTable1:
    def test_not_rounded(self):
        c = corpora.load("yogacara")
        wrong = {18000, 650000, 80000, 25000}
        for t in c.texts.values():
            assert t.char_count not in wrong
    def test_t1579_over_1m(self):
        assert corpora.load("yogacara").texts["T1579"].char_count > 1000000


if __name__ == "__main__":
    total = passed = failed = 0
    for cls in [TestKGEVersions, TestTriClassification, TestCorpusDefinitions, TestPaperTable1]:
        inst = cls()
        for m in [x for x in dir(inst) if x.startswith("test_")]:
            total += 1
            try:
                getattr(inst, m)()
                passed += 1
                print(f"  ✅ {cls.__name__}.{m}")
            except Exception as e:
                failed += 1
                print(f"  ❌ {cls.__name__}.{m}: {e}")
    print(f"\n{'=' * 50}")
    print(f"  總計：{total}  通過：{passed}  失敗：{failed}")
    print(f"{'=' * 50}")
