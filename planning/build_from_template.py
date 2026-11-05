"""정책평가팀 개선방향 보고서 양식(.hwp)을 원형으로 AI 에이전트 기획서를 재작성한다.

사용: python build_from_template.py <양식.hwp> <출력 경로(.hwpx)>
양식의 문단·표를 복제하여 문단모양·글자모양·테두리를 그대로 쓰고 텍스트만 바꾼다.
"""
import copy
import random
import sys
import zipfile

from hwpx import HwpxDocument
from lxml import etree

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
NS = {'hp': HP}
Q = lambda t: '{%s}%s' % (HP, t)

src, out = sys.argv[1], sys.argv[2]
tmp = out + '.base.hwpx'
HwpxDocument.open(src).save_to_path(tmp)
zin = zipfile.ZipFile(tmp)
root = etree.fromstring(zin.read('Contents/section0.xml'))
P = root.findall('hp:p', NS)


def rid():
    return str(random.randint(10**8, 2**31 - 1))


def strip_layout(el):
    for ls in el.iter(Q('linesegarray')):
        ls.getparent().remove(ls)


def clone(i):
    p = copy.deepcopy(P[i])
    for e in p.iter(Q('p'), Q('tbl')):
        if e.get('id') is not None:
            e.set('id', rid())
    strip_layout(p)
    return p


def set_runs(p, segs, para_pr=None):
    for r in p.findall('hp:run', NS):
        p.remove(r)
    for cp, text in segs:
        r = etree.SubElement(p, Q('run'), charPrIDRef=str(cp))
        etree.SubElement(r, Q('t')).text = text
    if para_pr:
        p.set('paraPrIDRef', str(para_pr))
    return p


def para(i, segs, para_pr=None):
    return set_runs(clone(i), segs, para_pr)


def cell_set(tc, lines, cp=None, para_pr=None):
    """셀 텍스트 교체. lines: 문자열 또는 [(charPr, text), ...] 목록의 리스트."""
    sub = tc.find('hp:subList', NS)
    ps = sub.findall('hp:p', NS)
    proto = ps[0]
    runs = proto.findall('hp:run', NS)
    base_cp = cp or (runs[0].get('charPrIDRef') if runs else '0')
    for q in ps:
        sub.remove(q)
    for line in lines:
        q = copy.deepcopy(proto)
        q.set('id', rid())
        strip_layout(q)
        segs = line if isinstance(line, list) else [(base_cp, line)]
        set_runs(q, segs, para_pr)
        sub.append(q)


def tbl_of(p):
    return next(p.iter(Q('tbl')))


def cells(tr):
    return tr.findall('hp:tc', NS)


def place(tc, col, row, width=None):
    a = tc.find('hp:cellAddr', NS)
    a.set('colAddr', str(col)); a.set('rowAddr', str(row))
    s = tc.find('hp:cellSpan', NS)
    s.set('colSpan', '1'); s.set('rowSpan', '1')
    if width:
        tc.find('hp:cellSz', NS).set('width', str(width))


def finish_table(tb, nrows, ncols):
    tb.set('rowCnt', str(nrows)); tb.set('colCnt', str(ncols))
    h = sum(int(tr.find('hp:tc', NS).find('hp:cellSz', NS).get('height')) for tr in tb.findall('hp:tr', NS))
    tb.find('hp:sz', NS).set('height', str(h))


# ── 원형 ─────────────────────────────────────────────
def title(text):
    p = clone(0)
    tc = next(tbl_of(p).iter(Q('tc')))
    cell_set(tc, [text])
    return p


def box(cur, imp, note):
    p = clone(1)
    tc = next(tbl_of(p).iter(Q('tc')))
    sub = tc.find('hp:subList', NS)
    ps = sub.findall('hp:p', NS)
    l1, sp, l2, l3 = ps[0], ps[1], ps[2], ps[3]
    for q in ps:
        sub.remove(q)
    set_runs(l1, [('24', '◈'), ('93', ' '), ('119', '(현행) '), ('9', cur)])
    set_runs(l2, [('30', ' ⇨'), ('31', ' '), ('117', '(개선) '), ('7', imp)])
    set_runs(l3, [('67', ' '), ('109', '※ '), ('121', note)])
    for q in (l1, sp, l2, copy.deepcopy(sp), l3):
        strip_layout(q)
        sub.append(q)
    return p


