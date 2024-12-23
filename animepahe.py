import requests
import urllib.parse
import re
import args
import math
from lxml import etree, cssselect

URL_BASE = "https://animepahe.ru"
URL_API_BASE = URL_BASE + "/api?m="

EXTERNAL_LINKS_SELECTOR = cssselect.CSSSelector('.external-links a')
DL_REDIRECT_SELECTOR = cssselect.CSSSelector('#pickDownload a')

ANIDB_ID_REGEX = re.compile(r'//anidb.net/anime/(\d+)')
DL_PAGE_URL_REGEX = re.compile(r'https:\/\/kwik.\w+\/f\/[^"]+')
FORM_HTML_PARAMS_REGEX = re.compile(r'\(\"(\w+)\",\d+,\"(\w+)\",(\d+),(\d+),\d+\)')

COOKIES = {"__ddg1_": "ghqix2xda4k1YXM8znC6", "__ddg2_": "kC5TSLlx7Md9Ua6A"}

CHAR_MAP_DIGITS = "0123456789"
CHAR_MAP_BASE = 10

def download_episodes(name: str, anidb_id) -> list:
  request = requests.get(URL_API_BASE + "seach&q=" + urllib.parse.quote(name.replace(' -',' ')),cookies=COOKIES)
  
  if request.status_code != 200:
    if args.parsed_args.verbose:
      print(f"[animepahe.py] [INFO] Getting data for \"{name}\" gave status code {request.status_code} (1)")
    return

  anime = request.json()

  # Check if the ID matches
  page_request = requests.get(URL_BASE + '/a/' + anime["id"],cookies=COOKIES)

  if page_request.status_code != 200:
    if args.parsed_args.verbose:
      print(f"[animepahe.py] [INFO] Getting page for \"{name}\" gave status code {request.status_code} (2)")
    return

  page = etree.HTML(page_request.text)

  found_anidb_id = None

  for link in EXTERNAL_LINKS_SELECTOR(page):
    if link.text != "AniDB":
      continue

    found_anidb_id = int(ANIDB_ID_REGEX.findall(link.attrib['href'])[0])
    break

  if found_anidb_id != anidb_id:
    if args.parsed_args.verbose:
      print(f"[animepahe.py] [INFO] {name}: found AniDB ID {found_anidb_id} doesn't match inputted {anidb_id}")
    return
  # End of ID check
  
  episode_list = get_episode_list(anime["session"])
  first_episode_num = episode_list[0]["episode"]

  episode_files = []

  for episode in episode_list:
    dl_url = get_episode_download(anime["session"], episode["session"])

    episode_files.append({
      # Subsequent seasons' episode numbers start from the previous season's last number,
      # so make sure every season starts with episode 1 with episode - (first_episode - 1)
      "episode_number": episode["episode"] - (first_episode_num - 1),
      "video_path": video_path
    })


def get_episode_list_page(anime_session: str, page: int):
  return requests.get(URL_API_BASE + f"release&sort=episode_asc&page={page}&id={anime_session}",cookies=COOKIES) 

def get_episode_list(anime_session: str):
  episode_list = []

  request = get_episode_list_page(anime_session, 1)
  response = request.json()

  episode_list.extend(response["data"])

  if response["last_page"] == 1:
    return episode_list
  
  for i in range(1, response["last_page"]):
    episode_list.extend(get_episode_list_page(anime_session, i)["data"])

  return episode_list

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
