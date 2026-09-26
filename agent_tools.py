# agent_tools.py
"""
Read-only tools for the multi-step agent.
Each tool has a schema (what Claude sees) and a function (what we run).
Functions take the tool input as keyword arguments and return a dict.
"""

import math
import os

import requests

from car import vm, refresh_vehicle_manager, get_address_from_coordinates

HTTP_HEADERS = {"User-Agent": "PersonalCarBot/1.0"}  # Required by Nominatim
NREL_API_KEY = os.getenv("NREL_API_KEY", "DEMO_KEY")  # DEMO_KEY is heavily rate limited
METERS_PER_MILE = 1609.34

# Full route shapes, kept here so Claude only has to pass a short route_id around
ROUTES = {}


def _vehicle():
    refresh_vehicle_manager()
    return list(vm.vehicles.values())[0]


# ---------- Car tools ----------

def get_battery_status():
    vehicle = _vehicle()
    return {
        "battery_percent": vehicle.ev_battery_percentage,
        "range_miles": vehicle.ev_driving_range,
    }


def get_lock_status():
    return {"locked": _vehicle().is_locked}


def get_car_location():
    vehicle = _vehicle()
    lat, lon = vehicle.location_latitude, vehicle.location_longitude
    return {
        "latitude": lat,
        "longitude": lon,
        "address": get_address_from_coordinates(lat, lon),
    }


# ---------- Trip tools ----------

def geocode_place(query):
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers=HTTP_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return {"error": f"No place found for '{query}'"}
    place = results[0]
    return {
        "name": place["display_name"],
        "latitude": float(place["lat"]),
        "longitude": float(place["lon"]),
    }


def _haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def plan_route(from_latitude, from_longitude, to_latitude, to_longitude):
    response = requests.get(
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{from_longitude},{from_latitude};{to_longitude},{to_latitude}",
        params={"overview": "full", "geometries": "geojson"},
        timeout=30,
    )
    response.raise_for_status()
    route = response.json()["routes"][0]
    total_miles = route["distance"] / METERS_PER_MILE

    # Mile marker for every point on the route, scaled to match OSRM's road distance
    points = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    miles = [0.0]
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        miles.append(miles[-1] + _haversine_miles(lat1, lon1, lat2, lon2))
    scale = total_miles / miles[-1] if miles[-1] else 1
    miles = [m * scale for m in miles]

    route_id = f"route_{len(ROUTES) + 1}"
    ROUTES[route_id] = {"points": points, "miles": miles}

    # A coarse checkpoint list so Claude can check weather along the way
    checkpoints, next_mile = [], 0
    for (lat, lon), mile in zip(points, miles):
        if mile >= next_mile:
            checkpoints.append({"mile": round(mile), "latitude": round(lat, 4), "longitude": round(lon, 4)})
            next_mile += 250
    return {
        "route_id": route_id,
        "distance_miles": round(total_miles),
        "driving_hours": round(route["duration"] / 3600, 1),
        "checkpoints_every_250_miles": checkpoints,
    }


