#!/bin/bash

# Variables globales
FILE_imageTAR="image.tar"
FILE_layerTAR="layer.tar"
DIR_IMAGE="decompress_imageTAR"
DIR_LAYER="decompress_layerTAR"

# Funciones del programa
function main { # principito
    # Descomprimimos imagen de Docker.
    echo -e "[+] Descomprimiendo objeto $FILE_imageTAR...\n"
    mkdir -p $DIR_IMAGE

    tar xf $FILE_imageTAR --directory $DIR_IMAGE

    # Descomprimimos cada archivo -layer.tar-.
    echo -e "[+] Descomprimiendo objeto $FILE_layerTAR encontrado en los directorios extraidos de $FILE_imageTAR...\n"
    cd $DIR_IMAGE

    for directory in $(ls -d */); do
        echo -en "* Directorio $directory"
        cd $directory
        mkdir -p "../${DIR_LAYER}/${directory}" && tar -xf $FILE_layerTAR --directory "../${DIR_LAYER}/${directory}"
        cd ..
        echo -e " [✔]"
    done

    echo -e "\n[+] Acá: $(pwd)/${DIR_LAYER} están los objetos descomprimidos y organizados por carpetas (:"
}

if [ ! -f "$FILE_imageTAR" ]; then
    echo -e "\n[-] Imagen de Docker ($FILE_imageTAR) no encontrada :("
    exit 1
else
    rm -rf $DIR_IMAGE
    main
fi
