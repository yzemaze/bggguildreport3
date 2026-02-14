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
        description="Print top x with diffs in a pretty format")
    parser.add_argument("old", help="old top file")
    parser.add_argument("new", help="new top file")
    parser.add_argument("--style", default="html", help="output format: bbcode|bgg|html - default: html")
    parser.add_argument("--lang", default="en", help="language for headlines and tableheaders - default: en")
    args = parser.parse_args()

    locales_dir = Path("locales")
    if locales_dir.exists():
        try:
            lang = gettext.translation("diff_toplists", localedir=str(locales_dir), languages=[args.lang])
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
    filename = Path(f"topdiff_{date_str}.{ext}")

    try:
        with open(args.old, "r", encoding="utf-8") as oldf:
            old_lists = json.load(oldf)
        with open(args.new, "r", encoding="utf-8") as newf:
            new_lists = json.load(newf)
    except Exception as e:
        logger.error(f"error loading input files: {e}")
        exit(1)

    new_top = new_lists["lists"][0]["games"]
    old_top = old_lists["lists"][0]["games"]
    
    headline = _("Top Diff")
    ths = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]

    diffs = diff_utils.calculate_diffs(old_top, new_top)

    with open(filename, "w", encoding="utf-8") as of:
        diff_utils.print_list(diffs, headline, style, of, ths)

    logger.info(f"+/- saved to {filename}")


if __name__ == "__main__":
    main()