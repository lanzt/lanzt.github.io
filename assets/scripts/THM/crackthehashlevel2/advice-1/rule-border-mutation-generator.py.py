#!/usr/bin/python3

symbols = "[!@#$%^&*()+=.?]"
digits = "[0-9]"
rules = []

with open('rules-syntax.txt', 'r') as file_syntax:
    for line in file_syntax.readlines():

        try:
            line_before_pw = line.split('password')[0]
            line_after_pw = line.split('password')[1]
        except:
            continue

        for char in line_before_pw:
            if char == "!":
                rules.append("^" + symbols)
            elif char == "0":
                rules.append("^" + digits)

        for char in line_after_pw:
            if char == "!":
                rules.append("$" + symbols)
            elif char == "0":
                rules.append("$" + digits)

        print("# ----->", line.strip())
        print(' '.join(rules) + '\n')
        rules = []
