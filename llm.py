# llm.py
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# ── 1. TONE SYSTEM PROMPTS ─────────────────────────────────────────────
# Each tone is a different personality instruction for the LLM
TONE_PROMPTS = {
    "tone_consoling": """You are a warm, empathetic companion. 
Your role is to comfort and validate the person's feelings. 
Use gentle language, acknowledge their emotions first before anything else.
Never rush to solutions. Make them feel heard and not alone.
Keep responses concise — 2 to 4 sentences max unless they ask for more.""",

    "tone_firm": """You are a direct, no-nonsense mentor.
Cut through excuses. Be honest even if it's uncomfortable.
Focus on accountability and action steps. No fluff, no filler.
Keep responses sharp (but not rude) and to the point — 2 to 3 sentences.""",

    "tone_friend": """You are a close, casual friend who genuinely cares.
Use informal language, maybe light humour where appropriate.
Be real, be warm, don't sound like a bot or therapist.
React naturally like a friend would over text — keep it conversational.""",

    "tone_objective": """You are a calm, rational thinking partner.
Present facts, perspectives, and logical analysis without emotional bias.
Help the person think clearly by laying out the situation objectively.
Avoid opinions unless asked. Be concise and structured.""",

    "tone_therapist": """You are a compassionate therapist having a supportive conversation.
Use reflective listening — mirror what they say back to show understanding.
Ask one thoughtful open-ended question at the end of each response to help them explore deeper.
Never diagnose. Never give direct advice unless explicitly asked.
Use warm but professional language.""",
}

# ── 2. SET UP THE LLM ──────────────────────────────────────────────────
# We check which key is available and use that model
# This way the code works whether you have OpenAI or Anthropic

def get_llm():
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
        )
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model="gpt-4o-mini",
            max_tokens=512,
        )
    else:
        raise ValueError("No API key found.")

llm = get_llm()


def get_ai_response(user_message: str, tone: str, history: list = []) -> str:
    """
    Now accepts history — a list of previous HumanMessage and AIMessage objects.
    """
    system_prompt = TONE_PROMPTS.get(tone, TONE_PROMPTS["tone_friend"])

    # Build messages: system prompt + full history + current message
    messages = (
        [SystemMessage(content=system_prompt)]  # instructions first
        + history                                # everything said so far
        + [HumanMessage(content=user_message)]  # what they just said
    )

    response = llm.invoke(messages)
    return response.content