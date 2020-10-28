import boto3
import pandas
import csv
import time
import json
import pytz
from datetime import datetime


def get_consultas(params):

    session = boto3.Session()

    s3 = boto3.client('s3')

    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=params['bucket'], Prefix=params['path'] +'/metadata/' + params['user_id'])

    s3 = boto3.resource('s3')

    lista_consultas = []

    for page in pages:
        if (page["KeyCount"] == 0):
            return lista_consultas
        for obj in page['Contents']:
            s3_object = s3.Object( params['bucket'] , obj['Key']).get()['Body'].read().decode('UTF-8')
            json_content = json.loads(s3_object)
            ####Conversion UTC a tiempo local####
            fmt_Day = '%Y-%m-%d'
            fmt_Hours = '%H:%M'
            local_timezone = pytz.timezone ("America/Santiago")
            naive = datetime.strptime(json_content['fecha_inicial'] + " " + json_content['hora_inicial'], "%Y-%m-%d %H:%M")
            utc_dt_i = pytz.utc.localize(naive, is_dst=None)
            naive = datetime.strptime(json_content['fecha_final'] + " " + json_content['hora_final'], "%Y-%m-%d %H:%M")
            utc_dt_f = pytz.utc.localize(naive, is_dst=None)

            local_dt_i = utc_dt_i.astimezone(local_timezone)
            local_dt_f = utc_dt_f.astimezone(local_timezone)
            json_content['fecha_inicial'] = local_dt_i.strftime(fmt_Day)
            json_content['hora_inicial'] = local_dt_i.strftime(fmt_Hours)
            json_content['fecha_final'] = local_dt_f.strftime(fmt_Day)
            json_content['hora_final'] = local_dt_f.strftime(fmt_Hours)
            #####################################
            lista_consultas.append(json_content)

    return lista_consultas


def detalle_consultas(params,filename):

    s3 = boto3.resource('s3')


    object_s3= s3.Object( params['bucket'] , params['path'] +'/' + params['user_id'] + '/' + filename)

    object_detalle = object_s3.get()['Body'].read().decode('utf-8')

    filename_metadata = filename.split(".")

    object_metadata = s3.Object( params['bucket'] , params['path'] +'/metadata/' + params['user_id'] + '/' + filename_metadata[0] + '.json')

    metadata = object_metadata.get()['Body'].read().decode('UTF-8')

    metadata_content = json.loads(metadata)

    metadata_content["destino_consulta"] =  metadata_content["destino_consulta"].replace("_"," ")
    metadata_content["rango_consulta"] =  metadata_content["rango_consulta"].replace("_"," ")

    lines = object_detalle.splitlines(True)
    detalle = csv.DictReader(lines)
    header = detalle.fieldnames

    return header, detalle, metadata_content

def detalle_descarga(params,filename):

    s3 = boto3.resource('s3')

    filename_metadata = filename.split(".")

    object_metadata = s3.Object( params['bucket'] , params['path'] +'/metadata/' + params['user_id'] + '/' + filename_metadata[0] + '.json')

    metadata = object_metadata.get()['Body'].read().decode('UTF-8')

    metadata_content = json.loads(metadata)

    metadata_content["destino_consulta"] =  metadata_content["destino_consulta"].replace("_"," ")
    metadata_content["rango_consulta"] =  metadata_content["rango_consulta"].replace("_"," ")


    return metadata_content



def build_sql_query(values):

    query = " "

    query = "SELECT name as sensor, axis as eje, "
    first = True
    ########## SELECT ##########
    for i in values['consultas_sensor']:

        if first:
            first = False
            query =  query + i + "(value) as " + i + " "
        else:
            query = query + ", " +  i + "(value) as " + i + " " 
    ########## FROM ###############
    if values['destino_consulta'] == 'almacenamiento_programado':
        query = query + "FROM " + "test "
    elif values['destino_consulta'] == 'evento_inesperado':
        query = query + "FROM " + "test " ## cambiar a tabla eventos inesperados

    ########## WHERE ##########

    if values['rango_consulta'] == 'todo_entre_las_fechas':
        query = query + "WHERE dt >= '" + values['fecha_inicial'] + "' AND dt <= '" + values['fecha_final'] +"' AND ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp))*1000 AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp))*1000 AS BIGINT)"
    elif values['rango_consulta'] == 'horas_por_dia':
        query = query + "WHERE dt >= '" + values['fecha_inicial'] + "' AND dt <= '" + values['fecha_final'] +"' AND ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp)) AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp)) AS BIGINT) AND date_format(from_unixtime(ts/1000) , '%H:%i:%s')  >= '" + values['hora_inicial'] +"'AND date_format(from_unixtime(ts/1000), '%H:%i:%s')  <= '" + values['hora_final'] +"'"
    ##### sensores #####    
    query = query + " AND ("
    first = True
    for j in values['lista_sensores']:

        if first:
            first = False
            query = query + "name = '" + j + "'"
        else:
            query = query + "OR name = '" + j + "'"
    ##### ejes #####    
    query = query + ") AND ("
    first = True
    for k in values['consultas_ejes']:
        if first:
            first = False
            query = query + "axis = '" + k + "'"
        else:
            query = query + "OR axis = '" + k + "'"
    query = query + ")"

    query = query + " GROUP BY name, axis"
    query = query + " ORDER BY name, axis"

    return query


