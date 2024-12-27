
# Download series opening and endings

from pathlib import Path

import ffmpeg
import args
import requests
import urllib.parse
from tqdm import tqdm

from utils import logprint

def download_themes(name: str, anidb_id: int|str, to_download: list[str]) -> list[dict]:
	themes = get_themes(name, anidb_id)
	themes_list = []

	for theme in themes:
		theme_type: str = theme["type"]
		theme_url: str = theme["animethemeentries"][0]["videos"][0]["audio"]["link"]
		file_name: str = theme_url.rsplit('/', 1)[1]
		
		theme_folder = None

		if "OP" in theme_type:
			if "op" not in to_download:
				continue
			theme_folder = "./openings"
		elif "ED" in theme_type:
			if "ed" not in to_download:
				continue
			theme_folder = "./endings"
		else:
			continue

		audio_path = f"{theme_folder}/{file_name}"

		if Path.exists(Path(audio_path).with_suffix('.mp3')):
			audio_path = Path(audio_path).with_suffix('.mp3')
		if Path.exists(Path(audio_path)):
			print(f"[animethemesmoe.py] [INFO] {file_name} has already been downloaded. Skipping")

			info: dict = ffmpeg.probe(audio_path)
			duration = info.get('format',{}).get('duration') or info.get('streams',[{}])[0].get('duration')

			themes_list.append({
				"file_path": str(audio_path),
				"duration": float(duration),
				"type": theme_type
			})
			continue

		headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4521.0 Safari/537.36 Edg/93.0.910.5"}
		response = requests.get(theme_url, allow_redirects=True, headers=headers, stream=True)

		if "audio" not in response.headers["Content-Type"]:
			logprint(f"[animethemesmoe.py] [WARNING] Theme {file_name} has no audio content-type! Skipping")
			continue

		if response.status_code != 200:
			logprint(f"[animethemesmoe.py] [WARNING] Theme {file_name} not reachable! (status code {response.status_code})")
			continue
		
		audio_file = open(audio_path, "wb")

		if args.parsed_args.verbose:
			content_length = int(response.headers["content-length"] or 0)
			progress_bar = tqdm(total=content_length, unit='iB', unit_scale=True)
			progress_bar.set_description(f"[animethemesmoe.py] [INFO] Downloading {file_name}")
		

		for chunk in response.iter_content(chunk_size=1024*1024):
			if args.parsed_args.verbose:
				progress_bar.update(len(chunk))

			audio_file.write(chunk)

		if args.parsed_args.verbose:
			progress_bar.close()

		audio_file.close()

		info: dict = ffmpeg.probe(audio_path)
		duration = info.get('format',{}).get('duration') or info.get('streams',[{}])[0].get('duration')

		themes_list.append({
			"file_path": audio_path,
			"duration": float(duration),
			"type": theme_type
		})
	
	return themes_list


def get_themes(name, anidb_id):
	response = requests.get(f"https://api.animethemes.moe/anime?include=resources,animethemes,animethemes.animethemeentries.videos.audio&q={urllib.parse.quote(name, safe='')}")
	
	if response.headers["Content-Type"] != "application/json":
		return []
	
	if len(response.json()["anime"]) == 0:
		return []

	anime_list = response.json()["anime"]

	themes = []
	for anime in anime_list:
		external_anidb_id = [resource['external_id'] for resource in anime['resources'] if resource['site'] == 'aniDB']
		if len(external_anidb_id) == 0 or external_anidb_id[0] != int(anidb_id):
			continue
		themes = anime['animethemes']
	
	logprint(f"[animethemesmoe.py] [INFO] Found {len(themes)} themes for {name}")
	
	return themes
