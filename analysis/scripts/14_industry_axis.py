"""다섯째 축 '지원산업': 지원이 겨냥하는 기술·산업 영역을 복수 태그로 유형화하고, AI 관여도를 3단계로 판정.
   - 자료: 사업명(세부·내역), 내역목적(없으면 세부목적), 공고 지원내용, 예산 산출근거, 수혜대상, DB 지원산업 필드
   - 점수: 사업명 키워드 3점 + 본문 키워드 출현 1점(최대 4) + DB 지원산업 필드 일치 2점 → 3점 이상이면 태그, 최고점이 주(主) 산업
   - AI 관여도: 핵심(사업명에 AI) / 활용(본문에 AI 적용 맥락 2회 이상, 또는 1회 이상이면서 총 3회 이상) / 언급(그 외 AI 언급) / 없음
     S1 인공지능 태그는 핵심·활용(또는 데이터 키워드)일 때 부여하되, 주 산업을 AI로 두는 것은 핵심 사업에 한정
   - 동일 내역사업은 연도별 점수 평균으로 단일 판정
사용: python scripts/14_industry_axis.py  →  output_bge-m3/industry_assignments.csv, S1~S8_*.csv, industry_validation.json, fig7
"""
import os, re, json, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.metrics import normalized_mutual_info_score as nmi
from sklearn.preprocessing import normalize
OUT = "output_bge-m3"
X = pd.read_csv(f"{OUT}/axes_assignments.csv"); raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id"); calc = pd.read_csv("data/biz_calc_2024_2026.csv").set_index("id")
D = json.load(open("config/industry_dict.json"))
name = (X["세부사업명"].fillna("") + " " + X["내역사업명"].fillna(""))
body = (X.id.map(raw["내역목적"]).fillna(X.id.map(raw["세부목적"])).fillna("") + " " + X.id.map(raw["공고지원내용"]).fillna("") + " " + X.id.map(calc["산출근거"]).fillna("") + " " + X.id.map(raw["수혜대상"]).fillna(""))
dbf = X.id.map(raw["지원산업"]).fillna("")
key = X["소관"] + "|" + X["세부사업명"] + "|" + X["내역사업명"]
# ---- AI 관여도
AI = r"(?<![A-Za-z])(AI|AX)(?![A-Za-z])|(?<![A-Za-z])AI(?=AGENT|SW|DX)|인공지능|생성형|머신러닝|딥러닝|거대언어|(?<![A-Za-z])LLM(?![A-Za-z])"
APP = r"((?<![A-Za-z])(AI|AX)(?![A-Za-z])|인공지능)\s?[·‧ㆍ]?\s?((DX|DT)\s?)?(-?\s?(활용|도입|적용|기반|전환|융합|솔루션|서비스|모델|개발|프로젝트|과정|교육|실증|알고리즘|역량|바우처|반도체|Native|응용|컴퓨팅|에이전트|학습|클라우드))|(?<![A-Za-z])AX\s?전환|생성형|LLM|머신러닝|딥러닝"
ai_name = name.str.contains(AI); ai_n = body.str.count(AI); ai_app = body.str.count(APP)
row_lvl = np.select([ai_name, (ai_app >= 2) | ((ai_app >= 1) & (ai_n >= 3)) | (ai_n >= 4), ai_n >= 1], [3, 2, 1], 0)
lvl = pd.Series(row_lvl, index=X.index).groupby(key.values).transform("max")   # 내역사업 단위: 연도 중 최고 수준
LV = {3: "핵심", 2: "활용", 1: "언급", 0: "없음"}
X["AI관여도"] = lvl.map(LV)
# ---- 산업 점수
S = {}
for s, cfg in D.items():
    pat = "|".join(cfg["kw"])
    occ = body.str.count(pat); dist = pd.Series([len({m.group(0) for m in re.finditer(pat, t)}) for t in body], index=X.index)
    sc = 3 * name.str.contains(pat).astype(int) + np.where(dist >= 2, occ.clip(upper=4), occ.clip(upper=2))   # 본문은 서로 다른 키워드 2개 이상일 때만 3점 이상 가능
    if cfg["db"]: sc = sc + 2 * dbf.str.contains("|".join(re.escape(d) for d in cfg["db"])).astype(int)
    S[s] = sc.astype(float)
