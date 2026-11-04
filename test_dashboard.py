import io
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard_support import (load_bundle, validate_data, select_scopes, scope_kpis,
                               top_categories, map_cells, export_payload)
from src.analysis import Filters, ranked_districts, nighttime_offenses


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


@pytest.fixture(scope="module")
def ranking(bundle):
    return ranked_districts(bundle[0])


def test_scope_membership_does_not_rerank(ranking):
    before = ranking.copy(deep=True)
    ids = tuple(ranking.iloc[15:30]["RPT Dist No"])
    eligible, shown = select_scopes(ranking, ids, top_n=5,
                                    sort_column="Nighttime reported offenses", descending=True)
    expected = ranking.loc[ranking["RPT Dist No"].isin(ids) & ranking["Active months"].ge(1)]
    assert eligible["Rank"].tolist() == expected["Rank"].tolist()
    assert set(shown["Rank"]) == set(expected.head(5)["Rank"])
    assert shown["Nighttime reported offenses"].is_monotonic_decreasing
    pd.testing.assert_frame_equal(ranking, before)


def test_top_limit_does_not_change_kpis_and_empty_is_none(ranking):
    e5, t5 = select_scopes(ranking, top_n=5)
    e20, t20 = select_scopes(ranking, top_n=20)
    assert len(t5) == 5 and len(t20) == 20
    assert scope_kpis(e5) == scope_kpis(e20)
    empty, shown = select_scopes(ranking, districts=())
    assert empty.empty and shown.empty and scope_kpis(empty)["coverage"] is None
    assert select_scopes(ranking, minimum=100)[0].empty


def test_map_generalizes_coordinates_and_removes_identifiers():
    raw = pd.DataFrame({"LAT": [34.12341, 34.12349, 34.12341],
                        "LON": [-118.23441, -118.23449, -118.23441],
                        "UniqueNIBRNo": ["secret-1", "secret-2", "secret-1"],
                        "LOCATION": ["private"] * 3})
    safe = map_cells(raw)
    assert safe.columns.tolist() == ["latitude", "longitude", "Reported offenses"]
    assert safe.iloc[0].to_dict() == {"latitude": 34.123, "longitude": -118.234, "Reported offenses": 2}
    assert "secret" not in safe.to_json() and "private" not in safe.to_json()
    assert map_cells(raw.iloc[:0]).empty


def test_full_map_count_reconciles(bundle):
    mapped = nighttime_offenses(bundle[0], Filters(districts=("1494",)), mapped_only=True)
    assert map_cells(mapped)["Reported offenses"].sum() == mapped["UniqueNIBRNo"].nunique()


def test_other_bucket_preserves_total_and_literal_other():
    summary = pd.DataFrame({"category": ["Other", "A", "B"], "nighttime_offenses": [9, 5, 2]})
    result = top_categories(summary, "category", n=1)
    assert result["category"].tolist() == ["Other", "Other (remaining categories)"]
    assert result["nighttime_offenses"].sum() == 16


def test_export_preserves_codes_order_values_and_scope(bundle, ranking):
    eligible, shown = select_scopes(ranking, top_n=5, sort_column="Recent nighttime offenses", descending=True)
    csv_bytes, json_bytes = export_payload(shown, bundle[3], Filters(), universe_count=len(ranking),
        eligible_count=len(eligible), minimum=1, top_n=5, sort_column="Recent nighttime offenses", descending=True)
    restored = pd.read_csv(io.BytesIO(csv_bytes), dtype={"RPT Dist No": "string"})
    assert restored["RPT Dist No"].tolist() == shown["RPT Dist No"].tolist()
    assert restored["Rank"].tolist() == shown["Rank"].tolist()
    assert restored["Priority score"].tolist() == pytest.approx(shown["Priority score"].tolist())
    assert len(restored.columns) == 15
    metadata = json.loads(json_bytes)
    assert metadata["scope_counts"] == {"universe": len(ranking), "eligible": len(eligible), "overview": 5}
    assert metadata["filters"]["districts"] is None
    assert len(metadata["processed_sha256"]) == 64


def test_validation_rejects_inconsistent_flags(bundle):
    data, quality, dictionary, _ = bundle
    sample = data.head(2).copy()
    sample.loc[sample.index[0], "is_night"] = not bool(sample.iloc[0]["is_night"])
    with pytest.raises(ValueError, match="nighttime flags"):
        validate_data(sample, dict(quality, processed_rows=2), dictionary)


def test_dashboard_filters_evidence_comparison_and_reset():
    app = AppTest.from_file("app.py").run(timeout=60)
    assert not app.exception
    assert len(app.tabs) == 4
    baseline = [metric.value for metric in app.metric]
    assert baseline[:2] == ["179,209", "1,164"]
    app.selectbox(key="top_n").select("5").run(timeout=60)
    assert not app.exception
    assert [metric.value for metric in app.metric] == baseline
    app.selectbox(key="active_district").set_value("1494").run(timeout=60)
    assert not app.exception
    assert not any("map is unavailable" in warning.value.lower() for warning in app.warning)
    app.multiselect(key="comparison").set_value(["1494", "0182"]).run(timeout=60)
    assert not app.exception
    app.checkbox(key="all_areas").uncheck().run(timeout=60)
    assert not app.exception
    assert app.metric[0].value == "0" and app.metric[1].value == "0"
    assert app.selectbox(key="active_district").value is None
    next(button for button in app.button if button.label == "Reset all filters").click().run(timeout=60)
    assert not app.exception
    assert [metric.value for metric in app.metric] == baseline
