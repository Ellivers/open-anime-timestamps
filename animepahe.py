from pathlib import Path
import requests
import urllib.parse
import re
import time
import os
import args
from tqdm import tqdm
import args
import math
from lxml import etree, cssselect
from utils import is_not_silent, logprint, get_media_duration

URL_BASE = "https://animepahe.si"
URL_API_BASE = URL_BASE + "/api?m="

MAX_RETRY_COUNT = args.parsed_args.scrape_max_retry or 10
if MAX_RETRY_COUNT < 1:
  MAX_RETRY_COUNT = 1

EXTERNAL_LINKS_SELECTOR = cssselect.CSSSelector('.external-links a')
DL_REDIRECT_SELECTOR = cssselect.CSSSelector('#pickDownload a')

FILENAME_REGEX = re.compile(r'\w{32}\?file=(.+\.mp4)')

ANIDB_ID_REGEX = re.compile(r'//anidb.net/anime/(\d+)')
DL_PAGE_URL_REGEX = re.compile(r'https:\/\/kwik.\w+\/f\/[^"]+')
FORM_HTML_PARAMS_REGEX = re.compile(r'\(\"(\w+)\",\d+,\"(\w+)\",(\d+),(\d+),\d+\)')

COOKIES = {"__ddg1_": "RmqGd2L0vTt99oWclUWc", "__ddg2_": "9or8WPBq08IUnAb5"}

CHAR_MAP_DIGITS = "0123456789"
CHAR_MAP_BASE = 10

def get_anime_session(name: str, anidb_id: int|str) -> list:
  request = requests.get(URL_API_BASE + "search&q=" + urllib.parse.quote(name.replace(' -',' ')),cookies=COOKIES)
  
  if request.status_code != 200:
    logprint(f"[animepahe.py] [WARNING] Getting data for \"{name}\" gave status code {request.status_code} (1). Skipping anime.")
    return

  search_result = request.json()
  if search_result["total"] == 0:
    logprint(f"[animepahe.py] [INFO] Found no results for \"{name}\". Skipping anime")
    return
  
  for anime in search_result["data"]:
    # Check if the ID matches
    page_request = requests.get(URL_BASE + '/a/' + str(anime["id"]),cookies=COOKIES)

    if page_request.status_code != 200:
      continue

    page = etree.HTML(page_request.text)

    found_anidb_id = None

    for link in EXTERNAL_LINKS_SELECTOR(page):
      if link.text != "AniDB":
        continue

      found_anidb_id = int(ANIDB_ID_REGEX.findall(link.attrib['href'])[0])
      break

    if found_anidb_id != int(anidb_id):
      continue

    return anime["session"]
  
  return None
  
def download_episodes(anime_session: str, full_episode_list: list, requirements: list, start_index=0) -> tuple[list[dict], int]:
  logprint(f"[animepahe.py] [INFO] Downloading episodes for anime with session {anime_session}")
  first_episode_num = full_episode_list[0]["episode"]

  current_download_size = 0

  # Total size taken up by downloaded episodes
  # Default value is 10GiB
  # Arg is in MiB
  max_download_size = args.parsed_args.episodes_max_size * 1024 * 1024

  episode_files = []

  for i in range(start_index, len(full_episode_list)):
    episode = full_episode_list[i]
    episode_number = float(episode["episode"] - (first_episode_num - 1))

    if current_download_size > max_download_size:
      logprint(f"[animepahe.py] [INFO] Episodes exceeded the size limit ({int((current_download_size - max_download_size)/1024)} KiB over). Episode batch ended")
      return (episode_files, i)

    if any(e['episode_number'] == episode_number and not (e['op'] or e['ed']) for e in requirements):
      logprint(f"[animepahe.py] [INFO] Findable timestamps for episode {episode_number} are already defined. Skipping")
      continue

    logprint(f"[animepahe.py] [INFO] Getting download link for episode {episode_number}")
    source = get_episode_download(anime_session, episode["session"])

    if source == None:
      logprint(f"[animepahe.py] [WARNING] Couldn't get video download URL for episode {episode_number}")
      continue

    video_path, file_size = download_episode(source)

    if video_path == None:
      logprint(f"[animepahe.py] [WARNING] Couldn't get video path for episode {episode_number}")
      continue

    if args.parsed_args.skip_movies:
      duration = get_media_duration(video_path)
      if duration > (60 * 40): # >40 minutes
        os.remove(video_path)
        logprint(f"[animepahe.py] [INFO] Skipped episode {episode_number} due to length (skip-movies)")
        continue

    current_download_size += file_size

    episode_files.append({
      # Subsequent seasons' episode numbers start from the previous season's last number,
      # so make sure every season starts with episode 1 with episode - (first_episode - 1)
      "episode_number": episode_number,
      "video_path": video_path
    })

  return (episode_files, None)


def get_episode_list_page(anime_session: str, page: int) -> list[dict]:
  return requests.get(URL_API_BASE + f"release&sort=episode_asc&page={page}&id={anime_session}",cookies=COOKIES).json()

def get_episode_list(anime_session: str) -> list[dict]:
  response = get_episode_list_page(anime_session, 1)

  if response['total'] == 0:
    return []
  
  episode_list = response["data"]

  if response["last_page"] == 1:
    return episode_list
  
  for i in range(2, response["last_page"]+1):
    episode_list.extend(get_episode_list_page(anime_session, i)["data"])

  return episode_list

