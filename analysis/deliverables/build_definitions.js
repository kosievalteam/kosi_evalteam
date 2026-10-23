// 중앙부처 중소기업 지원사업 유형 정의서(docx) 생성. 수치·대표 사업은 output_bge-m3/definition_stats.json(scripts/15)에서 읽음
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel, PageBreak, LevelFormat, BorderStyle, ShadingType, VerticalAlign, PageOrientation, Footer, PageNumber } = require("docx");
const { AX, MAJ, MID, TGT, INS, CON, IND, AIL } = require("./defs_data");
const ST = JSON.parse(fs.readFileSync(__dirname + "/../output_bge-m3/definition_stats.json", "utf8"));
const D = "KoPub돋움체", B = "KoPub바탕체", TEAL = "1D6B6B", LIGHT = "E8F3F1", HEAD = "2F6F7E";
const sp = (before = 0, after = 0) => ({ before, after, line: 360 });
const t = (text, o = {}) => new TextRun({ text, font: o.font || B, size: o.size || 22, bold: !!o.bold, color: o.color });
const P = (text, o = {}) => new Paragraph({ alignment: o.align, spacing: o.spacing || sp(0, 60), children: [t(text, o)] });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: sp(240, 160), border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL } }, children: [t(text, { font: D, size: 32, bold: true, color: TEAL })] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: sp(200, 100), children: [t(text, { font: D, size: 25, bold: true, color: HEAD })] });
const L = (level, text) => new Paragraph({ numbering: { reference: "def", level }, spacing: sp(0, 30), children: [t(text, { size: [22, 21, 20, 19][level], bold: level === 0 })] });
const CAP = (text) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: sp(160, 60), children: [t(text, { font: D, size: 21, bold: true })] });
const NOTE = (lines) => lines.map((s, i) => new Paragraph({ spacing: { before: 0, after: i === lines.length - 1 ? 140 : 0, line: 260 }, indent: { left: 160 }, children: [t(s, { font: D, size: 16, color: "444444" })] }));
const BR = () => new Paragraph({ children: [new PageBreak()] });
const border = { style: BorderStyle.SINGLE, size: 4, color: "9AA8A6" };
function TBL(headers, rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, w, hdr, i, shade) => new TableCell({ width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: hdr ? { type: ShadingType.CLEAR, fill: HEAD, color: "auto" } : (shade || (i === 0 && o.firstColShade) ? { type: ShadingType.CLEAR, fill: LIGHT, color: "auto" } : undefined),
    margins: { top: 50, bottom: 50, left: 80, right: 80 }, borders: { top: border, bottom: border, left: border, right: border },
    children: String(text).split("\n").map(line => new Paragraph({ alignment: hdr || (o.center || []).includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT, spacing: { before: 0, after: 0, line: 250 },
      children: [t(line, { font: D, size: o.size || 17, bold: hdr || (i === 0 && o.boldFirst), color: hdr ? "FFFFFF" : undefined })] })) });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, alignment: AlignmentType.CENTER,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true, i)) }),
      ...rows.map(r => new TableRow({ cantSplit: true, children: r.cells.map((c, i) => cell(c, widths[i], false, i, r.shade)) }))] });
}
const numbering = { config: [{ reference: "def", levels: [
  { level: 0, format: LevelFormat.BULLET, text: "□", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 340, hanging: 340 } } } },
  { level: 1, format: LevelFormat.BULLET, text: "○", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 640, hanging: 300 } } } },
  { level: 2, format: LevelFormat.BULLET, text: "-", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 920, hanging: 240 } } } },
  { level: 3, format: LevelFormat.BULLET, text: "*", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1180, hanging: 220 } } } }] }] };

