---
layout      : post
title       : "Ocultando data en archivos de Windows (con ADS)"
author      : lanz
date        : 2021-06-15 23:35:10
image       : https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_banner.png
categories  : [ article ]
tags        : [ ADS ]
---
Jugaremos con **Alternate Data Stream** o flujos de datos alternativos, veremos como un atacante (o víctima) puede ocultar información dentro de archivos ya sea para asegurarlos o para hacer locuras.

...

Menú del día e.e

1. [Entramos en m4t3r1a sobre los ADS](#teoria-ads).
2. [Ocultando información mediante los ADS](#hide-with-ads).
  * [Ocultando texto](#hide-text-with-ads).
  * [Ocultando binarios](#hide-bin-with-ads).
3. [Detectando archivos con ADS](#detect-ads).

...

## Entramos en m4t3r1a sobre los ADS [#](#teoria-ads) {#teoria-ads}

Este artículo esta más enfocada en como detectar (ver, encontrar, etc.) los **ADS** en archivos. No daré taaaaanta teoría, pondré un recurso que la tiene (y que tiene muuuchas cositas), veremos más que todo ejemplos en la terminal y cosas directas.

...

Flujos de datos alternativos, también llamados **ADS** (Alternate Data Stream). Básicamente son una característica de los ficheros [**NTFS**](https://www.ionos.es/digitalguide/servidores/know-how/ntfs/#:~:text=NTFS%20son%20las%20siglas%20de,y%20otros%20soportes%20de%20almacenamiento.) (sistema que sirve para organizar datos en discos duros y medios de almacenamiento) que permiten almacenar **metadatos** en archivos sin tener que separar esos metadatos (crear otros archivos aparte) del objeto.

* [Alternate Data Stream](https://es.wikipedia.org/wiki/Alternate_Data_Streams).

Recurso con baaaaaste más teoría e inspiración para hacer este pequeño articulo:

* [Flujos de datos alternativos en **Windows**](http://www.christiandve.com/2017/06/flujos-alternativos-datos-alternate-data-streams-windows-ads/).

La parte teórica es muy sencilla, un archivo en el cual podemos esconder cosas, ¿qué puede salir de eso? 

Pues desde la mirada de un atacante puede ser genial tener esta opción en un sistema, ya que:

1. Es "complicado" para la víctima encontrar los **ADS** si no sabes que existen (como muchas personas).
  * No es un archivo oculto, nop, es un archivo oculto dentro de otro 😝
2. Es divertido su uso.
3. No son visibles con facilidad, solo usando software especial para ello.
4. Los ficheros ocultos no modifican el tamaño del objeto real :O
3. Es muuuuuy sencillo de implementar.

Vamos a ver algunos ejemplos sencillos para entender como funciona y despues la manera de detectarlos o encontrarlos...

...

## Ocultando información mediante los ADS [#](#hide-with-ads) {#hide-with-ads}

...

### Ocultando texto [⌖](#hide-text-with-ads) {#hide-text-with-ads}

Hacer esto es muy simple, usando el comando [type](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/type) junto a los símbolos `>` (encargado de direccionar el flujo) y `:` (el encargado de unir un archivo a otro), veamos:

> Create `type textfile > visible.txt:hidden.txt` [Alternate Data Stream](https://www.sciencedirect.com/topics/computer-science/alternate-data-stream).

Por ejemplo, guardemos un archivo con contraseñas dentro de otro con un simple texto:

**credentials.txt:**

![ads_type_credentials](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_type_credentials.png)

**algorandom.txt:**

![ads_type_algorandom](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_type_algorandom.png)

Bien, pues ahora unámoslos:

```powershell
C:\Users\shxcx\ads_omg>type credentials.txt > algorandom.txt:creds.txt
```

Donde le indicamos que tome el contenido de `credentials.txt` y cree un **ADS** en el archivo `algorandom.txt` llamado `creds.txt`...

![ads_addADS_credsTXT](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_addADS_credsTXT.png)

¿Pero como validamos ahora lo insertado? Bien, con un simple [more](https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/more) podemos ver su contenido:

Viendo como lo vería un usuario normal:

![ads_more_algorandomNORMAL](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_more_algorandomNORMAL.png)

Jugando con el contenido que agregamos:

![ads_more_algorandomADS](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_more_algorandomADS.png)

Le estamos indicando que nos extraiga el **ADS** `creds.txt` del objeto (:

Perfecto, en ese caso borraríamos el archivo `credencials.txt` y podríamos jugar con `algorandom.txt` por la vida e.e 

**Antes de seguir me gustaría mostrarles que no es necesario que exista ningún archivo, ya que con el comando `echo` podemos escribir cualquier cadena y guardarla también en un ADS**:

Por ejemplo, otras credenciales:

![ads_createADSwithECHO](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_createADSwithECHO.png)

Y en su contenido:

![ads_moreADSwithECHOdone](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_moreADSwithECHOdone.png)

Podemos ver el contenido también con `type` y no habría nada raro (:

![ads_type_algorandom_afterADSs](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_type_algorandom_afterADSs.png)

...

**O** con un archivo que no exista sería algo asi, primero listamos (pa comprobar):

![ads_createADSahoraexiste](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_createADSahoraexiste.png)

Yyyy:

![ads_createADSahoraexiste_dir](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_createADSahoraexiste_dir.png)

![ads_createADSahoraexiste_more_type](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_createADSahoraexiste_more_type.png)

Listones, con esto ya se tendría una idea de tooooooooodo lo que podemos hacer para guardar texto en objetos...

...

### Ocultando binarios [#](#hide-bin-with-ads) {#hide-bin-with-ads}

En **WinXP** por ejemplo para guardar el binario `nc.exe` en el archivo `algorandom.txt` seria:

![ads_ncEXEads_algorandom](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_ncEXEads_algorandom.png)

Y para su ejecucion:

```powershell
C:\Users\shxcx\ads_omg>start algorandom.txt:nc.exe
```

Sencillito, **peeeeeeeeeero en sistemas operativos más actuales debemos hacer unos pasos de más:**

> [Obtenidos del recurso con el que hemos jugado todo el articulo](http://www.christiandve.com/2017/06/flujos-alternativos-datos-alternate-data-streams-windows-ads/).

Necesitamos generar 3 pasos despues de tener un binario oculto en algún objeto:

1. Crear un link simbólico que apunte al **ADS** generado (al objeto oculto).
2. Tomar ese link simbólico y crear el objeto que estamos restaurando.
3. Ejecutar el objeto.

Veamos cada paso con algo más de detalle:

Digamos que ocultamos `nc.exe` en `algorandom.txt:nc.exe`:

```powershell
C:\Users\shxcx\ads_omg>type C:\Users\shxcx\nc.exe algorandom.txt:nc.exe
```

<span style="color:yellow;">1. </span>Ahora deberíamos generar el link simbólico con un nombre distinto a `nc.exe`:

![ads_mklink_netcat](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_mklink_netcat.png)

Validamos:

![ads_dir_mklink](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_dir_mklink.png)

<span style="color:yellow;">2. </span>Luego tomaríamos el contenido de ese link simbólico (que sería el contenido del binario) y lo guardamos en un archivo (por ejemplo con el nombre del objeto oculto), en mi caso `nc.exe`:

![ads_type_ncEXE](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_type_ncEXE.png)

<span style="color:yellow;">3. </span>Y ahora simplemente deberíamos ejecutar el archivo creado (`nc.exe` contra una IP y un puerto), en mi caso obtendríamos:

![ads_ncEXE_done](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_ncEXE_done.png)

**(Da timeout porque esa IP no esta activa, pero la finalidad es que tenemos el binario `nc.exe` funcional)**

Entonces, en resumen es muy simple:

1. Ocultas (u obtienes un archivo con un binario oculto) el binario en un objeto cualquiera.
2. Generas un link simbólico hacia ese **ADS**.
3. Con el link simbólico creado, generas lo que sería el "recovery" del binario original.
4. Ejecutar (: 

😮

...

## Encontrando/Detectando ADS [#](#detect-ads) {#detect-ads}

Esta es la parte más sencilla, hay varias herramientas, [como las de este hilo](https://security.stackexchange.com/questions/34168/how-can-i-identify-discover-files-hidden-with-ads), pero destacaremos 3:

* [lads.exe](https://github.com/lanzt/blog/tree/main/assets/files/articles/ADS-Windows/lads.exe).
* [streams.exe](https://github.com/lanzt/blog/tree/main/assets/files/articles/ADS-Windows/streams.exe).
* `dir /r`.

Las 3 son directas, juguemos:

### lads.exe

Le podemos pasar el directorio donde esta el archivo (o los) a consultar y nos imprimiría:

![ads_lads_findads](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_lads_findads.png)

Perfecto, ya veríamos tooodos los archivos que tienen **ADS**...

### streams.exe

Su uso seria:

![ads_streams_usage](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_streams_usage.png)

Es más útil, ya que podemos borrar **ADS** de archivos, hacer la búsqueda recursivamente o por archivos específicos:

**Recursivamente:**

![ads_streams_recursive](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_streams_recursive.png)

Vemos también tooodos los archivos con **ADS** encima, ahora enfoquémonos en uno:

![ads_streams_algorandom](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_streams_algorandom.png)

Perfecto, así que si tuviéramos sospecha de algún archivo podríamos ir tras él :P

Y la más sencilla (que en algunos sistemas operativos no esta activa):

### dir /r

Usando el propio comando genérico podemos también ver si existen **ADS** en archivos:

![ads_dirR_recursive](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_dirR_recursive.png)

Así mismo podemos hacer más pequeña nuestra búsqueda haciéndolo con cada archivo:

![ads_dirR_algorandom](https://raw.githubusercontent.com/lanzt/blog/main/assets/images/articles/ADS-Windows/ads_dirR_algorandom.png)

YYYYYYYYYYYYYy ia (:

...

Fue algo que descubrí en la máquina **Dropzone** y me gusto mucho... Además que es superútil y llamativo, en cualquier momento puede ser necesario y es muy fácil de usar :P

Y bueno, como digo siempre en los *writeups*, a seguir con toda y a romper todo!!