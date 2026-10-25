from datetime import date, timedelta
import streamlit as st
from pydantic import ValidationError
from app.schemas import TripRequest

INTERESTS = ["Culture", "Food", "Nature", "Adventure", "Shopping", "History", "Relaxation", "Nightlife"]

def render_trip_form() -> TripRequest | None:
    with st.form("trip_form"):
        origin, destination = st.columns(2)
        with origin:
            starting_location = st.text_input(
                "Starting location",
                placeholder="e.g. Delhi, India",
                help="Where your trip starts. It must be a different city from your destination. Used to match sample flight routes; fares and availability are not live.",
            )
        with destination:
            destination_name = st.text_input(
                "Destination",
                placeholder="e.g. Jaipur, India",
                value="Jaipur, India",
            )
        left, right = st.columns(2)
        with left:
            start = st.date_input("Start date", value=date.today() + timedelta(days=14))
            budget = st.number_input("Total trip budget", min_value=500.0, value=25000.0, step=1000.0)
            currency = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"])
            travelers = st.number_input("Travelers", min_value=1, max_value=30, value=2)
        with right:
            end = st.date_input("End date", value=date.today() + timedelta(days=16))
            pace = st.selectbox("Travel pace", ["Relaxed", "Balanced", "Packed"], index=1)
            accommodation = st.selectbox("Accommodation", ["Any", "Budget", "Mid-range", "Luxury", "Hostel", "Family-friendly"])
            interests = st.multiselect("Interests", INTERESTS, default=["Culture", "Food", "History"])
        notes = st.text_area("Extra preferences", placeholder="Accessibility needs, dietary preferences, children, must-see places…")
        submitted = st.form_submit_button("✨ Generate itinerary", type="primary", use_container_width=True)
    if not submitted:
        return None
    try:
        return TripRequest(destination=destination_name.strip(), origin=starting_location.strip(),
                           start_date=start, end_date=end, budget=budget,
                           currency=currency, travelers=int(travelers), interests=interests or ["Culture"],
                           pace=pace, accommodation_preference=accommodation, notes=notes)
    except ValidationError as exc:
        messages = "; ".join(error["msg"] for error in exc.errors(include_url=False))
        st.error(f"Please correct the trip details: {messages}")
        return None
    except (TypeError, ValueError) as exc:
        st.error(f"Please correct the trip details: {exc}")
        return None
