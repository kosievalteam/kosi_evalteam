"""최종 유형화: fn 임베딩 KMeans(k=24) 군집 → 해석적 병합: 중분류(21) → 대분류(10).
   내역사업 단위 일관 배정(연도 평균 임베딩의 최근접 중심) + 메타데이터 보정규칙 → 집계표·안정성·행단위 배정 산출."""
import os, json, re, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score as ari, silhouette_score, normalized_mutual_info_score as nmi
df = pd.read_parquet("data/corpus.parquet"); E = np.load("data/emb_fn.npy")
km = KMeans(24, n_init=20, random_state=0).fit(E); lab = km.labels_; assert (lab == np.load("data/labels_fn_k24.npy")).all()
df["c"] = lab
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id"); df["세부지원"] = df.id.map(raw["세부지원"])
MID = {  # k=24 군집 → 중분류 (군집 프로파일 해석; output/cluster_profile_fn_k24 참조)
 11:"A1 기술개발(일반 R&D)", 8:"A2 원천·핵심기술 개발", 2:"A3 산학연·공동 R&D", 19:"A3 산학연·공동 R&D", 0:"A4 바이오·전략기술 R&D·사업화", 16:"A5 모빌리티 기술개발·기반구축", 23:"A6 에너지 기술개발·실증",
 1:"B1 지역·특구 상용화·공공실증", 15:"B2 현장 혁신·보급(스마트제조·현장지도)",
 12:"C1 창업·벤처 육성",
 5:"D1 수출 마케팅(전시·상담회)", 9:"D2 해외시장 진출", 20:"D3 수출업체 육성(농식품 등)",
 17:"E1 정책자금 융자(운전·시설)", 21:"E1 정책자금 융자(운전·시설)", 7:"E2 투자·보증·자금조달 지원",
 6:"F1 시설·설비 현대화",
 10:"G1 전문인력 양성·채용", 22:"G1 전문인력 양성·채용",
 13:"H1 고용장려금·고용안정", 14:"H2 산업안전·사업주 훈련지원",
 3:"I1 컨설팅·바우처·마케팅 서비스", 4:"I2 판로·공공구매 지원",
 18:"J1 복합·기반조성(판로·제도·생태계 등)"}
MAJ = {"A":"A. 기술개발(R&D)", "B":"B. 실증·상용화·기술사업화", "C":"C. 창업·벤처 육성", "D":"D. 수출·해외진출", "E":"E. 자금공급(융자·보증·투자)",
       "F":"F. 시설·설비 투자", "G":"G. 인력양성", "H":"H. 고용·노동환경", "I":"I. 경영·사업화 서비스", "J":"J. 복합·기반조성(기타)"}
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
r1 = (df["세부사업명"].fillna("").str.contains(r"\(융자\)") | df["세부지원"].fillna("").str.contains("융자")) & ~df["대분류"].str[0].isin(list("CDEF"))
r2 = nm.str.contains("보증|대위변제|팩토링|보험금|재보증") & (df["대분류"].str[0] != "E")
df.loc[r1, "중분류"] = "E1 정책자금 융자(운전·시설)"; df.loc[r2, "중분류"] = "E2 투자·보증·자금조달 지원"
df["대분류"] = df["중분류"].str[0].map(MAJ); df["보정"] = np.where(r1, "R1 융자", np.where(r2, "R2 보증·보험", ""))
print("일관배정으로 변경", n_changed_consist, "| 규칙 R1", int(r1.sum()), "R2", int(r2.sum()))
aris = [ari(lab, KMeans(24, n_init=10, random_state=s).fit_predict(E)) for s in range(1, 11)]
taxo = df["지원분야중분류"].fillna("NA"); m = taxo != "NA"
g = pd.DataFrame({"k": key, "mid": df["중분류_연도별"], "maj": df["대분류_연도별"]}); g = g[g.groupby("k").k.transform("size") > 1]
stab = dict(n_changed_by_program_consistency=n_changed_consist, n_rule_R1=int(r1.sum()), n_rule_R2=int(r2.sum()), ari_mean=np.mean(aris), ari_min=np.min(aris), silhouette=silhouette_score(E, lab), nmi_taxo=nmi(taxo[m], lab[m]), nmi_somewon=nmi(df["소관"], lab),
            consist_mid=(g.groupby("k").mid.nunique() == 1).mean(), consist_maj=(g.groupby("k").maj.nunique() == 1).mean(), n_multi_year_programs=g.k.nunique())
