"""중앙부처 내역사업(2024~2026) 문서 구성 + 형태소 토큰화.
입력: data/biz_central_2024_2026.csv   출력: data/corpus.parquet (문서·토큰)
문서 = 내역사업명 + 내역목적(없으면 세부목적의 해당 내역 구간 → 없으면 세부목적) + 수혜대상 + 공고지원내용
"""
import re, pandas as pd, numpy as np
from kiwipiepy import Kiwi

SRC = "data/biz_central_2024_2026.csv"
b = pd.read_csv(SRC)

def clean_name(s):
    s = str(s)
    s = re.sub(r"\((R&D|특별|일반|정보화|ODA|융자|출연|보조)\)", " ", s)
    s = re.sub(r"\([^)]{1,6}\)$", "", s)          # 지역 꼬리표 (세종)(제주) 등
    return re.sub(r"\s+", " ", s).strip()

def section_from_sebu(sebu, nae):
    """세부목적 안의 '(내역사업명) …' 구간을 찾아 반환. 없으면 None."""
    if not isinstance(sebu, str) or not isinstance(nae, str): return None
    key = re.sub(r"[\s·ㆍ\-_()]", "", clean_name(nae))[:8]
    if len(key) < 2: return None
    parts = re.split(r"(?=\([^()]{2,40}\))", sebu)
    for p in parts:
        m = re.match(r"\(([^()]{2,40})\)", p)
        if m and re.sub(r"[\s·ㆍ\-_]", "", m.group(1)).startswith(key[:4]):
            return p.strip()
    return None

def norm(t, maxlen=None):
    if not isinstance(t, str): return ""
    t = re.sub(r"[\r\n\t]+", " ", t)
    t = re.sub(r"[□■○●◎◇◆▶▷※☞•▪・]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:maxlen] if maxlen else t

rows = []
for r in b.itertuples(index=False):
    nae_name = clean_name(r.내역사업명)
    purpose_src = "내역목적"
    purpose = r.내역목적 if isinstance(r.내역목적, str) and r.내역목적.strip() else None
    if purpose is None:
        sec = section_from_sebu(r.세부목적, r.내역사업명)
        if sec: purpose, purpose_src = sec, "세부목적(구간추출)"
        elif isinstance(r.세부목적, str): purpose, purpose_src = r.세부목적, "세부목적(전체)"
        else: purpose, purpose_src = "", "없음"
    doc = " . ".join(x for x in [nae_name, norm(purpose, 800), norm(r.수혜대상, 200), norm(r.공고지원내용, 700)] if x)
    rows.append(dict(id=r.id, year=r.year, 소관=r.소관, 세부사업명=r.세부사업명, 내역사업명=r.내역사업명,
                     내역예산=pd.to_numeric(r.내역예산, errors="coerce"), 지원분야중분류=r.지원분야중분류, 지원분야소분류=r.지원분야소분류,
                     세부지원=r.세부지원, 목적출처=purpose_src, has_gonggo=isinstance(r.공고지원내용, str), doc=doc))
df = pd.DataFrame(rows)
print(df["목적출처"].value_counts().to_string()); print("has_gonggo", df.has_gonggo.mean().round(3))
print(df.doc.str.len().describe().round(0).to_string())

# ---- 형태소 토큰화 (명사·외국어·어근 중심) ----
kiwi = Kiwi(num_workers=4)
USER_WORDS = """소상공인 중소기업 중견기업 벤처기업 스타트업 예비창업자 초기창업 창업기업 사업화 기술사업화 실증 기술개발 소부장 뿌리산업 탄소중립 스마트공장 스마트팜 바우처 융자 보증 컨설팅
해외진출 수출바우처 전시회 상담회 판로개척 시제품 인건비 고용유지 장려금 직업훈련 근로자 사회적기업 협동조합 마을기업 자활기업 소셜벤처 지역특화 규제자유특구 산학연 연구개발 원천기술 상용화 실용화
인프라 테스트베드 데이터 디지털전환 인공지능 반도체 디스플레이 이차전지 바이오 수소 재생에너지 에너지효율 온실가스 친환경 순환경제 콘텐츠 관광 농식품 수산물 임산물 공공구매 기술보호 지식재산 특허
투자유치 펀드 모태펀드 엔젤투자 크라우드펀딩 재도약 재창업 폐업 전직 경영안정 긴급경영 매출채권 신용보증 기술보증 정책자금 운전자금 시설자금 창업보육 액셀러레이터 메이커스페이스 인증 시험인증 표준
""".split()
for w in USER_WORDS: kiwi.add_user_word(w, "NNG", 10.0)
KEEP = {"NNG", "NNP", "SL", "XR", "SH"}
STOP = set("""지원 사업 등 및 위하 통하 추진 내역 사업비 년 억원 백만원 만원 원 개 건 명 관련 대상 분야 중소기업 기업 운영 강화 확대 구축 기반 활성화 육성 제고
수행 실시 마련 제공 필요 경우 각종 해당 내 외 상 중 간 전 후 시 대 소 등등 이상 이하 이내 당 별 식 형 측 성 자 안 과제 세부 단위 프로그램 정부 국가 한국 우리
도모 촉진 확보 향상 개선 창출 조성 발굴 선정 지정 수립 지원금 지원사업 사업화 추진체계 비 수 기 것 수준 단계 방안 체계 과정 결과 효과 목적 내용 조건
연간 매년 신규 계속 기존 최대 최소 공고 공고문 신청 접수 일 월 주 회 차 년도 년차 기간 년간 억 천 백 십""".split())
def toks(text):
    out = []
    for t in kiwi.tokenize(text):
        if t.tag in KEEP and len(t.form) > 1 and t.form not in STOP and not re.fullmatch(r"[\d.,%~∼\-]+", t.form):
            out.append(t.form.lower())
    return out
df["tokens"] = [toks(d) for d in df.doc]
df["n_tok"] = df.tokens.str.len()
print(df.n_tok.describe().round(0).to_string())
df.to_parquet("data/corpus.parquet", index=False)
from collections import Counter
c = Counter(t for ts in df.tokens for t in ts); print(c.most_common(80))
