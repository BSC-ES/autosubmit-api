from autosubmit_api.bgtasks.bgtask import PopulateQueueRuntimes


def main():
    """ Process and updates queuing and running times. """
    PopulateQueueRuntimes.run()


if __name__ == "__main__":
    main()
