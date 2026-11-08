from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / 'app.py')


def test_labels_appear_across_page_but_not_in_map_hover():
    at = AppTest.from_file(APP, default_timeout=300).run()
    assert not at.exception
    table = at.dataframe[0].value
    assert table['RPT Dist No'].str.contains(' · ').all()
    assert table['RPT Dist No'].iloc[0] == '0182 · Central · near S Flower St'

    at.selectbox(key='evidence_select').select('0182').run()
    assert not at.exception
    assert any('0182 · Central · near S Flower St had' in m.value for m in at.markdown)
    charts = [c.proto.spec for c in at.get('plotly_chart')]
    assert any('near S Flower St' in spec for spec in charts)
    for spec in charts:
        if '"scattermap"' in spec:  # the street may be in the title, never in cell data
            assert '"customdata":[["' not in spec or 'Flower' not in spec.split('"customdata"')[1].split(']]')[0]


def test_all_and_none_stay_distinct_with_hidden_value_box():
    at = AppTest.from_file(APP, default_timeout=300).run()
    baseline = at.metric[0].value
    assert not any(w.key == 'sel_areas' for w in at.multiselect)  # hidden while All is ticked

    at.checkbox(key='all_areas').uncheck().run()
    assert not at.exception
    assert at.multiselect(key='sel_areas').value == []
    assert at.metric[0].value == '0'  # none means no records, not everything

    at.checkbox(key='all_areas').check().run()
    assert at.metric[0].value == baseline
