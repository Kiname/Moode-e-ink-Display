# **Guía Técnica: Configuración y Optimización de Pantalla E-Ink y Audio en Raspberry Pi 4**

Este documento detalla la resolución de conflictos de hardware y el desarrollo evolutivo de un sistema de visualización para un reproductor de audio basado en Raspberry Pi 4, utilizando un DAC Pro y una pantalla Waveshare E-Paper de 2.13 pulgadas.

## **1\. Resolución de Conflictos de Hardware (GPIO)**

El problema inicial consistía en la detención del sonido al ejecutar el script de la pantalla. Se identificó un conflicto en los pines GPIO, particularmente en el **GPIO 18**, el cual es utilizado simultáneamente por:

* **Raspberry DAC Pro:** Como reloj de bits (BCLK) para el bus I2S.  
* **Waveshare E-Paper:** Configurado por defecto como pin de alimentación (PWR\_PIN) en la librería epdconfig.py.

### **Solución Técnica**

Para solucionar el conflicto de hardware, se modificó el archivo epdconfig.py **eliminando por completo las referencias y el uso del CS\_PIN y el PWR\_PIN** de todo el código. Al no inicializar ni utilizar estos pines desde la librería de la pantalla, se liberó por completo el bus I2S, permitiendo que la tarjeta de sonido Raspberry DAC Pro funcionara sin interrupciones junto con la pantalla E-Paper.

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

## **4\. Funcionamiento de Script

### **4.1. Ejecucion local

El script puede ejecutarse localmente desde un terminal SSH con python3 /Screen/lector_lcd.py
Ctrl+C sale del script y borra la pantalla

### **4.2. Ejecucion como servicio

Tambien es posible ejecutarlo como servicio.


Tambien es posible 
