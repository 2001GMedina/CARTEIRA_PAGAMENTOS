import pandas as pd
import pyodbc
import os
from dotenv import load_dotenv

# ========================
# CONFIGURAÇÕES
# ========================
load_dotenv()

EXCEL_PATH = os.path.join("output", "TEMPLATE_TABELA_DEZ_25.xlsx")
TABLE_NAME = "[data_warehouse].[CARTEIRA_PAGAMENTOS]"

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=162.215.175.144;"
    "DATABASE=admin_dwasbevi;"
    "UID=asbevi_tech;"
    "PWD=Atlas032025*;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

# ========================
# FUNÇÕES
# ========================
def normalize_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    DATE_COLS = [
        "DATA_INICIO_PLANO",
        "DATA_VENCIMENTO",
    ]

    DATETIME_COLS = [
        "DATA_CRIACAO",
        "DATA_INT",
    ]

    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=True
            ).dt.date

    for col in DATETIME_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=True
            )

    return df

# ========================
# LEITURA DO EXCEL
# ========================
print("📥 Lendo arquivo Excel...")
df = pd.read_excel(EXCEL_PATH, engine="openpyxl")

print(f"✅ {len(df)} linhas carregadas")

# ========================
# NORMALIZAÇÕES
# ========================
df = normalize_date_columns(df)

# ESSENCIAL p/ pyodbc (NaN / NaT → None)
df = df.astype(object).where(pd.notnull(df), None)

# ========================
# MONTAGEM DO INSERT
# ========================
columns = list(df.columns)

columns_sql = ", ".join(f"[{col}]" for col in columns)
placeholders = ", ".join("?" for _ in columns)

sql_insert = f"""
INSERT INTO {TABLE_NAME} ({columns_sql})
VALUES ({placeholders})
"""

data = list(df.itertuples(index=False, name=None))

# ========================
# INSERÇÃO NO BANCO
# ========================
print("🔌 Conectando ao banco...")
conn = pyodbc.connect(CONN_STR)
cursor = conn.cursor()

cursor.fast_executemany = True

print("📤 Inserindo dados...")
cursor.executemany(sql_insert, data)

conn.commit()
cursor.close()
conn.close()

print("🎉 Inserção concluída com sucesso!")
