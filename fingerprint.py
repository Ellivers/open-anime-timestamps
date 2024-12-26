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
import pymysql.cursors
from dejavu import Dejavu
from dejavu.recognize import FileRecognizer

DROP_DATABASE_TABLE = """
DROP TABLE IF EXISTS %s;
"""

# Load config file
config = json.load(open("config.json"))
openings_database_cfg = config["openings"]
endings_database_cfg = config["endings"]

# Setup Dejavu and FileRecognizer instances 
openings_dejavu = Dejavu(openings_database_cfg)
openings_recognizer = FileRecognizer(openings_dejavu)
endings_dejavu = Dejavu(endings_database_cfg)
endings_recognizer = FileRecognizer(endings_dejavu)

def fingerprint_episodes(anidb_id, episodes):
	logprint("[fingerprint.py] [INFO] Adding openings to fingerprint database")

	openings_dejavu.fingerprint_directory("openings", [".ogg"]) # Try using mp3 instead?

	logprint("[fingerprint.py] [INFO] Adding endings to fingerprint database")

	endings_dejavu.fingerprint_directory("endings", [".ogg"])

	# Clear the ending/opening folders after done
	logprint("[fingerprint.py] [INFO] Clearing openings folder")
	for f in glob.glob("./openings/*"):
		os.remove(f)

	logprint("[fingerprint.py] [INFO] Clearing endings folder")
	for f in glob.glob("./endings/*"):
		os.remove(f)

	local_database_file = open("timestamps.json", "r+")
	local_database = json.load(local_database_file)

	"""
	indices = [i for i in range(len(local_database)) if local_database[i]["id"] == anidb_id]
	if len(indices) == 0:
		local_database.append({"id": anidb_id, "titles": []})
		indices = [len(local_database)-1]
	
	series = local_database[indices[0]]
	"""

	if anidb_id not in local_database:
		local_database[anidb_id] = []

	series = local_database[anidb_id]

	for episode in episodes:

		add_method = 'append'
		indices = [i for i in range(len(series)) if series[i]['episode_number'] == episode['episode_number']]
		if len(indices) > 0:
			# Check if timestamps are incomplete, and if so, what to update
			ep = series[indices[0]]
			opening_parts = [ep['opening']['start'],ep['opening']['end']]
			ending_parts = [ep['ending']['start'],ep['ending']['end']]
			if -1 in opening_parts and -1 in ending_parts:
				add_method = 'update_all'
			elif -1 in opening_parts and -1 not in ending_parts:
				add_method = 'update_op'
			elif -1 in ending_parts:
				add_method = 'update_ed'
			else:
				continue

		if add_method == 'append':
			timestamp_data = get_timestamp_template(episode['episode_number'], source="open_anime_timestamps")
		else:
			timestamp_data = series[indices[0]]

		if add_method != 'update_ed':
			logprint("[fingerprint.py] [INFO] Checking episode audio for opening")
			
			opening_results = openings_recognizer.recognize_file(episode["mp3_path"])
			if len(opening_results["results"]) == 0:
				logprint("[fingerprint.py] [INFO] No matches found for opening")
				continue
			opening_start = int(abs(opening_results["results"][0]["offset_seconds"])) # convert to positive and round down
			opening_end = opening_start + int(opening_results["results"][0]["audio_length"])

			timestamp_data["opening"]["start"] = opening_start
			timestamp_data["opening"]["end"] = opening_end
		
		if add_method != 'update_op':
			logprint("[fingerprint.py] [INFO] Checking episode audio for ending")
			
			ending_results = endings_recognizer.recognize_file(episode["mp3_path"])
			if len(opening_results["results"]) == 0:
				logprint("[fingerprint.py] [INFO] No matches found for ending")
				continue

			ending_start = int(abs(ending_results["results"][0]["offset_seconds"])) # convert to positive and round down
			ending_end = ending_start + int(ending_results["results"][0]["audio_length"])

			timestamp_data["ending"]["start"] = ending_start
			timestamp_data["ending"]["end"] = ending_end

		os.remove(episode["mp3_path"])

		logprint(f"[fingerprint.py] [INFO] Opening start: {timestamp_data['opening']['start']}. Ending start: {timestamp_data['ending']['start']}")

		if add_method == 'append':
			series.append(timestamp_data)
	
	local_database_file.seek(0)
	json.dump(local_database, local_database_file, indent=4)
	local_database_file.truncate()
	local_database_file.close()

def drop_database_tables():
	openings_database = pymysql.connect(
		host=openings_database_cfg['database']['host'],
		user=openings_database_cfg['database']['user'],
		password=openings_database_cfg['database']['password'],
		database=openings_database_cfg['database']['database']
	)
	with openings_database.cursor() as cursor:
		cursor.execute(DROP_DATABASE_TABLE % "fingerprints")
		cursor.execute(DROP_DATABASE_TABLE % "songs")
	openings_database.commit()
	openings_database.close()

	endings_database = pymysql.connect(
		host=endings_database_cfg['database']['host'],
		user=endings_database_cfg['database']['user'],
		password=endings_database_cfg['database']['password'],
		database=endings_database_cfg['database']['database']
	)
	with endings_database.cursor() as cursor:
		cursor.execute(DROP_DATABASE_TABLE % "fingerprints")
		cursor.execute(DROP_DATABASE_TABLE % "songs")
	endings_database.commit()
	endings_database.close()
