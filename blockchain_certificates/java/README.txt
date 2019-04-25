- Creating the actual certificates by populating a template from a CSV is optional.
  . we do not bundle the libraries that are needed
  . those interested need to download two java libraries: itextpdf-5.5.10.jar and json-simple-1.1.1.jar
  . and take note of their appropriate licenses

- If you decide to use them you need to get the source code from github and place the jars in the blockchain_certificates/java directory

- To compile, the code that populates pdfs download and place the jars in the appropriate directory and:

  $ javac -cp .:itextpdf-5.5.10.jar:json-simple-1.1.1.jar  FillPdf.java

  from this directory 
