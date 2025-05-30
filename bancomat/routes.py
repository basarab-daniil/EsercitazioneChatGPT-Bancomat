from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime, timedelta
from .bank import (
    verifica_pin, get_saldo, preleva, versa, cambia_pin, get_storico, esporta_storico_csv, user_exists, registra_utente
)
from bancomat.utils import carica_dati_json, salva_dati_json
import os

bancomat_bp = Blueprint('bancomat', __name__)

DATA_PATH = './data/bancomat.json'

def get_user():
    username = session.get('username')
    if not username:
        return None
    data = carica_dati_json(DATA_PATH, {})
    for user in data.get('users', []):
        if user['username'] == username:
            return user
    return None

def update_user(user):
    data = carica_dati_json(DATA_PATH, {})
    data[user['username']] = user
    salva_dati_json(DATA_PATH, data)

@bancomat_bp.before_request
def session_timeout():
    if 'logged_in' in session:
        now = datetime.now()
        if 'last_activity' in session and (now - session['last_activity']).total_seconds() > 300:
            session.clear()
            flash('Sessione scaduta. Effettua di nuovo il login.', 'warning')
            return redirect(url_for('bancomat.login'))
        session['last_activity'] = now

@bancomat_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pin = request.form.get('pin', '').strip()
        conferma_pin = request.form.get('conferma_pin', '').strip()
        if not username or not pin or not conferma_pin:
            flash('Tutti i campi sono obbligatori.', 'danger')
        elif pin != conferma_pin:
            flash('I PIN non coincidono.', 'danger')
        elif len(pin) != 4 or not pin.isdigit():
            flash('Il PIN deve essere di 4 cifre.', 'danger')
        elif user_exists(username):
            flash('Username già registrato.', 'danger')
        else:
            registra_utente(username, pin)
            flash('Registrazione avvenuta con successo! Effettua il login.', 'success')
            return redirect(url_for('bancomat.login'))
    return render_template('register.html')

@bancomat_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        pin = request.form.get('pin', '').strip()
        if verifica_pin(username, pin):
            session['logged_in'] = True
            session['username'] = username
            session['last_activity'] = datetime.now()
            return redirect(url_for('bancomat.dashboard'))
        else:
            flash('PIN errato, utente bloccato o non esistente.', 'danger')
    return render_template('login.html')

@bancomat_bp.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    saldo = get_saldo(session['username'])
    from .bank import get_storico
    storico = get_storico(session['username'])
    # Genera labels e saldo_settimanale fittizi o reali
    import datetime
    today = datetime.date.today()
    labels = [(today - datetime.timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
    saldo_settimanale = [saldo for _ in range(7)]  # Sostituire con dati reali se disponibili
    return render_template('dashboard.html', saldo=saldo, labels=labels, saldo_settimanale=saldo_settimanale, storico=storico)

@bancomat_bp.route('/preleva', methods=['GET', 'POST'])
def preleva_view():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    if request.method == 'POST':
        importo = request.form.get('importo', '0')
        from .bank import preleva
        esito, messaggio = preleva(session['username'], importo)
        if esito:
            flash(messaggio, 'success')
        else:
            flash(messaggio, 'danger')
        return redirect(url_for('bancomat.dashboard'))
    return render_template('preleva.html')

@bancomat_bp.route('/versa', methods=['GET', 'POST'])
def versa_view():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    if request.method == 'POST':
        try:
            importo = float(request.form.get('importo', '0'))
        except ValueError:
            flash('Importo non valido.', 'danger')
            return redirect(url_for('bancomat.versa_view'))
        if versa(session['username'], importo):
            flash(f'Versamento di €{importo:.2f} effettuato con successo.', 'success')
        else:
            flash('Versamento non valido.', 'danger')
        return redirect(url_for('bancomat.dashboard'))
    return render_template('versa.html')

@bancomat_bp.route('/storico')
def storico():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    storico = get_storico(session['username'])
    return render_template('storico.html', storico=storico)

@bancomat_bp.route('/cambia_pin', methods=['GET', 'POST'])
def cambia_pin_view():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    if request.method == 'POST':
        pin_vecchio = request.form.get('pin_vecchio', '')
        pin_nuovo = request.form.get('pin_nuovo', '')
        if cambia_pin(session['username'], pin_vecchio, pin_nuovo):
            flash('PIN cambiato con successo.', 'success')
            return redirect(url_for('bancomat.dashboard'))
        else:
            flash('Cambio PIN non riuscito. Controlla i dati inseriti.', 'danger')
    return render_template('cambia_pin.html')

@bancomat_bp.route('/logout')
def logout_view():
    session.clear()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('bancomat.login'))

@bancomat_bp.route('/esporta_storico')
def esporta_storico():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    esporta_storico_csv(session['username'])
    path = os.path.join(os.path.dirname(__file__), '../data/bancomat.csv')
    return send_file(path, as_attachment=True)

@bancomat_bp.route('/bonifico', methods=['GET', 'POST'])
def bonifico_view():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    from .bank import bonifico, carica_dati
    utenti = [u['username'] for u in carica_dati()['users'] if u['username'] != session['username']]
    if request.method == 'POST':
        destinatario = request.form.get('destinatario', '').strip()
        try:
            importo = float(request.form.get('importo', '0'))
        except ValueError:
            flash('Importo non valido.', 'danger')
            return redirect(url_for('bancomat.bonifico_view'))
        esito = bonifico(session['username'], destinatario, importo)
        if esito == "OK":
            flash(f'Bonifico di €{importo:.2f} inviato a {destinatario}.', 'success')
            return redirect(url_for('bancomat.dashboard'))
        else:
            flash(esito, 'danger')
    return render_template('bonifico.html', utenti=utenti)

@bancomat_bp.route('/impostazioni', methods=['GET', 'POST'])
def impostazioni_view():
    if not session.get('logged_in'):
        return redirect(url_for('bancomat.login'))
    from .bank import imposta_limite_prelievo, cambia_pin, get_user
    messaggio = None
    if request.method == 'POST':
        if 'nuovo_limite' in request.form:
            esito, messaggio = imposta_limite_prelievo(session['username'], request.form.get('nuovo_limite', ''))
            flash(messaggio, 'success' if esito else 'danger')
        elif 'pin_vecchio' in request.form and 'pin_nuovo' in request.form:
            esito = cambia_pin(session['username'], request.form.get('pin_vecchio', ''), request.form.get('pin_nuovo', ''))
            if esito:
                flash('PIN cambiato con successo.', 'success')
            else:
                flash('Cambio PIN non riuscito. Controlla i dati inseriti.', 'danger')
    user = get_user(session['username'])
    limite = user.get('limite_prelievo', 5000.0)
    return render_template('impostazioni.html', limite=limite)
