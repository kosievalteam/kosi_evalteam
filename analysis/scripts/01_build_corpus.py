"""01. 중앙부처 내역사업 분석용 코퍼스 구성
입력: data/biz_central_raw.parquet (Supabase public.biz, gubun='중앙부처', 2023~2026)
출력: data/corpus.parquet
- 내역사업 단위 문서(text) = 내역사업명 + 내역목적(결측 시 세부목적 해당 구간) + 공고지원내용 + 수혜대상
- 연도 간 동일 사업 식별키(사업키) 부여
"""
import re, pandas as pd, numpy as np

df = pd.read_parquet('data/biz_central_raw.parquet')

def norm_name(s):
    if pd.isna(s): return ''
    s = re.sub(r'\(.*?\)', '', str(s))          # (R&D), (일몰) 등 괄호 제거
    s = re.sub(r'[\s·ㆍ‧\-_/,.&]', '', s)
    return s

def clean(s, maxlen=None):
    if pd.isna(s): return ''
    s = str(s).replace('\n', ' ')
    s = re.sub(r'\[공고문 요약\]', ' ', s)
    s = re.sub(r'[ㅇ○□■◦▪•※▶\-]+\s', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:maxlen] if maxlen else s

def purpose_segment(row):
    """내역목적 결측 시 세부목적에서 '(내역명) ...' 구간을 찾아 대체"""
    if isinstance(row['내역목적'], str) and row['내역목적'].strip():
        return clean(row['내역목적']), 'naeyeok'
    sebu = row['세부목적']
    if not isinstance(sebu, str) or not sebu.strip():
        return '', 'none'
    key = norm_name(row['내역사업명'])
    segs = re.split(r'(?=\([^()]{2,40}\))', sebu)
    for seg in segs:
        m = re.match(r'\(([^()]{2,40})\)', seg)
        if m and key and (norm_name(m.group(1)) in key or key in norm_name(m.group(1))):
            return clean(seg), 'sebu_segment'
    if row['n_items'] == 1:
        return clean(sebu, 600), 'sebu_full'
    return clean(sebu, 300), 'sebu_head'

df['n_items'] = df.groupby(['year', '소관', '세부사업명'])['id'].transform('count')
res = df.apply(purpose_segment, axis=1, result_type='expand')
df['purpose_text'], df['purpose_src'] = res[0], res[1]
df['gonggo_text'] = df['공고지원내용'].apply(lambda s: clean(s, 800))
df['target_text'] = df['수혜대상'].apply(lambda s: clean(s, 200))
df['name_text'] = df['내역사업명'].apply(lambda s: re.sub(r'\(R&D\)', ' 연구개발 ', str(s)))
df['text'] = (df['name_text'] + '. ' + df['purpose_text'] + ' ' + df['gonggo_text'] + ' ' + df['target_text']).str.strip()
df['has_purpose'] = df['purpose_src'].eq('naeyeok')
df['has_gonggo'] = df['gonggo_text'].str.len() > 0
df['사업키'] = df['소관'] + '|' + df['세부사업명'].map(norm_name) + '|' + df['내역사업명'].map(norm_name)
df['지원형태'] = df['세부지원'].fillna('').str.replace(r'\s*\(.*?\)', '', regex=True)
df['기존중분류'] = df['지원분야중분류']
df.to_parquet('data/corpus.parquet', index=False)

print(df.shape, '사업키', df['사업키'].nunique())
print(df['purpose_src'].value_counts().to_dict())
print('has_gonggo', df['has_gonggo'].mean().round(3), 'text len', df['text'].str.len().describe()[['mean', '50%', 'min', 'max']].round(0).to_dict())
print(df.groupby('year')[['has_purpose', 'has_gonggo']].mean().round(3))
