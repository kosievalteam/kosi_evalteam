"""KMeans(k=K) 중분류 → 중심점 Ward 계층군집으로 대분류(G개). 군집 프로파일 출력(라벨링용)."""
import sys, json, numpy as np, pandas as pd, scipy.sparse as sp
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
K = int(sys.argv[1]) if len(sys.argv) > 1 else 24
G = int(sys.argv[2]) if len(sys.argv) > 2 else 8
EMB = sys.argv[3] if len(sys.argv) > 3 else "lsa"
df = pd.read_parquet("data/corpus.parquet"); E = np.load(f"data/emb_{EMB}.npy")
X = sp.load_npz("data/tfidf.npz"); vocab = np.array(json.load(open("data/tfidf_vocab.json")))
km = KMeans(K, n_init=20, random_state=0).fit(E); df["c"] = km.labels_
# 대분류: 중심점 Ward (군집 크기 가중 없이 중심점 거리 기준)
Z = linkage(km.cluster_centers_, "ward"); grp = fcluster(Z, G, "maxclust"); df["g"] = grp[df.c]
dn = dendrogram(Z, no_plot=True); order = dn["leaves"]
# c-TF-IDF 핵심어
def top_terms(idx, n=14):
    v = np.asarray(X[idx].mean(axis=0)).ravel(); glob = np.asarray(X.mean(axis=0)).ravel()
    s = v * np.log1p(v / (glob + 1e-9)); return vocab[np.argsort(-s)[:n]]
out = [f"# K={K}, G={G}, emb={EMB}\n", "덴드로그램 순서(중분류 번호): " + " ".join(map(str, order)) + "\n"]
for g in sorted(set(grp)):
    cs = [c for c in order if grp[c] == g]
    sub = df[df.g == g]
    out.append(f"\n## 대분류 G{g}  (문서 {len(sub)}, 중분류 {cs})  2026예산합 {sub[sub.year==2026].내역예산.sum():,.0f}백만원")
    for c in cs:
        d = df[df.c == c]; idx = np.where(df.c == c)[0]
        dist = np.linalg.norm(E[idx] - km.cluster_centers_[c], axis=1); rep = d.iloc[np.argsort(dist)[:7]]
        bud = d.groupby("year").내역예산.sum().reindex([2024, 2025, 2026]).fillna(0)
        out.append(f"\n### C{c}  n={len(d)} (연도별 {d.year.value_counts().reindex([2024,2025,2026]).fillna(0).astype(int).tolist()})  예산(백만원) 24/25/26 = {bud[2024]:,.0f} / {bud[2025]:,.0f} / {bud[2026]:,.0f}")
        out.append("핵심어: " + ", ".join(top_terms(idx)))
        out.append("소관: " + ", ".join(f"{k}({v})" for k, v in d.소관.value_counts().head(4).items()))
        out.append("기존분류(중분류): " + ", ".join(f"{k}({v})" for k, v in d.지원분야중분류.value_counts().head(4).items()) + f" / 결측 {d.지원분야중분류.isna().sum()}")
        out.append("대표: " + " | ".join(f"{r.소관}:{r.세부사업명}>{r.내역사업명}" for r in rep.itertuples()))
        big = d[d.year == 2026].nlargest(3, "내역예산")
        out.append("2026 최대예산: " + " | ".join(f"{r.소관}:{r.내역사업명}({r.내역예산:,.0f})" for r in big.itertuples()))
open(f"output/cluster_profile_{EMB}_k{K}_g{G}.md", "w").write("\n".join(out))
df[["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "지원분야중분류", "지원분야소분류", "목적출처", "has_gonggo", "c", "g"]].to_parquet(f"data/assign_{EMB}_k{K}_g{G}.parquet", index=False)
np.save(f"data/centers_{EMB}_k{K}.npy", km.cluster_centers_)
print("written", f"output/cluster_profile_{EMB}_k{K}_g{G}.md")
