# -*- coding: utf-8 -*-
"""여성기업 기초분석용 DuckDB(w.duckdb) 구축
   입력: cert.parquet(5.인증), sup.parquet(7.집계), eval_dea/comp·fin·patent parquet
   기준일: 2026-01-28(인증 자료 최종 인증일)"""
import duckdb, os
W = "F:/여성기업정책/sims_work/"
E = "F:/SIMS/26_Feb/eval_dea/"
con = duckdb.connect(W + "w.duckdb")
con.execute("SET threads=10; SET memory_limit='20GB'")
REF = "DATE '2026-01-28'"

con.execute(f"""CREATE OR REPLACE TABLE cert AS
SELECT 인증제도명 nm, 인증기관명 org, 사업자등록번호 biz,
       try_strptime(인증시작일자,'%Y%m%d')::DATE s, try_strptime(인증만료일자,'%Y%m%d')::DATE e,
       try_strptime(인증취소일자,'%Y%m%d')::DATE x, 인증상태명 st, 인증구분명 gb, 인증부가정보명 info
FROM '{W}cert.parquet' WHERE 사업자등록번호 IS NOT NULL""")

# 여성기업 확인: 기업 단위
con.execute(f"""CREATE OR REPLACE TABLE wfirm AS
SELECT biz, min(s) first_s, max(least(e, coalesce(x,e))) last_e, count(*) ncert,
       max((s<={REF} AND least(e,coalesce(x,e))>={REF})::int) valid_now
FROM cert WHERE nm='여성기업 확인제도' GROUP BY biz""")

# 기타 인증 보유 플래그(이력 기준 ever, 현재 유효 now)
con.execute(f"""CREATE OR REPLACE TABLE cflag AS
SELECT biz,
  max((nm='벤처기업 확인제도')::int) venture_ever,
  max((nm='벤처기업 확인제도' AND e>={REF})::int) venture_now,
  max((nm='이노비즈제도')::int) inno_ever, max((nm='이노비즈제도' AND e>={REF})::int) inno_now,
  max((nm='메인비즈제도')::int) main_ever, max((nm='메인비즈제도' AND e>={REF})::int) main_now,
  max((nm='직접생산 확인제도')::int) direct_ever, max((nm='직접생산 확인제도' AND e>={REF})::int) direct_now,
  max((nm='장애인기업 확인')::int) disabled_ever,
  max((nm='가족친화기업 인증')::int) family_ever,
  max((nm='수출유망중소기업 지정')::int) exportpromising_ever,
  max((nm='사회적기업 인증')::int) social_ever,
  max((nm LIKE '%내일채움공제%')::int) naeil_ever,
  max((nm='사업전환계획 승인기업')::int) bizconv_ever,
  max((nm LIKE '중소기업(중기업%')::int) sme_ever,
  max((nm LIKE '중소기업(중기업%' AND s<={REF} AND e>={REF})::int) sme_now
FROM cert GROUP BY biz""")

# 중소기업확인서: 기업-연도별 규모(소상공인/소기업/중기업), 해당 연도 말 기준 유효한 확인서
con.execute(f"""CREATE OR REPLACE TABLE smesize AS
SELECT biz, s, e, info size FROM cert WHERE nm LIKE '중소기업(중기업%' AND info IS NOT NULL AND x IS NULL""")

con.execute(f"""CREATE OR REPLACE TABLE comp AS
SELECT 사업자등록번호 biz, 지역코드 region, try_strptime(설립일자,'%Y%m%d')::DATE est,
       try_strptime(휴업폐업일자,'%Y%m%d')::DATE closed, 표준산업분류항목코드 ksic,
       기업상태코드 status, 기업형태코드 form, 기업규모코드 scale,
       (substr(사업자등록번호,4,2) BETWEEN '81' AND '88')::int corp
FROM '{E}comp.parquet'""")
con.execute("""CREATE OR REPLACE MACRO ksec(k) AS CASE
 WHEN k IS NULL THEN NULL WHEN substr(k,1,2) BETWEEN '01' AND '03' THEN 'A농림어업' WHEN substr(k,1,2) BETWEEN '05' AND '08' THEN 'B광업'
 WHEN substr(k,1,2) BETWEEN '10' AND '34' THEN 'C제조업' WHEN substr(k,1,2)='35' THEN 'D전기가스' WHEN substr(k,1,2) BETWEEN '36' AND '39' THEN 'E수도환경'
 WHEN substr(k,1,2) BETWEEN '41' AND '42' THEN 'F건설업' WHEN substr(k,1,2) BETWEEN '45' AND '47' THEN 'G도소매' WHEN substr(k,1,2) BETWEEN '49' AND '52' THEN 'H운수창고'
 WHEN substr(k,1,2) BETWEEN '55' AND '56' THEN 'I숙박음식' WHEN substr(k,1,2) BETWEEN '58' AND '63' THEN 'J정보통신' WHEN substr(k,1,2) BETWEEN '64' AND '66' THEN 'K금융보험'
 WHEN substr(k,1,2)='68' THEN 'L부동산' WHEN substr(k,1,2) BETWEEN '70' AND '73' THEN 'M전문과학기술' WHEN substr(k,1,2) BETWEEN '74' AND '76' THEN 'N사업지원임대'
 WHEN substr(k,1,2)='84' THEN 'O공공행정' WHEN substr(k,1,2)='85' THEN 'P교육' WHEN substr(k,1,2) BETWEEN '86' AND '87' THEN 'Q보건복지'
 WHEN substr(k,1,2) BETWEEN '90' AND '91' THEN 'R예술스포츠' WHEN substr(k,1,2) BETWEEN '94' AND '96' THEN 'S기타개인서비스' ELSE 'Z기타' END""")

con.execute(f"""CREATE OR REPLACE TABLE fin AS
SELECT 사업자등록번호 biz, try_cast(결산년도 AS INT) y, try_cast(매출액 AS DOUBLE) sales, try_cast(수출액 AS DOUBLE) exp_amt,
       try_cast(영업이익금 AS DOUBLE) oi, try_cast(연구개발비용 AS DOUBLE) rnd, try_cast(피보험자수 AS DOUBLE) emp
FROM '{E}fin.parquet' WHERE try_cast(결산년도 AS INT)>=2015""")

if os.path.exists(W + "sup.parquet"):
    con.execute(f"""CREATE OR REPLACE TABLE sup AS
    SELECT 사업자등록번호 biz, 세부사업ID sid, 세부사업명 sname, 관리사업ID mid, 관리사업명 mname, 대분야 f1, 중분야 f2,
           try_strptime(지원일자,'%Y%m%d')::DATE d, try_cast(지원금액 AS DOUBLE) amt
    FROM '{W}sup.parquet' WHERE 사업자등록번호 IS NOT NULL""")
    print("sup", con.sql("SELECT count(*), count(DISTINCT biz), min(d), max(d) FROM sup").fetchall())
con.execute(f"CREATE OR REPLACE TABLE pat AS SELECT * FROM '{E}patent_firm_year.parquet'")
print(con.sql("DESCRIBE pat").df().to_string())
for t in ["cert", "wfirm", "cflag", "smesize", "comp", "fin"]:
    print(t, con.sql(f"SELECT count(*) FROM {t}").fetchone())
