"""후속 호(AI 지원사업) 준비: AI 사업 전수 검토표, 산출근거 기반 AI 예산 범위, AI 지원 유형 집계.
   - 관여도: 14번과 같은 판정식을 연도별로 적용(이번 호는 내역사업 단위 연도 중 최고 단계) 후 config/ai_review.json의 검토 결과로 보정
   - AI 예산: 핵심=내역예산 전액. 활용=산출근거에서 AI 어휘가 붙은 항목 금액(자동 추출) → 검토 결과(lo/hi)가 있으면 우선
       하한=AI 전용 항목 합계, 상한=AI 포함 항목('AI트랙 포함' 등)까지 합계, 금액을 찾지 못하면 하한 0·상한 전액
   - AI 지원 유형: 인력·교육 / 창업·기업육성 / 실증·상용화 / 도입·활용(AX) / 기술개발 / 인프라·데이터 (사업명 → 목적 → 유형 코드 순 자동 판정 후 검토 보정)
사용: python scripts/16_ai_followup.py  →  output_bge-m3/A1_ai_review.xlsx, A2~A5_*.csv, ai_followup_summary.json
"""
import os, re, json, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = "output_bge-m3"
X = pd.read_csv(f"{OUT}/industry_assignments.csv").merge(pd.read_csv(f"{OUT}/axes_assignments.csv")[["id", "중분류"]], on="id", how="left")
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id"); calc = pd.read_csv("data/biz_calc_2024_2026.csv").set_index("id")
REV = json.load(open("config/ai_review.json", encoding="utf-8"))["items"]
X["목적"] = X.id.map(raw["내역목적"]).fillna(X.id.map(raw["세부목적"])).fillna("")
X["공고"] = X.id.map(raw["공고지원내용"]).fillna("")
X["산출근거"] = X.id.map(calc["산출근거"]).fillna("")
X["rk"] = X["소관"] + "|" + X["내역사업명"]

# ---- 연도별 관여도(14번과 같은 판정식)
AI = r"(?<![A-Za-z])(AI|AX)(?![A-Za-z])|(?<![A-Za-z])AI(?=AGENT|SW|DX)|인공지능|생성형|머신러닝|딥러닝|거대언어|(?<![A-Za-z])LLM(?![A-Za-z])"
APP = r"((?<![A-Za-z])(AI|AX)(?![A-Za-z])|인공지능)\s?[·‧ㆍ]?\s?((DX|DT)\s?)?(-?\s?(활용|도입|적용|기반|전환|융합|솔루션|서비스|모델|개발|프로젝트|과정|교육|실증|알고리즘|역량|바우처|반도체|Native|응용|컴퓨팅|에이전트|학습|클라우드))|(?<![A-Za-z])AX\s?전환|생성형|LLM|머신러닝|딥러닝"
name = X["세부사업명"].fillna("") + " " + X["내역사업명"].fillna("")
body = X["목적"] + " " + X["공고"] + " " + X["산출근거"] + " " + X.id.map(raw["수혜대상"]).fillna("")
n_ai, n_app = body.str.count(AI), body.str.count(APP)
LV = {3: "핵심", 2: "활용", 1: "언급", 0: "없음"}
X["관여도_연도"] = pd.Series(np.select([name.str.contains(AI), (n_app >= 2) | ((n_app >= 1) & (n_ai >= 3)) | (n_ai >= 4), n_ai >= 1], [3, 2, 1], 0), index=X.index).map(LV)
X["관여도_검토"] = [REV.get(k, {}).get("level", v) if v != "없음" or REV.get(k, {}).get("level") else v for k, v in zip(X.rk, X["관여도_연도"])]
AMT = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(백만원|억원)")


def ai_items(text):
    items, used = [], set()
    for m in re.finditer(AI, text):
        win = text[m.start(): m.start() + 90]; eq = win.find("=")
        a = AMT.search(win, eq if 0 <= eq < 70 else 0)
        if not a or a.start() + m.start() in used: continue
        used.add(a.start() + m.start())
        v = float(a.group(1).replace(",", "")) * (100 if a.group(2) == "억원" else 1)
        incl = "포함" in win[:a.start()] or bool(re.search(r"\([^)]*$", text[max(0, m.start() - 15): m.start()]))
        items.append((round(v), "포함" if incl else "전용", win[:a.end()].replace("\n", " ")))
    return items


