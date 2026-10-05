"""05. 집계표·도표·안정성 지표 생성
출력: output/T1~T9 CSV, output/fig1~3 PNG, output/typology_assignments.xlsx, output/stats.json
"""
import json, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import koreanize_matplotlib  # noqa: 한글 폰트
from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score

df = pd.read_parquet('data/assign.parquet')
df['억원'] = df['내역예산'] / 100
YEARS = [2023, 2024, 2025, 2026]
MAJ = sorted(df['유형명'].unique())
stats = {}

# T1 대분류 × 연도 (건수·예산·비중)
t1n = df.pivot_table(index='유형명', columns='year', values='id', aggfunc='count', fill_value=0)
t1b = df.pivot_table(index='유형명', columns='year', values='억원', aggfunc='sum', fill_value=0).round(0)
t1s = (t1b / t1b.sum() * 100).round(1)
t1 = pd.concat({'건수': t1n, '예산(억원)': t1b, '예산비중(%)': t1s}, axis=1)
t1['증감률_2023→2026(%)'] = ((t1b[2026] / t1b[2023] - 1) * 100).round(1)
t1.to_csv('output/T1_major_by_year.csv', encoding='utf-8-sig')

# T2 중분류 × 연도
t2b = df.pivot_table(index=['유형명', '중분류명'], columns='year', values='억원', aggfunc='sum', fill_value=0).round(0)
t2n = df.pivot_table(index=['유형명', '중분류명'], columns='year', values='id', aggfunc='count', fill_value=0)
t2 = pd.concat({'건수': t2n, '예산(억원)': t2b}, axis=1)
t2['비중_2026(%)'] = (t2b[2026] / t2b[2026].sum() * 100).round(1)
t2['증감률_2023→2026(%)'] = ((t2b[2026] / t2b[2023].replace(0, np.nan) - 1) * 100).round(1)
t2.to_csv('output/T2_mid_by_year.csv', encoding='utf-8-sig')

# T3 소관 × 대분류 (2026, 예산·건수)
d26 = df[df.year == 2026]
t3 = d26.pivot_table(index='소관', columns='유형명', values='억원', aggfunc='sum', fill_value=0).round(0)
t3['합계'] = t3.sum(1); t3 = t3.sort_values('합계', ascending=False)
t3.to_csv('output/T3_somewon_x_major_2026.csv', encoding='utf-8-sig')
t3n = d26.pivot_table(index='소관', columns='유형명', values='id', aggfunc='count', fill_value=0)
t3n['합계'] = t3n.sum(1); t3n.sort_values('합계', ascending=False).to_csv('output/T3n_somewon_x_major_2026_count.csv', encoding='utf-8-sig')
# 소관별 1위 유형 집중도
top_share = (t3.drop(columns='합계').max(1) / t3['합계'] * 100).round(1)
top_type = t3.drop(columns='합계').idxmax(1)
pd.DataFrame({'1위유형': top_type, '1위유형비중(%)': top_share, '예산(억원)': t3['합계'], '유형수': (t3.drop(columns='합계') > 0).sum(1)}).to_csv('output/T3s_somewon_concentration_2026.csv', encoding='utf-8-sig')
n_somewon_by_type = (t3.drop(columns='합계') > 0).sum(0)
stats['n_somewon_by_type_2026'] = n_somewon_by_type.to_dict()

# T4 기존 지원분야중분류 × 대분류 (2025~2026, 기존분류 보유분)
d = df[df.year >= 2025].copy(); d['기존중분류'] = d['기존중분류'].fillna('(결측)')
t4 = pd.crosstab(d['기존중분류'], d['유형명'])
t4['합계'] = t4.sum(1); t4.sort_values('합계', ascending=False).to_csv('output/T4_taxonomy_x_major.csv', encoding='utf-8-sig')
has = d[d['기존중분류'] != '(결측)']
stats['nmi_vs_existing_mid'] = round(float(normalized_mutual_info_score(has['기존중분류'], has['중분류코드'])), 3)
stats['nmi_vs_existing_field'] = round(float(normalized_mutual_info_score(d['내역분야'], d['대분류코드'])), 3)
stats['n_missing_existing_2025_26'] = int((d['기존중분류'] == '(결측)').sum())
# 기존 '혼합(단독+공동)', '기술사업화/이전/지도' 세분화 효과
for k in ['혼합(단독+공동)', '기술사업화/이전/지도', '디자인/상품화/사업화']:
    sub = d[d['기존중분류'] == k]
    stats[f'split_{k}'] = sub['중분류명'].value_counts().head(6).to_dict()

# T5 지원형태 × 대분류 (2026 예산)
def form_group(s):
    s = s or ''
    if s == '융자' or s == '보조;융자': return '융자'
    if '출자' in s: return '출자·투자'
    if s == '출연': return '출연'
    if s == '직접': return '직접'
    if '보조' in s and '출연' not in s: return '보조(혼합)'
    return '출연·보조 혼합' if s else '미기재'
