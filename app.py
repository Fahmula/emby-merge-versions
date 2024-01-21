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


# set up requests session
def requests_session():
    session = requests.session()
    session.headers.update(
        {
            "accept": "application/json",
        }
    )
    return session


# Merge HD and UHD Movies
def merge_movies(item_id_1, item_id_2, movie_name_1, session):
    url = f"{EMBY_BASE_URL}/emby/Videos/MergeVersions?Ids={item_id_1},{item_id_2}&api_key={EMBY_API_KEY}"
    response = session.post(
        url,
    )
    if 200 <= response.status_code < 300:
        logging.info(f"Merge Successful for movie: {movie_name_1}")
        return f"Merge Successful for movie: {movie_name_1}"
    else:
        logging.error("Merge Unsuccessful")
        return "Merge Unsuccessful"


def search_movies(prov_id, session):
    url = f"{EMBY_BASE_URL}/emby/Items?Recursive=true&AnyProviderIdEquals={prov_id}&api_key={EMBY_API_KEY}"
    response = session.get(url)
    movies_data = []
    for item in response.json()["Items"]:
        item_id = item["Id"]
        item_name = item["Name"]
        movies_data.append({"id": item_id, "name": item_name})
    return movies_data


@app.route("/emby-webhook", methods=["POST"])
def webhook_listener():
    # start requests session
    session = requests_session()
    try:
        data = json.loads(dict(request.form)["data"])
    except KeyError:
        data = json.loads(request.data)

    # List of provider IDs to search with
    provider_id = "Tmdb"
    # Search for movies using provider ID
    if "ProviderIds" in data["Item"] and provider_id in data["Item"]["ProviderIds"]:
        prov_key = provider_id.lower()  # Convert the provider key to lowercase
        prov_value = data["Item"]["ProviderIds"][provider_id]
        movies = search_movies(f"{prov_key}.{prov_value}", session)
        movie_name = movies[0]["name"] if movies else "unknown"

    # merge movies
    if movies is not None and len(movies) == 2:
        movie_1, movie_2 = movies
        merger = merge_movies(movie_1["id"], movie_2["id"], movie_1["name"], session)
        session.close()
        return merger

    elif len(movies) > 2:
        logging.info(
            f"No merge performed for {movie_name}, more than two movie IDs were found"
        )
        session.close()
        return "No merge performed more than two movie IDs were found"

    else:
        logging.info(
            f"No merge performed for {movie_name}, not enough movie IDs were found"
        )
        session.close()
        return "No merge performed, not enough movie IDs were found"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
