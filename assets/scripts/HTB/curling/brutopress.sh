#!/bin/bash

: '
References:
* Para validar contenido exacto en cadena usando -if-: https://unix.stackexchange.com/questions/275329/using-grep-in-conditional-statement-in-bash
* Archivo existe o no: https://linuxhint.com/check-if-a-file-exists-in-bash/
'

password_backup_file=password_backup.txt
# Hacemos el contenido del backup portable
password_backup_content_file="$(echo MDAwMDAwMDA6IDQyNWEgNjgzOSAzMTQxIDU5MjYgNTM1OSA4MTliIGJiNDggMDAwMCAgQlpoOTFBWSZTWS4uLkguLgowMDAwMDAxMDogMTdmZiBmZmZjIDQxY2YgMDVmOSA1MDI5IDYxNzYgNjFjYyAzYTM0ICAuLi4uQS4uLlApYXZhLjo0CjAwMDAwMDIwOiA0ZWRjIGNjY2MgNmUxMSA1NDAwIDIzYWIgNDAyNSBmODAyIDE5NjAgIE4uLi5uLlQuIy5AJS4uLmAKMDAwMDAwMzA6IDIwMTggMGNhMCAwMDkyIDFjN2EgODM0MCAwMDAwIDAwMDAgMDAwMCAgIC4uLi4uLnouQC4uLi4uLgowMDAwMDA0MDogMDY4MCA2OTg4IDM0NjggNjQ2OSA4OWE2IGQ0MzkgZWE2OCBjODAwICAuLmkuNGhkaS4uLjkuaC4uCjAwMDAwMDUwOiAwMDBmIDUxYTAgMDA2NCA2ODFhIDA2OWUgYTE5MCAwMDAwIDAwMzQgIC4uUS4uZGguLi4uLi4uLjQKMDAwMDAwNjA6IDY5MDAgMDc4MSAzNTAxIDZlMTggYzJkNyA4Yzk4IDg3NGEgMTNhMCAgaS4uLjUubi4uLi4uLkouLgowMDAwMDA3MDogMDg2OCBhZTE5IGMwMmEgYjBjMSA3ZDc5IDJlYzIgM2M3ZSA5ZDc4ICAuaC4uLiouLn15Li48fi54CjAwMDAwMDgwOiBmNTNlIDA4MDkgZjA3MyA1NjU0IGMyN2EgNDg4NiBkZmEyIGU5MzEgIC4+Li4uc1ZULnpILi4uLjEKMDAwMDAwOTA6IGM4NTYgOTIxYiAxMjIxIDMzODUgNjA0NiBhMmRkIGMxNzMgMGQyMiAgLlYuLi4hMy5gRi4uLnMuIgowMDAwMDBhMDogYjk5NiA2ZWQ0IDBjZGIgODczNyA2YTNhIDU4ZWEgNjQxMSA1MjkwICAuLm4uLi4uN2o6WC5kLlIuCjAwMDAwMGIwOiBhZDZiIGIxMmYgMDgxMyA4MTIwIDgyMDUgYTVmNSAyOTcwIGM1MDMgIC5rLi8uLi4gLi4uLilwLi4KMDAwMDAwYzA6IDM3ZGIgYWIzYiBlMDAwIGVmODUgZjQzOSBhNDE0IDg4NTAgMTg0MyAgNy4uOy4uLi4uOS4uLlAuQwowMDAwMDBkMDogODI1OSBiZTUwIDA5ODYgMWU0OCA0MmQ1IDEzZWEgMWMyYSAwOThjICAuWS5QLi4uSEIuLi4uKi4uCjAwMDAwMGUwOiA4YTQ3IGFiMWQgMjBhNyA1NTQwIDcyZmYgMTc3MiA0NTM4IDUwOTAgIC5HLi4gLlVAci4uckU4UC4KMDAwMDAwZjA6IDgxOWIgYmI0OCAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgLi4uSAo= | base64 -d > $password_backup_file)"
xxd_file_reverse=file_reverse
password_found_file=password.txt

# Reversamos el objeto al original.
xxd -r $password_backup_file > ${xxd_file_reverse}.txt

# Según que tipo de archivo sea empezará a descomprimir.
type_file=$(file ${xxd_file_reverse}.txt)

# Hacemos de cuenta que debemos hacer 10 descompresiones.
for i in $(seq 1 10); do
    # Si existe el archivo `password.txt`, imprime el contenido y termina el programa.
    if [ -f "$password_found_file" ]; then
        echo "Contenido del archivo $password_found_file: $(cat $password_found_file)"
        rm -r $password_backup_file $password_found_file
        rm -r $xxd_file_reverse*
        exit 0

    # Si el tipo de archivo contiene exactamente que es un `bzip2`, descomprime con `bzip2`. (Así para las demás)
    elif echo $type_file | grep -wq "bzip2"; then
        compressed_file=${xxd_file_reverse}.bz2
        mv $xxd_file_reverse* $compressed_file
        bzip2 -q -d $compressed_file

    elif echo $type_file | grep -wq "gzip"; then
        compressed_file=${xxd_file_reverse}.gz
        mv $xxd_file_reverse* $compressed_file
        gzip -q -d $compressed_file

    elif echo $type_file | grep -wq "tar"; then
        compressed_file=${xxd_file_reverse}.tar.gz
        mv $xxd_file_reverse* $compressed_file
        tar -xf $compressed_file

    else
        echo "[!] Este tipo de compresión no está en el script:"
        echo $type_file

    fi
    # Tomamos el tipo de archivo del objeto recién descomprimido.
    type_file=$(file ${compressed_file%.*})
done
