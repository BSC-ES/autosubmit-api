
import subprocess
from typing import List
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
  # Submits the commands
  ls_process = subprocess.Popen(
    ['ls', '-t', dir_path],
    stdout=subprocess.PIPE
  )
  grep_process = subprocess.Popen(
    ['grep', pattern],
    stdin=ls_process.stdout,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
  )

  # Allow ls_process to receive a SIGPIPE if grep_process exits
  ls_process.stdout.close()

  # Read the output of grep
  stdout, _ = grep_process.communicate()
  
  stdout = stdout.decode()
  files = stdout.split()
  return files