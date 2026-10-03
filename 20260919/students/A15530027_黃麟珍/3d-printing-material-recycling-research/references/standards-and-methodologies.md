# 3D 列印材料回收研究標準與方法論 (Standards & Methodologies)

本手冊彙整積層製造與高分子/金屬材料回收測試中適用的國際標準（ISO / ASTM）、測試方法及文獻品質審查準則。

---

## 1. 測試標準對照表

進行性能衰減分析與文獻比對時，必須核對文獻採用的測試標準：

### A. 機械性能測試 (Mechanical Testing)
| 特性項目 | ASTM 標準 | ISO 標準 | 試片規格與注意事項 |
|---|---|---|---|
| **拉伸強度與伸長率** | ASTM D638 | ISO 527-1 / 527-2 | 常見為 Type I 或 Type IV 啞鈴試片；注意列印方向（X/Y 平躺 vs Z 軸直立）。 |
| **彎曲強度與模數** | ASTM D790 | ISO 178 | 三點彎曲試驗；需固定跨距（Span-to-depth ratio）。 |
| **懸臂樑衝擊強度 (Izod)** | ASTM D256 | ISO 180 | 需註明有無缺口（Notched vs Unnotched）。 |
| **簡支樑衝擊強度 (Charpy)**| ASTM D6110 | ISO 179 | 常用於脆性與韌性轉變溫度評估。 |
| **層間結合剪切強度** | ASTM D3163 | ISO 4587 | 用於評估 FDM 絲層間之黏著力（Interlayer adhesion）。 |

### B. 熱性質與流變性能 (Thermal & Rheological)
| 特性項目 | ASTM 標準 | ISO 標準 | 物理意義與回收指標 |
|---|---|---|---|
| **熔融流動指數 (MFI/MFR)** | ASTM D1238 | ISO 1133 | 評估高分子分子量降解。MFI 劇增通常代表分子鏈斷裂。 |
| **差示掃描量熱法 (DSC)** | ASTM D3418 | ISO 11357 | 測量玻璃轉移溫度（Tg）、熔點（Tm）與結晶度（Xc %）。 |
| **熱重分析 (TGA)** | ASTM E1131 | ISO 11358 | 測量初始分解溫度（Td 5%）與灰分/填料含量。 |
| **凝膠滲透色譜 (GPC/SEC)** | ASTM D5296 | ISO 16014 | 直接定量數均分子量（Mn）、重均分子量（Mw）及多分散指數（PDI）。 |

### C. 粉末特性 (Powder Bed Fusion - SLS / SLM)
| 特性項目 | 適用標準 | 說明 |
|---|---|---|
| **粉末整體特性規範** | ISO/ASTM 52907 | 定義積層製造金屬與高分子粉末的取樣、粒徑與化學純度。 |
| **流動速率 (Hall Flow)** | ASTM B213 / ISO 4490 | 評估重覆使用後球形度劣化與流動性變化。 |
| **鬆裝密度 / 振實密度** | ASTM B212 / ASTM B527 | 充填密度影響粉床鋪粉均勻度與燒結孔隙率。 |
| **粒徑分佈 (PSD)** | ISO 13320 (雷射繞射) | 觀察多次回收後細粉流失或粗顆粒團聚現象。 |

### D. 環境生命週期評估 (LCA)
- **ISO 14040 / ISO 14044**：規範生命週期評估之架構與清冊分析。
  - 系統邊界通常定義為：Cradle-to-Grave（搖籃到墳墓）或 Cradle-to-Gate（搖籃到大門）。
  - 再生評估指標首重 **GWP（全球暖化潛勢，kg CO2-eq）** 與 **CED（累積能量需求，MJ）**。

---

## 2. 證據可信度審查原則

在將文獻數據登錄至證據矩陣前，依以下判準檢核：

1. **實測數據 (EMPIRICAL) 准入門檻**：
   - 必須註明測試標準代號（如 ASTM D638）。
   - 樣本數（Sample Size, $n$）不得少於 3 組（推薦 $n \ge 5$），且應附帶平均值與標準差（Mean ± SD）。
   - 必須有明確對照組（Baseline / G0 原始料）。
   - 列印方向（Print Orientation）需固定且明確標記（水平方向與垂直方向層間結合強度差異可達 40% 以上）。

2. **推估數據 (MODELLED) 審查**：
   - 模型計算式、模擬軟體版本（如 ANSYS, Moldflow）、熱力學假設必須完整說明。
   - 必須註明是否曾以實測數據做校準（Validation）。

3. **廠商宣稱 (CLAIMED) 處理**：
   - 產品標示「100% Recycled PLA」但未提供 TDS 實測拉伸強度或測試條件者，一律歸類為 CLAIMED。
   - 僅記載「強度與原生料無異」而無標準曲線者，標示為宣稱，不可採信為技術論文數據。

---

## 3. 關鍵降解指標計算公式

### A. 性能保留率 (Retention Rate, RR %)
$$RR = \frac{P_{Gn}}{P_{G0}} \times 100\%$$
- $P_{Gn}$：經 $n$ 次回收循環後測得之性能指標（如拉伸強度、斷裂伸長率）。
- $P_{G0}$：原生材料（Generation 0）在相同測試條件下之基準性能。

### B. 分子量降解率 (Molecular Weight Loss, MWL %)
$$MWL = \frac{Mw_{G0} - Mw_{Gn}}{Mw_{G0}} \times 100\%$$

### C. 混摻混合定律 (Rule of Mixtures)
若使用原生料與再生料混合配比（Blend Ratio）：
$$P_{blend} = (1 - w_r) \cdot P_{virgin} + w_r \cdot P_{recycled} \cdot \eta_{compat}$$
- $w_r$：再生料重量百分比（0.0 ~ 1.0）。
- $\eta_{compat}$：相容效率係數（無添加相容劑通常 $\eta \le 1.0$，因界面剪切或微空洞折減）。
