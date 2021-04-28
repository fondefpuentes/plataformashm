import dash
import collections
import dataframe as datos
import layout as layout
import plotly.express as px
import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import numpy as np
from dash.dependencies import Input, Output,State
from datetime import datetime as dt
from time import time

plotly_app = dash.Dash(
    __name__,meta_tags=[{"name": "viewport", "content": "width=device-width"}], url_base_pathname="/dash/", assets_folder="./DatosRecientes/assets"
)
ventana_tiempo = '288S'
tipo_sensor = 'Acelerometro'
cantidad_sensores = '1-sensor'

def init_plotly(server):
    plotly_app.title = 'Datos Recientes - Plataforma de Monitoreo Salud Estructural'
    plotly_app.layout = layout.datos_recientes_layout
    plotly_app.server = server
    return plotly_app.server

@plotly_app.callback(Output('indicador-multi','style'),
              [Input('boton-aceptar', 'n_clicks')],[State('cantidad-sensores','value')])

def update_info(clicks,cantidad_sensores):
    if clicks >= 0:
        if cantidad_sensores == '1-sensor':
            return {'display':'none'}
        else:
            return {'display':'inline'}

# Esta funcion cambia segun el tipo de sensor, los sensores disponibles y ademas si en las propiedades se selecciona tener mas de 1 sensor por grafica cambia el dropdown a multiple
@plotly_app.callback([Output('elegir-sensor', 'value'),Output('elegir-sensor', 'options'),Output('sensor-uni','style'),Output('ejes','style')],
                    [Input('cantidad-sensores','value')])

def lista_sensores(cantidad_sensores):
    nombres_sensores = datos.nombres_sensores(tipo_sensor)
    if cantidad_sensores == '1-sensor':
        print("entra 1")
        return str(nombres_sensores.get(list(nombres_sensores.keys())[0])),[{"label": key , "value": value}for key,value in nombres_sensores.items()],'',[{"label":'',"value":''}],{'display':'none'},{'display':'inline'},{'textAlign': 'center','display':'none'},{'textAlign': 'center','display':'inline'}
    elif cantidad_sensores == 'varios-sensores':
        print("entra multi")
        return '',[{"label":'',"value":''}],[str(nombres_sensores.get(list(nombres_sensores.keys())[0]))],[{"label": key , "value": value}for key,value in nombres_sensores.items()],{'display':'inline'},{'display':'none'},{'textAlign': 'center','display':'inline'},{'textAlign': 'center','display':'none'}


#Funcion que actualiza el grafico principal
@plotly_app.callback(Output('grafico-principal','figure'),
                    Input('boton-aceptar', 'n_clicks'),
                    [State('elegir-sensor','value'),State('elegir-eje','value')])

def update_grafico_principal(n_clicks,sensor,ejes):
    if len(ejes) < 1 :
        ejes.append('x')
    # fecha = datos.fecha_inicial()
    #Se inicializan variables
    df = pd.DataFrame()
    fig_principal = go.Figure()
    #Listas que conteneran cada trace generado por cada dataframe creado para poder visualizarlos en una grafica
    trace_principal = []
    if n_clicks >= 0:
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
                    df = datos.datos_ace(sensor,e)

                    elapsed_time = time() - start_time
                    print("Tiempo Transcurrido crear DF: %0.1f seconds." % elapsed_time)
                    # Aqui se crea el grafico OHLC
                    start_time = time()
                    trace_principal.append(go.Ohlc(x=df.index,
                        open=df['open'],
                        high=df['max'],
                        low=df['min'],
                        close=df['close'],
                        increasing_line_color= colors[new_count_in],
                        decreasing_line_color= colors[new_count_de],
                        name=str(sensor)+' eje: '+str(e),
                        showlegend=True))
                    count = count + 1
                    new_count_in = new_count_in + 2
                    new_count_de = new_count_de + 2
                    new_df = df

                    #lista de dataframe para generar los indicadores resumen
                    list_df.append(df)
                df = pd.concat(list_df, axis=0,ignore_index=True)
                fig_principal = go.Figure(data=trace_principal)
        return fig_principal
    # print("entra update grafico")
    # if len(ejes) < 1 :
    #     ejes.append('x')
    #
    # if n_clicks >= 0:
    #     df = datos.datos_ace(sensor,eje)
    #     fig_principal =  go.Figure(data=go.Ohlc(x = df.index,
    #                                                 open=df['open'],
    #                                                 high=df['max'],
    #                                                 low=df['min'],
    #                                                 close=df['close'],
    #                                                 increasing_line_color = 'green',
    #                                                 decreasing_line_color = 'red'
    #                                             )
    #                                 )
    # return fig_principal

# Main
if __name__ == "__main__":
    # plotly_app = dash.Dash(__name__, url_base_pathname="/dash/", assets_folder="./DatosRecientes/assets")

    # plotly_app = dash.Dash(
    #     __name__, url_base_pathname="/dash/", assets_folder="./DatosRecientes/assets"
    # )
    # plotly_app = dash.Dash( __name__,meta_tags=[{"name": "viewport", "content": "width=device-width"}], url_base_pathname="/dash/", assets_folder="./DatosRecientes/assets")

    plotly_app.title = 'Datos Recientes - Plataforma de Monitoreo Salud Estructural'
    plotly_app.layout = layout.datos_recientes_layout
    plotly_app.run_server(debug=True, use_reloader=True)
