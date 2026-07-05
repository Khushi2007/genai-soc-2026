import os, datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError
from langchain_core.messages import AIMessage, ToolMessage

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)


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


duckduckgo = DuckDuckGoSearchRun(
    description="Internal DuckDuckGo wrapper."
)

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

        if len(result) > 3000:
            result = result[:3000] + "\n..."

        return result
    
    except Exception as e:
        return f"Search failed: {e}"

wikipedia = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(
        top_k_results=3, 
        doc_content_chars_max=4000
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
        result = wikipedia.run(query)

        if len(result) > 3000:
            result = result[:3000] + "\n..."

        return result
    
    except Exception as e:
        return f"Wikipedia lookup failed: {e}"


tools = [web_search, wikipedia_search, get_current_date]


TODAY = datetime.date.today().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
You are AgentX, an intelligent research assistant.

Today's date is {TODAY}.

PERSONALITY
- Be friendly, conversational, and concise.
- Respond naturally to greetings and casual conversation.
- Maintain context across the conversation.
- Understand follow-up questions such as:
  • Tell me more
  • Compare them
  • Explain the second point
  • Summarize it

MEMORY
- Use previous conversation turns to understand follow-up questions.
- If the previous answer already contains enough information, expand on it without calling another tool.
- Only perform a new search if additional information is actually needed.

TOOLS
You have access to:

• Wikipedia
  Use for biographies, historical events, scientific concepts,
  definitions and background knowledge.

• Web Search
  Use for current events, recent news, products, companies,
  sports, weather, prices and information that changes over time.

• Current Date
  Use whenever the user refers to:
  today, latest, current, yesterday,
  this week, this month or this year.

Whenever the user asks a factual question,
use the appropriate tool before answering.

Never claim you used a tool unless it was actually executed.

Never fabricate citations.

OUTPUT FORMAT

For casual conversation:
Reply naturally without headings.

For research questions:

## Introduction

## Key Facts

## Recent Developments
(only if recent information is relevant)

## Conclusion

For every factual statement,
mention which tool supplied that information.

If information cannot be found,
say so honestly instead of guessing.
"""

memory = MemorySaver()
agent = create_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT
)


def run_agent_with_trace(user_input: str, session_id: str) -> tuple[str, str]:
    """Returns (final_answer, formatted_trace_string)."""
    trace_log = []
    final_answer = ""
    step = 1
    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 10,
    }

    try:
        for event in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="values"
        ):

            last = event["messages"][-1]

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

            if isinstance(last, AIMessage) and last.tool_calls:
                for tc in last.tool_calls:
                    trace_log.append(
                        f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕑 {timestamp}

Step {step}

🔧 Tool
{tc['name']}

📥 Input
{tc['args']}
"""
                    )

                    step += 1
            
            elif isinstance(last, ToolMessage):

                trace_log.append(
                    f"""
📤 Output

{last.content[:500]}
"""
                )

            elif isinstance(last, AIMessage):
                final_answer = last.content

    except GraphRecursionError:
        final_answer = (
            "⚠️ I couldn't finish within the step limit. "
            "Try rephrasing or narrowing your question."
        )

    except Exception as e:
        if "tool_use_failed" in str(e):
            final_answer = (
                "⚠️ The language model generated an invalid tool call.\n\n"
                "Please try asking the question again or rephrase it."
            )
        else:
            final_answer = f"Unexpected answer:\n{e}"

    trace_str = (
        "\n".join(trace_log)
        if trace_log
        else "No external tools were needed for this response."
    )
    return final_answer, trace_str