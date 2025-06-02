---
layout      : post
title       : "HackTheBox - UnderPass"
author      : lanz
footer_image: assets/images/footer-card/linux-icon.png
footer_text : Linux
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-banner.png
category    : [ htb ]
tags        : [ sudo, mosh, daloRADIUS, cracking, snmp ]
---
Entorno Linux nivel fácil. Jugueteo con **SNMP**, debemos ampliar el radio con **daloRADIUS**, algunas credenciales por ahí descansando y juegos de sesiones con `mosh`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-lab-information.png" style="width: 100%;"/>

**💥 Laboratorio creado por**: [dakkmaddy](https://app.hackthebox.com/profile/17571)

## TL;DR (Spanish writeup)

Hay que ampliar la búsqueda, hasta debajo del colchón.

Vamos a jugar con el servicio `SNMP`, extraeremos información relacionada con el servidor `daloRADIUS`. Usando la web encontraremos varias rutas y unas credenciales por default, con ellas nos convertiremos en el `administrator` de los operadores. Crackearemos una contraseña hasheada que está en la config interna del sitio, usando la contraseña en texto plano, podremos acceder mediante `SSH` al sistema como el usuario `svcMosh`. Finalmente, aprovecharemos que este usuario tiene el permiso de ejecutar como cualquier otro usuario el servicio `mosh`, lo usaremos para generar una sesión como `root`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-statistics.png" style="width: 80%;"/>

No tan juguetona y con temas más o menos reales.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

¡Gran Pecador!

1. [Reconocimiento](#reconocimiento)
2. [Enumeración](#enumeracion)
  * [Revisando el servicio web](#enumeracion-puerto-80)
  * [Revisando el servicio SNMP](#enumeracion-puerto-udp-161)
3. ["Explotación"](#explotacion)
  * [Daloradius?](#enumeracion-daloradius)
  * [Encontrando más credenciales](#explotacion-cracking-md5)
4. [Escalada de privilegios](#escalada-de-privilegios)
5. [Post-Explotación](#post-explotacion)

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Como siempre vamos a empezar descubriendo los servicios (puertos) que tiene expuestos la máquina, para eso usaremos la herramienta `nmap`:

```bash
nmap -p- --open -v 10.10.11.48 -oA tcp-portscan-underpass
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

El escaneo nos devuelve:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servicio para interactuar con un servidor web |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> `extractPorts tcp-portscan-underpass.gnmap`

Ahora que tenemos los puertos, vamos a profundizar un poco con ayuda de `nmap`, le pediremos que intente extraer información del software usado y que use algunos scripts que tiene por default, a ver si nos extrae más cositas:

```bash
nmap -sCV -p 22,80 10.10.11.48 -oA tcp-vvvscan-underpass
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Indicamos a qué puertos queremos realizar el escaneo |
| -sC       | Ejecuta scripts predefinidos contra cada servicio |
| -sV       | Intenta extraer la versión del servicio |

Y finalmente obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.9p1 Ubuntu 3ubuntu0.10 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | Apache httpd 2.4.52 ((Ubuntu)) |

Y no más por este lado... PEEERO apoyados de nuestro escaneo contra el protocolo [UDP](https://www.redeszone.net/tutoriales/internet/tcp-udp-caracteristicas-uso-diferencias/) (lo anterior fue contra el protocolo [TCP](https://www.redeszone.net/tutoriales/internet/tcp-udp-caracteristicas-uso-diferencias/)) también encontramos cositas:

```bash
sudo nmap -sU -p- --open -v 10.10.11.48 --min-rate=2000 -oA udp-portscan-underpass
```

| Argumento | Descripción |
| :-------- | :---------- |
| -sU       | Le indicamos que únicamente queremos descubrir puertos UDP. |
| –min-rate | (Para casos en los que el escaneo va lento) Envía X cantidad de paquetes por cada petición. |

Y nos entrega:

| Puerto | Descripción |
| ------ | :---------- |
| 161    | **[SNMP](https://www.fortinet.com/lat/resources/cyberglossary/simple-network-management-protocol#:~:text=SNMP%20pertenece%20a%20la%20familia,con%20un%20agente%20SNMP%20integrado.)** |

Bien bien, redes y más redes, ahora pidamos de nuevo a `nmap` que nos ayude a extraer más info:

```bash
sudo nmap -sU -p 161 10.10.11.48 --min-rate=2000 -oA udp-vvvscan-underpass
```

Yyy:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 161    | SNMP     | SNMPv1 server; net-snmp SNMPv3 server (public) |

Ujuu, tiene la comunidad `public` activa, no te preocupes que si es necesario (lo es), te explicaré esto más adelante.

Por ahora estamos listos, démosle...

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Revisando el servicio web [📌](#enumeracion-puerto-80) {#enumeracion-puerto-80}

Lo primero que recibimos al visitar el sitio web es:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80.png" style="width: 100%;"/>

La página por default de Apache. Y nada más 🙃

Dando algunas vueltas por el sitio no llegamos a nada (ni jugando con `fuzzing` (para encontrar archivos que esté alojando el servidor y no los veamos), ni con la versión del Apache, ni con revisión de código, nada). Tampoco obtenemos nada por el lado del servicio `SSH`, quizá jugando con su versión para llegar a vulns, pero nada.

## Revisando el servicio SNMP [📌](#enumeracion-puerto-udp-161) {#enumeracion-puerto-udp-161}

Por lo que nos queda el contenido del protocolo **SNMP**, así que, rápidamente:

> 🥅 **[SNMP](https://es.wikipedia.org/wiki/Protocolo_simple_de_administraci%C3%B3n_de_red)** es un protocolo que permite administrar facilmente dispositivos de una red.

Con la info que nos extrajo `nmap`, vimos que tiene disponible la comunidad **public**, ¿qué significa esto?, una comunidad puede pensarse como una carpeta, por lo que es la forma con la cual **SNMP** logra enumerar y leer información de un servicio publicado.

La comunidad **public** viene por defecto con **SNMP**, depende del administrador desactivarla o asegurarla.

Si quieres profundizar te dejo excelentes recursos:

* [https://hacking-etico.com](https://hacking-etico.com/2014/03/27/leyendo-informacion-snmp-con-snmpwalk/)
* [https://book.hacktricks.wiki](https://book.hacktricks.wiki/en/network-services-pentesting/pentesting-snmp/index.html)

Para lidiar con este servicio podemos emplear varias herramientas, como: `snmp-check`, `snmpwalk` o `snmpbulkwalk` (que son las que yo he usado). Así que intentemos obtener información con la primera de ellas, debemos indicar la versión y la comunidad que queremos visitar:

```bash
snmp-check -v1 -c public 10.10.11.48
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-snmpcheck.png" style="width: 100%;"/>

Ujujuuui, detalles interesantes:

```bash
Un dominio: UnDerPass.htb
Un usuario: steve@underpass.htb
Info del SO: Linux 5.15.0-126-generic #136-Ubuntu
No sé: daloradius server?
```

Lo que más llama la atención es eso de **servidor daloradius**, no sé si sea real o si es una palabra random, pero buscando en internet:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-google-daloradius-server.png" style="width: 70%;"/>

Efectivamente existe :O [https://github.com/lirantal/daloradius](https://github.com/lirantal/daloradius).

Y como es algo real, podríamos intentar validar si existe como una aplicación en el servidor web:

```txt
http://10.10.11.48/daloradius
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80-daloradius.png" style="width: 100%;"/>

Ay, no tenemos permitido acceder a ese recurso, ¿peeeeeeero eso que te dice? SIII, LA CARPETA EXISTE!! Podríamos intentar jugar con **fuzzing** pa ver si encontramos algo dentro de la carpeta.

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/common.txt -u http://10.10.11.48/daloradius/FUZZ -mc all -fs 273
```

> Con `-mc` le indicamos que nos muestre todos los códigos de estado (200, 403, 404, etc) y con `-fs` evitamos que nos devuelve resultados con un tamaño igual a 273 (ya que son falsos positivos y nos generan ruido)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-ffuf-daloradius.png" style="width: 100%;"/>

Epale, tenemos info y comparándola con la que registra en su [GitHub](https://github.com/lirantal/daloradius) sabemos que es la misma y podemos apoyarnos del repositorio en lugar de estar **fuzzeando** (:

# "Explotación" [#](#explotacion) {#explotacion}

---

## Daloradius? [📌](#enumeracion-daloradius) {#enumeracion-daloradius}

Este software es una herramienta que permite controlar quién tiene acceso a nuestra red yyyy manejarlo todo visualmente, o sea, facilita la vida para aquellos que no disfrutan de usar una consola de comandos.

* [https://www.daloradius.com/](https://www.daloradius.com/)

Usando el repositorio, encontramos un login:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80-daloradius-users-login.png" style="width: 100%;"/>

A veces los servicios configuran credenciales por default, como `admin:admin` o `admin:s3cr3t`, probando por ese lado no logramos iniciar sesión.

Revisando los [issues](https://github.com/lirantal/daloradius/issues) del proyecto, encontramos uno relacionado:

[Default login creds not working](https://github.com/lirantal/daloradius/issues/573)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-github-daloradius-default-creds.png" style="width: 100%;"/>

Descubrimos las credenciales por default de `daloRADIUS`, el usuario usado es `administrator` y su contraseña es `radius`. Pero probándolas tampoco nos funcionan :/

Cambiando el enfoque nos ponemos a buscar vulnerabilidades que existan contra ese servicio, llegamos a esta:

* [dalorRadius XXS + CSRF to Full Account Take over](https://github.com/lirantal/daloradius/security/advisories/GHSA-c9xx-6mvw-9v84)

Upale, un control total de una cuenta, notamos que se hace uso del archivo `mng-del.php`, buscándolo en la estructura del repositorio, llegamos a él:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80-daloradius-operators-login.png" style="width: 100%;"/>

Otro login, ahora enfocado en operadores. ¿Y si probamos la credencial que tenemos de antes?

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80-daloradius-operators-home.png" style="width: 100%;"/>

JAAA! Tamos dentro y no necesitamos control sobre ninguna cuenta, ya que somos administradores (:

## Encontrando más credenciales [📌](#explotacion-cracking-md5) {#explotacion-cracking-md5}

Dando vueltas por el sitio, llegamos a una ruta de configuración de usuarios, encontramos un usuario y una contraseña hasheada:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-page80-daloradius-operators-mnglistall.png" style="width: 100%;"/>

Usando [haiti](https://github.com/noraj/haiti) tenemos la posibilidad de ver rápidamente qué tipo de algoritmo se ha usado contra una hash y cuáles son los formatos usados por las dos herramientas más comunes de crackeo de contraseñas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-haiti-md5-svcMosh.png" style="width: 100%;"/>

El más probable es [MD5](https://es.wikipedia.org/wiki/MD5), el cual es un algoritmo que solo se recomienda usar para integridad y no para autenticación (ya que es muuuuuuuuuuuuuy inseguro), así que, guardemos el hash en un archivo y usemos **John The Ripper** para intentar encontrarle una coincidencia jugando con el diccionario **rockyou.txt**:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5 svcMosh.hash
```

Y nos encuentra un match!!! Para ver el resultado podemos ejecutar:

```bash
john --show --format=Raw-MD5 svcMosh.hash
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-john-md5-svcMosh.png" style="width: 100%;"/>

Liiiistones, tenemos una contraseña en texto plano. Ya vimos en nuestro reconocimiento que existe el servicio **SSH** y si intentamos esas credencialeeeees:

```bash
ssh svcMosh@10.10.11.48
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-ssh-svcMosh.png" style="width: 100%;"/>

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Revisando que permisos tenemos como `svcMosh` sobre otros usuarios, vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-ssh-svcMosh-sudoL.png" style="width: 100%;"/>

Podemos ejecutar como cualquier usuario (y sin usar la contraseña que ya conocemos) el binario `/usr/bin/mosh-server`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-ssh-svcMosh-moshServer.png" style="width: 100%;"/>

Es un servidor :P que está ejecutando algo y lo está colocando en segundo plano (detached).

* [https://mosh.org/](https://mosh.org/)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-google-mosh.png" style="width: 100%;"/>

Es una herramienta que nos permite jugar con sesiones, con controles remotos y como dicen, es un reemplazo de **SSH**, así que lindo, pa tenerlo en mente.

Esto quiere decir que estamos creando "un acceso remoto" con el usuario `root` (por el `sudo` sin ninguna especificación de usuario), solo nos falta conocer como -acceder- a ese servidor.

Buscando un poco más llegamos a esta info que nos da pistas de como seguir:

* [mosh-server](https://man.archlinux.org/man/mosh-server.1.en)
* [mosh-client](https://man.archlinux.org/man/mosh-client.1.en)

Peeeero, usando el sitio oficial nos queda súúúúper claro todo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-google-mosh-server-client.png" style="width: 100%;"/>

Al ejecutar el servidor **mosh**, este nos va a mostrar una cadena rara y un puerto, esa cadena rara es una llave que necesita el cliente **mosh** como método de autorización, por lo que si ejecutamos el servidor:

```bash
svcMosh@underpass:~$ sudo /usr/bin/mosh-server
[...]
MOSH CONNECT 60001 47eyjFxHPJWfK0AI6dH6gQ
```

Si quisiéramos conectarnos a él mediante el cliente:

```bash
MOSH_KEY=47eyjFxHPJWfK0AI6dH6gQ mosh-client 10.10.11.48 60001
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-bash-ssh-svcMosh-moshClient.png" style="width: 100%;"/>

EEEEEEEEPALE, tamos dentro de la sesión como el usuario `root` :P

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/underpass/htb641-google-dancedancefunny.gif" style="width: 50%;"/>

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

---

```bash
svcMosh@underpass:~$ cat user.txt
781a36fdf02[...]
```

```bash
root@underpass:~# cat root.txt
bb532404ac6[...]
```

...

Una máquina tranquila, pero de esas que si pasas por alto el simple detalle de no escanear los servicios del protocolo **UDP**, uffff, ahí uno se queda sufriendo.

Entretenida, me gustó el conocer el servicio **mosh**, suena chévere.

Y nada, nos leeremos después, muchas gracias por pasarse y recuerden, a seguir rompiendo de TOOOOOODOOOO!! Abrazitos