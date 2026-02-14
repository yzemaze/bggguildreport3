import logging

# Initialize logger
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
                f"<style>
.text-right {{text-align: right; padding: 0 5px;}}
</style>
"
                f"<{hlevel}>{h}</{hlevel}>
"
                f"<table id={h.replace(' ', '_')}>
<thead>
<tr>"
            ),
            "th": lambda t: f"<th>{t}</th>",
            "header_end": "</tr>
</thead>
<tbody>",
            "row_start": "<tr>",
            "td": lambda v, align="left": f"<td class="text-right">{v}</td>" if align == "right" else f"<td>{v}</td>",
            "row_end": "</tr>",
            "footer": "</tbody>
</table>"
        },
        "bbcode": {
            "header_start": lambda h: f"[{hlevel}]{h}[/{hlevel}]
[table]
[tr]",
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
        # Default text style with declarative formatting
        name_width = max(len(d["name"]) for d in diffs) if diffs else 10
        ratings_width = max(len(labels[3]), 4)
        mean_width = max(len(labels[5]), 5)

        # Column specifications: (width, alignment)
        col_specs = [
            (3, ">"), (5, ">"), (name_width, "<"), (ratings_width, ">"),
            (6, ">"), (mean_width, ">"), (9, ">"), (6, ">")
        ]

        def format_row(values):
            return " ".join(f"{str(val):{width}{align}}" for val, (width, align) in zip(values, col_specs))

        print(f"[b]{headline}[/b]
[c]", file=of)
        print(format_row(labels), file=of)

        for d in diffs:
            row_values = [
                d["index"], d["diff_index"], d["name"], d["ratings"],
                d["diff_ratings"], f"{d['mean']:.3f}", d["diff_mean"],
                f"{d['sd']:.3f}"
            ]
            print(format_row(row_values), file=of)
        print("[/c]", file=of)
