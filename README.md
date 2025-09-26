# svgexport.py

`svgexport.py` is a Python script designed to automate the export of multiple drawings from a single SVG file into separate files. Supported output formats include PDF, PNG and SVG.

## Features

- Export multiple drawings from a single SVG file.
- Supports output to PDF, PNG and SVG formats.
- Uses a dedicated "Export" layer in the SVG to define export regions.
- Each export region is defined by a rectangle (square) in the "Export" layer.
- Everything within each rectangle is exported as a separate file.

## How It Works

1. **Prepare your SVG file:**
    - Add a layer named `Export`.
    - In the `Export` layer, draw rectangles (squares) to outline each drawing you want to export.
    - Each rectangle defines the bounds of a single output file.

2. **Run the script:**
    - The script scans the SVG for the `Export` layer.
    - For each rectangle in the `Export` layer, it exports the content within that rectangle to a separate file.

## Usage
```
This script processes an SVG file and exports it to a specified filetype.

Usage:
    python svgexport.py <input_svg_filename> --filetype=[filetype]

Arguments:
    input_svg_filename (str): The path to the SVG file to be processed. This argument is mandatory.
    filetype (str, optional): The desired export filetype. Supported values are 'pdf', 'png', or 'svg'. 
                              If not specified, pdf is selected by default.

Example:
    python svgexport.py logo.svg --filetype=pdf

Notes:
    - Ensure that the input SVG file exists and is accessible.
    - The script will output the exported file in the same directory as the input SVG.
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
