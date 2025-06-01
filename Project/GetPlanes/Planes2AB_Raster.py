# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 13:25:03 2025
@author: DKR

"""
import os
import ast
import math
import numpy as np
from shapely.geometry import LineString, Polygon, MultiLineString, GeometryCollection
from shapely.ops import polygonize, unary_union

# Adjust to your working folder:
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
os.chdir(directory)

# AutoCAD color → feedrate (mm/s)
COLOR_SPEED_MAPPING = {
    1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8,
    256: 1.0,
    5: 1.2, 6: 1.4, 7: 1.6, 8: 1.8, 9: 2.0
}

# Fill parameters
VOXEL_DIAMETER = 0.2  # μm
OVERLAP = 0.5  # fraction
ARC_RESOLUTION = 30  # Points per full arc

# -----------------------------------------------------------------------------
# 1. Parse processed planes file (FIXED KEYS)
# -----------------------------------------------------------------------------
def parse_angles(line):
    parts = line.split(":", 1)[1].strip().replace("°", "")
    angle_parts = parts.split("-")
    if len(angle_parts) >= 2:
        try:
            start_angle = float(angle_parts[0].strip())
            end_angle = float(angle_parts[1].strip())
            return (start_angle, end_angle)
        except ValueError:
            return None
    return None

def interpolate_arc(segment, resolution, extrusion=(0.0, 0.0, 1.0)):
    if "angulos" not in segment or segment["angulos"] is None:
        return [segment["start"], segment["end"]]  # <--- Claves en inglés
    
    start_angle, end_angle = segment["angulos"]
    center = segment["centro"]
    radius = segment["radio"]
    extrusion_z = extrusion[2] if len(extrusion) > 2 else 1.0
    
    # Direction handling
    if extrusion_z < 0:  # Clockwise
        if end_angle < start_angle:
            end_angle += 360
        angles = np.linspace(start_angle, end_angle, resolution + 1)
    else:  # Counter-Clockwise
        if end_angle > start_angle:
            start_angle += 360
        angles = np.linspace(start_angle, end_angle, resolution + 1)[::-1]
    
    # Generate points
    points = []
    for angle in angles:
        angle_deg = angle % 360
        rad = math.radians(angle_deg)
        x = center[0] + radius * math.cos(rad)
        y = center[1] + radius * math.sin(rad)
        z = center[2] if len(center) > 2 else 0.0
        points.append((x, y, z))
    
    # Ensure start/end match
    if not np.allclose(points[0], segment["start"], atol=1e-5):  # <--- Clave en inglés
        points = list(reversed(points))
    return points

def parse_planos(file_path):
    planes = []
    current = None
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("PLANOS PROCESADOS:"):
            i += 1; continue
        if line.startswith("Plano"):
            if current: planes.append(current)
            current = {'metadata': line, 'extrusion': None, 'edges': []}
            i += 1; continue
        if current:
            if "Vector de extrusión" in line:
                try:
                    current['extrusion'] = ast.literal_eval(line.split(":",1)[1].strip())
                except:
                    current['extrusion'] = (0.0, 0.0, 1.0)
            elif line.startswith("Arista"):
                edge = {'start': None, 'end': None}  # <--- Inicializar claves
                i += 1
                while i < len(lines) and lines[i].startswith("    "):
                    sl = lines[i].strip()
                    if sl.startswith("Tipo:"):
                        edge['type'] = sl.split(":",1)[1].strip()
                    elif sl.startswith("Color:"):
                        try: edge['color'] = int(sl.split(":",1)[1].strip())
                        except: edge['color'] = None
                    elif sl.startswith("Desde:"):  # Parsear como 'start'
                        try: edge['start'] = ast.literal_eval(sl.split(":",1)[1].strip())
                        except: edge['start'] = None
                    elif sl.startswith("Hasta:"):  # Parsear como 'end'
                        try: edge['end'] = ast.literal_eval(sl.split(":",1)[1].strip())
                        except: edge['end'] = None
                    elif sl.startswith("Radio:"):
                        try: edge['radio'] = float(sl.split(":",1)[1].strip())
                        except: edge['radio'] = None
                    elif sl.startswith("Ángulos:"):
                        edge['angulos'] = parse_angles(sl)
                    elif sl.startswith("Centro:"):
                        try: edge['centro'] = ast.literal_eval(sl.split(":",1)[1].strip())
                        except: edge['centro'] = None
                    elif sl.startswith("Entidad original:"):
                        if i+1 < len(lines):
                            entity_line = lines[i+1].strip()
                            try:
                                edge['entity'] = ast.literal_eval(entity_line)
                                edge['extrusion'] = edge['entity'].get('extrusion', (0.0, 0.0, 1.0))
                            except:
                                edge['entity'] = None
                            i += 1  # Skip line
                    i += 1
                current['edges'].append(edge)
                continue
        i += 1
    if current: planes.append(current)
    return planes

# -----------------------------------------------------------------------------
# 2. Raster scanline generator
# -----------------------------------------------------------------------------
def generate_raster_lines(polygon: Polygon, spacing: float):
    minx, miny, maxx, maxy = polygon.bounds
    y = miny
    coords2d = []
    forward = True

    while y <= maxy:
        scan = LineString([(minx-spacing, y), (maxx+spacing, y)])
        inter = polygon.intersection(scan)
        
        if isinstance(inter, LineString):
            segs = [inter]
        elif isinstance(inter, MultiLineString):
            segs = list(inter.geoms)
        elif isinstance(inter, GeometryCollection):
            segs = [g for g in inter.geoms if isinstance(g, LineString)]
        else:
            segs = []

        for seg in segs:
            c = list(seg.coords)
            if not forward:
                c.reverse()
            coords2d.extend(c)
            forward = not forward

        y += spacing

    return coords2d

# -----------------------------------------------------------------------------
# 3. Generate AeroBasic code
# -----------------------------------------------------------------------------
def generate_aerobasic_plane_fill_code(planes, filename="Raster_Fill.abm"):
    all_pts = []
    for pl in planes:
        for e in pl['edges']:
            if e['start'] and e['end']:
                all_pts.extend([e['start'], e['end']])
    all_pts = np.array(all_pts)
    origin_x = float(np.min(all_pts[:,0])/100)
    origin_y = float(np.min(all_pts[:,1])/100)
    origin_z = float(np.max(all_pts[:,2])/100)

    margin_xy = 10.0/1000
    margin_z  = 100.0/1000

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

    for idx, plane in enumerate(planes, start=1):
        n = np.array(plane['extrusion'], float)
        n /= np.linalg.norm(n)
        arb = np.array([1,0,0])
        if abs(np.dot(arb,n)) > 0.9:
            arb = np.array([0,1,0])
        u = np.cross(n, arb); u /= np.linalg.norm(u)
        v = np.cross(n, u)

        pts3d = np.array([e['start'] for e in plane['edges'] if e['start']] +
                         [e['end'] for e in plane['edges'] if e['end']])
        origin_plane = np.mean(pts3d, axis=0)

        def to2d(p):
            d = np.array(p) - origin_plane
            return (float(np.dot(d,u)), float(np.dot(d,v)))

        # Build edges with arc handling
        lines2d = []
        for e in plane['edges']:
            if not e['start'] or not e['end']:
                print(f"[WARN] Edge missing start/end: {e}")
                continue
            
            tipo = e.get('type', '').upper()
            if 'ARC' in tipo and e.get('radio') and e.get('angulos') and e.get('centro'):
                extrusion = e.get('extrusion', (0.0, 0.0, 1.0))
                points_3d = interpolate_arc(e, ARC_RESOLUTION, extrusion)
                points_2d = [to2d(p) for p in points_3d]
                if len(points_2d) >= 2:
                    lines2d.append(LineString(points_2d))
            else:
                start_2d = to2d(e['start'])
                end_2d = to2d(e['end'])
                lines2d.append(LineString([start_2d, end_2d]))

        # Create polygon
        merged = unary_union(lines2d).buffer(1e-5)
        polys2d = list(polygonize(merged))
        if not polys2d:
            print(f"[ERROR] Plane {idx}: No polygon formed. Check edge connectivity.")
            continue
            
        poly2d = max(polys2d, key=lambda P: P.area)
        if not poly2d.is_valid:
            poly2d = poly2d.buffer(0)

        spacing = VOXEL_DIAMETER * (1-OVERLAP)
        raster2d = generate_raster_lines(poly2d, spacing)

        raster3d = [tuple(origin_plane + x*u + y*v) for x,y in raster2d]

        color_val = plane['edges'][0].get('color', 256)
        speed = COLOR_SPEED_MAPPING.get(color_val, 1.0)

        motion_blocks.append(f"\n' --- Raster fill Plane {idx} ---")
        motion_blocks.append(f"$SPEED = {speed:.1f}")

        if raster3d:
            x0,y0,z0 = raster3d[0]
            motion_blocks.append(
                f"LINEAR X{(x0-origin_x)/1000:.10f} "
                f"Y{(y0-origin_y)/1000:.10f} "
                f"Z{(z0-origin_z)/1000:.10f} F $SPEED"
            )
            motion_blocks.append("WAIT MOVEDONE X Y Z A; dwell 0.1; ShutterOpen")
            for x,y,z in raster3d[1:]:
                motion_blocks.append(
                    f"LINEAR X{(x-origin_x)/1000:.10f} "
                    f"Y{(y-origin_y)/1000:.10f} "
                    f"Z{(z-origin_z)/1000:.10f} F $SPEED"
                )
            motion_blocks.append("ShutterClose")

    footer = """
' --- Finalizacion ---
'SCOPETRIG STOP
'DATACOLLECT STOP
'FILECLOSE $fileNAME

VELOCITY OFF
MSGDISPLAY 0, "Proceso laser completado con exito."
END PROGRAM"""
    with open(filename, "w") as f:
        f.write(header)
        f.write("\n".join(motion_blocks))
        f.write(footer)
    print(f"Generated {filename}")

# -----------------------------------------------------------------------------
# 4. Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    planes = parse_planos("planos_procesadosRdAOut.txt")
    generate_aerobasic_plane_fill_code(planes, filename="CurvedPlane_Raster_CAD2AB.txt")
