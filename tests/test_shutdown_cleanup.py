from bot import _is_expected_playwright_shutdown_exception


class TargetClosedError(RuntimeError):
    pass


def test_expected_playwright_page_close_future_is_identified() -> None:
    context = {
        "message": "Future exception was never retrieved",
        "exception": TargetClosedError("Target page, context or browser has been closed"),
    }

    assert _is_expected_playwright_shutdown_exception(context) is True


def test_unrelated_asyncio_errors_are_not_hidden() -> None:
    assert _is_expected_playwright_shutdown_exception({
        "message": "Task exception was never retrieved",
        "exception": RuntimeError("database failed"),
    }) is False
    assert _is_expected_playwright_shutdown_exception({
        "message": "Future exception was never retrieved",
        "exception": TargetClosedError("Page crashed during an active request"),
    }) is False
