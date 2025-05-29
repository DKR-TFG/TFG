# Conversor CAD2AeroBasic 

Este repositorio contiene scripts en Python para la conversión de CAD a AeroBasic.

## Requisitos

- Python 3.x

Para instalar las librerías:  
```bash
pip install ezdxf numpy matplotlib shapely
# O con Anaconda
conda install -c conda-forge ezdxf numpy matplotlib shapely
```

## Notas

- Se espera que las unidades en el archivo DXF estén en micrómetros.  
- El origen en el código AeroBasic generado se sitúa respecto al punto con menor X y Y y mayor valor de Z.  
- Se añaden márgenes de 10 µm (XY) y 100 µm (Z) para una planificación de movimiento segura.  
- Para diferenciar automaticamente entre trayectorias y planos, emplea cualquier valor positivo para el grosor de la línea en la entidad (o entidades) cerrada/s para representar un plano.


## Uso de todos los scripts

1. **Configurar el directorio de trabajo** donde se encuentra el archivo de entrada (aquí se guardará el archivo de salida).  
2. **Ejecutar el script:**  
    ```bash
    python nombre_del_archivo.py
    ```  
3. **Salida:** Normalmente un archivo .txt o un print en la consola.


## Script: `dxftotxt.py`

### Descripción general

- **Objetivo:** Extraer datos geométricos de un archivo DXF y escribirlos en un archivo de texto.  
- **Entidades compatibles:** LINE (línea), ARC (arco), SPLINE (splina), HELIX (hélice), CIRCLE (círculo), ELLIPSE (elipse), POLYLINE (polilínea), LWPOLYLINE (polilínea ligera).  
- **Clasificación:** Las entidades se categorizan en `trayectorias` y `planos` según el grosor de línea.

### Principales características

