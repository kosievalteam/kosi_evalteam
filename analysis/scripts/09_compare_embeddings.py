"""두 임베딩 기반 최종 유형화 결과 비교: 대분류 교차표, 일치율(ARI/NMI), 기존 분류 정합성, 연도 간 일치율, 유형별 2026 예산 비중 차이.
사용: python scripts/09_compare_embeddings.py --a fn --b bge-m3_fn --out-b output_bge-m3
"""
import os, json, argparse, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.metrics import adjusted_rand_score as ari, normalized_mutual_info_score as nmi
ap = argparse.ArgumentParser(); ap.add_argument("--a", default="fn"); ap.add_argument("--b", required=True); ap.add_argument("--out-a", default="output"); ap.add_argument("--out-b", required=True)
args = ap.parse_args()
A = pd.read_csv(f"{args.out_a}/typology_assignments.csv"); B = pd.read_csv(f"{args.out_b}/typology_assignments.csv")
m = A[["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류", "지원분야중분류"]].merge(B[["id", "대분류", "중분류"]], on="id", suffixes=("_a", "_b"))
res = dict(n=len(m), ari_major=ari(m.대분류_a, m.대분류_b), nmi_major=nmi(m.대분류_a, m.대분류_b), ari_mid=ari(m.중분류_a, m.중분류_b), nmi_mid=nmi(m.중분류_a, m.중분류_b),
           agree_major=(m.대분류_a.str[0] == m.대분류_b.str[0]).mean())
sa, sb = json.load(open(f"{args.out_a}/stability.json")), json.load(open(f"{args.out_b}/stability.json"))
for k in ["silhouette", "ari_mean", "nmi_taxo", "nmi_somewon", "consist_mid", "consist_maj"]: res[f"{k}_a"] = sa[k]; res[f"{k}_b"] = sb[k]
print(json.dumps({k: round(float(v), 3) for k, v in res.items()}, ensure_ascii=False, indent=1))
ct = pd.crosstab(m.대분류_a, m.대분류_b); ct.columns = [c[:1] for c in ct.columns]; print(ct.to_string())
d26 = m[m.year == 2026]
share = pd.DataFrame({args.a: d26.groupby(d26.대분류_a.str[0]).내역예산.sum(), args.b: d26.groupby(d26.대분류_b.str[0]).내역예산.sum()}).fillna(0)
share = (share / share.sum() * 100).round(1); share["차이(p)"] = (share[args.b] - share[args.a]).round(1); print(share.to_string())
# 예산 상위 사업 중 대분류가 다른 사례
diff = d26[d26.대분류_a.str[0] != d26.대분류_b.str[0]].nlargest(25, "내역예산")[["소관", "세부사업명", "내역사업명", "내역예산", "대분류_a", "대분류_b"]]
print(diff.to_string())
os.makedirs(args.out_b, exist_ok=True)
with pd.ExcelWriter(f"{args.out_b}/compare_{args.a}_vs_{args.b}.xlsx") as w:
    pd.Series(res).to_frame("value").to_excel(w, sheet_name="지표"); ct.to_excel(w, sheet_name="대분류 교차표"); share.to_excel(w, sheet_name="2026 예산비중"); diff.to_excel(w, sheet_name="상위 불일치", index=False)
    m[m.대분류_a != m.대분류_b].to_excel(w, sheet_name="불일치 전체", index=False)
json.dump({k: float(v) for k, v in res.items()}, open(f"{args.out_b}/compare_{args.a}_vs_{args.b}.json", "w"), indent=1)
ct.to_csv(f"{args.out_b}/compare_crosstab.csv", encoding="utf-8-sig"); share.to_csv(f"{args.out_b}/compare_share2026.csv", encoding="utf-8-sig")
