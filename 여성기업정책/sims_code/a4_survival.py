# -*- coding: utf-8 -*-
"""A4. 5년 생존율 (a3_growth.py의 4년 폐업률을 대체)
   코호트 1: 2020-12-31 기준 확인서 유효 기업 → 2025-12-31까지 연차별 생존율(카플란-마이어식 누적)
   코호트 2: 2020년 설립 신생기업 → 설립 후 5년 생존율(통계청 기업생멸행정통계 '5년 생존율'과 같은 정의)
   W = 여성기업 확인 유효, N = 중소기업확인서 유효 & 코호트 기준일 이전 여성기업 확인 이력 없음(미래 정보 미사용)
   폐업 = 기업상태 '04'(폐업) & 휴폐업일자 보유. 민감도: 휴폐업일자 보유(휴업 포함)
   std = N을 W의 업종(대분류)×법인×업력 구성으로 재가중(코호트 2는 업력이 같으므로 업종×법인)"""
import duckdb, pandas as pd
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 300); pd.set_option('display.float_format', lambda v: f"{v:,.1f}")
con = duckdb.connect("F:/여성기업정책/sims_work/w.duckdb", read_only=True)
con.execute("SET threads=10; SET memory_limit='20GB'")


def q(title, s):
    df = con.sql(s).df(); print(f"\n### {title}"); print(df.to_string(index=False)); return df


D0, D1 = "DATE '2020-12-31'", "DATE '2025-12-31'"
CLOSED = "(status='04' AND closed IS NOT NULL)"        # 폐업
CLOSED_ANY = "(closed IS NOT NULL)"                     # 휴업 포함(민감도)

# ---------- 코호트 1: 2020년 말 확인서 유효 기업 ----------
con.execute(f"""CREATE TEMP TABLE w20 AS SELECT DISTINCT biz FROM cert
  WHERE nm='여성기업 확인제도' AND s<={D0} AND least(e,coalesce(x,e))>={D0}""")
con.execute(f"""CREATE TEMP TABLE n20 AS SELECT DISTINCT s.biz FROM smesize s LEFT JOIN wfirm w USING(biz)
  WHERE s.s<={D0} AND s.e>={D0} AND (w.biz IS NULL OR w.first_s>{D0})""")   # 2020년 말 이전 여성 확인 이력 없음
con.execute(f"""CREATE TEMP TABLE c1 AS
SELECT c.biz, c.corp, ksec(c.ksic) sec, c.est, c.closed, c.status,
  CASE WHEN w.biz IS NOT NULL THEN 'W' WHEN n.biz IS NOT NULL THEN 'N' END grp,
  CASE WHEN c.est IS NULL THEN 'x' WHEN c.est>DATE '2017-12-31' THEN 'a.3년미만' WHEN c.est>DATE '2013-12-31' THEN 'b.3~7년'
       WHEN c.est>DATE '2005-12-31' THEN 'c.7~15년' ELSE 'd.15년이상' END agegrp
FROM comp c LEFT JOIN w20 w USING(biz) LEFT JOIN n20 n USING(biz)
WHERE (w.biz IS NOT NULL OR n.biz IS NOT NULL) AND (c.closed IS NULL OR c.closed>{D0}) AND (c.est IS NULL OR c.est<={D0})""")
con.execute("""CREATE TEMP TABLE c1w AS SELECT c1.*, CASE WHEN grp='W' THEN 1.0 ELSE nw/nullif(nn,0) END wgt FROM c1 JOIN
  (SELECT sec, corp, agegrp, sum((grp='W')::int)::DOUBLE nw, sum((grp='N')::int)::DOUBLE nn FROM c1 GROUP BY ALL) t
  ON c1.sec IS NOT DISTINCT FROM t.sec AND c1.corp=t.corp AND c1.agegrp=t.agegrp""")
q("코호트 1 크기", "SELECT grp, count(*) n, sum(wgt) wsum FROM c1w GROUP BY 1")


def surv_cols(closed_expr):
    return ", ".join([f"100*sum(wgt*(NOT ({closed_expr} AND closed<={D0}+INTERVAL {t} YEAR))::int)/sum(wgt) s{t}y" for t in range(1, 6)])


def three(title, closed_expr, src="c1w", where="TRUE", by=""):
    expr = surv_cols(closed_expr); raw = expr.replace("wgt*", "1.0*").replace("sum(wgt)", "count(*)")
    g = f"{by}, " if by else ""
    return q(title, f"""SELECT {g}'W' g, count(*) n, {expr} FROM {src} WHERE grp='W' AND {where} {'GROUP BY '+by if by else ''}
      UNION ALL SELECT {g}'N raw', count(*), {raw} FROM {src} WHERE grp='N' AND {where} {'GROUP BY '+by if by else ''}
      UNION ALL SELECT {g}'N std', count(*), {expr} FROM {src} WHERE grp='N' AND {where} {'GROUP BY '+by if by else ''}
      ORDER BY {'1,' if by else ''} 2 DESC""")


