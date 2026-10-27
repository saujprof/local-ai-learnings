# Tools


search_flights = {
    "type": "function",
    "function": {
        "name": "search_flights",
        "description": "searches flight between 2 destination",
        "parameters": {
            "from": "string",
            "to": "string",
            "date": {
                "day": "number",
                "month": "number",
                "year": "number",
            },
        },
        "meta_data": {
            "read_only": True,
            "side_effecting": False,
            "parallel_safe": True,
            "idempotent": True,
            "requires_approval": False,
            "timeout_seconds": 5,
            "max_retries": 3,
        },
    },
}
search_hotels = {
    "type": "function",
    "function": {
        "name": "search_hotels",
        "description": "searches hotels in a city",
        "parameters": {
            "check_in": {
                "day": "number",
                "month": "number",
                "year": "number",
            },
            "check_out": {
                "day": "number",
                "month": "number",
                "year": "number",
            },
            "city": "string",
        },
        "meta_data": {
            "read_only": True,
            "side_effecting": False,
            "parallel_safe": False,
            "idempotent": True,
            "requires_approval": False,
            "timeout_seconds": 5,
            "max_retries": 3,
        },
    },
}

calculate_cost = {
    "type": "function",
    "function": {
        "name": "calculate_cost",
        "description": "calculates total cost of trip",
        "parameters": {
            "to_flight_cost": "number",
            "from_flight_cost": "number",
            "hotel_cost": "number",
        },
        "meta_data": {
            "read_only": True,
            "side_effecting": False,
            "parallel_safe": True,
            "idempotent": True,
            "requires_approval": False,
            "timeout_seconds": 2,
            "max_retries": 1,
        },
    },
}



def get_tool_key(key):
    if key == "search_flights":
        return search_flights
    if key == "search_hotels":
        return search_hotels
    if key == "calculate_cost":
        return calculate_cost