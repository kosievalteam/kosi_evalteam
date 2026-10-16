# -*- coding: utf-8 -*-
"""미뤄뒀던 SIMS 재분석 일괄 실행 (F:/여성기업정책/sims_work/w.duckdb 가 있는 PC에서 실행)
   사용: python run_all.py  → 같은 폴더에 a3_growth_v2.out, a4_survival.out 저장"""
import subprocess, sys, pathlib, time
here = pathlib.Path(__file__).parent
for name in ["a3_growth_v2", "a4_survival"]:
    out = here / f"{name}.out"; t = time.time()
    print(f"[{name}] 실행 중 ...", flush=True)
    with open(out, "w", encoding="utf-8") as f:
        r = subprocess.run([sys.executable, "-X", "utf8", str(here / f"{name}.py")], stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    print(f"[{name}] 종료코드 {r.returncode}, {time.time()-t:,.0f}초 → {out}", flush=True)
