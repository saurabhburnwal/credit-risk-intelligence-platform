"""Generate ML evaluation plots and diagrams for the presentation PDF."""
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from src.utils.config import BASE_DIR, MODELS_DIR

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10

PLOTS_DIR = BASE_DIR / "notebooks/plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Load metadata
with open(MODELS_DIR / "metadata.json", "r") as f:
    meta = json.load(f)

# 1. Feature Importance Plot
top_feats = meta.get("top_features", [])[:12]
feats = [item["feature"] for item in reversed(top_feats)]
imps = [item["importance"] for item in reversed(top_feats)]

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
bars = ax.barh(feats, imps, color="#1E3E62", edgecolor="#0B192C", height=0.65)
ax.barh(feats[-3:], imps[-3:], color="#00ADB5", edgecolor="#0B192C", height=0.65)  # highlight top 3
for bar in bars:
    w = bar.get_width()
    ax.text(w + 10, bar.get_y() + bar.get_height()/2, f"{int(w)}", va="center", ha="left", fontsize=8, color="#1F2937", fontweight="bold")

ax.set_title("LightGBM Champion — Top 12 Feature Importances", fontsize=12, fontweight="bold", pad=12, color="#0B192C")
ax.set_xlabel("Split Gain Importance", fontsize=10, fontweight="bold", color="#374151")
ax.set_xlim(0, max(imps) * 1.15)
plt.tight_layout()
fig.savefig(PLOTS_DIR / "feature_importance.png", dpi=300)
plt.close(fig)
print("Saved feature_importance.png")

# 2. Risk Band Distribution Plot
bands = ["Low Risk\n(<5% prob)", "Medium Risk\n(5% - 15% prob)", "High Risk\n(≥15% prob)"]
applicant_shares = [50.9, 35.7, 13.4]
default_rates = [2.67, 9.08, 25.90]

x = np.arange(len(bands))
width = 0.35

fig, ax1 = plt.subplots(figsize=(8, 4.2), dpi=300)
color1 = "#1E3E62"
rects1 = ax1.bar(x - width/2, applicant_shares, width, label="% of Applicant Population", color=color1, alpha=0.9)
ax1.set_ylabel("% of Total Applicants", color=color1, fontweight="bold")
ax1.set_ylim(0, 65)

ax2 = ax1.twinx()
color2 = "#E63946"
rects2 = ax2.bar(x + width/2, default_rates, width, label="Observed Default Rate (%)", color=color2, alpha=0.9)
ax2.set_ylabel("Observed Default Rate (%)", color=color2, fontweight="bold")
ax2.set_ylim(0, 35)

ax1.set_xticks(x)
ax1.set_xticklabels(bands, fontweight="bold", color="#111827")
ax1.set_title("Risk Band Separation: Applicant Volume vs. Realized Default Rate", fontsize=12, fontweight="bold", pad=12, color="#0B192C")

# Annotations
for r in rects1:
    h = r.get_height()
    ax1.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color=color1)

for r in rects2:
    h = r.get_height()
    ax2.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color=color2)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)
plt.tight_layout()
fig.savefig(PLOTS_DIR / "risk_band_distribution.png", dpi=300)
plt.close(fig)
print("Saved risk_band_distribution.png")

# 3. Confusion Matrix Plot
cm = np.array(meta["benchmarks"]["lightgbm_champion"]["confusion_matrix"])
labels = ["Non-Default (0)", "Default (1)"]

fig, ax = plt.subplots(figsize=(6, 4.2), dpi=300)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
            xticklabels=labels, yticklabels=labels,
            annot_kws={"size": 11, "weight": "bold"})
ax.set_title("LightGBM Champion Test Confusion Matrix (N = 61,503)", fontsize=11, fontweight="bold", pad=10, color="#0B192C")
ax.set_xlabel("Predicted Label", fontweight="bold", color="#374151")
ax.set_ylabel("True Label", fontweight="bold", color="#374151")
plt.tight_layout()
fig.savefig(PLOTS_DIR / "confusion_matrix.png", dpi=300)
plt.close(fig)
print("Saved confusion_matrix.png")
