"""03. 혼합 군집 세분화: 1차 군집(k=24) 내부를 2차 KMeans로 분할해 미세군집 생성 → 해석용 프로파일
출력: data/fine_clusters.parquet, output/fine_cluster_profile.md
"""
import json, numpy as np, pandas as pd
from sklearn.cluster import KMeans
df = pd.read_parquet('data/corpus.parquet').merge(pd.read_parquet('data/clusters.parquet'), on='id')
E = np.load('data/emb_lsa.npy')
tok = pd.read_parquet('data/tokens.parquet'); df = df.merge(tok, on='id')
fine = np.empty(len(df), dtype=object)
for c in sorted(df.cluster.unique()):
    idx = np.where(df.cluster.values == c)[0]
    n = len(idx)
    k = int(min(6, max(1, round(n / 55))))
    if k == 1:
        fine[idx] = [f'C{c:02d}.0'] * n; continue
    km = KMeans(k, n_init=20, random_state=0).fit(E[idx])
    for j, i in enumerate(idx): fine[i] = f'C{c:02d}.{km.labels_[j]}'
df['fine'] = fine
df[['id', 'fine']].to_parquet('data/fine_clusters.parquet', index=False)
print('fine clusters:', df.fine.nunique())

from collections import Counter
lines = ['# 미세군집 프로파일\n']
for f, sub in df.groupby('fine'):
    cnt = Counter(t for ts in sub.tokens for t in set(ts))
    top = [w for w, _ in cnt.most_common(14)]
    b26 = sub[sub.year == 2026]['내역예산'].sum() / 100
    lines.append(f'## {f} n={len(sub)} 2026예산={b26:,.0f}억 분야={json.dumps(sub["내역분야"].value_counts().head(3).to_dict(), ensure_ascii=False)} 형태={json.dumps(sub["지원형태"].value_counts().head(2).to_dict(), ensure_ascii=False)}')
    lines.append('- 핵심어: ' + ', '.join(top))
    ex = sub.sort_values('내역예산', ascending=False).drop_duplicates('사업키').head(5)
    for _, r in ex.iterrows():
        lines.append(f'  - {r.소관} | {r.세부사업명} > {r.내역사업명} ({r.내역예산/100:,.0f}억) : {r.purpose_text[:70]}')
open('output/fine_cluster_profile.md', 'w').write('\n'.join(lines))
