import chromadb
from chromadb.utils import embedding_functions

# 用 ChromaDB 自带的 embedding（基于 ONNX，比 sentence-transformers 轻量得多）
print("正在加载模型...")
embed_fn = embedding_functions.DefaultEmbeddingFunction()

# 三个句子
sentences = [
    "成都有大熊猫繁育研究基地，适合亲子游",
    "重庆火锅很有名，洪崖洞夜景很美",
    "大熊猫很可爱，可以去熊猫基地看它们",
]

# 生成向量
embeddings = embed_fn(sentences)

print(f"向量维度: {len(embeddings[0])}")

# 手动算余弦相似度
import numpy as np

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

sim_0_1 = cosine_sim(embeddings[0], embeddings[1])
sim_0_2 = cosine_sim(embeddings[0], embeddings[2])
sim_1_2 = cosine_sim(embeddings[1], embeddings[2])

print(f"句子0(成都熊猫) vs 句子1(重庆火锅): {sim_0_1:.4f}  ← 不相关，低")
print(f"句子0(成都熊猫) vs 句子2(大熊猫):   {sim_0_2:.4f}  ← 都关于熊猫，高")
print(f"句子1(重庆火锅) vs 句子2(大熊猫):   {sim_1_2:.4f}  ← 不相关，低")