- Utiliza la librería [`ezdxf`](https://github.com/mozman/ezdxf) para el análisis de archivos DXF.  
- Redondea coordenadas para mayor consistencia.  
- Extrae y organiza atributos de las entidades como tipo, color, grosor y datos geométricos específicos.  
- Genera la salida en un formato de texto legible por humanos.

### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)

dxf_file_name = 'RegHelix.dxf'
output_file_name = "RegHelix_Raw_2.txt"

extract_geometry_from_dxf(dxf_file_name, output_file_name)
```
---
# GetTrajectories
Esta carpeta contiene los scripts para procesar y generar trayectorias en AeroBasic a partir de datos CAD.

### Script: `process_trayec.py`

#### Descripción general

- **Objetivo:** Procesa la salida de `dxftotxt.py` (`RegHelix_Raw_2.txt`), limpia y redondea los datos, y los organiza por tipo de entidad en un archivo de texto más estructurado.  
- **Características:**  
  - Limpia y parsea las líneas usando `ast` y expresiones regulares.  
  - Redondea todos los valores numéricos a una precisión configurable.  
  - Agrupa las entidades por tipo y las exporta en un formato legible.

#### Principales características

- Utiliza librerías estándar de Python: `os`, `ast`, `re`, `collections` y `typing`.  
- Calcula parámetros adicionales (por ejemplo, `radio_base` para entidades HELIX).  
- Maneja todos los tipos de entidades compatibles y sus parámetros relevantes.

#### Ejemplo

```python
process_trayectorias(
    input_file="RegHelix_Raw_2.txt",
    output_file="params_RegHelix_2.txt",
    precision=6  # Ajusta la tolerancia del redondeo (0–10)
)
```
---
### Script: `CADTrajectory2AB.py`

#### Descripción general

- **Objetivo:** Lee archivos de parámetros de geometría procesados (por ejemplo, de `process_trayec.py`), genera trayectorias paramétricas (HELIX, LINE), las visualiza en 3D y produce código AeroBasic para el control láser.  
- **Características:**  
  - Parsea archivos de parámetros estructurados.  
  - Genera puntos paramétricos para entidades HELIX y LINE.  
  - Calcula centros de vóxel a lo largo de las trayectorias para la planificación del recorrido láser.  
  - Mapea el color de la entidad a la velocidad del láser.  
  - Visualiza las trayectorias en 3D usando Matplotlib.  
  - Genera código AeroBasic para sistemas Aerotech A3200.

#### Principales características

- Utiliza `numpy`, `matplotlib`, `scipy.interpolate` y librerías estándar de Python.  
- Soporta tanto entidades HELIX como LINE.  
- Configuración flexible de diámetro de vóxel y solapamiento.  
- Genera scripts AeroBasic listos para usar en sistemas láser.

#### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetTrayec\Helix'
os.chdir(directory)
Input_File = "params_helixpore_wg.txt"
VOXEL_DIAMETER = 0.2
OVERLAP = 0.5

# Lee el archivo de parámetros, genera trayectorias, visualiza y produce el código AeroBasic
# (Ver el script para más detalles)
```
---
## GetPlanes

Esta carpeta contiene los scripts para procesar y generar planos en AeroBasic a partir de datos CAD.

---

### Script: `process_planes.py`

#### Descripción general

- **Objetivo:** Procesa archivos de salida sin procesar que contienen entidades de tipo plano (por ejemplo, `PlanoXZ_Raw.txt`), extrae y agrupa bordes de planos, calcula vectores de extrusión (normales) y genera un archivo estructurado para su uso en la generación de código AeroBasic.  
- **Características:**  
  - Lee y separa las secciones `TRAYECTORIAS` y `PLANOS` del archivo de entrada.  
  - Identifica planos directos (CIRCLE, ELLIPSE) y calcula/ajusta sus vectores de extrusión.  
  - Extrae y agrupa bordes conectados (LINE, ARC, LWPOLYLINE) en grupos planares usando recorrido de grafos.  
  - Calcula el vector normal de cada plano agrupado utilizando puntos no colineales.  
  - Genera un resumen detallado y legible de cada plano, incluyendo vectores de extrusión y detalles de sus bordes.

#### Principales características

- Utiliza librerías estándar de Python: `os`, `ast`, `collections` y `numpy` para operaciones vectoriales.  
- Soporta tanto planos directos (CIRCLE/ELLIPSE) como agrupaciones planas de bordes arbitrarios.  
- Robusto frente a puntos colineales y casos degenerados.  
- Produce un archivo de salida con información geométrica y topológica completa de los planos procesados.

#### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
os.chdir(directory)
input_file = 'DiagPlane_Raw.txt'
output_file = 'planos_procesadosDiagPlane.txt'
```
---

### Script: `Planes2AB_Raster.py`

#### Descripción general

- **Objetivo:** Genera código AeroBasic con relleno tipo raster para planos con orientación arbitraria a partir de datos CAD procesados.  
- **Características:**  
  - Lee archivos de planos procesados que contienen bordes y vectores de extrusión.  
  - Construye un sistema de referencia ortonormal para cada plano basado en su vector de extrusión.  
  - Proyecta los bordes 3D del plano a un plano 2D para su poligonización y rasterización.  
  - Genera líneas de relleno tipo raster (ida y vuelta) dentro del área poligonal.  
  - Reconvierte los puntos rasterizados al espacio 3D original.  
  - Asocia el color de los bordes con la velocidad del láser (feedrate).  
  - Produce código AeroBasic para sistemas Aerotech A3200.

#### Principales características

- Utiliza `numpy` para operaciones vectoriales y transformaciones de coordenadas.  
- Usa `shapely` para operaciones geométricas (poligonización, intersecciones).  
- Soporta cualquier orientación de plano y configuraciones complejas de bordes.  
- Diámetro de vóxel y solapamiento configurables para el relleno raster.  
- Calcula automáticamente el origen global y márgenes para movimientos seguros.

#### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\DiagPlane'
os.chdir(directory)
planes = parse_planos("planos_procesadosDiagPlane.txt")
generate_aerobasic_plane_fill_code(planes, filename="DiagPlane_Raster_CAD2AB.txt")
```

---

### Script: `Planes2AB_Spiral.py`

#### Descripción general

- **Objetivo:** Genera código AeroBasic con relleno en espiral para planos con orientación arbitraria, que contengan bordes rectos y curvos (arcos), a partir de datos CAD procesados.  
- **Características:**  
  - Lee archivos de planos procesados con soporte para bordes rectos y en arco.  
  - Reconstruye los contornos del plano en 2D, incluyendo interpolación de arcos.  
  - Genera un patrón de relleno en espiral adaptado a la forma poligonal de cada plano.  
  - Reconvierte los puntos espiralados al espacio 3D usando el vector de extrusión del plano.  
  - Asocia el color del borde a la velocidad del láser (feedrate).  
  - Produce código AeroBasic para sistemas Aerotech A3200 con bloques de movimiento en espiral por plano.

#### Principales características

- Usa `numpy` para operaciones vectoriales y transformaciones de coordenadas.  
- Emplea `shapely` para operaciones geométricas (poligonización, manejo de arcos).  
- Soporta orientaciones arbitrarias de planos y arreglos complejos de bordes (incluyendo arcos).  
- Configurable: diámetro del vóxel, solapamiento y resolución de interpolación de arcos.  
- Calcula automáticamente el origen global y márgenes para movimientos seguros.  
- Robusto frente a polígonos degenerados o inválidos.

#### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\PlanoXZ'
os.chdir(directory)
planes = parse_planos("planos_procesadosXZ.txt")
generate_aerobasic_plane_fill_code(planes, filename="TEST.txt")
```
---
### Script: `Establish_Hierarchy.py`

#### Descripción general

- **Objetivo:** Lee un archivo de planos procesados, detecta relaciones jerárquicas entre planos (padre-hijo), construye polígonos con agujeros, genera una trayectoria basada en líneas de escaneo dentro del área permitida, asigna estados del láser ("shutter") a los segmentos de trayectoria, simplifica la trayectoria, la guarda en un archivo de texto y visualiza el resultado.  
- **Características:**  
  - Parsea bloques de planos y extrae contornos, color y vectores de extrusión.  
  - Usa `shapely` para detectar jerarquías poligonales (inclusión) y realizar operaciones geométricas.  
  - Genera trayectorias tipo raster que respetan los vacíos interiores (planos hijo).  
  - Asigna estados "shutter" (abierto/cerrado) a cada segmento de trayectoria según su ubicación.  
  - Simplifica la trayectoria uniendo segmentos colineales con el mismo estado.  
  - Genera un archivo de texto con los datos de trayectoria y una gráfica con contornos y estados del láser.

#### Principales características

- Utiliza `shapely` para operaciones poligonales y detección de jerarquías.  
- Soporta bordes rectos y curvos (con resolución configurable para interpolación).  
- Configurable: diámetro del vóxel y solapamiento para espaciamiento de líneas.  
- La trayectoria resultante incluye color del plano padre y un valor Z constante.  
- Visualiza trayectoria y contornos de planos con anotaciones del estado del "shutter".

#### Ejemplo

```python
base_directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
os.chdir(base_directory)
input_filename = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\testhiercode.txt'
trajectory_output = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA\trajectorytesting.txt'
resolution = 30           # Resolución para interpolación de arcos
VOXEL_DIAMETER = 0.2      # Diámetro del vóxel (para espaciamiento)
OVERLAP = 0.5
# Ejecutar main() para procesar y visualizar
```
---
### Script: `Planes2AB_ShutterTrajec.py`

#### Descripción general

- **Objetivo:** Convierte un archivo de trayectoria (con estados de shutter abierto/cerrado) en código AeroBasic para Aerotech A3200, permitiendo el control del láser con modulación de shutter a lo largo del recorrido.  
- **Características:**  
  - Parsea segmentos de trayectoria con estados de shutter explícitos.  
  - Extrae el color y el valor de Z del encabezado del archivo de trayectoria.  
  - Mapea el índice de color a la velocidad del láser.  
  - Genera código AeroBasic con los comandos correctos de apertura/cierre de shutter.  
  - Calcula el origen global y aplica márgenes de seguridad.  
  - Produce un script AeroBasic listo para usar.

#### Principales características

- Utiliza `numpy` para cálculos de coordenadas.  
- Maneja archivos de trayectoria con líneas como:  
  `De (x1, y1) a (x2, y2): shutter open/closed`  
- Configura automáticamente la posición inicial y los desplazamientos de coordenadas.  
- Soporta Z y velocidad configurables vía encabezado o valores por defecto.

#### Ejemplo

```python
directory = r'C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\RdA'
os.chdir(directory)
# Asegúrate de que 'trajectory.txt' exista con encabezado:
# Color extraído del Plano 1: 6
# Constante Z: 0.0
# De (x1, y1) a (x2, y2): shutter open/closed
# ...
# Luego ejecuta:
python Planes2AB_ShutterTrajec.py
```
---
## Script: `time_estimate.py`

### Descripción general

- **Objetivo:** Estima el tiempo total de ejecución de un archivo de código AeroBasic al parsear comandos de movimiento y de espera (dwell).  
- **Características:**  
  - Lee archivos AeroBasic y extrae todos los comandos de movimiento `LINEAR` con sus velocidades asociadas.  
  - Detecta y suma todos los comandos de espera (`dwell`).  
  - Calcula la distancia total recorrida y la divide por la velocidad correspondiente de cada segmento.  
  - Devuelve el tiempo total estimado en segundos y minutos.

### Principales características

- Utiliza librerías estándar de Python: `re`, `math`, `os` y `sys`.  
- Gestiona cambios de velocidad (`$SPEED`) asegurando que cada segmento use la velocidad correcta.  
- Informa si faltan datos suficientes para la estimación.

### Ejemplo

```python
directory = r"C:\Users\Daniel\Desktop\Uni\Python\TFG\GetPlanes\PlanoXZ"
os.chdir(directory)
filename = "PlanoXZ_Spiralv2_CAD2AB (3).txt"
estimate_time(filename)
```

