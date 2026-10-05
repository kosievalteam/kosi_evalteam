# 중앙부처 내역사업 지원목적 유형화 (2024~2026)

중앙부처 중소기업 지원사업의 **내역사업** 단위 텍스트(사업목적·내용 + 기업마당 공고 지원내용)를 임베딩하고
군집분석으로 **지원목적 유형**을 도출하는 분석 파이프라인입니다.

## 자료
- 선행 작업: 열린재정(재정정보공개시스템)의 세부사업별 「예산 및 기금운용계획 사업설명자료」(hwpx)를 전수 수집(연 7,400~8,100개 세부사업)하고
  중소기업 지원사업(연 400~470개 세부사업)을 선별한 뒤 서술 항목·내역 구조를 파싱하여 내역사업 단위 DB로 구축. 기업마당 공고·정책디렉토리 속성을 연계(REPORT.md Ⅰ장)
- 원천: 정책평가팀 Supabase DB(`biz`, `biz_struct`, `gonggo`, `biz_sunset`, `biz_transfer` 테이블) — 이 중 중앙부처, 2024~2026년, 내역사업 2,189건 사용
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
python scripts/02b_embed_pretrained.py --backend st --model BAAI/bge-m3      # (선택) 사전학습 문장 임베딩 + 영역 방향 제거 → data/emb_bge-m3_fn.npy
python scripts/04b_compact_profile.py 24 fn   # 군집 프로파일(라벨링 근거)
python scripts/07_final_typology.py --map config/mapping_fn_k24_v3.json   # 최종 유형 배정·집계표·안정성 지표 (LSA 단독)
python scripts/08_charts.py            # 보고서 도표
```

## 사전학습 문장 임베딩으로 교체하기
`02b_embed_pretrained.py`는 bge-m3·multilingual-e5(sentence-transformers, 로컬 추론) 또는 OpenAI text-embedding-3(API)로
동일 문서를 임베딩하고, 지원산업·소관을 판별하는 선형 방향(LDA)을 제거한 `emb_<모델>_fn.npy`를 만듭니다.
```bash
python scripts/02b_embed_pretrained.py --backend st --model BAAI/bge-m3   # emb_bge-m3.npy, _fn(영역 제거), _hyb(영역 제거 + 기능가중 LSA 결합; 최종 사용)
python scripts/04b_compact_profile.py 24 bge-m3_hyb           # 군집 프로파일을 보고 해석 → config/mapping_bge-m3_hyb_k24_v3.json
python scripts/07_final_typology.py --emb bge-m3_hyb --k 24 --map config/mapping_bge-m3_hyb_k24_v3.json --out output_bge-m3
python scripts/08_charts.py --emb bge-m3_hyb --out output_bge-m3
python scripts/09_compare_embeddings.py --a fn --b bge-m3_hyb --out-b output_bge-m3   # LSA 단독 결과와 비교
python scripts/11_axis_typology.py profile --k_target 16   # 대상·내용 축 군집 프로파일 → config/axes_mapping.json 작성
python scripts/11_axis_typology.py final --k_target 16     # 대상·수단·내용 유형 확정, X1~X8 집계표
python scripts/12_axis_charts.py                           # 4축 도표(fig5, fig6)
python scripts/13_axis_detail.py                           # 축별 상세 집계(Y1~Y8, axes_stability.json): 하위군집·추이·소관별·대표사업·타당성
```
결합 임베딩(`_hyb`)을 쓰는 이유: 문장 임베딩 단독은 산업영역 의존(소관 NMI 0.35)이 크고 연도 간 일치율(0.71)이 낮으며, 기능가중 LSA와 결합하면 일치율 0.83, 기존 분류 정합성 0.41로 모든 지표가 개선됨.
군집 번호는 임베딩마다 달라지므로 매핑 파일은 새로 작성해야 합니다. 형식은 `config/mapping_bge-m3_hyb_k24_v3.json` 참조.
- `MID` 군집 번호 → 중분류명(첫 글자가 대분류 부호), `MAJ` 대분류 부호 → 명칭, `R3`/`R3_SOURCE` 경계 사례 수작업 조정, `RULES` 융자·보증 보정규칙의 목표 유형
- `RESIDUAL_PREFIX`(기본 Z) 로 시작하는 중분류는 '미분류'로 취급. `SECOND_PASS: true` 이면 차순위 유형 군집 중심까지의 거리가 그 군집 평균 반경 이내인 사업만 저신뢰(R4) 배정
- v1·v2 매핑은 개정 전 체계(v1: 기술개발·실증 분리 및 복합 유형, v2: 통합 후 미분류를 유형으로 집계). v3부터 유형 명칭을 목적 서술어 형식으로 통일하고 유형화 제외 사업을 집계에서 분리(T0)

실행 환경 요건 (Claude Code 클라우드 환경의 경우 환경 설정 → Network access에서 허용):
- sentence-transformers: `huggingface.co`(메타데이터)와 가중치 CDN `us.aws.cdn.hf.co`(2026년 10월 현재 리다이렉트 대상; 가능하면 `*.hf.co` 전체 허용). 모델 약 2.3GB, CPU 4코어 기준 2,189건 추론 약 15~30분. 스크립트가 `HF_HUB_DISABLE_XET=1`을 기본 설정하므로 `cas-server.xethub.hf.co`는 불필요
- OpenAI: `api.openai.com` + 환경변수 `OPENAI_API_KEY`


## 추출 SQL (biz)
```sql
select id, year, 소관, 세부사업명, 내역사업명, 내역예산, 세부예산, 지원분야대분류, 지원분야중분류, 지원분야소분류, 지원산업,
       세부지원, 수혜대상, 세부추진기관, 내역추진기관, 프로그램, 단위사업, 근거법령, 세부목적, 내역목적, 공고지원내용, 비고, 내역비고, 평가등급
from biz where gubun='중앙부처' and year between 2024 and 2026 order by id;
```

## 산출물
| 파일 | 내용 |
|---|---|
| `REPORT.md` | 개조식 분석 보고서 (본 결과: bge-m3 결합 임베딩, 비교: LSA 단독) |
| `output_bge-m3/` | **본 결과**: bge-m3 결합 임베딩 기반 집계표·도표·지표·LSA 비교표, 4축(대상·수단·내용) 집계표 X1~X8 |
| `output/T1_major_by_year.csv` | (LSA 단독) 대분류별 건수·예산(2024~2026) |
| `output/T2_mid_by_year.csv` | 중분류별 건수·예산 |
| `output/T3_somewon_x_major_2026.csv` | 소관 × 유형 (2026 예산) |
| `output/T4_taxonomy_x_major.csv` | 기존 지원분야중분류 × 유형 교차표 |
| `output/T5_fundingform_x_major.csv` | 지원형태(출연·보조·융자·직접) × 유형 |
| `output/T7_type_switch_cases.csv` | 연도 간 유형이 바뀐 내역사업 |
| `output/T8_top_programs_2026.csv` | 유형별 2026 예산 상위 사업 |
| `output/stability.json` | 군집 안정성·정합성 지표 |
| `output/cluster_profile_*.md` | 군집별 핵심어·대표사업(라벨링 근거) |
| `output/fig_*.png` | 도표 |
