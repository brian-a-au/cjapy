"""Static checks for the typed data view methods. mypy reads this file; pytest does not run it."""

from typing import Any, Dict, List, Union

import pandas as pd
from typing_extensions import assert_type

from cjapy import CJA


def check(cja: CJA, output: str) -> None:
    assert_type(cja.getDataViews(), pd.DataFrame)
    assert_type(cja.getDataViews(output="df"), pd.DataFrame)
    assert_type(cja.getDataViews(output="raw"), List[Dict[str, Any]])
    assert_type(cja.getDataViews(output=output), Union[pd.DataFrame, List[dict]])
    assert_type(cja.getDataView("dv_1"), Dict[str, Any])

    assert_type(cja.getDimensions("dv_1"), pd.DataFrame)
    assert_type(cja.getDimensions("dv_1", output="raw"), List[Dict[str, Any]])
    assert_type(cja.getDimensions("dv_1", output=output), Union[pd.DataFrame, List[dict]])
    assert_type(cja.getDimension("dv_1", "variables/page"), Dict[str, Any])

    assert_type(cja.getMetrics("dv_1"), pd.DataFrame)
    assert_type(cja.getMetrics("dv_1", full=True, output="raw"), List[Dict[str, Any]])
    assert_type(cja.getMetrics("dv_1", output=output), Union[pd.DataFrame, List[dict]])
    assert_type(cja.getMetric("dv_1", "metrics/visits"), Dict[str, Any])
