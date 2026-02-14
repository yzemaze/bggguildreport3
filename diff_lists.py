import argparse
import datetime
import gettext
import json
import logging
from pathlib import Path


def print_list(old_list, new_list, headline, style, of):
    """ print list per category in given style with +/- to file."""
    # Create lookup dictionary for old list data: gameid -> (index, ratings, mean)
    old_lookup = {game[1]: (idx, game[2], game[3]) for idx, game in enumerate(old_list)}

    hlevel = "h3"
    ths = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]

    # Templates for different styles
    templates = {
        "html": {
            "header_start": lambda h, ids: (
                f"<style>\n.text-right {{text-align: right; padding: 0 5px;}}\n</style>\n"
                f"<{hlevel}>{h}</{hlevel}>\n"
                f"<table id={h.replace(' ', '_')}>\n<thead>\n<tr>"
            ),
            "th": lambda t: f"<th>{t}</th>",
            "header_end": "</tr>\n</thead>\n<tbody>",
            "row_start": "<tr>",
            "td": lambda v, align="left": f"<td class=\"text-right\">{v}</td>" if align == "right" else f"<td>{v}</td>",
            "row_end": "</tr>",
            "footer": "</tbody>\n</table>"
        },
        "bbcode": {
            "header_start": lambda h, ids: f"[{hlevel}]{h}[/{hlevel}]\n[table]\n[tr]",
            "th": lambda t: f"[th]{t}[/th]",
            "header_end": "[/tr]",
            "row_start": "[tr]",
            "td": lambda v, align="left": f"[td]{v}[/td]",
            "row_end": "[/tr]",
            "footer": "[/table]"
        }
    }

    if style in templates:
        tpl = templates[style]
        print(tpl["header_start"](headline, None), file=of)
        for th in ths:
            print(tpl["th"](th), end="", file=of)
        print(tpl["header_end"], file=of)

        for index, game_info in enumerate(new_list):
            old_data = old_lookup.get(game_info[1])
            if old_data:
                old_index, old_rating, old_mean = old_data
                diff_index = f"{old_index - index:>+3}"
                diff_ratings = f"{game_info[2] - old_rating:>+3}"
                diff_mean = f"{game_info[3] - old_mean:+.3f}"
            else:
                diff_index, diff_ratings, diff_mean = _("new"), "", ""

            print(tpl["row_start"], file=of)
            row_data = [
                (index + 1, "right"), (diff_index, "right"), (game_info[0], "left"),
                (game_info[2], "right"), (diff_ratings, "right"),
                (f"{game_info[3]:.3f}", "right"), (diff_mean, "right"),
                (f"{game_info[4]:.3f}", "right")
            ]
            for val, align in row_data:
                print(tpl["td"](val, align), file=of)
            print(tpl["row_end"], file=of)
        print(tpl["footer"], file=of)
    else:
        # Default text style
        name_width = max(len(x[0]) for x in new_list)
        ratings_width = max(len(ths[3]), 4)
        mean_width = max(len(ths[5]), 5)
        print(f"[b]{headline}[/b]\n[c]", file=of)
        print(f"{ths[0]:3} {ths[1]:5} {ths[2]:{name_width}} "
              f"{ths[3]:{ratings_width}} {ths[4]:6} "
              f"{ths[5]:{mean_width}} {ths[6]:9} {ths[7]:5}", file=of)

        for index, game_info in enumerate(new_list):
            old_data = old_lookup.get(game_info[1])
            if old_data:
                old_index, old_rating, old_mean = old_data
                diff_index = f"{old_index - index:>+3}"
                diff_ratings = f"{game_info[2] - old_rating:>+3}"
                diff_mean = f"{game_info[3] - old_mean:+.3f}"
            else:
                diff_index, diff_ratings, diff_mean = _("new"), "", ""

            print(f"{index+1:3} {diff_index:5} "
                  f"{game_info[0]:{name_width}} "
                  f"{game_info[2]:{ratings_width}} {diff_ratings:6} "
                  f"{game_info[3]:{mean_width}.3f} {diff_mean:8} "
                  f"{game_info[4]:6.3f}", file=of)
        print("[/c]", file=of)

if __name__ == "__main__":
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(
        description="Print lists with diffs in a pretty format")
    parser.add_argument(
        "old_file",
        help="file with old lists")
    parser.add_argument(
        "new_file",
        help="file with new lists")
    parser.add_argument(
        "--style",
        default="html",
        help="output format: bbcode|bgg|html - default: html")
    parser.add_argument(
        "--lang",
        default="en",
        help="language for headlines and tableheaders - default: en")
    args = parser.parse_args()

    locales_dir = Path("locales")
    if locales_dir.exists():
        try:
            lang = gettext.translation("diff_lists", localedir=str(locales_dir),
                                       languages=[args.lang])
            lang.install()
            _ = lang.gettext
        except FileNotFoundError:
            logger.warning(f"translation for {args.lang} not found, using default")
            _ = lambda s: s
    else:
        logger.warning("locales directory not found, using default translations")
        _ = lambda s: s

    if args.style in ("bgg", "bbcode"):
        style = args.style
        ext = "txt"
    else:
        style = "html"
        ext = "html"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    diff_file = Path(f"diff_{date_str}.{ext}")

    try:
        with open(args.old_file, "r", encoding="utf-8") as oldf:
            old_lists_raw = json.load(oldf)

        with open(args.new_file, "r", encoding="utf-8") as newf:
            new_lists_raw = json.load(newf)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"error loading input files: {e}")
        exit(1)

    # Convert old lists to a dictionary for category-based matching
    old_lists_map = {lst["category"]: lst["games"] for lst in old_lists_raw.get("lists", [])}

    # Mapping of category IDs to localized headlines
    category_headlines = {
        "top": _("Top"),
        "bottom": _("Bottom"),
        "variance": _("Most Varied"),
        "similar": _("Most Similar"),
        "most_rated": _("Most Rated"),
        "sleepers": _("Sleepers")
    }

    with open(diff_file, "w", encoding="utf-8") as of:
        for new_list_data in new_lists_raw.get("lists", []):
            category = new_list_data.get("category")
            if not category:
                continue
                
            headline = category_headlines.get(category, category.capitalize())
            
            if category in old_lists_map:
                print_list(old_lists_map[category], new_list_data["games"],
                           headline, style, of)
                logger.info(f"formatted printing of {headline} with +/- done")
            else:
                logger.warning(f"category {category} not found in old data")
                print_list([], new_list_data["games"], headline, style, of)

    logger.info(f"+/- saved to {diff_file}")