def query_athena(params,values):

    session = boto3.Session()
    time_start = time.time()
    ## Creating the Client for Athena
    client = boto3.client('athena')
    
    ## This function executes the query and returns the query execution ID
    response_query_execution_id = client.start_query_execution(
        QueryString = build_sql_query(values),
        QueryExecutionContext = {
            'Database' : params['database']
        },
        ResultConfiguration = {
            'OutputLocation': 's3://' + params['bucket'] + '/' + params['path']
        }
    )

    ## This function takes query execution id as input and returns the details of the query executed
    response_get_query_details = client.get_query_execution(
        QueryExecutionId = response_query_execution_id['QueryExecutionId']
    )



    ## Condition for checking the details of response

    status = 'RUNNING'
    iterations = 600

    while (iterations>0):
        iterations = iterations - 1
        response_get_query_details = client.get_query_execution(
        QueryExecutionId = response_query_execution_id['QueryExecutionId']
        )
        status = response_get_query_details['QueryExecution']['Status']['State']
        if (status == 'FAILED') or (status == 'CANCELLED') :
            return False
            
        elif status == 'SUCCEEDED':
            location = response_get_query_details['QueryExecution']['ResultConfiguration']['OutputLocation']


            QueryExecutionId = response_query_execution_id['QueryExecutionId']

            now = datetime.now()

            now_time = now.strftime("%Y-%m-%d_%H-%M-%S")
            
            s3 = boto3.resource('s3')
           
            queryLoc = params['bucket'] + "/" + params['path']  + "/" + QueryExecutionId + ".csv"


            s3.Object(params['bucket'], params['path'] + "/" + params['user_id'] + "/" + now_time + ".csv").copy_from(CopySource = queryLoc)


            #deletes Athena generated csv and it's metadata file
            s3 = boto3.client('s3')
            response = s3.delete_object(
                Bucket=params['bucket'],
                Key=params['path']  + "/" + QueryExecutionId+".csv"
            )
            response = s3.delete_object(
                Bucket=params['bucket'],
                Key=params['path']  + "/" + QueryExecutionId+".csv.metadata"
            )


            ## crear un objeto con metadata de la consulta.

            s3 = boto3.resource('s3')

            values["fecha_consulta"] = now.strftime("%Y-%m-%d %H:%M:%S")
            values["file_name"] = now_time + ".csv"
            time_end = time.time()
            values["execution_time"] = round(time_end - time_start)
            object_metadata = s3.Object( params['bucket'] , params['path'] +'/metadata/' + params['user_id'] + "/" + now_time + '.json')
            object_metadata.put( Body=(bytes(json.dumps(values).encode('UTF-8'))), ContentType='application/json' )

            return True
        else:
            time.sleep(1)
        
    return False

def build_download_sql_query(params,values,now_time):

    ##### SELECT #####
    query = "SELECT ts, name, axis, type, value"

    ##### FROM #####
    if values['destino_consulta'] == 'almacenamiento_programado':
        query = query + " FROM " + "test "
    elif values['destino_consulta'] == 'evento_inesperado':
        query = query + " FROM " + "test " ## cambiar a tabla eventos inesperados

    ##### WHERE #####   
    if values['rango_consulta'] == 'todo_entre_las_fechas':
        query = query + "WHERE dt >= '" + values['fecha_inicial'] + "' AND dt <= '" + values['fecha_final'] +"' AND ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp))*1000 AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp))*1000 AS BIGINT)"
    elif values['rango_consulta'] == 'horas_por_dia':
        query = query + "WHERE dt >= '" + values['fecha_inicial'] + "' AND dt <= '" + values['fecha_final'] +"' AND ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp))*1000 AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp))*1000 AS BIGINT) AND date_format(from_unixtime(ts/1000) , '%H:%i:%s')  >= '" + values['hora_inicial'] +"'AND date_format(from_unixtime(ts/1000), '%H:%i:%s')  <= '" + values['hora_final'] +"'"
    ##### sensores #####    
    query = query + " AND ("
    first = True
    for j in values['lista_sensores']:

        if first:
            first = False
            query = query + "name = '" + j + "'"
        else:
            query = query + "OR name = '" + j + "'"
    ##### ejes #####    
    query = query + ") AND ("
    first = True
    for k in values['consultas_ejes']:
        if first:
            first = False
            query = query + "axis = '" + k + "'"
        else:
            query = query + "OR axis = '" + k + "'"
    query = query + ")"

    query = query + " ORDER BY ts, name, axis ASC"

    query = "CREATE table new_parquet WITH (format='PARQUET', parquet_compression='SNAPPY', external_location = 's3://" + params['bucket'] + "/descargas/" + "test" + "/" + params['user_id'] + "/" + now_time + "', bucketed_by = ARRAY['ts'], bucket_count = 1) AS(" + query + ");"

    query_droptable = "DROP TABLE new_parquet;"

    return query, query_droptable



