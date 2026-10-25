import json
import math
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.schemas import TripRequest, Itinerary
from app.services.llm_factory import get_llm
from app.services.data_service import destination_rows, format_context, load_csv
from app.services.rag_service import retrieve_context

SYSTEM_PROMPT = """You are a careful travel-planning assistant. Build practical day-wise itineraries.
Treat supplied destination-matched CSV rows as the only evidence for destination-specific facts.
Do not use prior knowledge, guesswork, or retrieved content for a different destination to fill gaps.
Never invent attractions, venues, hotels, routes, schedules, opening hours, availability, prices,
or citations. If a requested fact is absent, say it is unavailable rather than guessing. Use each
row's source field verbatim when citing data; if it says there is no external source, identify the
information as illustrative and unverified, not as a factual or authoritative recommendation.
Never recommend any row whose source or notes identify it as synthetic, fake, test data, a fixture,
or not a real place. Ignore those rows when planning and treat them only as test records.
Never claim to have booked anything or present sample CSV prices as live prices. Keep plans feasible,
consider the user's budget and interests when selecting activities, and estimate activity costs
for the whole party.
Estimate realistic costs from the supplied evidence even when they exceed the user's budget. Never
reduce, omit, or set costs to zero just to make an itinerary appear within budget. Clearly explain
when and by how much the total exceeds the budget.
Accommodation is estimated separately and must not be added to activity costs. Return only the
requested structured output."""

parser = PydanticOutputParser(pydantic_object=Itinerary)
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT + "\n\n{format_instructions}"),
    ("human", "Trip requirements (origin/departure location and destination):\n{request_json}\n\nDestination-matched structured local data, including any routes matching the requested origin:\n{data_context}\n\nRetrieved context (may not match the destination; use only if it explicitly supports this destination and has a source):\n{rag_context}\n\nOnly name attractions, businesses, or destinations explicitly present in destination-matched data. Cite the exact source field for each supported recommendation. Sample flight fares are illustrative, one-way, and not live or bookable. Do not fabricate missing details or fill gaps from memory; state what information is unavailable. Flight estimate: {flight_cost} {currency} total for the travel party. {flight_note} Accommodation estimate: {accommodation_cost} {currency} for {nights} night(s), using {rooms} room(s) at the selected sample rate. The budget available for activities after fixed costs is {activity_budget} {currency}; this is informational, not a cap. Estimate realistic activity costs from the data even if they exceed this amount. Do not lower, omit, or zero costs merely to fit the budget. Include only activity costs in the itinerary's estimated_total_cost; the application adds accommodation and flights separately. Costs must be for the whole travel party.")
])


