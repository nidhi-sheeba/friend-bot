# agent.py
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import TOOLS
from llm import TONE_PROMPTS

load_dotenv()


def get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", max_tokens=1024)
    else:
        raise ValueError("No API key found.")


def get_agent_response(user_message: str, tone: str, history: list = []) -> str:
    llm = get_llm()
    system_prompt = TONE_PROMPTS.get(tone, TONE_PROMPTS["tone_friend"])

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, TOOLS, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=True,
        max_iterations=3,
        handle_parsing_errors=True,
    )

    formatted_history = []
    for msg in history:
        if isinstance(msg, HumanMessage):
            formatted_history.append(("human", msg.content))
        elif isinstance(msg, AIMessage):
            formatted_history.append(("ai", msg.content))

    result = executor.invoke({
        "input": user_message,
        "history": formatted_history,
    })

    output = result["output"]
    if isinstance(output, list):
        output = " ".join([
            item.get("text", str(item)) if isinstance(item, dict) else str(item)
            for item in output
        ])
    return str(output)
