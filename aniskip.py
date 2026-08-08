import time
import requests

from utils import logprint, get_timestamp_template

# Instantiate the client with an endpoint.
API_BASE = "https://api.aniskip.com/v2"

def find_skips(mal_id: int, episode: float) -> list[dict] | None:
	try:
		response = requests.get(f"{API_BASE}/skip-times/{mal_id}/{episode}?types[]=op&types[]=ed&types[]=mixed-op&types[]=mixed-ed&types[]=recap&episodeLength=0")
	except Exception:
		# If killed, just wait a second
		logprint(f"[aniskip.py] [WARNING] Error while requesting episode {episode} for show with MAL ID {mal_id}. Trying again in one second")

		time.sleep(1)
		return find_skips(mal_id)
	try:
		data = response.json()
		if data["found"]:
			return data["results"]
		else:
			if data['statusCode'] != 404:
				logprint(f"[aniskip.py] [WARNING] Could not find skips for episode {episode} MAL ID {mal_id}. Status {data['statusCode']} message {data['message']}")
			return None
	except Exception:
		return None

def parse_timestamps(skip_results: list, episode_number: float, episode_duration: int) -> dict:
	# Timestamp list passed from main.py is never empty
	timestamp_data = get_timestamp_template(episode_number, "aniskip")
	found_durations = []

	# accepting skip types op, ed, mixed-op, mixed-ed, recap

	for result in skip_results:
		timestamp_type = result["skipType"]
		if timestamp_type not in ["op","ed","mixed-op","mixed-ed","recap"]:
			continue

		if episode_duration != 0:
			# Keep the timestamp entry that most matches the episode duration
			existing = [a for a in found_durations if a['type'] == timestamp_type]
			if len(existing) and abs(existing[0]['duration'] - episode_duration) < abs(result['episodeLength'] - episode_duration):
				continue
			found_durations.append({
				"type": timestamp_type,
				"duration": result["episodeLength"]
			})

		timestamp = {"start": int(result["interval"]["startTime"]), "end": int(result["interval"]["endTime"])}

		if timestamp_type in ['op','mixed-op']:
			timestamp_data["opening"] = timestamp
		if timestamp_type in ['ed','mixed-ed']:
			timestamp_data["ending"] = timestamp
		if timestamp_type == 'recap':
			timestamp_data["recap"] = timestamp

	if timestamp_data["recap"]["start"] > timestamp_data["recap"]["end"] > -1:
		logprint(f"[aniskip.py] [WARNING] Invalid recap timestamp for episode {episode_number} ({timestamp_data['recap']}). Skipping timestamp")
		timestamp_data["recap"] = {"start":-1,"end":-1}
	if timestamp_data["opening"]["start"] > timestamp_data["opening"]["end"] > -1:
		logprint(f"[aniskip.py] [WARNING] Invalid opening timestamp for episode {episode_number} ({timestamp_data['opening']}). Skipping timestamp")
		timestamp_data["opening"] = {"start":-1,"end":-1}
	if timestamp_data["ending"]["start"] > timestamp_data["ending"]["end"] > -1:
		logprint(f"[aniskip.py] [WARNING] Invalid ending timestamp for episode {episode_number} ({timestamp_data['ending']}). Skipping timestamp")
		timestamp_data["ending"] = {"start":-1,"end":-1}

	return timestamp_data
