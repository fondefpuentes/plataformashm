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
import time
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import gzip
from datetime import datetime as dt

target_cols = ["timestamp","AC05"]
sensors = ["AC05","AC06","AC07","AC08","AC09","AC10","AC11","AC12","AC13","AC14","AC15","AC16","AC17","AC18"]

def getFileDataframe(data_dir,filename,sensor):
    # df_out = pd.read_parquet(os.path.join(data_dir,filename), columns=target_cols)
    df_out = pd.read_parquet(os.path.join(data_dir,filename), columns=["timestamp",sensor])
    df_out['timestamp'] = pd.to_datetime(df_out['timestamp'])
    # print("Timestamp y datos de "+sensor+" extraídos a "+filename+" leído.")
    return df_out

def iterFilesToDF(data_dir):
    #LEER DATAFRAMES EN ARCHIVOS Y ENCADENARLOS EN UN SOLO DATAFRAME
    column_names = ["timestamp", "x", "y", "z"]
    df = pd.DataFrame(columns = column_names)
    for filename in os.listdir(data_dir):       # Iterar sobre archivos en el directorio
        path = os.path.join(data_dir, filename)     # generar direccion completa del archivo a leer
        if os.path.isfile(path) and path.endswith('.gzip'): # Revisar que el objeto a iterar sea un archivo y que sea un archivo con extensión .gzip
            x_vals = []
            y_vals = []
            z_vals = []
            curr_df = getFileDataframe(data_dir,filename)
            ts_vals = curr_df["timestamp"].values.tolist()
            data = curr_df["AC05"]

            for triplet in data:
                x_vals.append(triplet["x"])
                y_vals.append(triplet["y"])
                z_vals.append(triplet["z"])

            proc_df = pd.DataFrame({'timestamp':ts_vals,'x':x_vals,'y':y_vals,'z':z_vals})
            proc_df['timestamp'] = pd.to_datetime(proc_df['timestamp'], unit='ms')
            proc_df['timestamp'] = proc_df['timestamp'].dt.tz_localize('UTC')
            proc_df['timestamp'] = proc_df['timestamp'].dt.tz_convert('America/Santiago')
            df = df.append(proc_df, ignore_index=True)

    df = df.set_index("timestamp")
    return df

def makeDatasetFile(data_dir, filepath, sensor):
    init = True
    pqwriter = None
    file_count = 0
    rows_per_file = 0
    print("Extrayendo datos y Timestamp del sensor "+sensor+" a el archivo "+filepath)
    for filename in os.listdir(data_dir):
        path = os.path.join(data_dir, filename)     # generar direccion completa del archivo a leer
        if os.path.isfile(path) and path.endswith('.gzip'): # Revisar que el objeto a iterar sea un archivo y que sea un archivo con extensión .gzip
            x_vals = []
            y_vals = []
            z_vals = []
            file_count += 1
            curr_df = getFileDataframe(data_dir,filename,sensor)
            ts_vals = curr_df['timestamp'].values.tolist()
            data = curr_df[sensor]

            for triplet in data:
                x_vals.append(triplet["x"])
                y_vals.append(triplet["y"])
                z_vals.append(triplet["z"])

            proc_df = pd.DataFrame({'timestamp':ts_vals,'x':x_vals,'y':y_vals,'z':z_vals})
            proc_df['timestamp'] = pd.to_datetime(proc_df['timestamp'], unit='ms')
            proc_df['timestamp'] = proc_df['timestamp'].dt.tz_localize('UTC')
            proc_df['timestamp'] = proc_df['timestamp'].dt.tz_convert('America/Santiago')
            proc_df = proc_df.set_index("timestamp")
            table = pa.Table.from_pandas(proc_df)
            # print(table)
            if init:
                init = False
                # print(table.schema)
                pqwriter = pq.ParquetWriter(filepath,table.schema)
                rows_per_file = len(proc_df.index)
            pqwriter.write_table(table)
            # print("archivo "+filename+" adjuntado a archivo final\n")

    if pqwriter:
        pqwriter.close()

    return file_count, rows_per_file

