import json
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from flask import Flask, request
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask application
app = Flask(__name__)

# Set up logging
log_filename = "emby-merge-version.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
rotating_handler = TimedRotatingFileHandler(
    log_filename, when="midnight", interval=1, backupCount=7
)
rotating_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logging.getLogger().addHandler(rotating_handler)

# Emby server settings
EMBY_BASE_URL = os.environ.get("EMBY_BASE_URL")
EMBY_API_KEY = os.environ.get("EMBY_API_KEY")
IGNORE_LIBRARY = os.environ.get("IGNORE_LIBRARY", "")
MERGE_ON_START = os.environ.get("MERGE_ON_START", "").lower() == "yes"

# Requests session
session = requests.Session()
session.headers.update({"accept": "application/json"})

# Helper Functions
def check_ignore_list(item):
    """Check if the item should be ignored based on the ignore library list."""
    ignore_list = [id.strip() for id in IGNORE_LIBRARY.split(",") if id.strip()]
    return all(library not in item.get("Path", "") for library in ignore_list)

def merge_movies(movies):
    """Merge movies based on their IDs."""
    for movie, movie_ids in movies.items():
        if len(movie_ids) == 2:
            params = {"Ids": movie_ids, "api_key": EMBY_API_KEY}
            try:
                response = session.post(f"{EMBY_BASE_URL}/emby/Videos/MergeVersions", params=params)
                response.raise_for_status()
                logging.info(f"Merge successful for movie: {movie}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error merging movies: {e}")
        elif len(movie_ids) > 2:
            logging.info(f"More than two movies found for {movie}, no merge performed.")
        else:
            logging.info(f"Not enough movie IDs found for {movie}, no merge performed.")

def search_movies(prov_id=None):
    """Search for movies, optionally filtered by provider ID."""
    params = {
        "Recursive": "true",
        "Fields": "ProviderIds, Path",
        "IncludeItemTypes": "Movie",
        "api_key": EMBY_API_KEY,
    }
    if prov_id:
        params["AnyProviderIdEquals"] = prov_id

    try:
        response = session.get(f"{EMBY_BASE_URL}/emby/Items", params=params)
        response.raise_for_status()
        movies_data = {}
        for item in response.json().get("Items", []):
            if check_ignore_list(item):
                item_id = item["Id"]
                item_name = item["Name"]
                movies_data.setdefault(item_name, []).append(item_id)
        return movies_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Error searching for movies: {e}")
        return {}

def merge_on_start():
    """Perform merging of movies at application start."""
    movies = search_movies()
    if movies:
        merge_movies(movies)

# Route Definitions
@app.route("/webhook", methods=["POST"])
def webhook_listener():
    """Handle incoming webhook requests."""
    try:
        data = json.loads(request.form.get("data") or request.data)
    except (KeyError, json.JSONDecodeError):
        logging.error("Invalid data received in webhook.")
        return "Invalid data", 400

    provider_id = "Tmdb"
    if "ProviderIds" in data.get("Item", {}) and provider_id in data["Item"]["ProviderIds"]:
        prov_key = provider_id.lower()
        prov_value = data["Item"]["ProviderIds"][provider_id]
        movies = search_movies(f"{prov_key}.{prov_value}")
        if movies:
            merge_movies(movies)

    return "Success", 200

if MERGE_ON_START:
    merge_on_start()

# Application Startup
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
