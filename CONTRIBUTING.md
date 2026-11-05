# Autosubmit API Contribution Guide

**Documentation:** http://autosubmit-api.readthedocs.io/en/latest/

**GitHub:** https://github.com/bsc-es/autosubmit

**Mailing list:** <autosubmit@bsc.es>

Thanks for contributing to Autosubmit API project. This document describes the conventions we enforce in pull requests. It focuses on doctrings, as currently we have style mismatches that we are progressively fixing.

## Doctring conventions

We build the documentation with Sphinx, so doctrings follow **PEP 257** standards with **Sphinx (reST) field lists**. This is the established style used in the codebase; new code should be consistent with it.

### Structure

- Document every public module, class, function and method. Private helpers need a docstring only when their behaviour is nto obvious from the name and signature.
- Start the docstring with a short one-line summary, ending with a period.
- Put the summary on the same line as the opening quotes. If the docstring has a body, leave one blank line between the summary and the body.

### Fields

| Field | Usage |
| --- | --- |
| `:param <name>` | One entry per parameter, in signature order. Describe its meaning, units and expected value. |
| `:returns` | Describe the returned value. Omit it when the function returns `None`. |
| `:raises <Exception>` | One entry per exception the function raises. |

We do not include `type` or `rtype` fields; it should be annotated in the signature instead.
Example:

```python
def get_job_names(expid: str, section: str) -> list[str]:
    """Return the job names of an experiment section.

    :param expid: Experiment identifier.
    :param section: Job section to filter by, for example ``SIM``.
    :returns: Job names sorted alphabetically; empty if section is empty.
    :raises ApiNotFoundError: If the experiment does not exist.
    """
```

As you can see, a single line is enough if it clear enough to understand how it works.
However, more lines can be added to further explain its behaviour if a blank line is left between.

### Do not repeat type annotations

Parameters and return values should be typed in the method signature. There is no need on repeating the same information in the docstring.

### Endpoints and models

- **FastAPI routes**: the endpoint title comes from the route's `name=` argument, and the docstring becomes the OpenAPI description. Write route doctrings for API consumers: what the endpoint answers and which identifiers it needs.
- **Pydantic models**: a short class docstring states what the model represents. Individual fields are documented with `Field(description=...)` (or `args=` for query and body models) so they are able to reach teh OpenAPI schema too.
