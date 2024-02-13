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
log_filename = "emby-merge-version.log"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a handler for rotating log files daily
rotating_handler = TimedRotatingFileHandler(
    log_filename, when="midnight", interval=1, backupCount=7
)
rotating_handler.setLevel(logging.INFO)
rotating_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)

# Add the rotating handler to the logger
logging.getLogger().addHandler(rotating_handler)

# Emby server settings
EMBY_BASE_URL = os.environ["EMBY_BASE_URL"]
EMBY_API_KEY = os.environ["EMBY_API_KEY"]
IGNORE_LIBRARY = os.environ["IGNORE_LIBRARY"]


# set up requests session
session = requests.session()
session.headers.update(
    {
        "accept": "application/json",
    }
)


def check_ignore_list(item):
    ignore_list = [id.strip() for id in IGNORE_LIBRARY.split(",") if IGNORE_LIBRARY]
    return all(library not in item.get("Path") for library in ignore_list)


# Merge HD and UHD Movies
def merge_movies(item_id_1, item_id_2, movie_name_1):
    url = f"{EMBY_BASE_URL}/emby/Videos/MergeVersions?Ids={item_id_1},{item_id_2}&api_key={EMBY_API_KEY}"

    try:
        response = session.post(url)
        response.raise_for_status()
        logging.info(f"Merge Successful for movie: {movie_name_1}")
        return f"Merge Successful for movie: {movie_name_1}"
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while merging movies: {e}")
    return "An error occurred while merging movies"


def search_movies(prov_id):
    url = f"{EMBY_BASE_URL}/emby/Items?Recursive=true&Fields=Path&AnyProviderIdEquals={prov_id}&api_key={EMBY_API_KEY}"
    try:
        response = session.get(url)
        response.raise_for_status()
        movies_data = []
        for item in response.json()["Items"]:
            if item.get("Type") == "Movie" and check_ignore_list(item):
                item_id = item["Id"]
                item_name = item["Name"]
                movies_data.append({"id": item_id, "name": item_name})
        return movies_data

    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while searching for movies: {e}")
    return "An error occurred while searching for movies"


@app.route("/emby-webhook", methods=["POST"])
def webhook_listener():

    try:
        data = json.loads(dict(request.form)["data"])
    except KeyError:
        data = json.loads(request.data)

    provider_id = "Tmdb"
    movies = []

    # Search for movies using provider ID until at least two movie IDs are found
    if "ProviderIds" in data["Item"] and provider_id in data["Item"]["ProviderIds"]:
        prov_key = provider_id.lower()  # Convert the provider key to lowercase
        prov_value = data["Item"]["ProviderIds"][provider_id]
        movies = search_movies(f"{prov_key}.{prov_value}")

    movie_name = movies[0]["name"] if movies else "unknown"

    # merge movies
    if movies is not None and len(movies) == 2:
        movie_1, movie_2 = movies
        merger = merge_movies(movie_1["id"], movie_2["id"], movie_1["name"])
        return merger

    elif movies is not None and len(movies) > 2:
        logging.info(
            f"No merge performed for {movie_name}, more than two movies were found"
        )
        return "No merge performed, more than two movies were found"

    else:
        logging.info(
            f"No merge performed for {movie_name}, not enough movie IDs were found"
        )
        return "No merge performed, not enough movie IDs were found"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
