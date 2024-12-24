import time
from python_graphql_client import GraphqlClient

from log import logprint

STANDARD_HEADERS = {
	"X-Client-ID": "f80QZGOAqCIU1BKEhRs1v4I8hYVOEGle"
}

TEST_HEADERS = {
	"X-Client-ID": "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
}

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="http://api.anime-skip.com/graphql")

def find_episodes_by_external_id(id: str, headers=STANDARD_HEADERS):
	query = """
		query FindShowsByExternalID($id: String!) {
			findShowsByExternalId(service: ANILIST serviceId: $id) {
				episodes {
					number
					timestamps { source at type { name }}
				}
			}
		}
	"""

	try:
		data = client.execute(query=query, variables={ "id": id }, headers=headers)
	except Exception:
		# If killed, just wait a second
		logprint(f"[anime_skip.py] [WARNING] Error while requesting show with Anilist ID {id}. Trying again in one second")

		time.sleep(1)
		return find_episodes_by_external_id(id)
	
	if "errors" in data:
		ratelimit = False
		try:
			if data["errors"][0]["message"] == "Rate limit exceeded":
				ratelimit = True
		except Exception:
			return None

		if ratelimit:
			# If rate limited, try using the api test headers instead
			logprint(f"[anime_skip.py] [INFO] Rate limited while requesting show with Anilist ID {id}. Trying test headers instead")

			time.sleep(2)
			return find_episodes_by_external_id(id, TEST_HEADERS)
	
	try:
		return data["data"]["findShowsByExternalId"][0]["episodes"]
	except Exception:
		return None

def parse_timestamps(timestamps: list, episode_number: float):
	timestamp_data = {
		"episode_number": episode_number,
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

	# anime-skip has a lot of timestamp types, most of which don't make sense to me
	# only taking a subset of them
	# "Canon" type means resuming from something else, like at the end of an opening
	timestamp_data["source"] = "anime_skip"

	current_type = "Unknown"
	for timestamp in timestamps:
		if timestamp["type"]["name"] not in ["Canon","Unknown","Recap","Intro","New Intro","Credits","New Credits","Preview"]:
			continue

		timestamp_data["source"] = str(timestamp["source"]).lower()

		timestamp_time = int(float(timestamp["at"]))

		if current_type in ["Canon","Unknown"]:
			if timestamp["type"]["name"] == "Recap":
				timestamp_data["recap"]["start"] = timestamp_time
				current_type = "Recap"
			
			if timestamp["type"]["name"] in ["New Intro","Intro"]:
				timestamp_data["opening"]["start"] = timestamp_time
				current_type = "Intro"

			if timestamp["type"]["name"] in ["New Credits","Credits"]:
				timestamp_data["ending"]["start"] = timestamp_time
				current_type = "Credits"

			if timestamp["type"]["name"] == "Preview":
				timestamp_data["preview_start"] = timestamp_time
				break # assuming that previews are only right at the end

		elif current_type in ["Recap","Intro","New Intro","Credits","New Credits"] and timestamp["type"]["name"] != current_type and timestamp["type"]["name"] in ["Canon","Unknown","Recap","New Intro","Intro"]:
			if current_type == "Recap":
				timestamp_data["recap"]["end"] = timestamp_time
			if current_type in ["Intro","New Intro"]:
				if timestamp["type"]["name"] in ["Credits","New Credits"]:
					continue
				timestamp_data["opening"]["end"] = timestamp_time
			if current_type in ["Credits","New Credits"]:
				timestamp_data["ending"]["end"] = timestamp_time

			current_type = timestamp["type"]["name"]

	return timestamp_data
