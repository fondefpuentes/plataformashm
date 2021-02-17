from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flask_table import Table, Col
from views import views_api
from models import db, Usuario
from flask_login import LoginManager
from flask_mail import Mail, Message
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import DatosRecientes.dataframe as datos
from dash.dependencies import Input, Output,State
from datetime import datetime as dt
from time import time
import pandas as pd
import plotly.graph_objects as go
import collections
import plotly.express as px
import dash_bootstrap_components as dbc
import DatosRecientes.layout as DashLayout
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='')
app.config.from_pyfile('config.py')
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 465,
    MAIL_USE_SSL = True,
    MAIL_USERNAME = "plataforma.shm.chile@gmail.com",
    MAIL_PASSWORD = "vewtbinxfhhjsfea",
)

### SCHEDULER ###

def actualizar_anomalias():
    print(time.strftime("%A, %d. %B %Y %I:%M:%S %p"))


if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true': # Se ejecuta cuando la app no esta en modo debug o en una rama principal (para evitar doble ejecucion)
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=actualizar_anomalias, trigger="interval", seconds=60)
    scheduler.start()
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())



### INTEGRACION DATOS RECIENTES ###

plotly_app = dash.Dash(__name__, server=app, url_base_pathname="/dash/", assets_folder="./DatosRecientes/assets")
plotly_app.layout = DashLayout.datos_recientes_layout

@plotly_app.callback(Output('indicador-multi','style'),[Input('boton-aceptar', 'n_clicks')],[State('cantidad-sensores','value')])

def update_info(clicks,cantidad_sensores):
    if clicks >= 0:
        if cantidad_sensores == '1-sensor':
            return {'display':'none'}
        else:
            return {'display':'inline'}

# Esta funcion cambia segun el tipo de sensor, los sensores disponibles y ademas si en las propiedades se selecciona tener mas de 1 sensor por grafica cambia el dropdown a multiple
@plotly_app.callback([Output('elegir-sensor', 'value'),Output('elegir-sensor', 'options'),Output('elegir-sensor-multi', 'value'),Output('elegir-sensor-multi', 'options'),Output('sensor-multi', 'style'),Output('sensor-uni','style'),Output('ejes-multi', 'style'),Output('ejes','style')],
              [Input('cantidad-sensores','value'),Input('elegir-tipo-sensor','value')])

def lista_sensores(cantidad_sensores,tipo_sensor):
    if cantidad_sensores == '1-sensor':
        return str(datos.nombres_sensores(tipo_sensor).get(list(datos.nombres_sensores(tipo_sensor).keys())[0])),[{"label": key , "value": value}for key,value in datos.nombres_sensores(tipo_sensor).items()],'',[{"label":'',"value":''}],{'display':'none'},{'display':'inline'},{'textAlign': 'center','display':'none'},{'textAlign': 'center','display':'inline'}
    elif cantidad_sensores == 'varios-sensores':
        return '',[{"label":'',"value":''}],[str(datos.nombres_sensores(tipo_sensor).get(list(datos.nombres_sensores(tipo_sensor).keys())[0]))],[{"label": key , "value": value}for key,value in datos.nombres_sensores(tipo_sensor).items()],{'display':'inline'},{'display':'none'},{'textAlign': 'center','display':'inline'},{'textAlign': 'center','display':'none'}

#Esta funcion cambia las fechas del selector de fechas deacuerdo a las disponibles en cada sensor
@plotly_app.callback([Output('elegir-fecha','min_date_allowed'),Output('elegir-fecha','max_date_allowed'),Output('elegir-fecha','initial_visible_month'),Output('elegir-fecha','date')],
              [Input('elegir-tipo-sensor','value')])

def update_fecha(tipo_sensor):

    ini = datos.fecha_inicial(tipo_sensor,'x')
    fin = datos.fecha_final(tipo_sensor,'x')
    return ini,fin,ini,ini

# Esta funcion muestra el rangeslider de horas, siempre que este seleccionado la opcion de "1 hora" 
@plotly_app.callback(Output('contenedor-horas-disponibles', 'style'),
              [Input('ventana-tiempo','value')])

def update_seleccion_horas(opciones):
    if opciones == '12S':
        return {'display':'inline'}
    else:
        return {'display':'none'}

#Muestra las horas disponibles segun el sensor en el rangeslider
@plotly_app.callback([Output('horas-disponibles','value'),Output('horas-disponibles','min'),Output('horas-disponibles','max'),Output('horas-disponibles','marks')],
              [Input('elegir-sensor','value'),Input('elegir-sensor-multi','value'),Input('elegir-fecha','date'),Input('cantidad-sensores','value')])

