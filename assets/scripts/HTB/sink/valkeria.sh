#!/bin/bash

# Generamos el archivo con las keys
aws --endpoint-url=http://localhost:4566 kms list-keys | grep KeyId | cut -d '"' -f 4 > keys.tmp
file_with_keys=./keys.tmp
types_algorithms=( SYMMETRIC_DEFAULT RSAES_OAEP_SHA_1 RSAES_OAEP_SHA_256 )

while read keyId; do
        echo -e "\n[+++] Llave: $keyId:"
        for algorithm in "${types_algorithms[@]}"; do
                echo -e "[*] Algoritmo: $algorithm"
                # Habilitamos la llave
                aws --endpoint-url=http://localhost:4566 kms enable-key --key-id "$keyId" 2>/dev/null

                # Desencriptamos el archivo servers.enc
                aws --endpoint-url=http://localhost:4566 kms decrypt --key-id "$keyId" --ciphertext-blob fileb:///home/david/Projects/Prod_Deployment/servers.enc --output text --query Plaintext --encryption-algorithm $algorithm
        done
done < $file_with_keys

shred -zun 10 $file_with_keys
