import argparse
import datetime
import gettext
import json


def print_list(category, games, headline, count, style):
    """Print list per category in given style to file."""
    hlevel = "h3"
    ths = [_("No."), _("Game"), _("Ratings"), _("Mean"), _("Stdev")]

    json_data = games
    if style == "html":
        print("<", hlevel, ">", headline, "</", hlevel, ">", sep="", file=of)
        print("<table id=", category, "><thead><tr>", sep="", file=of)
        for i, th in enumerate(ths):
            print("<th>", th, "</th>", sep="", file=of)
        print("</tr></thead><tbody>", sep="", file=of)
        for idx, game in enumerate(json_data):
            table_row_data = (idx + 1, game[0], game[2], game[3], game[4])
            print("<tr><td class=\"text-right\">{:2}</td> \
                <td>{}</td><td class=\"text-right\">{:2}</td> \
                <td class=\"text-right\">{:5.3f}</td> \
                <td class=\"text-right\">{:5.3f}</td></tr>".format(
                *table_row_data), file=of)
        print("</tbody></table>", file=of)
    elif style == "bbcode":
        print("[", hlevel, "]", headline, "[/", hlevel, "]", sep="", file=of)
        print("[table][tr]", sep="", file=of)
        for i, th in enumerate(ths):
            print("[th]", th, "[/th]", sep="", file=of)
        print("[/tr]", sep="", file=of)
        for idx, game in enumerate(json_data):
            table_row_data = (idx + 1, game[0], game[2], game[3], game[4])
            print("[tr][td]{:2}[/td][td]{}[/td][td]{:2}[/td] \
                [td]{:5.3f}[/td][td]{:5.3f}[/td][/tr]".format(
                *table_row_data), file=of)
        print("[/table]", file=of)
    else:
        # bgg-style
        format_string_prefix = u"{:2} {:"
        format_string_ext = u"} {:3} {:5.3f} {:5.3f}"
        max_name_width = max([len(game[0]) for game in json_data])
        format_string = format_string_prefix \
            + str(max_name_width) + format_string_ext
        print("\n[b]", headline, "[/b]\n[c]", sep="", file=of)
        for idx, game in enumerate(json_data):
            detail_string = format_string.format(
                idx + 1, game[0], game[2], game[3], game[4])
            print(detail_string, file=of)
        print("[/c]", file=of)


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(
        description="Process file to print in a pretty format")
    parser.add_argument(
        "filename",
        help="file to format")
    parser.add_argument(
        "--style",
        default="html",
        help="output format: bbcode|bgg|html - default: html")
    parser.add_argument(
        "--lang",
        default="en",
        help="language used for headlines and tableheaders")
    args = parser.parse_args()

    lang = gettext.translation("print_lists", localedir="locales",
                               languages=[args.lang])
    lang.install()
    _ = lang.gettext

    with open(args.filename) as f:
        data = json.load(f)
        f.close()
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        if (args.style == "bgg") or (args.style == "bbcode"):
            style = args.style
            ext = "txt"
        else:
            style = "html"
            ext = "html"

        with open("output_" + date_str + "." + ext, "w") as of:
            headlines = [
                _("Top"), _("Bottom"),
                _("Most Varied"), _("Most Similar"),
                _("Most Rated"), _("Sleepers")]
            if style == "html":
                print("<style>\n.text-right {\
                        text-align: right; padding: 0 5px;}\n\
                    </style>", file=of)
            i = 0
            for d in data["lists"]:
                print_list(d["category"], d["games"],
                           headlines[i], d["count"], style)
                i += 1
            of.close()