def estimate_accommodation(request: TripRequest) -> tuple[float, str, str]:
    nights = max(request.days - 1, 0)
    rooms = math.ceil(request.travelers / 2)
    if nights == 0:
        return 0, "", "No overnight stay is included for a one-day trip."

    hotels = destination_rows("hotels", request.destination)
    if hotels.empty or "currency" not in hotels.columns:
        return 0, "", "No matching sample hotel data is available, so accommodation is not included in the estimate."

    hotels = hotels[hotels["currency"].astype(str).str.upper() == request.currency.upper()].copy()
    if hotels.empty:
        return 0, "", (
            f"No sample hotel rates are available in {request.currency}; "
            "accommodation is not included, so the total budget cannot be verified."
        )

    hotels["estimated_nightly_cost"] = hotels["estimated_nightly_cost"].astype(float)
    hotels = hotels[hotels["estimated_nightly_cost"] >= 0]
    if hotels.empty:
        return 0, "", "No valid sample hotel rates are available, so accommodation is not included in the estimate."

    requested_tier = request.accommodation_preference.casefold()
    if requested_tier in {"budget", "mid-range", "luxury"}:
        preferred = hotels[hotels["tier"].astype(str).str.casefold() == requested_tier]
    else:
        preferred = hotels.iloc[0:0]

    preferred = preferred.sort_values("estimated_nightly_cost")
    all_hotels = hotels.sort_values("estimated_nightly_cost")
    chosen = preferred.iloc[0] if not preferred.empty else None
    chosen_cost = (
        float(chosen["estimated_nightly_cost"]) * nights * rooms
        if chosen is not None else float("inf")
    )

    if chosen is None or chosen_cost > request.budget:
        affordable = all_hotels[
            all_hotels["estimated_nightly_cost"] * nights * rooms <= request.budget
        ]
        if not affordable.empty:
            chosen = affordable.iloc[0]
            chosen_cost = float(chosen["estimated_nightly_cost"]) * nights * rooms
        elif chosen is None or all_hotels.iloc[0]["estimated_nightly_cost"] * nights * rooms < chosen_cost:
            chosen = all_hotels.iloc[0]
            chosen_cost = float(chosen["estimated_nightly_cost"]) * nights * rooms

    hotel_name = str(chosen["name"])
    hotel_tier = str(chosen["tier"])
    nightly_cost = float(chosen["estimated_nightly_cost"])
    suggestion = (
        f"{hotel_name} ({hotel_tier}; sample estimate {request.currency} "
        f"{nightly_cost:,.0f}/room/night, {rooms} room(s) × {nights} night(s))"
    )
    if chosen_cost > request.budget:
        note = (
            f"The selected sample accommodation estimate is "
            f"{request.currency} {chosen_cost:,.0f}, which exceeds the total budget."
        )
    elif preferred.empty and requested_tier not in {"any", "hostel", "family-friendly"}:
        note = f"No sample rate matches the {request.accommodation_preference} preference; a lower-cost available option was estimated."
    elif requested_tier in {"budget", "mid-range", "luxury"} and hotel_tier.casefold() != requested_tier:
        note = f"The requested accommodation tier did not fit the budget; estimated a lower-cost {hotel_tier} option instead."
    else:
        note = ""
    return chosen_cost, suggestion, note


def estimate_flight(request: TripRequest) -> tuple[float, str]:
    if not request.origin.strip():
        return 0, "No starting location was provided; flights are unavailable and excluded from the estimate."

    routes = destination_rows("flights", request.destination)
    if routes.empty or "origin" not in routes.columns or "estimated_fare" not in routes.columns:
        return 0, (
            f"No sample flight route is available from {request.origin} to {request.destination}; "
            "flights are excluded from the estimated total."
        )

    origin_parts = {
        part.strip().casefold()
        for part in request.origin.split(",")
        if part.strip()
    }
    routes = routes[routes["origin"].astype(str).str.strip().str.casefold().isin(origin_parts)].copy()
    if routes.empty:
        return 0, (
            f"No sample flight is available from {request.origin} to {request.destination}; "
            "the estimate excludes flights."
        )

    if "currency" in routes.columns:
        routes = routes[routes["currency"].astype(str).str.upper() == request.currency.upper()]
    if routes.empty:
        return 0, (
            f"No sample flight fare is available from {request.origin} to {request.destination} "
            f"in {request.currency}; the estimate excludes flights."
        )

    routes["estimated_fare"] = pd.to_numeric(routes["estimated_fare"], errors="coerce")
    routes = routes[routes["estimated_fare"].notna() & (routes["estimated_fare"] >= 0)]
    if routes.empty:
        return 0, (
            f"No valid sample flight fare is available from {request.origin} to {request.destination}; "
            "the estimate excludes flights."
        )

    fare_per_traveler = float(routes["estimated_fare"].min())
    total = fare_per_traveler * request.travelers
    return total, (
        f"Includes an illustrative one-way flight estimate of {request.currency} "
        f"{fare_per_traveler:,.0f} per traveler × {request.travelers} traveler(s) "
        f"from {request.origin} to {request.destination}. This is not a live fare or booking."
    )


def budget_status_note(
    *,
    total: float,
    budget: float,
    currency: str,
    accommodation: float,
    flights: float,
    activities: float,
) -> str:
    if total <= budget:
        return (
            f"Estimated total is within the {currency} {budget:,.2f} budget, "
            f"with {currency} {budget - total:,.2f} remaining."
        )

    overage = total - budget
    costs = [
        f"accommodation {currency} {accommodation:,.2f}",
        f"flights {currency} {flights:,.2f}",
        f"activities {currency} {activities:,.2f}",
    ]
    return (
        f"Over budget by {currency} {overage:,.2f}: estimated costs total "
        f"{currency} {total:,.2f} against your {currency} {budget:,.2f} budget. "
        f"Reason: {', '.join(costs)}."
    )


