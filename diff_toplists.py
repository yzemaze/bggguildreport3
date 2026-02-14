import argparse
import datetime
import json
import logging
from pathlib import Path
import diff_utils

# Initialize module-level logger
logger = logging.getLogger(__name__)

# Constants for JSON data structure
LISTS_KEY = "lists"
GAMES_KEY = "games"


def main():
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Print top x with diffs in a pretty format")
    parser.add_argument("old", help="old top file")
    parser.add_argument("new", help="new top file")
    parser.add_argument("--style", default="html", help="output format: bbcode|bgg|html - default: html")
    parser.add_argument("--lang", default="en", help="language for headlines and tableheaders - default: en")
    args = parser.parse_args()

    _ = diff_utils.setup_translation("diff_toplists", args.lang)

    if args.style in ("bgg", "bbcode"):
        style, ext = args.style, "txt"
    else:
        style, ext = "html", "html"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    filename = Path(f"topdiff_{date_str}.{ext}")

    try:
        with open(args.old, "r", encoding="utf-8") as oldf:
            old_lists = json.load(oldf)
        with open(args.new, "r", encoding="utf-8") as newf:
            new_lists = json.load(newf)
    except Exception as e:
        logger.error(f"error loading input files: {e}")
        exit(1)

    new_top = new_lists[LISTS_KEY][0][GAMES_KEY]
    old_top = old_lists[LISTS_KEY][0][GAMES_KEY]
    
    headline = _("Top Diff")
    ths = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]

    diffs = diff_utils.calculate_diffs(old_top, new_top)

    with open(filename, "w", encoding="utf-8") as of:
        diff_utils.print_list(diffs, headline, style, of, ths)

    logger.info(f"+/- saved to {filename}")


if __name__ == "__main__":
    main()