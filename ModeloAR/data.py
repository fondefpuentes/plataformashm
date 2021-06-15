import random
import pandas as pd
import numpy as np
import psycopg2
import os
import time
from datetime import datetime as dt
from datetime import timedelta as td



esquema = ['public.','inventario_puentes.','llacolen.']

def randomARCoef(num):
    coefs = []
    for x in range(num):
        coefs.append(random.randint(1,20))
    return coefs

def randomData(segs):
    serie = []
    for x in range(segs*100):
        serie.append(random.randint(-20,20))
    return serie

def getDataDay(hora):
    # Obtener datos de un sensor de un puente
    directorio = "ModeloAR/Datos/"
    return pd.read_csv(directorio + "dia1_" + str(hora) + ".csv")

def getParquetDay(sensor, date, hora):
    path = '/Users/angeloenrique/Dev/puentes/plataformashm/ModeloAR/Datos/'
    df = pd.read_parquet(path + sensor + '-' + date + '_dataset.parquet')
    df = df.reset_index()
    return (df[df['timestamp'].dt.hour == hora]).reset_index(drop=True)

def traductor_nombre(sensor):
    try:
        conexion = psycopg2.connect(user="postgres",
                                      password="puentes123",
                                      host="54.207.253.104",
                                      port="5432",
                                      database="thingsboard")
        print("Base de datos conectada")
    except (Exception, psycopg2.DatabaseError) as err:
        print("No se pudo conectar a la base de datos")
        print(err)   
    print('query traductor_nombre')
    return pd.read_sql_query("SELECT name FROM public.device WHERE id = '"+str(sensor)+"'",conexion)['name'][0]


