from datetime import date
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Interest = Literal["Culture", "Food", "Nature", "Adventure", "Shopping", "History", "Relaxation", "Nightlife"]

class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=100)
    origin: str = Field(default="", max_length=100)
    start_date: date
    end_date: date
    budget: float = Field(gt=0, le=10_000_000)
    currency: str = "INR"
    travelers: int = Field(default=1, ge=1, le=30)
    interests: list[Interest] = Field(default_factory=lambda: ["Culture", "Food"])
    pace: Literal["Relaxed", "Balanced", "Packed"] = "Balanced"
    accommodation_preference: str = "Any"
    notes: str = ""

    @model_validator(mode="after")
    def origin_must_differ_from_destination(self):
        if self.origin.strip() and _normalize_city(self.origin) == _normalize_city(self.destination):
            raise ValueError("Starting location and destination must be different cities.")
        return self

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, value, info):
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("End date must be on or after the start date.")
        return value

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1


def _normalize_city(location: str) -> str:
    city = location.split(",", maxsplit=1)[0]
    return re.sub(r"\s+", " ", city).strip().casefold()


class Activity(BaseModel):
    time: str = "Flexible"
    name: str
    description: str
    estimated_cost: float = Field(default=0, ge=0)
    category: str = "Sightseeing"
    source: str = "AI suggestion; verify locally"

class DayPlan(BaseModel):
    day: int
    date: str
    title: str
    activities: list[Activity] = Field(default_factory=list)

class Itinerary(BaseModel):
    destination: str
    trip_summary: str
    currency: str = "INR"
    requested_budget: float | None = Field(default=None, ge=0)
    estimated_accommodation_cost: float = Field(default=0, ge=0)
    estimated_flight_cost: float = Field(default=0, ge=0)
    estimated_total_cost: float = Field(default=0, ge=0)
    budget_notes: str = "Estimates only; verify before booking."
    accommodation_suggestions: list[str] = Field(default_factory=list)
    travel_tips: list[str] = Field(default_factory=list)
    days: list[DayPlan] = Field(default_factory=list)
