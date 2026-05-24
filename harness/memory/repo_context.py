
from typing import List, Dict
from harness.config import get_settings

settings = get_settings()
embedder = None
qdrant = None

def _clients():
    global embedder, qdrant
    if embedder is None or qdrant is None:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        qdrant = QdrantClient(url=settings.qdrant_url)
    return embedder, qdrant

def init_collection(repo_name: str):
    from qdrant_client.models import Distance, VectorParams
    _, client = _clients()
    if not client.collection_exists(repo_name):
        client.create_collection(
            collection_name=repo_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

def index_snippets(repo_name: str, snippets: List[Dict[str, str]]):
    init_collection(repo_name)
    from qdrant_client.models import PointStruct
    model, client = _clients()
    points = []
    for i, s in enumerate(snippets):
        vec = model.encode(s["text"]).tolist()
        points.append(PointStruct(id=i, vector=vec, payload=s))
    client.upsert(collection_name=repo_name, points=points)

def search_snippets(repo_name: str, query: str, top_k: int = 5) -> List[Dict]:
    model, client = _clients()
    vec = model.encode(query).tolist()
    results = client.search(collection_name=repo_name, query_vector=vec, limit=top_k)
    return [r.payload for r in results]