def horas_disponibles_sensor(sensor,sensor_multi,fecha_ini,cantidad_sensores):
    if fecha_ini == None:
        fecha_ini = str(dt(2008,1,1)).split(sep=' ')[0]
    fecha_str = str(fecha_ini).split(sep='T')[0]
    fecha = dt.strptime(fecha_str, '%Y-%m-%d')
    if cantidad_sensores == '1-sensor':
        if sensor == '':
            horas,min,max = [0,1],0,1
        else:
            horas,min,max = datos.horas_del_dia(sensor,fecha)
        marks = {}

        for i in horas:
            if i == 0 or i == 6 or i == 12 or i == 18 or i == 23:
                marks[i]= {'label': datos.crear_hora(i)[:5],'style': {'color': 'black'}}
            else:
                marks[i]= {'label': ' '}        
        return min,min,max,marks
    else:
        if str(type(sensor_multi)) == "<class 'str'>":
            horas,min,max = [0,1],0,1
        else:
            horas,min,max = datos.horas_del_dia(sensor_multi[0],fecha)
        marks = {}
        for i in horas:
            if i == 0 or i == 6 or i == 12 or i == 18 or i == 23:
                marks[i]= {'label': datos.crear_hora(i)[:5],'style': {'color': 'black'}}
            else:
                marks[i]= {'label': ' '} 
        return min,min,max,marks

# Esta funcion actualiza el texto bajo el rangeslider de horas, con la hora que se selecciona en el rangeslider
@plotly_app.callback(Output('hora-disponible-seleccionada','children'),
             [Input('horas-disponibles', 'value')])

def update_hora_seleccionada(hora):
    hora_sel = 'Hora Seleccionada: '+datos.crear_hora(hora)[:5]
    return hora_sel

# Esta funcion cambia las opciones que se muestran en el radioitem cantidad de sensores a visualizar
@plotly_app.callback(Output('cantidad-sensores','options'),
             [Input('elegir-tipo-sensor','value')])

def change_cantidad_sensores(tipo_sensor):
    return [{"label": key , "value": value}for key,value in datos.cantidad_sensores_visualizar(tipo_sensor).items()]

# Esta funcion cambia las opciones que se muestran en el radioitem ventana de tiempo, dependiendo de lo que se encuentre en la base de datos
@plotly_app.callback([Output('ventana-tiempo','options'),Output('ventana-tiempo','value')],
             [Input('elegir-fecha', 'date'),Input('elegir-tipo-sensor','value')])

def change_ventana_tiempo(fecha_ini,tipo_sensor):

    if fecha_ini == None:
        fecha_ini = datos.fecha_inicial(tipo_sensor,'x')
    fecha_ini = str(fecha_ini)
    fecha_ini = dt.strptime(str(dt(int(fecha_ini[0:4]),int(fecha_ini[5:7]),int(fecha_ini[8:10]),0,0,0)),'%Y-%m-%d %H:%M:%S')
    fecha_fin = datos.fecha_final(tipo_sensor,'x')
    rango = datos.dias_entre_fechas(fecha_ini,fecha_fin)
    if rango > 13:
        return [{"label": key , "value": value}for key,value in datos.ventana_tiempo(3).items()],str(list(datos.ventana_tiempo(3).values())[0])
    elif rango > 6 and rango < 14:
        return [{"label": key , "value": value}for key,value in datos.ventana_tiempo(2).items()],str(list(datos.ventana_tiempo(3).values())[0])
    elif rango > 0 and rango < 7:
        return [{"label": key , "value": value}for key,value in datos.ventana_tiempo(1).items()],str(list(datos.ventana_tiempo(3).values())[0])
    elif rango == 0:
        return [{"label": key , "value": value}for key,value in datos.ventana_tiempo(0).items()],str(list(datos.ventana_tiempo(3).values())[0])

# Esta funcion actualiza el numero de clicks del boton agregar linea de control inferior, cuando se presiona el boton quitar linea 
@plotly_app.callback(Output('boton-linea-inf', 'n_clicks'),
              [Input('boton-quitar-linea-inf', 'n_clicks')])

def update_boton_inf(click_quitar_inf):
    if click_quitar_inf >= 0:
        return 0
    else:
        return 1

# Esta funcion actualiza el numero de clicks del boton agregar linea de control superior, cuando se presiona el boton quitar linea
@plotly_app.callback(Output('boton-linea-sup', 'n_clicks'),
              [Input('boton-quitar-linea-sup', 'n_clicks')])

def update_boton_sup(click_quitar_sup):
    if click_quitar_sup >= 0:
        return 0
    else:
        return 1

