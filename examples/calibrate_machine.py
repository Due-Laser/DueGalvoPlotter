# -- coding: utf-8 --
import sys
import os
import clr
from System.Diagnostics import Debug
import json
import re
import threading
import time
from pynput import keyboard
from galvo.controller import GalvoController
import math

#offset_x_light, offset_y_light = -5, -11
#offset_x_light, offset_y_light = -4.5, -13
last_click_time = 0  # Variável global para debouncing

# Redireciona a saída padrão para o Debug do Visual Studio
class DebugWriter:
    def write(self, message):
        if message.strip():
            Debug.WriteLine(message)
    def flush(self):
        pass

sys.stdout = DebugWriter()

# -----------------------------------------------------------------
# Função: Inicializa o controlador
# -----------------------------------------------------------------

from galvo import *

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

__settings__ = os.path.join(__location__, "default.json")
controller = GalvoController(settings_file=__settings__)

# Lista dos pontos de calibração (em mm)
calibration_points = [
    {"name": "superior_esquerdo", "mm": (-35, 100)},
    {"name": "inferior_esquerdo", "mm": (35, 100)},
    {"name": "superior_direito", "mm": (-35, -100)},
    {"name": "inferior_direito", "mm": (35, -100)},
    {"name": "centro", "mm": (0, 0)},
    {"name": "centro_superior", "mm": (0, 90)},
    {"name": "centro_inferior", "mm": (0, -90)},
    {"name": "centro_esquerdo", "mm": (-30, 0)},
    {"name": "centro_direito", "mm": (30, 0)},
    {"name": "quadrante_superior_esquerdo", "mm": (-15, 45)},
    {"name": "quadrante_superior_direito", "mm": (15, 45)},
    {"name": "quadrante_inferior_esquerdo", "mm": (-15, -45)},
    {"name": "quadrante_inferior_direito", "mm": (15, -45)},
    {"name": "meio_superior_esquerdo", "mm": (-22.5, 67.5)},
    {"name": "meio_superior_direito", "mm": (22.5, 67.5)},
    {"name": "meio_inferior_esquerdo", "mm": (-22.5, -67.5)},
    {"name": "meio_inferior_direito", "mm": (22.5, -67.5)}
]

saved_points = []
affine_transform_matrix = None

# Variáveis globais para o loop de desenho
calibration_active = False
current_calibration_point = None
draw_thread = None
processing_click = False  # Flag para controlar o desenho durante o clique

click_lock = threading.Lock()

# Offsets e parâmetros (em mm) – mantenha os nomes originais
offset_x = 0
offset_y = 0
offset_x_light = 0
offset_y_light = 0

laser_power = 100
laser_speed = 100
laser_line_thickness = 1
_scale_factor = 1

# -----------------------------------------------------------------------------
# NOVAS FUNÇÕES: Obter o frame (retângulo) da arte com os pontos extremos
# -----------------------------------------------------------------------------
def get_frame_points(scaledPoints):
    """
    Retorna os cantos extremos do retângulo que delimita a arte.
    Usa os pontos globais 'points' (assumindo que já foram centralizados).
    """
    xs = [p[0] for p in scaledPoints]
    ys = [p[1] for p in scaledPoints]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    # Ordem: inferior esquerdo, inferior direito, superior direito, superior esquerdo, e fecha com inferior esquerdo
    return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y), (min_x, min_y)]

