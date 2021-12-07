from flask import Blueprint, render_template, session, flash, request, redirect, url_for, send_file, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import *
from flask_login import login_user, login_required, current_user, logout_user
import sys
import sqlalchemy
from sqlalchemy import or_
import json
import os
from datetime import datetime
import unidecode
import boto3
import aws_functions
import swagger
import pytz
import requests
from ModeloAR.modelo import *
from ModeloAR.data import *
from ModeloAR.visualization import *

views_api = Blueprint('views_api',__name__)

#Función que, dado el id de un puente, obtiene el tipo de activo (Puente, paso nivel, etc..) y nombre (Llacolén, Chacabuco, etc...), y los entrega a las rutas definidas
def obtener_nombre_y_activo(id_puente):
    puente = Estructura.query.filter_by(id=id_puente).all()[0]
    nombre_puente = puente.nombre.capitalize()
    tipo_activo = puente.tipo_activo.lower()
    res = {
        'nombre_puente' : nombre_puente,
        'tipo_activo' : tipo_activo
    }
    return res

#Función que, dada una lista de canales, remueve aquellos que están ocupados, y entrega una lista de canales disponibles 
def revisar_disponibilidad_canales(canales, ocupados):
    res = []
    for i in canales:
        if i in (canales and ocupados):
            res.append((i[0], i[1], i[2], True))
        else:
            res.append((i[0], i[1], i[2], False))
    res.sort(key=lambda tup: tup[0])
    return res

#Función que, dado un sensor instalado y un nombre para la nueva tabla, genera la hypertable respectiva
def crear_tabla_sensor(id_sensor_instalado, nombre_nueva_tabla):
    actualizar_nombre_sensor = SensorInstalado.query.filter_by(id=id_sensor_instalado).first()
    actualizar_nombre_sensor.nombre_tabla = nombre_nueva_tabla
    db.session.add(actualizar_nombre_sensor)
    new_table = db.session.execute('CREATE TABLE IF NOT EXISTS '+nombre_nueva_tabla+'(fecha timestamp, lectura double precision, PRIMARY KEY(fecha))')
    new_hypertable = db.session.execute('SELECT create_hypertable(\''+nombre_nueva_tabla+'\', \'fecha\')')
    db.session.commit()
    
#PERMISOS = TODOS
#Redirige a la vista de Login (si no inicia sesión), o a la vista del mapa (profile.html, si inició sesión)
@views_api.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.profile'))
    else:
        return render_template('login.html')

#PERMISOS = TODOS
#Requiere login para entrar, muestra todos los puentes en un mapa generado con Leaflet y MarkerCluster (JS)
@views_api.route('/profile')
@login_required
def profile():
    #Estructura: id, region, provincia, nombre, en_monitoreo
    #EstadoDano: fecha y estado,
    #Estado: fecha_estado,estado,seguridad
    puentes = db.session.query(Estructura.id, Estructura.nombre, Estructura.region, Estructura.en_monitoreo, EstadoEstructura.fecha_estado, EstadoEstructura.estado, EstadoEstructura.seguridad, EstadoDanoEstructura.estado.label('estado_dano') , EstadoDanoEstructura.diahora_calculo).filter(EstadoEstructura.id_estructura == Estructura.id, EstadoDanoEstructura.id_estructura == Estructura.id).order_by(Estructura.id,EstadoEstructura.fecha_estado.desc()).distinct(Estructura.id).all()

    #Variables para el template
    context = {
        'puentes' : puentes
    }
    return render_template('profile.html', **context)


#PERMISOS = TODOS
#En caso de error, redirige a esta paǵina
@views_api.route('/acceso_restringido')
def usuario_no_autorizado():
    return render_template('usuario_no_autorizado.html')


#PERMISOS = Administrador
#Crea el schema para el monitoreo de un puente, solo el admin. puede usarla
@views_api.route('/crear_monitoreo/<int:id_puente>', methods=['POST'])
@login_required
def crear_monitoreo(id_puente):
    if(current_user.permisos == 'Administrador'):
        
        estructura = Estructura.query.filter_by(id=id_puente).first()
        ip_request = request.form.get('ip')
        user = request.form.get('user')
        password = request.form.get('pass')
        if(ip_request == None or user == None or password == None):
          flash("Error al conectar con Thingsboard",'error')
          return redirect(url_for('views_api.administrar_monitoreos'))
  
        #obtencion API KEY de TB    
        api_key_url = requests.post(
        ip_request + '/api/auth/login',
        data='{"username":"tenant@thingsboard.org", "password":"tenant"}', headers={'Content-Type': 'application/json','Accept': 'application/json'})
        json_response = api_key_url.json()
        
        #Generacion de API_KEY para autentificacion en Swagger
        x_auth = 'Bearer ' + json_response['token']
  
        #obtencion tipos de sensor desde BD
        t_sensor = TipoSensor.query.all()
        t_s_dict = {}
        for i in t_sensor:
          t_s_dict[i.nombre] = i.id
  
        #obtencion tipos de zona desde DB
        t_zona = TipoElemento.query.all()
        t_z_dict = {}
        for i in t_zona:
          t_z_dict[i.nombre_zona] = i.id
  
        zonas_dict = {}
        #Peticion a Swagger de DEVICES
        response = requests.get( ip_request + '/api/tenant/deviceInfos?pageSize=20&page=0',headers={'Accept' : 'application/json','X-Authorization': x_auth},)
        json_devices = response.json()
        sensores_dict = {}
        daq_dict = {}
        #insercion de nuevas zonas a BD
        try:
  
          #insercion DAQs 
          canales_bd = {}
          for i in json_devices['data']:
            if(i['type'] == "daq"):
              #obtencion atributos del DAQ
              attr_request = requests.get(ip_request + '/api/plugins/telemetry/DEVICE/' + str(i['id']['id'])+'/values/attributes',headers={'Accept' : 'application/json','X-Authorization': x_auth})
              attr_response = attr_request.json()
              chns = 0
              zona = ""
              
              for attr in attr_response:
                if(attr['key'] == "Canales"):
                  chns = attr['value']
                if(attr['key'] == "Elemento Estructural"):
                  zona = attr['value']
                  if not zona in zonas_dict:
                    nueva_zona = ElementoEstructural(id_estructura=id_puente,tipo_zona=t_z_dict['Tablero'],descripcion=zona)
                    db.session.add(nueva_zona)
                    db.session.flush()
                    zonas_dict[zona] = nueva_zona.id
              
              nuevo_daq = DAQ(nro_canales=chns)
              db.session.add(nuevo_daq)
              db.session.flush()
              zona_daq = DAQPorZona(id_daq=nuevo_daq.id, id_zona=zonas_dict[zona], id_estructura=id_puente)
              db.session.add(zona_daq)
              caract = DescripcionDAQ(id_daq=nuevo_daq.id, caracteristicas=i['name'])
              db.session.add(caract)
              estado_nuevo_daq = EstadoDAQ(id_daq=nuevo_daq.id, fecha_estado=datetime.now(), detalles='Conectado')
              db.session.add(estado_nuevo_daq)
              canales = []
              for i in range(1,int(chns)+1):
                x = Canal(id_daq=nuevo_daq.id, numero_canal=i)
                db.session.add(x)
                db.session.flush()
                canales_bd[x.numero_canal] = x.id


          #insercion sensores 
          for i in json_devices['data']:
            if(i['type'] != "daq"):
              #obtencion atributos del sensor
              attr_request = requests.get(ip_request + '/api/plugins/telemetry/DEVICE/' + str(i['id']['id'])+'/values/attributes',headers={'Accept' : 'application/json','X-Authorization': x_auth})
              attr_response = attr_request.json()
              zona = ""
              canal = 0
              frecuencia = 0

              for attr in attr_response:
                if(attr['key'] == "Elemento Estructural"):
                  zona = attr['value']
                  if not zona in zonas_dict:
                    nueva_zona = ElementoEstructural(id_estructura=id_puente,tipo_zona=t_z_dict['Tablero'],descripcion=zona)
                    db.session.add(nueva_zona)
                    db.session.flush()
                    zonas_dict[zona] = nueva_zona.id
                if(attr['key'] == "Canal"):
                  canal = attr['value']
                if(attr['key'] == "Frecuencia"):
                  frecuencia = attr['value']

                  
              nuevo_sensor = Sensor(tipo_sensor = t_s_dict[i['type']],frecuencia = frecuencia, uuid_device = i['id']['id'])
              nueva_instalacion_sensor = InstalacionSensor(fecha_instalacion=datetime.now())
              db.session.add(nueva_instalacion_sensor)
              db.session.add(nuevo_sensor)
              db.session.flush()
              nuevo_sensor_instalado = SensorInstalado(id_instalacion=nueva_instalacion_sensor.id,conexion_actual = canales_bd.get(canal),id_sensor=nuevo_sensor.id, id_zona=zonas_dict[zona], id_estructura=id_puente, es_activo=True)
              db.session.add(nuevo_sensor_instalado)
              db.session.flush()
              nueva_descripcion = DescripcionSensor(id_sensor_instalado = nuevo_sensor_instalado.id,descripcion = i['name'])
              db.session.add(nueva_descripcion)
              db.session.flush()   

          estructura.en_monitoreo = True
          estructura.ip_instancia = ip_request
          db.session.add(estructura)
          db.session.commit()
           
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
          db.session.rollback()
          flash(str(error.orig) + " for parameters" + str(error.params),'error')
          return redirect(url_for('views_api.administrar_monitoreos'))

        flash("Monitoreo iniciado exitosamente", 'info')
        return redirect(url_for('views_api.administrar_monitoreos'))
    else:
        #Si el usuario no está autorizado, redirige a la vista de error
        return redirect(url_for('views_api.usuario_no_autorizado'))

#Maneja el inicio de sesión, con ayuda del package "flask_login"
@views_api.route('/login', methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.profile'))
    else:
        if(request.method == "GET"):
            return render_template('login.html')
        elif(request.method == "POST"):
            mail = request.form.get('email')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            user = Usuario.query.filter_by(id=mail).first()
            if not user or not check_password_hash(user.contrasena, password):
                flash('Contraseña o nombre de usuario no existe.')
                return redirect(url_for('views_api.login'))
            login_user(user,remember=remember)
            return redirect(url_for('views_api.profile'))
        else:
            return redirect(url_for('views_api.usuario_no_autorizado'))

#Crea nuevos usuarios en la plataforma, requiere de correo (primary_key), nombre, apellido y permisos
@views_api.route('/signup', methods=["GET","POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('views_api.usuario_no_autorizado'))
    else:
        if(request.method == "GET"):
            return render_template('signup.html')
        elif(request.method == "POST"):
            first_name = request.form.get('firstname')
            last_name = request.form.get('lastname')
            mail = request.form.get('mail')
            password = request.form.get('password')
            user = Usuario.query.filter_by(id=mail).first()
            if user:
                flash('Dirección de correo electrónico ya está registrada.')
                return redirect(url_for('views_api.signup'))
            elif len(password) < 8:
                flash('Contraseña debe ser al menos 8 caracteres.')
                return redirect(url_for('views_api.signup'))
            
            new_user = Usuario(id=mail,nombre=first_name,apellido=last_name,contrasena=generate_password_hash(password),permisos="Visita")
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('views_api.login'))
           

#Cerrar sesión
@views_api.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('login.html')

#PERMISOS = TODOS
#Muestra el detalle de una estructura, dado el id del puente en la BD
@views_api.route('/estructura/<int:id>')
@login_required
def informacion_estructura(id):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    esta_monitoreada = estructura.en_monitoreo
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    
    sensores = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo, DescripcionSensor.descripcion.label("nombre_sensor"),EstadoSensor.fecha_estado.label("fecha123"),EstadoSensor.confiabilidad, EstadoSensor.operatividad, EstadoSensor.mantenimiento,DescripcionDAQ.caracteristicas, DAQPorZona.id_daq, EstadoDanoSensor.diahora_calculo, EstadoDanoSensor.estado).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, EstadoSensor.id_sensor_instalado == SensorInstalado.id,SensorInstalado.conexion_actual == Canal.id, Canal.id_daq == DAQPorZona.id_daq, DescripcionDAQ.id_daq == DAQPorZona.id_daq, EstadoDanoSensor.id_sensor_instalado == SensorInstalado.id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc(),EstadoSensor.fecha_estado.desc(),EstadoDanoSensor.diahora_calculo.desc()).all()
    
    daqs = db.session.query(DAQPorZona.id_daq, DAQPorZona.id_zona, DescripcionDAQ.caracteristicas, EstadoDAQ.fecha_estado, EstadoDAQ.operatividad, EstadoDAQ.mantenimiento, ElementoEstructural.descripcion).filter(DAQPorZona.id_estructura == id, DAQPorZona.id_daq == EstadoDAQ.id_daq, DAQPorZona.id_daq == DescripcionDAQ.id_daq,DAQPorZona.id_zona == ElementoEstructural.id).order_by(DAQPorZona.id_daq, EstadoDAQ.fecha_estado.desc()).distinct(DAQPorZona.id_daq).all()
    ultimo_estado = EstadoEstructura.query.filter_by(id_estructura=id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    estado_dano = EstadoDanoEstructura.query.filter_by(id_estructura=id).first()
    
    session['id_puente'] = id
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura':bim_estructura,
        'sensores':sensores,
        'daqs' : daqs,
        'estado': ultimo_estado,
        'estado_dano': estado_dano,
        'title' : "Perfil " + estructura.nombre.capitalize()
    }
    return render_template('tabla_estructura.html', **context)

