"""Tests for the realism-audit aggregation (Workstream C2)."""
import csv
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apparatus.corpus.realism import (RealismRating, render_rating_template,
                                        parse_rating_csv, parse_inputs,
                                        aggregate, REALISM_HALT_THRESHOLD,
                                        write_template)


def _task(task_id, text="A real-looking stakeholder request."):
    return {"task_id": task_id, "text": text,
            "domain": "financial_reporting",
            "category": "full_specification"}


def test_template_has_header_and_one_row_per_task():
    tasks = [_task("TASK-MAIN-FIN-001"), _task("TASK-MAIN-FIN-002")]
    csv_text = render_rating_template(tasks, "carter")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(rows) == 2
    for r in rows:
        assert r["rater_id"] == "carter"
        assert r["rating"] == ""
        assert "task_id" in r and "text_preview" in r


def test_template_truncates_long_text(tmp_path):
    long = "x" * 1000
    tasks = [_task("T1", text=long)]
    csv_text = render_rating_template(tasks, "r")
    row = list(csv.DictReader(io.StringIO(csv_text)))[0]
    assert len(row["text_preview"]) < 250
    assert row["text_preview"].endswith("...")


def test_parse_records_ratings_and_drops_blanks(tmp_path):
    p = tmp_path / "carter.csv"
    p.write_text(
        "task_id,domain,category,text_preview,rating,notes,rater_id\n"
        "T1,d,c,prev1,4,looks real,carter\n"
        "T2,d,c,prev2,,not yet,carter\n"
        "T3,d,c,prev3,2,too generic,carter\n")
    ratings = parse_rating_csv(str(p))
    assert len(ratings) == 3
    assert [r.rating for r in ratings] == [4.0, None, 2.0]
    assert all(r.rater_id == "carter" for r in ratings)


def test_parse_records_out_of_range_as_none_with_note(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        "task_id,domain,category,text_preview,rating,notes,rater_id\n"
        "T1,d,c,p,7,,x\n"
        "T2,d,c,p,abc,,x\n")
    ratings = parse_rating_csv(str(p))
    assert ratings[0].rating is None
    assert "out-of-range" in ratings[0].notes
    assert ratings[1].rating is None
    assert "invalid" in ratings[1].notes


def test_aggregate_computes_mean_and_flags_halt():
    ratings = [
        RealismRating("T1", "carter", 4.0),
        RealismRating("T1", "mckay", 3.5),
        RealismRating("T2", "carter", 2.0),
        RealismRating("T2", "mckay", 2.5),
        RealismRating("T3", "carter", 5.0),
        RealismRating("T3", "mckay", 5.0),
    ]
    rep = aggregate(ratings)
    assert rep["n_raters"] == 2 and rep["n_tasks"] == 3
    t1 = rep["by_task"]["T1"]
    assert abs(t1["mean"] - 3.75) < 1e-9
    assert t1["below_threshold"] is False
    # T2 mean is 2.25, below the 2.5 halt threshold
    assert rep["halt_list"] == ["T2"]
    assert rep["halt_count"] == 1


def test_aggregate_with_one_rater_yields_no_irr_value():
    """Krippendorff alpha is None or returnable when only one rater is
    present; the test asserts that aggregate does not crash and reports a
    sensible halt list."""
    ratings = [RealismRating("T1", "carter", 4.0),
               RealismRating("T2", "carter", 2.0)]
    rep = aggregate(ratings)
    assert rep["n_raters"] == 1
    assert rep["halt_list"] == ["T2"]


def test_aggregate_threshold_is_2_5():
    """A mean of exactly 2.5 is NOT below the threshold; only strict
    below counts. The protocol's '<2.5' wording, FORMS Section 4."""
    assert REALISM_HALT_THRESHOLD == 2.5
    ratings = [RealismRating("T1", "carter", 2.5),
               RealismRating("T1", "mckay", 2.5)]
    rep = aggregate(ratings)
    assert rep["halt_list"] == []


def test_parse_inputs_reads_directory_of_csvs(tmp_path):
    write_template([_task("T1")], "carter", str(tmp_path / "carter.csv"))
    write_template([_task("T1")], "mckay", str(tmp_path / "mckay.csv"))
    # fill in ratings manually
    for fn, rate in (("carter.csv", "4"), ("mckay.csv", "3")):
        p = tmp_path / fn
        lines = p.read_text().splitlines()
        # header + one row; insert rating in the rating column (5th)
        header = lines[0].split(",")
        rating_col = header.index("rating")
        cols = lines[1].split(",")
        cols[rating_col] = rate
        p.write_text(lines[0] + "\n" + ",".join(cols) + "\n")
    all_ratings = parse_inputs([str(tmp_path)])
    assert len(all_ratings) == 2
    assert sorted(r.rater_id for r in all_ratings) == ["carter", "mckay"]
