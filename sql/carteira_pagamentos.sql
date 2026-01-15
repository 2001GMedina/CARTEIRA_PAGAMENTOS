WITH
    PARCELAS
    AS
    (
        SELECT
            CLIENTE_ID,
            COUNT(*) AS QTD_FATURAS_ABERTO
        FROM
            (                                                                                                                                                                                                                                              SELECT
                    CLIENTE_ID
                FROM
                    FATURAS_CARTAO_CREDITO
                WHERE
                STATUS_PROVIDER = 'pending'
                    AND DATA_VENCIMENTO >= DATEADD(MONTH, -4, GETDATE())
            UNION
            ALL
                SELECT
                    CLIENTE_ID
                FROM
                    FATURAS_CARNE
                WHERE
                STATUS_PROVIDER = 'overdue'
                    AND DATA_VENCIMENTO >= DATEADD(MONTH, -4, GETDATE())
        ) AS FATURAS_ABERTAS
        GROUP BY
        CLIENTE_ID
    ),
    CARTEIRA
    AS
    (
        SELECT
            FP.NOME AS FORMA_PAGAMENTO,
            SC.ID AS SC_ID,
            SC.NOME AS STATUS,
            C.ID,
            C.DATA_INICIO_PLANO,
            C.NOME,
            C.CPF,
            C.ATIVO,
            C.DATA_CRIACAO,
            C.DIA_VENCIMENTO_BOLETO,
            CASE
            WHEN C.FORMA_PAGAMENTO_ID = 14 THEN DATEFROMPARTS(
                YEAR(GETDATE()),
                MONTH(GETDATE()),
                CASE
                    WHEN C.DIA_VENCIMENTO_BOLETO > DAY(EOMONTH(GETDATE())) THEN DAY(EOMONTH(GETDATE()))
                    ELSE C.DIA_VENCIMENTO_BOLETO
                END
            )
            ELSE DATEFROMPARTS(
                YEAR(GETDATE()),
                MONTH(GETDATE()),
                CASE
                    WHEN DAY(C.DATA_INICIO_PLANO) > DAY(EOMONTH(GETDATE())) THEN DAY(EOMONTH(GETDATE()))
                    ELSE DAY(C.DATA_INICIO_PLANO)
                END
            )
        END AS DATA_VENCIMENTO,
            CASE
    WHEN C.FORMA_PAGAMENTO_ID = 14 THEN CAST(
        ISNULL(
            NULLIF(C.VALOR_DESCONTO_CARNE, 0),
            P.MENSALIDADE_CARNE
        ) AS FLOAT
    )
    WHEN C.FORMA_PAGAMENTO_ID = 13 THEN CAST(
        ISNULL(
            NULLIF(C.VALOR_DESCONTO_CARTAO_CREDITO, 0),
            P.MENSALIDADE_CARTAO_CREDITO
        ) AS FLOAT
    )
    ELSE CAST(NULL AS FLOAT)
    END AS VALOR_MENSALIDADE,
            PAR.QTD_FATURAS_ABERTO

        FROM
            CLIENTES C
            LEFT JOIN PLANOS P ON C.PLANO_ID = P.ID
            LEFT JOIN FORMAS_PAGAMENTO FP ON C.FORMA_PAGAMENTO_ID = FP.ID
            LEFT JOIN STATUS_CLIENTE SC ON C.STATUS_CLIENTE_ID = SC.ID
            LEFT JOIN ENDERECOS E ON C.ENDERECO_ID = E.ID
            LEFT JOIN PARCELAS PAR ON C.ID = PAR.CLIENTE_ID
        WHERE
        C.STATUS_CLIENTE_ID IN (3, 33)
            AND C.FORMA_PAGAMENTO_ID IN (13, 14)
            AND C.ID NOT IN (111295, 111302, 111304, 91225)
            AND P.ID NOT IN (19, 10, 20)
            AND C.ATIVO = 1
    )
SELECT /**TOP 10**/
    GETDATE() AS DATA_INT,
    C.*,
    CASE 
        WHEN C.QTD_FATURAS_ABERTO IS NULL THEN CAST(C.VALOR_MENSALIDADE AS FLOAT) 
        ELSE CAST(ROUND(C.VALOR_MENSALIDADE * C.QTD_FATURAS_ABERTO, 2) AS FLOAT) 
    END AS VALOR_FINAL,
    CASE
        WHEN GETDATE() < C.DATA_VENCIMENTO THEN 'PENDENTE'
        WHEN GETDATE() > C.DATA_VENCIMENTO AND C.SC_ID = 33 THEN 'ATRASADO'
        ELSE 'PAGO'
    END AS STATUS_PAG
FROM
    CARTEIRA C
ORDER BY
    DATA_VENCIMENTO