import streamlit as st

def render_sidebar() -> str:
    with st.sidebar:
        st.header("⚙️ AI settings")
        provider = st.selectbox("LLM provider", ["ollama", "openai", "gemini"], index=0,
                                help="Ollama runs locally. Cloud providers need their API key in .env.")
        st.caption("The provider selection applies to itinerary generation only.")
        st.divider()
        st.markdown("**Included features**")
        st.markdown("- LangChain prompt + structured output\n- RAG retrieval with Chroma\n- CSV-backed sample travel data\n- JSON / Markdown export")
        st.warning("Sample data is for demonstration, not live inventory or booking.")
    return provider
