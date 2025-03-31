from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.compiler import Compiler, interfaces
from svg_to_gcode import TOLERANCES

TOLERANCES['approximation'] = 0.1

#https://github.com/johannesnoordanus/SvgToGcode

def convert_svg_to_gcode(svg_filepath: str, gcode_filepath: str):
    # Instantiate a compiler, specifying the interface type, maximum_laser_power and speed at which the tool moves while 
    # cutting. (Note that rapid moves - moves to and from cuts - move at a machine defined speed and are not set here.)
    # pass_depth controls how far down the tool moves - how deep the laser cuts - after every pass. Set it to 0 (default)
    # if your machine # does not support Z axis movement.
    gcode_compiler = Compiler(interfaces.Gcode, 1000, 1000, pass_depth=0)

    # Parse an svg file into geometric curves, and compile to gcode
    curves = parse_file(svg_filepath, transform_origin=False, canvas_height=991)
    gcode_compiler.append_curves(curves)

    # do final compilation and emit gcode 2 ('passes') times
    gcode_compiler.compile(passes=1)

    # or, to combine the above 2 steps into one and emit to a file:
    gcode_compiler.compile_to_file(gcode_filepath, passes=1)