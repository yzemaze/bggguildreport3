# get the top games for a BGG guild
#
# This was written for pulling the top games from the Heavy Cardboard
# BGG Guild.
#
# TODO: pydoc strings
# TODO: implement pastable report

import argparse
import csv
import datetime
import json
import logging
import math
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from queue import Queue
from statistics import mean, stdev
import yaml

from boardgamegeek import BGGClient

# load XML API token from .env
load_dotenv()
API_TOKEN = os.getenv("BGG_API_TOKEN")
if not API_TOKEN:
    raise ValueError("No BGG_API_TOKEN found.")
print("Token loaded successfully.")

# requests per minute
RPM = 6

# guild ids
HEAVY_CARDBOARD = 2044
PUNCHING_CARDBOARD = 1805
UNKNOWNS = 3422
TEST = 2387

# dictionary keys
SORTED_GAMES = "sorted_games"
SUMMARY = "summary"
TOTAL_GAMES = "total_games_rated"
GUILD_MEMBER_COUNT = "guild_members"
MEMBERS = "members"
TIME = "time_at_generation"

### functions that retrieve from BGG ###


def _get_bgg_client(bgg=None):
    if bgg is None:
        return BGGClient(API_TOKEN, requests_per_minute=RPM)
    return bgg


def get_guild_user_list(guild_id, bgg=None):
    """retrieve the member list for a BGG guild"""
    bgg = _get_bgg_client(bgg)
    logger.info("retrieving guild user list")
    guild = bgg.guild(guild_id)
    return list(guild.members)


def get_user_ratings(username, bgg=None):
    """returns a dict: gameid -> rating"""
    bgg = _get_bgg_client(bgg)
    user_ratings = dict()
    collection = bgg.collection(username, rated=True)
    print(collection)
    for item in collection:
        if item.rating:
            user_ratings[item.id] = item.rating
    return user_ratings


def get_game_info(game_id, bgg=None):
    """retrieve the BGG info for game having game_id"""
    res = get_game_info_batch([game_id], bgg)
    return res[0] if res else None


def get_game_info_batch(game_ids, bgg=None):
    """retrieve the BGG info for a list of game_ids"""
    if not game_ids:
        return []
    logger.info(f"retrieving info for {len(game_ids)} games")
    bgg = _get_bgg_client(bgg)
    games = []
    chunk_size = 20
    MAX_RETRIES = 5
    
    for i in range(0, len(game_ids), chunk_size):
        chunk = game_ids[i:i + chunk_size]
        retries = 0
        while retries < MAX_RETRIES:
            try:
                games.extend(bgg.game_list(chunk))
                break
            except Exception as e:
                retries += 1
                wait_time = 2 ** retries
                logger.info(f"Error retrieving chunk (attempt {retries}/{MAX_RETRIES}): {e}. Waiting {wait_time}s...")
                time.sleep(wait_time)
        else:
            logger.error(f"Failed to retrieve games after {MAX_RETRIES} attempts: {chunk}")
            
    return games


def add_individual_to_group_ratings(master_dict, user_dict):
    """combine a user's ratings with the overall ratings"""
    for game, rating in user_dict.items():
        master_dict[game].append(rating)


def load_members_from_file(filename):
    members = list()
    fi = open(filename, "r")
    for line in fi.readlines():
        members.append(line.strip())
    return members


def get_all_ratings(members, bgg=None):
    """get the ratings for all users in the list members
        returns: a dict (gameid, game name) -> list of ratings
        and a list of users which data was not available
    """
    bgg = _get_bgg_client(bgg)
    all_member_ratings = dict()
    logger.info("retrieving user ratings ...")
    
    failed = list()
    
    def fetch_user(member):
        logger.info(f"retrieving data for {member}")
        try:
            user_ratings = get_user_ratings(member, bgg=bgg)
            logger.info(f"data retrieved for {member}")
            return member, user_ratings
        except Exception as e:
            if str(e) == "Invalid username specified":
                logger.info(f"invalid username: {member}")
                failed.append(member)
            else:
                logger.info(f"error retrieving {member}: {e}")
                failed.append(member)
            return member, None

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_user, members))
    
    for member, ratings in results:
        if ratings is not None:
            all_member_ratings[member] = ratings
            
    logger.info(f"could not retrieve ratings for {len(failed)} users\n"
                f"{failed}")
    return all_member_ratings, failed


