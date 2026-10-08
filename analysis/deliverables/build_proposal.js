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
  row("제목(안)", [P("중앙부처 중소기업 지원사업의 지원목적·대상·수단·내용 유형 분석", { bold: true, after: 20 }), P("— 문장 임베딩 기반 4축 분류와 지원 포트폴리오 진단(2024~2026년)", { after: 0, size: 20 })]),
  row("현안 및 배경", [
    L(0, "정책평가팀은 중소기업 지원사업 현황조사를 위해 열린재정의 세부사업별 「예산 및 기금운용계획 사업설명자료」(연 7,400~8,100개)를 전수 수집·파싱하여 중소기업 지원사업 정보 DB를 구축(2024~2026년 중앙부처 내역사업 2,189건, 기업마당 공고 연계). 이 DB를 활용한 지원사업 구조 분석이 후속 과제"),
    L(0, "중앙부처 중소기업 지원사업은 23개 소관, 연 670~800건의 내역사업(2026년 예산 30.95조원)으로 운영되나 부처별 사업목적 서술이 달라 '무엇을 위한 지원인가'를 공통 기준으로 비교하기 어려움"),
    L(0, "정책디렉토리의 지원분야 분류는 2025년 이후에만 연계되어 내역사업의 36%(787건)가 결측이고 '혼합(단독+공동)' 등 포괄 항목이 331건에 달하며, 수단 항목(융자)과 목적 항목(시장개척)이 한 축에 혼재"),
    L(0, "사전협의·성과평가의 유사·중복 검토와 포트폴리오 점검에는 목적·대상·수단·내용을 함께 비교할 수 있는 다축 분류체계가 필요"),
    L(0, "사전학습 언어모델(bge-m3) 기반 문장 임베딩은 표현이 다른 동일 목적의 사업 서술을 공통 기준으로 재분류할 수 있어, 추가 학습 없이 전 사업에 적용 가능")]),
  row("작성 목적", [
    L(0, "열린재정 사업설명자료 기반 중소기업 지원사업 정보 DB의 구축 과정과 보유 항목을 제시하고, DB를 활용한 분석 사례로 지원사업 유형화를 수행"),
    L(0, "2024~2026년 중앙부처 내역사업 2,189건의 사업목적·내용과 기업마당 공고 지원내용을 임베딩·군집분석하여 지원목적 유형(8개 대분류·23개 중분류)을 도출하고, 목적 서술이 포괄적인 사업은 지원내용(공고·예산 산출근거)으로 분류하여 전수 유형화. 여기에 지원대상(10개)·지원수단(9개)·지원내용(11개) 유형을 더한 4축 분류체계를 제시"),
    L(0, "유형별 예산 구조와 2024~2026년 추이, 소관별 특성, 축 간 관계를 분석하여 분류체계 개편·유사중복 검토·포트폴리오 점검의 정책과제를 제안")]),
  row("내  용", [
    L(0, "(서론) 배경·목적, 분석자료와 방법(문장 임베딩 → 산업영역 방향 제거 → 기능어휘 결합 → 군집 → 해석적 병합)"),
    L(0, "(사업정보 DB 구축) 열린재정 사업설명자료 전수 수집(연 7,400~8,100개 세부사업) → 중소기업 지원사업 선별(400~470개) → 세부·내역사업 2계층 파싱(내역사업 796·722·671건) → 기업마당 공고·정책디렉토리 연계 → 연도 간 일몰·이관 추적"),
    L(0, "(지원목적 유형 체계) 8개 대분류·23개 중분류, 목적 서술이 일반 어휘에 그친 265건(12.1%)의 지원내용 기반 배정 방법과 신뢰도(교차검증 대분류 정확도 93.0%, 저신뢰 82.6%)"),
    L(0, "(유형별 규모와 추이) 2026년 자금조달·경영안정 지원 48.0%, 기술혁신 촉진 19.2%, 고용·노동환경 9.1% 등 포트폴리오 구조와 급증·축소 유형, 융자·보증 재원을 제외한 순지원 기준 민감도"),
    L(1, "해외시장 진출 +390%, 기술사업화·기술이전 +79%, 환경·에너지 설비 전환 +76% 증가; 원천·핵심기술 개발 △30%, 정책자금 융자 △10% 감소; 소상공인경영안정바우처(5,790억원) 신설로 경영비용 보전형 지원 등장"),
    L(0, "(지원대상·수단·내용 유형) 대상은 중소·중견기업 일반 24.0%·소상공인 15.4%·산학연 15.3%·보증·보험 이용기업 13.3%, 수단은 융자 38.0%·R&D 출연 18.1%·보증 15.5%, 내용은 자금 융자·보증 제공 47.5%·기술개발 과제 12.3%; 축별 타당성 지표, 목적×수단·대상·내용 교차와 4축 조합(313개, 1차 유사중복 검토 모집단 110개 조합) 분석"),
    L(0, "(소관별 구조와 분류체계 비교) 소관별 특화 구조, 다부처 운영 영역(창업·벤처 육성 12개 소관, 수출 마케팅 4개 부처, 범부처 협업형 AI 응용제품 신속 상용화 6개 부처 등), 기존 지원분야 분류와의 교차, 어휘 임베딩(LSA) 결과와의 교차 검증"),
    L(0, "(시사점 및 정책과제) 분류체계의 4축 개편과 임베딩 기반 자동 분류, 사업목적 서술 기준 마련, 4축 기반 유사중복 검토 제도화, 포트폴리오 정기 점검, 급증 유형의 성과지표 공통화")]),
  row("기대효과", [
    L(0, "부처 간 상이한 사업 서술을 공통 기준으로 비교 가능하게 하여, 중소기업 지원사업 통합관리·사전협의·성과평가의 유사중복 검토 모집단 제공"),
    L(0, "기존 지원분야 분류의 결측(36%)·포괄 항목을 보완하는 자동 분류 절차와 '목적·대상·수단·내용' 4축 분류 기준 제시"),
    L(0, "자금조달 편중(48%, 융자·보증 재원 제외 순지원 기준 병행)·역량형 지원 과소(5.0%) 등 포트폴리오 진단 지표를 제공하여 중소기업 지원 기본계획과 예산 편성의 근거자료로 활용")]),
  row("기타", [
    L(0, "정책평가팀이 구축한 중소기업 지원사업 정보 DB(열린재정 사업설명자료 파싱, 중앙부처·지자체 세부·내역사업, 기업마당 공고 연계)와 공개 분석 코드(bge-m3, scikit-learn, kiwipiepy) 활용"),
    L(0, "전년도 정책연구 '중소기업 지원사업 사전협의·성과평가' 수행 결과와 연계하여 유형별 검토 사례 보강 예정")]),
] });
const doc = new Document({ numbering, styles: { default: { document: { run: { font: B, size: 22 } } } },
  sections: [{ properties: { page: { margin: { top: 1200, bottom: 1200, left: 1300, right: 1300 } } }, children: [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 300 }, children: [t("중소기업 이슈n 포커스 제안서(2026년 10월)", { font: D, size: 32, bold: true })] }),
    new Paragraph({ spacing: { before: 120, after: 120 }, children: [t("• 제안자", { font: D, size: 24, bold: true })] }), t1,
    new Paragraph({ spacing: { before: 360, after: 120 }, children: [t("• 주요 내용", { font: D, size: 24, bold: true })] }), t2,
  ] }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync("KOSI_이슈n포커스_제안서_지원사업유형분석.docx", b); console.log("proposal written", b.length); });
