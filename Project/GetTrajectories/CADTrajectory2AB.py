# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 15:35:44 2025

@author: DKR
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import splprep, splev, interp1d
import ast
import os 
# Index Colors (From AutoCAD) ---> Speed Dictionary 
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

# ==================================================
# 1. FUNCIÓN PARA LEER ARCHIVOS DE PARÁMETROS
# ==================================================
def parse_parameters(Input_File):
    """Lee y parsea archivos de parámetros de geometrías complejas"""
    entities = {}
    current_entity = None
    current_type = None
    
    with open(Input_File, 'r') as f:
        for line in f:
            line = line.strip()
            
            if line.startswith("====="):
                current_type = line.replace("=", "").strip()
                entities[current_type] = []
                continue
                
            if line.startswith("Entidad"):
                current_entity = {}
                entities[current_type].append(current_entity)
                continue
                
            if line.startswith("-"):
                key, value = line.split(":", 1)
                key = key.strip().replace("- ", "")
                value = value.strip()
                
                if key == 'color':
                    value = int(value)
                
                try:
                    if '[' in value or '(' in value:
                        parsed_value = ast.literal_eval(value)
                    else:
                        try:
                            parsed_value = float(value) if '.' in value else int(value)
                        except:
                            parsed_value = value
                    current_entity[key] = parsed_value
                except:
                    current_entity[key] = value

    return entities

# ==================================================
# 2. FUNCIONES PARA GENERAR TRAYECTORIAS
# ==================================================
def generate_parametric_helix(params):
    """Genera puntos para una hélice cónica paramétrica considerando axis_vector"""
    axis_base = np.array(params["axis_base"])
    axis_vector = np.array(params["axis_vector"])
    axis_vector = axis_vector / np.linalg.norm(axis_vector)  # Normalizar

    start = np.array(params["start_point"])
    radio_base = params["radio_base"]
    radio_top = params["radius"]
    turns = params["turns"]
    turn_height = params["turn_height"]
    H = turns * turn_height
    d = 1 if params["handedness"] == "counter clockwise" else -1

    # Definir un vector arbitrario que no sea paralelo a axis_vector
    arbitrary = np.array([0, 0, 1])
    if np.allclose(axis_vector, arbitrary):
        arbitrary = np.array([0, 1, 0])

    # Calcular dos vectores perpendiculares a axis_vector
    u = np.cross(axis_vector, arbitrary)
    u = u / np.linalg.norm(u)
    v = np.cross(axis_vector, u)
    v = v / np.linalg.norm(v)
    
    # Proyectar el vector de inicio sobre el plano definido por u y v
    delta = start - axis_base
    a = np.dot(delta, u)
    b = np.dot(delta, v)
    theta0 = np.arctan2(b, a)
    
    # Generación de la hélice
    t = np.linspace(0, 2 * np.pi * turns, 1000)
    # Radio variable de radio_base a radio_top
    r = radio_base + (radio_top - radio_base) / (2 * np.pi * turns) * t
    
    # Coordenadas de la hélice
    x = axis_base[0] + r * np.cos(theta0 + d * t) * u[0] + r * np.sin(theta0 + d * t) * v[0] + (H / (2 * np.pi * turns) * t) * axis_vector[0]
    y = axis_base[1] + r * np.cos(theta0 + d * t) * u[1] + r * np.sin(theta0 + d * t) * v[1] + (H / (2 * np.pi * turns) * t) * axis_vector[1]
    z = axis_base[2] + r * np.cos(theta0 + d * t) * u[2] + r * np.sin(theta0 + d * t) * v[2] + (H / (2 * np.pi * turns) * t) * axis_vector[2]
    
    return x, y, z

def generate_voxels(x, y, z, VOXEL_DIAMETER=0.2, overlap=0.5):
    """Calcula centros de vóxeles para cubrir la trayectoria"""
    # Cálculo de longitud de arco
    dx = np.diff(x)
    dy = np.diff(y)
    dz = np.diff(z)
    distances = np.sqrt(dx**2 + dy**2 + dz**2)
    s = np.insert(np.cumsum(distances), 0, 0)
    
    # Interpolación para muestreo equiespaciado
    fx = interp1d(s, x, 'linear')
    fy = interp1d(s, y, 'linear')
    fz = interp1d(s, z, 'linear')
    
    # Espaciado entre centros de vóxeles
    step = VOXEL_DIAMETER * (1 - overlap)
    s_samples = np.arange(0, s[-1], step)
    
    return fx(s_samples), fy(s_samples), fz(s_samples)