#PERMISOS = TODOS
#Muestra el detalle de las zonas en una estructura
@views_api.route('/zonas_estructura/<int:id>')
@login_required
def zonas_de_estructura(id):
    zonas = db.session.query(ElementoEstructural.id, ElementoEstructural.descripcion, ElementoEstructural.material, TipoElemento.nombre_zona).filter(ElementoEstructural.tipo_zona == TipoElemento.id, ElementoEstructural.id_estructura==id).all()
    context = {
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'zonas_puente' : zonas
    }
    return render_template('zonas_puente.html',**context)

#PERMISOS = TODOS
#Obtiene el detalle de los sensores instalados actualmente
@views_api.route('/sensores_estructura/<int:id>')
@login_required
def sensores_de_estructura(id):
    sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
    context = {
        'id_puente' : id,
        'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
        'sensores_puente' : sensores_actuales
    }
    return render_template('sensores_puente.html',**context)

#PERMISOS = Administrador, dueño
#Método que permite gestionar estados en una estructura
@views_api.route('/gestion_estado/<int:id>', methods=["GET", "POST"])
@login_required
def gestion_estado(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Dueño'):
        
        if(request.method == "GET"):
            estructura = Estructura.query.filter_by(id=id).first()
            esta_monitoreada = estructura.en_monitoreo
            #Se guarda momentaneamente el id del puente en la sesión actual
            session['id_puente'] = id
            estados = EstadoEstructura.query.filter_by(id_estructura=id).order_by(EstadoEstructura.fecha_estado.desc()).all()
            context = {
                'id_puente' : id,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'datos_puente' : estructura,
                'esta_monitoreada':esta_monitoreada,
                'historial': estados,
                'title' : "Gestión Estados " + estructura.nombre.capitalize()
            }
            return render_template('gestion_estado.html',**context)
        #En POST se envia lo ingresado via formulario, para guardar en la BD
        elif(request.method == "POST"):
            estado_global = request.form.get('globalRadio')
            nivel_seguridad = request.form.get('seguridadRadio')
            detalles_estado = request.form.get('detalles')
            try:
                nuevo_estado = EstadoEstructura(id_estructura=id,fecha_estado=datetime.now(),estado=estado_global,seguridad=nivel_seguridad,detalles=detalles_estado)
                db.session.add(nuevo_estado)
                db.session.commit()
            #En caso de ocurrir un fallo, se hace un rollback()
            except:
                db.session.rollback()
                raise
            #Finalmente, se redirige al listado de sensores disponibles
            finally:
                return redirect(url_for('views_api.gestion_estado',id=session['id_puente']))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/detalle_sensor/<int:id_sensor>', methods=["GET", "POST"])
@login_required
def detalle_sensor(id_sensor):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Dueño' or current_user.permisos == 'Analista'):
        
        if(request.method == "GET"):
            
            #sensor = SensorInstalado.query.filter_by(id=id_sensor).first()
            info_sensor = db.session.query(Sensor.id, SensorInstalado.id.label("siid"), SensorInstalado.id_estructura, Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, DescripcionSensor.descripcion.label("nombre_sensor"), DescripcionDAQ.caracteristicas, Sensor.uuid_device, Canal.numero_canal, DescripcionDAQ.id_daq).filter(SensorInstalado.id == id_sensor, TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona,  DescripcionSensor.id_sensor_instalado == SensorInstalado.id, SensorInstalado.conexion_actual == Canal.id, Canal.id_daq == DescripcionDAQ.id_daq).first()
            
            estructura = Estructura.query.filter_by(id=info_sensor.id_estructura).first()
            esta_monitoreada = estructura.en_monitoreo
            
            estados_sensor = EstadoSensor.query.filter_by(id_sensor_instalado=id_sensor).order_by(EstadoSensor.fecha_estado.desc()).all()
            estado_dano = EstadoDanoSensor.query.filter_by(id_sensor_instalado=id_sensor).order_by(EstadoDanoSensor.diahora_calculo.desc()).first()
            mantenimientos = Mantenimiento.query.filter_by(id_sensor_instalado=id_sensor).order_by(Mantenimiento.fecha_mantenimiento.desc()).all()
            #Se guarda momentaneamente el id del puente en la sesión actual
            context = {
                'datos_puente' : estructura,
                'esta_monitoreada':esta_monitoreada,
                'sensor' : info_sensor,
                'estados_sensor' : estados_sensor,
                'mantenimientos' : mantenimientos,
                'estado_dano': estado_dano
            }
            return render_template('detalle_sensor.html',**context)
            
        #En POST se envia lo ingresado via formulario, para guardar en la BD
        elif(request.method == "POST"):
            operatividad = request.form.get('opRadio')
            confiabilidad = request.form.get('confRadio')
            mantenimiento = request.form.get('manRadio')
            detalles_mantenimiento = request.form.get('detalle_man')
            try:
                nuevo_estado = EstadoSensor(id_sensor_instalado=id_sensor,fecha_estado=datetime.now(),operatividad=operatividad,confiabilidad=confiabilidad,mantenimiento=mantenimiento)
                db.session.add(nuevo_estado)
                db.session.commit()
            #En caso de ocurrir un fallo, se hace un rollback()
            except:
                db.session.rollback()
                raise
            #Finalmente, se redirige al listado de sensores disponibles
            finally:
                return redirect(url_for('views_api.detalle_sensor',id_sensor=id_sensor))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))
        
@views_api.route('/mantenimiento_sensor/<int:id_sensor>', methods=["POST"])
@login_required
def mantenimiento_sensor(id_sensor):
    estado = request.form.get('detalleRadio')
    detalles = request.form.get('detalles')
    try:
      nuevo_mantenimiento = Mantenimiento(id_sensor_instalado=id_sensor,fecha_mantenimiento=datetime.now(),estado=estado,detalles=detalles)
      db.session.add(nuevo_mantenimiento)
      db.session.commit()
      #En caso de ocurrir un fallo, se hace un rollback()
    except:
      db.session.rollback()
      raise
    #Finalmente, se redirige al listado de sensores disponibles
    finally:
      return redirect(url_for('views_api.detalle_sensor',id_sensor=id_sensor))

@views_api.route('/detalle_daq/<int:id_daq>',methods=["GET", "POST"])
@login_required
def detalle_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Dueño'  or current_user.permisos == 'Analista'):
      if(request.method == "GET"):
        daq = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas).filter(DescripcionDAQ.id_daq == DAQ.id, DAQ.id==id_daq).first()
        zona = db.session.query(DAQPorZona.id_zona,DAQPorZona.id_estructura,ElementoEstructural.descripcion).filter(DAQPorZona.id_daq==id_daq,DAQPorZona.id_zona==ElementoEstructural.id).first()
        estructura = Estructura.query.filter_by(id=zona.id_estructura).first()
        estado_daq = EstadoDAQ.query.filter_by(id_daq = id_daq).order_by(EstadoDAQ.fecha_estado.desc()).all()
        
        sensores_conectados = db.session.query(SensorInstalado.id, Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, DescripcionSensor.descripcion.label("nombre_sensor"), Canal.numero_canal,EstadoSensor.operatividad).filter(Canal.id == SensorInstalado.conexion_actual, Canal.id_daq == id_daq,SensorInstalado.id == DescripcionSensor.id_sensor_instalado, SensorInstalado.id_sensor == Sensor.id, TipoSensor.id == Sensor.tipo_sensor, ElementoEstructural.id == SensorInstalado.id_zona, EstadoSensor.id_sensor_instalado == SensorInstalado.id).order_by(Sensor.id,EstadoSensor.fecha_estado.desc()).distinct(Sensor.id).all()
        
        mantenimientos = MantenimientoDAQ.query.filter_by(id_daq=id_daq).order_by(MantenimientoDAQ.fecha_mantenimiento.desc()).all()
        session['id_puente'] = estructura.id   
        context = {
            'id_puente' : estructura.id,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
            'esta_monitoreada':estructura.en_monitoreo,
            'datos_puente' : estructura,
            'info_daq' : daq,
            'zona': zona,
            'estado_daq':estado_daq,
            'sensores_conectados': sensores_conectados,
            'mantenimientos': mantenimientos
        }
        return render_template('detalle_daq.html',**context)
        
      elif(request.method == "POST"):
        operatividad = request.form.get('opRadio')
        mantenimiento = request.form.get('manRadio')
        try:
          nuevo_estado = EstadoDAQ(id_daq=id_daq,fecha_estado=datetime.now(),operatividad=operatividad,mantenimiento=mantenimiento)
          db.session.add(nuevo_estado)
          db.session.commit()
          #En caso de ocurrir un fallo, se hace un rollback()
        except:
          db.session.rollback()
          raise
        #Finalmente, se redirige al detalle del daq
        finally:
          return redirect(url_for('views_api.detalle_daq',id_daq=id_daq))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/mantenimiento_daq/<int:id_daq>', methods=["POST"])
@login_required
def mantenimiento_daq(id_daq):
    detalles = request.form.get('detalles')
    try:
      nuevo_mantenimiento = MantenimientoDAQ(id_daq=id_daq,fecha_mantenimiento=datetime.now(),detalles=detalles)
      db.session.add(nuevo_mantenimiento)
      db.session.commit()
      #En caso de ocurrir un fallo, se hace un rollback()
    except:
      db.session.rollback()
      raise
    #Finalmente, se redirige al detalle del daq
    finally:
      return redirect(url_for('views_api.detalle_daq',id_daq=id_daq))
      
#PERMISOS = Administrador, dueño
#Método que permite instalar un nuevo sensor en una estructura
@views_api.route('/agregar_sensor/<int:id>', methods=["GET", "POST"])
@login_required
def agregar_sensor_en(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Dueño'):
        #En GET se carga el formulario que permite agregar nuevos sensores a la estructura
        if(request.method == "GET"):
            zonas_puente = db.session.query(ElementoEstructural.id, ElementoEstructural.descripcion).filter_by(id_estructura=id).all()
            #Se filtran los sensores ya conectados
            sensores_conectados = db.session.query(SensorInstalado.conexion_actual).filter(SensorInstalado.id_estructura == id, SensorInstalado.conexion_actual > 0)
            conexiones = db.session.query(Canal.id.label('sensores_conectados')).except_(sensores_conectados).subquery()
            #Se obtienen las conexiones disponibles de los DAQs
            disponibles = db.session.query(Canal).join(conexiones, conexiones.c.sensores_conectados == Canal.id).order_by(Canal.id_daq.asc(), Canal.numero_canal.asc()).all()
            tipos_sensores = TipoSensor.query.all()
            #Se guarda momentaneamente el id del puente en la sesión actual
            session['id_puente'] = id
            context = {
                'id_puente' : id,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'zonas_puente': zonas_puente,
                'tipos_sensores': tipos_sensores,
                'conexiones' : disponibles
            }
            return render_template('agregar_sensor.html',**context)
        #En POST se envia lo ingresado via formulario, para guardar en la BD
        elif(request.method == "POST"):
            zona_sensor = request.form.get('zona_puente')
            tipo_sensor = request.form.get('tipo_sensor')
            daq_sensor = request.form.get('daqs_disponibles')
            freq_sensor = request.form.get('frecuencia')
            #Se guarda el nuevo sensor instalado, y la fecha de la instalación en la BD
            try:
                nuevo_sensor = Sensor(tipo_sensor=tipo_sensor, frecuencia = freq_sensor)
                nueva_instalacion_sensor = InstalacionSensor(fecha_instalacion=datetime.now())
                db.session.add(nueva_instalacion_sensor)
                db.session.add(nuevo_sensor)
                db.session.flush()
                nuevo_sensor_instalado = SensorInstalado(id_instalacion=nueva_instalacion_sensor.id, id_sensor=nuevo_sensor.id, id_zona=zona_sensor, id_estructura=session['id_puente'], conexion_actual=daq_sensor, es_activo=True)
                db.session.add(nuevo_sensor_instalado)
                db.session.flush()
            
                nombre_tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id==tipo_sensor).first().nombre
                nombre_puente = Estructura.query.filter_by(id = session['id_puente']).first().nombre    
                nombre_nueva_tabla = nombre_puente+'.'+nombre_tipo_sensor+'_'+str(session['id_puente'])+str(request.form.get('zona_puente'))+str(nuevo_sensor.id)+str(nuevo_sensor_instalado.id)
                db.session.commit()
                x = nombre_nueva_tabla.lower().replace(" ","_")
                crear_tabla_sensor(nuevo_sensor_instalado.id, x)
            #En caso de ocurrir un fallo, se hace un rollback()
            except:
                db.session.rollback()
                raise
            #Finalmente, se redirige al listado de sensores disponibles
            finally:
                return redirect(url_for('views_api.sensores_de_estructura',id=session['id_puente']))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, dueño y analista
