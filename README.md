# EPUB to PDF Converter

A Python command-line tool that converts EPUB (Electronic Publication) files into well-formatted PDF documents. The converter preserves the original reading order, applies professional styling, and handles complex EPUB structures.

## Features

✨ **Smart Chapter Ordering** - Reads EPUB metadata to maintain correct chapter sequence  
📖 **Professional Formatting** - Applies book-style typography and layout  
🎨 **Custom Styling** - Uses CSS for consistent, readable output  
🔧 **Pure Python** - No external system dependencies required  
⚡ **Simple CLI** - Easy-to-use command-line interface

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository** (or download the source code):

   ```bash
   git clone <repository-url>
   cd epub2pdf
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies from the requirements file**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Conversion

Convert an EPUB file to PDF with default settings:

```bash
python -m epub2pdf.cli book.epub
```

This creates `output.pdf` in the current directory.

### Specify Output File

Convert with a custom output filename:

```bash
python -m epub2pdf.cli book.epub -o mybook.pdf
```

### Full Example

```bash
python -m epub2pdf.cli "My Book Title.epub" -o "My Book Title.pdf"
```

### Command-Line Options

```
Usage: python -m epub2pdf.cli [OPTIONS] EPUB_FILE

Arguments:
  EPUB_FILE  Path to the input EPUB file (required)

Options:
  -o, --output TEXT  Output PDF filename (default: output.pdf)
  --help            Show this message and exit
```

## How It Works

1. **Extraction** - Unzips the EPUB file to access its contents
2. **Metadata Parsing** - Reads the OPF manifest to determine correct chapter order
3. **Content Processing** - Extracts and combines chapters in sequence
4. **HTML Assembly** - Builds a complete HTML document with embedded CSS
5. **PDF Generation** - Converts the HTML to a formatted PDF file

## Project Structure

```
epub2pdf/
├── epub2pdf/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── epub.py          # EPUB extraction and parsing
│   ├── html_builder.py  # HTML processing and assembly
│   ├── pdf.py           # PDF generation
│   └── styles.py        # CSS styling definitions
├── .gitignore
└── README.md
```

## Dependencies

- **click** - Command-line interface creation
- **beautifulsoup4** - HTML/XML parsing
- **lxml** - XML processing
- **xhtml2pdf** - HTML to PDF conversion

## Styling

The converter applies professional book-style formatting:

- **Page Size**: A4 (210mm × 297mm)
- **Margins**: 2.5cm (top), 2.2cm (right), 3cm (bottom), 2.2cm (left)
- **Font**: Times New Roman, 12pt
- **Line Height**: 1.6 for comfortable reading
- **Text Alignment**: Justified
- **Chapter Breaks**: Each H1 heading starts a new page

You can customize the styling by editing `epub2pdf/styles.py`.

## Troubleshooting

### Common Issues

**Problem**: `ModuleNotFoundError: No module named 'epub2pdf'`  
**Solution**: Make sure you're running the command from the project root directory and using `python -m epub2pdf.cli`

**Problem**: Images not appearing in PDF  
**Solution**: This is a known limitation with relative image paths in some EPUB files. The text content will still convert correctly.

**Problem**: Chapters in wrong order  
**Solution**: The converter reads the EPUB spine metadata. If the original EPUB has incorrect metadata, the order may be wrong. This has been fixed in the latest version.

## Limitations

- Some complex CSS from EPUB files may not be fully preserved
- Images with relative paths may not load correctly
- Advanced EPUB 3 features (audio, video) are not supported
- DRM-protected EPUB files cannot be converted

## Contributing

Contributions are welcome! Here are some areas for improvement:

- Better image path resolution
- Support for EPUB 3 features
- Custom CSS templates
- Progress indicators for large files
- Batch conversion support

## License

This project is open source and available under the MIT License.

## Author

Created with ❤️ for book lovers and developers

## Acknowledgments

- **xhtml2pdf** - For reliable HTML to PDF conversion
- **BeautifulSoup** - For robust HTML/XML parsing
- **Click** - For elegant CLI creation

---

**Note**: This tool is for personal use with DRM-free EPUB files that you own or have permission to convert.
