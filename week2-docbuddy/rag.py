import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHROMA_PATH = "./chroma_store"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

LLM_MODEL = "llama-3.3-70b-versatile"

embeddings = HuggingFaceBgeEmbeddings(model_name=EMBEDDING_MODEL)

vectorstore = None

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=0,
    api_key=GROQ_API_KEY
)

def load_existing_vectorstore():
    global vectorstore

    if not os.path.exists(CHROMA_PATH):
        return False
    
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    return True


def index_documents(pdf_paths):
    global vectorstore

    documents = []

    for pdf_path in pdf_paths:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()

        filename = os.path.basename(pdf_path)

        for doc in docs:
            doc.metadata["source"] = filename
            doc.metadata["page"] = doc.metadata.get("page", 0) + 1
        
        documents.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)

    print("=" * 50)
    print(f"Indexed {len(pdf_paths)} document(s)")
    print(f"Created {len(chunks)} chunks")
    print("=" * 50)

    if vectorstore is not None:
        vectorstore.delete_collection()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )

    return len(pdf_paths), len(chunks)


def format_context(chunks):
    markdown = ""

    for i, chunk in enumerate(chunks, start=1):
        source = chunk.metadata.get("source", "Unknown")
        page = chunk.metadata.get("page", "?")

        preview = chunk.page_content.strip()

        if len(preview) > 300:
            preview = preview[:300] + "..."

        markdown += f"""### 📄 Chunk {i}
**Source:** `{source}`
**Page:** {page}

{preview}

---

"""
        
    return markdown


def format_sources(chunks):
    """
    Generate a unique list of source citations.
    """

    seen = set()
    citations = []

    for chunk in chunks:
        source = chunk.metadata.get("source", "Unknown")
        page = chunk.metadata.get("page", "?")

        citation = f"- **{source}** (Page {page})"

        if citation not in seen:
            seen.add(citation)
            citations.append(citation)

    return "\n".join(citations)


def ask(question, history):
    global vectorstore

    if vectorstore is None:
        return(
            "No documents have been indexed yet.",
            "No retrieved context."
        )
    
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    recent_history = history[-4:]

    for msg in recent_history:
        messages.append(msg)

    retrieval_query = question

    if history:
        previous_user_messages = [
            msg["content"]
            for msg in history
            if msg["role"] == "user"
        ]

        retrieval_query = (
            "\n".join(previous_user_messages[-2:])
            + "\n"
            + question
        )
    
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 10,
            "fetch_k": 30
        }
    )
    retrieved_docs = retriever.invoke(retrieval_query)

    context = ""

    for doc in retrieved_docs:
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")

        context += f"""
Source: {source} (Page {page})

{doc.page_content}

-------------------------

"""
        
    prompt = f"""
{SYSTEM_PROMPT}

Retrieved Context:

{context}

Question:
{question}
"""
    
    messages.append(
        {
            "role": "user",
            "content": f"{prompt}"
        }
    )

    response = llm.invoke(messages)

    answer = response.content

    citations = format_sources(retrieved_docs)

    answer += "\n\n---\n### 📚 Sources\n" + citations

    context_display = format_context(retrieved_docs)

    return answer, context_display