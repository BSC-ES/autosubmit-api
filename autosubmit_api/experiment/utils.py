import os
import subprocess
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
import lzma
import gzip


XZ_MAGIC = "FD 37 7A 58 5A 00"
GZIP_MAGIC = "1F 8B"


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


def is_safe_normpath(basedir: str, path: str) -> bool:
    """
    Check if a path is inside a basedir after normalization.
    Basedir and path as absolute, normalized.
    """
    basedir = os.path.abspath(basedir)
    path = os.path.abspath(os.path.normpath(path))
    return os.path.commonpath([basedir, path]) == basedir


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


def is_xz_file(filepath: str) -> bool:
    with open(filepath, "rb") as f:
        magic = f.read(6)
    return magic == bytes.fromhex(XZ_MAGIC)


def is_gzip_file(filepath: str) -> bool:
    with open(filepath, "rb") as f:
        magic = f.read(2)
    return magic == bytes.fromhex(GZIP_MAGIC)


def decompress_lzma_tailed(input_path: str, tail_lines: int = 150) -> List[dict]:
    """
    Decompresses the last tail_lines of a lzma compressed file.
    It buffers the lines in memory to avoid decompressing the entire file.

    :param input_path: path to the compressed file
    :param tail_lines: number of lines to read from the end of the file
    """
    buff_lines: list[str] = []

    with lzma.open(input_path, "rt") as f:
        while True:
            line = f.readline()
            if not line:
                break
            buff_lines.append(line)

            if len(buff_lines) > tail_lines:
                buff_lines.pop(0)

    tail_content = [
        {"index": i, "content": item.rstrip()} for i, item in enumerate(buff_lines)
    ]
    return tail_content


def decompress_gzip_tailed(input_path: str, tail_lines: int = 150) -> List[dict]:
    """
    Decompresses the last tail_lines of a gzip compressed file.
    It buffers the lines in memory to avoid decompressing the entire file.

    :param input_path: path to the compressed file
    :param tail_lines: number of lines to read from the end of the file
    """
    buff_lines: list[str] = []

    with gzip.open(input_path, "rt") as f:
        while True:
            line = f.readline()
            if not line:
                break
            buff_lines.append(line)

            if len(buff_lines) > tail_lines:
                buff_lines.pop(0)

    tail_content = [
        {"index": i, "content": item.rstrip()} for i, item in enumerate(buff_lines)
    ]
    return tail_content
