import yaml
def main(user, member_data_file):
    with open(member_data_file, "r") as data_file:
        member_data = yaml.safe_load(data_file)

    user_data = member_data[user]
    del member_data[user]
    user_collection_size = len(user_data)

    member_scores = list()
    user_game_ids = set(user_data.keys())
    for member_user, ratings in member_data.items():
        common_games = user_game_ids & set(ratings.keys())
        score = sum((user_data[gid] - ratings[gid])**2 for gid in common_games)
        games_in_common = len(common_games)
        member_scores.append(
            {"user": member_user, "score": score, "common": games_in_common})

    member_scores = [x for x in member_scores if x[
        "common"] >= 0.5 * user_collection_size]
    member_scores.sort(key=lambda x: x["score"])

    filename = user + "_followers.yml"
    with open(filename, "w") as fo:
        yaml.dump(member_scores, fo)

    for i in range(5):
        member = member_scores[i]
        print(member["user"], member["score"], member["common"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--member-data")
    args = parser.parse_args()
    main(args.user, args.member_data)
