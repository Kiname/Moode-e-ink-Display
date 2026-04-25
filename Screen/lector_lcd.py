import os
import time
import sys
import logging
import signal
import atexit

# NUEVAS IMPORTACIONES PARA EL SISTEMA DE EVENTOS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import epd2in13_V2
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURACIÓN BÁSICA ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

ARCHIVO = "/home/kiko/lcd.txt"
RUTA_FUENTE = "/home/kiko/Screen/Font.ttc" 
RUTA_IMAGEN_STOP = "/home/kiko/Screen/kc.bmp"

ANCHO_PANTALLA, ALTO_PANTALLA = 250, 122

ETIQUETAS = {"artist", "album", "title", "encoded", "bitrate", "state", "file", "outrate"}

# --- MEMORIA CACHÉ Y ESTADOS ---
FUENTES = {}
IMAGEN_STOP_ROTADA = None

contador_parciales = 0
estado_anterior = "stop" 

def inicializar_recursos():
    global IMAGEN_STOP_ROTADA
    logging.info("Precargando recursos gráficos...")
    
    if not os.path.exists(RUTA_FUENTE):
        logging.error(f"¡CRÍTICO! No se encuentra la fuente en {RUTA_FUENTE}.")
    else:
        try:
            for i in range(10, 36):
                FUENTES[i] = ImageFont.truetype(RUTA_FUENTE, i)
            logging.info("Fuentes .ttc cargadas.")
        except Exception as e:
            logging.error(f"Fallo al interpretar la fuente: {e}")

    try:
        if os.path.exists(RUTA_IMAGEN_STOP):
            img = Image.open(RUTA_IMAGEN_STOP).resize((ANCHO_PANTALLA, ALTO_PANTALLA)).convert('L')
            IMAGEN_STOP_ROTADA = img.point(lambda x: 0 if x < 128 else 255, '1').rotate(180)
    except Exception as e:
        logging.error(f"Fallo al cargar imagen de stop: {e}")

def leer_datos():
    if not os.path.exists(ARCHIVO): return {}
    datos = {}
    with open(ARCHIVO, 'r', encoding='utf-8') as f:
        for linea in f:
            if '=' in linea:
                clave, valor = linea.strip().split('=', 1)
                if clave in ETIQUETAS:
                    datos[clave] = valor.strip()
    return datos

