"""Borrow code from https://github.com/bananaml/banana-python-sdk pending dependency conflict resolution."""

import time
from uuid import uuid4

import requests

ENDPOINT = "https://api.banana.dev/"


def start(api_key, model_key, model_inputs):
    """Start a model transaction."""
    route_start = "start/v4/"
    url_start = ENDPOINT + route_start

    payload = {
        "id": str(uuid4()),
        "created": int(time.time()),
        "apiKey": api_key,
        "modelKey": model_key,
        "modelInputs": model_inputs,
        "startOnly": True,
    }

    response = requests.post(url_start, json=payload)

    if response.status_code != 200:
        raise Exception("server error: status code {}".format(response.status_code))

    try:
        out = response.json()
    except Exception:
        raise Exception("server error: returned invalid json")

    if "error" in out["message"].lower():
        raise Exception(out["message"])

    return out["callID"]


def check(api_key, call_id):
    """Check status of a model transaction."""
    route_check = "check/v4/"
    url_check = ENDPOINT + route_check

    payload = {
        "id": str(uuid4()),
        "created": int(time.time()),
        "longPoll": True,
        "callID": call_id,
        "apiKey": api_key
    }
    response = requests.post(url_check, json=payload)

    if response.status_code != 200:
        raise Exception("server error: status code {}".format(response.status_code))

    try:
        out = response.json()
    except Exception:
        raise Exception("server error: returned invalid json")

    if "error" in out["message"].lower():
        raise Exception(out["message"])
    return out
