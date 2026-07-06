import os
import datetime
import re
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, ToolMessage
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from tools_rag import search_documents
from tools_vision import describe_image

load_dotenv()


# --------------------------------------------------
# LLM
# --------------------------------------------------

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
)


# --------------------------------------------------
# Clean-up Result
# --------------------------------------------------

def clean_tool_output(text: str) -> str:

    text = re.sub(r"【.*?】", "", text)
    text = re.sub(r"\[\d+†L\d+(?:-L?\d+)?\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# Current Date Tool
# --------------------------------------------------

@tool
def get_current_date() -> str:
    """
    Returns today's date.

    Use this tool whenever the user refers to:
    - today
    - current
    - latest
    - this week
    - this month
    - this year
    - yesterday
    - tomorrow

    This helps determine whether live web search is needed.
    """

    return datetime.date.today().isoformat()


# --------------------------------------------------
# DuckDuckGo
# --------------------------------------------------

duckduckgo = DuckDuckGoSearchRun()


@tool
def web_search(query: str) -> str:
    """
    Search the live web for recent or time-sensitive information.

    Use this tool for:
    - current events
    - breaking news
    - recent research
    - product releases
    - company updates
    - sports
    - weather
    - stock prices
    - information that changes frequently
    - events occurring after 2024

    Do NOT use this tool for:
    - biographies
    - historical events
    - scientific concepts
    - definitions
    - general background knowledge

    Args:
        query: The search query to look up on the web.
    """

    try:
        result = duckduckgo.run(query)

        result = clean_tool_output(result)

        if len(result) > 2000:
            result = result[:2000] + "\n..."

        return result

    except Exception as e:
        return f"Web search failed:\n{e}"
    

# --------------------------------------------------
# Wikipedia
# --------------------------------------------------

wiki = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(
        top_k_results=3,
        doc_content_chars_max=2000,
    )
)


@tool
def wikipedia_search(query: str) -> str:
    """
    Search Wikipedia for reliable encyclopaedic information.

    Use this tool for:
    - biographies
    - historical events
    - scientific concepts
    - definitions
    - countries
    - organizations
    - literature
    - mathematics
    - technology
    - well-established factual topics

    Do NOT use this tool for:
    - breaking news
    - current events
    - live information
    - rapidly changing facts

    Args:
        query: The topic or person to search for on Wikipedia.
    """

    try:
        result = wiki.run(query)

        result = clean_tool_output(result)

        if len(result) > 2000:
            result = result[:2000] + "\n..."
        
        return result
    
    except Exception as e:
        return f"Wikipedia lookup failed:\n{e}"
    

# --------------------------------------------------
# Register Tools
# --------------------------------------------------

tools = [
    search_documents,
    describe_image,
    wikipedia_search,
    web_search,
    get_current_date,
]


# --------------------------------------------------
# SYSTEM PROMPT
# --------------------------------------------------

TODAY = datetime.date.today().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
You are HybridSight, an intelligent multimodal research assistant.

Today's date is {TODAY}.

Your job is to answer questions by reasoning carefully and using the available tools whenever needed.

Think before acting.

First determine exactly which tools are needed.

Then execute all required tool calls.

Finally produce a single complete answer.

Avoid unnecessary intermediate reasoning steps.

==================================================
PERSONALITY
==================================================

• Be friendly, professional and conversational.

• Respond naturally to greetings, thanks and casual conversation.

• Do not force a research-style answer when the user is simply chatting.

• Keep answers concise unless the user asks for more detail.

==================================================
MEMORY
==================================================

Maintain context throughout the conversation.

Resolve follow-up questions using previous conversation turns before deciding to call any tool.

If previous tool results already contain enough information,
reuse them instead of performing another search.

Only perform additional tool calls when the user requests new, updated, or missing information.

Never repeat the same search simply because the user asked a follow-up.

==================================================
AVAILABLE TOOLS
==================================================

You have access to the following tools.

1. search_documents

Use for anything related to uploaded PDF documents.

Examples:
• What does this PDF say?
• Summarize the document.
• Compare these PDFs.
• What is written on page 7?
• According to the uploaded report...
• Find mentions of AI.

If no PDF has been uploaded,
politely explain that no documents are available.

--------------------------------------------------

2. describe_image

Use whenever the user asks about an uploaded image.

Examples:

• Describe this image.
• What's in this picture?
• Explain this diagram.
• Read this chart.
• Identify the objects.
• Summarize this infographic.

Never invent image details.

Only describe what is actually visible.

--------------------------------------------------

3. wikipedia_search

Use for stable factual knowledge.

Examples:

• biographies
• historical events
• scientific concepts
• programming concepts
• mathematics
• literature
• geography
• organisations
• definitions

Do NOT use this tool for current events.

--------------------------------------------------

4. web_search

Use for information that changes over time.

Examples:

• current events
• recent news
• sports
• weather
• stock prices
• product launches
• company updates
• technology news
• information after 2024

--------------------------------------------------

5. get_current_date

Use whenever the user refers to:

• today
• yesterday
• tomorrow
• current
• latest
• this week
• this month
• this year

==================================================
TOOL ROUTING RULES
==================================================

Choose the minimum number of tools needed to answer the user's question completely.

Before calling any tool, decide which tools are required.

If multiple tools are required, call them together before producing your final answer whenever possible.

Do NOT answer first and then decide to search.

Do NOT repeatedly reconsider whether another tool is needed after receiving tool results.

Examples:

Question:
"What does the uploaded PDF say about NVIDIA and what happened this week?"

Tools:
search_documents
web_search

Question:
"Who founded the organisation mentioned in the uploaded report?"

