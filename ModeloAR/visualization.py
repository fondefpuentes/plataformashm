import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from .modelo import getCoef, mahalanobis
import pandas as pd
import numpy as np
import json

def create_plot(nombre):
    coefdf = []
    data = go.Figure()
    eje = ['x', 'y', 'z']
    for axis in range(3):
        df = getCoef(6589, nombre, axis)
        gb = df.groupby('reporte_dano_id')
        dfs = [gb.get_group(x) for x in gb.groups]
        coef_sensor = []
        for i in range(len(dfs)):
            column = dfs[i]["numero_modelo"]
            max_value = column.max()
            for j in range(max_value + 1):
                df2 = dfs[i][dfs[i]['numero_modelo'] == j].sort_values(by=['numero'])
                coef_sensor.append(np.array(df2['valor']))
        coefdf.append(pd.DataFrame(coef_sensor))
    for i in range(3):
        mean = []
        num_coefs = np.arange(len(coefdf[i].columns))

        for columna in coefdf[i].columns:
            mean.append(coefdf[i][columna].mean())
        data.add_trace(
            go.Scatter(
                x = num_coefs,
                y = mean,
                name = 'Promedio eje ' + eje[i],
                mode = 'lines',
                marker_color = 'rgba(250,0,0,.5)',
            ),
        )
        # for last in range(len(coefdf[i])):
        #     data.add_trace(
        #         go.Scatter(
        #             x = coefs,
        #             y = mean,
        #             name = str(last) + ' ultimo coef eje ' + eje[i],
        #             mode = 'lines',
        #             marker_color = 'rgba(0,250,0,.5)',
        #         )
        #     )
        try:
            for last in range(len(coefdf[i]), len(coefdf[i]) - 3, -1):
                data.add_trace(
                    go.Scatter(
                        x = num_coefs,
                        y = coefdf[i].iloc[last - 1],
                        name = str(len(coefdf[i]) - last) + ' ultimo coef eje ' + eje[i],
                        mode = 'lines',
                        marker_color = 'rgba(0,250,0,.5)',
                    ),
                )
        except:
            print("No tiene datos")
        # print("coeficientes", coefdf[i].columns[:-1])
        # print("valores", coefdf[i].loc[:, [0,1,2,3,4,5,6]][-3:].values)
        # data.add_trace(
        #     go.Scatter(
        #         x = num_coefs,
        #         y = coefdf[i].loc[:, [0,1,2,3,4,5,6]][-3:].values,
        #         name = 'Ultima hora del eje ' + eje[i],
        #         mode = 'lines',
        #         marker_color = 'rgba(0,250,0,.5)',
        #     ),
        #     row = 1,
        #     col = 1,
        # )
    data.update_xaxes(title_text="Coeficiente AR")
    data.update_yaxes(title_text="Valor coeficiente AR")
    data.update_layout(
        title= nombre,
        legend_title="Series coeficientes",
        # font=dict(
        #     family="Courier New, monospace",
        #     size=18,
        #     color="RebeccaPurple"
        # )
    )

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

def create_mah(nombre):

    coefdf = []
    data = go.Figure()
    eje = ['x', 'y', 'z']
    for axis in range(3):
        df = getCoef(6589, nombre, axis)
        gb = df.groupby('reporte_dano_id')
        dfs = [gb.get_group(x) for x in gb.groups]
        coef_sensor = []
        for i in range(len(dfs)):
            column = dfs[i]["numero_modelo"]
            max_value = column.max()
            for j in range(max_value + 1):
                df2 = dfs[i][dfs[i]['numero_modelo'] == j].sort_values(by=['numero'])
                coef_sensor.append(np.array(df2['valor']))
        coefdf.append(pd.DataFrame(coef_sensor))
    for i in range(3):
        mean = []
        num_coefs = np.arange(len(coefdf[i].columns))
        mh = mahalanobis(x = coefdf[i], data = coefdf[i])
        coefdf[i]['mahalanobis'] = mh
        data.add_trace(
                go.Bar(
                    x = coefdf[i].index.values,
                    y = coefdf[i]['mahalanobis'],
                    name = "Distancia Mahalanobis eje " + eje[i],
                ),
        )


    data.add_hline(y=15, line_width=2, fillcolor="red", opacity=0.5, row =2, col=1)
    data.update_xaxes(title_text="Serie de datos")
    data.update_yaxes(title_text="Valor Distancia Mahalanobis")
    data.update_layout(
        legend_title="Ejes de distancias",
        # font=dict(
        #     family="Courier New, monospace",
        #     size=18,
        #     color="RebeccaPurple"
        # )
    )

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON
