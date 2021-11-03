"""
Script para convertir en lote los archivos tipo "dato-timestamp.parquet.gzip"
Debe ejecutarse dentro de la carpeta donde estén los archivos.
Requiere Python 3 o superior e instalar las librerías Pandas y Pyarrow* con pip3 install.

*Si Pyarrow da error al instalar via pip, debe hacerse
pip3 install --upgrade
Y luego instalar Cython a traves de pip3
"""
import os
import json
import psycopg2
import gzip
import pytz
import tempfile
import sqlalchemy as sql
import requests
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
# import dataframe as datos
from time import time
from datetime import datetime as dt
from datetime import date as dt_date
from datetime import timedelta as delta
#from pytz import timezone as tz

db_engine2=sql.create_engine('postgresql://postgres:puentes123@52.67.122.51:5432/thingsboard')

sampling_freq = 120
CLT = pytz.timezone('America/Santiago')
puente = "LA_MOCHITA"   #TODO Esto debe obtenerse de una query a la bd de inventario
main_dir = os.path.dirname(os.path.realpath(__file__))
work_folder = "DB_DATAFRAMES"
results_folder = "RESULTS"
hours_folder = "HOUR_DATA"
data_dir = main_dir+"/"+work_folder.replace("/", os.path.sep)
results_dir = main_dir+"/"+results_folder.replace("/", os.path.sep)
hours_dir = main_dir+"/"+hours_folder.replace("/", os.path.sep)

def read_sql_tmpfile(query):
    with tempfile.TemporaryFile() as tmpfile:
        copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
           query=query, head="HEADER"
        )
        conn = db_engine2.raw_connection()
        cur = conn.cursor()
        cur.copy_expert(copy_sql, tmpfile)
        tmpfile.seek(0)
        df = pd.read_csv(tmpfile)
        return df

