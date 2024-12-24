import requests

from log import logprint

def details(id):
	response = requests.get(f"https://kitsu.io/api/edge/anime/{id}")
	return response.json()

def episodes(id, offset=0):
	response = requests.get(f"https://kitsu.io/api/edge/anime/{id}/episodes?page[limit]=20&page[offset]={offset}")
	data = response.json()
	episodes_list = [*data["data"]]

	if "next" in data["links"]:
		next_offset = offset+len(data["data"])
		logprint(f"[kitsu.py] [INFO] Series with Kitsu ID {id} has more episodes, getting next page ({next_offset}/{data['meta']['count']})")
		episodes_list = [*episodes_list, *episodes(id, next_offset)]

	return episodes_list