# Esta funcion actualiza el texto que aparece en el cuadro para indicar el valor de la linea de control inferior, una vez que se presiona el boton de quitar linea
@plotly_app.callback(Output('linea-control-inf','value'),
             [Input('boton-quitar-linea-inf','n_clicks')])

def update_text_input_inf(clicks_inf):
    if clicks_inf >= 0 :
        return None

# Esta funcion actualiza el texto que aparece en el cuadro para indicar el valor de la linea de control superior, una vez que se presiona el boton de quitar linea
@plotly_app.callback(Output('linea-control-sup','value'),
             [Input('boton-quitar-linea-sup','n_clicks')])

def update_text_input_sup(clicks_sup):
    if clicks_sup >= 0 :
        return None

#funcion que desabilita el dropdown de tipos de sensores cuando se agrega una linea de control o cuando se selecciona la opcion de multiples sensores
@plotly_app.callback([Output('elegir-tipo-sensor','disabled'),Output('elegir-sensor','disabled'),Output('elegir-sensor-multi','disabled')],
             [Input('cantidad-sensores','value'),Input('boton-linea-sup', 'n_clicks'),Input('boton-linea-inf', 'n_clicks')])

def disable_tipo_sensores(cantidad_sensores,click_agr_sup,click_agr_inf):
    if cantidad_sensores == '1-sensor':
        if click_agr_sup > 0 or click_agr_inf > 0:
            return True,True,True
        else:
            return False,False,False
    else:
        if click_agr_sup > 0 or click_agr_inf > 0:
            return True,True,False
        else:
            return True,False,False

#Funcion que actualiza el grafico principal y le agrega las lineas de control
@plotly_app.callback([Output('valor-promedio', 'children'),Output('valor-max', 'children'),Output('valor-min', 'children'),Output('fecha-valor-max','children'),
               Output('fecha-valor-min','children'),Output('num-valor-max','children'),Output('num-valor-min','children'),Output('alert-sup','children'),
               Output('alert-inf','children'),Output('fecha-alert-sup','children'),Output('fecha-alert-inf','children'),Output('grafico-principal','figure')],
              [Input('boton-aceptar', 'n_clicks'),Input('boton-linea-sup', 'n_clicks'),Input('boton-linea-inf', 'n_clicks')],
              [State('cantidad-sensores','value'),State('horas-disponibles', 'value'),State('elegir-tipo-sensor','value'),State('elegir-sensor','value'),State('elegir-sensor-multi','value'),State('elegir-fecha','date'),State('ventana-tiempo','value'),
               State('linea-control-sup','value'),State('linea-control-inf','value')],State('elegir-eje','value'),State('elegir-eje-multi','value'))

