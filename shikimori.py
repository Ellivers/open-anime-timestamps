import time
from python_graphql_client import GraphqlClient

from utils import logprint

REQUESTS_PER_SECOND = 90
SECONDS_BETWEEN_REQUESTS = 60/REQUESTS_PER_SECOND

# Instantiate the client with an endpoint.
client = GraphqlClient(endpoint="https://shikimori.one/api/graphql")

global last_request
last_request = 0

def get_anime_info(id: str):
	global last_request
	between_requests = time.time() - last_request
	if between_requests < SECONDS_BETWEEN_REQUESTS:
		time.sleep(SECONDS_BETWEEN_REQUESTS - between_requests)
		return get_anime_info(id)

	query = """
		query GetAnimeInfo($ids: String!) {
			animes(ids: $ids) {
				id
				malId
				episodes
				episodesAired

				related {
					anime {
						id
						malId
					}
					relationKind
				}
			}
		}
	"""

	try:
		data = client.execute(query=query, variables={ "ids": id })
	except Exception as e:
		logprint(e)
		# If killed, just wait a second
		logprint(f"[shikimori.py] [WARNING] Error while requesting show with MAL ID {id}. Trying again in two seconds")

		time.sleep(2)
		return get_anime_info(id)
	
	last_request = time.time()
	
	try:
		return data["data"]["animes"][0]
	except Exception:
		return None

def get_related_anime_info(info: dict, relation_type: str):
	for rel in info['related']:
		if rel['relationKind'] == relation_type.lower() and rel['anime']:
			return get_anime_info(rel['anime']['malId'])

def get_series_data(info: dict, season_count=1, previous_episode_count=0):
	prequel = get_related_anime_info(info, 'prequel')
	if prequel:
		season_count += 1
		previous_episode_count += (prequel['episodesAired'] or prequel['episodes'])
		return get_series_data(prequel, season_count, previous_episode_count)
	else:
		return {
			"current_season": season_count,
			"previous_episode_count": previous_episode_count,
			"start_id": int(info['malId'])
		}
