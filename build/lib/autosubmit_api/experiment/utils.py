
import xml.etree.ElementTree as ET
import traceback

def get_cas_user_from_xml(xmlstring):    
    """
    Parses xmlstring and looks for the user tag.
    
    :return: user  
    :rtype: str or None
    """
    try:
      root_node = ET.fromstring(xmlstring)
      user = None
      for child in root_node:        
          if child.tag == '{http://www.yale.edu/tp/cas}authenticationSuccess':
              for subchild in child:
                  if subchild.tag == '{http://www.yale.edu/tp/cas}user':
                      user = subchild.text
    except Exception as exp:
      print(exp)
      print(traceback.format_exc)
    return user