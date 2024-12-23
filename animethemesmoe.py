
# Download series opening and endings

import os.path
import args
import requests
import urllib.parse
import re
from tqdm import tqdm
from difflib import SequenceMatcher

def download_themes(name: str):
	themes = get_themes(name)
	themes_list = []

	for theme in themes:
		theme_type: str = theme["type"]
		theme_url: str = theme["animethemeentries"][0]["videos"][0]["audio"]["link"]
		file_name: str = theme_url.rsplit('/', 1)[1]
		
		theme_folder = None

		if "OP" in theme_type:
			theme_folder = "./openings"
		elif "ED" in theme_type:
			theme_folder = "./endings"

		audio_path = f"{theme_folder}/{file_name}"
		
		similar_enough = SequenceMatcher(None, re.sub('\-(ED|OP)\d?\.\w+$','', file_name), name.replace(' ','')).ratio() > 0.75
		if os.path.exists(audio_path):
			print(f"[themes.moe] [INFO] {file_name} has already been downloaded. Skipping")
			if similar_enough:
				themes_list.append(audio_path)
			continue

		headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4521.0 Safari/537.36 Edg/93.0.910.5"}
		response = requests.get(theme_url, allow_redirects=True, headers=headers, stream=True)

		if "audio" not in response.headers["Content-Type"]:
			if args.parsed_args.verbose:
				print(f"[themes.moe] [WARNING] Theme {file_name} has no audio content-type! Skipping")
			continue

		if response.status_code != 200:
			if args.parsed_args.verbose:
				print(f"[themesmoe.py] [WARNING] Theme {file_name} not reachable! (status code {response.status_code})")
			continue
		
		audio_file = open(audio_path, "wb")

		if args.parsed_args.verbose:
			content_length = int(response.headers["content-length"] or 0)
			progress_bar = tqdm(total=content_length, unit='iB', unit_scale=True)
			progress_bar.set_description(f"[themesmoe.py] [INFO] Downloading {file_name}")
		

		for chunk in response.iter_content(chunk_size=1024*1024):
			if args.parsed_args.verbose:
				progress_bar.update(len(chunk))

			audio_file.write(chunk)

		if args.parsed_args.verbose:
			progress_bar.close()

		audio_file.close()
		if similar_enough:
			themes_list.append(audio_path)
	
	return themes_list


def get_themes(name):
	response = requests.get(f"https://api.animethemes.moe/search?fields%5Bsearch%5D=animethemes&include%5Banimetheme%5D=animethemeentries.videos.audio&q={urllib.parse.quote(name, safe='')}")
	
	if response.headers["Content-Type"] != "application/json":
		return []
	
	if len(response.json()["search"]) == 0:
		return []

	data = response.json()["search"]
	themes = data["animethemes"]
	
	if args.parsed_args.verbose:
		print(f"[themesmoe.py] [INFO] Found {len(themes)} themes for {name}")
	
	return themes
