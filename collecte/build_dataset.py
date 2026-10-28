"""Fusionne la collecte (raw_collecte.tsv) et les 16 offres initiales en offers.csv / skills.csv."""
import csv
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
REPO = HERE.parent  # racine du dépôt

MAP = {"Provisionnement": "Provisionnement / inventaire",
       "Dataviz": "Dataviz (Power BI/Tableau/Qlik)",
       "Data volumineuse / multi-sources": "Data volumineuse / multi-sources"}

CATEGORY = {
    "Réglementaire": {"Solvabilité II", "ORSA", "IFRS 17"},
    "Outil": {"Python", "R", "SAS", "SQL", "Excel", "VBA", "Prophet", "Spark", "SIG", "ReMetrica",
              "Dataviz (Power BI/Tableau/Qlik)", "Autre logiciel actuariel"},
    "Savoir-être": {"Communication", "Vulgarisation non-actuaires", "Travail transverse", "Rigueur",
                    "Autonomie", "Synthèse", "Esprit critique", "Curiosité", "Anglais", "Gestion de projet"},
}


def category(skill):
    for c, s in CATEGORY.items():
        if skill in s:
            return c
    return "Métier"


# --- 16 offres de la première version (même codage, vocabulaire harmonisé)
old_offers = pd.read_csv(HERE / "v1/offers.csv")
old_skills = pd.read_csv(HERE / "v1/skills.csv")
old_dates = {  # date de publication estimée à partir des mentions relatives relevées le 2026-10-28
    "O01": "2026-09", "O02": "inconnue", "O03": "2026-07", "O04": "2026-09", "O05": "2026-10",
    "O06": "2026-10", "O07": "2026-07", "O08": "2026-02", "O09": "2026-07", "O10": "inconnue",
    "O11": "2026-07", "O12": "2026-06", "O13": "2026-10", "O14": "inconnue", "O15": "2026-04",
    "O16": "2026-10"}
old_domain = {"Provisionnement": "Inventaire / Provisionnement", "ERM": "Risques / ERM",
              "Pricing IARD": "Pricing IARD", "Conseil": "Conseil actuariel", "CAT / Climat": "CAT / Climat",
              "Réassurance": "Réassurance", "ALM": "ALM", "Vie / Épargne": "Data / IA actuariat"}
rows = []
for r in old_offers.itertuples():
    rows.append(dict(offer_id=r.offer_id, source="v1", status=r.status, title=r.title, company=r.company,
                     city=r.city, contract=r.contract if isinstance(r.contract, str) else "unknown",
                     exp_raw="" if pd.isna(r.experience_min_years) else str(int(r.experience_min_years)),
                     posted=old_dates[r.offer_id], domain=old_domain[r.domain], url=r.url))
sk = [(r.offer_id, MAP.get(r.skill, r.skill)) for r in old_skills.itertuples()]

# --- 34 offres collectées (C001-C034)
with open(HERE / "raw_collecte.tsv", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        rows.append(dict(offer_id=r["id"], source=r["source"], status=r["status"], title=r["title"],
                         company=r["company"], city=r["city"], contract=r["contract"], exp_raw=r["exp_min"],
                         posted=r["posted"], domain=r["domain"], url=r["url"]))
        sk += [(r["id"], s.strip()) for s in r["skills"].split(";") if s.strip()]

offers = pd.DataFrame(rows)


def level(x):
    if x == "confirmé":
        return "Confirmé (4 ans et +)"
    if x == "":
        return "Non précisé"
    y = int(x)
    return "Débutant (0-1 an)" if y <= 1 else "Junior (2-3 ans)" if y <= 3 else "Confirmé (4 ans et +)"


offers["experience_min_years"] = offers["exp_raw"].where(offers["exp_raw"].str.fullmatch(r"\d+"), "")
offers["experience_level"] = offers["exp_raw"].map(level)
offers["date_2026_verified"] = offers["posted"].str.match(r"2026-\d\d")
offers = offers.drop(columns="exp_raw")
cols = ["offer_id", "company", "title", "domain", "city", "contract", "experience_min_years",
        "experience_level", "status", "posted", "date_2026_verified", "source", "url"]
offers = offers[cols].sort_values("offer_id")

skills = pd.DataFrame(sk, columns=["offer_id", "skill"]).drop_duplicates()
skills["category"] = skills["skill"].map(category)
skills = skills[["offer_id", "category", "skill"]].sort_values(["offer_id", "category", "skill"])

offers.to_csv(REPO / "data/offers.csv", index=False)
skills.to_csv(REPO / "data/skills.csv", index=False)
print(len(offers), "offres;", int(offers.date_2026_verified.sum()), "datées 2026;", skills.skill.nunique(), "compétences")
print(offers.groupby("experience_level").size())
