from typing import Annotated, List, Optional
from pydantic import BaseModel, Field


class BaseExperimentRun(BaseModel):
    run_id: Annotated[int, Field(description="Run ID", example=1)]
    start: Annotated[
        Optional[str],
        Field(description="Start time of the run", example="2021-01-01T00:00:00Z"),
    ]
    finish: Annotated[
        Optional[str],
        Field(description="Finish time of the run", example="2021-01-01T00:00:00Z"),
    ]


class ExperimentSearchItem(BaseModel):
    id: Annotated[int, Field(description="Numerical Experiment ID", example=3)]
    name: Annotated[str, Field(description="Expid of the experiment", example="a002")]
    user: Annotated[
        Optional[str],
        Field(description="User who created the experiment", example="user"),
    ]
    description: Annotated[
        Optional[str],
        Field(description="Description of the experiment", example="Description"),
    ]
    hpc: Annotated[
        Optional[str],
        Field(description="HPC where the experiment was run", example="hpc"),
    ]
    version: Annotated[
        Optional[str],
        Field(description="Version of Autosubmit of this experiment", example="4.1.0"),
    ]
    created: Annotated[
        Optional[str],
        Field(
            description="Creation time of the experiment", example="2023-10-16 15:21:51"
        ),
    ]
    modified: Annotated[
        Optional[str],
        Field(
            description="Last modification time of the experiment",
            example="2024-01-12T16:38:56",
        ),
    ]
    status: Annotated[
        Optional[str], Field(description="Status of the experiment", example="RUNNING")
    ]
    completed: Annotated[
        Optional[int], Field(description="Number of completed jobs", example=0)
    ]
    total: Annotated[
        Optional[int], Field(description="Total number of jobs", example=8)
    ]
    submitted: Annotated[
        Optional[int], Field(description="Number of submitted jobs", example=0)
    ]
    queuing: Annotated[
        Optional[int], Field(description="Number of jobs in the queue", example=0)
    ]
    running: Annotated[
        Optional[int], Field(description="Number of jobs running", example=0)
    ]
    failed: Annotated[
        Optional[int], Field(description="Number of failed jobs", example=0)
    ]
    suspended: Annotated[
        Optional[int], Field(description="Number of suspended jobs", example=0)
    ]


class BaseExperimentWrapper(BaseModel):
    wrapper_name: Annotated[
        str,
        Field(
            description="Name of the wrapper",
            example="a6zi_ASThread_17108816522924_528_10",
        ),
    ]
    job_names: Annotated[List[str], Field(description="List of job names")]
