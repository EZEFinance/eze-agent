import os
import orjson
import requests
from dotenv import load_dotenv
load_dotenv()

DEFILLAMA_API = os.getenv("DEFILLAMA_API")

class YieldDataFetcher:
    def __init__(self, url):
        self.url = url
        self.data = None
        self.filtered_data = None

    def fetch_data(self):
        response = requests.get(self.url)
        if response.status_code == 200:
            self.data = orjson.loads(response.content)
        else:
            raise Exception(f"Failed to fetch data, status code: {response.status_code}")

    def filter_data(self):
        if self.data is None:
            raise ValueError("Data is not fetched yet. Please call fetch_data() first.")
        
        self.filtered_data = [{
            "chain": item["chain"],
            "project": item["project"],
            "symbol": item["symbol"],
            "tvlUsd": item["tvlUsd"],
            "apyBase": item["apyBase"],
            "stablecoin": item["stablecoin"]
        } for item in self.data['data']
          if item["chain"] == "Base" 
          and item["apyBase"] is not None 
          and item["apyBase"] != 0
          and "-" not in item["symbol"]
        ]

    def save_data(self, filename="result.json"):
        if self.filtered_data is None:
            raise ValueError("Data is not filtered yet. Please call filter_data() first.")
        
        with open(filename, "wb") as f:
            f.write(orjson.dumps(self.filtered_data, option=orjson.OPT_INDENT_2))

if __name__ == "__main__":
    fetcher = YieldDataFetcher(DEFILLAMA_API)

    try:
        fetcher.fetch_data()
        fetcher.filter_data()
        fetcher.save_data("model/knowledge.json")
        print("Data successfully fetched, filtered, and saved.")
    except Exception as e:
        print(f"An error occurred: {e}")
