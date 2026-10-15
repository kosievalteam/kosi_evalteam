# -*- coding: utf-8 -*-
"""개조식 Markdown(□/○/-/*) → KOSI 이슈ⁿ포커스 양식 HWPX 생성기
   양식 규칙(샘플 .hwp 기준): 표지 제목 KoPub돋움 Bold 20 / 저자 KoPub돋움 Medium 10.5 / 목차·요약 KoPub돋움 Medium 13
   ◆ KoPub돋움 Medium 13 / • KoPub바탕 Light 12 / - KoPub바탕 Light 11.5 / * KoPub바탕 Light 11 / 줄간격 160%
   장제목 KoPub돋움 Bold 20 / 가. 소제목 KoPub바탕 Bold 15 / 표제목 KoPub돋움 Bold 11 / 표안 KoPub돋움 10.5·단위 8 / 자료 8.5
   참고자료 구분 KoPub바탕 Medium 12 / 항목 KoPub바탕 Light 12"""
import re, sys, zipfile, os
from xml.sax.saxutils import escape

SRC, OUT = sys.argv[1], sys.argv[2]
TITLE = sys.argv[3] if len(sys.argv) > 3 else "여성 창업 테크기업 성공 사례 조사"
SUBTITLE = sys.argv[4] if len(sys.argv) > 4 else ""
AUTHORS = ["○ ○ ○ 연구위원 (연락처 / 이메일@kosi.re.kr)"]

PAGE_W, PAGE_H = 61228, 85889           # 샘플 양식 용지(216×303mm)
ML, MR, MT, MB = 6803, 6803, 6519, 4251  # 좌우 24mm
TEXT_W = PAGE_W - ML - MR

FONTS = ["KoPub돋움체 Bold", "KoPub돋움체 Medium", "KoPub돋움체 Light", "KoPub바탕체 Bold", "KoPub바탕체 Medium", "KoPub바탕체 Light"]
# charPr: (font idx, size pt, bold, color)
CHAR = {
    "body": (5, 12, 0, "#000000"), "title": (0, 20, 1, "#000000"), "subtitle": (1, 13, 0, "#000000"), "author": (1, 10.5, 0, "#000000"),
    "l1": (1, 13, 0, "#000000"), "l2": (5, 12, 0, "#000000"), "l3": (5, 11.5, 0, "#000000"), "l4": (5, 11, 0, "#000000"),
    "chap": (0, 20, 1, "#1F5C5C"), "sub": (3, 15, 1, "#000000"), "tbltitle": (0, 11, 1, "#000000"), "tblnote": (2, 8.5, 0, "#000000"),
    "tblhead": (1, 10, 0, "#000000"), "tblbody": (2, 10, 0, "#000000"), "refhead": (4, 12, 0, "#000000"), "ref": (5, 12, 0, "#000000"),
    "toc": (1, 13, 0, "#000000"), "sumhead": (0, 20, 1, "#1F5C5C"), "date": (2, 10, 0, "#000000"),
}
CID = {k: i for i, k in enumerate(CHAR)}
# paraPr: (align, left, intent, prev, next, linespacing%, pageBreakBefore, keepWithNext)
PARA = {
    "body": ("JUSTIFY", 0, 0, 0, 0, 160, 0, 0), "center": ("CENTER", 0, 0, 0, 0, 160, 0, 0), "right": ("RIGHT", 0, 0, 0, 0, 130, 0, 0),
    "l1": ("JUSTIFY", 1900, -1900, 700, 0, 160, 0, 1), "l2": ("JUSTIFY", 3300, -1400, 250, 0, 160, 0, 0),
    "l3": ("JUSTIFY", 4500, -1200, 150, 0, 160, 0, 0), "l4": ("JUSTIFY", 5700, -1200, 150, 0, 160, 0, 0),
    "chap": ("LEFT", 0, 0, 0, 1200, 160, 1, 1), "chapfirst": ("LEFT", 0, 0, 0, 1200, 160, 0, 1), "sub": ("LEFT", 0, 0, 1400, 500, 160, 0, 1),
    "tbltitle": ("CENTER", 0, 0, 900, 200, 150, 0, 1), "tblnote": ("LEFT", 0, 0, 100, 600, 130, 0, 0),
    "cell": ("CENTER", 0, 0, 0, 0, 130, 0, 0), "cellleft": ("LEFT", 0, 0, 0, 0, 130, 0, 0),
    "ref": ("JUSTIFY", 2000, -2000, 0, 0, 150, 0, 0), "refhead": ("LEFT", 0, 0, 800, 200, 150, 0, 1),
    "toc": ("LEFT", 1200, 0, 200, 0, 170, 0, 0), "tocsub": ("LEFT", 3000, 0, 0, 0, 170, 0, 0),
    "title": ("LEFT", 0, 0, 6000, 1500, 150, 0, 0),
}
PID = {k: i for i, k in enumerate(PARA)}


