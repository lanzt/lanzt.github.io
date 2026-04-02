---
layout      : post
title       : "HackTheBox - Expressway"
author      : lanz
footer_image: assets/images/footer-card/linux-icon.png
footer_text : Linux
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-banner.png
category    : [ htb ]
tags        : [ ike, vpn, sudo, squid-cache, logs, hostnames ]
---
Entorno Linux nivel fácil. Movimientos con el protocolo **IKE**, credenciales volando, logs y hostnames.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-lab-information.png" style="width: 100%;"/>

**💥 Laboratorio creado por**: [dakkmaddy](https://app.hackthebox.com/profile/17571).

## TL;DR (Spanish writeup)

La seguridad ante todo, ¿si oke?

Vamos a encontrar el servicio **IKE** expuesto, nos adentraremos en su mundo agresivamente para obtener un usuario y romper la llave compartida **PSK**, en conjunto formaremos unas credenciales y las usaremos para obtener una sesión como el usuario `ike` en el sistema.

Internamente encontraremos unos archivos de `squid` y dentro de uno de ellos un subdominio. Jugando con permisos y hostnames, encontraremos accesos administrativos en el sistema.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-statistics.png" style="width: 80%;"/>

Debemos ensuciarnos las manos y enumerar un montón.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Los pergaminos.

1. [Reconocimiento](#reconocimiento)
2. [Enumeración](#enumeracion)
  * [¿IKE?](#enumeracion-puerto-udp-500)
3. [Explotación](#explotacion)
  * [¿Rompemos OKE?](#explotacion-ike)
  * [Agresivamente, nos robamos cosas](#explotacion-psk-crack)
4. [Escalada de privilegios](#escalada)
  * [Cache-ando y log-eando](#escalada-squid-logs)
  * [¿Sudas?](#escalada-sudos)
5. [Post-Explotación](#post-explotacion)

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Empezamos como siempre, descubriendo que servicios (puertos) tiene expuestos la máquina que vamos a atacar, para ello usamos la herramienta `nmap`:

```bash
nmap -p- --open -v 10.129.134.213 -oA tcp-all-htb_expressway
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

El escaneo solo nos devuelve el puerto `22`:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |

Pero tener solo este puerto es raro, ya que si no encontramos una vulnerabilidad específica para ese SSH o realizamos brute-force (y eso que aún no tenemos usuarios válidos) de credenciales, pues no hay pa donde darle más.

Eso me hizo pensar en que acabamos de hacer un escaneo [TCP](https://protonvpn.com/support/udp-tcp), pero y si hacemos uno [UDP](https://protonvpn.com/support/udp-tcp)? A ver...

> Los protocolos **TCP** y **UDP** estan encargados de transportar información mediante la red, el tema es que **TCP** busca mover la info de forma clara y sin errores, con **UDP** es lo contrario, ahí se busca rapidez sin importar la integridad de la información (entre otras muchas más caracteristicas).

Apoyados de `nmap` también podemos realizar ese escaneo:

```bash
sudo nmap -sU -p- --open -v --min-rate=5000 10.129.134.213 -oA udp-all-htb_expressway
```

| Parámetro | Descripción |
| --------- | :---------- |
| -sU        | Indicamos que queremos un escaneo por UDP |
| --min-rate | Este escaneo es lento, con esto podemos indicarle cuantos paquetes enviar por petición |

Obtenemos nueva infoooooooooo:

| Puerto | Descripción |
| ------ | :---------- |
| 500    | **[IKE](https://www.quora.com/What-is-the-UDP-500-used-for)**: Servicio que permite establecer conexiones VPN de forma segura |
| 53553  | **no lo sabemos con seguridad** |

Ihsss, lindo, ahora si tenemos de donde empezar a cocinar.

# Enumeración [#](#enumeracion) {#enumeracion}

## ¿IKE? [📌](#enumeracion-puerto-udp-500) {#enumeracion-puerto-udp-500}

Como ya vimos, es un protocolo que permite una conexión segura entre redes virtuales privadas (**VPN**):

* [https://www.quora.com/What-is-the-UDP-500-used-for](https://www.quora.com/What-is-the-UDP-500-used-for)
* [https://www.cbtnuggets.com/common-ports/what-is-port-500](https://www.cbtnuggets.com/common-ports/what-is-port-500)
* [CISCO - Comprensión del protocolo IPsec IKEv1 (completísimo, te recomiendo leerlo)](https://www.cisco.com/c/es_mx/support/docs/security-vpn/ipsec-negotiation-ike-protocols/217432-understand-ipsec-ikev1-protocol.html)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-ipsec-ike.png" style="width: 100%;"/>

Nos ponemos a investigar, a ver como podemos jugar...

# Explotación [#](#explotacion) {#explotacion}

## ¿IKE? ¿Rompemos o ke? [📌](#explotacion-ike) {#explotacion-ike}

Llegamos a esta gran guía:

* [Pentesting VPN's](https://www.packtpub.com/en-pl/product/kali-linux-an-ethical-hackers-cookbook-9781787121829/chapter/kali-an-introduction-1/section/pentesting-vpns-ike-scan-ch01lvl1sec10?srsltid=AfmBOoomNQQKuscbAGy9-QW9EtEdf5nRCMaV7yl_WX8DSd7ujxyddF1z)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-ike-methods.png" style="width: 100%;"/>

Como vemos, el protocolo **IKE** inicialmente tiene dos fases, la primera es para establecer la conexión segura y la segunda es para empezar a transportar la información, en la primera fase se usan dos métodos para el intercambio de llaves, el modo **principal** y el modo **agresivo**, la guía explorara el modo ***agresivo***.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-ike-methods-main-and-aggresive.png" style="width: 100%;"/>

* [IKE Modes (Phase 1)](https://www.cisco.com/c/en/us/support/docs/security-vpn/ipsec-negotiation-ike-protocols/217432-understand-ipsec-ikev1-protocol.html#toc-hId--390876093)

Como notamos, el modo agresivo intenta responder con una llave compartida y otros datos para la generación de la sesión. Nuestro enfoque será intentar obtener esa llave y si esta no es robusta, obtener el resultado en texto plano de ella.

Explorando sobre esa llave, encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-ike-psk.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-ike-aggresive.png" style="width: 100%;"/>

Así que con más razón vamos tras ella.

Lo primero que nos indica la guía es instalar la herramienta [ike-scan](https://github.com/royhills/ike-scan) para descubrir más información del servicio y en pasos posteriores intentar extraer la llave:

```bash
./ike-scan 10.129.134.213 -M -A
```

> `-M` para que nos imprima la información en varias lineas y `-A` para que use el modo agresivo

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-bash-ikescan-aggresive.png" style="width: 100%;"/>

```bash
10.129.134.213  Aggressive Mode Handshake returned
        HDR=(CKY-R=306bd5ea590fe122)
        SA=(Enc=3DES Hash=SHA1 Group=2:modp1024 Auth=PSK LifeType=Seconds LifeDuration=28800)
        KeyExchange(128 bytes)
        Nonce(32 bytes)
        ID(Type=ID_USER_FQDN, Value=ike@expressway.htb)
        VID=09002689dfd6b712
        VID=afcad71368a1f1c96b8696fc77570100
        Hash(20 bytes)
```

Vemos que efectivamente existe un hash en formato **SHA1** y también obtenemos el usuario `ike`.

## Agresivamente, nos robamos cosas [📌](#explotacion-psk-crack) {#explotacion-psk-crack}

Guardamos el hash en un archivo:

```bash
./ike-scan/ike-scan 10.129.134.213 -A --pskcrack --pskcrack=ike.psk
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-bash-psk-hash-in-file.png" style="width: 100%;"/>

Ahora la idea es usar la herramienta **psk-crack** para intentar descubrir el valor en texto plano del hash, si la herramienta genera un hash idéntico al que tenemos, ya tendríamos el origen del hash:

```bash
./ike-scan/psk-crack -d /usr/share/wordlists/rockyou.txt ike.psk
```

> Con `-d` le indicamos el diccionario de palabras para que la herramienta vaya probando y generando los hashes

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-bash-pskcrack-ike-result.png" style="width: 100%;"/>

```txt
key "freakingrockstarontheroad" matches SHA1 hash f27f15b6c4bdabb8aaf1db91549079c72c734f9d
```

¡OBTENEMOS EL VALOOOOOOR!!!

Ya con eso, lo único que se nos ocurre es pensar en el servicio **SSH**, ya que tenemos un usuario y el resultado de una llave, quizá ese usuario usó ese valor como credencial:

```bash
ike : freakingrockstarontheroad
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike.png" style="width: 100%;"/>

Tamoooos dentrooo (:)

# Escalada de privilegios [#](#escalada) {#escalada}

Despues de probar demasiadas cosas (enserio, muchas) y perderme en temas relacionados a **squid** (ya hablaremos de esto), **tftp**, **capabilities**, logs y otras, encontramos el camino...

## Cache-ando y log-eando [📌](#escalada-squid-logs) {#escalada-squid-logs}

Estos son los grupos que tiene asignados el usuario `ike`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-id.png" style="width: 100%;"/>

El grupo `proxy` es distinto a lo normal, buscando archivos relacionados a ese grupo (a los cuales **ike** tendría acceso) encontramos:

```bash
find / -group proxy -ls 2>/dev/null
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-find-group-proxy.png" style="width: 100%;"/>

Jmm, archivos relacionados con el servicio [Squid](https://www.squid-cache.org/), el cual actúa como un proxy enfocado en temas de caché. Si recorremos los archivos, existe un log en el que alguien intentó acceder a un subdominio:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-cat-squid-access-subdomain-found.png" style="width: 100%;"/>

¿Lo encontraste?

```txt
offramp.expressway.htb
```

Y acá fue donde me re perdí y me puse a divagar :P Es que pensé, "pues tengo un subdominio, pero no tengo un sitio web, ¿qué hagooooo?", y lo que hice fue perderme fklasdjfl, pero bueno...

Una vez tenemos el subdominio, nos lo guardamos, es info importante, pero aún no lo sabemos ;)

## ¿Sudas? [📌](#escalada-sudos) {#escalada-sudos}

Siguiendo con mis pruebas, se me hizo raro encontrar dos objetos [sudo](https://phoenixnap.com/kb/linux-sudo) en el sistema (que nos permite ejecutar acciones privilegiadas sobre otros usuarios):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-echo-path.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-ls-local-bin.png" style="width: 100%;"/>

Pero es que el sistema por default ya tiene uno en la ruta `/usr/bin/sudo`, si revisamos, son versiones distintas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-sudos-version.png" style="width: 100%;"/>

:O

Esto me pone a dudar y me lleva a buscar posibles vulnerabilidades relacionadas con la versión más vieja, encontramos:

* [https://nvd.nist.gov/vuln/detail/CVE-2025-32462](https://nvd.nist.gov/vuln/detail/CVE-2025-32462)
* [CVE-2025–32462: How a 12-Year-Old Sudo Bug Lets You Become Root Where You Shouldn’t](https://medium.com/@mhdg./cve-2025-32462-how-a-12-year-old-sudo-bug-lets-you-become-root-where-you-shouldnt-780699101736)

Un bug para bypasear restricciones relacionadas con **hostnames**, o sea, si tenemos (por ejemplo) estos dos **hostnames**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-google-sudos-hostnames.png" style="width: 100%;"/>

En la vuln, un usuario podría ejecutar comandos en `prod-server` pretendiendo estar en `dev-server`.

Solo queeeeeeeee, en lugar de enfocarnos en la vuln, nos enfocamos en el tema "**hostnames**", ya que está interesante y es algo que no había probado y realmente no sabía.

Previamente, encontramos el **subdominio** `offramp.expressway.htb` y ahora estamos sobre `expressway.htb`, ejecutando `sudo -l` contra `expressway.htb` para ver si tenemos permisos sobre otros usuarios, el sistema responde que no señorito. PEEEEERO, llegó el gran PERO, ¿y si probamos contra el subdominio (como si fuera un hostname)?

```bash
/usr/local/bin/sudo -l -h offramp.expressway.htb
/usr/bin/sudo -l -h offramp.expressway.htb
sudo -l -h offramp.expressway.htb
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-sudo-l-offramp-hostname.png" style="width: 100%;"/>

JAAAAY!!! ¡Nuestro subdominio era un hostname y tenemos permisos de ejecución total sobre ese hostname como cualquier usuariooooooOOOOOO!

Levantemos una terminal como `root`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-ssh-ike-sudo-su-offramp-hostname.png" style="width: 100%;"/>

Y tamos finos :P

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/expressway/htbEXPRESSWAY-flags.png" style="width: 100%;"/>

...

Listones, una máquina sencilla, pero que puede llegar a ser locura. Me gustó el tema de **IKE** y su seguridad, el meternos en el tema y aprender.

Por ahora es todo, nos leeremos otro día, muchas gracias 💖

Abrazoooooos y a seguir rompiendo de todooooo!!