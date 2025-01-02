from glob import glob
import os
import json
from pathlib import Path
from pydub import AudioSegment
import args
import re
import anime_skip
import anidb
import anime_offline_database
import bettervrv
import kitsu
import animethemesmoe
#import animixplay
#import twistmoe
import animepahe
import fingerprint
import chapters
import math
import myanimelist
import shutil
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
	local_database: dict = json.load(local_database_file)

	if args.parsed_args.combine_database:
		path = args.parsed_args.combine_database
		if not os.path.exists(path):
			logprint(f"[main.py] [ERROR] Could not find file {path}",ignore_silent=True)
			return
		file = open(path)
		try:
			import_db_file = json.load(file)
		except json.decoder.JSONDecodeError:
			logprint("[main.py] [ERROR] Inputted file is not a valid JSON file",ignore_silent=True)
			return
		
		if type(import_db_file) is not dict:
			logprint("[main.py] [ERROR] Inputted file is not a JSON dict",ignore_silent=True)
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
				if episode_number < 0:
					logprint(f"[main.py] [WARNING] Skipping episode with invalid number {episode_number}")
					continue

				if 'recap' in ep and ep['recap'].get('end',-1) != -1 and ep['recap'].get('start',-1) == -1:
					ep['recap']['start'] = 0
				if 'opening' in ep and ep['opening'].get('end',-1) != -1 and ep['opening'].get('start',-1) == -1:
					ep['opening']['start'] = 0
				if 'ending' in ep and ep['ending'].get('end',-1) != -1 and ep['ending'].get('start',-1) == -1:
					ep['ending']['start'] = 0

				indices = [i for i in range(len(series)) if float(series[i]['episode_number']) == float(episode_number)]
				if len(indices) == 0:
					series.append(merge_timestamps(ep, get_timestamp_template(episode_number)))
				else:
					series[indices[0]] = merge_timestamps(ep, series[indices[0]])
		
		local_database_file.seek(0)
		json.dump(dict(sorted(local_database.items(), key=lambda pair: int(pair[0]))), local_database_file, indent=4)
		local_database_file.truncate()
		local_database_file.close()

		return
	
	if args.parsed_args.episodes_max_size > shutil.disk_usage('/').free // (2**20):
		logprint(f'[main.py] [ERROR] Inputted max episode disk size {args.parsed_args.episodes_max_size} MiB is greater than space left on disk. Exiting',ignore_silent=True)
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
		
		logprint(f"[main.py] [INFO] Finding timestamps from anime-skip and bettervrv")

		for anime in anime_titles[start_index:]:
			anidb_id = str(anime["id"])
			anilist_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "anilist")
			mal_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "myanimelist")

			if anidb_id not in local_database:
				local_database[anidb_id] = []

			series = local_database[anidb_id]

			if mal_id:
				anime_info = myanimelist.get_anime_info(mal_id)
			else:
				anime_info = None

			episode_count = None
			if anime_info and anime_info['num_episodes']:
				episode_count = anime_info['num_episodes']
			else:
				kitsu_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "kitsu")
				kitsu_details = kitsu.details(kitsu_id)
				if 'data' in kitsu_details:
					keys_exist = all(a in kitsu_details['data']['attributes'] for a in ['totalLength','episodeLength'])
					if keys_exist:
						total_length = kitsu_details['data']['attributes']['totalLength']
						episode_length = kitsu_details['data']['attributes']['episodeLength']
					if 'data' in kitsu_details and keys_exist and bool(total_length and episode_length):
						episode_count = int(total_length / episode_length)
			if not episode_count:
				episode_count = 9999

			# Anime-skip
			as_episodes = anime_skip.find_episodes(str(anilist_id))

			if as_episodes:
				actual_series = series
				logprint(f"[main.py] [INFO] Found anime-skip timestamps for series with ID {anidb_id}")
				
				for episode in as_episodes:
					if not episode["number"]:
							continue
					if len(episode['timestamps']) == 0:
							continue
					
					try:
						episode_number = float(episode["number"])
					except Exception:
						logprint(f"[main.py] [WARNING] Got invalid episode number {episode['number']}")
						continue

					if episode_number > episode_count and anime_info:
						# Check which series this episode belongs to
						actual_anime = myanimelist.get_anime_from_episode_num(anime_info, episode_number)
						actual_anidb_id = anime_offline_database.convert_anime_id(actual_anime['id'], "myanimelist", "anidb")
						if actual_anidb_id:
							actual_anidb_id = str(actual_anidb_id)
							if actual_anidb_id not in local_database:
								local_database[actual_anidb_id] = []
							actual_series = local_database[actual_anidb_id]
							episode_number = float(actual_anime['episode_num'])
							logprint(f"[main.py] [INFO] Found anime-skip timestamps for series {actual_anidb_id} within timestamps for series {anidb_id}")
					
					if episode_number < 0:
						logprint(f"[main.py] [WARNING] Got negative episode number {episode_number}. Skipping episode")
						continue

					timestamp_data = anime_skip.parse_timestamps(episode["timestamps"], episode_number)

					if timestamp_data["recap"]["start"] == -1 and timestamp_data["opening"]["start"] == -1 and timestamp_data["ending"]["start"] == -1 and timestamp_data["preview_start"] == -1:
						continue

					existing_indices = [i for i in range(len(actual_series)) if actual_series[i]["episode_number"] == episode_number]
					if len(existing_indices) > 0:
						actual_series[existing_indices[0]] = merge_timestamps(timestamp_data, actual_series[existing_indices[0]])
					else:
						actual_series.append(timestamp_data)
					
				local_database_file.seek(0)
				json.dump(local_database, local_database_file, indent=4)
				local_database_file.truncate()
			
			# BetterVRV

			# OK to use 'continue' here because no more sources are after BetterVRV
			if not anime_info:
				continue

			series_data = myanimelist.get_series_data(anime_info)

			if series_data['start_id'] == mal_id:
				titles = anime["titles"]
			else:
				start_anidb_id = anime_offline_database.convert_anime_id(series_data['start_id'], "myanimelist", "anidb")
				found_anime = [a for a in anime_titles if a['id'] == start_anidb_id]
				if len(found_anime) == 0:
					continue
				else:
					titles = found_anime[0]["titles"]
			
			bvrv_episodes = None
			for title in [t['title'] for t in titles if t['language'] in ['x-jat','en'] and t['type'] in ['main','official']]:
				bvrv_episodes = bettervrv.find_episodes(title, series_data['current_season'], episode_count)
				if bvrv_episodes:
					break
			
			if bvrv_episodes:
				logprint(f"[main.py] [INFO] Found bettervrv timestamps for series with ID {anidb_id}")

				for episode in bvrv_episodes:
					if not episode["episodeNumber"]:
							continue
					
					try:
						episode_number = float(episode["episodeNumber"])
					except Exception:
						logprint(f"[main.py] [WARNING] Got invalid episode number {episode['episodeNumber']}")
						continue

					if series_data['previous_episode_count'] > 0 and int(episode_number) > series_data['previous_episode_count']:
						episode_number = int(episode_number - series_data['previous_episode_count'])

					if episode_number < 0:
						logprint(f"[main.py] [WARNING] Got negative episode number {episode_number}. Skipping episode")
						continue

					timestamp_data = bettervrv.parse_timestamps(episode, float(episode_number))
					
					if timestamp_data["recap"]["start"] == -1 and timestamp_data["opening"]["start"] == -1 and timestamp_data["ending"]["start"] == -1 and timestamp_data["preview_start"] == -1:
						continue

					existing_indices = [i for i in range(len(series)) if series[i]["episode_number"] == float(episode_number)]
					if len(existing_indices) > 0:
						series[existing_indices[0]] = merge_timestamps(timestamp_data, series[existing_indices[0]])
					else:
						series.append(timestamp_data)

				local_database_file.seek(0)
				json.dump(local_database, local_database_file, indent=4)
				local_database_file.truncate()
			
		myanimelist.empty_anime_info_cache()
	
	local_database_file.close()

	# Scrape other timestamps
	start_index = 0
	if args.parsed_args.scrape_start != None:
		start_index = next((i for i, anime in enumerate(anime_titles) if int(anime["id"]) == args.parsed_args.scrape_start), 0)

	for anime in anime_titles[start_index:]:
		anidb_id = str(anime["id"])
		kitsu_id = anime_offline_database.convert_anime_id(anidb_id, "anidb", "kitsu")

		if not kitsu_id:
			logprint(f"[main.py] [WARNING] {anidb_id} AniDB ID has no Kitsu ID! Skipping")
			continue

		kitsu_details = kitsu.details(kitsu_id)

		# animethemes and animepahe use two different main title formats
		kitsu_title = kitsu_details["data"]["attributes"]["canonicalTitle"]
		episode_count = kitsu_details['data']['attributes']['episodeCount']

		pahe_session = animepahe.get_anime_session(kitsu_title, anidb_id)
		if not pahe_session:
			continue

		total_episodes = animepahe.get_episode_list(pahe_session)
		logprint(f"[main.py] [INFO] Found {len(total_episodes)} episodes for \"{kitsu_title}\"")

		if len(total_episodes) == 0:
			continue
		
		if anidb_id not in local_database:
			local_database[anidb_id] = []

		series = local_database[anidb_id]

		# Check if all episodes in the list already have defined OPs and EDs
		if all(any(ep2['episode_number'] == float(ep['episode']) and -1 not in [
				ep2['opening']['start'],ep2['opening']['end'],
				ep2['ending']['start'],ep2['ending']['end']
			] for ep2 in series) for ep in total_episodes):
			
			logprint(f"[main.py] [INFO] \"{kitsu_title}\" with ID {anidb_id} doesn't require fingerprinting. Skipping")
			continue

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

		jp_title = None
		titles = anime["titles"]
		title_reults = [title for title in titles if title["type"] == "main"]
		if len(title_reults) > 0:
			jp_title = title_reults[0]["title"]
		else:
			jp_title = titles[0]

		themes = animethemesmoe.download_themes(jp_title, anidb_id, themes_to_download)

		if len(themes) == 0:
			logprint(f"[main.py] [INFO] No themes to get from \"{kitsu_title}\". Skipping")
			continue

		# Make sure that existing timestamps for this series have ends marked
		# I'll remove this when all fixable timestamps have been fixed
		if len(series) > 0 and \
			any((ep['opening']['start'] != -1 and ep['opening']['end'] == -1) or (ep['ending']['start'] != -1 and ep['ending']['end'] == -1) for ep in series):
			local_database_file = open("timestamps.json", "r+")

			openings = [t for t in themes if "OP" in t['type']]
			endings = [t for t in themes if "ED" in t['type']]

			# All OPs and EDs have to have the same duration for this to work
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
					logprint(f"[main.py] [INFO] Completed opening timestamp for episode {ep['episode_number']}")
					ep['opening']['end'] = start + op_duration

				start = ep['ending']['start']
				if ed_duration != -1 and start != -1 and ep['ending']['end'] == -1:
					logprint(f"[main.py] [INFO] Completed ending timestamp for episode {ep['episode_number']}")
					ep['ending']['end'] = start + ed_duration
			
			local_database_file.seek(0)
			json.dump(local_database, local_database_file, indent=4)
			local_database_file.truncate()
			local_database_file.close()

		####
		# This is also to be deleted
		# Check if all episodes in the list already have defined OPs and EDs
		if all(any(ep2['episode_number'] == float(ep['episode']) and -1 not in [
				ep2['opening']['start'],ep2['opening']['end'],
				ep2['ending']['start'],ep2['ending']['end']
			] for ep2 in series) for ep in total_episodes):
			
			logprint(f"[main.py] [INFO] \"{kitsu_title}\" with ID {anidb_id} doesn't require fingerprinting. Skipping")
			for f in glob("./openings/*"):
				os.remove(f)
			for f in glob("./endings/*"):
				os.remove(f)
			continue
		####

		for theme in themes:
			file_path = Path(theme["file_path"])

			if file_path.suffix == '.mp3':
				continue

			mp3_path = Path(file_path).with_suffix(".mp3")

			if os.path.exists(mp3_path):
				continue

			logprint(f"[main.py] [INFO] Converting {file_path} to mp3")

			AudioSegment.from_file(file_path).export(mp3_path, format="mp3")
			os.remove(file_path)
			theme["file_path"] = mp3_path

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
				chapters.parse_chapters(video_path, anidb_id, episode['episode_number'], themes)

				logprint(f"[main.py] [INFO] Converting {video_path} to mp3")

				AudioSegment.from_file(video_path).export(mp3_path, format="mp3")
				os.remove(video_path)

			logprint(f"[main.py] [INFO] Starting fingerprinting for \"{kitsu_title}\"")

			fingerprint.fingerprint_episodes(anidb_id, episodes)

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