lab0 = KMeans(24, n_init=10, random_state=0).fit_predict(np.load("data/emb_lsa.npy")); stab["nmi_taxo_lsa"] = nmi(taxo[m], lab0[m]); stab["nmi_somewon_lsa"] = nmi(df["소관"], lab0)
json.dump({k: float(v) for k, v in stab.items()}, open("output/stability.json", "w"), indent=1, ensure_ascii=False); print(stab)
yrs = [2024, 2025, 2026]
def agg(by):
    n = df.pivot_table(index=by, columns="year", values="id", aggfunc="count").reindex(columns=yrs).fillna(0).astype(int)
    b = df.pivot_table(index=by, columns="year", values="내역예산", aggfunc="sum").reindex(columns=yrs).fillna(0).round(0)
    t = pd.concat({"건수": n, "예산(백만원)": b}, axis=1); t[("예산(백만원)", "증감률24→26(%)")] = ((b[2026] / b[2024] - 1) * 100).round(1)
    t[("예산(백만원)", "2026비중(%)")] = (b[2026] / b[2026].sum() * 100).round(1); return t
T1 = agg("대분류"); T2 = agg(["대분류", "중분류"]); T1.to_csv("output/T1_major_by_year.csv", encoding="utf-8-sig"); T2.to_csv("output/T2_mid_by_year.csv", encoding="utf-8-sig")
d26 = df[df.year == 2026]
T3 = d26.pivot_table(index="소관", columns="대분류", values="내역예산", aggfunc="sum").fillna(0).round(0); T3["합계"] = T3.sum(1); T3 = T3.sort_values("합계", ascending=False); T3.to_csv("output/T3_somewon_x_major_2026.csv", encoding="utf-8-sig")
T3n = d26.pivot_table(index="소관", columns="대분류", values="id", aggfunc="count").fillna(0).astype(int); T3n.to_csv("output/T3n_somewon_x_major_2026_count.csv", encoding="utf-8-sig")
T4 = pd.crosstab(df["지원분야중분류"].fillna("(결측)"), df["대분류"]); T4["합계"] = T4.sum(1); T4 = T4.sort_values("합계", ascending=False); T4.to_csv("output/T4_taxonomy_x_major.csv", encoding="utf-8-sig")
T5 = pd.crosstab(df["세부지원"].fillna("(결측)").str.replace(r" \(국고보조율.*\)", "", regex=True), df["대분류"]); T5 = T5.loc[T5.sum(1).sort_values(ascending=False).index]; T5.to_csv("output/T5_fundingform_x_major.csv", encoding="utf-8-sig")
T6 = df.groupby("대분류").agg(건수=("id", "count"), 공고보유율=("has_gonggo", "mean"), 내역목적보유율=("목적출처", lambda s: (s == "내역목적").mean()), 평균토큰=("n_tok", "mean")).round(3); T6.to_csv("output/T6_text_coverage_by_major.csv", encoding="utf-8-sig")
dd = df.assign(k=key).sort_values("year"); ch = dd.groupby("k").filter(lambda x: x.대분류_연도별.nunique() > 1)
T7 = ch.groupby("k").apply(lambda x: " → ".join(f"{y}:{mm[:1]}" for y, mm in zip(x.year, x.대분류_연도별))).rename("연도별 텍스트기준 배정").reset_index()
T7["최종배정"] = T7.k.map(dd.drop_duplicates("k").set_index("k")["대분류"]); T7.to_csv("output/T7_type_switch_cases.csv", index=False, encoding="utf-8-sig")
T8 = d26.sort_values("내역예산", ascending=False).groupby("중분류").head(5)[["중분류", "소관", "세부사업명", "내역사업명", "내역예산"]]; T8.to_csv("output/T8_top_programs_2026.csv", index=False, encoding="utf-8-sig")
cols = ["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류", "대분류_연도별", "중분류_연도별", "보정", "지원분야중분류", "지원분야소분류", "세부지원", "목적출처", "has_gonggo", "doc"]
df[cols].to_csv("output/typology_assignments.csv", index=False, encoding="utf-8-sig")
with pd.ExcelWriter("output/typology_assignments.xlsx") as w:
    df[cols].to_excel(w, sheet_name="배정결과", index=False)
    for nm, t in [("T1 대분류", T1), ("T2 중분류", T2), ("T3 소관x유형(2026예산)", T3), ("T4 기존분류x유형", T4), ("T5 지원형태x유형", T5)]: t.to_excel(w, sheet_name=nm)
    T7.to_excel(w, sheet_name="T7 유형전환", index=False); T8.to_excel(w, sheet_name="T8 대표사업", index=False)
df[["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류"]].to_parquet("data/final_assign.parquet", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(T1.to_string()); print(); print(T2.to_string()); print(); print(T6.to_string()); print(); print("전환 사례", len(T7), "/", g.k.nunique()); print(T7.head(12).to_string())
