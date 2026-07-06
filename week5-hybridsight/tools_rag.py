import os
from langchain_core.tools import tool
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# --------------------------------------------------
# Embedding Model
# --------------------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# Chroma Vector Store
# --------------------------------------------------

vectorstore = Chroma(
    persist_directory="./chroma_store",
    embedding_function=embeddings
)


# --------------------------------------------------
# Text Splitter
# --------------------------------------------------

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150
)

documents_loaded = False

# --------------------------------------------------
# PDF Indexing
# --------------------------------------------------

def index_documents(pdf_paths: list[str]) -> str:
    """
    Clears the current Chroma collection and indexes
    all uploaded PDF documents
    """

    global vectorstore
    global documents_loaded
    
    # Remove previous collection
    try:
        vectorstore.delete_collection()
    except Exception:
        pass

    # Recreate empty collection
    vectorstore = Chroma(
        persist_directory="./chroma_store",
        embedding_function=embeddings
    )

    documents = []

    for pdf in pdf_paths:
        loader = PyPDFLoader(pdf)
        docs = loader.load()

        for doc in docs:
            doc.metadata["source"] = os.path.basename(doc.metadata["source"])
        
        documents.extend(docs)

    chunks = splitter.split_documents(documents)

    vectorstore.add_documents(chunks)

    documents_loaded = True

    return f"Successfully indexed {len(pdf_paths)} PDF(s) into {len(chunks)} searchable chunks."


# --------------------------------------------------
# Clear Documents
# --------------------------------------------------

def clear_documents():
    global vectorstore
    global documents_loaded

    try:
        vectorstore.delete_collection()
    except Exception:
        pass

    vectorstore = Chroma(
        persist_directory="./chroma_store",
        embedding_function=embeddings
    )

    documents_loaded = False

    return "All uploaded documents have been cleared."


# --------------------------------------------------
# RAG Tool
# --------------------------------------------------

@tool
def search_documents(query: str) -> str:
    """
    Search the uploaded PDF documents.

    Use this tool whenever user asks about
    uploaded files, PDFs, reports, notes,
    manuals or documentation.

    Returns the most relevant passages together
    with the document name and page number.

    If no PDFs have been uploaded,
    explain that to the user instead.
    """

    global vectorstore
    global documents_loaded

    if not documents_loaded:
        return "No PDF documents have been uploaded yet. Ask the user to upload one first."
    
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 15,
        },
    )
    
    docs = retriever.invoke(query)

    if not docs:
        return "No relevant information was found in the uploaded PDFs."
    
    results = []

    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?") + 1

        results.append(
            f"""Document: {source}
Page: {page}

Content:
{doc.page_content}
"""
        )


    return "\n" + ("\n" + "-" * 60 + "\n").join(results)