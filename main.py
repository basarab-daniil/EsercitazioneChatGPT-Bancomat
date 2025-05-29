from flask import Flask
from flask_session import Session
from bancomat.routes import bancomat_bp
from bancomat.init_data import ensure_bancomat_json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

# Assicurati che la cartella /data e il file bancomat.json esistano
ensure_bancomat_json()

# Registrazione blueprint
app.register_blueprint(bancomat_bp)

if __name__ == '__main__':
    app.run(debug=True)
