import argparse
import datetime
import gettext
import json
import logging
from pathlib import Path
import diff_utils

# Initialize module-level logger
logger = logging.getLogger(__name__)


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
            
            diffs = diff_utils.calculate_diffs(old_games, new_list_data["games"])
            diff_utils.print_list(diffs, headline, style, of, ths)
            logger.info(f"formatted printing of {headline} done")

    logger.info(f"+/- saved to {diff_file}")


if __name__ == "__main__":
    main()