d26 = d26.assign(지원형태군=d26['지원형태'].map(form_group))
t5 = d26.pivot_table(index='유형명', columns='지원형태군', values='억원', aggfunc='sum', fill_value=0).round(0)
t5['합계'] = t5.sum(1); t5_share = (t5.div(t5['합계'], axis=0) * 100).round(1)
t5.to_csv('output/T5_fundingform_x_major_2026.csv', encoding='utf-8-sig'); t5_share.to_csv('output/T5s_fundingform_share_2026.csv', encoding='utf-8-sig')

# T6 텍스트 보유율 × 대분류
t6 = df.groupby('유형명').agg(건수=('id', 'count'), 내역목적보유율=('has_purpose', 'mean'), 공고지원내용보유율=('has_gonggo', 'mean'), 사업키수=('사업키', 'nunique')).round(3)
t6.to_csv('output/T6_text_coverage_by_major.csv', encoding='utf-8-sig')
stats['coverage'] = {'purpose': round(float(df.has_purpose.mean()), 3), 'gonggo': round(float(df.has_gonggo.mean()), 3), 'n_rows': int(len(df)), 'n_keys': int(df['사업키'].nunique())}

# T7 연도 간 유형 전환 사례(연도별 배정이 사업키 통일값과 다른 건)
sw = df[df['중분류코드_연도별'] != df['중분류코드']]
t7 = sw.groupby('사업키').agg(소관=('소관', 'first'), 세부사업명=('세부사업명', 'first'), 내역사업명=('내역사업명', 'first'),
                          최종유형=('중분류명', 'first'), 연도별배정=('중분류코드_연도별', lambda x: ';'.join(f'{y}:{c}' for y, c in zip(sw.loc[x.index, 'year'], x))),
                          예산2026=('억원', lambda x: x[sw.loc[x.index, 'year'] == 2026].sum()))
t7.sort_values('예산2026', ascending=False).to_csv('output/T7_type_switch_cases.csv', encoding='utf-8-sig')
multi = df.groupby('사업키')['year'].nunique(); keys_multi = multi[multi > 1].index
yr_consistency = 1 - df[df['사업키'].isin(keys_multi)].groupby('사업키')['중분류코드_연도별'].nunique().gt(1).mean()
maj_consistency = 1 - df[df['사업키'].isin(keys_multi)].groupby('사업키')['대분류_연도별'].nunique().gt(1).mean()
stats['year_consistency_mid'] = round(float(yr_consistency), 3); stats['year_consistency_major'] = round(float(maj_consistency), 3)
stats['n_keys_multi_year'] = int(len(keys_multi)); stats['n_switch_rows'] = int(len(sw))

# T8 2026 유형별 상위 사업
t8 = d26.sort_values('억원', ascending=False).groupby('유형명').head(8)[['유형명', '중분류명', '소관', '세부사업명', '내역사업명', '억원', '지원형태']]
t8.to_csv('output/T8_top_programs_2026.csv', index=False, encoding='utf-8-sig')

# T9 다부처 운영 유형(2026): 유형별 소관 수·상위 3개 소관 비중
rows = []
for m in MAJ:
    s = t3[m].sort_values(ascending=False); s = s[s > 0]
    rows.append(dict(유형=m, 소관수=int(len(s)), 예산=round(s.sum()), 상위1소관=s.index[0] if len(s) else '', 상위1비중=round(s.iloc[0] / s.sum() * 100, 1) if len(s) else 0,
                     상위3비중=round(s.head(3).sum() / s.sum() * 100, 1) if len(s) else 0, 건수=int(t3n[m].sum())))
pd.DataFrame(rows).to_csv('output/T9_multi_ministry_2026.csv', index=False, encoding='utf-8-sig')

# 군집 품질
stats['k_selection'] = pd.read_csv('output/T0_k_selection.csv').to_dict('records')
# 유형 내 군집 순도: 각 유형에서 최다 1차 군집 비중
pur = df.groupby('대분류코드')['cluster'].agg(lambda x: x.value_counts(normalize=True).iloc[0]).round(2)
stats['major_cluster_purity'] = pur.to_dict()
stats['rule_override_rate'] = None
json.dump(stats, open('output/stats.json', 'w'), ensure_ascii=False, indent=1)

# ---------- 엑셀 ----------
asg = pd.read_csv('output/typology_assignments.csv')
with pd.ExcelWriter('output/typology_assignments.xlsx', engine='openpyxl') as xw:
    asg.to_excel(xw, sheet_name='배정결과(행단위)', index=False)
    pd.read_csv('output/typology_scheme.csv').to_excel(xw, sheet_name='유형체계', index=False)
    t1.to_excel(xw, sheet_name='T1_대분류x연도'); t2.to_excel(xw, sheet_name='T2_중분류x연도'); t3.to_excel(xw, sheet_name='T3_소관x대분류_2026')
    t4.to_excel(xw, sheet_name='T4_기존분류x대분류'); t5.to_excel(xw, sheet_name='T5_지원형태x대분류'); t8.to_excel(xw, sheet_name='T8_유형별상위사업', index=False)
    pd.DataFrame(rows).to_excel(xw, sheet_name='T9_다부처운영', index=False)

