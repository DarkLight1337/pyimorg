from __future__ import annotations

import functools

from hypothesis import assume, given, strategies as st
import pytest

from pyimorg.func import JobsFailed, T, map_mt_with_tqdm, map_with_retry


def st_any() -> st.SearchStrategy[object]:
    return st.none() | st.booleans() | st.binary() | st.integers() | st.floats() | st.functions()

def st_num_jobs(
    *,
    min_valid: int = 1,
    max_valid: int = 8,
) -> st.SearchStrategy[int]:
    return st.integers(min_value=min_valid, max_value=max_valid)

def st_count(
    *,
    valid_value: bool = True,
    min_valid: int = 1,
    max_valid: int = 8,
) -> st.SearchStrategy[int]:
    if valid_value:
        return st.integers(min_value=min_valid, max_value=max_valid)

    return st.integers(max_value=0)

def st_delay_secs(*, valid: bool = True, max_valid: float = 1e-5) -> st.SearchStrategy[float]:
    if valid:
        return st.floats(min_value=0, max_value=max_valid, allow_nan=False)

    return st.floats(max_value=0, exclude_max=True)

def st_exc_or_tuple(*, min_size: int = 0) -> st.SearchStrategy[Exception | tuple[Exception, ...]]:
    return st.one_of(
        st.from_type(Exception),
        st.lists(st.from_type(Exception), min_size=min_size).map(lambda x: tuple(x)),
    )


@given(st_exc_or_tuple(), st_count(valid_value=False), st_delay_secs())
def test_map_with_retry_invalid_count_value(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
):
    if isinstance(exc_or_tuple, Exception):
        on = type(exc_or_tuple)
    else:
        on = tuple(type(exc) for exc in exc_or_tuple)

    with pytest.raises(ValueError):
        map_with_retry(on, count=count, delay_secs=delay_secs)

@given(st_exc_or_tuple(), st_count(), st_delay_secs(valid=False))
def test_map_with_retry_invalid_delay_value(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
):
    if isinstance(exc_or_tuple, Exception):
        on = type(exc_or_tuple)
    else:
        on = tuple(type(exc) for exc in exc_or_tuple)

    with pytest.raises(ValueError):
        map_with_retry(on, count=count, delay_secs=delay_secs)

@given(st_exc_or_tuple(), st_count(), st_delay_secs(), st.lists(st_any()), st_num_jobs())
def test_map_with_retry_success_no_retry(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
    values: list[object],
    n_jobs: int,
):
    if isinstance(exc_or_tuple, Exception):
        on = type(exc_or_tuple)
    else:
        on = tuple(type(exc) for exc in exc_or_tuple)

    mapper = map_with_retry(on, count=count, delay_secs=delay_secs) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=None))

    attempt_count = 0

    def identity(x: T) -> T:
        nonlocal attempt_count
        attempt_count += 1

        return x

    assert mapper(values, identity) == values, 'Incorrect value'
    assert attempt_count == len(values), 'Incorrect number of attempts'

@given(st_exc_or_tuple(min_size=1), st_count(min_valid=2), st_delay_secs(), st.lists(st_any(), min_size=1), st_num_jobs())
def test_map_with_retry_success_on_retry(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
    values: list[object],
    n_jobs: int,
):
    if isinstance(exc_or_tuple, Exception):
        on = type(exc_or_tuple)
        exc = exc_or_tuple
    else:
        on = tuple(type(exc) for exc in exc_or_tuple)
        exc = exc_or_tuple[0]

    mapper = map_with_retry(on, count=count, delay_secs=delay_secs) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=None))

    attempt_count = 0
    is_fail = True

    def identity(x: T) -> T:
        nonlocal attempt_count
        attempt_count += 1

        nonlocal is_fail

        if is_fail:
            is_fail = False
            raise exc

        return x

    assert mapper(values, identity) == values, 'Incorrect value'
    assert attempt_count == 1 + len(values), 'Incorrect number of attempts'

@given(st_exc_or_tuple(min_size=1), st_count(), st_delay_secs(), st.lists(st_any(), min_size=1), st_num_jobs())
def test_map_with_retry_fail_exc_type_mismatch(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
    values: list[object],
    n_jobs: int,
):
    if isinstance(exc_or_tuple, Exception):
        on = ()
        exc = exc_or_tuple
    else:
        on = tuple(type(exc) for exc in exc_or_tuple[1:])
        exc = exc_or_tuple[0]

    assume(type(exc) not in on)

    mapper = map_with_retry(on, count=count, delay_secs=delay_secs) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=None))

    attempt_count = 0

    def identity(x: T) -> T:
        nonlocal attempt_count
        attempt_count += 1

        raise exc

    with pytest.raises(type(exc)):
        mapper(values, identity)

    # The exact number of attempts depends on the error handling in `map_mt_with_tqdm`

@given(st_exc_or_tuple(min_size=1), st_count(), st_delay_secs(), st.lists(st_any(), min_size=1), st_num_jobs())
def test_map_with_retry_fail_out_of_attempts(
    exc_or_tuple: Exception | tuple[Exception, ...],
    count: int,
    delay_secs: float,
    values: list[object],
    n_jobs: int,
):
    if isinstance(exc_or_tuple, Exception):
        on = type(exc_or_tuple)
        exc = exc_or_tuple
    else:
        on = tuple(type(exc) for exc in exc_or_tuple)
        exc = exc_or_tuple[0]

    mapper = map_with_retry(on, count=count, delay_secs=delay_secs) \
        (functools.partial(map_mt_with_tqdm, n_jobs=n_jobs, desc=None))

    attempt_count = 0

    def identity(x: T) -> T:
        nonlocal attempt_count
        attempt_count += 1

        raise exc

    with pytest.raises(JobsFailed) as exc_info:
        mapper(values, identity)

    assert all(job.exc == exc for job in exc_info.value.failed_jobs)

    assert attempt_count == count * len(values), 'Incorrect number of attempts'