def snippets(text, n=3, w=45):
    out = []
    for m in re.finditer(AI, text):
        s = text[max(0, m.start() - w): m.end() + w].replace("\n", " ").strip()
        if not out or s[:20] not in out[-1]: out.append(s)
        if len(out) >= n: break
    return " … ".join(out)


TYPES = [("인력·교육", r"교육|훈련|인재|인력|아카데미|일학습|과정", ("F2", "F1", "A7"), ("K9",)),
         ("창업·기업육성", r"창업|스타트업|벤처|TIPS|팁스|기업육성|기업집중육성", ("B1",), ("K5",)),
         ("실증·상용화", r"실증|상용화|사업화|확산|테스트베드", ("A8", "A9"), ()),
         ("도입·활용(AX)", r"도입|활용|전환|AX|바우처|스마트공장|스마트 ?제조|제조AI|솔루션|공급기업|수요기업", ("G1", "G2", "E1", "E2"), ("K7", "K8")),
         ("기술개발", r"기술개발|R&D|연구개발|핵심기술|원천", ("A1", "A2", "A3", "A4", "A5", "A6"), ("K1",)),
         ("인프라·데이터", r"인프라|데이터|컴퓨팅|클러스터|플랫폼|센터|거점", (), ("K2", "K3"))]


def ai_type(r):
    for src in (r["내역사업명"], f"{r['세부사업명']} {r['내역사업명']}", r["목적"][:300]):
        for t, pat, _, _ in TYPES:
            if re.search(pat, src): return t
    mid, con = str(r["중분류"])[:2], str(r["내용유형"]).split(" ")[0]
    for t, _, mids, cons in TYPES:
        if mid in mids or con in cons: return t
    return "기타"


AIX = X[X["관여도_검토"].isin(["핵심", "활용"]) | X["관여도_연도"].isin(["핵심", "활용"])].copy()
rows = []
for i, r in AIX.iterrows():
    b, lv, rv = r["내역예산"], r["관여도_검토"], REV.get(r["rk"], {})
    it = ai_items(r["산출근거"]) if lv == "활용" else []
    if lv == "핵심": lo = hi = b; basis = "전액(핵심)"
    elif lv != "활용": lo = hi = 0.0; basis = f"제외({lv})"
    elif rv.get("year") == r["year"] and "lo" in rv: lo, hi, basis = float(rv["lo"]), float(rv["hi"]), "검토 확정"
    elif it: lo = min(sum(v for v, k, _ in it if k == "전용"), b); hi = min(sum(v for v, _, _ in it), b); basis = "산출근거 자동 추출"
    else: lo, hi, basis = 0.0, b, "항목 금액 미확인"
    rows.append((lo, hi, basis, " | ".join(f"[{k}] {v:,}백만원: {s}" for v, k, s in it)))
AIX[["AI예산_하한", "AI예산_상한", "산정근거", "AI항목(자동)"]] = pd.DataFrame(rows, index=AIX.index)
auto_t = AIX.sort_values("year").groupby("rk").apply(lambda g: ai_type(g.iloc[-1]))
AIX["AI유형"] = [REV.get(k, {}).get("type", auto_t[k]) for k in AIX.rk]
AIX["검토 메모"] = [REV.get(k, {}).get("note", "") for k in AIX.rk]
AIX["근거(사업명·목적·공고)"] = [snippets(f"{a} {b} {c}") for a, b, c in zip(AIX["내역사업명"], AIX["목적"], AIX["공고"])]
INC = AIX["관여도_검토"].isin(["핵심", "활용"])

# ---- 검토표: 연도별 행
cols = ["year", "소관", "세부사업명", "내역사업명", "내역예산", "AI관여도", "관여도_연도", "관여도_검토", "AI유형", "대분류", "중분류", "대상유형", "수단유형", "내용유형",
        "AI예산_하한", "AI예산_상한", "산정근거", "검토 메모", "AI항목(자동)", "근거(사업명·목적·공고)"]