def find_chargers_along_route(route_id, from_mile, to_mile, max_results=5):
    route = ROUTES.get(route_id)
    if route is None:
        return {"error": f"Unknown route_id '{route_id}'. Call plan_route first."}

    # The slice of the route inside the requested mile window, thinned to ~100 points
    window = [(p, m) for p, m in zip(route["points"], route["miles"]) if from_mile <= m <= to_mile]
    if len(window) < 2:
        return {"error": f"No route points between mile {from_mile} and {to_mile}."}
    window = window[:: max(1, len(window) // 100)]
    linestring = "LINESTRING(" + ",".join(f"{lon} {lat}" for (lat, lon), _ in window) + ")"

    response = requests.post(
        "https://developer.nlr.gov/api/alt-fuel-stations/v1/nearby-route.json",
        params={"api_key": NREL_API_KEY},
        data={
            "route": linestring,
            "distance": 5,  # miles either side of the road
            "fuel_type": "ELEC",
            "ev_charging_level": "dc_fast",
            "ev_connector_type": "J1772COMBO",  # CCS, the Ioniq's fast-charge plug
            "status": "E",  # open, not planned or closed
            "limit": 50,
        },
        timeout=30,
    )
    if response.status_code == 429:
        # Tell Claude what to do instead of retrying; the limit resets hourly
        return {"error": "Charger search is rate limited for the next hour. Do not retry; "
                         "plan with the chargers already found."}
    response.raise_for_status()

    chargers = []
    for station in response.json()["fuel_stations"]:
        # Mile marker of the route point nearest to this station
        _, mile = min(
            window,
            key=lambda pm: _haversine_miles(pm[0][0], pm[0][1], station["latitude"], station["longitude"]),
        )
        chargers.append({
            "name": station["station_name"],
            "city": f"{station['city']}, {station['state']}",
            "route_mile": round(mile),
            "miles_off_route": round(station.get("distance") or 0, 1),
            "network": station.get("ev_network"),
            "dc_fast_ports": station.get("ev_dc_fast_num"),
            "hours": station.get("access_days_time"),
        })

    # Prefer the biggest stations, then present them in driving order
    chargers.sort(key=lambda c: c["dc_fast_ports"] or 0, reverse=True)
    chargers = sorted(chargers[:max_results], key=lambda c: c["route_mile"])
    return {"found_in_window": len(response.json()["fuel_stations"]), "chargers": chargers}


def get_weather(latitude, longitude):
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,precipitation",
            "daily": "temperature_2m_min,temperature_2m_max",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
            "forecast_days": 1,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "temperature_f": data["current"]["temperature_2m"],
        "wind_mph": data["current"]["wind_speed_10m"],
        "precipitation_mm": data["current"]["precipitation"],
        "today_low_f": data["daily"]["temperature_2m_min"][0],
        "today_high_f": data["daily"]["temperature_2m_max"][0],
    }


# ---------- Registry ----------

TOOL_FUNCTIONS = {
    "get_battery_status": get_battery_status,
    "get_lock_status": get_lock_status,
    "get_car_location": get_car_location,
    "geocode_place": geocode_place,
    "plan_route": plan_route,
    "find_chargers_along_route": find_chargers_along_route,
    "get_weather": get_weather,
}

NO_INPUT = {"type": "object", "properties": {}, "required": []}

TOOLS = [
    {
        "name": "get_battery_status",
        "description": "Get the car's current battery percentage and the car's own estimated driving range in miles.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "get_lock_status",
        "description": "Check whether the car is currently locked.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "get_car_location",
        "description": "Get the car's current GPS coordinates and street address.",
        "input_schema": NO_INPUT,
    },
    {
        "name": "geocode_place",
        "description": "Look up the GPS coordinates of a place, city or address by name.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "e.g. 'San Francisco, CA'"}},
            "required": ["query"],
        },
    },
    {
        "name": "plan_route",
        "description": (
            "Plan a driving route between two coordinates. Returns the road distance, driving time, "
            "a route_id to use with find_chargers_along_route, and checkpoints every 250 miles."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_latitude": {"type": "number"},
                "from_longitude": {"type": "number"},
                "to_latitude": {"type": "number"},
                "to_longitude": {"type": "number"},
            },
            "required": ["from_latitude", "from_longitude", "to_latitude", "to_longitude"],
        },
    },
    {
        "name": "find_chargers_along_route",
        "description": (
            "Find open DC fast chargers with a CCS plug within 5 miles of a planned route, "
            "between two mile markers measured from the start of the route. "
            "Each charger includes its route_mile. Search a window of 100 miles or less."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "route_id": {"type": "string"},
                "from_mile": {"type": "number"},
                "to_mile": {"type": "number"},
                "max_results": {"type": "integer", "description": "default 5"},
            },
            "required": ["route_id", "from_mile", "to_mile"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather and today's low/high temperature (°F) at a coordinate.",
        "input_schema": {
            "type": "object",
            "properties": {"latitude": {"type": "number"}, "longitude": {"type": "number"}},
            "required": ["latitude", "longitude"],
        },
    },
]
