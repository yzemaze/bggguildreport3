import argparse
import datetime
import json
import logging
from pathlib import Path
import diff_utils


def print_list(category, games, headline, count, style, of):
    """print list per category in given style to file."""
    hlevel = "h3"
    ths = [_("No."), _("Game"), _("Ratings"), _("Mean"), _("Stdev")]

    json_data = games
    if style == "html":
        print(f"<{hlevel}>{headline}</{hlevel}>", file=of)
        print(f"<table id={category.replace(' ', '_')}>\n<thead>\n<tr>", file=of)
        for i, th in enumerate(ths):
            print(f"<th>{th}</th>", file=of)
        print("</tr>\n</thead>\n<tbody>", file=of)
        for idx, game in enumerate(json_data):
            print(f"<tr>\n"
                  f"<td class=\"text-right\">{idx + 1}</td>\n"
                  f"<td>{game[0]}</td>\n"
                  f"<td class=\"text-right\">{game[2]}</td>\n"
                  f"<td class=\"text-right\">{game[3]:.3f}</td>\n"
                  f"<td class=\"text-right\">{game[4]:.3f}</td>\n"
                  f"</tr>",
                  file=of)
        print("</tbody>\n</table>", file=of)
    elif style == "bbcode":
        print(f"[{hlevel}]{headline}[/{hlevel}]", file=of)
        print("[table]\n[tr]", file=of)
        for i, th in enumerate(ths):
            print(f"[th]{th}[/th]", file=of)
        print("[/tr]", file=of)
        for idx, game in enumerate(json_data):
            print(f"[tr]\n"
                  f"[td]{idx+1:2}[/td]\n"
                  f"[td]{game[0]}[/td]\n"
                  f"[td]{game[2]:2}[/td]\n"
                  f"[td]{game[3]:5.3f}[/td]\n"
                  f"[td]{game[4]:5.3f}[/td]\n"
                  f"[/tr]",
                  file=of)
        print("[/table]", file=of)
    else:
        # bgg-style
        max_name_width = max([len(game[0]) for game in json_data])
        print(f"\n[b]{headline}[/b]\n[c]", file=of)
        for idx, game in enumerate(json_data):
            print(f"{idx + 1:2} {game[0]:{max_name_width}} {game[2]:3} "
                  f"{game[3]:5.3f} {game[4]:5.3f}", file=of)
        print("[/c]", file=of)


if __name__ == "__main__":
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(
        description="Process file to print in a pretty format")
    parser.add_argument(
        "filename",
        help="file to format")
    parser.add_argument(
        "--style",
        default="html",
        help="output format: bbcode|bgg|html - default: html")
    parser.add_argument(
        "--lang",
        default="en",
        help="language used for headlines and tableheaders")
    args = parser.parse_args()

    _ = diff_utils.setup_translation("print_lists", args.lang)

    with open(args.filename) as f:
        data = json.load(f)
        logger.info(f"loaded {args.filename}")

        if (args.style == "bgg") or (args.style == "bbcode"):
            style = args.style
            ext = "txt"
        else:
            style = "html"
            ext = "html"

        date_str = datetime.datetime.now().strftime("%Y%m%d")
        filename = f"output_{date_str}.{ext}"
        
        category_headlines = {
            "top": _("Top"),
            "bottom": _("Bottom"),
            "variance": _("Most Varied"),
            "similar": _("Most Similar"),
            "most_rated": _("Most Rated"),
            "sleepers": _("Sleepers")
        }

        with open(filename, "w") as of:
            if style == "html":
                print(f"<style>\n"
                      f".text-right {{text-align: right; padding: 0 5px;}}\n"
                      f"</style>", file=of)
            
            for d in data["lists"]:
                category = d["category"]
                headline = category_headlines.get(category, category.capitalize())
                print_list(category, d["games"],
                           headline, d["count"], style, of)
                logger.info(f"formatted printing of {headline} done")

    logger.info(f"formatted lists saved to {filename}")