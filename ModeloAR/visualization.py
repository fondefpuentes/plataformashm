import plotly
import plotly.graph_objs as go

import pandas as pd
import numpy as np
import json

def create_plot(nombre):


    data = go.Figure()
    for i in range(50):
        N = 6
        x = np.linspace(0, 1, N)
        y = np.random.randn(N)
        df = pd.DataFrame({'x': x, 'y': y}) # creating a sample dataframe



        if i >= 47:
            data.add_trace(
                go.Scatter(
                    x=df['x'], # assign x as the dataframe column 'x'
                    y=df['y'],
                    name = 'Ultimo',
                    mode = 'lines',
                    marker_color = 'rgba(250,0,0,1)',
                )
            )

        else:
            data.add_trace(
                go.Scatter(
                    x=df['x'], # assign x as the dataframe column 'x'
                    y=df['y'],
                    name = 'Series',
                    mode = 'lines',
                    marker_color = 'rgba(0,0,0,.5)',
                )
            )   

    data.update_layout(
        title= nombre,
        xaxis_title="Coeficientes AR",
        yaxis_title="Valor de coeficiente",
        legend_title="Series coeficientes",
        # font=dict(
        #     family="Courier New, monospace",
        #     size=18,
        #     color="RebeccaPurple"
        # )
    )

    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON
