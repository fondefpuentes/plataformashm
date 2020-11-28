import requests, json

#ip_instance = "http://52.67.122.51:8080"
#ip_instance = Estructura.query.get(id_puente).ip_instancia

##SOLO APLICA SI TIENES COMO PARAMETRO EN ELGUNA PARTE LA ID DEL PUENTE

def get_sensor_axis(ip_instance):

    data_usr = {"username":"tenant@thingsboard.org","password":"tenant"}
    data_usr = json.dumps(data_usr)
    #obtencion de API_KEY
    api_key_url = requests.post(ip_instance + '/api/auth/login',data=data_usr,headers={'Content-Type': 'application/json','Accept': 'application/json'})
    json_response = api_key_url.json()

    #Generación de API_KEY para autentificación en Swagger
    x_auth = 'Bearer ' + json_response['token']

    #Petición a Swagger de dispositivos TENANT
    response = requests.get(
        ip_instance + '/api/tenant/deviceInfos?pageSize=40&page=0',
        headers={'Accept' : 'application/json','X-Authorization': x_auth})
    json_devices = response.json()


    sensor_list=[]


    axis_list=[]

    for i in json_devices['data']:
        if i['type'] == 'daq':
            continue
        info = {}
        dev_request = requests.get(ip_instance + '/api/plugins/telemetry/DEVICE/' + str(i['id']['id'])+'/keys/timeseries',headers={'Accept' : 'application/json','X-Authorization': x_auth},)
        dev_response = dev_request.json()
        info['uuid'] = i['id']['id']
        info['name'] = i['name']
        
        sensor_list.append(info)

        for sensor in dev_response:
            if sensor not in axis_list:
                axis_list.append(sensor)
    axis_list.sort()
    
    return sorted(sensor_list, key = lambda x: x['name']), axis_list