def section(num, text, page_break=False):
    p = clone(3)
    tcs = list(tbl_of(p).iter(Q('tc')))
    cell_set(tcs[0], [num])
    cell_set(tcs[2], [text])
    if page_break:
        p.set('pageBreak', '1')
    return p


def spacer(i):
    return clone(i)


def prob(mark, head, body):           # 1. 문제점: ➊ (머리) 본문
    return para(5, [('75', mark + ' '), ('79', '(%s)' % head), ('7', ' ' + body)])


def star1(text):                      # 1. 문제점 하위 *
    return para(7, [('13', '   '), ('22', '* '), ('136', text)])


def item(text, page_break=False):     # 2. 주요 내용: ➊ 소제목
    p = para(30, [('79', text)])
    p.set('pageBreak', '1' if page_break else '0')
    return p


def o(text, head=None):               # ㅇ
    if head:
        return para(50, [('58', ' '), ('18', 'ㅇ '), ('171', '(%s)' % head), ('172', ' '), ('20', text)])
    return para(32, [('58', ' '), ('18', 'ㅇ '), ('151', text)])


def dash(text, head=None):            # -
    segs = [('58', '  -'), ('25', ' ')]
    segs += [('171', '(%s) ' % head), ('18', text)] if head else [('18', text)]
    return para(34, segs)


def star(text):                       # *
    return para(42, [('13', '   * '), ('211', text)])


def caption(text):
    return para(37, [('154', '  < %s >' % text)])


def data_table(headers, rows, weights, left_cols=()):
    p = clone(38)
    tb = tbl_of(p)
    trs = tb.findall('hp:tr', NS)
    h0, h1 = cells(trs[0]), cells(trs[1])
    head_proto = [h0[0], h0[2], h0[4]]
    body_proto = [h1[0], h1[2], h1[4]]
    total = int(tb.find('hp:sz', NS).get('width'))
    ws = [round(total * w / sum(weights)) for w in weights]
    ws[-1] = total - sum(ws[:-1])
    for tr in trs:
        tb.remove(tr)
    n = len(headers)

    def pick(protos, j):
        return protos[0] if j == 0 else (protos[2] if j == n - 1 else protos[1])

    for r, vals in enumerate([headers] + rows):
        tr = etree.SubElement(tb, Q('tr'))
        for j, v in enumerate(vals):
            tc = copy.deepcopy(pick(head_proto if r == 0 else body_proto, j))
            place(tc, j, r, ws[j])
            lines = v.split('\n') if isinstance(v, str) else v
            if r == 0:
                cell_set(tc, lines, cp='156')
            elif j == 0:
                cell_set(tc, lines, cp='204')
            else:
                cell_set(tc, lines, cp='14', para_pr='11' if j in left_cols else '70')
            tr.append(tc)
    finish_table(tb, len(rows) + 1, n)
    for r in p.findall('hp:run', NS)[1:]:
        p.remove(r)
    return p


def compare_table(rows):
    p = clone(28)
    tb = tbl_of(p)
    trs = tb.findall('hp:tr', NS)
    head, gap, itm, sep = trs[0], trs[1], trs[8], trs[9]
    for tr in trs:
        tb.remove(tr)
    seq = [copy.deepcopy(head), copy.deepcopy(gap)]
    for k, (a, b, c) in enumerate(rows):
        t = copy.deepcopy(itm)
        cs = cells(t)
        cell_set(cs[0], [a]); cell_set(cs[2], b.split('\n')); cell_set(cs[4], c.split('\n'))
        seq.append(t)
        if k < len(rows) - 1:
            seq.append(copy.deepcopy(sep))
    for r, tr in enumerate(seq):
        for c, tc in enumerate(cells(tr)):
            place(tc, c, r)
            strip_layout(tc)
        tb.append(tr)
    finish_table(tb, len(seq), 5)
    return p


def flow(steps):                      # □ 단계(주체) → ...
    segs = [('23', '□ ')]
    for k, (s, w) in enumerate(steps):
        if k:
            segs.append(('11', ' → '))
        segs += [('11', s), ('201', '(%s)' % w)]
    return para(121, segs)


def annex(title_text):
    p = clone(122)
    tcs = list(tbl_of(p).iter(Q('tc')))
    cell_set(tcs[1], [title_text])
    p.set('pageBreak', '1')
    return p


