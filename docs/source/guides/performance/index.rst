.. _performanceMetrics:

Understanding the Performance Metrics
#######################################


Autosubmit computes metrics to measure experiment performance. Besides the
usual metrics, *Simulated Years Per Day* (SYPD), *Core Hours per Simulated
Year* (CHSY), and *Joules Per Simulated Year* (JPSY), it also calculates two
variations of SYPD, *Post Simulated Years Per Day* (PSYPD) and *Workflow
Simulated Years Per Day* (WSYPD).

Metrics Definition
==================

Each experiment has defined a `Parallelization` variable (estimation is defined below), :math:`k`, which is the
number of requested *Processing Elements* (PE), and the number of simulated
years parameter, :math:`y`, calculated from `CHUNK_SIZE`, :math:`c_s`, and
`CHUNK_UNIT`.

- If `CHUNK_UNIT = year`, :math:`y = c_s`
- If `CHUNK_UNIT = month`, :math:`y = \frac{c_s}{12}`
- If `CHUNK_UNIT = day`, :math:`y = \frac{c_s}{365}`
- If `CHUNK_UNIT = hour`, :math:`y = \frac{c_s}{8760}`

Let :math:`I` be the set of SIM jobs whose state is `COMPLETED`. For each job :math:`i \in I` the following attributes are taken into
account:

- time in seconds in queue, :math:`q_i`
- runtime in seconds, :math:`r_i`
- energy consumption in joules, :math:`\eta_i`

Let :math:`C` be the set of SIM jobs that are `COMPLETED`. Let :math:`P`
be the set of POST jobs that are `COMPLETED`.

**Experiment's Post Simulated Years Per Day**: :math:`PSYPD = \frac{\sum_{i \in C} y_i \cdot 86400}{\sum_{i \in C} (q_i + r_i) + \frac{1}{|P|}\sum_{j \in P}(q_j+r_j)}`

The computation of *Real Simulated Year Per Day* will only consider experiments
that have a TRANSFER or a CLEAN job at the end of the workflow. AutosubmitAPI
checks when the first SIM job started (not submitted), and when the
last TRANSFER job finished. If the workflow does not have a TRANSFER job, then it
checks the last CLEAN job finish time.

Let :math:`t_s` be the time, in seconds, that the first SIM job started. Let
:math:`t_f` be the time in which the last TRANSFER or CLEAN job ended.

**Experiment's Real Simulated Years Per Day**: :math:`RSYPD = \frac{\sum_{i \in C} y_i \cdot 86400}{t_f - t_s}`

Generalization of SYPD and PSYPD
================================

AutosubmitAPI can also compute SYPD and PSYPD for any job that has a `chunk` value.
These jobs share the same attributes as SIM jobs. Only `COMPLETED` jobs are considered.

**Generalized Simulated Years Per Day**: :math:`SYPD_i = \frac{y_i \cdot 86400}{r_i}`

As for PSYPD, it will only consider experiments that have at least one POST
job.

**Generalized Post Simulated Years Per Day**: :math:`PSYPD_i = \frac{y_i \cdot 86400}{(q_i + r_i) + \frac{1}{|P|}\sum_{j \in P}(q_j+r_j)}`

Parallelization estimation
==========================

.. code-block:: python

    if NODES is None:
        if TASKS is not None and PROCESSORS != TASKS:
            NODES = ROUNDUP(PROCESSORS/TASKS)
            if PROCESSORS_PER_NODE is not None:
                PEs = NODES * PROCESSORS_PER_NODE
            else:
                ERROR(MISSING PROCESSORS_PER_NODE)
        elif PROCESSORS_PER_NODE is not None and PROCESSORS > PROCESSORS_PER_NODE:
            PEs = NHMPN(PROCESSORS)
        else:
            PEs = PROCESSORS  # PEs could not be totally accurate but we don't know how many PROCESSORS_PER_NODE
    else:
        if NODES > 1 and PROCESSORS_PER_NODE is not None:
            PEs = NODES * PROCESSORS_PER_NODE
        elif NODES > 1:
            ERROR(MISSING PROCESSORS_PER_NODE)
        else:
            PEs = PROCESSORS