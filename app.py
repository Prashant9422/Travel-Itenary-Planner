import streamlit as st
from app.components.sidebar import render_sidebar
from app.components.trip_form import render_trip_form
from app.components.itinerary_view import render_itinerary
from app.services.itinerary_service import generate_itinerary

st.set_page_config(page_title="AI Travel Itinerary Planner", page_icon="🧭", layout="wide")
st.title("🧭 GenAI Travel Itinerary Planner")
st.caption("Plan smarter trips with LangChain, RAG, local travel data, and your preferred LLM.")
st.markdown("Generate a day-wise plan tailored to your dates, budget, interests, and travel style.")
provider = render_sidebar()
request = render_trip_form()
if request:
    with st.spinner(f"Planning your {request.days}-day trip to {request.destination}… First run may download the local embedding model."):
        try:
            itinerary, sources = generate_itinerary(request, provider=provider)
            st.session_state["last_itinerary"] = itinerary.model_dump(mode="json")
            st.session_state["last_sources"] = sources
        except Exception as exc:
            st.error(f"Itinerary generation failed: {exc}")
            if provider == "ollama":
                st.markdown("Check that Ollama is running and that your model is downloaded. Example: `ollama pull llama3.1:8b`.")
            st.exception(exc)
            
if st.session_state.get("last_itinerary"):
    from app.schemas import Itinerary
    render_itinerary(Itinerary.model_validate(st.session_state["last_itinerary"]), st.session_state.get("last_sources", []))
else:
    st.markdown("### How it works")
    st.markdown("1. **Parse:** validate travel preferences.\n2. **Retrieve:** search local travel knowledge using semantic similarity (RAG).\n3. **Generate:** ask the selected LLM for a structured itinerary.\n4. **Review:** inspect source context and cost estimates.\n5. **Export:** download the plan as Markdown or JSON.")
