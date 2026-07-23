.. _eta:

Understanding the Experiment ETA
################################

The ETA (Estimated Time of Arrival) endpoint predicts how much time
remains for an experiment section to finish. It is available at:

.. code-block:: bash

   GET /v4/experiments/{expid}/eta?section=SIM

The ``section`` query parameter is optional and defaults to ``SIM``.

How the estimation works
========================

The ETA is based on the average runtime of already completed chunks:

1. Jobs are grouped in chunks
2. For each chunk where all the jobs are completed, the chunk runtime
is calculated as the difference between the latest finish time and the
earliest start time of its jobs.
3. These runtimes of all completed chunks are averaged.
4. The result is multiplied by the number of remaining chunks not yet completed.

.. code-block:: text

    For each completed chunk:
      runtime = max(finish) - min(start)

    avg_runtime = average(runtime of all completed chunks)
    remaining   = total_chunks - completed_chunks

    eta = avg_runtime × remaining

Requisites an experiment should have to get a valid ETA
========================================================

The ETA estimation can only be computed if the experiment:
1. Has at least one completed chunk. If not, the ETA will be returned as ``null``.
2. The section specified in the query parameter (or the default ``SIM``) is
defined with ``RUNNING: chunk``.

Example
=======

The following experiment has 5 SIM chunks. After some time running,
2 chunks are completed, each taking about 2400 seconds to finish.
The ETA would be:

.. code-block:: text

    avg_runtime = (2400 + 2400) / 2 = 2400 seconds
    remaining   = 5 - 2 = 3 chunks
    eta         = 2400 × 3 = 7200 seconds (2 hours)

API response:

.. code-block:: json

    {
      "eta_seconds": 7200.0,
      "chunks_total": 5,
      "chunks_remaining": 3,
      "avg_runtime_per_chunk_seconds": 2400.0
    }