# -*- coding: utf-8 -*-
"""A3 v2. 성장·규모 전환·생존 (2021년 말 기준 코호트) — 정의 보정판
   보정 1) 폐업 = 기업상태 '04'(폐업) & 휴폐업일자 보유 (v1은 휴업 포함). 민감도: 휴업 포함
   보정 2) N21 = 2021-12-31 중소기업확인서 유효 & 2021-12-31 이전 여성기업 확인 이력 없음 (v1은 전 기간 이력 없음 → 미래 정보 사용)
   보정 3) 코호트 대칭 민감도: W21도 2021-12-31 중소기업확인서(size21) 보유 기업으로 한정한 결과 병행
   보정 4) 하위집단(수출·규모 전환·매출·고용) 분석 시 해당 하위집단 내부에서 업종×법인×업력 가중치 재산출
   기준일 2025-12-31"""
import duckdb, pandas as pd
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 300); pd.set_option('display.float_format', lambda v: f"{v:,.1f}")
con = duckdb.connect("F:/여성기업정책/sims_work/w.duckdb", read_only=True)
con.execute("SET threads=10; SET memory_limit='20GB'")


def q(title, s):
    df = con.sql(s).df(); print(f"\n### {title}"); print(df.to_string(index=False)); return df


D0, D1 = "DATE '2021-12-31'", "DATE '2025-12-31'"
CLOSED = f"(status='04' AND closed IS NOT NULL AND closed<={D1})"   # 폐업(보정 1)
CLOSED_ANY = f"(closed IS NOT NULL AND closed<={D1})"               # 휴업 포함(민감도, v1 정의)

con.execute(f"""CREATE TEMP TABLE w21 AS SELECT DISTINCT biz FROM cert WHERE nm='여성기업 확인제도' AND s<={D0} AND least(e,coalesce(x,e))>={D0}""")
con.execute(f"""CREATE TEMP TABLE sz AS SELECT biz,
   arg_max(size, s) FILTER (s<={D0} AND e>={D0}) size21, arg_max(size, s) FILTER (s<={D1} AND e>={D1}) size25 FROM smesize GROUP BY biz""")
# 보정 2: N21은 2021년 말 이전 여성 확인 이력이 없는 기업 (이후 확인받은 기업 포함)
con.execute(f"""CREATE TEMP TABLE c AS
SELECT c.biz, c.corp, ksec(c.ksic) sec, c.est, c.closed, c.status,
  CASE WHEN a.biz IS NOT NULL THEN 'W21' WHEN (w.biz IS NULL OR w.first_s>{D0}) AND sz.size21 IS NOT NULL THEN 'N21' END grp,
  CASE WHEN c.est IS NULL THEN 'x' WHEN c.est>DATE '2018-12-31' THEN 'a.3년미만' WHEN c.est>DATE '2014-12-31' THEN 'b.3~7년' WHEN c.est>DATE '2006-12-31' THEN 'c.7~15년' ELSE 'd.15년이상' END agegrp,
  sz.size21, sz.size25
FROM comp c LEFT JOIN w21 a USING(biz) LEFT JOIN wfirm w USING(biz) LEFT JOIN sz USING(biz)
WHERE (a.biz IS NOT NULL OR ((w.biz IS NULL OR w.first_s>{D0}) AND sz.size21 IS NOT NULL))
  AND (c.closed IS NULL OR c.closed>{D0}) AND (c.est IS NULL OR c.est<={D0})""")


def reweight(src, dst, where="TRUE"):
    """보정 4: 지정 하위집단(where) 내부에서 N21을 W21의 업종×법인×업력 구성으로 재가중"""
    con.execute(f"DROP TABLE IF EXISTS {dst}")
    con.execute(f"""CREATE TEMP TABLE {dst} AS SELECT s.*, CASE WHEN grp='W21' THEN 1.0 ELSE nw/nullif(nn,0) END wgt
      FROM (SELECT * EXCLUDE(wgt) FROM {src} WHERE {where}) s JOIN
      (SELECT sec, corp, agegrp, sum((grp='W21')::int)::DOUBLE nw, sum((grp='N21')::int)::DOUBLE nn FROM {src} WHERE {where} GROUP BY ALL) t
      ON s.sec IS NOT DISTINCT FROM t.sec AND s.corp=t.corp AND s.agegrp=t.agegrp""")


con.execute("CREATE TEMP TABLE c0 AS SELECT *, NULL::DOUBLE wgt FROM c")
reweight("c0", "cw")
q("코호트 크기", "SELECT grp, count(*) n, sum(wgt) wsum, 100*avg((size21 IS NOT NULL)::int) has_size21 FROM cw GROUP BY 1")
q("보정 2 효과: 2022년 이후 처음 여성 확인을 받은 N21 기업 수", f"SELECT count(*) n FROM c JOIN wfirm USING(biz) WHERE grp='N21' AND first_s>{D0}")


