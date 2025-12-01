
import os
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings


_index = None
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-exp-03-07")

def init_pinecone(index_name="pdf-index"):

    global _index
    if _index is not None:
        return _index

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    if "pdf-index" in pc.list_indexes().names():
        pc.delete_index("pdf-index")

    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

    _index = pc.Index(index_name)
    return _index



def process_message(username, message, index):
    combined_text = f"{username}: {message}"
    try:
        vector = embeddings.embed_query(combined_text)

        response = index.upsert(
            vectors=[
                {
                    "id": f"{username}_{hash(combined_text)}",
                    "values": vector,
                    "metadata": {
                        "username": username,
                        "message": message
                    }
                }
            ],
            namespace="pdf-namespace"
        )

        print(response)
        if response.get("upserted_count", 0) != 1:
            print("\nWarning: Upserted count was not 1")

    except Exception as e:
        print(f"Error during upsert: {e}")


def retrieve_context(prompt,index):
    query_vector = embeddings.embed_query(prompt)
    response = index.query(
        vector=query_vector,
        top_k=10,
        namespace="pdf-namespace",
        include_values=False,
        include_metadata=True
    )
    return response['matches']

def format_context(matches):
    if not matches:
        return "No relevant context found."

    formatted_parts = []
    for i, match in enumerate(matches, 1):
        metadata = match.get('metadata', {})
        score = match.get('score', 0)
        message = metadata.get('message', 'No message available').strip()
        username = metadata.get('username', 'Unknown user')

        context_piece = (
            f"[Context {i}] (Relevance: {score:.2f})\n"
            f"User: {username}\n"
            f"Message: {message}\n"
        )
        formatted_parts.append(context_piece)

    return "\n" + "=" * 50 + "\n" + "\n".join(formatted_parts) + "\n" + "=" * 50
