import os
import sys
import uuid
import gradio as gr

from agent import run_agent_with_trace
from tools_rag import (
    index_documents,
    clear_documents,
)
from tools_vision import (
    set_image,
    clear_image,
)
from safe_call import safe_call


# --------------------------------------------------
# Startup Checks
# --------------------------------------------------

os.makedirs("./chroma_store", exist_ok=True)

if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY is not set.")
    print("Add it to your .env file or Hugging Face Spaces Secrets.")
    sys.exit(1)


# --------------------------------------------------
# Upload PDFs
# --------------------------------------------------

@safe_call
def upload_pdf(files, uploaded_pdfs):

    if not files:
        return (
            "No PDFs uploaded.",
            uploaded_pdfs,
            "No PDFs uploaded."
        )

    uploaded_pdfs = [file.name for file in files]

    status = index_documents(uploaded_pdfs)

    display = "\n".join(
        f"✅ {os.path.basename(pdf)}"
        for pdf in uploaded_pdfs
    )

    return (
        status,
        uploaded_pdfs,
        display
    )


# --------------------------------------------------
# Clear PDFs
# --------------------------------------------------

@safe_call
def clear_pdf_list():

    clear_documents()

    return (
        None,
        "No PDFs uploaded.",
        [],
        "No PDFs uploaded."
    )


# --------------------------------------------------
# Upload Image
# --------------------------------------------------

@safe_call
def upload_image(image):

    if image is None:
        return (
            "No image uploaded.",
            "No image uploaded."
        )

    set_image(image)

    return (
        "Image uploaded successfully.",
        f"✅ {os.path.basename(image)}"
    )


# --------------------------------------------------
# Remove Image
# --------------------------------------------------

@safe_call
def remove_image():

    clear_image()

    return (
        None,
        "No image uploaded.",
        "No image uploaded."
    )


# --------------------------------------------------
# Chat
# --------------------------------------------------

@safe_call
def chat(message, history, session_id):

    if not message.strip():
        return "", history, "", session_id

    answer, trace = run_agent_with_trace(
        message,
        session_id
    )

    history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    return (
        "",
        history,
        trace,
        session_id,
    )


# --------------------------------------------------
# New Chat
# --------------------------------------------------

@safe_call
def new_chat():

    return (
        [],
        "",
        str(uuid.uuid4())
    )


# --------------------------------------------------
# UI
# --------------------------------------------------

with gr.Blocks(
    title="HybridSight",
    theme=gr.themes.Soft(),
) as demo:

    session_id = gr.State(str(uuid.uuid4()))
    uploaded_pdfs = gr.State([])

    gr.Markdown(
        """
# 🔍 HybridSight

A hybrid AI assistant capable of answering from:

- 📄 Uploaded PDFs (RAG)
- 🌐 Live Web Search
- 📚 Wikipedia
- 🖼 Uploaded Images

It remembers previous conversation and displays its reasoning trace.
"""
    )

    with gr.Tabs():

        # ==================================================
        # TAB 1 — Hybrid Chat
        # ==================================================

        with gr.Tab("💬 Hybrid Chat"):

            with gr.Row():

                with gr.Column(scale=3):

                    chatbot = gr.Chatbot(
                        height=520,
                        label="Conversation"
                    )

                    textbox = gr.Textbox(
                        placeholder="Ask anything...",
                        show_label=False
                    )

                    with gr.Row():

                        send = gr.Button(
                            "Send",
                            variant="primary"
                        )

                        new_chat_btn = gr.Button(
                            "🆕 New Chat"
                        )

                with gr.Column(scale=1):

                    with gr.Accordion(
                        "🔍 Agent Reasoning Trace",
                        open=False
                    ):

                        trace_box = gr.Textbox(
                            lines=20,
                            interactive=False,
                            show_label=False
                        )

            send.click(
                chat,
                inputs=[
                    textbox,
                    chatbot,
                    session_id
                ],
                outputs=[
                    textbox,
                    chatbot,
                    trace_box,
                    session_id
                ]
            )

            textbox.submit(
                chat,
                inputs=[
                    textbox,
                    chatbot,
                    session_id
                ],
                outputs=[
                    textbox,
                    chatbot,
                    trace_box,
                    session_id
                ]
            )

            new_chat_btn.click(
                new_chat,
                outputs=[
                    chatbot,
                    trace_box,
                    session_id
                ]
            )

        # ==================================================
        # TAB 2 — Documents
        # ==================================================

        with gr.Tab("📄 Document QA"):

            pdf = gr.File(
                label="Upload PDF(s)",
                file_types=[".pdf"],
                file_count="multiple"
            )

            pdf_status = gr.Textbox(
                label="Indexing Status",
                interactive=False
            )

            pdf_list = gr.Markdown(
                "No PDFs uploaded."
            )

            clear_pdf = gr.Button(
                "🗑 Clear PDFs",
                variant="secondary"
            )

            pdf.upload(
                upload_pdf,
                inputs=[
                    pdf,
                    uploaded_pdfs
                ],
                outputs=[
                    pdf_status,
                    uploaded_pdfs,
                    pdf_list
                ]
            )

            clear_pdf.click(
                clear_pdf_list,
                outputs=[
                    pdf,
                    pdf_status,
                    uploaded_pdfs,
                    pdf_list
                ]
            )

        # ==================================================
        # TAB 3 — Image Studio
        # ==================================================

        with gr.Tab("🖼 Image Studio"):

            image = gr.Image(
                type="filepath",
                label="Upload Image"
            )

            image_status = gr.Textbox(
                label="Status",
                interactive=False
            )

            image_name = gr.Markdown(
                "No image uploaded."
            )

            clear_img = gr.Button(
                "🗑 Remove Image",
                variant="secondary"
            )

            image.upload(
                upload_image,
                inputs=image,
                outputs=[
                    image_status,
                    image_name
                ]
            )

            clear_img.click(
                remove_image,
                outputs=[
                    image,
                    image_status,
                    image_name
                ]
            )


if __name__ == "__main__":
    demo.launch()