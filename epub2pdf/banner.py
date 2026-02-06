# banner.py
import click
from pyfiglet import Figlet

APP_NAME = "EPUB2PDF"
VERSION = "1.0.0"
AUTHOR = "George Inkoom (@blaq_arab)"

def print_banner():
    figlet = Figlet(font="slant")  # try: standard, big, small, doom
    banner = figlet.renderText(APP_NAME)

    click.secho(banner, fg="cyan", bold=True)
    click.secho(
        f" Convert EPUB books to PDF format\n"
        f" Version {VERSION}\n"
        f" © 2026 {AUTHOR}\n",
        fg="cyan"
    )
