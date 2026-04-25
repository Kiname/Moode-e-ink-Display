![E-ink Display](e-ink_display.jpg)

# **English description here: [README_EN.md](README_EN.md)**

# **UPDATE:**
Este script es mas rapido y optimiza recursos al usar la libreria Watchdog en lugar de comprobar LCD.TXT cada segundo pero necesita la instalacion de esta libreria.
```bash
sudo apt install python3-watchdog
```

# **Guía Técnica: Configuración y Optimización de Pantalla E-Ink y Audio en Raspberry Pi 4**

Este documento detalla la resolución de conflictos de hardware y el desarrollo evolutivo de un sistema de visualización para un reproductor de audio basado en Raspberry Pi 4, utilizando un DAC Pro y una pantalla Waveshare E-Paper V2 de 2.13 pulgadas.

## **1\. Resolución de Conflictos de Hardware (GPIO)**

El problema inicial consistía en la detención del sonido al ejecutar el script de la pantalla. Se identificó un conflicto en los pines GPIO, particularmente en el **GPIO 18**, el cual es utilizado simultáneamente por:

* **Raspberry DAC Pro:** Como reloj de bits (BCLK) para el bus I2S.  
* **Waveshare E-Paper:** Configurado por defecto como pin de alimentación (PWR\_PIN) en la librería epdconfig.py.


### **Solución Técnica**

Para solucionar el conflicto de hardware, se modificó el archivo epdconfig.py **eliminando por completo las referencias y el uso del CS\_PIN y el PWR\_PIN** de todo el código. Al no inicializar ni utilizar estos pines desde la librería de la pantalla, se liberó por completo el bus I2S, permitiendo que la tarjeta de sonido Raspberry DAC Pro funcionara sin interrupciones junto con la pantalla E-Paper.
Estos pines solamente serian necesarios en el caso de usar mas de una tarjeta en el bus I2C.

## **2\. Desarrollo del Script de Control (lector\_lcd.py)**

El script evolucionó para integrar diversas funcionalidades estéticas y operativas, optimizando la legibilidad y el rendimiento del sistema.

### **2.1. Funcionalidades Implementadas**

| Funcionalidad | Descripción   |
| :---- | :---- |
| **Rotación de 180º** | Ajuste mediante software (.rotate(180)) para adaptar la orientación física del montaje. |
| **Modo Detenido (Stop/Pause)** | Visualización de una imagen personalizada (kc.bmp) cuando el estado del reproductor no es "play". |
| **Diseño Minimalista** | Eliminación de etiquetas (Artist:, Album:) para mostrar solo los valores, centrados y divididos por líneas horizontales. |
| **Soporte Bluetooth** | Detección automática de la clave file=Bluetooth Active para mostrar una interfaz específica con la tasa de salida (outrate). |

### **2.2. Optimización de Rendimiento**

Para minimizar el desgaste de la tarjeta microSD y mejorar la velocidad de respuesta, se implementó una **estrategia de caché**:

* **Precarga de Fuentes:** Los objetos ImageFont se cargan en la RAM al inicio del script en un rango de tamaños (10 a 35).  
* **Caché de Imágenes:** La imagen kc.bmp se procesa y almacena en memoria una sola vez.  
* **Frecuencia de Lectura:** El script monitoriza el archivo lcd.txt cada 1 segundo (time.sleep(1)) comparando la fecha de modificación (mtime).

## **3\. Configuracion Moode**

Dentro de Moode es necesario activar LCD UPDATE dentro de la configuracion de perifericos, esto generara el archivo LCD.txt en /home/"USER"/, es necesario activar esto antes de ejecutar el script.

## **4\. Funcionamiento de Script**
Copia la carpeta /Screen del repositorio en /home/"USER"

edita el archivo lector_lcd.py con

```bash
nano ./Screen/lector_lcd.py
```

Al comienzo del archivo lector_lcd.py cambia en las lineas:

```bash
ARCHIVO = "/home/kiko/lcd.txt"
RUTA_FUENTE = "/home/kiko/Screen/Font.ttc" 
RUTA_IMAGEN_STOP = "/home/kiko/Screen/kc.bmp"
```
kiko (mi usuario) por el tuyo

debe quedarte algo asi:
```bash
ARCHIVO = "/home/moode/lcd.txt"
RUTA_FUENTE = "/home/moode/Screen/Font.ttc" 
RUTA_IMAGEN_STOP = "/home/moode/Screen/kc.bmp"
```

### **4.1. Ejecucion local**

El script puede ejecutarse localmente desde un terminal SSH con:
```bash
python3 /home/"USER"/Screen/lector_lcd.py
```
Ctrl+C sale del script y borra la pantalla

### **4.2. Ejecucion como servicio**

Tambien es posible ejecutarlo como servicio.

Pasos para crear el Servicio de Systemd
 Detén el script si lo tienes corriendo. (Presiona Ctrl+C).

Crea el archivo del servicio:
Abre tu terminal y ejecuta este comando para crear un archivo de configuración nuevo:

```bash
sudo nano /etc/systemd/system/pantalla_lcd.service
```
Pega la configuración:
Copia y pega el siguiente texto en ese archivo.

```bash
[Unit]
Description=Monitor de Pantalla E-Paper LCD
After=multi-user.target

[Service]
Type=simple
User=kiko
WorkingDirectory=/home/kiko
ExecStart=/usr/bin/python3 /home/USER/Screen/lector_lcd.py


KillSignal=SIGTERM
TimeoutStopSec=12
SendSIGKILL=yes

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target

```
Guarda y cierra:

Presiona Ctrl + O (letra O, no cero) para guardar.

Presiona Enter para confirmar.

Presiona Ctrl + X para salir de nano.

Activa y arranca el servicio:

Ahora vamos a decirle a la Raspberry que lea este nuevo archivo, que lo arranque ahora mismo, y que lo arranque automáticamente cada vez que enciendas la máquina. Ejecuta estos tres comandos uno a uno:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pantalla_lcd.service
sudo systemctl start pantalla_lcd.service
```

¿Cómo saber si está funcionando?
Como ahora corre en segundo plano de forma "invisible", si quieres ver los mensajes que antes te salían en la terminal (los INFO: Cambio detectado...), puedes usar este comando para ver el registro en tiempo real:

```bash
journalctl -u pantalla_lcd.service -f
```
(Presiona Ctrl+C para salir de esa vista, el programa seguirá corriendo de fondo).

## **5\. Personalizacion**

Modifica el archivo kc.bmp a tu gusto, debe ser una imagen BMP monocromo con un tamaño de 255x122 pixel.


