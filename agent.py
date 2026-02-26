# agent.py
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import TOOLS
from llm import TONE_PROMPTS  # reuse the tone prompts you already wrote

load_dotenv()


def get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,  # slightly higher — agent needs space to think
        )
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o-mini", max_tokens=1024)
    else:
        raise ValueError("No API key found.")


def get_agent_response(user_message: str, tone: str, history: list = []) -> str:
    """
    Runs the LangChain agent with tools available.
    The agent decides whether to use tools or just respond directly.
    """
    llm = get_llm()
    system_prompt = TONE_PROMPTS.get(tone, TONE_PROMPTS["tone_friend"])

    # The prompt template tells the agent how to behave
    # MessagesPlaceholder is a slot where history and agent scratchpad get inserted
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),      # conversation history
        ("human", "{input}"),                              # current user message
        MessagesPlaceholder(variable_name="agent_scratchpad"),  # agent's thinking space
    ])

    # create_tool_calling_agent wires the LLM + tools + prompt together
    # It creates an agent that knows about the tools and can call them
    agent = create_tool_calling_agent(llm, TOOLS, prompt)

    # AgentExecutor is the runner — it handles the loop:
    # think → maybe call tool → see result → think again → respond
    executor = AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=True,       # prints the agent's thinking to your terminal — great for learning
        max_iterations=3,   # safety cap — prevents infinite tool-calling loops
        handle_parsing_errors=True,  # don't crash on malformed tool calls
    )

    # Convert LangChain message objects to the format the agent expects
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
        # If it's a list of content blocks, extract the text
        output = " ".join([item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in output])
    return str(output)