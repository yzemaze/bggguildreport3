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

    def load_json(file_path):
        p = Path(file_path)
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if LISTS_KEY not in data or not data[LISTS_KEY]:
                logger.error(f"Invalid structure in {file_path}: missing or empty '{LISTS_KEY}'")
                return None
            return data
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path}: {e}")
        return None

    old_lists = load_json(args.old)
    new_lists = load_json(args.new)

    if new_lists is None:
        logger.error("Cannot proceed without new data list.")
        exit(1)

    # Graceful fallback for missing old data
    if old_lists is None:
        logger.warning("Old lists data missing, generating report without differences.")
        old_top = []
    else:
        try:
            old_top = old_lists[LISTS_KEY][0][GAMES_KEY]
        except (IndexError, KeyError):
            logger.warning("Could not find top games in old data, generating without diffs.")
            old_top = []

    try:
        new_top = new_lists[LISTS_KEY][0][GAMES_KEY]
    except (IndexError, KeyError) as e:
        logger.error(f"Error accessing new top games list: {e}")
        exit(1)
    
    headline = _("Top Diff")
    ths = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]

    diffs = diff_utils.calculate_diffs(old_top, new_top)

    try:
        with filename.open("w", encoding="utf-8") as of:
            diff_utils.print_list(diffs, headline, style, of, ths)
        logger.info(f"+/- saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save report to {filename}: {e}")
        exit(1)


if __name__ == "__main__":
    main()