def light_frame(pixel_tuple, angle, image_width=640, image_height=480, display_width=None, display_height=None):
    """
    Desenha um frame (retângulo) da arte utilizando somente os pontos extremos (bounding box).
    Essa função calcula os cantos do retângulo que envolve a arte e, opcionalmente, aplica a rotação.
    """
    if display_width is not None and display_height is not None:
        scale_x = image_width / display_width
        scale_y = image_height / display_height
        pixel_tuple = (pixel_tuple[0] * scale_x, pixel_tuple[1] * scale_y)
        print("Pixel ajustado para calibração (frame):", pixel_tuple)
    
    converted_mm = pixel_to_mm((pixel_tuple[0], pixel_tuple[1]), affine_transform_matrix)
    tam_x_mm, tam_y_mm = converted_mm
    print("Converted mm (frame):", converted_mm)

    # Aplica a escala de forma local
    scaled_points = scale_art_points(_scale_factor)
    
    # Obtém os pontos extremos (bounding box)
    frame_points = get_frame_points(scaled_points)
    # Prepara os pontos para rotação (adiciona s=0)
    frame_points_with_s = [(x, y, 0) for (x, y) in frame_points]

    # Aplica a rotação usando a função já existente
    frame_points_rotated = rotate_art_points(frame_points_with_s, angle)
    # Remove o valor 's' para usar somente (x, y)
    frame_points_rotated = [(x, y) for (x, y, s) in frame_points_rotated]
    
    total_offset_x = offset_x + offset_x_light
    total_offset_y = offset_y + offset_y_light
    
    with controller.lighting() as c:
        # Define o ponto de início
        start_x, start_y = mm_to_galvo(total_offset_x + tam_x_mm, total_offset_y + tam_y_mm)
        c.goto(start_x, start_y)
        # Desenha o frame conectando os pontos extremos
        for (x_mm, y_mm) in frame_points_rotated:
            x, y = mm_to_galvo(x_mm + total_offset_x + tam_x_mm, y_mm + total_offset_y + tam_y_mm)
            c.light(x, y)
        #c.Remove(light_frame)
    #time.sleep(1)
    controller.remove(light_frame)
    #return False

# -----------------------------------------------------------------
# Função: Desenha continuamente o padrão de referência
# -----------------------------------------------------------------
def continuous_draw_calibration():
    global calibration_active, current_calibration_point, processing_click
    while calibration_active:
        with click_lock:
            local_processing = processing_click
        if current_calibration_point is not None and not local_processing:
            try:
                with controller.lighting() as c:
                    draw_square_zero_point(c, current_calibration_point["mm"])
            except Exception as e:
                print("Erro no desenho contínuo:", e)
        # Intervalo curto para atualização
        time.sleep(0.0001)

# -----------------------------------------------------------------
# Função: Desenha o quadrado de referência via laser
# -----------------------------------------------------------------
def draw_square_zero_point(c, mm_center):
    """
    Aciona o laser para desenhar um pequeno quadrado de referência
    centrado em mm_center.
    """
    offset = 5  # Tamanho do quadrado em mm
    corners = [
        (mm_center[0] - offset, mm_center[1] - offset),
        (mm_center[0] + offset, mm_center[1] - offset),
        (mm_center[0] + offset, mm_center[1] + offset),
        (mm_center[0] - offset, mm_center[1] + offset),
        (mm_center[0] - offset, mm_center[1] - offset)  # Fecha o quadrado
    ]
    galvo_corners = [mm_to_galvo(x, y) for (x, y) in corners]
    for x, y in galvo_corners:
        for i in range(1):
            c.light(x, y)

# -----------------------------------------------------------------
# Função: Inicia a calibração e a thread de desenho contínuo
# -----------------------------------------------------------------
def start_calibration():
    global saved_points, calibration_active, current_calibration_point, draw_thread, processing_click
    saved_points = []
    if calibration_points:
        current_calibration_point = calibration_points[0]
        calibration_active = True
        processing_click = False
        with controller.lighting() as c:
            draw_square_zero_point(c, current_calibration_point["mm"])
        draw_thread = threading.Thread(target=continuous_draw_calibration, daemon=True)
        draw_thread.start()
        print("Laser posicionado em:", current_calibration_point)
        return current_calibration_point["name"]
    else:
        return None

