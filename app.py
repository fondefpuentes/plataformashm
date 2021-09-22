from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_table import Table, Col
from flask_login import LoginManager
from flask_mail import Mail, Message
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output,State
from datetime import datetime as dt
import time
import pandas as pd
import plotly.graph_objects as go
import collections
import plotly.express as px
import dash_bootstrap_components as dbc
import pytz
import tzlocal 
import atexit
from datetime import timedelta as delta
from datetime import datetime as dt
# from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler
from views import views_api
from models import db, Usuario, AnomaliaPorHora, EstadoDanoSensor, SensorInstalado, DescripcionSensor, Estructura, ConfiguracionModeloAR
from ModeloAR.batch_job_last_hour import hourly_batch_job
from ModeloAR.modelo import propagation, aplicar_modelo, deleteFirstReporteDano, addAnomallyAll


app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='')
app.config.from_pyfile('config.py')
app.config.update(
  MAIL_SERVER = 'smtp.gmail.com',
  MAIL_PORT = 465,
  MAIL_USE_SSL = True,
  MAIL_USERNAME = "plataforma.shm.chile@gmail.com",
  MAIL_PASSWORD = "vewtbinxfhhjsfea",
)

mail = Mail(app)

db.init_app(app)
app.register_blueprint(views_api)

with app.app_context():
  db.create_all()

### SCHEDULER ###

scheduler = APScheduler()
# if you don't wanna use a config, you can set options here:
# scheduler.api_enabled = True
scheduler.init_app(app)

@scheduler.task('interval', id='actualizar_estados', seconds=60*60)
def actualizar_estados():
    print(time.strftime("%d. %B %Y %H:%M:%S"))
    executing = True
    while executing:
        try:
            with scheduler.app.app_context():
                pathsensor = '/home/ubuntu/serverflask/plataformashm/ModeloAR/Datos'
                Local = pytz.timezone('America/Santiago')
                tiempo_extraccion = dt.now(Local) - delta(hours = 1)
                puentes = db.session.query(Estructura.id).filter(Estructura.en_monitoreo == True).all()
                for file in os.listdir(pathsensor):
                    file_path = os.path.join(pathsensor, file)
                    os.remove(file_path)
                for puente in puentes:
                    config = ConfiguracionModeloAR.query.filter_by(id_estructura = puente.id).first()
                    sensores = db.session.query(SensorInstalado.id.label("si"), DescripcionSensor.descripcion.label("nombre_sensor")).filter(SensorInstalado.id_estructura == puente.id, DescripcionSensor.id_sensor_instalado == SensorInstalado.id).order_by(SensorInstalado.id.asc())
                    if(config.actualizacion_completa):
                        print('Se actualiza todo')
                        config.actualizacion_completa = False
                        db.session.commit()
                    else:
                        hourly_batch_job(pathsensor, sensores)
                        aplicar_modelo(tiempo_extraccion, tiempo_extraccion.hour, puente.id, sensores, False)
                        addAnomallyAll(puente.id, sensores)
                propagation()
                executing = False
        except:
            db.session.rollback()
            time.sleep(3)
            executing = True

# if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true': # Se ejecuta cuando la app no esta en modo debug o en una rama principal (para evitar doble ejecucion)
# scheduler = BackgroundScheduler()
# scheduler.daemonic = False
# scheduler.add_job(func=actualizar_estados, trigger="interval", seconds=60)

scheduler.start()
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

login_manager = LoginManager()
login_manager.login_view = 'views_api.login'
login_manager.init_app(app)

def datetimefilter(value, format="%Y-%m-%d %H:%M:%S"):
  tz = pytz.timezone('America/Santiago') # timezone you want to convert to from UTC
  utc = pytz.timezone('UTC')  
  value = utc.localize(value, is_dst=None).astimezone(pytz.utc)
  local_dt = value.astimezone(tz)
  return local_dt.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter

@login_manager.user_loader
def load_user(user_id):
  return Usuario.query.get(user_id)

@app.route('/password_reset', methods=["GET", "POST"])
def password_reset():
  if request.method == "GET":
    return render_template('password_reset.html')
  if request.method == "POST":
    email = request.form.get("email")
    user = Usuario.verify_email(email)
    if user:
        token = user.get_reset_token()
        msg = Message()
        msg.subject = "[Plataforma SHM] Reestablecer contraseña"
        msg.sender = app.config['MAIL_USERNAME']
        msg.recipients = [user.id]
        msg.html = render_template('reset_email.html', user=user, token=token)
        mail.send(msg)
    return redirect(url_for('views_api.login'))

@app.errorhandler(404)
def page_not_found(e):
  return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=False, use_reloader=False)
