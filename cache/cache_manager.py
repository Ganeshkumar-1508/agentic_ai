import uuid
import chromadb
from chromadb.utils import embedding_functions

# Embedding model
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Persistent ChromaDB client
client = chromadb.PersistentClient(path="./cache/chroma_cache")

# Collection
collection = client.get_or_create_collection(
    name="qa_cache",
    embedding_function=embedding_function
)


def get_from_cache(question: str, threshold: float = 0.35):
    """
    Compare question embedding with stored question embeddings
    Return cached answer if similarity is within threshold
    """

    results = collection.query(
        query_texts=[question],
        n_results=1
    )
    # print("cache count:",collection.count())
    # Safety checks
    # If there is no matched question or no answer or no similarity score,
    # do not use cache
    if (
        not results
        or not results.get("documents")
        or not results["documents"][0]
        or not results.get("metadatas")
        or not results["metadatas"][0]
        or not results.get("distances")
        or not results["distances"][0]
    ):
        return None

    distance = results["distances"][0][0]

    if distance < threshold:
        return results["metadatas"][0][0]["answer"]

    return None


def store_in_cache(question: str, answer: str):
    """
    Store question as document (embedded)
    Store answer as metadata (plain text)
    Persistence is handled automatically by PersistentClient
    """

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[question],
        metadatas=[{
            "answer": answer
        }]
    )


def delete_from_cache(question: str):
    """
    Delete the closest matched cached entry for the given question
    """

    results = collection.query(
        query_texts=[question],
        n_results=1
    )

    if results.get("ids") and results["ids"][0]:
        collection.delete(ids=results["ids"][0])


