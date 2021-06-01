import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from . import dataframe as datos
#import dash_bootstrap_components as dbc

datos_recientes_layout = html.Div([
        # Div que contiene el titulo de la pagina
        html.Div([
            html.Div([
                html.H3(
                    "Datos Recientes",
                    style={'color': 'Black','fontWeight': 'bold',"marginBottom": "0px"},
                ),
                html.H5(
                    "Plataforma Monitoreo Salud Estructural",
                    style={"marginTop": "0px"}
                ),
            ],
            className="one-half column",
            id="title",
            ),
        ],
        id="header",
        className="row flex-display",
        style={"marginBottom": "25px"},
        ),

html.Div([
    #Esta seccion contiene todo lo que se muestra en la pestaña "Datos Sensores" del menu de opciones
    html.Div([
        html.P(
            "Seleccione Sensor",
            className="control_label",
            style={'textAlign': 'center','fontSize':'20px'}
        ),
        html.Div([
            dcc.Loading(
                id="carga-elegir-sen",
                children=[
                dcc.Dropdown(
                        id="elegir-sensor",
                        multi=False,
                        options=[{"label": key , "value": value}for key,value in datos.nombres_sensores('Acelerometro').items()],
                        value=str(datos.nombres_sensores('Acelerometro').get(list(datos.nombres_sensores('Acelerometro').keys())[0])),
                    ),
                ],type="default"
            )
        ],id='sensor-uni'),
        html.P(
            "Seleccione Ejes",
            className="control_label",
            style={'textAlign': 'center','fontSize':'20px'}
        ),
        html.Div([
            dcc.Loading(
                id="carga-elegir-eje",
                children=[
                    dcc.Checklist(
                        id="elegir-eje",
                        options=[{'label': 'X', 'value': 'x'},
                                {'label': 'Y', 'value': 'y'},
                                {'label': 'Z', 'value': 'z'}],
                        value=['x'],
                        labelStyle={'display': 'inline-block'}
                    ),
                ],type="default"
            )
        ],style={'textAlign': 'center','display':'inline'},id='ejes'),
        html.Br(),
        html.Div([
            html.Button(
                "Actualizar Gráficos",
                id='boton-aceptar',
                n_clicks = 0,
                style={'color': 'Black', 'backgroundColor':'lavender','fontSize':'17px'}
            ),
        ],style={'textAlign': 'center'}),
        ],className="pretty_container four columns",id="cross-filter-options",
    ),
    # En esta seccion se tiene todo lo relacionado con los indicadores, promedio, maximo valor , minimo valor y las lineas de control
    html.Div([
        # En esta seccion se tienen todos los graficos a mostrar en la ventana
        html.Div([
            dcc.Loading(
                id="carga-grafico-principal",
                children=[
                    dcc.Graph(
                        id="grafico-principal"
                        )
                    ],type="default"
                ),
            ],id='cuadro-grafico-principal',className="pretty_container",
            ),
        ],id="right-column",className="eight columns",
    ),
    ],className="row flex-display",
),
],id="mainContainer",style={"display": "flex", "flexDirection": "column"},
)