# ==================================================
# 3. VISUALIZACIÓN 3D
# ==================================================
def plot_trajectories(trajectories):
    """Crea una visualización 3D de las distintas trayectorias"""
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection='3d')
    
    colors = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5']
    
    for i, traj in enumerate(trajectories):
        label = traj['label']
        color = colors[i % len(colors)]
        
        if traj['type'] == 'HELIX':
            x, y, z = traj['points']
            ax.plot(x, y, z, linewidth=2, color=color, alpha=0.6, label=f'{label} trajectory')
        elif traj['type'] == 'LINE':
            start = traj['start']
            end = traj['end']
            x = [start[0], end[0]]
            y = [start[1], end[1]]
            z = [start[2], end[2]]
            ax.plot(x, y, z, linewidth=2, color=color, alpha=0.6, label=f'{label} trajectory')

    ax.set_xlabel('X [µm]', fontsize=12)
    ax.set_ylabel('Y [µm]', fontsize=12)
    ax.set_zlabel('Z [µm]', fontsize=12)
    ax.set_title('Waveguide', fontsize=14)
    plt.tight_layout()
#    ax.legend()
    plt.show()

# ==================================================
# 4. GENERACIÓN DE CÓDIGO AEROBASIC
# ==================================================
def generate_aerobasic_generic_laser(trajectories, filename="CAD2AB_0605.txt"):
    """Genera código AeroBasic para múltiples trayectorias"""
    # Determinar el origen global considerando todas las trayectorias
    all_points = []
    for traj in trajectories:
        if traj['type'] == 'HELIX':
            x, y, z = traj['points']
            all_points.extend(zip(x, y, z))
        elif traj['type'] == 'LINE':
            all_points.append(tuple(traj['start']))
            all_points.append(tuple(traj['end']))
    
    all_points = np.array(all_points)
    all_x = all_points[:, 0]
    all_y = all_points[:, 1]
    all_z = all_points[:, 2]
    
    origin_x = min(all_x)
    origin_y = min(all_y)
    origin_z = max(all_z)
    
    # Márgenes relativos al origen (coordenadas del código) en mm
    margin_xy = 10.0 / 1000
    margin_z  = 100.0 / 1000
    
    header = f"""
'==================================================
' AUTOGENERADO PARA SISTEMA LASER AEROTECH A3200
' ORIGEN: X{origin_x:.10f} Y{origin_y:.10f} Z{origin_z:.10f}
'==================================================

' --- Macros shutter laser ---
#define ShutterClose $DO0.Z = 0
#define ShutterOpen $DO0.Z = 1

' --- Declaración de variables ---
DVAR $SPEED $numSamples $samplingTime $fileNAME $Mode

' --- Configuracion inicial ---

$SPEED = 1
MSGCLEAR -1
ShutterClose
HOME X Y Z A

' --- Parametros para recoleccion de datos ---
$numSamples = 71000	 'number of points to be collected
$samplingTime = 1 'in ms
'$strtask = 'YourPath + YourFileName + .dat'    'Use double quotes 
'$fileNAME = FILEOPEN $strtask, 0

' --- Especificar los datos que deben almacenarse --- 
'DATACOLLECT ITEM RESET	'reset previous data collection config
'DATACOLLECT ITEM 0, X, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 1, Y, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 2, Z, DATAITEM_PositionFeedback
'DATACOLLECT ITEM 3, Z, DATAITEM_DigitalOutput, 0

' --- Recolectar datos del movimiento ---
'$Mode = 1 '-> collects infinitely until data collect stop
'DATACOLLECT START $fileNAME, $numSamples, $samplingTime, 1

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

    for traj in trajectories:
        label = traj['label']
        speed = traj['speed']
        motion_blocks.append(f"\n' --- Inicio de la trayectoria {label} ---")
        motion_blocks.append(f"$SPEED = {speed:.1f}")
        
        if traj['type'] == 'HELIX':
            # Para hélices, mantenemos el código proporcionado originalmente
            x_vox, y_vox, z_vox = traj['voxels']
            num_points = len(x_vox)
            
            # Ajustar coordenadas relativas al origen
            x_adj = [x - origin_x for x in x_vox]
            y_adj = [y - origin_y for y in y_vox]
            z_adj = [z - origin_z for z in z_vox]
            
            for i, (x, y, z) in enumerate(zip(x_adj, y_adj, z_adj)):
                # Convertir de um a mm
                x_mm = x / 1000
                y_mm = y / 1000
                z_mm = z / 1000
                motion_blocks.append(f"LINEAR X{x_mm:.10f} Y{y_mm:.10f} Z{z_mm:.10f} F $SPEED  ' Punto {i+1}/{num_points}")
                if i == 0:
                    motion_blocks.append("WAIT MOVEDONE X Y Z A")
                    motion_blocks.append("dwell 0.1")
                    motion_blocks.append("ShutterOpen")
            
            motion_blocks.append("ShutterClose")
        
        elif traj['type'] == 'LINE':
            start = traj['start']
            end = traj['end']
            
            # Ajustar coordenadas relativas al origen y convertir de um a mm
            x_start_mm = (start[0] - origin_x) / 1000
            y_start_mm = (start[1] - origin_y) / 1000
            z_start_mm = (start[2] - origin_z) / 1000
            
            x_end_mm = (end[0] - origin_x) / 1000
            y_end_mm = (end[1] - origin_y) / 1000
            z_end_mm = (end[2] - origin_z) / 1000
            
            motion_blocks.append(f"LINEAR X{x_start_mm:.10f} Y{y_start_mm:.10f} Z{z_start_mm:.10f} F $SPEED ' Posicionarse al inicio")
            motion_blocks.append(f"$SPEED = {speed:.1f}")
            motion_blocks.append("dwell 0.1")
            motion_blocks.append("ShutterOpen")
            motion_blocks.append(f"LINEAR X{x_end_mm:.10f} Y{y_end_mm:.10f} Z{z_end_mm:.10f} F $SPEED ' Movimiento lineal a lo largo de la linea")
            motion_blocks.append("ShutterClose")
    
    footer = """


