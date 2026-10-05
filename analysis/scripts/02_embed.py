"""임베딩 생성: (a) TF-IDF→LSA, (b) 단어벡터(spaCy ko_core_news_lg floret) TF-IDF 가중평균, (c) 결합.
출력: data/emb_lsa.npy, data/emb_w2v.npy, data/emb_hyb.npy, data/tfidf_vocab.json
"""
import json, numpy as np, pandas as pd, spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

df = pd.read_parquet("data/corpus.parquet")
docs = [" ".join(t) for t in df.tokens]
tf = TfidfVectorizer(tokenizer=str.split, preprocessor=None, lowercase=False, token_pattern=None,
                     ngram_range=(1, 2), min_df=3, max_df=0.4, sublinear_tf=True)
X = tf.fit_transform(docs); vocab = np.array(tf.get_feature_names_out())
print("tfidf", X.shape)

svd = TruncatedSVD(n_components=200, random_state=0); L = svd.fit_transform(X)
print("LSA explained var %.3f" % svd.explained_variance_ratio_.sum())
emb_lsa = normalize(L)

nlp = spacy.load("ko_core_news_lg", exclude=["parser", "ner", "tagger", "lemmatizer", "attribute_ruler", "morphologizer"])
uni = [i for i, v in enumerate(vocab) if " " not in v]
V = np.vstack([nlp.vocab[vocab[i]].vector for i in uni])           # floret: 어떤 문자열도 서브워드로 벡터화
Xu = X[:, uni]
W = Xu @ V
den = np.asarray(Xu.sum(axis=1)).ravel(); den[den == 0] = 1
emb_w2v = normalize(W / den[:, None])
print("w2v", emb_w2v.shape, "zero-vec docs", int((np.abs(W).sum(1) == 0).sum()))

emb_hyb = normalize(np.hstack([emb_lsa, emb_w2v]))
np.save("data/emb_lsa.npy", emb_lsa); np.save("data/emb_w2v.npy", emb_w2v); np.save("data/emb_hyb.npy", emb_hyb)
import scipy.sparse as sp; sp.save_npz("data/tfidf.npz", X.tocsr()); json.dump(list(vocab), open("data/tfidf_vocab.json", "w"), ensure_ascii=False)
print("saved")
