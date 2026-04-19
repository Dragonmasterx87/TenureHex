# TenureHex
**TenureHex** is a Python toolkit for analyzing **academic faculty offer letters** and **candidate CVs** to generate **theoretical success reports** for tenure-track career planning.

<p align="center">
  <img src="tenurehex.png" width="200"/>
</p>

## 🎯 **Why TenureHex?**

Faculty offers get compared informally, but package structures (**startup size**, **protected time**, **salary support**, **carryover rules**) strongly affect academic outcomes. TenureHex turns **unstructured offer letters** into **structured, reproducible comparisons**.

## 🚀 **Quick Start**

```bash
# Install dependencies
pip install pandas numpy matplotlib python-docx pypdf tabulate

# Run analysis
python offer_report_generator.py \
  --cv "Your_CV_2026.docx" \
  --offers "UF_Offer.pdf" "Miami_Offer.docx" "Tulane_Offer.pdf" \
  --outdir "my_report"
```

## 📊 **Complete Output Package**
```
my_report/
├── parsed_offers.csv # Extracted package details
├── parsed_cv_metrics.csv # h-index, citations, pubs, K99/R00
├── r01_annual.png # Annual R01 probabilities
├── r01_cumulative.png # R01 survival curve
├── high_impact_pubs.png # 10-year publication trajectory
├── phd_cumulative.png # Cumulative PhD grads (10yr)
├── phd_annual.png # Annual PhD output curve
├── grants_10yr.png # Cumulative grants trajectory
├── summary_panel.png # 2x2 key metrics dashboard
└── report.md # Executive summary
```

## 🧠 **What It Analyzes**

### **From Offer Letters** (`docx/pdf/txt`):
Base salary

Startup package size

Salary/fringe support

Protected research effort (100% vs mixed)

Carryover flexibility

Formal mentorship language

Tenure clock length


### **From CV**:
Total citations - h-index

First-author papers - Senior-author papers

Total publications - K99/R00 detection


## 💾 **Example Results**

| Institution | **R01 Yr5** | **Tenure Yr7** | **PhDs Yr10** | **High-IF Pubs** | **Total Grants** |
|-------------|-------------|----------------|---------------|------------------|------------------|
| **UF**      | **87%**     | **95%**        | **11**        | **28**           | **7**            |
| **Miami**   | **80%**     | **95%**        | **9**         | **27**           | **6**            |
| **Tulane**  | **31%**     | **92%**        | **5**         | **15**           | **3**            |

## 🔧 **Customization**

Edit `model_outputs()` for:
- **Field-specific NIH paylines**
- **Trainee vs publication-heavy** criteria  
- **Private vs public** expectations
- **R01 vs program project** priorities

## 🏗️ **Repository Structure**
```
tenurehex/
├── offer_report_generator.py
├── README.md
├── LICENSE
└── assets/
└── tenurehex.png
```


## 📱 **Roadmap**

- [ ] YAML config for field-specific weights
- [ ] Automatic PDF report export
- [ ] Web UI (drag+drop)
- [ ] Public faculty benchmarking

## ⚖️ **License**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

*🔷 Structured analysis for unstructured offers 🔷*

**⭐ Star if helpful!** **[Run your offers now →](#quick-start)**
