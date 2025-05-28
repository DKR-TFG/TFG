# -*- coding: utf-8 -*-
"""
Created on Sun Jan 18 12:02:11 2025

@author: DKR
"""

import re
import os
import numpy as np

# Index Colors (From AutoCAD) ---> Speed - Dictionary 
COLOR_SPEED_MAPPING = {         #mm/s
    1: 0.2,                     #Red
    2: 0.4,                     #Yellow
    3: 0.6,                     #Green
    4: 0.8,                     #Cyan
    256: 1,                     #Default
    5: 1.2,                     #Blue
    6: 1.4,                     #Magenta
    7: 1.6,                     #White
    8: 1.8,                     #Dark-Gray
    9: 2                        #Light-Gray
} 

def parse_line(line):
    """
    Parsea una línea con el formato:
      De (x1, y1) a (x2, y2): shutter <state>
    y retorna una tupla: (x1, y1, x2, y2, shutter_state)
    """
    pattern = r"De\s*\(\s*([^,]+),\s*([^)]+)\s*\)\s*a\s*\(\s*([^,]+),\s*([^)]+)\s*\):\s*shutter\s*(\w+)"
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        x1 = float(match.group(1))
        y1 = float(match.group(2))
        x2 = float(match.group(3))
        y2 = float(match.group(4))
        shutter_state = match.group(5).lower()  # debe ser "open" o "closed"
        return (x1, y1, x2, y2, shutter_state)
    else:
        return None

def generate_aerobasic_code(segments, z_coord=-50.0, speed=0.8):
    """
    Genera código AeroBasic a partir de segmentos.
    Cada segmento es una tupla: (x1, y1, x2, y2, shutter_state)
    
    Se calcula el origen global (mínimo X, mínimo Y y máximo Z) a partir de todos los puntos
    y se aplican márgenes para el posicionamiento inicial.
    Las coordenadas se convierten a mm (dividiendo entre 1000) y se expresan con 10 decimales.
    """
    # --- Cálculo del origen global ---
    all_points = []
    for seg in segments:
        x1, y1, x2, y2, _ = seg
        # Se asume que z_coord es constante para todos los segmentos
        all_points.append((x1, y1, z_coord))
        all_points.append((x2, y2, z_coord))
    all_points = np.array(all_points)
    origin_x = float(np.min(all_points[:, 0]))
    origin_y = float(np.min(all_points[:, 1]))
    origin_z = float(np.max(all_points[:, 2]))
    print(origin_x,origin_y,origin_z)
    
    # --- Márgenes (en mm) ---
    margin_xy = 10.0 / 1000
    margin_z  = 100.0 / 1000

    # --- Encabezado ---
    header = f"""
'==================================================
' AUTOGENERADO PARA SISTEMA LASER AEROTECH A3200
' ORIGEN: X{origin_x:.10f} Y{origin_y:.10f} Z{origin_z:.10f}
'==================================================

' --- Macros shutter laser ---
#define ShutterClose $DO0.Z = 0
#define ShutterOpen $DO0.Z = 1

' --- Declaracion de variables ---
DVAR $SPEED $numSamples $samplingTime $fileNAME

' --- Configuracion inicial ---
$SPEED = 1
MSGCLEAR -1
ShutterClose
HOME X Y Z A

' --- Parametros para recoleccion de datos ---
$numSamples = 71000	 'number of points to be collected
$samplingTime = 1 'in ms
'$strtask = 'YourPath' + 'YourFileName' + '.dat'
'$fileNAME = FILEOPEN $strtask, 0

' --- Especificar los datos que deben almacenarse --- 
'DATACOLLECT ITEM RESET	'reset previous data collection config
'DATACOLLECT ITEM 0, X, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 1, Y, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 2, Z, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 3, Z, DATAITEM_DigitalOutput, 0

' --- Recolectar datos del movimiento ---
'$Mode = 1 -> collects infinitely until data collect stop
DATACOLLECT START $fileNAME, $numSamples, $samplingTime, 1

' --- Habilitar ejes y E/S ---
ENABLE X Y Z

' --- Configurar modo velocidad continua ---
VELOCITY ON     'Do NOT decelerate between CONSECUTIVE moves
ABSOLUTE        'Absolute positioning and moves

' --- Posicionamiento inicial fuera del area de trabajo ---
LINEAR X{-margin_xy:.10f} Y{-margin_xy:.10f} Z{-margin_z:.10f} F $SPEED 

' --- Establecer nuevo origen de coordenadas ---
POSOFFSET SET X 0 Y 0 Z 0

' === SECUENCIA DE TRABAJO ===
'SCOPETRIG CONTINUOUS   'Trigger the scope to start collecting data 
'NEVER USE SCOPETRIG AND DATACOLLECT AT THE SAME TIME OR PC WILL CRASH
"""
    motion_blocks = []
    
    # --- Posicionamiento inicial ---
    if segments:
        first_seg = segments[0]
        start_x, start_y = first_seg[0], first_seg[1]
        # Convertir la posición inicial a mm (relativa al origen)
        init_x = (start_x - origin_x) / 1000
        init_y = (start_y - origin_y) / 1000
        init_z = (z_coord - origin_z) / 1000
        motion_blocks.append("")
        motion_blocks.append("' --- Mover a la posición inicial ---")
        motion_blocks.append(f"LINEAR X{init_x:.10f} Y{init_y:.10f} Z{init_z:.10f} F $SPEED  ' Punto 0 (inicio)")
    
    current_shutter = "closed"
    point_index = 1
    total_segments = len(segments)
    
    for seg in segments:
        x1, y1, x2, y2, shutter = seg
        
        # Cambiar estado del shutter si es necesario
        if shutter != current_shutter:
            if shutter == "open":
                motion_blocks.append("dwell 0.01")
                motion_blocks.append("ShutterOpen")
                motion_blocks.append("dwell 0.01")
            else:
                motion_blocks.append("ShutterClose")
                motion_blocks.append("dwell 0.1")
            current_shutter = shutter
        pt_x = (x2 - origin_x) / 1000
        pt_y = (y2 - origin_y) / 1000
        pt_z = (z_coord - origin_z) / 1000
        motion_blocks.append(f"LINEAR X{pt_x:.10f} Y{pt_y:.10f} Z{pt_z:.10f} F $SPEED  ' Punto {point_index}/{total_segments}")
        point_index += 1

    footer = """
ShutterClosed
' --- Finalizacion ---
VELOCITY OFF
MSGDISPLAY 0, "Proceso laser completado con exito."
END
"""
    all_lines = header.strip().split("\n") + motion_blocks + footer.strip().split("\n")
    return all_lines