def three(title, expr, src="cw", where="TRUE"):
    raw = expr.replace("wgt*", "1.0*").replace("sum(wgt)", "count(*)")
    return q(title, f"""SELECT 'W21' g, count(*) n, {expr} FROM {src} WHERE grp='W21' AND {where}
      UNION ALL SELECT 'N21 raw', count(*), {raw} FROM {src} WHERE grp='N21' AND {where}
      UNION ALL SELECT 'N21 std', count(*), {expr} FROM {src} WHERE grp='N21' AND {where}""")


# ---------- 생존: 2022-01-01 ~ 2025-12-31 ----------
three("[주제1·5] 2022~2025 폐업률(%) — 폐업 기준(보정 1)", f"100*sum(wgt*{CLOSED}::int)/sum(wgt) closed_4y")
three("[주제1·5] 2022~2025 폐업률(%) — 민감도: 휴업 포함(v1 정의)", f"100*sum(wgt*{CLOSED_ANY}::int)/sum(wgt) closed_4y_any")
q("기업상태 분포(휴폐업일자 보유 기업)", "SELECT grp, status, count(*) n FROM cw WHERE closed IS NOT NULL GROUP BY ALL ORDER BY 1,2")
# 보정 3: 코호트 대칭 — W21도 size21 보유로 한정
reweight("c0", "cw_sym", "size21 IS NOT NULL")
q("코호트 크기(대칭: 양 집단 모두 2021년 말 중기확인서 보유)", "SELECT grp, count(*) n, sum(wgt) wsum FROM cw_sym GROUP BY 1")
three("[보정 3] 대칭 코호트 폐업률(%)", f"100*sum(wgt*{CLOSED}::int)/sum(wgt) closed_4y", src="cw_sym")
q("폐업률: 업력별", f"SELECT agegrp, grp, count(*) n, 100*avg({CLOSED}::int) closed_4y FROM cw GROUP BY ALL ORDER BY 1,2")
q("폐업률: 2021 규모별", f"SELECT size21, grp, count(*) n, 100*avg({CLOSED}::int) closed_4y FROM cw WHERE size21 IS NOT NULL GROUP BY ALL ORDER BY 1,2")
q("폐업률: 업종별(W21 1,000개 이상)", f"""SELECT sec, sum((grp='W21')::int) w_n, 100*avg({CLOSED}::int) FILTER (grp='W21') w_closed, 100*avg({CLOSED}::int) FILTER (grp='N21') n_closed
   FROM cw GROUP BY 1 HAVING sum((grp='W21')::int)>=1000 ORDER BY w_n DESC""")

# ---------- 규모 전환: 2021말 → 2025말 (양 시점 확인서 보유) ----------
q("[주제1·8] 규모 전환 2021말→2025말 (양 시점 중기확인서 보유 기업, 행 %)", """SELECT grp, size21, count(*) n, 100*avg((size25='소상공인')::int) to_micro, 100*avg((size25='소기업')::int) to_small, 100*avg((size25='중기업')::int) to_medium
   FROM cw WHERE size21 IS NOT NULL AND size25 IS NOT NULL GROUP BY ALL ORDER BY 2,1""")
reweight("c0", "cw_up1", "size21='소상공인' AND size25 IS NOT NULL")
three("소상공인(2021) → 소기업 이상(2025) 전환율(%) — 하위집단 재가중(보정 4)", "100*sum(wgt*(size25 IN ('소기업','중기업'))::int)/sum(wgt) upgrade", src="cw_up1")
reweight("c0", "cw_up2", "size21='소기업' AND size25 IS NOT NULL")
three("소기업(2021) → 중기업(2025) 전환율(%) — 하위집단 재가중(보정 4)", "100*sum(wgt*(size25='중기업')::int)/sum(wgt) upgrade", src="cw_up2")

# ---------- 매출·고용 성장 ----------
con.execute("""CREATE TEMP TABLE gr0 AS SELECT c0.*, a.sales s21, b.sales s24, a.emp e21, e.emp e25
  FROM c0 LEFT JOIN (SELECT * FROM fin WHERE y=2021) a USING(biz) LEFT JOIN (SELECT * FROM fin WHERE y=2024) b USING(biz) LEFT JOIN (SELECT * FROM fin WHERE y=2025) e USING(biz)""")
reweight("gr0", "gr_s", "s21>0 AND s24>0")
q("[주제1] 매출 2021→2024 (양 시점 매출>0)", """SELECT grp, count(*) n, median(s21)/1e8 med21_eok, median(s24)/1e8 med24_eok, 100*(median(s24/s21)-1) med_growth_pct,
   100*avg((s24/s21>=1.728)::int) high_growth, 100*avg((s24<s21)::int) decline, 100*avg((s24/s21<0.7)::int) big_decline FROM gr_s GROUP BY 1""")