# -----------------------------------------------------------------
# Função: Salva o ponto de calibração e atualiza para o próximo
# -----------------------------------------------------------------
def save_calibration_point(point_name, click_x, click_y):
    global current_calibration_point, calibration_active, processing_click, last_click_time
    now = time.time()
    # Debounce de 0.3 segundos
    if now - last_click_time < 0.3 or processing_click:
        print("Clique ignorado devido a debounce ou clique em processamento.")
        return current_calibration_point["name"] if current_calibration_point else None

    processing_click = True
    last_click_time = now

    idx = len(saved_points)
    if idx < len(calibration_points):
        expected_point = calibration_points[idx]
        if expected_point["name"] != point_name:
            print("Aviso: Ponto inesperado. Esperado:", expected_point["name"], "Recebido:", point_name)
        saved_points.append({
            "name": expected_point["name"],
            "mm": expected_point["mm"],
            "click": (click_x, click_y)
        })
        print(f"Ponto {expected_point['name']} salvo com click em: ({click_x}, {click_y})")
        if len(saved_points) < len(calibration_points):
            current_calibration_point = calibration_points[len(saved_points)]
            print("Mover laser para:", current_calibration_point)
            with controller.lighting() as c:
                draw_square_zero_point(c, current_calibration_point["mm"])
            processing_click = False
            return current_calibration_point["name"]
        else:
            calibration_active = False
            print("Calibração completa. Pontos salvos:", saved_points)
            update_transformation_matrix()
            processing_click = False
            return None
    else:
        print("Todos os pontos já foram calibrados.")
        processing_click = False
        return None

# -----------------------------------------------------------------
# Função: Finaliza a calibração
# -----------------------------------------------------------------
def finalize_calibration():
    global calibration_active
    calibration_active = False
    if draw_thread is not None:
        draw_thread.join()
    print("Finalizando calibração. Pontos salvos:", saved_points)
    update_transformation_matrix()
    return "Calibração concluída com sucesso."

