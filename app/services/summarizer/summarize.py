
from langchain_community.document_loaders import PyPDFLoader

from ..summarizer.llm import summary_chain_prompt




def summarize_pdf(pdf_path):
    docs = extract_text_from_pdf(pdf_path)
    summary = summary_chain_prompt(docs)
    return summary["output_text"]



def extract_text_from_pdf(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load_and_split()
    return docs
