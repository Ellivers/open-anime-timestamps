import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Create a database of anime theme timestamps.")
parser.add_argument("-s", "--silent", dest="silent", action="store_true", help="disable logging")
parser.add_argument("-sa", "--skip-aggregation", dest="skip_aggregation", action="store_true", help="skips the first loop that aggregates timestamps from other databases")
parser.add_argument("-sk", "--skip-known", dest="skip_known", action="store_true", help="skips episodes that are already stored in the database")
parser.add_argument("-sm", "--skip-movies", dest="skip_movies", action="store_true", help="skips movie entries (>40 minutes long)")
parser.add_argument("-asi", "--aggregation-start-id", dest="aggregation_start", type=int, help="set the start ID for the first, aggregation, loop")
parser.add_argument("-ssi", "--scrape-start-id", dest="scrape_start", type=int, help="set the start ID for the second, scraping, loop")
parser.add_argument("-smr", "--scrape-max-retry", dest="scrape_max_retry", type=int, help="change the max retry count for episode scraping. Default 10")
parser.add_argument("-ems", "--episodes-max-size", dest="episodes_max_size", type=int, default=10240, help="threshold for size of episodes on disk before they are processed (in MiB). Default 10GiB (10240 MiB)")
parser.add_argument("-cdb", "--combine-database", dest="combine_database", type=Path, help="adds timestamps from the specified JSON file to the existing database, then exits")

parsed_args = parser.parse_args()