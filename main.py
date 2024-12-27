import os
import json
from pathlib import Path
from pydub import AudioSegment
import args
import re
import anime_skip
import anidb
import anime_offline_database
import kitsu
import animethemesmoe
#import animixplay
#import twistmoe
import animepahe
import fingerprint
import chapters
import math
from utils import logprint, get_timestamp_template, merge_timestamps

Path("./openings").mkdir(exist_ok=True)
Path("./endings").mkdir(exist_ok=True)
Path("./episodes").mkdir(exist_ok=True)

MULTIPLE_EPISODE_REGEX = re.compile(r'^(\d+)\-(\d+)$')

def main():
	# Create JSON database if not exists
	if not os.path.exists("timestamps.json"):
		with open("timestamps.json", "w") as f:
			json.dump({}, f)
			f.close()

	local_database_file = open("timestamps.json", "r+")
	local_database = json.load(local_database_file)

	if args.parsed_args.combine_database:
		path = args.parsed_args.combine_database
		if not os.path.exists(path):
			print(f"[main.py] [ERROR] Could not find file {path}")
			return
		file = open(path)
		try:
			import_db_file = json.load(file)
		except json.decoder.JSONDecodeError:
			print("[main.py] [ERROR] Inputted file is not a valid JSON file")
			return
		
		if type(import_db_file) is not dict:
			print("[main.py] [ERROR] Inputted file is not a JSON dict")
			return
		
		for key, value in list(dict.items(import_db_file)):
			if not key.isdigit():
				continue
			if type(value) is not list:
				continue
			if key not in local_database:
				local_database[key] = []
			series = local_database[key]
			for ep in value:
				episode_number = ep.get('episode_number')
				if not episode_number:
					continue
				indices = [i for i in range(len(series)) if float(series[i]['episode_number']) == float(episode_number)]
				if len(indices) == 0:
					series.append(merge_timestamps(ep, get_timestamp_template(episode_number)))
				else:
					series[indices[0]] = merge_timestamps(ep, series[indices[0]])
		
		local_database_file.seek(0)
		json.dump(local_database, local_database_file, indent=4)
		local_database_file.truncate()
		local_database_file.close()

		return
	
	# Update the anime titles cache
	anidb.update_title_cache()

	# Update anime ID db
	anime_offline_database.update_id_database()

	anime_titles_json = open("anime-titles.json", 'rb+')
	anime_titles = json.load(anime_titles_json)

	# Pull timestamps from other databases first
	if not args.parsed_args.skip_aggregation:
		start_index = 0
		if args.parsed_args.aggregation_start != None:
			start_index = next((i for i, anime in enumerate(anime_titles) if int(anime["id"]) == args.parsed_args.aggregation_start), 0)
		
		logprint(f"[main.py] [INFO] Finding timestamps using anime-skip")

		for anime in anime_titles[start_index:]:
			anidb_id = str(anime["id"])
			anilist_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "anilist")
			
			if not anilist_id:
				continue

			episodes = anime_skip.find_episodes_by_external_id(str(anilist_id))

			if anidb_id not in local_database:
				local_database[anidb_id] = []

			series = local_database[anidb_id]

			if episodes is None or len(series) == len(episodes):
				continue

			logprint(f"[main.py] [INFO] Found anime-skip timestamps for series with ID {anidb_id}")
			
			for episode in episodes:
				if episode["number"] is None:
						continue
				if len(episode['timestamps']) == 0:
						continue
				
				try:
					episode_number = float(episode["number"])
				except Exception:
					logprint(f"[main.py] [WARNING] Got invalid episode number {episode['number']}")
					continue
				
				if not any(e['episode_number'] == episode_number for e in series):
					#bettervrv_episode_timestamps = bettervrv.find_episode_by_name(episode["attributes"]["canonicalTitle"])
					
					timestamp_data = anime_skip.parse_timestamps(episode["timestamps"], episode_number)

					"""
					elif bettervrv_episode_timestamps:
						timestamp_data["source"] = "bettervrv"

						if "introStart" in bettervrv_episode_timestamps:
							timestamp_data["opening"]["start"] = int(bettervrv_episode_timestamps["introStart"])

							if "introEnd" in bettervrv_episode_timestamps:
								timestamp_data["opening"]["end"] = int(bettervrv_episode_timestamps["introEnd"])

						if "outroStart" in bettervrv_episode_timestamps:
							timestamp_data["ending"]["start"] = int(bettervrv_episode_timestamps["outroStart"])
							
							if "outroEnd" in bettervrv_episode_timestamps:
								timestamp_data["ending"]["end"] = int(bettervrv_episode_timestamps["outroEnd"])

						if "previewStart" in bettervrv_episode_timestamps:
							timestamp_data["preview_start"] = int(bettervrv_episode_timestamps["previewStart"])

						# BetterVRV also has a "postSceneEnd" timestamp, not sure what it does though. Not tracked
					"""

					if timestamp_data["recap"]["start"] == -1 and timestamp_data["opening"]["start"] == -1 and timestamp_data["ending"]["start"] == -1 and timestamp_data["preview_start"] == -1:
						continue

					"""
					existing_indices = [i for i in range(len(series)) if series[i]["episode_number"] == timestamp_data["episode_number"]]
					if len(existing_indices) > 0:
						if len(existing_indices) > 1:
							logprint(f"[main.py] [WARNING] Anime with ID {anidb_id} has duplicates of episode {timestamp_data['episode_number']}")
						series[existing_indices[0]] = timestamp_data
					else:
						series.append(timestamp_data)
					"""
					series.append(timestamp_data)

			local_database_file.seek(0)
			json.dump(local_database, local_database_file, indent=4)
			local_database_file.truncate()

	local_database_file.close()

	# Scrape other timestamps
	start_index = 0
	if args.parsed_args.scrape_start != None:
		start_index = next((i for i, anime in enumerate(anime_titles) if int(anime["id"]) == args.parsed_args.scrape_start), 0)

	for anime in anime_titles[start_index:]:
		anidb_id = anime["id"]
		kitsu_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "kitsu")

		if not kitsu_id:
			logprint(f"[main.py] [WARNING] {anidb_id} AniDB ID has no Kitsu ID! Skipping")
			continue

		kitsu_details = kitsu.details(kitsu_id)

		# animethemes and animepahe use two different main title formats
		kitsu_title = kitsu_details["data"]["attributes"]["canonicalTitle"]
		episode_count = kitsu_details['data']['attributes']['episodeCount']

		if anidb_id not in local_database:
			local_database[anidb_id] = []

		series = local_database[anidb_id]

		requirements = []
		for ep in series:
			requirements.append({
				"episode_number": ep['episode_number'],
				"op": ep['opening']['start'] == -1 or ep['opening']['end'] == -1,
				"ed": ep['ending']['start'] == -1 or ep['ending']['end'] == -1
			})

		# Check if op/ed timestamps are already defined
		themes_to_download = []
		if not episode_count or episode_count > len(series):
			themes_to_download = ['op','ed']
		else:
			if any(e['op'] for e in requirements):
				themes_to_download.append('op')
			if any(e['ed'] for e in requirements):
				themes_to_download.append('ed')

		if len(themes_to_download) == 0:
			logprint(f"[main.py] [INFO] \"{kitsu_title}\" with ID {anidb_id} doesn't require fingerprinting. Skipping")
			continue
		
		pahe_session = animepahe.get_anime_session(kitsu_title, anidb_id)
		if not pahe_session:
			continue

		jp_title = None
		titles = anime["titles"]
		title_reults = [title for title in titles if title["type"] == "main"]
		if len(title_reults) > 0:
			jp_title = title_reults[0]["title"]
		else:
			jp_title = titles[0]

		themes = animethemesmoe.download_themes(jp_title, anidb_id, themes_to_download)

		if len(themes) == 0:
			logprint(f"[main.py] [WARNING] \"{kitsu_title}\" provided no themes! Skipping")
			continue

		# Make sure that existing timestamps for this series have ends marked
		if len(series) > 0 and \
			any((ep['opening']['start'] != -1 and ep['opening']['end'] == -1) or (ep['ending']['start'] != -1 and ep['ending']['end'] == -1) for ep in series):

			openings = [t for t in themes if "OP" in t['type']]
			endings = [t for t in themes if "ED" in t['type']]

			# All OPs and EDs have to have the same duration
			# This is because multiple durations would make the timestamp data inaccurate
			op_duration = -1
			ed_duration = -1
			if all(round(t['duration']) == round(openings[0]['duration']) for t in openings):
				op_duration = math.floor(openings[0]['duration'])
			if all(round(t['duration']) == round(endings[0]['duration']) for t in endings):
				ed_duration = math.floor(endings[0]['duration'])
			
			for ep in series:
				start = ep['opening']['start']
				if op_duration != -1 and start != -1 and ep['opening']['end'] == -1:
					ep['opening']['end'] = start + op_duration
					continue

				start = ep['ending']['start']
				if ed_duration != -1 and start != -1 and ep['ending']['end'] == -1:
					ep['ending']['end'] = start + ed_duration
					continue

		for theme in themes:
			file_path = Path(theme["file_path"])

			if file_path.suffix == '.mp3':
				continue

			mp3_path = Path(file_path).with_suffix(".mp3")

			if not os.path.exists(file_path) and os.path.exists(mp3_path):
				continue

			logprint(f"[main.py] [INFO] Converting {file_path} to {mp3_path}")

			AudioSegment.from_file(file_path).export(mp3_path, format="mp3")
			os.remove(file_path)
			theme["file_path"] = mp3_path

		total_episodes = animepahe.get_episode_list(pahe_session)

		episode_index = 0
		while episode_index != None:
			episodes, next_index = animepahe.download_episodes(pahe_session, total_episodes, requirements, episode_index)

			for episode in episodes:
				video_path = episode["video_path"]

				mp3_path = Path(video_path).with_suffix(".mp3")
				episode["mp3_path"] = mp3_path

				if not os.path.exists(video_path) and os.path.exists(mp3_path):
					continue

				# Attempt parse any chapters the video file might have
				chapters.parse_chapters(video_path, str(anidb_id), episode['episode_number'], themes)

				logprint(f"[main.py] [INFO] Converting {video_path} to {mp3_path}")

				AudioSegment.from_file(video_path).export(mp3_path, format="mp3")
				os.remove(video_path)

			logprint(f"[main.py] [INFO] Starting fingerprinting for \"{kitsu_title}\"")

			fingerprint.fingerprint_episodes(str(anidb_id), episodes)

			episode_index = next_index

		fingerprint.drop_database_tables()

		'''
		titles = anime["title"]
		title = None

		for option in titles:
			if option["lang"] == "x-jat" and option["type"] != "short":
				title = option["title"]
				break

			if option["lang"] == "en" and option["type"] != "short":
				title = option["title"]
				break
		
		episodes = animixplay.get_episodes(title)
		fingerprint.fingerprint_episodes(anidb_id, episodes)
		'''

if __name__ == '__main__':
	main()