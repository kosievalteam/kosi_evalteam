"""복수 배정(태깅): 단일 배정(주 유형)은 유지하고, 복수의 목적·대상·수단·내용·산업을 가진 사업에 부 유형 태그를 부여.
   - 지원목적: ① 중분류 중심(hyb 임베딩의 유형별 평균)과의 유사도가 주 유형 유사도에 근접(차이 ≤ PURPOSE_MARGIN)하면 부 태그
                ② 사업명·지원형태의 강한 신호(융자→D1, 보증→D2, 창업→B1, 수출·해외→C1/C2, 장려금→G1, 인력양성→F1) 규칙 태그
   - 지원대상: 수혜대상 필드의 대상 어휘 사전(T1~T10) → 어휘가 있는 유형 모두 태그
   - 지원수단: 지원형태 메타(출연·보조·직접·융자·출자)를 분해하고 수단 어휘(보증·팩토링, 바우처, 장려금, R&D)를 결합 → 형태별 유형 모두 태그
   - 지원내용: ① 지원내용 문서의 내용 어휘 사전(K1~K11) 2회 이상 ② 유형 중심 유사도 근접(≤ CONTENT_MARGIN)
   - 지원산업: 14번의 복수 태그 그대로
   동일 내역사업은 연도 통합(텍스트 합집합, 임베딩 평균)으로 판정. 유형당 태그 수 상한 TAG_CAP(주 유형 포함)
사용: python scripts/17_multilabel.py  →  output_bge-m3/multilabel_assignments.csv, M1~M4_*.csv, multilabel_summary.json
"""
import os, re, json, sys, numpy as np, pandas as pd
from sklearn.preprocessing import normalize
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = "output_bge-m3"
PURPOSE_MARGIN = float(os.environ.get("PURPOSE_MARGIN", 0.03)); CONTENT_MARGIN = float(os.environ.get("CONTENT_MARGIN", 0.02)); TAG_CAP = 3; LEX_MIN = int(os.environ.get("LEX_MIN", 3))

A = pd.read_csv(f"{OUT}/axes_assignments.csv")
S = pd.read_csv(f"{OUT}/industry_assignments.csv")[["id", "지원산업(주)", "지원산업(태그)", "AI관여도"]]
A = A.merge(S, on="id", how="left")
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id")
key = (A["소관"] + "|" + A["세부사업명"] + "|" + A["내역사업명"]).values
A["key"] = key
MID = sorted(A["중분류"].unique()); TGT = sorted(A["대상유형"].unique()); INS = sorted(A["수단유형"].unique()); CON = sorted(A["내용유형"].unique())
code = lambda s: str(s).split(" ")[0]
name_of = {code(t): t for t in MID + TGT + INS + CON}


def prog_text(col_series):
    return pd.Series(np.asarray(col_series, dtype=object), index=key).groupby(level=0).agg(lambda s: " ".join(dict.fromkeys(str(x) for x in s if pd.notna(x) and str(x) != "nan")))


def centroid_tags(E, labels, margin, exclude_prefix=None):
    """E: 행 임베딩(정규화), labels: 행별 유형. 사업 단위 평균 임베딩과 유형 중심의 코사인 유사도로 부 태그."""
    Em = normalize(pd.DataFrame(E).groupby(key).mean().values); keys = pd.DataFrame(E).groupby(key).mean().index
    types = sorted(set(labels)); C = normalize(np.vstack([E[np.array(labels) == t].mean(0) for t in types]))
    sim = Em @ C.T; prim = pd.Series(labels, index=key).groupby(level=0).first().reindex(keys).values
    out = {}
    for i, k in enumerate(keys):
        p = types.index(prim[i]); sp = sim[i, p]
        cand = [(sim[i, j] , types[j]) for j in range(len(types)) if j != p and sim[i, j] >= sp - margin and (exclude_prefix is None or not types[j].startswith(exclude_prefix))]
        out[k] = [t for _, t in sorted(cand, reverse=True)]
    return out, dict(zip(keys, prim))


