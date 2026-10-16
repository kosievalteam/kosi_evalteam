# -*- coding: utf-8 -*-
"""A2. 연구주제별 SIMS 기초분석
   W = 여성기업 확인 유효 기업, N = 중소기업확인서 유효 & 여성기업 확인 이력 없음(남성기업이 아니라 '미확인' 기업)
   표준화(std): N을 W의 업종(대분류)×법인여부×설립시기 분포로 재가중한 값"""
import duckdb, pandas as pd
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 300); pd.set_option('display.max_colwidth', 44); pd.set_option('display.float_format', lambda v: f"{v:,.1f}")
con = duckdb.connect("F:/여성기업정책/sims_work/w.duckdb", read_only=True)
con.execute("SET threads=10; SET memory_limit='20GB'")
def q(title, s):
    df = con.sql(s).df(); print(f"\n### {title}"); print(df.to_string(index=False)); return df
REF = "DATE '2026-01-28'"

# ---------- 현재 시점 집단 ----------
con.execute(f"""CREATE TEMP TABLE g AS
SELECT c.biz, c.corp, c.est, c.closed, c.status, ksec(c.ksic) sec, substr(c.ksic,1,2) k2,
  CASE WHEN w.valid_now=1 THEN 'W' WHEN w.biz IS NULL AND f.sme_now=1 THEN 'N' END grp,
  CASE WHEN c.est IS NULL THEN 'x' WHEN c.est>=DATE '2023-01-28' THEN 'a.3년미만' WHEN c.est>=DATE '2019-01-28' THEN 'b.3~7년' WHEN c.est>=DATE '2011-01-28' THEN 'c.7~15년' ELSE 'd.15년이상' END agegrp,
  coalesce(f.venture_now,0) venture_now, coalesce(f.inno_now,0) inno_now
FROM comp c LEFT JOIN wfirm w USING(biz) LEFT JOIN cflag f USING(biz)
WHERE w.valid_now=1 OR (w.biz IS NULL AND f.sme_now=1)""")
con.execute("""CREATE TEMP TABLE wt AS
SELECT sec, corp, agegrp, sum((grp='W')::int)::DOUBLE nw, sum((grp='N')::int)::DOUBLE nn FROM g GROUP BY ALL""")
con.execute("""CREATE TEMP TABLE gw AS SELECT g.*, CASE WHEN grp='W' THEN 1.0 ELSE nw/nullif(nn,0) END wgt FROM g JOIN wt ON g.sec IS NOT DISTINCT FROM wt.sec AND g.corp=wt.corp AND g.agegrp=wt.agegrp""")
q("집단·가중 확인", "SELECT grp, count(*) n, sum(wgt) wsum FROM gw GROUP BY 1")
q("W/N 업력 구간·법인", "SELECT grp, agegrp, n, 100.0*n/sum(n) OVER (PARTITION BY grp) pct FROM (SELECT grp, agegrp, count(*) n FROM g GROUP BY 1,2) ORDER BY 1,2")

# ---------- [주제1·13·9·10] 지원 수혜 (2023~2025) ----------
con.execute("""CREATE TEMP TABLE s3 AS SELECT biz, f1, f2, sid, sname, mname, d, amt FROM sup WHERE d BETWEEN DATE '2023-01-01' AND DATE '2025-12-31'""")
con.execute("""CREATE TEMP TABLE sf AS SELECT biz,
  1 any_sup, count(*) n_sup, count(DISTINCT sid) n_prog,
  max((f1='금융' AND f2='보증')::int) guar, max((f1='금융' AND f2='융자')::int) loan, max((f1='금융' AND f2='펀드/투자')::int) invest, max((f1='금융' AND f2 LIKE '보험%')::int) expins,
  max((f1='기술')::int) tech, max((f1='기술' AND f2 IN ('혼합(단독+공동)','단독기술개발','공동기술개발'))::int) rnd,
  max((f1='수출')::int) exp_sup, max((f1='창업')::int) startup, max((f1='내수')::int) domestic, max((f1='인력')::int) hr, max((f1='인력' AND f2='고용유지')::int) empkeep, max((f1='경영')::int) mgmt,
  max((f2='재기지원')::int) rebirth, max((sname LIKE '%여성%' OR mname LIKE '%여성%')::int) wprog,
  sum(amt) FILTER (f1='금융' AND f2='보증') guar_amt, sum(amt) FILTER (f1='금융' AND f2='융자') loan_amt, sum(amt) FILTER (f1='기술') tech_amt
  FROM s3 GROUP BY biz""")
cols = ["any_sup","guar","loan","invest","expins","tech","rnd","exp_sup","startup","domestic","hr","empkeep","mgmt","rebirth","wprog"]
sel = ", ".join([f"100*sum(wgt*coalesce({c},0))/sum(wgt) {c}" for c in cols])
q("2023~25 지원 수혜율(%) : W, N(원자료), N(std=W 구성으로 표준화)", f"""
SELECT 'W' g, count(*) n, {sel} FROM gw LEFT JOIN sf USING(biz) WHERE grp='W'
UNION ALL SELECT 'N raw', count(*), {", ".join([f"100*avg(coalesce({c},0)) {c}" for c in cols])} FROM gw LEFT JOIN sf USING(biz) WHERE grp='N'
UNION ALL SELECT 'N std', count(*), {sel} FROM gw LEFT JOIN sf USING(biz) WHERE grp='N'""")
q("수혜기업 1개사당 금액(억원, 중앙값) 2023~25", """SELECT grp, median(guar_amt)/1e8 guar_med, avg(guar_amt)/1e8 guar_avg, median(loan_amt)/1e8 loan_med, avg(loan_amt)/1e8 loan_avg, median(tech_amt)/1e8 tech_med, avg(tech_amt)/1e8 tech_avg, median(n_prog) nprog_med
   FROM gw JOIN sf USING(biz) GROUP BY 1 ORDER BY 1""")
