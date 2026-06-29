from unittest.mock import patch
from app.tasks.catalog_refresh import refresh_printify_catalog


def test_refresh_task_calls_catalog_refresh():
    with patch("app.tasks.catalog_refresh.get_catalog_service") as gcs:
        refresh_printify_catalog.run()
    gcs.return_value.refresh.assert_called_once()
