"""Contrôles indépendants : on recalcule autrement ce que le script calcule."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analyze  # noqa: E402


def test_data_integrity():
    offers, skills = analyze.load()
    analyze.check(offers, skills)


def test_junior_scope_rules():
    offers, _ = analyze.load()
    j = analyze.scope(offers, junior_only=True)
    assert j["date_2026_verified"].all()
    assert (j["experience_min_years"] <= 3).all()
    assert j["posted"].str.startswith("2026").all()


def test_frequency_matches_manual_count():
    offers, skills = analyze.load()
    j = analyze.scope(offers, junior_only=True)
    freq, n = analyze.frequency(j, skills)
    assert n == len(j)
    ids = set(j["offer_id"])
    manual = skills[(skills.skill == "Python") & skills.offer_id.isin(ids)]["offer_id"].nunique()
    assert int(freq.loc[freq.skill == "Python", "nb_offres"].iloc[0]) == manual


def test_matrix_totals_match_long_table():
    offers, skills = analyze.load()
    m = analyze.matrix(offers, skills)
    assert m.values.sum() == len(skills)
    assert set(m.values.ravel()) <= {0, 1}
