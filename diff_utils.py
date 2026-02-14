"""
Utility functions for calculating and rendering differences between game lists.
"""

import logging
import gettext
from pathlib import Path
from typing import List, Dict, Any, Tuple, TextIO, Callable, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Style templates for rendering reports
TEMPLATES = {
    "html": {
        "header_start": lambda h, labels, specs: (
            f"<style>\n.text-right {{text-align: right; padding: 0 5px;}}\n</style>\n"
            f"<h3>{h}</h3>\n"
            f"<table id={h.replace(' ', '_')}>\n<thead>\n<tr>"
        ),
        "th": lambda t: f"<th>{t}</th>",
        "header_end": lambda: "</tr>\n</thead>\n<tbody>",
        "row_start": lambda: "<tr>",
        "td": lambda v, align="left", width=0: f"<td class=\"text-right\">{v}</td>" if align == "right" else f"<td>{v}</td>",
        "row_end": lambda: "</tr>",
        "footer": lambda: "</tbody>\n</table>"
    },
    "bbcode": {
        "header_start": lambda h, labels, specs: f"[h3]{h}[/h3]\n[table]\n[tr]",
        "th": lambda t: f"[th]{t}[/th]",
        "header_end": lambda: "[/tr]",
        "row_start": lambda: "[tr]",
        "td": lambda v, align="left", width=0: f"[td]{v}[/td]",
        "row_end": lambda: "[/tr]",
        "footer": lambda: "[/table]"
    },
    "text": {
        "header_start": lambda h, labels, specs: (
            f"[b]{h}[/b]\n[c]\n" +
            " ".join(f"{str(val):{align}{width}}" for val, (width, align) in zip(labels, specs))
        ),
        "th": lambda t: "",  # Labels handled in header_start for text
        "header_end": lambda: "",
        "row_start": lambda: "",
        "td": lambda v, align, width: f"{str(v):{align}{width}}",
        "row_end": lambda: "",
        "footer": lambda: "[/c]"
    }
}


def setup_translation(domain: str, lang_code: str) -> Callable[[str], str]:
    """
    Setup gettext translation and return the gettext function.

    Args:
        domain: The translation domain (e.g., 'diff_lists').
        lang_code: The language code (e.g., 'en', 'de').

    Returns:
        The gettext function.
    """
    locales_dir = Path("locales")
    if locales_dir.exists():
        try:
            lang = gettext.translation(domain, localedir=str(locales_dir), languages=[lang_code])
            lang.install()
            return lang.gettext
        except Exception:
            logger.warning(f"translation for {lang_code} not found in {domain}, using default")
    else:
        logger.warning("locales directory not found, using default translations")
    return lambda s: s


def calculate_diffs(old_list: List[List[Any]], new_list: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Calculate differences between an old and a new list of games.

    Args:
        old_list: A list of game data tuples from the previous report.
        new_list: A list of game data tuples from the current report.

    Returns:
        A list of dictionaries containing calculated differences for each game.
        Each dictionary includes keys: index, diff_index, name, ratings, 
        diff_ratings, mean, diff_mean, and sd.
    """
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


def print_list(diffs: List[Dict[str, Any]], headline: str, style: str, of: TextIO, labels: List[str]) -> None:
    """
    Render a list of game differences to a file handle using a specific style.

    Args:
        diffs: Pre-calculated list of difference dictionaries.
        headline: The title of the report section.
        style: The output format (e.g., 'html', 'bbcode', 'text').
        of: A file-like object for output.
        labels: A list of header labels for the report table.
    """
    tpl = TEMPLATES.get(style, TEMPLATES["text"])
    
    name_width = max(len(d["name"]) for d in diffs) if diffs else 10
    ratings_width = max(len(labels[3]), 4)
    mean_width = max(len(labels[5]), 5)

    # Column specifications: (width, alignment)
    col_specs = [
        (3, ">"), (5, ">"), (name_width, "<"), (ratings_width, ">"),
        (6, ">"), (mean_width, ">"), (9, ">"), (6, ">")
    ]

    header = tpl["header_start"](headline, labels, col_specs)
    if header:
        print(header, end="" if style in ("text", "bgg") else "\n", file=of)
    
    if style not in ("text", "bgg"):
        for th in labels:
            print(tpl["th"](th), end="", file=of)
        
    h_end = tpl["header_end"]()
    if h_end:
        print(h_end, file=of)
    elif style in ("text", "bgg"):
        print("", file=of) # Newline after text header labels

    for d in diffs:
        r_start = tpl["row_start"]()
        if r_start:
            print(r_start, file=of)
            
        row_values = [
            (d["index"], "right", 3), (d["diff_index"], "right", 5), (d["name"], "left", name_width),
            (d["ratings"], "right", ratings_width), (d["diff_ratings"], "right", 6),
            (f"{d['mean']:.3f}", "right", mean_width), (d["diff_mean"], "right", 9),
            (f"{d['sd']:.3f}", "right", 6)
        ]
        
        row_str_parts = []
        for i, (val, align, width) in enumerate(row_values):
            # Align mapping for templates
            a = "right" if align == "right" else "left"
            if style in ("text", "bgg"):
                row_str_parts.append(tpl["td"](val, col_specs[i][1], col_specs[i][0]))
            else:
                print(tpl["td"](val, a, width), file=of)
        
        if style in ("text", "bgg"):
            print(" ".join(row_str_parts), file=of)

        r_end = tpl["row_end"]()
        if r_end:
            print(r_end, file=of)
            
    print(tpl["footer"](), file=of)