def t(s):
    s = s.replace("\\~", "~").replace("\\[", "[").replace("\\]", "]")
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return escape(s)


# ---------------- header.xml ----------------
def header_xml():
    ff = "".join(f'<hh:fontface lang="{lang}" fontCnt="{len(FONTS)}">' + "".join(
        f'<hh:font id="{i}" face="{escape(f)}" type="TTF" isEmbedded="0"/>' for i, f in enumerate(FONTS)) + "</hh:fontface>"
        for lang in ["HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER"])
    def bf(i, line, fill=None):
        b = f'<hh:{{}}Border type="{line}" width="0.12 mm" color="#000000"/>'
        fillx = f'<hc:fillBrush><hc:winBrush faceColor="{fill}" hatchColor="#000000" alpha="0"/></hc:fillBrush>' if fill else ""
        return (f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
                f'<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
                + "".join(b.format(side) for side in ["left", "right", "top", "bottom"]) +
                f'<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{fillx}</hh:borderFill>')
    bfs = bf(1, "NONE") + bf(2, "NONE") + bf(3, "SOLID") + bf(4, "SOLID", "#E8EEEE") + bf(5, "NONE", "#F3F6F6")
    cps = ""
    for k, (fi, sz, bold, col) in CHAR.items():
        cps += (f'<hh:charPr id="{CID[k]}" height="{int(sz*100)}" textColor="{col}" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">'
                f'<hh:fontRef hangul="{fi}" latin="{fi}" hanja="{fi}" japanese="{fi}" other="{fi}" symbol="{fi}" user="{fi}"/>'
                '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
                '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
                '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
                '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
                + ("<hh:bold/>" if bold else "") + "</hh:charPr>")
    pps = ""
    for k, (al, left, intent, prev, nxt, ls, pb, kwn) in PARA.items():
        margin = (f'<hh:margin><hc:intent value="{intent}" unit="HWPUNIT"/><hc:left value="{left}" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/>'
                  f'<hc:prev value="{prev}" unit="HWPUNIT"/><hc:next value="{nxt}" unit="HWPUNIT"/></hh:margin>'
                  f'<hh:lineSpacing type="PERCENT" value="{ls}" unit="HWPUNIT"/>')
        pps += (f'<hh:paraPr id="{PID[k]}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="0" suppressLineNumbers="0" checked="0">'
                f'<hh:align horizontal="{al}" vertical="BASELINE"/><hh:heading type="NONE" idRef="0" level="0"/>'
                f'<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="0" keepWithNext="{kwn}" keepLines="0" pageBreakBefore="{pb}" lineWrap="BREAK"/>'
                '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
                f'<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">{margin}</hp:case><hp:default>{margin}</hp:default></hp:switch>'
                '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" version="1.4" secCnt="1">'
            '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/><hh:refList>'
            f'<hh:fontfaces itemCnt="7">{ff}</hh:fontfaces><hh:borderFills itemCnt="5">{bfs}</hh:borderFills>'
            f'<hh:charProperties itemCnt="{len(CHAR)}">{cps}</hh:charProperties>'
            '<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>'
            '<hh:numberings itemCnt="1"><hh:numbering id="1" start="0">'
            + "".join(f'<hh:paraHead start="1" level="{i}" align="LEFT" useInstWidth="1" autoIndent="1" widthAdjust="0" textOffsetType="PERCENT" textOffset="50" numFormat="DIGIT" charPrIDRef="4294967295" checkable="0">^{i}.</hh:paraHead>' for i in range(1, 8))
            + '</hh:numbering></hh:numberings>'
            f'<hh:paraProperties itemCnt="{len(PARA)}">{pps}</hh:paraProperties>'
            '<hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles>'
            '</hh:refList><hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument>'
            '<hh:docOption><hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/></hh:docOption><hh:trackchageConfig flag="0"/></hh:head>')


