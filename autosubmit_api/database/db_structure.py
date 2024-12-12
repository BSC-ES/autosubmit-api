import traceback
from typing import Dict, List

from autosubmit_api.repositories.experiment_structure import (
    create_experiment_structure_repository,
)


def get_structure(expid: str) -> Dict[str, List[str]]:
    """
    Creates file of database and table of experiment structure if it does not exist.
    Returns current structure as a Dictionary Job Name -> Children's Names

    :return: Map from job to children
    :rtype: Dictionary Key: String, Value: List(of String)
    """
    try:
        structure_repo = create_experiment_structure_repository(expid)
        rows = structure_repo.get_all()

        structure: Dict[str, List[str]] = {}
        for edge in rows:
            _from, _to = edge.e_from, edge.e_to

            structure.setdefault(_from, []).append(_to)
            structure.setdefault(_to, [])

        return structure
    except Exception:
        print((traceback.format_exc()))
