# -*- coding: utf-8 -*-
"""A1. 여성기업 확인 기업의 규모·특성 (기준일 2026-01-28)
   비교군: 유효한 중소기업확인서 보유 기업 중 여성기업 확인 이력이 없는 기업(=여성기업 미확인, '남성기업'이 아님)"""
import duckdb, pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.float_format', lambda v: f"{v:,.1f}")
con = duckdb.connect("F:/여성기업정책/sims_work/w.duckdb", read_only=True)
def q(title, s):
    df = con.sql(s).df(); print(f"\n### {title}"); print(df.to_string(index=False)); return df

q("매칭률", """SELECT count(*) wfirms, sum((c.biz IS NOT NULL)::int) in_comp, sum(valid_now) valid_now,
   sum((valid_now=1 AND c.biz IS NOT NULL)::int) valid_in_comp FROM wfirm w LEFT JOIN comp c USING(biz)""")

# 분석 집단: W=여성기업 확인 유효, WX=과거 확인(현재 만료), N=중소기업확인서 유효 & 여성확인 이력 없음
con.execute("""CREATE OR REPLACE TEMP TABLE g AS
SELECT c.*, CASE WHEN w.valid_now=1 THEN '1.여성확인 유효' WHEN w.biz IS NOT NULL THEN '2.여성확인 만료' WHEN f.sme_now=1 THEN '3.중기확인 유효·여성확인 없음' ELSE '4.그 외 SIMS 기업' END grp,
       w.first_s, w.ncert, f.sme_now, f.venture_now, f.venture_ever, f.inno_now, f.main_now, f.direct_now, f.direct_ever, f.family_ever, f.social_ever, f.disabled_ever, f.bizconv_ever, f.naeil_ever, f.exportpromising_ever
FROM comp c LEFT JOIN wfirm w USING(biz) LEFT JOIN cflag f USING(biz)""")
q("집단 크기", "SELECT grp, count(*) n FROM g GROUP BY 1 ORDER BY 1")
q("법인 비중·상태·업력", """SELECT grp, count(*) n, 100*avg(corp) corp_pct, 100*avg((status='04')::int) closed_pct, 100*avg((status='01')::int) active_pct,
   median(date_diff('year', est, DATE '2026-01-28')) med_age, 100*avg((est>=DATE '2019-01-28')::int) under7_pct, 100*avg((est IS NULL)::int) noest
   FROM g WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("최신 중소기업확인서상 규모(유효 확인서 기준)", """WITH s AS (SELECT biz, arg_max(size, s) size FROM smesize WHERE s<=DATE '2026-01-28' AND e>=DATE '2026-01-28' GROUP BY biz)
   SELECT grp, count(*) n, 100*avg((size IS NOT NULL)::int) has_sme, 100*sum((size='소상공인')::int)/nullif(sum((size IS NOT NULL)::int),0) micro,
   100*sum((size LIKE '소기업%')::int)/nullif(sum((size IS NOT NULL)::int),0) small, 100*sum((size='중기업')::int)/nullif(sum((size IS NOT NULL)::int),0) medium
   FROM g LEFT JOIN s USING(biz) WHERE grp<'3' OR grp LIKE '3%' GROUP BY 1 ORDER BY 1""")
q("smesize 값", "SELECT size, count(*) n FROM smesize GROUP BY 1 ORDER BY n DESC LIMIT 10")
q("2024 매출·2025 피보험자(보유 기업 기준)", """SELECT grp, count(*) n, 100*avg((f.sales IS NOT NULL)::int) has_sales, median(f.sales)/1e8 med_sales_eok, quantile_cont(f.sales,0.25)/1e8 p25, quantile_cont(f.sales,0.75)/1e8 p75, quantile_cont(f.sales,0.9)/1e8 p90,
   100*avg((f.sales>=5e8)::int) FILTER (f.sales IS NOT NULL) over5eok, 100*avg((f.sales>=1e10)::int) FILTER (f.sales IS NOT NULL) over100eok,
   100*avg((e.emp IS NOT NULL)::int) has_emp, median(e.emp) med_emp, avg(e.emp) avg_emp, 100*avg((e.emp>=5)::int) FILTER (e.emp IS NOT NULL) emp5, 100*avg((e.emp>=10)::int) FILTER (e.emp IS NOT NULL) emp10, 100*avg((e.emp>=50)::int) FILTER (e.emp IS NOT NULL) emp50
   FROM g LEFT JOIN (SELECT * FROM fin WHERE y=2024) f USING(biz) LEFT JOIN (SELECT * FROM fin WHERE y=2025) e USING(biz) WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("총량(2024 매출, 2025 피보험자)", """SELECT grp, sum(f.sales)/1e12 sales_tril, sum(e.emp)/1e4 emp_man FROM g LEFT JOIN (SELECT * FROM fin WHERE y=2024) f USING(biz) LEFT JOIN (SELECT * FROM fin WHERE y=2025) e USING(biz) WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("업종 분포(%)", """PIVOT (SELECT grp, coalesce(ksec(ksic),'미상') sec, count(*) n FROM g WHERE grp<'4' GROUP BY ALL) ON grp USING sum(n) ORDER BY sec""")
q("지역 분포", """PIVOT (SELECT grp, substr(region,1,2) r, count(*) n FROM g WHERE grp<'4' GROUP BY ALL) ON grp USING sum(n) ORDER BY r""")
q("인증 보유(%)", """SELECT grp, count(*) n, 100*avg(coalesce(venture_now,0)) venture_now, 100*avg(coalesce(venture_ever,0)) venture_ever, 100*avg(coalesce(inno_now,0)) inno_now, 100*avg(coalesce(main_now,0)) main_now,
   100*avg(coalesce(direct_now,0)) direct_now, 100*avg(coalesce(direct_ever,0)) direct_ever, 100*avg(coalesce(family_ever,0)) fam_friendly, 100*avg(coalesce(social_ever,0)) social_ent, 100*avg(coalesce(naeil_ever,0)) naeil, 100*avg(coalesce(exportpromising_ever,0)) exp_promising
   FROM g WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("수출(2023 수출액>0, 매출 보유 기업 대비 %)", """SELECT grp, sum((f.sales IS NOT NULL)::int) n_sales, 100*avg((coalesce(f.exp_amt,0)>0)::int) FILTER (f.sales IS NOT NULL) exporter_pct, median(f.exp_amt) FILTER (f.exp_amt>0) med_exp_raw_unit, sum((f.exp_amt>0)::int) n_exporters
   FROM g LEFT JOIN (SELECT * FROM fin WHERE y=2023) f USING(biz) WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("R&D(2023 연구개발비>0 %)", """SELECT grp, 100*avg((coalesce(f.rnd,0)>0)::int) FILTER (f.sales IS NOT NULL) rnd_pct, sum((f.rnd>0)::int) n_rnd FROM g LEFT JOIN (SELECT * FROM fin WHERE y=2023) f USING(biz) WHERE grp<'4' GROUP BY 1 ORDER BY 1""")
q("유효 여성확인 기업의 최초 확인 시점", "SELECT year(first_s) y, count(*) n FROM g WHERE grp LIKE '1%' GROUP BY 1 ORDER BY 1")
q("유효 여성확인 기업 설립연도대", "SELECT (year(est)//5)*5 y5, count(*) n FROM g WHERE grp LIKE '1%' GROUP BY 1 ORDER BY 1")
q("확인 시점의 업력(최초 확인일-설립일, 년)", "SELECT year(first_s) y, count(*) n, median(date_diff('month', est, first_s))/12.0 med_age_at_cert, 100*avg((date_diff('month', est, first_s)<12)::int) within1y, 100*avg((date_diff('month', est, first_s)<36)::int) within3y FROM g WHERE first_s IS NOT NULL AND est IS NOT NULL AND year(first_s)>=2016 GROUP BY 1 ORDER BY 1")
