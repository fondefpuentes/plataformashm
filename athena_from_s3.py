import boto3
import pandas
import csv
import time
import json
from datetime import datetime
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
    if values['destino_consulta'] == 'alm_prog':
        query = query + "FROM " + "test_alldata "
    elif values['destino_consulta'] == 'event_inesp':
        query = query + "FROM " + "test_alldata " ## cambiar a tabla eventos inesperados

    ########## WHERE ##########

    if values['rango_consulta'] == 'todo':
        query = query + "WHERE ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp))*1000 AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp))*1000 AS BIGINT)"
    elif values['rango_consulta'] == 'horas_por_dia':
        query = query + "WHERE ts >= CAST(to_unixtime(CAST('" + values['fecha_inicial'] + " " + values['hora_inicial'] + "' AS timestamp)) AS BIGINT) AND ts <= CAST(to_unixtime(CAST('" + values['fecha_final'] + " " + values['hora_final'] +"' AS timestamp)) AS BIGINT) AND date_format(from_unixtime(ts/1000) , '%H:%i:%s')  >= '" + values['hora_inicial'] +"'AND date_format(from_unixtime(ts/1000), '%H:%i:%s')  <= '" + values['hora_final'] +"'"
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


    # time.sleep(1)
    ## Condition for checking the details of response

    status = 'RUNNING'
    iterations = 120

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

            ## Function to get output results
            #response_query_result = client.get_query_results(
            QueryExecutionId = response_query_execution_id['QueryExecutionId']
            #)

            s3 = boto3.resource('s3')

            queryLoc = params['bucket'] + "/" + params['path']  + "/" + QueryExecutionId + ".csv"

            ## crear un objeto con metadata de la consulta.



            now = datetime.now()

            now_time = now.strftime("%Y-%m-%d_%H-%M-%S")

            values["fecha_consulta"] = now.strftime("%Y-%m-%d %H:%M:%S")
            values["file_name"] = now_time + ".csv"

            object_metadata = s3.Object( params['bucket'] , params['path'] +'/metadata/' + params['user_id'] + "/" + now_time + '.json')
            object_metadata.put( Body=(bytes(json.dumps(values).encode('UTF-8'))), ContentType='application/json' )


            ##

            s3.Object(params['bucket'], params['path'] + "/" + params['user_id'] + "/" + now_time + ".csv").copy_from(CopySource = queryLoc)

            s3 = boto3.client('s3')

            #deletes Athena generated csv and it's metadata file
            response = s3.delete_object(
                Bucket=params['bucket'],
                Key=params['path']  + "/" + QueryExecutionId+".csv"
            )
            response = s3.delete_object(
                Bucket=params['bucket'],
                Key=params['path']  + "/" + QueryExecutionId+".csv.metadata"
            )

            return True
        else:
            time.sleep(1)
        
    return False