"""6축 유형 정의서용 집계: 축·유형별 2026년 건수·예산·비중, 2024~2026년 누적 건수, 2026년 예산 상위 대표 사업.
입력: output_bge-m3/axes_assignments.csv, industry_assignments.csv  출력: output_bge-m3/definition_stats.json
"""
import json
import pandas as pd

OUT = "output_bge-m3"
a = pd.read_csv(f"{OUT}/axes_assignments.csv")
s = pd.read_csv(f"{OUT}/industry_assignments.csv")
x = a.merge(s[["id", "지원산업(주)", "AI관여도"]], on="id", how="left")
x["대분류코드"] = x["대분류"].str[:1]

ABBR = {"중소벤처기업부": "중기부", "산업통상부": "산업부", "고용노동부": "고용부", "기후에너지환경부": "기후부", "문화체육관광부": "문체부",
        "농림축산식품부": "농식품부", "과학기술정보통신부": "과기부", "금융위원회": "금융위", "해양수산부": "해수부", "보건복지부": "복지부",
        "국토교통부": "국토부", "식품의약품안전처": "식약처", "행정안전부": "행안부"}
GENERIC = {"운영", "융자금", "출연금", "기반구축"}     # 내역사업명이 일반 명사인 경우 세부사업명으로 표기


def label(r):
    nm = r.세부사업명.replace("(융자)", "").replace("(R&D)", "") + " " + r.내역사업명 if r.내역사업명 in GENERIC else r.내역사업명
    return f"{nm}({ABBR.get(r.소관, r.소관)}, {r.내역예산 / 100:,.0f}억원)"


y = x[x.year == 2026]
tot = y["내역예산"].sum()
out = {"_meta": {"year": 2026, "n": int(len(y)), "budget_jo": round(tot / 1e6, 2), "n_all": int(len(x))}}
for col in ["대분류", "중분류", "대상유형", "수단유형", "내용유형", "지원산업(주)", "AI관여도"]:
    g = y.groupby(col)["내역예산"].agg(["size", "sum"])
    n_all = x.groupby(col).size()
    d = {}
    for k, r in g.iterrows():
        top = y[y[col] == k].sort_values("내역예산", ascending=False).drop_duplicates("내역사업명").head(3)
        d[k] = {"n26": int(r["size"]), "b26": round(r["sum"] / 1e6, 2), "sh": round(r["sum"] / tot * 100, 1),
                "nall": int(n_all.get(k, 0)), "ex": [label(t) for t in top.itertuples()]}
    out[col] = d
json.dump(out, open(f"{OUT}/definition_stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("written", {k: len(v) for k, v in out.items() if k != "_meta"})
