from typing import Annotated, List, Optional
from pydantic import BaseModel, Field


class BaseExperimentRun(BaseModel):
    run_id: Annotated[
        int, Field(description="Run ID", json_schema_extra={"example": 1})
    ]
    start: Annotated[
        Optional[str],
        Field(
            description="Start time of the run",
            json_schema_extra={"example": "2021-01-01T00:00:00Z"},
        ),
    ]
    finish: Annotated[
        Optional[str],
        Field(
            description="Finish time of the run",
            json_schema_extra={"example": "2021-01-01T00:00:00Z"},
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
