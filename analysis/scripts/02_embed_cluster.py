"""02. 형태소 분석 → 지원목적 축 가중 TF-IDF → LSA 임베딩 → KMeans 군집
입력: data/corpus.parquet
출력: data/tokens.parquet, data/emb_lsa.npy, data/clusters.parquet, output/cluster_profile_k{K}.md, output/T0_k_selection.csv
"""
import re, sys, json, numpy as np, pandas as pd
from collections import Counter
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import chi2
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

SEED = 0
df = pd.read_parquet('data/corpus.parquet')

# ---------- 1. 형태소 분석 (명사 중심) ----------
kiwi = Kiwi()
USER_WORDS = ['기술사업화', '사업화', '상용화', '실증', '액셀러레이터', '스케일업', '이차보전', '바우처', '스타트업',
              '벤처', '유니콘', '딥테크', '소부장', '탄소중립', '디지털전환', '스마트공장', '스마트팩토리', '메이커',
              '크라우드펀딩', '모태펀드', '팁스', '규제샌드박스', '테스트베드', '리빙랩', '인큐베이팅', '공공조달',
              '혁신조달', '판로', '내수', '수출바우처', '온라인수출', '전시회', '바이어', '무역보험', '수출보험',
              '신용보증', '기술보증', '매출채권', '재창업', '재기', '폐업', '소상공인', '전통시장', '상권',
              '고용유지', '일자리', '근로자', '산업재해', '안전보건', '작업환경', '직업훈련', '인력양성', '재직자',
              '마이스터', '계약학과', '특성화', '현장실습', '청년', '외국인력', '인증', '시험인증', '표준화', '특허',
              '지식재산', '디자인', '브랜드', '컨설팅', '정보화', '데이터', '플랫폼', '클러스터', '혁신클러스터',
              '산업단지', '산단', '연구개발특구', '규제자유특구', '지역주력', '지역특화', '시설투자', '설비투자',
              '융자', '보증', '투자', '펀드', '출자', '보조', '출연']
for w in USER_WORDS:
    kiwi.add_user_word(w, 'NNG', 5.0)

STOP = set('''사업 지원 추진 위 통 등 및 것 동 내역 목적 수행 관련 분야 대상 년 월 억 백만 원 개 과제 연 당 최대 이내 내외 총 규모 공고 요약
정부 국가 국내 우리 각 해당 경우 중 후 전 간 시 내 외 별 수 성 형 제 소 대 상 하 기 적 안 명 건 식 차 단계 부 처 청 과
필요 마련 도모 확보 제고 강화 촉진 활성 활성화 확대 증진 기여 향상 극대화 실현 달성 추구 선도 창출 유도 지속 체계 기반 중심
중소기업 중소 중견기업 중견 기업 관계 사항 내용 방식 운영 관리 실시 시행 요구 제공 계획 전략 국비 지방비 자부담 정부지원 연구개발비 비 금액 예산 집행 선정 평가 심사 접수 신청 공모 절차 서류 안내 문의 담당 기준 자격 기간 개월 년간 이상 이하 미만 약 명 별도 상이 참고 포함 제외 단 또는 및'''.split())

TAGS = {'NNG', 'NNP', 'SL', 'XR'}
def tokenize(text):
    toks, prev = [], None
    for t in kiwi.tokenize(text, normalize_coda=True):
        if t.tag == 'XSN' and toks and t.form in ('화', '성', '력', '업', '산업', '비', '망', '권', '제'):
            toks[-1] = toks[-1] + t.form; continue
        if t.tag in TAGS and len(t.form) > 1:
            f = t.form.upper() if t.tag == 'SL' else t.form
            if f not in STOP and not re.fullmatch(r'[0-9]+', f):
                toks.append(f)
    return toks

print('tokenizing...', flush=True)
df['tokens'] = df['text'].map(tokenize)
df[['id', 'tokens']].to_parquet('data/tokens.parquet', index=False)
docs = df['tokens'].map(' '.join)

# ---------- 2. TF-IDF + 지원목적 축 가중 ----------
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=0.5, sublinear_tf=True, token_pattern=r'\S+')
X = vec.fit_transform(docs)
terms = np.array(vec.get_feature_names_out())
print('tfidf', X.shape)

# (a) 자료 기반: 기존 지원분야(내역분야 7범주)와의 χ² 연관도 → 목적 어휘 식별
chi, _ = chi2(X, df['내역분야'].fillna('기타'))
chi = np.nan_to_num(chi)
rank = pd.Series(chi).rank(pct=True).values           # 0~1
w_chi = 0.6 + 0.9 * rank                              # 0.6 ~ 1.5

