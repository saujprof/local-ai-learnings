# Tools


search_flights = {
    "type": "function",
    "function": {
        "name": "search_flights",
        "description": "searches flight between 2 destination",
        "parameters": {
            "from": "string",
            "to":"string",
            "date": {
                "day": "number",
                "month": "number",
                "year": "number",
            },
        }
    }
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
            "city": "string"
        }
    }
}
calculate_cost = {
    "type": "function",
    "function": {
        "name": "calculate_cost",
        "description": "calculates total cost of trip",
        "parameters": {
            "flight_cost": "number",
            "hotel_cost": "number",
        }
    }
}