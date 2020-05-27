# bggguildreport3
Scripts for generating top 50 etc. lists for guilds on BoardGameGeek.
python3 and <a href="https://github.com/lcosmin/boardgamegeek">boardgamegeek</a> by <a href="https://github.com/lcosmin">lcosmin</a> are required.

These scripts are still very rough. Because so many calls to BGG are necessary and can fail intermediate steps are dumped to files.

Changes in comparison to <a href="https://github.com/vizcacha/bggguildreport">vizcacha/bggguildreport</a>:
- python3
- refactoring
- select output format (html/bbcode/txt)
- i18n
- combine lists of users and guild’s user list
- lists added (sleepers, most varied/similar)
- save/load gameinfos to prevent unnecessary calls to BGG