def query_data(fecha_i,fecha_f,sensor,id_sensor,eje):
    query = ("SELECT t.ts AS fecha, t.dbl_v FROM public.ts_kv as t "
            "JOIN public.device as d ON d.id = t.entity_id "
            "JOIN public.ts_kv_dictionary as dic ON t.key = dic.key_id "
            "WHERE (dic.key = '"+str(eje)+"') and (d.id = '"+str(id_sensor)+"') and (t.ts BETWEEN "+str(int(fecha_i.timestamp()*1000))+" and "+str(int(fecha_f.timestamp()*1000))+") "
            "GROUP BY fecha, t.dbl_v "
            "ORDER BY fecha ASC ")
    print("\nConsulta de datos para sensor:  "+sensor+" y eje: "+eje)
    # "Se realizará QUERY entre fechas:  "+query_date_start.strftime("%d/%m/%Y %H:%M:%S")+" -- "+query_date_end.strftime("%d/%m/%Y %H:%M:%S")
    print("DATAFRAME %s: " %eje)
    fecha_inicio = dt(fecha_i.year, fecha_i.month, fecha_i.day, fecha_i.hour, fecha_i.minute, fecha_i.second, fecha_i.microsecond)
    #fecha_inicio = fecha_inicio.astimezone(CLT)
    fecha_fin = dt(fecha_f.year, fecha_f.month, fecha_f.day, fecha_f.hour, fecha_f.minute, fecha_f.second, fecha_i.microsecond)
    #fecha_fin = fecha_fin.astimezone(CLT)

    start_time = time()
    # df = pd.read_sql_query(query,conexion) #QUERY A BASE DE DATOS
    df = read_sql_tmpfile(query)
    # print(df)

    if df.empty == False:
        df = df.rename(columns={"fecha":'timestamp'})
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        #df["timestamp"] = df["timestamp"].dt.tz_localize('UTC')
        #df["timestamp"] = df["timestamp"].dt.tz_convert('America/Santiago')
        df = df.set_index("timestamp")
        #print(df)

        # print("N de valores nulos: ", curr_df_x['dbl_v'].isna().sum())
        exp_len = pd.Timedelta(fecha_fin - fecha_inicio,'ms').total_seconds()*sampling_freq
        print("Numero de datos esperados en el DF: ", int(exp_len))
        if len(df.index) < int(exp_len):
            print("Numero de datos presentes es inferior a los datos esperados. Completando fechas faltantes.")
            head = df.head(1).index.to_pydatetime()[0]
            tail = df.tail(1).index.to_pydatetime()[0]

            diff1 = pd.Timedelta(head - fecha_inicio,'ms')
            diff2 = pd.Timedelta(fecha_fin - tail,'ms')
            if diff1.total_seconds() > 0.01:    # Si hay datos faltantes al inicio de la query
                print("primera fila diferente, diferencia en segundos: ",diff1.total_seconds())
                print("head date ", head)
                print("expected date ", fecha_inicio)
                date_vals = list(df.index.values)
                data = df["dbl_v"].values

                r1 = pd.Timedelta(head - fecha_inicio,'ms').total_seconds()*sampling_freq+1
                #r = pd.date_range(start=fecha_inicio, end=head,periods=r1,tz='America/Santiago',closed='left')
                r = pd.date_range(start=fecha_inicio, end=head,periods=r1,closed='left')
                df_a = pd.DataFrame({'timestamp':r}).set_index("timestamp")
                df = pd.concat([df_a,df])
                df = df.replace(np.nan, -9999.0)

            if diff2.total_seconds() > 0.01:    #Si hay datos faltantes al final de la query
                print("ultima fila diferente, diferencia en segundos: ", diff2.total_seconds())
                print("tail date ", tail)
                print("expected date ", fecha_fin)
                date_vals = list(df.index.values)
                data = df["dbl_v"].values

                r2 = pd.Timedelta(fecha_fin - tail,'ms').total_seconds()*sampling_freq+1
                #r = pd.date_range(start=tail, end=fecha_fin,periods=r2,tz='America/Santiago',closed='left')
                r = pd.date_range(start=tail, end=fecha_fin,periods=r2,closed='left')
                df_b = pd.DataFrame({'timestamp':r}).set_index("timestamp")
                df = pd.concat([df,df_b])
                df = df.replace(np.nan, -9999.0)

            if len(df.index) > int(exp_len):    #Si se reciben más datos de los esperados
                rows_to_delete = len(df.index)-int(exp_len)
                print("Filas extras detectadas, eliminando %d filas del final de DF" %rows_to_delete)
                # Delete the last n rows in the DataFrame
                df = df.drop(df.index[-rows_to_delete])
        elif len(df.index) > int(exp_len):      #Si se reciben más datos de los esperados
            rows_to_delete = len(df.index)-int(exp_len)
            print("Filas extras detectadas, eliminando %d filas del final de DF" %rows_to_delete)
            # Delete the last n rows in the DataFrame
            df = df.drop(df.index[-rows_to_delete])
        else:
            print("Numero correcto de datos en Query realizada.")
        elapsed_time = time() - start_time
        # print(df)
        print("Tiempo Transcurrido en crear DF desde Query: %0.1f segundos." % elapsed_time)
    else:
        print("Dataframe Vacío, generando archivo vacío.")  #Si la query no entrega datos, se genera dataframe vacío.
        column_names = ["timestamp", "dbl_v"]
        df = pd.DataFrame(columns = column_names)

        r3 = pd.Timedelta(fecha_fin - fecha_inicio,'ms').total_seconds()*sampling_freq+1
        #r = pd.date_range(start=fecha_inicio, end=fecha_fin,periods=r3,tz='America/Santiago',closed='left')
        r = pd.date_range(start=fecha_inicio, end=fecha_fin,periods=r3,closed='left')
        df_b = pd.DataFrame({'timestamp':r})
        df = pd.concat([df,df_b])
        df = df.set_index("timestamp")
        df = df.replace(np.nan, -9999.0)
        # print(df)

    return df

