import requests

from utils import logprint

API_PATH = "https://api.myanimelist.net/v2"

HEADERS = {
  "X-MAL-CLIENT-ID": "347bf7170686781dae25d5c2e60f9a64"
}

anime_info_cache = {}

def empty_anime_info_cache():
	global anime_info_cache
	anime_info_cache = {}

def get_anime_info(id: int) -> dict | None:
	global anime_info_cache
	if str(id) in anime_info_cache:
		return anime_info_cache[str(id)]
	req = requests.get(f"{API_PATH}/anime/{id}?fields=num_episodes,related_anime", headers=HEADERS)
	status_code = req.status_code
	if status_code != 200:
		if status_code == 504:
			logprint(f"[myanimelist.py] [WARNING] Failed to get info for anime with MAL ID {id} (response code {status_code}). Retrying")
			return get_anime_info(id)
		else:
			logprint(f"[myanimelist.py] [WARNING] Failed to get info for anime with MAL ID {id} (response code {status_code}). Skipping")
			return
	info = req.json()
	if len([rel for rel in info['related_anime'] if rel['relation_type'] in ['prequel','sequel']]) > 0:
		anime_info_cache[str(id)] = info
	return info

def get_related_anime_info(info: dict, relation_type: str) -> dict:
	for rel in info['related_anime']:
		if rel['relation_type'] == relation_type.lower():
			return get_anime_info(rel['node']['id'])

def get_series_data(info: dict, season_count=1, previous_episode_count=0) -> dict:
	prequel = get_related_anime_info(info, 'prequel')
	if prequel:
		season_count += 1
		if prequel['num_episodes']: # Episode count is null for ongoing anime
			previous_episode_count += prequel['num_episodes']
		return get_series_data(prequel, season_count, previous_episode_count)
	else:
		return {
			"current_season": season_count,
			"previous_episode_count": previous_episode_count,
			"start_id": info['id']
		}

def get_anime_from_episode_num(info: dict, episode_num: float) -> dict:
	sequel = get_related_anime_info(info, 'sequel')
	if sequel and info['num_episodes']:
		episode_num -= info['num_episodes']
		if episode_num <= info['num_episodes']:
			return {
				'id': sequel['id'],
				'episode_num': episode_num
			}
		return get_anime_from_episode_num(sequel, episode_num)
	else:
		return {
				'id': info['id'],
				'episode_num': episode_num
			}
