# NCAAF Weekly Top 25 Best Card

Independent Friday-morning college-football selection and results system.

## Weekly email

The card contains five games involving at least one current AP Top 25 team. Games with two ranked teams always receive priority over games with only one ranked team.

Each game contains:

1. One spread selection using the Friday-morning line.
2. One running-back touchdown scorer.
3. One wide receiver or tight-end touchdown scorer.

The email begins with the prior week's frozen-card results. Spread pushes are tracked separately from wins and losses.

## Schedule

GitHub Actions publishes on Friday morning with three backup attempts. Google Apps Script checks the summary sheet hourly on Friday morning and sends each season/week only once.

## Data

- ESPN college-football schedule, AP ranking and odds feeds.
- cfbfastR play-level player statistics and current rosters.
- Recent team scoring margin and player touchdown/red-zone usage.

## Google Sheets tabs

- `NCAAF Best Card Email Summary`
- `NCAAF Best Card Archive`
- `NCAAF Best Card Results`

## Required GitHub Actions secret

- `GOOGLE_SHEETS_ID`

Google authentication uses GitHub OIDC and Google Workload Identity Federation. The spreadsheet-bound Apps Script is in `apps_script/NcaafBestCardEmail.gs`.

## Validation

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```
