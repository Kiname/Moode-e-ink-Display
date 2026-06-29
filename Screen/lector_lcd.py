import os
import time
import sys
import logging
import signal
import atexit
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw, ImageFont

import epd2in13_V2

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Usamos Path para mayor seguridad en rutas
BASE_PATH = Path("/home/kiko")
ARCHIVO_DATOS = BASE_PATH / "lcd.txt"
RUTA_FUENTE = BASE_PATH / "Screen/Font.ttc"
RUTA_IMAGEN_STOP = BASE_PATH / "Screen/kc.bmp"

ANCHO, ALTO = 250, 122
ETIQUETAS_VALIDAS = {"artist", "album", "title", "encoded", "bitrate", "state", "file", "outrate"}

class PantallaControlador:
    def __init__(self):
        self.epd = epd2in13_V2.EPD()
        self.fuentes = {}
        self.imagen_stop = None
        self.estado_anterior = "arranque"
        self.contador_parciales = 5
        self.estado_posicion_lineas = 0
        self.datos_ant = {}
        
        self._cargar_recursos()

    def _cargar_recursos(self):
        logging.info("Precargando recursos...")
        # Cargar fuentes
        if RUTA_FUENTE.exists():
            try:
                for i in range(10, 36):
                    self.fuentes[i] = ImageFont.truetype(str(RUTA_FUENTE), i)
            except Exception as e:
                logging.error(f"Error cargando fuentes: {e}")
        
        # Cargar imagen de stop
        if RUTA_IMAGEN_STOP.exists():
            try:
                img = Image.open(RUTA_IMAGEN_STOP).resize((ANCHO, ALTO)).convert('L')
                self.imagen_stop = img.point(lambda x: 0 if x < 128 else 255, '1').rotate(180)
            except Exception as e:
                logging.error(f"Error cargando imagen stop: {e}")

    def leer_datos(self):
        if not ARCHIVO_DATOS.exists():
            return {}
        datos = {}
        try:
            with open(ARCHIVO_DATOS, 'r', encoding='utf-8') as f:
                for linea in f:
                    if '=' in linea:
                        partes = linea.strip().split('=', 1)
                        if len(partes) == 2:
                            clave, valor = partes
                            if clave in ETIQUETAS_VALIDAS:
                                datos[clave] = valor.strip()
        except Exception as e:
            logging.error(f"Error leyendo archivo: {e}")
        return datos

    def obtener_fuente_y_ancho(self, draw, texto, tam_ideal):
        """Busca el tamaño de fuente que mejor se ajuste al ancho de la pantalla."""
        if not self.fuentes:
            return ImageFont.load_default(), 100
        
        for tam in range(tam_ideal, 9, -1):
            fnt = self.fuentes.get(tam, self.fuentes.get(10))
            # Método moderno para medir texto (Pillow 10+)
            ancho = draw.textlength(texto, font=fnt)
            if ancho <= (ANCHO - 5):
                return fnt, ancho
        return self.fuentes.get(10), ANCHO

    def renderizar_y_mostrar(self, datos):
        estado_actual = datos.get("state", "").lower()
        
        # Lógica de STOP / PAUSE
        if estado_actual in ("stop", "pause"):
            if self.estado_anterior not in ("stop", "pause"):
                logging.info("-> Modo STOP")
                self.epd.init(self.epd.FULL_UPDATE)
                if self.imagen_stop:
                    self.epd.display(self.epd.getbuffer(self.imagen_stop))
                self.epd.sleep()
            self.estado_anterior = estado_actual
            return

        # Determinación de tipo de actualización
        venimos_de_stop = self.estado_anterior in ("stop", "pause")
        es_full_update = venimos_de_stop or self.contador_parciales >= 5

        if es_full_update:
            self.estado_posicion_lineas = (self.estado_posicion_lineas + 1) % 3

        # Crear imagen base
        imagen = Image.new('1', (ANCHO, ALTO), 255)
        draw = ImageDraw.Draw(imagen)

        # Pixel Shifting para las líneas
        offset_y = {0: 0, 1: -2, 2: 2}.get(self.estado_posicion_lineas, 0)
        draw.line([(15, 36 + offset_y), (235, 36 + offset_y)], fill=0, width=1)
        draw.line([(15, 92 + offset_y), (235, 92 + offset_y)], fill=0, width=1)

        # Preparar textos
        artista = datos.get("artist", "")
        es_radio = "radio station" in artista.lower()
        es_bluetooth = datos.get("file", "").lower() == "bluetooth active"

        # Función auxiliar interna para centrar texto horizontalmente
        def dibujar_centrado(texto, y, tam_fuente):
            f, w = self.obtener_fuente_y_ancho(draw, texto, tam_fuente)
            draw.text(((ANCHO - w) // 2, y), texto, font=f, fill=0)

        # Lógica de dibujo según contexto
        if es_bluetooth:
            dibujar_centrado("Bluetooth", 2, 28)
            dibujar_centrado(datos.get("outrate", ""), 98, 16)
        elif es_radio:
            dibujar_centrado(datos.get("album", ""), 2, 28)
            dibujar_centrado(datos.get("title", "Sintonizando..."), 55, 24)
            info = f"{datos.get('encoded','')} | {datos.get('bitrate','')}".strip(" |")
            dibujar_centrado(info, 98, 16)
        else:
            dibujar_centrado(artista, 2, 28)
            dibujar_centrado(datos.get("album", ""), 42, 20)
            dibujar_centrado(datos.get("title", ""), 64, 24)
            info = f"{datos.get('encoded','')} | {datos.get('bitrate','')}".strip(" |")
            dibujar_centrado(info, 98, 16)

        # Enviar a pantalla
        buffer = self.epd.getbuffer(imagen.rotate(180))
        if es_full_update:
            logging.info(f"-> Full Update (Posición línea: {self.estado_posicion_lineas})")
            self.epd.init(self.epd.FULL_UPDATE)
            self.epd.displayPartBaseImage(buffer)
            self.contador_parciales = 0
        else:
            logging.info(f"-> Partial Update ({self.contador_parciales}/5)")
            self.epd.init(self.epd.PART_UPDATE)
            self.epd.displayPartial(buffer)
            self.contador_parciales += 1

        self.estado_anterior = estado_actual

    def limpiar_pantalla(self):
        logging.info("Iniciando limpieza profunda...")
        try:
            self.epd.init(self.epd.FULL_UPDATE)
            for color in [0xFF, 0x00, 0xFF]:
                self.epd.Clear(color)
                time.sleep(0.5)
            self.epd.sleep()
            epd2in13_V2.epdconfig.module_exit(cleanup=True)
        except Exception as e:
            logging.error(f"Error en limpieza: {e}")

# --- GESTOR DE EVENTOS ---
class GestorCambiosLCD(FileSystemEventHandler):
    def __init__(self, controlador):
        self.ctrl = controlador

    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path) == ARCHIVO_DATOS:
            time.sleep(0.1) # Breve pausa para asegurar escritura completa
            datos = self.ctrl.leer_datos()
            
            # Si el archivo está vacío o no se pudo leer, forzamos STOP
            if not datos:
                datos = {"state": "stop"}
                
            if datos != self.ctrl.datos_ant:
                # Definimos qué campos realmente justifican un refresco de la pantalla E-ink
                campos_clave = ["artist", "album", "title", "state", "file"]
                
                cambio_importante = False
                for campo in campos_clave:
                    if datos.get(campo) != self.ctrl.datos_ant.get(campo):
                        cambio_importante = True
                        break
                
                # Solo renderizamos si ha cambiado la canción o el estado (play/stop)
                if cambio_importante:
                    self.ctrl.renderizar_y_mostrar(datos)
                
                # Actualizamos siempre el diccionario anterior para mantener los datos al día,
                # de este modo, cuando haya un cambio importante, la pantalla pintará el
                # bitrate más reciente que se haya registrado en segundo plano.
                self.ctrl.datos_ant = datos

def main():
    controlador = PantallaControlador()
    
    # Primera ejecución
    datos_ini = controlador.leer_datos()
    
    # Si al arrancar el archivo está vacío o no existe, forzamos STOP
    if not datos_ini:
        datos_ini = {"state": "stop"}
        
    controlador.renderizar_y_mostrar(datos_ini)
    controlador.datos_ant = datos_ini

    # Configurar Watchdog
    observer = Observer()
    manejador = GestorCambiosLCD(controlador)
    observer.schedule(manejador, path=str(ARCHIVO_DATOS.parent), recursive=False)
    observer.start()

    # Manejo de señales para apagado limpio
    def handler_apagar(sig, frame):
        observer.stop()
        controlador.limpiar_pantalla()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler_apagar)
    signal.signal(signal.SIGTERM, handler_apagar)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.join()

if __name__ == "__main__":
    main()