def update_grafico_principal(n_clicks,click_linea_sup,click_linea_inf,cantidad_sensores,hora,tipo_sensor,sensor,sensor_multi,fecha,ventana_tiempo,linea_control_sup,linea_control_inf,ejes,eje):

    if len(ejes) < 1 :
        ejes.append('x')
    if fecha != None:
        if str(str(fecha).split(sep='T')[0]) == str(str(datos.fecha_inicial(tipo_sensor,eje)).split(sep=' ')[0]):
            #fecha = dt.strptime(str(str(fecha).split(sep='T')[0]) + ' ' + str(str(datos.fecha_inicial()).split(sep=' ')[1]),'%Y-%m-%d %H:%M:%S')
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
        else:
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
    else:
        fecha = datos.fecha_inicial(tipo_sensor,eje)
    #Se inicializan variables
    df = pd.DataFrame()
    fig_principal = go.Figure()
    alert_inf, alert_sup, fecha_peak_sup, fecha_peak_inf = '---','---','---','---'
    promedio,maximo,minimo,count_max,count_min,fecha_ultimo_max,fecha_ultimo_min = '---','---','---','---','---','---','---'
    #Listas que conteneran cada trace generado por cada dataframe creado para poder visualizarlos en una grafica
    trace_principal = []
    if n_clicks >= 0:
        fecha_ini_titulo,fecha_fin_titulo = datos.fecha_titulo(fecha,ventana_tiempo)
        #Dependiendo del tipo de sensor se crean visualizaciones distintas
        if tipo_sensor == 'Acelerometro':
            if cantidad_sensores == '1-sensor':
                # La variable df contiene el dataframe que se utiliza para generar los graficos OHLC e histograma
                
                new_df = pd.DataFrame()
                list_df = []

                colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', 
                          '#f58231', '#911eb4']
                count = 0
                new_count_de = 0
                new_count_in = 1

                for e in ejes:
                    start_time = time()
                    df = datos.datos_ace(fecha,ventana_tiempo,sensor,e)

                    elapsed_time = time() - start_time
                    print("Tiempo Transcurrido crear DF: %0.1f seconds." % elapsed_time)
                    # Aqui se crea el grafico OHLC
                    start_time = time()
                    trace_principal.append(go.Ohlc(x=df['fecha'],
                        open=df['open'],
                        high=df['max'],
                        low=df['min'],
                        close=df['close'],
                        increasing_line_color= colors[new_count_in], 
                        decreasing_line_color= colors[new_count_de],
                        name=str(datos.traductor_nombre(sensor)+' eje: '+str(e)),
                        showlegend=True))
                    count = count + 1
                    new_count_in = new_count_in + 2
                    new_count_de = new_count_de + 2
                    
                    new_df = df

                    #lista de dataframe para generar los indicadores resumen
                    list_df.append(df)

                #Variables que contienen los datos a mostrar en los indicadores de promedio, minimo y maximo
                promedio,maximo,minimo,count_max,count_min,fecha_ultimo_max,fecha_ultimo_min = datos.datos_mini_container(new_df,sensor)

                df = pd.concat(list_df, axis=0,ignore_index=True)
                fig_principal = go.Figure(data=trace_principal)
                #Aqui se agregan las lineas de control
                if (click_linea_inf > 0 and linea_control_inf != None) and (click_linea_sup > 0 and linea_control_sup != None):
                    trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                    trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                    trace_linea_inf.extend(trace_linea_sup)
                    trace_principal.extend(trace_linea_inf)
                    fig_principal = go.Figure(data=trace_principal)
                
                #Linea de control inferior
                elif click_linea_inf > 0 and linea_control_inf != None:
                    trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                    trace_principal.extend(trace_linea_inf)
                    fig_principal = go.Figure(data=trace_principal)
                #Linea de control superior       
                elif click_linea_sup > 0 and linea_control_sup != None:
                    trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                    trace_principal.extend(trace_linea_sup)
                    fig_principal = go.Figure(data=trace_principal)

                fig_principal.update(layout_xaxis_rangeslider_visible=False)

                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)

                fig_principal.update_layout(title={'text':"Datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+" del "+str(datos.traductor_nombre(sensor))+" durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")"},yaxis={"title": "Aceleración (cm/s²)"})

                elapsed_time = time() - start_time
                print("Tiempo Transcurrido crear OHLC: %0.1f seconds." % elapsed_time)

                

            else:
                
                #colores para las graficas
                colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', 
                          '#f58231', '#911eb4', '#46f0f0', '#f032e6', 
                          '#bcf60c', '#fabebe', '#008080', '#e6beff', 
                          '#9a6324', '#fffac8', '#800000', '#aaffc3', 
                          '#808000', '#ffd8b1', '#000075', '#808080', 
                          '#ffffff', '#000000', '#e6194b', '#3cb44b', 
                          '#ffe119', '#4363d8', '#f58231', '#911eb4', 
                          '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', 
                          '#008080', '#e6beff', '#9a6324', '#fffac8', 
                          '#800000', '#aaffc3', '#808000', '#ffd8b1', 
                          '#000075', '#808080', '#ffffff', '#000000']
                count = 0
                new_count_de = 0
                new_count_in = 1
                new_df = pd.DataFrame()
                new_sensor = ''
                list_df = []

                #por cada sensor seleccionado se crean df 
                for sen in sensor_multi:

                    df = datos.datos_ace(fecha,ventana_tiempo,sen,eje)
                    
                    #trace para el grafico OHLC
                    trace_principal.append(
                        go.Ohlc(
                            x=df['fecha'],
                            open=df['open'],
                            high=df['max'],
                            low=df['min'],
                            close=df['close'],
                            increasing_line_color= colors[new_count_in], 
                            decreasing_line_color= colors[new_count_de],
                            showlegend=True,
                            name= datos.traductor_nombre(sen)
                            )
                        )

                    count = count + 1
                    new_count_in = new_count_in + 2
                    new_count_de = new_count_de + 2

                    new_df = df
                    new_sensor = sen
                    #lista de dataframe para generar los indicadores resumen
                    list_df.append(df)

                #Variables que contienen los datos a mostrar en los indicadores de promedio, minimo y maximo
                promedio,maximo,minimo,count_max,count_min,fecha_ultimo_max,fecha_ultimo_min = datos.datos_mini_container(new_df,new_sensor)
                
                df = pd.concat(list_df, axis=0,ignore_index=True)
                fig_principal = go.Figure(data=trace_principal)
                #Aqui se agregan las lineas de control
                if (click_linea_inf > 0 and linea_control_inf != None) and (click_linea_sup > 0 and linea_control_sup != None):
                    trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                    trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                    trace_linea_inf.extend(trace_linea_sup)
                    trace_principal.extend(trace_linea_inf)
                    fig_principal = go.Figure(data=trace_principal)

                #Linea de control inferior
                elif click_linea_inf > 0 and linea_control_inf != None:
                    trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                    trace_principal.extend(trace_linea_inf)
                    fig_principal = go.Figure(data=trace_principal)
                #Linea de control superior       
                elif click_linea_sup > 0 and linea_control_sup != None:
                    trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                    trace_principal.extend(trace_linea_sup)
                    fig_principal = go.Figure(data=trace_principal)
    
                fig_principal.update(layout_xaxis_rangeslider_visible=False)
                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)
            
                fig_principal.update_layout(title={'text':"Datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+", durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")"},yaxis={"title": "Aceleración (cm/s²)"})

        elif tipo_sensor == 'weather-station':
            # La variable df y dff contiene el dataframe que se utiliza para generar el graficos OHLC
            df = datos.datos_ace(fecha,ventana_tiempo,'temperatura')

            # Aqui se crea el grafico OHLC para la temperatura
            trace_principal.append(
                go.Ohlc(
                    x=df['fecha'],
                    open=df['open'],
                    high=df['max'],
                    low=df['min'],
                    close=df['close'],
                    increasing_line_color= 'green', 
                    decreasing_line_color= 'red',
                    showlegend=True,
                    name= 'Temperatura'
                    )
                )

            fig_principal = go.Figure(data=trace_principal)
            #Aqui se agregan las lineas de control
            if (click_linea_inf > 0 and linea_control_inf != None) and (click_linea_sup > 0 and linea_control_sup != None):
                trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                trace_linea_inf.extend(trace_linea_sup)
                trace_principal.extend(trace_linea_inf)
                fig_principal = go.Figure(data=trace_principal)

            #Linea de control inferior
            elif click_linea_inf > 0 and linea_control_inf != None:
                trace_linea_inf,alert_inf,fecha_peak_inf = datos.lineas_control('inf',df,linea_control_inf,0)
                trace_principal.extend(trace_linea_inf)
                fig_principal = go.Figure(data=trace_principal)
            #Linea de control superior       
            elif click_linea_sup > 0 and linea_control_sup != None:
                trace_linea_sup,alert_sup,fecha_peak_sup = datos.lineas_control('sup',df,0,linea_control_sup)
                trace_principal.extend(trace_linea_sup)
                fig_principal = go.Figure(data=trace_principal)

            fig_principal.update(layout_xaxis_rangeslider_visible=False)
            titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)
            #titulos para ambos graficos OHLC
            fig_principal.update_layout(title={'text':"Datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+" de la Temperatura durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")"},yaxis={"title": "Temperatura (°C)"})

            #Se obtienen los datos de los indicadores resumen, en este caso pertenecientes a los datos de temperatura
            promedio,maximo,minimo,count_max,count_min,fecha_ultimo_max,fecha_ultimo_min = datos.datos_mini_container(df,'temperatura')
            
            
        return promedio,maximo,minimo,fecha_ultimo_max,fecha_ultimo_min,count_max,count_min,alert_sup,alert_inf,fecha_peak_sup,fecha_peak_inf,fig_principal

    #else:
    #    return '---','---','---','---','---','---','---','---','---','---','---',{}

