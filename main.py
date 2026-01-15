import os
from dotenv import load_dotenv
import pandas as pd
from decimal import Decimal

from mods.logger import setup_logger, get_logger
from mods.sql_server import connect_sql_server, run_query


def read_sql_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "DIA_VENCIMENTO_BOLETO" in df.columns:
        df["DIA_VENCIMENTO_BOLETO"] = df["DIA_VENCIMENTO_BOLETO"].apply(
            lambda x: str(int(x)) if pd.notna(x) else None
        )

    # ================================
    # SC_ID -> INT
    # ================================
    if "SC_ID" in df.columns:
        df["SC_ID"] = df["SC_ID"].apply(
            lambda x: int(x) if pd.notna(x) else None
        )

#    if "QTD_FATURAS_ABERTO" in df.columns:
 #       df["QTD_FATURAS_ABERTO"] = df["QTD_FATURAS_ABERTO"].apply(
  #          lambda x: int(x) if pd.notna(x) else None
   #     )

    # ================================
    # ATIVO -> BIT
    # ================================
    if "ATIVO" in df.columns:
        df["ATIVO"] = df["ATIVO"].apply(
            lambda x: bool(x) if pd.notna(x) else None
        )

    # ================================
    # PASSO CRÍTICO PARA PYODBC
    # Remove NAType / NaN
    # ================================
    df = df.astype(object)
    df = df.where(pd.notnull(df), None)

    return df


def insert_dataframe(conn, df: pd.DataFrame, schema: str, table: str):
    cursor = conn.cursor()

    full_table_name = f"{schema}.{table}"
    columns = list(df.columns)

    col_names = ",".join(columns)
    placeholders = ",".join(["?"] * len(columns))

    insert_sql = f"""
        INSERT INTO {full_table_name} ({col_names})
        VALUES ({placeholders})
    """

    cursor.fast_executemany = True
    cursor.executemany(
        insert_sql,
        df.itertuples(index=False, name=None)
    )

    conn.commit()
    cursor.close()


def log_dataframe_preview(logger, df: pd.DataFrame):
    logger.info("Preview dos dados (5 primeiras linhas):")
    logger.info(df.head(5).to_string())

    if "VALOR_MENSALIDADE" in df.columns:
        logger.info("Tipos VALOR_MENSALIDADE:")
        logger.info(
            df["VALOR_MENSALIDADE"]
            .apply(type)
            .value_counts()
            .to_string()
        )

        logger.info("Estatísticas VALOR_MENSALIDADE:")
        logger.info(
            df["VALOR_MENSALIDADE"]
            .describe()
            .to_string()
        )


def main():
    setup_logger()
    logger = get_logger()

    logger.info("Iniciando carga CARTEIRA_PAGAMENTOS")

    load_dotenv()

    crm_conn_string = os.getenv("CRM_CONN_STRING")
    dw_conn_string = os.getenv("DW_CONN_STRING")
    target_schema = os.getenv("TARGET_SCHEMA", "data_warehouse")
    target_table = os.getenv("TARGET_TABLE")

    if not all([crm_conn_string, dw_conn_string, target_table]):
        logger.error("Variáveis de ambiente obrigatórias não carregadas")
        return

    sql_path = os.path.join("sql", "carteira_pagamentos.sql")
    query = read_sql_file(sql_path)

    crm_conn = None
    dw_conn = None

    try:
        logger.info("Conectando ao CRM")
        crm_conn = connect_sql_server(crm_conn_string)

        logger.info("Executando query no CRM")
        df = run_query(crm_conn, query)

        logger.info(f"Linhas retornadas: {len(df)}")

    finally:
        if crm_conn:
            crm_conn.close()
            logger.info("Conexão CRM encerrada")

    if df.empty:
        logger.warning("Nenhum dado retornado")
        return

    logger.info("Sanitizando dados")
    df = sanitize_dataframe(df)

    log_dataframe_preview(logger, df)

    try:
        logger.info("Conectando ao DW")
        dw_conn = connect_sql_server(dw_conn_string)

        logger.info(f"Inserindo dados em {target_schema}.{target_table}")
        insert_dataframe(dw_conn, df, target_schema, target_table)

        logger.info(f"{len(df)} linhas inseridas com sucesso")

    except Exception:
        if dw_conn:
            dw_conn.rollback()
        logger.exception("Erro durante inserção no DW")
        raise

    finally:
        if dw_conn:
            dw_conn.close()
            logger.info("Conexão DW encerrada")

    logger.info("Carga finalizada com sucesso")


if __name__ == "__main__":
    main()