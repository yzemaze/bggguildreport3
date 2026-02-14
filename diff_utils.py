import logging
from typing import List, Dict, Any, Tuple, TextIO, Callable, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Style templates
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
        "td": lambda v, align="left": f"<td class=\"text-right\">{v}</td>" if align == "right" else f"<td>{v}</td>",
        "row_end": lambda: "</tr>",
        "footer": lambda: "</tbody>\n</table>"
    },
    "bbcode": {
        "header_start": lambda h, labels, specs: f"[h3]{h}[/h3]\n[table]\n[tr]",
        "th": lambda t: f"[th]{t}[/th]",
        "header_end": lambda: "[/tr]",
        "row_start": lambda: "[tr]",
        "td": lambda v, align="left": f"[td]{v}[/td]",
        "row_end": lambda: "[/tr]",
        "footer": lambda: "[/table]"
    },
    "text": {
        "header_start": lambda h, labels, specs: (
            f"[b]{h}[/b]\n[c]\n" +
            " ".join(f"{str(val):{width}{align}}" for val, (width, align) in zip(labels, specs))
        ),
        "th": lambda t: "",  # Labels handled in header_start for text
        "header_end": lambda: "",
        "row_start": lambda: "",
        "td": lambda v, align, width: f"{str(v):{width}{align}}",
        "row_end": lambda: "",
        "footer": lambda: "[/c]"
    }
}


def calculate_diffs(old_list: List[List[Any]], new_list: List[List[Any]]) -> List[Dict[str, Any]]:
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


def print_list(diffs: List[Dict[str, Any]], headline: str, style: str, of: TextIO, labels: List[str]) -> None:
    """Print the pre-calculated diffs in the given style."""
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
        print(header, end="" if style == "text" else "\n", file=of)
    
    if style != "text":
        for th in labels:
            print(tpl["th"](th), end="", file=of)
        
    h_end = tpl["header_end"]()
    if h_end:
        print(h_end, file=of)
    elif style == "text":
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
            if style == "text":
                row_str_parts.append(tpl["td"](val, col_specs[i][1], col_specs[i][0]))
            else:
                print(tpl["td"](val, a), file=of)
        
        if style == "text":
            print(" ".join(row_str_parts), file=of)

        r_end = tpl["row_end"]()
        if r_end:
            print(r_end, file=of)
            
    print(tpl["footer"](), file=of)