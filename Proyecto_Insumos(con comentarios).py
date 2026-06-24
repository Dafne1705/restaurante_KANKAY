# ======================================================================
# IMPORTACIÓN DE BIBLIOTECAS
# ======================================================================
# sqlite3: Viene incluido con Python y nos permite trabajar con bases de datos SQLite
# os: Nos permite ejecutar comandos del sistema operativo (como limpiar la pantalla)
# datetime: Nos permite trabajar con fechas y horas
# ======================================================================
import sqlite3
import os
from datetime import datetime

# ======================================================================
# CONFIGURACIÓN INICIAL
# ======================================================================
# ANCHO: Define el ancho de los recuadros que se muestran en pantalla (90 caracteres)
# DB_NAME: Nombre del archivo de la base de datos SQLite
# ======================================================================
ANCHO = 90
DB_NAME = "registros_carnicos.db"

# ======================================================================
# FUNCIONES DE LA BASE DE DATOS
# ======================================================================

def crear_tablas():
    """
    Crea las tablas necesarias en la base de datos si no existen.
    - Tabla 'sesiones': Guarda información de cada sesión de registro (fecha, responsable, área, hora)
    - Tabla 'registros': Guarda los productos registrados en cada sesión
    """
    # Conectamos a la base de datos (si no existe, se crea automáticamente)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()  # El cursor nos permite ejecutar comandos SQL
    
    # Creamos la tabla de sesiones
    # Cada sesión tiene: ID único, fecha, responsable, área de cocina, hora y fecha de creación automática
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,      -- ID único auto-incrementable
            fecha TEXT NOT NULL,                       -- Fecha de la sesión (DD-MM-YYYY)
            responsable TEXT NOT NULL,                 -- Nombre del responsable/encargado
            area TEXT NOT NULL,                        -- Área de cocina (Ej: Salteados, Fritura)
            hora TEXT NOT NULL,                        -- Hora de creación de la sesión
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Fecha y hora automática
        )
    ''')
    
    # Creamos la tabla de registros (productos)
    # Cada registro pertenece a una sesión (relacionado por sesion_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER NOT NULL,                -- ID de la sesión a la que pertenece
            producto TEXT NOT NULL,                    -- Nombre del producto
            inicio INTEGER NOT NULL,                   -- Cantidad inicial
            adicion INTEGER NOT NULL,                  -- Cantidad agregada (reposición)
            evento INTEGER NOT NULL,                   -- Productos separados para evento
            salida INTEGER NOT NULL,                   -- Productos vendidos/salidos
            final INTEGER NOT NULL,                    -- Cantidad final (calculada automáticamente)
            observacion TEXT,                          -- Observaciones adicionales
            FOREIGN KEY (sesion_id) REFERENCES sesiones (id) ON DELETE CASCADE  -- Si se elimina la sesión, se eliminan sus registros
        )
    ''')
    
    # Guardamos los cambios y cerramos la conexión
    conn.commit()
    conn.close()

def guardar_sesion(fecha, responsable, area, hora, registros):
    """
    Guarda una sesión completa en la base de datos.
    Recibe: fecha, responsable, área, hora y una lista de registros (productos)
    Retorna: El ID de la sesión creada
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Insertamos la sesión en la tabla 'sesiones'
    cursor.execute('''
        INSERT INTO sesiones (fecha, responsable, area, hora)
        VALUES (?, ?, ?, ?)
    ''', (fecha, responsable, area, hora))
    
    # Obtenemos el ID de la sesión que acabamos de insertar
    sesion_id = cursor.lastrowid
    
    # Insertamos cada registro (producto) en la tabla 'registros'
    for reg in registros:
        cursor.execute('''
            INSERT INTO registros 
            (sesion_id, producto, inicio, adicion, evento, salida, final, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sesion_id,
            reg["producto"],
            reg["inicio"],
            reg["adicion"],
            reg["evento"],
            reg["salida"],
            reg["final"],
            reg["observacion"]
        ))
    
    # Guardamos y cerramos
    conn.commit()
    conn.close()
    return sesion_id  # Devolvemos el ID por si se necesita después

def cargar_sesiones():
    """
    Carga todas las sesiones guardadas en la base de datos.
    Retorna: Una lista con todas las sesiones y sus registros
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Esto permite acceder a los datos por nombre de columna
    cursor = conn.cursor()
    
    # Obtenemos todas las sesiones ordenadas de la más reciente a la más antigua
    cursor.execute('''
        SELECT id, fecha, responsable, area, hora 
        FROM sesiones 
        ORDER BY fecha_creacion DESC
    ''')
    sesiones = cursor.fetchall()  # Obtenemos todas las filas
    
    resultado = []  # Aquí guardaremos el resultado final
    for sesion in sesiones:
        # Para cada sesión, obtenemos sus registros (productos)
        cursor.execute('''
            SELECT id, producto, inicio, adicion, evento, salida, final, observacion
            FROM registros
            WHERE sesion_id = ?
        ''', (sesion["id"],))
        
        registros = [dict(row) for row in cursor.fetchall()]  # Convertimos a diccionarios
        
        # Agregamos la sesión con sus registros al resultado
        resultado.append({
            "id": sesion["id"],
            "fecha": sesion["fecha"],
            "responsable": sesion["responsable"],
            "area": sesion["area"],
            "hora": sesion["hora"],
            "registros": registros
        })
    
    conn.close()
    return resultado

