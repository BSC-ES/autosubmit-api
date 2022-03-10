import autosubmitAPIwu.workers.populate_times as PopulateTimes


def main():
    # Process queue and running times
    PopulateTimes.process_completed_times()


if __name__ == "__main__":
    main()
