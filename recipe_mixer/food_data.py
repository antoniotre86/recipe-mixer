'''
Created on 12/11/2021

@author: trentaa
'''
import requests
import json


class FoodData:
    measure_uris = {
        "gram": "http://www.edamam.com/ontologies/edamam.owl#Measure_gram",
        "ml": "http://www.edamam.com/ontologies/edamam.owl#Measure_milliliter",
        "tbsp": "http://www.edamam.com/ontologies/edamam.owl#Measure_tablespoon",
        "tsp": "http://www.edamam.com/ontologies/edamam.owl#Measure_teaspoon",
        "serving": "http://www.edamam.com/ontologies/edamam.owl#Measure_serving",
        "unit": "http://www.edamam.com/ontologies/edamam.owl#Measure_serving"
    }

    store = {}

    def __init__(self, app_id, api_key):
        self._app_id = app_id
        self._api_key = api_key

    def _request_post(self, url, json):
        request_id = url + str(json)
        if request_id in self.store:
            return self.store[request_id]
        else:
            resp = requests.post(url, json=json)
            self.store[request_id] = resp
            return resp

    def _request_get(self, url):
        request_id = url
        if request_id in self.store:
            return self.store[request_id]
        else:
            resp = requests.get(url)
            self.store[request_id] = resp
            return resp

    def get_nutrients_for_food(self, food_id, quantity, measure):
        request_url = f"https://api.edamam.com/api/food-database/v2/nutrients?app_id={self._app_id}&app_key={self._api_key}"
        request_data = {
            "ingredients": [
                {
                    "quantity": quantity,
                    "measureURI": self.measure_uris[measure],
                    "foodId": food_id
                }
            ]
        }
        return self._request_post(request_url, json=request_data).json()

    def get_food_ids_for_food_name(self, food_name, n_results=10):
        request_url = f"https://api.edamam.com/api/food-database/v2/parser?app_id={self._app_id}&app_key={self._api_key}&ingr={food_name}&nutrition-type=cooking"
        response = self._request_get(request_url).json()
        out = []
        if "parsed" in response and len(response["parsed"]) > 0:
            food_id_parsed = [r["food"]["foodId"] for r in response["parsed"]]
            food_name_parsed = [r["food"]["label"] for r in response["parsed"]]
            out += list(zip(food_id_parsed, food_name_parsed, ["parsed"] * len(food_id_parsed)))
        if "hints" in response and len(response["hints"]) > 0:
            food_id_hints = [r["food"]["foodId"] for r in response["hints"]]
            food_name_hints = [r["food"]["label"] for r in response["hints"]]
            out += list(zip(food_id_hints, food_name_hints, ["hints"] * len(food_id_hints)))
        return out[:n_results]
