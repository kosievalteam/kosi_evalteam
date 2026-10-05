"""축별(대상·수단·내용) 유형화 상세 집계: 하위군집 구조, 연도별 규모·추이, 소관별 구조, 대표 사업, 기존 항목과의 비교, 안정성 지표.
사용: python scripts/13_axis_detail.py   →  output_bge-m3/Y*_*.csv, axes_stability.json
"""
import os, re, json, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.metrics import silhouette_score, silhouette_samples, adjusted_rand_score, normalized_mutual_info_score
OUT = "output_bge-m3"; K = 16
A = pd.read_csv(f"{OUT}/axes_assignments.csv"); raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id")
for c in ["지원분야소분류", "지원분야중분류", "지원산업", "수혜대상", "공고지원내용", "내역목적", "세부목적"]: A[c] = A.id.map(raw[c])
cfg = json.load(open("config/axes_mapping.json"))
key = (A["소관"] + "|" + A["세부사업명"] + "|" + A["내역사업명"]).values
typed = ~A["대분류"].str.startswith("유형화")
# ---------- 임베딩 복원(11번과 동일) ----------
Et = np.load("data/axes/emb_target.npy"); Ec_raw = np.load("data/axes/emb_content.npy")
dom = (A["지원산업"].fillna("NA") + "|" + A["소관"]).values; vc = pd.Series(dom).value_counts(); dom = np.where(pd.Series(dom).map(vc) >= 15, dom, "기타"); mask = ~pd.Series(dom).str.startswith("NA").values
lda = LDA(n_components=12, solver="eigen", shrinkage="auto").fit(Ec_raw[mask], dom[mask]); Q, _ = np.linalg.qr(lda.scalings_[:, :12]); Ec = normalize(Ec_raw - (Ec_raw @ Q) @ Q.T)
E = {"target": Et, "content": Ec}; lab = {ax: np.load(f"data/axes/labels_{ax}_k{K}.npy") for ax in E}; cen = {ax: np.load(f"data/axes/centers_{ax}_k{K}.npy") for ax in E}
TYPE = {"target": "대상유형", "content": "내용유형", "instrument": "수단유형"}
from kiwipiepy import Kiwi; kiwi = Kiwi()
STOP = set("지원 사업 등 및 중소기업 기업 대상 위하 통하 추진 운영 강화 확대 경우 이내 최대 당 관련 분야 국내 위한 개발 기술".split())
def topw(texts, n=10):
    from collections import Counter; c = Counter()
    for t in texts:
        for tk in kiwi.tokenize(str(t)[:400]):
            if tk.tag in ("NNG", "NNP", "SL") and len(tk.form) > 1 and tk.form not in STOP: c[tk.form] += 1
    return ", ".join(w for w, _ in c.most_common(n))
d26 = A[(A.year == 2026) & typed]
# ---------- 1. 하위군집 구조 ----------
for ax in E:
    rows = []
    for c in range(K):
        m = (lab[ax] == c); d = A[m]; t26 = d[(d.year == 2026) & typed[m].values]
        txt = d["수혜대상"].fillna("(미기재)") if ax == "target" else np.where(d["공고지원내용"].fillna("").str.strip() != "", d["공고지원내용"].fillna(""), d["내역목적"].fillna(d["세부목적"]).fillna(""))
        rows.append({"유형": cfg[ax][str(c)], "군집": f"C{c}", "건수": int(m.sum()), "2026 건수": len(t26), "2026 예산(억원)": round(t26.내역예산.sum() / 100, 0),
                     "주요 목적유형": ", ".join(f"{k[:1]}{v}" for k, v in d["대분류"].value_counts().head(3).items()),
                     "핵심어": topw(pd.Series(txt)), "대표 서술": " | ".join(pd.Series(txt).value_counts().head(3).index.str[:50]) if ax == "target" else "",
                     "대표 사업(2026 예산순)": " / ".join(t26.sort_values("내역예산", ascending=False)["내역사업명"].head(3))})
    pd.DataFrame(rows).sort_values(["유형", "군집"]).to_csv(f"{OUT}/Y4_{ax}_subclusters.csv", index=False, encoding="utf-8-sig")
# ---------- 2. 연도별 규모·추이 / 소관별 / 대표 사업 / 건당 예산 ----------
T = A[typed]
for ax, col in TYPE.items():
    g = T.groupby([col, "year"]).agg(건수=("id", "size"), 예산=("내역예산", "sum")).unstack("year").fillna(0)
    out = pd.DataFrame({f"건수 {y}": g[("건수", y)] for y in (2024, 2025, 2026)} | {f"예산 {y}(조원)": (g[("예산", y)] / 1e6).round(2) for y in (2024, 2025, 2026)})
    for y in (2024, 2025, 2026): out[f"비중 {y}(%)"] = (g[("예산", y)] / g[("예산", y)].sum() * 100).round(1)
    out["증감률 24→26(%)"] = ((g[("예산", 2026)] / g[("예산", 2024)].replace(0, np.nan) - 1) * 100).round(1)
    out["건당 예산 2026(억원)"] = (g[("예산", 2026)] / g[("건수", 2026)].replace(0, np.nan) / 100).round(0)
    out["소관 수 2026"] = d26.groupby(col)["소관"].nunique()
    out.to_csv(f"{OUT}/Y1_{ax}_by_year.csv", encoding="utf-8-sig")
    pv = d26.pivot_table(index="소관", columns=col, values="내역예산", aggfunc="sum").fillna(0); pv["합계"] = pv.sum(1); (pv.sort_values("합계", ascending=False) / 100).round(0).to_csv(f"{OUT}/Y5_{ax}_somewon_2026.csv", encoding="utf-8-sig")
    top = d26.sort_values("내역예산", ascending=False).groupby(col).head(4)[[col, "소관", "세부사업명", "내역사업명", "내역예산", "대분류"]]
    top.to_csv(f"{OUT}/Y6_{ax}_top_programs_2026.csv", index=False, encoding="utf-8-sig")