def processDatasetFile(batch_size, filepath, sensor):
    init = True
    results_filepath = os.path.dirname(filepath)+os.path.sep+sensor+"results.parquet"
    print(results_filepath)
    pqwriter = None
    _file = pa.parquet.ParquetFile(filepath)
    batches = _file.iter_batches(batch_size) #batches es generador, iterando sobre el archivo en lotes de filas

    batch_count = 0
    for batch in batches:
        batch_count += 1
        batch_df = batch.to_pandas()
        ohlc_x = batch_df['x'].resample('288S').ohlc()
        ohlc_x = ohlc_x[:-1]
        ohlc_y = batch_df['y'].resample('288S').ohlc()
        ohlc_y = ohlc_y[:-1]
        ohlc_z = batch_df['z'].resample('288S').ohlc()
        ohlc_z = ohlc_z[:-1]
        # print(ohlc_x,ohlc_y,ohlc_z)
        # full_df = pd.DataFrame({"timestamp":ohlc_x.index,"o_x":ohlc_x["open"],"h_x":ohlc_x["high"],"l_x":ohlc_x["low"],"c_x":ohlc_x["close"],
        #                                                  "o_y":ohlc_y["open"],"h_y":ohlc_y["high"],"l_y":ohlc_y["low"],"c_y":ohlc_y["close"],
        #                                                  "o_z":ohlc_z["open"],"h_z":ohlc_z["high"],"l_z":ohlc_z["low"],"c_z":ohlc_z["close"]})
        # full_df = full_df.set_index("timestamp")
        avg_x = batch_df['x'].mean()
        avg_y = batch_df['y'].mean()
        avg_z = batch_df['z'].mean()
        kur_x = batch_df['x'].kurtosis()
        kur_y = batch_df['y'].kurtosis()
        kur_z = batch_df['z'].kurtosis()

        full_df = pd.DataFrame({"timestamp":ohlc_x.index,"o_x":ohlc_x["open"],"h_x":ohlc_x["high"],"l_x":ohlc_x["low"],"c_x":ohlc_x["close"],"avg_x":avg_x,"k_x":kur_x,
                                                         "o_y":ohlc_y["open"],"h_y":ohlc_y["high"],"l_y":ohlc_y["low"],"c_y":ohlc_y["close"],"avg_y":avg_y,"k_y":kur_y,
                                                         "o_z":ohlc_z["open"],"h_z":ohlc_z["high"],"l_z":ohlc_z["low"],"c_z":ohlc_z["close"],"avg_z":avg_z,"k_z":kur_z})
        full_df = full_df.set_index("timestamp")
        # print(full_df)
        table = pa.Table.from_pandas(full_df)
        if init:
            init = False
            # print(table.schema)
            pqwriter = pq.ParquetWriter(results_filepath,table.schema)
        pqwriter.write_table(table)
    if pqwriter:
        pqwriter.close()

    results = pd.read_parquet(results_filepath)
    results = results[:-1]

    return results


if __name__ == '__main__':
    freq = '288S'
    data_dir = "C:/Development/data_backups/20_02_2020/".replace("/", os.path.sep)
    # dataset_filepath = data_dir+"dataset.parquet"

    # count = makeDatasetFile(data_dir, dataset_filepath)
    # total_row_count = count[0]*count[1] #x_archivos * y_columnas_por_archivo
    # print("row count = ",total_row_count)
    # rows_per_batch = total_row_count/300
    # #rows_per_batch = 34560
    # results = processDatasetFile(batch_size=rows_per_batch, filepath = dataset_filepath)
    # print(results)

    for curr_sensor in sensors:
        dataset_filepath = data_dir+curr_sensor+"dataset.parquet"
        print(dataset_filepath)
        count = makeDatasetFile(data_dir, dataset_filepath, curr_sensor)
        total_row_count = count[0]*count[1] #x_archivos * y_columnas_por_archivo
        rows_per_batch = total_row_count/300
        results = processDatasetFile(batch_size=rows_per_batch, filepath = dataset_filepath, sensor = curr_sensor)
        print(results)
        time.sleep(1)


    ## LEER ARCHIVOS Y ANEXARLOS AL DATAFRAME PRINCIPAL
    # df = iterFilesToDF(data_dir)
    ## CALCULAR OHLC PARA CADA VARIABLE DESDE EL DATAFRAME PRINCIPAL
    # ohlc_x = df['x'].resample(freq).ohlc()
    # ohlc_x = ohlc_x[:-2]
    # ohlc_y = df['y'].resample(freq).ohlc()
    # ohlc_y = ohlc_y[:-2]
    # ohlc_z = df['z'].resample(freq).ohlc()
    # ohlc_z = ohlc_z[:-2]

    # print(ohlc_x)
    # print(ohlc_y)
    # print(ohlc_z)