S = pd.DataFrame(S)
s1 = list(D)[0]; data_m = S[s1].groupby(key.values).transform("mean")   # AI 가중 전 데이터 키워드 점수
S[s1] = S[s1] + np.select([lvl == 3, lvl == 2], [6, 3], 0)                # AI 핵심 → 사업명 수준 가중, 활용 → 태그 기준 충족(부 태그)
Sm = S.groupby(key.values).transform("mean")                             # 내역사업 단위 평균 점수
tags = Sm.ge(3)
PRI = Sm.where(tags, -1).copy(); PRI[s1] = np.where(lvl == 3, 99, np.where(data_m >= 3, data_m, -1))   # 주 산업 S1은 AI 핵심 또는 데이터 산업 사업만
PRI[list(D)[1]] = PRI[list(D)[1]] - 0.1                                    # 동점이면 범용 디지털보다 구체 산업 우선
has = (PRI > 0).any(axis=1)
prim = PRI.idxmax(axis=1).where(has, "S0 업종 공통(산업 무관)")
X["지원산업(주)"] = prim.values
X["지원산업(태그)"] = [";".join(c.split(" ")[0] for c in Sm.columns[tags.loc[i]]) or "S0" for i in X.index]
X["태그수"] = tags.sum(1).values
cols = ["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "대상유형", "수단유형", "내용유형", "지원산업(주)", "지원산업(태그)", "태그수", "AI관여도"]
X[cols].to_csv(f"{OUT}/industry_assignments.csv", index=False, encoding="utf-8-sig")
yrs = [2024, 2025, 2026]; d26 = X[X.year == 2026]; tot26 = d26.내역예산.sum()
# ---- 집계
def by_year(col):
    g = X.groupby([col, "year"]).agg(n=("id", "size"), b=("내역예산", "sum")).unstack("year").fillna(0)
    t = pd.DataFrame({f"건수 {y}": g[("n", y)].astype(int) for y in yrs} | {f"예산 {y}(조원)": (g[("b", y)] / 1e6).round(2) for y in yrs})
    for y in yrs: t[f"비중 {y}(%)"] = (g[("b", y)] / g[("b", y)].sum() * 100).round(1)
    t["증감률 24→26(%)"] = ((g[("b", 2026)] / g[("b", 2024)].replace(0, np.nan) - 1) * 100).round(1)
    t["건당 예산 2026(억원)"] = (g[("b", 2026)] / g[("n", 2026)].replace(0, np.nan) / 100).round(0)
    t["소관 수 2026"] = d26.groupby(col)["소관"].nunique(); return t
by_year("지원산업(주)").to_csv(f"{OUT}/S1_industry_primary_by_year.csv", encoding="utf-8-sig")
# 복수 태그 기준(중복 포함) 규모
rows = []
for s in D:
    c = s.split(" ")[0]; m = X["지원산업(태그)"].str.split(";").apply(lambda l: c in l)
    r = {"지원산업": s}
    for y in yrs: r[f"태그 건수 {y}"] = int((m & (X.year == y)).sum()); r[f"태그 예산 {y}(조원)"] = round(X.loc[m & (X.year == y), "내역예산"].sum() / 1e6, 2)
    r["태그 예산 비중 2026(%)"] = round(X.loc[m & (X.year == 2026), "내역예산"].sum() / tot26 * 100, 1); rows.append(r)
pd.DataFrame(rows).to_csv(f"{OUT}/S2_industry_tag_by_year.csv", index=False, encoding="utf-8-sig")
# 다른 축과의 교차(2026 예산, 주 산업)
for nm, col in [("S3_industry_x_purpose", "대분류"), ("S4_industry_x_instrument", "수단유형"), ("S5_industry_x_somewon", "소관"), ("S6_industry_x_target", "대상유형"), ("S6b_industry_x_content", "내용유형")]:
    d26.pivot_table(index="지원산업(주)", columns=col, values="내역예산", aggfunc="sum").fillna(0).round(0).to_csv(f"{OUT}/{nm}_2026.csv", encoding="utf-8-sig")
# AI 관여도
ai = X.groupby(["AI관여도", "year"]).agg(n=("id", "size"), b=("내역예산", "sum")).unstack("year").fillna(0)
ait = pd.DataFrame({f"건수 {y}": ai[("n", y)].astype(int) for y in yrs} | {f"예산 {y}(조원)": (ai[("b", y)] / 1e6).round(2) for y in yrs}).reindex(["핵심", "활용", "언급", "없음"])
ait.to_csv(f"{OUT}/S7_ai_level_by_year.csv", encoding="utf-8-sig")
aic = X[X.AI관여도.isin(["핵심", "활용"]) & (X.year == 2026)]
for nm, col in [("purpose", "대분류"), ("instrument", "수단유형"), ("target", "대상유형"), ("content", "내용유형"), ("somewon", "소관")]:
    aic.pivot_table(index=col, columns="AI관여도", values="내역예산", aggfunc=["sum", "count"]).fillna(0).to_csv(f"{OUT}/S7_ai_{nm}_2026.csv", encoding="utf-8-sig")
X[X.AI관여도.isin(["핵심", "활용"])].sort_values(["year", "내역예산"], ascending=[False, False])[cols].to_csv(f"{OUT}/S8_ai_programs.csv", index=False, encoding="utf-8-sig")
d26.sort_values("내역예산", ascending=False).groupby("지원산업(주)").head(4)[["지원산업(주)", "소관", "내역사업명", "내역예산", "지원산업(태그)", "AI관여도"]].to_csv(f"{OUT}/S8_industry_top_programs_2026.csv", index=False, encoding="utf-8-sig")
# ---- 검증
val = {}
val["주산업_태그수_분포"] = X["태그수"].value_counts().sort_index().to_dict()
val["업종공통_비율(건수)"] = round(float((X["지원산업(주)"].str.startswith("S0")).mean()), 3)
for d, s in [("농축산", "S9"), ("환경", "S5"), ("문화/관광", "S8"), ("IT/SW", "S2"), ("스포츠", "S8")]:
    m = dbf.str.contains(re.escape(d)); val[f"DB필드[{d}] → {s} 태그 비율(n={int(m.sum())})"] = round(float(X.loc[m, "지원산업(태그)"].str.contains(s + r"(;|$)").mean()), 3)
m = dbf.str.contains(r"전체\[일반\]"); val["DB필드[전체 일반] 중 특정 산업 태그 비율"] = round(float((X.loc[m, "태그수"] > 0).mean()), 3)
val["NMI(주산업, 소관)"] = round(float(nmi(X["소관"], X["지원산업(주)"])), 3)
val["NMI(주산업, 지원목적 대분류)"] = round(float(nmi(X["대분류"], X["지원산업(주)"])), 3)
for c in ["대상유형", "수단유형", "내용유형"]: val[f"NMI(주산업, {c})"] = round(float(nmi(X[c], X["지원산업(주)"])), 3)
# 의미 정합성: 원 문장 임베딩(영역 방향 제거 전)의 최근접 10개 이웃 중 같은 주 산업 비율 vs 무작위 기대치
E = normalize(np.load("data/emb_bge-m3.npy")); sim = E @ E.T; np.fill_diagonal(sim, -1)
kk = np.asarray(key.values, dtype=object); same_prog = kk[:, None] == kk[None, :]; sim[same_prog] = -1
nn = np.argsort(-sim, axis=1)[:, :10]; p = np.asarray(X["지원산업(주)"].values, dtype=object)
val["임베딩 10-최근접 이웃 동일 주산업 비율"] = round(float((p[nn] == p[:, None]).mean()), 3)
share = pd.Series(p).value_counts(normalize=True); val["무작위 기대 비율"] = round(float((share ** 2).sum()), 3)
for s in D:
    m = p == s
    if m.sum(): val[f"이웃일치[{s.split(' ')[0]}]"] = round(float((p[nn[m]] == s).mean()), 3)
g = pd.DataFrame({"k": key, "y": X.year, "lvl": row_lvl}); g = g[g.groupby("k").k.transform("size") > 1]
val["AI 관여도 연도 간 일치율(행 단위 판정)"] = round(float((g.groupby("k").lvl.nunique() == 1).mean()), 3)
json.dump(val, open(f"{OUT}/industry_validation.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(val, ensure_ascii=False, indent=1))
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(pd.read_csv(f"{OUT}/S1_industry_primary_by_year.csv", index_col=0).to_string()); print(pd.read_csv(f"{OUT}/S2_industry_tag_by_year.csv").to_string()); print(ait.to_string())
# ---- 도표 fig7: (좌) AI 관여도별 예산 추이, (우) 지원산업별 2026 예산(주 산업 vs 태그 기준)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.font_manager as fm
for f in ["fonts/NotoSansKR-Regular.otf", "fonts/NotoSansKR-Bold.otf"]: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK KR", "axes.unicode_minus": False, "figure.dpi": 200, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#c9c8c2"})
SURF, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0), gridspec_kw={"width_ratios": [1, 1.45]}); fig.patch.set_facecolor(SURF)
ax = axes[0]; ax.set_facecolor(SURF); lv = ["핵심", "활용", "언급"]; COL = {"핵심": "#2a78d6", "활용": "#7fb1ec", "언급": "#bdbcb5"}
xs = np.arange(len(yrs)); w = 0.26
for j, l in enumerate(lv):
    v = [ait.loc[l, f"예산 {y}(조원)"] for y in yrs]; ax.bar(xs + (j - 1) * w, v, width=w - 0.02, color=COL[l], label=f"AI {l}", zorder=3)
    for x, vv in zip(xs + (j - 1) * w, v): ax.text(x, vv + 0.08, f"{vv:.2f}", ha="center", fontsize=7.5, color=TXT2)