// ---------- 통계 조회 ----------
const stat = (axis, code) => { const d = ST[axis]; const k = Object.keys(d).find(k => k === code || k.startsWith(code + " ") || k.startsWith(code + ".")); return k ? d[k] : null; };
const scale = (axis, code) => { const s = stat(axis, code); return s ? `${s.n26}건\n${s.b26.toFixed(2)}조원\n(${s.sh.toFixed(1)}%)` : "-"; };
const exs = (axis, code, n = 2) => { const s = stat(axis, code); return s ? s.ex.slice(0, n).join("\n") : "-"; };
// 유형 표 공통: 코드·명칭 | 정의 | 판정 기준·단서 | 경계·유의 | 대표 사업 | 2026 규모
const W6 = [2350, 3450, 3000, 2650, 2188, 800];
const H6 = ["코드·유형명", "정  의", "판정 기준·단서", "경계·유의 사항", "대표 사업(2026년 예산 상위)", "2026 규모"];
const typeTable = (axis, defs) => TBL(H6, defs.map(([code, name, def, crit, bnd]) => ({ cells: [`${code}\n${name}`, def, crit, bnd, exs(axis, code), scale(axis, code)] })), W6, { boldFirst: true, center: [5], firstColShade: true });
const sumNote = (axis) => { const tot = Object.values(ST[axis]).reduce((a, s) => a + s.n26, 0); return `* 주: 2026년 규모는 내역사업 ${tot}건·${ST._meta.budget_jo}조원 기준 건수·예산·비중, 대표 사업은 해당 유형의 2026년 내역예산 상위 사업`; };

// ---------- 표지·개요 ----------
const cover = [
  new Paragraph({ spacing: sp(1600, 200), alignment: AlignmentType.CENTER, children: [t("중앙부처 중소기업 지원사업", { font: D, size: 40, bold: true, color: TEAL })] }),
  new Paragraph({ spacing: sp(0, 400), alignment: AlignmentType.CENTER, children: [t("유형 정의서", { font: D, size: 52, bold: true })] }),
  new Paragraph({ spacing: sp(0, 1400), alignment: AlignmentType.CENTER, children: [t("지원목적 · 지원대상 · 지원수단 · 지원내용 · 지원산업 · AI 관여도", { font: D, size: 26, color: "444444" })] }),
  P("2026. 10.", { align: AlignmentType.CENTER, font: D, size: 24 }),
  P("중소벤처기업연구원 정책평가팀", { align: AlignmentType.CENTER, font: D, size: 26, bold: true }),
  BR(),
];
const overview = [
  H1("Ⅰ. 개요"),
  L(0, "본 정의서는 중앙부처 중소기업 지원 내역사업의 유형화 기준을 정리한 것으로, 기준별 판정 방법과 유형별 정의·판정 단서·경계를 명시하여 유형화의 일관성과 재현성을 확보하기 위한 것임"),
  L(1, "유형의 명칭과 구성은 임베딩 군집 결과를 바탕으로 전문가 자문을 거쳐 확정"),
  L(1, "(적용 단위) 예산서 내역사업. 동일 내역사업은 연도별 판정을 종합하여 연도 간 단일 유형으로 배정"),
  L(1, `(적용 범위) 2024~2026년 중앙부처 내역사업 ${ST._meta.n_all.toLocaleString()}건(23개 소관), 2026년 ${ST._meta.n}건·${ST._meta.budget_jo}조원`),
  L(1, "(활용) 사업정보 DB 등록 시 유형 기재, 사전협의·성과평가의 유사중복 검토 모집단 구성, 유형별 예산 포트폴리오 점검"),
  L(0, "여섯 가지 기준은 서로 독립적으로 판정하며, 같은 사업이라도 기준마다 다른 질문에 답함"),
  L(1, "지원목적은 '왜', 지원수단은 '어떤 재정 방식으로', 지원내용은 '수혜자가 무엇을 받는가'를 구분하므로, 같은 융자라도 목적에 따라 다른 목적 유형에 배정"),
  L(2, "지원수단이 같아도 사업 서술의 목적에 따라 지원목적 유형이 갈림"),
  L(3, "창업기반지원(융자)은 운전자금 성격으로 D1, 농식품글로벌육성지원자금(융자)은 수출업체 육성으로 C1, 신재생에너지 생산및시설자금(융자)은 설비 전환으로 E2"),
  L(1, "정책 테마 관여도는 지원산업 유형화의 하위 지표로 판정하나 테마별 집계에 별도로 쓰이므로 독립 기준으로 정의하며, 본 정의서는 정책 테마 중 AI를 대표 사례로 수록"),
  CAP("<표 1> 유형화 기준 개관"),
  TBL(["구  분", "질  문", "정  의", "원천 정보", "판정 방법", "유형 수", "배정"], AX.map(r => ({ cells: r })), [1500, 2000, 2400, 3000, 3138, 1300, 1100], { boldFirst: true, center: [5, 6], firstColShade: true, size: 18 }),
  ...NOTE(["* 주: 원천 정보는 열린재정 사업설명자료 파싱 DB와 기업마당 공고 연계 정보. 지원목적의 군집 수 k는 연도 간 일치율·실루엣·최소 군집 크기로 선정"]),
  L(0, "공통 원칙"),
  L(1, "(코드 체계) 기준별 문자 + 일련번호(지원목적 A~H 대분류·A1~H2 중분류, 대상 T, 수단 I, 내용 K, 산업 S). 원천 정보가 없으면 0번 코드(T0·I0·K0), 특정 산업이 없으면 S0"),
  L(1, "(명칭 원칙) 지원목적은 '목적 서술어 + (수단)' 형식으로 명명하여 목적과 수단을 구분"),
  L(1, "(신뢰도 표시) 분류기·규칙의 확신도가 낮은 배정(지원목적의 지원내용 기반 배정 중 확률 0.5 미만)은 저신뢰로 표시하여 담당자 확인 대상으로 관리"),
  L(1, "(갱신) 매년 예산서 반영 시 신규 사업을 같은 기준으로 판정하고, 기존 유형에 대응하지 않는 사업이 누적되면 유형 신설을 검토"),
  BR(),
];