def generate_itinerary(request: TripRequest, provider: str | None = None) -> tuple[Itinerary, list[dict]]:
    query = f"Travel itinerary from {request.origin or 'unspecified origin'} to {request.destination}; interests {', '.join(request.interests)}; {request.days} days; {request.pace} pace; {request.accommodation_preference} accommodation"
    accommodation_cost, accommodation_suggestion, accommodation_note = estimate_accommodation(request)
    flight_cost, flight_note = estimate_flight(request)
    nights = max(request.days - 1, 0)
    rooms = math.ceil(request.travelers / 2)
    activity_budget = request.budget - accommodation_cost - flight_cost
    attractions = destination_rows("attractions", request.destination)
    if attractions.empty:
        no_data_message = (
            f"No destination-specific attraction data is available for {request.destination} "
            "in the local CSV files. To avoid inventing recommendations, no itinerary was generated. "
            "Add verified destination data with source references and try again."
        )
        return (
            Itinerary(
                destination=request.destination,
                trip_summary=no_data_message,
                currency=request.currency,
                requested_budget=request.budget,
                estimated_accommodation_cost=accommodation_cost,
                estimated_flight_cost=flight_cost,
                estimated_total_cost=accommodation_cost + flight_cost,
                budget_notes=(
                    "No activities were estimated because destination data is missing. "
                    f"{accommodation_note or 'Accommodation estimate is based on illustrative local sample data.'} "
                    f"{flight_note} "
                    f"{budget_status_note(total=accommodation_cost + flight_cost, budget=request.budget, currency=request.currency, accommodation=accommodation_cost, flights=flight_cost, activities=0)} "
                    "The total is incomplete and should not be treated as a complete trip budget."
                ),
                accommodation_suggestions=[accommodation_suggestion] if accommodation_suggestion else [],
                travel_tips=[
                    "Add destination-matched attractions and source references to the local CSV files before generating this itinerary."
                ],
                days=[],
            ),
            [{"source": "Data coverage", "content": no_data_message}],
        )

    try:
        rag_context, sources = retrieve_context(query, k=5)
    except Exception as exc:
        # App remains usable if vector index/embedding setup is not ready; this is surfaced in sources.
        rag_context, sources = "RAG retrieval unavailable for this run. Use only other supplied context and be transparent.", []
        sources.append({"source": "RAG status", "content": str(exc)[:400]})
    chain = prompt | get_llm(provider) | parser
    itinerary = chain.invoke({
        "format_instructions": parser.get_format_instructions(),
        "request_json": json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2),
        "data_context": format_context(request.destination, request.origin),
        "rag_context": rag_context,
        "currency": request.currency,
        "flight_cost": f"{flight_cost:,.2f}",
        "flight_note": flight_note,
        "accommodation_cost": f"{accommodation_cost:,.2f}",
        "nights": nights,
        "rooms": rooms,
        "activity_budget": f"{activity_budget:,.2f}",
    })
    item_total = sum(a.estimated_cost for day in itinerary.days for a in day.activities)
    total = accommodation_cost + flight_cost + item_total
    itinerary.estimated_accommodation_cost = accommodation_cost
    itinerary.estimated_flight_cost = flight_cost
    itinerary.estimated_total_cost = total
    itinerary.requested_budget = request.budget
    itinerary.currency = request.currency
    itinerary.destination = request.destination
    notes = [itinerary.budget_notes]
    if accommodation_note:
        notes.append(accommodation_note)
    notes.append(flight_note)
    notes.append(
        budget_status_note(
            total=total,
            budget=request.budget,
            currency=request.currency,
            accommodation=accommodation_cost,
            flights=flight_cost,
            activities=item_total,
        )
    )
    if nights > 0 and not accommodation_suggestion:
        notes.append("Budget compliance cannot be confirmed because no matching accommodation estimate is available.")
    itinerary.budget_notes = " ".join(notes)
    if accommodation_suggestion:
        itinerary.accommodation_suggestions.insert(0, accommodation_suggestion)
    return itinerary, sources
