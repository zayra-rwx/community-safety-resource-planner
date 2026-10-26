from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/LAPD_NIBRS_Offenses_Dataset_20261004.csv'
PROCESSED = ROOT / 'data/processed/lapd_nibrs_offenses.parquet'
REPORTS = ROOT / 'reports/phase2'
START_DATE = '2025-01-01'
EXPECTED_BYTES = 178693032
EXPECTED_SHA256 = '97a8dbadafe60eee4b4d86e99769df3aaa23307d45539283879414f8760b39e5'
EXPECTED_ROWS = 489955
SOURCE_COLUMNS = [
    'CaseNo', 'UniqueNIBRNo', 'Date Rptd', 'Date OCC', 'Time OCC', 'AREA',
    'AREA NAME', 'RPT Dist No', 'TotalOffenseCount', 'Group', 'NIBR Code',
    'NIBR Description', 'Crime Against', 'Premise Cd', 'Premise Desc',
    'Weapon Used Cd', 'Weapon Desc', 'Status', 'Status Desc', 'TotalVictimCount',
    'Victim Shot', 'Domestic Violence Crime', 'Hate Crime', 'Gang-related Crime',
    'Transit-related Crime', 'Homeless-Victim Crime', 'Homeless-Suspect Crime',
    'Homeless-Arrestee Crime', 'LOCATION', 'LAT', 'LON',
]
DATE_FORMAT = '%Y %b %d %I:%M:%S %p'
# Broad screening box, not an administrative boundary or geocoding verification.
LAT_BOUNDS = (33.5, 34.9)
LON_BOUNDS = (-118.9, -117.5)
FREQUENCY_WEIGHT = 0.60
PERSISTENCE_WEIGHT = 0.40
