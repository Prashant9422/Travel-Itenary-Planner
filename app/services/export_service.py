import json
from app.schemas import Itinerary
from app.services.data_service import display_source_name

def itinerary_json(itinerary: Itinerary) -> str:
    return json.dumps(itinerary.model_dump(mode="json"), ensure_ascii=False, indent=2)

def itinerary_markdown(itinerary: Itinerary) -> str:
    activity_total = sum(a.estimated_cost for day in itinerary.days for a in day.activities)
    lines = [f"# {itinerary.destination} — Travel Itinerary", "", itinerary.trip_summary, "",
             f"**Estimated accommodation:** {itinerary.currency} {itinerary.estimated_accommodation_cost:,.2f}",
             f"**Estimated one-way flights:** {itinerary.currency} {itinerary.estimated_flight_cost:,.2f}",
             f"**Estimated activities:** {itinerary.currency} {activity_total:,.2f}",
             f"**Estimated trip total:** {itinerary.currency} {itinerary.estimated_total_cost:,.2f}", "",
             *(
                 [f"**Proposed budget:** {itinerary.currency} {itinerary.requested_budget:,.2f}", ""]
                 if itinerary.requested_budget is not None else []
             ),
             f"**Budget notes:** {itinerary.budget_notes}", "", "## Accommodation suggestions"]
    lines += [f"- {x}" for x in itinerary.accommodation_suggestions] or ["- No specific suggestions supplied."]
    for day in itinerary.days:
        lines += ["", f"## Day {day.day} — {day.date}: {day.title}"]
        for a in day.activities:
            lines.append(f"- **{a.time} — {a.name}** ({itinerary.currency} {a.estimated_cost:,.2f}; {a.category}) — {a.description} _Source: {display_source_name(a.source)}_")
    lines += ["", "## Travel tips"] + [f"- {x}" for x in itinerary.travel_tips]
    lines += ["", "> Prices and availability are estimates, not live quotes. Verify with providers before booking."]
    return "\n".join(lines)
