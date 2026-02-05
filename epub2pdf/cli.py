import click
import tempfile
from .epub import extract_epub, get_chapters
from .html_builder import build_html, process_footnotes
from .pdf import render_pdf

@click.command()
@click.argument("epub_file")
@click.option("-o", "--output", default="output.pdf")
def convert(epub_file, output):
    with tempfile.TemporaryDirectory() as tmp:
        extract_epub(epub_file, tmp)
        chapters = get_chapters(tmp)
        html = build_html(chapters)
        html = process_footnotes(html)
        render_pdf(html, output)

    click.echo(f"✔ PDF created: {output}")

if __name__ == "__main__":
    convert()
