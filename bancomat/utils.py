import json
import os

def carica_dati_json(path, default):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default, f, indent=2)
    with open(path, 'r') as f:
        return json.load(f)

def salva_dati_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