def obtener_sesion_por_id(sesion_id):
    """
    Obtiene una sesión específica por su ID.
    Útil para la función de edición.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscamos la sesión por su ID
    cursor.execute('''
        SELECT id, fecha, responsable, area, hora
        FROM sesiones
        WHERE id = ?
    ''', (sesion_id,))
    
    sesion = cursor.fetchone()  # Obtenemos una sola fila
    if not sesion:
        conn.close()
        return None  # Si no existe, devolvemos None
    
    # Obtenemos sus registros
    cursor.execute('''
        SELECT id, producto, inicio, adicion, evento, salida, final, observacion
        FROM registros
        WHERE sesion_id = ?
    ''', (sesion_id,))
    
    registros = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {
        "id": sesion["id"],
        "fecha": sesion["fecha"],
        "responsable": sesion["responsable"],
        "area": sesion["area"],
        "hora": sesion["hora"],
        "registros": registros
    }

def actualizar_sesion(sesion_id, fecha, responsable, area, registros):
    """
    Actualiza una sesión existente.
    Primero actualiza los datos de la sesión, luego elimina los registros antiguos y los reemplaza con los nuevos.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Actualizamos los datos de la sesión
    cursor.execute('''
        UPDATE sesiones 
        SET fecha = ?, responsable = ?, area = ?
        WHERE id = ?
    ''', (fecha, responsable, area, sesion_id))
    
    # Eliminamos los registros antiguos de esta sesión
    cursor.execute('DELETE FROM registros WHERE sesion_id = ?', (sesion_id,))
    
    # Insertamos los nuevos registros
    for reg in registros:
        cursor.execute('''
            INSERT INTO registros 
            (sesion_id, producto, inicio, adicion, evento, salida, final, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sesion_id,
            reg["producto"],
            reg["inicio"],
            reg["adicion"],
            reg["evento"],
            reg["salida"],
            reg["final"],
            reg["observacion"]
        ))
    
    conn.commit()
    conn.close()

def obtener_todos_los_registros():
    """
    Obtiene todos los registros de todas las sesiones, agrupados por responsable.
    Útil para la función "Ver total de productos".
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Hacemos una consulta que une las tablas 'registros' y 'sesiones'
    cursor.execute('''
        SELECT 
            s.fecha,
            s.responsable,
            s.area,
            r.producto,
            r.inicio,
            r.adicion,
            r.evento,
            r.salida,
            r.final,
            r.observacion
        FROM registros r
        JOIN sesiones s ON r.sesion_id = s.id
        ORDER BY s.responsable, r.producto
    ''')
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Agrupamos los resultados por responsable
    if resultados:
        grupos = {}
        for row in resultados:
            responsable = row["responsable"]
            if responsable not in grupos:
                grupos[responsable] = []  # Si es un nuevo responsable, creamos una lista vacía
            grupos[responsable].append(row)  # Agregamos el registro a su grupo
        return grupos
    return {}

def buscar_registros_por_fecha(fecha_buscar):
    """
    Busca todos los registros de una fecha específica, agrupados por responsable.
    Útil para la función "Buscar por fecha".
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscamos solo los registros que coinciden con la fecha proporcionada
    cursor.execute('''
        SELECT 
            s.id as sesion_id,
            s.fecha,
            s.responsable,
            s.area,
            s.hora,
            r.id as registro_id,
            r.producto,
            r.inicio,
            r.adicion,
            r.evento,
            r.salida,
            r.final,
            r.observacion
        FROM registros r
        JOIN sesiones s ON r.sesion_id = s.id
        WHERE s.fecha = ?  -- Filtramos por la fecha que el usuario ingresó
        ORDER BY s.responsable, r.producto
    ''', (fecha_buscar,))
    
    resultados = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Agrupamos por responsable (igual que en la función anterior)
    if resultados:
        grupos = {}
        for row in resultados:
            responsable = row["responsable"]
            if responsable not in grupos:
                grupos[responsable] = []
            grupos[responsable].append(row)
        return grupos
    return {}

# ======================================================================
# FUNCIONES DE INTERFAZ Y DISEÑO DE RECUADROS
# ======================================================================
# Estas funciones crean los recuadros y líneas que se ven en la pantalla
# Usan caracteres especiales para dibujar bordes (╔ ═ ╗ ║ ╠ ╣ ╚ ╝)

def linea_top():
    """Dibuja la línea superior de un recuadro"""
    print("╔" + "═" * ANCHO + "╗")

def linea_mid():
    """Dibuja una línea media de separación dentro del recuadro"""
    print("╠" + "═" * ANCHO + "╣")

def linea_bot():
    """Dibuja la línea inferior de un recuadro"""
    print("╚" + "═" * ANCHO + "╝")

def linea_doble():
    """Dibuja una línea doble para separar secciones importantes"""
    print("╠" + "═" * ANCHO + "╣")

def fila(texto="", alinear="left"):
    """
    Dibuja una fila de texto dentro del recuadro.
    Puede alinear el texto a la izquierda (por defecto) o al centro.
    """
    if alinear == "center":
        contenido = texto.center(ANCHO)  # Centramos el texto
    else:
        contenido = " " + texto.ljust(ANCHO - 1)  # Alineamos a la izquierda con un espacio
    print("║" + contenido + "║")

def limpiar():
    """
    Limpia la pantalla de la consola.
    Usa 'cls' en Windows o 'clear' en Linux/Mac.
    """
    os.system("cls" if os.name == "nt" else "clear")

# ======================================================================
# ENCABEZADO PRINCIPAL
# ======================================================================
def encabezado(subtitulo=""):
    """
    Muestra el encabezado principal del programa.
    Siempre muestra "CONTROL INTERNO" y opcionalmente un subtítulo.
    """
    limpiar()  # Limpiamos la pantalla antes de mostrar el encabezado
    linea_top()
    fila("CONTROL INTERNO", "center")  # Título principal centrado
    linea_mid()
    if subtitulo:  # Si hay subtítulo, lo mostramos
        fila(subtitulo, "center")
        linea_mid()

# ======================================================================
# VALIDACIÓN DE NÚMEROS
# ======================================================================
def pedir_numero(etiqueta, descripcion, obligatorio=True):
    """
    Pide al usuario que ingrese un número y valida que sea correcto.
    - etiqueta: El nombre del campo (Ej: "INICIO")
    - descripcion: Una breve descripción del campo
    - obligatorio: Si es True, el usuario debe ingresar un valor
    Retorna: El número ingresado (entero)
    """
    while True:  # Bucle infinito hasta que el usuario ingrese un número válido
        fila(etiqueta + " :")
        fila("  (" + descripcion + ")")
        linea_bot()
        raw = input("   >> ").strip()  # Obtenemos la entrada del usuario
        encabezado()  # Volvemos a mostrar el encabezado después del input
        
        if raw == "" and not obligatorio:
            return 0  # Si el campo es opcional y el usuario presiona Enter, devolvemos 0
        if raw == "" and obligatorio:
            fila("  ! Campo obligatorio. Ingresa un numero.")
            linea_mid()
            continue  # Volvemos a pedir el número
        
        try:
            v = int(raw)  # Intentamos convertir a entero
            if v < 0:
                fila("  ! El numero no puede ser negativo.")
                linea_mid()
                continue
            return v  # Si es válido, devolvemos el número
        except ValueError:
            fila("  ! Solo se permiten numeros enteros.")
            linea_mid()

# ======================================================================
# REGISTRO DE PRODUCTOS
# ======================================================================
def registrar_producto(nombre):
    """
    Registra un nuevo producto pidiendo al usuario todos sus datos.
    Recibe: El nombre del producto
    Retorna: Un diccionario con todos los datos del producto
    """
    # Definimos los campos que se le pedirán al usuario
    # Cada campo tiene: etiqueta, descripción, obligatorio
    campos = [
        ("INICIO",  "Cantidad inicial", True),
        ("ADICION", "Reposicion", False),
        ("EVENTO",  "Productos separados", False),
        ("SALIDA",  "Productos vendidos", False),
    ]
    valores = []  # Aquí guardaremos los valores que ingrese el usuario

    # Recorremos cada campo y pedimos el número
    for etiqueta, descripcion, oblig in campos:
        encabezado("INGRESO DE DATOS")
        fila("Producto : " + nombre)
        linea_mid()
        # Mostramos los valores ya ingresados
        for i, v in enumerate(valores):
            fila("  " + campos[i][0] + " : " + str(v))
        linea_mid()
        v = pedir_numero(etiqueta, descripcion, oblig)
        valores.append(v)  # Agregamos el valor a la lista

    # Calculamos el final automáticamente: (inicio + adicion + evento) - salida
    inicio, adicion, evento, salida = valores
    final = (inicio + adicion + evento) - salida

    # Mostramos un resumen de los datos ingresados
    encabezado("INGRESO DE DATOS")
    fila("Producto : " + nombre)
    linea_mid()
    fila("  INICIO  : " + str(inicio))
    fila("  ADICION : " + str(adicion))
    fila("  EVENTO  : " + str(evento))
    fila("  SALIDA  : " + str(salida))
    linea_mid()
    fila("  FINAL (calculado) : " + str(final))
    if final < 0:
        fila("  ADVERTENCIA: el FINAL es negativo!")  # Advertencia si el final es negativo
    linea_mid()
    fila("  OBSERVACION (Enter para omitir) :")
    linea_bot()
    obs = input("   >> ").strip()  # Observación opcional

    # Devolvemos todos los datos como un diccionario
    return {
        "producto":    nombre,
        "inicio":      inicio,
        "adicion":     adicion,
        "evento":      evento,
        "salida":      salida,
        "final":       final,
        "observacion": obs,
    }

def registrar_producto_edicion(nombre, valores_actuales=None):
    """
    Similar a registrar_producto, pero para edición.
    Muestra los valores actuales y permite modificarlos.
    """
    campos = [
        ("INICIO",  "Cantidad inicial", True),
        ("ADICION", "Reposicion", False),
        ("EVENTO",  "Productos separados", False),
        ("SALIDA",  "Productos vendidos", False),
    ]
    valores = []

    for i, (etiqueta, descripcion, oblig) in enumerate(campos):
        encabezado("EDITAR DATOS")
        fila("Producto : " + nombre)
        linea_mid()
        for j, v in enumerate(valores):
            fila("  " + campos[j][0] + " : " + str(v))
        linea_mid()
        
        # Mostramos el valor actual para que el usuario lo vea
        if valores_actuales and i < len(valores_actuales):
            fila("  Valor actual: " + str(valores_actuales[i]))
            fila("  (Enter para mantener el valor actual)")
        linea_mid()
        
        v = pedir_numero(etiqueta, descripcion, oblig)
        # Si el usuario ingresó 0 y hay un valor actual, mantenemos el actual
        if v == 0 and valores_actuales and i < len(valores_actuales):
            v = valores_actuales[i]
        valores.append(v)

    inicio, adicion, evento, salida = valores
    final = (inicio + adicion + evento) - salida

    encabezado("EDITAR DATOS")
    fila("Producto : " + nombre)
    linea_mid()
    fila("  INICIO  : " + str(inicio))
    fila("  ADICION : " + str(adicion))
    fila("  EVENTO  : " + str(evento))
    fila("  SALIDA  : " + str(salida))
    linea_mid()
    fila("  FINAL (calculado) : " + str(final))
    if final < 0:
        fila("  ADVERTENCIA: el FINAL es negativo!")
    linea_mid()
    fila("  OBSERVACION (Enter para omitir) :")
    linea_bot()
    obs = input("   >> ").strip()

    return {
        "producto":    nombre,
        "inicio":      inicio,
        "adicion":     adicion,
        "evento":      evento,
        "salida":      salida,
        "final":       final,
        "observacion": obs,
    }

# ======================================================================
# MOSTRAR RESUMEN EN TABLA
# ======================================================================
def mostrar_resumen(registros, fecha, responsable, area):
    """
    Muestra un resumen de una sesión en formato de tabla.
    Útil después de guardar una sesión o para ver el historial.
    """
    limpiar()
    linea_top()
    fila("RESUMEN DE SESION", "center")
    linea_mid()
    fila("Responsable : " + responsable)
    fila("Area        : " + area)
    fila("Fecha       : " + fecha)
    linea_mid()

    # Encabezados de la tabla
    cab = " {:<16} {:>6} {:>7} {:>7} {:>7} {:>6}".format(
        "PRODUCTO", "INICIO", "ADIC.", "EVENTO", "SALIDA", "FINAL"
    )
    fila(cab)
    linea_mid()

    # Mostramos cada registro
    for r in registros:
        linea = " {:<16} {:>6} {:>7} {:>7} {:>7} {:>6}".format(
            r["producto"][:16],  # Truncamos a 16 caracteres si es muy largo
            r["inicio"],
            r["adicion"],
            r["evento"],
            r["salida"],
            r["final"],
        )
        fila(linea)
        if r["observacion"]:
            fila("  Obs: " + r["observacion"][:46])  # Mostramos observación si existe

    # Calculamos y mostramos los totales
    linea_mid()
    ti = sum(r["inicio"]  for r in registros)
    ta = sum(r["adicion"] for r in registros)
    te = sum(r["evento"]  for r in registros)
    ts = sum(r["salida"]  for r in registros)
    tf = sum(r["final"]   for r in registros)
    tot = " {:<16} {:>6} {:>7} {:>7} {:>7} {:>6}".format(
        "TOTALES", ti, ta, te, ts, tf
    )
    fila(tot)
    linea_bot()

# ======================================================================
# VER TODOS LOS PRODUCTOS (TODAS LAS SESIONES)
# ======================================================================
def ver_todos_los_productos():
    """
    Muestra todos los productos registrados en todas las sesiones.
    Agrupa los productos por responsable y muestra totales.
    """
    grupos = obtener_todos_los_registros()  # Obtenemos todos los registros agrupados
    
    encabezado("TODOS LOS PRODUCTOS REGISTRADOS")
    
    if not grupos:
        fila("No hay productos registrados en ninguna sesion.")
        linea_bot()
        input("   >> ")
        return
    
    fila("DATOS ENCONTRADOS")
    linea_mid()
    fila("")
    
    primer_grupo = True  # Variable para controlar el primer grupo (no mostrar separador antes)
    for responsable, registros in grupos.items():
        # Si no es el primer grupo, mostramos una línea separadora
        if not primer_grupo:
            linea_doble()
            fila("═" * ANCHO, "center")
            linea_doble()
        
        area = registros[0]["area"] if registros else "Sin área"  # Obtenemos el área del primer registro
        
        fila(f"ENCARGADO: {responsable}")
        fila(f"AREA: {area}")
        fila("")
        
        # Encabezados de la tabla
        fila("FRUTIRA    PRODUCTO       INICIO   ADICION   EVENTO   SALIDA   FINAL   OBSERVACIÓN")
        linea_mid()
        
        # Mostramos cada registro
        for r in registros:
            producto = r["producto"][:14] if len(r["producto"]) > 14 else r["producto"].ljust(14)
            observacion = r["observacion"][:10] if r["observacion"] and len(r["observacion"]) > 10 else (r["observacion"] or "").ljust(10)
            fila(f"           {producto}    {r['inicio']:>5}     {r['adicion']:>5}     {r['evento']:>5}     {r['salida']:>5}     {r['final']:>5}   {observacion}")
        
        # Totales por responsable
        total_inicio = sum(r["inicio"] for r in registros)
        total_adicion = sum(r["adicion"] for r in registros)
        total_evento = sum(r["evento"] for r in registros)
        total_salida = sum(r["salida"] for r in registros)
        total_final = sum(r["final"] for r in registros)
        
        linea_mid()
        fila(f"TOTAL {responsable[:12]}: {total_inicio:>5}     {total_adicion:>5}     {total_evento:>5}     {total_salida:>5}     {total_final:>5}")
        
        primer_grupo = False  # Ya no es el primer grupo
    
    # Totales generales de todos los productos
    todos_los_registros = []
    for responsable, registros in grupos.items():
        todos_los_registros.extend(registros)
    
    if len(grupos) > 1:  # Si hay más de un responsable, mostramos totales generales
        linea_doble()
        fila("═" * ANCHO, "center")
        linea_doble()
        fila("TOTALES GENERALES DE TODOS LOS PRODUCTOS:")
        total_inicio = sum(r["inicio"] for r in todos_los_registros)
        total_adicion = sum(r["adicion"] for r in todos_los_registros)
        total_evento = sum(r["evento"] for r in todos_los_registros)
        total_salida = sum(r["salida"] for r in todos_los_registros)
        total_final = sum(r["final"] for r in todos_los_registros)
        fila(f"TOTAL GENERAL:        {total_inicio:>5}     {total_adicion:>5}     {total_evento:>5}     {total_salida:>5}     {total_final:>5}")
    
    linea_bot()
    fila("Presiona Enter para volver al menu...")
    linea_bot()
    input("   >> ")

# ======================================================================
# BUSCAR POR FECHA
# ======================================================================
def buscar_por_fecha():
    """
    Busca y muestra todos los registros de una fecha específica.
    El usuario ingresa una fecha y el programa muestra todos los registros de ese día.
    """
    encabezado("BUSCAR POR FECHA")
    fila("Ingresa la fecha a buscar (formato DD-MM-YYYY)")
    fila("Ejemplo: 23-06-2026")
    linea_bot()
    fecha_buscar = input("   >> ").strip()
    
    if not fecha_buscar:
        encabezado("AVISO")
        fila("No ingresaste ninguna fecha.")
        linea_bot()
        input("   >> ")
        return
    
    # Validamos que la fecha tenga el formato correcto
    try:
        datetime.strptime(fecha_buscar, "%d-%m-%Y")
    except ValueError:
        encabezado("ERROR")
        fila("Formato de fecha invalido.")
        fila("Usa el formato DD-MM-YYYY")
        linea_bot()
        input("   >> ")
        return
    
    grupos = buscar_registros_por_fecha(fecha_buscar)  # Buscamos los registros
    
    encabezado(f"REGISTROS DEL {fecha_buscar}")
    
    if not grupos:
        fila("NO SE ENCONTRARON REGISTROS")
        fila(f"Para la fecha: {fecha_buscar}")
        linea_bot()
        input("   >> ")
        return
    
    fila("DATOS ENCONTRADOS")
    linea_mid()
    fila("")
    
    primer_grupo = True
    for responsable, registros in grupos.items():
        if not primer_grupo:
            linea_doble()
            fila("═" * ANCHO, "center")
            linea_doble()
        
        area = registros[0]["area"] if registros else "Sin área"
        
        fila(f"FECHA: {fecha_buscar}")
        fila("")
        fila(f"ENCARGADO: {responsable}")
        fila(f"AREA: {area}")
        fila("")
        
        # Mostramos los registros en formato tabla
        fila("FRUTIRA    PRODUCTO       INICIO   ADICION   EVENTO   SALIDA   FINAL   OBSERVACIÓN")
        linea_mid()
        
        for r in registros:
            producto = r["producto"][:14] if len(r["producto"]) > 14 else r["producto"].ljust(14)
            observacion = r["observacion"][:10] if r["observacion"] and len(r["observacion"]) > 10 else (r["observacion"] or "").ljust(10)
            fila(f"           {producto}    {r['inicio']:>5}     {r['adicion']:>5}     {r['evento']:>5}     {r['salida']:>5}     {r['final']:>5}   {observacion}")
        
        total_inicio = sum(r["inicio"] for r in registros)
        total_adicion = sum(r["adicion"] for r in registros)
        total_evento = sum(r["evento"] for r in registros)
        total_salida = sum(r["salida"] for r in registros)
        total_final = sum(r["final"] for r in registros)
        
        linea_mid()
        fila(f"TOTAL {responsable[:12]}: {total_inicio:>5}     {total_adicion:>5}     {total_evento:>5}     {total_salida:>5}     {total_final:>5}")
        
        primer_grupo = False
    
    # Totales generales de la fecha
    todos_los_registros = []
    for responsable, registros in grupos.items():
        todos_los_registros.extend(registros)
    
    if len(grupos) > 1:
        linea_doble()
        fila("═" * ANCHO, "center")
        linea_doble()
        fila("TOTALES GENERALES DE LA FECHA:")
        total_inicio = sum(r["inicio"] for r in todos_los_registros)
        total_adicion = sum(r["adicion"] for r in todos_los_registros)
        total_evento = sum(r["evento"] for r in todos_los_registros)
        total_salida = sum(r["salida"] for r in todos_los_registros)
        total_final = sum(r["final"] for r in todos_los_registros)
        fila(f"TOTAL:                 {total_inicio:>5}     {total_adicion:>5}     {total_evento:>5}     {total_salida:>5}     {total_final:>5}")
    
    linea_bot()
    fila("Presiona Enter para volver al menu...")
    linea_bot()
    input("   >> ")

# ======================================================================
# EDITAR SESIÓN (NUEVA FUNCIONALIDAD)
# ======================================================================
def editar_sesion():
    """
    Permite al usuario editar una sesión existente.
    Puede modificar: responsable, área, fecha y los productos de la sesión.
    """
    sesiones = cargar_sesiones()  # Cargamos todas las sesiones
    
    encabezado("EDITAR SESION")
    
    if not sesiones:
        fila("No hay sesiones guardadas para editar.")
        linea_bot()
        input("   >> ")
        return
    
    # Mostramos la lista de sesiones para que el usuario elija
    fila("SELECCIONA LA SESION A EDITAR:")
    linea_mid()
    for i, s in enumerate(sesiones, 1):
        fila(f"  {i}. {s['fecha']} - {s['responsable']}  ({s['area']})  ({len(s['registros'])} productos)")
    
    linea_mid()
    fila("  (Ingresa el numero de la sesion)")
    fila("  (Enter para cancelar)")
    linea_bot()
    op = input("   >> ").strip()
    
    if not op:
        return  # Si presiona Enter, cancelamos
    
    if not op.isdigit():
        encabezado("ERROR")
        fila("Debes ingresar un numero valido.")
        linea_bot()
        input("   >> ")
        return
    
    idx = int(op) - 1  # Convertimos a índice (0-based)
    if idx < 0 or idx >= len(sesiones):
        encabezado("ERROR")
        fila("Numero de sesion invalido.")
        linea_bot()
        input("   >> ")
        return
    
    sesion_original = sesiones[idx]  # Obtenemos la sesión seleccionada
    sesion_id = sesion_original["id"]
    
    # Mostramos los datos actuales
    encabezado("EDITAR SESION - DATOS ACTUALES")
    fila(f"Responsable: {sesion_original['responsable']}")
    fila(f"Area: {sesion_original['area']}")
    fila(f"Fecha: {sesion_original['fecha']}")
    fila(f"Productos: {len(sesion_original['registros'])}")
    linea_mid()
    
    # Editamos los datos de la sesión
    fila("NUEVOS DATOS (Enter para mantener el valor actual):")
    linea_mid()
    
    fila(f"Responsable ({sesion_original['responsable']}):")
    linea_bot()
    nuevo_responsable = input("   >> ").strip()
    if not nuevo_responsable:
        nuevo_responsable = sesion_original["responsable"]  # Mantenemos el valor actual
    
    encabezado("EDITAR SESION")
    fila(f"Area ({sesion_original['area']}):")
    fila("  Ejemplos: Salteados, Fritura, Parrilla, Cocidos")
    fila("")
    fila("  - Salteados")
    fila("  - Fritura")
    fila("  - Parrilla")
    fila("  - Cocidos")
    fila("")
    linea_bot()
    nueva_area = input("   >> ").strip()
    if not nueva_area:
        nueva_area = sesion_original["area"]
    
    encabezado("EDITAR SESION")
    fila(f"Fecha ({sesion_original['fecha']}):")
    fila("  (Formato DD-MM-YYYY)")
    linea_bot()
    nueva_fecha = input("   >> ").strip()
    if not nueva_fecha:
        nueva_fecha = sesion_original["fecha"]
    
    # Preguntamos si quiere editar los productos
    encabezado("EDITAR PRODUCTOS")
    fila("¿Quieres editar los productos de esta sesion?")
    fila("  S. Si, editar productos")
    fila("  N. No, mantener los productos actuales")
    linea_bot()
    editar_productos = input("   >> ").strip().upper()
    
    nuevos_registros = []
    if editar_productos == "S":
        productos_actuales = sesion_original["registros"]
        
        # Mostramos los productos actuales
        encabezado("PRODUCTOS ACTUALES")
        for i, reg in enumerate(productos_actuales, 1):
            fila(f"  {i}. {reg['producto']} - INICIO:{reg['inicio']} ADICION:{reg['adicion']} EVENTO:{reg['evento']} SALIDA:{reg['salida']} FINAL:{reg['final']}")
            if reg["observacion"]:
                fila(f"     Obs: {reg['observacion']}")
        linea_mid()
        
        # Editamos cada producto
        productos_editados = []
        for reg in productos_actuales:
            encabezado(f"EDITAR PRODUCTO: {reg['producto']}")
            fila(f"Producto: {reg['producto']}")
            fila(f"  INICIO actual: {reg['inicio']}")
            fila(f"  ADICION actual: {reg['adicion']}")
            fila(f"  EVENTO actual: {reg['evento']}")
            fila(f"  SALIDA actual: {reg['salida']}")
            fila(f"  FINAL actual: {reg['final']}")
            if reg["observacion"]:
                fila(f"  OBSERVACION actual: {reg['observacion']}")
            linea_mid()
            fila("¿Deseas editar este producto? (S/N)")
            linea_bot()
            editar = input("   >> ").strip().upper()
            
            if editar == "S":
                valores_actuales = [reg["inicio"], reg["adicion"], reg["evento"], reg["salida"]]
                nuevo_reg = registrar_producto_edicion(reg["producto"], valores_actuales)
                productos_editados.append(nuevo_reg)
            else:
                productos_editados.append(reg)  # Mantenemos el producto sin cambios
        
        # Preguntamos si quiere agregar nuevos productos
        while True:
            encabezado("AGREGAR PRODUCTO ADICIONAL")
            fila("¿Quieres agregar un nuevo producto? (S/N)")
            linea_bot()
            agregar = input("   >> ").strip().upper()
            if agregar != "S":
                break
            
            fila("Nombre del nuevo producto:")
            linea_bot()
            nuevo_producto = input("   >> ").strip().upper()
            if nuevo_producto:
                reg = registrar_producto(nuevo_producto)
                productos_editados.append(reg)
        
        nuevos_registros = productos_editados
    else:
        nuevos_registros = sesion_original["registros"]  # Mantenemos los productos originales
    
    # Guardamos los cambios
    actualizar_sesion(sesion_id, nueva_fecha, nuevo_responsable, nueva_area, nuevos_registros)
    
    encabezado("EXITO")
    fila("Sesion actualizada correctamente.")
    linea_bot()
    input("   >> ")

# ======================================================================
# NUEVA SESIÓN
# ======================================================================
def nueva_sesion():
    """
    Crea una nueva sesión de registro.
    Pide: responsable, área de cocina, fecha y luego permite agregar productos.
    """
    encabezado("NUEVA SESION")
    fila("Nombre del responsable (ICARG.) :")
    linea_bot()
    responsable = input("   >> ").strip()
    if not responsable:
        responsable = "Sin nombre"
    
    encabezado("NUEVA SESION")
    fila("Area de cocina :")
    fila("  Ejemplos: Salteados, Fritura, Parrilla, Cocidos")
    fila("")
    fila("  - Salteados")
    fila("  - Fritura")
    fila("  - Parrilla")
    fila("  - Cocidos")
    fila("")
    linea_bot()
    area = input("   >> ").strip()
    if not area:
        area = "Sin area"

    encabezado("NUEVA SESION")
    hoy = datetime.now().strftime("%d-%m-%Y")  # Fecha actual
    fila("Fecha (Enter = hoy " + hoy + ") :")
    linea_bot()
    fecha = input("   >> ").strip()
    if not fecha:
        fecha = hoy  # Si no ingresa fecha, usamos la de hoy

    # Lista de productos disponibles (se irá llenando)
    PRODUCTOS_DEFAULT = []  # Productos predefinidos (vacío por ahora)
    productos = list(PRODUCTOS_DEFAULT)
    registros = []  # Aquí guardamos los productos registrados
    hora = datetime.now().strftime("%H:%M:%S")  # Hora actual

    # Bucle principal para agregar productos
    while True:
        encabezado("SELECCIONAR PRODUCTO")
        fila("Responsable : " + responsable + "   Area : " + area + "   Fecha : " + fecha)
        fila("Productos registrados : " + str(len(registros)))
        linea_mid()

        # Productos que ya han sido registrados
        registrados = [r["producto"] for r in registros]
        # Productos que aún no han sido registrados
        pendientes = [p for p in productos if p not in registrados]

        # Mostramos los productos pendientes si hay
        if pendientes:
            for i, p in enumerate(pendientes, 1):
                fila("  " + str(i) + ". " + p)
            linea_mid()

        # Opciones del menú
        fila("  N. Agregar nuevo producto")
        fila("  V. Ver resumen parcial")
        fila("  F. Finalizar y guardar")
        linea_bot()
        op = input("   >> ").strip().upper()

        if op == "F":
            break  # Finalizar y salir del bucle

        elif op == "V":
            if registros:
                mostrar_resumen(registros, fecha, responsable, area)
                linea_top()
                fila("Presiona Enter para continuar...")
                linea_bot()
                input("   >> ")

        elif op == "N":
            encabezado("NUEVO PRODUCTO")
            fila("Nombre del producto :")
            linea_bot()
            nuevo = input("   >> ").strip().upper()
            
            if nuevo:
                if nuevo not in productos:
                    productos.append(nuevo)  # Agregamos a la lista de productos
                    encabezado(f"REGISTRANDO: {nuevo}")
                    fila("Producto : " + nuevo)
                    linea_mid()
                    
                    reg = registrar_producto(nuevo)  # Registramos el producto
                    registros.append(reg)
                    
                    encabezado("PRODUCTO REGISTRADO")
                    fila("'" + nuevo + "' guardado correctamente.")
                    linea_mid()
                    fila("  C. Continuar con otro producto")
                    fila("  F. Finalizar y guardar")
                    linea_bot()
                    accion = input("   >> ").strip().upper()
                    if accion == "F":
                        break
                else:
                    encabezado("AVISO")
                    fila(f"El producto '{nuevo}' ya existe en la lista.")
                    linea_bot()
                    input("   >> ")

        elif op.isdigit():
            idx = int(op) - 1  # Convertimos a índice
            if 0 <= idx < len(pendientes):
                reg = registrar_producto(pendientes[idx])
                registros.append(reg)

                encabezado("PRODUCTO REGISTRADO")
                fila("'" + pendientes[idx] + "' guardado correctamente.")
                linea_mid()
                fila("  C. Continuar con otro producto")
                fila("  F. Finalizar y guardar")
                linea_bot()
                accion = input("   >> ").strip().upper()
                if accion == "F":
                    break

    if not registros:
        encabezado("AVISO")
        fila("No se registro ningun producto.")
        fila("Sesion cancelada.")
        linea_bot()
        input("   >> ")
        return

    # Guardamos la sesión en la base de datos
    guardar_sesion(fecha, responsable, area, hora, registros)
    mostrar_resumen(registros, fecha, responsable, area)
    linea_top()
    fila("Datos guardados correctamente en SQLite.")
    fila("Presiona Enter para volver al menu...")
    linea_bot()
    input("   >> ")

# ======================================================================
# HISTORIAL DE SESIONES
# ======================================================================
def ver_historial():
    """
    Muestra todas las sesiones guardadas para que el usuario pueda ver los detalles de cada una.
    """
    sesiones = cargar_sesiones()
    encabezado("HISTORIAL DE SESIONES")
    if not sesiones:
        fila("No hay sesiones guardadas aun.")
        linea_bot()
        input("   >> ")
        return

    # Mostramos la lista de sesiones
    for i, s in enumerate(sesiones, 1):
        fila(f"  {i}. {s['fecha']} - {s['responsable']}  ({s['area']})  ({len(s['registros'])} productos)")

    linea_mid()
    fila("  Numero de sesion para ver detalle")
    fila("  (Enter para volver) :")
    linea_bot()
    op = input("   >> ").strip()
    if op.isdigit():
        idx = int(op) - 1
        if 0 <= idx < len(sesiones):
            s = sesiones[idx]
            mostrar_resumen(s["registros"], s["fecha"], s["responsable"], s["area"])
            linea_top()
            fila("Presiona Enter para volver...")
            linea_bot()
            input("   >> ")

# ======================================================================
# MENÚ PRINCIPAL
# ======================================================================
def menu_principal():
    """
    Función principal que muestra el menú y maneja las opciones.
    Es el punto de entrada del programa.
    """
    crear_tablas()  # Aseguramos que las tablas existen al iniciar
    
    while True:  # Bucle infinito hasta que el usuario elija salir
        limpiar()
        linea_top()
        fila("CONTROL INTERNO", "center")
        linea_mid()
        fila("  1. Nueva sesion de registro")
        fila("  2. Ver historial de sesiones")
        fila("  3. Ver total de productos")
        fila("  4. Buscar por fecha")
        fila("  5. Editar sesion")
        fila("  6. Salir")
        linea_bot()
        op = input("   >> ").strip()

        # Llamamos a la función correspondiente según la opción elegida
        if op == "1":
            nueva_sesion()
        elif op == "2":
            ver_historial()
        elif op == "3":
            ver_todos_los_productos()
        elif op == "4":
            buscar_por_fecha()
        elif op == "5":
            editar_sesion()
        elif op == "6":
            limpiar()
            linea_top()
            fila("Hasta luego!", "center")
            linea_bot()
            print()
            break  # Salimos del bucle y terminamos el programa

# ======================================================================
# PUNTO DE ENTRADA DEL PROGRAMA
# ======================================================================
# Esta condición verifica si el script se está ejecutando directamente
# (y no siendo importado como módulo en otro programa)
if __name__ == "__main__":
    menu_principal()  # Iniciamos el programa