three("[코호트 1] 연차별 누적 생존율(%) 2020년 말 → 1~5년, 폐업 기준", CLOSED)
three("[코호트 1] 연차별 누적 생존율(%) 민감도: 휴업 포함", CLOSED_ANY)
three("[코호트 1] 5년 생존율: 업력별", CLOSED, by="agegrp")
q("[코호트 1] 5년 생존율: 업종별(W 1,000개 이상)", f"""SELECT sec, sum((grp='W')::int) w_n,
   100*avg((NOT ({CLOSED} AND closed<={D1}))::int) FILTER (grp='W') w_s5y, 100*avg((NOT ({CLOSED} AND closed<={D1}))::int) FILTER (grp='N') n_s5y
   FROM c1 GROUP BY 1 HAVING sum((grp='W')::int)>=1000 ORDER BY w_n DESC""")

# ---------- 코호트 2: 2020년 설립 신생기업의 설립 후 5년 생존율 ----------
# W: 설립 후 3년 내 여성기업 확인, N: 설립 후 3년 내 중소기업확인서 보유 & 2025년 말까지 여성기업 확인 이력 없음
con.execute(f"""CREATE TEMP TABLE c2 AS
SELECT c.biz, c.corp, ksec(c.ksic) sec, c.est, c.closed, c.status,
  CASE WHEN w.first_s IS NOT NULL AND w.first_s<=c.est+INTERVAL 3 YEAR THEN 'W'
       WHEN w.biz IS NULL AND s.biz IS NOT NULL THEN 'N' END grp
FROM comp c LEFT JOIN wfirm w USING(biz)
LEFT JOIN (SELECT DISTINCT s.biz FROM smesize s JOIN comp c USING(biz) WHERE s.s<=c.est+INTERVAL 3 YEAR) s USING(biz)
WHERE c.est BETWEEN DATE '2020-01-01' AND DATE '2020-12-31'""")
con.execute("DELETE FROM c2 WHERE grp IS NULL")
con.execute("""CREATE TEMP TABLE c2w AS SELECT c2.*, CASE WHEN grp='W' THEN 1.0 ELSE nw/nullif(nn,0) END wgt FROM c2 JOIN
  (SELECT sec, corp, sum((grp='W')::int)::DOUBLE nw, sum((grp='N')::int)::DOUBLE nn FROM c2 GROUP BY ALL) t
  ON c2.sec IS NOT DISTINCT FROM t.sec AND c2.corp=t.corp""")
q("코호트 2 크기(2020년 설립)", "SELECT grp, count(*) n, sum(wgt) wsum FROM c2w GROUP BY 1")


def surv_cols2(closed_expr):
    return ", ".join([f"100*sum(wgt*(NOT ({closed_expr} AND closed<=est+INTERVAL {t} YEAR))::int)/sum(wgt) s{t}y" for t in range(1, 6)])


def three2(title, closed_expr):
    expr = surv_cols2(closed_expr); raw = expr.replace("wgt*", "1.0*").replace("sum(wgt)", "count(*)")
    return q(title, f"""SELECT 'W' g, count(*) n, {expr} FROM c2w WHERE grp='W'
      UNION ALL SELECT 'N raw', count(*), {raw} FROM c2w WHERE grp='N'
      UNION ALL SELECT 'N std', count(*), {expr} FROM c2w WHERE grp='N'""")


three2("[코호트 2] 2020년 설립 기업의 설립 후 1~5년 생존율(%), 폐업 기준", CLOSED)
three2("[코호트 2] 민감도: 휴업 포함", CLOSED_ANY)
q("[코호트 2] 5년 생존율: 업종별(W 300개 이상)", f"""SELECT sec, sum((grp='W')::int) w_n,
   100*avg((NOT ({CLOSED} AND closed<=est+INTERVAL 5 YEAR))::int) FILTER (grp='W') w_s5y,
   100*avg((NOT ({CLOSED} AND closed<=est+INTERVAL 5 YEAR))::int) FILTER (grp='N') n_s5y
   FROM c2 GROUP BY 1 HAVING sum((grp='W')::int)>=300 ORDER BY w_n DESC""")
# 참고: 통계청 기업생멸행정통계 5년 생존율(여성 33.5% vs 남성 38.9%, 2023년 기준)은 전체 신생기업 기준이므로
#       코호트 2(확인서 보유 신생기업)는 생존 편의로 수준이 더 높게 나옴 → 격차(W-N)만 비교
