# Dashboard Landtagswahl 2026 Stuttgart Ost

Interaktives Streamlit-Dashboard zur Auswertung der Landtagswahl 2026 fuer Buendnis 90 / Die Gruenen in Stuttgart Ost.

## Funktionsumfang

- KPI-Uebersicht fuer Wahlbeteiligung, Gruene Erst- und Zweitstimmen, Split-Ticket-Differenz, Ausschoepfungsgrad und Vorsprung zur CDU
- Kartenansicht fuer Stuttgart Ost auf Basis des GPKG-Layers `03_Ost`
- Vergleich von Urnenwahl, Briefwahl und aggregierten Gesamtbezirken
- Bezirksranking, Mobilisierungssicht und Parteienvergleich

## Start

Das Projekt verwendet `uv`.

```powershell
uv run streamlit run main.py
```

Die App startet danach lokal im Browser.

## Datengrundlage

- `ltw26-ergebnisse.csv`: Ergebnisdaten auf Wahlkreis- und Wahlbezirksebene
- `wahlbezirke.gpkg`: Geometrien fuer Stuttgart Ost, genutzt ueber den Layer `03_Ost`
