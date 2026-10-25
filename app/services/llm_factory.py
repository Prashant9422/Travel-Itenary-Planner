"""Provider-agnostic LangChain chat-model factory.

Switch providers with LLM_PROVIDER in .env. Keep secrets in environment variables.
"""
from functools import lru_cache
from langchain_core.language_models import BaseChatModel
from app import config

@lru_cache(maxsize=4)
def get_llm(provider: str | None = None) -> BaseChatModel:
    selected = (provider or config.LLM_PROVIDER).lower().strip()
    if selected == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=config.OLLAMA_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=config.TEMPERATURE,
        )
    if selected == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY,
                          temperature=config.TEMPERATURE)
    
    if selected in {"gemini", "google"}:
        if not config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is missing. Add it to your .env file.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=config.GEMINI_MODEL, google_api_key=config.GOOGLE_API_KEY,
                                      temperature=config.TEMPERATURE)
    raise ValueError(f"Unsupported LLM_PROVIDER '{selected}'. Use ollama, openai, or gemini.")
