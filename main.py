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
from log import logprint

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
				
				try:
					episode_number = float(episode["number"])
				except Exception:
					logprint(f"[main.py] [WARNING] Got invalid episode number {episode['number']}")
					continue
				
				if not any(e['episode_number'] == episode_number for e in series):
					#bettervrv_episode_timestamps = bettervrv.find_episode_by_name(episode["attributes"]["canonicalTitle"])
					
					timestamp_data = anime_skip.parse_timestamps(episode["timestamps"])

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

					existing_indices = [i for i in range(len(series)) if series[i]["episode_number"] == timestamp_data["episode_number"]]
					if len(existing_indices) > 0:
						if len(existing_indices) > 1:
							logprint(f"[main.py] [WARNING] Anime with ID {anidb_id} has duplicates of episode {timestamp_data['episode_number']}")
						series[existing_indices[0]] = timestamp_data
					else:
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

		jp_title = None
		titles = anime["titles"]
		title_indices = [i for i in range(len(titles)) if titles[i]["type"] == "main"]
		if len(title_indices) > 0:
			jp_title = titles[title_indices[0]]["title"]
		else:
			jp_title = titles[0]

		themes = animethemesmoe.download_themes(jp_title)

		# animethemes and animepahe use two different main title formats
		kitsu_title = kitsu_details["data"]["attributes"]["canonicalTitle"]

		if len(themes) == 0:
			logprint(f"[main.py] [WARNING] {kitsu_title} has no themes! Skipping")
			continue

		pahe_session = animepahe.get_anime_session(kitsu_title, anidb_id)
		episodes = animepahe.download_episodes(pahe_session)

		for episode in episodes:
			video_path = episode["video_path"]
			mp3_path = Path(video_path).with_suffix(".mp3")

			episode["mp3_path"] = mp3_path

			logprint(f"[main.py] [INFO] Converting {video_path} to {mp3_path}")

			AudioSegment.from_file(video_path).export(mp3_path, format="mp3")
			os.remove(video_path)

		logprint(f"[main.py] [INFO] Starting fingerprinting for \"{kitsu_title}\"")

		print(episodes)

		fingerprint.fingerprint_episodes(str(anidb_id), episodes)

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