from pathlib import Path
import pandas as pd
import urllib
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parents[0]

load_dotenv(project_root / ".env")

data_path = project_root / "data" / "raw" / "dynamic_supply_chain_logistics_dataset.csv"

db_host = os.getenv("SQL_SERVER_HOST", "localhost")
db_port = os.getenv("SQL_SERVER_PORT", "1433")
db_user = os.getenv("SQL_ADMIN_USER")
db_password = os.getenv("SQL_ADMIN_PASSWORD")

print(f"Loading CSV from {data_path}...")

df = pd.read_csv(data_path)

legacy_mapping = {
    "timestamp": "TS_UTC",
    "vehicle_gps_latitude": "V_LAT",
    "vehicle_gps_longitude": "V_LON",
    "iot_temperature": "IOT_TEMP_VAL_C",
    "cargo_condition_status": "CGO_COND_CD",
    "risk_classification": "RISK_CLS_TXT",
    "delay_probability": "DELAY_PROB_DEC",
    "port_congestion_level": "PRT_CNG_LVL",
    "route_risk_level": "RT_RSK_IDX",
}

df_legacy = (
    df[list(legacy_mapping.keys())]
    .rename(columns=legacy_mapping)
)

df_legacy["SYS_INGEST_FLAG"] = "Y"

print("Connecting to legacy MSSQL Database...")

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={db_host},{db_port};"
    "DATABASE=master;"
    f"UID={db_user};"
    f"PWD={db_password};"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

params = urllib.parse.quote_plus(connection_string)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={params}",
    pool_pre_ping=True,
)

print("Testing SQL Server connection...")

try:
    with engine.connect() as conn:
        result = conn.exec_driver_sql("SELECT @@VERSION")
        print(result.fetchone())

    print("✅ SQL Server connection successful!")

except Exception as e:
    print("❌ SQL Server connection failed:")
    print(e)
    raise

table_name = "TBL_SC_FLEET_HIST_RAW"

print(
    f"Ingesting into {table_name}. "
    f"{len(df_legacy):,} rows..."
)

df_legacy.to_sql(
    table_name,
    engine,
    if_exists="replace",
    index=False,
    schema="dbo",
)

print("✅ Legacy data ingestion complete!")