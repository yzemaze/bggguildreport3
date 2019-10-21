import argparse
import datetime
import gettext
import json


def print_list(old_file, new_file, style):

    with open(old_file, "r") as of:
        old_lists = json.load(of)
        of.close()
        with open(new_file, "r") as nf:
            new_lists = json.load(nf)
            nf.close()

            new_top50 = new_lists["top50"]
            old_top50 = old_lists["top50"]

            old_top50_gameids = [x[1] for x in old_top50]

            name_width = max([len(x[0]) for x in new_top50])
            format_string = "{:2} ({:3}). {:" + str(name_width) + \
                "} {:3} {:5.3f} {:5.3f}"

            for index, game_info in enumerate(new_top50):
                try:
                    old_index = old_top50_gameids.index(game_info[1])
                except ValueError:
                    old_index = -1

                if old_index > -1:
                    diff = old_index - index
                    if diff > -1:
                        diff_string = "+" + str(diff)
                    else:
                        diff_string = str(diff)
                else:
                    diff_string = "new"

                detail_string = format_string.format(index + 1,
                                                     diff_string,
                                                     game_info[0],
                                                     game_info[2],
                                                     game_info[3],
                                                     game_info[4])
                print(detail_string)

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(
        description="Print top50 with diffs in a pretty format")
    parser.add_argument(
        "old",
        help="old top50 file")
    parser.add_argument(
        "new",
        help="new top50 file")
    parser.add_argument(
        "--style",
        default="html",
        help="output format: bbcode|bgg|html - default: html")
    parser.add_argument(
        "--lang",
        default="en",
        help="language used for headlines and tableheaders")
    args = parser.parse_args()

    lang = gettext.translation("base", localedir="locales",
                               languages=[args.lang])
    lang.install()
    _ = lang.gettext

    if (args.style == "bgg") or (args.style == "bbcode"):
        style = args.style
        ext = "txt"
    else:
        style = "html"
        ext = "html"
    print_list(args.old, args.new, style)