rev = AIX[cols].rename(columns={"year": "연도", "내역예산": "내역예산(백만원)", "AI관여도": "관여도(이번 호, 연도 최고)"}).sort_values(["연도", "관여도_검토", "내역예산(백만원)"], ascending=[False, True, False])
with pd.ExcelWriter(f"{OUT}/A1_ai_review.xlsx") as w:
    rev.to_excel(w, sheet_name="AI사업 검토표", index=False)
    pd.DataFrame({"항목": ["관여도(이번 호)", "관여도_연도", "관여도_검토", "AI 예산 하한·상한", "산정근거", "검토 메모"],
                  "설명": ["이번 호 기준: 내역사업 단위로 연도 중 가장 높은 단계", "해당 연도 서술만으로 판정한 단계", "연도별 판정에 config/ai_review.json 검토 결과를 반영한 단계(후속 호 기준)",
                         "핵심=전액, 활용=산출근거 AI 항목(검토 확정 우선), 금액 미확인 시 하한 0·상한 전액, 언급·없음=0", "전액(핵심) / 검토 확정 / 산출근거 자동 추출 / 항목 금액 미확인 / 제외",
                         "1차 검토 판단 근거(연구진 확인 필요)"]}).to_excel(w, sheet_name="설명", index=False)


def jo(v): return round(float(v) / 1e6, 2)
A = AIX[INC]
by = A.groupby(["year", "관여도_검토"]).agg(건수=("id", "size"), 예산=("내역예산", "sum"), 하한=("AI예산_하한", "sum"), 상한=("AI예산_상한", "sum")).reset_index()
for c in ["예산", "하한", "상한"]: by[c] = by[c].map(jo)
by.to_csv(f"{OUT}/A2_ai_budget_range_by_year.csv", index=False, encoding="utf-8-sig")
t = A.pivot_table(index="AI유형", columns="year", values=["id", "AI예산_하한", "AI예산_상한"], aggfunc={"id": "size", "AI예산_하한": "sum", "AI예산_상한": "sum"}).fillna(0)
t.columns = [f"{ {'id': '건수', 'AI예산_하한': '하한(조원)', 'AI예산_상한': '상한(조원)'}[a]} {y}" for a, y in t.columns]
for c in t.columns:
    if "조원" in c: t[c] = (t[c] / 1e6).round(3)
t.to_csv(f"{OUT}/A3_ai_type_by_year.csv", encoding="utf-8-sig")
d26 = A[A.year == 2026]
d26.groupby("소관").agg(건수=("id", "size"), 핵심=("관여도_검토", lambda s: int((s == "핵심").sum())), 하한=("AI예산_하한", "sum"), 상한=("AI예산_상한", "sum")).sort_values("상한", ascending=False) \
   .assign(하한=lambda d: d.하한.map(jo), 상한=lambda d: d.상한.map(jo)).to_csv(f"{OUT}/A4_ai_somewon_2026.csv", encoding="utf-8-sig")
pd.crosstab(d26["AI유형"], d26["수단유형"].str.split(" ").str[0], values=d26["AI예산_상한"], aggfunc="sum").fillna(0).div(1e6).round(3) \
  .to_csv(f"{OUT}/A5_ai_type_x_instrument_2026.csv", encoding="utf-8-sig")

pub = X[X["AI관여도"].isin(["핵심", "활용"])].groupby("year")["내역예산"].sum()
summ = {"검토 대상 내역사업(연도별 행)": int(len(AIX)), "검토 반영 후 AI 사업(연도별 행)": A.groupby("year").size().to_dict(),
        "연도별": {int(y): {"이번 호 집계(조원)": jo(pub.get(y, 0)), "AI예산 하한(조원)": jo(g.AI예산_하한.sum()), "AI예산 상한(조원)": jo(g.AI예산_상한.sum()),
                         "핵심(조원)": jo(g[g.관여도_검토 == "핵심"].내역예산.sum()), "건수": int(len(g))} for y, g in A.groupby("year")},
        "2026 유형별(하한~상한, 조원)": {k: [jo(g.AI예산_하한.sum()), jo(g.AI예산_상한.sum()), int(len(g))] for k, g in d26.groupby("AI유형")},
        "2026 산정근거": d26.산정근거.value_counts().to_dict(),
        "2026 제외·하향": AIX[(AIX.year == 2026) & ~INC][["내역사업명", "관여도_연도", "관여도_검토", "내역예산"]].values.tolist()}
json.dump(summ, open(f"{OUT}/ai_followup_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
