---
layout      : post
title       : "TryHackMe - Crack The Hash Level 2"
author      : lanz
footer_image: assets/images/footer-card/weak-security.png
footer_text : Cracking de contraseñas
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-banner.png
category    : [ thm ]
tags        : [ cracking, john, hashcat ]
---
Seguiremos en el mundo del descubrimiento de contraseñas, jugaremos con diccionarios creados por nosotros, con reglas, con máscaras, uff, nos moveremos mucho

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-lab-information.png" style="width: 70%;"/>

## TL;DR (Spanish writeup)

**💥 Laboratorio creado por**: [noraj](https://tryhackme.com/p/noraj).

Ball-Buster x2

Seguiremos colándonos por el grandioso mundo del cracking, de los ataques de fuerza bruta, de los ataques por diccionario, de las formas de crear infinidad de alternativas para romper contraseñas, si si si 😵

Volvemos a jugar con **john the ripper** y **hashcat** (herramientas más famosas para este tipo de ataques) para meternos a la fuerza (buenísimo) en este lindo tema, usaremos reglas, máscaras, wordlist personalizados, muuuuucho proceso manual, pero nos divertiremos y aprenderemos.

...

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

STOOR

1. [Introducción](#introduccion)
2. [Retos](#challenge)
  * [Advice n°1](#advice-1)
  * [Advice n°2](#advice-2)
  * [Advice n°3](#advice-3)
  * [Advice n°4](#advice-4)
  * [Advice n°5](#advice-5)
  * [Advice n°6](#advice-6)
  * [Advice n°7](#advice-7)
  * [Advice n°8](#advice-8)
  * [Advice n°9](#advice-9)

...

# Introducción [#](#introduccion) {#introduccion}

**TryHackMe** nos presenta la continuación del laboratorio [Crack the hash](https://tryhackme.com/r/room/crackthehash), el cual [ya abordamos en el blog](https://lanzt.github.io/thm/crackthehash). Este tipo de entorno nos va a permitir seguir acalorados con el tema del [cracking de contraseñas](https://es.wikipedia.org/wiki/Descifrado_de_contrase%C3%B1a) y toooooooodas sus opciones y diversiones 🥵

Toda la teoría base la encuentras en el primer nivel: [TryHackMe - Crack the hash](https://lanzt.github.io/thm/crackthehash). Sin embargo, haré un recorrido muy rápido por conceptos.

> Algo que vamos a encontrar en esta ocasión es que la mayoria de ataques van a necesitar de nuestra creatividad (y de buscar mucho por internet) para lograr ser satisfactorios, con esto quiero decir que vamos a tener que ensuciarnos las manos mucho.

---

### ⏪ **¿Hash?**

En el mundo se guardan las contraseñas en formatos de hashes 🧐, ¿qué significa esto?: una función de hashing toma una entrada (la contraseña) y la convierte en un valor de longitud fija, que es prácticamente imposible de revertir. Pero no quiere decir que ya sea segura, hay **demasiadas** formas de crear ese hash, por lo que van a haber opciones menos seguras que otras 😭 (y también va a depender muuuucho de la contraseña, imagina tener como contraseña **hola**, pues de poco servirá tener el algoritmo más robusto por detrás).

### ⏪ **¿Cómo obtengo la contraseña que está detrás de un hash?**

Si quisiéramos mediante fuerza bruta obtener el texto plano del hash (recuerda: no lo podemos romper, es algo irreversible), necesitamos crear una lista de opciones, después automatizamos el proceso (con [john the ripper](https://www.openwall.com/john/) o [hashcat](https://hashcat.net/hashcat/)) para que tome cada opción de nuestra lista, la convierta mediante el algoritmo que creemos se usó, en un hash y después la herramienta comparara ambos hashes, si coinciden, significa que sabemos el origen del hash inicial, por lo que obtendríamos el texto plano, o sea, la contraseña.

### ⏪ **¿Reglas?**

En partes del artículo hablaremos de las [reglas](https://hashcat.net/wiki/doku.php?id=rule_based_attack), estas son funciones que nos van a permitir generar infinidad de candidatos (opciones a contraseñas), existen reglas para todo, si creemos que la contraseña que estamos descifrando está al revés y está en mayúscula, si creemos que es una palabra que se repite 5 veces, si creemos que al final tiene 3 dígitos y al inicio una letra en mayúscula, si creemos que solo la quinta letra está en mayúscula y que al final tiene un carácter especial y dos dígitos, en fin, como dije, hay reglas para todo.

Cuando juguemos con **John**, vamos a tener que modificar un archivo de configuración (casi siempre encontrado en `/etc/john/jonh.conf`), peeero, para no cambiarle cosas al archivo principal, podemos crear (o actualizar) el objeto `/usr/share/john/john-local.conf`, el cual **john** en su ejecución también busca y detecta. Allí agregaremos todas nuestras reglas y configuraciones sin temor a borrar o dañar algo en el principal.

* [John RULES](https://www.openwall.com/john/doc/RULES.shtml)

En **Hashcat** tenemos la posibilidad de crear un archivo con las reglas en el directorio donde estemos, así que cero problema por ese lado.

* [Hashcat RULES](https://hashcat.net/wiki/doku.php?id=rule_based_attack)

Lo que sí nos puede afectar un poco es el cómo maneja cada uno las reglas, pero esto lo veremos según vayamos explorando el lab.

### ⏪ **¿Máscaras?**

Con las [máscaras](https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK) vamos a jugar un poco más suave que con las reglas, ya que son funciones para ahorrar tiempo o tareas que haríamos manualmente, como probar solo con candidatos en minúscula, agregar dígitos secuencialmente a las opciones, caracteres especiales, etc. Es ir más directo que con las reglas (y son más sencillas de entender).

...

Con todo esto dicho y entrados en calor, el laboratorio presenta:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehash-lab-info.png" style="width: 100%;"/>

Y los siguientes apartados:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehash-lab-tasks.png" style="width: 100%;"/>

Nos enfocaremos en la tarea `6`, ya que ella es la que contiene los hashes que debemos crackear. Las otras tareas servirán para reconocer el laboratorio y obtener herramientas, ese te lo dejo a ti.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehash-lab-tasks-task6.png" style="width: 100%;"/>

¡Entonces a darle!

# Retos [#](#challenge) {#challenge}

---

## Advice n°1 [📌](#advice-1) {#advice-1}

---

### #️⃣ **Información del hash**

---

```txt
b16f211a8ad7f97778e5006c7cecdf31
```

Como parte del laboratorio, el creador nos presenta una herramienta llamada [haiti](https://github.com/noraj/haiti), la cual ayuda a identificar que tipos de hashes de forma linda, además nos indica el formato a usar tanto en **john the ripper** como en **hashcat**.

Así que la instalamos y usamos contra este hash:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice1-bash-haiti.png" style="width: 100%;"/>

> No ahondaré tanto en los tipos de hashes que ya vimos [en el nivel uno de este lab](https://lanzt.github.io/thm/crackthehash).

El más probable es [MD5](https://es.wikipedia.org/wiki/MD5), el cual tiene como formato en **john**: `Raw-MD5` y en **hashcat**: `0`; sin embargo, tengamos en mente los demás.

### 💬 **Consejo y explicación**

Ya que aclaramos el hash, veamos que le dijeron a nuestra víctima:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice1.png" style="width: 100%;"/>

Destacamos:

* Se llama **John**.
* Usualmente, coloca el nombre del hijo como contraseña.
* Le recomiendan usar algo llamado **border mutation**.

Las mutaciones se pueden ver como "actualizaciones/mejoras" empleadas en este caso en contraseñas (palabras) para modificar su formato original.

* Te dejo una lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html).

En este caso le indican a **John** que lo mejor es que use la mutación **Border**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-dictionary-mutations-border.png" style="width: 100%;"/>

La cual toma la contraseña (palabra o frase) y le agrega, ya sea al inicio, al final o a ambos lados, números o caracteres especiales, por ejemplo:

```txt
Palabra:
hola

Mutación:
1hola
[...]
hola$
[...]
3hola#
[...]
123hola*
[...]
```

Apoyados en las reglas, notamos las dos que necesitamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-hashcat-border-rules.png" style="width: 100%;"/>

Ya tenemos la mutación, pero nos falta lo que vamos a mutar...

Sabemos que su contraseña está relacionada con el nombre del hijo, apoyados de [SecLists](https://github.com/danielmiessler/SecLists) y sus listas de palabras de diferentes temas, encontramos algunas que tienen nombres:

```bash
➧ find /opt/seclists | grep -i names
[...]
/opt/seclists/Usernames/Names/malenames-usa-top1000.txt
/opt/seclists/Usernames/Names/forenames-india-top1000.txt
/opt/seclists/Usernames/Names/femalenames-usa-top1000.txt
/opt/seclists/Usernames/Names/familynames-usa-top1000.txt
/opt/seclists/Usernames/Names/names.txt
[...]
```

Podemos quedarnos con `malenames...txt` y `names.txt`. Con esto completamos lo necesario para intentar el crackeo.

### 🎩 **Cracking con John The Ripper**

Teniendo en cuenta las reglas, podemos armar:

```bash
cat /usr/share/john/john-local.conf
```

```txt
[List.Rules:Borders]
$[0-9] $[!@#$%^&*()+=.?]
^[0-9] ^[!@#$%^&*()+=.?]
```

Donde al ejecutarse tomaría cada palabra de la lista y le agregaría:

* De primeras, agrega al final un dígito (del **0** al **9**) y un carácter especial (del conjunto que ves arriba).
* Y de segundas, la misma iteración de antes, pero al inicio de la cadena.

> Cree un archivo llamado `test.txt` con `carlitos` como unica palabra, **lo vamos a usar a lo largo del writeup**.

```bash
➧ john --wordlist=test.txt --rules=Borders --stdout
```

> Con `--stdout` podemos validar que lo que tenemos pensado hacer (**John** o **Hashcat**) efectivamente se este realizando como queremos.

```txt
[...]
carlitos9.
carlitos9?
!0carlitos
@0carlitos
[...]
```

> Si te fijas, en la segunda iteración, esta agregando primero el caracter y despues el digito, apesar de que se lo indiqué al reves, esto intente esclarecerlo, pero lo que obtuve es que es tema interno de como maneja **John** las reglas y su procesamiento. De igual forma, para arreglarlo y obtener el resultado esperado, simplemente mueve la regla, o sea, en la priemra columna los caracteres y en la segunda los digitos 😘

Ya estamos listos para combinar lo que tenemos y ejecutar cositas:

```bash
john --wordlist=/opt/seclists/Usernames/Names/names.txt --rules=Borders --format=Raw-MD5 hash_ad1
```

* En `--wordlist` asignamos el archivo con las palabras (en este caso nombres) a mutar.
* En `--rules` llamamos la regla que creamos previamente.
* En `--format` indicamos el formato del hash a crackear (puedes listar el formato usando `john --list=formats | grep -i md5` (pero ya nos lo había indicado `haiti`)).
* En el archivo `hash_ad1` está alojado el hash a crackear.

Pero nada, no logramos encontrarle match al hash, así que hay que ponerse creativo e intentar variantes, como agregar 2 dígitos al inicio y un carácter especial al final, o al inicio, o 10 dígitos al final, etc. También es una posibilidad que el nombre esté en mayúsculas, que solo tenga una letra en mayúscula, varias cositas, pero cero líos, estamos aprendiendo (:

Después de probar y probar, llegue a la conclusión de que me cansé de estar moviendo `$[0-9]` y la de los caracteres de un lado pal otro manualmente, así que me cree este script (que convertí en repositorio):

> [https://github.com/lanzt/mutorder](https://github.com/lanzt/mutorder)

El cual necesita simplemente un archivo llamado `rules-syntax.txt` y va a contener la sintaxis de como quieres que quede la contraseña:

```bash
➧ cat rules-syntax.txt:
password00
password!0
!password0
```

> El digito `0` y el caracter `!` son necesarios, ya que el script se basa en ellos para ordenar la regla.

Si lo ejecutamos:

```bash
➧ python3 rule-border-mutation-generator.py
# -----> password00
$[0-9] $[0-9]
# -----> password!0
$[!@#$%^&*()+=.?] $[0-9]
# -----> !password0
^[!@#$%^&*()+=.?] $[0-9]
```

Esto nos da más flexibilidad pa probar cositas, pero probando y probando tampoco logramos descubrir la contraseña.

Así que pasé a probar el tema de las mayúsculas en el nombre, lo que hice fue tomar las reglas que ya tenía y duplicarlas para al inicio de ellas agregar estas nuevas reglas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-hashcat-case-rules.png" style="width: 100%;"/>

Llegando finalmente a crear estas reglas:

```txt
[List.Rules:Borders]
# -----> password0000!
$[0-9] $[0-9] $[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> password0000!
l$[0-9] $[0-9] $[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> PASSWORD0000!
u$[0-9] $[0-9] $[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> Password0000!
c$[0-9] $[0-9] $[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> pASSWORD0000!
C$[0-9] $[0-9] $[0-9] $[0-9] $[!@#$%^&*()+=.?]
```

Que cuando lanzamos **John** con ellas:

```bash
john --wordlist=/opt/seclists/Usernames/Names/names.txt --rules=Borders --format=Raw-MD5 hash_ad1
```

TaDa!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice1-bash-john-cracked.png" style="width: 100%;"/>

Obtenemos en texto plano la contraseña (: Un camino duro, pero se logró.

### 🐈 **Cracking con Hashcat**

Lamentablemente con **hashcat** no podemos hacer esos conjuntos de opciones (`$[0-9]`), sino que toca uno a uno. Y hacer eso a mano es una locura descomunal, ya que deberíamos llegar a esta regla:

```bash
c $1 $2 $3 $4 $*
```

Pero si usamos máscaras podemos armar distintas pruebas, hasta llegar a la deseada:

```bash
hashcat -a 6 /opt/seclists/Usernames/Names/names.txt -j 'c' '?d?d?d?d?s' --stdout
```

* [-a 6](https://hashcat.net/wiki/#core_attack_modes): Nos permite combinar **wordlists** más **máscaras**
* `-j`: Permite asignar reglas a la palabra
  * `c`: Esta regla toma la palabra y coloca únicamente la primera letra en mayúscula
* ['...'](https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK): Es la máscara usada, se puede sin las comillas, pero para que sea más claro
  * [?d](https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK): Define una lista de dígitos (0 al 9)
  * [?s](https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK): Define una lista de caracteres especiales (como `#$%&,.` entre otros)

Lo que estaríamos diciendo es, toma una palabra, ponle la primera letra en mayúscula y al final agrégale 4 dígitos y un carácter especial:

```txt
[...]
Allen8441-
[...]
Allen7387/
[...]
```

> Es el output que necesitamos, comparado con el resultado obtenido con **john**

Así que si le damos forma al comando:

```bash
hashcat -a 6 -m 0 hash_ad1 /opt/seclists/Usernames/Names/names.txt -j 'c' '?d?d?d?d?s' -o hash_ad1.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice1-bash-hashcat-cracked.png" style="width: 60%;"/>

Listones, juguetón el primero, continuemos...

## Advice n°2 [📌](#advice-2) {#advice-2}

---

### #️⃣ **Información del hash**

---

```txt
7463fcb720de92803d179e7f83070f97
```

Usando `haiti` nos indica:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice2-bash-haiti.png" style="width: 60%;"/>

Lo mismo de antes, posiblemente [MD5](https://es.wikipedia.org/wiki/MD5), pero mantenemos la mente abierta por si debemos probar los otros.

### 💬 **Consejo y explicación**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice2.png" style="width: 100%;"/>

* Se llama **Levy**.
* Usa el **nombre de la hija**.
* De nuevo **border mutation**.

> Te dejo una lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html).
> <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-dictionary-mutations-border.png" style="width: 100%;"/>

Por lo que tomaremos solo listas relacionadas con nombres de mujeres. Pa cambiar un poco, usaremos una herramienta que el creador de la máquina presenta:

* [wordlistctl](https://github.com/BlackArch/wordlistctl) contiene más de **6400** listas de palabras.

La instalamos y buscamos listas relacionadas con mujeres:

```bash
➧ wordlistctl.py search female
--==[ wordlistctl by blackarch.org ]==--

    0 > femalenames-usa-top1000 (6.94 Kb)
    1 > FEMALE-N (39.39 Kb)
    2 > top_1000_usa_femalenames_english (6.78 Kb)
    3 > Female (2.96 Mb)
```

Yo usaré la número 2:

```bash
➧ wordlistctl.py fetch top_1000_usa_femalenames_english --decompress
```

Y ya tendríamos el archivo en la ruta `/usr/share/wordlists/misc/top_1000_usa_femalenames_english.txt`.

```bash
➧ cat /usr/share/wordlists/misc/top_1000_usa_femalenames_english.txt | head -n 10
MARY
PATRICIA
LINDA
BARBARA
ELIZABETH
[...]
```

> Ojito que los nombres estan en mayuscula, pero con las reglas podemos modificar eso :P

Tamos listos, tenemos todo: el hash, el wordlist, el formato y la regla (como es **border**, pues tomamos la misma del reto 1).

### 🎩 **Cracking con John The Ripper**

---

```bash
john --wordlist=/usr/share/wordlists/misc/top_1000_usa_femalenames_english.txt --rules=Borders --format=Raw-MD5 hash_ad2
```

Pero no logramos romperla...

Dándole vueltas a como queremos que quede la contraseña ([https://github.com/lanzt/mutorder](https://github.com/lanzt/mutorder)), llegamos a esta:

```bash
➧ cat /usr/share/john/john-local.conf
[...]
[List.Rules:Borders]
# -----> PASSWORD00!
$[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> password00!
l$[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> Password00!
c$[0-9] $[0-9] $[!@#$%^&*()+=.?]
# -----> pASSWORD00!
C$[0-9] $[0-9] $[!@#$%^&*()+=.?]
```

Si la ejecutamooooososososso:

```bash
john --wordlist=/usr/share/wordlists/misc/top_1000_usa_femalenames_english.txt --rules=Borders --format=Raw-MD5 hash_ad2
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice2-bash-john-cracked.png" style="width: 100%;"/>

La rompimo'!

### 🐈 **Cracking con Hashcat**

Podemos usar la misma técnica de máscara de antes, ya que con reglas es muy duro llegar a la correcta:

> Vamos directos, pero piensa como si hubieramos probado y probado opciones.

```bash
hashcat -a 6 -m 0 hash_ad2 /usr/share/wordlists/misc/top_1000_usa_femalenames_english.txt -j 'c' '?d?d?s' -o hash_ad2.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice2-bash-hashcat-cracked.png" style="width: 60%;"/>

## Advice n°3 [📌](#advice-3) {#advice-3}

---

### #️⃣ **Información del hash**

---

```txt
f4476669333651be5b37ec6d81ef526f
```

Pasándoselo a [haiti](https://noraj.github.io/haiti/#/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice3-bash-haiti.png" style="width: 60%;"/>

Posiblemente [MD5](https://es.wikipedia.org/wiki/MD5).

### 💬 **Consejo y explicación**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice3.png" style="width: 100%;"/>

* Se llama **Charlotte**.
* Tiene 23 años.
* La contraseña es una ciudad visitada durante su viaje a **México**.
* La contraseña tiene que cumplir una política, por lo que ha de ser difícil.
* Se le recomienda usar la mutación **Freak** o también llamada **1337** (**l33t**).

> Te dejo una lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html).
> <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-dictionary-mutations-freak.png" style="width: 100%;"/>

Esta mutación permite intercambiar/reemplazar algunos caracteres por dígitos o caracteres especiales, imagina este ejemplo:

Tenemos la palabra `buenas`.

Usando esta mutación se modificaría por:

```txt
bu3nas
bu3n@s
buena$
bu3n45
```

Y muchas más combinaciones que sean acordes a la(s) letra(s).

Ahora necesitamos una lista de palabras que relacionen ciudades de **México**, buscando llegamos a muchas:

* [cities_mexico.json](https://raw.githubusercontent.com/israelcrux/ciudades_mexico/master/cities_mexico.json)
* [List of cities in Mexico](https://simple.wikipedia.org/wiki/List_of_cities_in_Mexico)
* [Mexico Cities Database](https://simplemaps.com/data/mx-cities)
* [List of cities and towns in Mexico](https://www.britannica.com/topic/list-of-cities-and-towns-in-Mexico-2039050)
* Encontrada en el sistema: [city-state-country.txt](https://raw.githubusercontent.com/danielmiessler/SecLists/refs/heads/master/Miscellaneous/Security-Question-Answers/city-state-country.txt)

Listo, nos queda implementar la locura (**Freak** / **l33t**)...

Si revisamos las reglas, hay una que permite reemplazar cositas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-hashcat-replace-rule.png" style="width: 100%;"/>

Creemos un ejemplo para tenerla clara:

```bash
➧ cat /usr/share/john/john-local.conf
[...]
[List.Rules:Freak]
# ----> palabras : p@l@br@s
sa@
# ----> palabras : p4l4br4s
sa4
# ----> palabras : palabra$
ss$
```

Pero según como lo estamos viendo, puede ser un proceso muuuuuuy manual, de reemplazar esto con esto, o combinar esto y esto, pff, locura.

Inspeccionemos como lidiar con esto en cada herramienta.

### 🎩 **Cracking con John The Ripper**

Intentando buscar alguna regla predefinida dentro de la configuración de **john** encontramos sabrosura, como el dicho, "llegue buscando cobre y encontré oro" 👵

```bash
➧ cat /usr/share/john/john.conf | grep -i leet
# External hybrid 'leet code
[List.External:Leet]
```

Revisando el archivo y buscando eso de "`[List.External:Leet]`" notamos que hay un código programado para jugar con estoooooo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice3-bash-cat-johnConf-external-leet.png" style="width: 100%;"/>

> El [modo externo](https://www.openwall.com/john/doc/EXTERNAL.shtml) permite implementar codigo escrito en `C`, el cual podra ser invocado por **John**.

Brutal!

Buscando `[List.External:Leet]` en internet [encontramos este recurso](https://www.openwall.com/lists/john-users/2016/04/02/1) y sabemos como usarlo (:

```bash
➧ john --wordlist=test.txt --external=Leet --stdout
c4rlitos
[...]
c4r1i7os
[...]
c4rl!70s
[...]
c@r1i7o$
[...]
```

Peeeeerfecto, crea todas las combinaciones básicas, si quisiéramos agregar más, lo único que debemos hacer es jugar con los **if** que está implementando en la configuración:

```c
[...]
if (word[wlen] == 'a') {
    rotor[rotor_off++] = 'a';
    rotor[rotor_off++] = '4';
    rotor[rotor_off++] = '@';
}
[...]
```

Pero probaremos inicialmente con esos.

Cansado de tanto probar, de extraer ciudades, de quitar, de poner (cansao toy), nos quedamos con esta lista:

```bash
cat /opt/seclists/Miscellaneous/security-question-answers/city-state-country.txt | grep -i mexico
[...]
Tuxpam de Rodriguez Cano,Veracruz,Mexico
San Juan Bautista Tuxtepec,San Juan Bautista Tuxtepec,Oaxaca,Mexico
Veracruz,Veracruz,Mexico
Cuyamungue,New Mexico,United States
[...]
```

Pero nos está mostrando también sitios de Estados Unidos, filtremos por las líneas que acaban en **México**, obtengamos sus ciudades y guardemos el resultado en un archivo:

```bash
cat /opt/seclists/Miscellaneous/security-question-answers/city-state-country.txt | grep -i 'mexico$' | cut -d ',' -f 1 > mexico_towns.txt
```

E intentemos la crackeazion:

```bash
john --wordlist=mexico_towns.txt --external=Leet --format=Raw-MD5 hash_ad3
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice3-bash-john-cracked.png" style="width: 100%;"/>

AJAJAAAAAI!! Fino esto 💥

> Pero fue un reto muy desgastante, casi no llego a la lista correcta 😩

...

Te dejo una herramienta que me gustó mucho y con la cual también logré armar el wordlist para romper el hash:

* [https://github.com/TheTechromancer/password-stretcher](https://github.com/TheTechromancer/password-stretcher)

Yyy también pude romper el hash usando esta regla:

```txt
[List.Rules:Freak]
s[iI][!1] s[eE][3] s[sS][$5] s[aA][4@] s[tT][+7] s[oO][0]
```

> Pero lo dicho, muuy manual

Sigamo.

### 🐈 **Cracking con Hashcat**

Investigando en la web, encontramos que hay una regla definida por **hashcat** para este propósito:

```bash
/usr/share/hashcat/rules/leetspeak.rule
```

Pero al probarla no logramos nada, ya que está reemplazando de a una opción y como ya vimos con **john**, el resultado tiene dos opciones reemplazadas (`a por @` y `o por 0`).

Con la búsqueda, encontramos esta otra lista de reglas relacionadas con **leet**:

```bash
➧ find /usr/share/hashcat/rules/ | grep -i leet
/usr/share/hashcat/rules/unix-ninja-leetspeak.rule
/usr/share/hashcat/rules/leetspeak.rule
/usr/share/hashcat/rules/Incisive-leetspeak.rule
```

**Incisive** tiene muuuchas más opciones y combinaciones, si probamos:

```bash
hashcat test.txt -r /usr/share/hashcat/rules/Incisive-leetspeak.rule --stdout
[...]
carli70$
carlit0$
[...]
```

Por **john** sabemos que la primera letra de la ciudad es en mayúscula, así que usamos la misma regla que en el reto anterior y ejecutamos:

```bash
hashcat -a 0 -m 0 hash_ad3 mexico_towns.txt -r /usr/share/hashcat/rules/Incisive-leetspeak.rule -j 'c' -o hash_ad3.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice3-bash-hashcat-cracked.png" style="width: 60%;"/>

## Advice n°4 [📌](#advice-4) {#advice-4}

---

### #️⃣ **Información del hash**

---

```txt
a3a321e1c246c773177363200a6c0466a5030afc
```

Según [haiti](https://noraj.github.io/haiti/#/) el tipo de algoritmo más probable es [SHA-1](https://es.wikipedia.org/wiki/Secure_Hash_Algorithm):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice4-bash-haiti.png" style="width: 60%;"/>

### 💬 **Consejo y explicación**

En esta ocasión le recomiendan:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice4.png" style="width: 100%;"/>

* **David**.
* Le gusta el rap y es DJ
* Le gusta Eminem
* Le gusta esta canción: [Eminem - My Name Is](https://www.youtube.com/watch?v=sNPnbI1arSE)
* En su password quiere usar su nombre completo: **David Guettapan**
* Le indican que use la **Case Mutation**

> Te dejo una lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html).
> <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-dictionary-mutations-case.png" style="width: 100%;"/>

Esta mutación lo que hace es tomar una letra y si está en minúscula, convertirla a mayúscula, o viceversa. Ejemplo:

```txt
Palabra:
Hola

Mutación:
hola
hOla
HOlA
holA
[...]
```

Es sencilla de entender, además ya hemos venido implementando algunas de estas reglas relacionadas con el "case-sensitive":

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice4-google-hashcat-rules-case-toogle.png" style="width: 100%;"/>

Un ejemplo rápido:

```bash
cat /usr/share/john/john-local.conf
```

```bash
[List.Rules:NiCasoWey]
# minuscula todo
l
# MAYUSCULA TODO
u
# Unicamente primera letra mayuscula
c
# mINUSCULA EL PRIMER CARACTER Y MAYUSCULA EL RESTO
C
# camBia (o CAMbIA) el case de la letra en la posición 3 (empieza en la 0)
T3
```

```bash
➧ john --wordlist=test.txt --rule=NiCasoWey --stdout
carlitos
CARLITOS
Carlitos
cARLITOS
carLitos
```

Lindo lindo.

...

La cosa es que tenemos muuuchas opciones como semilla de contraseña, el nombre **David** (y apellido), una canción de Eminem (nombre y letra), el propio Eminem, etc. Para no complicarnos vamos a iniciar con **David** y su apellido (ya que el mismo indica que su contraseña tiene su nombre).

¿Pero será solo **David**? ¿O quizá con su apellido? ¿Tal vez el apellido primero? Pff, teniendo eso en cuenta nos armamos estas opciones:

```bash
➧ cat david_name.txt
David Guettapan
Guettapan David
DavidGuettapan
GuettapanDavid
Guettapan
David
```

Ya tenemos el formato del hash, el hash y las reglas que nos pueden servir, y las opciones para construir las contraseñas, así que a construir.

### 🎩 **Cracking con John The Ripper**

Intentando con las reglas no logré nada (que claramente se puede, pero de mis pruebas, ninguna fue fructifera), así que regresé a la herramienta [password-stretcher](https://github.com/TheTechromancer/password-stretcher) (que te recomendé antes) y aproveché su opción `--capswap`:

```bash
echo 'David Guettapan\nDavidGuettapan\nGuettapan\nDavid' | password-stretcher --capswap
```

Esto nos genera:

```txt
dAVID
[...]
gUEttapan
[...]
DaVid gUETTAPAN
```

Exactamente lo que necesitamos. Guardamos su resultado en un archivo:

```bash
echo 'David Guettapan\nDavidGuettapan\nGuettapan\nDavid' | password-stretcher --capswap > wordlist.txt
```

Y ejecutamoooooooos:

```bash
john --wordlist=wordlist.txt --format=Raw-SHA1 hash_ad4
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice4-bash-john-cracked.png" style="width: 100%;"/>

Listongo (: (y sin usar la canción 😐).

### 🐈 **Cracking con Hashcat**

Aprovechamos que tenemos el wordlist y simplemente ejecutamos:

```bash
hashcat -a 0 -m 100 hash_ad4 wordlist.txt -o hash_ad4.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice4-bash-hashcat-cracked.png" style="width: 70%;"/>

## Advice n°5 [📌](#advice-5) {#advice-5}

---

### #️⃣ **Información del hash**

---

```txt
d5e085772469d544a447bc8250890949
```

Ayudándonos de [haiti](https://noraj.github.io/haiti/#/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-bash-haiti.png" style="width: 80%;"/>

El tipo de hash con mayor probabilidad es [MD5](https://es.wikipedia.org/wiki/MD5).

### 💬 **Consejo y explicación**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5.png" style="width: 80%;"/>

Destacamos:

* Se llama **Jack Pott**.
* Le gusta la música de **Adele** y **sus letras**.
* Le aconsejan que haga la contraseña más larga y él dice que ya es larga.
* Como consejo final le dicen que reversee las letras de la contraseña.

Si nos fijamos en la lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html), hay una relacionada con el orden de los caracteres y las palabras:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-dictionary-mutations-order.png" style="width: 100%;"/>

Ejemplo para entenderla mejor:

```txt
Cadena:
Si buenas

Mutación:
saneub iS
Si buenasSi buenas
Si buenassaneub iS
```

Revisando las reglas, encontramos las relacionadas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-google-hashcat-rules-order.png" style="width: 100%;"/>

Si armamos un ejemplo para ver como funcionan:

```bash
➧ cat /usr/share/john/john-local.conf
[List.Rules:Reversa]
# asreveR -de toda la cadena-
r
# DuplicaDuplica -la cadena-
d
# DuplicaDuplicaDuplicaDuplica -la cadena el número de veces indicado-
p4
# DuplicaacilpuD -la cadena escrita en reverso-
f
```

Validamos:

```bash
➧ john --wordlist=test.txt --rule=Reversa --stdout
sotilrac
carlitoscarlitos
carlitoscarlitoscarlitoscarlitoscarlitos
carlitossotilrac
```

Listo listo, tenemos las reglas y el formato del hash, nos falta averiguar cuanto tiene que ver **Adele** y sus canciones en esta contraseña.

...

Apoyados de internet llegamos a muuuchas listas con las [canciones de Adele](https://www.azlyrics.com/a/adele.html), pero probando varias letras no llegue a nada. Buscando y buscando, consulté `wordlist using lyrics` en internet y llegué a esta tool:

* [https://github.com/initstring/lyricpass](https://github.com/initstring/lyricpass)

> Ella permite crear listas de contraseñas usando letras de canciones relacionadas a artistas.

Su uso es muy sencillo, en este caso si queremos buscar letras de **Adele**:

```bash
python3 lyricpass.py --artist adele
[+] Looking up artist adele
[+] Found 368 songs for artists adele
[+] All done! 368/368...
[...]
Raw lyrics: raw-lyrics-2024-07-21-15.23.55
Passphrases: wordlist-2024-07-21-15.23.55
[...]
```

Como vemos nos da dos archivos, uno conteniendo las letras en crudo y otro con frases, nos enfocaremos en el que tiene las letras, ya que tiene más contenido:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-bash-ls-lyrics-files.png" style="width: 100%;"/>

Ahora sí, contamos con lo necesario, démosle.

### 🎩 **Cracking con John The Ripper**

Simplemente armamos el comando:

```bash
john --wordlist=raw-lyrics-2024-07-21-15.23.55 --rule=Reversa --format=Raw-MD5 hash_ad5
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-bash-john-cracked.png" style="width: 100%;"/>

🙌

> Y sip, la canción es **Remedy**.

### 🐈 **Cracking con Hashcat**

Vamos a usar la misma regla y la misma wordlist de antes, pero la diferencia reside en que el archivo de la regla puede ser cualquiera, vamos a crearlo justo donde estamos:

```bash
cat my.rules
```

```bash
# asreveR -de toda la cadena-
r
# DuplicaDuplica -la cadena-
d
# DuplicaDuplicaDuplicaDuplica -la cadena el número de veces indicado-
p4
# DuplicaacilpuD -la cadena escrita en reverso-
f
```

Probamos:

```bash
➧ hashcat test.txt -r my.rules --stdout                                        
sotilrac
carlitoscarlitos
carlitoscarlitoscarlitoscarlitoscarlitos
carlitossotilrac
```

Funcionando, así queeee:

```bash
hashcat -a 0 -m 0 hash_ad5 raw-lyrics-2024-07-21-15.23.55 -r my.rules -o hash_ad5.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-bash-hashcat-cracked.png" style="width: 100%;"/>

...

Te voy a dejar un truco, pueda que a veces probemos muuuuchas reglas al tiempo y queramos saber cual logro el crackeo, podemos usar las funciones de debug que nos ofrece **hashcat**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-google-hashcat-debug.png" style="width: 100%;"/>

```bash
hashcat -a 0 -m 0 hash_ad5 raw-lyrics-2024-07-21-15.23.55 -r my.rules --debug-mode=4 --debug-file=hash_ad5.debug -o hash_ad5.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice5-bash-hashcat-cracked-debug.png" style="width: 100%;"/>

## Advice n°6 [📌](#advice-6) {#advice-6}

---

### #️⃣ **Información del hash**

---

```txt
377081d69d23759c5946a95d1b757adc
```

Acá el tipo de formato usado al parecer vuelve a ser [MD5](https://es.wikipedia.org/wiki/MD5), esto según [haiti](https://noraj.github.io/haiti/#/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6-bash-haiti.png" style="width: 90%;"/>

### 💬 **Consejo y explicación**

Como indicación vemos y destacamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6.png" style="width: 50%;"/>

* Se llama **Crystal Ball**
* Contraseña facil de recordar
* Le dicen que ponga como contraseña su número de celular
* Y sabemos que Crystal es de [Sint Marteen](https://es.wikipedia.org/wiki/San_Mart%C3%ADn_(Pa%C3%ADses_Bajos)), ***por lo tanto su numero de celular tambien***.

Cada pais (incluso ciudad) del mundo, tiene su propio ID antes del numero de celular o fijo, esto para que sea claro el destinatario de la comunicación, averiguando, conocemos que el prefijo de **Sint Marteen** es `721` en **Paises Bajos**, pero internacionalmente debemos agregar el codigo de pais `1`, dando dos opciones de numero como resultado: `721` y `1721`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6-google-sint-maarten-phone-prefix.png" style="width: 80%;"/>

> [https://en.wikipedia.org/wiki/Area_code_721](https://en.wikipedia.org/wiki/Area_code_721)

Listo, ahora nos queda crear la lista de posibles numeros, como parte del laboratorio, el creador nos enseña una herramienta muy util y que podemos usar en este reto:

* [https://github.com/tp7309/TTPassGen](https://github.com/tp7309/TTPassGen)

Con ella podemos crear multitud de patrones, combinaciones, asignar el orden de esa info, implementar reglas, uf, muy completa.

Buscando números reales de entidades, de organizaciones y personas en **Sint Maarten**, conocemos algunos formatos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6-google-sint-maarten-phone-examples.png" style="width: 60%;"/>

* [www.sintmaartengov.org](https://www.sintmaartengov.org/Pages/Emergency-Numbers.aspx)
* [www.nagico.com/st-maarten-emergency-numbers-2/](www.nagico.com/st-maarten-emergency-numbers-2/)

Algo que tambien constatamos es que la longiutd del numero es de **11** digitos (o **10**), de los cuales ya sabemos **4** (o **3**).

```bash
1-721-xxx.xxxx
+1-721-xxx.xxxx
721-xxx.xxxx
+721-xxx.xxxx
1721xxxxxxx
+1721xxxxxxx
721xxxxxxx
+721xxxxxxx
```

El jugueteo con **TTPassGen** es sencillo, creemos las combinaciones de la primera opcion para entender el funcionamiento:

```bash
ttpassgen --rule '1-721-[?d]{3:3:*}.[?d]{4:4:*}' sint_maarten_phones_wordlist.txt
```

* `1-721-`: Es un texto que vamos a concatenar a los resultados
* `?d`: [Igual que en el nivel uno](https://lanzt.github.io/thm/crackthehash), la **d** significa **dígitos** y al llamarla, devuelve **0123456789**
* `{...}`: Encerramos una condición que queremos que se cumpla
  * `3`: Le indicamos que el tamaño inicial va a ser de 3 dígitos
  * `3`: Le indicamos que el tamaño final va a ser de 3 dígitos (o sea, estamos limitando que solo queremos resultados de 3 dígitos en esta condición)
  * `*`: Permitimos que los caracteres se muestren de 0 a muchas veces, o sea, que se puedan repetir (para que sea secuencial)
* `.`: Texto que también vamos a concatenar
* Lo mismo de antes pero con distinta longitud

Revisamos lo que nos generó a ver si estoy diciendo la verdad:

```bash
➧ head sint_maarten_phones_wordlist.txt
1-721-000.0000
1-721-000.0001
1-721-000.0002
[...]
➧ tail sint_maarten_phones_wordlist.txt
[...]
1-721-999.9997
1-721-999.9998
1-721-999.9999
```

Listos, tenemos la lista, a romper...

### 🎩 **Cracking con John The Ripper**

---

```bash
john --wordlist=sint_maarten_phones_wordlist.txt --format=Raw-MD5 hash_ad6
```

Pero nop, no lo logramos con esta lista. Generamos y generamos hasta que conquistamos:

```bash
ttpassgen --rule '+1721[?d]{7:7:*}' sint_maarten_phones_wordlist.txt
```

```bash
john --wordlist=sint_maarten_phones_wordlist.txt --format=Raw-MD5 hash_ad6
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6-bash-john-cracked.png" style="width: 100%;"/>

...

Probando con máscaras también llegamos a crackearlo:

```bash
john --mask='+1721?d?d?d?d?d?d?d' --format=Raw-MD5 hash_ad6
```

### 🐈 **Cracking con Hashcat**

Realizando el mismo ataque usando la wordlist creada:

```bash
hashcat -a 0 -m 0 hash_ad6 sint_maarten_phones_wordlist.txt -o hash_ad6.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice6-bash-hashcat-cracked.png" style="width: 70%;"/>

## Advice n°7 [📌](#advice-7) {#advice-7}

---

### #️⃣ **Información del hash**

---

```txt
ba6e8f9cd4140ac8b8d2bf96c9acd2fb58c0827d556b78e331d1113fcbfe425ca9299fe917f6015978f7e1644382d1ea45fd581aed6298acde2fa01e7d83cdbd
```

Distinto, revisando con [haiti](https://noraj.github.io/haiti/#/):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice7-bash-haiti.png" style="width: 100%;"/>

[SHA-512](https://www.ciberseguridad.eus/ciberglosario/sha-512), pero tengamos en cuenta los demás.

### 💬 **Consejo y explicación**

Lo aconsejan de la siguiente forma:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice7.png" style="width: 100%;"/>

* Se llama **Justin Thyme**
* Dice que necesita una manera más robusta de guardar su contraseña que **no sea MD5** 🙊
* Y le recomiendan revisar la última competición del [proyecto NIST](https://www.nist.gov/)
* Así mismo le indican que no se refieren a **SHA-1**

Buscando en internet sobre el proyecto **NIST** (Instituto Nacional de Estándares y Tecnología) y que tenía que ver con una competición de criptografía, llegamos a este recurso:

* [Cryptographic Hash Algorithm Competition](https://www.nist.gov/programs-projects/cryptographic-hash-algorithm-competition)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice7-bash-hashcat-cracked.png" style="width: 100%;"/>

> Fue un taller que se hizo para que los usuarios probaran la seguridad de los algoritmos.

Mediante esta competición entre algoritmos, se decidió que el ganador era [KECCAK](https://keccak.team/keccak_specs_summary.html) y sería estandarizado como el nuevo [SHA-3](https://es.wikipedia.org/wiki/SHA-3).

> 🧽 "Keccak se basa en un enfoque novedoso llamado construcción de esponjas. La construcción de esponja se basa en una amplia función aleatoria o permutación aleatoria , y permite ingresar ("absorber" en la terminología de esponja) cualquier cantidad de datos, y generar (exprimir) cualquier cantidad de datos, mientras actúa como una función pseudoaleatoria con respecto a todas las entradas anteriores." ~ [wikipedia.org](https://es.wikipedia.org/wiki/SHA-3)

Pero ten en cuenta que **KECCAK** y **SHA-3** no son lo mismo, ya que *Keccak* es el algoritmo ganador y *Sha-3* es la versión estandarizada por el **NIST**.

* [https://www.cybertest.com/blog/keccak-vs-sha3](https://www.cybertest.com/blog/keccak-vs-sha3)

Por lo tanto, modificamos lo que habíamos encontrado y colocamos en primera posición a **SHA-3** como el formato usado.

Tenemos el hash y su formato, como esta vez no necesitamos (o no lo sabemos aún) crear una lista de palabras, jugaremos con la siempre fiel **rockyou.txt**.

### 🎩 **Cracking con John The Ripper**

---

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-SHA3 hash_ad7
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice7-bash-john-cracked.png" style="width: 100%;"/>

Reto fácil, pero no tan fácil :P

### 🐈 **Cracking con Hashcat**

El formato lo conocemos gracias a **haiti**, pero siempre puedes usar la ayuda de la herramienta y filtrar por el que necesitas.

```bash
➧ hashcat -h | grep -i sha
[...]
 17600 | SHA3-512 | Raw Hash
[...]
```

```bash
hashcat -a 0 -m 17600 hash_ad7 /usr/share/wordlists/rockyou.txt -o cracked.txt
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice7-bash-hashcat-cracked.png" style="width: 100%;"/>

## Advice n°8 [📌](#advice-8) {#advice-8}

---

### #️⃣ **Información del hash**

---

```bash
9f7376709d3fe09b389a27876834a13c6f275ed9a806d4c8df78f0ce1aad8fb343316133e810096e0999eaf1d2bca37c336e1b7726b213e001333d636e896617
```

[haiti](https://noraj.github.io/haiti/#/) nos indica que probablemente sea **SHA-512**, ya veremos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-bash-haiti.png" style="width: 100%;"/>

### 💬 **Consejo y explicación**

Y del consejo obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8.png" style="width: 100%;"/>

* Se llama **Robyn Banks**.
* Necesita una contraseña muuuuy fuerte.
* Y le aconsejan que tome una palabra de una web, que la repita unas 2, 3, 4 o 5 veces y que elija un algoritmo duro, hardcore, agresivo 😨
* Robyn les responde que tomará uno de los finalistas para ser **SHA-3** (la competición de la que hablamos en el reto anterior)
* Y que será el ganador de la **PHC** ([Password Hashing Competition](https://www.password-hashing.net/)) y que ese algoritmo usa [KDF](https://www.comparitech.com/blog/information-security/key-derivation-function-kdf/)
* También sabemos que sea el algoritmo que sea, es usado por [WireGuard](https://es.wikipedia.org/wiki/WireGuard)

Le aconsejaron usar la mutación **order**, la cual ya entendimos antes ¿la recuerdas?:

> Lista de [todas las mutaciones](https://www.elcomsoft.com/help/en/ewsa/dictionary_mutations.html).

La regla en este caso sería:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-google-hashcat-rules-duplicate.png" style="width: 100%;"/>

```bash
[List.Rules:Repiteme]
# DuplicaDuplica -una vez-
p1
# DuplicaDuplicaDuplica -dos veces-
p2
# DuplicDuplicDuplicaDuplica -tres veces-
p3
p4
p5
```

Ya tenemos la regla, indaguemos sobre el tipo de algoritmo usado.

> [KDF](https://www.comparitech.com/blog/information-security/key-derivation-function-kdf/) son partes importantes en la criptografia, ya que estas pueden usarse para dar origen a nuevos resultados desde llaves o valores complejos. Para más info visita [comparitech.com](https://www.comparitech.com/blog/information-security/key-derivation-function-kdf/)

Buscando cuál fue el ganador de la competición **PHC** encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-google-phc-winner.png" style="width: 100%;"/>

Nuestra opción se llama [Argon2](https://es.wikipedia.org/wiki/Argon2) y establece varias resistencias y optimizaciones con respecto al cracking realizado con GPU.

* [https://github.com/p-h-c/phc-winner-argon2](https://github.com/p-h-c/phc-winner-argon2)
* [https://github.com/P-H-C/phc-winner-argon2/blob/master/argon2-specs.pdf](https://github.com/P-H-C/phc-winner-argon2/blob/master/argon2-specs.pdf)

Por lo que movemos a primera posición a **Argon2** como nuestro formato. Nos queda sacar las palabras de la web y armar nuestro wordlist.

Supongamos que no tienes el laboratorio encendido, te voy a dejar el archivo `.html` del sitio de donde se debe obtener la palabra:

> [ad8-content.html](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/crackthehashlevel2/advice-8/ad8-content.html)

Lo colocamos en una ruta y en esa misma ruta levantamos un servidor web, en mi caso lo haré con **Python** (`python3 -m http.server`), ya con el archivo hosteado, aprovecharemos la herramienta [CeWL](https://github.com/digininja/CeWL) que lee un sitio web y según lo que le indiquemos, nos va a devolver las palabras encontradas:

```bash
cewl http://localhost:8000/ad8-content.html --with-numbers --depth 10 --write wordlist_ad8.txt
```

> Le decimos que nos extraiga tambien las palabras que tienen numeros, así mismo que profundice lo más que pueda y nos traiga todas toditas las palabras y que nos guarde el resultado en un archivo.

```bash
➧ cat wordlist_ad8.txt | head
and
the
Error
security
```

Listones.

### 🎩 **Cracking con John The Ripper**

El formato para **Argon2** en ***john*** es `argon2`, así que probemos:

```bash
john --wordlist=wordlist_ad8.txt --rule=Repiteme --format=argon2 hash_ad8
```

Nadita, nada de nada :/

Recordemos que uno de los consejos era que el algoritmo era tan fuerte que lo usaba [WireGuard](https://es.wikipedia.org/wiki/WireGuard), un software para intercambio de comunicaciones en redes privadas (VPN).

Visitando la [información que tiene **WireGuard** sobre la seguridad de sus protocolos](https://www.wireguard.com/protocol/), notamos una referencia a la función criptográfica [BLAKE2s](https://www.blake2.net/), la cual es usada para crear hashes (por lo general usados para verificar integridad). Esta también nos la mostró **haiti**.

Así que ojito, podemos probar con ella. [Que si profundizamos en la info sobre **Argon2**, notamos la referencia hacia **Blake2**](https://es.wikipedia.org/wiki/Argon2#Funci%C3%B3n_hash_de_longitud-variable):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-google-wikipedia-argon2-blake.png" style="width: 100%;"/>

🥵 Pero algo importante antes de seguir 🌡️

> ☀️ **BLAKE**, **SHA-256**, **MD5** y otras, son <u>funciones criptograficas para crear hashes</u>, peeeero **NO** son funciones destinadas a crear contraseñas ¿ay como así? Tranqui, <u>las funciones criptograficas</u> ayudan a verificar integridad, tanto de archivos como de mensajes, mejor dicho, cualquier entrada de datos. Por el otro lado <u>las funciones de contraseñas</u > estan creadas para ser lentas y seguras, estan adaptadas para que un atacante tenga que cansarse de intentar romperlas, ya que el procesamiento necesario es gigante. Algunos ejemplos son **Argon2** o **bcrypt**.

Incluso el mismo **Blake2** nos advierte:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-google-blake2-advertisement-about-hashing-password.png" style="width: 100%;"/>

Readys pa seguir...

El formato de **Blake2** (`john --list=formats | grep -i blake`) es `Raw-Blake2`:

```bash
john --wordlist=wordlist_ad8.txt --rule=Repiteme --format=Raw-Blake2 hash_ad8
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-bash-john-cracked.png" style="width: 100%;"/>

MATAUUU'

### 🐈 **Cracking con Hashcat**

Tomamos las mismas reglas de antes y creamos el archivo:

```bash
➧ cat my.rules
p1
p2
p3
p4
p5
```

Si recordamos el output de **haiti**, no nos indicaba uno para **Blake2**, aun así existe uno llamado `BLAKE2b-512` (revisa la ayuda de **hashcat**), pero al intentar:

```bash
hashcat -a 0 -m 600 hash_ad8 wordlist_ad8.txt -r my.rules -o hash_ad8.plain
```

No nos identifica el hash (`No hashes loaded.`). Buscando por internet y guiándonos de los [ejemplos de hashes que tiene hashcat](https://hashcat.net/wiki/doku.php?id=example_hashes), encontramos el formato correcto de los hashes **Blake2**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-google-hashcat-examples-blake2.png" style="width: 100%;"/>

Notamos que el ejemplo tiene `$BLAKE2$` antes del hash, así que démosle forma a nuestro hash y volvamos a intentar:

```bash
➧ cat hash_ad8.hashcat
$BLAKE2$9f7376709d3fe09b389a27876834a13c6f275ed9a806d4c8df78f0ce1aad8fb343316133e810096e0999eaf1d2bca37c336e1b7726b213e001333d636e896617
```

```bash
hashcat -a 0 -m 600 hash_ad8.hashcat wordlist_ad8.txt -r my.rules -o hash_ad8.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice8-bash-hashcat-cracked.png" style="width: 100%;"/>

> Siempre hay que buscar :P

## Advice n°9 [📌](#advice-9) {#advice-9}

---

### #️⃣ **Información del hash**

---

```txt
$6$kI6VJ0a31.SNRsLR$Wk30X8w8iEC2FpasTo0Z5U7wke0TpfbDtSwayrNebqKjYWC4gjKoNEJxO/DkP.YFTLVFirQ5PEh4glQIHuKfA/
```

Se vino uno agresivo 🤨 [haiti](https://noraj.github.io/haiti/#/) indica:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice9-bash-haiti.png" style="width: 100%;"/>

Este tipo de hash [ya lo vimos en el primer nivel](https://lanzt.github.io/thm/crackthehash#level2-3): `SHA-512 Crypt`, donde [SHA-512](https://www.ciberseguridad.eus/ciberglosario/sha-512) es el algoritmo y [Crypt](https://es.wikipedia.org/wiki/Sal_(criptograf%C3%ADa)) el uso de la [sal](https://keepcoding.io/blog/que-es-el-salting-en-criptografia/).

### 💬 **Consejo y explicación**

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice9.png" style="width: 100%;"/>

* **Warren Peace** indica que no es necesaria tanta cosa, que con un hash fuerte sumado a una sal, esa vaina es irrompible.

Veamos si es verdad...

Como vimos en el primer nivel, este tipo de algoritmo es pesado, duro, difícil, de romper (va teniendo razón **Warren**), ya que se puede configurar para que realice muuuchas iteraciones antes de devolver el hash, sumado a que tiene una sal fuerte (`kI6VJ0a31.SNRsLR`).

Así mismo, **john** y **hashcat** tienen la posibilidad de detectar automáticamente si un hash tiene **sal**, pero con algunos algoritmos no lo van a poder hacer, en nuestro caso no hay preocupación, ya que es un viejo conocido :P

### 🎩 **Cracking con John The Ripper**

Intentando la simple notamos que va muuuuuuuuuuuuuUUUy lento:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=sha512crypt hash_ad9
```

Por ende, optamos a indicarle a **john** que pruebe primero las palabras con 1 letra, después las que tienen 2 letras, las que tienen 3, etc. Para así ir descartando opciones:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --min-len=1 --max-len=1 --format=sha512crypt hash_ad9
john --wordlist=/usr/share/wordlists/rockyou.txt --min-len=2 --max-len=2 --format=sha512crypt hash_ad9
john --wordlist=/usr/share/wordlists/rockyou.txt --min-len=3 --max-len=3 --format=sha512crypt hash_ad9
[...]
```

Siguiendo las pruebas, al llegar a las palabras con 8 caracteres:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --min-len=8 --max-len=8 --format=sha512crypt hash_ad9
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice9-bash-john-cracked.png" style="width: 100%;"/>

Cuchau!

### 🐈 **Cracking con Hashcat**

Para jugar con la cantidad de caracteres debemos implementar una regla pequeña:

* [Rules used to reject plains](https://hashcat.net/wiki/doku.php?id=rule_based_attack#rules_used_to_reject_plains)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-google-hashcat-rule-reject-plains.png" style="width: 100%;"/>

La que necesitamos es `_N`, la cual rechaza cadenas que no sean iguales a **N**.

En la parte final nos indica que debemos usar `-j` o `-k` para implementar alguna de estas reglas.

> Con `-j` le indicamos que la regla será ejecutada <u>antes</u> de que la palabra sea procesada por **hashcat**, o sea, en su formato original. Y con `-k` lo que hará será ejecutar la regla (que asignemos) <u>al resultado obtenido por la regla</u> `-j`.

Eeeentonces:

```bash
hashcat -a 0 -m 1800 hash_ad9 /usr/share/wordlists/rockyou.txt -j '_8' -o hash_ad9.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehashlevel2/thmCrackthehashlevel2-reto-advice9-bash-hashcat-cracked.png" style="width: 100%;"/>

Y LISTOOOOOooo, hemos terminado 🏃‍♀️

...

Un laboratorio en general que me gustó mucho, el entender toooodo lo que se puede hacer con **john** y **hashcat** (y eso que hay cosas que no se usaron, pero son brutales).

El cómo una contraseña puede ser tan fácilmente bruteforceada si no se implementa un correcto algoritmo o al menos un sentido de seguridad.

Lindo lindo, espero te hayas divertido, hayas aprendido o reforzado cositas y te haya gustado (:

Nos leeremos prontico, muuuuchas gracias por pasarte y nada, a darle duro y a romper de todoooooo!!