#API que obtiene las lecturas de un sensor en el formato JSON, con la opción de ventanas de tiempo (periodo: 1 = 1 hora, 2 = 1 dia, 3 = 1 semana)
@views_api.route('/lecturas_sensor_rango/<int:sensor>/<int:periodo>')
def obtener_lecturas_rango(sensor, periodo):
    try:
        nombre_tabla = SensorInstalado.query.filter_by(id=sensor).first().nombre_tabla
        rango_de_tiempo = ""
        if(periodo == 1):
            rango_de_tiempo = "12 seconds"
        elif(periodo == 2):
            rango_de_tiempo = "288 seconds"
        elif(periodo == 3):
            rango_de_tiempo = "2016 seconds"
        lecturas = db.session.execute("""SELECT time_bucket('"""+rango_de_tiempo+"""', x.fecha) as sec, max(lectura),min(lectura),avg(lectura) FROM """+nombre_tabla+""" as x WHERE x.fecha <= '2008-01-02' GROUP BY sec ORDER BY sec DESC LIMIT 300""")
        res = {}
        for i in lecturas:
            #res[i['fecha'].strftime("%d-%d-%Y %H:%M:%S.%f")] = i['lectura']
            res[i['sec'].strftime("%d-%d-%Y %H:%M:%S.%f")] = {
                'max' : i['max'],
                'min' : i['min'],
                'avg' : i['avg']
            }
        return res
    except Exception as e:
        return render_template('usuario_no_autorizado.html')

#PERMISOS = Administrador, dueño y analista
#API que obtiene las lecturas de un sensor en el formato JSON, entrega todo el contenido de la tabla
@views_api.route('/lecturas_sensor/<int:sensor>')
def obtener_lecturas(sensor):
    try:
        nombre_tabla = SensorInstalado.query.filter_by(id=sensor).first().nombre_tabla
        lecturas = db.session.execute("""SELECT * FROM """+nombre_tabla+""" LIMIT 300""")
        res = {}
        for i in lecturas:
            res[i['fecha'].strftime("%d-%d-%Y %H:%M:%S.%f")] = i['lectura']
        return res
    except Exception as e:
        return render_template('usuario_no_autorizado.html')

#PERMISOS = TODOS
#Función que permite a la barra de búsqueda encontrar el listado de estructuras
@views_api.route('/buscar_estructura', methods=['POST'])
@login_required
def buscar_estructura():
    try:
        x = request.form.get('autocomplete').split()[0]
        return redirect(url_for('views_api.informacion_estructura', id=x))
    except Exception as e:
        return render_template('estructura_no_existe.html')

