'''
Created on 12/11/2021

@author: trentaa
'''
import json
import logging
import os

import dash
from dash import dcc, html
import pandas as pd
from dash.dependencies import Input, Output, State
from dotenv import load_dotenv

from recipe_mixer.food_data import FoodData

app = dash.Dash(__name__)


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Dash app")


# Initialise food data API client
load_dotenv()
api_key = os.getenv("API_KEY")
app_id = os.getenv("APP_ID")
fd = FoodData(api_key=api_key, app_id=app_id)

measure_options = [{"label": m, "value": m} for m in fd.measure_uris.keys()]


def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


# Divs

def div_search_ingredient_box():
    return html.Div(
        id="search-ingredient-box",
        className="search-ingredient-box",
        children=[
            html.Div(
                children=[
                    dcc.Input(id="ingredient-name", value="", type="text", debounce=True,
                              placeholder="Ingredient Name"),
                    html.Button(id="search-ingredient-button", n_clicks=0, children="Search"),
                ],
                style={"display": "flex", "width": "100%"}
            ),
            dcc.Dropdown(id="ingredient-input", searchable=False, style={"width": "100%"}),
            # html.Div(
            #     children=[
            #         dcc.Dropdown(id="ingredient-measure", options=measure_options, value="gram", searchable=False,
            #                      clearable=False, style={"width": "100px"}),
            #         dcc.Input(id="ingredient-quantity", value=1, min=0, type="number",
            #                   placeholder="Ingredient quantity in grams", style={"width": "100px"}),
            #     ],
            #     style={"display": "flex", "width": "200px"}
            # ),
            html.Button(id="add-ingredient-button", n_clicks=0, children="Add ingredient")
        ]
    )


def div_ingredient_list_entry(food_id, food_name):
    return html.Div(
        id=f"ingredient-list-entry-{food_id}",
        className="ingredient-list",
        children=[
            html.P(food_name),
            dcc.Dropdown(id="ingredient-measure", options=measure_options, value="gram", searchable=False,
                         clearable=False, style={"width": "100px"}),
            dcc.Input(id="ingredient-quantity", value=1, min=0, type="number",
                      placeholder="Ingredient quantity in grams", style={"width": "100px"})
        ],
        style={"display": "flex", "width": "200px"}
    )


# Callbacks

@app.callback(
    Output("food-names-store", "data"),
    Input("search-ingredient-button", "n_clicks"),
    State("ingredient-name", "value"),
    prevent_initial_call=True
)
def search_ingredient(_, ingredient_name):
    if ingredient_name != "":
        ingredient_search_results = fd.get_food_ids_for_food_name(ingredient_name)
    else:
        ingredient_search_results = {}
    return json.dumps(ingredient_search_results)


@app.callback(
    Output("ingredient-input", "options"),
    Output("ingredient-input", "placeholder"),
    Input("food-names-store", "data"),
    prevent_initial_call=True
)
def update_ingredient_name_dropdown(ingredient_search_results):
    ingredient_search_results = json.loads(ingredient_search_results)
    if len(ingredient_search_results) > 0:
        options = [{"label": i_name, "value": i_id} for i_id, i_name, _ in ingredient_search_results]
    else:
        options = []
    return options, options[0]["label"]


@app.callback(
    Output("food-data-store", "data"),
    Input("add-ingredient-button", "n_clicks"),
    State("ingredient-input", "value"),
    State("food-data-store", "data"),
    prevent_initial_call=True
)
def get_ingredient_data(_, ingredient_id, ingredient_nutrition_data_json):
    ingredient_nutrition_data = json.loads(ingredient_nutrition_data_json or "[]")
    if ingredient_id != "":
        food_data = fd.get_nutrients_for_food(ingredient_id, 1, "gram")
        ingredient_nutrition_data += [(ingredient_id, food_data)]
    return json.dumps(ingredient_nutrition_data)


@app.callback(
    Output("ingredient-nutrition", "children"),
    Input("food-data-store", "data"),
    Input("ingredient-quantity", "value"),
    prevent_initial_call=True
)
def render_ingredient_nutrition_table(ingredient_nutrition_data_json, ingredient_quantity):
    ingredient_nutrition_data = json.loads(ingredient_nutrition_data_json or "[]")
    q = ingredient_quantity or 0
    ingredient_nutrition_df = pd.DataFrame()
    for i_id, i_data in ingredient_nutrition_data:
        ingredient_nutrition_df = ingredient_nutrition_df.append(
            pd.Series({
                "Ingredient": i_data["ingredients"][0]["parsed"][0]["food"],
                "KCal": i_data["calories"]*q,
                "Carb": (i_data["totalNutrients"]["CHOCDF"]["quantity"]*q if "CHOCDF" in i_data["totalNutrients"] else 0),
                "Fat": (i_data["totalNutrients"]["FAT"]["quantity"]*q if "FAT" in i_data["totalNutrients"] else 0),
                "Protein": (i_data["totalNutrients"]["PROCNT"]["quantity"]*q if "PROCNT" in i_data["totalNutrients"] else 0)
            }),
            ignore_index=True
        )
    total_df = ingredient_nutrition_df.sum(0)
    total_df["Ingredient"] = "-- Total"
    ingredient_nutrition_df = ingredient_nutrition_df.append(total_df, ignore_index=True)
    return generate_table(ingredient_nutrition_df.round(2))


@app.callback(
    Output("ingredient-list", "children"),
    Input("food-data-store", "data"),
    prevent_initial_call=True
)
def render_ingredient_list(ingredient_nutrition_data_json):
    ingredient_nutrition_data = json.loads(ingredient_nutrition_data_json or "[]")
    ingredient_list_data = [div_ingredient_list_entry(i_id, i_data["ingredients"][0]["parsed"][0]["food"])
                            for i_id, i_data in ingredient_nutrition_data]
    return ingredient_list_data


# App

app.layout = html.Div(
    id="app-container",

    children=[
        # Food data
        dcc.Store(id="food-data-store"),
        dcc.Store(id="food-names-store"),
        dcc.Store(id="ingredient-list-store"),

        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[html.Img(src=app.get_asset_url("plotly_logo.png"))]
        ),

        # Left column
        html.Div(
            id="left-column",
            className="four columns",
            children=[
                html.H1("Ingredient input"),
                div_search_ingredient_box(),
                html.H2("Ingredient list"),
                html.Div(
                    id="ingredient-list",
                    className="ingredient-list"
                )
            ]
        ),

        # Right column
        html.Div(
            id="right-column",
            className="eight columns",
            children=[
                html.H1("Your recipe nutritional information"),
                html.Div(id="ingredient-nutrition")
            ]
        )

    ]
)


if __name__ == '__main__':
    app.run_server(debug=True)




