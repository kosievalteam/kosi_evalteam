"""최종 유형화: 임베딩(--emb) KMeans(--k) 군집 → 매핑 파일(--map)로 해석적 병합: 중분류 → 대분류.
   기본값: fn 임베딩, k=24, config/mapping_fn_k24.json (현행 유형 체계).
   내역사업 단위 일관 배정(연도 평균 임베딩의 최근접 중심) + 메타데이터 보정규칙 → 집계표·안정성·행단위 배정 산출."""
import os, json, re, argparse, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ari, silhouette_score, normalized_mutual_info_score as nmi
ap = argparse.ArgumentParser(); ap.add_argument("--emb", default="fn"); ap.add_argument("--k", type=int, default=24); ap.add_argument("--map", default="config/mapping_fn_k24.json"); ap.add_argument("--out", default="output")
args = ap.parse_args(); EMB, K, OUT = args.emb, args.k, args.out; os.makedirs(OUT, exist_ok=True)
df = pd.read_parquet("data/corpus.parquet"); E = np.load(f"data/emb_{EMB}.npy")
km = KMeans(K, n_init=20, random_state=0).fit(E); lab = km.labels_
df["c"] = lab
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id"); df["세부지원"] = df.id.map(raw["세부지원"])
cfg = json.load(open(args.map)); MID = {int(k): v for k, v in cfg["MID"].items()}; MAJ = cfg["MAJ"]; R3 = cfg.get("R3", {})
assert set(MID) == set(range(K)), f"매핑 파일의 군집 번호가 k={K}와 맞지 않습니다"
df["중분류_연도별"] = df.c.map(MID); df["대분류_연도별"] = df["중분류_연도별"].str[0].map(MAJ); assert df["중분류_연도별"].notna().all()
# ---- 내역사업 단위 일관 배정: 같은 내역사업(소관|세부|내역)의 연도별 임베딩 평균 → 최근접 군집 중심
key = df["소관"] + "|" + df["세부사업명"] + "|" + df["내역사업명"]; df["key"] = key
Em = pd.DataFrame(E).groupby(key.values).mean()
from sklearn.preprocessing import normalize
cm = np.argmin(((normalize(Em.values)[:, None, :] - km.cluster_centers_[None, :, :]) ** 2).sum(-1), axis=1)
prog_c = pd.Series(cm, index=Em.index); df["c_prog"] = key.map(prog_c).values
df["중분류"] = df.c_prog.map(MID); df["대분류"] = df["중분류"].str[0].map(MAJ)
n_changed_consist = int((df["중분류"] != df["중분류_연도별"]).sum())
# ---- 메타데이터 보정규칙(투명성: 건수 보고). R1 융자사업이 자금·창업·수출·시설 외 유형이면 E1. R2 보증·보험·대위변제·팩토링은 E2.
nm = df["세부사업명"].fillna("") + " " + df["내역사업명"].fillna("")
RU = cfg["RULES"]
r1 = (df["세부사업명"].fillna("").str.contains(r"\(융자\)") | df["세부지원"].fillna("").str.contains("융자")) & ~df["중분류"].str[0].isin(RU["R1_EXEMPT_PREFIXES"])
r2 = nm.str.contains("보증|대위변제|팩토링|보험금|재보증") & (df["중분류"].str[0] != RU["R2_SKIP_PREFIX"])
assert RU["R1_TARGET"] in MID.values() and RU["R2_TARGET"] in MID.values()
df.loc[r1, "중분류"] = RU["R1_TARGET"]; df.loc[r2, "중분류"] = RU["R2_TARGET"]
df["보정"] = np.where(r1, "R1 융자", np.where(r2, "R2 보증·보험", ""))
# R3 경계 사례 수작업 조정: B(실증·상용화) 군집에 포함됐으나 목적이 인력양성·고용·경영서비스·시설인 사업 (내역사업명 기준)
n_r3 = 0
for mid_name, names in R3.items():
    m3 = df["중분류"].str[:2].isin(cfg.get("R3_SOURCE", [])) & df["내역사업명"].str.replace(" ", "").isin([n.replace(" ", "") for n in names])
    df.loc[m3, "중분류"] = mid_name; df.loc[m3, "보정"] = "R3 경계조정"; n_r3 += int(m3.sum())