# ---------------- section0.xml ----------------
pid = [0]


def para(text, c="body", p="body", extra=""):
    pid[0] += 1
    return (f'<hp:p id="{pid[0]}" paraPrIDRef="{PID[p]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{CID[c]}">{extra}<hp:t>{t(text)}</hp:t></hp:run></hp:p>')


def secpr():
    note = ('<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
            '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/><hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
            '<hp:numbering type="CONTINUOUS" newNum="1"/>')
    pbf = "".join(f'<hp:pageBorderFill type="{x}" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"><hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill>' for x in ["BOTH", "EVEN", "ODD"])
    return ('<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">'
            '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/><hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
            f'<hp:pagePr landscape="WIDELY" width="{PAGE_W}" height="{PAGE_H}" gutterType="LEFT_ONLY"><hp:margin header="4252" footer="4252" gutter="0" left="{ML}" right="{MR}" top="{MT}" bottom="{MB}"/></hp:pagePr>'
            f'<hp:footNotePr>{note}<hp:placement place="EACH_COLUMN" beneathText="0"/></hp:footNotePr><hp:endNotePr>{note}<hp:placement place="END_OF_DOCUMENT" beneathText="0"/></hp:endNotePr>{pbf}</hp:secPr>'
            '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>')


tblno = [0]


def table(rows, note_unit=None, source=None):
    """rows: list of list of str (첫 행 헤더). 열 너비는 글자 수 비례"""
    ncol = max(len(r) for r in rows); rows = [r + [""] * (ncol - len(r)) for r in rows]
    lens = [max(2, min(28, max(len(r[c]) for r in rows))) for c in range(ncol)]
    widths = [int(TEXT_W * l / sum(lens)) for l in lens]; widths[-1] += TEXT_W - sum(widths)
    tblno[0] += 1
    out = (f'<hp:tbl id="{1000+tblno[0]}" zOrder="{tblno[0]}" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="{len(rows)}" colCnt="{ncol}" cellSpacing="0" borderFillIDRef="3" noAdjust="0">'
           f'<hp:sz width="{TEXT_W}" widthRelTo="ABSOLUTE" height="{len(rows)*900}" heightRelTo="ABSOLUTE" protect="0"/>'
           '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
           '<hp:outMargin left="0" right="0" top="0" bottom="0"/><hp:inMargin left="283" right="283" top="141" bottom="141"/>')
    for ri, r in enumerate(rows):
        out += "<hp:tr>"
        for ci, cell in enumerate(r):
            head = ri == 0
            bfid = 4 if head else 3
            c = "tblhead" if head else "tblbody"
            p = "cell" if (head or ci > 0 and re.match(r"^[\d\.\,\%\-~\s/억원달러개명–]*$", cell or "x")) else "cellleft"
            if head: p = "cell"
            out += (f'<hp:tc name="" header="{1 if head else 0}" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="{bfid}">'
                    '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                    + para(cell, c, p) +
                    f'</hp:subList><hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
                    f'<hp:cellSz width="{widths[ci]}" height="900"/><hp:cellMargin left="283" right="283" top="141" bottom="141"/></hp:tc>')
        out += "</hp:tr>"
    out += "</hp:tbl>"
    pid[0] += 1
    res = ""
    if note_unit: res += para(note_unit, "tblnote", "right")
    res += f'<hp:p id="{pid[0]}" paraPrIDRef="{PID["center"]}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{CID["tblbody"]}">{out}</hp:run></hp:p>'
    if source: res += para(source, "tblnote", "tblnote")
    return res


