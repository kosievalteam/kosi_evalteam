# 중앙부처 내역사업 지원목적 유형화 (2024~2026)

중앙부처 중소기업 지원사업의 **내역사업** 단위 텍스트(사업목적·내용 + 기업마당 공고 지원내용)를 임베딩하고
군집분석으로 **지원목적 유형**을 도출하는 분석 파이프라인입니다.

## 자료
- 원천: 정책평가팀 Supabase DB(`biz`, `gonggo` 테이블) — 중앙부처, 2024~2026년, 내역사업 2,189건
  (biz_info 웹앱 <https://kosievalteam.github.io/biz_info/> 과 동일한 자료)
- 자료 파일(`data/`)과 행 단위 결과(`output/*.csv`, `*.xlsx`)는 **git에 올리지 않습니다**(.gitignore). 집계표·지표·보고서만 커밋합니다.

## 실행 순서
```bash
pip install -r requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/ko_core_news_lg-3.8.0/ko_core_news_lg-3.8.0-py3-none-any.whl
python scripts/00_parse_mcp_dump.py <execute_sql 결과파일> data/biz_central_2024_2026.csv   # 또는 DB에서 직접 CSV 추출
python scripts/01_build_corpus.py      # 문서 구성 + 형태소(kiwipiepy) 토큰화
python scripts/02_embed.py             # TF-IDF→LSA / 단어벡터 / 결합 임베딩
python scripts/03_select_k.py          # 임베딩·k별 품질지표
python scripts/05_function_axis.py     # 지원목적(기능) 축 임베딩: 산업영역 어휘 가중 완화
python scripts/04b_compact_profile.py 24 fn   # 군집 프로파일(라벨링 근거)
python scripts/07_final_typology.py    # 최종 유형 배정·집계표·안정성 지표
python scripts/08_charts.py            # 보고서 도표
```

## 추출 SQL (biz)
```sql
select id, year, 소관, 세부사업명, 내역사업명, 내역예산, 세부예산, 지원분야대분류, 지원분야중분류, 지원분야소분류, 지원산업,
       세부지원, 수혜대상, 세부추진기관, 내역추진기관, 프로그램, 단위사업, 근거법령, 세부목적, 내역목적, 공고지원내용, 비고, 내역비고, 평가등급
from biz where gubun='중앙부처' and year between 2024 and 2026 order by id;
```

## 산출물
| 파일 | 내용 |
|---|---|
| `REPORT.md` | 개조식 분석 보고서 |
| `output/T1_major_by_year.csv` | 대분류별 건수·예산(2024~2026) |
| `output/T2_mid_by_year.csv` | 중분류별 건수·예산 |
| `output/T3_somewon_x_major_2026.csv` | 소관 × 유형 (2026 예산) |
| `output/T4_taxonomy_x_major.csv` | 기존 지원분야중분류 × 유형 교차표 |
| `output/T5_fundingform_x_major.csv` | 지원형태(출연·보조·융자·직접) × 유형 |
| `output/T7_type_switch_cases.csv` | 연도 간 유형이 바뀐 내역사업 |
| `output/T8_top_programs_2026.csv` | 유형별 2026 예산 상위 사업 |
| `output/stability.json` | 군집 안정성·정합성 지표 |
| `output/cluster_profile_*.md` | 군집별 핵심어·대표사업(라벨링 근거) |
| `output/fig_*.png` | 도표 |