def main():
    # Directorio de trabajo y archivos de entrada/salida
    directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
    os.chdir(directory)
    input_file = "trajectory.txt"          # Archivo de entrada (con encabezado)
    output_file = "RdA_CAD2AB.txt"     # Archivo de salida

    segments = []
    color_val = None
    constant_z_val = None

    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Se asume que las dos primeras líneas contienen el encabezado:
    # Ejemplo:
    #   Color extraído del Plano 1: 6
    #   Constante Z: 0.0
    if len(lines) >= 2:
        header_line1 = lines[0].strip()
        header_line2 = lines[1].strip()
        m = re.search(r"(?i)Color\s+extraido.*:\s*(\d+)", header_line1)
        if m:
            color_val = int(m.group(1))
        else:
            print("No se pudo extraer el color del encabezado; se usará valor por defecto.")
            color_val = 6
        m = re.search(r"(?i)Constante\s+Z:\s*([\d\.\-]+)", header_line2)
        if m:
            constant_z_val = float(m.group(1))
        else:
            print("No se pudo extraer la constante Z; se usará valor por defecto.")
            constant_z_val = -50.0
    else:
        print("Encabezado no encontrado; se usarán valores por defecto.")
        color_val = 6
        constant_z_val = -50.0

    # Procesar el resto del archivo: se ignoran líneas que no comienzan con "De ("
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("De ("):
            continue
        parsed = parse_line(line)
        if parsed:
            segments.append(parsed)
        else:
            print("Warning: Could not parse line:", line)
    
    if not segments:
        print("No valid segments were found in the input file.")
        return

    speed = COLOR_SPEED_MAPPING.get(color_val, 1)
    
    code_lines = generate_aerobasic_code(segments, z_coord=constant_z_val, speed=speed)
    
    with open(output_file, 'w') as f:
        for cl in code_lines:
            f.write(cl + "\n")
    
    print("AeroBasic code generated in", output_file)

if __name__ == '__main__':
    main()