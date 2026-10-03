# 結構化證據庫欄位定義與可行性評估標準 (Evidence Matrix Schema)

本文件規範 3D 列印材料回收證據矩陣之標準欄位架構、資料型態、限制條件與可行性技術成熟度（TRL）評估指標。

---

## 1. 證據庫標準欄位架構 (Schema)

證據庫以 JSON 陣列或資料表儲存，每筆紀錄（Record）必須包含以下 16 項標準欄位：

| 欄位名稱 (Field Name) | 資料型別 | 必填 | 說明與範例值 |
|---|---|:---:|---|
| `record_id` | String | 是 | 唯一辨識碼，格式如 `REC-PLA-001`、`REC-SLS-PA12-02`。 |
| `process_type` | String (Enum) | 是 | 製程類別：`FDM/FFF`、`SLA/DLP`、`SLS`、`SLM/DMLS`、`COMPOSITE`。 |
| `material_name` | String | 是 | 材料化學名稱與原廠牌號，例：`PLA (NatureWorks Ingeo 4043D)`。 |
| `recycled_content_pct` | Float | 是 | 再生料掺合重量百分比（0.0 ~ 100.0）。 |
| `cycle_generation` | String | 是 | 回收代數，原生料為 `G0`，一次回收為 `G1`，依此類推。 |
| `additive_or_compatibilizer` | String | 否 | 改性劑或擴鏈劑說明，例：`0.3% Joncryl ADR-4368` 或 `None`。 |
| `tensile_strength_mpa` | Float | 否 | 實測拉伸強度平均值（MPa）。 |
| `tensile_retention_pct` | Float | 否 | 抗拉強度相較 G0 原生料之保留率（%）。 |
| `elongation_at_break_pct`| Float | 否 | 斷裂伸長率平均值（%）。 |
| `elongation_retention_pct`| Float | 否 | 伸長率相較 G0 之保留率（%）。 |
| `melt_flow_index` | Float | 否 | 熔融流動指數（g/10 min），需附帶測試溫度與砝碼重。 |
| `evidence_level` | String (Enum) | 是 | 證據等級：`EMPIRICAL`（實測）、`MODELLED`（推估/模擬）、`CLAIMED`（廠商宣稱）。 |
| `testing_standard` | String | 是 | 測試依據標準，例：`ASTM D638 (Type IV, 5mm/min)`。 |
| `environmental_lca_impact`| String | 否 | 碳排或能源指標，例：`-62% CO2-eq vs virgin pellet`。 |
| `safety_ehs_notes` | String | 否 | 環安衛或危害考量，例：`低 VOC 排放；粉碎作業需配戴 N95 防塵口罩`。 |
| `source_reference` | String | 是 | 文獻來源，優先提供 DOI（如 `DOI: 10.1016/j.addma.2020.101234`）或標準號。 |

---

## 2. 結構化 JSON 格式範例

```json
{
  "study_title": "PLA 列印廢料重複擠出拉絲之機械性能衰退研究",
  "baseline": {
    "material_name": "PLA (Ingeo 4043D)",
    "tensile_strength_mpa": 60.5,
    "elongation_at_break_pct": 5.8,
    "mfi_g_per_10min": 7.2
  },
  "records": [
    {
      "record_id": "REC-PLA-001",
      "process_type": "FDM/FFF",
      "material_name": "PLA (Ingeo 4043D)",
      "recycled_content_pct": 100.0,
      "cycle_generation": "G1",
      "additive_or_compatibilizer": "None",
      "tensile_strength_mpa": 57.2,
      "tensile_retention_pct": 94.5,
      "elongation_at_break_pct": 4.6,
      "elongation_retention_pct": 79.3,
      "melt_flow_index": 11.4,
      "evidence_level": "EMPIRICAL",
      "testing_standard": "ASTM D638 Type IV",
      "environmental_lca_impact": "-64% Cradle-to-gate GWP",
      "safety_ehs_notes": "常規通風，加工溫度不超過 200°C",
      "source_reference": "DOI: 10.1016/j.polymdegradstab.2021.109600"
    }
  ]
}
```

---

## 3. 技術可行性分級標準 (Technology Readiness Levels, TRL 1 ~ 9)

根據文獻中驗證的規模與穩定性，評定該再生路線的技術成熟度：

| 級別區間 | 評級定義 | 特徵與准入條件 | 典型案例 |
|---|---|---|---|
| **TRL 1 ~ 3** | **概念與實驗室驗證 (Lab-scale Concept)** | 僅於實驗室微量樣品測試（<1 kg）；依賴精密儀器（如微型混鍊機），未驗證量產線徑均勻度或連續列印性。 | 光敏樹脂裂解產物添加至新樹脂。 |
| **TRL 4 ~ 6** | **原型試製與小型工坊 (Pilot / Small Fablab)** | 可使用小型單螺桿擠出機（如 3devo, Filastruder）穩定連續拉絲 100m 以上；線徑公差控制在 $\pm 0.05\text{ mm}$ 內；成功完成長時列印驗收。 | 創客空間將 PLA 廢支撐回收再製為 1kg 線材並成功列印外殼。 |
| **TRL 7 ~ 9** | **工業級量產與商業閉環 (Commercial / Industrial)** | 噸級穩定造粒；提供正式材料安全資料表（SDS）與技術數據表（TDS）；通過批次均一性檢驗與長時疲勞老化驗證。 | 商業化 100% 再生 PETG / rPLA 線材品牌（如 Reflow, Formfutura ReFill）。 |

---

## 4. 資料缺口分析判定邏輯 (Data Gap Checklist)

在產出研究結論時，自動掃描以下可能存在的資料死角：

1. **熱歷史與世代模糊**：文獻未載明回收循環次數（僅標註「廢料混合」）。
2. **缺乏基線對照**：無 G0 原生料在同批設備下的基準測試數據。
3. **單一方向測試**：僅測量 X-Y 水平列印試片，缺乏 Z 軸層間結合力數據。
4. **耐久性數據缺失**：缺乏吸濕後抗拉測試、耐候性（UV 耐光）或長期疲勞蠕變數據。
5. **環安衛清冊空白**：缺乏高溫重複熱熔之微粒與揮發性氣體釋放檢測。