# ---------- 도표 ----------
BLUE = '#2a78d6'; SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#1c5cab', '#104281', '#0d366b']
TXT = '#0b0b0b'; MUTED = '#52514e'; GRID = '#e6e5e1'; SURF = '#fcfcfb'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': GRID, 'axes.labelcolor': TXT, 'xtick.color': MUTED, 'ytick.color': MUTED, 'figure.facecolor': SURF, 'axes.facecolor': SURF})

# fig1: 2026 대분류별 예산 (가로 막대, 단일 계열)
s = t1b[2026].sort_values()
fig, ax = plt.subplots(figsize=(9, 5.2))
bars = ax.barh(s.index, s.values / 10000, color=BLUE, height=0.62)
for b, v, sh in zip(bars, s.values / 10000, t1s[2026].loc[s.index]):
    ax.text(v + 0.05, b.get_y() + b.get_height() / 2, f'{v:,.1f}조원 ({sh:.1f}%)', va='center', color=TXT, fontsize=9)
ax.set_xlim(0, s.max() / 10000 * 1.25); ax.set_xlabel('2026년 내역예산(조원)'); ax.grid(axis='x', color=GRID, lw=0.6); ax.set_axisbelow(True)
for sp in ['top', 'right', 'left']: ax.spines[sp].set_visible(False)
ax.set_title('그림 1. 중앙부처 중소기업 지원 내역사업의 지원목적 유형별 예산(2026년)', loc='left', fontsize=11, color=TXT)
plt.tight_layout(); plt.savefig('output/fig1_budget_by_type_2026.png', dpi=160); plt.close()

# fig2: 유형별 예산 추이 소형다중(2023~2026)
fig, axes = plt.subplots(2, 5, figsize=(13, 5.4), sharex=True)
for ax, m in zip(axes.flat, MAJ):
    y = t1b.loc[m, YEARS].values / 10000
    ax.plot(YEARS, y, color=BLUE, lw=2, marker='o', ms=5)
    ax.set_title(m, fontsize=9.5, loc='left', color=TXT)
    ax.text(YEARS[-1], y[-1], f' {y[-1]:.2f}', va='center', fontsize=8.5, color=TXT)
    ax.set_xticks(YEARS); ax.tick_params(labelsize=8); ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.set_ylim(0, max(y.max() * 1.35, 0.05)); ax.set_xlim(2022.7, 2026.8)
    for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
axes[0, 0].set_ylabel('조원'); axes[1, 0].set_ylabel('조원')
fig.suptitle('그림 2. 지원목적 유형별 예산 추이(2023~2026년, 조원)', x=0.01, ha='left', fontsize=11, color=TXT)
plt.tight_layout(); plt.savefig('output/fig2_trend_small_multiples.png', dpi=160); plt.close()

# fig3: 소관 × 대분류 히트맵 (2026, 소관 내 비중)
h = t3.drop(columns='합계'); h = h[h.sum(1) >= 500]  # 500억 이상 소관
hs = h.div(h.sum(1), axis=0) * 100
fig, ax = plt.subplots(figsize=(11, 0.42 * len(hs) + 2.2))
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list('seq', ['#f6f9fe'] + SEQ)
im = ax.imshow(hs.values, cmap=cmap, vmin=0, vmax=100, aspect='auto')
ax.set_xticks(range(len(hs.columns))); ax.set_xticklabels([c.split('. ')[0] for c in hs.columns]); ax.set_yticks(range(len(hs))); ax.set_yticklabels([f'{i} ({h.loc[i].sum()/10000:.1f}조)' for i in hs.index], fontsize=9)
for i in range(hs.shape[0]):
    for j in range(hs.shape[1]):
        v = hs.values[i, j]
        if v >= 5: ax.text(j, i, f'{v:.0f}', ha='center', va='center', fontsize=8, color='white' if v > 55 else TXT)
cols = list(hs.columns); ax.set_xlabel('지원목적 유형(대분류): ' + ' / '.join(cols[:5]) + '\n' + ' / '.join(cols[5:]), fontsize=8, color=MUTED)
ax.set_title('그림 3. 소관별 지원목적 유형 구성(2026년, 소관 예산 내 비중 %, 예산 500억원 이상 소관)', loc='left', fontsize=11, color=TXT)
cb = plt.colorbar(im, ax=ax, fraction=0.025, pad=0.02); cb.set_label('비중(%)', color=MUTED)
plt.tight_layout(); plt.savefig('output/fig3_heatmap_somewon_type_2026.png', dpi=160); plt.close()
print(json.dumps(stats, ensure_ascii=False, indent=1)[:3000])
print(t1.to_string())
