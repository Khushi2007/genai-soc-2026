import os
import json

import gradio as gr
from groq import Groq
from dotenv import load_dotenv

from personas import PERSONAS

MODEL_NAME = "llama-3.3-70b-versatile"

DISPLAY_TO_KEY = {
    persona["name"]: key
    for key, persona in PERSONAS.items()
}

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_messages(persona_key, history, user_message):
    persona = PERSONAS[persona_key]

    messages = [
        {
            "role": "system",
            "content": persona["system_prompt"]
        }
    ]

    messages.extend(persona["few_shot_examples"])

    messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    return messages


def chat_stream(message, history, display_name, temperature):
    if not message.strip():
        yield history, history
        return
    
    persona_key = DISPLAY_TO_KEY[display_name]
    persona = PERSONAS[persona_key]

    messages = build_messages(persona_key, history, message)

    if persona["output_format"] == "json":
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            stream=False
        )

        raw_response = response.choices[0].message.content

        try:
            review = json.loads(raw_response)
            markdown = f"""
## Overall Summary

{review["summary"]}

## Issues

"""
            for issue in review["issues"]:
                markdown += f"""
### {issue["title"]}

**Severity:** {issue["severity"]}

**Description**

{issue["description"]}

**Suggestion**

{issue["suggestion"]}

---

"""

            if review["good_practices"]:                
                markdown += f"""
## Good Practices

"""
                for practice in review["good_practices"]:
                    markdown += f"""
{practice}

---

"""

        except json.JSONDecodeError:
            markdown = f"""
⚠️ **Couldn't parse the JSON response.**

Raw response:
```json
{raw_response}
```"""
            
        updated_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": markdown}
        ]

        yield updated_history, updated_history


    else:

        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=temperature,
                stream=True
            )

            response = ""

            updated_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""}
            ]

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                response += delta

                updated_history[-1]["content"] = response

                yield updated_history, updated_history

        except Exception as e:
            updated_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"❌ Error: {str(e)}"}
            ]

            yield updated_history, updated_history


def update_persona(display_name):
    persona_key = DISPLAY_TO_KEY[display_name]
    persona = PERSONAS[persona_key]

    return (
        persona["description"],
        persona["system_prompt"],
        f"✨ Switched to **{persona['name']}**. Starting a fresh conversation.",
        [],
        []
    )


with gr.Blocks(title="PromptForge") as demo:
    gr.Markdown("# 🛠️ PromptForge")
    gr.Markdown("Choose an AI persona and start chatting!")

    with gr.Row():
        persona_dropdown = gr.Dropdown(
            choices=list(DISPLAY_TO_KEY.keys()),
            value=PERSONAS["detective"]["name"],
            label="🎭 Choose Your Persona"
        )

        temperature = gr.Slider(
            minimum=0.0,
            maximum=1.5,
            value=0.7,
            step=0.1,
            label="🌡️ Temperature"
        )

    description = gr.Markdown(PERSONAS["detective"]["description"])

    status = gr.Markdown("🕵️‍♂️ Currently chatting with **Detective Holmes**.")

    with gr.Accordion("Active System Prompt", open=False):
        system_prompt = gr.Markdown(PERSONAS["detective"]["system_prompt"])

    chatbot = gr.Chatbot(height=500, label="Conversation")

    textbox = gr.Textbox(
        placeholder="Ask anything...",
        label="Your Prompt"
    )

    with gr.Row():
    
        send = gr.Button("Send", variant="primary", scale=3)

        clear = gr.Button("🗑️ Clear Chat", scale=3)

    history = gr.State([])

    persona_dropdown.change(
        fn=update_persona,
        inputs=persona_dropdown,
        outputs=[
            description,
            system_prompt,
            status,
            chatbot,
            history
        ]
    )

    send.click(
        fn=chat_stream,
        inputs=[textbox, history, persona_dropdown, temperature],
        outputs=[chatbot, history]
    ).then(
        lambda: "",
        outputs=textbox
    )

    textbox.submit(
        fn=chat_stream,
        inputs=[textbox, history, persona_dropdown, temperature],
        outputs=[chatbot, history]
    ).then(
        lambda: "",
        outputs=textbox
    )

    clear.click(
        lambda: ([], []),
        outputs=[chatbot, history]
    )


if __name__ == "__main__":
    demo.launch()