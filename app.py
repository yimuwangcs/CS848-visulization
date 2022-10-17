import panel as pn
pn.extension('plotly')
from panel import widgets as pnw
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

import plotly.graph_objects as go
from datetime import datetime
from meteostat import Point, Daily

from collections import defaultdict
import time
import requests
import urllib.parse
import pandas as pd
import math
from tqdm import tqdm
from multiprocessing.dummy import Pool
from threading import Thread, Lock
import os

def load_data():
    if os.path.exists('database.csv'):
        print(f'reading data')
        return pd.read_csv('database.csv', index_col=0)
    else:
        print(f'crawling data')
        rank = defaultdict(int)

        year_pair = []
        for fromyear_2 in range(1980, 2023):
            for toyear_2 in range(fromyear_2 + 1, 2023):
                year_pair.append((fromyear_2, toyear_2))

        rank = update_rank_with_latandlon(rank)
        
        for fromyear_2, toyear_2 in tqdm(year_pair):
            rank = update_rank(rank, fromyear=fromyear_2, toyear=toyear_2)

        for fromyear_2, toyear_2 in tqdm(year_pair):
            rank = update_rank_with_avgtemporature(rank, fromyear=fromyear_2, toyear=toyear_2)
        df = pd.DataFrame(rank).T 
        df.to_csv('database.csv')
        return df

from_year_1 = pn.widgets.Select(name='From Year1', options=list(range(1980, 2023)))
to_year_1 = pn.widgets.Select(name='To Year1', options=list(range(1980, 2023)))
from_year_2 = pn.widgets.Select(name='From Year2', options=list(range(1980, 2023)))
to_year_2 = pn.widgets.Select(name='To Year2', options=list(range(1980, 2023)))

from_year_2.value = 2002
to_year_2.value = 2022
from_year_1.value = 1982
to_year_1.value = 2002

title = pn.pane.Markdown("# CS848: The art and science of empirical computer science\n##The Visualization Project\n###By Yimu Wang")

pbutton = pnw.Button(name='Click me', button_type='primary')
plot = pn.pane.Plotly(name='plot')

alert = pn.pane.Alert('Pleae note that the from year must be bigger than to year, and from year1 must bigger than from year 2'.format(alert_type='danger'), alert_type='danger')
alert.visible = False

def b(event):
    df = load_data()
    fromyear_1 = from_year_1.value
    toyear_1 = to_year_1.value
    fromyear_2 = from_year_2.value
    toyear_2 = to_year_2.value
#     title.text = f'{fromyear_1}-{toyear_1}'
    if fromyear_1 < toyear_1 and fromyear_2 < toyear_2 and fromyear_1 < fromyear_2:

        df = pd.DataFrame(df, columns=['lat', 'lon', 
                                       f'rank-{fromyear_1}-{toyear_1}',
                                      f'rank-{fromyear_2}-{toyear_2}'] + 
                         [f'temperature-{i}' for i in set(list(range(fromyear_1, toyear_1 + 1)) + list(range(fromyear_2, toyear_2 + 1)))])
        df = df.dropna(axis=0, how='any')

        df[f'temperature-{fromyear_2}-{toyear_2}'] = 0
        for _year in range(fromyear_2, toyear_2 + 1):
            df[f'temperature-{fromyear_2}-{toyear_2}'] += df[f'temperature-{_year}']
        df[f'temperature-{fromyear_2}-{toyear_2}'] /= (toyear_2 + 1 - fromyear_2)

        df[f'temperature-{fromyear_1}-{toyear_1}'] = 0
        for _year in range(fromyear_1, toyear_1 + 1):
            df[f'temperature-{fromyear_1}-{toyear_1}'] += df[f'temperature-{_year}']
        df[f'temperature-{fromyear_1}-{toyear_1}'] /= (toyear_1 + 1 - fromyear_1)

        df['rank_diff'] = (df[f'rank-{fromyear_2}-{toyear_2}'] - df[f'rank-{fromyear_1}-{toyear_1}'])
        df['temp_diff'] = (df[f'temperature-{fromyear_2}-{toyear_2}'] - df[f'temperature-{fromyear_1}-{toyear_1}'])
        df['diff'] = df['rank_diff'] * df['temp_diff']


        limits = [(0,float('inf')), (float('-inf'),0)]
        colors = ["royalblue","crimson","lightseagreen","orange","lightgrey"]


        fig = go.Figure()

        df_sub = df.loc[(df['rank_diff'] < 0) & (df['temp_diff'] < 0)]
        scale = 20 / df_sub['diff'].abs().max()
        fig.add_trace(go.Scattergeo(
            locationmode = 'USA-states',
            lon = df_sub['lon'],
            lat = df_sub['lat'],
            text = df_sub.index,
            marker = dict(
                size = df_sub['diff'].abs() * scale,
                color = colors[0],
                line_color='rgb(40,40,40)',
                line_width=0.5,
                sizemode = 'area'
            ),
            name = 'temp and rank both down'))

        df_sub = df.loc[(df['rank_diff'] < 0) & (df['temp_diff'] > 0)]
        fig.add_trace(go.Scattergeo(
            locationmode = 'USA-states',
            lon = df_sub['lon'],
            lat = df_sub['lat'],
            text = df_sub.index,
            marker = dict(
                size = df_sub['diff'].abs() * scale,
                color = colors[1],
                line_color='rgb(40,40,40)',
                line_width=0.5,
                sizemode = 'area'
            ),
            name = 'temp up and rank down'))

        df_sub = df.loc[(df['rank_diff'] > 0) & (df['temp_diff'] < 0)]
        fig.add_trace(go.Scattergeo(
            locationmode = 'USA-states',
            lon = df_sub['lon'],
            lat = df_sub['lat'],
            text = df_sub.index,
            marker = dict(
                size = df_sub['diff'].abs() * scale,
                color = colors[2],
                line_color='rgb(40,40,40)',
                line_width=0.5,
                sizemode = 'area'
            ),
            name = 'temp down and rank up'))

        df_sub = df.loc[(df['rank_diff'] > 0) & (df['temp_diff'] > 0)]
        fig.add_trace(go.Scattergeo(
            locationmode = 'USA-states',
            lon = df_sub['lon'],
            lat = df_sub['lat'],
            text = df_sub.index,
            marker = dict(
                size = df_sub['diff'].abs() * scale,
                color = colors[3],
                line_color='rgb(40,40,40)',
                line_width=0.5,
                sizemode = 'area'
            ),
            name = 'temp and rank up'))


        fig.update_layout(
                title_text = f'Comparison between {fromyear_1}-{toyear_1} and {fromyear_2}-{toyear_2}',
                showlegend = True,
                geo = dict(
                    scope = 'usa',
                    landcolor = 'rgb(217, 217, 217)',
                )
            )
        fig.layout.autosize = True
        plot.object = fig
    else:
        alert.visible = True
    
pbutton.on_click(b)

#pbutton.click() <--- I would put my trigger here
pbutton.clicks += 1


dash = pn.Column(title,
          pn.pane.Markdown("We explore the relationship between the change of temperature and the rank of different universities by csranking."),
          pn.Row(from_year_1, to_year_1),
        pn.Row(from_year_2, to_year_2),
        pbutton, alert, plot
         ).servable()
pn.serve(dash)

# pn.Column(pbutton, plot, other_button).servable()
