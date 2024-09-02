
#!/usr/bin/env python
from abc import ABCMeta
from typing import Dict

class Edge(object, metaclass=ABCMeta):
  """ Abstract Edge """

  def __init__(self):
    self._id = ""
    self._from = ""
    self._to = ""
    self._is_in_wrapper = ""
    self._dashed = ""    

  def _get_build_identifier(self) -> str:
    return "{0}-{1}".format(self._from, self._to)

  def get_as_json(self) -> Dict[str, str]:
    return {
      "id": self._id,
      "from": self._from,
      "to": self._to,
      "is_wrapper": self._is_in_wrapper,
      "dashed":  self._dashed
    }
  
class RealEdge(Edge):
  def __init__(self, from_node_name: str, to_node_name: str, in_wrapper_and_same_wrapper: bool):
    super(RealEdge, self).__init__()    
    self._from = from_node_name
    self._to = to_node_name
    self._id = self._get_build_identifier()    
    self._is_in_wrapper = in_wrapper_and_same_wrapper
    self._dashed = False

class PackageInnerEdge(Edge):
  def __init__(self, from_node_name: str, to_node_name: str):
    super(PackageInnerEdge, self).__init__()
    self._from = from_node_name
    self._to = to_node_name
    self._id = self._get_build_identifier()    
    self._is_in_wrapper = True
    self._dashed = True
  
  
    