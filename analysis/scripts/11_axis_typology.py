"""축별 독립 유형화 (지원목적과 동일 절차): 축별 텍스트/특성 → 임베딩 → KMeans → 프로파일 출력(라벨링용) 또는 매핑 적용(최종).
  대상: 수혜대상 필드 → bge-m3 임베딩 → k=12
  내용: 공고 지원내용(없으면 내역목적) → bge-m3 임베딩(지원산업·소관 판별방향 제거) → k=16
  수단: 지원형태 메타(출연·보조·직접·융자·출자) + 수단 어휘 신호의 우선순위 규칙(범주형 속성이므로 군집 대신 규칙)
사용: python 11_axis_typology.py profile            # 프로파일 → output_bge-m3/axis_profiles.md
      python 11_axis_typology.py final --map config/axes_mapping.json
"""
import os, re, sys, json, argparse, numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["profile", "final"]); ap.add_argument("--map", default="config/axes_mapping.json"); ap.add_argument("--out", default="output_bge-m3")
ap.add_argument("--k_target", type=int, default=12); ap.add_argument("--k_content", type=int, default=16); ap.add_argument("--k_instr", type=int, default=10)
args = ap.parse_args(); OUT = args.out
A = pd.read_csv(f"{OUT}/typology_assignments.csv"); raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id")
for c in ["수혜대상", "세부지원", "내역목적", "공고지원내용", "세부목적", "지원분야소분류", "지원산업"]: A[c] = A.id.map(raw[c])
os.makedirs("data/axes", exist_ok=True)
def embed(texts, name):
    p = f"data/axes/emb_{name}.npy"
    if os.path.exists(p): return np.load(p)
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("BAAI/bge-m3", device="cpu"); E = m.encode(list(texts), batch_size=16, normalize_embeddings=True, show_progress_bar=False); np.save(p, E); return E
def norm(s): return re.sub(r"\s+", " ", str(s)).strip()
# ---------- 축 텍스트/특성 ----------
A["대상_text"] = A["수혜대상"].fillna("").map(norm); A.loc[A["대상_text"] == "", "대상_text"] = "(수혜대상 미기재)"
A["내용_text"] = np.where(A["공고지원내용"].fillna("").str.strip() != "", A["공고지원내용"].fillna(""), A["내역목적"].fillna(A["세부목적"]).fillna("")); A["내용_text"] = A["내용_text"].map(norm).str[:1500]
A["내용_출처"] = np.where(A["공고지원내용"].fillna("").str.strip() != "", "공고", np.where(A["내역목적"].fillna("").str.strip() != "", "내역목적", "세부목적"))
meta = A["세부지원"].fillna("").str.replace(r"\s*\(.*?\)", "", regex=True)
body = (A["내역사업명"].fillna("") + " " + A["내역목적"].fillna(A["세부목적"]).fillna("") + " " + A["공고지원내용"].fillna("")).map(norm)
FEAT = {"메타_출연": meta.str.contains("출연"), "메타_보조": meta.str.contains("보조"), "메타_직접": meta.str.contains("직접"), "메타_융자": meta.str.contains("융자"), "메타_출자": meta.str.contains("출자"),
 "어휘_융자대출": body.str.contains(r"융자|대출|이차보전|금리"), "어휘_보증보험": body.str.contains(r"보증|보험|팩토링|대위변제"), "어휘_보증팩토링": body.str.replace(r"고용보험|산재보험|보험료|보험 가입|보험가입", "", regex=True).str.contains(r"보증|팩토링|대위변제|보험금|무역보험|수출보험"), "어휘_투자펀드": body.str.contains(r"펀드|투자유치|투자 유치|모태|엔젤|출자|투자연계"),
 "어휘_바우처": body.str.contains("바우처"), "어휘_장려금인건비": body.str.contains(r"장려금|인건비|지원금|수당|공제"), "어휘_R&D과제": body.str.contains(r"기술개발|연구개발|R&D|연구비"),
 "어휘_서비스": body.str.contains(r"컨설팅|교육|훈련|멘토링|코칭|진단|자문|지도|상담"), "어휘_공간장비": body.str.contains(r"입주|공간|보육|장비|시설 활용|플랫폼|테스트베드|센터"),
 "어휘_제도": body.str.contains(r"공공구매|조달|판로|인증|규제|특례|특구|샌드박스|지정|표준"), "어휘_비용보조": body.str.contains(r"비용|경비|사업비|자금 지원|매칭|국비")}
