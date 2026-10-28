"""Analyse des compétences demandées dans des offres d'emploi en actuariat (France, 2026).

Entrées : data/offers.csv (1 ligne par offre), data/skills.csv (1 ligne par offre x compétence)
Sorties : reports/*.csv et reports/*.png
Usage   : python src/analyze.py

Périmètre d'analyse : offres dont la date de publication 2026 est vérifiée.
Cible "junior" : offres demandant 0 à 3 ans d'expérience.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, REPORTS = ROOT / "data", ROOT / "reports"
CATEGORIES = ["Métier", "Réglementaire", "Outil", "Savoir-être"]
LEVELS = ["Débutant (0-1 an)", "Junior (2-3 ans)", "Confirmé (4 ans et +)", "Non précisé"]
JUNIOR = LEVELS[:2]
INK, TEAL, GRID = "#1F2A44", "#2E6F73", "#E3E8E8"


def load():
    offers = pd.read_csv(DATA / "offers.csv")
    skills = pd.read_csv(DATA / "skills.csv")
    return offers, skills


def check(offers, skills):
    """Contrôles de fiabilité avant tout calcul."""
    assert offers["offer_id"].is_unique, "offer_id dupliqué dans offers.csv"
    assert offers["url"].is_unique, "même URL saisie deux fois (doublon d'offre)"
    orphans = set(skills["offer_id"]) - set(offers["offer_id"])
    assert not orphans, f"Compétences rattachées à des offres inconnues : {orphans}"
    no_skill = set(offers["offer_id"]) - set(skills["offer_id"])
    assert not no_skill, f"Offres sans aucune compétence codée : {no_skill}"
    dups = skills.duplicated(["offer_id", "skill"])
    assert not dups.any(), f"Doublons offre x compétence : {skills[dups].values.tolist()}"
    assert set(skills["category"]) <= set(CATEGORIES), "catégorie inconnue"
    assert set(offers["experience_level"]) <= set(LEVELS), "niveau d'expérience inconnu"
    multi = skills.groupby("skill")["category"].nunique()
    assert (multi == 1).all(), f"Compétence dans plusieurs catégories : {list(multi[multi > 1].index)}"
    # cohérence niveau <-> années
    yrs = offers["experience_min_years"]
    assert (yrs[offers.experience_level == "Débutant (0-1 an)"] <= 1).all()
    assert yrs[offers.experience_level == "Junior (2-3 ans)"].between(2, 3).all()


def scope(offers, junior_only=False):
    s = offers[offers["date_2026_verified"]]
    return s[s["experience_level"].isin(JUNIOR)] if junior_only else s


def frequency(offers, skills):
    n = offers["offer_id"].nunique()
    sk = skills[skills["offer_id"].isin(offers["offer_id"])]
    freq = (sk.groupby(["category", "skill"])["offer_id"].nunique().rename("nb_offres").reset_index())
    freq["part_offres"] = (freq["nb_offres"] / n).round(3)
    return freq.sort_values(["nb_offres", "skill"], ascending=[False, True]), n


def matrix(offers, skills):
    m = pd.crosstab(skills["skill"], skills["offer_id"])
    return m.reindex(columns=offers["offer_id"], fill_value=0)


def compare(offers, skills):
    """Part des offres junior vs confirmé citant chaque compétence."""
    dated = scope(offers)
    j, _ = frequency(dated[dated.experience_level.isin(JUNIOR)], skills)
    c, _ = frequency(dated[dated.experience_level == "Confirmé (4 ans et +)"], skills)
    out = j.merge(c, on=["category", "skill"], how="outer", suffixes=("_junior", "_confirme")).fillna(0)
    out["ecart_points"] = ((out["part_offres_confirme"] - out["part_offres_junior"]) * 100).round(0)
    return out.sort_values("ecart_points", ascending=False)


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", labelsize=8, length=0)
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)


def plot_skills(freq, n, path, title, top=20):
    d = freq.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 7), dpi=150)
    bars = ax.barh([f"{s}  ({c})" for s, c in zip(d["skill"], d["category"])], d["nb_offres"], color=TEAL, height=0.65)
    for b, v in zip(bars, d["nb_offres"]):
        ax.text(b.get_width() + 0.15, b.get_y() + b.get_height() / 2, f"{v}/{n}", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, n + 1.5)
    ax.set_xlabel("Nombre d'offres qui citent la compétence")
    ax.set_title(title, fontsize=10, loc="left", color=INK)
    _style(ax)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def plot_levels(offers, path):
    d = scope(offers)["experience_level"].value_counts().reindex(LEVELS, fill_value=0).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 2.8), dpi=150)
    bars = ax.barh(d.index, d.values, color=TEAL, height=0.6)
    for b, v in zip(bars, d.values):
        ax.text(b.get_width() + 0.2, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8, color=INK)
    ax.set_xlabel("Nombre d'offres")
    ax.set_title(f"Expérience minimale demandée — {int(d.sum())} offres datées 2026", fontsize=10, loc="left", color=INK)
    _style(ax)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def main():
    offers, skills = load()
    check(offers, skills)
    REPORTS.mkdir(exist_ok=True)
    junior = scope(offers, junior_only=True)
    freq, n = frequency(junior, skills)
    freq.to_csv(REPORTS / "skills_frequency_junior.csv", index=False)
    matrix(offers, skills).to_csv(REPORTS / "skills_matrix.csv")
    cmp_ = compare(offers, skills)
    cmp_.to_csv(REPORTS / "junior_vs_confirme.csv", index=False)
    plot_skills(freq, n, REPORTS / "top_skills_junior.png",
                f"Top 20 des compétences — {n} offres junior (0-3 ans) publiées en 2026")
    plot_levels(offers, REPORTS / "experience_levels.png")
    print(f"{len(offers)} offres collectées, {len(scope(offers))} datées 2026, {n} junior")
    for c in CATEGORIES:
        print(f"\n== {c} (junior) ==")
        print(freq[freq.category == c].head(6).to_string(index=False))
    print("\n== Ce qui augmente le plus avec l'expérience (points de %) ==")
    print(cmp_.head(8)[["skill", "part_offres_junior", "part_offres_confirme", "ecart_points"]].to_string(index=False))


if __name__ == "__main__":
    main()