def cap(prim, tags):
    seq = [prim] + [t for t in tags if t != prim]
    return list(dict.fromkeys(seq))[:TAG_CAP]


# ---------- ① 지원목적 ----------
Eh = np.load("data/emb_bge-m3_hyb.npy")
ptags, pprim = centroid_tags(Eh, A["중분류"].values, PURPOSE_MARGIN)
name = prog_text(A["세부사업명"] + " " + A["내역사업명"]); meta = prog_text(A["세부지원"].fillna(""))
PRULE = [("D1", lambda n, m: ("융자" in m) or bool(re.search(r"\(융자\)", n))), ("D2", lambda n, m: bool(re.search(r"보증|대위변제|팩토링|보험금|재보증", n))),
         ("B1", lambda n, m: bool(re.search(r"창업|스타트업|벤처", n))), ("C2", lambda n, m: bool(re.search(r"해외진출|해외 진출|글로벌", n))), ("C1", lambda n, m: bool(re.search(r"수출", n))),
         ("G1", lambda n, m: bool(re.search(r"장려금|고용유지|일자리", n))), ("F1", lambda n, m: bool(re.search(r"인력양성|인재양성|인력 양성|인재 양성", n)))]
purpose_tags = {}
for k in pprim:
    rule = [name_of[c] for c, f in PRULE if f(name[k], meta[k]) and code(pprim[k]) != c and code(pprim[k])[0] != c[0]]
    purpose_tags[k] = cap(pprim[k], ptags[k] + rule)

# ---------- ② 지원대상 ----------
TDICT = {"T1": r"중소기업|중견기업|중소·중견|중소ㆍ중견|소기업|기업체|제조업체|사업체|업체",
         "T2": r"벤처기업|이노비즈|인증|지정|선정된|우수|유망|글로벌|진출|희망|혁신형|강소|기술기업",
         "T3": r"예비창업|창업기업|창업자|스타트업|창업 ?\d|초기기업|업력", "T4": r"소상공인|소공인|자영업|전통시장|상인|상권",
         "T5": r"대학|연구소|연구기관|출연연|산학연|컨소시엄|연구개발기관|연구원", "T6": r"사업주|근로자|피보험자|재직자|노동자",
         "T7": r"국민|종사자|창작자|예술인|개인|청년|구직자|학생|일반인", "T8": r"지자체|지방자치단체|공공기관|수요기업|설치자|협회|단체|조합|기관|센터",
         "T9": r"농업인|어업인|농가|농어업|농식품|수산|임업|축산|영농|어촌|농촌", "T10": r"보증|채권|금융기관|보험|팩토링"}
tgt_text = prog_text(A["수혜대상"].fillna("")); tgt_prim = pd.Series(A["대상유형"].values, index=key).groupby(level=0).first()
target_tags = {}
for k in tgt_prim.index:
    tt = re.sub(r"고용보험|산재보험|보험료|보험 ?가입", "", tgt_text[k]); hits = [name_of[c] for c, pat in TDICT.items() if re.search(pat, tt)]
    if code(tgt_prim[k]) == "T0": hits = []
    target_tags[k] = cap(tgt_prim[k], hits)

# ---------- ③ 지원수단 ----------
ins_prim = pd.Series(A["수단유형"].values, index=key).groupby(level=0).first(); lex = prog_text(A["수단_text"].fillna("")); pur = pd.Series(A["대분류"].values, index=key).groupby(level=0).first()
instrument_tags = {}
for k in ins_prim.index:
    m, L, t = meta[k], lex[k], []
    if "융자" in m or re.search(r"\(융자\)", name[k]): t.append("I4")
    if "출자" in m: t.append("I7")
    if "보증팩토링" in L and ("직접" in m or str(pur[k]).startswith("D")): t.append("I8")
    if "바우처" in L: t.append("I9")
    if "출연" in m: t.append("I1" if "R&D과제" in L else "I2")
    if "보조" in m: t.append("I3")
    if "직접" in m: t.append("I5" if ("장려금인건비" in L and str(pur[k]).startswith("G")) else "I10")
    t = [name_of.get(c, "I7 투자·출자(펀드)") for c in t]
    instrument_tags[k] = cap(ins_prim[k], t)

