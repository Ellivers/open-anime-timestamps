<p float="left">
	<img alt="Linux" src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black">
	<img alt="Ubuntu" src="https://img.shields.io/badge/Ubuntu 20.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white">
	<img alt="Python" src="https://img.shields.io/badge/python 3+-%2314354C.svg?style=for-the-badge&logo=python&logoColor=white"/>
</p>

# Open Anime Timestamps
## Open source database and scraper for anime episode opening and ending timestamps

### Like my work? Consider supporting me on Patreon and Ko-Fi to help make open soure software my full-time job!
<a href="https://www.patreon.com/jonbarrow"><img alt="Patreon" src="https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white" /></a>
<a href="https://ko-fi.com/jonbarrow"><img alt="Ko-Fi" src="https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white" /></a>

# What is this?
Open Anime Timestamps is an open source tool for building a database of opening and ending theme timestamps for anime episodes. Feel free to open a PR with an updated `timestamps.json`.

# This opening/ending timestamp is wrong!
Open Anime Timestamps is an automated tool that tries to find where certain music segments are in an episode video file. There may be times when it thinks it's found the correct start but hasn't, because the episode uses an ending/opening song multiple times, it may not have an opening/ending, etc. These issues can be fixed by opening an issue report or a PR with the correct times.

# Requirements
- Python 3.11.x (not higher)
- MySQL
- ffmpeg

# Installation
```bash$
$ sudo apt-get install python3-dev libmysqlclient-dev python3-numpy python3-matplotlib ffmpeg portaudio19-dev
$ pip3 install -r requirements.txt
```

You will also need to create two MySQL databases and set up `config.json`. An example config [`example_config.json`](/example_config.json) is available.
```json
{
	"openings": {
		"database": {
			"host": "127.0.0.1",
			"user": "root",
			"password": "",
			"database": "openings"
		},
		"database_type": "mysql"
	},
	"endings": {
		"database": {
			"host": "127.0.0.1",
			"user": "root",
			"password": "",
			"database": "endings"
		},
		"database_type": "mysql"
	}
}
```

If you are getting errors about a `fromstring` function, try downgrading numpy. Version 2.0.0 has been tested to work.

# Installation (Dejavu)
The above SHOULD work to install all dependencies needed to install Dejavu on Ubuntu 20.04 and Windows 10. Dejavu is somewhat annoying to install, you may have to manually install some packages or package versions for your setup. If you need help, refer to the Dejavu repo https://github.com/worldveil/dejavu/ or the updated fork that Open Anime Timestamps uses https://github.com/JPery/dejavu

# Usage
```bash
$ python3 main.py [arguments]
```

# Arguments
| Name                          | Alias        | Description                                                                    |
|-------------------------------|--------------|--------------------------------------------------------------------------------|
|`--help`                       | `-h`         | Show the help dialog                                                           |
|`--silent`                     | `-s`         | Disable logging                                                                |
|`--skip-aggregation`           | `-sa`        | Skips the first loop that aggregates timestamps from other databases           |
|`--skip-known`                 | `-sk`        | Skips scraping episodes that are known to exist, even if their timestamps are  undefined |
|`--skip-movies`                | `-sm`        | Skips episodes that are considered movies (>40 minutes long)                   |
|`--aggregation-start-id VALUE` | `-asi VALUE` | Set the start ID for the first, aggregation, loop                              |
|`--scrape-start-id VALUE`      | `-ssi VALUE` | Set the start ID for the second, scraping, loop                                |
|`--scrape-max-retry VALUE`     | `-smr VALUE` | Change the max retry count for episode scraping. Default 10                    |
|`--episodes-max-size VALUE`    | `-ems VALUE` | Threshold for size of episodes on disk before they are processed (in MiB). Default 10GiB (10240 MiB) |
|`--combine-database PATH`    | `-cdb PATH` | Adds timestamps from the specified JSON file to the existing database, then exits |

# How does it work?
Acoustic fingerprinting and aggregating data from other databases. A database of fingerprints made from the opening and ending themes is used on individual episodes to determine where in each video file the opening/ending fingerprint appears. The data for the opening and endings, and episodes, is scraped from the sources below. Some data comes from existing databases, which we then build off here to try and create a "complete" database.

# Fingerprinting
The fingerprinting library used here is Dejavu. This process takes a good amount of RAM to run. Open Anime Timestamps was tested on:
- Ubuntu 20.04 running Python 3.8
- Windows 10 running Python 3.11.9 and Python 3.10
- Fedora 43 running Python 3.11.14

# Database format
The "database" right now is just a plain json file. Each key is the AniDB ID for the series. Using MAL, Kitsu, or Anilist for IDs? Use an API like https://relations.yuna.moe/ to convert these IDs to AniDB IDs. Each value is an array of objects containing the source of the timestamp, episode number, opening start and end, ending start and end, beginning recap start and end, and ending "next episode" preview start (all in seconds). Not each episode will have every timestamp, `-1` in a value means not found/missing timestamp.
```json
{
	"1": [
		{
			"sources": [
				"anime_skip"
			],
			"episode_number": 1,
			"recap": {
				"start": -1,
				"end": -1
			},
			"opening": {
				"start": 10,
				"end": 100
			},
			"ending": {
				"start": 1300,
				"end": 1390
			},
			"preview_start": -1
		},
		{
			"sources": [
				"open_anime_timestamps"
			],
			"episode_number": 4,
			"recap": {
				"start": 10,
				"end": 30
			},
			"opening": {
				"start": 30,
				"end": 120
			},
			"ending": {
				"start": 1300,
				"end": 1400
			},
			"preview_start": -1
		},
		{
			"sources": [
				"better_vrv",
				"open_anime_timestamps"
			],
			"episode_number": 99,
			"recap": {
				"start": -1,
				"end": -1
			},
			"opening": {
				"start": 105,
				"end": 165
			},
			"ending": {
				"start": 1300,
				"end": 1390
			},
			"preview_start": 2000
		}
	]
}
```

# Credits
## This projects takes data from multiple sources
| URL                                                      | Use                                               |
|----------------------------------------------------------|---------------------------------------------------|
| https://github.com/c032/anidb-animetitles-archive        | Anime title list dumps                            |
| https://github.com/manami-project/anime-offline-database | AniDB IDs to MAL/Kitsu IDs                        |
| https://animethemes.moe                                  | Anime opening/ending themes                       |
| https://animepahe.ru                                     | Anime episodes                                    |
| https://github.com/worldveil/dejavu ([used fork](https://github.com/JPery/dejavu))                     | Acoustic fingerprinting                           |
| https://www.anime-skip.com                               | Other timestamp DB                                |
| https://tuckerchap.in/BetterVRV                          | Other timestamp DB                                |
| https://github.com/montylion                             | Running this tool to build most of the timestamps |
| https://github.com/SenZmaKi/Senpwai                      | Methods for scraping AnimePahe                    |

# TODO
- [ ] Speed this thing up. Right now it takes FOREVER to scrape
- [x] Add opening/ending length times for easier skipping
- [ ] Add more sources for episodes? gogoanime might be viable
- [ ] Better comments
- [ ] Clean up the code