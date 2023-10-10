from ..workers.business import process_graph_drawings as ProcessGraph


def main():
    """
    Process coordinates of nodes in a graph drawing and saves them.
    """
    ProcessGraph.process_active_graphs()


if __name__ == "__main__":
    main()