df["대분류"] = df["중분류"].str[0].map(MAJ)
print("규칙 R3", n_r3)
# ---- R4 잔여(미분류) 2차 배정: 잔여 접두(RESIDUAL_PREFIX) 군집에 속한 내역사업을, 차순위(비잔여) 군집 중심까지의 거리가
#      그 군집 구성원의 평균 중심거리(자기 군집 평균 반경) 이내일 때만 해당 유형에 '저신뢰' 배정. 나머지는 미분류로 유지.
RP = cfg.get("RESIDUAL_PREFIX"); n_r4 = 0; n_resid = int(df["중분류"].str.startswith(RP).sum()) if RP else 0
if RP and cfg.get("SECOND_PASS", False):
    resid_c = [c for c, v in MID.items() if v.startswith(RP)]; typed_c = [c for c in range(K) if c not in resid_c]
    radius = {c: float(np.linalg.norm(E[lab == c] - km.cluster_centers_[c], axis=1).mean()) for c in typed_c}
    Pm = normalize(Em.values); dist = np.linalg.norm(Pm[:, None, :] - km.cluster_centers_[None, typed_c, :], axis=2)
    j = dist.argmin(1); near = np.array(typed_c)[j]; dmin = dist[np.arange(len(j)), j]
    ok = pd.Series([dmin[i] <= radius[near[i]] for i in range(len(j))], index=Em.index); near_s = pd.Series(near, index=Em.index)
    own_r = {c: float(np.linalg.norm(E[lab == c] - km.cluster_centers_[c], axis=1).mean()) for c in resid_c}
    prog_c_s = pd.Series(prog_c, index=Em.index); alt_ok = pd.Series([dmin[i] <= own_r.get(prog_c_s.iloc[i], 0) for i in range(len(j))], index=Em.index)
    n_r4_alt = int((df["중분류"].str.startswith(RP) & df["key"].map(alt_ok).fillna(False) & (df["보정"] == "")).sum())
    m4 = df["중분류"].str.startswith(RP) & df["key"].map(ok).fillna(False) & (df["보정"] == "")
    df.loc[m4, "중분류"] = df.loc[m4, "key"].map(near_s).map(MID); df.loc[m4, "보정"] = "R4 2차배정(저신뢰)"; n_r4 = int(m4.sum())
    df["대분류"] = df["중분류"].str[0].map(MAJ)
    print(f"잔여 {n_resid}건 중 2차 배정 {n_r4}건, 미분류 잔존 {int(df['중분류'].str.startswith(RP).sum())}건")
# ---- R5 지원내용 기반 배정: 2차 배정 후에도 남은 잔여 사업을 지원내용 문서 분류 결과(10_content_assign.py)로 유형화
CA = cfg.get("CONTENT_ASSIGN"); n_r5 = 0
if RP and CA and os.path.exists(CA):
    ca = pd.read_csv(CA).set_index("key")
    m5 = df["중분류"].str.startswith(RP) & df["key"].isin(ca.index)
    df.loc[m5, "중분류"] = df.loc[m5, "key"].map(ca["중분류"]); df.loc[m5, "보정"] = "R5 " + df.loc[m5, "key"].map(ca["신뢰"])
    n_r5 = int(m5.sum()); df["대분류"] = df["중분류"].str[0].map(MAJ)
    print(f"지원내용 기반 배정 {n_r5}건, 잔여 {int(df['중분류'].str.startswith(RP).sum())}건")
