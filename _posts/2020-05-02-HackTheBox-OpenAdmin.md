---
layout      : post
title       : "HackTheBox - OpenAdmin"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/banneropenadmin.png
categories  : [ htb ]
tags        : [ apache-files, OpenNetAdmin, sudo, ssh-keys, nano ]
---
Maquina Linux nivel fácil. Jugaremos con inspección de código, peticiones web, movimientos internos con Apache, con SSH keys y romperemos /bin/nano.

![openadminHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/openadminHTB.png)

Esta máquina es 90% de enumeración, veamos cuáles son los pasos que seguiremos.

- [Enumeración](#enumeracion)
- [Explotación](#explotacion)
- [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración {#enumeracion}

Empecemos con el escaneo de red, usaremos `nmap`, el cual nos dará información sobre que puertos y servicios están corriendo sobre la máquina.

```bash
$ nmap -sC -sV -p- --open -T4 -oN initialScan 10.10.10.171
```

| Param  | Description   |
| -------|:------------- |
| -sC    | Muestra todos los scripts relacionados con el servicio |
| -sV    | Nos permite ver las versiones de los servicios     |
| -p-    | Escaneo de todos los puertos                       |
| --open | Muestra solo los puertos abiertos                  |
| -T4    | Agresividad con la que hace el escaneo (-T{1-5})   |

![nmapInitial](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/nmapInitial.png)

Tenemos estos servicios corriendo:

- 22: SSH, probablemente nos sirva más adelante
- 80: HTTP, empezaremos por acá a ver que tiene la página web

Veamos el servidor web.

![defaultApache](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/defaultApache.png)

Ok... **. _.** nos muestra la página por default de apache, así que usaremos herramientas que hacen fuerza bruta para ver si hay directorios o archivos activos.

En este caso usaremos `dirsearch`.

```bash
$ dirsearch -u http://10.10.10.171/ -e html,php,js,json
```

* Si le queremos indicar que busque cualquier extensión, se usa `-E`

![dsAll](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/dsAll.png)

Encontramos una carpeta y un archivo HTML. El HTML, nos redirecciona a la misma página por default.

Al ingresar a `/music`, nos muestra:

![pageMusic](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/pageMusic.png)

Después de recorrer la página y encontrar solo hoyos de dudas, entre al apartado `Login`.
 
Si nos fijamos, al tener el mouse sobre él, nos indica que nos moverá a una nueva carpeta llamada`/ona`.

> Acá hay algo importante y es que, siendo una sola web, ¿no deberia estar `/ona` dentro de music, osea `/music/ona`?, esto toma fuerza mas adelante :P no nos volvamos locos tan pronto.

![onaPage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/onaPage.png)

La página ya nos da información importante, estamos corriendo un servicio llamado **Open Net Admin** y su versión **18.1.1**

> [OpenNetAdmin](http://opennetadmin.com/about.html) es un sistema para el seguimiento de las propiedades de la red IP en una base de datos. Basicamente permite rastrear toda la info gueardada en una base de datos sobre una IP.

...

## Explotación {#explotacion}

Después de varios hoyos de dudas y sin saber que hacer con la interfaz, buscamos en Linux a través de una tool muy buena **searchsploit** que directamente es **exploidb** pero en la terminal. 

> [Exploit Database](https://www.exploit-db.com/) es una base de datos que aloja exploits y seguimientos a vulnerabilidades.

![ssploit](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/ssploit.png)

Para nuestra versión solo nos sirven los dos últimos, usaremos el que **no** dispone de **metasploit**.

Con [searchsploit](https://www.exploit-db.com/searchsploit#using) podemos indicarle que nos deje ver el exploit y copiarlo a nuestro entorno (y muchas cosas más)

| Parámetro     | Descripción   |
| --------------|:------------- |
| -x, --examine | Ver el contenido del exploit                     |
| -m, --mirror  | (aka copies) un exploit a nuestro entorno actual |

![exploitVim](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/exploitVim.png)

Básicamente encontramos:

- Se deberá ejecutar sobre bash
- Recibe como primer parámetro la URL
- Está enviando por medio de *curL* la data, envía el formato estándar que recibe *xajax*, pero también nos permite agregar comandos `${cmd}` para al final mandarla a la `${URL}`. 

Algo impirtante es que **no** estamos obteniendo una shell, simplemente estamos haciendo **command execution**, no podremos movernos a una carpeta en especifico, pero si podemos ver su contenido (`cat`) y listarlo (`ls`)

Al ejecutar el exploit, nos da varios errores... Despues de buscar cual era el error, encontramos que el archivo esta en formato **DOS (windows)**. Usamos la herramienta `dos2unix` que practicametne lo dice su nombre, convierte de *dos to unix**.

![dos2unix](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/dos2unix.png)

¡Listo!

Enumeracion y enumeracion, andando de carpeta en carpeta :) 

Hay 3 usuarios disponibles, 

- **www-data**: en el que estamos
- **jimmy**
- **joanna**

![db_setting_ex](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/db_setting_ex.png)

Bien, conseguimos una pw. Veamos si es de alguno de los dos usuarios por medio de SSH

```bash
$ ssh jimmy@10.10.10.171
```

Sip!! Entramos al perfil de **jimmy**, sigamos enumerando. No pondre todas las trampas en las que cai ;) pero encontramos algo despues de todo.

Si utilizamos el comando `id` notamos que estamos dentro del grupo **internal**. Veamos desde la raiz del sistema que archivos son de jimmy y estan asignados al grupo internal

```bash
$ find / -user jimmy -group internal
```

![jimmy_internal](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/jimmy_internal.png)

Fijemonos en `main.php`.

![main_php](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/main_php.png)

Si conseguimos entrar a `/main.php` se ejecutara una consulta al **id_rsa (private key)** dentro del home de **joanna**, así que veamos como hacer esa consulta.

Arriba en el exploit se usaba *curL* para enviar la data a una URL especificada. ¿Acá no es acaso lo mismo? ¿solo que en vez de data queremos entrar en un archivo dentro de una carpeta?

```bash
$ curl http://10.10.10.171/internal/main.php
```

Pero esto simplemente nos muestra:

```bash
...
<title>404 Not Found</title>
</head><body>                                                                         
<h1>Not Found</h1>                 
<p>The requested URL was not found on this server.</p>
<hr>
...
```

Así que acá toma fuerza lo que habíamos olvidado arriba, sobre si estábamos trabajando en una sola web. Resulta que podemos configurar un sistema para que **internal**mente podamos alojar varios dominios sobre el mismo servidor, esto se llama **Virtual Host**, en este caso tenemos:

![virtual_host_domains](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/virtual_host_domains.png)

- 10.10.10.171/music
- 10.10.10.171/ona
- 10.10.10.171/marga
- 10.10.10.171/artwork

Entonces el *curL* de arriba estaría mal, dado que no hay ningún dominio llamado `internal`, pero probando sin él, tampoco obtenemos respuesta. Entonces la respuesta debe estar **interna**mente en la configuración del servidor.

Así que vayamos a la configuración de apache2 en `/etc/apache2`, revisando cada carpeta encontramos dentro de `/sites-enabled` dos archivos y en uno de ellos.

![virtual_host_conf](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/virtual_host_conf.png)

Hay un **VirtualHost** corriendo sobre el **localhost** en el puerto **52846** en el que la información que esta alojando esta en **/var/www/internal** (que es la que vimos relacionada con `main.php`).

Así que acá ya cambia la cosa, podemos hacer una petición'on con *curL* sobre esa info.

![private_key_joanna](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/private_key_joanna.png)

Perfecto, siempre tuvimos la pista en frente... (**internal**)

Guardamos esa llave en un archivo. Intentamos conectarnos mediante la llave indicandole  `$ ssh -i file user@host` pero nos pide una password phrase para el **private key** que le estamos ingresando. 

Asi que debemos crackear mediante la llave la password del user :) Hay varias herramientas, usaremos [ssh2john.py](https://github.com/koboi137/john/blob/bionic/ssh2john.py) que efectivamente hace lo que necesitamos.

Al ejecutarlo obtenemos el hash que en este caso con `john` nos ayuda perfecto.

![ssh2john_and_john](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/ssh2john_and_john.png)

Obtenemos la password, intentando de nuevo la conexion, logramos entrar como **joanna**.

![sshconecttojoanna](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/sshconecttojoanna.png)

...

## Escalada de privilegios {#escalada-de-privilegios}

Listones, inicialmente tenemos la flag `user.txt`. Tambien tenemos permisos como administrador a traves del binario `/bin/nano` (que es un editor de texto) sobre el archivo **/opt/priv**, lo que quiere decir que todo lo que hagamos con ese archivo lo estaremos haciendo como root.

![sudo_binNano_optPriv](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/sudo_binNano_optPriv.png)

Buscando por internet nos encontramos con la herramienta [GTFOBins](https://gtfobins.github.io/gtfobins/nano/), que nos provee de una gran lista de como los binarios Unix pueden ser explotados, asi que busquemos algo sobre **nano**.

Nos dice que dentro de un archivo ejecutado por `nano` tenemos la opcion de ejecutar comandos oprimiendo `Ctrl R + Ctrl X`, aca podemos hacerlo de varias formas, obtener una Shell o simplemente eacribir los comandos y recibir la respuesta.

![nanocommandexecution](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/nanocommandexecution.png)

Para obtener una shell pondriamos, `reset; sh 1>&0 2>&0` y tendriamos una shell como root

![resetSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/resetSH.png)

O pasandole los comandos, nos imprimiria la respuesta en el mismo archivo **/opt/priv**.

![commandwithnano](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/commandwithnano.png)

Y vemos la flag del usuario `root`.

![headRoot_txt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/openadmin/headRoot_txt.png)