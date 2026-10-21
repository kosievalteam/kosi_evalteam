const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, BorderStyle, ShadingType, VerticalAlign, LevelFormat } = require("docx");
const D = "KoPub돋움체", B = "KoPub바탕체"; const HEAD = "E8F3F1";
const t = (text, o = {}) => new TextRun({ text, font: o.font || B, size: o.size || 22, bold: !!o.bold, color: o.color });
const P = (text, o = {}) => new Paragraph({ children: [t(text, o)], spacing: { before: 0, after: o.after ?? 60, line: 320 }, alignment: o.align });
const L = (level, text) => new Paragraph({ numbering: { reference: "prop", level }, spacing: { before: 0, after: 40, line: 320 }, children: [t(text, { size: level === 0 ? 21 : 20 })] });
const border = { style: BorderStyle.SINGLE, size: 6, color: "000000" };
const cell = (children, w, o = {}) => new TableCell({ width: { size: w, type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER, shading: o.hdr ? { type: ShadingType.CLEAR, fill: HEAD, color: "auto" } : undefined,
  margins: { top: 60, bottom: 60, left: 100, right: 100 }, borders: { top: border, bottom: border, left: border, right: border }, columnSpan: o.span, children: Array.isArray(children) ? children : [P(children, { bold: !!o.hdr, align: o.hdr ? AlignmentType.CENTER : undefined, after: 0, size: 21 })] });
const numbering = { config: [{ reference: "prop", levels: [
  { level: 0, format: LevelFormat.BULLET, text: "○", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 300, hanging: 300 } } } },
  { level: 1, format: LevelFormat.BULLET, text: "-", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 240 } } } },
  { level: 2, format: LevelFormat.BULLET, text: "*", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 880, hanging: 220 } } } }] }] };