# ---------- 3. 기존 항목과의 비교 ----------
sub = A["지원분야소분류"].fillna("(미연계)").str.replace(r"\[.*?\]", "", regex=True)
pd.crosstab(A.loc[typed, "대상유형"], sub[typed]).to_csv(f"{OUT}/Y7_target_x_taxonomy_sub.csv", encoding="utf-8-sig")
meta = A["세부지원"].fillna("(미기재)").str.replace(r"\s*\(.*?\)", "", regex=True).str.replace(" ", "")
pd.crosstab(A.loc[typed, "수단유형"], meta[typed]).to_csv(f"{OUT}/Y7_instrument_x_meta.csv", encoding="utf-8-sig")
pd.crosstab(A.loc[typed, "내용유형"], A.loc[typed, "대분류"].str[:1]).to_csv(f"{OUT}/Y7_content_x_purpose.csv", encoding="utf-8-sig")
pd.crosstab(A.loc[typed, "내용유형"], A.loc[typed, "내용_출처"]).to_csv(f"{OUT}/Y7_content_x_source.csv", encoding="utf-8-sig")
pd.crosstab(A.loc[typed, "대상유형"], A.loc[typed, "수단유형"]).to_csv(f"{OUT}/Y8_target_x_instrument_count_all.csv", encoding="utf-8-sig")
# ---------- 4. 안정성·타당성 ----------
val = {}
for ax in E:
    X = E[ax]; L = lab[ax]; col = TYPE[ax]; ty = A[col].values
    val[f"{ax}_silhouette_k16"] = round(float(silhouette_score(X, L, sample_size=None, random_state=0)), 3)
    val[f"{ax}_silhouette_type"] = round(float(silhouette_score(X, ty)), 3)
    val[f"{ax}_ARI_seeds"] = round(float(np.mean([adjusted_rand_score(L, KMeans(K, n_init=5, random_state=s).fit_predict(X)) for s in range(1, 11)])), 3)
    val[f"{ax}_NMI_소관"] = round(float(normalized_mutual_info_score(A["소관"], ty)), 3)
    val[f"{ax}_NMI_지원목적대분류"] = round(float(normalized_mutual_info_score(A["대분류"], ty)), 3)
    lk = sub != "(미연계)"; val[f"{ax}_NMI_지원분야소분류(연계분)"] = round(float(normalized_mutual_info_score(sub[lk], pd.Series(ty)[lk])), 3)
    # 연도별 텍스트만으로의 유형 일치율: 행 단위 군집→유형 매핑
    M = {int(k): v for k, v in cfg[ax].items()}; rowtype = pd.Series(L).map(M).values
    g = pd.DataFrame({"k": key, "t": rowtype}); g = g[g.groupby("k").k.transform("size") > 1]; val[f"{ax}_연도간일치율(유형)"] = round(float((g.groupby("k").t.nunique() == 1).mean()), 3)
    # 유형별 응집도: 유형 내 평균 중심거리 대비 타 유형 중심 최소거리
    C = {t: normalize(X[ty == t].mean(0, keepdims=True))[0] for t in np.unique(ty)}
    coh = {}
    for t, c in C.items():
        own = np.linalg.norm(X[ty == t] - c, axis=1).mean(); other = min(np.linalg.norm(c - c2) for t2, c2 in C.items() if t2 != t); coh[t] = round(float(other / own), 3)
    val[f"{ax}_유형응집도(타중심최소거리/자기평균거리)"] = coh
    # 병합 군집 간 거리(동일 유형으로 묶인 군집 쌍의 중심거리 vs 전체 군집 쌍 평균)
    cc = cen[ax]; D = np.linalg.norm(cc[:, None] - cc[None], axis=2); pairs = [(i, j) for i in range(K) for j in range(i + 1, K)]
    same = [D[i, j] for i, j in pairs if cfg[ax][str(i)] == cfg[ax][str(j)]]; diff = [D[i, j] for i, j in pairs if cfg[ax][str(i)] != cfg[ax][str(j)]]
    val[f"{ax}_병합군집쌍 중심거리 평균"] = round(float(np.mean(same)), 3) if same else None; val[f"{ax}_비병합군집쌍 중심거리 평균"] = round(float(np.mean(diff)), 3)
ty = A["수단유형"].values
val["instrument_NMI_소관"] = round(float(normalized_mutual_info_score(A["소관"], ty)), 3); val["instrument_NMI_지원목적대분류"] = round(float(normalized_mutual_info_score(A["대분류"], ty)), 3)
val["instrument_NMI_지원형태메타"] = round(float(normalized_mutual_info_score(meta, ty)), 3)
# 수단 규칙의 어휘 신호 의존도: 메타만으로 결정되는 비율
val["instrument_어휘신호로 세분된 비율(I5·I8·I9)"] = round(float(pd.Series(ty).str.match(r"I(5|8|9) ").mean()), 3)
json.dump(val, open(f"{OUT}/axes_stability.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(val, ensure_ascii=False, indent=1))
