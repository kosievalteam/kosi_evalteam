"""2단계: 1단계(fn, k=12)의 일반어휘 잔여군집(최대 군집)을 세분 군집. 결과 profile 출력."""
import sys, json, numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
K2 = int(sys.argv[1]) if len(sys.argv) > 1 else 7
df = pd.read_parquet("data/corpus.parquet"); A = pd.read_parquet("data/assign_fn_k12_g6.parquet")
E = np.load("data/emb_fn.npy"); X = sp.load_npz("data/tfidf.npz"); vocab = np.array(json.load(open("data/tfidf_vocab.json")))
big = A.c.value_counts().idxmax(); idx = np.where(A.c.values == big)[0]; print("잔여군집", big, len(idx))
Xs = sp.load_npz("data/tfidf_fn.npz")[idx]
from sklearn.decomposition import TruncatedSVD; from sklearn.preprocessing import normalize
Es = normalize(TruncatedSVD(80, random_state=0).fit_transform(Xs))      # 잔여군집 내부에서 재축소(내부 대비 극대화)
for k in [5, 6, 7, 8, 9, 10]:
    c = KMeans(k, n_init=10, random_state=0).fit_predict(Es); print(k, round(silhouette_score(Es, c), 3), np.bincount(c).tolist())
km = KMeans(K2, n_init=20, random_state=0).fit(Es); sub = km.labels_
glob = np.asarray(X.mean(axis=0)).ravel()
def top_terms(ii, n=14):
    v = np.asarray(X[ii].mean(axis=0)).ravel(); s = v * np.log1p(v / (glob + 1e-9)); return vocab[np.argsort(-s)[:n]]
out = [f"# stage2 of C{big}: K2={K2}"]
for s in range(K2):
    ii = idx[sub == s]; d = df.iloc[ii]; a = A.iloc[ii]
    dist = np.linalg.norm(Es[sub == s] - km.cluster_centers_[s], axis=1); rep = d.iloc[np.argsort(dist)[:8]]
    bud = d.groupby("year").내역예산.sum().reindex([2024, 2025, 2026]).fillna(0)
    out.append(f"\n### S{s} n={len(d)} 연도별 {d.year.value_counts().reindex([2024,2025,2026]).fillna(0).astype(int).tolist()} 예산 24/25/26 = {bud[2024]:,.0f} / {bud[2025]:,.0f} / {bud[2026]:,.0f}")
    out.append("핵심어: " + ", ".join(top_terms(ii)))
    out.append("소관: " + ", ".join(f"{k}({v})" for k, v in d.소관.value_counts().head(4).items()))
    out.append("기존분류: " + ", ".join(f"{k}({v})" for k, v in d.지원분야중분류.value_counts().head(4).items()) + f" / 결측 {d.지원분야중분류.isna().sum()}")
    out.append("대표: " + " | ".join(f"{r.소관}:{r.세부사업명}>{r.내역사업명}" for r in rep.itertuples()))
    big3 = d[d.year == 2026].nlargest(4, "내역예산"); out.append("2026 최대예산: " + " | ".join(f"{r.소관}:{r.내역사업명}({r.내역예산:,.0f})" for r in big3.itertuples()))
open(f"output/stage2_profile_k{K2}.md", "w").write("\n".join(out)); print("\n".join(out))
A["c2"] = A.c.astype(str); A.loc[A.index[idx], "c2"] = [f"{big}-{s}" for s in sub]; A.to_parquet("data/assign_stage2.parquet", index=False)
