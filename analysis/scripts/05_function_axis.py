"""지원목적(기능) 축 임베딩: 용어별 χ² 연관도 — 기존 지원유형 분류(지원분야중분류) vs 산업영역(지원산업·소관) — 비율로 TF-IDF 열 가중.
출력: data/emb_fn.npy, output/term_weights.csv, output/k_selection_fn.csv
"""
import json, re, numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.feature_selection import chi2
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, normalized_mutual_info_score as nmi
df = pd.read_parquet("data/corpus.parquet"); X = sp.load_npz("data/tfidf.npz"); vocab = np.array(json.load(open("data/tfidf_vocab.json")))
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id"); df["지원산업"] = df.id.map(raw["지원산업"])
def collapse(s, min_n=15):
    s = s.fillna("NA"); vc = s.value_counts(); return s.where(s.map(vc) >= min_n, "기타")
# 기능 라벨: 지원분야중분류 (결측 제외)
yt = collapse(df["지원분야중분류"]); mt = (yt != "NA").values
ct, _ = chi2(X[mt], yt[mt]); ct = np.nan_to_num(ct)
# 영역 라벨: 지원산업(결측 제외) + 소관 (둘의 χ²를 각각 정규화해 평균)
ys = collapse(df["지원산업"]); ms = (ys != "NA").values
cs, _ = chi2(X[ms], ys[ms]); cs = np.nan_to_num(cs)
co, _ = chi2(X, collapse(df["소관"])); co = np.nan_to_num(co)
def z(v): return v / (v.mean() + 1e-12)
dom = (z(cs) + z(co)) / 2; fn = z(ct)
w = (fn + 0.05) / (fn + dom + 0.10)            # 0~1: 1에 가까우면 기능 어휘, 0에 가까우면 영역 어휘
tw = pd.DataFrame(dict(term=vocab, w=w, chi_fn=ct, chi_dom=dom, df=np.asarray((X > 0).sum(0)).ravel()))
tw.sort_values("w", ascending=False).to_csv("output/term_weights.csv", index=False)
hi = tw[tw.df >= 15].sort_values("w", ascending=False)
print("기능어휘 상위:", ", ".join(hi.term.head(60)))
print("영역어휘 상위:", ", ".join(hi.term.tail(60)))
Xf = X @ sp.diags(w ** 2)                     # 제곱으로 대비 강화
Xf = normalize(Xf)
svd = TruncatedSVD(150, random_state=0); E = normalize(svd.fit_transform(Xf)); print("var", round(svd.explained_variance_ratio_.sum(), 3))
np.save("data/emb_fn.npy", E); sp.save_npz("data/tfidf_fn.npz", Xf.tocsr())
key = df["소관"] + "|" + df["세부사업명"] + "|" + df["내역사업명"]
def consistency(c):
    g = pd.DataFrame({"k": key, "c": c}); g = g[g.groupby("k").k.transform("size") > 1]; return (g.groupby("k").c.nunique() == 1).mean()
lab = df["지원분야중분류"].fillna("NA"); mask = lab != "NA"; res = []
for k in [6, 8, 10, 12, 14, 16, 18, 20, 24]:
    c = KMeans(k, n_init=10, random_state=0).fit_predict(E)
    res.append(dict(k=k, sil=silhouette_score(E, c, sample_size=2000, random_state=0), nmi_taxo=nmi(lab[mask], c[mask]), nmi_somewon=nmi(df["소관"], c), consist=consistency(c), min_size=np.bincount(c).min())); print(res[-1])
pd.DataFrame(res).to_csv("output/k_selection_fn.csv", index=False)