# -----------------------------------------------------------------
# Função: Salva os dados de calibração em arquivo (JSON)
# -----------------------------------------------------------------
def save_calibration_data(filename="calibration_data.txt"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(saved_points, f, indent=4)
        print("Dados de calibração salvos em", filename)
    except Exception as e:
        print("Erro ao salvar dados de calibração:", e)

def load_calibration_data(filename="calibration_data.txt"):
    global saved_points
    try:
        with open(filename, "r", encoding="utf-8") as f:
            saved_points = json.load(f)
        print("Dados de calibração carregados de", filename)
        update_transformation_matrix()
    except Exception as e:
        print("Erro ao carregar dados de calibração:", e)

# --- Funções para conversão pixel -> mm ---
def compute_affine_transform_mm(camera_pts, mm_points):
    import numpy as np
    import cv2
    src = np.array(camera_pts[:3], dtype=np.float32)
    dst = np.array(mm_points[:3], dtype=np.float32)
    print("Pontos da câmera:", src)
    print("Pontos em mm:", dst)
    M = cv2.getAffineTransform(src, dst)
    return M

def pixel_to_mm(pixel_coord, transform_matrix):
    import numpy as np
    import cv2
    pt = np.array([[pixel_coord]], dtype=np.float32)
    mm_pt = cv2.transform(pt, transform_matrix)
    return tuple(mm_pt[0][0])

def update_transformation_matrix():
    global affine_transform_matrix
    if len(saved_points) >= 3:
        camera_pts = [p["click"] for p in saved_points[:3]]
        mm_points = [p["mm"] for p in calibration_points[:3]]
        affine_transform_matrix = compute_affine_transform_mm(camera_pts, mm_points)
        print("Matriz de transformação calculada:", affine_transform_matrix)
        return affine_transform_matrix
    else:
        print("Não há pontos suficientes para calcular a matriz de transformação.")
        affine_transform_matrix = None
        return None

def parse_gcode(file_path):
    points = []      
    current_x = None 
    current_y = None 
    current_s = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("Frame:"):
                continue
            x_match = re.search(r'X([-+]?[0-9]*\.?[0-9]+)', line)
            y_match = re.search(r'Y([-+]?[0-9]*\.?[0-9]+)', line)
            s_match = re.search(r'S([-+]?[0-9]*\.?[0-9]+)', line)
            if x_match:
                current_x = abs(float(x_match.group(1)))
            if y_match:
                current_y = abs(float(y_match.group(1)))
            if s_match:
                current_s = float(s_match.group(1))
            if current_x is not None and current_y is not None and current_s is not None:
                points.append((current_x, current_y, current_s))
    return points

def get_center(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx = sum(xs) / len(points)
    cy = sum(ys) / len(points)
    return cx, cy

def get_center_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    return cx, cy

def center_art(points):
    #cx, cy = get_center(points)
    cx, cy = get_center_bbox(points)
    print("Centro calculado para centralização:", (cx, cy))
    return [(x - cx, y - cy, s) for (x, y, s) in points]

def set_gcode_points(file_path):
    global points
    points = parse_gcode(file_path)
    points = center_art(points)
    print("Pontos após centralização:", points)
    print("Centro dos pontos centralizados:", get_center([(x, y) for (x, y, s) in points]))

def mm_to_galvo(x_mm, y_mm, field_size_mm=200, galvo_range=65536, correction_x=0.864, correction_y=0.874):
    scale = galvo_range / field_size_mm
    center_offset = galvo_range / 2  
    galvo_x = x_mm * scale * correction_x + center_offset
    galvo_y = y_mm * scale * correction_y + center_offset
    return int(galvo_x), int(galvo_y)

def scale_art_points(scale_factor):
    """
    Escala os pontos da arte de forma uniforme sem distorcer,
    mantendo o centro dos pontos inalterado.
    
    Parâmetros:
        scale_factor (float): Fator de escala. Valores > 1 aumentam o tamanho,
                              valores < 1 diminuem o tamanho.
    
    Retorna:
        Lista de pontos escalados no formato [(x, y, s), ...].
    """
    # Calcula o centro dos pontos
    cx, cy = get_center_bbox(points)
    scaled_points = []
    for (x, y, s) in points:
        # Escala cada ponto em relação ao centro
        new_x = cx + (x - cx) * scale_factor
        new_y = cy + (y - cy) * scale_factor
        scaled_points.append((new_x, new_y, s))
    return scaled_points

def set_laser_parameters(power, speed, line_thickness):
    global laser_power, laser_speed, laser_line_thickness
    laser_power = power
    laser_speed = speed
    laser_line_thickness = line_thickness
    print("Parâmetros do laser atualizados: Potência:", laser_power, "Velocidade:", laser_speed, "Espessura de Linhas:", laser_line_thickness)

# Offsets para ajuste fino (em mm)
def set_offsets(x, y):
    global offset_x, offset_y
    offset_x = y
    offset_y = x
    print("Offsets atualizados para:", offset_x, offset_y)

def set_light_offsets(x, y):
    global offset_x_light, offset_y_light
    offset_x_light = y
    offset_y_light = x
    print("Offsets atualizados para:", offset_x_light, offset_y_light)

def StopContinuousMarking():
    print("Parando a marcação contínua.")
    #controller.remove(draw_camera)
    return "Parando a marcação contínua"

def cancel_LightContinuousCommand():
    print("Parando a marcação contínua.")
    # Mantém a função original – integração com C#/Python
    CancelLightContinuousCommand()
    return "Parando a marcação contínua"

def mark_command(x, y, angle):
    print("Executando MarkCommand com pixel:", (x, y))
    draw_camera((x, y), angle)
    return f"Arte enviada na posição da circunferência: ({x}, {y} - Angulo: {int(angle)})"

def light_command(x , y, angle):
    print("Executando LightCommand com pixel", (x, y))
    light_frame((x, y), angle)
    return f"Light da Arte enviada na posição da circunferência: ({x}, {y}) - Angulo: {int(angle)}"

def scale_command(scale_factor_received):
    global _scale_factor
    print("Executando ScaleCommand com fator de escala:", _scale_factor)
    _scale_factor = scale_factor_received
    return f"Arte escalada para {int(_scale_factor * 100)}% - Fator de Escala: {int(_scale_factor)}x"

def convert_to_centered_coords(x, y, image_width, image_height):
    center_x = image_width / 2
    center_y = image_height / 2
    return x - center_x, center_y - y  # Inverte Y para que positivo seja para cima

def rotate_point_around_center(x, y, angle, cx, cy):
    rad = math.radians(angle)
    x_shift = x - cx
    y_shift = y - cy
    x_rot = x_shift * math.cos(rad) - y_shift * math.sin(rad)
    y_rot = x_shift * math.sin(rad) + y_shift * math.cos(rad)
    return x_rot + cx, y_rot + cy

def get_center(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx = sum(xs) / len(points)
    cy = sum(ys) / len(points)
    return cx, cy

def rotate_art_points(centered_points, angle):
    """
    Rotaciona a lista de pontos (cada um como (x_mm, y_mm, s_val))
    em torno da origem – assumindo que já foram centralizados.
    """
    print("Rotacionando pontos com ângulo:", angle)
    rotated = []
    for (x_mm, y_mm, s_val) in centered_points:
        x_rot = x_mm * math.cos(math.radians(angle)) - y_mm * math.sin(math.radians(angle))
        y_rot = x_mm * math.sin(math.radians(angle)) + y_mm * math.cos(math.radians(angle))
        rotated.append((x_rot, y_rot, s_val))
    print("Pontos rotacionados:", rotated)
    return rotated

def draw_camera(pixel_tuple, angle, image_width=640, image_height=480, display_width=None, display_height=None):
    if display_width is not None and display_height is not None:
        scale_x = image_width / display_width
        scale_y = image_height / display_height
        pixel_tuple = (pixel_tuple[0] * scale_x, pixel_tuple[1] * scale_y)
        print("Pixel ajustado para calibração:", pixel_tuple)
    
    print("Entrou na função draw_camera com pixel_tuple =", pixel_tuple)
    
    converted_mm = pixel_to_mm((pixel_tuple[0], pixel_tuple[1]), affine_transform_matrix)
    print("Converted mm:", converted_mm)
    base_mm = converted_mm
    
    # Debug: imprime o centro dos pontos da arte antes da rotação
    center = get_center([(x, y) for (x, y, s) in points])
    print("Centro dos pontos (antes da rotação):", center)

    # Aplica a escala de forma local
    scaled_points = scale_art_points(_scale_factor)
    
    # Aplica a rotação – os pontos já foram centralizados em set_gcode_points
    rotated_points = rotate_art_points(scaled_points, angle)
    print("Centro dos pontos rotacionados (deve ser próximo de 0,0):", get_center([(x, y) for (x, y, s) in rotated_points]))
    
    # Usa offsets consistentes
    total_offset_x = offset_x + offset_x_light
    total_offset_y = offset_y + offset_y_light

    ####light
    tam_x_mm, tam_y_mm = converted_mm    
    # Obtém os pontos extremos (bounding box)
    frame_points = get_frame_points(scaled_points)
    # Prepara os pontos para rotação (adiciona s=0)
    frame_points_with_s = [(x, y, 0) for (x, y) in frame_points]
    # Aplica a rotação usando a função já existente
    frame_points_rotated = rotate_art_points(frame_points_with_s, angle)
    # Remove o valor 's' para usar somente (x, y)
    frame_points_rotated = [(x, y) for (x, y, s) in frame_points_rotated]
    
    #controller = GalvoController(r"C:\Users\Lucas - Due Laser\Source\Repos\DueStudio5\AvaloniaDueStudio5\camera\default.json")
    controller = GalvoController(settings_file=__settings__)
    with controller.marking() as c:
        c.set_mark_speed(1)
        # Desenho de referência (primeira parte)
        # Define o ponto de início
        start_x, start_y = mm_to_galvo(total_offset_x + tam_x_mm, total_offset_y + tam_y_mm)
        c.goto(start_x, start_y)
        # Desenha o frame conectando os pontos extremos
        for i in range(10):
            for (x_mm, y_mm) in frame_points_rotated:
                x, y = mm_to_galvo(x_mm + total_offset_x + tam_x_mm, y_mm + total_offset_y + tam_y_mm)
                c.light(x, y)

        c.set_mark_speed(laser_speed)
        c.set_power(laser_power)
        c.set_fly_res(0, 99, 1000, laser_line_thickness)
        # Desenho final (segunda parte)
        start_x, start_y = mm_to_galvo(
            offset_x + base_mm[0],
            offset_y + base_mm[1]
        )
        c.goto(start_x, start_y)
        for (x_mm, y_mm, s_val) in rotated_points:
            x, y = mm_to_galvo(
                x_mm + offset_x + base_mm[0],
                y_mm + offset_y + base_mm[1]
            )
            if s_val == 0:
                c.goto(x, y)
            else:
                c.mark(x, y)
                
    controller.remove(draw_camera)

def light_camera(pixel_tuple, angle, image_width=640, image_height=480, display_width=None, display_height=None):
    if display_width is not None and display_height is not None:
        scale_x = image_width / display_width
        scale_y = image_height / display_height
        pixel_tuple = (pixel_tuple[0] * scale_x, pixel_tuple[1] * scale_y)
        print("Pixel ajustado para calibração:", pixel_tuple)
    
    converted_mm = pixel_to_mm((pixel_tuple[0], pixel_tuple[1]), affine_transform_matrix)
    tam_x_mm, tam_y_mm = converted_mm
    print("Converted mm (light):", converted_mm)
    
    center = get_center([(x, y) for (x, y, s) in points])
    print("Centro dos pontos para rotação (light):", center)
    
    #controller = GalvoController(r"C:\Users\Lucas - Due Laser\Source\Repos\DueStudio5\AvaloniaDueStudio5\camera\default.json")
    controller = GalvoController(settings_file=__settings__)
    with controller.lighting() as c:
        total_offset_x = offset_x + offset_x_light
        total_offset_y = offset_y + offset_y_light
        start_x, start_y = mm_to_galvo(
            total_offset_x + tam_x_mm,
            total_offset_y + tam_y_mm
        )
        c.goto(start_x, start_y)
        for (x_mm, y_mm, s_val) in points:
            x, y = mm_to_galvo(
                x_mm + total_offset_x + tam_x_mm,
                y_mm + total_offset_y + tam_y_mm
            )
            if s_val == 0:
                c.goto(x, y)
            else:
                c.light(x, y)
                    
    controller.remove(light_camera)
    # Chama a função de rotação para teste
    light_camera_rotated(pixel_tuple, angle, image_width, image_height, display_width, display_height)

def light_camera_rotated(pixel_tuple, angle, image_width=640, image_height=480, display_width=None, display_height=None):
    if display_width is not None and display_height is not None:
        scale_x = image_width / display_width
        scale_y = image_height / display_height
        pixel_tuple = (pixel_tuple[0] * scale_x, pixel_tuple[1] * scale_y)
        print("Pixel ajustado para calibração (rotated):", pixel_tuple)
    
    converted_mm = pixel_to_mm((pixel_tuple[0], pixel_tuple[1]), affine_transform_matrix)
    tam_x_mm, tam_y_mm = converted_mm
    print("Converted mm (rotated):", converted_mm)

    # Aplica a escala de forma local
    scaled_points = scale_art_points(_scale_factor)
    
    rotated_points = rotate_art_points(scaled_points, angle)
    total_offset_x = offset_x + offset_x_light
    total_offset_y = offset_y + offset_y_light
    
    with controller.lighting() as c:
        start_x, start_y = mm_to_galvo(
            total_offset_x + tam_x_mm,
            total_offset_y + tam_y_mm
        )
        c.goto(start_x, start_y)
        for (x_mm, y_mm, s_val) in rotated_points:
            x, y = mm_to_galvo(
                x_mm + total_offset_x + tam_x_mm,
                y_mm + total_offset_y + tam_y_mm
            )
            if s_val == 0:
                c.goto(x, y)
            else:
                c.light(x, y)
                    
    controller.remove(light_camera_rotated)

# ------------------------------------------------------------------------------------
# Modo contínuo – Controle via teclado (não altere os nomes ou a estrutura original)
# ------------------------------------------------------------------------------------
continuous_active = False

def toggle_LightContinuousCommand(x, y,angle, image_width=640, image_height=480, display_width=None, display_height=None):
    global continuous_active
    pixel_tuple = (x, y)
    if not continuous_active:
        continuous_active = True
        print("Modo contínuo iniciado para a posição:", pixel_tuple)
        while continuous_active:
            try:
                light_frame(pixel_tuple, angle)
            except Exception as ex:
                print("Erro ao enviar comando light_camera:", ex)
                continuous_active = False
                break
        print("Loop contínuo finalizado")
        return "Modo contínuo finalizado"
    else:
        continuous_active = False
        controller.shutdown()
        print("Modo contínuo cancelado")
        return "Light contínuo cancelado"

def on_release(key):
    #if key == keyboard.Key.space: # ou qualquer outra tecla para parar
        global continuous_active
        continuous_active = False
        controller.shutdown()

listener = keyboard.Listener(on_release=on_release)
listener.start()


# ------------------------------------------------------------------------------------
# Modo contínuo – Controle via botão
# ------------------------------------------------------------------------------------

"""
# Variáveis globais de controle
continuous_active = False
continuous_thread = None

# --- Função de execução do light contínuo em thread separada ---
def continuous_light_loop(pixel_tuple, angle, image_width, image_height, display_width, display_height):
    global continuous_active
    # Ajusta o pixel, se necessário
    if display_width is not None and display_height is not None:
        scale_x = image_width / display_width
        scale_y = image_height / display_height
        pixel_tuple_scaled = (pixel_tuple[0] * scale_x, pixel_tuple[1] * scale_y)
        print("Pixel ajustado para calibração (frame):", pixel_tuple_scaled)
    else:
        pixel_tuple_scaled = pixel_tuple

    # Converte coordenadas de pixel para mm (utilize sua função existente)
    converted_mm = pixel_to_mm((pixel_tuple_scaled[0], pixel_tuple_scaled[1]), affine_transform_matrix)
    tam_x_mm, tam_y_mm = converted_mm
    print("Converted mm (frame):", converted_mm)

    # Obtém os pontos do bounding box e aplica rotação
    frame_points = get_frame_points()
    frame_points_with_s = [(x, y, 0) for (x, y) in frame_points]
    frame_points_rotated = rotate_art_points(frame_points_with_s, angle)
    frame_points_rotated = [(x, y) for (x, y, s) in frame_points_rotated]

    total_offset_x = offset_x + offset_x_light
    total_offset_y = offset_y + offset_y_light

    try:
        # Abre o contexto de iluminação uma única vez
        with controller.lighting() as c:
            start_x, start_y = mm_to_galvo(total_offset_x + tam_x_mm, total_offset_y + tam_y_mm)
            c.goto(start_x, start_y)
            print("Contexto de iluminação aberto. Iniciando loop contínuo.")

            while continuous_active:
                # Para cada iteração, percorre os pontos e envia o comando de light
                for (x_mm, y_mm) in frame_points_rotated:
                    if not continuous_active:
                        print("Cancelado dentro do loop")
                        break
                    x, y = mm_to_galvo(
                        x_mm + total_offset_x + tam_x_mm,
                        y_mm + total_offset_y + tam_y_mm
                    )
                    c.light(x, y)
                    c.light_on()
                time.sleep(0.1)  # intervalo para evitar sobrecarga
    except Exception as ex:
        print("Erro no loop contínuo:", ex)
    finally:
        controller.shutdown()
        print("Loop contínuo finalizado.")

# --- Função para iniciar o modo contínuo (chamada pelo botão no software) ---
def toggle_LightContinuousCommand(x, y, angle, image_width=640, image_height=480, display_width=None, display_height=None):
    global continuous_active, continuous_thread
    if not continuous_active:
        continuous_active = True
        pixel_tuple = (x, y)
        # Inicia a thread para executar o loop de light contínuo
        continuous_thread = threading.Thread(
            target=continuous_light_loop,
            args=(pixel_tuple, angle, image_width, image_height, display_width, display_height)
        )
        continuous_thread.daemon = True  # para não travar na finalização do programa
        continuous_thread.start()
        print("Modo contínuo iniciado para a posição:", pixel_tuple)
        return "Modo contínuo iniciado"
    else:
        return "Modo contínuo já está ativo"

# --- Função para cancelar o modo contínuo (pode ser chamada pelo botão de cancel no software) ---
def cancel_LightContinuousCommand():
    global continuous_active, continuous_thread
    continuous_active = False
    # Se necessário, aguarda a thread terminar (com timeout para não travar)
    if continuous_thread is not None:
        continuous_thread.join(timeout=1)
    controller.shutdown()
    print("Modo contínuo cancelado")
    return "Continuous light cancelled"

# --- Listener para a tecla espaço (cancelamento assíncrono) ---
def on_key_release(key):
    if key == keyboard.Key.space:
        cancel_LightContinuousCommand()
        print("Cancelamento via tecla espaço")

# Inicia o listener para a tecla espaço (em thread separada)
listener = keyboard.Listener(on_release=on_key_release)
listener.start()

"""