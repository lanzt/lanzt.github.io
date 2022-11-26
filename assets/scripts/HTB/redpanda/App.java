package com.logparser;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Scanner;

import com.drew.imaging.jpeg.JpegMetadataReader;
import com.drew.imaging.jpeg.JpegProcessingException;
import com.drew.metadata.Directory;
import com.drew.metadata.Metadata;
import com.drew.metadata.Tag;

import org.jdom2.JDOMException;
import org.jdom2.input.SAXBuilder;
import org.jdom2.output.Format;
import org.jdom2.output.XMLOutputter;
import org.jdom2.*;

public class App {
    public static Map parseLog(String line) {
        String[] strings = line.split("\\|\\|");              // Ejemplo: // 200||10.10.14.57||curl/7.84.0||/img/greg.jpg
        Map map = new HashMap<>();
        map.put("status_code", Integer.parseInt(strings[0])); // 200
        map.put("ip", strings[1]);                            // 10.10.14.57
        map.put("user_agent", strings[2]);                    // curl/7.84.0
        map.put("uri", strings[3]);                           // /img/greg.jpg

        return map;
    }

    public static boolean isImage(String filename){
        if(filename.contains(".jpg"))                         // Toma toda la cadena y busca si existe '.jpg' entre ella.
        {
            return true;
        }
        return false;
    }

    public static String getArtist(String uri) throws IOException, JpegProcessingException
    {
        String fullpath = "/opt/panda_search/src/main/resources/static" + uri;  // Toma ruta de imagenes, intentando LFI (../../../../../../ruta/distinta/del/sistema/con/imagen) no hace la parte de los views en addViewTo
                                                                                // - Si se intenta el LFI la toma y extrae el artista, podria hacer otro LFI en el artista para que abra un XML distinto:
                                                                                // -- default: artist=damian > path=/credits/damian_creds.xml | LFI: artist=../../tmp/hola > path=/credits/../../tmp/hola_creds.xml
        File jpgFile = new File(fullpath);
        Metadata metadata = JpegMetadataReader.readMetadata(jpgFile);
        for(Directory dir : metadata.getDirectories())
        {
            for(Tag tag : dir.getTags())
            {
                if(tag.getTagName() == "Artist")
                {
                    return tag.getDescription();
                }
            }
        }

        return "N/A";
    }

    public static void addViewTo(String path, String uri) throws JDOMException, IOException
    // path : /credits/damian_creds.xml
    // uri: Lo que enviamos como URL (/img/angy.jpg o /../../../../../../../tmp/angy.jpg)
    {
        SAXBuilder saxBuilder = new SAXBuilder();
        XMLOutputter xmlOutput = new XMLOutputter();
        xmlOutput.setFormat(Format.getPrettyFormat());

        File fd = new File(path);                           // path : /credits/damian_creds.xml

        Document doc = saxBuilder.build(fd);

        Element rootElement = doc.getRootElement();

        for(Element el: rootElement.getChildren())
        {
            if(el.getName() == "image")
            {
                if(el.getChild("uri").getText().equals(uri))
                {
                    Integer totalviews = Integer.parseInt(rootElement.getChild("totalviews").getText()) + 1;
                    System.out.println("Total views:" + Integer.toString(totalviews));
                    rootElement.getChild("totalviews").setText(Integer.toString(totalviews));
                    Integer views = Integer.parseInt(el.getChild("views").getText());
                    el.getChild("views").setText(Integer.toString(views + 1));
                }
            }
        }
        BufferedWriter writer = new BufferedWriter(new FileWriter(fd));
        xmlOutput.output(doc, writer);
    }

    public static void main(String[] args) throws JDOMException, IOException, JpegProcessingException {
        File log_fd = new File("/opt/panda_search/redpanda.log");
        Scanner log_reader = new Scanner(log_fd);
        while(log_reader.hasNextLine())                                    // Si existe otra linea despues de la actual entra.
        {
            String line = log_reader.nextLine();
            if(!isImage(line))
            {
                continue;
            }
            Map parsed_data = parseLog(line);                              // * Lo que devuelve: {status_code=200, ip=10.10.14.57, uri=/img/greg.jpg, user_agent=curl/7.84.0}
            System.out.println(parsed_data.get("uri"));                    // * /img/greg.jpg
            String artist = getArtist(parsed_data.get("uri").toString());  // * nombre del artista: damian - woodenk
            System.out.println("Artist: " + artist);
            String xmlPath = "/credits/" + artist + "_creds.xml";
            addViewTo(xmlPath, parsed_data.get("uri").toString());
        }

    }
}