# The following two functions are from https://github.com/SenZmaKi/Senpwai/blob/master/senpwai/scrapers/pahe/main.py
def get_char_code(content: str, s1: int) -> int:
    j = 0
    for index, c in enumerate(reversed(content)):
        j += (int(c) if c.isdigit() else 0) * int(math.pow(s1, index))
    k = ""
    while j > 0:
        k = CHAR_MAP_DIGITS[j % CHAR_MAP_BASE] + k
        j = (j - (j % CHAR_MAP_BASE)) // CHAR_MAP_BASE
    return int(k) if k else 0

def decrypt_post_form(full_key: str, key: str, v1: int, v2: int) -> str:
    r = ""
    i = 0
    while i < len(full_key):
        s = ""
        while full_key[i] != key[v2]:
            s += full_key[i]
            i += 1
        for idx, c in enumerate(key):
            s = s.replace(c, str(idx))
        r += chr(get_char_code(s, v2) - v1)
        i += 1
    return r
#

def get_play_page_html(url: str):
  try:
    response = requests.get(url,cookies=COOKIES)
  except Exception:
    # If killed, wait a second
    logprint(f"[animepahe.py] [WARNING] Error while requesting player page. Trying again in one second")
    time.sleep(1)
    return get_play_page_html(url)
  
  return etree.HTML(response.text)

def get_episode_download(anime_session: str, episode_session: str) -> str:
  play_page_url = URL_BASE + f'/play/{anime_session}/{episode_session}'
  play_page_html = get_play_page_html(play_page_url)

  redirect_elements = DL_REDIRECT_SELECTOR(play_page_html)
  dl_page_url = None
  for elem in redirect_elements:
    redirect_html_text = requests.get(elem.attrib['href'],cookies=COOKIES).text
    dl_page_results = DL_PAGE_URL_REGEX.findall(redirect_html_text) # Find the URL to the download page inside the redirection page
    if len(dl_page_results) == 0:
      logprint(f"[animepahe.py] [WARNING] Could not get download page url from redirect link. Trying next")
      continue

    dl_page_url = dl_page_results[0]
    break
  
  if not dl_page_url:
    return None

  dl_page_response = requests.get(dl_page_url,cookies=COOKIES)
  dl_page_html_text = dl_page_response.text

  form_params = FORM_HTML_PARAMS_REGEX.findall(dl_page_html_text)[0]
  form_html = etree.HTML(decrypt_post_form(form_params[0],form_params[1],int(form_params[2]),int(form_params[3])))

  post_url = None
  post_token = None
  for elem in form_html.iter():
    if elem.tag == 'form':
      post_url = elem.attrib["action"]
    if elem.tag == 'input':
      post_token = elem.attrib["value"]
      break
  
  dl_url = requests.post(post_url, {'_token': post_token}, headers={"Referer": dl_page_url}, cookies=dl_page_response.cookies, allow_redirects=False)
  return dl_url.headers["Location"]

def download_episode(source: str) -> tuple[str, int]:
  file_name = FILENAME_REGEX.findall(Path(source).name)[0]
  video_path = f"./episodes/{file_name}"

  if os.path.exists(video_path):
    logprint(f"[animepahe.py] [INFO] {file_name} has already been downloaded. Skipping")
    return (video_path, os.path.getsize(video_path))

  for i in range(1,MAX_RETRY_COUNT+1):
    initial_response = requests.head(source, headers={"Referer": "https://kwik.cx/"})

    if initial_response.status_code != 200:
      logprint(f"[animepahe.py] [WARNING] Episode {source} not reachable! (status code {initial_response.status_code})")
      if i >= MAX_RETRY_COUNT or initial_response.status_code != 522:
        return (None,0)
      else:
        logprint(f"[animepahe.py] [INFO] Retrying in one second ({i}/{MAX_RETRY_COUNT})")
        time.sleep(1)
    else:
      break

  content_length = int(initial_response.headers["content-length"] or 0)
  video_file = open(video_path, "wb")
  downloaded_bytes = 0
  retries = 0

  if is_not_silent():
    progress_bar = tqdm(total=content_length, unit='iB', unit_scale=True)
    progress_bar.set_description(f"[animepahe.py] [INFO] Downloading {file_name}")

  while downloaded_bytes < content_length:
    try:
      response = requests.get(source, timeout=5, stream=True, headers={"Range": "bytes=%d-" % downloaded_bytes, "Referer": "https://kwik.cx/"})
      for chunk in response.iter_content(chunk_size=1024*1024):
        chunk_len = len(chunk)
        downloaded_bytes += chunk_len
        
        if is_not_silent():
          progress_bar.update(chunk_len)

        video_file.write(chunk)

        # debug
        #percent = int(downloaded_bytes * 100. // content_length)
        #print(f"Downloaded {downloaded_bytes}/{content_length} ({percent}%)")
    except requests.RequestException:
      # If killed, just wait a second or skip
      retries += 1

      if retries >= MAX_RETRY_COUNT:
        if is_not_silent():
          logprint(f"[animepahe.py] [WARNING] Max retries hit. Skipping episode")
          progress_bar.close()
        break

      logprint(f"[animepahe.py] [WARNING] Error while downloading episode. Continuing in one second ({retries}/{MAX_RETRY_COUNT} retries)")
      
      time.sleep(1)

  if is_not_silent():
    progress_bar.close()

  video_file.close()

  if retries >= MAX_RETRY_COUNT:
    os.remove(video_path)
    return (None,0)
  
  return (video_path, content_length)