print("일관배정으로 변경", n_changed_consist, "| 규칙 R1", int(r1.sum()), "R2", int(r2.sum()))
aris = [ari(lab, KMeans(K, n_init=10, random_state=s).fit_predict(E)) for s in range(1, 11)]
taxo = df["지원분야중분류"].fillna("NA"); m = taxo != "NA"
g = pd.DataFrame({"k": key, "mid": df["중분류_연도별"], "maj": df["대분류_연도별"]}); g = g[g.groupby("k").k.transform("size") > 1]
stab = dict(emb=EMB, k=K, n_changed_by_program_consistency=n_changed_consist, n_rule_R1=int(r1.sum()), n_rule_R2=int(r2.sum()), n_rule_R3=n_r3, n_residual_before=n_resid, n_rule_R4=n_r4, n_rule_R5=n_r5, n_rule_R4_alt_ownradius=(n_r4_alt if RP and cfg.get("SECOND_PASS") else 0), n_unclassified=int(df["중분류"].str.startswith(RP).sum()) if RP else 0, ari_mean=np.mean(aris), ari_min=np.min(aris), silhouette=silhouette_score(E, lab), nmi_taxo=nmi(taxo[m], lab[m]), nmi_somewon=nmi(df["소관"], lab),
            consist_mid=(g.groupby("k").mid.nunique() == 1).mean(), consist_maj=(g.groupby("k").maj.nunique() == 1).mean(), n_multi_year_programs=g.k.nunique())
lab0 = KMeans(K, n_init=10, random_state=0).fit_predict(np.load("data/emb_lsa.npy")); stab["nmi_taxo_lsa"] = nmi(taxo[m], lab0[m]); stab["nmi_somewon_lsa"] = nmi(df["소관"], lab0)
json.dump({k: (v if isinstance(v, str) else float(v)) for k, v in stab.items()}, open(f"{OUT}/stability.json", "w"), indent=1, ensure_ascii=False); print(stab)
yrs = [2024, 2025, 2026]
EXCL = df["중분류"].str.startswith(RP) if RP else pd.Series(False, index=df.index)   # 유형화 제외(목적 서술 불충분)
dt = df[~EXCL]                                                                        # 유형 집계는 유형화된 사업만 대상
T0 = pd.DataFrame({"유형화 제외 건수": df[EXCL].groupby("year").size().reindex(yrs).fillna(0).astype(int),
                   "전체 건수": df.groupby("year").size().reindex(yrs), "유형화 제외 예산(백만원)": df[EXCL].groupby("year").내역예산.sum().reindex(yrs).fillna(0).round(0),
                   "전체 예산(백만원)": df.groupby("year").내역예산.sum().reindex(yrs).round(0)})
T0["건수 비중(%)"] = (T0["유형화 제외 건수"] / T0["전체 건수"] * 100).round(1); T0["예산 비중(%)"] = (T0["유형화 제외 예산(백만원)"] / T0["전체 예산(백만원)"] * 100).round(1)
T0.to_csv(f"{OUT}/T0_excluded_by_year.csv", encoding="utf-8-sig")
R5m = df["보정"].fillna("").str.startswith("R5")
T0c = pd.DataFrame({"내용기반 배정 건수": df[R5m].groupby("year").size().reindex(yrs).fillna(0).astype(int), "전체 건수": df.groupby("year").size().reindex(yrs),
                    "내용기반 배정 예산(백만원)": df[R5m].groupby("year").내역예산.sum().reindex(yrs).fillna(0).round(0), "전체 예산(백만원)": df.groupby("year").내역예산.sum().reindex(yrs).round(0)})
T0c["건수 비중(%)"] = (T0c["내용기반 배정 건수"] / T0c["전체 건수"] * 100).round(1); T0c["예산 비중(%)"] = (T0c["내용기반 배정 예산(백만원)"] / T0c["전체 예산(백만원)"] * 100).round(1)
T0c.to_csv(f"{OUT}/T0c_content_assigned_by_year.csv", encoding="utf-8-sig")
def agg(by):
    n = dt.pivot_table(index=by, columns="year", values="id", aggfunc="count").reindex(columns=yrs).fillna(0).astype(int)
    b = dt.pivot_table(index=by, columns="year", values="내역예산", aggfunc="sum").reindex(columns=yrs).fillna(0).round(0)
    t = pd.concat({"건수": n, "예산(백만원)": b}, axis=1); t[("예산(백만원)", "증감률24→26(%)")] = ((b[2026] / b[2024] - 1) * 100).round(1)
    t[("예산(백만원)", "2026비중(%)")] = (b[2026] / b[2026].sum() * 100).round(1); return t
