# ============================================================
# Mini-Projeto Módulo 2 — Visualização de Dados e BI
# Aluno: André Abranjo Ramos | Turma T2
# Script: consolidação das bases BPS 2020–2026
# Objetivo: deszipar, padronizar e concatenar os arquivos
# anuais do Banco de Preços em Saúde em uma base única
# ============================================================

import os
import zipfile
import pandas as pd
import glob

# ------------------------------------------------------------
# 0. CONFIGURAÇÃO DE CAMINHOS
# ------------------------------------------------------------

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_DIR    = os.path.join(BASE_DIR, "..", "data", "raw")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "data", "processed")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "BPS_20_26_AndreAbranjoRamos.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# 1. DESZIPAR ARQUIVOS
# Objetivo: extrair todos os ZIPs encontrados na pasta raw
# ------------------------------------------------------------

print("=" * 55)
print("ETAPA 1 — DESCOMPACTANDO ARQUIVOS ZIP")
print("=" * 55)

zips = glob.glob(os.path.join(RAW_DIR, "*.zip"))

if not zips:
    print("⚠️  Nenhum arquivo ZIP encontrado em data/raw/")
else:
    for zip_path in zips:
        print(f"  Descompactando: {os.path.basename(zip_path)}")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(RAW_DIR)
    print(f"✅ {len(zips)} arquivo(s) descompactado(s)")

# ------------------------------------------------------------
# 2. LOCALIZAR CSVS EXTRAÍDOS
# ------------------------------------------------------------

print("\n" + "=" * 55)
print("ETAPA 2 — LOCALIZANDO ARQUIVOS CSV")
print("=" * 55)

csvs = glob.glob(os.path.join(RAW_DIR, "**", "*.csv"), recursive=True)
csvs += glob.glob(os.path.join(RAW_DIR, "*.csv"))
csvs = list(set(csvs))  # remove duplicatas de caminho

print(f"  CSVs encontrados: {len(csvs)}")
for c in sorted(csvs):
    print(f"  → {os.path.basename(c)}")

# ------------------------------------------------------------
# 3. CARREGAR E INSPECIONAR CADA ARQUIVO
# Objetivo: mapear discrepâncias de colunas entre os anos
# ------------------------------------------------------------

print("\n" + "=" * 55)
print("ETAPA 3 — INSPECIONANDO ESTRUTURA POR ANO")
print("=" * 55)

dfs = []
discrepancias = {}

for csv_path in sorted(csvs):
    nome = os.path.basename(csv_path)

    # Tenta encodings comuns em bases brasileiras
    for enc in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(
                csv_path,
                encoding=enc,
                sep=";",          # BPS usa ponto-e-vírgula
                low_memory=False,
                dtype=str          # lê tudo como texto primeiro
            )
            print(f"\n  ✅ {nome} | encoding: {enc} | "
                  f"linhas: {df.shape[0]:,} | colunas: {df.shape[1]}")
            break
        except Exception:
            continue
    else:
        print(f"  ❌ Falha ao ler: {nome}")
        continue

    # Padronizar nomes de colunas
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
    )

    # Identificar ano a partir do nome do arquivo
    ano = "".join(filter(str.isdigit, nome))[:4]
    df["ano_arquivo"] = ano

    discrepancias[nome] = df.columns.tolist()
    dfs.append(df)

# Mapear diferenças de colunas entre arquivos
print("\n" + "=" * 55)
print("ETAPA 3b — MAPEAMENTO DE DISCREPÂNCIAS")
print("=" * 55)

if dfs:
    todas_colunas = set()
    for cols in discrepancias.values():
        todas_colunas.update(cols)

    for nome, cols in discrepancias.items():
        faltando = todas_colunas - set(cols)
        if faltando:
            print(f"\n  ⚠️  {nome} — colunas ausentes:")
            for c in sorted(faltando):
                print(f"      - {c}")
        else:
            print(f"  ✅ {nome} — estrutura completa")

# ------------------------------------------------------------
# 4. CONCATENAR TODAS AS BASES
# ------------------------------------------------------------

print("\n" + "=" * 55)
print("ETAPA 4 — CONCATENANDO BASES")
print("=" * 55)

if not dfs:
    print("❌ Nenhum arquivo carregado. Verifique a pasta data/raw/")
else:
    df_total = pd.concat(dfs, ignore_index=True, sort=False)
    print(f"  Total de linhas concatenadas: {df_total.shape[0]:,}")
    print(f"  Total de colunas: {df_total.shape[1]}")

    # ------------------------------------------------------------
    # 5. TRATAMENTO E LIMPEZA
    # ------------------------------------------------------------

    print("\n" + "=" * 55)
    print("ETAPA 5 — TRATAMENTO DA BASE CONSOLIDADA")
    print("=" * 55)

    # 5a. Verificar nulos por coluna
    print("\n  Nulos por coluna (top 10):")
    nulos = df_total.isna().sum().sort_values(ascending=False).head(10)
    print(nulos)

    # 5b. Verificar duplicatas
    duplicatas = df_total.duplicated().sum()
    print(f"\n  Duplicatas encontradas: {duplicatas:,}")
    if duplicatas > 0:
        df_total = df_total.drop_duplicates()
        print(f"  ✅ Duplicatas removidas. Linhas restantes: {df_total.shape[0]:,}")

    # 5c. Converter campos numéricos
    # Campos comuns do BPS — ajuste conforme colunas reais
    campos_numericos = ["preco_unitario", "preco_total", "quantidade"]
    for campo in campos_numericos:
        if campo in df_total.columns:
            df_total[campo] = (
                df_total[campo]
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df_total[campo] = pd.to_numeric(df_total[campo], errors="coerce")
            print(f"  ✅ Campo numérico convertido: {campo}")

    # 5d. Padronizar campo de data
    campos_data = ["data_compra", "data_abertura", "data"]
    for campo in campos_data:
        if campo in df_total.columns:
            df_total[campo] = pd.to_datetime(
                df_total[campo], dayfirst=True, errors="coerce"
            )
            print(f"  ✅ Campo de data convertido: {campo}")

    # ------------------------------------------------------------
    # 6. EXPORTAR BASE CONSOLIDADA
    # ------------------------------------------------------------

    print("\n" + "=" * 55)
    print("ETAPA 6 — EXPORTANDO BASE CONSOLIDADA")
    print("=" * 55)

    df_total.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig", sep=";")
    tamanho_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"  ✅ Arquivo salvo: {OUTPUT_FILE}")
    print(f"  Tamanho: {tamanho_mb:.1f} MB")
    print(f"  Linhas: {df_total.shape[0]:,}")
    print(f"  Colunas: {df_total.shape[1]}")

    print("\n" + "=" * 55)
    print("CONSOLIDAÇÃO CONCLUÍDA COM SUCESSO")
    print("=" * 55)