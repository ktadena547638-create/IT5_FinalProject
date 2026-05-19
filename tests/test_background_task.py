"""Unit tests for BackgroundTask threading and async operations."""

import time

from main import BackgroundTask, run_in_background


def test_background_task_runs_and_waits():
    """Test background task execution and wait completion."""
    results = []

    def heavy(x, y):
        time.sleep(0.1)
        return x + y

    def on_complete(res):
        results.append(res)

    task = BackgroundTask(target=heavy, args=(1, 2), on_complete=on_complete)
    task.start()
    BackgroundTask.wait_all(timeout=1)

    assert results == [3]


def test_run_in_background_helper():
    """Test the run_in_background convenience function."""
    results = []

    def add(a, b):
        return a + b

    def on_complete(res):
        results.append(res)

    run_in_background(target=add, args=(4, 5), on_complete=on_complete)
    BackgroundTask.wait_all(timeout=1)
    assert results == [9]
