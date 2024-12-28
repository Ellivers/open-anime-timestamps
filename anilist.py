import time
from python_graphql_client import GraphqlClient

from utils import logprint

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="https://graphql.anilist.co")

def get_episode_count(id: int):
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
		logprint(f"[anime_skip.py] [WARNING] Error while requesting show with Anilist ID {id}. Trying again in one second")

		time.sleep(1)
		return get_episode_count(id)
	
	try:
		return data["data"]["Media"]["episodes"]
	except Exception:
		return None

def get_relations(id: int):
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
	except Exception:
		# If killed, just wait a second
		logprint(f"[anime_skip.py] [WARNING] Error while requesting show with Anilist ID {id}. Trying again in one second")

		time.sleep(1)
		return get_relations(id)
	
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
