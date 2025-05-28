#!/usr/bin/env python3
# estimate_time.py
# Estima el tiempo de trayectoria de un script AEROTECH A3200

import re
import math
import sys
import os

def estimate_time(file_path):
    coords = []         # lista de tuplas (x, y, z, speed)
    dwell_times = []    # lista de tiempos de dwell (s)
    current_speed = None

    # Expresiones regulares
    re_speed  = re.compile(r'^\s*\$SPEED\s*=\s*([\d\.]+)')
    re_linear = re.compile(
        r'^\s*LINEAR\s+X([-\d\.]+)\s+Y([-\d\.]+)\s+Z([-\d\.]+)\s+F\s+\$SPEED'
    )
    re_dwell  = re.compile(r'^\s*dwell\s+([\d\.]+)', re.IGNORECASE)

# … (imports y expresiones regulares iguales)

    with open(file_path, 'r') as f:
        for line in f:
            # 1) Detecto un cambio de velocidad
            m_speed = re_speed.match(line)
            if m_speed:
                current_speed = float(m_speed.group(1))
                # sigo al siguiente
                continue

            # 2) Detecto un tramo LINEAR
            m_lin = re_linear.match(line)
            if m_lin:
                if current_speed is None:
                    raise RuntimeError("Se usa F $SPEED antes de definir $SPEED")
                x, y, z = map(float, m_lin.groups())
                # añado el tramo con la velocidad actual
                coords.append((x, y, z, current_speed))
                continue

            # 3) Detecto dwell (pausa)
            m_dwell = re_dwell.match(line)
            if m_dwell:
                dwell_times.append(float(m_dwell.group(1)))


    if len(coords) < 2:
        print("No se encontraron suficientes puntos LINEAR para calcular recorrido.")
        return

    # Calcular tiempo total
    total_time = 0            # tiempo de arranque (10s por defecto)
    for (x0, y0, z0, s0), (x1, y1, z1, s1) in zip(coords, coords[1:]):
        dist = math.sqrt((x1-x0)**2 + (y1-y0)**2 + (z1-z0)**2)
        total_time += dist / s0

    # Añadir pausas dwell
    total_time += sum(dwell_times)

    # Mostrar resultado
    mins, secs = divmod(total_time, 60)
    print(f"Distancia total de {len(coords)-1} tramos.")
    print(f"Tiempo total estimado: {total_time:.2f} s  ({int(mins)} min {secs:.2f} s)")

if __name__ == "__main__":
    directory = r"C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\PlanoXZ"
    os.chdir(directory)
    filename= "PlanoXZ_Spiralv2_CAD2AB (3).txt"
    estimate_time(filename)