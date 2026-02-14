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
    logger.info(f"retrieving info for game {game_id}")
    bgg = _get_bgg_client(bgg)
    game = None
    while game is None:
        try:
            game = bgg.game(game_id=game_id)
        except Exception:
            logger.info("Trying to retrieve again ...")
            continue
    return game


def add_individual_to_group_ratings(master_dict, user_dict):
    """combine a user's ratings with the overall ratings"""
    for game, rating in user_dict.items():
        if game in master_dict:
            master_dict[game].append(rating)
        else:
            master_dict[game] = [rating]


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
    work_queue = Queue()
    retry_queue = Queue()
    failed = list()
    for member in members:
        work_queue.put(member)
    while not work_queue.empty():
        logger.info(f"{work_queue.qsize()} members to process")
        member = work_queue.get()
        logger.info(f"retrieving data for {member}")
        try:
            user_ratings = get_user_ratings(member, bgg=bgg)
            logger.info(f"data retrieved for {member}")
        except Exception as e:
            if str(e) == "Invalid username specified":
                logger.info(f"invalid username: {member}")
                failed.append(member)
            else:
                logger.info(e)
                logger.info(f"request queued for {member}")
                retry_queue.put(member)
            continue
        all_member_ratings[member] = user_ratings
    while not retry_queue.empty():
        logger.info(f"{retry_queue.qsize()} members to retry")
        member = retry_queue.get()
        logger.info(f"retrieving data for {member}")
        try:
            user_ratings = get_user_ratings(member, bgg=bgg)
        except Exception:
            logger.info(f"no data available for {member}")
            failed.append(member)
            continue
        all_member_ratings[member] = user_ratings
    logger.info(f"could not retrieve ratings for {len(failed)} users\n"
                f"{failed}")
    return all_member_ratings, failed


def collapse_ratings(member_ratings):
    guild_ratings = dict()
    for _, ratings in member_ratings.items():
        add_individual_to_group_ratings(guild_ratings, ratings)
    return guild_ratings


def _build_game_list(games, limit, game_infos, bgg, sort_key, reverse=True):
    games.sort(key=sort_key, reverse=reverse)
    result = []
    count = 0
    for game in games:
        gameid = str(game[0])
        try:
            info = game_infos[gameid]
            logger.info(f"read info for game {gameid} from cache")
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            info = {"name": game_info.name, "expansion": game_info.expansion}
            game_infos[gameid] = info

        if not info["expansion"]:
            count += 1
            result.append((info["name"], game[0], game[1], game[2], game[3]))

        if count >= limit:
            break
    return result