def actualizar_pantalla(datos):
    global contador_parciales, estado_anterior
    
    epd = epd2in13_V2.EPD()
    estado_actual = datos.get("state", "").lower()

    if estado_actual in ("stop", "pause"):
        if estado_anterior not in ("stop", "pause"):
            logging.info("-> Modo STOP (FULL_UPDATE con imagen BMP)")
            epd.init(epd.FULL_UPDATE)
            if IMAGEN_STOP_ROTADA:
                epd.display(epd.getbuffer(IMAGEN_STOP_ROTADA))
            epd.sleep() 
        
        estado_anterior = estado_actual
        return

    image = Image.new('1', (ANCHO_PANTALLA, ALTO_PANTALLA), 255)
    draw = ImageDraw.Draw(image)

    def obtener_fuente(texto, tam_ideal):
        if not FUENTES:
            return ImageFont.load_default(), 100 
            
        for tam in range(tam_ideal, 9, -1):
            fuente = FUENTES.get(tam, FUENTES.get(10))
            try: ancho = draw.textlength(texto, font=fuente)
            except AttributeError: ancho = draw.textsize(texto, font=fuente)[0]
            if ancho <= 245: return fuente, ancho
        return FUENTES.get(10), 245

    artista = datos.get("artist", "")
    es_radio = "radio station" in artista.lower()
    es_bluetooth = datos.get("file", "").lower() == "bluetooth active"

    draw.line([(15, 36), (235, 36)], fill=0, width=2)     
    draw.line([(15, 92), (235, 92)], fill=0, width=2)    

    if es_bluetooth:
        f_bt, w_bt = obtener_fuente("Bluetooth", 28) 
        draw.text(((ANCHO_PANTALLA - w_bt) // 2, 2), "Bluetooth", font=f_bt, fill=0)
        outrate = datos.get("outrate", "")
        if outrate:
            f_out, w_out = obtener_fuente(outrate, 16) 
            draw.text(((ANCHO_PANTALLA - w_out) // 2, 98), outrate, font=f_out, fill=0)

    elif es_radio:
        estacion = datos.get("album", "")
        f_est, w_est = obtener_fuente(estacion, 28) 
        draw.text(((ANCHO_PANTALLA - w_est) // 2, 2), estacion, font=f_est, fill=0)
        titulo = datos.get("title", "Sintonizando...")
        f_tit, w_tit = obtener_fuente(titulo, 24) 
        draw.text(((ANCHO_PANTALLA - w_tit) // 2, 55), titulo, font=f_tit, fill=0)
        enc = datos.get("encoded", "")
        bit = datos.get("bitrate", "")
        info_tec = f"{enc} | {bit}" if (enc and bit) else f"{enc}{bit}"
        if info_tec:
            f_tec, w_tec = obtener_fuente(info_tec, 16) 
            draw.text(((ANCHO_PANTALLA - w_tec) // 2, 98), info_tec, font=f_tec, fill=0)

    else:
        f_art, w_art = obtener_fuente(artista, 28) 
        draw.text(((ANCHO_PANTALLA - w_art) // 2, 2), artista, font=f_art, fill=0)
        album = datos.get("album", "")
        f_alb, w_alb = obtener_fuente(album, 20) 
        draw.text(((ANCHO_PANTALLA - w_alb) // 2, 42), album, font=f_alb, fill=0)
        titulo = datos.get("title", "")
        f_tit, w_tit = obtener_fuente(titulo, 24) 
        draw.text(((ANCHO_PANTALLA - w_tit) // 2, 64), titulo, font=f_tit, fill=0)
        enc = datos.get("encoded", "")
        bit = datos.get("bitrate", "")
        info_tec = f"{enc} | {bit}" if (enc and bit) else f"{enc}{bit}"
        if info_tec:
            f_tec, w_tec = obtener_fuente(info_tec, 16) 
            draw.text(((ANCHO_PANTALLA - w_tec) // 2, 98), info_tec, font=f_tec, fill=0)

    buffer_imagen = epd.getbuffer(image.rotate(180))
    venimos_de_stop = estado_anterior in ("stop", "pause")

    if venimos_de_stop or contador_parciales >= 10:
        logging.info("-> Limpieza Total (FULL_UPDATE)")
        epd.init(epd.FULL_UPDATE)
        epd.displayPartBaseImage(buffer_imagen) 
        contador_parciales = 0
    else:
        logging.info(f"-> Actualización Parcial (PART_UPDATE) - Refresco {contador_parciales}/10")
        epd.init(epd.PART_UPDATE)
        epd.displayPartial(buffer_imagen)
        contador_parciales += 1

    estado_anterior = estado_actual


# --- NUEVA CLASE PARA GESTIONAR EVENTOS DE ARCHIVO ---
class GestorCambiosLCD(FileSystemEventHandler):
    def __init__(self):
        self.datos_ant = {}

    def on_modified(self, event):
        # Asegurarnos de que reaccionamos al archivo correcto, no a la carpeta entera
        if not event.is_directory and event.src_path == ARCHIVO:
            # Pausa de 0.1s muy importante: Evita que leamos el archivo justo 
            # en el microsegundo en el que el otro programa lo está escribiendo.
            time.sleep(0.1) 
            try:
                datos_nuevos = leer_datos()
                # Solo actualizamos si el contenido REALMENTE ha cambiado
                if datos_nuevos and datos_nuevos != self.datos_ant:
                    actualizar_pantalla(datos_nuevos)
                    self.datos_ant = datos_nuevos
            except Exception as e:
                logging.error(f"Error procesando el evento: {e}")


# --- RUTINA DE VIDA DEL SERVICIO ---
limpieza_realizada = False
def apagar_seguro(*args):
    global limpieza_realizada
    if limpieza_realizada: return
    try:
        logging.info("Apagando pantalla de forma segura...")
        epd = epd2in13_V2.EPD()
        epd.init(epd.FULL_UPDATE)
        epd.Clear(0xFF)
        epd.sleep()
        epd2in13_V2.epdconfig.module_exit(cleanup=True)
        limpieza_realizada = True
    except: pass
    sys.exit(0)


def main():
    inicializar_recursos()
    
    gestor_eventos = GestorCambiosLCD()

    # Hacemos una primera lectura manual al iniciar por si el reproductor ya estaba sonando
    if os.path.exists(ARCHIVO):
        datos_iniciales = leer_datos()
        if datos_iniciales:
            actualizar_pantalla(datos_iniciales)
            gestor_eventos.datos_ant = datos_iniciales

    # Configuramos al vigía (Observer) de Watchdog
    directorio_vigilado = os.path.dirname(ARCHIVO)
    observer = Observer()
    # Le decimos que vigile la carpeta, pasando nuestro Gestor cuando detecte algo
    observer.schedule(gestor_eventos, path=directorio_vigilado, recursive=False)
    observer.start()
    
    logging.info(f"Vigilancia activa por eventos en: {ARCHIVO}")

    try:
        while True:
            # El hilo principal se queda "congelado" cediendo la CPU.
            # Watchdog está trabajando en un hilo secundario consumiendo 0%.
            time.sleep(3600) 
    except KeyboardInterrupt:
        logging.info("Interrupción por teclado detectada...")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    atexit.register(apagar_seguro)
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, apagar_seguro)
    main()
