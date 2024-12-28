import requests

from utils import logprint

API_PATH = "https://api.myanimelist.net/v2"

HEADERS = {
  "X-MAL-CLIENT-ID": "347bf7170686781dae25d5c2e60f9a64"
}

def get_anime_info(id: int):
	req = requests.get(f"{API_PATH}/anime/{id}?fields=num_episodes,related_anime", headers=HEADERS)
	if req.status_code != 200:
		logprint(f"[myanimelist.py] [WARNING] Failed getting info for anime with MAL ID {id} (response code {req.status_code})")
		return
	return req.json()

def get_related_anime_info(info: dict, relation_type: str):
	for rel in info['related_anime']:
		if rel['relation_type'] == relation_type.lower():
			return get_anime_info(rel['node']['id'])

def get_series_data(info: dict, season_count=1, previous_episode_count=0):
	prequel = get_related_anime_info(info, 'prequel')
	if prequel:
		season_count += 1
		previous_episode_count += info['num_episodes']
		return get_series_data(prequel, season_count, previous_episode_count)
	else:
		return {
			"current_season": season_count,
			"previous_episode_count": previous_episode_count,
			"start_id": info['id']
		}
