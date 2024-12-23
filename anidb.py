# Download the anime title list

import requests
from log import logprint

ANIME_DATA_URL = "https://raw.githubusercontent.com/c032/anidb-animetitles-archive/refs/heads/main/data/animetitles.json"
ANIME_DATA_PATH = "./anime-titles.json"

def can_download_titles():
		return True

def update_title_cache():
	if can_download_titles():
		logprint("[anidb.py] [INFO] Updating cached anime-titles.json")

		response = requests.get(ANIME_DATA_URL)
		if response.status_code != 200:
			logprint("[anidb.py] [INFO] Failed to get file. Using cached anime-titles.json")
			return
		
		converted_json = "[" + ",\n".join(response.text.splitlines()) + "]"
		json_file = open(ANIME_DATA_PATH, "wb")
		json_file.write(converted_json.encode('utf-8'))
		json_file.close()
	else:
		logprint("[anidb.py] [INFO] Using cached anime-titles.json")
