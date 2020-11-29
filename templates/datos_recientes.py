import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import DatosRecientes.dataframe as datos
#import dash_bootstrap_components as dbc

datos_recientes_layout = html.Div([
        #Div que contiene el titulo de la pagina
        html.Div([
            html.Div(
                id='retorno-reportes', 
                style={'display': 'none'}
            ),
            
            html.Div([
                html.H3(
                    "Datos Recientes",
                    style={'color': 'Black','font-weight': 'bold',"margin-bottom": "0px"},
                ),
                html.H5(
                    "Plataforma Monitoreo Salud Estructural", 
                    style={"margin-top": "0px"}
                ),
            ],
            className="one-half column",
            id="title",
            ),
            html.Div([
                html.A(
                    dcc.Loading(
                        id="carga-reportes",
                        children=[
                            html.Button(
                                "Generar Reporte", 
                                id="boton-generar-reporte",
                                n_clicks = 0,
                                style={'color': 'Black', 'backgroundColor':'lavender','font-size':'17px'}
                            ),
                        ]
                    )
                )
            ],
            className="one-third column",
            id="button",
            ),
        ],
        id="header",
        className="row flex-display",
        style={"margin-bottom": "25px"},
        ),
        html.Div([
            html.Div([
                #Esta seccion contiene todo lo que se muestra en la pestaña "Datos Sensores" del menu de opciones
                dcc.Tabs([
                    dcc.Tab(
                        label='Datos Sensores', 
                        children=[
                            html.P(
                                "Seleccione Tipo de Sensor",
                                className="control_label",
                                style={'textAlign': 'center','font-size':'20px'}
                            ),
                            html.Div([
                                dcc.Loading(
                                    id="carga-elegir-tipo-sen", 
                                    children=[
                                        dcc.Dropdown(
                                            id="elegir-tipo-sensor", 
                                            multi=False, 
                                            options=[{"label": key , "value": value}for key,value in datos.tipos_sensores().items()],
                                            value=str(datos.tipos_sensores().get(list(datos.tipos_sensores().keys())[0])),
                                        ),
                                    ],type="default"
                                )
                            ]),
                            html.Br(),
                            html.P(
                                "Seleccione Sensor",
                                className="control_label",
                                style={'textAlign': 'center','font-size':'20px'}
                            ),
                            html.Div([
                                dcc.Loading(
                                    id="carga-elegir-sen", 
                                    children=[
                                        dcc.Dropdown(
                                            id="elegir-sensor", 
                                            multi=False, 
                                            options=[{"label": key , "value": value}for key,value in datos.nombres_sensores('acelerometro').items()],
                                            value=str(datos.nombres_sensores('acelerometro').get(list(datos.nombres_sensores('acelerometro').keys())[0])),
                                        ),
                                    ],type="default"
                                )
                            ],id='sensor-uni'),
                            html.Div([
                                dcc.Loading(
                                    id="carga-elegir-sen-multi", 
                                    children=[
                                        dcc.Dropdown(
                                            id="elegir-sensor-multi",
                                            multi=True, 
                                            options=[{"label": key , "value": value}for key,value in datos.nombres_sensores('acelerometro').items()],
                                            value=str(datos.nombres_sensores('acelerometro').get(list(datos.nombres_sensores('acelerometro').keys())[0])),
                                        ),
                                    ],type="default"
                                )
                            ],style={'display':'none'},id='sensor-multi'),
                            html.P(
                                "Seleccione Ejes",
                                className="control_label",
                                style={'textAlign': 'center','font-size':'20px'}
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
                            html.Div([
                                dcc.Loading(
                                    id="carga-elegir-eje-multi", 
                                    children=[
                                        dcc.RadioItems(
                                            id="elegir-eje-multi",  
                                            options=[{'label': 'X', 'value': 'x'},
                                                    {'label': 'Y', 'value': 'y'},
                                                    {'label': 'Z', 'value': 'z'}],
                                            value='x',
                                            labelStyle={'display': 'inline-block'}
                                        ),
                                    ],type="default"
                                )
                            ],style={'display':'none'},id='ejes-multi'),
                            html.Br(),
                            html.P(
                                "Seleccione Fecha Inicial: ",
                                className="control_label",
                                style={'textAlign': 'center','font-size':'20px'}
                            ),
                            html.Div([
                                dcc.Loading(
                                    id="carga-elegir-fecha", 
                                    children=[
                                        dcc.DatePickerSingle(
                                            id='elegir-fecha',
                                            display_format='DD/MM/YYYY',
                                            min_date_allowed=datos.fecha_inicial('acelerometro','x'),
                                            max_date_allowed=datos.fecha_final('acelerometro','x'),
                                            initial_visible_month=datos.fecha_inicial('acelerometro','x'),
                                            date = datos.fecha_inicial('acelerometro','x')
                                        ),
                                    ],type="default"
                                )
                            ],style={'textAlign': 'center'}),
                            html.Br(),
                            html.P(
                                "Seleccione Ventana de Tiempo", 
                                className="control_label",
                                style={'textAlign': 'center','font-size':'20px'}
                            ),
                            html.Div([
                                dcc.Loading(
                                    id="carga-ventana-tiempo", 
                                    children=[
                                        dcc.RadioItems(
                                            id="ventana-tiempo",
                                            options=[{"label": key , "value": value}for key,value in datos.ventana_tiempo(3).items()],
                                            value=str(list(datos.ventana_tiempo(3).values())[0]),
                                            labelStyle={"display": "inline-block"},
                                            className="dcc_control",
                                        ),
                                    ],type="default"
                                )  
                            ],style={'textAlign': 'center'}),
                            html.Br(),
                            html.Div([
                                html.P(
                                    "Deslice para Seleccionar Hora", 
                                    className="control_label",
                                    style={'textAlign': 'center','font-size':'20px'}
                                ),
                                html.Div([
                                    dcc.Loading(
                                        id="carga-horas-disponibles", 
                                        children=[
                                            dcc.Slider(
                                                id='horas-disponibles',
                                                min=0,
                                                max=23,
                                                value=int(datos.horas_del_dia(str(datos.nombres_sensores('acelerometro').get(list(datos.nombres_sensores('acelerometro').keys())[0])),datos.fecha_inicial('acelerometro','x'))[1]),
                                                step=None,
                                                dots=True,
                                                updatemode='drag',
                                                included=False
                                            ),
                                        ],type="default"
                                    )
                                ]),  
                                html.P(
                                    "Hora Seleccionada: ---",
                                    id='hora-disponible-seleccionada', 
                                    className="control_label",
                                    style={'textAlign': 'center','font-size':'18px'}
                                )    
                            ],id='contenedor-horas-disponibles'),
                            html.Br(),
                            html.Div([
                                html.Button(
                                    "Actualizar Gráficos",
                                    id='boton-aceptar',
                                    n_clicks = 0,
                                    style={'color': 'Black', 'backgroundColor':'lavender','font-size':'17px'}
                                ),
                            ],style={'textAlign': 'center'}),
                        ]),
                        # Esta seccion contiene todo lo que se muestra en la pestaña "Propiedades de los graficos"
                    dcc.Tab(
                            label='Propiedades de los Gráficos', 
                            children=[
                                html.Br(),
                                html.Br(),
                                html.P(
                                    "Cantidad de Sensores a Visualizar por Gráficas", 
                                    className="control_label",
                                    style={'textAlign': 'center','font-size':'20px'}
                                ),
                                html.Br(),
                                html.Div([
                                    dcc.RadioItems(
                                        id='cantidad-sensores',
                                        options=[
                                            {'label': '1 Sensor', 'value': '1-sensor'},
                                            {'label': 'Varios Sensores', 'value': 'varios-sensores'},
                                        ],
                                        value='1-sensor',
                                        labelStyle={'display': 'inline-block'}
                                    ), 
                                ],style={'textAlign': 'center'}), 
                                html.Br(),
                                html.Br(),
                                html.P(
                                    "Linea de control Superior", 
                                    className="control_label",
                                    style={'textAlign': 'center','font-size':'20px'}
                                ),
                                html.Br(),
                                html.Div([
                                    dcc.Input(
                                        id='linea-control-sup', 
                                        type="number", 
                                        placeholder="Solo valores positivos",
                                        min=0, 
                                        max=1000, 
                                        step=0.001,
                                        style={"width": "35%",'font-size':'15px'}
                                    ),
                                ],style={'textAlign': 'center'}),
                                html.Br(),
                                html.Div([
                                    html.Button(
                                        'Agregar / Actualizar',
                                        id='boton-linea-sup',
                                        n_clicks = 0,
                                        style={'color': 'Black', 'backgroundColor':'lavender','font-size':'15px'}
                                    ),
                                    html.Button(
                                        'Quitar',
                                        id='boton-quitar-linea-sup',
                                        n_clicks = 0,
                                        style={'color': 'Black', 'backgroundColor':'tomato','font-size':'15px'}
                                    ),
                                ],style={'textAlign': 'center'}),
                                html.Br(),
                                html.Br(),
                                html.P(
                                    "Linea de control Inferior", 
                                    className="control_label",
                                    style={'textAlign': 'center','font-size':'20px'}
                                ),
                                html.Br(),
                                html.Div([
                                    dcc.Input(
                                        id='linea-control-inf', 
                                        type="number", 
                                        placeholder="Solo valores negativos",
                                        value =None,
                                        min=-1000, 
                                        max=0, 
                                        step=0.001,
                                        style={"width": "35%",'font-size':'15px'}
                                    ),
                                ],style={'textAlign': 'center'}),
                                html.Br(),
                                html.Div([
                                    html.Button(
                                        'Agregar / Actualizar',
                                        id='boton-linea-inf',
                                        n_clicks = 0,
                                        style={'color': 'Black', 'backgroundColor':'lavender','font-size':'15px'}
                                    ),
                                    html.Button(
                                        'Quitar',
                                        id='boton-quitar-linea-inf',
                                        n_clicks = 0,
                                        style={'color': 'Black', 'backgroundColor':'tomato','font-size':'15px'}
                                    ),
                                ],style={'textAlign': 'center'})
                            ])
                    ])
                ],className="pretty_container four columns",id="cross-filter-options",
            ),
            # En esta seccion se tiene todo lo relacionado con los indicadores, promedio, maximo valor , minimo valor y las lineas de control
            html.Div([
                html.Div([
                    html.Div([
                        dcc.Loading(
                            id="carga-promedio", 
                            children=[
                                html.Br(),
                                html.Br(),  
                                html.P("Valor Promedio",style={'color': 'Black','font-weight': 'bold'}),
                                html.H4('---',id="valor-promedio"),
                                html.P("(Datos de los indicadores pertencientes al ultimo sensor seleccionado)", id="indicador-multi",style={'display': 'none'}),
                                ],type="default"        
                            )
                            ],id="promedio",className="mini_container",
                        ),
                    html.Div([
                        dcc.Loading(
                            id="carga-val-max", 
                            children=[
                                html.P("Valor Máximo",style={'color': 'Black','font-weight': 'bold'}),
                                html.H4('---',id="valor-max"),
                                html.P("N° Veces: ---",id='num-valor-max'),
                                html.P("Última Repetición:"),
                                html.P("---",id='fecha-valor-max'),
                                ],type="default"
                            ),
                            ],id="max",className="mini_container",
                        ),
                    html.Div([
                        dcc.Loading(
                            id="carga-val-min", 
                            children=[
                                html.P("Valor Mínimo",style={'color': 'Black','font-weight': 'bold'}),
                                html.H4('---',id="valor-min"),
                                html.P("N° Veces: ---",id='num-valor-min'),
                                html.P("Última Repetición:"),
                                html.P("---",id='fecha-valor-min'),
                                ],type="default"
                            ),
                            ],id="min",className="mini_container",
                        ),
                    html.Div([
                        dcc.Loading(
                            id="carga-aler-sup", 
                            children=[
                                html.P("N° Alertas",style={'color': 'Black','font-weight': 'bold'}),
                                html.P("Línea de Control",style={'color': 'Black','font-weight': 'bold'}),
                                html.P("Superior",style={'color': 'Black','font-weight': 'bold'}),
                                html.H4('---',id="alert-sup"),
                                html.P("Última Alerta:"),
                                html.P("---",id='fecha-alert-sup'),
                                ],type="default"
                            ),
                            ],id="alertmax",className="mini_container",
                        ),
                    html.Div([
                        dcc.Loading(
                            id="carga-aler-inf",
                            children=[
                                html.P("N° Alertas",style={'color': 'Black','font-weight': 'bold'}),
                                html.P("Línea de Control",style={'color': 'Black','font-weight': 'bold'}),
                                html.P("Inferior",style={'color': 'Black','font-weight': 'bold'}),
                                html.H4('---',id="alert-inf"),
                                html.P("Última Alerta:"),
                                html.P("---",id='fecha-alert-inf'),
                                ],type="default"
                            ),
                            ],id="alertmin",className="mini_container",
                        ),
                    ],id="info-container",className="row container-display",
                ),
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
        #Esta seccion contiene todas las graficas
        html.Div([
            html.Div([
                dcc.Loading(
                    id="carga-grafico-1",
                    children=[
                        dcc.Graph(
                            id='grafico-1'
                            )
                        ],type="default"
                    ),
                ],id='cuadro-grafico-1',className="pretty_container seven columns",
            ),
            html.Div([
                dcc.Loading(
                    id="carga-grafico-2",
                    loading_state={'is_loading':True},
                    children=[
                        dcc.Graph(
                            id='grafico-2'
                            )
                        ],type="default"
                    ),
                ],id='cuadro-grafico-2',className="pretty_container five columns",
            ),
            ],className="row flex-display",
        ),
    ],id="mainContainer",style={"display": "flex", "flex-direction": "column"},
)