F = pd.DataFrame(FEAT).astype(float); A["수단_text"] = [";".join(k.split("_")[1] for k in FEAT if F.loc[i, k] == 1) for i in A.index]
# ---------- 임베딩 ----------
Et = embed(A["대상_text"], "target"); Ec_raw = embed(A["내용_text"], "content")
dom = (A["지원산업"].fillna("NA") + "|" + A["소관"]).values; vc = pd.Series(dom).value_counts(); dom = np.where(pd.Series(dom).map(vc) >= 15, dom, "기타"); mask = ~pd.Series(dom).str.startswith("NA").values
lda = LDA(n_components=12, solver="eigen", shrinkage="auto").fit(Ec_raw[mask], dom[mask]); Q, _ = np.linalg.qr(lda.scalings_[:, :12]); Ec = normalize(Ec_raw - (Ec_raw @ Q) @ Q.T)
W = np.array([({"메타_융자": 3, "메타_출자": 3}.get(c, 2) if c.startswith("메타_") else 1) for c in F.columns], dtype=float)
Ei = normalize(F.values * W)          # 메타(지원형태) 가중
AX = {"target": (Et, args.k_target), "content": (Ec, args.k_content)}
lab = {}
for ax, (E, k) in AX.items():
    km = KMeans(k, n_init=20, random_state=0).fit(E); lab[ax] = km.labels_; np.save(f"data/axes/labels_{ax}_k{k}.npy", km.labels_); np.save(f"data/axes/centers_{ax}_k{k}.npy", km.cluster_centers_)
    A[f"{ax}_c"] = km.labels_
# 프로그램 단위 일관 배정(연도 평균 임베딩 최근접 중심)
key = A["소관"] + "|" + A["세부사업명"] + "|" + A["내역사업명"]
for ax, (E, k) in AX.items():
    C = np.load(f"data/axes/centers_{ax}_k{k}.npy"); Em = pd.DataFrame(E).groupby(key.values).mean(); Pm = normalize(Em.values)
    pc = pd.Series(np.argmin(((Pm[:, None, :] - C[None]) ** 2).sum(-1), 1), index=Em.index); A[f"{ax}_cp"] = key.map(pc).values
if args.mode == "profile":
    from kiwipiepy import Kiwi; kiwi = Kiwi()
    def topw(texts, n=12, stop=set("지원 사업 등 및 중소기업 기업 대상 위하 통하 추진 운영 강화 확대 경우 이내 최대 당".split())):
        from collections import Counter; c = Counter()
        for t in texts:
            for tk in kiwi.tokenize(str(t)[:400]):
                if tk.tag in ("NNG", "NNP", "SL") and len(tk.form) > 1 and tk.form not in stop: c[tk.form] += 1
        return ", ".join(w for w, _ in c.most_common(n))
    out = []
    for ax, (E, k) in AX.items():
        out.append(f"\n# 축: {ax} (k={k})")
        for c in range(k):
            d = A[A[f"{ax}_c"] == c]; d26 = d[d.year == 2026]
            out.append(f"\n## {ax} C{c}  n={len(d)}  2026예산={d26.내역예산.sum():,.0f}백만원  목적분포: {', '.join(f'{k[:1]}{v}' for k, v in d['대분류'].value_counts().head(4).items())}")
            if ax == "target": out.append("대표 수혜대상: " + " | ".join(d["대상_text"].value_counts().head(8).index)); out.append("소분류: " + ", ".join(f"{k}{v}" for k, v in d["지원분야소분류"].fillna("NA").value_counts().head(3).items()))
            if ax == "content":
                out.append("핵심어: " + topw(d["내용_text"])); out.append("출처: " + ", ".join(f"{k}{v}" for k, v in d["내용_출처"].value_counts().items()))
                for t in d["내용_text"].sample(min(3, len(d)), random_state=0): out.append("  · " + t[:160])
            out.append("예시: " + " | ".join(d["내역사업명"].head(6)))
    open(f"{OUT}/axis_profiles.md", "w").write("\n".join(out)); print("\n".join(out))
