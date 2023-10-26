import json
from flask import Flask, request
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Set up logging
log_filename = 'emby-merge-version.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a handler for rotating log files daily
rotating_handler = TimedRotatingFileHandler(log_filename, when="midnight", interval=1, backupCount=7)
rotating_handler.setLevel(logging.INFO)
rotating_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Add the rotating handler to the logger
logging.getLogger().addHandler(rotating_handler)

# Emby server settings
EMBY_BASE_URL = os.environ["EMBY_BASE_URL"]
EMBY_API_KEY = os.environ["EMBY_API_KEY"]
HEADERS = {'accept': 'application/json', }


# Merge HD and UHD Movies
def merge_movies(item_id_1, item_id_2):
    url = f"{EMBY_BASE_URL}/emby/Videos/MergeVersions?Ids={item_id_1},{item_id_2}&api_key={EMBY_API_KEY}"
    response = requests.post(url, headers=HEADERS,)
    if response.status_code == 204:
        logging.info('Merge Successful')
        return 'Merge Successful'
    else:
        logging.error('Merge Unsuccessful')
        return 'Merge Unsuccessful'


def search_movies(prov_id):
    url = f"{EMBY_BASE_URL}/emby/Items?Recursive=true&AnyProviderIdEquals={prov_id}&api_key={EMBY_API_KEY}"
    response = requests.get(url)
    movie_ids = []
    for item in response.json()["Items"]:
        item_id = item["Id"]
        movie_ids.append(item_id)
    return movie_ids


@app.route('/emby-webhook', methods=['POST'])
def webhook_listener():
    data = json.loads(dict(request.form)['data'])
    # List of provider IDs to search with
    provider_ids_to_search = ['Tmdb', 'Imdb']
    movies = None
    # Search for movies using each provider ID until at least two movie IDs are found
    for provider_id in provider_ids_to_search:
        if 'ProviderIds' in data['Item'] and provider_id in data['Item']['ProviderIds']:
            prov_key = provider_id.lower()  # Convert the provider key to lowercase
            prov_value = data['Item']['ProviderIds'][provider_id]
            movies = search_movies(f"{prov_key}.{prov_value}")
            if len(movies) >= 2:
                break  # Stop searching if two or more movies are found

    if movies is not None and len(movies) == 2:
        movie_1, movie_2 = movies
        merger = merge_movies(movie_1, movie_2)
        return merger
    else:
        logging.info('No merge performed, not enough movie IDs were found')
        return 'No merge performed, not enough movie IDs were found'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