def annex_head(text):
    return para(124, [('128', '□ ' + text)])


def note(text):
    return para(129, [('13', '  * ' + text)])


# ── 본문 ─────────────────────────────────────────────
B = []
B += [title('중소기업 지원사업 판정·분류 AI 에이전트 도입(안)'),
      box('특정 부처 예산사업설명서를 중심으로 검토자가 수기로 중소기업 지원사업을 판정하여 누락 부처가 발생하고, 8주의 법정 기한 안에서 판정의 일관성 확보에 한계',
          '전 부처 국회확정 예산을 전수 대상으로 AI 에이전트가 판정·분류를 1차 수행하고, 검토자는 불확실·고위험 사업의 검토와 최종 확정에 집중하는 체계로 전환',
          '중소기업 지원사업 현황조사(법정 조사, 매년 1월 말 예산서 수집 → 3월 말 완료) 수행체계 개편'),
      spacer(2)]

B += [section('1', '문제점 및 한계'), spacer(4),
      prob('➊', '검토 범위 누락', '특정 부처 예산사업설명서 중심 검토로 전 부처 국회확정 예산 대비 검토 공백 발생'),
      spacer(8),
      star1("지원사업 확인 소관은 전체 61~62개 중 16~22개('24~'26년), '26년에는 교육부·보건복지부 등 6개 소관에서 지원사업이 새로 확인"),
      spacer(8),
      star1('지원사업 미확인 소관에도 기업 지원 관련 사업(사업명 기준)이 연 51~87건 존재하고, 사업설명자료 DB에 없는 세부사업이 연 567~951건(국회확정 예산 목록 대비 6.2~10.7%)'),
      spacer(10),
      prob('➋', '업무 과부하', '약 8주 안에 국회확정 예산 세부사업 8,900~9,200개와 243개 자치단체 세출사업을 수기로 전수 검토'),
      spacer(8),
      star1('중앙부처 지원 세부사업 1개를 찾기 위해 제외 세부사업 17~22개를 함께 검토하고, 선별된 세부사업도 내역사업별로 다시 판정'),
      spacer(8),
      star1('예산서 공개(1월 말~2월 초)부터 3월 말 완료까지 수집·판정·분류·집계·검증이 같은 기간에 집중'),
      spacer(10),
      prob('➌', '판정 일관성 미흡', '간접 지원·혼합 편성 사업의 판정 경계가 모호하고, 판정 근거를 사업별로 기록·축적하는 체계가 미흡'),
      spacer(8),
      star1('한 세부사업 안에 기업 지원 내역과 기관 운영 내역이 섞여, 지원 세부사업 예산(31.9~36.0조원)과 지원 내역사업 예산(28.7~31.0조원)의 차이가 연 3.2~5.1조원'),
      spacer(10),
      prob('➍', '연속성 관리 부담', '사업의 신설·일몰·이관·통합·분리를 매년 수작업으로 대조하여 계속사업에도 재검토 부담 발생'),
      spacer(8),
      star1("고유 내역사업 1,391개 중 2개 연도 이상 연속 확인된 사업은 565개(40.6%), '23~'26년 일몰 196건·세부사업 이관 33건"),
      spacer(10),
      prob('➎', '분류 활용 한계', '기존 지원분야 분류의 결측·포괄 항목이 많아 사업 비교와 정책 분석에 제약'),
      spacer(8),
      star1("'24~'26년 중앙부처 내역사업 2,189건 중 787건(36.0%)이 지원분야 미연계, '혼합' 등 포괄 항목 331건")]

B += [section('2', '주요 내용'),
      compare_table([
          ('검토범위', '특정 부처\n예산사업설명서 중심', '전 부처 국회확정 예산 전수'),
          ('판정단위', '세부사업 중심 판정', '중앙부처 내역사업·\n지자체 세부사업'),
          ('판정방식', '검토자 전수 판독', 'AI 1차 판정·분류 +\n검토자 확정'),
          ('판정근거', '검토자 판단(기록 미흡)', '근거 문장·적용 조항·\n확정 이력 기록'),
          ('승계관리', '연도별 수작업 대조', '전년 판정 승계,\n변경 사업만 재판정'),
          ('분류체계', '지원분야 분류(결측 36%)', '5축 분류\n(목적·대상·수단·내용·산업)'),
      ]),
      spacer(29)]