# ---------- ④ 지원내용 ----------
KDICT = {"K1": r"기술개발|연구개발|R&D|과제|연구비|기술 개발", "K2": r"생태계|플랫폼|네트워크|협력체계|기반 ?구축|거점|클러스터|인프라",
         "K3": r"지역|사회적경제|사회적기업|마을|상권|활성화 프로그램|로컬", "K4": r"융자|대출|보증|이차보전|금리|상환|거치",
         "K5": r"사업화 ?자금|투자연계|투자 ?유치|보육|입주|액셀러|시제품|사업화 지원", "K6": r"전시회|상담회|바이어|해외 ?진출|수출|현지화|해외 마케팅",
         "K7": r"바우처|비용 ?지원|비용의|경비|보조금|매칭|소요 ?비용", "K8": r"컨설팅|진단|인증|시험|홍보|멘토링|자문|코칭|상담",
         "K9": r"교육|훈련|연수|과정 ?운영|아카데미|양성", "K10": r"장려금|인건비|지원금|수당|공제|급여", "K11": r"설비|시설|장비|방지시설|구축 ?지원|설치"}
ctext = prog_text(raw.loc[A.id, "공고지원내용"].fillna(raw.loc[A.id, "내역목적"]).fillna(raw.loc[A.id, "세부목적"]).fillna("").values)
Ec = np.load("data/axes/emb_content.npy"); ctags, cprim = centroid_tags(Ec, A["내용유형"].values, CONTENT_MARGIN, exclude_prefix="K0")
content_tags = {}
for k in cprim:
    txt = ctext[k]; hits = [(len(re.findall(pat, txt)), c) for c, pat in KDICT.items()]
    lexi = [name_of[c] for n, c in sorted(hits, reverse=True) if n >= LEX_MIN and code(cprim[k]) != c]
    content_tags[k] = cap(cprim[k], ctags[k] + lexi) if code(cprim[k]) != "K0" else [cprim[k]]

# ---------- ⑤ 지원산업 ----------
ind_tags = {k: v for k, v in zip(key, A["지원산업(태그)"].fillna("S0"))}

# ---------- 결과 ----------
A["목적_태그"] = [";".join(code(t) for t in cap(m, purpose_tags[k])) for k, m in zip(key, A["중분류"])]   # 연도별 주 유형(R1 등 규칙 적용분)을 앞에
A["대상_태그"] = [";".join(code(t) for t in target_tags[k]) for k in key]
A["수단_태그"] = [";".join(code(t) for t in instrument_tags[k]) for k in key]
A["내용_태그"] = [";".join(code(t) for t in content_tags[k]) for k in key]
A["산업_태그"] = [ind_tags[k] for k in key]
for ax in ["목적", "대상", "수단", "내용", "산업"]: A[f"{ax}_태그수"] = A[f"{ax}_태그"].str.count(";") + 1
cols = ["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류", "목적_태그", "대상유형", "대상_태그", "수단유형", "수단_태그", "내용유형", "내용_태그", "지원산업(주)", "산업_태그", "AI관여도"] + [f"{ax}_태그수" for ax in ["목적", "대상", "수단", "내용", "산업"]]
A[cols].to_csv(f"{OUT}/multilabel_assignments.csv", index=False, encoding="utf-8-sig")

