# banner.py
import click
from pyfiglet import Figlet
from . import __version__

APP_NAME = "EPUB2PDF"
AUTHOR = "George Inkoom (@blaq_arab)"

def print_banner():
    figlet = Figlet(font="slant")  # try: standard, big, small, doom
    banner = figlet.renderText(APP_NAME)

    click.secho(banner, fg="cyan", bold=True)
    click.secho(
        f" Convert EPUB books to PDF format\n"
        f" Version {__version__}\n"
        f" © 2026 {AUTHOR}\n",
        fg="cyan"
    )