// ---------- ① 지원목적 ----------
const purpose = [
  H1("Ⅱ. 지원목적 유형"),
  L(0, "지원목적은 '사업이 달성하려는 정책 목적'으로, 8개 대분류·23개 중분류로 구성"),
  L(1, "(원천 정보) 내역사업명 + 내역목적(없으면 세부목적의 해당 내역 구간) + 수혜대상 + 공고 지원내용을 결합한 목적 문서"),
  L(1, "(판정 방법) 문장 임베딩(bge-m3)에서 산업·소관 판별 방향을 제거하고 수단 어휘를 결합한 뒤 K-평균(k=24)으로 군집하여 중분류로 명명·병합(명칭과 병합 결과는 전문가 자문으로 확정)"),
  L(2, "동일 내역사업은 연도별 임베딩 평균의 최근접 군집으로 단일 유형에 배정"),
  L(2, "보정규칙: R1(목적 군집이 B·C·D·E가 아닌 융자 사업 → D1), R2(보증·팩토링·대위변제 사업 → D2)"),
  L(1, "(지원내용 기반 배정) 목적 서술이 '산업 육성·생태계 조성·활성화' 등 일반 어휘에 그쳐 목적 군집이 형성되지 않은 사업은 지원내용 문서(사업명·공고 지원내용·산출근거·수혜대상·지원형태)를 분류기로 판정"),
  L(2, "확률 0.5 미만은 저신뢰로 표시하고, 소상공인 대상 비용부담 경감·손실보상 사업은 D3로 배정(내용 명시 규칙)"),
  L(1, "(경계 원칙) 목적과 수단을 분리하여 판정: 융자·보조 등 수단은 목적 판정의 근거로 쓰지 않으며, 같은 수단이라도 서술된 목적에 따라 배정"),
  CAP("<표 2> 지원목적 대분류 정의"),
  TBL(["코드", "대분류", "정  의", "포함 중분류", "2026 규모"], MAJ.map(([c, n, d, m]) => ({ cells: [c, n, d, m, scale("대분류", c)] })), [800, 3000, 6838, 2600, 1200], { boldFirst: true, center: [0, 3, 4], firstColShade: true, size: 18 }),
  ...NOTE([sumNote("대분류")]),
  CAP("<표 3> 지원목적 중분류 정의"),
  TBL(H6, MID.map(([code, name, def, crit, bnd]) => ({ shade: false, cells: [`${code}\n${name}`, def, crit, bnd, exs("중분류", code), scale("중분류", code)] })), W6, { boldFirst: true, center: [5], firstColShade: true }),
  ...NOTE([sumNote("중분류")]),
  BR(),
];

