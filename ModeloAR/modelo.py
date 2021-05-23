# from matplotlib import pyplot
from statsmodels.tsa.ar_model import AutoReg, ar_select_order
from statsmodels.tsa.api import acf, pacf, graphics
from sklearn.metrics import mean_squared_error
from math import sqrt
import numpy as np
# import sys
# import os
# sys.path.append(os.path.realpath('.'))
import pandas as pd
from scipy.spatial import distance
import scipy as stats
from matplotlib import pyplot
from statsmodels.tsa.ar_model import AutoReg, ar_select_order
from statsmodels.tsa.api import acf, pacf, graphics
from sklearn.metrics import mean_squared_error
from datetime import datetime 
from math import sqrt
from .peaks import scpa
from .data import getDataDay
from models import *
from sqlalchemy import func

def extraer_coef_total(data):   #Por sensor
    model = []
    for i in range(24):
        for j in range(3):
            model.append(AutoReg(data[i][j], lags = [1,2,3,4,5,6], old_names=True))
    model_fit = []
    for i in range(24*3):
        model_fit.append(model[i].fit())
    coef = []
    coef.append([x.params for x in model_fit])
    print(coef)
    return coef


def mahalanobis(x=None, data=None, cov=None): # (xi - x_mean)^T * cov^-1 * (xi - x_mean)
    x_mu = x - np.mean(data) # xi - x_mean
    if not cov:
        cov = np.cov(data.values.T)
    inv_covmat = np.linalg.inv(cov) # cov^-1
    left = np.dot(x_mu, inv_covmat) # (xi - x_mean)^T * cov^-1
    mahal = np.dot(left, x_mu.T) # (xi - x_mean)^T * cov^-1 * (xi - x_mean)
    #print(mahal)
    return mahal.diagonal()

def mahalanobisScipy(x=None, data=None, cov=None): # (xi - x_mean)^T * cov^-1 * (xi - x_mean)
    mahal = []
    x_mean = np.mean(data) # xi - x_mean
    #print(x.loc[0])
    if not cov:
        cov = np.cov(data.values.T)
    inv_covmat = np.linalg.inv(cov)
    for i in range(len(x)):
        dist = distance.mahalanobis(x.loc[i],x_mean,inv_covmat)
        mahal.append(dist*dist)
    return list(mahal)

def aplicar_modelo_total():
    for hora in range(24):
        print("Hora = ", hora)
        aplicar_modelo(hora)


def applyCoef(serie):
    model = []
    for i in range(3):
        model.append(AutoReg(serie[i], lags = [1,2,3,4,5,6], old_names=True))
    model_fit = []
    for i in range(3):
        model_fit.append(model[i].fit())
    coef = [x.params for x in model_fit]
    return coef


def aplicar_modelo(hora):
    data = getDataDay(hora)
    time = data['timestamp'].apply(lambda x: datetime.fromtimestamp(x/1e3))
    
    for col in data:
        print("Sensor = ", col)
        x = []
        y = []
        z = []
        if col == "timestamp":
            continue
        else:
            for row in data[col]:
                separados = row.replace("'", "").replace("{","").replace("}","").replace(":","").replace("x","").replace("y","").replace("z","").split(",")
                for i,datos in enumerate(separados):
                    separados[i] = float(datos.strip())
                x.append(separados[0])
                y.append(separados[1])
                z.append(separados[2])
            x = np.array(x)
            y = np.array(y)
            z = np.array(z)
            series_x = scpa(time, x, 3, 60)
            series_y = scpa(time, y, 3, 60)
            series_z = scpa(time, z, 3, 60)
            sens_x = []
            sens_y = []
            sens_z = []
            for i in range(0,3):
                sens_x.append(np.array(x[series_x[i][0]:series_x[i][-1]]))
                sens_y.append(np.array(y[series_y[i][0]:series_y[i][-1]]))
                sens_z.append(np.array(z[series_z[i][0]:series_z[i][-1]]))
            x_coef = applyCoef(sens_x)
            y_coef = applyCoef(sens_y)
            z_coef = applyCoef(sens_z)
            # print("x coef = ", x_coef)
            # print("y coef = ", y_coef)
            # print("z coef = ", z_coef)
            saveCoef(time[0], col, x_coef, axis = 0)
            saveCoef(time[0], col, y_coef, axis = 1)
            saveCoef(time[0], col, z_coef, axis = 2)


