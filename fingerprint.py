##########################################################
# Monkey patch for getting Dejabu running on Python 3.8+ #
#    (platform.linux_distribution was removed in 3.8)    #
import platform
try:
	import distro
	def linux_distribution():
		return [distro.like()]
	platform.linux_distribution = linux_distribution
except ImportError:
	pass
##########################################################

from utils import logprint, get_timestamp_template
import json
import glob
import os
from dejavu import Dejavu
from dejavu.recognize import FileRecognizer

# Load config file
config = json.load(open("config.json"))
openings_database_cfg = config["openings"]
endings_database_cfg = config["endings"]

# Setup Dejavu and FileRecognizer instances 
openings_dejavu = Dejavu(openings_database_cfg)
openings_recognizer = FileRecognizer(openings_dejavu)
endings_dejavu = Dejavu(endings_database_cfg)
endings_recognizer = FileRecognizer(endings_dejavu)

def fingerprint_episodes(anidb_id: str, episodes: list[dict]):
	logprint("[fingerprint.py] [INFO] Adding openings to fingerprint database")

	openings_dejavu.fingerprint_directory("openings", [".ogg"])

	logprint("[fingerprint.py] [INFO] Adding endings to fingerprint database")

	endings_dejavu.fingerprint_directory("endings", [".ogg"])

	# Clear the ending/opening folders after done
	logprint("[fingerprint.py] [INFO] Clearing openings folder")
	for f in glob.glob("./openings/*"):
		os.remove(f)

	logprint("[fingerprint.py] [INFO] Clearing endings folder")
	for f in glob.glob("./endings/*"):
		os.remove(f)

	local_database_file = open("timestamps.json", "r")
	local_database = json.load(local_database_file)
	local_database_file.close()

	if anidb_id not in local_database:
		local_database[anidb_id] = []

	series = local_database[anidb_id]

	opening_count = openings_dejavu.db.get_num_songs()
	ending_count = endings_dejavu.db.get_num_songs()

	for episode in episodes:
		episode_number = episode['episode_number']

		add_method = 'append'
		indices = [i for i in range(len(series)) if series[i]['episode_number'] == episode_number]
		if len(indices) > 0:
			# Check if timestamps are incomplete, and if so, what to update
			ep = series[indices[0]]

			update_opening = -1 in [ep['opening']['start'],ep['opening']['end']] and opening_count > 0
			update_ending = -1 in [ep['ending']['start'],ep['ending']['end']] and ending_count > 0

			if update_opening and update_ending:
				add_method = 'update_all'
			elif update_opening and not update_ending:
				add_method = 'update_op'
			elif update_ending:
				add_method = 'update_ed'
			else:
				logprint(f"[fingerprint.py] [INFO] Episode {episode_number} does not need to be checked")
				os.remove(episode["video_path"])
				continue

		if add_method == 'append':
			timestamp_data = get_timestamp_template(episode_number, source="open_anime_timestamps")
		else:
			timestamp_data = series[indices[0]]

		if add_method != 'update_ed' and opening_count > 0:
			logprint(f"[fingerprint.py] [INFO] Checking episode {episode_number} audio for opening")
			
			opening_result = openings_recognizer.recognize_file(episode["video_path"])
			if opening_result and opening_result['confidence'] > 12:
				logprint(f"[fingerprint.py] [INFO] Found opening with confidence {opening_result['confidence']}")
				opening_start = int(abs(opening_result["offset_seconds"])) # convert to positive and round down
				opening_end = opening_start + int(opening_result["audio_length"])

				timestamp_data["opening"]["start"] = opening_start
				timestamp_data["opening"]["end"] = opening_end
				if 'open_anime_timestamps' not in timestamp_data['sources']:
					timestamp_data['sources'].append('open_anime_timestamps')
			else:
				logprint("[fingerprint.py] [INFO] No good match found for opening")
		
		if add_method != 'update_op' and ending_count > 0:
			logprint(f"[fingerprint.py] [INFO] Checking episode {episode_number} audio for ending")
			
			ending_result = endings_recognizer.recognize_file(episode["video_path"])
			if ending_result and ending_result['confidence'] > 12:
				logprint(f"[fingerprint.py] [INFO] Found ending with confidence {ending_result['confidence']}")
				ending_start = int(abs(ending_result["offset_seconds"])) # convert to positive and round down
				ending_end = ending_start + int(ending_result["audio_length"])

				timestamp_data["ending"]["start"] = ending_start
				timestamp_data["ending"]["end"] = ending_end
				if 'open_anime_timestamps' not in timestamp_data['sources']:
					timestamp_data['sources'].append('open_anime_timestamps')
			else:
				logprint("[fingerprint.py] [INFO] No good match found for ending")

		os.remove(episode["video_path"])

		if add_method == 'append':
			series.append(timestamp_data)
	
		logprint(f"[fingerprint.py] [INFO] Opening: {timestamp_data['opening']}. Ending: {timestamp_data['ending']}")

		local_database_file = open("timestamps.json", 'w')
		json.dump(local_database, local_database_file, indent=4)
		local_database_file.close()

def drop_database_tables():
	logprint("[fingerprint.py] [INFO] Clearing databases")
	openings_dejavu.db.empty()
	endings_dejavu.db.empty()

def get_fingerprinted_songs() -> list[dict]:
	songs_list = []

	openings = [{'song_id': s['song_id'], 'song_name': s['song_name'], 'type': 'opening'} for s in openings_dejavu.db.get_songs()]
	endings = [{'song_id': s['song_id'], 'song_name': s['song_name'], 'type': 'ending'} for s in endings_dejavu.db.get_songs()]

	songs_list.extend(openings)
	songs_list.extend(endings)
	
	return songs_list

def get_song_by_id(id: int, song_type: str):
	if song_type == 'opening':
		return openings_dejavu.db.get_song_by_id(id)
	if song_type == 'ending':
		return endings_dejavu.db.get_song_by_id(id)
	return None
