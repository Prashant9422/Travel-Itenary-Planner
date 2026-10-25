from datetime import date, timedelta

import app.services.itinerary_service as itinerary_service
from app.services.data_service import load_csv
from app.services.data_service import format_context
from app.services.data_service import display_source_name
from app.schemas import Activity, DayPlan, Itinerary, TripRequest
from app.services.export_service import itinerary_markdown
from app.services.itinerary_service import (
    budget_status_note,
    estimate_accommodation,
    estimate_flight,
)


def make_request(
    *,
    budget: float,
    travelers: int = 2,
    preference: str = "Any",
    destination: str = "Jaipur",
    origin: str = "",
) -> TripRequest:
    today = date.today()
    return TripRequest(
        destination=destination,
        start_date=today,
        end_date=today + timedelta(days=2),
        budget=budget,
        travelers=travelers,
        accommodation_preference=preference,
        origin=origin,
    )


def test_accommodation_estimate_uses_nights_and_shared_rooms():
    cost, suggestion, note = estimate_accommodation(make_request(budget=20_000, travelers=3))

    assert cost == 7_200
    assert "2 room(s) × 2 night(s)" in suggestion
    assert note == ""


def test_accommodation_matches_city_country_destination():
    cost, suggestion, note = estimate_accommodation(
        make_request(budget=20_000, destination="Jaipur, India")
    )

    assert cost == 3_600
    assert "Sample Heritage Guesthouse" in suggestion
    assert note == ""


def test_accommodation_falls_back_to_affordable_tier():
    cost, suggestion, note = estimate_accommodation(
        make_request(budget=10_000, preference="Luxury")
    )

    assert cost == 3_600
    assert "Budget" in suggestion
    assert "lower-cost Budget option" in note


def test_flight_estimate_multiplies_one_way_fare_by_travelers():
    cost, note = estimate_flight(
        make_request(budget=20_000, travelers=3, origin="Delhi, India")
    )

    assert cost == 10_500
    assert "3,500 per traveler × 3 traveler(s)" in note
    assert "one-way" in note


def test_missing_flight_route_returns_explicit_exclusion_message():
    cost, note = estimate_flight(
        make_request(budget=20_000, origin="Kathmandu", destination="Jaipur")
    )

    assert cost == 0
    assert "No sample flight is available from Kathmandu to Jaipur" in note
    assert "estimate excludes flights" in note


def test_budget_status_explains_overage_and_cost_reasons():
    note = budget_status_note(
        total=31_000,
        budget=25_000,
        currency="INR",
        accommodation=24_000,
        flights=7_000,
        activities=0,
    )

    assert "Over budget by INR 6,000.00" in note
    assert "accommodation INR 24,000.00" in note
    assert "flights INR 7,000.00" in note
    assert "activities INR 0.00" in note


def test_generated_trip_total_includes_accommodation_and_stays_within_budget(monkeypatch):
    class FakeChain:
        def __or__(self, _parser):
            return self

        def invoke(self, values):
            assert values["activity_budget"] == "1,400.00"
            assert values["flight_cost"] == "7,000.00"
            return Itinerary(
                destination="Jaipur",
                trip_summary="Test",
                days=[
                    DayPlan(
                        day=1,
                        date="2026-10-22",
                        title="Sightseeing",
                        activities=[
                            Activity(
                                name="Attraction",
                                description="Test",
                                estimated_cost=30_000,
                            )
                        ],
                    )
                ],
            )

    class FakePrompt:
        def __or__(self, _llm):
            return FakeChain()

    monkeypatch.setattr(itinerary_service, "prompt", FakePrompt())
    monkeypatch.setattr(itinerary_service, "get_llm", lambda _provider: object())
    monkeypatch.setattr(itinerary_service, "retrieve_context", lambda *_args, **_kwargs: ("", []))
    monkeypatch.setattr(itinerary_service, "format_context", lambda _destination, _origin: "")

    itinerary, sources = itinerary_service.generate_itinerary(
        make_request(budget=12_000, origin="Delhi")
    )

    assert itinerary.estimated_accommodation_cost == 3_600
    assert itinerary.estimated_flight_cost == 7_000
    assert itinerary.estimated_total_cost == 40_600
    assert itinerary.days[0].activities[0].estimated_cost == 30_000
    assert "Over budget by INR 28,600.00" in itinerary.budget_notes
    assert sources == []


def test_unknown_destination_returns_no_invented_itinerary(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("LLM should not be called for an unsupported destination")

    monkeypatch.setattr(itinerary_service, "get_llm", fail_if_called)
    request = make_request(budget=25_000, destination="Paris", origin="Delhi")

    itinerary, sources = itinerary_service.generate_itinerary(request)

    assert itinerary.days == []
    assert itinerary.estimated_accommodation_cost == 0
    assert itinerary.estimated_total_cost == 0
    assert "no itinerary was generated" in itinerary.trip_summary
    assert sources[0]["source"] == "Data coverage"
    assert request.model_dump()["origin"] == "Delhi"


def test_flight_context_filters_by_requested_origin():
    context = format_context("Jaipur", "Delhi, India")

    assert "Jaipur,Delhi,Sample domestic route,3500" in context
    assert "Bengaluru,6500" not in context


def test_all_travel_csv_rows_have_source_provenance():
    for dataset in ("attractions", "flights", "hotels", "guides"):
        frame = load_csv(dataset)
        assert "source" in frame.columns
        assert frame["source"].astype(str).str.strip().ne("").all()


def test_synthetic_attractions_are_marked_and_excluded_by_master_prompt():
    attractions = load_csv("attractions")
    synthetic = attractions[
        attractions["source"].str.contains("Synthetic test fixture", case=False)
    ]

    assert len(synthetic) == 200
    assert synthetic["name"].str.startswith("Synthetic Test Attraction").all()
    assert "Never recommend any row whose source or notes identify it as synthetic" in itinerary_service.SYSTEM_PROMPT
    context = format_context("Jaipur")
    assert "Synthetic Test Attraction" not in context


def test_synthetic_destination_guides_are_excluded_from_context():
    guides = load_csv("guides")
    synthetic = guides[
        guides["source"].str.contains("Synthetic test fixture", case=False)
    ]

    assert len(synthetic) == 200
    assert synthetic["content"].str.contains("not travel advice", case=False).all()
    assert "Synthetic guide fixture" not in format_context("Jaipur")


def test_user_facing_sources_hide_csv_filenames():
    assert display_source_name("attractions.csv") == "Attractions data"
    assert display_source_name("destination_guides.csv") == "Destination guidance"
    assert ".csv" not in display_source_name("attractions.csv")
    assert ".md" not in display_source_name("travel_basics.md")

    itinerary = Itinerary(
        destination="Jaipur",
        trip_summary="Test",
        days=[
            DayPlan(
                day=1,
                date="2026-10-22",
                title="Sightseeing",
                activities=[
                    Activity(
                        name="Amber Fort",
                        description="A sample attraction.",
                        source="attractions.csv",
                    )
                ],
            )
        ],
    )
    assert "Attractions data" in itinerary_markdown(itinerary)
    assert "attractions.csv" not in itinerary_markdown(itinerary)
