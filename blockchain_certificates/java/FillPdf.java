import com.itextpdf.text.DocumentException;
import com.itextpdf.text.pdf.AcroFields;
import com.itextpdf.text.pdf.XfaForm;
//import com.itextpdf.text.pdf.BaseFont;
import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.PdfStamper;

import org.json.simple.JSONObject;
import org.json.simple.JSONArray;
import org.json.simple.parser.ParseException;
import org.json.simple.parser.JSONParser;
 
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Iterator;
 
public class FillPdf {
 
    //public static final String FONT = "/home/kostas/crypto/unic/blockchain-certificates/blockchain_certificates/java/FreeSans.ttf";
 
    public static void main(String[] args) throws Exception, IOException, ParseException {
	String pdfTemplateFile = args[0];
	String outputFile = args[1];
	String fieldsAsJsonString = args[2];
	boolean isXfaForm = false;
	if(args.length > 3) 
	    isXfaForm = "xfa".equals(args[3]);
	//System.out.println(fieldsAsJsonString);

	JSONParser parser = new JSONParser();
	Object obj = parser.parse(fieldsAsJsonString);
	JSONObject fieldsArray = (JSONObject) obj;

	if(!isXfaForm) 
	    fillInCertificates(pdfTemplateFile, outputFile, fieldsArray);
	else
	    fillInIndexXFA(pdfTemplateFile, outputFile, fieldsArray);
    }


    public static void fillInCertificates(String src, String dest, JSONObject fieldsArray) throws Exception, IOException, ParseException {
        PdfReader reader = new PdfReader(src);
        PdfStamper stamper = new PdfStamper(reader, new FileOutputStream(dest));
        AcroFields fields = stamper.getAcroFields();
        //BaseFont bf = BaseFont.createFont(FONT, BaseFont.IDENTITY_H, BaseFont.EMBEDDED, false, null, null, false);
        //fields.setFieldProperty("Name", "textfont", bf, null);
	
	for(Iterator iterator = fieldsArray.keySet().iterator(); iterator.hasNext();) {
	    String key = (String) iterator.next();
	    String value = (String) fieldsArray.get(key);
	    fields.setField(key, value);
	}
        stamper.setFormFlattening(true);
        stamper.close();
    }
    
    public static void fillInIndexXFA(String src, String dest, JSONObject fieldsArray) throws Exception, IOException, ParseException {
        PdfReader reader = new PdfReader(src);
        PdfStamper stamper = new PdfStamper(reader, new FileOutputStream(dest));
        AcroFields fields = stamper.getAcroFields();
	
	StringBuffer buf = new StringBuffer();
	buf.append("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n");
	buf.append("<form1><page1>");

	for(Iterator iterator = fieldsArray.keySet().iterator(); iterator.hasNext();) {
	    String key = (String) iterator.next();
	    String value = (String) fieldsArray.get(key);
	    buf.append("<" + key + ">");
	    buf.append(value);
	    buf.append("</" + key + ">\n");
	}
	buf.append("</page1></form1>");

	String xmlStr = buf.toString();
System.out.println(xmlStr);
	XfaForm xfa = fields.getXfa();
	xfa.fillXfaForm(new ByteArrayInputStream(xmlStr.getBytes()));

	fields.removeXfa();

        stamper.setFormFlattening(true);
        stamper.close();
	reader.close();
    }


}

