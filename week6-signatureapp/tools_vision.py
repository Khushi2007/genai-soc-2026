import os
import base64
import mimetypes
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()


# --------------------------------------------------
# Vision Model
# --------------------------------------------------

vision_llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=os.getenv("GROQ_API_KEY"),
)


# --------------------------------------------------
# Image Path
# --------------------------------------------------

current_image_path = None


def set_image(path: str):
    """
    Stores the path of the currently uploaded image.
    """

    global current_image_path
    current_image_path = path


# --------------------------------------------------
# Clear Image
# --------------------------------------------------

def clear_image():
    global current_image_path
    current_image_path = None


# --------------------------------------------------
# Vision Tool
# --------------------------------------------------

@tool
def describe_image(prompt: str = "Describe this image in detail.") -> str:
    """
    Analyze the uploaded image.

    Use this tool whenever the user asks about an uploaded image,
    photograph, diagram, chart, screenshot, graph, drawing,
    handwritten notes, or any visual content.

    If no image has been uploaded, explain that to the user.
    """

    global current_image_path

    if current_image_path is None:
        return "No image has been uploaded yet. Please ask the user to upload an image first."
    
    try:
        with open(current_image_path, "rb") as f:
            image_bytes = f.read()

        image_base64 = base64.b64encode(image_bytes).decode()

        mime_type, _ = mimetypes.guess_type(current_image_path)

        if mime_type is None:
            mime_type = "image/jpeg"

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_base64}"
                    },
                },
            ]
        )

        response = vision_llm.invoke([message])

        return response.content
    
    except Exception:
        return "The uploaded image could not be analyzed because the vision service is currently unavailable."