# import ezdxf
# import svgwrite

# doc = ezdxf.readfile("arquivo.dwg")
# msp = doc.modelspace()
# dwg = svgwrite.Drawing("saida.svg")

# for entity in msp:
#     if entity.dxftype() == "LINE":
#         start = entity.dxf.start
#         end = entity.dxf.end
#         dwg.add(dwg.line(start, end, stroke="black"))

# dwg.save()