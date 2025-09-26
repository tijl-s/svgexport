import os
import math
import argparse
import subprocess
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

# Namespace dictionary for SVG
ns = {'svg': 'http://www.w3.org/2000/svg',
      'inkscape': 'http://www.inkscape.org/namespaces/inkscape'}


def get_coordinates(e: Element):
    # Get rid of the namespace from the tag.
    tag = e.tag.replace(f'{{{ns["svg"]}}}', '')

    x, y = None, None
    match tag:
        case 'circle' | 'ellipse':
            x = e.attrib.get('cx')
            y = e.attrib.get('cy')
        case 'path':
            d = e.attrib.get('d')
            if d:
                a = d.split(" ")
                x, y = map(float, a[1].split(','))
        case _:
            # 'rect' and 'text' end up here.
            x = e.attrib.get('x')
            y = e.attrib.get('y')

    if x is None or y is None:
        return None

    x = float(x)
    y = float(y)

    # The element can have transformations applied to it.
    transformation = e.attrib.get('transform')
    if transformation is not None:
        x, y = transform_coordinates(x, y, transformation)

    return x, y


def transform_coordinates(x: float, y: float, transformation: str) -> tuple[float, float]:
    """Transform a pair of coordinates based on a transformation string from an svg file.

    :param transformation: Transformation string in the form of: 'translate(50,0)'
    """
    # Split the string into an operation and operand.
    operation, operand = transformation.split('(')
    operand = operand.rstrip(')')

    xtrans, ytrans = x, y
    match operation:
        case 'translate':
            # The y argument is optional and assumed zero when not given: translate(<x> [<y>])
            xt, yt = 0, 0

            operand = operand.split(',')
            if len(operand) == 2:
                xt, yt = operand
            else:
                xt = operand[0]

            xt = float(xt)
            yt = float(yt)

            # Translate coordinates.
            xtrans = xtrans + xt
            ytrans = ytrans + yt
        case 'matrix':
            ma, mb, mc, md, me, mf = map(float, operand.split(','))

            if x is not None and y is not None:
                xtrans = (ma * x) + (mc * y) + me
                ytrans = (mb * x) + (md * y) + mf
        case 'rotate':
            # Rotation of a degrees around x,y with x and y optional: rotate(<a> [<x> <y>])
            at, xt, yt = 0, 0, 0

            operand = operand.split(',')
            if len(operand) == 3:
                at, xt, yt = operand
            if len(operand) == 2:
                at, xt = operand
            else:
                at = operand[0]

            xt = float(xt)
            yt = float(yt)
            at = float(at)

            # Now apply the rotation to the coordinates.
            at_rad = math.radians(at)

            x_shift = x - xt
            y_shift = y - yt

            xtrans = (x_shift * math.cos(at_rad)) - \
                (y_shift * math.sin(at_rad))
            ytrans = (x_shift * math.sin(at_rad)) + \
                (y_shift * math.cos(at_rad))

            xtrans += xt
            ytrans += yt
        case 'scale':
            # Scale operation where x=y when y is not given: scale(<x> [<y>])
            xt, yt = 0, 0

            operand = operand.split(',')
            if len(operand) == 2:
                xt, yt = operand
            else:
                xt = operand[0]
                yt = operand[0]

            xt = float(xt)
            yt = float(yt)

            # Currently we just use the sign of the numbers
            if xt < 0:
                xtrans = -xtrans
            if yt < 0:
                ytrans = -ytrans

    return xtrans, ytrans


def get_first_ungrouped_element(e: Element) -> tuple[Element, list[str]]:
    """Get the first non-group element from a set of nested groups and get all the transformations that apply to it."""
    gtransforms = []

    # Get the next element in the group.
    element_iter = iter(e)
    next_element = next(element_iter)

    tag = next_element.tag.replace(f'{{{ns["svg"]}}}', '')
    # Is it again a group then dig deeper.
    if tag == 'g':
        non_group_element, transforms = get_first_ungrouped_element(
            next_element)
        gtransforms.extend(transforms)
    else:
        non_group_element = next_element

    t = e.attrib.get('transform')
    if t is not None:
        gtransforms.append(t)

    return non_group_element, gtransforms


def parse_and_export(xml_file) -> list[str]:
    # Load in the document to parse it.
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find the 'Export' layer
    export_layer = root.find(".//svg:g[@inkscape:label='Export']", ns)
    drawing_layer = root.find(".//svg:g[@inkscape:label='Drawings']", ns)
    if export_layer is None:
        raise RuntimeError("No 'Export' layer found.")

    # Iterate over the rectangles in the 'Export' layer
    out_files = []
    for rect in export_layer:
        # Only parse rectangles.
        tag = rect.tag.replace(f'{{{ns["svg"]}}}', '')
        if tag != 'rect':
            continue

        # Load the template svg to which the export image is added.
        outtree = ET.parse("template.svg")
        out_svg = outtree.getroot()

        # Copy the defs from the original file.
        defs = root.findall('{http://www.w3.org/2000/svg}defs')
        for definition in defs:
            out_svg.append(definition)

        x_min = float(rect.attrib.get('x'))
        y_min = float(rect.attrib.get('y'))
        x_max = float(rect.attrib.get('width')) + x_min
        y_max = float(rect.attrib.get('height')) + y_min

        # Set the canvas size and viewport to match the exported image.
        x_view = abs(x_max - x_min)
        y_view = abs(y_max - y_min)
        out_svg.set('viewBox', f"{x_min} {y_min} {x_view} {y_view}")
        out_svg.set('width', str(x_view))
        out_svg.set('height', str(y_view))

        out_filename = rect.attrib.get('id')
        if out_filename is None:
            continue

        for e in drawing_layer:
            # Get rid of the namespace from the tag.
            tag = e.tag.replace(f'{{{ns["svg"]}}}', '')

            sube = e
            # Does a group transformation apply?
            gtransform = None
            # If we have a group get the first element in the group and all the transformations that apply.
            if tag == 'g':
                sube, gtransform = get_first_ungrouped_element(e)
                # # A group has transformations applied which we apply to the reference window.
                # gtransform = e.attrib.get('transform')

                # # Now get the elements out of the group so we can iterate over them.
                # elements = []
                # for sube in e:
                #     elements.append(sube)

            xy = get_coordinates(sube)
            if xy is None:
                continue
            else:
                x, y = xy

            if gtransform is not None:
                for transform in gtransform:
                    x, y = transform_coordinates(x, y, transform)

            if x and y:
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    out_svg.append(e)

        # Write the new SVG to a file
        tree = ET.ElementTree(out_svg)
        tree.write(f'{out_filename}.svg')
        out_files.append(out_filename)

    return out_files


if __name__ == '__main__':
    # Add CLI argument parsing.
    parser = argparse.ArgumentParser(description="Export SVG drawings on the Export layer to individual files.")
    parser.add_argument('filename', type=str, help="The input SVG file.")
    parser.add_argument('--filetype', type=str, default='pdf', help="The output file type (default: pdf).")
    args = parser.parse_args()

    # Assign arguments to variables.
    svg_file = args.filename
    out_file_type = args.filetype

    # Process the SVG file.
    exported_files = parse_and_export(svg_file)

    for svg_file in exported_files:
        result = subprocess.run(
            ["inkscape", f"--export-type={out_file_type}", f"{svg_file}.svg"], shell=True, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to export svg: {result.stderr}")

        # Treat the svgs as temporary and remove them afterwards.
        os.remove(f"{svg_file}.svg")