const W = [1700, 2400, 1700, 2400, 1700]; const TOT = W.reduce((a, b) => a + b, 0);
const t1 = new Table({ width: { size: TOT, type: WidthType.DXA }, columnWidths: W, rows: [
  new TableRow({ children: [cell("제안자 소속", W[0], { hdr: true }), cell("중소벤처기업연구원 정책평가팀", W[1]), cell("성      명", W[2], { hdr: true }), cell("○ ○ ○ (연구위원)", W[3]), cell("", W[4])] }),
  new TableRow({ children: [cell("신  청  일", W[0], { hdr: true }), cell("2026. 10. 00.", W[1]), cell("희 망 발 간 일", W[2], { hdr: true }), cell("2027. 00. (27-00호)", W[3]), cell("", W[4])] }),
  new TableRow({ children: [cell("중기부 관련 과", W[0], { hdr: true }), cell("정책분석평가과(안)", W[1]), cell("관련 담당자", W[2], { hdr: true }), cell("○○○ 사무관", W[3]), cell("", W[4])] }),
] });
const W2 = [1800, 8100]; const TOT2 = W2.reduce((a, b) => a + b, 0);
const row = (label, paras) => new TableRow({ children: [cell(label, W2[0], { hdr: true }), cell(paras, W2[1])] });
const t2 = new Table({ width: { size: TOT2, type: WidthType.DXA }, columnWidths: W2, rows: [
  new TableRow({ children: [cell("구  분", W2[0], { hdr: true }), cell("내       용", W2[1], { hdr: true })] }),
  row("제목(안)", [P("중소기업 AI 지원사업의 규모와 구조 진단", { bold: true, after: 20 }), P("— AI 관여도와 예산 산출근거로 본 실제 규모(2024~2026년)", { after: 0, size: 20 })]),
  row("현안 및 배경", [
    L(0, "정부는 AI 전환(AX)을 핵심 정책 과제로 추진하고 있으며, 중소기업 지원사업에서도 AI 관련 사업이 빠르게 늘고 있음"),
    L(1, "직전 호(「중소기업 지원사업 유형화로 본 지원구조와 시사점」)에서 AI 지원(핵심+활용)은 2026년 1.83조원으로 2년 사이 2.5배 증가하고, 운영 소관은 6개에서 12개로 확대"),
    L(0, "AI 지원 규모는 집계 기준에 따라 크게 달라져 정책 판단의 근거로 쓰기 어려움"),
    L(1, "'AI 언급' 사업까지 포함하면 6.88조원으로, 관여도 기준의 3.8배"),
    L(1, "AI가 지원 항목의 일부인 '활용' 사업도 사업 예산 전체가 집계되어, AI에 실제로 배정된 예산은 확인되지 않음"),
    L(2, "예산서 산출근거에 AI 항목이 'AI트랙 포함' 등으로만 기재되어 금액이 구분되지 않는 사업이 다수"),
    L(0, "AI 지원이 기술개발·실증·도입·인력 중 어디에 배분되는지, 부처 간 역할 분담이 적절한지에 대한 진단이 부족"),
    L(1, "AI 응용제품 신속 상용화 지원사업은 6개 부처가 분야별로 운영하며, AI 바우처·AX 바우처 등 유사한 방식의 지원도 여러 부처에 분산")]),
  row("작성 목적", [
    L(0, "중소기업 AI 지원사업의 실제 규모를 예산 산출근거 단위로 추정하여 하한~상한 범위로 제시"),
    L(0, "AI 지원을 기술개발, 실증·상용화, 도입·활용(AX), 인력·교육, 인프라·데이터, 창업·기업육성으로 구분하여 배분 구조를 진단"),
    L(0, "부처 간 분담과 중복을 점검하여 AI 지원 집계 기준과 사업 설계의 개선 과제를 제안")]),
  row("내  용", [
    L(0, "(1장 서론) 연구 배경·목적, 분석 대상과 방법"),
    L(1, "대상: 중앙부처 중소기업 지원 내역사업 중 AI 관여도 핵심·활용 사업(2024~2026년)"),
    L(1, "방법: 직전 호의 유형화 결과와 AI 관여도 판정을 바탕으로 사업별 전수 검토, 예산 산출근거의 AI 항목 분해"),
    L(0, "(2장 AI 지원사업의 범위와 규모) 관여도 판정 기준과 검토 결과, 집계 기준별 규모(키워드·관여도·산출근거 항목), 연도별 추이"),
    L(1, "연도별 서술을 기준으로 관여도를 판정하여, 특정 연도에 AI 항목이 없는 사업의 포함 여부를 구분"),
    L(0, "(3장 AI 지원의 구조) AI 지원 유형별 배분, 지원대상·수단과의 관계, 소관별 분담과 다부처 사업군"),
    L(1, "중소기업의 AI 도입·활용(AX) 지원 규모와 기술개발·실증 지원의 균형을 진단"),
    L(0, "(4장 시사점 및 정책과제) AI 지원 집계 기준의 표준화, 예산서 AI 항목의 구분 기재, 중소기업 AX 지원 방향, 다부처 사업군의 역할 분담"),
    L(0, "(부록) AI 사업별 검토표, 관여도 판정 기준")]),
  row("기대효과", [
    L(0, "정부 중소기업 AI 지원 규모를 기준별로 일관되게 산정하는 방법을 제시하여 정책 보고와 예산 심의의 근거로 활용"),
    L(0, "AI 지원의 단계별 배분 진단으로 중소기업 AX 정책의 우선순위 설정 근거 제공"),
    L(0, "예산서 사업설명자료의 AI 항목 구분 기재 등 작성 지침 개선 근거 제공")]),
  row("기타", [
    L(0, "직전 호의 중소기업 지원사업 정보 DB와 유형화 결과를 활용하며, 사업별 전수 검토 결과는 검토표로 함께 제공"),
    L(0, "필요 시 소관 부처 확인을 거쳐 AI 항목 금액을 보완")]),
] });
const doc = new Document({ numbering, styles: { default: { document: { run: { font: B, size: 22 } } } },
  sections: [{ properties: { page: { margin: { top: 1200, bottom: 1200, left: 1300, right: 1300 } } }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 300 }, children: [t("중소기업 이슈n 포커스 제안서(2026년 10월, 후속 호)", { font: D, size: 32, bold: true })] }),
    new Paragraph({ spacing: { before: 120, after: 120 }, children: [t("• 제안자", { font: D, size: 24, bold: true })] }), t1,
    new Paragraph({ spacing: { before: 360, after: 120 }, children: [t("• 주요 내용", { font: D, size: 24, bold: true })] }), t2,
  ] }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync("KOSI_이슈n포커스_제안서_AI지원사업.docx", b); console.log("proposal written", b.length); });