' --- Finalizacion ---
'SCOPETRIG STOP
'DATACOLLECT STOP
'FILECLOSE $fileNAME

VELOCITY OFF
MSGDISPLAY 0, "Proceso laser completado con exito."
END"""

    with open(filename, "w") as f:
        f.write(header)
        f.write("\n".join(motion_blocks))
        f.write(footer)

    print(f"Script generado: {filename}")

# ==================================================
# 5. EJECUCIÓN PRINCIPAL
# ==================================================
if __name__ == "__main__":
    
    directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
    os.chdir(directory)
    Input_File = "params_helixpore_wg.txt"  
    VOXEL_DIAMETER = 0.2
    OVERLAP = 0.5 
    
    # Paso 1: Leer archivo
    entities = parse_parameters(Input_File)
    
    trajectories = []

    # Procesar entidades HELIX
    if "HELIX" in entities:
        for idx, helix_params in enumerate(entities["HELIX"]):
            try:
                # Generar hélice paramétrica
                x_param, y_param, z_param = generate_parametric_helix(helix_params)
                
                # Calcular vóxeles
                x_vox, y_vox, z_vox = generate_voxels(x_param, y_param, z_param, VOXEL_DIAMETER, OVERLAP)
                
                # Mapeo color-velocidad
                color_value = helix_params.get('color', 256)
                speed = COLOR_SPEED_MAPPING.get(color_value, 1.0)
                
                trajectories.append({
                    'type': 'HELIX',
                    'points': (x_param, y_param, z_param),
                    'voxels': (x_vox, y_vox, z_vox),
                    'label': f"HELIX_{idx+1}",
                    'speed': speed
                })
            except KeyError as e:
                print(f"Error en HELIX {idx+1}: El parámetro {e} no está definido.")
    
    # Procesar entidades LINE
    if "LINE" in entities:
        for idx, line_params in enumerate(entities["LINE"]):
            try:
                # Extraer puntos de inicio y fin
                start = line_params["start"]
                end = line_params["end"]
                
                # Mapeo color-velocidad
                color_value = line_params.get('color', 256)
                speed = COLOR_SPEED_MAPPING.get(color_value, 1.0)
                
                trajectories.append({
                    'type': 'LINE',
                    'start': start,
                    'end': end,
                    'label': f"LINE_{idx+1}",
                    'speed': speed
                })
            except KeyError as e:
                print(f"Error en LINE {idx+1}: El parámetro {e} no está definido.")
    
    # Verificar si hay trayectorias para procesar
    if trajectories:
        # Paso 5: Visualización
        plot_trajectories(trajectories)
        # Generar código de control
        generate_aerobasic_generic_laser(trajectories)
    else:
        print("No se encontraron trayectorias para procesar.")
