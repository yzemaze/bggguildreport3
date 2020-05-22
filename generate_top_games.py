# Get the top games for a BGG Guild
#
# This was written for pulling the top games from the Heavy Cardboard
# BGG Guild.
#
# TODO: Pydoc strings
# TODO: Refactor user retries
# TODO: Implement pastable report
# TODO: Remove dependency on boardgamegeek module to make better queries

import csv
import datetime
import json
import math
from queue import Queue
from statistics import mean, stdev
import yaml

from boardgamegeek import BGGClient

# guild ids
HEAVY_CARDBOARD = 2044
PUNCHING_CARDBOARD = 1805
UNKNOWNS = 3422

# Dictionary Keys
SORTED_GAMES = "sorted_games"
SUMMARY = "summary"
TOTAL_GAMES = "total_games_rated"
GUILD_MEMBER_COUNT = "guild_members"
MEMBERS = "members"
TIME = "time_at_generation"

### Functions that fetch from BGG ###


def get_guild_user_list(guild_id, bgg=None):
    """Fetch the member list for a BGG Guild"""
    if bgg is None:
        bgg = BGGClient()
    print("Fetching guild user list")
    guild = bgg.guild(guild_id)
    return list(guild.members)


def get_user_ratings(username, bgg=None):
    """Returns a dict: gameid -> rating"""
    if bgg is None:
        bgg = BGGClient()
    user_ratings = dict()
    collection = bgg.collection(username)
    print(collection)
    for item in collection:
        if item.rating:
            user_ratings[item.id] = item.rating
    return user_ratings


def get_game_info(game_id, bgg=None):
    """Fetch the BGG info for game having game_id"""
    print("Fetching info for game", str(game_id))
    if bgg is None:
        bgg = BGGClient()
    game = None
    while game is None:
        try:
            game = bgg.game(game_id=game_id)
        except Exception:
            print("Trying to fetch again...")
            continue
    return game


def add_individual_to_group_ratings(master_dict, user_dict):
    """Combine a user's ratings with the overall ratings"""
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
    """Get the ratings for all users in the list members.
        Returns: A dict (gameid, game name) -> list of ratings
    """
    if bgg is None:
        bgg = BGGClient()
    all_member_ratings = dict()
    print("Retrieving user ratings...")
    work_queue = Queue()
    retry_queue = Queue()
    fails = list()
    for member in members:
        work_queue.put(member)
    while not work_queue.empty():
        print(work_queue.qsize(), "members to process")
        member = work_queue.get()
        print("Fetching data for ", member)
        try:
            user_ratings = get_user_ratings(member, bgg=bgg)
        except Exception:
            retry_queue.put(member)
            continue
        all_member_ratings[member] = user_ratings
    while not retry_queue.empty():
        print(retry_queue.qsize(), "members to process")
        member = retry_queue.get()
        print("Fetching data for ", member)
        try:
            user_ratings = get_user_ratings(member, bgg=bgg)
        except Exception:
            print("No data available for ", member)
            fails.append(member)
            continue
        all_member_ratings[member] = user_ratings
    print("Ratings retrieved for all users except", fails)
    return all_member_ratings


def collapse_ratings(member_ratings):
    guild_ratings = dict()
    for _, ratings in member_ratings.items():
        add_individual_to_group_ratings(guild_ratings, ratings)
    return guild_ratings