d26 = A[A.year == 2026]; tot = d26["내역예산"].sum()
jo = lambda v: round(float(v) / 1e6, 2)
rows = []
for ax, prim_col, names in [("목적", "중분류", MID), ("대상", "대상유형", TGT), ("수단", "수단유형", INS), ("내용", "내용유형", CON)]:
    for t in names:
        c = code(t); pm = d26[prim_col] == t; tg = d26[f"{ax}_태그"].str.split(";").apply(lambda L: c in L)
        rows.append([ax, t, int(pm.sum()), jo(d26.loc[pm, "내역예산"].sum()), round(d26.loc[pm, "내역예산"].sum() / tot * 100, 1), int(tg.sum()), jo(d26.loc[tg, "내역예산"].sum()), round(d26.loc[tg, "내역예산"].sum() / tot * 100, 1)])
pd.DataFrame(rows, columns=["기준", "유형", "주 유형 건수", "주 유형 예산(조원)", "주 유형 비중(%)", "태그 건수", "태그 예산(조원)", "태그 비중(%)"]).to_csv(f"{OUT}/M1_tag_vs_primary_2026.csv", index=False, encoding="utf-8-sig")
share = pd.DataFrame([{ "기준": ax, "복수 태그 사업 비중(%)": round((d26[f"{ax}_태그수"] >= 2).mean() * 100, 1), "복수 태그 예산 비중(%)": round(d26.loc[d26[f"{ax}_태그수"] >= 2, "내역예산"].sum() / tot * 100, 1), "평균 태그 수": round(d26[f"{ax}_태그수"].mean(), 2), "태그 합계/건수": round(d26[f"{ax}_태그수"].sum() / len(d26), 2)} for ax in ["목적", "대상", "수단", "내용", "산업"]])
share.to_csv(f"{OUT}/M2_multi_share_2026.csv", index=False, encoding="utf-8-sig")
pairs = []
for ax in ["목적", "대상", "수단", "내용", "산업"]:
    pc = {}
    for L, b in zip(d26[f"{ax}_태그"].str.split(";"), d26["내역예산"]):
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                p = tuple(sorted([L[i], L[j]])); pc.setdefault(p, [0, 0.0]); pc[p][0] += 1; pc[p][1] += b
    for p, (n, b) in sorted(pc.items(), key=lambda x: -x[1][0])[:8]: pairs.append([ax, " + ".join(p), n, jo(b)])
pd.DataFrame(pairs, columns=["기준", "태그 조합", "건수", "예산(조원)"]).to_csv(f"{OUT}/M3_tag_pairs_2026.csv", index=False, encoding="utf-8-sig")
KNOWN = ["희망리턴패키지", "창업기반지원", "농식품글로벌육성지원자금(융자)", "생산및시설자금", "소상공인역량강화", "제조혁신구축지원", "TIPS", "청년일자리도약장려금", "수출바우처", "산업맞춤형", "일반훈련", "창업패키지"]
kn = A[A["내역사업명"].isin(KNOWN) | A["세부사업명"].isin(KNOWN)].sort_values("year").groupby("key").tail(1)
kn[["year", "소관", "세부사업명", "내역사업명", "중분류", "목적_태그", "대상유형", "대상_태그", "수단유형", "수단_태그", "내용유형", "내용_태그", "산업_태그"]].to_csv(f"{OUT}/M4_known_cases.csv", index=False, encoding="utf-8-sig")
summ = {"params": {"PURPOSE_MARGIN": PURPOSE_MARGIN, "CONTENT_MARGIN": CONTENT_MARGIN, "TAG_CAP": TAG_CAP}, "share_2026": share.to_dict("records"),
        "programs_multi_any_axis_2026(%)": round(float((d26[[f"{ax}_태그수" for ax in ["목적", "대상", "수단", "내용", "산업"]]].ge(2).any(axis=1)).mean() * 100), 1)}
json.dump(summ, open(f"{OUT}/multilabel_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(share.to_string(index=False)); print("any-axis multi:", summ["programs_multi_any_axis_2026(%)"])
print(kn[["내역사업명", "중분류", "목적_태그", "대상_태그", "수단_태그", "내용_태그"]].to_string(index=False))
