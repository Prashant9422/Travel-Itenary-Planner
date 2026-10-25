import streamlit as st
from app.schemas import Itinerary
from app.services.data_service import display_source_name
from app.services.export_service import itinerary_json, itinerary_markdown

def render_itinerary(itinerary: Itinerary, sources: list[dict]) -> Itinerary:
    st.subheader(f"Your {itinerary.destination} itinerary")
    st.write(itinerary.trip_summary)
    activity_cost = sum(activity.estimated_cost for day in itinerary.days for activity in day.activities)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Days planned", len(itinerary.days))
    m2.metric("Accommodation", f"{itinerary.currency} {itinerary.estimated_accommodation_cost:,.0f}")
    m3.metric("Flights", f"{itinerary.currency} {itinerary.estimated_flight_cost:,.0f}")
    m4.metric("Activities", f"{itinerary.currency} {activity_cost:,.0f}")
    m5.metric("Total estimate", f"{itinerary.currency} {itinerary.estimated_total_cost:,.0f}")
    if itinerary.requested_budget is not None:
        st.caption(f"Proposed budget: {itinerary.currency} {itinerary.requested_budget:,.0f}")
    if itinerary.requested_budget is not None and itinerary.estimated_total_cost > itinerary.requested_budget:
        st.warning(itinerary.budget_notes)
    else:
        st.info(itinerary.budget_notes)
    st.caption("Estimate includes sample accommodation when available, matching one-way flights when available, and itinerary activities. Meals and local transport are excluded.")
    if itinerary.accommodation_suggestions:
        st.markdown("**Accommodation ideas**")
        for item in itinerary.accommodation_suggestions:
            st.write(f"- {item}")
    st.markdown("### Day-by-day plan")
    for day in itinerary.days:
        with st.expander(f"Day {day.day} · {day.date} · {day.title}", expanded=True):
            for activity in day.activities:
                with st.container(border=True):
                    st.markdown(f"**{activity.time} — {activity.name}**")
                    st.write(activity.description)
                    st.caption(f"{activity.category} · Estimated {itinerary.currency} {activity.estimated_cost:,.0f} · {display_source_name(activity.source)}")
    if itinerary.travel_tips:
        st.markdown("### Travel tips")
        for tip in itinerary.travel_tips:
            st.write(f"- {tip}")
    st.warning("Prices, opening hours, routes, and availability may change. This demo does not book flights or hotels.")
    st.markdown("### Edit itinerary")
    with st.form("edit_itinerary"):
        updated_summary = st.text_area("Trip summary", value=itinerary.trip_summary)
        locked_names = st.text_input("Activities to keep unchanged (comma-separated names)",
                                     placeholder="e.g. Amber Fort, Hawa Mahal")
        extra_request = st.text_area("Requested changes", placeholder="e.g. add more vegetarian food stops; reduce walking")
        apply = st.form_submit_button("Save notes to this session")
    if apply:
        itinerary.trip_summary = updated_summary
        st.session_state["edit_notes"] = {"locked_activities": locked_names, "requested_changes": extra_request}
        st.success("Notes saved in this session. To regenerate with these changes, submit a new request with the changes in Extra preferences.")
    a, b = st.columns(2)
    a.download_button("Download Markdown", itinerary_markdown(itinerary), file_name="travel_itinerary.md", mime="text/markdown", use_container_width=True)
    b.download_button("Download JSON", itinerary_json(itinerary), file_name="travel_itinerary.json", mime="application/json", use_container_width=True)
    with st.expander("RAG retrieval sources / diagnostics"):
        if not sources:
            st.write("No RAG sources were returned. The itinerary may have been generated using the structured data only.")
        for source in sources:
            st.markdown(f"**{display_source_name(source.get('source', 'source'))}**")
            st.caption(source.get("content", "")[:1200])
    return itinerary
