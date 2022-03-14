import autosubmit_api.workers.business.populate_times as PopulateTimes


def main():
    """ Process and updates queuing and running times. """
    PopulateTimes.process_completed_times()


if __name__ == "__main__":
    main()
