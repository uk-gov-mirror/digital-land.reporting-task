import json

import pandas as pd

import duplicate_geometry_expectations as dge


def _bounds_df(rows):
    return pd.DataFrame(rows, columns=["dataset", "organisation", "parameters", "details"])


def _bounds_row(dataset, organisation, organisation_entity, entities):
    return (
        dataset,
        organisation,
        json.dumps({"lpa": "E60000000", "organisation_entity": organisation_entity, "expected": 0}),
        json.dumps(
            {
                "failures": [{"organisation_entity": str(organisation_entity), "entity": e} for e in entities],
                "actual": len(entities),
                "expected": 0,
                "entities": entities,
            }
        ),
    )


def test_parse_out_of_bounds_collects_checked_organisations_and_offending_entities():
    df = _bounds_df(
        [
            _bounds_row("conservation-area", "local-authority:EHA", 122, [44016385, 44016386]),
            _bounds_row("conservation-area", "local-authority:HAA", 153, []),
        ]
    )

    checked, out_of_bounds = dge.parse_out_of_bounds(df)

    assert checked == {("conservation-area", 122), ("conservation-area", 153)}
    assert out_of_bounds == {("conservation-area", 44016385), ("conservation-area", 44016386)}


def test_parse_out_of_bounds_with_no_rows_is_empty():
    checked, out_of_bounds = dge.parse_out_of_bounds(_bounds_df([]))

    assert checked == set()
    assert out_of_bounds == set()


def _matches():
    return pd.DataFrame(
        {
            "dataset": ["conservation-area"] * 3,
            "entity_a": pd.array([44017000, 44017000, 44017008], dtype="Int64"),
            "entity_a_organisation": pd.array([2, 2, 2], dtype="Int64"),
            "entity_b": pd.array([44016370, 44016385, 44016398], dtype="Int64"),
            "entity_b_organisation": pd.array([153, 122, 122], dtype="Int64"),
        }
    )


def test_add_out_of_bounds_flags_true_false_and_unknown():
    checked = {("conservation-area", 153), ("conservation-area", 122)}
    out_of_bounds = {("conservation-area", 44016385)}

    result = dge.add_out_of_bounds_flags(_matches(), checked, out_of_bounds)

    # HAA entity in bounds, EHA copy out of bounds, EHA entity that only touches the boundary in bounds
    assert list(result["entity_b_out_of_bounds"]) == [False, True, False]
    # organisation 2 has no boundary result, so unknown rather than in bounds
    assert result["entity_a_out_of_bounds"].isna().all()


def test_add_out_of_bounds_flags_is_unknown_when_organisation_was_not_checked():
    result = dge.add_out_of_bounds_flags(_matches(), {("conservation-area", 153)}, set())

    assert list(result["entity_b_out_of_bounds"][:1]) == [False]
    assert result["entity_b_out_of_bounds"][1:].isna().all()


def test_add_out_of_bounds_flags_writes_blank_for_unknown_in_csv(tmp_path):
    result = dge.add_out_of_bounds_flags(_matches(), {("conservation-area", 153)}, set())
    path = tmp_path / "out.csv"

    result.to_csv(path, index=False)

    lines = path.read_text().splitlines()
    assert lines[1].endswith(",False")
    assert lines[2].endswith(",")
