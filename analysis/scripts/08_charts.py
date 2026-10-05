"""보고서 도표: (1) 대분류별 예산 2024~2026, (2) 임베딩 2차원 지도(대분류별 소다중), (3) 소관×유형 2026 예산 히트맵."""
import os, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.font_manager as fm, argparse
ap = argparse.ArgumentParser(); ap.add_argument("--emb", default="fn"); ap.add_argument("--out", default="output"); args = ap.parse_args(); EMB, OUT = args.emb, args.out
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for f in ["fonts/NotoSansKR-Regular.otf", "fonts/NotoSansKR-Bold.otf"]: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK KR", "axes.unicode_minus": False, "figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#c9c8c2", "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e", "text.color": "#0b0b0b"})
SURF, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
ORD = ["#86b6ef", "#2a78d6", "#104281"]          # 연도(순서형): 참조 팔레트 blue 250/450/650
BLUE, GRAY = "#2a78d6", "#d6d5cf"
a = pd.read_parquet("data/final_assign.parquet" if OUT == "output" else f"data/final_assign_{EMB}.parquet"); E = np.load(f"data/emb_{EMB}.npy"); corp = pd.read_parquet("data/corpus.parquet")
n_all = len(a); a = a[~a["대분류"].str.startswith("유형화 제외")]; n_ex = n_all - len(a)
majors = sorted(a["대분류"].unique())
# ---- 그림1: 대분류별 예산(조원) 2024~2026 가로 막대
piv = a.pivot_table(index="대분류", columns="year", values="내역예산", aggfunc="sum").fillna(0) / 1e6   # 백만원→조원
piv = piv.loc[piv[2026].sort_values().index]
fig, ax = plt.subplots(figsize=(9, 6.2)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
y = np.arange(len(piv)); h = 0.26
for i, yr in enumerate([2024, 2025, 2026]):
    ax.barh(y + (i - 1) * h, piv[yr], height=h - 0.03, color=ORD[i], label=str(yr), zorder=3)
for yi, v in zip(y, piv[2026]): ax.text(v + 0.08, yi + h, f"{v:.2f}", va="center", fontsize=8.5, color=TXT2)
ax.set_yticks(y); ax.set_yticklabels(piv.index, fontsize=9.5); ax.xaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True)
ax.set_xlabel("내역사업 예산 합계(조원)", fontsize=9.5)
fig.text(0.01, 0.975, "지원목적 유형별 중앙부처 내역사업 예산, 2024~2026", fontsize=12, fontweight="bold", color=TXT, va="top")
fig.text(0.01, 0.935, f"값 표시는 2026년. 자료: 정책평가팀 DB(중앙부처 내역사업 2,189건) 기준 유형 배정, 목적 서술 불충분 {n_ex}건은 제외", fontsize=8.5, color=TXT2, va="top")
ax.legend(frameon=False, fontsize=9, loc="lower right", title="연도", title_fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.91)); fig.savefig(f"{OUT}/fig1_budget_by_type.png"); plt.close(fig)
# ---- 그림2: 2차원 지도(t-SNE) 소다중 — 패널마다 해당 유형만 강조
from sklearn.manifold import TSNE
Z = TSNE(2, perplexity=35, init="pca", random_state=0).fit_transform(E); np.save(f"data/tsne_{EMB}.npy", Z)
m = corp[["id"]].merge(a[["id", "대분류"]], on="id", how="left")["대분류"].fillna("(제외)").values
fig, axes = plt.subplots(2, 4, figsize=(13, 6.4)); fig.patch.set_facecolor(SURF)
for ax, g in zip(axes.ravel(), majors):
    ax.set_facecolor(SURF); sel = m == g
    ax.scatter(Z[~sel, 0], Z[~sel, 1], s=4, c=GRAY, linewidths=0, rasterized=True)
    ax.scatter(Z[sel, 0], Z[sel, 1], s=7, c=BLUE, linewidths=0, rasterized=True)
    ax.set_title(f"{g}  (n={sel.sum()})", fontsize=8.8, loc="left", color=TXT); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(True); sp.set_color(GRID)
fig.suptitle("내역사업 임베딩 2차원 지도(t-SNE): 유형별 분포", x=0.01, ha="left", fontsize=12, fontweight="bold", color=TXT)
fig.text(0.01, 0.925, f"지원목적 축 임베딩({EMB}) 2,189건. 파란 점이 해당 유형, 회색은 나머지", fontsize=8.5, color=TXT2)
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(f"{OUT}/fig2_map_small_multiples.png"); plt.close(fig)
# ---- 그림3: 소관 × 유형 2026 예산 히트맵(순차 단색)
d26 = a[a.year == 2026]; H = d26.pivot_table(index="소관", columns="대분류", values="내역예산", aggfunc="sum").fillna(0) / 1e3   # 십억원
H = H.loc[H.sum(1).sort_values(ascending=False).index].head(12); H.columns = [c[:1] for c in H.columns]
fig, ax = plt.subplots(figsize=(9, 5.6)); fig.patch.set_facecolor(SURF)
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
cmap = LinearSegmentedColormap.from_list("blue", ["#f3f7fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
im = ax.imshow(H.values, cmap=cmap, norm=PowerNorm(0.45), aspect="auto")
ax.set_xticks(range(H.shape[1])); ax.set_xticklabels(H.columns, fontsize=10); ax.set_yticks(range(H.shape[0])); ax.set_yticklabels(H.index, fontsize=9.5)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        v = H.values[i, j]
        if v >= 50: ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=7.8, color="white" if v > H.values.max() * 0.25 else TXT)
fig.text(0.01, 0.975, "소관 × 지원목적 유형별 2026년 내역사업 예산(십억원, 상위 12개 소관)", fontsize=11.5, fontweight="bold", color=TXT, va="top")
fig.text(0.01, 0.935, "  ".join(f"{k[:1]} {k[3:].split('(')[0]}" for k in majors), fontsize=8, color=TXT2, va="top")
for sp in ax.spines.values(): sp.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label("십억원", fontsize=8.5); cb.outline.set_visible(False)
fig.tight_layout(rect=(0, 0, 1, 0.91)); fig.savefig(f"{OUT}/fig3_heatmap_somewon_type_2026.png"); plt.close(fig); print("figs saved")
