import click
import tempfile
import sys
import os
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from .epub import extract_epub, get_chapters
from .html_builder import build_html, process_footnotes
from .pdf import render_pdf
from .banner import print_banner

@click.command()
@click.argument("epub_file")
@click.option("-o", "--output", default=None, help="Output PDF filename (defaults to input name with .pdf extension)")
def convert(epub_file, output):
    if output is None:
        base = os.path.splitext(epub_file)[0]
        output = base + ".pdf"

    # Display banner
    print_banner()
    click.secho(f"Input:  {epub_file}", fg='blue', bold=True)
    click.secho(f"Output: {output}\n", fg='blue', bold=True)
    
    try:
        # Step 1: Extract EPUB
        with click.progressbar(length=100, label=click.style('Extracting EPUB', fg='cyan', bold=True)) as bar:
            with tempfile.TemporaryDirectory() as tmp:
                extract_epub(epub_file, tmp)
                bar.update(20)
                
                # Step 2: Read chapters
                bar.label = click.style('Reading chapters', fg='cyan', bold=True)
                chapters, content_dir = get_chapters(tmp)
                bar.update(20)
                
                # Step 3: Build HTML
                bar.label = click.style('Building HTML', fg='cyan', bold=True)
                html = build_html(chapters, content_dir)
                bar.update(20)
                
                # Step 4: Process footnotes
                bar.label = click.style('Processing content', fg='cyan', bold=True)
                html = process_footnotes(html)
                bar.update(20)
                
                # Step 5: Render PDF (suppress verbose output)
                bar.label = click.style('Generating PDF', fg='cyan', bold=True)
                
                # Capture and filter output
                stdout_capture = StringIO()
                stderr_capture = StringIO()
                
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    render_pdf(html, output)
                
                # Check for important warnings
                stderr_text = stderr_capture.getvalue()
                if stderr_text and 'error' in stderr_text.lower():
                    click.secho('\nWarnings during conversion:', fg='yellow', bold=True)
                    for line in stderr_text.split('\n'):
                        if 'error' in line.lower() or 'warning' in line.lower():
                            click.secho(f'   {line}', fg='yellow')
                
                bar.update(20)
        
        # Success message
        click.echo()
        click.secho('Success! PDF created successfully', fg='green', bold=True)
        click.secho(f'Location: {output}', fg='green')
        
    except FileNotFoundError:
        click.secho(f'\nError: EPUB file not found: {epub_file}', fg='red', bold=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f'\nError: {str(e)}', fg='red', bold=True)
        sys.exit(1)

if __name__ == "__main__":
    convert()
