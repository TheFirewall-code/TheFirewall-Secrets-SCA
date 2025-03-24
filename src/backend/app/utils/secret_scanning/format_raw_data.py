import json
import urllib.parse


def format_raw_data(raw_data: bytes) -> dict:
    try:
        # Attempt to load raw data as JSON
        raw_data_json = json.loads(raw_data)
    except json.JSONDecodeError:
        # Decode URL-encoded data if JSON loading fails
        decoded_data = urllib.parse.unquote(raw_data.decode('utf-8'))
        if decoded_data.startswith("payload="):
            decoded_data = decoded_data[len("payload="):]
        raw_data_json = json.loads(decoded_data)

    return raw_data_json