ax.set_xticks(xs); ax.set_xticklabels([str(y) for y in yrs], fontsize=9); ax.yaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True)
ax.set_ylabel("내역사업 예산(조원)", fontsize=9); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("AI 관여도별 예산", loc="left", fontsize=10.5, fontweight="bold", color=TXT)
ax = axes[1]; ax.set_facecolor(SURF)
pr = X[X.year == 2026].groupby("지원산업(주)").내역예산.sum() / 1e6; pr = pr.drop([i for i in pr.index if i.startswith("S0")])
tg = pd.read_csv(f"{OUT}/S2_industry_tag_by_year.csv").set_index("지원산업")["태그 예산 2026(조원)"]
order = pr.sort_values().index; lab = [o.split(" ", 1)[1] for o in order]; yy = np.arange(len(order))
ax.barh(yy + 0.18, [tg[o] for o in order], height=0.34, color="#bcd6f4", label="태그 기준(중복 포함)", zorder=3)
ax.barh(yy - 0.18, pr[order].values, height=0.34, color="#2a78d6", label="주 산업 기준", zorder=3)
for y_, v in zip(yy, pr[order].values): ax.text(v + 0.03, y_ - 0.18, f"{v:.2f}", va="center", fontsize=7.5, color=TXT2)
ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=8.5); ax.xaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True); ax.set_xlabel("2026년 예산(조원)", fontsize=9)
ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.set_title("지원산업 유형별 2026년 예산(업종 공통 제외)", loc="left", fontsize=10.5, fontweight="bold", color=TXT)
fig.text(0.01, 0.98, "지원산업 축: AI 관여도와 산업별 지원 규모", fontsize=12, fontweight="bold", color=TXT, va="top")
fig.text(0.01, 0.935, "AI 핵심=사업명에 AI, 활용=지원 항목에 AI 도입·활용 포함, 언급=우대·예시 수준. 업종 공통(산업 무관) 2026년 20.70조원은 우측에서 제외", fontsize=8.3, color=TXT2, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.9)); fig.savefig(f"{OUT}/fig7_industry_ai.png"); plt.close(fig)
