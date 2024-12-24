import time
from python_graphql_client import GraphqlClient

from log import logprint

HEADERS = {
	"X-Client-ID": "f80QZGOAqCIU1BKEhRs1v4I8hYVOEGle"
}

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="http://api.anime-skip.com/graphql")

def find_episodes_by_external_id(id: str):
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
		data = client.execute(query=query, variables={ "id": id }, headers=HEADERS)
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
			# If killed, just wait a second
			# TODO: Find the right time to wait
			logprint(f"[anime_skip.py] [INFO] Rate limited while requesting show with Anilist ID {id}. Trying again in ten seconds")

			time.sleep(10)
			return find_episodes_by_external_id(id)
	
	try:
		return data["data"]["findShowsByExternalId"][0]["episodes"]
	except Exception:
		return None