def collapse_ratings(member_ratings):
    guild_ratings = defaultdict(list)
    for _, ratings in member_ratings.items():
        add_individual_to_group_ratings(guild_ratings, ratings)
    return guild_ratings


def prefetch_game_info(games_to_fetch, game_infos, bgg):
    """identify missing game IDs and fetch them in one batch"""
    missing_ids = [int(gid) for gid in games_to_fetch if str(gid) not in game_infos]
    if missing_ids:
        logger.info(f"pre-fetching {len(missing_ids)} missing games info")
        fetched_games = get_game_info_batch(missing_ids, bgg)
        for g in fetched_games:
            game_infos[str(g.id)] = {"name": g.name, "expansion": g.expansion}


def _build_game_list(games, limit, game_infos, bgg, sort_key, reverse=True):
    games.sort(key=sort_key, reverse=reverse)
    result = []
    count = 0
    for game in games:
        gameid = str(game[0])
        info = game_infos.get(gameid)
        if not info:
            # Should have been pre-fetched, but fallback just in case
            game_info = get_game_info(gameid, bgg)
            if game_info:
                info = {"name": game_info.name, "expansion": game_info.expansion}
                game_infos[gameid] = info
            else:
                continue

        if not info["expansion"]:
            count += 1
            result.append((info["name"], game[0], game[1], game[2], game[3]))

        if count >= limit:
            break
    return result


def get_guild_members(guild_id, users_file=None, concat=False, bgg=None):
    """load members from file and/or query for current list"""
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    if users_file is None:
        members = get_guild_user_list(guild_id, bgg=bgg)
    elif concat:
        members_file = load_members_from_file(users_file)
        members_guild = get_guild_user_list(guild_id, bgg=bgg)
        members = members_file + members_guild
    else:
        members = load_members_from_file(users_file)

    members = sorted(list(set(m.lower() for m in members)))

    if users_file is None or concat:
        with open(f"members_{date_str}.txt", "w") as of:
            for member in members:
                print(member, file=of)

    return members


def process_guild_ratings(members, bgg=None):
    """fetch ratings for all members and collapse them into guild ratings"""
    member_ratings, invalid_users = get_all_ratings(members, bgg=bgg)
    guild_size = len(members) - len(invalid_users)
    logger.info(f"members list loaded: {guild_size} members")
    guild_ratings = collapse_ratings(member_ratings)
    
    logger.info("processing results ...")
    all_games = []
    for game_id, ratings in guild_ratings.items():
        num_ratings = len(ratings)
        avg_rating = round(mean(ratings), 3)
        sd_ratings = round(stdev(ratings), 3) if num_ratings > 1 else 0
        all_games.append((game_id, num_ratings, avg_rating, sd_ratings))
    
    all_games.sort(key=lambda x: x[2], reverse=True)
    return all_games, member_ratings, guild_size


def export_results(rating_data, member_ratings, date_str):
    """save guild data and member ratings to files"""
    with open(f"guild_data_{date_str}.json", "w") as f:
        json.dump(rating_data, f)
        logger.info(f"guild data saved to guild_data_{date_str}.json")
    with open(f"member_data_{date_str}.yml", "w") as f:
        yaml.dump(member_ratings, f)
        logger.info(f"member ratings saved to member_data_{date_str}.yml")


