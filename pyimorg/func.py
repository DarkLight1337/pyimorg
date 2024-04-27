from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
import functools
import time
from typing import Callable, Generic, Literal, TypeVar

from pqdm.processes import pqdm as pqdm_mp
from pqdm.threads import pqdm as pqdm_mt

from .logger import get_logger

__all__ = ['map_mp_with_tqdm', 'map_mt_with_tqdm', 'JobsFailed', 'map_with_retry']

logger = get_logger()


T, R = TypeVar('T'), TypeVar('R')

def map_mp_with_tqdm(
    arr: Collection[T],
    fn: Callable[[T], R],
    *,
    n_jobs: int,
    desc: str | None,
) -> Collection[R]:
    """
    Executes a function in parallel using multiprocessing.

    Each element of `arr` contains the arguments that are passed to `fn`
    for one execution.

    Returns a list where the `i`th element corresponds to the return value
    of the `i`th execution (i.e., invoking `fn` with arguments `arr[i]`).
    """
    return pqdm_mp(
        arr,
        fn,
        n_jobs=n_jobs,
        exception_behaviour='immediate',
        desc='' if desc is None else desc,
        total=len(arr),
        disable=desc is None,
    )

def map_mt_with_tqdm(
    arr: Collection[T],
    fn: Callable[[T], R],
    *,
    n_jobs: int,
    desc: str | None,
) -> Collection[R]:
    """
    Executes a function in parallel using multithreading.

    Each element of `arr` contains the arguments that are passed to `fn`
    for one execution.

    Returns a list where the `i`th element corresponds to the return value
    of the `i`th execution (i.e., invoking `fn` with arguments `arr[i]`).
    """
    return pqdm_mt(
        arr,
        fn,
        n_jobs=n_jobs,
        exception_behaviour='immediate',
        desc='' if desc is None else desc,
        total=len(arr),
        disable=desc is None,
    )


def _get_func_name(func: Callable[..., object]) -> str:
    if isinstance(func, (functools.partial, functools.partialmethod)):
        return _get_func_name(func.func)

    return getattr(func, '__name__', str(func))

@dataclass(frozen=True)
class _NewJob(Generic[T]):
    """Wraps the argument to a new function call."""

    arg: T
    status: Literal['new'] = 'new'

@dataclass(frozen=True)
class _CompletedJob(Generic[R]):
    """Wraps the output of a completed function call."""

    result: R
    status: Literal['done'] = 'done'

@dataclass(frozen=True)
class _FailedJob(Generic[T]):
    """Wraps the argument to a failed function call."""

    arg: T
    exc: Exception
    status: Literal['failed'] = 'failed'

class JobsFailed(Exception, Generic[T]):
    def __init__(self, message: str, failed_jobs: Collection[_FailedJob[T]]) -> None:
        super().__init__(message)

        self.message = message
        self.failed_jobs = failed_jobs

def map_with_retry(
    on: type[Exception] | tuple[type[Exception], ...],
    *,
    count: int = 1,
    delay_secs: float = 0.0,
) -> Callable[
    [Callable[[Collection[T], Callable[[T], R]], Collection[R]]],
    Callable[[Collection[T], Callable[[T], R]], Collection[R]],
]:
    """
    Decorates a mapper (which applies a mapping function to a collection of values)
    such that in case any exception type in `on` is raised, the function is invoked again
    after `delay_secs` until a total of `count` attempts have been made. Once all attempts
    have been exhausted, the error of the last attempt of each failed item is re-raised by
    the wrapper function using :class:`JobsFailed`.
    """
    if count < 1:
        msg = '`count` must be a positive integer'
        raise ValueError(msg)
    if delay_secs < 0:
        msg = '`delay_secs` must be a non-negative number'
        raise ValueError(msg)

    def return_job(fn: Callable[[T], R]) -> Callable[[T], _CompletedJob[R] | _FailedJob[T]]:

        def wrapped_fn(val: T) -> _CompletedJob[R] | _FailedJob[T]:
            try:
                return _CompletedJob(fn(val))
            except on as exc:
                return _FailedJob(val, exc)

        return wrapped_fn

    def inner(mapper: Callable[[Collection[T], Callable[[T], R]], Collection[R]]):
        mapper_name = _get_func_name(mapper)

        @functools.wraps(mapper)
        def wrapped_mapper(arr: Collection[T], fn: Callable[[T], R]) -> Collection[R]:
            wrapped_fn = return_job(fn)

            jobs: list[_NewJob[T] | _CompletedJob[R] | _FailedJob[T]] = [_NewJob(e) for e in arr]
            failed_jobs: list[_FailedJob[T]] = []

            for c in range(1, count + 1):
                inputs = [(i, job) for i, job in enumerate(jobs) if job.status != 'done']
                input_idxs, input_args = [e[0] for e in inputs], [e[1].arg for e in inputs]

                for i, job in zip(input_idxs, mapper(input_args, wrapped_fn)):  # pyright: ignore[reportArgumentType]
                    jobs[i] = job

                failed_jobs = [job for job in jobs if job.status == 'failed']
                if len(failed_jobs) == 0:
                    results = [job.result for job in jobs if job.status == 'done']
                    assert len(results) == len(arr)
                    return results

                if c < count:
                    logger.warning(
                        'Failed %d/%d calls to %s. Retrying (%d/%d)...',
                        len(failed_jobs), len(arr), mapper_name, c, count,
                    )
                    time.sleep(delay_secs)
            else:
                for job in failed_jobs:
                    logger.error('Job failed with exception: %s', job.exc)

                msg = f"Failed {len(failed_jobs)}/{len(arr)} calls to {mapper_name}"
                raise JobsFailed(msg, failed_jobs)

        return wrapped_mapper

    return inner
