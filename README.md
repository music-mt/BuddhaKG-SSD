# BuddhaKG-SSD v3.0

**佛典術語跨文本研究的計算框架**
Computational Framework for Cross-Textual Buddhist Terminology Research

整合知識圖譜嵌入（橫向）與 usage-based 語義差異分析（縱向），
以三分類義理驗證框架進行佛典術語的差異定性。

## 核心發現

- **三分類框架**：區分真語義位移、僅語境改變、技術性偽位移
- **系統性背離**：MRR 自動指標與人工義理精確率之間存在系統性分歧
  - v1.2 MRR=0.3712（最高），人工精確率=21%
  - v1.3 MRR=0.3284（較低），人工精確率=74%
- **義理關係純化策略**：語料純化的效益遠高於調整訓練參數

## 快速開始

```bash
pip install -r requirements.txt

# 執行測試
python tests\test_config.py

# 驗證數據一致性
python pipeline.py --validate

# 查看可用語料集
python pipeline.py --list-corpora

# 生成語料統計（論文表一）
python pipeline.py --stats

# 切換語料集
python pipeline.py --corpus tiantai --stats
```

## 擴展至其他佛典

1. 在 `corpora/` 新增語料定義檔
2. 在 `corpora/__init__.py` 註冊
3. 執行 `python pipeline.py --corpus <name> --all`

已定義語料集：
- **yogacara** — 瑜伽行派（Pilot Corpus）
- **tiantai** — 天台宗
- **madhyamaka** — 中觀學派

## Pilot Corpus

| 論典 | Work ID | 卷數 | 字數 |
|------|---------|------|------|
| 解深密經 | T0676 | 5 | 42,325 |
| 瑜伽師地論 | T1579 | 100 | 1,053,602 |
| 成唯識論 | T1585 | 10 | 106,000 |
| 攝大乘論本 | T1594 | 3 | 31,145 |

語料來源：CBETA 數位典藏（2025R3）

## 授權

程式碼：CC BY-NC 4.0
語料：依 CBETA 數位典藏授權條款
