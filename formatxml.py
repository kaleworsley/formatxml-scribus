#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

try:
   # Please do not use 'from scribus import *' . If you must use a 'from import',
   # Do so _after_ the 'import scribus' and only import the names you need, such
   # as commonly used constants.
   import scribus
except ImportError, err:
   print "This Python script is written for the Scribus scripting interface."
   print "It can only be run from within Scribus."
   sys.exit(1)

import xml.sax
import xml.sax.handler

class XMLFormatter (xml.sax.handler.ContentHandler):
   """Formats xml in scribus document
   Every text node including whitespace is placed in the document
   Paragraph styles are applied through an attribute sla:style in the namespace "http://www.scribus.net/formatxml".
   Character styles are applied through the attribute sla:override in the same namespace
   Paragraph and character styles are inherited automatically"""

   def __init__ (self):
       self.styles = [None]
       self.overrides = [None]
       self.template = ""
       self.document = ""
       self.name = ""
       self.in_namespace = False
       self.prefix = None
       self.first = True

   def make_textframe (self):
       margins = scribus.getPageMargins()
       size = scribus.getPageSize()
       w = size[0] - margins[1] - margins[3]
       h = size[1] - margins[0] - margins[2]
       return scribus.createText (margins[1], margins[0], w, h)
       
   def startPrefixMapping(self, prefix, uri):
       """checks if current node is in proper namespace"""
       if uri == "http://www.scribus.net/formatxml":
           self.in_namespace = True
           if prefix != "":
               self.prefix = prefix + ":"
               
   def endPrefixMapping(self, prefix):
       """signal that we are no longer in namespace"""
       if self.in_namespace:
           self.in_namespace = False
           self.prefix = None
       
   def startDocument(self):
       """Open document"""
       scribus.openDoc(self.template)
       self.name = self.make_textframe()
       
   def add_style (self, stack, style):
       if style == None:
           style = stack[-1]
       stack.append(style)
               
   def startElementNS(self, name, qname, attrs):
       """record styles or overrides"""
       attrs_names = attrs.getQNames()
       if self.in_namespace:
           if self.prefix + "style" in attrs_names:
               style = attrs.getValueByQName(self.prefix + "style")
           else:
               style = None
           self.add_style(self.styles, style)
           if self.prefix + "override" in attrs_names:
               override = attrs.getValueByQName(self.prefix + "override")
           else:
               override = None
           self.add_style(self.overrides, override) 
       
   def endElementNS(self, name, qname):
       self.styles.pop()
       self.overrides.pop()
       
   def shouldSetStyle (self):
       if self.first:
           return True
       else:
           return scribus.getAllText(self.name)[-1] == "\r"
       
   def characters(self, content):
       """place text, apply style"""
       start = scribus.getTextLength(self.name)
       go_ahead = self.shouldSetStyle()
       scribus.insertText (content, -1, self.name)
       scribus.selectText(start, len(content), self.name)
       if self.styles[-1] != None and go_ahead:
           try:
               scribus.setStyle(self.styles[-1], self.name)
           except scribus.NotFoundError:
               scribus.createParagraphStyle(self.styles[-1])
               scribus.setStyle(self.styles[-1], self.name)
       if self.overrides[-1] != None:
           try:
               scribus.setFont(self.overrides[-1], self.name)
           except ValueError:
               pass
       self.first = False
       
   def flow(self):
       while(scribus.textOverflows(self.name) > 0 and scribus.getTextLines(self.name)):
           current = self.name
           scribus.newPage(-1)
           scribus.gotoPage( scribus.pageCount() )
           self.name = self.make_textframe()
           scribus.linkTextFrames(current, self.name)

   def endDocument(self):
       """Save and close document"""
       self.flow()
       scribus.saveDocAs(self.document)
       scribus.closeDoc()
#end class XMLFormatter    

class UserCanceled (Exception):
   pass
#end class UserCanceled

def format(xml_file, scribus_template, document):
   fmt = XMLFormatter ()
   fmt.template = scribus_template
   fmt.document = document
   p = xml.sax.make_parser()
   p.setFeature(xml.sax.handler.feature_namespaces, True)
   p.setContentHandler(fmt)
   p.parse(xml_file)

def getFile(caption, filter, defaultname, issave):
   file = scribus.fileDialog(caption, filter, defaultname, issave)
   if len(file) == 0:
       raise UserCanceled("canceled")
   else:
       return file

def main():
   """Formats xml file using Scribus template"""
   try:
       xml_file = getFile("XML File", 'XML (*.xml)')
       template = getFile("Scribus template", "Scribus document (*.sla)")
       document = getFile("Save document", "Alles (*.*)", xml_file.replace(".xml", ".sla"), False, True)
       format (xml_file, template, document)
   except UserCanceled:
       pass
   except xml.sax.SAXParseException:
       scribus.messageBox("XML Error", "XML Error: please check your document")
   
def main_wrapper():
   """The main_wrapper() function disables redrawing, sets a sensible generic
   status bar message, and optionally sets up the progress bar. It then runs
   the main() function. Once everything finishes it cleans up after the main()
   function, making sure everything is sane before the script terminates."""
   try:
       scribus.statusMessage("Running script...")
       scribus.progressReset()
       main()
   finally:
       # Exit neatly even if the script terminated with an exception,
       # so we leave the progress bar and status bar blank and make sure
       # drawing is enabled.
       if scribus.haveDoc():
           scribus.setRedraw(True)
       scribus.statusMessage("")
       scribus.progressReset()

# This code detects if the script is being run as a script, or imported as a module.
# It only runs main() if being run as a script. This permits you to import your script
# and control it manually for debugging.
if __name__ == '__main__':
   main_wrapper()