// ---------- ② 지원대상 ----------
const target = [
  H1("Ⅲ. 지원대상 유형"),
  L(0, "지원대상은 '예산서에 기재된 직접 수혜 주체'로, 10개 유형과 미기재(T0)로 구성"),
  L(1, "(원천 정보) 예산서 '수혜대상' 필드(평균 20자 내외의 명사구)"),
  L(1, "(판정 방법) 수혜대상 문장 임베딩 → K-평균(k=16) → 해석적 병합(10개) → 보정규칙(T8 중 보증·보험 명시 사업을 T10으로 분리)"),
  L(1, "(구조) 기업 계층형(T1~T4), 비기업 주체형(T5~T7, T9), 매개형(T8·T10)"),
  L(1, "(경계 원칙) 예산서 기재를 그대로 따르며, 간접 지원 사업의 최종 수혜 기업은 추정하지 않음"),
  L(2, "중기부 창업 사업도 수혜대상이 '중소기업'으로 기재되면 T1로 배정되므로, 창업 지원 규모는 지원목적 B와 함께 판단"),
  CAP("<표 4> 지원대상 유형 정의"),
  typeTable("대상유형", TGT), ...NOTE([sumNote("대상유형")]),
  BR(),
];

// ---------- ③ 지원수단 ----------
const instrument = [
  H1("Ⅳ. 지원수단 유형"),
  L(0, "지원수단은 '예산이 수혜자에게 전달되는 재정 방식'으로, 9개 유형과 미기재(I0)로 구성"),
  L(1, "(원천 정보) 예산서 '지원형태'(출연·보조·직접·융자·출자)와 사업명·목적·공고의 수단 어휘(보증·팩토링, 바우처, 장려금·인건비, 기술개발)"),
  L(1, "(판정 방법) 지원형태는 범주형이므로 군집 대신 아래 우선순위 규칙을 위에서부터 적용하여 처음 충족하는 유형에 배정"),
  L(2, "① 융자 → I4, ② 보증·팩토링 → I8, ③ 바우처 → I9, ④ 직접+장려금(목적 G) → I5, ⑤ 출연+보조·직접 → I6"),
  L(2, "⑥ 출연+R&D → I1, ⑦ 출연 → I2, ⑧ 보조 → I3, ⑨ 직접 → I10, ⑩ 미기재 → I0"),
  L(1, "(구조) 금융형(I4·I8), 재정지원형(I1·I2·I3·I9), 직접형(I5·I10), 혼합형(I6)"),
  L(1, "(경계 원칙) 투자·출자(I7)는 지원형태 '출자' 단독 사업이 1건에 그쳐 독립 유형으로 두지 않고 해당 사업의 다른 지원형태로 판정"),
  CAP("<표 5> 지원수단 유형 정의"),
  typeTable("수단유형", INS), ...NOTE([sumNote("수단유형") + ". 규칙 번호는 우선순위 규칙의 적용 순서"]),
  BR(),
];

