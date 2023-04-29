---
layout      : post
title       : "HackTheBox - Ambassador"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499banner.png
category    : [ htb ]
tags        : [ path-traversal, Consul, Grafana ]
---
Máquina Linux nivel medio. **Path Traversal** con `Grafana` y sus plugins, credenciales volando y unas verificaciones (**checks**) con el servicio `Consul` algo peligrosas.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499ambassadorHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [DirectRoot](https://www.hackthebox.eu/profile/24906).

No se pivotea, pero se salta.

Vamos a encontrar un servicio web en el puerto **3000** ejecutando el software `Grafana`, así mismo la máquina tiene expuesto el servicio `MySQL`. 

La versión del **grafana** es vulnerable a `Path Traversal` mediante plugins, buscaremos archivos relacionados con **grafana** para llegar a unas credenciales de **MySQL**, investigando nuevas bases de datos, llegaremos a otras credenciales con las cuales generaremos una sesión en el sistema como el usuario `developer`.

Estando dentro nos encontraremos con el servicio `Consul` y la posibilidad de crear objetos de configuración que sean ejecutados por el propio **Consul**. Apoyados en la documentación jugaremos con el feature `checks` para explotar un RCE mediante la validación de scrips en configuraciones maliciosas. Con esto obtendremos una terminal como el usuario `root`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499rating.png" style="width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499statistics.png" style="width: 80%;"/>

Vulns reales, pero complementadas no son tan reales. Vamos directicos!

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

STOOR.

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
  * [Visitando el puerto 80](#puerto-80).
  * [Visitando el puerto 3000](#puerto-3000).
3. [Explotación](#explotacion).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Como siempre necesitamos saber qué servicios (puertos) está ofreciendo el host, usaré `nmap` para ello:

```bash
nmap -p- --open -v 10.10.11.183 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos estos puertos abiertos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Permite obtener una terminal de forma segura. |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Permite visualizar un servidor web. |
| 3000   | No sabemos aún, pero posiblemente sea un servidor web (es comúnmente usado para ello). |
| 3306   | **[MySQL Server](https://searchnetworking.techtarget.com/definition/port-80)**: Curioso, permite interactuar con el gestor de bases de datos **MySQL**. |

**+ ~ +(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos puertos), pero si tuviéramos varios evitamos tener que escribirlos uno a uno**
 
```bash
[*] Extracting information...

    [*] IP Address: 10.10.11.183
    [*] Open ports: 22,80,3000,3306

[*] Ports copied to clipboard
```

**)+ ~ +**

Ya teniendo los puertos vamos a apoyarnos de **nmap** para profundizar un poco más, intentaremos ver que versión de software está siendo ejecutada y ejecutar unos scripts que tiene por default para ver si nos encuentra cositas llamativas...

```bash
nmap -p 22,80,3000,3306 -sCV 10.10.11.183 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Encontramos relevancia en:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.5 |
| 80     | HTTP     | Apache httpd 2.4.41 |
| 3000   | No sabo  | peeeero |

* Vemos cabeceras usadas en peticiones **web**, así que es un servicio **HTTP**.

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 3306   | mysql    | MySQL 8.0.30-0ubuntu0.20.04.2 |

* Esto es interesante y raro, no es común, hay que estar atentos a ver cuando usarlo...

Eso es todo lo que obtenemos de los escaneos, de a poco obtenemos info, por ahora empecemos a jugar y a recorrer la máquina.

# Enumeración [#](#enumeracion) {#enumeracion}

---

## Visitando el puerto 80 [📌](#puerto-80) {#puerto-80}

Inicialmente obtenemos esta vista:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499page80.png" style="width: 100%;"/>

En el enunciado hay texto llamativo:

> "When you start as a developer at Ambassador, you will be assigned a development server of your own to use." "Connecting to this machine" using "the **developer** account to **SSH**, **DevOps** will give you the **password**."

Nos indica que tendremos acceso a un servidor de desarrollo propio ingresando como el usuario `developer` mediante **SSH**, peeeero que la contraseña nos la brindara el departamento (o quizás el usuario) de **DevOps**... Así que tenemos algo, pero no tenemos mucho. Hay que averiguar a que se refieren con **devops**.

Con este puerto no encontramos nada más llamativo.

## Visitando el puerto 3000 [📌](#puerto-3000) {#puerto-3000}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499page3000.png" style="width: 100%;"/>

Un software llamado **Grafana** en su versión `8.2.0`:

> 📊 "Grafana is a multi-platform open source analytics and interactive visualization web application. **It provides charts, graphs, and alerts** for the web when connected to supported data sources." ~ [Grafana](https://grafana.com/).

Probando credenciales por default no logramos nada, por lo que empezamos a buscar posibles vulns relacionadas con esa versión...

# Explotación [#](#explotacion) {#explotacion}

Y sí, llegamos a un [repo de **Github**](https://github.com/pedrohavay/exploit-grafana-CVE-2021-43798) referenciando el CVE [CVE-2021-43798](https://nvd.nist.gov/vuln/detail/CVE-2021-43798):

> Esta vulnerabilidad aprovecha el mal uso de **plugins** y rutas de la web para explotar un [Path Traversal](https://www.acunetix.com/blog/articles/path-traversal/), permitiendo que un usuario interactue con directorios distintos a los que tiene permitidos, logrando así descubrir archivos y rutas del sistema.

Les dejo un [post con la explicación completa y detallada del como encontraron este **0day**](https://j0vsec.com/post/cve-2021-43798/) en su momento.

... Sigamos ... 

Clonamos el repositorio, instalamos los requerimientos, modificamos el objeto `targets.txt` agregando la URL del sitio donde está **Grafana** y ejecutamos el archivo `exploit.py`:

```bash
 cat targets.txt 
http://10.10.11.183:3000
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_PYexp_grafanaLFI.png" style="width: 100%;"/>

Opaaaa, parece que encontró un **plugin** vulnerable (`alertlist`) con este payload: 

```bash
http://10.10.11.183:3000/public/plugins/alertlist/..%2f..%2f..%2f..%2f..%2f..%2f..%2f..%2fARCHIVO_PARA_LFI
```

Entre sus pruebas nos extrae algunos archivos del sistema y los guarda en la carpeta `./http_10_10_11_183_3000`:

```bash
 tree http_10_10_11_183_3000 
http_10_10_11_183_3000
├── cmdline
├── defaults.ini
├── grafana.db
├── grafana.ini
└── passwd
```

Revisando el objeto donde se alojan los usuarios del sistema (`/etc/passwd` o en este caso `passwd`) notamos cositas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_cat_grafanaLFI_passwd.png" style="width: 80%;"/>

* Encontramos al usuario `developer`.
* Hay otro usuario con ruta en `/home` (pero no tiene acceso por terminal, esto es raro).
* Y que los únicos usuarios que disponen de una terminal son **developer** y **root**.

Revisando los demás objetos de **grafana** encontramos también cositas en `defaults.ini` y `grafana.ini`:

**📈 <u>defaults.ini</u>**:

Vemos unas credenciales (que claramente ya probamos mucho antes y no fueron válidas) y un **secret key** usado posiblemente para firmar las cookies o algo parecido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_cat_grafanaLFI_defaultsINI_userANDpassword.png" style="width: 100%;"/>

**📈 <u>grafana.ini</u>**:

Este objeto tiene la misma info que el anterior, solo que en lugar de la contraseña por default tiene una custom:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_cat_grafanaLFI_grafanaINI_newPassword.png" style="width: 100%;"/>

Esto es llamativo, la tomamos, la guardamos en nuestras notas yyyy nos vamos al login de **grafana** a probar el acceso al usuario **admin** con esa pw...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499page3000_dashboard.png" style="width: 100%;"/>

TAMOS DENTRO ÑAÑAIIII!

> Esas credenciales no nos sirven contra **SSH** y buscando llaves privadas u objetos con contraseñas tampoco llegamos a ningún lado (tampoco vemos nada en el archivo `.db` encontrado con el LFI).

Recorriendo el sitio notamos en la configuración una referencia a un archivo `.yaml` de **MySQL**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499page3000_configuration_mysqlYAML_reference.png" style="width: 90%;"/>

Y si le damos click nos indica que posiblemente tenga credenciales (pueda que no, pero "piense que sí, paisita"):

> Tambien es llamativo ya que la máquina tiene el servicio **MySQL** expuesto, así que si obtenemos credenciales las podemos usar a ver si son validas.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499page3000_datasource_mysqlYAML.png" style="width: 90%;"/>

> Los **data sources** son conexiones que usa **Grafana** para obtener la información a analizar: [Grafana Data Sources](https://www.metricfire.com/blog/grafana-data-sources/).

Se me ocurre que quizás debamos buscar ese archivo mediante el **LFI** (si es que existe 🥵). Voy a dar unas vueltas más por el sitio y si no hay nada vuelvo y empezamos a buscar ese archivo.

> Pos no hay nada más llamativo, así que a darle (:

Para no hacer fuzzeos ahí a lo loco sobre `/etc/grafana` (el exploit que usamos busca y encuentra varios objetos ahí) recorrí la web obteniendo rutas en donde se alojen esos archivos `.yaml`, encontramos en su documentación un **guiño**:

* [Data sources](https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources).

> It's possible to manage data sources in **Grafana** by adding one or more **YAML config files** in the `provisioning/datasources` directory.

Por lo que podemos pensar algo tal que así:

```bash
/etc/grafana/provisioning/datasources/mysql.yaml
```

Si ejecutamos una petición buscando ese archivooooooo (creamos un script sencillito o con **cURL**):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_curl_grafanaLFI_datasource_mysqlYAML.png" style="width: 100%;"/>

AJAAAAAAAAAAAAAAAAAAAAI! Tenemos el archivo y efectivamente trae unas credenciales... Pues a reciclar (es algo que siempre -SIEMPRE- debemos hacer) contra **SSH** y claramente contra **MySQL**, puede que sirvan de algo...

```bash
mysql -u grafana -p -h 10.10.11.183
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_mysql_remoteConnection.png" style="width: 90%;"/>

Y son validaaaaaaaaaaaaaaas! Pues enumeremos... Veamos las bases de datos:

```sql
mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| grafana            |
| information_schema |
| mysql              |
| performance_schema |
| sys                |
| whackywidget       |
+--------------------+
```

Están las que se generan con **MySQL**, la de **grafana** con la cual ya jugamos y hay una nueva: `whackywidget`, veamos sus tablas:

```sql
mysql> use whackywidget;
mysql> show tables;
+------------------------+
| Tables_in_whackywidget |
+------------------------+
| users                  |
+------------------------+
```

Solo existe una tabla llamada **users**, pues veamos su contenido:

```sql
mysql> SELECT * FROM users;
+-----------+------------------------------------------+
| user      | pass                                     |
+-----------+------------------------------------------+
| developer | YW5FbmdsaXNoTWFuSW5OZXdZb3JrMDI3NDY4Cg== |
+-----------+------------------------------------------+
```

Uhhhh, el usuario `developer` del que nos habló el sitio web yyyy tiene una contraseña que parece estar encodeada en **base64**, si intentamos decodearla obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_base64_decodeDeveloperPassword.png" style="width: 80%;"/>

Efectivamente estaba codificadoooooo. Ya que tenemos en mente que nos habían hablado del usuario `developer` y una conexión `SSH`, probemos con estas nuevas creds:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_ssh_developerSH.png" style="width: 90%;"/>

UJUJUUUUPAAAAA! Obtenemos una terminal en el sistemaaaaaaaaaaaaaaaa (: Pues a escalar esta vaina...

> Les dejo este post donde nos indica que en el archivo `.db` tambien estaba el contenido del objeto `mysql.yaml`: [Grafana 8.3.0 – Directory Traversal and Arbitrary File Read](https://vk9-sec.com/grafana-8-3-0-directory-traversal-and-arbitrary-file-read-cve-2021-43798/).

---

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Como primer dato, estos serian los grupos a los que está asignado el usuario:

```bash
developer@ambassador:/etc/consul.d$ id
uid=1000(developer) gid=1000(developer) groups=1000(developer)
```

Revisando en el sistema los objetos asociados al grupo `developer` encontramos uno juguetón:

```bash
developer@ambassador:~$ find / -group developer 2>/dev/null | grep -vE "proc|run|sys"
/etc/consul.d/config.d
...
```

Existe interacción alguna con la carpeta `config.d` en la ruta `/etc/consul.d`, revisemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_developerSH_lsLA_etcConsuld.png" style="width: 80%;"/>

Ahí lo vemos, todo el que este asignado al grupo `developer` tiene acceso de **escritura y ejecución** sobre la carpeta `/etc/consul.d/config.d` (además el owner es **root**), bieeeeen llamativo esto...

Está claro que debemos escribir algo en ese directorio (o si no para qué existe ese acceso raro) y además buscando entre las operaciones de inicio con el sistema ([systemd](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files)) encontramos una relacionada con **consul** (que es el nombre de la carpeta donde está la configuración rara, por lo que pueda que el servicio se llame **consul**):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_developerSH_cat_systemdConsulService.png" style="width: 100%;"/>

Y si prestamos atención sabemos dos cosas:

1. El servicio está siendo ejecutado por el usuario `root` (así que si lo explotamooooos...).
2. El sistema ejecuta un **agente** (?) y obtiene su configuración de la carpeta a la que tenemos acceso y/u otro objeto.

Averigüemos de que se trata este servicio.

## ¿Consultamos? [📌](#consul) {#consul}

> Según su [propia documentación](https://developer.hashicorp.com/consul/docs/intro), **Consul** en pocas palabras es una solución de red que permite asegurar la conexión entre servicios, entornos y ejecuciones.

> Y un agente: "The **agent** maintains membership information, registers services, runs checks, responds to queries, and more." ~ [Agents Overview](https://developer.hashicorp.com/consul/docs/agent).

Así que un agente es el jefesito, me gusta.

Revisemos a ver de que nos podemos aprovechar o si hay alguna manera de indicar en la configuración que ejecute código o algo así.

...

Para no hacer largo el writeup caí en un **rabbithole** por no leer bien y prestar atención, aunque bueno, aprendí cositas relacionadas con los `checks` y abrí los ojos:

> Pa que sepan: Los `checks` **basicamente es gestionar que un servicio este "vivo" (activo) constantemente, o en tal caso revisar que toodo el nodo lo este (un servicio puede estar dentro de nodos, como pueda que no)**. Esto segùn [Health Checks](https://developer.hashicorp.com/consul/docs/discovery/checks).

...

Si abrimos bien los ojos en varias partes de la documentación nos muestra este <span style="color: yellow;">Warning</span>:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499google_consulDoc_warningRCE.png" style="width: 100%;"/>

El tema es que aparentemente tenían una vulnerabilidad que no importaba que `script` **(por ejemplo, podríamos ingresar cualquier objeto o script del sistema tomando como base esto:**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499google_consulDoc_checks_scriptExample.png" style="width: 100%;"/>

**)** se creará, el `check` lo "validaría" y, por lo tanto, lo ejecutaría, consiguiendo así que si alguien tenía acceso mal intencionado a la configuración pudiera lanzar código remotamente 😯

* [Protecting Consul from RCE Risk in Specific Configurations](https://www.hashicorp.com/blog/protecting-consul-from-rce-risk-in-specific-configurations).

Como tal, la vuln es sencilla de entender: Los **script checks** ejecutan cualquier comando o -script- alojado en alguna configuración, (esa característica no está activada por default) por lo que si se cumplen estos tres ítems se podrá usar ese **check** para ejecutar código malicioso:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499google_consulBlog_conditionsConsulRCE.png" style="width: 80%;"/>

* No sabemos nada aún de la **API**, pero [acá](https://developer.hashicorp.com/consul/docs/install/ports) nos dice que se encuentra en el puerto `8500` yyyy:
  
  ```bash
  developer@ambassador:/etc/consul.d$ netstat -lna | grep 8500
  tcp        0      0 127.0.0.1:8500          0.0.0.0:*               LISTEN
  ```

  ```bash
  developer@ambassador:/etc/consul.d$ curl http://localhost:8500
  Consul Agent: UI disabled. To enable, set ui_config.enabled=true in the agent configuration and restart.
  ```

  No tenemos **UI** (interfaz de usuario), peeero si nos responde la **API**, así que finos.

* Podemos pensar que están habilitados los script checks.
* Y también que la ACL está mal configurada.

Finalmente nos confirman lo que pensamos arriba:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499google_consulBlog_withConditionsIsValidRCE.png" style="width: 80%;"/>

🤗 Vueno baztante testo, a travajar...

Buscando exploits en internet caí en este del panita [sha16](https://www.youtube.com/@sha16) (cáiganle a sus videos y suscríbansele) (gracias por aportar rey):

* [https://github.com/sha-16/HashiCorp-Consul-RCE/blob/main/consul_rce.py](https://github.com/sha-16/HashiCorp-Consul-RCE/blob/main/consul_rce.py)

En él hace lo que indicamos, crea (registra) el agente, la configuración, lo que permitirá en generar una reverse shell con **netcat** y por último borra el agente registrado. Todo mediante la **API** alojada en el puerto `8500`, así que lo subimos a la máquina, modificamos las variables que toma dentro del script (ips y puertos) yyyy nos ponemos en escucha (yo usaré el puerto **4433** para obtener (en dado caso) la reverse shell):

```bash
nc -lvp 4433
```

Ejecutamos el script yyyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499bash_developerSH_PY_consulAgentRCE_done_rootRevSH.png" style="width: 100%;"/>

EL AGENTE NOS ENTREGÓ UNA TERMINAL COMO EL USUARIO `ROOT`!!! ([Hagámosla linda](https://lanzt.gitbook.io/cheatsheet-pentest/tty) y veamos las flags):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ambassador/499flags.png" style="width: 100%;"/>

...

Una máquina con pasos interesantes, me gusto que tiene vulnerabilidades reales, la concatenación de ellas en un solo entorno no es tan real, peeero aun así me gustó. Además, conocí varios servicios que a futuro pueden estar juguetones.

Por ahorita no es más, solo aprender y aprender (: Nos vamos charlando y a ROMPER DE TODOOOOOOO!