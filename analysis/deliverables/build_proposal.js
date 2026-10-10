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
  new TableRow({ children: [cell("신  청  일", W[0], { hdr: true }), cell("2026. 10. 00.", W[1]), cell("희 망 발 간 일", W[2], { hdr: true }), cell("2026. 12. (26-00호)", W[3]), cell("", W[4])] }),
  new TableRow({ children: [cell("중기부 관련 과", W[0], { hdr: true }), cell("정책분석평가과(안)", W[1]), cell("관련 담당자", W[2], { hdr: true }), cell("○○○ 사무관", W[3]), cell("", W[4])] }),
] });
const W2 = [1800, 8100]; const TOT2 = W2.reduce((a, b) => a + b, 0);
const row = (label, paras) => new TableRow({ children: [cell(label, W2[0], { hdr: true }), cell(paras, W2[1])] });
const t2 = new Table({ width: { size: TOT2, type: WidthType.DXA }, columnWidths: W2, rows: [
  new TableRow({ children: [cell("구  분", W2[0], { hdr: true }), cell("내       용", W2[1], { hdr: true })] }),
  row("제목(안)", [P("중앙부처 중소기업 지원사업의 지원목적·대상·수단·내용·산업 유형 분석", { bold: true, after: 20 }), P("— 문장 임베딩 기반 5축 분류와 지원 포트폴리오 진단(2024~2026년)", { after: 0, size: 20 })]),
  row("현안 및 배경", [
    L(0, "정책평가팀은 중소기업 지원사업 현황조사를 위해 열린재정의 세부사업별 「예산 및 기금운용계획 사업설명자료」를 전수 수집·파싱하여 사업정보 DB를 구축하였으며, 이 DB를 활용한 지원사업 구조 분석이 후속 과제"),
    L(1, "연 7,400~8,100개 세부사업 수집, 2024~2026년 중앙부처 내역사업 2,189건 구조화, 기업마당 공고 연계"),
    L(0, "중앙부처 중소기업 지원사업은 규모가 크나 부처별 사업목적 서술 방식이 달라 '무엇을 위한 지원인가'를 공통 기준으로 비교하기 어려움"),
    L(1, "23개 소관, 연 670~800건의 내역사업, 2026년 내역사업 예산 30.95조원"),
    L(0, "기존 정책디렉토리 지원분야 분류는 결측·포괄 항목이 많고 목적과 수단이 한 축에 혼재되어 포트폴리오 점검 기준으로 한계"),
    L(1, "2025년 이후분만 연계되어 내역사업의 36.0%(787건)가 미분류이고, '혼합(단독+공동)' 등 포괄 항목이 331건"),
    L(2, "수단 항목(융자)과 목적 항목(시장개척)이 같은 분류 축에 병렬 배치"),
    L(0, "사전협의·성과평가의 유사·중복 검토에는 목적·대상·수단·내용·산업을 함께 비교할 수 있는 다축 분류체계가 필요"),
    L(0, "AI 등 정책 테마 지원은 키워드 언급과 실제 지원을 구분하는 집계 기준이 없어 지원 규모가 과대평가될 우려"),
    L(0, "사전학습 언어모델 기반 문장 임베딩은 표현이 다른 동일 목적의 사업 서술을 공통 기준으로 재분류할 수 있어 추가 학습 없이 전 사업에 적용 가능")]),
  row("작성 목적", [
    L(0, "사업정보 DB의 구축 과정과 보유 항목을 제시하고, DB 활용 분석 사례로 지원사업 유형화를 수행"),
    L(0, "2024~2026년 중앙부처 내역사업 2,189건을 대상으로 지원목적·대상·수단·내용·산업 5개 축의 유형 분류체계를 도출"),
    L(1, "목적 서술이 일반 어휘에 그친 사업은 공고 지원내용·예산 산출근거로 분류하여 전 사업을 유형화"),
    L(1, "지원산업 축에서 AI 관여도(핵심·활용·언급)를 판정하여 AI 지원 규모를 수준별로 산정"),
    L(0, "유형별 예산 구조·추이와 소관별 특성을 진단하여 분류체계 개편·유사중복 검토·포트폴리오 점검의 정책과제를 제안")]),
  row("내  용", [
    L(0, "(서론) 연구 배경·목적, 분석자료와 방법"),
    L(1, "지원목적은 문장 임베딩(bge-m3) → 산업영역 방향 제거 → 기능어휘 결합 → 군집분석 → 해석적 병합, 지원대상·내용은 같은 임베딩·군집 절차, 지원수단은 지원형태 규칙, 지원산업은 산업 사전 규칙으로 유형화"),
    L(0, "(사업정보 DB 구축) 열린재정 사업설명자료 전수 수집 → 중소기업 지원사업 선별 → 세부·내역사업 2계층 파싱 → 기업마당 공고·정책디렉토리 연계 → 연도 간 일몰·이관 추적"),
    L(0, "(지원목적 유형 체계) 군집분석과 해석적 병합으로 대분류·중분류 체계를 도출하고, 목적 서술이 포괄적인 사업의 지원내용 기반 배정 방법과 신뢰도를 제시"),
    L(1, "군집 수는 연도 간 배정 일치율·실루엣·최소 군집 크기로 결정하고, 재군집 안정성(ARI)과 기존 분류와의 정합성으로 타당성 검증"),
    L(0, "(유형별 규모와 추이) 유형별 예산 비중과 2024~2026년 증감을 분석하여 비중이 크거나 작은 유형과 신설·급증 유형을 식별"),
    L(1, "융자·보증 재원을 제외한 순지원 기준을 병행하여, 예산 총액 기준과 결론이 같은지 확인"),
    L(1, "내역 통합·이관 등 예산서 구조 변화에 따른 유형 간 이동을 연속성 정보로 구분하여 실질 증감을 해석"),
    L(0, "(지원대상·수단·내용 유형) 축별 유형 체계와 타당성 지표를 제시하고, 지원목적과의 교차 및 4축 조합을 분석"),
    L(1, "목적·대상·수단·내용 조합이 같은 사업군을 1차 유사중복 검토 모집단으로 제시하고, 조합 내 문서 유사도로 실질적 중복 후보를 압축하는 절차 제안"),
    L(0, "(지원산업 유형과 AI) 산업 분야 분류와 AI 관여도를 판정하고, 관여도 수준별 AI 지원 규모와 운영 소관 추이를 분석"),
    L(1, "'AI 언급' 사업 포함 여부에 따른 집계 차이를 비교하여 관여도 기준 집계 방식 제안"),
    L(0, "(소관별 구조와 분류체계 비교) 소관별 특화 구조와 다부처 운영 영역, 기존 지원분야 분류와의 교차, 어휘 임베딩(LSA) 결과와의 교차 검증"),
    L(0, "(시사점 및 정책과제) 분류체계 개편과 표본 검증을 전제로 한 자동 분류, 사업목적 서술 기준, 유사중복 검토 제도화, 포트폴리오 정기 점검 방향")]),
  row("기대효과", [
    L(0, "부처 간 상이한 사업 서술을 공통 기준으로 비교 가능하게 하여 중소기업 지원사업 통합관리·사전협의·성과평가의 유사중복 검토 모집단과 후보 압축 절차 제공"),
    L(0, "기존 지원분야 분류의 결측·포괄 항목을 보완하는 자동 분류 절차와 '목적·대상·수단·내용·산업' 5축 분류 기준 제시"),
    L(0, "총액·순지원 기준의 유형별 예산 비중·추이 등 포트폴리오 진단 지표를 제공하여 중소기업 지원 기본계획과 예산 편성의 근거자료로 활용"),
    L(0, "AI 등 정책 테마 지원의 관여도별 집계 기준을 마련하여 정부 AI 지원 규모 산정과 성과관리의 근거로 활용")]),
  row("기타", [
    L(0, "정책평가팀이 구축한 중소기업 지원사업 정보 DB(열린재정 사업설명자료 파싱, 중앙부처·지자체 세부·내역사업, 기업마당 공고 연계)와 공개 분석 도구(bge-m3, scikit-learn, kiwipiepy) 활용"),
    L(0, "전년도 정책연구 '중소기업 지원사업 사전협의·성과평가' 수행 결과와 연계하여 유형별 검토 사례 보강 예정")]),
] });
const doc = new Document({ numbering, styles: { default: { document: { run: { font: B, size: 22 } } } },
  sections: [{ properties: { page: { margin: { top: 1200, bottom: 1200, left: 1300, right: 1300 } } }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 300 }, children: [t("중소기업 이슈n 포커스 제안서(2026년 10월)", { font: D, size: 32, bold: true })] }),
    new Paragraph({ spacing: { before: 120, after: 120 }, children: [t("• 제안자", { font: D, size: 24, bold: true })] }), t1,
    new Paragraph({ spacing: { before: 360, after: 120 }, children: [t("• 주요 내용", { font: D, size: 24, bold: true })] }), t2,
  ] }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync("KOSI_이슈n포커스_제안서_지원사업유형분석.docx", b); console.log("proposal written", b.length); });