else:
    cfg = json.load(open(args.map))
    for ax in AX:
        M = {int(k): v for k, v in cfg[ax].items()}; A[f"{ax}_type"] = A[f"{ax}_cp"].map(M); assert A[f"{ax}_type"].notna().all(), ax
    # 대상 축 보정규칙: 수혜대상 서술의 명시 어휘로 유형 세분(예: 보증·보험 이용기업), 프로그램 단위 최빈값으로 통일
    for ov in cfg.get("target_overlays", []):
        m = A["target_type"].str.startswith(ov["from"] + " ") & A["수혜대상"].fillna("").str.contains(ov["regex"])
        A.loc[m, "target_type"] = ov["type"]
    if cfg.get("target_overlays"):
        ks = pd.Series(key.values, index=A.index); A["target_type"] = ks.map(A.groupby(ks.values)["target_type"].agg(lambda x: x.value_counts().index[0])).values
    # ---- 수단 축: 지원형태 메타데이터 + 어휘 신호의 우선순위 규칙 (범주형 속성이므로 군집 대신 규칙으로 유형화)
    def instr(i):
        m = meta[i]; f = F.loc[i]; pur = str(A.loc[i, "대분류"])[:1]
        if "(융자)" in str(A.loc[i, "세부사업명"]) and "융자" not in m: m = m + ";융자"      # 세부사업명의 (융자) 표기를 메타 보완
        if "융자" in m and not (f["어휘_보증팩토링"] == 1 and pur == "D" and "직접" in m): return "I4 융자(정책자금 대출)"
        if f["어휘_보증팩토링"] == 1 and ("직접" in m or pur == "D"): return "I8 보증·보험(신용보강)"
        if f["어휘_바우처"] == 1: return "I9 바우처"
        if "직접" in m and f["어휘_장려금인건비"] == 1 and pur == "G": return "I5 장려금·수당 직접지급"
        if "출연" in m and re.search("보조|직접", m): return "I6 혼합(출연+보조+직접 등 복수 형태)"
        if "출연" in m and f["어휘_R&D과제"] == 1: return "I1 R&D 과제 출연(연구개발비)"
        if "출연" in m: return "I2 출연(기관 운영·인프라·위탁 서비스)"
        if "보조" in m: return "I3 보조금(사업비 보조·매칭)"
        if "직접" in m: return "I10 직접 수행(직접사업)"
        return "I0 지원형태 미기재"
    A["instrument_type"] = [instr(i) for i in A.index]
    key_s = pd.Series(key.values, index=A.index)
    mode = A.groupby(key_s.values)["instrument_type"].agg(lambda x: x.value_counts().index[0]); A["instrument_type"] = key_s.map(mode).values   # 프로그램 단위 최빈 유형
    A = A.rename(columns={"target_type": "대상유형", "content_type": "내용유형", "instrument_type": "수단유형"})
    cols = ["id", "year", "소관", "세부사업명", "내역사업명", "내역예산", "대분류", "중분류", "대상유형", "수단유형", "내용유형", "내용_출처", "수혜대상", "세부지원", "수단_text"]
    A[cols].to_csv(f"{OUT}/axes_assignments.csv", index=False, encoding="utf-8-sig")
    typed = A[~A["대분류"].str.startswith("유형화")]; d26 = typed[typed.year == 2026]
    def dist(col):
        t = pd.DataFrame({"건수('24~'26)": typed.groupby(col).size(), "2026 건수": d26.groupby(col).size(), "2026 예산(백만원)": d26.groupby(col).내역예산.sum().round(0)}).fillna(0)
        t["2026 예산 비중(%)"] = (t["2026 예산(백만원)"] / t["2026 예산(백만원)"].sum() * 100).round(1); return t.sort_index()
    for name, col in [("X1_target_dist", "대상유형"), ("X2_instrument_dist", "수단유형"), ("X3_content_dist", "내용유형")]: dist(col).to_csv(f"{OUT}/{name}.csv", encoding="utf-8-sig"); print(dist(col))
    for name, a, b in [("X4_purpose_x_target", "대분류", "대상유형"), ("X5_purpose_x_instrument", "대분류", "수단유형"), ("X6_purpose_x_content", "대분류", "내용유형"), ("X8_target_x_instrument", "대상유형", "수단유형")]:
        pd.crosstab(d26[a], d26[b]).to_csv(f"{OUT}/{name}_count2026.csv", encoding="utf-8-sig"); d26.pivot_table(index=a, columns=b, values="내역예산", aggfunc="sum").fillna(0).round(0).to_csv(f"{OUT}/{name}_budget2026.csv", encoding="utf-8-sig")
    prof = d26.groupby(["대분류", "대상유형", "수단유형", "내용유형"]).agg(건수=("id", "count"), 예산=("내역예산", "sum"), 예시=("내역사업명", lambda s: " / ".join(s.head(3)))).reset_index().sort_values("예산", ascending=False)
    prof.to_csv(f"{OUT}/X7_four_axis_profiles_2026.csv", index=False, encoding="utf-8-sig")
    # 안정성·검증
    val = {}
    for ax, (E, k) in AX.items():
        g = pd.DataFrame({"k": key, "c": A[f"{ax}_c"]}); g = g[g.groupby("k").k.transform("size") > 1]; val[f"{ax}_연도간일치율(군집)"] = float((g.groupby("k").c.nunique() == 1).mean())
        val[f"{ax}_프로그램단위_조정건수"] = int((A[f"{ax}_c"] != A[f"{ax}_cp"]).sum())
    g = pd.DataFrame({"k": key, "c": [instr(i) for i in A.index]}); g = g[g.groupby("k").k.transform("size") > 1]; val["instrument_연도간일치율(규칙)"] = float((g.groupby("k").c.nunique() == 1).mean())
    sub = A["지원분야소분류"].fillna("")
    val["대상검증_소분류 소상공인→소상공인 유형"] = float(A.loc[sub.str.contains("소상공인"), "대상유형"].str.contains("소상공인").mean())
    val["대상검증_소분류 창업벤처→창업 유형"] = float(A.loc[sub.str.contains("창업벤처"), "대상유형"].str.contains("창업").mean())
    val["수단검증_메타 융자→융자 유형"] = float(A.loc[meta.str.contains("융자"), "수단유형"].str.contains("융자").mean())
    val["내용_공고기반 비율"] = float((A["내용_출처"] == "공고").mean())
    json.dump(val, open(f"{OUT}/axes_validation.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(val, ensure_ascii=False, indent=1)); print(prof.head(12).to_string())
