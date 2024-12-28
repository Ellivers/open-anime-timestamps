import time
from python_graphql_client import GraphqlClient

from utils import logprint, get_timestamp_template

STANDARD_HEADERS = {
	"X-Client-ID": "f80QZGOAqCIU1BKEhRs1v4I8hYVOEGle"
}

TEST_HEADERS = {
	"X-Client-ID": "ZGfO0sMF3eCwLYf8yMSCJjlynwNGRXWE"
}

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="http://api.anime-skip.com/graphql")

async def find_episodes(anilist_id: str, from_ratelimit=False):
	if from_ratelimit:
		headers = TEST_HEADERS
	else:
		headers = STANDARD_HEADERS

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
		data = client.execute(query=query, variables={ "id": anilist_id }, headers=headers)
	except Exception:
		# If killed, just wait a second
		logprint(f"[anime_skip.py] [WARNING] Error while requesting show with Anilist ID {anilist_id}. Trying again in one second")

		time.sleep(1)
		return find_episodes(anilist_id, from_ratelimit)
	
	if "errors" in data:
		ratelimit = False
		try:
			if data["errors"][0]["message"] == "Rate limit exceeded":
				ratelimit = True
		except Exception:
			return None

		if ratelimit:
			# If rate limited, try using the api test headers instead
			if not from_ratelimit:
				logprint(f"[anime_skip.py] [INFO] Rate limited while requesting show with Anilist ID {anilist_id}. Trying test headers instead")

			time.sleep(2)
			return find_episodes(anilist_id, True)
	
	try:
		return data["data"]["findShowsByExternalId"][0]["episodes"]
	except Exception:
		return None

def parse_timestamps(timestamps: list, episode_number: float):
	# Timestamp list passed from main.py is never empty
	timestamp_data = get_timestamp_template(episode_number, str(timestamps[0]["source"]).lower())

	# anime-skip has a lot of timestamp types, most of which don't make sense to me
	# only taking a subset of them
	# "Canon" type means resuming from something else, like at the end of an opening
	
	ongoing_type = None

	for timestamp in timestamps:

		timestamp_name = timestamp["type"]["name"]
		if timestamp_name not in ["Canon","Unknown","Recap","Intro","New Intro","Credits","New Credits","Preview"]:
			continue

		timestamp_time = int(float(timestamp["at"]))

		# Set start times
		if timestamp_name in ["Intro","New Intro"]:
			timestamp_data["opening"]["start"] = timestamp_time
		elif timestamp_name in ["Credits","New Credits"]:
			timestamp_data["ending"]["start"] = timestamp_time
		elif timestamp_name == 'Recap':
			timestamp_data["recap"]["start"] = timestamp_time
		elif timestamp_name == 'Preview':
			timestamp_data["preview_start"] = timestamp_time

		# Handle end times
		if ongoing_type == "op":
			timestamp_data["opening"]["end"] = timestamp_time
		elif ongoing_type == "ed":
			timestamp_data["ending"]["end"] = timestamp_time
		elif ongoing_type == "rc":
			timestamp_data["recap"]["end"] = timestamp_time

		if timestamp_name == 'Preview':
			break  # assuming that previews are only right at the end
		
		# Set ongoing type
		if timestamp_name in ["Intro", "New Intro"]:
			ongoing_type = "op"
		elif timestamp_name in ["Credits", "New Credits"]:
			ongoing_type = "ed"
		elif timestamp_name == 'Recap':
			ongoing_type = "rc"
		else:
			ongoing_type = None

	return timestamp_data