# ---------------- Markdown 파싱 ----------------
lines = open(SRC, encoding="utf-8").read().split("\n")
blocks = []  # (kind, payload)
i = 0
while i < len(lines):
    l = lines[i]
    if l.startswith("| "):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            if not re.match(r"^\|\s*-+", lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
            i += 1
        blocks.append(("table", rows)); continue
    if l.startswith("## "): blocks.append(("h1", l[3:].strip()))
    elif l.startswith("### "): blocks.append(("h2", l[4:].strip()))
    elif l.startswith("# "): pass
    elif l.startswith("□ "): blocks.append(("l1", l[2:]))
    elif l.startswith("○ "): blocks.append(("l2", l[2:]))
    elif l.startswith("- "): blocks.append(("l3", l[2:]))
    elif l.startswith("* "): blocks.append(("l4", l[2:]))
    elif l.strip(): blocks.append(("text", l.strip()))
    i += 1

# 장·절 번호
h1s = [b[1] for b in blocks if b[0] == "h1"]
body = []
chap = 0; first_chap = True; tbl_counter = 0; in_ref = False
table_titles = {"비교군은": "여성기업 확인 기업과 비교군의 특성", "SIMS 기초분석 결과": "SIMS로 본 여성기업 확인 기업과 비교군의 단계별 지표",
                "요인별 정의": "ERIS 모델의 요인별 정의와 분석 항목", "100인 전체": "한국 여성 스타트업 대표 100인 명단(2022.8)",
                "20개사의 창업연도": "국내 심층 사례 20개사 개요", "데카콘": "해외 벤치마크 6개사 개요", "요인별 관찰": "20개 사례의 ERIS 요인별 관찰 결과", "요인별 진단": "요인별 정책 시사점 종합"}
last_text = ""
for kind, pay in blocks:
    if kind == "h1":
        if pay.startswith("참고 자료"):
            body.append(para("참고자료", "chap", "chap")); in_ref = True; continue
        chap += 1
        m = re.match(r"^\d+\.\s*(.*)$", pay); title = m.group(1) if m else pay
        body.append(para(f"{chap:02d}  {title}", "chap", "chapfirst" if first_chap else "chap")); first_chap = False
    elif kind == "h2":
        m = re.match(r"^\d+-(\d+)\.\s*(.*)$", pay)
        sub = "가나다라마바사"[int(m.group(1)) - 1] + ". " + m.group(2) if m else pay
        body.append(para(sub, "sub", "sub"))
    elif kind == "table":
        tbl_counter += 1
        title = next((v for k, v in table_titles.items() if k in last_text), "")
        unit = "(단위: %, 개)" if any("%" in c for r in pay for c in r) else None
        src = None
        if "100인" in title: src = "자료: 한경 긱스·스타트업얼라이언스, 한국 여성 스타트업 대표 100인(2022.8.10); 누적 투자액은 2022년 8월 기준"
        elif "SIMS" in title or "비교군" in title: src = "자료: 중소벤처기업연구원 SIMS 기초분석(기준일 2025-12-31; 특성·비교 지표는 2026년 2월 반출본). 표준화는 비교군을 여성기업 확인 기업의 업종×법인×업력 구성으로 재가중한 값"
        elif "ERIS 모델" in title: src = "자료: Sandberg & Hofer(1987), 한정화(2003)를 토대로 작성"
        elif "시사점" in title: src = "자료: 3장 사례 분석과 2장 SIMS 기초분석 결과를 토대로 작성"
        else: src = "자료: 각 사 공시·언론 보도를 토대로 작성"
        body.append(para(f"<표 {tbl_counter}> {title}", "tbltitle", "tbltitle"))
        body.append(table(pay, unit, src))
    elif in_ref:
        if kind == "l3" or kind == "l4": body.append(para(pay, "ref", "ref"))
        else: body.append(para(pay, "refhead", "refhead"))
    elif kind in ("l1", "l2", "l3", "l4"):
        mark = {"l1": "◆ ", "l2": "• ", "l3": "- ", "l4": "* "}[kind]
        body.append(para(mark + pay, kind, kind)); last_text = pay
    elif kind == "text":
        if re.match(r"^\w{3} \d+, \d{4}", pay): continue   # 작성일·작성자 줄 제외
        body.append(para(pay, "l2", "body")); last_text = pay

# ---------------- 표지·목차·요약 ----------------
SUMMARY = [
    ("l1", "본 조사는 여성 창업 테크기업 20개사의 성공 요인을 ERIS 모델로 분석하고, SIMS 여성기업 전체 지표와 대조하여 정책 시사점을 도출"),
    ("l2", "사례는 '한국 여성 스타트업 대표 100인' 명단 안팎에서 유니콘·IPO·M&A·100억 원 이상 투자·글로벌 진출 중 하나 이상을 충족한 20개사(상장 7, 유니콘 1, M&A 1, 성장 단계 11)"),
    ("l2", "SIMS에는 대표자 성별 변수가 없어 여성기업은 확인서 보유 기업(2025년 말 유효 91,110개)으로, 비교군은 중소기업확인서 유효·여성기업 미확인 기업(460,638개)으로 식별"),
    ("l1", "(SIMS) 여성기업은 기술업종 진입은 빠르나 혁신 인증·R&D·수출·규모 상향으로 이어지는 비율이 비교군보다 낮음"),
    ("l2", "설립 7년 미만 기술업종 비중 18.0% vs 13.0%로 진입은 앞서나, 벤처확인 4.4% vs 6.3%, 연구개발비 지출 6.3% vs 10.9%, 기술 분야 1개사당 지원금 평균 1.1억 vs 3.0억 원"),
    ("l2", "수출기업 비중 3.7% vs 5.8%(표준화), 소기업 → 중기업 전환 8.5% vs 13.6%로 생존이 아닌 성장 단계에서 격차가 발생"),
    ("l2", "인증 보유 기업 전체 중 여성확인기업 비중은 벤처 9.9%·이노비즈 6.8%로 여성기업 비중(40.2%)에 크게 못 미침"),
    ("l1", "(사례) 20개사의 성장은 창업가 경력·당사자 경험(E) → 전략적 자본(R) → 흑자·글로벌 전략(S)의 연결로, 위기는 자본시장·규제 변화(I) 이후 자원·전략의 동시 재구성 여부로 설명됨"),
    ("l2", "20개 중 15개가 금융·의료·연구·IT 등 직무 경력을 활용해 창업하였고, 회수 사례 다수가 시리즈C 이상에서 전략적 투자자·사모펀드를 확보"),
    ("l2", "성공 사례는 모두 적자 장기화·규제 도입·사고 등 위기를 경험했으며, 수익 구조 전환(컬리)·M&A(스타일쉐어·컴투스)·사모펀드 유치(메디포스트)·제도권 편입(뮤직카우·에잇퍼센트)으로 극복"),
    ("l2", "본 조사 사례의 절반은 VC 투자 통계 밖(상장·M&A·산업 자본)에서 확인되어, VC 통계만으로는 여성 창업 성공 사례가 과소 포착됨"),
    ("l1", "(시사점) 여성 테크창업 정책은 창업 건수 확대보다 성장 단계 진입과 위기 구간 통과를 지원하는 방향으로 재편 필요"),
    ("l2", "(R) 시리즈B 이상 투자 비중 2%의 성장 자본 공백에 대응해 대기업·금융그룹 전략적 투자와 모태펀드 여성 전용 계정을 연계한 후속 투자 매칭"),
    ("l2", "(I) 패션·뷰티·커머스 집중을 완화하기 위해 기본계획의 생활·문화 분야 육성에 AI·헬스케어·SaaS 트랙과 경력 전환형 창업 지원을 보완"),
    ("l2", "(S) 위기 극복 경로별 지원(M&A 매칭·세컨더리 펀드·사업 모델 전환 컨설팅)과, 지원 도달이 아닌 진입이 병목인 수출의 도달률 지표·저진입 경로 설계"),
    ("l2", "(E) 성공 창업자의 멘토링·엔젤투자 참여 인센티브와 여성 심사역 양성 프로그램 연계"),
]
cover = [para(TITLE, "title", "title")]
if SUBTITLE: cover.append(para(SUBTITLE, "subtitle", "body"))
for a in AUTHORS: cover.append(para(a, "author", "body"))
cover.append(para("", "body", "body"))
toc = [para("목차", "sumhead", "chapfirst")]
n = 0
for kind, pay in blocks:
    if kind == "h1":
        if pay.startswith("참고 자료"): toc.append(para("참고자료", "toc", "toc")); continue
        n += 1; m = re.match(r"^\d+\.\s*(.*)$", pay); toc.append(para(f"{n:02d}  {m.group(1) if m else pay}", "toc", "toc"))
    elif kind == "h2":
        m = re.match(r"^\d+-(\d+)\.\s*(.*)$", pay); toc.append(para("가나다라마바사"[int(m.group(1)) - 1] + ". " + m.group(2), "l2", "tocsub"))
summ = [para("요약", "sumhead", "chap")] + [para({"l1": "◆ ", "l2": "• "}[k] + s, k, k) for k, s in SUMMARY]

first = para("", "body", "body").replace('<hp:run charPrIDRef="0">', '<hp:run charPrIDRef="0">' + secpr(), 1)
section = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
           + first + "".join(cover) + "".join(toc) + "".join(summ) + "".join(body) + "</hs:sec>")

