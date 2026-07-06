import uuid
import gradio as gr
from agent import run_agent_with_trace
from tools_rag import index_documents, clear_documents
from tools_vision import set_image, clear_image
import os


# --------------------------------------------------
# Upload PDFs
# --------------------------------------------------

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
        f"✓ {os.path.basename(pdf)}"
        for pdf in uploaded_pdfs
    )

    return status, uploaded_pdfs, display


# --------------------------------------------------
# Clear PDFs
# --------------------------------------------------

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

def upload_image(image):

    if image is None:
        return (
            "No image uploaded.",
            "No image uploaded."
        )

    set_image(image)

    return (
        "Image uploaded successfully.",
        f"✓ {os.path.basename(image)}"
    )


# --------------------------------------------------
# Clear Image
# --------------------------------------------------

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
            "content": message
        }
    )

    history.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    return "", history, trace, session_id


# --------------------------------------------------
# UI
# --------------------------------------------------

with gr.Blocks(title="HybridSight") as demo:

    session_id = gr.State(str(uuid.uuid4()))

    uploaded_pdfs = gr.State([])

    gr.Markdown(
        """
# 🔍 HybridSight

A hybrid AI agent that can answer from:

- 📄 Uploaded PDFs
- 🌐 Live Web Search
- 📚 Wikipedia
- 🖼 Uploaded Images

The agent remembers previous conversation and shows its reasoning trace.
"""
    )

    with gr.Row():

        with gr.Column(scale=1):

            pdf = gr.File(
                label="Upload PDF(s)",
                file_types=[".pdf"],
                file_count="multiple"
            )

            pdf_status = gr.Textbox(
                label="Status",
                interactive=False
            )

            pdf_list = gr.Markdown(
                "No PDFs uploaded."
            )

            clear_pdf = gr.Button("🗑 Clear PDFs")

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

            clear_img = gr.Button("🗑 Remove Image")

        with gr.Column(scale=3):

            chatbot = gr.Chatbot(
                height=500
            )

            textbox = gr.Textbox(
                placeholder="Ask anything..."
            )

            send = gr.Button(
                "Send",
                variant="primary"
            )

            with gr.Accordion(
                "🔍 Agent Reasoning Trace",
                open=False
            ):

                trace_box = gr.Textbox(
                    lines=14,
                    interactive=False
                )


    pdf.upload(
        upload_pdf,
        inputs=[pdf, uploaded_pdfs],
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


if __name__ == "__main__":
    demo.launch()