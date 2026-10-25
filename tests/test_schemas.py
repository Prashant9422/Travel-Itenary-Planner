from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from app.schemas import TripRequest, Itinerary

def test_trip_days_inclusive():
    today = date.today()
    req = TripRequest(destination="Jaipur", start_date=today, end_date=today + timedelta(days=2), budget=10000)
    assert req.days == 3

def test_end_date_before_start_is_rejected():
    today = date.today()
    with pytest.raises(ValidationError):
        TripRequest(destination="Jaipur", start_date=today, end_date=today - timedelta(days=1), budget=10000)


@pytest.mark.parametrize(
    ("origin", "destination"),
    [
        ("Jaipur", "Jaipur"),
        (" jaipur ", "JAIPUR"),
        ("Jaipur, Rajasthan", "Jaipur, India"),
    ],
)
def test_same_origin_and_destination_are_rejected(origin, destination):
    today = date.today()

    with pytest.raises(ValidationError, match="Starting location and destination must be different cities"):
        TripRequest(
            origin=origin,
            destination=destination,
            start_date=today,
            end_date=today + timedelta(days=2),
            budget=10_000,
        )


def test_different_origin_and_destination_are_accepted():
    today = date.today()
    request = TripRequest(
        origin="Delhi, India",
        destination="Jaipur, India",
        start_date=today,
        end_date=today + timedelta(days=2),
        budget=10_000,
    )

    assert request.origin == "Delhi, India"


def test_itinerary_schema():
    plan = Itinerary(destination="Jaipur", trip_summary="Sample", estimated_total_cost=100)
    assert plan.destination == "Jaipur"