three("고성장(3년 매출 +72.8% 이상=연 20%) 비율 — 하위집단 재가중(보정 4)", "100*sum(wgt*(s24/s21>=1.728)::int)/sum(wgt) high_growth, 100*sum(wgt*(s24<s21)::int)/sum(wgt) decline", src="gr_s")
q("매출 성장: 2021 매출 구간별", """SELECT CASE WHEN s21<1e8 THEN '1.1억 미만' WHEN s21<5e8 THEN '2.1~5억' WHEN s21<3e9 THEN '3.5~30억' WHEN s21<1.2e10 THEN '4.30~120억' ELSE '5.120억 이상' END band, grp, count(*) n,
   100*(median(s24/s21)-1) med_growth_pct, 100*avg((s24/s21>=1.728)::int) high_growth, 100*avg((s24<s21)::int) decline FROM gr_s GROUP BY ALL ORDER BY 1,2""")
reweight("gr0", "gr_e", "e21 IS NOT NULL AND e25 IS NOT NULL")
q("[주제8] 고용 2021→2025 (양 시점 피보험자 자료 보유)", """SELECT grp, count(*) n, avg(e21) avg21, avg(e25) avg25, 100*avg((e25>e21)::int) up, 100*avg((e25<e21)::int) down,
   100*avg((e25>=1)::int) FILTER (e21=0) zero_to_hire, sum((e21=0)::int) n_zero21, 100*avg((e25>=5)::int) FILTER (e21 BETWEEN 1 AND 4) small_to_5plus, sum((e21 BETWEEN 1 AND 4)::int) n_1to4
   FROM gr_e GROUP BY 1""")
reweight("gr0", "gr_e14", "e21 BETWEEN 1 AND 4 AND e25 IS NOT NULL")
three("피보험자 1~4명(2021) → 5명 이상(2025) 전환율 — 하위집단 재가중(보정 4)", "100*sum(wgt*(e25>=5)::int)/sum(wgt) to5plus, 100*sum(wgt*(e25>=10)::int)/sum(wgt) to10plus", src="gr_e14")
q("고용 분포(2021, 자료 보유 기업)", "SELECT grp, count(*) n, 100*avg((e21=0)::int) z, 100*avg((e21 BETWEEN 1 AND 4)::int) e1_4, 100*avg((e21 BETWEEN 5 AND 9)::int) e5_9, 100*avg((e21 BETWEEN 10 AND 49)::int) e10_49, 100*avg((e21>=50)::int) e50 FROM gr_e GROUP BY 1")

# ---------- 수출 (fin에 export 열이 있는 경우만) ----------
cols = [r[0] for r in con.sql("DESCRIBE fin").fetchall()]
if "exp_amt" in cols:
    con.execute("""CREATE TEMP TABLE gx0 AS SELECT c0.*, a.exp_amt x21, b.exp_amt x24 FROM c0
      LEFT JOIN (SELECT * FROM fin WHERE y=2021) a USING(biz) LEFT JOIN (SELECT * FROM fin WHERE y=2024) b USING(biz)""")
    reweight("gx0", "gx", "x21 IS NOT NULL OR x24 IS NOT NULL")
    three("[주제6] 수출 기업 비율(2021, 2024) — 하위집단 재가중(보정 4)", "100*sum(wgt*(x21>0)::int)/sum(wgt) exp21, 100*sum(wgt*(x24>0)::int)/sum(wgt) exp24", src="gx")
else:
    print("\n### [주제6] 수출: fin 테이블에 exp_amt 열 없음 → 생략 (열 목록: " + ", ".join(cols) + ")")

# ---------- 여성기업 확인 유지 여부와 성과 ----------
q("W21의 2025말 확인 유지 여부별 성과", f"""WITH k AS (SELECT DISTINCT biz FROM cert WHERE nm='여성기업 확인제도' AND s<={D1} AND least(e,coalesce(x,e))>={D1})
   SELECT (k.biz IS NOT NULL) kept, count(*) n, 100*avg({CLOSED}::int) closed, 100*(median(s24/s21) FILTER (s21>0 AND s24>0)-1) med_growth, median(s21)/1e8 med_s21
   FROM gr0 LEFT JOIN k USING(biz) WHERE grp='W21' GROUP BY 1""")
q("여성확인 이력 기업 폐업 연도(기업상태 '04')", "SELECT year(c.closed) y, count(*) n FROM wfirm w JOIN comp c USING(biz) WHERE c.closed IS NOT NULL AND c.status='04' AND year(c.closed)>=2015 GROUP BY 1 ORDER BY 1")