#Funcion que actualiza el grafico secundario 1
@plotly_app.callback(Output('grafico-1','figure'),
              [Input('boton-aceptar', 'n_clicks')],
              [State('cantidad-sensores','value'),State('horas-disponibles', 'value'),State('elegir-tipo-sensor','value'),State('elegir-sensor','value'),
               State('elegir-sensor-multi','value'),State('elegir-fecha','date'),State('ventana-tiempo','value'),State('elegir-eje','value'),State('elegir-eje-multi','value')])

def update_grafico_1(n_clicks,cantidad_sensores,hora,tipo_sensor,sensor,sensor_multi,fecha,ventana_tiempo,ejes,eje):
    if len(ejes) < 1 :
        ejes.append('x')

    if fecha != None:
        if str(str(fecha).split(sep='T')[0]) == str(str(datos.fecha_inicial(tipo_sensor,eje)).split(sep=' ')[0]):
            #fecha = dt.strptime(str(str(fecha).split(sep='T')[0]) + ' ' + str(str(datos.fecha_inicial()).split(sep=' ')[1]),'%Y-%m-%d %H:%M:%S')
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
        else:
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
    else:
        fecha = datos.fecha_inicial(tipo_sensor,eje)
    #Se inicializan variables
    df = pd.DataFrame()
    fig_1 = go.Figure()
    if n_clicks >= 0:
        fecha_ini_titulo,fecha_fin_titulo = datos.fecha_titulo(fecha,ventana_tiempo) 
        #Dependiendo del tipo de sensor se crean visualizaciones distintas
        if tipo_sensor == 'Acelerometro':
            if cantidad_sensores == '1-sensor':

                #Aqui se crea el grafico boxplot
                start_time = time()
                repeat = 12
                #Cuando la ventana de tiempo es de 1 hora o 1 dia se obtinen 12 box en cambio si es de 7 dias o 14 se obtienen 14 por eso cambia el valor de repeat
                if ventana_tiempo == '12S' or ventana_tiempo == '288S':
                    repeat = 12
                else:
                    repeat = 14
                # bucle que genera cada box
                for e in ejes:
                    for i in range(repeat):
                        if i == 0: 
                            vars()['df'+str(i)],vars()['ultimo'+str(i)] = datos.datos_box(fecha,ventana_tiempo,sensor,e)
                            fig_1.add_trace(go.Box(y=vars()['df'+str(i)][str(vars()['ultimo'+str(i)])], name=str(vars()['ultimo'+str(i)])+' eje: '+str(e),boxpoints='suspectedoutliers',showlegend=False))
                        else:
                            vars()['df'+str(i)],vars()['ultimo'+str(i)] = datos.datos_box(vars()['ultimo'+str(i-1)],ventana_tiempo,sensor,e)
                            fig_1.add_trace(go.Box(y=vars()['df'+str(i)][str(vars()['ultimo'+str(i)])], name=str(vars()['ultimo'+str(i)])+' eje: '+str(e),boxpoints='suspectedoutliers',showlegend=False))
        
                elapsed_time = time() - start_time
                print("Tiempo Transcurrido crear BOX: %0.1f seconds." % elapsed_time)

                # Titulos para el grafico OHLC y Boxplot
                titulo_box = datos.titulo_box(ventana_tiempo)
                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)
   
                fig_1.update_layout(title="Promedio de datos cada "+str(titulo_box)+" del "+str(datos.traductor_nombre(sensor))+" durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")",yaxis={"title": "Aceleración (cm/s²)"})
                
            else:
                #Listas que conteneran cada trace generado por cada dataframe creado para poder visualizarlos en una grafica
                trace_sec1 = []
                
                #Para el grafico boxplot
                repeat = 12
                #Cuando la ventana de tiempo es de 1 hora o 1 dia se obtinen 12 box en cambio si es de 7 dias o 14 se obtienen 14 por eso cambia el valor de repeat
                if ventana_tiempo == '12S' or ventana_tiempo == '288S':
                    repeat = 12
                else:
                    repeat = 14
                #colores para las graficas
                colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080', '#ffffff', '#000000']
                count = 0

                #por cada sensor seleccionado se crean df 
                for sen in sensor_multi:
                    # bucle que genera cada box para guardarlo en el trace
                    for i in range(repeat):
                        if i == 0: 
                            vars()['df'+str(i)],vars()['ultimo'+str(i)] = datos.datos_box(fecha,ventana_tiempo,sen,eje)
                            trace_sec1.append(
                                go.Box(
                                    y=vars()['df'+str(i)][str(vars()['ultimo'+str(i)])], 
                                    name=str(vars()['ultimo'+str(i)]),
                                    boxpoints='suspectedoutliers',
                                    showlegend=False,
                                    marker_color = colors[count]
                                )
                            )
                        else:
                            vars()['df'+str(i)],vars()['ultimo'+str(i)] = datos.datos_box(vars()['ultimo'+str(i-1)],ventana_tiempo,sen,eje)
                            trace_sec1.append(
                                go.Box(
                                    y=vars()['df'+str(i)][str(vars()['ultimo'+str(i)])], 
                                    name=str(vars()['ultimo'+str(i)]),
                                    boxpoints='suspectedoutliers',
                                    showlegend=False,
                                    marker_color = colors[count]
                                )
                            )

                    count = count + 1

                fig_1 = go.Figure(data=trace_sec1)
                
                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)

                titulo_box = datos.titulo_box(ventana_tiempo)
            
   
                fig_1.update_layout(title="Promedio de datos cada "+str(titulo_box)+", durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")",yaxis={"title": "Aceleración (cm/s²)"})
        elif tipo_sensor == 'weather-station':
            # La variable df contiene el dataframe que se utiliza para generar el graficos OHLC
            df = datos.datos_ace(dt(2008,4,1,0,38,3),ventana_tiempo,'humedad')

            # Aqui se crea el grafico OHLC para la humedad
            fig_1.add_trace(
                go.Ohlc(
                    x=df['fecha'],
                    open=df['open'],
                    high=df['max'],
                    low=df['min'],
                    close=df['close'],
                    increasing_line_color= 'blue', 
                    decreasing_line_color= 'red',
                    showlegend=True,
                    name= 'Humedad'
                    )
                )
 
            fig_1.update(layout_xaxis_rangeslider_visible=False)
            titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)
            #titulos para ambos graficos OHLC

            fig_1.update_layout(title={'text':"Datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+" de la Humedad durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")"},yaxis={"title": "Humedad"})

        return fig_1

    #else:
    #    return {}

