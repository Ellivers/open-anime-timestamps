import time
from math import ceil
from python_graphql_client import GraphqlClient

from utils import logprint

REQUESTS_PER_SECOND = 30
SECONDS_BETWEEN_REQUESTS = ceil(60/REQUESTS_PER_SECOND)

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="https://graphql.anilist.co")

global last_request
last_request = 0

def get_episode_count(id: int):
	global last_request
	between_requests = time.time() - last_request
	if between_requests < SECONDS_BETWEEN_REQUESTS:
		time.sleep(SECONDS_BETWEEN_REQUESTS - between_requests)
		return get_episode_count(id)

	query = """
		query GetAnimeInfo($id: Int!) {
			Media(id: $id) {
				episodes
      }
		}
	"""

	try:
		data = client.execute(query=query, variables={ "id": id })
	except Exception:
		# If killed, just wait a second
		logprint(f"[anilist.py] [WARNING] Error while requesting show with Anilist ID {id}. Trying again in two seconds")

		time.sleep(2)
		return get_episode_count(id)
	
	last_request = time.time()
	
	try:
		return data["data"]["Media"]["episodes"]
	except Exception:
		return None

def get_relations(id: int):
	global last_request
	between_requests = time.time() - last_request
	if between_requests < SECONDS_BETWEEN_REQUESTS:
		time.sleep(SECONDS_BETWEEN_REQUESTS - between_requests)
		return get_relations(id)

	query = """
		query FindRelations($id: Int!) {
			Media(id: $id) {
        relations {
          edges {
            relationType
            node {
              id
			  episodes
            }
          }
        }
      }
		}
	"""

	try:
		data = client.execute(query=query, variables={ "id": id })
	except Exception as e:
		logprint(e)
		# If killed, just wait a second
		logprint(f"[anilist.py] [WARNING] Error while requesting show with Anilist ID {id}. Trying again in two seconds")

		time.sleep(2)
		return get_relations(id)
	
	last_request = time.time()
	
	try:
		return data["data"]["Media"]["relations"]["edges"]
	except Exception:
		return None

def get_relation_data(id: int, relation_type: str):
	relations = get_relations(id)
	if not relations:
		return None
	
	for rel in relations:
		if rel['relationType'] == relation_type.upper():
			return {
				"id": rel['node']['id'],
				"episode_count": rel['node']['episodes']
			}

def get_series_info(id: int) -> dict:
	first_entry = id
	episodes_before = 0
	season = 1
	prequel = get_relation_data(id, 'PREQUEL')
	while prequel:
		season += 1
		first_entry = prequel['id']
		if prequel['episode_count']:
			episodes_before += prequel['episode_count']
		prequel = get_relation_data(id, 'PREQUEL')
	
	return {
		"season": season,
		"first_entry": first_entry,
		"episodes_before": episodes_before
	}