T1 = agg("대분류"); T2 = agg(["대분류", "중분류"]); T1.to_csv(f"{OUT}/T1_major_by_year.csv", encoding="utf-8-sig"); T2.to_csv(f"{OUT}/T2_mid_by_year.csv", encoding="utf-8-sig")
d26 = dt[dt.year == 2026]
T3 = d26.pivot_table(index="소관", columns="대분류", values="내역예산", aggfunc="sum").fillna(0).round(0); T3["합계"] = T3.sum(1); T3 = T3.sort_values("합계", ascending=False); T3.to_csv(f"{OUT}/T3_somewon_x_major_2026.csv", encoding="utf-8-sig")
T3n = d26.pivot_table(index="소관", columns="대분류", values="id", aggfunc="count").fillna(0).astype(int); T3n.to_csv(f"{OUT}/T3n_somewon_x_major_2026_count.csv", encoding="utf-8-sig")
T4 = pd.crosstab(df["지원분야중분류"].fillna("(결측)"), df["대분류"]); T4["합계"] = T4.sum(1); T4 = T4.sort_values("합계", ascending=False); T4.to_csv(f"{OUT}/T4_taxonomy_x_major.csv", encoding="utf-8-sig")
T5 = pd.crosstab(dt["세부지원"].fillna("(결측)").str.replace(r" \(국고보조율.*\)", "", regex=True), dt["대분류"]); T5 = T5.loc[T5.sum(1).sort_values(ascending=False).index]; T5.to_csv(f"{OUT}/T5_fundingform_x_major.csv", encoding="utf-8-sig")
T6 = df.groupby("대분류").agg(건수=("id", "count"), 공고보유율=("has_gonggo", "mean"), 내역목적보유율=("목적출처", lambda s: (s == "내역목적").mean()), 평균토큰=("n_tok", "mean")).round(3); T6.to_csv(f"{OUT}/T6_text_coverage_by_major.csv", encoding="utf-8-sig")
dd = df.assign(k=key).sort_values("year"); ch = dd.groupby("k").filter(lambda x: x.대분류_연도별.nunique() > 1)
T7 = ch.groupby("k").apply(lambda x: " → ".join(f"{y}:{mm[:1]}" for y, mm in zip(x.year, x.대분류_연도별))).rename("연도별 텍스트기준 배정").reset_index()
T7["최종배정"] = T7.k.map(dd.drop_duplicates("k").set_index("k")["대분류"]); T7.to_csv(f"{OUT}/T7_type_switch_cases.csv", index=False, encoding="utf-8-sig")
T8 = d26.sort_values("내역예산", ascending=False).groupby("중분류").head(5)[["중분류", "소관", "세부사업명", "내역사업명", "내역예산"]]; T8.to_csv(f"{OUT}/T8_top_programs_2026.csv", index=False, encoding="utf-8-sig")
cols = ["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류", "대분류_연도별", "중분류_연도별", "보정", "지원분야중분류", "지원분야소분류", "세부지원", "목적출처", "has_gonggo", "doc"]
df[cols].to_csv(f"{OUT}/typology_assignments.csv", index=False, encoding="utf-8-sig")
with pd.ExcelWriter(f"{OUT}/typology_assignments.xlsx") as w:
    df[cols].to_excel(w, sheet_name="배정결과", index=False)
    for nm, t in [("T1 대분류", T1), ("T2 중분류", T2), ("T3 소관x유형(2026예산)", T3), ("T4 기존분류x유형", T4), ("T5 지원형태x유형", T5)]: t.to_excel(w, sheet_name=nm)
    T7.to_excel(w, sheet_name="T7 유형전환", index=False); T8.to_excel(w, sheet_name="T8 대표사업", index=False)
df[["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류"]].to_parquet("data/final_assign.parquet" if OUT == "output" else f"data/final_assign_{EMB}.parquet", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(T1.to_string()); print(); print(T2.to_string()); print(); print(T6.to_string()); print(); print("전환 사례", len(T7), "/", g.k.nunique()); print(T7.head(12).to_string())