B += [item('➊ 국회확정 예산 전수 검토 체계 구축'), spacer(31),
      o('전 부처 국회확정 예산 세부사업 목록을 판정 모집단으로 확정하고, 사업설명자료는 판정 근거 자료로 연결'),
      spacer(33),
      dash("열린재정 '재정사업 설명자료(분류별 검색)'의 국회확정 예산 세부사업 전체(연 8,900~9,200개, 61~62개 소관)", '모집단'),
      spacer(33),
      dash('모든 세부사업에 해당·비해당·판정 보류 중 하나를 부여하여 판정 결과가 없는 사업이 남지 않도록 관리', '판정 완결성'),
      spacer(41),
      star('설명자료 미확보 사업은 프로그램·단위사업·세부사업명과 예산으로 1차 선별 후 부처에 자료 보완 요청, 세부 내역 비공개 소관(국가정보원 등)은 판정 보류로 사유 기록'),
      spacer(53),
      o('243개 자치단체(광역 17·기초 226)의 세출예산 사업명세서를 수집하여 같은 체계로 판정', '지자체')]

B += [spacer(85), item('➋ 최하위 사업 단위 판정과 재원 구분'), spacer(31),
      o('판정·분류·예산 집계의 기본 단위를 중앙부처는 내역사업, 지자체는 세부사업으로 하고, 상위 사업은 1차 선별에 활용'),
      spacer(33),
      dash('세부사업 1차 선별 → 내역사업 판정', '중앙부처'),
      spacer(33),
      dash('단위사업 1차 선별 → 세부사업 판정', '지자체'),
      spacer(53),
      o('지자체 사업의 국비·시도비·시군구비를 구분하고, 국고보조 사업은 중앙부처 사업과 연결하여 중복 집계 방지', '재원 구분'),
      spacer(41),
      star('국비분은 중앙부처 사업으로, 시도비·시군구비분은 지자체 자체 재원으로 구분 집계')]

B += [spacer(85), item('➌ AI 에이전트 6단계 판정·분류 체계 도입', page_break=True), spacer(31),
      o('수집부터 검토 배분까지 6단계를 AI 에이전트가 수행하고, 단계별 결과와 근거를 DB에 기록하여 검토자가 확인·수정'),
      spacer(46),
      caption('AI 에이전트 처리 단계'),
      data_table(['단계', '주요 기능', '활용 기반'], [
          ['① 수집·적재', '국회확정 예산 목록으로 모집단 확정, 사업설명자료·지자체 예산서 수집, 소관·자치단체별 확보율 점검', '열린재정,\n지방재정365'],
          ['② 구조화', '세부·내역사업(지자체는 단위·세부사업) 항목 추출, 재원·국고보조 여부 추출', '예산서 파싱 DB'],
          ['③ 연속성 대조', '전년 DB와 매칭(코드 → 사업명 → 임베딩 유사도), 계속·신규·일몰·이관·통합·분리 판별', '일몰·이관 이력 DB'],
          ['④ 판정', '상위 사업 1차 선별 후 규칙·유사 사례·생성형 AI 3중 판정, 근거 문장·적용 조항·신뢰도 산출', '판정 기준 매뉴얼'],
          ['⑤ 분류', '5축 유형(목적·대상·수단·내용·산업) 배정, 복수 목적 사업은 주·보조 유형 부여', '임베딩 유형화 체계'],
          ['⑥ 검토 배분', '신뢰도·위험도 기준으로 필수 검토·표본 검토·승계 확인 등급 부여', '검토 화면'],
      ], [10, 30, 11], left_cols=(1,)),
      spacer(49),
      o("세 판정이 일치하고 신뢰도가 기준 이상이면 '판정 확실', 그 밖에는 '판정 불확실'로 분류", '판정 방식'),
      spacer(33),
      dash('1차 선별은 명백한 비해당(기본경비·인건비 등)만 제외하고, 소관 단위 일괄 제외는 금지'),
      spacer(41),
      star('단위사업 또는 세부사업명에 기본경비·인건비가 포함된 사업 연 1,767~1,792개(전체의 약 20%)'),
      spacer(53),
      o('정책평가팀이 구축한 예산서 파싱 DB와 임베딩 기반 5축 유형화 체계를 재사용', '선행 기반 활용'),
      spacer(41),
      star('지원내용 기반 분류기의 교차검증 정확도 대분류 93.0%·중분류 88.1%')]