#Funcion que actualiza el grafico secundario 2
@plotly_app.callback(Output('grafico-2','figure'),
              [Input('boton-aceptar', 'n_clicks')],
              [State('cantidad-sensores','value'),State('horas-disponibles', 'value'),State('elegir-tipo-sensor','value'),State('elegir-sensor','value'),
               State('elegir-sensor-multi','value'),State('elegir-fecha','date'),State('ventana-tiempo','value'),State('elegir-eje','value'),State('elegir-eje-multi','value')])

def update_grafico_2(n_clicks,cantidad_sensores,hora,tipo_sensor,sensor,sensor_multi,fecha,ventana_tiempo,ejes,eje):
    if len(ejes) < 1 :
        ejes.append('x')
    if fecha != None:
        if str(str(fecha).split(sep='T')[0]) == str(str(datos.fecha_inicial(tipo_sensor,eje)).split(sep=' ')[0]):
            #fecha = dt.strptime(str(str(fecha).split(sep='T')[0]) + ' ' + str(str(datos.fecha_inicial()).split(sep=' ')[1]),'%Y-%m-%d %H:%M:%S')
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
        else:
            fecha = dt.strptime(str(str(fecha).split(sep='T')[0])+' '+datos.crear_hora(hora),'%Y-%m-%d %H:%M:%S')
    else:
        fecha = datos.fecha_inicial(tipo_sensor,eje)
    #Se inicializan variables
    df = pd.DataFrame()
    fig_2 = go.Figure()
    if n_clicks >= 0:
        fecha_ini_titulo,fecha_fin_titulo = datos.fecha_titulo(fecha,ventana_tiempo) 
        #Dependiendo del tipo de sensor se crean visualizaciones distintas
        if tipo_sensor == 'weather-station':
            
            #Aqui se crea el histograma circular que contine datos de la direccion y velocidad del viento
            dir = datos.datos_ace(dt(2008,4,1,0,38,3),ventana_tiempo,'dir_viento')['dir_viento'].tolist()
            vel = datos.datos_ace(dt(2008,4,1,0,38,3),ventana_tiempo,'vel_viento')['vel_viento'].tolist()

            tmp1 = collections.Counter(dir)
            ini,fin = datos.rangos(tmp1)

            rr,tt = datos.datos_por_rango(pd.DataFrame({'dir_viento': dir,'vel_viento':vel}),ini,fin)
            dff = pd.DataFrame({'Dirección': tt,'Velocidad (m/s)':rr})
            fig_2 = px.bar_polar(dff, r="Velocidad (m/s)", theta="Dirección",color_discrete_sequence= px.colors.sequential.Plasma_r)
            titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)

            fig_2.update_layout(title={'text':"Dirección y Velocidad (m/s) del viento durante "+str(titulo_OHLC)+" "})
        elif tipo_sensor == 'Acelerometro':
            if cantidad_sensores == '1-sensor':
                # La variable df contiene el dataframe que se utiliza para generar el histograma
                # Aqui se crea el histograma
                trace_sec2 = []
                colors = ['#e6194b', '#3cb44b', '#ffe119']
                count = 0
                for e in ejes:
                    start_time = time()

                    df = datos.datos_ace(fecha,ventana_tiempo,sensor,e)
                    start_time = time()

                    #fig_2 = go.Figure(data=[go.Histogram(x=df[sensor],showlegend=False)])
                    trace_sec2.append(
                        go.Histogram(
                            x=df[sensor],
                            showlegend=True,
                            marker_color = colors[count],
                            name=datos.traductor_nombre(sensor)+' eje: '+str(e)
                        )
                    )
                    count = count + 1
                    fig_2 = go.Figure(data=trace_sec2)
                    elapsed_time = time() - start_time
                    print("Tiempo Transcurrido crear Histograma: %0.1f seconds." % elapsed_time)
                
                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)

                fig_2.update_layout(title="Frecuencia de datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+" del "+str(datos.traductor_nombre(sensor))+"<br>durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")",yaxis={"title": "Frecuencia (N° de Datos)"}, xaxis={"title": "Aceleración (cm/s²)"},bargap=0.1,)
            else:
                #Listas que conteneran cada trace generado por cada dataframe creado para poder visualizarlos en una grafica
                trace_sec2 = []
                
                
                #colores para las graficas
                colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080', '#ffffff', '#000000']
                count = 0

                #por cada sensor seleccionado se crean df 
                for sen in sensor_multi:

                    df = datos.datos_ace(fecha,ventana_tiempo,sen,eje)

                    # Aqui se crea el histograma
                    trace_sec2.append(
                        go.Histogram(
                            x=df[sen],
                            showlegend=True,
                            marker_color = colors[count],
                            name=datos.traductor_nombre(sen)
                        )
                    )
                    count = count + 1
                
                fig_2 = go.Figure(data=trace_sec2)
                
                titulo_OHLC = datos.titulo_OHLC(ventana_tiempo)
            
                fig_2.update_layout(title="Frecuencia de datos cada "+str(datos.titulo_freq_datos(ventana_tiempo))+"<br>durante "+str(titulo_OHLC)+"<br>("+fecha_ini_titulo+" - "+fecha_fin_titulo+")",yaxis={"title": "Frecuencia (N° de Datos)"}, xaxis={"title": "Aceleración (cm/s²)"},bargap=0.1,)

        return fig_2

    #else:
    #    return {}

