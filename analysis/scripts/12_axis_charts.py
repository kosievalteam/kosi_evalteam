"""4축 도표: fig5 목적×수단(2026 예산 비중 누적막대), fig6 대상유형·내용유형별 2026 예산."""
import os, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.font_manager as fm, argparse
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--out", default="output_bge-m3"); OUT = ap.parse_args().out
for f in ["fonts/NotoSansKR-Regular.otf", "fonts/NotoSansKR-Bold.otf"]: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK KR", "axes.unicode_minus": False, "figure.dpi": 200, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#c9c8c2"})
SURF, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
PAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
a = pd.read_csv(f"{OUT}/axes_assignments.csv"); d = a[(a.year == 2026) & ~a["대분류"].str.startswith("유형화")]
# fig5: 목적 × 수단(상위 7개 + 기타) 예산 비중
ins = d.groupby("수단유형").내역예산.sum().sort_values(ascending=False); keep = list(ins.index[:7]); d["수단g"] = np.where(d["수단유형"].isin(keep), d["수단유형"], "기타")
pv = d.pivot_table(index="대분류", columns="수단g", values="내역예산", aggfunc="sum").fillna(0); pv = pv[keep + (["기타"] if "기타" in pv.columns else [])]
sh = pv.div(pv.sum(1), axis=0) * 100; sh = sh.loc[sh.index[::-1]]
fig, ax = plt.subplots(figsize=(9.5, 5.6)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF); left = np.zeros(len(sh))
for j, c in enumerate(sh.columns):
    ax.barh(sh.index, sh[c], left=left, color=PAL[j % 8] if c != "기타" else "#bdbcb5", label=c, height=0.62, edgecolor=SURF, linewidth=1, zorder=3)
    for i, v in enumerate(sh[c]):
        if v >= 8: ax.text(left[i] + v / 2, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if c != "기타" else TXT)
    left += sh[c].values
ax.set_xlim(0, 100); ax.set_xlabel("2026년 예산 비중(%)", fontsize=9); ax.xaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True); ax.tick_params(labelsize=8.5)
h, l = ax.get_legend_handles_labels(); ax.legend(h, [x.split("(")[0] for x in l], frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
fig.text(0.01, 0.975, "지원목적 유형별 지원수단 구성(2026년 예산 기준)", fontsize=12, fontweight="bold", color=TXT, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(f"{OUT}/fig5_purpose_x_instrument.png"); plt.close(fig)
# fig6: 대상유형·내용유형 2026 예산(조원) 가로막대 2패널
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2)); fig.patch.set_facecolor(SURF)
for ax, col, title in zip(axes, ["대상유형", "내용유형"], ["지원대상 유형별", "지원내용 유형별"]):
    s = (d.groupby(col).내역예산.sum() / 1e6).sort_values(); lab = [x.split("(")[0] for x in s.index]
    ax.set_facecolor(SURF); ax.barh(lab, s.values, color="#2a78d6", height=0.6, zorder=3)
    for i, v in enumerate(s.values): ax.text(v + 0.1, i, f"{v:.2f}", va="center", fontsize=8, color=TXT2)
    ax.set_title(f"{title} 2026년 예산(조원)", loc="left", fontsize=10.5, fontweight="bold", color=TXT); ax.xaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True); ax.tick_params(labelsize=8); ax.set_xlim(0, s.max() * 1.18)
fig.tight_layout(); fig.savefig(f"{OUT}/fig6_target_content_budget.png"); plt.close(fig); print("figs saved")