// ---------- ④ 지원내용 ----------
const content = [
  H1("Ⅴ. 지원내용 유형"),
  L(0, "지원내용은 '수혜자가 실제로 받는 지원 항목'으로, 11개 유형과 미기재(K0)로 구성"),
  L(1, "(원천 정보) 기업마당 공고 지원내용(없으면 내역목적·세부목적)"),
  L(1, "(판정 방법) 지원내용 문장 임베딩에서 산업·소관 판별 방향을 제거한 뒤 K-평균(k=16) → 해석적 병합(11개)"),
  L(1, "(구조) 자금 전달형(K4·K5·K7·K10), 과제·기반형(K1·K2·K11), 서비스형(K3·K6·K8·K9)"),
  L(1, "(경계 원칙) 비용을 보조하는지(K7), 서비스를 현물로 제공하는지(K8)를 구분하고, 공고가 없는 사업은 예산서 서술 수준에 따라 유형이 달라질 수 있음을 유의"),
  CAP("<표 6> 지원내용 유형 정의"),
  typeTable("내용유형", CON), ...NOTE([sumNote("내용유형")]),
  BR(),
];

// ---------- ⑤ 지원산업 ----------
const industry = [
  H1("Ⅵ. 지원산업 유형"),
  L(0, "지원산업은 '지원이 겨냥하는 기술·산업 영역'으로, 10개 산업 유형과 업종 공통(S0)으로 구성"),
  L(1, "(원천 정보) 사업명·내역목적·공고 지원내용·예산 산출근거와 DB '지원산업' 필드"),
  L(1, "(판정 방법) 유형별 산업 사전(핵심어 6~25개)으로 점수를 매겨 복수 태그와 주(主) 산업을 부여"),
  L(2, "점수 = 사업명 핵심어 3점 + 본문 출현 1점씩(최대 4점, 서로 다른 핵심어 2개 이상일 때만 2점 초과) + DB 필드 일치 2점"),
  L(2, "3점 이상이면 태그를 부여하고 최고점 산업을 주 산업으로 하며, 태그가 없으면 S0. 동일 내역사업은 연도별 점수 평균으로 판정"),
  L(1, "(경계 원칙) 주 산업은 단일 배정(합계 100%), 태그는 복수 배정(중복 집계)으로 구분하여 보고"),
  CAP("<표 7> 지원산업 유형 정의"),
  typeTable("지원산업(주)", IND), ...NOTE([sumNote("지원산업(주)") + ". 규모는 주 산업 기준"]),
  BR(),
];

// ---------- ⑥ AI 관여도 ----------
const ai = [
  H1("Ⅶ. AI 관여도"),
  L(0, "AI 관여도는 '사업 안에서 AI가 차지하는 위상'으로, 핵심·활용·언급·없음의 4단계로 구성"),
  L(1, "(원천 정보) 사업명·내역목적·공고 지원내용·예산 산출근거"),
  L(1, "(판정 방법) AI 어휘(AI·AX·인공지능·생성형·머신러닝·딥러닝·LLM 등)와 적용 맥락 어휘의 출현으로 연도별 단계를 판정하고, 내역사업 단위로 연도 중 최고 단계를 부여"),
  L(1, "(집계 원칙) 'AI 지원'은 핵심+활용으로 집계하고 언급은 제외하며, 집계 시 관여도 기준을 명시"),
  L(2, "언급 사업까지 포함하면 2026년 AI 지원 규모가 핵심+활용 기준의 3.8배로 부풀려짐"),
  CAP("<표 8> AI 관여도 단계 정의"),
  TBL(["단계", "정  의", "판정 기준", "유의 사항", "대표 사업(2026년 예산 상위)", "2026 규모"], AIL.map(([k, nm, def, crit, bnd]) => ({ cells: [nm, def, crit, bnd, exs("AI관여도", k), scale("AI관여도", k)] })), [1800, 3200, 3700, 2600, 2338, 800], { boldFirst: true, center: [0, 5], firstColShade: true }),
  ...NOTE([sumNote("AI관여도")]),
];

const doc = new Document({ numbering, styles: { default: { document: { run: { font: B, size: 22 } } } },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE }, margin: { top: 1000, bottom: 1000, left: 1200, right: 1200 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: D, size: 18 })] })] }) },
    children: [...cover, ...overview, ...purpose, ...target, ...instrument, ...content, ...industry, ...ai] }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(__dirname + "/KOSI_지원사업_유형정의서.docx", b); console.log("written", b.length); });
