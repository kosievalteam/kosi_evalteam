import re, sys
from hwpx import HwpxDocument

src, out = sys.argv[1], sys.argv[2]
lines = open(src, encoding='utf-8').read().split('\n')
doc = HwpxDocument.new()
doc.set_page_margins(left=8504, right=8504, top=5669, bottom=4252)  # 30/30/20/15mm (HWPUNIT)

BODY, HEAD = '함초롬바탕', '함초롬돋움'
S = {
 'title': doc.ensure_run_style(bold=True, font=HEAD, size=18),
 'meta':  doc.ensure_run_style(font=BODY, size=11),
 'h2':    doc.ensure_run_style(bold=True, font=HEAD, size=15, color='#1F3864'),
 'sq':    doc.ensure_run_style(bold=True, font=BODY, size=14),
 'ci':    doc.ensure_run_style(font=BODY, size=13),
 'da':    doc.ensure_run_style(font=BODY, size=12),
 'st':    doc.ensure_run_style(font=BODY, size=11),
 'th':    doc.ensure_run_style(bold=True, font=HEAD, size=10),
 'td':    doc.ensure_run_style(font=HEAD, size=10),
 'code':  doc.ensure_run_style(font=HEAD, size=10),
}

def para(text, style, **fmt):
    doc.add_paragraph(text, char_pr_id_ref=S[style])
    idx = len(doc.paragraphs) - 1
    if fmt:
        doc.set_paragraph_format(paragraph_index=idx, **fmt)

def cells(row):
    return [c.strip() for c in row.strip().strip('|').split('|')]

def table(rows, mono=False):
    hdr = cells(rows[0]); body = [cells(r) for r in rows[2:]]
    data = [hdr] + body
    nr, nc = len(data), len(hdr)
    t = doc.add_table(nr, nc, width=42520, char_pr_id_ref=S['td'])  # 150mm
    for i, r in enumerate(data):
        for j in range(nc):
            v = r[j] if j < len(r) else ''
            t.cell(i, j).set_text(v, preserve_format=True)
            for p in t.cell(i, j).paragraphs:
                for run in p.runs:
                    run.char_pr_id_ref = S['th'] if i == 0 else S['td']
        if i == 0:
            for j in range(nc):
                t.set_cell_shading(0, j, '#D9E2F3')
    w = [min(max(len(r[j]) if j < len(r) else 0 for r in data), 60) + 4 for j in range(nc)]
    w = [max(x, 10) for x in w]
    t.set_column_widths(w)
    t.element.set('repeatHeader', '1')
    para('', 'st')

def box(text_lines):
    t = doc.add_table(1, 1, width=42520, char_pr_id_ref=S['code'])
    t.cell(0, 0).set_text('\n'.join(text_lines), preserve_format=True, split_paragraphs=True)
    for p in t.cell(0, 0).paragraphs:
        for run in p.runs:
            run.char_pr_id_ref = S['code']
    para('', 'st')

i = 0
first_h2 = True
while i < len(lines):
    ln = lines[i]; s = ln.strip()
    if s.startswith('```'):
        j = i + 1; buf = []
        while not lines[j].strip().startswith('```'):
            buf.append(lines[j].strip()); j += 1
        box(buf); i = j + 1; continue
    if s.startswith('|'):
        j = i; buf = []
        while j < len(lines) and lines[j].strip().startswith('|'):
            buf.append(lines[j]); j += 1
        table(buf); i = j; continue
    if not s or s == '---':
        i += 1; continue
    if s.startswith('# '):
        para(s[2:], 'title', alignment='CENTER', spacing_after_pt=6)
    elif s.startswith('## '):
        para(s[3:], 'h2', spacing_before_pt=4 if first_h2 else 14, spacing_after_pt=4,
             keep_with_next=True, bottom_border=True, border_color='#1F3864',
             page_break_before=(not first_h2 and s[3:].startswith(('Ⅰ', '붙임'))))
        first_h2 = False
    elif s.startswith('작성:'):
        para(s, 'meta', alignment='RIGHT', spacing_after_pt=10)
    elif s.startswith('□'):
        para(s, 'sq', indent_left_mm=4, first_line_indent_mm=-4, spacing_before_pt=10,
             spacing_after_pt=3, line_spacing_percent=160)
    elif s.startswith('○'):
        para(s, 'ci', indent_left_mm=8, first_line_indent_mm=-4, spacing_before_pt=5,
             line_spacing_percent=160)
    elif s.startswith('- '):
        para(s, 'da', indent_left_mm=12, first_line_indent_mm=-3, line_spacing_percent=160)
    elif s.startswith('* '):
        para('*' + s[1:], 'st', indent_left_mm=15, first_line_indent_mm=-3, line_spacing_percent=150)
    else:
        para(s, 'da', line_spacing_percent=160)
    i += 1

doc.set_page_number(format='- page -') if False else doc.set_page_number()
doc.save_to_path(out)
print('saved', out)
