# Download the anime title list

import os
import time
import requests
import json
from tqdm import tqdm
import anime_offline_database
from utils import is_not_silent, logprint, get_timestamp_template, merge_timestamps

URL = "https://raw.githubusercontent.com/aniskip/sanitize_db_dump/refs/heads/main/skip_times_public.csv"
PATH = "./aniskip-database.csv"

def process():
	if can_download():
		logprint("[aniskip.py] [INFO] Updating cached aniskip-database.csv")
		response = requests.get(URL)
		file = open(PATH, 'w')
		file.write(response.text)
		file.close()
	else:
		logprint("[aniskip.py] [INFO] Using cached aniskip-database.csv")

	file = open(PATH, 'r')
	lines = file.readlines()

	skips = []
	couldnt_convert = []

	if is_not_silent():
		progress_bar = tqdm(range(1, len(lines)))
		progress_bar.set_description("[aniskip.py] [INFO] Parsing aniskip database")
	else:
		progress_bar = range(1, len(lines))

	for i in progress_bar:
		line = lines[i].split(',')
		mal_id = line[0]
		anidb_id = anime_offline_database.convert_anime_id(mal_id, "myanimelist", "anidb")
		if not anidb_id:
			couldnt_convert.append(mal_id)
			continue
		skip_obj = {
			"anidb_id": anidb_id,
			"episode": float(line[1]),
			"skip_type": line[3],
			"votes": int(line[4]),
			"timestamp": {
				"start": int(float(line[5])),
				"end": int(float(line[6]))
			}
		}
		discard = False
		remove_indices = []
		for i in range(len(skips)):
			compare_skip = skips[i]
			if not (compare_skip['anidb_id'] == anidb_id and compare_skip['episode'] == skip_obj["episode"] and compare_skip['skip_type'] == skip_obj["skip_type"]):
				continue
			if compare_skip['votes'] >= skip_obj["votes"]:
				discard = True
				break
			else:
				remove_indices.append(i)
		for i in remove_indices:
			skips.pop(i)

		if discard:
			continue
		skips.append(skip_obj)

	for mal_id in couldnt_convert:
		logprint(f"[aniskip.py] [WARNING] Couldn't convert MAL ID {mal_id}")

	local_database_file = open("timestamps.json", "r")
	local_database: dict = json.load(local_database_file)
	local_database_file.close()

	logprint("[aniskip.py] [INFO] Adding aniskip timestamps to database")

	for skip in skips:
		anidb_id = skip['anidb_id']
		if anidb_id not in local_database:
			local_database[anidb_id] = []
		series = local_database[anidb_id]

		timestamp_data = get_timestamp_template(skip["episode"], "aniskip")
		timestamp_type = skip['skip_type']
		if timestamp_type in ['op','mixed-op']:
			timestamp_data["opening"] = skip['timestamp']
		if timestamp_type in ['ed','mixed-ed']:
			timestamp_data["ending"] = skip['timestamp']
		if timestamp_type == 'recap':
			timestamp_data["recap"] = skip['timestamp']

		existing_indices = [i for i in range(len(series)) if series[i]["episode_number"] == skip['episode']]
		if len(existing_indices) > 0:
			series[existing_indices[0]] = merge_timestamps(timestamp_data, series[existing_indices[0]])
		else:
			series.append(timestamp_data)

	local_database_file = open("timestamps.json",'w')
	json.dump(local_database, local_database_file, indent=4)
	local_database_file.close()

def can_download() -> bool:
	if os.path.isfile(PATH) and os.access(PATH, os.R_OK):
		# Only update the file once every 5 hours
		update_time = os.path.getmtime(PATH)
		return ((time.time() - update_time) > (3600 * 5))
	else:
		return True
