import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

DATA_FILE = os.path.join(os.path.dirname(__file__), '../data/bancomat.json')
CSV_FILE = os.path.join(os.path.dirname(__file__), '../data/bancomat.csv')

# Configurazione iniziale struttura multiutente
DEFAULT_DATA = {
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
}

PRELIEVO_GIORNALIERO_MAX = 500.0
TENTATIVI_MAX = 3
SESSION_TIMEOUT_MIN = 5

# Utility per caricare/salvare dati

def carica_dati():
    if not os.path.exists(DATA_FILE):
        salva_dati(DEFAULT_DATA)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def salva_dati(data):
    dir_path = os.path.dirname(DATA_FILE)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def user_exists(username):
    data = carica_dati()
    return any(u['username'] == username for u in data['users'])

def get_user(username, data=None):
    if data is None:
        data = carica_dati()
    for u in data['users']:
        if u['username'] == username:
            return u
    return None

def registra_utente(username, pin):
    data = carica_dati()
    nuovo_utente = {
        "username": username,
        "pin": pin,
        "saldo": 0.0,
        "storico": [],
        "tentativi": 0,
        "bloccato": False,
        "ultimo_accesso": None,
        "prelievi_oggi": 0.0,
        "data_prelievo": None
    }
    data['users'].append(nuovo_utente)
    salva_dati(data)

# Funzioni richieste per utente

def verifica_pin(username: str, pin: str) -> bool:
    data = carica_dati()
    user = get_user(username)
    if not user:
        return False
    if user["bloccato"]:
        return False
    if pin == user["pin"]:
        user["tentativi"] = 0
        user["ultimo_accesso"] = datetime.now().isoformat()
        salva_dati(data)
        return True
    else:
        user["tentativi"] += 1
        if user["tentativi"] >= TENTATIVI_MAX:
            user["bloccato"] = True
        salva_dati(data)
        return False

def get_saldo(username: str) -> float:
    user = get_user(username)
    return user["saldo"] if user else 0.0

def preleva(username: str, importo: float) -> bool:
    data = carica_dati()
    user = get_user(username, data)
    if not user:
        return False
    oggi = datetime.now().date()
    data_prelievo = user["data_prelievo"]
    if data_prelievo is None or datetime.fromisoformat(data_prelievo).date() != oggi:
        user["prelievi_oggi"] = 0.0
        user["data_prelievo"] = oggi.isoformat()
    if importo <= 0 or importo % 5 != 0:
        return False
    if importo > user["saldo"]:
        return False
    if user["prelievi_oggi"] + importo > PRELIEVO_GIORNALIERO_MAX:
        return False
    user["saldo"] -= importo
    user["prelievi_oggi"] += importo
    registra_operazione(username, "Prelievo", importo, datetime.now(), data)
    salva_dati(data)
    return True

def versa(username: str, importo: float) -> bool:
    data = carica_dati()
    user = get_user(username, data)
    if not user or importo <= 0:
        return False
    user["saldo"] += importo
    registra_operazione(username, "Versamento", importo, datetime.now(), data)
    salva_dati(data)
    return True

def cambia_pin(username: str, pin_vecchio: str, pin_nuovo: str) -> bool:
    data = carica_dati()
    user = get_user(username, data)
    if not user or pin_vecchio != user["pin"] or len(pin_nuovo) != 4 or not pin_nuovo.isdigit():
        return False
    user["pin"] = pin_nuovo
    registra_operazione(username, "Cambio PIN", 0.0, datetime.now(), data)
    salva_dati(data)
    return True

def get_storico(username: str) -> List[Dict]:
    user = get_user(username)
    return user["storico"][-10:][::-1] if user else []

def registra_operazione(username: str, tipo: str, importo: float, data_op: datetime, data=None) -> None:
    if data is None:
        data = carica_dati()
    user = get_user(username)
    if not user:
        return
    user["storico"].append({
        "tipo": tipo,
        "importo": importo,
        "data": data_op.strftime("%Y-%m-%d %H:%M:%S")
    })
    salva_dati(data)

def logout() -> None:
    pass  # Gestito da Flask session

def esporta_storico_csv(username: str):
    user = get_user(username)
    if not user:
        return
    df = pd.DataFrame(user["storico"])
    df.to_csv(CSV_FILE, index=False)

def bonifico(mittente: str, destinatario: str, importo: float) -> str:
    if mittente == destinatario:
        return "Non puoi inviare un bonifico a te stesso."
    data = carica_dati()
    user_from = get_user(mittente, data)
    user_to = get_user(destinatario, data)
    if not user_to:
        return "Destinatario non trovato."
    if not user_from or importo <= 0:
        return "Importo non valido."
    if user_from["saldo"] < importo:
        return "Saldo insufficiente."
    user_from["saldo"] -= importo
    user_to["saldo"] += importo
    registra_operazione(mittente, f"Bonifico inviato a {destinatario}", importo, datetime.now(), data)
    registra_operazione(destinatario, f"Bonifico ricevuto da {mittente}", importo, datetime.now(), data)
    salva_dati(data)
    return "OK"
