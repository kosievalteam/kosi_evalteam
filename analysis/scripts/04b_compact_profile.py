import sys, json, numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.cluster import KMeans
K = int(sys.argv[1]); EMB = sys.argv[2] if len(sys.argv) > 2 else "fn"
df = pd.read_parquet("data/corpus.parquet"); E = np.load(f"data/emb_{EMB}.npy")
X = sp.load_npz("data/tfidf.npz"); vocab = np.array(json.load(open("data/tfidf_vocab.json"))); glob = np.asarray(X.mean(axis=0)).ravel()
km = KMeans(K, n_init=20, random_state=0).fit(E); df["c"] = km.labels_
np.save(f"data/labels_{EMB}_k{K}.npy", km.labels_)
for c in range(K):
    idx = np.where(df.c == c)[0]; d = df.iloc[idx]
    v = np.asarray(X[idx].mean(axis=0)).ravel(); s = v * np.log1p(v / (glob + 1e-9)); tt = vocab[np.argsort(-s)[:10]]
    dist = np.linalg.norm(E[idx] - km.cluster_centers_[c], axis=1); rep = d.iloc[np.argsort(dist)[:5]]
    b26 = d[d.year == 2026].내역예산.sum()
    print(f"C{c} n={len(d)} 26예산={b26:,.0f} | {', '.join(tt)} | 소관 {', '.join(f'{k}{v}' for k,v in d.소관.value_counts().head(3).items())} | 기존 {', '.join(f'{k}{v}' for k,v in d.지원분야중분류.value_counts().head(2).items())}")
    print("   대표: " + " | ".join(f"{r.내역사업명}" for r in rep.itertuples()) + " || 최대: " + " | ".join(f"{r.내역사업명}({r.내역예산:,.0f})" for r in d[d.year==2026].nlargest(3,'내역예산').itertuples()))
