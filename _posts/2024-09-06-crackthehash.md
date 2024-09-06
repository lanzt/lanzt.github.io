---
layout      : post
title       : "TryHackMe - Crack the hash"
author      : lanz
footer_image: assets/images/footer-card/weak-security.png
footer_text : Cracking de contraseñas
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-banner.png
category    : [ thm ]
tags        : [ cracking, john, hashcat ]
---
Nos adentraremos en el mundo del descubrimiento de contraseñas, jugaremos con diccionarios, con máscaras, con reglas, ja, con todo!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-lab-information.png" style="width: 50%;"/>

## TL;DR (Spanish writeup)

**💥 Laboratorio creado por**: [ben](https://tryhackme.com/p/ben).

Ball-buster!

Nos colaremos por el grandioso mundo del cracking, de los ataques de fuerza bruta, de los ataques por diccionario, de las formas de crear infinidad de alternativas para romper contraseñas, si si si.

Vamos a jugar con las herramientas (famosas): **john the ripper** y **hashcat** para inmiscuirnos a la fuerza (🥁) en este lindo tema, usaremos cositas básicas, claro que sí, pero también lidiaremos con **máscaras** y con algunas **reglas** para llegar a tantos candidatos como podamos.

...

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

TMW.

1. [Introducción](#introduccion).
2. [Nivel 1](#level1).
  * [Nivel 1 - 1](#level1-1).
  * [Nivel 1 - 2](#level1-2).
  * [Nivel 1 - 3](#level1-3).
  * [Nivel 1 - 4](#level1-4).
  * [Nivel 1 - 5](#level1-5).
3. [Nivel 2](#level2).
  * [Nivel 2 - 1](#level2-1).
  * [Nivel 2 - 1](#level2-2).
  * [Nivel 2 - 1](#level2-3).
  * [Nivel 2 - 1](#level2-4).

...

# Introducción [#](#introduccion) {#introduccion}

**TryHackMe** nos propone este lab en el que podemos empezar a entrar en calor con el tema del [cracking de contraseñas](https://es.wikipedia.org/wiki/Descifrado_de_contrase%C3%B1a), para que podamos conocer toooodas sus opciones y diversiones :P

> Primero, algo de información rapída

Sabemos que en el mundo se guardan las contraseñas (o demás información) por lo general (quiero pensar) en formatos de hashes, ¿qué significa esto?: una función de hashing toma una entrada (la contraseña) y la convierte en un valor de longitud fija, que es prácticamente imposible de revertir.

Pero claro, eso no quiere decir que ya sea segura y que todos felices, nop, hay **demasiadas** formas de crear ese hash, o sea, **demasiadas** "valorizaciones" de seguridad, por lo que van a haber opciones menos seguras que otras 😭

Digamos que usamos el algoritmo de hash **más** robusto, pero revisamos la contraseña y literalmente es: "**hola**", pues de nada va a servir contar con un hash fuerte si la contraseña es débil.

Así que, si nos encontramos con el hash robusto del que hablamos, ¿qué necesitamos hacer para llegar a la conclusión de que la contraseña es **hola**? Debemos crear muuuuuuuuuuUUUchas opciones de contraseñas y usar herramientas automatizadas (**john** o **hashcat**, ya hablaremos de ellas) para que estas, a cada opción de contraseña le apliquen el algoritmo robusto, comparen ese resultado con el hash robusto que le pasamos y si en algún momento los dos valores de hash son iguales, quiere decir que ha encontrado el valor plano de esa contraseña, o seaaaaaa, **hola**.

Con todo esto dicho y entrados en calor, el laboratorio presenta dos niveles:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-lab-levels.png" style="width: 100%;"/>

El nivel 1 nos enfrenta con estos hashes:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-lab-level1-intro.png" style="width: 100%;"/>

Y el nivel 2 con estos hashes:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-lab-level2-intro.png" style="width: 100%;"/>

Así que dejemos de hablar y pongámonos a jugar (:

# Nivel 1 [#](#level1) {#level1}

---

## Nivel 1 - 1 [📌](#level1-1) {#level1-1}

El hash propuesto es este:

```txt
48bb6e862e54f2a795ffc4e541caed4d
```

Usando la herramienta [hash-identifier](https://www.kali.org/tools/hash-identifier/) (que por lo general ya está instalada en Kali Linux) podemos intentar comprobar con qué algoritmo fue creado el hash:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-1-bash-hash-identifier.png" style="width: 100%;"/>

El más probable es uno llamado [MD5](https://es.wikipedia.org/wiki/MD5), que seguramente lo has escuchado, lo usamos mucho para comprobar la integridad de un archivo al ser transferido (`md5sum`).

Este algoritmo anteriormente se usaba para el cifrado de datos (como en este ejercicio), pero en varios estudios se han [revelado vulnerabilidades](https://es.wikipedia.org/wiki/Colisi%C3%B3n_(hash)), así que lo mejor es no usarlo.

Procedamos a intentar algún match mediante fuerza bruta a ver si obtenemos la contraseña en texto plano. Aprovecharemos la oportunidad para conocer las dos herramientas más usadas en este ámbito, [John The Ripper](https://www.openwall.com/john/) y [hashcat](https://hashcat.net/hashcat/).

### 🎩 **John The Ripper**

**John** casi siempre necesita que le indiquemos con qué formato (algoritmo) fue creado el hash que va a intentar descifrar, por lo que primero debemos buscar en concreto el formato de **MD5**:

```bash
➧ john --list=formats | grep -i md5
[...]
Raw-MD5
[...]
```

Ya lo tenemos, lo siguiente es guardar el hash que queremos descubrir en un archivo, yo lo voy a llamar `hash`:

```bash
echo '48bb6e862e54f2a795ffc4e541caed4d' > hash
```

Y listo, tenemos lo necesario para ejecutar la fuerza bruta:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5 hash
```

Básicamente, estamos tomando una palabra de tooooda una [lista de palabras](https://www.keepersecurity.com/blog/es/2023/08/04/understanding-rockyou-txt-a-tool-for-security-and-a-weapon-for-hackers/) (`rockyou.txt`), esa palabra va a ser convertida a **MD5** y después comparada con nuestra cadena **MD5** (`hash`), si estos dos valores coinciden ¿qué significaría? Esato, que sabemos con qué palabra se ha generado ese **MD5**, por lo tanto conocemos la contraseña en texto plano.

Y al instante obtenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-1-bash-john-cracked.png" style="width: 100%;"/>

Y liiiistos, sencillo, peeeeero no siempre es así, vamos calentando (:

### 🐈 **Hashcat**

Igual que con **john**, tenemos que pasarle el tipo de hash (formato), podemos hacerlo de dos formas, por ahora usaremos la ayuda del propio comando:

```bash
hashcat -h
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-1-bash-hashcat-help-hash-modes.png" style="width: 20%;"/>

Y además, debemos indicarle el tipo de ataque que vamos a realizar, en este caso como jugaremos con un diccionario usaremos `0`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-1-google-hashcat-attack-modes.png" style="width: 100%;"/>

Por lo que, nuestro comando principal quedaría así:

```bash
hashcat --attack-mode 0 --hash-type 0 hash /usr/share/wordlists/rockyou.txt --outfile hash.plain
# or
hashcat -a 0 -m 0 hash /usr/share/wordlists/rockyou.txt -o hash.plain
```

Lo ejecutamos yyy:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-1-bash-hashcat-cracked.png" style="width: 100%;"/>

PERFECTO, primer reto completado y también logramos conocer las dos herramientas con las que jugaremos en todo el post, así que sigámosle pues!!

## Nivel 1 - 2 [📌](#level1-2) {#level1-2}

Este reto nos presenta el siguiente hash:

```bash
CBFDAC6008F9CAB4083784CBD1874F76618D2A97
```

Ahora usaremos la herramienta [hashid](https://www.kali.org/tools/hashid/) (también comúnmente instalada en Kali) para comprobar que tipo de algoritmo fue el usado sobre este hash:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-2-bash-hashid.png" style="width: 80%;"/>

El más probable es [SHA-1 (Secure Hash Algorithm)](https://en.wikipedia.org/wiki/SHA-1) de la familia [SHA](https://es.wikipedia.org/wiki/Secure_Hash_Algorithm), que generalmente lo encontramos como un número hexadecimal de 40 caracteres. Así mismo [se le han encontrado vulnerabilidades y no se recomienda su uso](https://www.schneier.com/blog/archives/2005/02/sha1_broken.html).

* [ciberseguridad.eus/ciberglosario/sha-1](https://www.ciberseguridad.eus/ciberglosario/sha-1)

Bien, procedamos al crackeito... Guardamos el hash en un archivo (igual que antes) y seguimos.

### 🎩 **John The Ripper**

Como dije antes, a veces **john** no va a lograr devolver un match si no se le indica que formato de hash se está pasando, peeeero a veces sí, las razones son varias:

* Porque la contraseña es muy fácil de descifrar.
* Porque el formato del hash es muy común.
* Porque **john** detecta el formato automáticamente.

Por lo que si ejecutamos la instrucción sin el formato:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt hash2
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-2-bash-john-without-format-cracked.png" style="width: 100%;"/>

Ya tendríamos la contraseña en texto plano (:

Peeeero ¿y si ahora quisiéramos volver a ejecutar el crackeo? ¿O si quisiéramos asignarle el formato y volver a ejecutar? Sucede que si lanzamos otra vez el comando no nos va a mostrar nada, ya que **john** ya lo crackeo y para evitar volver a gastar recursos del sistema usa un archivo donde guardar los hashes y sus resultados:

```bash
➧ cat ~/.john/john.pot 
$dynamic_26$cbfdac6008f9cab4083784cbd1874f76618d2a97:password123
```

Lo único que debemos hacer es borrar la línea relacionada a la tarea que queremos volver a ejecutar yyyy volver a ejecutar **john**:

```bash
➧ john --list=formats | grep -i SHA1
[...]
Raw-SHA1
[...]
```

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-SHA1 hash2
```

Si quisiéramos mostrar el resultado descubierto de ese hash sin visitar el archivo `john.pot`, únicamente debemos ejecutar:

```bash
➧ john --show hash2
?:password123
```

Sigamou!

### 🐈 **Hashcat**

Descubrimos el formato usando la ayuda de **hashcat**:

```bash
➧ hashcat -h | grep -i SHA
    100 | SHA1
    [...]
```

Y ejecutamos:

```bash
hashcat -a 0 -m 100 hash2 /usr/share/wordlists/rockyou.txt -o hash2.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-2-bash-hashcat-cracked.png" style="width: 100%;"/>

## Nivel 1 - 3 [📌](#level1-3) {#level1-3}

Ahora tenemos este hash:

```txt
1C8BFE8F801D79745C4631D09FFF36C82AA37FC4CCE4FC946683D7B336B63032
```

Si usamos un servicio web para descubrir que tipo de algoritmo fue usado, por ejemplo [Hash Analyzer](https://www.tunnelsup.com/hash-analyzer/), encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-3-google-hash-analyzer.png" style="width: 100%;"/>

Se usó [SHA2-256 (SHA-256)](https://es.wikipedia.org/wiki/SHA-2), el cual es un algoritmo robusto comparado a los anteriores, con algunas fallas, pero que aún se sigue implementando.

* [Info SHA-256](https://www.ciberseguridad.eus/ciberglosario/sha-256).

---

### 🎩 **John The Ripper**

Buscamos el formato:

```bash
➧ john --list=formats | grep -i 256 
[...]
Raw-SHA256
[...]
```

Y ejecutamos:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-SHA256 hash3
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-3-bash-john-cracked.png" style="width: 100%;"/>

### 🐈 **Hashcat**

Descubrimos formato:

```bash
➧ hashcat -h | grep -i 256
   1400 | SHA2-256
   [...]
```

```bash
hashcat -a 0 -m 1400 hash3 /usr/share/wordlists/rockyou.txt -o hash3.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-3-bash-hashcat-cracked.png" style="width: 100%;"/>

## Nivel 1 - 4 [📌](#level1-4) {#level1-4}

Nos enfrentamos a:

```txt
$2y$12$Dwt1BZj6pcyc3Dy1FWZ5ieeUznr71EeNkJkUlypTsgbX1H68wsRom
```

En este caso vamos a usar [unos ejemplos](https://hashcat.net/wiki/doku.php?id=example_hashes) (que me gustan mucho) de [hashcat](https://hashcat.net/wiki/doku.php?id=example_hashes) para identificar el formato usado.

* [https://hashcat.net/wiki/doku.php?id=example_hashes](https://hashcat.net/wiki/doku.php?id=example_hashes)

Entramos a los ejemplos y filtramos por el inicio de la cadena, o sea por `$2`, si revisamos atentamente, entre las opciones vemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-4-google-hashcat-examples.png" style="width: 100%;"/>

Puede ser **bcrypt** o **Blowfish**.

[Blowfish](https://es.wikipedia.org/wiki/Blowfish) es un algoritmo creado con el fin de reemplazar a [DES](https://es.wikipedia.org/wiki/Data_Encryption_Standard). No se han encontrado vulnerabilidades relevantes, dado que se le ha dado más importancia a otros algoritmos.

[bcrypt](https://en.wikipedia.org/wiki/Bcrypt) (algoritmo basado en **Blowfish**) entre varias cosas es adaptativo, permite asignar cuantas "veces" se quiere iterar para hacer la contraseña más segura, lo que significa mucho costo de cómputo para nosotros como atacantes, así queeeeee, nos tenemos que armar de paciencia y de conocimiento para evitar perder tiempo :P

Si nos fijamos en el ejemplo, está el número **3200**, sencillamente ese es el formato que usa **hashcat** para jugar con ese algoritmo (lo mismo que hacíamos con la **CLI**).

### 🎩 **John The Ripper**

Ya tenemos el formato en **hashcat** (3200), pero no en **john**, busquémoslo:

```bash
➧ john --list=formats | grep -i bcrypt
[...]
bcrypt
```

Y ejecutamos:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=bcrypt hash4
```

La cosa es que después de un buen rato no logramos obtener nada, y pues es sencillo de entender, como ya vimos, este algoritmo es difícil (lento) de crackear, así que o podemos esperar ooooo podemos empezar a filtrar (?)

Me refiero, y si tomamos el archivo `rockyou.txt` y extraemos únicamente las palabras que tengan 3 caracteres? Claramente tendríamos una lista muuucho más reducida con la cual jugar. Después, si no obtenemos nada, podemos tomar solo las palabras con 4 caracteres. Después las de 5 y así sucesivamente.

Para lograr eso podemos emplear [grep](https://www.freecodecamp.org/espanol/news/grep-command-tutorial-how-to-search-for-a-file-in-linux-and-unix-with-recursive-find/) y una expresión regular muy sencilla:

```bash
cat /usr/share/wordlists/rockyou.txt | grep -E '^.{2}$' > wordlist.txt
```

Donde:

* `^`: indica que la cadena empiece con...
* `.{N}`: toma N caracteres (excepto una nueva línea)
* `$`: indica que la cadena termine con...

O sea, leeremos el archivo `rockyou.txt`, filtraremos palabras que empiecen y terminen por 2 caracteres y guardaremos el resultado en el archivo `wordlist.txt`.

Obtenemos:

```bash
➧ cat /usr/share/wordlists/rockyou.txt | grep -E '^.{2}$' | head
me
hi
yo
no
```

Y finalmente ejecutamos:

```bash
john --wordlist=wordlist.txt --format=bcrypt hash4
```

Con 2 caracteres no obtenemos respuesta, con 3 tampoco, pero con 4 cambia la cosa:

```bash
cat /usr/share/wordlists/rockyou.txt | grep -E '^.{4}$' > wordlist.txt
john --wordlist=wordlist.txt --format=bcrypt hash4
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-4-bash-john-with-grep-cracked.png" style="width: 100%;"/>

Y ya tendríamos la contraseña en texto plano (:

Buscando en internet me di cuenta de que también se puede hacer directamente con **john**, simplemente usando `--min-len`/`-min-len`/`--min-length` y `--max-len`/`-max-len`/`--max-length`:

* [John the Ripper - filter-the-word-length-of-wordlists](https://exploit-notes.hdks.org/exploit/cryptography/tool/john-the-ripper/#filter-the-word-length-of-wordlists).

Así que en nuestro caso para extraer palabras con un máximo y mínimo de 4 caracteres, usamos:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --min-length=4 --max-length=4 --format=bcrypt hash4
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-4-bash-john-cracked.png" style="width: 100%;"/>

---

### 🐈 **Hashcat**

De antes ya contamos con el formato (3200), así que averigüemos como realizar el tema de las palabras con N caracteres...

* [https://hashcat.net/wiki/doku.php?id=rule_based_attack](https://hashcat.net/wiki/doku.php?id=rule_based_attack)

Si nos fijamos, hay un [apartado exclusivo para "rechazar" candidatos](https://hashcat.net/wiki/doku.php?id=rule_based_attack#rules_used_to_reject_plains):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-google-hashcat-rule-reject-plains.png" style="width: 100%;"/>

Pero antes de, ¿cómo así [ataque basado en reglas](https://hashcat.net/wiki/doku.php?id=rule_based_attack)? Profundicemos un poquito 😲

Como el propio [**hashcat** nos introduce](https://hashcat.net/wiki/doku.php?id=rule_based_attack), este método de ataque es el más "complicado", ya que las reglas se pueden usar para generar infinidad de candidatos a contraseña, por ejemplo hay reglas para: modificar partes exactas de una palabra, remover números de palabras, repetir las veces que queramos una palabra, en fin, muuuuuchas opciones personalizables.

Pero no tanto como para alarmarse, es como todo, práctica y más practica :P

Regresando a la imagen y la regla para rechazar candidatos, hay una para rechazar opciones que no sean iguales a **N** :o Pero revisando la letra pequeña (abajo), nos dice que estas reglas no funcionan como unas reglas normales de **hashcat** (usando un archivo, por ahora no nos interesan), sino que deben ser invocadas en el mismo comando, usando `-j` o `-k`, ¿como así? Sencillo:

```bash
➧ hashcat -h
[...]
 -j, --rule-left                | Rule | Single rule applied to each word from left wordlist  | -j 'c'
 -k, --rule-right               | Rule | Single rule applied to each word from right wordlist | -k '^-'
[...]
```

Con `-j` le indicamos que la regla será ejecutada **antes** de que la palabra sea procesada por **hashcat**, o sea, en su formato original. Y con `-k` lo que hará es ejecutar la regla (que asignemos) **al resultado obtenido por la regla** `-j`.

Así que ejecutamos:

```bash
hashcat -a 0 -m 3200 hash4 /usr/share/wordlists/rockyou.txt -j '_4' -o hash4.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-4-bash-hashcat-cracked.png" style="width: 100%;"/>

## Nivel 1 - 5 [📌](#level1-5) {#level1-5}

Descubrimos el formato:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-google-hash-analyzer.png" style="width: 100%;"/>

Puede ser tanto **MD4** como **MD5**.

[MD4](https://es.wikipedia.org/wiki/MD4) es un algoritmo antiguo al cual se le han descubierto colisiones de hashes calculadas a mano, por lo que no es recomendado usarlo. Y de **MD5** hablamos previamente (:

¡Así que rompamos esto pueeeees!!

### 🎩 **John The Ripper**

---

> Realmente quemé mucho tiempo, pero me sirvio para aprender más sobre las reglas y sobre un nuevo termino: las mascaras.

Sabemos que puede ser o **MD4** o **MD5**, así que tengámoslos en el radar (en mi caso no lo hice y me quede solo con **MD5** 🤗🤫)

Si probamos como hicimos con el primer ejercicio no logramos respuesta, así que como estamos hasta ahora entrando en calor, o jugamos con reglas o jugamos con máscaras :P

¿Mascarás? Aja:

El concepto es muy sencillo, usándolas nos podemos ahorrar un moooontón de tiempo comparado a los métodos tradicionales, ya que probamos toda la cantidad de opciones para una palabra, pero sabiendo que estamos probando y no al azar (como en un ataque de diccionario o de fuerza bruta).

Por ejemplo, usándolas podemos tomar una palabra y añadir un número al final, un número al inicio, que la primera letra sea en mayúscula, etc.

* [https://hashcat.net/wiki/doku.php?id=mask_attack](https://hashcat.net/wiki/doku.php?id=mask_attack)
* [https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK](https://github.com/openwall/john/blob/bleeding-jumbo/doc/MASK)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-google-john-mask-l-u-d-s-a.png" style="width: 100%;"/>

Entonces, digamos que queremos agregarle dígitos al final de cada una de las palabras de nuestro diccionario, podemos hacerlo de la siguiente forma.

🎯 Creamos diccionario:

```bash
echo "hola" > wordlist.txt
```

🎯 Jugamos con la máscara para mostrar la palabra tal cual, sin procesar ni intentar crackear:

```bash
➧ john --wordlist=wordlist.txt --mask='?w' --stdout
Using default input encoding: UTF-8
hola
```

🎯 Le indicamos que le agregue un dígito al final de cada palabra usando la máscara `?d`:

```bash
➧ john --wordlist=wordlist.txt --mask='?w?d' --stdout
Using default input encoding: UTF-8
hola1
hola0
hola2
hola3
hola9
hola8
hola5
hola4
hola6
hola7
```

Como último aprendizaje, digamos que queremos agregarle al inicio un dígito y después un carácter especial, además que al final haya una letra en mayúscula y también un carácter especial, ¿cómo sería?

```bash
➧ john --wordlist=wordlist.txt --mask='?d?s?w?u?s' --stdout
[...]
7|holaA.
1.holaE.
0.holaE.
2.holaE.
[...]
```

Siguiendo con el reto y recordando que tenemos dos posibles formatos (**MD5** y **MD4**), jugamos y jugamos con las máscaras, hasta queeeeee al agregar un dígito al final ob te ne moooos:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --mask='?w?d' --format=Raw-MD4 hash5
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-bash-john-cracked.png" style="width: 100%;"/>

> Se me fue la vida jugando con **MD5**, hasta que volví a los apuntes y dije "no puede seeeeer, no me vayas a salir con que es **MD4**", fui a probar y pumbale!

¡Tenemos la contraseña!!

### 🐈 **Hashcat**

Identificamos el formato:

```bash
➧ hashcat -h | grep -i md4
    900 | MD4
    [...]
```

Y buscando como jugar con las máscaras en **hashcat** encontramos:

* [https://hashcat.net/wiki/#core_attack_modes](https://hashcat.net/wiki/#core_attack_modes)
* [https://hashcat.net/wiki/doku.php?id=hybrid_attack](https://hashcat.net/wiki/doku.php?id=hybrid_attack)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-google-hashcat-attack-modes.png" style="width: 100%;"/>

Debemos usar el modo de ataque `6` (o sea: **wordlist + mask**) y como parte del comando indicar qué máscara implementar, en nuestro caso sería que agregara un dígito al final de la palabra:

```bash
hashcat -a 6 -m 900 hash5 /usr/share/wordlists/rockyou.txt '?d' -o hash5.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level1-5-bash-hashcat-cracked.png" style="width: 100%;"/>

...

**Listo, terminamos con el nivel 1, jugamos de varias formas y aprendimos, así que sigamos con el nivel 2 un poco más directo**.

...

# Nivel 2 [#](#level2) {#level2}

---

## Nivel 2 - 1 [📌](#level2-1) {#level2-1}

Nos encontramos a est@ loquit@:

```txt
F09EDCB1FCEFC6DFB23DC3505A882655FF77375ED8AA2D1C13F640FCCC2D0C85
```

Usando `hash-identifier` detectamos a `SHA-256` como el algoritmo más probable:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-1-bash-hash-identifier.png" style="width: 100%;"/>

Ya hablamos antes de este algoritmo, así que procedamos a romperlo.

### 🎩 **John The Ripper**

---

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-SHA256 hash6
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-1-bash-john-cracked.png" style="width: 100%;"/>

---

### 🐈 **Hashcat**

---

```bash
hashcat -a 0 -m 1400 hash6 /usr/share/wordlists/rockyou.txt -o hash6.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-1-bash-hashcat-cracked.png" style="width: 100%;"/>

Tranquilito y para toda la familia.

## Nivel 2 - 2 [📌](#level2-2) {#level2-2}

Tenemos:

```txt
1DFECA0C002AE40B8619ECF94819CC1B
```

Identificando el algoritmo usado mediante `hash-identifier` identificamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-2-bash-hash-identifier.png" style="width: 100%;"/>

Varias posibilidades, probando y probando, llegamos a info interesante de **NTLM** (además que su sintaxis (mayúscula) me lo recordó, pero igual con una búsqueda en internet basta):

* [LM, NTLM, Net-NTLMv2, oh my!](https://medium.com/@petergombos/lm-ntlm-net-ntlmv2-oh-my-a9b235c58ed4)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-2-google-petergombos-ntlm.png" style="width: 70%;"/>

Como vemos, también en su ejemplo el hash tiene mayúsculas (que no quiere decir 100% que sea **NTLM**, pero, pues es una característica a tener en cuenta).

[NTLM](https://es.wikipedia.org/wiki/NTLM) es un conjunto de protocolos de seguridad de **Microsoft**, usados para autenticación, integridad y confidencialidad. Se considera débil, ya que los ataques de fuerza bruta son muy comunes (y sencillos) actualmente.

### 🎩 **John The Ripper**

Revisando como podemos romper este algoritmo usando **john**, encontramos:

* [Using John The Ripper with LM Hashes](https://medium.com/secstudent/using-john-the-ripper-with-lm-hashes-f757bd4fb094).
* [How to Crack Passwords using John The Ripper](https://www.freecodecamp.org/news/crack-passwords-using-john-the-ripper-pentesting-tutorial/).

El formato es `NT`:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=NT hash7
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-2-bash-john-cracked.png" style="width: 100%;"/>

Liiistones.

### 🐈 **Hashcat**

Identificamos el formato:

```bash
➧ hashcat -h | grep -i nt
   [...]
   1000 | NTLM
   [...]
```

Y rompemos:

```bash
hashcat -a 0 -m 1000 hash7 /usr/share/wordlists/rockyou.txt -o hash7.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-2-bash-hashcat-cracked.png" style="width: 100%;"/>

Si si siiigamos.

## Nivel 2 - 3[📌](#level2-3) {#level2-3}

El reto se pone curioso:

```bash
Hash: $6$aReallyHardSalt$6WKUTqzq.UQQmrm0p/T7MPpMbGNnzXPMAXi4bJMl9be.cfi3/qxIf.hsGpS41BqMhSrHVXgMpdjS6xeKZAs02.
Salt: aReallyHardSalt
```

¿Sal? Entendamos:

La **sal** (salt) es simplemente un conjunto de bits aleatorios (debería ser así :P) que se usa junto a una contraseña para añadir seguridad a esta.

* [es.wikipedia.org/wiki/Sal(criptografía)](https://es.wikipedia.org/wiki/Sal_(criptograf%C3%ADa))
* [¿Qué es el salting en criptografía?](https://keepcoding.io/blog/que-es-el-salting-en-criptografia/)

Sencillito y para toda la familia.

Identificando el algoritmo mediante `hashid` y los ejemplos de `hashcat`, encontramos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-3-bash-hashid.png" style="width: 100%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-3-google-hashcat-examples-sha512crypt.png" style="width: 100%;"/>

Según nuestras dos fuentes, el algoritmo usado es **SHA-512 Crypt**, donde [SHA-512](https://www.ciberseguridad.eus/ciberglosario/sha-512) hace alusión al algoritmo en sí y [crypt](https://es.wikipedia.org/wiki/Sal_(criptograf%C3%ADa)) al uso de la sal. Por lo que se convierte en un algoritmo robusto siempre y cuando se configure con varias iteraciones y su sal sea aleatoria y fuerte. Pero aun así existen mejores alternativas a usar.

Pero, probablemente te preguntes... ¿cómo le indicamos a **john** y a **hashcat** que le vamos a pasar una "sal"? Bueno, cada una tiene sus formas, indaguémoslas.

### 🐈 **Hashcat**

Deambulando por el [foro de **hashcat**, uno de los moderadores escribe](https://hashcat.net/forum/thread-10645.html):

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-3-google-hashcat-forum-salt-already-in-hash.png" style="width: 100%;"/>

Así que únicamente debemos tomar el hash (que como vemos en este formato, la sal ya está agregada) y crear el comando:

> Este algoritmo tambien es dificil de crackear, así que para ir descartando candidatos, filtraremos por cantidad de letras (como antes).

Es hasta que probamos con palabras de 6 caracteres queeeeee:

```bash
hashcat -a 0 -m 1800 hash8 /usr/share/wordlists/rockyou.txt -j '_6' -o hash8.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-3-bash-hashcat-cracked.png" style="width: 100%;"/>

:P

### 🎩 **John The Ripper**

Con **john** también va a detectar (según el algoritmo) la "sal" si es que la tiene, en caso de que no, tendremos que jugar con **subformatos**, peeero, eso lo veremos después (quizá :D).

Así que simplemente descubrimos el formato:

```bash
➧ john --list=formats | grep -i crypt 
[...]
sha512crypt
[...]
```

Y armamos el comando final:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --min-len=6 --max-len=6 --format=sha512crypt hash8
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-3-bash-john-cracked.png" style="width: 100%;"/>

Pa lante...

## Nivel 2 - 4 [📌](#level2-4) {#level2-4}

Volvemos a enfrentarnos a una **sal**:

```txt
Hash: e5d8870e5bdd26602cab8dbe07a942c8669e56d6
Salt: tryhackme
```

Peeero, no la vemos unida al hash... No te preocupes, ya exploraremos.

Usando **hash-identifier** sabemos que el algoritmo usado es `SHA-1`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-4-bash-hash-identifier.png" style="width: 100%;"/>

Metámonos con cada herramienta y veamos como usarlas para romper este hash.

### 🐈 **Hashcat**

Con ayuda de los ejemplos de **hashcat** notamos varias cositas:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-4-google-hashcat-examples.png" style="width: 100%;"/>

* Hay varios formatos relacionados.
* Sabemos como es la sintaxis para indicar un **hash** + una **sal**.

Así que modifiquemos el archivo para que quede de la siguiente forma:

```bash
➧ cat hash9salt
e5d8870e5bdd26602cab8dbe07a942c8669e56d6:tryhackme
```

Y empecemos a probar:

```bash
hashcat -a 0 -m 110 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
hashcat -a 0 -m 120 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
hashcat -a 0 -m 130 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
hashcat -a 0 -m 140 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
hashcat -a 0 -m 150 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
hashcat -a 0 -m 160 hash9salt /usr/share/wordlists/rockyou.txt -o hash9.plain
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-4-bash-hashcat-cracked.png" style="width: 100%;"/>

Ajaaaai, el formato correcto es `HMAC-SHA1` con la **sal** como llave.

* [HMACSHA1](https://learn.microsoft.com/es-es/dotnet/api/system.security.cryptography.hmacsha1?view=net-8.0)
* ["Why is HMAC-SHA1 still considered secure?"](https://crypto.stackexchange.com/questions/26510/why-is-hmac-sha1-still-considered-secure)
* [HMAC](https://es.wikipedia.org/wiki/HMAC)

Este algoritmo se considera seguro, pero no es la mejor opción para usar hoy en día, ya que existen **HMAC-SHA256** o **HMAC-SHA3** como alternativas.

Intentemos con **john**.

### 🎩 **John The Ripper**

En **john** no encontramos ese formato:

```bash
john --list=formats | grep -i SHA1
```

Más sin embargo, al probar con subformatos, vemos algunas opciones (pero ninguna relacionada con **HMAC**):

```bash
john --list=subformats | grep -i SHA1
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-4-bash-john-subformats-grep-sha1.png" style="width: 100%;"/>

Por ejemplo, podríamos probar la `dynamic_24` o la `dynamic_25`:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=dynamic_24 hash9salt
```

Pero nadita.

Buscando, encontramos la sintaxis correcta para indicar hashes con sal:

* [github.com/openwall/john/doc/DYNAMIC](https://github.com/openwall/john/blob/bleeding-jumbo/doc/DYNAMIC)

El archivo debe estar así:

```bash
userID:$dynamic_#$base_16_hash[$salt]
```

Por lo que, si organizamos el archivo para usar los subformatos `dynamic_24` y `dynamic_25`, generaríamos:

```bash
➧ cat hash9salt_dynamic_john
carlitos:$dynamic_24$e5d8870e5bdd26602cab8dbe07a942c8669e56d6$tryhackme

john --wordlist=/usr/share/wordlists/rockyou.txt --format=dynamic_24 hash9salt_dynamic_john
```

```bash
➧ cat hash9salt_dynamic_john
carlitos:$dynamic_25$e5d8870e5bdd26602cab8dbe07a942c8669e56d6$tryhackme

john --wordlist=/usr/share/wordlists/rockyou.txt --format=dynamic_25 hash9salt_dynamic_john
```

Peeeeero tampoco obtenemos resultado.

Divagando por la web, desde el foro oficial de **john** nos aclaran todo:

* ["cracking HMAC-SHA1 (key=salt)"](https://www.openwall.com/lists/john-users/2020/11/27/2)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/crackthehash/thmCrackthehash-level2-4-google-john-forum-hmacsha1-keysalt-issue.png" style="width: 100%;"/>

Así que pailangas, no vamos a poder crackearlo, por la sencilla razón de que no han implementado el formato en **john** /: Lo bueno es que contamos con dos herramientas y una de ellas nos sirvió 🥳

...

Y liiiiiisto, finalizamos el camino de la crackeazion :P Me gustó el entorno, además nos sirvio para jugar con varias herramientas y empezar a meternos con reglas, mascarás, subformatos y demás cositas.

Espero me haya hecho entender y que hayas aprendido o reforzado el tema (:

Nos leeremos por ahí, estate atento a la segunda parte que está 🔥 Abrazitos y a seguir rompiendo de todooooooooo!!