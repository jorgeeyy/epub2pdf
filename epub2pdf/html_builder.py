from bs4 import BeautifulSoup
from .styles import PRINT_CSS

def process_footnotes(html):
    soup = BeautifulSoup(html, "lxml")

    for a in soup.find_all("a", href=True):
        if a["href"].startswith("#fn"):
            a["class"] = a.get("class", []) + ["footnote"]

    return str(soup)


def build_html(chapters):
    body = "".join(chapters)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{PRINT_CSS}
</style>
</head>
<body>
{body}
</body>
</html>
"""