def main(b, n, s, guild, concat=False,
         raw_data=None, prune=False, users=None):
    if users is None or concat is True:
        if guild == "hc":
            guild_id = HEAVY_CARDBOARD
        elif guild == "pc":
            guild_id = PUNCHING_CARDBOARD
        elif guild == "uk":
            guild_id = UNKNOWNS
        elif guild == "test":
            guild_id = TEST
        else:
            guild_id = guild
        logger.info(f"guild: {guild} => id: {guild_id}")
    bgg = _get_bgg_client()
    # if not users and not raw_data: get users + user ratings, process ratings
    # if users and not raw_data: load users, get user ratings, process ratings
    # if raw data: load users + user ratings, process ratings
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    if raw_data is None:
        if concat is False:
            # load members from file or query for current list
            if users is None:
                members = get_guild_user_list(guild_id, bgg=bgg)
                with open(f"members_{date_str}.txt", "w") as of:
                    for member in members:
                        print(member, file=of)
            else:
                members = load_members_from_file(users)
                members = [member.lower() for member in members]
                members = sorted(set(members))
        else:
            # concatenate members from file and guild members
            members_file = load_members_from_file(users)
            members_guild = get_guild_user_list(guild_id, bgg=bgg)
            members = members_file + members_guild
            members = [member.lower() for member in members]
            members = sorted(set(members))
            with open(f"members_{date_str}.txt", "w") as of:
                for member in members:
                    print(member, file=of)

        member_ratings, invalid_users = get_all_ratings(members, bgg=bgg)
        guild_size = len(members) - len(invalid_users)
        logger.info(f"members list loaded: {guild_size} members")
        guild_ratings = collapse_ratings(member_ratings)

        logger.info("processing results ...")
        logger.info(f"{len(guild_ratings)} games rated")
        all_games = list()
        for game_id, ratings in guild_ratings.items():
            num_ratings = len(ratings)
            avg_rating = round(mean(ratings), 3)
            if num_ratings > 1:
                sd_ratings = round(stdev(ratings), 3)
            else:
                sd_ratings = 0
            all_games.append((game_id, num_ratings, avg_rating, sd_ratings))

        all_games.sort(key=lambda x: x[2], reverse=True)

        # dump raw data into files
        current_time_str = str(datetime.datetime.now())
        rating_data = dict()
        rating_data[SUMMARY] = {GUILD_MEMBER_COUNT: guild_size,
                                TOTAL_GAMES: len(guild_ratings),
                                TIME: current_time_str
                                }
        rating_data[MEMBERS] = members
        rating_data[SORTED_GAMES] = all_games
        with open(f"guild_data_{date_str}.json", "w") as raw_data_file:
            json.dump(rating_data, raw_data_file)
            logger.info(f"guild data saved to guild_data_{date_str}.json")
        with open(f"member_data_{date_str}.yml", "w") as raw_data_file:
            yaml.dump(member_ratings, raw_data_file)
            logger.info(f"member ratings saved to member_data_{date_str}.yml")
    elif raw_data is not None:
        rating_data = json.load(open(raw_data, "r"))

    # either path we now have rating_data
    all_games = rating_data[SORTED_GAMES]
    member_count = rating_data[SUMMARY][GUILD_MEMBER_COUNT]

    # if we want to prune the games
    if prune is True:
        pruned_games = list()
        with open(prune, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                gameid = int(row[0])
                matches = [x for x in all_games if x[0] == gameid]
                if len(matches) == 1:
                    match = matches[0]
                    matched_game = (
                        row[1], match[0], match[1], match[2], match[3])
                elif len(matches) == 0:
                    matched_game = (row[1], gameid, 0, 0, 0)
                else:
                    logger.error("could not read pruned_games")
                    return
                pruned_games.append(matched_game)
        pruned_games.sort(key=lambda x: x[3], reverse=True)

        max_name_width = max([len(game[0]) for game in pruned_games])
        for idx, game in enumerate(pruned_games):
            print(f"{idx + 1:2} {game[0]:{max_name_width}} {game[2]:3} "
                  f"{game[3]:5.3f} {game[4]:5.3f}")
        return
    else:
        top_games = [x for x in all_games if x[1] >= 0.1 * member_count]
        sleeper_games = [
            x for x in all_games
            if x[1] < 0.1 * member_count
            and x[1] >= 0.02 * member_count
            and x[2] >= 7.5]

    # get game infos from file if possible, else create dict
    filename = "game_infos.json"
    try:
        with open(filename, "r") as fi:
            game_infos = json.load(fi)
    except IOError:
        logger.error(f"could not open {filename}, creating new dict()")
        game_infos = dict()

    # get the lists
    logger.info("get top games")
    top = _build_game_list(top_games, n, game_infos, bgg, lambda x: x[2], True)

    logger.info("get bottom games")
    bottom = _build_game_list(top_games, b, game_infos, bgg, lambda x: x[2], False)

    logger.info("get most varied games")
    variance = _build_game_list(top_games, b, game_infos, bgg, lambda x: x[3], True)

    logger.info("get most similar games")
    similar = _build_game_list(top_games, b, game_infos, bgg, lambda x: x[3], False)

    logger.info("get most rated games")
    most_rated = _build_game_list(top_games, b, game_infos, bgg, lambda x: x[1], True)

    logger.info("get sleepers")
    sleepers = _build_game_list(sleeper_games, s, game_infos, bgg, lambda x: x[2], True)

    # save game_infos
    with open(filename, "w") as fi:
        json.dump(game_infos, fi)

    # save lists
    lists_dict = dict()
    lists_dict["lists"] = []
    lists_dict["lists"].append(
        {"category": "top", "count": n, "games": top})
    lists_dict["lists"].append(
        {"category": "bottom", "count": b, "games": bottom})
    lists_dict["lists"].append({
        "category": "variance", "count": b, "games": variance})
    lists_dict["lists"].append(
        {"category": "similar", "count": b, "games": similar})
    lists_dict["lists"].append({
        "category": "most_rated", "count": b, "games": most_rated})
    lists_dict["lists"].append(
        {"category": "sleepers", "count": s, "games": sleepers})
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

    main(
        b=args.b,
        concat=args.concat,
        guild=args.guild,
        n=args.n,
        prune=args.prune,
        raw_data=args.raw,
        s=args.s,
        users=args.users)