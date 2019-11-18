import argparse
import datetime
import gettext
import json


def print_list(old_file, new_file, style):

    with open(old_file, "r") as oldf:
        old_lists = json.load(oldf)
        oldf.close()
        with open(new_file, "r") as newf:
            new_lists = json.load(newf)
            newf.close()

            new_top50 = new_lists["top50"]
            old_top50 = old_lists["top50"]
            old_top50_gameids = [x[1] for x in old_top50]
            old_top50_means = [x[3] for x in old_top50]
            old_top50_ratings = [x[2] for x in old_top50]

            hlevel = "h3"
            headline = _("Top50 Diff")
            ths = [
                _("No."),
                _("+/-"),
                _("Game"),
                _("Ratings"),
                _("+/-"),
                _("Mean"),
                _("+/-"),
                _("SD")]

            # table header
            if style == "html":
                print("<style>\n\
                    .text-right {text-align: right; padding: 0 5px;}\n\
                    </style>", file=of)
                print("<", hlevel, ">", headline, "</", hlevel, ">",
                      sep="", file=of)
                print("<table id=", headline, "><thead><tr>",
                      sep="", file=of)
                for i, th in enumerate(ths):
                    print("<th>", th, "</th>", sep="", file=of)
                print("</tr></thead><tbody>", sep="", file=of)
            elif style == "bbcode":
                print("[", hlevel, "]", headline,
                      "[/", hlevel, "]", sep="", file=of)
                print("[table][tr]", sep="", file=of)
                for i, th in enumerate(ths):
                    print("[th]", th, "[/th]", sep="", file=of)
                print("[/tr]", sep="", file=of)
            else:
                name_width = max([len(x[0]) for x in new_top50])
                ratings_width = max(len(ths[3]), 4)
                mean_width = max(len(ths[5]), 5)
                sd_width = max(len(ths[7]), 5)
                format_string = "{:3} {:5} {:" + str(name_width) + "}" \
                    " {:" + str(ratings_width) + "} {:6}" + \
                    " {:" + str(mean_width) + ".3f} {:8}" + \
                    " {:" + str(sd_width) + ".3f}"
                format_headers = "{:3} {:5} {:" + str(name_width) + "}" \
                    " {:" + str(ratings_width) + "} {:6}" + \
                    " {:" + str(mean_width) + "} {:8}" + \
                    " {:" + str(sd_width) + "}"
                print(format_headers.format(*ths), file=of)

            # table content
            for index, game_info in enumerate(new_top50):
                try:
                    old_index = old_top50_gameids.index(game_info[1])
                except ValueError:
                    old_index = -1

                if old_index > -1:
                    diff = old_index - index
                    diff_ratings = game_info[2] - \
                        old_top50_ratings[old_index]
                    diff_mean = game_info[3] - \
                        old_top50_means[old_index]
                    diff_string = "({:>+3})".format(diff)
                    diff_ratings = "({:>+3})".format(diff_ratings)
                    diff_mean = "({:+.3f})".format(diff_mean)
                else:
                    diff_string = "(" + _("new") + ")"
                    diff_mean = ""
                    diff_ratings = ""

                table_row_data = (index + 1, diff_string, game_info[0],
                                  game_info[2], diff_ratings,
                                  game_info[3], diff_mean, game_info[4])

                if style == "html":
                    print("<tr><td class=\"text-right\">{}</td> \
                        <td class=\"text-right\">{}</td> \
                        <td>{}</td> \
                        <td class=\"text-right\">{:4}</td> \
                        <td class=\"text-right\">{}</td> \
                        <td class=\"text-right\">{:5.3f}</td> \
                        <td class=\"text-right\">{}</td> \
                        <td class=\"text-right\">{:5.3f}</td> \
                        </tr>".format(
                        *table_row_data), file=of)
                elif style == "bbcode":
                    print("[tr][td]{}[/td] \
                        [td]{}[/td] \
                        [td]{}[/td] \
                        [td]{:4}[/td] \
                        [td]{}[/td] \
                        [td]{:5.3f}[/td] \
                        [td]{}[/td] \
                        [td]{:5.3f}[/td] \
                        [/tr]".format(
                        *table_row_data), file=of)
                else:
                    detail_string = format_string.format(*table_row_data)
                    print(detail_string, file=of)

            # table footer
            if style == "html":
                print("</tbody></table>", file=of)
            elif style == "bbcode":
                print("[/table]", file=of)

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(
        description="Print top50 with diffs in a pretty format")
    parser.add_argument(
        "old",
        help="old top50 file")
    parser.add_argument(
        "new",
        help="new top50 file")
    parser.add_argument(
        "--style",
        default="html",
        help="output format: bbcode|bgg|html - default: html")
    parser.add_argument(
        "--lang",
        default="en",
        help="language used for headlines and tableheaders")
    args = parser.parse_args()

    lang = gettext.translation("diff_top50", localedir="locales",
                               languages=[args.lang])
    lang.install()
    _ = lang.gettext

    if (args.style == "bgg") or (args.style == "bbcode"):
        style = args.style
        ext = "txt"
    else:
        style = "html"
        ext = "html"

    date_str = datetime.datetime.now().strftime("%Y%m%d")
    with open("top50diff_" + date_str + "." + ext, "w") as of:
        print_list(args.old, args.new, style)
        of.close()
