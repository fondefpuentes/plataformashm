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

#Funcion para crear el dataframe a utilizar en el grafico OHLC, ademas el valor de la columna avg se utiliza para para el histograma
#La funcion requiere de una fecha inicial, para calcular a partir de esta los rangos de fechas
#La frecuencia, la cual corresponde al intervalo para generar el rango de fechas (12seg,288seg,2016seg y 4032seg)
#Y por ultimo requiere del nombre del sensor
def datos_ace(fecha_inicio,freq,sensor,eje):
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
    periodo = 300 #Cantidad de fechas a generar
    sensor_ = '"'+str(sensor)+'"'
    fecha_final = fecha_inicio + td(hours=1)

    query = ("SELECT time_bucket('"+str(freq)+"', to_timestamp(t.ts/1000) AT TIME ZONE 'UTC+3') AS fecha,first(t.dbl_v,t.ts) as open,last (t.dbl_v,t.ts) as close ,avg(t.dbl_v) as "+str(sensor_)+",min(t.dbl_v) as min, max(t.dbl_v) as max "
    "FROM public.ts_kv as t "
    "JOIN public.device as d ON d.id = t.entity_id "
    "JOIN public.ts_kv_dictionary as dic ON t.key = dic.key_id "
    "WHERE (t.dbl_v is NOT NULL) and (dic.key = '"+str(eje)+"') and (d.id = '"+str(sensor)+"') and (t.ts BETWEEN "+str(fecha_inicio.timestamp() * 1000)+" and "+str(fecha_final.timestamp() * 1000)+") "
    "GROUP BY fecha "
    "ORDER BY fecha ASC LIMIT "+str(periodo)+";")

    print('query datos_ace')
    new_df = pd.read_sql_query(query,conexion)
    return new_df
