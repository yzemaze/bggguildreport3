import argparse
import datetime
import gettext
import json
import logging
from pathlib import Path

# Initialize module-level logger
logger = logging.getLogger(__name__)


def calculate_diffs(old_list, new_list):
    """Calculate differences between old and new lists."""
    old_lookup = {game[1]: (idx, game[2], game[3]) for idx, game in enumerate(old_list)}
    diffs = []
    for index, game_info in enumerate(new_list):
        old_data = old_lookup.get(game_info[1])
        if old_data:
            old_index, old_rating, old_mean = old_data
            diff_index = f"{old_index - index:>+3}"
            diff_ratings = f"{game_info[2] - old_rating:>+3}"
            diff_mean = f"{game_info[3] - old_mean:+.3f}"
        else:
            diff_index, diff_ratings, diff_mean = "new", "", ""
        
        diffs.append({
            "index": index + 1,
            "diff_index": diff_index,
            "name": game_info[0],
            "ratings": game_info[2],
            "diff_ratings": diff_ratings,
            "mean": game_info[3],
            "diff_mean": diff_mean,
            "sd": game_info[4]
        })
    return diffs


def print_list(diffs, headline, style, of, labels):
    """Print the pre-calculated diffs in the given style."""
    hlevel = "h3"
    
    # Templates for different styles
    templates = {
        "html": {
            "header_start": lambda h: (
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
            "header_start": lambda h: f"[{hlevel}]{h}[/{hlevel}]\n[table]\n[tr]",
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
        print(tpl["header_start"](headline), file=of)
        for th in labels:
            print(tpl["th"](th), end="", file=of)
        print(tpl["header_end"], file=of)

        for d in diffs:
            print(tpl["row_start"], file=of)
            row_data = [
                (d["index"], "right"), (d["diff_index"], "right"), (d["name"], "left"),
                (d["ratings"], "right"), (d["diff_ratings"], "right"),
                (f"{d['mean']:.3f}", "right"), (d["diff_mean"], "right"),
                (f"{d['sd']:.3f}", "right")
            ]
            for val, align in row_data:
                print(tpl["td"](val, align), file=of)
            print(tpl["row_end"], file=of)
        print(tpl["footer"], file=of)
    else:
        # Default text style
        name_width = max(len(d["name"]) for d in diffs) if diffs else 10
        ratings_width = max(len(labels[3]), 4)
        mean_width = max(len(labels[5]), 5)
        print(f"[b]{headline}[/b]\n[c]", file=of)
        print(f"{labels[0]:3} {labels[1]:5} {labels[2]:{name_width}} "
              f"{labels[3]:{ratings_width}} {labels[4]:6} "
              f"{labels[5]:{mean_width}} {labels[6]:9} {labels[7]:5}", file=of)

        for d in diffs:
            print(f"{d['index']:3} {d['diff_index']:5} "
                  f"{d['name']:{name_width}} "
                  f"{d['ratings']:{ratings_width}} {d['diff_ratings']:6} "
                  f"{d['mean']:{mean_width}.3f} {d['diff_mean']:8} "
                  f"{d['sd']:6.3f}", file=of)
        print("[/c]", file=of)


def main():
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Print lists with diffs in a pretty format")
    parser.add_argument("old_file", help="file with old lists")
    parser.add_argument("new_file", help="file with new lists")
    parser.add_argument("--style", default="html", help="output format: bbcode|bgg|html - default: html")
    parser.add_argument("--lang", default="en", help="language for headlines and tableheaders - default: en")
    args = parser.parse_args()

    locales_dir = Path("locales")
    if locales_dir.exists():
        try:
            lang = gettext.translation("diff_lists", localedir=str(locales_dir), languages=[args.lang])
            lang.install()
            _ = lang.gettext
        except Exception:
            logger.warning(f"translation for {args.lang} not found, using default")
            _ = lambda s: s
    else:
        logger.warning("locales directory not found, using default translations")
        _ = lambda s: s

    if args.style in ("bgg", "bbcode"):
        style, ext = args.style, "txt"
    else:
        style, ext = "html", "html"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    diff_file = Path(f"diff_{date_str}.{ext}")

    try:
        with open(args.old_file, "r", encoding="utf-8") as oldf:
            old_lists_raw = json.load(oldf)
        with open(args.new_file, "r", encoding="utf-8") as newf:
            new_lists_raw = json.load(newf)
    except Exception as e:
        logger.error(f"error loading input files: {e}")
        exit(1)

    old_lists_map = {lst["category"]: lst["games"] for lst in old_lists_raw.get("lists", [])}
    category_headlines = {
        "top": _("Top"), "bottom": _("Bottom"), "variance": _("Most Varied"),
        "similar": _("Most Similar"), "most_rated": _("Most Rated"), "sleepers": _("Sleepers")
    }
    ths = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]

    with open(diff_file, "w", encoding="utf-8") as of:
        for new_list_data in new_lists_raw.get("lists", []):
            category = new_list_data.get("category")
            if not category: continue
            
            headline = category_headlines.get(category, category.capitalize())
            old_games = old_lists_map.get(category, [])
            
            diffs = calculate_diffs(old_games, new_list_data["games"])
            print_list(diffs, headline, style, of, ths)
            logger.info(f"formatted printing of {headline} done")

    logger.info(f"+/- saved to {diff_file}")


if __name__ == "__main__":
    main()