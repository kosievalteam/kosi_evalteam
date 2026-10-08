"""지원내용 기반 배정: 목적 서술이 일반 어휘에 그쳐 군집 단계에서 유형화되지 않은 사업(잔여 Z군집)을
   지원내용 문서(내역사업명 + 공고 지원내용 + 예산 산출근거 + 수혜대상 + 지원형태)로 유형화한다.
   - 학습: 군집 단계에서 유형이 정해진 사업(보정 R5 제외)의 중분류 라벨
   - 특성: 지원내용 문서 임베딩 + 지원내용 축 임베딩(공고/내역목적, 영역 방향 제거) + 목적 결합 임베딩 (내역사업 단위 GroupKFold로 비교·선택)
   - 예측: 잔여 사업의 내역사업 단위 평균 확률 → 최대 확률 중분류. 확률 0.5 미만은 '저신뢰'로 표시
   - 내용 명시 규칙(R5-규칙): 소상공인 대상 + 지원내용에 '비용부담 경감·손실보상'이 명시된 사업은 기존 중분류에 대응 유형이 없어
     D3 경영비용 경감·손실 보전(바우처·보상금)으로 배정
사용: python scripts/10_content_assign.py   (07_final_typology.py 1차 실행 후)  →  data/content_assign_bge-m3.csv, output_bge-m3/content_assign_*.csv/json
"""
import os, re, json, numpy as np, pandas as pd
os.environ.setdefault("HF_HUB_DISABLE_XET", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import normalize
OUT = "output_bge-m3"
A = pd.read_csv(f"{OUT}/typology_assignments.csv"); raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id")
calc = pd.read_csv("data/biz_calc_2024_2026.csv").set_index("id")
def clean(s):
    s = str(s) if isinstance(s, str) else ""
    s = re.sub(r"[\(（]?[’‘'`]?\d{2,4}[^)）]{0,30}[\)）]?\s*[\d,\.]+\s*백만원", " ", s)       # 연도별 금액 표기 제거
    s = re.sub(r"[\d,\.]+\s*(백만원|억원|천원|원|%|개소|개사|명|건|개)", " ", s); s = re.sub(r"[→×\*\+\-:①-⑳]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
key = (A["소관"] + "|" + A["세부사업명"] + "|" + A["내역사업명"]).values
gg = A.id.map(raw["공고지원내용"]).fillna(""); cb = A.id.map(calc["산출근거"]).map(clean)
tg = A.id.map(raw["수혜대상"]).fillna(""); fm = A.id.map(raw["세부지원"]).fillna("").str.replace(r"\s*\(.*?\)", "", regex=True)
fallback = A.id.map(raw["내역목적"]).fillna(A.id.map(raw["세부목적"])).fillna("")
has_content = (gg.str.len() > 5) | (cb.str.len() > 20)
doc = (A["내역사업명"].fillna("") + ". 지원내용: " + gg.str[:700] + " " + cb.str[:700] + " 대상: " + tg + " 형태: " + fm)
doc = np.where(has_content, doc, A["내역사업명"].fillna("") + ". " + fallback.str[:700] + " 대상: " + tg + " 형태: " + fm)
A["내용문서_출처"] = np.where(gg.str.len() > 5, np.where(cb.str.len() > 20, "공고+산출근거", "공고"), np.where(cb.str.len() > 20, "산출근거", "목적(대체)"))
p = "data/axes/emb_contentdoc.npy"
if os.path.exists(p): Ed = np.load(p)
else:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("BAAI/bge-m3", device="cpu"); Ed = m.encode(list(doc), batch_size=16, normalize_embeddings=True, show_progress_bar=False); np.save(p, Ed)
Eh = normalize(np.load("data/emb_bge-m3_hyb.npy")); Ec = np.load("data/axes/emb_content.npy")
train = ~A["대분류"].str.startswith("유형화") & ~A["보정"].fillna("").str.startswith("R5")
target = ~train
y = A["중분류"].where(train)
FEATS = {"내용문서": Ed, "내용문서+내용축": np.hstack([Ed, Ec]), "목적결합": Eh, "내용문서+내용축+목적결합": np.hstack([Ed, Ec, Eh])}
gkf = GroupKFold(n_splits=5); res = {}
for nm, X in FEATS.items():
    pred = pd.Series(index=A.index[train], dtype=object); proba_max = pd.Series(index=A.index[train], dtype=float)
    Xt, yt, gt = X[train.values], y[train].values, key[train.values]
    for tr, te in gkf.split(Xt, yt, gt):
        clf = LogisticRegression(C=4.0, max_iter=3000).fit(Xt[tr], yt[tr])
        P = clf.predict_proba(Xt[te]); pred.iloc[te] = clf.classes_[P.argmax(1)]; proba_max.iloc[te] = P.max(1)
    acc_mid = float((pred.values == yt).mean()); acc_maj = float((pred.str[0].values == pd.Series(yt).str[0].values).mean())
    sub = A.loc[train, "내용문서_출처"].values != "목적(대체)"
    res[nm] = dict(acc_mid=round(acc_mid, 3), acc_maj=round(acc_maj, 3), acc_maj_content_docs=round(float((pred.str[0].values[sub] == pd.Series(yt).str[0].values[sub]).mean()), 3),
                   acc_maj_hiconf=round(float((pred.str[0].values[proba_max.values >= .5] == pd.Series(yt).str[0].values[proba_max.values >= .5]).mean()), 3), share_hiconf=round(float((proba_max.values >= .5).mean()), 3))
    print(nm, res[nm])
# 지원내용 문서·지원내용 축을 중심으로 하되, 목적 결합 임베딩을 함께 써서 교차검증 정확도가 가장 높은 조합으로 배정
CHOSEN = "내용문서+내용축+목적결합"; X = FEATS[CHOSEN]
clf = LogisticRegression(C=4.0, max_iter=3000).fit(X[train.values], y[train].values)
P = pd.DataFrame(clf.predict_proba(X), columns=clf.classes_, index=A.index)
Pk = P.groupby(key).mean()                                             # 내역사업 단위 평균 확률
best = Pk.idxmax(1); conf = Pk.max(1); second = Pk.apply(lambda r: r.drop(r.idxmax()).idxmax(), axis=1)
out = pd.DataFrame({"key": Pk.index, "중분류": best.values, "확률": conf.round(3).values, "차순위": second.values})
tk = pd.Series(key[target.values]).unique(); out = out[out.key.isin(tk)]
out["신뢰"] = np.where(out["확률"] >= .5, "내용기반", "내용기반(저신뢰)")
# 내용 명시 규칙: 소상공인 대상 경영비용 경감·손실 보전(현금성) 사업
txt = (A.id.map(raw["내역목적"]).fillna("") + " " + gg + " " + A.id.map(calc["산출근거"]).fillna("")).values
rule = pd.Series(pd.Series(txt).str.contains(r"비용\s?부담\s?경감|손실\s?보상").values & tg.str.contains("소상공인").values & target.values)
rk = set(key[rule.values]); D3 = "D3 경영비용 경감·손실 보전(바우처·보상금)"
out.loc[out.key.isin(rk), ["중분류", "신뢰"]] = [D3, "내용명시 규칙"]
out.to_csv("data/content_assign_bge-m3.csv", index=False, encoding="utf-8-sig")
T = A[target].copy(); T["key"] = key[target.values]; T = T.merge(out, on="key", suffixes=("_기존", ""))
T["내용문서_출처"] = A.loc[target, "내용문서_출처"].values
T[["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "중분류", "확률", "차순위", "신뢰", "내용문서_출처"]].sort_values("내역예산", ascending=False).to_csv(f"{OUT}/content_assign_cases.csv", index=False, encoding="utf-8-sig")
# 외부 대조: 어휘 임베딩(LSA) 유형화가 같은 사업을 유형화한 경우의 대분류 일치율
lsa = pd.read_parquet("data/final_assign.parquet").set_index("id")["대분류"]
lt = T.id.map(lsa); okm = lt.notna() & ~lt.fillna("").str.startswith("유형화")
summ = dict(n_target_rows=int(target.sum()), n_target_programs=int(len(out)), cv=res, chosen=CHOSEN, n_rule_programs=int(len(rk)),
            share_hiconf_rows=round(float((T["신뢰"] == "내용기반").mean()), 3), src_dist=T["내용문서_출처"].value_counts().to_dict(),
            lsa_typed_rows=int(okm.sum()), lsa_agree_maj=round(float((lt[okm].str[0] == T.loc[okm, "중분류"].str[0]).mean()), 3),
            maj_dist_rows=T["중분류"].str[0].value_counts().to_dict(), maj_dist_budget2026=T[T.year == 2026].groupby(T["중분류"].str[0]).내역예산.sum().round(0).to_dict())
json.dump(summ, open(f"{OUT}/content_assign_summary.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(summ, ensure_ascii=False, indent=1))
