from autosubmit_api.logger import logger
from math import ceil


def estimate_requested_nodes(
    nodes: int, processors: int, tasks: int, processors_per_node: int
) -> int:
    """Estimates the number of requested nodes.

    In the past we had ``ZeroDivisionError`` due to the number of ``tasks`` being set
    to ``0`` by default in the ``Job`` class. If that changes, we can remove the checks
    here.

    If ``nodes`` is provided and valid, that's returned immediately.

    If ``tasks`` is provided and valid, and ``tasks`` is greater than ``0`` (to prevent
    the ``ZeroDivisionError``) then we return the ceiling value of ``processors``
    divided by ``tasks``.

    If ``processors_per_node`` is provided and valid, and ``processors_per_node`` is
    greater than zero (``ZeroDivisionError``), and ``processors_per_node`` is not
    greater than ``processors``, then we return the ceiling value of ``processors``
    divided by the number of ``processors_per_node``.

    Else, we return ``1``.
    """
    _estimated_nodes = 1
    if str(nodes).isdigit():
        _estimated_nodes = int(nodes)
    elif str(tasks).isdigit() and int(tasks) > 0:
        _estimated_nodes = ceil(int(processors) / int(tasks))
    elif str(processors_per_node).isdigit() and 0 < int(processors_per_node) < int(
        processors
    ):
        _estimated_nodes = ceil(int(processors) / int(processors_per_node))

    if _estimated_nodes < 1:
        logger.warning(
            f"Estimated nodes is less than 1. This should not happen. Defaulting to 1. "
            f"Estimated nodes: {_estimated_nodes}, processors: {processors}, tasks: {tasks}, processors_per_node: {processors_per_node}"
        )
        _estimated_nodes = 1
    return _estimated_nodes


def calculate_processing_elements(
    nodes: int, processors: int, tasks: int, processors_per_node: int, exclusive: bool
) -> int:
    if str(processors_per_node).isdigit():
        if str(nodes).isdigit():
            return int(nodes) * int(processors_per_node)
        else:
            estimated_nodes = estimate_requested_nodes(
                nodes, processors, tasks, processors_per_node
            )
            if (
                not exclusive
                and estimated_nodes <= 1
                and int(processors) <= int(processors_per_node)
            ):
                return int(processors)
            else:
                return estimated_nodes * int(processors_per_node)
    elif str(tasks).isdigit() or str(nodes).isdigit():
        logger.warning(
            "Missing PROCESSORS_PER_NODE. Should be set if TASKS or NODES are defined. "
            "The PROCESSORS will be used instead."
        )
    return int(processors)
