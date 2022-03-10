
#!/usr/bin/env python
from abc import ABCMeta, abstractmethod
from typing import List, Dict

class Edge(object):
  """ Abstract Edge """
  __metaclass__ = ABCMeta

  def __init__(self):
    self._id = ""
    self._from = ""
    self._to = ""
    self._is_in_wrapper = ""
    self._dashed = ""    

  def _get_build_identifier(self):
    # type: () -> str
    return "{0}-{1}".format(self._from, self._to)

  def get_as_json(self):
    # type: () -> Dict[str, str]
    return {
      "id": self._id,
      "from": self._from,
      "to": self._to,
      "is_wrapper": self._is_in_wrapper,
      "dashed":  self._dashed
    }
  
class RealEdge(Edge):
  def __init__(self, from_node_name, to_node_name, in_wrapper_and_same_wrapper):
    # type: (str, str, bool) -> None
    super(RealEdge, self).__init__()    
    self._from = from_node_name
    self._to = to_node_name
    self._id = self._get_build_identifier()    
    self._is_in_wrapper = in_wrapper_and_same_wrapper
    self._dashed = False

class PackageInnerEdge(Edge):
  def __init__(self, from_node_name, to_node_name):
    # type: (str, str) -> None
    super(PackageInnerEdge, self).__init__()
    self._from = from_node_name
    self._to = to_node_name
    self._id = self._get_build_identifier()    
    self._is_in_wrapper = True
    self._dashed = True
  
  
    