B += [spacer(85), item('➍ 검토자 역할 재정의 및 검토 배분'), spacer(31),
      o('검토자는 전수 판독 대신 불확실·고위험 사업의 검토와 최종 확정을 담당하고, 수정 사유를 기록하여 판정 기준에 환류'),
      spacer(46),
      caption('검토 등급별 대상 및 방식'),
      data_table(['등급', '대상', '검토 방식'], [
          ['필수 검토', '판정 불확실, 전년 대비 판정 변경, 상위 사업 선별과 상충, 예산 상위 사업, 구조화 점검 대상', '전수 확인'],
          ['표본 검토', '판정 확실한 신규·변경 사업(해당·비해당 모두), 1차 선별 제외 사업', '무작위 표본(예: 20%),\n오류 시 전수 확대'],
          ['승계 확인', '계속(변경 없음) 사업', '일괄 확인,\n표본(예: 5%) 점검'],
      ], [8, 28, 14], left_cols=(1,)),
      spacer(49),
      o('최종 확정은 검토자 명의로 기록하고, AI 판정은 검토 보조 자료로 규정', '책임성'),
      spacer(33),
      dash('수정 사유(기준 해석 차이·원문 정보 부족·추출 오류·분류 체계 미비)를 구분 기록하여 규칙과 판정 기준 매뉴얼 개정에 반영')]

B += [spacer(85), item('➎ 정답 자료·판정 기준 정비 및 성능 관리', page_break=True), spacer(31),
      o('과거 판정 결과를 정답 자료로 정비하고, 판정 기준을 조항 단위로 정형화'),
      spacer(33),
      dash('세부사업 선별용·내역사업 판정용·지자체 판정용으로 구분 구축', '정답 자료'),
      spacer(41),
      star("과거 검토 범위 밖 소관의 사업은 '비해당'이 아닌 '미검토'로 보아 정답 자료에서 제외하고, 표본을 새로 판정하여 보완"),
      spacer(33),
      dash('조항별 식별번호·포함 요건·제외 요건·대표 사례로 정리하여 생성형 AI 판정 근거와 검토자 공통 기준으로 활용', '판정 기준 매뉴얼'),
      spacer(53),
      o('시범 운영 결과로 확정하되, 지원사업 누락 방지를 위해 재현율을 우선', '성능 목표'),
      spacer(46),
      caption('정량 목표(안)'),
      data_table(['구분', '지표', '목표(안)'], [
          ['판정', '재현율(지원사업을 놓치지 않는 비율)', '98% 이상'],
          ['판정', '정밀도(지원 판정 사업 중 실제 지원사업 비율)', '85% 이상'],
          ['분류', '지원목적 대분류 정확도', '90% 이상'],
          ['운영', '필수 검토 대상 비중', '판정 대상의 20% 이내'],
          ['운영', '판정·분류 확정 시점', '3월 중순'],
      ], [8, 26, 14], left_cols=(1,)),
      spacer(49),
      o("'24~'25년 자료로 구축하고 '26년 자료로 검증한 뒤, '27년 현황조사에서 수기 판정과 병행 비교", '검증')]

B += [spacer(85), item('➏ 위험 관리 장치 마련'), spacer(31),
      o('모집단 누락, 지원사업 누락, 중복 집계, 생성형 AI의 사실과 다른 출력에 대한 관리 장치를 마련'),
      spacer(33),
      dash('국회확정 예산 목록과 판정 결과를 소관·회계별 건수·예산 합계로 대조하고, 판정 결과가 없는 사업은 자동 경고', '모집단 누락'),
      spacer(33),
      dash('비해당 판정 표본 점검, 전년도 지원사업 보유 상위 사업의 1차 선별 제외 금지', '지원사업 누락'),
      spacer(33),
      dash('판정 근거를 원문 인용으로 제한하고, 인용 문장의 원문 일치 여부를 자동 확인', '사실과 다른 출력'),
      spacer(33),
      dash('판정·검토 이력은 내부 DB에 보관하고, 공공부문 생성형 AI 활용 지침 준수', '정보 보안')]

