# Download the anime title list

import requests
import args

ANIME_DATA_URL = "https://raw.githubusercontent.com/c032/anidb-animetitles-archive/refs/heads/main/data/animetitles.json"
ANIME_DATA_PATH = "./anime-titles.json"

def can_download_titles():
		return True

def update_title_cache():
	if can_download_titles():
		if args.parsed_args.verbose:
			print("[anidb.py] [INFO] Updating cached anime-titles.json")

		response = requests.get(ANIME_DATA_URL)
		if response.status_code != 200:
			if args.parsed_args.verbose:
				print("[anidb.py] [INFO] Failed to get file. Using cached anime-titles.json")
				return
		
		converted_json = "[" + ",\n".join(response.text.splitlines()) + "]"
		json_file = open(ANIME_DATA_PATH, "wb")
		json_file.write(converted_json.encode('utf-8'))
		json_file.close()
	else:
		if args.parsed_args.verbose:
			print("[anidb.py] [INFO] Using cached anime-titles.json")
