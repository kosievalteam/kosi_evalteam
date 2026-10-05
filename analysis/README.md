# 중앙부처 내역사업 지원목적 유형화 분석

biz_info(중소기업지원사업 검색시스템) Supabase DB의 `public.biz` 테이블(구분=중앙부처, 2023~2026년)을 텍스트 분석해
내역사업을 지원목적 기준 10개 대분류·30개 중분류로 유형화한 파이프라인과 결과물입니다.
보고서는 [REPORT.md](REPORT.md)를 참조하십시오.

## 파이프라인

| 단계 | 스크립트 | 입력 → 출력 |
|---|---|---|
| 0 | (Supabase SQL) | `public.biz` where gubun='중앙부처' → `data/biz_central_raw.parquet` |
| 1 | `scripts/01_build_corpus.py` | 원자료 → 사업별 문서·사업키 (`data/corpus.parquet`) |
| 2 | `scripts/02_embed_cluster.py [k]` | 형태소 분석 → 가중 TF-IDF → LSA → KMeans (`data/emb_lsa.npy`, `data/clusters.parquet`, `output/cluster_profile_k24.md`, `output/T0_k_selection.csv`) |
| 3 | `scripts/03_subcluster.py` | 1차 군집 내부 재분할 → 미세군집 55개 (`output/fine_cluster_profile.md`) |
| 4 | `scripts/04_assign_typology.py` | 미세군집 매핑 + 사업명 규칙 + 수작업 보정 + 연도 간 일관화 → `output/typology_assignments.csv`, `output/typology_scheme.csv` |
| 5 | `scripts/05_tables_figs.py` | 집계표 T1~T9, 도표 fig1~3, `output/typology_assignments.xlsx`, `output/stats.json` |

### 0단계 추출 SQL

```sql
select id, year, 소관, 회계명, 프로그램, 단위사업, 세부사업명, 내역사업명, 세부예산, 내역예산, 전년본예산, 전전년결산, 예산증감액,
       세부분야, 내역분야, 세부목적, 내역목적, 세부지원, 수혜대상, 공고지원내용, 지원분야대분류, 지원분야중분류, 지원분야소분류,
       지원산업, 근거법령, 세부추진기관, 내역추진기관, 성과평가, 평가등급, 비고, 내역비고, 예산서키
from biz where gubun='중앙부처' and year = {2023|2024|2025|2026} order by id;
```

연도별 결과(JSON 배열)를 합쳐 `data/biz_central_raw.parquet`로 저장합니다(숫자 컬럼은 numeric 변환).

## 실행

```bash
pip install pandas numpy scikit-learn kiwipiepy matplotlib openpyxl pyarrow koreanize-matplotlib scipy
cd analysis
python3 scripts/01_build_corpus.py
python3 scripts/02_embed_cluster.py 24
python3 scripts/03_subcluster.py
python3 scripts/04_assign_typology.py
python3 scripts/05_tables_figs.py
```

- `data/`와 행 단위 배정 결과(`output/typology_assignments.*`)는 원자료를 포함하므로 git에서 제외합니다.
- 군집은 `random_state=0`으로 고정되어 있으나 라이브러리 버전에 따라 미세군집 구성이 달라질 수 있습니다. 이 경우 `04_assign_typology.py`의 `FINE_MAP`을 `output/fine_cluster_profile.md`를 보고 재지정해야 합니다.
- 사전학습 문장 임베딩을 쓰려면 `02_embed_cluster.py`의 LSA 구간을 교체하면 됩니다(네트워크 제한으로 본 분석에서는 미적용).
