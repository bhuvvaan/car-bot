# agent_tools.py
"""
Read-only tools for the multi-step agent.
Each tool has a schema (what Claude sees) and a function (what we run).
Functions take the tool input as keyword arguments and return a dict.
"""

from car import vm, refresh_vehicle_manager, get_address_from_coordinates


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


# ---------- Registry ----------

TOOL_FUNCTIONS = {
    "get_battery_status": get_battery_status,
    "get_lock_status": get_lock_status,
    "get_car_location": get_car_location,
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
]
