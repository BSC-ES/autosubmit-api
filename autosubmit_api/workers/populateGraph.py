import autosubmit_api.workers.process_graph_drawings as ProcessGraph


def main():
    """
    Process and positions graph drawing.
    """
    ProcessGraph.process_active_graphs()


if __name__ == "__main__":
    main()
