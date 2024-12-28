# Database with a few thousand timestamps already

import json
import time
import urllib.parse
import requests
from utils import get_timestamp_template, logprint

PARSE_SERVER = "https://parseapi.back4app.com"
APP_ID = "CfnxYFbrcy0Eh517CcjOAlrAOH9hfe7dpOqfMcJj"
JS_ID = "Ke0lTaWiPPvLmpDOLLrukkbdAq34GTxVIEh4wcAU"

def find_episodes(name, season, episode_count):
	where = {
		"$and": [
			{
				"series": {
					"$inQuery": {
						"where": {
							"seriesTitle": name
						},
						"className": "Series"
					}
				}
			},
			{
				"$or": [
					{
						"hasIntro": True,
						"introStart": {
							"$exists": True
						},
						"introEnd": {
							"$exists": True
						}
					},
					{
						"hasOutro": True,
						"outroStart": {
							"$exists": True
						},
						"outroEnd": {
							"$exists": True
						}
					},
					{
						"hasPreview": True,
						"previewStart": {
							"$exists": True
						}
					}
				]
			}
		]
	}

	if season != 1:
		where['$and'][0]['seasonNumber'] = season

	params = urllib.parse.urlencode({
		"limit": episode_count,
		"where": json.dumps(where),
		"order": "episodeNumber"
	})

	try:
		response = requests.get(f"{PARSE_SERVER}/classes/Timestamps?{params}", headers={
			"X-Parse-Application-Id": APP_ID,
			"X-Parse-JavaScript-Key": JS_ID
		})
	except Exception:
		# If killed, just wait a second
		logprint(f"[bettervrv.py] [WARNING] Error while requesting {name}. Trying again in one second")

		time.sleep(1)
		return find_episodes(name, season, episode_count)

	try:
		return response.json()["results"]
	except Exception:
		return []

def parse_timestamps(data: dict, episode_number: float) -> dict:
	timestamp_data = get_timestamp_template(episode_number, "better_vrv")

	if "introStart" in data:
		timestamp_data["opening"]["start"] = int(data["introStart"])
		if "introEnd" in data:
			timestamp_data["opening"]["end"] = int(data["introEnd"])

	if "outroStart" in data:
		timestamp_data["ending"]["start"] = int(data["outroStart"])
		if "outroEnd" in data:
			timestamp_data["ending"]["end"] = int(data["outroEnd"])

	if "previewStart" in data:
		timestamp_data["preview_start"] = int(data["previewStart"])

	# BetterVRV also has a "postSceneEnd" timestamp, not sure what it does though. Not tracked
	return timestamp_data
