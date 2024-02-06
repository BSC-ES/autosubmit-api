#!/bin/env/python

from datetime import timedelta


def timedelta2hours(deltatime):
    # type: (timedelta) -> float
    return deltatime.days * 24 + deltatime.seconds / 3600.0