# ---------------- 패키징 ----------------
files = {
    "mimetype": "application/hwp+zip",
    "version.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" tagetApplication="WORDPROCESSOR" major="5" minor="0" micro="5" buildNumber="0" os="1" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="11, 0, 0, 1"/>',
    "META-INF/container.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf"><ocf:rootfiles><ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/></ocf:rootfiles></ocf:container>',
    "META-INF/manifest.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"><odf:file-entry odf:full-path="/" odf:media-type="application/hwp+zip"/><odf:file-entry odf:full-path="Contents/header.xml" odf:media-type="application/xml"/><odf:file-entry odf:full-path="Contents/section0.xml" odf:media-type="application/xml"/><odf:file-entry odf:full-path="settings.xml" odf:media-type="application/xml"/></odf:manifest>',
    "Contents/content.hpf": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><opf:package xmlns:opf="http://www.idpf.org/2007/opf/" version="" unique-identifier="" id="">'
                             f'<opf:metadata><opf:title>{escape(TITLE)}</opf:title><opf:language>ko</opf:language><opf:meta name="creator" content="text">중소벤처기업연구원</opf:meta></opf:metadata>'
                             '<opf:manifest><opf:item id="header" href="Contents/header.xml" media-type="application/xml"/><opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/><opf:item id="settings" href="settings.xml" media-type="application/xml"/></opf:manifest>'
                             '<opf:spine><opf:itemref idref="header" linear="yes"/><opf:itemref idref="section0" linear="yes"/></opf:spine></opf:package>'),
    "Contents/header.xml": header_xml(),
    "Contents/section0.xml": section,
    "settings.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"><ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/></ha:HWPApplicationSetting>',
}
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr(zipfile.ZipInfo("mimetype"), files["mimetype"], compress_type=zipfile.ZIP_STORED)
    for k, v in files.items():
        if k != "mimetype": zf.writestr(k, v)
print("written", OUT, "paragraphs", pid[0], "tables", tblno[0])
