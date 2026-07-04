import os
import gradio as gr
from dotenv import load_dotenv
from rag import load_existing_vectorstore, index_documents, ask

load_dotenv()

db_loaded = load_existing_vectorstore()

if db_loaded:
    initial_status = "✅ Existing Chroma database loaded."
else:
    initial_status = "⚠️ No documents indexed yet."


def index_files(files):
    if not files:
        return (
            "❌ Please upload at least one PDF.",
            "",
            [],
            []
        )
    
    paths = [file.name for file in files]

    num_docs, num_chunks = index_documents(paths)

    status = (
        f"✅ Indexed **{num_docs} document(s)** "
        f"with **{num_chunks} total chunks**."
    )

    return status, "", [], []


def chat(question, history):
    if not question.strip():
        return history, "", "", history
    
    answer, context = ask(question, history)

    updated_history = history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ]

    return (
        updated_history,
        context,
        "",
        updated_history
    )


with gr.Blocks(title="DocBuddy Pro") as demo:
    
    gr.Markdown("# 📚 DocBuddy Pro")
    
    gr.Markdown("Ask questions across multiple PDFs with source citations.")

    files = gr.File(
        file_count="multiple",
        file_types=[".pdf"],
        label="Upload PDFs"
    )

    history = gr.State([])

    index_button = gr.Button("📑 Index Documents", variant="primary")

    status = gr.Markdown(initial_status)

    chatbot = gr.Chatbot(label="Conversation", height=500)

    question = gr.Textbox(label="Ask a Question", placeholder="What would you like to know?")

    with gr.Accordion("🔍 Retrieved Context", open=False):
        context = gr.Markdown("No retrieval yet.")

    
    index_button.click(
        fn=index_files,
        inputs=files,
        outputs=[status, context, chatbot, history]
    )

    question.submit(
        fn=chat,
        inputs=[question, history],
        outputs=[chatbot, context, question, history]
    )


if __name__ == "__main__":
    demo.launch()