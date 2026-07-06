import functools

import gradio as gr
import groq

from langgraph.errors import GraphRecursionError


def safe_call(func):
    """
    Decorator that converts exceptions into
    friendly Gradio pop-up messages.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        try:
            return func(*args, **kwargs)

        except GraphRecursionError:
            raise gr.Error(
                "⚠️ The agent exceeded its reasoning limit.\n\n"
                "Try asking a simpler question."
            )

        except groq.RateLimitError:
            raise gr.Error(
                "⏱️ Groq rate limit reached.\n\n"
                "Please wait a few seconds and try again."
            )

        except groq.APIConnectionError:
            raise gr.Error(
                "🌐 Unable to reach Groq.\n\n"
                "Please check your internet connection."
            )

        except groq.AuthenticationError:
            raise gr.Error(
                "🔑 Invalid GROQ_API_KEY."
            )

        except FileNotFoundError:
            raise gr.Error(
                "📄 The selected file could not be found."
            )

        except ValueError as e:
            raise gr.Error(str(e))

        except Exception as e:
            raise gr.Error(
                f"{type(e).__name__}: {e}"
            )

    return wrapper