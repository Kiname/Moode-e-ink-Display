import os
from mutagen import File

def extraer_caratulas(ruta_base, nombre_imagen="cover.jpg"):
    """
    Recorre los directorios, extrae la carátula del primer MP3/FLAC 
    y la guarda en el directorio correspondiente.
    """
    # os.walk recorre todos los directorios y subdirectorios
    for raiz, directorios, archivos in os.walk(ruta_base):
        # Ordenamos los archivos para asegurar que siempre procesamos el "primero" de forma consistente
        archivos.sort()
        
        for archivo in archivos:
            if archivo.lower().endswith(('.mp3', '.flac')):
                ruta_completa = os.path.join(raiz, archivo)
                
                try:
                    # Mutagen detecta automáticamente si es MP3 o FLAC
                    audio = File(ruta_completa)
                    
                    if audio is None:
                        continue
                        
                    datos_imagen = None
                    
                    # --- Extracción para FLAC ---
                    if archivo.lower().endswith('.flac'):
                        if hasattr(audio, 'pictures') and audio.pictures:
                            datos_imagen = audio.pictures[0].data
                            
                    # --- Extracción para MP3 ---
                    elif hasattr(audio, 'tags') and audio.tags:
                        # Buscamos la etiqueta APIC (Attached Picture) en los metadatos ID3
                        for etiqueta in audio.tags.values():
                            if etiqueta.FrameID == 'APIC':
                                datos_imagen = etiqueta.data
                                break
                    
                    # Si encontramos una imagen, la guardamos y dejamos de buscar en este directorio
                    if datos_imagen:
                        ruta_salida = os.path.join(raiz, nombre_imagen)
                        
                        # Si ya existe un cover.jpg, puedes decidir si saltarlo. 
                        # En este caso, lo sobrescribirá.
                        with open(ruta_salida, 'wb') as img_file:
                            img_file.write(datos_imagen)
                            
                        print(f"✅ Carátula extraída en: {raiz} (desde {archivo})")
                        break # Rompemos el bucle 'for archivo...' para pasar al siguiente directorio
                        
                except Exception as e:
                    print(f"❌ Error procesando {ruta_completa}: {e}")
                    # Si falla este archivo, el bucle continúa con el siguiente en la misma carpeta

# --- Ejecución del script ---
if __name__ == "__main__":
    # Sustituye esta ruta por la ruta de tu disco o carpeta de música
    ruta_musica = "./" 
    
    print(f"Iniciando escaneo en: {ruta_musica}\n")
    extraer_caratulas(ruta_musica)
    print("\nProceso terminado.")
