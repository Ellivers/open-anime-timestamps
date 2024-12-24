from pathlib import Path
import requests
import urllib.parse
import re
import requests
import time
import os
import args
from tqdm import tqdm
import args
import math
from lxml import etree, cssselect
from log import logprint

URL_BASE = "https://animepahe.ru"
URL_API_BASE = URL_BASE + "/api?m="

MAX_RETRY_COUNT = args.parsed_args.scrape_max_retry or 10

EXTERNAL_LINKS_SELECTOR = cssselect.CSSSelector('.external-links a')
DL_REDIRECT_SELECTOR = cssselect.CSSSelector('#pickDownload a')

FILENAME_REGEX = re.compile(r'\w{64}\?file=([^\.]+\.mp4)')

ANIDB_ID_REGEX = re.compile(r'//anidb.net/anime/(\d+)')
DL_PAGE_URL_REGEX = re.compile(r'https:\/\/kwik.\w+\/f\/[^"]+')
FORM_HTML_PARAMS_REGEX = re.compile(r'\(\"(\w+)\",\d+,\"(\w+)\",(\d+),(\d+),\d+\)')

COOKIES = {"__ddg1_": "ghqix2xda4k1YXM8znC6", "__ddg2_": "kC5TSLlx7Md9Ua6A"}

CHAR_MAP_DIGITS = "0123456789"
CHAR_MAP_BASE = 10

def get_anime_session(name: str, anidb_id: int) -> list:
  request = requests.get(URL_API_BASE + "search&q=" + urllib.parse.quote(name.replace(' -',' ')),cookies=COOKIES)
  
  if request.status_code != 200:
    logprint(f"[animepahe.py] [WARNING] Getting data for \"{name}\" gave status code {request.status_code} (1). Skipping anime.")
    return

  anime = request.json()["data"][0]

  # Check if the ID matches
  page_request = requests.get(URL_BASE + '/a/' + str(anime["id"]),cookies=COOKIES)

  if page_request.status_code != 200:
    logprint(f"[animepahe.py] [WARNING] Getting page for \"{name}\" gave status code {request.status_code} (2). Skipping anime.")
    return

  page = etree.HTML(page_request.text)

  found_anidb_id = None

  for link in EXTERNAL_LINKS_SELECTOR(page):
    if link.text != "AniDB":
      continue

    found_anidb_id = int(ANIDB_ID_REGEX.findall(link.attrib['href'])[0])
    break

  if found_anidb_id != anidb_id:
    logprint(f"[animepahe.py] [WARNING] {name}: found AniDB ID {found_anidb_id} doesn't match inputted {anidb_id}. Skipping")
    return
  # End of ID check

  return anime["session"]
  
def download_episodes(anime_session):
  episode_list = get_episode_list(anime_session)
  first_episode_num = episode_list[0]["episode"]

  episode_files = []

  for episode in episode_list:
    episode_number = episode["episode"] - (first_episode_num - 1)
    source = get_episode_download(anime_session, episode["session"])

    video_path = download_episode(source)
    if video_path == None:
      logprint(f"[animepahe.py] [WARNING] Couldn't get video path for episode {episode_number} with anime session {anime_session}")
      continue

    episode_files.append({
      # Subsequent seasons' episode numbers start from the previous season's last number,
      # so make sure every season starts with episode 1 with episode - (first_episode - 1)
      "episode_number": episode_number,
      "video_path": video_path
    })

  return episode_files


def get_episode_list_page(anime_session: str, page: int):
  return requests.get(URL_API_BASE + f"release&sort=episode_asc&page={page}&id={anime_session}",cookies=COOKIES).json()

def get_episode_list(anime_session: str):
  response = get_episode_list_page(anime_session, 1)

  episode_list = response["data"]

  if response["last_page"] == 1:
    return episode_list
  
  for i in range(1, response["last_page"]+1):
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

def get_episode_download(anime_session: str, episode_session: str) -> str:
  play_page = etree.HTML(requests.get(URL_BASE + f'/play/{anime_session}/{episode_session}',cookies=COOKIES).text)

  redirect_url = DL_REDIRECT_SELECTOR(play_page)[0].attrib['href']
  redirect_html_text = requests.get(redirect_url,cookies=COOKIES).text

  dl_page_url = DL_PAGE_URL_REGEX.findall(redirect_html_text)[0] # Find the URL to the download page inside the redirection page
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

def download_episode(source: str) -> str:
  file_name = FILENAME_REGEX.findall(Path(source).name)[0]
  video_path = f"./episodes/{file_name}"

  initial_response = requests.get(source)

  if initial_response.status_code != 200:
    logprint(f"[animepahe.py] [WARNING] Episode {source} not reachable! (status code {initial_response.status_code})")
    return None

  content_length = int(initial_response.headers["content-length"] or 0)
  video_file = open(video_path, "wb")
  downloaded_bytes = 0
  retries = 0

  if args.parsed_args.verbose:
    progress_bar = tqdm(total=content_length, unit='iB', unit_scale=True)
    progress_bar.set_description(f"[animepahe.py] [INFO] Downloading {file_name}")

  while downloaded_bytes < content_length:
    try:
      response = requests.get(source, timeout=5, stream=True, headers={"Range": "bytes=%d-" % downloaded_bytes})
      for chunk in response.iter_content(chunk_size=1024*1024):
        chunk_len = len(chunk)
        downloaded_bytes += chunk_len
        
        if args.parsed_args.verbose:
          progress_bar.update(chunk_len)

        video_file.write(chunk)

        # debug
        #percent = int(downloaded_bytes * 100. // content_length)
        #print(f"Downloaded {downloaded_bytes}/{content_length} ({percent}%)")
    except requests.RequestException:
      # If killed, just wait a second or skip
      retries += 1

      if retries >= MAX_RETRY_COUNT:
        if args.parsed_args.verbose:
          logprint(f"[animepahe.py] [WARNING] Max retries hit. Skipping episode")
          progress_bar.close()
        break

      logprint(f"[animepahe.py] [WARNING] Error while downloading episode. Continuing in one second ({retries}/{MAX_RETRY_COUNT} retries)")
      
      time.sleep(1)

  if args.parsed_args.verbose:
    progress_bar.close()

  video_file.close()

  if retries >= MAX_RETRY_COUNT:
    os.remove(video_path)
    return None
  
  return video_path