def download_query_athena(params,values):

    session = boto3.Session()
    time_start = time.time()
    now = datetime.now()

    now_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    query , query_droptable = build_download_sql_query(params,values,now_time)

    ## Creating the Client for Athena
    client = boto3.client('athena')
    
    ## This function executes the query and returns the query execution ID
    response_query_execution_id = client.start_query_execution(
        QueryString = query,
        QueryExecutionContext = {
            'Database' : params['database']
        },
        ResultConfiguration = {
            'OutputLocation': 's3://' + params['bucket'] + '/' + params['path_athena'] + '/' + params['user_id'] + '/' + now_time
        }
    )

    response_get_query_details = client.get_query_execution(
        QueryExecutionId = response_query_execution_id['QueryExecutionId']
    )



    ## Condition for checking the details of response
    ## Set to 18000 secs or 5 hours
    status = 'RUNNING'
    iterations = 18000

    while (iterations>0):
        iterations = iterations - 1
        response_get_query_details = client.get_query_execution(
        QueryExecutionId = response_query_execution_id['QueryExecutionId']
        )
        status = response_get_query_details['QueryExecution']['Status']['State']
        if (status == 'FAILED') or (status == 'CANCELLED') :
            return False
            
        elif status == 'SUCCEEDED':
            location = response_get_query_details['QueryExecution']['ResultConfiguration']['OutputLocation']

            QueryExecutionId = response_query_execution_id['QueryExecutionId']

            ## Copy Object and renamed
            s3 = boto3.client('s3')
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=params['bucket'], Prefix=params['path'] + '/' + params['user_id'] + '/' + now_time)
            s3 = boto3.resource('s3')
            for page in pages:
                if (page["KeyCount"] == 0):
                    break
                for obj in page['Contents']:
                    queryLoc = params['bucket'] + "/" + obj['Key']
                    s3.Object(params['bucket'], params['path'] + '/' + params['user_id'] + '/' + now_time).copy_from(CopySource = queryLoc)
                    s3 = boto3.client('s3')
                    #deletes Athena generated file
                    response = s3.delete_object(
                        Bucket=params['bucket'],
                        Key= obj['Key']
                    )


            # Drop CTAS Table
            s3 = boto3.resource('s3')
            response_query_execution_id = client.start_query_execution(
                QueryString = query_droptable,
                QueryExecutionContext = {
                    'Database' : params['database']
                },
                ResultConfiguration = {
                    'OutputLocation': 's3://' + params['bucket'] + params['path_athena'] + '/' + params['user_id'] + '/' + now_time
                }
            )
            ## Descarga sin contenido
            if (page["KeyCount"] == 0):
                return False

            ## crear un objeto con metadata de la descarga.
            s3 = boto3.resource('s3')
            values["fecha_consulta"] = now.strftime("%Y-%m-%d %H:%M:%S")
            values["file_name"] = now_time
            values["size"] = round(s3.Bucket(params['bucket'] ).Object(params['path'] + '/' + params['user_id'] + '/' + now_time).content_length / pow(1024,2),1)
            time_end = time.time()
            values["execution_time"] = round(time_end - time_start)
            object_metadata = s3.Object( params['bucket'] , params['path'] +'/metadata/' + params['user_id'] + '/' + now_time + '.json')
            object_metadata.put( Body=(bytes(json.dumps(values).encode('UTF-8'))), ContentType='application/json')
            return True
        else:
            time.sleep(1)
        
    return False


def get_attachment_url(params,filename):
    s3 = boto3.client('s3')
    return s3.generate_presigned_url('get_object', Params={'Bucket': params['bucket'], "Key": params['path'] + '/' + params['user_id'] + '/' + filename }, ExpiresIn=60)