def get_sensor_names():
    query = ("SELECT DISTINCT name as nombre_sensor, id FROM public.device WHERE (type = 'Acelerómetro') and (name like '%AC%')")
    df = read_sql_tmpfile(query)
    return(df)

def hourly_batch_job(data_dir, sensors):
    hoy = dt.now(CLT)
    print("\nBATCH JOB DE HORA EJECUTADO EN : ", hoy)
    tiempo_final = dt(hoy.year, hoy.month, hoy.day, hoy.hour, 00, 00)
    tiempo_inicial = tiempo_final - delta(hours = 1)

    print("hora inicial: ",tiempo_inicial)
    print("hora final: ",tiempo_final)

    sensors_ids = get_sensor_names()

    #LOOP SENSORES
    for sensor_completo in sensors:  #Loop externo itera sobre cada sensor, para crear un archivo por sensor
        # filepath = data_dir+sensor+"_dataset.parquet"
        init = True #Crear archivo nuevo por cada sensor en la misma hora
        pqwriter = None
        sensor = sensor_completo.nombre_sensor
        print("\nITERACIÓN DE SENSOR: ",sensor)
        try:
            uuid = sensors_ids.loc[sensors_ids["nombre_sensor"]==sensor]["id"].values[0] #cruza de nombre sensor actual con tabla de uuid's
        except:
            continue
        print("UUID de sensor: ",uuid)

        filepath = data_dir+"/"+sensor+"-"+tiempo_inicial.strftime("%d_%m_%Y-%H_%M_%S")+"-hour_data.parquet".replace("/", os.path.sep)

        print("Se realizará QUERY entre fechas:  "+tiempo_inicial.strftime("%d/%m/%Y %H:%M:%S")+" -- "+tiempo_final.strftime("%d/%m/%Y %H:%M:%S"))
        start_time = time()
        curr_df_x = query_data(tiempo_inicial,tiempo_final,sensor,uuid,"x")
        curr_df_y = query_data(tiempo_inicial,tiempo_final,sensor,uuid,"y")
        curr_df_z = query_data(tiempo_inicial,tiempo_final,sensor,uuid,"z")

        ts_vals = curr_df_x.index
        df = pd.DataFrame({'timestamp':ts_vals,'x':curr_df_x['dbl_v'],'y':curr_df_y['dbl_v'],'z':curr_df_z['dbl_v']})
        df["timestamp"] = df["timestamp"].dt.tz_localize('utc')
        df["timestamp"] = df["timestamp"].dt.tz_convert('America/Santiago')
        df = df.set_index("timestamp")

        elapsed_time = time() - start_time
        print("Tiempo Transcurrido en construir archivo de hora "+tiempo_inicial.strftime("%H:%M:%S-%d/%m")+": %0.1f segundos." % elapsed_time)

        # print(df)
        # print("datetime : ", df.head(1).index)

        table = pa.Table.from_pandas(df)
        # print(table)
        if init:
            init = False
            # print(table.schema)
            pqwriter = pq.ParquetWriter(filepath,table.schema,use_deprecated_int96_timestamps=True)
            # total_rows = len(df.index)
        pqwriter.write_table(table)
        # total_rows += len(df.index)
            # print("archivo "+filename+" adjuntado a archivo final\n")
        if pqwriter:
            pqwriter.close()

#if __name__ == '__main__':

#    #if hours_folder not in os.listdir(main_dir):
#    #    os.mkdir(hours_folder)

   # conexion = psycopg2.connect(user="postgres", password="puentes123",
   #                             host="52.67.122.51", port="5432",
   #                             database="thingsboard")
#    esquema = ['public.','inventario_puentes.','llacolen.']
#    hourly_fname_pattern = '*_hour-data.parquet'

#    ##PROCESOS INDIVIDUALES
#    hourly_batch_job(hours_dir, sensors)
