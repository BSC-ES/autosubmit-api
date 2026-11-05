from dataclasses import dataclass
from autosubmit_api.repositories.job_data import ExperimentJobDataModel

@dataclass(frozen=True)
class PerformanceJob:
    """Contains fields required for performance calculations."""

    job_name: str
    section: str
    member: str | None
    chunk: int | None
    run_id: int | None

    submit: int
    start: int
    finish: int

    ncpus: int
    energy: float
    split: int | None
    splits: int | None

    chunk_years: float


def to_performance_job(
    job_data: ExperimentJobDataModel,
    chunk_years: float,
) -> PerformanceJob:
    """Convert a job row into a object to be used in performance calculations.
    
    :param job_data: The job data row to convert.
    :param chunk_years: The number of years represented by a single chunk.
    :return: The performance job object.
    """
    return PerformanceJob(
        job_name=job_data.job_name,
        section=job_data.section,
        member=job_data.member,
        chunk=int(job_data.chunk) if job_data.chunk is not None else None,
        run_id=int(job_data.run_id) if job_data.run_id is not None else None,
        submit=job_data.submit,
        start=job_data.start,
        finish=job_data.finish,
        ncpus=int(job_data.ncpus or 0),
        energy=float(job_data.energy or 0.0),
        split=job_data.split,
        splits=job_data.splits,
        chunk_years=chunk_years,
    )