#PERMISOS = Administrador, analista
#Función que permite obtener el historial de estado de monitoreo de una estructura
@views_api.route('/estados_monitoreo/<int:id>')
@login_required
def historial_monitoreo_estructura(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        historial = EstadoEstructura.query.filter_by(id_estructura = id).all()
        context = {
            'id_puente' : id,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
            'estados_monitoreo': historial
        }
        return render_template('historial_monitoreo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Método que permite actualizar el estado de monitoreo de una estructura
@views_api.route('/actualizar_estado/<int:id>', methods=["GET","POST"])
@login_required
def actualizar_estado_monitoreo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        #Acceso con GET al formulario
        if(request.method == "GET"):
            context = {
                'id_puente' : id,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id)
            }
            return render_template('actualizar_estado_monitoreo.html', **context)
        #Acceso con POST para escribir en la BD
        elif(request.method == "POST"):
            x = EstadoEstructura(id_estructura=id, estado = request.form.get('nuevo_estado'), fecha_estado = datetime.now())
            try:
                db.session.add(x)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.historial_monitoreo_estructura',id=id))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite acceder al historial de calibraciones de un sensor instalado, dado su id
@views_api.route('/calibraciones/<int:x>')
@login_required
def historial_calibraciones_sensor(x):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensor = Sensor.query.filter_by(id=x).first()
        tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
        calibraciones = db.session.query(CalibracionSensor.detalles, CalibracionSensor.fecha_calibracion, SensorInstalado.id_sensor, ElementoEstructural.descripcion).filter(CalibracionSensor.id_sensor_instalado == SensorInstalado.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_sensor == x).order_by(CalibracionSensor.fecha_calibracion.desc()).all()
        context = {
            'id_sensor' : sensor.id,
            'tipo_sensor' : tipo_sensor.nombre,
            'calibraciones' : calibraciones
        }
        return render_template('historial_calibraciones.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite agregar una nueva calibración de un sensor a la BD
@views_api.route('/nueva_calibracion/<int:x>', methods=["GET","POST"])
@login_required
def nueva_calibracion(x):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        #GET para acceder al formulario
        if(request.method == "GET"):
            sensor = Sensor.query.filter_by(id=x).first()
            tipo_sensor = TipoSensor.query.filter_by(id=sensor.tipo_sensor).first()
            context = {
                'id_sensor' : sensor.id,
                'tipo_sensor' : tipo_sensor.nombre,
            }
            return render_template('nueva_calibracion.html',**context)
        #POST para enviar los datos a la BD
        elif(request.method == "POST"):
            sensor_instalado_actual = db.session.query(SensorInstalado.id).filter(InstalacionSensor.id == SensorInstalado.id_instalacion, SensorInstalado.id_sensor == x).order_by(InstalacionSensor.fecha_instalacion.desc()).first()
            nueva_calibracion = CalibracionSensor(id_sensor_instalado=sensor_instalado_actual.id, fecha_calibracion=datetime.now(), detalles=request.form.get('nueva_calibracion'))
            try:
                db.session.add(nueva_calibracion)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.historial_calibraciones_sensor',x=x))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Listado de DAQs de una estructura
@views_api.route('/daqs_estructura/<int:id_puente>')
@login_required
def daqs_de_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ElementoEstructural.id == DAQPorZona.id_zona, DAQPorZona.id_estructura == id_puente).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'daqs' : daqs
        }
        return render_template('daqs_de_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Listado de DAQs por zona de la estructura
@views_api.route('/daqs_zona/<int:id_zona>')
@login_required
def daqs_de_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        puente = db.session.query(Estructura.id, Estructura.nombre, Estructura.tipo_activo).filter(ElementoEstructural.id_estructura == Estructura.id, ElementoEstructural.id == id_zona).first()
        nombre_puente = puente.nombre.capitalize()
        tipo_activo = puente.tipo_activo.lower()
        zona = db.session.query(TipoElemento.nombre_zona).filter(ElementoEstructural.tipo_zona == TipoElemento.id, ElementoEstructural.id==id_zona).first()
        daqs = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ElementoEstructural.id == DAQPorZona.id_zona, DAQPorZona.id_zona == id_zona).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
        context = {
            'id_puente' : puente.id,
            'nombre_puente' : nombre_puente,
            'tipo_activo' : tipo_activo,
            'nombre_zona' : zona.nombre_zona,
            'daqs' : daqs
        }
        return render_template('daqs_de_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Entrega del detalle de un DAQ en una estructura
@views_api.route('/daq/<int:id_puente>/<int:id_daq>')
@login_required
def informacion_daq(id_puente, id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        daq = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas).filter(DescripcionDAQ.id_daq == DAQ.id, DAQ.id==id_daq).first()
        zonas_del_daq = db.session.query(DAQPorZona.id_zona, ElementoEstructural.descripcion).filter(ElementoEstructural.id == DAQPorZona.id_zona, DAQ.id == id_daq).all()
        estado_actual = EstadoDAQ.query.filter_by(id_daq = id_daq).order_by(EstadoDAQ.fecha_estado.desc()).first()
        canales_del_daq = db.session.query(Canal.id, Canal.id_daq, Canal.numero_canal).filter(Canal.id_daq == id_daq).all()
        canales_ocupados = db.session.query(SensorInstalado.conexion_actual, Canal.id_daq, Canal.numero_canal).filter(Canal.id == SensorInstalado.conexion_actual, Canal.id_daq == id_daq, SensorInstalado.conexion_actual > 0)
        x = revisar_disponibilidad_canales(canales_del_daq, canales_ocupados)
        session['id_puente'] = id_puente   
        context = {
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'info_daq' : daq,
            'estado_actual':estado_actual,
            'zonas' : zonas_del_daq,
            'canales' : x
        }
        return render_template('informacion_daq.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Entrega el historial de estados de un DAQ
@views_api.route('/historial_daq/<int:id_daq>')
@login_required
def historial_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = EstadoDAQ.query.filter_by(id_daq=id_daq).all()
        context = {
            'id_daq' : id_daq,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
            'estados' : x
        }
        return render_template('historial_daq.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Método que permite actualizar el estado de un DAQ en la BD
@views_api.route('/actualizar_estado_daq/<int:id_daq>', methods=["GET","POST"])
@login_required
def actualizar_estado_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        #GET para obtener el formualrio
        if(request.method == "GET"):
            context = {
                'id_daq' : id_daq,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
            }
            return render_template('actualizar_estado_daq.html',**context)
        #POST para enviar los datos a la BD
        elif(request.method == "POST"):
            nuevo_estado = EstadoDAQ(id_daq=id_daq, fecha_estado=datetime.now(), detalles=request.form.get('nuevo_estado'))
            try:
                db.session.add(nuevo_estado)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.historial_daq',id_daq = id_daq))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite ver las revisiones de un DAQ, registradas en la BD
@views_api.route('/revisiones_daq/<int:id_daq>')
@login_required
def revisiones_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = RevisionDAQ.query.filter_by(id_daq=id_daq).all()
        context = {
            'id_daq' : id_daq,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente']),
            'revisiones' : x
        }
        return render_template('revisiones_daq.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite añadir una nueva revisión de un DAQ
@views_api.route('/nueva_revision_daq/<int:id_daq>', methods=["GET","POST"])
@login_required
def actualizar_revision_daq(id_daq):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            context = {
                'id_daq' : id_daq,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(session['id_puente'])
            }
            return render_template('nueva_revision_daq.html',**context)
        elif(request.method == "POST"):
            nueva_revision = RevisionDAQ(id_daq=id_daq, fecha_revision=datetime.now(), detalles=request.form.get('nueva_revision'))
            try:
                db.session.add(nueva_revision)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.revisiones_daq',id_daq = id_daq))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Método que muestra los "clusters" de sensores próximos entre si, en una estructura
@views_api.route('/clusters/<int:id_puente>')
@login_required
def clusters_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        clusters = db.session.query(Conjunto.id, Conjunto.nombre).filter(ConjuntoZona.id_conjunto == Conjunto.id, ConjuntoZona.id_estructura == id_puente).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'clusters' : clusters
        }
        return render_template('clusters_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Muestra el listado de sensores pertenecientes a un "cluster"
@views_api.route('/sensores_cluster/<int:id_cluster>')
@login_required
def sensores_cluster(id_cluster):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        nombre_cluster = db.session.query(Conjunto.nombre).filter_by(id = id_cluster).first().nombre
        sensores_cluster = db.session.query(Sensor.id, SensorInstalado.id.label("si"), ElementoEstructural.descripcion, Sensor.frecuencia, TipoSensor.nombre, SensorInstalado.es_activo).filter(SensorInstalado.id == ConjuntoSensorInstalado.id_sensor_instalado, Sensor.id == SensorInstalado.id_sensor, ElementoEstructural.id == SensorInstalado.id_zona, TipoSensor.id == Sensor.tipo_sensor, ConjuntoSensorInstalado.id_conjunto == id_cluster).all()
        context = {
            'id_cluster' : id_cluster,
            'nombre_cluster' : nombre_cluster,
            'sensores_cluster' : sensores_cluster
        }
        return render_template('sensores_cluster.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite agregar un sensor a un cluster (a modo de ejemplo, en la realidad, esto no debiese ser una interacción del usuario)
@views_api.route('/nuevo_sensor_cluster/<int:id_cluster>')
@login_required
def agregar_sensor_cluster(id_cluster):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            sensores_ocupados = db.session.query(SensorInstalado.id, TipoSensor.nombre, ElementoEstructural.descripcion).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.es_activo == True, ConjuntoSensorInstalado.id_sensor_instalado == SensorInstalado.id, ConjuntoSensorInstalado.id_conjunto == id_cluster)
            sensores_disponibles = db.session.query(SensorInstalado.id, TipoSensor.nombre, ElementoEstructural.descripcion).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.es_activo == True).except_(sensores_ocupados).all()
            context = {
                'id_cluster' : id_cluster,
                'sensores' : sensores_disponibles
            }
            return render_template('agregar_sensor_cluster.html',**context)
        elif(request.method == "POST"):
            id_sensor = request.form.get('sensor')
            zona = db.session.query(SensorInstalado.id_estructura, SensorInstalado.id_zona).filter(SensorInstalado.id == id_sensor).first()
            nuevo_sensor_cluster = ConjuntoSensorInstalado(id_sensor_instalado = id_sensor, id_conjunto = id_cluster)
            try:
                db.session.add(nuevo_sensor_cluster)
                check_if_exists = ConjuntoZona.query.filter(ConjuntoZona.id_conjunto == id_cluster, ConjuntoZona.id_zona == zona.id_zona, ConjuntoZona.id_estructura == zona.id_estructura).first()
                if(check_if_exists is None):
                    nueva_zona_cluster = ConjuntoZona(id_conjunto = id_cluster, id_zona = zona.id_zona, id_estructura = zona.id_estructura)
                    db.session.add(nueva_zona_cluster)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.sensores_cluster', id_cluster = id_cluster))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Entrega el listado de sensores que pertenecen a una zona de la estructura
@views_api.route('/sensores_zona/<int:id_zona>')
@login_required
def sensores_por_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        puente = db.session.query(Estructura.nombre, Estructura.tipo_activo).filter(ElementoEstructural.id_estructura == Estructura.id, ElementoEstructural.id == id_zona).first()
        nombre_puente = puente.nombre.capitalize()
        tipo_activo = puente.tipo_activo.lower()
        zona = db.session.query(ElementoEstructural.descripcion).filter(ElementoEstructural.id==id_zona).first()
        sensores = db.session.query(Sensor.id, SensorInstalado.id.label('si'), Sensor.frecuencia, TipoSensor.nombre).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_zona == id_zona).all()
        context = {
            'nombre_puente' : nombre_puente,
            'tipo_activo' : tipo_activo,
            'nombre_zona' : zona.descripcion,
            'sensores' : sensores
        }
        return render_template('sensores_por_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Método que retorna el historial de estado de un sensor instalado
@views_api.route('/historial_sensor/<int:id_sensor>')
@login_required
def historial_estado_sensor(id_sensor):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        x = db.session.query(SensorInstalado.id_estructura).filter(SensorInstalado.id_sensor == id_sensor).first().id_estructura
        tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id == Sensor.tipo_sensor, Sensor.id == id_sensor).first().nombre
        historial = db.session.query(SensorInstalado.id, ElementoEstructural.descripcion, EstadoSensor.detalles, EstadoSensor.fecha_estado).filter(SensorInstalado.id == EstadoSensor.id_sensor_instalado, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_sensor == id_sensor).all()
        context = {
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(x),
            'tipo_sensor': tipo_sensor,
            'id_sensor': id_sensor,
            'historial' : historial
        }
        return render_template('historial_sensor.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Método que permite al usuario (autorizado) actualizar el estado de un sensor (a modo de ejemplo)
@views_api.route('/actualizar_estado_sensor/<int:id_sensor>')
@login_required
def actualizar_estado_sensor(id_sensor):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == "GET"):
            x = db.session.query(SensorInstalado.id_estructura).filter(SensorInstalado.id_sensor == id_sensor).first().id_estructura
            tipo_sensor = db.session.query(TipoSensor.nombre).filter(TipoSensor.id == Sensor.tipo_sensor, Sensor.id == id_sensor).first().nombre
            context = {
                'id_sensor' : id_sensor,
                'tipo_sensor' : tipo_sensor,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(x)
            }
            return render_template('actualizar_estado_sensor.html', **context)
        elif(request.method == "POST"):
            id_sensor_instalado_actual = db.session.query(SensorInstalado.id, InstalacionSensor.fecha_instalacion).filter(InstalacionSensor.id == SensorInstalado.id_instalacion, SensorInstalado.id_sensor == id_sensor).order_by(InstalacionSensor.fecha_instalacion.desc()).first().id
            x = EstadoSensor(id_sensor_instalado=id_sensor_instalado_actual, detalles = request.form.get('nuevo_estado'), fecha_estado = datetime.now())
            try:
                db.session.add(x)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.historial_estado_sensor',id_sensor=id_sensor))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Vista que permite al usuario en la sesión actual, crear un grupo personalizado de sensores
@views_api.route('/grupo_definido_usuario', methods=['GET','POST'])
@login_required
def grupo_definido_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        #GET para ver el formulario
        if(request.method == 'GET'):
            sensores = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ElementoEstructural.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ElementoEstructural.id == SensorInstalado.id_zona).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            context = {
                'sensores' : sensores
            }
            return render_template('grupo_definido_usuario.html',**context)
        #POST para enviar el grupo a la BD
        elif(request.method == 'POST'):
            nombre = request.form.get('nombre_grupo')
            sensores = request.form.getlist('sensores_elegidos')
            nuevo_grupo = GrupoDefinidoUsuario(nombre=nombre, id_usuario=current_user.id, fecha_creacion=datetime.now())
            try:
                db.session.add(nuevo_grupo)
                db.session.flush()
                for i in sensores:
                    x = SensorPorGrupoDefinido(id_sensor_instalado=i, id_grupo=nuevo_grupo.id, fecha_creacion=datetime.now())
                    db.session.add(x)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Vista con el listado de grupos de sensores creados por el usuario actual
@views_api.route('/grupos_usuario')
@login_required
def grupos_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        grupos = GrupoDefinidoUsuario.query.filter_by(id_usuario = current_user.id).all()
        context = {
            'grupos' : grupos
        }
        return render_template('listado_grupos.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite acceder al listado de sensores incluidos en un grupo personalizado
@views_api.route('/sensores_de_grupo/<int:id>')
@login_required
def sensores_de_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensores = db.session.query(TipoSensor.nombre.label('tipo_sensor'), ElementoEstructural.descripcion, Estructura.tipo_activo, Estructura.nombre, SensorInstalado.id, SensorInstalado.id_sensor, SensorInstalado.nombre_tabla, SensorPorGrupoDefinido.fecha_creacion).filter(GrupoDefinidoUsuario.id == SensorPorGrupoDefinido.id_grupo, SensorInstalado.id == SensorPorGrupoDefinido.id_sensor_instalado, Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, ElementoEstructural.id == SensorInstalado.id_zona, Estructura.id == SensorInstalado.id_estructura, GrupoDefinidoUsuario.id == id).all()
        nombre_grupo = db.session.query(GrupoDefinidoUsuario.nombre).filter(GrupoDefinidoUsuario.id == id).first().nombre
        context = {
            'nombre_grupo':nombre_grupo,
            'sensores':sensores
        }
        return render_template('sensores_de_grupo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Al acceder a este método, el usuario elimina un grupo de sensores (borra la relacion "Grupo Definido por usuario", los sensores siguen donde estaban)
@views_api.route('/eliminar_grupo/<int:id>', methods=['POST'])
@login_required
def eliminar_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        sensores_a_eliminar = SensorPorGrupoDefinido.query.filter_by(id_grupo = id).delete()
        try:
            grupo_a_eliminar = GrupoDefinidoUsuario.query.filter_by(id = id).delete()
            db.session.commit()
        except:
            db.session.rollback()
        finally:
            return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista
#Permite al usuario editar el grupo que él creo (ya sea el nombre del grupo, o los sensores que forman parte de este)
@views_api.route('/editar_grupo/<int:id>', methods=['GET','POST'])
@login_required
def editar_grupo(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == 'GET'):
            sensores_del_grupo = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ElementoEstructural.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id == SensorPorGrupoDefinido.id_sensor_instalado, SensorPorGrupoDefinido.id_grupo == GrupoDefinidoUsuario.id, GrupoDefinidoUsuario.id == id).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            sensores_disponibles = sensores = db.session.query(SensorInstalado.id, SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion, TipoSensor.nombre.label('tipo_sensor'), Estructura.nombre, Estructura.tipo_activo, ElementoEstructural.descripcion, SensorInstalado.es_activo, SensorInstalado.nombre_tabla, SensorInstalado.conexion_actual).filter(Sensor.id == SensorInstalado.id_sensor, TipoSensor.id == Sensor.tipo_sensor, InstalacionSensor.id == SensorInstalado.id_instalacion, Estructura.id == SensorInstalado.id_estructura, ElementoEstructural.id == SensorInstalado.id_zona).distinct(SensorInstalado.id_sensor).order_by(SensorInstalado.id_sensor, InstalacionSensor.fecha_instalacion.desc()).all()
            nombre_grupo = db.session.query(GrupoDefinidoUsuario.nombre).filter_by(id = id).first().nombre
            context = {
                'id_grupo' : id,
                'nombre_grupo' : nombre_grupo, 
                'sensores_disponibles' : sensores_disponibles,
                'sensores_del_grupo' : sensores_del_grupo
            }
            return render_template('actualizar_grupo_definido_usuario.html',**context)
        elif(request.method == 'POST'):
            inicial_query = SensorPorGrupoDefinido.query.filter_by(id_grupo = id).all()
            inicial_lista = [(i.id_sensor_instalado, i.id_grupo) for i in inicial_query] 
            final_query = request.form.getlist('sensores_elegidos')
            final_lista = [(int(i), id) for i in final_query]
            try:
                #Para remover elementos
                for i in inicial_lista:
                    if i not in final_lista:
                        x = SensorPorGrupoDefinido.query.filter_by(id_sensor_instalado = i[0], id_grupo=i[1]).delete()
                #Para añadir elementos
                for i in final_lista:
                    if i not in inicial_lista:
                        y = SensorPorGrupoDefinido(id_sensor_instalado = i[0], id_grupo = i[1], fecha_creacion = datetime.now())
                        db.session.add(y)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.grupos_usuario'))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Listado de informes de monitoreo visual asociados a una estructura
@views_api.route('/informes_estructura/<int:id_puente>')
@login_required
def informes_monitoreo_estructura(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informes = db.session.query(InformeMonitoreoVisual.ruta_acceso_archivo, InformeMonitoreoVisual.id_informe, Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha).filter(InformeMonitoreoVisual.id_usuario == Usuario.id, InformeMonitoreoVisual.id_estructura == id_puente).all()
        context = {
            'id_puente' : id_puente,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
            'informes' : informes
        }
        return render_template('informes_monitoreo_estructura.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Ruta para acceder a un informe en particular (abre el visor de pdf en el navegador)
@views_api.route('/informe/<int:id>')
@login_required
def ver_informe(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informe = InformeMonitoreoVisual.query.filter_by(id_informe = id).first()
        context = {
            'informe' : informe
        }
        return render_template('pdf_informe.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, analista, Dueño
#Para eliminar un informe de monitoreo ("Debe hacerlo el mismo usuario que creo el informe")
@views_api.route('/eliminar_informe/<int:id>', methods=['POST'])
@login_required
def eliminar_informe(id):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informe = InformeMonitoreoVisual.query.filter_by(id_informe = id).first()
        try:
            if(informe.id_usuario == current_user.id):
                os.chdir('static/reports')
                os.remove(informe.ruta_acceso_archivo)
                os.chdir('../..')
                informe_a_borrar = InformeMonitoreoVisual.query.filter_by(id_informe = id).delete()
                db.session.commit()
        except:
            db.session.rollback()
        finally:
            return redirect(url_for('views_api.informes_monitoreo_estructura',id_puente=informe.id_estructura))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador, analista, Dueño
#Permite agregar un nuevo informe de monitoreo visual, asociado a una estructura
@views_api.route('/agregar_informe/<int:id_puente>', methods=['POST'])
@login_required
def agregar_informe(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        file = request.files['input-file-now']
        try:
            os.chdir('static/reports')
            file.save(secure_filename(unidecode.unidecode(file.filename.replace(" ","_"))))
            os.chdir('../..')
            nuevo_informe = InformeMonitoreoVisual(id_usuario=current_user.id, id_estructura=id_puente, contenido=request.form.get('contenido'), fecha=datetime.now(), ruta_acceso_archivo=unidecode.unidecode(file.filename.replace(" ","_")))
            db.session.add(nuevo_informe)
            db.session.commit()
        except:
            db.session.rollback()
        finally:
            return redirect(url_for('views_api.informes_monitoreo_estructura', id_puente=id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Listado con los informes subidos por el usuario en sesión actual
@views_api.route('/mis_informes')
@login_required
def informes_monitoreo_usuario():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        informes = db.session.query(InformeMonitoreoVisual.ruta_acceso_archivo, InformeMonitoreoVisual.id_informe, Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha).filter(InformeMonitoreoVisual.id_usuario == Usuario.id, InformeMonitoreoVisual.id_usuario == current_user.id).all()
        context = {
            'informes' : informes
        }
        return render_template('mis_informes_monitoreo.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Listado con los informes de monitoreo visual asociados a una zona del puente
@views_api.route('/informes_zona/<int:id_zona>')
@login_required
def informes_monitoreo_zona(id_zona):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        estructura = db.session.query(ElementoEstructural.id_estructura, ElementoEstructural.descripcion).filter(ElementoEstructural.id == id_zona).first()
        id_estructura = estructura.id_estructura
        descripcion = estructura.descripcion
        informes = db.session.query(Usuario.nombre, Usuario.apellido, InformeMonitoreoVisual.id_informe, InformeMonitoreoVisual.id_usuario, InformeMonitoreoVisual.contenido, InformeMonitoreoVisual.fecha, InformeMonitoreoVisual.ruta_acceso_archivo, InformeZona.id_zona).filter(Usuario.id == InformeMonitoreoVisual.id_usuario, InformeZona.id_informe == InformeMonitoreoVisual.id_informe, InformeZona.id_zona == id_zona).all()
        context = {
            'id_puente' : id_estructura,
            'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_estructura),
            'descripcion' : descripcion,
            'informes' : informes
        }
        return render_template('informes_monitoreo_zona.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Listado de hallazgos asociados a un informe de monitoreo visual
@views_api.route('/hallazgos_informe/<int:id_informe>')
@login_required
def hallazgos_de_informe(id_informe):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        hallazgos = db.session.query(HallazgoVisual.id, HallazgoVisual.detalle_hallazgo, HallazgoVisual.fecha, HallazgoVisual.id_zona, ElementoEstructural.descripcion, HallazgoVisual.id_estructura, HallazgoInforme.id_informe).filter(HallazgoVisual.id == HallazgoInforme.id_hallazgo, ElementoEstructural.id == HallazgoVisual.id_zona, HallazgoInforme.id_informe == id_informe).all()
        res = []
        for i in hallazgos:
            audiovisual = MaterialAudiovisual.query.filter_by(id_hallazgo = i[0]).all()
            element = {
                'hallazgo' : i,
                'material_apoyo' : audiovisual
            }
            res.append(element)
        context = {
            'id_informe' : id_informe,
            'hallazgos' : res
        }
        return render_template('hallazgos_de_informe.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
#Este método permite agregar nuevos hallazgos a un informe ya existente
@views_api.route('/agregar_hallazgo/<int:id_informe>', methods=['GET','POST'])
@login_required
def agregar_hallazgo(id_informe):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        if(request.method == 'GET'):
            id_estructura = InformeMonitoreoVisual.query.filter_by(id_informe = id_informe).first().id_estructura
            zonas_estructura = ElementoEstructural.query.filter_by(id_estructura = id_estructura).all()
            context = {
                'zonas_puente' : zonas_estructura,
                'id_estructura' : id_estructura,
                'id_informe' : id_informe
            }
            return render_template('agregar_hallazgo.html',**context)
        elif(request.method == 'POST'):
            id_estructura = InformeMonitoreoVisual.query.filter_by(id_informe = id_informe).first().id_estructura
            nuevo_hallazgo = HallazgoVisual(id_usuario=current_user.id, detalle_hallazgo=request.form.get('detalle'), fecha=datetime.now(), id_zona = request.form.get('zona_puente'), id_estructura=id_estructura)
            try:
                db.session.add(nuevo_hallazgo)
                db.session.flush()
                imagenes = request.files.getlist('imagenes')
                list_img = []
                os.chdir('static/images')
                for i in imagenes:
                    i.save(secure_filename(unidecode.unidecode(i.filename.replace(" ","_"))))
                    list_img.append(MaterialAudiovisual(id_hallazgo=nuevo_hallazgo.id, tipo_material='imagen',ruta_acceso_archivo=unidecode.unidecode(i.filename.replace(" ","_"))))
                os.chdir('../..')
                db.session.bulk_save_objects(list_img)
                asociar_a_informe = HallazgoInforme(id_informe=id_informe, id_hallazgo=nuevo_hallazgo.id)
                db.session.add(asociar_a_informe)
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.hallazgos_de_informe',id_informe=id_informe))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#Rutas que permiten acceder a recursos estáticos de la plataforma (Archivos BIM, Imágenes e Informes)
@views_api.route('/static/bim/<int:id_puente>')
def show_3d_bim(id_puente):
        return redirect(url_for('static', filename='bim/'+str(id_puente)+'/index.html'))
        # return render_template('static/bim/'+str(idpuente)+'/index.html')

@views_api.route('/bim/<int:id_puente>')
def show_bim(id_puente):
        return send_file('./static/bim/'+str(id_puente)+'/index.html')
        # return render_template('static/bim/'+str(idpuente)+'/index.html')
        
@views_api.route('/static/images/<string:filename>')
def show_image(filename):
    return send_file('./static/images/'+filename)

@views_api.route('/static/reports/<string:filename>')
def show_report(filename):
    return send_file('./static/reports/'+filename)

#PERMISOS = Administrador, analista
#Método que permite agregar nuevos DAQs a una estructura
@views_api.route('/agregar_daq/<int:id_puente>', methods = ['GET','POST'])
@login_required
def agregar_daq(id_puente):
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista'):
        if(request.method == 'GET'):
            zonas_puente = ElementoEstructural.query.filter_by(id_estructura = id_puente).all()
            context = {
                'id_puente' : id_puente,
                'zonas_puente' : zonas_puente,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente)
            }
            return render_template('agregar_daq.html',**context)
        elif(request.method == 'POST'):
            nuevo_daq = DAQ(nro_canales=request.form.get('nro_canales'))
            try:
                db.session.add(nuevo_daq)
                db.session.flush()
                zona_daq = DAQPorZona(id_daq=nuevo_daq.id, id_zona=request.form.get('zona_puente'), id_estructura=id_puente)
                db.session.add(zona_daq)
                caract = DescripcionDAQ(id_daq=nuevo_daq.id, caracteristicas=request.form.get('caracteristicas'))
                db.session.add(caract)
                estado_nuevo_daq = EstadoDAQ(id_daq=nuevo_daq.id, fecha_estado=datetime.now(), detalles='Conectado')
                db.session.add(estado_nuevo_daq)
                canales = []
                for i in range(1,int(nuevo_daq.nro_canales)+1):
                    x = Canal(id_daq=nuevo_daq.id, numero_canal=i)
                    canales.append(x)
                db.session.bulk_save_objects(canales)                
                db.session.commit()
            except:
                db.session.rollback()
            finally:
                return redirect(url_for('views_api.daqs_de_estructura',id_puente = id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


#PERMISOS = Administrador
#Versión beta del método "sensores_de_estructura", pero con la diferencia de que se filtra por fecha, permitiendo ver los sensores instalados en otros instantes de tiempo
@views_api.route('/sensores_estructura_test/<int:id>',methods=["GET","POST"])
@login_required
def sensores_de_estructura_test(id):
    if(current_user.permisos == "Administrador"):
        if(request.method == "GET"):
            sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
            context = {
                'id_puente' : id,
                'fecha_actual' : datetime.now().strftime('%Y-%m-%d'),
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'sensores_puente' : sensores_actuales
            }
            return render_template('sensores_puente_test.html',**context)
        elif(request.method == "POST"):
            fecha = request.form.get('date')
            x = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id, InstalacionSensor.fecha_instalacion <= fecha).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).subquery()
            sensores = db.session.query(x).filter(x.c.es_activo == True)
            context = {
                'id_puente' : id,
                'fecha_actual' : request.form.get('date'),
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id),
                'sensores_puente' : sensores
            }
            return render_template('sensores_puente_test.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = Administrador, analista, Dueño
@views_api.route('/agregar_informe', methods=['POST'])
@login_required
def agregar_informe_test():
    if(current_user.permisos == 'Administrador' or current_user.permisos == 'Analista' or current_user.permisos == 'Dueño'):
        print(os.getcwd())
        id_puente = request.form.get('id_puente')
        file = request.files['input-file-now']
        os.chdir('static/reports')
        file.save(secure_filename(unidecode.unidecode(file.filename.replace(" ","_"))))
        os.chdir('../..')
        nuevo_informe = InformeMonitoreoVisual(id_usuario=current_user.id, id_estructura=id_puente, contenido=request.form.get('contenido'), fecha=datetime.now(), ruta_acceso_archivo=unidecode.unidecode(file.filename.replace(" ","_")))
        db.session.add(nuevo_informe)
        db.session.commit()
        return redirect(url_for('views_api.informes_monitoreo_estructura', id_puente=id_puente))
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))


@views_api.route('/hallazgos/<int:id_puente>')
def obtener_hallazgos(id_puente):
    hallazgos = HallazgoVisual.query.filter_by(id_estructura=id_puente).all()
    res = {}
    res['data'] = []
    for i in hallazgos:
        imagenes = MaterialAudiovisual.query.filter_by(id_hallazgo=i.id).all()
        print(imagenes)
        res_img = []
        for j in imagenes:
            aux_img = {
                'id_material_apoyo': j.id,
                'tipo_material' : j.tipo_material,
                'ruta_acceso_archivo' : 'http://54.207.236.190/static/images/'+j.ruta_acceso_archivo
            }
            res_img.append(aux_img)
        aux = {
            'id_hallazgo'       : i.id,
            'id_usuario'        : i.id_usuario,
            'detalle_hallazgo'  : i.detalle_hallazgo,
            'fecha'             : i.fecha,
            'coord_x'           : i.coord_x,
            'coord_y'           : i.coord_y,
            'coord_z'           : i.coord_z,
            'id_zona'           : i.id_zona,
            'id_estructura'     : i.id_estructura,
            'imagenes'          : res_img
        }
        res['data'].append(aux)
    return res

####################### INTEGRACION UNITY ####################################
@views_api.route('/sensores_instalados/<int:id_puente>')
def sensores_instalados(id_puente):
  sensores_actuales = db.session.query(Sensor.id, SensorInstalado.id.label("si"),SensorInstalado.coord_x,SensorInstalado.coord_y,SensorInstalado.coord_z,Sensor.frecuencia,Sensor.uuid_device, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion,DescripcionSensor.descripcion.label("nsensor")).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id_puente, DescripcionSensor.id_sensor_instalado == SensorInstalado.id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
  data = {}
  data['data'] = []
  if(sensores_actuales != None):
    for element in sensores_actuales:
      aux = {
      'nombre'    : element.nsensor,
      'id'        : element.si,
      'uuid'      : element.uuid_device,
      'frecuencia': element.frecuencia,
      'tipo'      : element.nombre,
      'fecha_inst': element.fecha_instalacion,
      'zona'      : element.descripcion,
      'coord_x'   : element.coord_x,
      'coord_y'   : element.coord_y,
      'coord_z'   : element.coord_z
      }
      data['data'].append(aux)
  else:
    data['data'] = "ND"
  return data 

@views_api.route('/estado_sensor/<int:id_si>')
def estado_sensor(id_si):
  estado = db.session.query(EstadoSensor.operatividad, EstadoSensor.fecha_estado).filter(SensorInstalado.id == id_si, EstadoSensor.id_sensor_instalado == SensorInstalado.id).order_by(EstadoSensor.fecha_estado.desc()).first()
  if(estado != None):
    data = estado.operatividad
  else:
    data = "ND"  
  return data

@views_api.route('/actualizar_si/<int:id_si>', methods=["POST"])
def actualizar_si(id_si):
  if request.is_json:
    req = request.get_json()
    sensor_a_actualizar = SensorInstalado.query.filter_by(id = id_si).first()
    try:
      sensor_a_actualizar.coord_x = req.get("x")
      sensor_a_actualizar.coord_y = req.get("y")
      sensor_a_actualizar.coord_z = req.get("z")
      db.session.add(sensor_a_actualizar)
      db.session.commit()
      response_body = {
      "message": "Aceptado" 
      }
      res = make_response(jsonify(response_body), 200)
      return res
    except:
      db.session.rollback()
      return make_response(jsonify({"message": "Error al Actualizar"}), 400)
  else:
    return make_response(jsonify({"message": "No es un JSON valido"}), 400)

@views_api.route('/actualizar_hallazgo/<int:id_hallazgo>', methods=["POST"])
def actualizar_hallazgo(id_hallazgo):
  if request.is_json:
    req = request.get_json()
    hallazgo_a_actualizar = HallazgoVisual.query.filter_by(id = id_hallazgo).first()
    try:
      hallazgo_a_actualizar.coord_x = req.get("x")
      hallazgo_a_actualizar.coord_y = req.get("y")
      hallazgo_a_actualizar.coord_z = req.get("z")
      db.session.add(hallazgo_a_actualizar)
      db.session.commit()
      response_body = {
      "message": "Aceptado" 
      }
      res = make_response(jsonify(response_body), 200)
      return res
    except:
      db.session.rollback()
      return make_response(jsonify({"message": "Error al Actualizar"}), 400)
  else:
    return make_response(jsonify({"message": "No es un JSON valido"}), 400)
####################### INTEGRACIÓN CON THINGSBOARD #########################
@views_api.route('/tiemporeal/<int:id>')
def tiempo_real(id):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    #Revisa si el schema del puente existe, de no ser así, es por que no está siendo monitoreada
    nombre_del_schema = estructura.nombre.lower().replace(" ","_")
    check_schema = db.session.execute("""SELECT * FROM pg_catalog.pg_namespace WHERE nspname = \'"""+nombre_del_schema+"""\'""").fetchone()
    esta_monitoreada = True
    if(check_schema is None):
        esta_monitoreada = False
    #Consulta por rutas de imágenes y BIM asociados
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }
    return render_template('tiemporeal.html', **context)


####################### Inicio CRUD Estructura, Sensores y Usuarios ####################### 

### VISTA PRINCIPAL ###
#PERMISOS = ADMINISTRADOR
#Ver Panel
@views_api.route('/gestion', methods=['GET'])
@login_required
def panel_administracion():
    if(current_user.permisos == "Administrador"):
        return render_template('panel_gestion.html')
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

### USUARIOS ###

#PERMISOS = ADMINISTRADOR
#Ver Usuarios
@views_api.route('/gestion/usuarios', methods=['GET'])
@login_required
def administrar_usuarios():
    if(current_user.permisos == "Administrador"):
        usuarios = Usuario.query.all()
        context = {'usuarios':usuarios}
        return render_template('panel_gestion_usuarios.html', **context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/password_reset_verified/<token>', methods=['GET','POST'])
def reset_verified(token):
    user = Usuario.verify_reset_token(token)
    print(user)
    if not user:
        return redirect(url_for('views_api.login'))
    password = request.form.get('password')
    if password:
        print(password)
        print(generate_password_hash(password))
        user.contrasena = generate_password_hash(password)
        db.session.commit()
        return redirect(url_for('views_api.login'))
    return render_template('reset_verified.html')

#PERMISOS = ADMINISTRADOR
#Editar Usuario
@views_api.route('/editar_permisos', methods=['POST'])
def cambiar_permisos():
    if request.method == "POST":
        if(current_user.permisos == "Administrador"):
            user = Usuario.query.filter_by(id=request.form.get('userid')).first()
            user.permisos = request.form.get('permisos')
            db.session.commit()
            return redirect(url_for('views_api.administrar_usuarios'))
        else:
            return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Eliminar Usuario
@views_api.route('/eliminar_usuario', methods=['POST'])
def eliminar_usuario():
    if request.method == "POST":
        if(current_user.permisos == "Administrador"):
            user = Usuario.query.filter_by(id=request.form.get('userid')).delete()
            db.session.commit()
            return redirect(url_for('views_api.administrar_usuarios'))
        else:
            return redirect(url_for('views_api.usuario_no_autorizado'))

### ESTRUCTURAS ###

#PERMISOS = ADMINISTRADOR
#Cargar Estructuras
@views_api.route('/gestion/estructura_crear', methods=['GET'])
@login_required
def administrar_estructura_creacion():
  if(current_user.permisos == "Administrador"):
    puentes = Estructura.query.all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_estructura_crear.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/gestion/estructura_modificar', methods=['GET'])
@login_required
def administrar_estructura_modificacion():
  if(current_user.permisos == "Administrador"):
    puentes = Estructura.query.all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_estructura_modificar.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Crear Estructura
@views_api.route('/gestion/estructura/create', methods=['POST'])
@login_required
def crear_estructura():
  if(current_user.permisos == "Administrador"):
    try:
      nuevo_puente = Estructura(nombre=request.form.get("nombre"), 
                                rol=request.form.get("rol"), 
                                nombre_camino=request.form.get("nombre_camino"),
                                cauce_queb = request.form.get("cauce_queb"),
                                provincia = request.form.get("provincia"),
                                tipo_activo = "Puente",
                                region = request.form.get("region"),
                                coord_x = request.form.get("coord_x"),
                                coord_y = request.form.get("coord_y"),
                                largo = request.form.get("largo"),
                                ancho_total = request.form.get("ancho_total"),
                                mat_estrib = request.form.get("mat_estrib"),
                                piso = request.form.get("piso"),
                                mat_vigas = request.form.get("mat_vigas"),
                                num_cepas = request.form.get("num_cepas"),
                                mat_cepas = request.form.get("mat_cepas"))
      db.session.add(nuevo_puente)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_estructura_creacion'))
      
    flash("Puente " + request.form.get("nombre") +" registrado.", 'info')
    return redirect(url_for('views_api.administrar_estructura_creacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Buscar Estructura AJAX
@views_api.route('/gestion/estructura/retrieve/<int:id_estructura>', methods=['POST'])
@login_required
def buscar_estructura_ajax(id_estructura):
  if request.method == "POST":
    estructura = Estructura.query.filter_by(id=id_estructura).first()
    context = {'estructura' : estructura}
    return jsonify({'htmlresponse': render_template('editar_estructura.html',estructura=estructura)})

#PERMISOS = ADMINISTRADOR
#Editar Estructura
@views_api.route('/gestion/estructura/update/<int:id_estructura>', methods=['POST'])
@login_required
def editar_estructura(id_estructura):
  if(current_user.permisos == "Administrador"):
    try:
      estructura = Estructura.query.filter_by(id=id_estructura).first()
      estructura.nombre=request.form.get("nombre")
      estructura.nombre_camino=request.form.get("nombre_camino")
      estructura.cauce_queb = request.form.get("cauce_queb")
      estructura.provincia = request.form.get("provincia")
      estructura.region = request.form.get("region")
      estructura.coord_x = request.form.get("coord_x")
      estructura.coord_y = request.form.get("coord_y")
      estructura.largo = request.form.get("largo")
      estructura.ancho_total = request.form.get("ancho_total")
      estructura.mat_estrib = request.form.get("mat_estrib")
      estructura.piso = request.form.get("piso")
      estructura.mat_vigas = request.form.get("mat_vigas")
      estructura.num_cepas = request.form.get("num_cepas")
      estructura.mat_cepas = request.form.get("mat_cepas")
      db.session.add(estructura)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_estructura'))
            
    flash("Puente " + estructura.nombre + " Actualizado.", 'info')
    return redirect(url_for('views_api.administrar_estructura_modificacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Eliminar Estructura
@views_api.route('/gestion/estructura/delete/<int:id_estructura>', methods=['POST'])
@login_required
def eliminar_estructura(id_estructura):
  if(current_user.permisos == "Administrador"):
    try:
      estructura = Estructura.query.filter_by(id=id_estructura).delete()
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_estructura'))
      
    flash("Puente eliminado del registro.", 'info')  
    return redirect(url_for('views_api.administrar_estructura_modificacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
### ELEMENTOS ESTRUCTURALES ###

#PERMISOS = ADMINISTRADOR
#Carga de Tipos de Elementos Estructurales
@views_api.route('/gestion/elementos/tipo', methods=['GET'])
@login_required
def administrar_tipos_elementos():
  if(current_user.permisos == "Administrador"):  
    tipos = TipoElemento.query.all()
    context = {'tipos_elem': tipos}
    return render_template('panel_gestion_elementos_tipo.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Carga de estructuras a filtar y Tipos de Elementos Estructurales para creacion de elemento.
@views_api.route('/gestion/elementos/crear', methods=['GET'])
@login_required
def administrar_elementos_creacion():
  if(current_user.permisos == "Administrador"):
    puentes = Estructura.query.all()
    tipos = TipoElemento.query.all()
    context = {'puentes': puentes,
               'tipos_elem': tipos}
    return render_template('panel_gestion_elementos_crear.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Carga de estructuras a filtar y Tipos de Elementos Estructurales para modificacion de elemento.
@views_api.route('/gestion/elementos/modificar', methods=['GET'])
@login_required
def administrar_elementos_modificacion():
  if(current_user.permisos == "Administrador"):
    puentes = Estructura.query.all()
    tipos = TipoElemento.query.all()
    context = {'puentes': puentes,
               'tipos_elem': tipos}
    return render_template('panel_gestion_elementos_modificar.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Crear Tipo Elemento
@views_api.route('/gestion/elementos/create_tipo', methods=['POST'])
@login_required
def crear_tipo_elemento():
  if(current_user.permisos == "Administrador"):
    try:
      nuevo_tipo = TipoElemento(nombre_zona=request.form.get("nombre_zona"))                           
      db.session.add(nuevo_tipo)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_tipos_elementos'))
      
    flash("Tipo de Elemento <" + nuevo_tipo.nombre_zona +"> registrado.", 'info')
    return redirect(url_for('views_api.administrar_tipos_elementos'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
        
#PERMISOS = ADMINISTRADOR
#Crear Elemento
@views_api.route('/gestion/elementos/create', methods=['POST'])
@login_required
def crear_elemento():
  if(current_user.permisos == "Administrador"):
    try:
      nuevo_elemento = ElementoEstructural(id_estructura=request.form.get("id_estructura"), 
                                tipo_zona=request.form.get("tipo_zona"), 
                                material=request.form.get("material"),
                                descripcion = request.form.get("descripcion"))                           
      db.session.add(nuevo_elemento)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_elementos_creacion'))
      
    flash("Elemento Estructural <" + nuevo_elemento.descripcion +"> registrado.", 'info')
    return redirect(url_for('views_api.administrar_elementos_creacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Buscar Elementos AJAX
@views_api.route('/gestion/elementos/retrieve/<int:id_estructura>', methods=['POST'])
@login_required
def buscar_elementos_ajax(id_estructura):
  if request.method == "POST":
    elementstruct = ElementoEstructural.query.filter_by(id_estructura=id_estructura).all()
    tipos = TipoElemento.query.all()
    context = {'elementos' : elementstruct,
               'tipos': tipos}
    return jsonify({'htmlresponse': render_template('elementos_de_estructura.html',**context)})

#PERMISOS = ADMINISTRADOR
#Editar Elemento
@views_api.route('/gestion/elementos/update/<int:id_elemento>', methods=['POST'])
@login_required
def editar_elemento(id_elemento):
  if(current_user.permisos == "Administrador"):
    try:
      elemento = ElementoEstructural.query.filter_by(id=id_elemento).first()
      elemento.tipo_zona=request.form.get("tipo_zona"), 
      elemento.material=request.form.get("material"),
      elemento.descripcion = request.form.get("descripcion")
      db.session.add(elemento)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_elementos_modificacion'))
            
    flash("Elemento Estructural <" + elemento.descripcion + "> actualizado.", 'info')
    return redirect(url_for('views_api.administrar_elementos_modificacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Eliminar Elemento
@views_api.route('/gestion/elementos/delete/<int:id_elemento>', methods=['POST'])
@login_required
def eliminar_elemento(id_elemento):
  if(current_user.permisos == "Administrador"):
    try:
      elemento = ElementoEstructural.query.filter_by(id=id_elemento).delete()
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_elementos_modificacion'))
      
    flash("Elemento Estructural eliminado del registro.", 'info')  
    return redirect(url_for('views_api.administrar_elementos_modificacion'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
### DISPOSITIVOS ###

#PERMISOS = ADMINISTRADOR
#Cargar Dispositivos
@views_api.route('/gestion/dispositivos', methods=['GET'])
@login_required
def administrar_dispositivos():
  if(current_user.permisos == "Administrador"):  
    puentes = Estructura.query.filter_by(en_monitoreo = True).all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_dispositivos.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Crear Dispositivo
@views_api.route('/gestion/dispositivos/create', methods=['POST'])
@login_required
def crear_dispositivos():
  if(current_user.permisos == "Administrador"):

    return redirect(url_for('views_api.administrar_dispositivos'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Buscar Dispositivos de Estructura AJAX
@views_api.route('/gestion/dispositivos/retrieve/<int:id_estructura>', methods=['POST'])
@login_required
def buscar_dispositivos_ajax(id_estructura):
  if(current_user.permisos == "Administrador"):
    if request.method == "POST":
      
      sensores_actuales = db.session.query(Sensor.id, Sensor.modelo, Sensor.serial, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, Sensor.uuid_device, DescripcionSensor.descripcion.label("nombre_sensor"), DAQPorZona.id_daq).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id_estructura, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, SensorInstalado.conexion_actual == Canal.id, Canal.id_daq == DAQPorZona.id_daq, ).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc()).all()
      
      daq_actuales = db.session.query(DAQ.id, DAQ.nro_canales, DescripcionDAQ.caracteristicas, EstadoDAQ.detalles, EstadoDAQ.fecha_estado).filter(EstadoDAQ.id_daq == DAQ.id, DescripcionDAQ.id_daq == DAQ.id, DAQPorZona.id_daq == DAQ.id, ElementoEstructural.id == DAQPorZona.id_zona, DAQPorZona.id_estructura == id_estructura).distinct(DAQ.id).order_by(DAQ.id.asc(), EstadoDAQ.fecha_estado.desc()).all()
      
      ip_instancia = Estructura.query.filter_by(id=id_estructura).first().ip_instancia
      
      if ip_instancia != None:
        #obtencion API KEY de TB    
        api_key_url = requests.post(ip_instancia + '/api/auth/login',data='{"username":"tenant@thingsboard.org", "password":"tenant"}', headers={'Content-Type': 'application/json','Accept': 'application/json'})
        json_response = api_key_url.json()
        
        #Generacion de API_KEY para autentificacion en Swagger
        x_auth = 'Bearer ' + json_response['token']
        
        #Peticion a Swagger de DEVICES
        response = requests.get( ip_instancia + '/api/tenant/deviceInfos?pageSize=20&page=0',headers={'Accept' : 'application/json','X-Authorization': x_auth},)
        json_devices = response.json()
        
        dict_uuid={}
        dict_name={}
        for device in json_devices['data']:
          dict_uuid[device['id']['id']] = device['name']
          dict_name[device['name']] = device['id']['id']
          
        context = {
        'dict_uuid': dict_uuid,
        'dict_name': dict_name,
        'sensores_puente' : sensores_actuales,
        'daqs_puente' : daq_actuales  
        }
      
      else:
        context = {
        'sensores_puente' : sensores_actuales,
        'daqs_puente' : daq_actuales
        } 
      return jsonify({'htmlresponse': render_template('dispositivos_de_estructura.html',**context,id_estructura = id_estructura)})
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Editar Dispositivo
@views_api.route('/gestion/dispositivos/update_uuid/<int:id_sensor><string:uuid>', methods=['POST'])
@login_required
def editar_uuid_sensor(id_sensor, uuid):
  if(current_user.permisos == "Administrador"):
    try:
      sensor = Sensor.query.filter_by(id=id_sensor).first()
      sensor.uuid_device = uuid
      db.session.add(sensor)
      db.session.commit()
      
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_dispositivos'))
            
    flash("UUID actualizado.", 'info')
    return redirect(url_for('views_api.administrar_dispositivos'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Solucionar discpreancias de UUID y nombre repsecto a la información desde Thingsboard
@views_api.route('/gestion/dispositivos/solucionar_discrepancias/<int:id_estructura>', methods=['POST'])
@login_required
def solucionar_discrepancias_uuid(id_estructura):
  
  uuid_adjust = 0
  name_adjust = 0  

  if(current_user.permisos == "Administrador"):
    
    ip_instancia = Estructura.query.filter_by(id=id_estructura).first().ip_instancia
      
    if ip_instancia != None:
        #obtencion API KEY de TB    
        api_key_url = requests.post(ip_instancia + '/api/auth/login',data='{"username":"tenant@thingsboard.org", "password":"tenant"}', headers={'Content-Type': 'application/json','Accept': 'application/json'})
        json_response = api_key_url.json()
        
        #Generacion de API_KEY para autentificacion en Swagger
        x_auth = 'Bearer ' + json_response['token']
        
        #Peticion a Swagger de DEVICES
        response = requests.get( ip_instancia + '/api/tenant/deviceInfos?pageSize=20&page=0',headers={'Accept' : 'application/json','X-Authorization': x_auth},)
        json_devices = response.json()
        
        dict_uuid={}
        dict_name={}
        for device in json_devices['data']:
          dict_uuid[device['id']['id']] = device['name']
          dict_name[device['name']] = device['id']['id']          
        
        
        try:
          sensores_actuales = SensorInstalado.query.filter_by(id_estructura = id_estructura).all()
          for element in sensores_actuales:
            sensor = Sensor.query.filter_by(id=element.id_sensor).first()
            nombre = DescripcionSensor.query.filter_by(id_sensor_instalado=element.id).first()
            if not sensor.uuid_device in dict_uuid.keys():
              sensor.uuid_device = dict_name[nombre.descripcion]
              db.session.add(sensor)
              uuid_adjust += 1
            if not nombre.descripcion in dict_name.keys():
              nombre.descripcion = dict_uuid[sensor.uuid_device]
              name_adjust += 1
          
          db.session.commit()
          
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
          db.session.rollback()
          flash(str(error.orig) + " for parameters" + str(error.params),'error')
          return redirect(url_for('views_api.administrar_dispositivos'))
            
        flash("Se detectaron y corrigieron " + str(uuid_adjust) + " discrepancias de UUID y " + str(name_adjust) + " discrepancias de nombre.", 'info')
        return redirect(url_for('views_api.administrar_dispositivos'))
      
    return redirect(url_for('views_api.administrar_dispositivos'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Editar Dispositivo
@views_api.route('/gestion/dispositivos/update/<int:id_device>', methods=['POST'])
@login_required
def editar_dispositivo(id_device):
  if(current_user.permisos == "Administrador"):
    try:
      sensor = Sensor.query.filter_by(id=id_device).first()
      sensor.modelo = request.form.get("modelo")
      sensor.serial = request.form.get("serial")
      db.session.add(sensor)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_dispositivos'))
            
    flash("Sensor actualizado.", 'info')
    return redirect(url_for('views_api.administrar_dispositivos'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Eliminar Dispositivo. Utilizar solo cuando el sensor no se encuentre representado por información de Thingsboard.
@views_api.route('/gestion/dispositivos/delete/<int:id_device>', methods=['POST'])
@login_required
def eliminar_dispositivo(id_device):
  if(current_user.permisos == "Administrador"):
    try:
      sensor = SensorInstalado.query.filter_by(id=id_device).delete()
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_dispositivos'))
      
    flash("Sensor eliminado del registro.", 'info')  
    return redirect(url_for('views_api.administrar_dispositivos'))

### THINGSBOARD ###
    
#PERMISOS = ADMINISTRADOR
#Acceso a Thingsboard
@views_api.route('/gestion/thingsboard', methods=['GET'])
@login_required
def administrar_thingsboard():
  if(current_user.permisos == "Administrador"):  
    puentes = Estructura.query.all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_thingsboard.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

### MONITOREOS ###

#PERMISOS = ADMINISTRADOR
#Acceso a Creación de Monitoreos
@views_api.route('/gestion/monitoreos', methods=['GET'])
@login_required
def administrar_monitoreos():
  if(current_user.permisos == "Administrador"):  
    puentes = Estructura.query.all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_monitoreo.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Acceso a Monitoreos Configurados
@views_api.route('/gestion/monitoreos/configurar', methods=['GET'])
@login_required
def administrar_monitoreos_configurados():
  if(current_user.permisos == "Administrador"):  
    puentes = Estructura.query.filter_by(en_monitoreo=True).all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_monitoreo_modificar.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
#PERMISOS = ADMINISTRADOR
#Inicio de Monitoreo en una Estructura
@views_api.route('/gestion/iniciar_monitoreo/<int:id_estructura>', methods=['GET'])
@login_required
def iniciar_monitoreo_gestion(id_estructura):
  if(current_user.permisos == "Administrador"):  
    puente = Estructura.query.filter_by(id = id_estructura).first()
    context = {'puente': puente}
    return render_template('iniciar_monitoreo.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Verificar conexión con Thingsboard
@views_api.route('/check_thingsboard_instance/<int:id_estructura>', methods=['POST'])
@login_required
def check_thingsboard_instance(id_estructura):
  if(current_user.permisos == "Administrador"):  
    ip_instancia = request.form.get('ip_instancia')
    username = request.form.get('user')
    password = request.form.get('passw')

    user_data= {}
    user_data['user'] = username
    user_data['pass'] = password
    user_data['ip'] = ip_instancia

    if not ip_instancia:
      return jsonify({'error':render_template('error.html',message = "Por Favor Ingrese una Dirección. ")})
    try:

      api_key_url = requests.post(ip_instancia + '/api/auth/login',data='{"username":"' + username +  '" , "password": "'+ password +'" }', headers={'Content-Type': 'application/json','Accept': 'application/json'})
      json_response = api_key_url.json()
      
      if "token" in json_response:
        #Generacion de API_KEY para autentificacion en Swagger
        x_auth = 'Bearer ' + json_response['token']
        
        #Peticion a Swagger de DEVICES
        response = requests.get( ip_instancia + '/api/tenant/deviceInfos?pageSize=20&page=0',headers={'Accept' : 'application/json','X-Authorization': x_auth},)
        json_devices = response.json()
        
        element_list = []
        devices = {}
        devices['data'] = []
        for device in json_devices['data']:

          attr_request = requests.get(ip_instancia + '/api/plugins/telemetry/DEVICE/' + str(device['id']['id'])+'/values/attributes',headers={'Accept' : 'application/json','X-Authorization': x_auth})
          attr_response = attr_request.json()

          attr_device = {}
          for attribute in attr_response:
            if(attribute['key'] == "Canales"):
              attr_device['canales'] = attribute['value']
            if(attribute['key'] == "Elemento Estructural"):
              attr_device['elemento-estructural'] = attribute['value']
              element_list.append(attribute['value'])
            if(attribute['key'] == "Canal"):
              attr_device['canal'] = attribute['value']
            if(attribute['key'] == "Frecuencia"):
              attr_device['frecuencia'] = attribute['value']

          device = {'uuid' : device['id']['id'],
                    'name' : device['name'],
                    'type' : device['type'],
                    'attrs': attr_device
          }
          devices['data'].append(device)
        
        elementos_estructurales = list(dict.fromkeys(element_list))
        tipos_de_elementos = TipoElemento.query.all()
        tipos_de_sensor = TipoSensor.query.all()
        context = {'response': devices,
                   'elementos_estructurales': elementos_estructurales,
                   'tipo_sensor': tipos_de_sensor,
                   'puente': id_estructura,
                   'tb_data': user_data}
        return jsonify({'htmlresponse':render_template('form_inicio_monitoreo.html',**context)})
      else:
        return jsonify({'error':render_template('error.html',message = "Fallo en la Autentificación.")})
      
    except requests.exceptions.HTTPError as e:
      return jsonify({'error':render_template('error.html',message = "Dirección no válida.")})
    except requests.exceptions.MissingSchema as e:
      return jsonify({'error':render_template('error.html',message = "Anteponga 'http://' a su dirección.")})
    except requests.exceptions.InvalidURL as e: 
      return jsonify({'error':render_template('error.html',message = "Compruebe la Dirección entregada e intente nuevamente.")})
      
    except requests.exceptions.ConnectionError as e:
      return jsonify({'error':render_template('error.html',message = "Dirección no válida, verifique si añadió el puerto.")})
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))


### PARAMETROS AR ###

#PERMISOS = ADMINISTRADOR
#Cargar Puentes para Configuración de parámetros
@views_api.route('/gestion/parametros', methods=['GET'])
@login_required
def administrar_parametros():
  if(current_user.permisos == "Administrador"):  
    puentes = Estructura.query.filter_by(en_monitoreo = True).all()
    context = {'puentes': puentes}
    return render_template('panel_gestion_parametros_ar.html',**context)
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))

#PERMISOS = ADMINISTRADOR
#Buscar Configuraciones de Estructura AJAX
@views_api.route('/gestion/parametros/retrieve/<int:id_estructura>', methods=['POST'])
@login_required
def buscar_configuracion_ajax(id_estructura):
  if(current_user.permisos == "Administrador"):
    if request.method == "POST":
      configuracion = ConfiguracionModeloAR.query.filter_by(id_estructura=id_estructura).first()
      
      context = {
        'configuracion': configuracion
      }
      return jsonify({'htmlresponse': render_template('form_configuracion.html',**context,id_estructura = id_estructura)})
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))    

#PERMISOS = ADMINISTRADOR
#Editar Configuración de parámetros
@views_api.route('/gestion/parametros/edit/<int:id_configuracion>', methods=['POST'])
@login_required
def editar_configuracion_ar(id_configuracion):
  if(current_user.permisos == "Administrador"):  
    try:
      configuracion = ConfiguracionModeloAR.query.filter_by(id=id_configuracion).first()
      configuracion.cantidad_coeficientes_ar=request.form.get("cant_coef_ar")
      configuracion.umbral_distancia=request.form.get("dist_umbrales")
      configuracion.cantidad_umbrales = request.form.get("cant_umbrales")
      configuracion.numero_peaks = request.form.get("nro_peaks")
      configuracion.tiempo_peaks_segundos = request.form.get("tiempo_peaks")
      configuracion.tipo_peaks=request.form.get("tipo_peaks")
      configuracion.actualizacion_completa=True
      db.session.add(configuracion)
      db.session.commit()
    except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError) as error:
      db.session.rollback()
      flash(str(error.orig) + " for parameters" + str(error.params),'error')
      return redirect(url_for('views_api.administrar_parametros'))
            
    flash("Configuración actualizada.", 'info')
    return redirect(url_for('views_api.administrar_parametros'))
  else:
    return redirect(url_for('views_api.usuario_no_autorizado'))
    
############################## Prueba JSON DataTable #########################################
@views_api.route('/cargar_estructuras', methods=['GET'])
@login_required
def cargar_estructuras_ajax(): 
    puentes = Estructura.query.all()
    data = []
    for element in puentes:
      puente = {'Rol': element.rol,
                'Nombre': {'nombre': element.nombre, 'ruta': "estructura/" + str(element.id)},
                'Region': element.region,
                'Provincia': element.provincia,
                'Monitoreo': {'monitoreo': element.en_monitoreo, 'ruta': url_for('views_api.iniciar_monitoreo_gestion',id_estructura = element.id), 'nombre': element.nombre}
                }
      data.append(puente)
    return jsonify({'data': data})

###################### INTEGRACIÓN ALMACENAMIENTO HISTÓRICO ########################
@views_api.route('/hconsulta/<int:id>', methods=["POST","GET"])
def hconsulta(id):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    esta_monitoreada = estructura.en_monitoreo
    #Consulta por rutas de im�genes y BIM asociados
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }

    params = {
    'region' : 'sa-east-1',
    'database' : 'historical-db',
    'bucket' : 'shm-historical-temp',
    'path'  : 'consultas/test',
    'user_id': current_user.id
    }

    ip_instance = Estructura.query.get(id).ip_instancia
    if(ip_instance is None):
        return redirect(url_for('views_api.informacion_estructura',id = id))

    info_sensores, info_ejes = swagger.get_sensor_axis(ip_instance)

    info_consultas = aws_functions.get_consultas(params)

    for i in info_sensores:
        sensor_query = Sensor.query.filter_by(uuid_device = i["uuid"]).first()
        frecuencia = sensor_query.frecuencia
        modelo = sensor_query.modelo
        tipo_sensor = TipoSensor.query.filter_by(id = sensor_query.tipo_sensor).first().nombre
        sensor_instalado = SensorInstalado.query.filter_by(id = sensor_query.id).first()
        id_sensor_instalado = sensor_instalado.id
        estado_sensor = EstadoSensor.query.filter_by(id_sensor_instalado = sensor_instalado.id).first().operatividad
        zona_sensor = ElementoEstructural.query.filter_by(id = sensor_instalado.id_zona).first().descripcion
        canal = Canal.query.filter_by(id = sensor_instalado.conexion_actual).first()
        numero_canal = canal.numero_canal
        daq = DescripcionDAQ.query.filter_by(id_daq = canal.id_daq).first().caracteristicas        
        i.update({"frecuencia": frecuencia,"modelo": modelo, "tipo_sensor":tipo_sensor, "estado_sensor": estado_sensor, "zona_sensor": zona_sensor, "numero_canal": numero_canal, "daq":daq,"id_sensor_instalado":id_sensor_instalado,"id_daq":canal.id_daq})
    
    if request.method == "POST":
        destino_consulta = request.form["destino_consulta"]
        rango_consulta = "rango_completo"
        #rango_consulta = request.form["rango_consulta"]
        fecha_inicial = request.form["fecha_inicial"]
        hora_inicial = "00:00"
        #hora_inicial = request.form["hora_inicial"]
        fecha_final = request.form["fecha_final"]
        hora_final = "00:00"
        #hora_final = request.form["hora_final"]
        lista_sensores = request.form.getlist("sensor_selected")
        consultas_ejes = request.form.getlist("consultas_ejes")
        consultas_sensor = request.form.getlist("consultas_sensor")
        
        id_sensores = []

        for i in lista_sensores:
            for j in info_sensores:
                if j["name"] == i:
                    id_sensores.append(j["uuid"])

        ####Conversion tiempo local a UTC####
        local_timezone = pytz.timezone ("America/Santiago")
        naive = datetime.strptime(fecha_inicial + " " + hora_inicial, "%Y-%m-%d %H:%M")
        local_dt_i = local_timezone.localize(naive, is_dst=None)
        naive = datetime.strptime(fecha_final + " " + hora_final, "%Y-%m-%d %H:%M")
        local_dt_f = local_timezone.localize(naive, is_dst=None)

        utc_dt_i = local_dt_i.astimezone(pytz.utc)
        utc_dt_f = local_dt_f.astimezone(pytz.utc)
        #####################################
        values = {
            'destino_consulta' : destino_consulta,
            'rango_consulta' : rango_consulta,
            'fecha_inicial' : utc_dt_i.strftime("%Y-%m-%d"),
            'hora_inicial'  : utc_dt_i.strftime("%H:%M"),
            'fecha_final': utc_dt_f.strftime("%Y-%m-%d"),
            'hora_final'  : utc_dt_f.strftime("%H:%M"),
            'lista_sensores'  : lista_sensores,
            'id_sensores'  : id_sensores,
            'consultas_ejes' : consultas_ejes,
            'consultas_sensor'  : consultas_sensor
        }
        athena_status = aws_functions.query_athena(params,values)
        if(athena_status == True):
            flash("Solicitud recibida","success")
        else:
            flash("Error","error")
        return redirect(url_for("views_api.hconsulta",id=id))
   
    return render_template('hconsulta.html', **context, info_consultas = info_consultas, info_sensores = info_sensores, info_ejes = info_ejes)

@views_api.route('/hdetalles/<int:id>/<string:filename>')
def hdetalles(id,filename):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    esta_monitoreada = estructura.en_monitoreo
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }

    params = {
    'region' : 'sa-east-1',
    'database' : 'historical-db',
    'bucket' : 'shm-historical-temp',
    'path'  : 'consultas/test',
    'user_id': current_user.id
    }
        
    header_consulta , detalle_consulta, metadata_consulta = aws_functions.detalle_consultas(params,filename)

   
    return render_template('hdetalles.html', **context, header= header_consulta, detalle = detalle_consulta, metadata = metadata_consulta)
 

@views_api.route('/hdescarga/<int:id>', methods=["POST","GET"])
def hdescarga(id):
#Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    esta_monitoreada = estructura.en_monitoreo
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }

    params = {
    'region' : 'sa-east-1',
    'database' : 'historical-db',
    'bucket' : 'shm-historical-temp',
    'path'  : 'descargas/test',
    'path_athena' : 'athena/test',
    'user_id': current_user.id
    }

    ip_instance = Estructura.query.get(id).ip_instancia
    if(ip_instance is None):
        return redirect(url_for('views_api.informacion_estructura',id = id))

    info_sensores, info_ejes = swagger.get_sensor_axis(ip_instance)
    
    info_consultas = aws_functions.get_consultas(params)

    for i in info_sensores:
        sensor_query = Sensor.query.filter_by(uuid_device = i["uuid"]).first()
        frecuencia = sensor_query.frecuencia
        modelo = sensor_query.modelo
        tipo_sensor = TipoSensor.query.filter_by(id = sensor_query.tipo_sensor).first().nombre
        sensor_instalado = SensorInstalado.query.filter_by(id = sensor_query.id).first()
        id_sensor_instalado = sensor_instalado.id
        estado_sensor = EstadoSensor.query.filter_by(id_sensor_instalado = sensor_instalado.id).first().operatividad
        zona_sensor = ElementoEstructural.query.filter_by(id = sensor_instalado.id_zona).first().descripcion
        canal = Canal.query.filter_by(id = sensor_instalado.conexion_actual).first()
        numero_canal = canal.numero_canal
        daq = DescripcionDAQ.query.filter_by(id_daq = canal.id_daq).first().caracteristicas        
        i.update({"frecuencia": frecuencia,"modelo": modelo, "tipo_sensor":tipo_sensor, "estado_sensor": estado_sensor, "zona_sensor": zona_sensor, "numero_canal": numero_canal, "daq":daq,"id_sensor_instalado":id_sensor_instalado,"id_daq":canal.id_daq})

    if request.method == "POST":
        destino_consulta = request.form["destino_consulta"]
        rango_consulta = "rango_completo"
        #rango_consulta = request.form["rango_consulta"]
        fecha_inicial = request.form["fecha_inicial"]
        hora_inicial = "00:00"
        #hora_inicial = request.form["hora_inicial"]
        fecha_final = request.form["fecha_final"]
        hora_final = "00:00"
        #hora_final = request.form["hora_final"]
        lista_sensores = request.form.getlist("sensor_selected")
        consultas_ejes = request.form.getlist("consultas_ejes")
        consultas_sensor = request.form.getlist("consultas_sensor")

        id_sensores = []

        for i in lista_sensores:
            for j in info_sensores:
                if j["name"] == i:
                    id_sensores.append(j["uuid"])

        ####Conversion tiempo local a UTC####
        local_timezone = pytz.timezone ("America/Santiago")
        naive = datetime.strptime(fecha_inicial + " " + hora_inicial, "%Y-%m-%d %H:%M")
        local_dt_i = local_timezone.localize(naive, is_dst=None)
        naive = datetime.strptime(fecha_final + " " + hora_final, "%Y-%m-%d %H:%M")
        local_dt_f = local_timezone.localize(naive, is_dst=None)

        utc_dt_i = local_dt_i.astimezone(pytz.utc)
        utc_dt_f = local_dt_f.astimezone(pytz.utc)
        #####################################
        values = {
            'destino_consulta' : destino_consulta,
            'rango_consulta' : rango_consulta,
            'fecha_inicial' : utc_dt_i.strftime("%Y-%m-%d"),
            'hora_inicial'  : utc_dt_i.strftime("%H:%M"),
            'fecha_final': utc_dt_f.strftime("%Y-%m-%d"),
            'hora_final'  : utc_dt_f.strftime("%H:%M"),
            'lista_sensores'  : lista_sensores,
            'id_sensores'  : id_sensores,
            'consultas_ejes' : consultas_ejes
        }
        athena_status = aws_functions.download_query_athena(params,values)
        if(athena_status == True):
            flash("Solicitud recibida","success")
        else:
            flash("Error","error")
        return redirect(url_for("views_api.hdescarga",id=id))

    return render_template('hdescarga.html', **context, info_consultas = info_consultas, info_sensores = info_sensores, info_ejes = info_ejes)

@views_api.route('/hdetallesdescarga/<int:id>/<string:filename>')
def hdetallesdescarga(id,filename):
    #Detalles generales de la estructura
    estructura = Estructura.query.filter_by(id=id).first()
    estado_monitoreo = EstadoEstructura.query.filter_by(id_estructura = id).order_by(EstadoEstructura.fecha_estado.desc()).first()
    esta_monitoreada = estructura.en_monitoreo
    imagenes_estructura = ImagenEstructura.query.filter_by(id_estructura = id).all()
    bim_estructura = VisualizacionBIM.query.filter_by(id_estructura = id).first()
    context = {
        'datos_puente':estructura,
        'estado_monitoreo':estado_monitoreo,
        'esta_monitoreada':esta_monitoreada,
        'imagenes_estructura':imagenes_estructura,
        'bim_estructura' : bim_estructura
    }

    params = {
    'region' : 'sa-east-1',
    'database' : 'historical-db',
    'bucket' : 'shm-historical-temp',
    'path'  : 'descargas/test',
    'user_id': current_user.id
    }

    metadata_consulta, lista_descargables = aws_functions.detalle_descarga(params,filename)

    return render_template('hdetallesdescarga.html', **context, metadata = metadata_consulta, lista_descargables = lista_descargables)

@views_api.route('/descargar/<string:file_name>')
def hgetdescarga(file_name):
    params = {
    'region' : 'sa-east-1',
    'database' : 'historical-db',
    'bucket' : 'shm-historical-temp',
    'path'  : 'descargas/test',
    'user_id': current_user.id
    }

    url = aws_functions.get_attachment_url(params,file_name)
    return redirect(url, code=302)


############################### Ultima iteracion ##########################

#Vista de mapa nueva
@views_api.route('/mapa')
@login_required
def mapa():
    puentes = Estructura.query.all()
    #Genera los markers para el mapa
    markers = []
    for i in puentes:
        markers.append([i.coord_x, i.coord_y, i.tipo_activo.capitalize()+' '+i.nombre.capitalize(), i.id])
    #Variables para el template
    context = {
        'puentes' : puentes,
        'markers' : markers
    }
    return render_template('mapa.html', **context)

@views_api.route("/datos_recientes")
def datos_recientes():
    if current_user.is_authenticated:
        estructura = Estructura.query.filter_by(id=session['id_puente']).first()
        context = {
                'datos_puente':estructura,
                'esta_monitoreada':estructura.en_monitoreo
        }
        return render_template('template_datos_recientes.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route('/mi_cuenta')
def mi_cuenta():
    if current_user.is_authenticated:
        usuario = Usuario.query.filter_by(id=current_user.id).first()

        paramsconsultas = {
        'region' : 'sa-east-1',
        'database' : 'historical-db',
        'bucket' : 'shm-historical-temp',
        'path'  : 'consultas/test',
        'user_id': current_user.id
        }

        paramsdescargas = {
        'region' : 'sa-east-1',
        'database' : 'historical-db',
        'bucket' : 'shm-historical-temp',
        'path'  : 'descargas/test',
        'path_athena' : 'athena/test',
        'user_id': current_user.id
        }

        info_consultas = aws_functions.get_consultas(paramsconsultas)
        info_descargas = aws_functions.get_consultas(paramsdescargas)

        context = {

        'usuario':usuario,
        'info_consultas':info_consultas,
        'info_descargas':info_descargas
        }

        return render_template('mi_cuenta.html', **context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route("/deteccion_temprana/<int:id_puente>", methods= ['GET', 'POST'])
@login_required
def deteccion_temprana(id_puente):
    if current_user.is_authenticated:
        if(request.method == "GET"):
            estructura = Estructura.query.filter_by(id=id_puente).first()
            sensores = db.session.query(Sensor.id, SensorInstalado.id.label("si"), Sensor.frecuencia, TipoSensor.nombre, ElementoEstructural.descripcion, InstalacionSensor.fecha_instalacion, SensorInstalado.es_activo, DescripcionSensor.descripcion.label("nombre_sensor"),EstadoSensor.fecha_estado.label("fecha123"),EstadoSensor.confiabilidad, EstadoSensor.operatividad, EstadoSensor.mantenimiento,DescripcionDAQ.caracteristicas, DAQPorZona.id_daq, EstadoDanoSensor.estado.label("estado_dano_sensor"), EstadoDanoSensor.diahora_calculo.label("fecha_dano_sensor")).filter(TipoSensor.id == Sensor.tipo_sensor, SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_instalacion == InstalacionSensor.id, ElementoEstructural.id == SensorInstalado.id_zona, SensorInstalado.id_estructura == id_puente, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, EstadoSensor.id_sensor_instalado == SensorInstalado.id,SensorInstalado.conexion_actual == Canal.id, Canal.id_daq == DAQPorZona.id_daq, DescripcionDAQ.id_daq == DAQPorZona.id_daq, EstadoDanoSensor.id_sensor_instalado == SensorInstalado.id).distinct(Sensor.id).order_by(Sensor.id, InstalacionSensor.fecha_instalacion.desc(),EstadoSensor.fecha_estado.desc()).all()
            anomalias = db.session.query(DescripcionSensor.descripcion.label("nombre_sensor"), SensorInstalado.id.label("si"), AnomaliaPorHora.hora_calculo, AnomaliaPorHora.anomalia, AnomaliaPorHora.umbralx, AnomaliaPorHora.umbraly, AnomaliaPorHora.umbralz).filter(SensorInstalado.id_sensor == Sensor.id, SensorInstalado.id_estructura == id_puente, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, AnomaliaPorHora.id_sensor_instalado == SensorInstalado.id_sensor, DescripcionSensor.id_sensor_instalado == SensorInstalado.id,).order_by(AnomaliaPorHora.hora_calculo.desc()).all() 
            esta_monitoreada = estructura.en_monitoreo
            #Se guarda momentaneamente el id del puente en la sesión actual
            session['id_puente'] = id_puente
            lineplot = create_plot(sensores[0].nombre_sensor)
            barplot = create_mah(sensores[0].nombre_sensor)
            # estados = EstadoEstructura.query.filter_by(id_estructura=id_puente).order_by(EstadoEstructura.fecha_estado.desc()).all()
            estado_dano = EstadoDanoEstructura.query.filter_by(id_estructura=id_puente).first()
            zonas_dano = EstadoDanoElemento.query.filter_by(id_estructura=id_puente)
            zonas_dano = db.session.query(EstadoDanoElemento.diahora_calculo, EstadoDanoElemento.estado, ElementoEstructural.descripcion).filter(EstadoDanoElemento.id_estructura==id_puente, EstadoDanoElemento.id_elemento == ElementoEstructural.id)
            context = {
                'id_puente' : id_puente,
                'nombre_y_tipo_activo' : obtener_nombre_y_activo(id_puente),
                'datos_puente' : estructura,
                'esta_monitoreada':esta_monitoreada,
                'sensores': sensores,
                'anomalias_sensores': anomalias,
                'plot' : lineplot,
                'mah' : barplot,
                'estado_dano' : estado_dano,
                'zonas_dano' : zonas_dano,
            }
            return render_template('deteccion_temprana.html',**context)
    else:
        return redirect(url_for('views_api.usuario_no_autorizado'))

@views_api.route("/agregar_anomalia/<int:id_puente>/<int:id_sensor>")
def agregar_anomalia(id_puente,id_sensor):
    anomalia = AnomaliaPorHora(id_sensor_instalado = id_sensor, hora_calculo = datetime.now(), anomalia = True)
    db.session.add(anomalia)
    db.session.commit()
    print("Se agrega anomalia al sensor " + str(id_sensor))
    return redirect(url_for('views_api.deteccion_temprana', id_puente=session['id_puente']))

@views_api.route('/bar', methods=['GET', 'POST'])
def change_features():

    feature = request.args['selected']
    graphJSON= create_plot(feature)

    return graphJSON

@views_api.route('/bar2', methods=['GET', 'POST'])
def change_features2():

    feature = request.args['selected']
    graphJSON= create_mah(feature)

    return graphJSON

