"""Supabase MCP(execute_sql) 결과 파일(JSON 래퍼) → CSV 변환.
사용: python 00_parse_mcp_dump.py <결과파일> <출력csv>
"""
import json, re, sys, pandas as pd
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
outer = json.loads(s)["result"]
m = re.search(r"<untrusted-data-[0-9a-f-]+>\n(.*)\n</untrusted-data-", outer, re.S)
rows = json.loads(m.group(1))
df = pd.DataFrame(rows)
df.to_csv(dst, index=False, encoding="utf-8-sig")
print(dst, df.shape); print(df.dtypes.to_string()[:1500])
