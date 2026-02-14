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
CATEGORY_KEY = "category"
COUNT_KEY = "count"


def main():
    logging.basicConfig(filename="std.log", encoding="utf-8",
                        format="%(asctime)s %(message)s", level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Process file to print in a pretty format")
    parser.add_argument("filename", help="file to format")
    parser.add_argument("--style", default="html", help="output format: bbcode|bgg|html - default: html")
    parser.add_argument("--lang", default="en", help="language used for headlines and tableheaders")
    args = parser.parse_args()

    _ = diff_utils.setup_translation("print_lists", args.lang)

    if args.style in ("bgg", "bbcode"):
        style, ext = args.style, "txt"
    else:
        style, ext = "html", "html"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    output_filename = Path(f"output_{date_str}.{ext}")

    def load_json(file_path):
        p = Path(file_path)
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if LISTS_KEY not in data:
                logger.error(f"Invalid structure in {file_path}: missing '{LISTS_KEY}'")
                return None
            return data
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path}: {e}")
        return None

    data = load_json(args.filename)
    if data is None:
        exit(1)

    category_headlines = {
        "top": _("Top"),
        "bottom": _("Bottom"),
        "variance": _("Most Varied"),
        "similar": _("Most Similar"),
        "most_rated": _("Most Rated"),
        "sleepers": _("Sleepers")
    }
    ths = [_("No."), _("Game"), _("Ratings"), _("Mean"), _("SD")]

    # Adapt data for diff_utils.print_list (which expects diff dictionaries)
    # We create "fake" diffs where diff_index, diff_ratings, and diff_mean are empty.
    
    with output_filename.open("w", encoding="utf-8") as of:
        # For html style, diff_utils expects its own style tag which is slightly different
        # but we use its standard rendering.
        
        for d in data[LISTS_KEY]:
            category = d.get(CATEGORY_KEY)
            if not category: continue
            
            headline = category_headlines.get(category, category.capitalize())
            games = d.get(GAMES_KEY, [])
            
            # Format games into the structure diff_utils expects
            formatted_data = []
            for idx, game in enumerate(games):
                formatted_data.append({
                    "index": idx + 1,
                    "diff_index": "", # No diff for simple print
                    "name": game[0],
                    "ratings": game[2],
                    "diff_ratings": "",
                    "mean": game[3],
                    "diff_mean": "",
                    "sd": game[4]
                })
            
            # diff_utils.print_list labels are hardcoded for 8 columns in TEMPLATES
            # We'll adapt our labels to match the expected structure
            print_labels = [_("No."), _("+/-"), _("Game"), _("Ratings"), _("+/-"), _("Mean"), _("+/-"), _("SD")]
            
            diff_utils.print_list(formatted_data, headline, style, of, print_labels)
            logger.info(f"formatted printing of {headline} done")

    logger.info(f"formatted lists saved to {output_filename}")


if __name__ == "__main__":
    main()
