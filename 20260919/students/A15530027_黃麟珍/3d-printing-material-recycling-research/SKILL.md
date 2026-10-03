---
name: 3d-printing-material-recycling-research
description: >-
  Research and analyze 3D printing material recycling across FDM/FFF, vat photopolymerization (SLA/DLP),
  powder bed fusion (SLS/SLM), composites (CFRTP), and metal powders. Collect empirical data, standards,
  and SDS/TDS; distinguish measured evidence from claims; evaluate thermal-mechanical degradation across
  recycle cycles; and generate structured evidence matrices and feasibility gap assessments.
---

# 3D 列印材料回收與再生研究 (3D Printing Material Recycling Research)

本技能提供積層製造（3D 列印）廢料、殘料及支撐材之回收、改性與再生研究的標準化工作流程。透過結構化資料萃取、嚴格證據分級、熱機械降解分析與資料缺口辨識，產出具備學術與工程可信度的研究報告與證據矩陣。

## 涵蓋製程與材料範疇

1. **熱熔沉積成型 (FDM / FFF)**：
   - 常見熱塑性塑料：PLA、PETG、ABS、ASA、TPU、PC、PA（尼龍）。
   - 再生路徑：列印廢件與支撐材粉碎粒化、單/雙螺桿擠出拉絲（Filament Extrusion）、混摻原生料（Virgin Blend）。
2. **光固化技術 (SLA / DLP / LCD)**：
   - 光敏聚合物（Photopolymer Resin）：洗淨廢液殘醇回收、未固化廢液分離、固化支撐廢料熱裂解（Pyrolysis）或填料化應用。
3. **粉末床熔融 (PBF / SLS / SLM / DMLS)**：
   - 高分子粉床（如 PA12、PA11、TPU）：溢粉再篩分（Refresh / Mix Ratio）、老化特性（Orange Peel、MFI 衰退）。
   - 金屬粉末（如 316L、Ti6Al4V、AlSi10Mg）：篩分循環次數、顆粒球形度、氧/氮雜質吸附、流動性（Hall Flow）。
4. **複合材料 (Continuous / Chopped Fiber Composites)**：
   - 碳纖維/玻璃纖維增強熱塑性塑膠（CFRTP / GFRTP）：重複熔融造粒之纖維長度折損（Fiber Length Attrition）與界面結合強度。

---

## 權威來源階層 (Source Hierarchy)

萃取資料時，依循以下優先順序進行驗證與引用：

- **Tier 1 (最高權威 - 同儕審查與標準)**：
  - 同儕審查學術期刊論文（需標註 DOI、期刊名、年份，如 *Additive Manufacturing*, *Journal of Cleaner Production*, *Polymer Degradation and Stability*）。
  - 國際/國家標準：ISO/ASTM 52900 系列、ISO/ASTM 52907、ISO/ASTM 52920、ASTM D638、ASTM D790、ISO 1133、ISO 14040/14044（LCA）。
- **Tier 2 (法規與公部門文件)**：
  - 歐盟 REACH / RoHS、美國 EPA、OSHA、台灣環境部廢棄物再利用相關規範。
- **Tier 3 (製造商技術規格)**：
  - 原廠技術數據表（TDS）、安全資料表（SDS / MSDS）。
- **Tier 4 (實務社群與開源專案)**：
  - Precious Plastic、RepRap 社群、知名製造者實測紀錄（必須明確標註為「社群實務經驗」，不可混同於學術實測）。

---

## 證據分級機制 (Evidence Categorization)

所有性能數據與結論必須標記其證據等級：

| 證據等級 | 英文代碼 | 認定標準 | 引用規則 |
|---|---|---|---|
| **實測數據** | `EMPIRICAL` | 遵循標準測試方法（如 ASTM/ISO），具體標明樣品數（n≥3）、試驗條件與標準差。 | 可作為性能衰退曲線的主要依據 |
| **推估/模擬** | `MODELLED` | 來自動力學模型、分子動力學模擬、熱力學外推或生命週期評估估算值。 | 需清楚揭示模型假設與邊界條件 |
| **廠商/行銷宣稱**| `CLAIMED` | 來自商業宣傳單、設備商廣告或無第三方認證之專利規格。 | 僅列作參考，不可直接視為定論 |

---

## 標準研究與執行流程

### 步驟 1：確認研究標的與邊界
明確記錄使用者指定的以下參數：
- 目標材料與原始規格（如 NatureWorks Ingeo 4043D PLA）。
- 成型技術（FDM/SLS/SLA 等）。
- 循環世代（Generation G0 代表原生料，G1~Gn 代表重複加工次數）或再生掺合比（Recycled Content %）。
- 終端用途與性能要求（非結構件、承重結構件、戶外耐候等）。

### 步驟 2：核心維度檢索與數據萃取
詳細調閱並比對文獻，涵蓋以下五大面向：
1. **熱機械性能變化**：
   - 拉伸強度（Tensile Strength, MPa）與斷裂伸長率（Elongation at Break, %）。
   - 熔融流動指數（MFI / MFR, g/10min）與分子量（Mn, Mw）。
   - 熱性質變化（玻璃轉移溫度 Tg, 熔點 Tm, 熱重分析 TGA 熱分解溫度）。
2. **加工工藝與參數**：
   - 粉碎粒徑分佈、乾燥條件（溫度/時間/露點）、擠出溫度設定與螺桿剪切歷史。
3. **降解與雜質控制**：
   - 熱降解、水解（Hydrolysis）、光氧化及色素/異材質交叉污染。
4. **安全、健康與法規 (EHS)**：
   - 熱加工 VOCs 與超細微粒（UFP）釋放量、粉塵爆炸風險（金屬/高分子微粉）。
5. **環境與經濟效益**：
   - LCA 碳足跡減排量（kg CO2-eq/kg）、能耗與設備投資門檻。

### 步驟 3：執行結構化工具
使用隨附的 Python 工具 `scripts/evidence_collector.py` 處理數據：
1. 建立或更新研究資料 JSON。
2. 執行校驗與保留率計算：
   ```bash
   python scripts/evidence_collector.py calculate --input data.json
   ```
3. 匯出 Markdown 證據矩陣與缺口分析：
   ```bash
   python scripts/evidence_collector.py export --input data.json --format markdown
   ```
4. 查閱詳細規範時參考 [references/evidence-matrix-schema.md](references/evidence-matrix-schema.md) 與 [references/material-recycling-profiles.md](references/material-recycling-profiles.md)。

### 步驟 4：輸出標準研究報告
報告必須包含：
1. **研究摘要與材料識別**
2. **結構化證據矩陣 (Evidence Matrix)**（含證據等級、DOI 來源）
3. **性能保留率分析（Retention Rate %）與衰減機理**
4. **可行工藝流程建議與關鍵參數管制點**
5. **技術成熟度與可行性分級 (TRL 1~9)**
6. **關鍵資料缺口 (Data Gaps)**：指出當前缺乏哪些實測數據（如缺少長期蠕變疲勞數據、缺少 G3 以上降解曲線等）。

---

## 邊界與限制

1. **安全第一**：涉及高反應性金屬粉末（如鋁、鈦）回收處理時，必須強調防爆（ATEX/NFPA）與惰性氣體保護；涉及光固化清洗液蒸餾時，提示防爆及有機溶劑吸入防護。
2. **禁用領域提醒**：未經完整生物相容性（ISO 10993）或食品接觸（FDA 21 CFR）重新驗證之再生料，一律嚴禁標示為醫療級或食品級應用。
3. **無保證報價與量產保證**：本技能產出之數據為研發及製程評估參考，實際量產良率須經現場小批量打樣確認。
