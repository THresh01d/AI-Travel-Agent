import chromadb
from chromadb.utils import embedding_functions
from .spots_data import spots_descriptions

client = chromadb.PersistentClient(path="./chroma_data")

embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="./local_model/BAAI/bge-small-zh-v1___5"
)

collection = client.get_or_create_collection(
    name="travel_spots",
    embedding_function=embed_fn,
)


def init_knowledge_base():
    """首次启动时把景点数据存入 ChromaDB（自动跳过重复的）"""
    
    # 检查是否已经存过
    if collection.count() > 0:
        print(f"知识库已有 {collection.count()} 条记录，跳过初始化")
        return
    
    # 逐条存入
    docs = []
    ids = []
    metadatas = []
    
    for i, spot in enumerate(spots_descriptions):
        docs.append(spot["description"])
        ids.append(str(i))
        metadatas.append({
            "city": spot["city"],
            "name": spot["name"],
            "type": spot["type"],
        })
    
    collection.add(documents=docs, ids=ids, metadatas=metadatas)
    print(f"知识库初始化完成，共 {len(docs)} 条")


def search_spots(query: str, top_k: int = 3) -> tuple[str, str]:
    """用用户查询搜索最相关景点，返回拼接好的文本"""
    
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )
    
    # results 结构：{ids, distances, metadatas, documents}
    spots_text = []
    
    inferred_city = None
    
    for i in range(len(results["ids"][0])):
        city = results["metadatas"][0][i]["city"]
        name = results["metadatas"][0][i]["name"]
        desc = results["documents"][0][i]
        
        # 第一个结果的城市作为推断城市
        if inferred_city is None:
            inferred_city = city
        
        spots_text.append(f"【{city} · {name}】{desc}")
    
    return "\n\n".join(spots_text), inferred_city