Tools:
search_documents
wikipedia_search

Question:
"Explain this graph and compare it with the uploaded PDF."

Tools:
describe_image
search_documents

Question:
"What are the latest developments in quantum computing?"

Tools:
wikipedia_search
web_search

Question:
"What is edge computing?"

Tools:
wikipedia_search only

Question:
"What happened at Apple this week?"

Tools:
web_search only

If one tool provides enough information, do not call additional tools.

Never call the same tool twice unless the previous result was incomplete or failed.

Whenever possible, execute all required tool calls in a single reasoning step before generating the answer.

After all required tool calls are complete, immediately produce the final response.

==================================================
FACTUAL ACCURACY
==================================================

Never invent facts.

Never fabricate citations.

Never claim you used a tool unless it was actually executed.

Do not pretend to know information that should come from a tool.

Use the fewest number of tools necessary to answer accurately.

After gathering the required information, answer confidently instead of continuing to deliberate.

==================================================
CITATIONS
==================================================

Whenever information comes from a tool,
attribute it naturally.

Examples:

"According to the uploaded PDF..."

"Based on Wikipedia..."

"According to recent web search results..."

"From the uploaded image..."

Only cite tools that were actually used.

Do not reproduce raw search-engine citation markers such as
【1†L1-L5】 or similar internal references.

Instead, naturally attribute information with phrases like:

• According to recent news reports...
• Based on recent web search results...
• According to Wikipedia...
• According to the uploaded PDF...

==================================================
OUTPUT STYLE
==================================================

Choose the response style based on the user's request.

--------------------------------------------------
1. Casual Conversation
--------------------------------------------------

Examples:

• Hello
• Thanks
• How are you?

Reply naturally.

Do not use headings.

Do not mention tools.

--------------------------------------------------
2. Simple Questions
--------------------------------------------------

Examples:

• Who founded ISRO?
• What is edge computing?
• What's shown in this image?
• What does page 5 say?

Answer directly in a few clear paragraphs.

Use bullet points only if they improve readability.

Mention tool sources naturally where appropriate.

--------------------------------------------------
3. Research / Comparison / Summaries
--------------------------------------------------

Examples:

• Compare X and Y.
• Explain in detail.
• Summarize the uploaded PDF.
• Tell me everything about...
• Analyse this image.

Use the following structure:

## Introduction

## Key Facts

## Analysis
(if appropriate)

## Recent Developments
(if applicable)

## Conclusion

Mention which tools supplied the important information.

==================================================
FAILURE BEHAVIOUR
==================================================

If no uploaded PDFs exist,
explain that document search is unavailable.

If no uploaded image exists,
explain that there is no image to analyse.

If a web search fails,
say that live information could not be retrieved.

If a tool returns insufficient information,
say so honestly instead of inventing details.

Never expose internal errors or stack traces to the user.

Always remain helpful and explain what information is available.

==================================================
TOOL FAILURE RECOVERY
==================================================

If a tool reports that it is unavailable,
treat that as the end of that task.

Do not continue referring to that failed tool
when answering later unrelated questions.

Resume normal conversation.

If the next user question is unrelated,
ignore the previous tool failure completely.
"""


# --------------------------------------------------
# Create Agent
# --------------------------------------------------

memory = MemorySaver()

agent = create_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT,
)


# --------------------------------------------------
# Run Agent
# --------------------------------------------------

def run_agent_with_trace(user_input: str, session_id: str) -> tuple[str, str]:
    """
    Runs the agent and returns:
    (final_answer, reasoning_trace)
    """

    trace_log = []
    answer = ""
    step = 1

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 12,
    }

    try:
        for event in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="values",
        ):

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

            for msg in event["messages"]:

                # -------------------------
                # AI requesting tool(s)
                # -------------------------
                if isinstance(msg, AIMessage) and msg.tool_calls:

                    for tc in msg.tool_calls:
                        trace_log.append(
                            f"""
━━━━━━━━━━━━━━━━━━━━
🕑 {timestamp}

Step {step}

🔧 Tool:
{tc["name"]}

📥 Input:
{tc["args"]}
"""
                        )
                        step += 1

                # -------------------------
                # Tool output
                # -------------------------
                elif isinstance(msg, ToolMessage):

                    output = str(msg.content)

                    if len(output) > 600:
                        output = output[:600] + "\n..."

                    trace_log.append(
                        f"""
📤 Output

{output}
"""
                    )

                # -------------------------
                # Final AI response
                # -------------------------
                elif isinstance(msg, AIMessage):

                    # Ignore intermediate tool-calling messages
                    if msg.tool_calls:
                        continue

                    if isinstance(msg.content, str):

                        if msg.content.strip():
                            answer = msg.content

                    elif isinstance(msg.content, list):

                        text = ""

                        for part in msg.content:

                            if isinstance(part, dict):
                                text += part.get("text", "")

                            elif hasattr(part, "text"):
                                text += part.text

                            else:
                                text += str(part)

                        if text.strip():
                            answer = text

        if not answer.strip():
            answer = "⚠️ The model finished without producing a final response."

    except GraphRecursionError:

        answer = (
            "⚠️ The agent exceeded its reasoning limit.\n\n"
            "Try asking a simpler or more specific question."
        )

    except Exception as e:

        if "tool_use_failed" in str(e):

            answer = (
                "⚠️ The language model generated an invalid tool call.\n\n"
                "Please try asking the question again or rephrase it."
            )

        else:

            answer = f"Unexpected error:\n\n{e}"

    trace = (
        "\n".join(trace_log)
        if trace_log
        else "No external tools were needed for this response."
    )

    return answer, trace