def main(b, n, s, guild, concat=False,
         raw_data=None, prune=False, users=None):
    # Resolve guild ID
    guild_map = {"hc": HEAVY_CARDBOARD, "pc": PUNCHING_CARDBOARD, "uk": UNKNOWNS, "test": TEST}
    guild_id = guild_map.get(guild, guild)
    logger.info(f"guild: {guild} => id: {guild_id}")
    
    bgg = _get_bgg_client()
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    
    if raw_data is None:
        members = get_guild_members(guild_id, users, concat, bgg)
        all_games, member_ratings, guild_size = process_guild_ratings(members, bgg)
        
        rating_data = {
            SUMMARY: {GUILD_MEMBER_COUNT: guild_size, TOTAL_GAMES: len(all_games), TIME: str(datetime.datetime.now())},
            MEMBERS: members,
            SORTED_GAMES: all_games
        }
        export_results(rating_data, member_ratings, date_str)
    else:
        with open(raw_data, "r") as f:
            rating_data = json.load(f)
        all_games = rating_data[SORTED_GAMES]
        guild_size = rating_data[SUMMARY][GUILD_MEMBER_COUNT]

    if prune:
        # Pruning logic
        pruned_games = []
        with open(prune, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                gameid = int(row[0])
                matches = [x for x in all_games if x[0] == gameid]
                match = matches[0] if matches else (gameid, 0, 0, 0)
                pruned_games.append((row[1], match[0], match[1], match[2], match[3]))
        
        pruned_games.sort(key=lambda x: x[3], reverse=True)
        max_name_width = max(len(g[0]) for g in pruned_games)
        for idx, g in enumerate(pruned_games):
            print(f"{idx + 1:2} {g[0]:{max_name_width}} {g[2]:3} {g[3]:5.3f} {g[4]:5.3f}")
        return

    # Filter games
    member_count = rating_data[SUMMARY][GUILD_MEMBER_COUNT]
    top_games = [x for x in all_games if x[1] >= 0.1 * member_count]
    sleeper_games = [x for x in all_games if 0.02 * member_count <= x[1] < 0.1 * member_count and x[2] >= 7.5]

    # Load cache
    filename = "game_infos.json"
    try:
        with open(filename, "r") as fi:
            game_infos = json.load(fi)
    except IOError:
        game_infos = {}

    # Identify all candidate games to pre-fetch their info
    candidates = set()
    for g in top_games:
        candidates.add(g[0])
    for g in sleeper_games:
        candidates.add(g[0])
    
    prefetch_game_info(candidates, game_infos, bgg)

    # Build lists
    logger.info("building game lists")
    lists = [
        ("top", n, top_games, lambda x: x[2], True),
        ("bottom", b, top_games, lambda x: x[2], False),
        ("variance", b, top_games, lambda x: x[3], True),
        ("similar", b, top_games, lambda x: x[3], False),
        ("most_rated", b, top_games, lambda x: x[1], True),
        ("sleepers", s, sleeper_games, lambda x: x[2], True)
    ]
    
    lists_dict = {"lists": []}
    for category, count, source, key, rev in lists:
        logger.info(f"get {category} games")
        result = _build_game_list(source, count, game_infos, bgg, key, rev)
        lists_dict["lists"].append({"category": category, "count": count, "games": result})

    # Final save
    with open(filename, "w") as fi:
        json.dump(game_infos, fi)
    
    with open(f"lists_{date_str}.json", "w") as fi:
        json.dump(lists_dict, fi)
    logger.info(f"games lists saved to lists_{date_str}.json")


if __name__ == "__main__":
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser()
    parser.add_argument(
      "-b", type=int, default=10,
      help="output the bottom, most/least variable & most rated B games")
    parser.add_argument(
      "-c", "--concat",
      action="store_true",
      help="concatenate lists of users and guild members")
    parser.add_argument(
      "-g", "--guild",
      help="guild-id or one of [hc, pc, uk, test]")
    parser.add_argument(
      "-n", type=int, default=50,
      help="output the top N games, default=50")
    parser.add_argument(
      "-p", "--prune",
      action="store_true",
      help="prune raw data to a specific list of games")
    parser.add_argument(
      "-r", "--raw",
      help="RAW = guild_data_YYYYMMDD.json to regenerate final data")
    parser.add_argument(
      "-s", type=int, default=50,
      help="output the top S sleepers, default=50")
    parser.add_argument(
      "-u", "--users",
      help="use provided file of users instead of pulling a new one")
    args = parser.parse_args()
    main(b=args.b, concat=args.concat, guild=args.guild, n=args.n,
         prune=args.prune, raw_data=args.raw, s=args.s, users=args.users)