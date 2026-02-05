PRINT_CSS = """
@page {
  size: A4;
  margin: 2.5cm 2.2cm 3cm 2.2cm;
}

body {
  font-family: "Times New Roman", serif;
  font-size: 12pt;
  line-height: 1.6;
}

h1 {
  page-break-before: always;
  font-size: 24pt;
  margin-top: 0;
  margin-bottom: 1em;
}

h2 {
  font-size: 18pt;
  page-break-after: avoid;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}

h3 {
  font-size: 14pt;
  page-break-after: avoid;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

p {
  text-align: justify;
  margin-bottom: 0.5em;
}

img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
}

.footnote {
  font-size: 9pt;
  vertical-align: super;
}

code, pre {
  font-family: "Courier New", monospace;
  background-color: #f5f5f5;
  padding: 2px 4px;
}

pre {
  padding: 10px;
  overflow-x: auto;
}
"""
