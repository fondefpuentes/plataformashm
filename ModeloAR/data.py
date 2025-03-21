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

def getParquetDay(sensor, day, hora):
    path = '/home/ubuntu/serverflask/DatosRecientes/DB_DATAFRAMES'
    date = str(day.day).zfill(2) + '_' + str(day.month).zfill(2) + '_' + str(day.year)
    try:
        df = pd.read_parquet(path + sensor + '-' + date + '_dataset.parquet')
        df = df.reset_index()
        return (df[df['timestamp'].dt.hour == hora]).reset_index(drop=True)
    except:
        return pd.DataFrame()

def getParquetHourly(sensor, day, hora):
    path = '/home/ubuntu/serverflask/plataformashm/ModeloAR/Datos/'
    date = str(day.day).zfill(2) + '_' + str(day.month).zfill(2) + '_' + str(day.year) + '-' + str(hora).zfill(2) + '_00_00'
    parquet_path = path + sensor + '-' + date + '-hour_data.parquet'
    # print(parquet_path)
    try:
        df = pd.read_parquet(parquet_path)
        df = df.replace(-9999, np.nan)
        df = df.dropna()
        df = df.reset_index()
        return df
    except:
        return pd.DataFrame()
