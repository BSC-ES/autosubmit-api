from typing import Annotated, List, Optional
from pydantic import BaseModel, Field


class BaseExperimentRun(BaseModel):
    """A run of an experiment, as recorded in its historical database.

    Only per-run data is reported, so the payload stays small regardless of the number
    of runs of the experiment.
    """

    run_id: Annotated[
        int, Field(description="Run ID", json_schema_extra={"example": 1})
    ]
    created: Annotated[
        Optional[str],
        Field(
            description="Creation time of the run",
            json_schema_extra={"example": "2024-04-11-16:53:56"},
        ),
    ]
    start: Annotated[
        Optional[str],
        Field(
            description="Start time of the run in UTC. `None` if the run never started",
            json_schema_extra={"example": "2024-04-11T16:53:56+00:00"},
        ),
    ]
    finish: Annotated[
        Optional[str],
        Field(
            description="Finish time of the run in UTC. `None` if the run has not finished",
            json_schema_extra={"example": "2024-04-11T18:30:00+00:00"},
        ),
    ]
    status: Annotated[
        str,
        Field(
            description=(
                "State of the run derived from its job counters: `RUNNING` when jobs are "
                "queuing, running or submitted, `COMPLETED` when all the jobs are "
                "completed, `FAILED` when there are failed jobs and nothing in flight, "
                "`UNKNOWN` otherwise (e.g. a run that was interrupted)"
            ),
            json_schema_extra={"example": "RUNNING"},
        ),
    ]
    chunk_unit: Annotated[
        Optional[str],
        Field(
            description="Chunking unit of the run",
            json_schema_extra={"example": "month"},
        ),
    ]
    chunk_size: Annotated[
        Optional[int],
        Field(description="Chunk size of the run", json_schema_extra={"example": 4}),
    ]
    queuing: Annotated[
        Optional[int],
        Field(
            description="Number of queuing jobs of the run",
            json_schema_extra={"example": 0},
        ),
    ]
    running: Annotated[
        Optional[int],
        Field(
            description="Number of running jobs of the run",
            json_schema_extra={"example": 0},
        ),
    ]
    submitted: Annotated[
        Optional[int],
        Field(
            description="Number of submitted jobs of the run",
            json_schema_extra={"example": 0},
        ),
    ]
    completed: Annotated[
        Optional[int],
        Field(
            description="Number of completed jobs of the run",
            json_schema_extra={"example": 8},
        ),
    ]
    failed: Annotated[
        Optional[int],
        Field(
            description="Number of failed jobs of the run",
            json_schema_extra={"example": 0},
        ),
    ]
    suspended: Annotated[
        Optional[int],
        Field(
            description="Number of suspended jobs of the run",
            json_schema_extra={"example": 0},
        ),
    ]
    total: Annotated[
        Optional[int],
        Field(
            description="Number of jobs of the run",
            json_schema_extra={"example": 8},
        ),
    ]


class ExperimentSearchItem(BaseModel):
    id: Annotated[
        int,
        Field(description="Numerical Experiment ID", json_schema_extra={"example": 3}),
    ]
    name: Annotated[
        str,
        Field(
            description="Expid of the experiment", json_schema_extra={"example": "a002"}
        ),
    ]
    user: Annotated[
        Optional[str],
        Field(
            description="User who created the experiment",
            json_schema_extra={"example": "user"},
        ),
    ]
    description: Annotated[
        Optional[str],
        Field(
            description="Description of the experiment",
            json_schema_extra={"example": "Description"},
        ),
    ]
    hpc: Annotated[
        Optional[str],
        Field(
            description="HPC where the experiment was run",
            json_schema_extra={"example": "hpc"},
        ),
    ]
    version: Annotated[
        Optional[str],
        Field(
            description="Version of Autosubmit of this experiment",
            json_schema_extra={"example": "4.1.0"},
        ),
    ]
    created: Annotated[
        Optional[str],
        Field(
            description="Creation time of the experiment",
            json_schema_extra={"example": "2023-10-16 15:21:51"},
        ),
    ]
    modified: Annotated[
        Optional[str],
        Field(
            description="Last modification time of the experiment",
            json_schema_extra={"example": "2024-01-12T16:38:56"},
        ),
    ]
    status: Annotated[
        Optional[str],
        Field(
            description="Status of the experiment",
            json_schema_extra={"example": "RUNNING"},
        ),
    ]
    completed: Annotated[
        Optional[int],
        Field(description="Number of completed jobs", json_schema_extra={"example": 0}),
    ]
    total: Annotated[
        Optional[int],
        Field(description="Total number of jobs", json_schema_extra={"example": 8}),
    ]
    submitted: Annotated[
        Optional[int],
        Field(description="Number of submitted jobs", json_schema_extra={"example": 0}),
    ]
    queuing: Annotated[
        Optional[int],
        Field(
            description="Number of jobs in the queue", json_schema_extra={"example": 0}
        ),
    ]
    running: Annotated[
        Optional[int],
        Field(description="Number of jobs running", json_schema_extra={"example": 0}),
    ]
    failed: Annotated[
        Optional[int],
        Field(description="Number of failed jobs", json_schema_extra={"example": 0}),
    ]
    suspended: Annotated[
        Optional[int],
        Field(description="Number of suspended jobs", json_schema_extra={"example": 0}),
    ]


class BaseExperimentWrapper(BaseModel):
    wrapper_name: Annotated[
        str,
        Field(
            description="Name of the wrapper",
            json_schema_extra={"example": "a6zi_ASThread_17108816522924_528_10"},
        ),
    ]
    job_names: Annotated[List[str], Field(description="List of job names")]
