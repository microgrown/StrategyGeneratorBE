import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def save(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)


def get(key, default=None):
    return load().get(key, default)


def set(key, value):
    data = load()
    data[key] = value
    save(data)
