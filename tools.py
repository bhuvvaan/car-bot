# tools.py
"""
Tool definitions for Claude to interact with the car.
Each tool maps to a Bluelink operation.
"""

tools = [
    {
        "name": "get_battery_status",
        "description": "Get the current battery percentage and estimated range of the car",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_lock_status",
        "description": "Check if the car is currently locked or unlocked. It can also be used to get the last know location of the car",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
     {
        "name": "lock_car",
        "description": "Remotely lock the car, ONLY use if the user asks to lock it explicitly.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "unlock_car",
        "description": "Remotely unlock the car, ONLY use if the user asks to unlock it explicitly.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }

]