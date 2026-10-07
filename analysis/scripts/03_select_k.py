"""군집 수 탐색: 임베딩별 KMeans k=6..36 — 실루엣, 기존 분류(지원분야중분류)와의 NMI, 동일 내역사업의 연도간 군집 일치율."""
import sys, os, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NAMES = sys.argv[1].split(",") if len(sys.argv) > 1 else ["lsa", "w2v", "hyb"]; OUT = sys.argv[2] if len(sys.argv) > 2 else "output/k_selection.csv"
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, normalized_mutual_info_score as nmi
df = pd.read_parquet("data/corpus.parquet")
key = df["소관"] + "|" + df["세부사업명"] + "|" + df["내역사업명"]
lab = df["지원분야중분류"].fillna("NA"); mask = lab != "NA"
def consistency(c):
    g = pd.DataFrame({"k": key, "c": c}); g = g[g.groupby("k").k.transform("size") > 1]
    return (g.groupby("k").c.nunique() == 1).mean()
res = []
for name in NAMES:
    E = np.load(f"data/emb_{name}.npy")
    for k in [6, 8, 10, 12, 15, 18, 21, 24, 28, 32, 36]:
        km = KMeans(k, n_init=10, random_state=0).fit(E); c = km.labels_
        res.append(dict(emb=name, k=k, sil=silhouette_score(E, c, sample_size=2000, random_state=0),
                        nmi_taxo=nmi(lab[mask], c[mask]), consist=consistency(c), min_size=np.bincount(c).min()))
        print(res[-1])
pd.DataFrame(res).to_csv(OUT, index=False)
