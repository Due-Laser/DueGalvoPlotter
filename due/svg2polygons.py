import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
import shapely.affinity
import time

def parse_svg(svg_file):
    """Lê um arquivo SVG e extrai os polígonos."""
    tree = ET.parse(svg_file)
    root = tree.getroot()
    namespace = {'svg': 'http://www.w3.org/2000/svg'}

    polygons = []
    for elem in root.findall('.//svg:path', namespace):
        d = elem.attrib.get('d')  # Obtém a string 'd' do path
        if d:
            poly = svg_path_to_polygon(d)
            if poly:
                polygons.append(poly)

    return polygons

def svg_path_to_polygon(d):
    """Converte um path SVG (atributo 'd') para um polígono."""
    from svgpathtools import parse_path
    
    path = parse_path(d)
    points = [(seg.start.real, seg.start.imag) for seg in path if hasattr(seg, 'start')]
    if len(points) > 2:  # Apenas polígonos válidos
        return Polygon(points)
    return None

def classify_polygons(polygons):
    """Separa polígonos externos e buracos usando orientação."""
    polygons = sorted(polygons, key=lambda p: p.area, reverse=True)  # Maior primeiro
    external = []
    holes = []

    for poly in polygons:
        if poly.exterior.is_ccw:  # Anti-horário = externo
            external.append(poly)
        else:  # Horário = buraco
            holes.append(poly)

    return external, holes

# Exemplo de uso:
start_time = time.time()
svg_file = "svgs/kip18_gabarito3.svg"
polygons = parse_svg(svg_file)
externals, holes = classify_polygons(polygons)

print(f"Polígonos externos: {len(externals)}, Buracos detectados: {len(holes)}")

end_time = time.time()
print(f"Tempo de execução: {end_time - start_time} segundos")