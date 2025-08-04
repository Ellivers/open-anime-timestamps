# Download the anime title list

import os
import time
import requests
import json
from utils import logprint

URL = "https://raw.githubusercontent.com/manami-project/anime-offline-database/master/anime-offline-database.json"
PATH = "./anime-offline-database-processed.json"

def update_id_database():
	if not can_download():
		logprint("[anime_offline_database.py] [INFO] Using cached anime-offline-database-processed.json")
		return
	
	logprint("[anime_offline_database.py] [INFO] Updating cached anime-offline-database-processed.json")

	response = requests.get(URL)
	data = response.json()["data"]

	id_database = []


	logprint("[anime_offline_database.py] [INFO] Creating anime ID relations")

	for anime in data:
		relation = {
			"anilist": None,
			"anidb": None,
			"myanimelist": None,
			"kitsu": None
		}

		for source in anime["sources"]:
			anime_id = source.split("/")[-1]

			if "anilist.co" in source:
				relation["anilist"] = int(anime_id)

			if "anidb.net" in source:
				relation["anidb"] = int(anime_id)

			if "myanimelist.net" in source:
				relation["myanimelist"] = int(anime_id)

			if "kitsu.app" in source:
				relation["kitsu"] = int(anime_id)

		if all(value == None for value in relation.values()):

			logprint(f"[anime_offline_database.py] [WARNING] No relations found for {anime['title']}")
			continue

		id_database.append(relation)

	logprint("[anime_offline_database.py] [INFO] Saving processed relations")
	
	local_database_file = open(PATH, "w")
	local_database_file.seek(0)
	json.dump(id_database, local_database_file, indent=4)
	local_database_file.close()

def can_download() -> bool:
	if os.path.isfile(PATH) and os.access(PATH, os.R_OK):
		# Only update the file once every 5 hours
		update_time = os.path.getmtime(PATH)
		return ((time.time() - update_time) > (3600 * 5))
	else:
		return True

def convert_anime_id(anime_id: str|int, id_from: str, id_to: str) -> int:
	local_database_file = open(PATH, "r")
	local_database = json.load(local_database_file)

	for entry in local_database:
		if entry[id_from] == int(anime_id):
			local_database_file.close()
			return entry[id_to]

	local_database_file.close()