#!/usr/bin/python3

import base64

# private static string enc_password = "0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E";
enc_password = '0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E'
print("(+) Encoded Password: " + enc_password)

# private static byte[] key = Encoding.ASCII.GetBytes("armando");
key = b'armando'
print("(+) Key: armando")

def get_password():
    # byte[] array = Convert.FromBase64String(enc_password);
    # * Convert.FromBase64String = https://www.delftstack.com/es/howto/csharp/encode-and-decode-a-base64-string-in-csharp/#decodificar-una-cadena-de-una-cadena-base64-con-el-m%C3%A9todo-convert-frombase64string-en-c
    array = base64.b64decode(enc_password)

    # byte[] array2 = array; (array para ir agregando nuevos valores, en este caso lo hacemos VACIO)
    array2 = []

    for i in range(len(array)):
        # array2[i] = (byte)((uint)(array[i] ^ key[i % key.Length]) ^ 0xDFu);
        # * Hex to Dec :: 0xDFu == 223 > https://www.rapidtables.com/convert/number/ascii-hex-bin-dec-converter.html
        array2.append(chr((array[i] ^ key[i % len(key)]) ^ 223))

    return array2

print("(+) Decoded Password: " + ''.join(letter for letter in get_password()))