#Funcion para crear los reportes
@plotly_app.callback(Output('retorno-reportes','children'),
             [Input('boton-generar-reporte','n_clicks')],[State('grafico-principal','figure'),State('grafico-1','figure'),State('grafico-2','figure'),
              State('valor-promedio', 'children'),State('valor-max', 'children'),State('valor-min', 'children'),State('fecha-valor-max','children'),
              State('fecha-valor-min','children'),State('num-valor-max','children'),State('num-valor-min','children'),State('alert-sup','children'),
              State('alert-inf','children'),State('fecha-alert-sup','children'),State('fecha-alert-inf','children'),State('elegir-sensor','value'),
              State('elegir-sensor-multi','value'),State('elegir-fecha','date'),State('ventana-tiempo','value'),State('linea-control-sup','value'),
              State('linea-control-inf','value'),State('horas-disponibles', 'value'),State('cantidad-sensores','value'),State('elegir-eje','value'),
              State('elegir-eje-multi','value')])

def crear_reporte(clicks, fig_principal,fig_sec1,fig_sec2,valor_promedio,valor_max,valor_min,fecha_valor_max,fecha_valor_min,num_valor_max,num_valor_min,alert_sup,alert_inf,fecha_alert_sup,fecha_alert_inf,sensor,sensor_multi,fecha,ventana_tiempo,valor_linea_control_sup,valor_linea_control_inf,hora,cantidad_sensores,ejes,eje):
    if len(ejes) < 1 :
        ejes.append('x')

    sensores = list()
    if (str(type(sensor_multi))=="<class 'list'>"):
        for sen in sensor_multi:
            sensores.append(datos.traductor_nombre(sen))
    else:
        sensor = datos.traductor_nombre(sensor)
    if clicks > 0:
        datos.generar_reportes(go.Figure(fig_principal),go.Figure(fig_sec1),go.Figure(fig_sec2),valor_promedio,valor_max,valor_min,fecha_valor_max,fecha_valor_min,num_valor_max,num_valor_min,alert_sup,alert_inf,fecha_alert_sup,fecha_alert_inf,sensor,sensores,fecha,ventana_tiempo,valor_linea_control_sup,valor_linea_control_inf,hora,cantidad_sensores,ejes,eje)
    return 'uno'

### FIN DATOS RECIENTES ###

mail = Mail(app)

db.init_app(app)
app.register_blueprint(views_api)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'views_api.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(user_id)

@app.route('/password_reset', methods=["GET", "POST"])
def password_reset():
    if request.method == "GET":
        return render_template('password_reset.html')
    if request.method == "POST":
        email = request.form.get('email')
        user = Usuario.verify_email(email)
        if user:
            token = user.get_reset_token()
            msg = Message()
            msg.subject = "[Plataforma SHM] Reestablecer contraseña"
            msg.sender = app.config['MAIL_USERNAME']
            msg.recipients = [user.id]
            msg.html = render_template('reset_email.html', user=user, token=token)
            mail.send(msg)
        return redirect(url_for('views_api.login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, use_reloader=False)
