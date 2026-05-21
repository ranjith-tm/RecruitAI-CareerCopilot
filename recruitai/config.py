import os
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def get_llm(provider: str = "openai", model: str | None = None, api_key: str | None = None) -> BaseChatModel:
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            temperature=0.1,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model or "llama-3.3-70b-versatile",
            temperature=0.1,
            api_key=api_key or os.getenv("GROQ_API_KEY"),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


OPENAI_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