# (b) 사전 기반: 지원목적 핵심어 상향, 산업·기술영역 어휘 하향
PURPOSE_LEX = {
 'R&D': ['연구개발', '기술개발', 'R&D', '원천기술', '핵심기술', '개발', '연구', '기술혁신', '산학연', '출연연'],
 '실증': ['실증', '상용화', '보급', '현장', '적용', '확산', '시범', '테스트베드', '리빙랩', '제품화', '양산', '사업화', '기술사업화', '기술이전', '이전'],
 '창업': ['창업', '스타트업', '벤처', '액셀러레이터', '예비창업', '초기', '인큐베이팅', '보육', '팁스', '유니콘', '스케일업', '재창업'],
 '수출': ['수출', '해외', '글로벌', '해외진출', '바이어', '전시회', '해외시장', '수출바우처', '무역', '통상', '진출', '현지'],
 '자금': ['융자', '보증', '투자', '펀드', '출자', '이차보전', '정책자금', '자금', '금융', '대출', '신용보증', '기술보증', '모태펀드', '보험'],
 '시설': ['시설', '설비', '장비', '구축', '조성', '단지', '산업단지', '산단', '센터', '인프라', '거점', '공간', '입지', '클러스터'],
 '인력': ['인력', '양성', '인재', '교육', '훈련', '직업훈련', '재직자', '학과', '석박사', '전문인력', '기술인력', '역량'],
 '고용': ['고용', '일자리', '근로자', '채용', '고용유지', '노동', '안전보건', '산업재해', '작업환경', '근무환경', '복지', '임금'],
 '경영': ['컨설팅', '인증', '시험', '디자인', '브랜드', '마케팅', '판로', '홍보', '정보화', '디지털전환', '스마트공장', '경영', '생산성', '공공조달', '내수', '유통', '소상공인', '전통시장', '상권'],
}
DOMAIN_LEX = ['의약품', '바이오', '농업', '농산물', '축산', '수산', '해양', '선박', '조선', '자동차', '반도체', '디스플레이', '에너지', '원전', '수소',
              '배터리', '섬유', '철강', '화학', '소재', '부품', '장비', '항공', '우주', '위성', '드론', '로봇', 'AI', '인공지능', 'ICT', 'SW', '소프트웨어',
              '콘텐츠', '게임', '방송', '관광', '식품', '산림', '임업', '목재', '환경', '기후', '탄소', '물', '기상', '문화', '체육', '스포츠',
              '건설', '국토', '교통', '물류', '철도', '도로', '의료', '헬스', '화장품', '뷰티', '패션', '한류', '지식재산', '특허', '표준', '방위', '국방', '원자력']
purpose_words = {w for ws in PURPOSE_LEX.values() for w in ws}
w_lex = np.ones(len(terms))
for i, t in enumerate(terms):
    parts = t.split(' ')
    if any(p in purpose_words for p in parts): w_lex[i] *= 1.6
    if all(p in DOMAIN_LEX for p in parts): w_lex[i] *= 0.5
    elif any(p in DOMAIN_LEX for p in parts) and not any(p in purpose_words for p in parts): w_lex[i] *= 0.75
W = w_chi * w_lex
Xw = X.multiply(W[None, :]).tocsr()
Xw = normalize(Xw)

# ---------- 3. LSA 임베딩 ----------
svd = TruncatedSVD(n_components=160, random_state=SEED)
E = normalize(svd.fit_transform(Xw))
np.save('data/emb_lsa.npy', E)
print('LSA explained var', svd.explained_variance_ratio_.sum().round(3))

# ---------- 4. k 선택 ----------
rows = []
for k in [10, 12, 16, 20, 24, 28, 32]:
    km = KMeans(k, n_init=10, random_state=SEED).fit(E)
    sil = silhouette_score(E, km.labels_, sample_size=3000, random_state=SEED)
    sizes = np.bincount(km.labels_)
    rows.append(dict(k=k, silhouette=round(float(sil), 4), inertia=round(float(km.inertia_), 1), min_size=int(sizes.min()), max_size=int(sizes.max())))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('output/T0_k_selection.csv', index=False)

K = int(sys.argv[1]) if len(sys.argv) > 1 else 24
km = KMeans(K, n_init=30, random_state=SEED).fit(E)
df['cluster'] = km.labels_
d = ((E[:, None, :] - km.cluster_centers_[None]) ** 2).sum(-1)
df['dist'] = d[np.arange(len(df)), km.labels_]
df['second_cluster'] = np.argsort(d, 1)[:, 1]
df[['id', 'cluster', 'dist', 'second_cluster']].to_parquet('data/clusters.parquet', index=False)

# ---------- 5. 군집 프로파일 ----------
Xd = Xw.toarray()
lines = [f'# 군집 프로파일 (k={K})\n']
for c in range(K):
    m = df['cluster'] == c
    cen = Xd[m.values].mean(0)
    top = terms[np.argsort(-cen)[:18]]
    sub = df[m]
    byyear = sub.groupby('year')['내역예산'].agg(['count', 'sum'])
    lines.append(f'## C{c:02d}  n={m.sum()}  2026예산={sub[sub.year==2026]["내역예산"].sum()/100:,.0f}억원  사업키={sub["사업키"].nunique()}')
    lines.append('- 핵심어: ' + ', '.join(top))
    lines.append('- 내역분야: ' + json.dumps(sub['내역분야'].value_counts().head(4).to_dict(), ensure_ascii=False)
                 + ' | 기존중분류: ' + json.dumps(sub['기존중분류'].value_counts().head(4).to_dict(), ensure_ascii=False)
                 + ' | 지원형태: ' + json.dumps(sub['지원형태'].value_counts().head(3).to_dict(), ensure_ascii=False))
    lines.append('- 소관: ' + json.dumps(sub['소관'].value_counts().head(5).to_dict(), ensure_ascii=False))
    ex = sub[sub.year == sub.year.max()].sort_values('내역예산', ascending=False).drop_duplicates('사업키').head(10)
    for _, r in ex.iterrows():
        lines.append(f'  - [{r.year}] {r.소관} | {r.세부사업명} > {r.내역사업명} ({r.내역예산/100:,.0f}억) : {r.purpose_text[:90]}')
    lines.append('')
open(f'output/cluster_profile_k{K}.md', 'w').write('\n'.join(lines))
print('written', f'output/cluster_profile_k{K}.md')
