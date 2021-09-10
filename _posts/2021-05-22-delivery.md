---
layout      : post 
title       : "HackTheBox - Delivery"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308banner.png
category    : [ htb ]
tags        : [ cracking, osticket, mattermost, rule-based-attack, ticket-support ]
---
Máquina Linux nivel fácil, jugaremos con **osTicket** creando tickets que nos servirán para ¿obtener emails externos en el propio status del ticket? ¿khE? (jajaj, sip), nos moveremos entre archivos y bases de datos **MySQL** y curiosamente usaremos las **reglas** para romper cosas con **HashCat** y **John The Ripper** :)

![308deliveryHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308deliveryHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [ippsec](https://www.hackthebox.eu/profile/3769). El master craster faster :D

Bueno bueno bueeeeno, encontraremos dos servicios, uno que nos permite generar tickets que serán enviados a una mesa de ayuda (software **osTicket**) y otro que nos permitirá comunicarnos con nuestros equipos de trabajo (software **Mattermost**)... Jugando con los dos, encontraremos que cuando generamos un ticket, crea un email asociado a ese ticket. Peeero que si validamos el status de ese ticket e interactuamos con ese email externamente, podremos llegar a obtener correos enviados a ese email en el **status** del ticket 🙃 Una vaina loca!

Apoyados en esto lograremos validar una cuenta creada en el servicio **Mattermost**, en el dashboard encontraremos un chat correspondiente a un equipo de trabajo, en esos mensajes tendremos unas credenciales, una referencia a reutilización de contraseñas y a reglas de hashcat. Las credenciales nos servirán para entrar al panel de control donde están todos los tickets y también nos permitirán obtener una sesión por medio de **SSH** como el usuario **maildeliverer** en la máquina.

Enumerando los directorios de los servicios web, encontramos en la raíz de **Mattermost** unas credenciales del usuario que mantiene la base de datos **MySQL**, recorreremos la base de datos **mattermost** para encontrar una contraseña encriptada en formato *bcrypt* asociada a un usuario llamado **root** del servicio web. 

Jugando con las reglas tanto de **hashcat** como de **john** lograremos crackear el hash del usuario **root**. Probando esa contraseña en el sistema contra el usuario **root** obtendremos una sesión como él.

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

Tonces!

1. [Enumeración](#enumeracion).
2. [Explotación](#explotacion).
3. [Escalada de privilegios](#escalada-de-privilegios).

...

## Enumeración [#](#enumeracion) {#enumeracion}

Hacemos un escaneo inicial para obtener los puertos abiertos y que servicios aparentemente estás corriendo sobre ellos:

```bash
ゝnmap -p- --open -v 10.10.10.222 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                      |
| --open     | Solo los puertos que están abiertos          |
| -v         | Permite ver en consola lo que va encontrando |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
ゝ cat initScan
# Nmap 7.80 scan initiated Tue Jan 12 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.222
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.222 () Status: Up
Host: 10.10.10.222 () Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 8065/open/tcp/////
# Nmap done at Tue Jan 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 126.12 seconds
```

Encontramos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://www.ssh.com/academy/ssh/port)**                 |
| 80     | **[HTTP](https://www.techopedia.com/definition/15709/port-80)** |
| 8065   | No sabemos aún |

Ahora validemos si existen versiones y scripts relacionados para esos servicios corriendo:

```bash
ゝ nmap -p 22,80,8065 -sC -sV 10.10.10.222 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
❭ cat portScan 
# Nmap 7.80 scan initiated Tue Jan 12 25:25:25 2021 as: nmap -p 22,80,8065 -sC -sV -oN portScan 10.10.10.222
Nmap scan report for 10.10.10.222
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.9p1 Debian 10+deb10u2 (protocol 2.0)
| ssh-hostkey: 
|   2048 9c:40:fa:85:9b:01:ac:ac:0e:bc:0c:19:51:8a:ee:27 (RSA)
|   256 5a:0c:c0:3b:9b:76:55:2e:6e:c4:f4:b9:5d:76:17:09 (ECDSA)
|_  256 b7:9d:f7:48:9d:a2:f2:76:30:fd:42:d3:35:3a:80:8c (ED25519)
80/tcp   open  http    nginx 1.14.2
|_http-server-header: nginx/1.14.2
|_http-title: Welcome
8065/tcp open  unknown
| fingerprint-strings: 
|   GenericLines, Help, RTSPRequest, SSLSessionReq, TerminalServerCookie: 
|     HTTP/1.1 400 Bad Request
|     Content-Type: text/plain; charset=utf-8
|     Connection: close
|     Request
|   GetRequest: 
|     HTTP/1.0 200 OK
|     Accept-Ranges: bytes
|     Cache-Control: no-cache, max-age=31556926, public
|     Content-Length: 3108
|     Content-Security-Policy: frame-ancestors 'self'; script-src 'self' cdn.rudderlabs.com
|     Content-Type: text/html; charset=utf-8
|     Last-Modified: Tue, 12 Jan 2021 14:01:26 GMT
|     X-Frame-Options: SAMEORIGIN
|     X-Request-Id: sjgqngc48j8m3j91o7tu3pyigy
|     X-Version-Id: 5.30.0.5.30.1.57fb31b889bf81d99d8af8176d4bbaaa.false
|     Date: Tue, 12 Jan 2021 15:16:24 GMT
|     <!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=0"><meta name="robots" content="noindex, nofollow"><meta name="referrer" content="no-referrer"><title>Mattermost</title><meta name="mobile-web-app-capable" content="yes"><meta name="application-name" content="Mattermost"><meta name="format-detection" content="telephone=no"><link re
|   HTTPOptions: 
|     HTTP/1.0 405 Method Not Allowed
|     Date: Tue, 12 Jan 2021 15:16:24 GMT
|_    Content-Length: 0
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port8065-TCP:V=7.80%I=7%D=1/12%Time=5FFDBB34%P=x86_64-pc-linux-gnu%r(Ge
SF:nericLines,67,"HTTP/1\.1..."
...
...
# Esto no es necesario, además lo quito por unos problemas que me da con la busqueda
...
...

Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Jan 12 25:25:25 2021 -- 1 IP address (1 host up) scanned in 113.07 seconds
```

Y ahora obtenemos las versiones:

| Puerto | Servicio | Versión |
| :----- | :------- | :------ |
| 22     | SSH      | OpenSSH 7.9p1 |
| 80     | HTTP     | nginx 1.14.2 |
| 8065   | HTTP     | unknown - Pero parece un servidor web |

Bueno, profundicemos en cada uno de ellos (:

...

### Puerto 80 - osTicket [⌖](#puerto-80) {#puerto-80}

![308page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80.png)

Un simple servicio web, si posicionamos el cursor sobre **HELPDESK**, vemos que nos redirige a un dominio: `helpdesk.delivery.htb`, agreguémoslo al archivo [/etc/hosts](https://tldp.org/LDP/solrhe/Securing-Optimizing-Linux-RH-Edition-v1.3/chap9sec95.html) para que cuando hagamos una petición hacia ese dominio nos resuelva hacia la IP **10.10.10.200**, así logra el servicio web entender hacia donde debe ir a buscar la info del dominio:

**(Aprovechemos para agregar el dominio **delivery.htb**, por si algo)**

```bash
ゝ cat /etc/hosts
...
10.10.10.222  helpdesk.delivery.htb delivery.htb
...
```

Si nos dirigimos hacia el dominio, vemos:

![308page80_helpdesk](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_helpdesk.png)

Valeee, estamos ante un servicio llamado [osTicket](https://avantys.com/clientes/knowledgebase/89/Que-es-OsTicket.html), que se encarga de brindar soporte al cliente, facilitando el orden y administración de los tickets enviados a mesa de ayuda, entre otras cosas...

Tenemos varios apartados, a la vista tres: abrir un nuevo ticket, verificar el status de un ticket y logearnos en **osTicket**. Si nos dirigimos a abrir un ticket nos pide una dirección email, así que veamos si podemos crearnos una:

![308page80_signin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_signin.png)

Vemos aparentemente dos nuevos apartados, uno en donde podemos registrar una cuenta y otra que nos dirige a un nuevo login, en este caso (según lo que vimos) para los ["agentes"](https://docs.osticket.com/en/latest/Admin/Agents/Agents.html), echemos un ojo rápidamente:

![308page80_agent_login](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_agent_login.png)

Probando credenciales por default no logramos nada, así que volvamos y registremos una cuenta.

Registramos y nos redirige a una ventana que nos indica que nos enviara un email de verificación para hacer efectivo el registro :( (Acá pensé en tomar un **email** temporal online y volver a registrarnos, pero no llega ningún correo, así que esto no debe ser relevante. Si intentamos logearnos con las credenciales registradas obtenemos:

```html
Account confirmation required
```

Así que F, reconfirmamos que probablemente no sea necesario crear una cuenta para explotar la máquina ;) 

Ahora sí, creemos un ticket con el email que registramos a ver si vemos algo, llenamos los campos necesarios, damos clic en **Create Ticket** y nos responde con:

![308page80_creating_ticket_as_lanz](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_creating_ticket_as_lanz.png)

Varias cositas interesantes:

* Crea un ticket con lo que parece ser un número aleatorio,
* pero ese mismo número lo usa para generar un **email** con dominio `delivery.htb`...

Si intentamos ver el status del ticket nos vuelve a responder con **Account confirmation required** :(

Jmmm, despues de muchas pruebas (listo 2, pero uff, lo que probé jaja), como estas:

* Crearnos un correo que tenga el dominio `delivery.htb`, crear ticket y validar su estado.
* Usar el correo que nos da al crear el ticket y registar una cuenta con él.

No logramos ver ningún ticket.

Se me dio por probar a crear un ticket como el usuario **admin@delivery.htb** (que no sabía que existía, pero son pruebas que se deben hacer) y con el sí podemos ver el status del ticket.

Como ejemplo creamos uno y nos devuelve:

* ID: **9827830**.
* email: **9827830@delivery.htb**.

![308page80_check_ticket_as_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_check_ticket_as_admin.png)

Llegamos a:

![308page80_check_ticketContent_as_admin](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_check_ticketContent_as_admin.png)

Bien, tenemos un usuario válido para ver tickets... No podemos hacer mucho con el contenido del ticket, así que tamos perdidos de nuevo :)

Probando cosas (de nuevo) no conseguimos nada, así que movámonos de servicio mientras tanto, quizás encontramos algo útil para volver.

...

### Puerto 8065 - Mattermost [⌖](#puerto-8065) {#puerto-8065}

![308page8065](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page8065.png)

Nos redirige al apartado `/login` y efectivamente tenemos un login 😜 del servicio [Mattermost](https://www.neolo.com/blog/que-es-mattermost-y-para-que-sirve.php), que nos ayuda a comunicarnos con un (o muchos) equipo(s) de trabajo.

En la imagen vemos la opción de crear una cuenta, la creamos y nos muestra como respuesta:

![308page8065_verify_email](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page8065_verify_email.png)

De nuevo tenemos que validar el email :(

...

## Explotación [#](#explotacion) {#explotacion}

Estuve también probando varias cosas, pero en un momento intente algo curioso y loco (muy loco):

* Crear una cuenta asociada a este email: **9827830@delivery.htb**, que fue el que obtuvimos al crear el ticket.

Hasta acá todo normal y nada loco... Pero actualice la página donde teníamos el status del ticket **9827830** y la info cambio, ahora tenemos esto:

![308page80_ticketContent_emailLinkMattermost](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_ticketContent_emailLinkMattermost.png)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308google_gif_what.gif" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Exacto, así quede. WtfFFFFFFFFFfdfffFffffffffffffff.

Tenemos el link para activar nuestra cuenta recientemente creada en el servicio **Mattermost**... Entendamos el porqué:

<span style="color:red;">1. </span>Creamos un ticket en el servicio **osTicket** y ese ticket genera un email, en la respuesta al generar el ticket vemos:

> If you want to **add more information to your ticket**, just email **9827830@delivery.htb**.

No lo vimos relevante pero ahora toma sentido.

<span style="color:red;">2. </span>Creamos una cuenta con el email anterior en el servicio **Mattermost** y como respuesta el servicio envía un correo para validar la cuenta.

<span style="color:red;">3. </span>Como vimos en el **punto 1**, prácticamente estamos "añadiendo" más información al ticket, donde esa "más información" es el correo enviado por **Mattermost**, por lo que entendemos que toda info enviada a ese correo actualizara el estado del ticket :) Bingo!

Perfecto, ya entendemos que está pasando, y que locura eh! Podemos seguir (:

En el correo enviado por **Mattermost** nos referencian el link para activar la cuenta:

```txt
Please activate your email by going to: http://delivery.htb:8065/do_verify_email?
token=6qm5nbugy3fgtwhm3zoxwt4zybrc8ip9xxffpfamfcyku8uhqepccj3rnopkrbsu&email=9827830%40delivery.htb
```

Si vamos hacia él, obtenemos:

![308page8065_emailVerified](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page8065_emailVerified.png)

Listones, tamos verificaos', colocamos la contraseña, enviamos la petición yyyy:

![308page8065_selecTeam](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page8065_selecTeam.png)

Nos pide seleccionar un equipo, dejamos el que esta por default llamado **internal**, damos clic sobre él, despues nos hace un tutorial y finalmente llegamos a toda la info sobre el equipo **internal**:

![308page8065_internalTeam_messages](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page8065_internalTeam_messages.png)

Vale, varias cositas interesantes:

* Nos da unas credenciales de "un servidor", tenemos 3 logins para probar y un SSH, así que tamos bien...
* Dice que están usando la misma contraseña en todos los sitios :o Y que las contraseñas están relacionadas con **PleaseSubscribe!**.
* Y vemos una referencia a **reglas** de hashcat, que relacionando el anterior punto, tiene mucho sentido :)

Bien, pues primero validemos las credenciales que nos dieron a ver donde funcionan.

Probándolas en el login de los agentes vemos que son válidas:

![308page80_agent_login_prevDONE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_agent_login_prevDONE.png)

![308page80_agent_login_DONE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308page80_agent_login_DONE.png)

Encontramos tooooooooooooooooodos los tickets creados y su histórico, entre muchas cosas más, como el **Admin Panel** en la parte superior (:

**Probándolas contra el servicio** SSH **obtenemos una sesión**:

```bash
ゝ ssh maildeliverer@10.10.10.222
maildeliverer@10.10.10.222's password: 
Linux Delivery 4.19.0-13-amd64 #1 SMP Debian 4.19.160-2 (2020-11-28) x86_64
...
maildeliverer@Delivery:~$ id
uid=1000(maildeliverer) gid=1000(maildeliverer) groups=1000(maildeliverer)
maildeliverer@Delivery:~$ 
```

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Despues de enumerar algunos archivos, encontramos los objetos fuente del servicio **Mattermost** y una carpeta de configuración:

```bash
maildeliverer@Delivery:/opt/mattermost/config$ ls -la
total 36
drwxrwxr-x  2 mattermost mattermost  4096 Dec 26 09:23 .
drwxrwxr-x 12 mattermost mattermost  4096 Dec 26 09:24 ..
-rw-rw-r--  1 mattermost mattermost   922 Dec 18 08:52 cloud_defaults.json
-rw-rw-r--  1 mattermost mattermost 18774 May 15 19:24 config.json
-rw-rw-r--  1 mattermost mattermost   243 Dec 18 08:52 README.md
```

Echando un ojito al archivo [config.json](https://docs.mattermost.com/administration/config-settings.html), vemos algo interesante:

```json
{
...
    ...
    "SqlSettings": {
        "DriverName": "mysql",
        "DataSource": "mmuser:Crack_The_MM_Admin_PW@tcp(127.0.0.1:3306)/mattermost?charset=utf8mb4,utf8\u0026readTimeout=30s\u0026writeTimeout=30s",
        "DataSourceReplicas": [],
        "DataSourceSearchReplicas": [],
        "MaxIdleConns": 20,
        "ConnMaxLifetimeMilliseconds": 3600000,
        "MaxOpenConns": 300,
        "Trace": false,
        "AtRestEncryptKey": "n5uax3d4f919obtsp1pw1k5xetq1enez",
        "QueryTimeout": 30,
        "DisableDatabaseSearch": false
    },
    ...
...
```

Ehh opa, conseguimos lo que parecen ser unas credenciales del servicio **MySQL** (gestor bases de datos):

* **mmuser:Crack_The_MM_Admin_PW**, una pw bastante extraña.

> Al parecer es un atributo propio de **Mattermost** y no algo hecho a posta por **ippsec**: [mattermost - config-in-database](https://docs.mattermost.com/administration/config-in-database.html).

Probemos a ver si son válidas:

```bash
maildeliverer@Delivery:/opt/mattermost/config$ mysql -u mmuser -p
Enter password: 
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 556
Server version: 10.3.27-MariaDB-0+deb10u1 Debian 10

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MariaDB [(none)]>
```

```bash
maildeliverer@Delivery:/opt/mattermost/config$ mysql -u mmuser -pCrack_The_MM_Admin_PW
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 557
Server version: 10.3.27-MariaDB-0+deb10u1 Debian 10

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MariaDB [(none)]>
```

**(Solo quería mostrarles dos maneras de hacerlo :P)**

Son válidas e.e Pues enumeremos las bases de datos y su información...

...

### Buscando en MySQL

Tenemos:

```mysql
MariaDB [(none)]> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mattermost         |
+--------------------+
2 rows in set (0.000 sec)

MariaDB [(none)]>
```

```mysql
MariaDB [(none)]> use mattermost;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
MariaDB [mattermost]> 
```

```mysql
MariaDB [mattermost]> show tables;
+------------------------+
| Tables_in_mattermost   |
+------------------------+
| Audits                 |
...
| UserAccessTokens       |
| UserGroups             |
| UserTermsOfService     |
| Users                  |
+------------------------+
46 rows in set (0.001 sec)

MariaDB [mattermost]> 
```

Varias tablas, pero veamos **Users** inicialmente:

```mysql
MariaDB [mattermost]> SELECT * FROM Users;
...
```

![308bash_delivery_mysql_Users_table](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308bash_delivery_mysql_Users_table.png)

Jmmm, un montón de usuarios y al haber tantos campos, pues se ve horrible todo :o Pero más o menos el formato de la tabla es así:

```mysql
| Id                         | CreateAt      | UpdateAt      | DeleteAt | Username                         | Password                                                     | AuthData | AuthService | Email                   | EmailVerified | Nickname | FirstName          | LastName | Position | Roles                    | AllowMarketing | Props | NotifyProps                                                                                                                                                                  | LastPasswordUpdate | LastPictureUpdate | FailedAttempts | Locale | Timezone                                                                                 | MfaActive | MfaSecret |   
| 16w657nsqpga5ci965u5gjks9w | 1621140348792 | 1621140348792 |        0 | hola                             | $2a$10$HMg19A65aU4TPSj2K3pbCuOYrc0zNh45URBKuNAX1f6AzXTnulB9m | NULL     |             | hola@lanz.com           |             0 |          |                    |          |          | system_user              |              1 | {}    | {"channel":"true","comments":"never","desktop":"mention","desktop_sound":"true","email":"true","first_name":"false","mention_keys":"","push":"mention","push_status":"away"} |      1621140348792 |                 0 |              0 | en     | {"automaticTimezone":"","manualTimezone":"","useAutomaticTimezone":"true"}               |         0 |           |
...
```

Donde en la contraseña vemos un hash tipo **bcrypt** según [la wiki](https://hashcat.net/wiki/doku.php?id=example_hashes) de ejemplos de **hashcat**.

![308google_wiki_hashcat_bcrypt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308google_wiki_hashcat_bcrypt.png)

Claramente no voy a jugar con un usuario que yo cree :P, pero si con uno interesante que vi:

```mysql
...
| dijg7mcf4tf3xrgxi5ntqdefma | 1608992692294 | 1609157893370 |        0 | root                             | $2a$10$VM6EeymRxJ29r8Wjkr8Dtev0O.1STWb4.4ScG.anuu7v0EFJwgjjO | NULL     |             | root@delivery.htb       |             1 |          |                    |          |          | system_admin system_user |              1 | {}    | {"channel":"true","comments":"never","desktop":"mention","desktop_sound":"true","email":"true","first_name":"false","mention_keys":"","push":"mention","push_status":"away"} |      1609157893370 |                 0 |              0 | en     | {"automaticTimezone":"Africa/Abidjan","manualTimezone":"","useAutomaticTimezone":"true"} |         0 |           |
...
```

Dos cositas interesantes de este usuario:

* Pos que se llama **root** e.e
* Pero más importante, en la columna **Roles**, tiene asignados: ***system_admin*** y **system_user**. ¿Cuál es el importante y porque es relevante este usuario? 

Listones, tomemos ese *hash* y guardémoslo en un archivo:

```bash
ゝ cat hash_root_mattermost
$2a$10$VM6EeymRxJ29r8Wjkr8Dtev0O.1STWb4.4ScG.anuu7v0EFJwgjjO
```

Y procedamos a crackearlo, podríamos usar el famoso diccionario **rockyou.txt**, pero recordemos lo que nos encontramos en los mensajes del equipo:

> PleaseSubscribe! may not be in RockYou but if any hacker manages to get our hashes, they can use hashcat rules to easily crack all variations of common words or phrases.

Todas las contraseñas están asociadas o tienen que ver con **PleaseSubscribe!** y que esa palabra no está en el diccionario **rockyou.txt**...

Entonces, sabemos que debe estar asociada a **PleaseSubscribe!** (este sería nuestro diccionario), podemos hacer uso de reglas (como bien nos lo indica el mensaje citado) para indicar que tome nuestro diccionario y empiece (depende de la regla) a modificar cada palabra del diccionario agregándole, borrándole, cambiando a mayúsculas, minúsculas, moviendo letras, agregando números, símbolos, etc. Todo lo que podamos imaginarnos con respecto a manipular una palabra lo hacen las reglas. Entonces por cada modificación va validando si ese resultado hace match con el hash...

Haremos el ataque basado en reglas usando **hashcat** y **JohnTheRipper**:

### HashCat - Rule Based Attack

Empecemos por **hashcat**.

* [Estudio de varias reglas, viendo la velocidad y eficacia de cada una en **hashcat**](https://notsosecure.com/one-rule-to-rule-them-all/)

Las reglas están en el directorio `/usr/share/hashcat/rules/`:

```bash
ゝ ls /usr/share/hashcat/rules/
best64.rule      generated2.rule  Incisive-leetspeak.rule      OneRuleToRuleThemAll.rule  T0XlC-insert_00-99_1950-2050_toprules_0_F.rule  T0XlCv1.rule   toggles4.rule
combinator.rule  generated.rule   InsidePro-HashManager.rule   oscommerce.rule            T0XlC-insert_space_and_special_0_F.rule         toggles1.rule  toggles5.rule
d3ad0ne.rule     hob064.rule      InsidePro-PasswordsPro.rule  rockyou-30000.rule         T0XlC-insert_top_100_passwords_1_G.rule         toggles2.rule  unix-ninja-leetspeak.rule
dive.rule        hybrid           leetspeak.rule               specific.rule              T0XlC.rule                                      toggles3.rule
```

Bien, siguiendo el estudio referenciado antes, usaremos la regla `InsidePro-PasswordsPro.rule`:

* [Acá podemos entender el contenido de las reglas](https://hashcat.net/wiki/doku.php?id=rule_based_attack).

Entonces, tenemos la regla y el hash, creamos un archivo llamado `dic.txt` que tenga la cadena **PleaseSubscribe!**, para así contar con todos los elementos para empezar a jugar...

Teniendo todo ejecutamos:

```bash
ゝ hashcat -m 3200 -r /usr/share/hashcat/rules/InsidePro-HashManager.rule hash_root_mattermost dic.txt -o cracked.txt
```

Donde:

* -m: Tiene el tipo de hash a crackear, en este caso **3200:bcrypt**.
* -r: Tiene la regla a usar.
* Pasamos el archivo que contiene el hash.
* Pasamos el diccionario, el cual contiene la cadena **PleaseSubscribe!**.
* -o: Le indicamos que si crackea el hash, nos guarde el resultado en el archivo llamado `cracked.txt`.

Despues de un rato obtenemos respuesta:

```bash
ゝ cat cracked.txt 
$2a$10$VM6EeymRxJ29r8Wjkr8Dtev0O.1STWb4.4ScG.anuu7v0EFJwgjjO:PleaseSubscribe!21
```

Con una cadena en texto plano: **PleaseSubscribe!21**. La cual sería la contraseña del usuario **root** del servicio **Mattermost**, peeeero intentando rehusarla contra la máquina y el usuario **root**, obtenemos:

![308bash_delivery_su_rootDONE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308bash_delivery_su_rootDONE.png)

Una sesión como él :))))))))) Ahora hagamos el mismo procedimiento pero con **John The Ripper**:

### John The Ripper - Rule Based Attack

Con **john** encontramos un lindo recurso con el que nos guiaremos:

* [Comprehensive Guide to John the Ripper - Rule-based attack](https://miloserdov.org/?p=5477).

En esta herramienta debemos actualizar (si quieren crear su propia regla) un archivo, en mi caso `/etc/john/john.conf` y agregarle lo que quieran, un punto superinteresante es que las reglas usadas en **hashcat** y **john** pueden ser las mismas, esto facilita mucho el aprendizaje. Además podemos ver como actúan las reglas en una cadena, esto está genial como aprendizaje de cada regla...

Creo una regla llamada **Lanz**:

```bash
ゝ cat /etc/john/john.conf
# Yo lo puse al final del archivo :P
...
[List.Rules:Lanz]
T0
T1
T2
T0T1
T1T2
T0T2
T0T1T2
$1
$2
$2$3
$2$1
$1$2
...
# Acá puedes agregar infinitas reglas según lo que quieras probar...
...
```

En este caso le pasamos la regla **T** (Cambia entre mayúscula a minúscula y al revés :P) y un numero, donde ese numero es la posición donde queremos que se efectúe la regla (:
Y le pasamos la regla **$**, que agrega al final algo, donde sé algo es lo que esta despues de dicho símbolo, por ejemplo **$1**, agregara al final de la cadena el número **1**, veamos la regla en ejecución:

```bash
ゝ john --rules=Lanz --wordlist=dic.txt --stdout
Using default input encoding: UTF-8
pleaseSubscribe!
PLeaseSubscribe!
PlEaseSubscribe!
pLeaseSubscribe!
PLEaseSubscribe!
plEaseSubscribe!
pLEaseSubscribe!
PleaseSubscribe!1
PleaseSubscribe!2
PleaseSubscribe!23
PleaseSubscribe!21
PleaseSubscribe!12
12p 0:00:00:00 100,00% (2021-05-17 25:25) 85.71p/s PleaseSubscribe!12
```

Le pasamos la regla que creamos anteriormente (`--rules`), el diccionario (`--wordlist`) y que nos muestre por pantalla lo que probaría (`--stdout`).

Perfecto, vemos como se va modificando nuestro diccionario según la regla (**eso esta buenaso**), ahora probemos contra el hash:

```bash
ゝ john --rules=Lanz --wordlist=dic.txt --format=bcrypt hash_root_mattermost 
Using default input encoding: UTF-8
Loaded 1 password hash (bcrypt [Blowfish 32/64 X3])
Cost 1 (iteration count) is 1024 for all loaded hashes
Press 'q' or Ctrl-C to abort, almost any other key for status
PleaseSubscribe!21 (?)
1g 0:00:00:00 DONE (2021-05-17 25:25) 3.571g/s 42.85p/s 42.85c/s 42.85C/s PleaseSubscribe!23..PleaseSubscribe!12
Use the "--show" option to display all of the cracked passwords reliably
Session completed
```

```bash
ゝ john --show hash_root_mattermost 
?:PleaseSubscribe!21

1 password hash cracked, 0 left
```

Y si, también hace la tarea de jugar con las reglas para finalmente darnos la cadena **PleaseSubscribe!21** como válida ante el hash :) Y por consiguiente volvernos a conectar como **root** y leer las flags :)

![308flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/delivery/308flags.png)

> Pa leer: [Otro recurso que habla de las reglas con respecto a **john**](https://www.openwall.com/john/doc/RULES.shtml).

...

Como conclusión [ippsec](https://www.youtube.com/c/ippsec/videos) nos deja una nota:

```bash
root@Delivery:~# cat note.txt 
I hope you enjoyed this box, the attack may seem silly but it demonstrates a pretty high risk vulnerability I've seen several times.  The inspiration for the box is here: 

- https://medium.com/intigriti/how-i-hacked-hundreds-of-companies-through-their-helpdesk-b7680ddc2d4c 

Keep on hacking! And please don't forget to subscribe to all the security streamers out there.

- ippsec
```

...

Me gusto bastante el ataque inicial una vez entendido, brutalidad eh! Como de algo tan pequeño explotan cosas gigantes ufff. El tema de las reglas es algo que puede ser muuuuy peligroso, me encanta como trabajan y modifican la data, que loco (:

Weno, hemos llegado hasta acá pero nos queda mucho por explorar, pero también nos queda como siempre seguir rompiendo de todooooo! Gracias por leer <3