def main(b, n, s, guild, concat=False,
         raw_data=None, prune=False, users=None):
    if users is None or concat is True:
        if guild == "hc":
            guild_id = HEAVY_CARDBOARD
        elif guild == "pc":
            guild_id = PUNCHING_CARDBOARD
        elif guild == "uk":
            guild_id = UNKNOWNS
        else:
            guild_id = guild
        print("Guild:", guild, "=> id:", guild_id)
    bgg = BGGClient()
    # if not users and not raw_data: get users, get user ratings, process ratings
    # if users and not raw_data: load users, get user ratings, process ratings
    # if raw data: load users, load user ratings, process ratings
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    if raw_data is None:
        if concat is False:
            # load members from file or query for current list
            if users is None:
                members = get_guild_user_list(guild_id, bgg=bgg)
                of = open("members_" + date_str + ".txt", "w")
                for member in members:
                    of.write(member + "\n")
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
            of = open("members_" + date_str + ".txt", "w")
            for member in members:
                of.write(member + "\n")

        guild_size = len(members)
        print("Members list loaded: %d members" % guild_size)
        member_ratings = get_all_ratings(members, bgg=bgg)
        guild_ratings = collapse_ratings(member_ratings)

        print("Processing results...")
        print("%d games rated" % len(guild_ratings))
        all_games = list()
        for game_id, ratings in guild_ratings.items():
            num_ratings = len(ratings)
            avg_rating = round(mean(ratings), 3)
            if num_ratings > 1:
                sd_ratings = round(stdev(ratings), 3)
            else:
                sd_ratings = 0
            all_games.append((game_id, num_ratings, avg_rating, sd_ratings))

        # Sort the list
        all_games.sort(key=lambda x: x[2], reverse=True)

        # Write out the raw data to this point
        current_time_str = str(datetime.datetime.now())
        rating_data = dict()
        rating_data[SUMMARY] = {GUILD_MEMBER_COUNT: guild_size,
                                TOTAL_GAMES: len(guild_ratings),
                                TIME: current_time_str
                                }
        rating_data[MEMBERS] = members
        rating_data[SORTED_GAMES] = all_games
        with open("guild_data_" + date_str + ".json", "w") as raw_data_file:
            json.dump(rating_data, raw_data_file)
        with open("member_data_" + date_str + ".yml", "w") as raw_data_file:
            yaml.dump(member_ratings, raw_data_file)
    elif raw_data is not None:
        rating_data = json.load(open(raw_data, "r"))

    # Either path we now have rating_data
    all_games = rating_data[SORTED_GAMES]
    member_count = rating_data[SUMMARY][GUILD_MEMBER_COUNT]

    # If we want to prune the games
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
                    print("ERROR")
                    return
                pruned_games.append(matched_game)
        pruned_games.sort(key=lambda x: x[3], reverse=True)

        max_name_width = max([len(game[0]) for game in pruned_games])
        format_string_prefix = "{:2} {:"
        format_string_suffix = "} {:3} {:5.3f} {:5.3f}"
        format_string = format_string_prefix + \
            str(max_name_width) + format_string_suffix
        for idx, game in enumerate(pruned_games):
            detail_string = format_string.format(idx + 1,
                                                 game[0],
                                                 game[2],
                                                 game[3],
                                                 game[4])
            print(detail_string)
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
        print("Could not open ", filename, ", creating new dict()", sep="")
        game_infos = dict()

    # Get the top x
    print("TOP")
    top = list()
    top_games.sort(key=lambda x: x[2], reverse=True)
    count_of_printed = 0
    for game in top_games:
        gameid = str(game[0])
        # game_name available from file else load from BGG
        try:
            game_name = game_infos[gameid]["name"]
            print("Read info for game", gameid, "from", filename)
            if not game_infos[gameid]["expansion"]:
                count_of_printed += 1
                top.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                top.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > n - 1:
            break
    # Get the bottom x
    print("BOTTOM")
    bottom = list()
    top_games.sort(key=lambda x: x[2])
    count_of_printed = 0
    for game in top_games:
        gameid = str(game[0])
        try:
            game_name = game_infos[gameid]["name"]
            if not game_infos[gameid]["expansion"]:
                print("Read info for game", gameid, "from", filename)
                count_of_printed += 1
                bottom.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                bottom.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > b - 1:
            break
    # Get the most variable
    print("VARIANCE")
    variance = list()
    top_games.sort(key=lambda x: x[3], reverse=True)
    count_of_printed = 0
    for game in top_games:
        gameid = str(game[0])
        try:
            game_name = game_infos[gameid]["name"]
            if not game_infos[gameid]["expansion"]:
                print("Read info for game", gameid, "from", filename)
                count_of_printed += 1
                variance.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                variance.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > b - 1:
            break
    # Get the least variable
    print("SIMILAR")
    similar = list()
    top_games.sort(key=lambda x: x[3], reverse=False)
    count_of_printed = 0
    for game in top_games:
        gameid = str(game[0])
        try:
            game_name = game_infos[gameid]["name"]
            if not game_infos[gameid]["expansion"]:
                print("Read info for game", gameid, "from", filename)
                count_of_printed += 1
                similar.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                similar.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > b - 1:
            break
    # Get the most rated
    print("MOST RATED")
    most_rated = list()
    top_games.sort(key=lambda x: x[1], reverse=True)
    count_of_printed = 0
    for game in top_games:
        gameid = str(game[0])
        try:
            game_name = game_infos[gameid]["name"]
            if not game_infos[gameid]["expansion"]:
                print("Read info for game", gameid, "from", filename)
                count_of_printed += 1
                most_rated.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                most_rated.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > b - 1:
            break
    # Get sleepers
    print("SLEEPERS")
    sleepers = list()
    sleeper_games.sort(key=lambda x: x[2], reverse=True)
    count_of_printed = 0
    for game in sleeper_games:
        gameid = str(game[0])
        try:
            game_name = game_infos[gameid]["name"]
            if not game_infos[gameid]["expansion"]:
                print("Read info for game", gameid, "from", filename)
                count_of_printed += 1
                sleepers.append(
                    (game_name, game[0], game[1], game[2], game[3]))
        except KeyError:
            game_info = get_game_info(gameid, bgg)
            game_infos[gameid] = {"name": game_info.name,
                                  "expansion": game_info.expansion}
            if not game_info.expansion:
                count_of_printed += 1
                sleepers.append(
                    (game_info.name, game[0], game[1], game[2], game[3]))
        if count_of_printed > s - 1:
            break

    # save game_infos
    with open(filename, "w") as fi:
        json.dump(game_infos, fi)

    # save lists
    lists_dict = dict()
    lists_dict["top50"] = top
    lists_dict["bottom10"] = bottom
    lists_dict["variable10"] = variance
    lists_dict["similar10"] = similar
    lists_dict["most10"] = most_rated
    lists_dict["sleeper10"] = sleepers
    with open("lists_" + date_str + ".json", "w") as fi:
        json.dump(lists_dict, fi)
    print("Finished")

if __name__ == "__main__":
    import argparse

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
        help="guild-id or one of [pc, hc, uk]")
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
        help="use provided list of users instead of pulling a new one")
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
