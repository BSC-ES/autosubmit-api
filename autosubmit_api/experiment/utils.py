
import subprocess
from typing import List
import xml.etree.ElementTree as ET
import traceback
from pathlib import Path

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
      print((traceback.format_exc))
    return user

def read_tail(file_path: str, num_lines: int =150) -> List[dict]:
    """
    Reads the last num_lines of a file and returns them as a dictionary.
   
    :param file_path: path to the file
    :param num_lines: number of lines to read
    """
    tail_content = []

    lines = subprocess.check_output(
        ["tail", "-{0}".format(num_lines), file_path], text=True
    ).splitlines()

    for i, item in enumerate(lines):
        tail_content.append({"index": i, "content": item})

    return tail_content

def get_files_from_dir_with_pattern(dir_path: str, pattern: str) -> List[str]:
  """
  Returns a list of files ordered by creation date in a directory that match a pattern.
  """
  path = Path(dir_path)
  files = sorted(
    [file for file in path.glob(f"*{pattern}*")],
    key=lambda x: Path(x).stat().st_mtime,
    reverse=True
  )
  files = [file.name for file in files]
  return files
