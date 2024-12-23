import os
import json
from pathlib import Path
from pydub import AudioSegment
import args
import bettervrv
import anime_skip
import anidb
import anime_offline_database
import kitsu
import animethemesmoe
#import animixplay
import twistmoe
import fingerprint

Path("./openings").mkdir(exist_ok=True)
Path("./endings").mkdir(exist_ok=True)
Path("./episodes").mkdir(exist_ok=True)

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

	anime_titles_json = open("anime-titles.json", 'rb')
	anime_titles = json.load(anime_titles_json)

	# Pull timestamps from other databases first
	if not args.parsed_args.skip_aggregation:
		start_index = 0
		if args.parsed_args.aggregation_start != None:
			start_index = next((i for i, anime in enumerate(anime_titles) if int(anime["id"]) == args.parsed_args.aggregation_start), 0)
		
		for anime in anime_titles[start_index:]:
			anidb_id = anime["id"]
			kitsu_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "kitsu")
			
			if not kitsu_id:
				continue

			episodes = kitsu.episodes(kitsu_id)

			if anidb_id not in local_database:
				local_database[anidb_id] = []

			series = local_database[anidb_id]

			if len(series) == len(episodes):
				continue
			
			for episode in episodes:
				if not episode["attributes"]["canonicalTitle"]:
					continue

				if not any(e['episode_number'] == episode["attributes"]["number"] for e in series):
					anime_skip_episode_timestamps = anime_skip.find_episode_by_name(episode["attributes"]["canonicalTitle"])
					bettervrv_episode_timestamps = bettervrv.find_episode_by_name(episode["attributes"]["canonicalTitle"])
					
					timestamp_data = {
						"episode_number": episode["attributes"]["number"],
						"recap": {
							"start": -1,
							"end": -1
						},
						"opening": {
							"start": -1,
							"end": -1
						},
						"ending": {
							"start": -1,
							"end": -1
						},
						"preview_start": -1
					}

					if anime_skip_episode_timestamps:
						# anime-skip has a lot of timestamp types, most of which don't make sense to me
						# only taking a subset of them
						# "Canon" type means resuming from something else, like at the end of an opening
						timestamp_data["source"] = "anime_skip"

						current_type = "Canon"
						for i in range(len(anime_skip_episode_timestamps)):
							timestamp = anime_skip_episode_timestamps[i]

							if current_type == "Canon":
								if timestamp["type"]["name"] == "Recap":
									timestamp_data["recap"]["start"] = int(timestamp["at"])
									current_type = "Recap"
								
								if timestamp["type"]["name"] in ["New Intro","Intro"]:
									timestamp_data["opening"]["start"] = int(timestamp["at"])
									current_type = "Intro"

								if timestamp["type"]["name"] == ["New Credits","Credits"]:
									timestamp_data["ending"]["start"] = int(timestamp["at"])
									current_type = "Credits"

								if timestamp["type"]["name"] == "Preview":
									timestamp_data["preview_start"] = int(timestamp["at"])
									break # assuming that previews are only right at the end

							elif timestamp["type"]["name"] == "Canon":
								if current_type == "Recap":
									timestamp_data["recap"]["end"] = int(timestamp["at"])
								if current_type == "Intro":
									timestamp_data["opening"]["end"] = int(timestamp["at"])
								if current_type == "Credits":
									timestamp_data["ending"]["end"] = int(timestamp["at"])

								current_type = "Canon"

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

					if timestamp_data["recap_start"] == -1 and timestamp_data["opening_start"] == -1 and timestamp_data["ending_start"] == -1 and timestamp_data["preview_start"] == -1:
						continue

					series.append(timestamp_data)

			local_database_file.seek(0)
			json.dump(local_database, local_database_file, indent=4)

	local_database_file.close()

	# Scrape other timestamps
	start_index = 0
	if args.parsed_args.scrape_start != None:
		start_index = next((i for i, anime in enumerate(anime_titles) if int(anime["id"]) == args.parsed_args.scrape_start), 0)

	for anime in anime_titles[start_index:]:
		anidb_id = anime["id"]
		mal_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "myanimelist")
		kitsu_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "kitsu")

		if not kitsu_id:
			if args.parsed_args.verbose:
				print(f"[main.py] [WARNING] {anidb_id} AniDB ID has no Kitsu ID! Skipping")
			continue

		kitsu_details = kitsu.details(kitsu_id)
		themes = animethemesmoe.download_themes(kitsu_details["data"]["attributes"]["canonicalTitle"])

		if len(themes) == 0:
			if args.parsed_args.verbose:
				title = kitsu_details["data"]["attributes"]["canonicalTitle"]
				print(f"[main.py] [WARNING] {title} has no themes! Skipping")
			continue

		episodes = twistmoe.download_episodes(kitsu_details["data"]["attributes"]["slug"])

		for episode in episodes:
			video_path = episode["video_path"]
			mp3_path = Path(video_path).with_suffix(".mp3")

			episode["mp3_path"] = mp3_path

			if args.parsed_args.verbose:
				print(f"[main.py] [INFO] Converting {video_path} to {mp3_path}")

			AudioSegment.from_file(video_path).export(mp3_path, format="mp3")
			os.remove(video_path)

		if args.parsed_args.verbose:
			print("[main.py] [INFO] Starting fingerprinting")

		print(episodes)

		fingerprint.fingerprint_episodes(anidb_id, episodes)

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