def saveCoef(hora, sensor, data, axis = 0):  # Guarda los coeficientes en la base de datos
    try:
        sensor_instalado = DescripcionSensor.query.filter_by(descripcion = str(sensor)).first()
        sensor_id = sensor_instalado.id_sensor_instalado
        reporte = ReporteDanoAR(id_sensor_instalado = sensor_id, hora = hora, axis = axis)
        db.session.add(reporte)
        db.session.flush()
        for i,serie in enumerate(data):
            modelo = ModeloAR(id_reporte_dano_ar = reporte.id, numero_modelo = i)
            db.session.add(modelo)
            db.session.flush()
            for j, valor in enumerate(serie):
               coef = CoeficienteAR(id_modelo_ar = modelo.id, valor = valor, numero = j)
               db.session.add(coef)
        db.session.commit()
    except:
        print("Fallo consulta")
        db.session.rollback()

def getCoef(puente_id, nombre_sensor, eje):
    coeficientes = db.session.query(CoeficienteAR.valor, CoeficienteAR.numero, ModeloAR.numero_modelo, ReporteDanoAR.id.label("reporte_dano_id") ).filter(DescripcionSensor.descripcion == nombre_sensor, ReporteDanoAR.axis == eje, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, SensorInstalado.id == ReporteDanoAR.id_sensor_instalado, ReporteDanoAR.id == ModeloAR.id_reporte_dano_ar, ModeloAR.id == CoeficienteAR.id_modelo_ar)
    df_coef = pd.read_sql(coeficientes.statement, db.session.bind)
    # print(df_coef.head())
    return df_coef

def deleteFirstReporteDano():
    try:
        subquery = db.session.query(func.min(ReporteDanoAR.hora)).subquery()
        query = db.session.query(ReporteDanoAR).filter(ReporteDanoAR.hora == subquery).delete()
        print("Numero de filas eliminadas = ", query)
    except:
        db.session.rollback()
    return

def getDamage(puente_id, nombre_sensor):
    flag_damage = False
    for eje in range(3):
        df = getCoef(puente_id, nombre_sensor, eje)
        gb = df.groupby('reporte_dano_id')
        dfs = [gb.get_group(x) for x in gb.groups]
        coef_sensor = []
        for i in range(len(dfs)):
            column = dfs[i]["numero_modelo"]
            max_value = column.max()
            for j in range(max_value + 1):
                df2 = dfs[i][dfs[i]['numero_modelo'] == j].sort_values(by=['numero'])
                coef_sensor.append(np.array(df2['valor']))
        coefdf = pd.DataFrame(coef_sensor)
        mh = mahalanobis(x=coefdf, data=coefdf)
        if (analizeDamage(mh, 16, 3)):
            flag_damage = True
    return flag_damage

def analizeDamage(mahal, umbral_dist, umbral_num):
    count = 0
    for dist in mahal:
        if dist > umbral_dist:
            count += 1
    if count > umbral_num:
        return True
    else:
        return False

def addAnomallyAll(id_puente):
    try:
        sensores_de_puente = db.session.query(SensorInstalado.id.label("si"), DescripcionSensor.descripcion.label("nombre_sensor")).filter(SensorInstalado.id_estructura == id_puente, DescripcionSensor.id_sensor_instalado == SensorInstalado.id).order_by(SensorInstalado.id.desc())
        for sensor in sensores_de_puente:
            anomalia = AnomaliaPorHora(id_sensor_instalado = sensor.si, hora_calculo = datetime.now(), anomalia = getDamage(id_puente, sensor.nombre_sensor))
            db.session.add(anomalia)
            db.session.commit()
    except:
        db.session.rollback()

def addAnomally(id_puente, name):
    try:
        sensores_de_puente = db.session.query(SensorInstalado.id.label("si"), DescripcionSensor.descripcion.label("nombre_sensor")).filter(SensorInstalado.id_estructura == id_puente, DescripcionSensor.id_sensor_instalado == SensorInstalado.id, DescripcionSensor.descripcion == name).order_by(SensorInstalado.id.desc())
        for sensor in sensores_de_puente:
            anomalia = AnomaliaPorHora(id_sensor_instalado = sensor.si, hora_calculo = datetime.now(), anomalia = getDamage(id_puente, sensor.nombre_sensor))
            db.session.add(anomalia)
            db.session.commit()
    except:
        db.session.rollback()

def resetAllAnomally(id_puente):
    try:
        num_rows_deleted = db.session.query(AnomaliaPorHora).delete()
        db.session.commit()
        print("Filas Eliminadas = " + str(num_rows_deleted))
        sensores_de_puente = db.session.query(SensorInstalado.id.label("si")).filter(SensorInstalado.id_estructura == id_puente).order_by(SensorInstalado.id.desc())
        for sensor in sensores_de_puente:
            anomalia = AnomaliaPorHora(id_sensor_instalado = sensor.si, hora_calculo = datetime.now(), anomalia = False)
            db.session.add(anomalia)
            db.session.commit()
    except:
        db.session.rollback()
