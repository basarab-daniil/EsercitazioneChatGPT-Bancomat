import os
import json

def ensure_data_dir():
    data_dir = os.path.join(os.path.dirname(__file__), '../data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def ensure_bancomat_json():
    data_dir = ensure_data_dir()
    data_file = os.path.join(data_dir, 'bancomat.json')
    if not os.path.exists(data_file):
        with open(data_file, 'w') as f:
            json.dump({
                "users": [
                    {
                        "username": "demo",
                        "pin": "1234",
                        "saldo": 1000.0,
                        "storico": [],
                        "tentativi": 0,
                        "bloccato": False,
                        "ultimo_accesso": None,
                        "prelievi_oggi": 0.0,
                        "data_prelievo": None
                    }
                ]
            }, f, indent=2)

# Chiamare questa funzione all'avvio dell'applicazione