q("W가 가장 많이 받은 세부사업 Top 25 (2023~25, 수혜 기업 수)", """SELECT s.sname, s.f1, any_value(s.f2) f2, count(DISTINCT s.biz) w_firms, round(100.0*count(DISTINCT s.biz)/(SELECT count(*) FROM g WHERE grp='W'),1) pct_of_w
   FROM s3 s JOIN g USING(biz) WHERE grp='W' GROUP BY 1,2 ORDER BY w_firms DESC LIMIT 25""")
q("여성 명칭 사업(세부·관리사업명에 '여성') 연도별", """SELECT year(d) y, count(DISTINCT sid) n_sid, count(DISTINCT mname) n_mgmt, count(*) n, count(DISTINCT biz) firms, sum(amt)/1e8 eok,
   100.0*count(DISTINCT CASE WHEN w.biz IS NOT NULL THEN s.biz END)/count(DISTINCT s.biz) pct_ever_wcert
   FROM sup s LEFT JOIN wfirm w USING(biz) WHERE (sname LIKE '%여성%' OR mname LIKE '%여성%') AND year(d)>=2015 GROUP BY 1 ORDER BY 1""")
q("전체 지원에서 W(현재 유효)가 차지하는 비중 2023~25, 분야별", """SELECT f1, count(DISTINCT s.biz) firms_all, count(DISTINCT CASE WHEN g.grp='W' THEN s.biz END) firms_w, 100.0*count(DISTINCT CASE WHEN g.grp='W' THEN s.biz END)/count(DISTINCT s.biz) w_firm_share,
   sum(s.amt)/1e12 amt_tril, 100*sum(CASE WHEN g.grp='W' THEN s.amt END)/sum(s.amt) w_amt_share FROM s3 s LEFT JOIN g USING(biz) GROUP BY 1 ORDER BY firms_all DESC""")

# ---------- [주제3] 기술기반·신생 ----------
q("기술기반 업종(제조C·정보통신J·전문과학기술M) & 7년 미만", """SELECT grp, count(*) n, 100*avg((sec IN ('C제조업','J정보통신','M전문과학기술'))::int) tech_sec, 100*avg((sec='J정보통신')::int) ict, 100*avg((sec='M전문과학기술')::int) prof,
   100*avg((agegrp IN ('a.3년미만','b.3~7년'))::int) young, 100*avg((agegrp IN ('a.3년미만','b.3~7년') AND sec IN ('C제조업','J정보통신','M전문과학기술'))::int) young_tech, 100*avg(venture_now) venture, 100*avg(inno_now) inno FROM g GROUP BY 1""")
q("벤처확인 보유율: 업력×집단", "SELECT agegrp, grp, count(*) n, 100*avg(venture_now) venture FROM g GROUP BY ALL ORDER BY 1,2")
q("특허(출원·등록) 보유율", """WITH p AS (SELECT * FROM 'F:/SIMS/26_Feb/eval_dea/patent_firm_year.parquet') SELECT * FROM p LIMIT 3""")

# ---------- [주제10] 수출 ----------
q("수출기업 비중(2023 수출액>0 / 2023 매출 보유)", """SELECT 'W' g, sum(wgt) n, 100*sum(wgt*(coalesce(f.exp_amt,0)>0)::int)/sum(wgt) exporter FROM gw JOIN (SELECT * FROM fin WHERE y=2023 AND sales IS NOT NULL) f USING(biz) WHERE grp='W'
 UNION ALL SELECT 'N raw', count(*), 100*avg((coalesce(f.exp_amt,0)>0)::int) FROM gw JOIN (SELECT * FROM fin WHERE y=2023 AND sales IS NOT NULL) f USING(biz) WHERE grp='N'
 UNION ALL SELECT 'N std', sum(wgt), 100*sum(wgt*(coalesce(f.exp_amt,0)>0)::int)/sum(wgt) FROM gw JOIN (SELECT * FROM fin WHERE y=2023 AND sales IS NOT NULL) f USING(biz) WHERE grp='N'""")
q("수출기업 비중: 업종별(2023)", """SELECT sec, sum((grp='W')::int) w_n, 100*avg((coalesce(f.exp_amt,0)>0)::int) FILTER (grp='W') w_exporter, sum((grp='N')::int) n_n, 100*avg((coalesce(f.exp_amt,0)>0)::int) FILTER (grp='N') n_exporter,
   median(f.exp_amt) FILTER (grp='W' AND f.exp_amt>0) w_med_exp, median(f.exp_amt) FILTER (grp='N' AND f.exp_amt>0) n_med_exp
   FROM g JOIN (SELECT * FROM fin WHERE y=2023 AND sales IS NOT NULL) f USING(biz) GROUP BY 1 HAVING sum((grp='W')::int)>=1000 ORDER BY w_n DESC""")
q("수출기업 중 수출지원 수혜율(2023~25)", """SELECT grp, count(*) exporters, 100*avg(coalesce(exp_sup,0)) exp_sup, 100*avg(coalesce(expins,0)) expins FROM g JOIN (SELECT * FROM fin WHERE y=2023 AND exp_amt>0) f USING(biz) LEFT JOIN sf USING(biz) GROUP BY 1""")