B += [spacer(85), section('3', '기대 효과'), spacer(4),
      prob('➊', '포괄성', '전 부처 국회확정 예산의 모든 세부사업이 판정 결과를 가져 부처 누락 해소'),
      spacer(10),
      prob('➋', '적시성', '1차 판정·분류를 2월 3주까지 마치고, 3월은 검토·확정과 검증에 집중'),
      spacer(10),
      prob('➌', '일관성·투명성', '판정 근거·적용 조항·확정 이력이 남아 사후 검증과 대외 설명 가능'),
      spacer(10),
      prob('➍', '활용성', '5축 분류가 매년 자동 갱신되어 사전협의 유사·중복 검토, 성과평가 대상 선정 등에 활용'),
      spacer(118)]

B += [section('4', '추진 일정'), spacer(120),
      flow([('준비', "정답 자료·매뉴얼·시제품, ’26.11~12월"), ('병행 운영', "중앙부처, ’27.1~3월"),
            ('고도화·지자체 확장', "’27.4~12월"), ('본운영', "중앙부처·지자체, ’28.1월~")]),
      spacer(120),
      flow([('수집·구조화', '1월 말~2월 1주'), ('1차 판정·분류', '2월 2~3주'),
            ('검토·확정', '2월 4주~3월 2주'), ('검증·결과 확정', '3월 3~4주')])]
B[-1].findall('hp:run', NS)[0].find('hp:t', NS).text = '□ (연간 운영) '

B += [annex('국회확정 예산 대비 검토 범위 진단'), spacer(123),
      annex_head('연도별 검토 범위'),
      data_table(['구분', "'24년", "'25년", "'26년"], [
          ['국회확정 예산 세부사업(회계별)', '8,907개', '8,890개', '9,154개'],
          ['소관 수', '61개', '61개', '62개'],
          ['지원사업 확인 소관 수', '17개', '16개', '22개'],
          ['사업설명자료 DB 미확보 세부사업', '617개', '951개', '567개'],
          ['미확인 소관 내 기업 지원 관련 사업', '87건', '83건', '51건'],
          ['선별 지원 세부사업', '470개', '434개', '397개'],
      ], [22, 9, 9, 9]),
      spacer(126),
      annex_head("지원사업 미확인 소관의 검토 후보 예시('26년)"),
      data_table(['소관', '세부사업', '예산'], [
          ['방위사업청', '방위산업 수출지원', '675억원'],
          ['방위사업청', '방산수출 투자지원', '300억원'],
          ['공정거래위원회', '대중소기업간 거래행태개선 및 동반성장시책추진', '27억원'],
          ['외교부', '해외진출기업 활동지원', '37억원'],
          ['재외동포청', '재외동포·국내 중소기업 비즈니스 활성화', '17억원'],
          ['새만금개발청', '새만금산단 기업성장센터 건립', '17억원'],
      ], [10, 28, 8], left_cols=(1,)),
      note('사업명 어휘 기준 단순 추출 결과로, 지원사업 해당 여부는 판정 필요. 자료: 열린재정 국회확정 예산, 정책평가팀 DB')]

B += [annex('결정 및 확인 사항'), spacer(123),
      annex_head('결정 필요 사항'),
      dash('재현율 98%·정밀도 85% 등 정량 목표(안)와 본운영 전환 기준', '목표치'),
      dash("'27년 현황조사의 수기 검토·AI 판정 병행 운영 여부", '병행 운영'),
      dash('외부 상용 API 활용 또는 내부 모델 구축 여부', '생성형 AI'),
      dash('개발 인력의 내부 확보 또는 외부 위탁 여부와 소요 예산', '예산·인력'),
      spacer(126),
      annex_head('착수 전 확인 사항'),
      dash('과거 현황조사의 세부사업·내역사업별 선별·제외 판정 결과 보유 연도와 제외 사유 기록 여부'),
      dash('현행 판정 기준 문서의 최신본과 근거 법령 조문'),
      dash('세부 내역이 비공개인 세부사업의 처리 기준과 부처 자료 요청 절차'),
      dash('243개 자치단체 전체 세출사업 규모, 지자체 판정 단위, 국고보조 매칭 사업의 집계 기준')]

for p in root.findall('hp:p', NS):
    root.remove(p)
for p in B:
    root.append(p)

xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
with zipfile.ZipFile(out, 'w') as zout:
    for info in zin.infolist():
        data = xml if info.filename == 'Contents/section0.xml' else zin.read(info.filename)
        zout.writestr(info, data, compress_type=zipfile.ZIP_STORED if info.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
print('saved', out, len(B), 'paragraphs')
