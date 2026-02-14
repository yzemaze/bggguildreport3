import yaml
from pathlib import Path
def calculate_similarity(user_data, other_ratings):
    user_game_ids = set(user_data.keys())
    common_games = user_game_ids & set(other_ratings.keys())
    score = sum((user_data[gid] - other_ratings[gid])**2 for gid in common_games)
    return score, len(common_games)


def main(user, member_data_file):
    with open(member_data_file, "r") as data_file:
        member_data = yaml.safe_load(data_file)

    if user not in member_data:
        print(f"Error: User '{user}' not found in member data.")
        return

    user_data = member_data[user]
    del member_data[user]
    user_collection_size = len(user_data)

    member_scores = list()
    for member_user, ratings in member_data.items():
        score, games_in_common = calculate_similarity(user_data, ratings)
        member_scores.append(
            {"user": member_user, "score": score, "common": games_in_common})

    member_scores = [x for x in member_scores if x[
        "common"] >= 0.5 * user_collection_size]
    member_scores.sort(key=lambda x: x["score"])

    output_path = Path(f"{user}_followers.yml")
    with output_path.open("w") as fo:
        yaml.dump(member_scores, fo)

    for i in range(min(5, len(member_scores))):
        member = member_scores[i]
        print(member["user"], member["score"], member["common"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--member-data")
    args = parser.parse_args()
    main(args.user, args.member_data)
