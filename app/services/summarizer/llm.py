
import os
from ollama import Client
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.chains.summarize import load_summarize_chain
from ..summarizer.pinecone import retrieve_context,format_context
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser


ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client = Client(host=ollama_host)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    timeout=60,
    max_retries=3,
)

def summary_chain_prompt(docs):
    chain = load_summarize_chain(llm,chain_type="map_reduce")
    summary = chain.invoke(docs)
    return summary



def contextual_prompt(query,index):
    print(f"/ask {query}")
    context = retrieve_context(query,index)
    formatted_context =format_context(context)
    template = f"""
    You are a QA assistant specializing in summarizing user activities from Slack workspace conversations. The context provided will include messages with usernames and their message texts.

    Your task is to:
    - Understand the query regarding a specific user or task.
    - Analyze the provided context carefully.
    - Provide a clear, concise summary directly related to the user or task mentioned in the query.
    - Focus only on relevant actions, status updates, or decisions—avoid unnecessary details.
    - Do not give me bullet points just return short description of answer.

    Context:
    {formatted_context}

    Query:
    {query}

    Summary:
    """
    prompt = ChatPromptTemplate.from_template(template)
    rag_chain = prompt | llm | StrOutputParser()
    response = rag_chain.invoke({"context": formatted_context, "input": query})
    return response.strip()
