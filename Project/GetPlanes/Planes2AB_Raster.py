# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 13:25:03 2025
@author: DKR

Unified raster‐fill for arbitrarily oriented planes:
  1. Read processed planes (edges + extrusion vectors).
  2. For each plane:
     a. Build orthonormal frame (u,v,n) from extrusion.
     b. Project edges into the u–v plane (2D).
     c. Polygonize, then generate raster lines in 2D.
     d. Lift raster points back into world‐space 3D.
  3. Emit AeroBasic code.
"""

import os
import ast
import numpy as np
from shapely.geometry import LineString, Polygon, Point, MultiLineString, GeometryCollection
from shapely.ops import polygonize, unary_union

# Adjust to your working folder:
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
os.chdir(directory)

# AutoCAD color → feedrate (mm/s)
COLOR_SPEED_MAPPING = {
    1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8,
    256: 1.0,
    5: 1.2, 6: 1.4, 7: 1.6, 8: 1.8, 9: 2.0
}

# Fill parameters
VOXEL_DIAMETER = 0.2  # μm
OVERLAP        = 0.5  # fraction

# -----------------------------------------------------------------------------
# 1. Parse processed planes file
# -----------------------------------------------------------------------------
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
                    current['extrusion'] = None
            elif line.startswith("Arista"):
                edge = {}
                i += 1
                while i < len(lines) and lines[i].startswith("    "):
                    sl = lines[i].strip()
                    if sl.startswith("Tipo:"):
                        edge['type'] = sl.split(":",1)[1].strip()
                    elif sl.startswith("Color:"):
                        try: edge['color'] = int(sl.split(":",1)[1].strip())
                        except: edge['color'] = None
                    elif sl.startswith("Desde:"):
                        try: edge['start'] = ast.literal_eval(sl.split(":",1)[1].strip())
                        except: edge['start'] = None
                    elif sl.startswith("Hasta:"):
                        try: edge['end'] = ast.literal_eval(sl.split(":",1)[1].strip())
                        except: edge['end'] = None
                    i += 1
                current['edges'].append(edge)
                continue
        i += 1
    if current: planes.append(current)
    return planes

# -----------------------------------------------------------------------------
# 2. Raster scanline generator in 2D
# -----------------------------------------------------------------------------
def generate_raster_lines(polygon: Polygon, spacing: float):
    """
    Given a 2D polygon and line spacing, return a list of 2D points tracing
    a back-and-forth (raster) fill. Safely handles any intersection geometry.
    """
    minx, miny, maxx, maxy = polygon.bounds
    y = miny
    coords2d = []
    forward = True

    while y <= maxy:
        scan = LineString([(minx-spacing, y), (maxx+spacing, y)])
        inter = polygon.intersection(scan)

        # collect only LineString segments
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
# 3. Generate AeroBasic raster‐fill for ANY oriented plane
# -----------------------------------------------------------------------------
def generate_aerobasic_plane_fill_code(planes, filename="Raster_Fill.abm"):
    # 3a. Compute global origin from all planes
    all_pts = []
    for pl in planes:
        for e in pl['edges']:
            all_pts.extend([e['start'], e['end']])
    all_pts = np.array(all_pts)
    origin_x = float(np.min(all_pts[:,0])/100)
    origin_y = float(np.min(all_pts[:,1])/100)
    origin_z = float(np.max(all_pts[:,2])/100)

    margin_xy = 10.0/1000
    margin_z  = 100.0/1000

    # Header
    header = f"""
'==================================================
' AUTOGENERATED FOR LASER AEROTECH A3200
' ORIGIN: X{origin_x:.10f} Y{origin_y:.10f} Z{origin_z:.10f}
'==================================================
#define ShutterClose $DO0.Z=0
#define ShutterOpen  $DO0.Z=1
DVAR $SPEED $numSamples $samplingTime $fileNAME $Mode
$SPEED=1; MSGCLEAR -1; ShutterClose; HOME X Y Z A
ENABLE X Y Z; VELOCITY ON; ABSOLUTE
LINEAR X{-margin_xy:.10f} Y{-margin_xy:.10f} Z{-margin_z:.10f} F $SPEED
POSOFFSET SET X 0 Y 0 Z 0
"""
    motion_blocks = []

    for idx, plane in enumerate(planes, start=1):
        # build orthonormal frame (u,v,n)
        n = np.array(plane['extrusion'], float)
        n /= np.linalg.norm(n)
        arb = np.array([1,0,0])
        if abs(np.dot(arb,n)) > 0.9:
            arb = np.array([0,1,0])
        u = np.cross(n, arb); u /= np.linalg.norm(u)
        v = np.cross(n, u)

        # plane origin as centroid of all edge pts
        pts3d = np.array([e['start'] for e in plane['edges']] +
                         [e['end'] for e in plane['edges']])
        origin_plane = np.mean(pts3d, axis=0)

        # project edges into 2D
        def to2d(p):
            d = np.array(p) - origin_plane
            return (float(np.dot(d,u)), float(np.dot(d,v)))

        lines2d = [LineString([to2d(e['start']), to2d(e['end'])])
                   for e in plane['edges']]
        merged = unary_union(lines2d)
        polys2d = list(polygonize(merged))
        if not polys2d:
            print(f"[WARN] Plane {idx}: no polygon from edges.")
            continue
        poly2d = max(polys2d, key=lambda P: P.area)

        # raster in 2D
        spacing = VOXEL_DIAMETER * (1-OVERLAP)
        raster2d = generate_raster_lines(poly2d, spacing)

        # lift back to world‐space 3D
        raster3d = [tuple(origin_plane + x*u + y*v) for x,y in raster2d]

        # speed from first edge’s color
        color_val = plane['edges'][0].get('color', 256)
        speed = COLOR_SPEED_MAPPING.get(color_val, 1.0)

        # emit motion block
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
        else:
            motion_blocks.append(f"' [WARN] Plane {idx} has empty raster path")

    # footer
    footer = """
VELOCITY OFF
MSGDISPLAY 0,"Laser process complete."
END
"""
    with open(filename, "w") as f:
        f.write(header)
        f.write("\n".join(motion_blocks))
        f.write(footer)
    print(f"Generated {filename}")

# -----------------------------------------------------------------------------
# 4. Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    planes = parse_planos("planos_procesadosDiagPlane.txt")
    generate_aerobasic_plane_fill_code(planes, filename="DiagPlane_Raster_CAD2AB.txt")
