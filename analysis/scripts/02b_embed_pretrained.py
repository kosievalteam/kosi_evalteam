"""사전학습 문장 임베딩 (교체 가능 백엔드) + 지원목적 축 투영.
사용 예:
  python scripts/02b_embed_pretrained.py --backend st --model BAAI/bge-m3            # 로컬 추론(sentence-transformers)
  python scripts/02b_embed_pretrained.py --backend st --model intfloat/multilingual-e5-large
  python scripts/02b_embed_pretrained.py --backend openai --model text-embedding-3-large  # OPENAI_API_KEY 필요
  python scripts/02b_embed_pretrained.py --from-npy data/emb_w2v.npy                       # 기존 임베딩에 영역 방향 제거만 적용
출력: data/emb_<name>.npy (원 임베딩), data/emb_<name>_fn.npy (산업영역 방향 제거본)
  <name> = 모델명의 마지막 경로 요소 소문자 (예: bge-m3, multilingual-e5-large, text-embedding-3-large)
필요 네트워크: st → huggingface.co, cdn-lfs.hf.co, cdn-lfs-us-1.hf.co / openai → api.openai.com
  ※ huggingface_hub 의 Xet 백엔드(cas-server.xethub.hf.co)가 막힌 환경에서는 HF_HUB_DISABLE_XET=1 로 실행 (아래에서 기본 설정)
"""
import os, sys, argparse, json, numpy as np, pandas as pd
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")   # cdn-lfs 경로로 내려받기 (Xet 서버 차단 환경 대응)
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--backend", choices=["st", "openai"], default="st")
ap.add_argument("--model", default="BAAI/bge-m3")
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--max-chars", type=int, default=1500)
ap.add_argument("--domain-dims", type=int, default=12, help="제거할 산업영역 판별 방향 수")
ap.add_argument("--from-npy", default=None, help="이미 계산된 임베딩(.npy)에 영역 방향 제거만 적용 (모델 호출 생략)")
args = ap.parse_args()
name = os.path.basename(args.from_npy).replace("emb_", "").replace(".npy", "") if args.from_npy else args.model.split("/")[-1].lower()
df = pd.read_parquet("data/corpus.parquet")
docs = [d[: args.max_chars] for d in df.doc]

def embed_st(texts):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(args.model, device="cpu")
    kw = {}
    if "e5" in args.model: texts = ["query: " + t for t in texts]      # e5 계열 권장 접두어
    return m.encode(texts, batch_size=args.batch, normalize_embeddings=True, show_progress_bar=True, **kw)

def embed_openai(texts):
    from openai import OpenAI
    cli = OpenAI(); out = []
    for i in range(0, len(texts), 64):
        r = cli.embeddings.create(model=args.model, input=texts[i:i + 64]); out += [e.embedding for e in r.data]
        print(f"{i + len(r.data)}/{len(texts)}", end="\r")
    E = np.array(out, dtype=np.float32); return E / np.linalg.norm(E, axis=1, keepdims=True)

if args.from_npy:
    E = np.load(args.from_npy)
else:
    E = embed_st(docs) if args.backend == "st" else embed_openai(docs)
    E = np.asarray(E, dtype=np.float32); np.save(f"data/emb_{name}.npy", E); print("\nsaved", f"data/emb_{name}.npy", E.shape)

# ---- 지원목적 축: 산업영역(지원산업·소관) 판별 방향을 제거(선형 투영)하여 '무슨 목적'이 군집을 주도하도록 조정
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.preprocessing import normalize
raw = pd.read_csv("data/biz_central_2024_2026.csv").set_index("id")
def collapse(s, min_n=15):
    s = s.fillna("NA"); vc = s.value_counts(); return s.where(s.map(vc) >= min_n, "기타")
dom = (collapse(df.id.map(raw["지원산업"])) + "|" + collapse(df["소관"])).values
mask = ~pd.Series(dom).str.startswith("NA").values
lda = LDA(n_components=min(args.domain_dims, len(set(dom[mask])) - 1), solver="eigen", shrinkage="auto").fit(E[mask], dom[mask])
W = lda.scalings_[:, : lda.n_components]; Q, _ = np.linalg.qr(W)          # 영역 판별 방향 직교기저
Efn = normalize(E - (E @ Q) @ Q.T); np.save(f"data/emb_{name}_fn.npy", Efn)
json.dump(dict(model=args.model, backend=args.backend, dim=int(E.shape[1]), domain_dims=int(Q.shape[1])), open(f"data/emb_{name}_meta.json", "w"), ensure_ascii=False, indent=1)
print("saved", f"data/emb_{name}_fn.npy", "(영역 방향", Q.shape[1], "개 제거)")
