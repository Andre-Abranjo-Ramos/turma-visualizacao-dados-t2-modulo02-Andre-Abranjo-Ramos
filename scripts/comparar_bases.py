# ============================================================
# Mini-Projeto Módulo 2 — Visualização de Dados e BI
# Aluno: André Abranjo Ramos | Turma T2
# Script: comparação das bases anuais BPS 2020–2026
# Objetivo: verificar se as bases são estruturalmente iguais
# ou diferentes antes da consolidação e da conexão com Power BI
# Responde: colunas iguais? tipos iguais? volumes coerentes?
# ============================================================

import os
import glob
import pandas as pd

# ------------------------------------------------------------
# 0. CONFIGURAÇÃO
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR  = os.path.join(BASE_DIR, "..", "data", "raw")
OUT_DIR  = os.path.join(BASE_DIR, "..", "data", "processed")

# ------------------------------------------------------------
# 1. CARREGAR TODAS AS BASES ANUAIS
# ------------------------------------------------------------

print("=" * 60)
print("COMPARAÇÃO DAS BASES ANUAIS — BPS 2020 a 2026")
print("=" * 60)

csvs = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))

if not csvs:
    print("❌ Nenhum CSV encontrado em data/raw/")
    exit()

bases = {}

for csv_path in csvs:
    nome = os.path.basename(csv_path)
    ano  = "".join(filter(str.isdigit, nome))[:4]

    for enc in ["utf-8", "latin-1", "cp1252", "utf-8-sig"]:
        try:
            df = pd.read_csv(
                csv_path,
                encoding=enc,
                sep=";",
                low_memory=False,
                dtype=str
            )
            # Padronizar colunas
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(" ", "_")
                .str.normalize("NFKD")
                .str.encode("ascii", errors="ignore")
                .str.decode("ascii")
                .str.replace(r"[^a-z0-9_]", "", regex=True)
            )
            bases[ano] = {"df": df, "nome": nome, "encoding": enc}
            print(f"\n  ✅ {nome}")
            print(f"     Encoding : {enc}")
            print(f"     Linhas   : {df.shape[0]:,}")
            print(f"     Colunas  : {df.shape[1]}")
            break
        except Exception:
            continue
    else:
        print(f"  ❌ Falha ao ler: {nome}")

# ------------------------------------------------------------
# 2. COMPARAÇÃO DE COLUNAS ENTRE ANOS
# Objetivo: detectar se algum ano tem coluna a mais,
# a menos ou com nome diferente
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("BLOCO 1 — COMPARAÇÃO DE COLUNAS ENTRE ANOS")
print("=" * 60)

anos      = sorted(bases.keys())
ref_ano   = anos[0]
ref_cols  = set(bases[ref_ano]["df"].columns)

print(f"\n  Referência: {ref_ano} ({len(ref_cols)} colunas)")

resultado_colunas = {}

for ano in anos[1:]:
    cols_ano   = set(bases[ano]["df"].columns)
    so_na_ref  = ref_cols - cols_ano
    so_no_ano  = cols_ano - ref_cols
    em_comum   = ref_cols & cols_ano

    resultado_colunas[ano] = {
        "total"       : len(cols_ano),
        "em_comum"    : len(em_comum),
        "so_na_ref"   : sorted(so_na_ref),
        "so_no_ano"   : sorted(so_no_ano),
        "identicas"   : len(so_na_ref) == 0 and len(so_no_ano) == 0
    }

    status = "✅ IDÊNTICA" if resultado_colunas[ano]["identicas"] else "⚠️  DIVERGENTE"
    print(f"\n  {ano} vs {ref_ano} — {status}")
    print(f"     Colunas em comum  : {len(em_comum)}")

    if so_na_ref:
        print(f"     Só em {ref_ano}       : {so_na_ref}")
    if so_no_ano:
        print(f"     Só em {ano}          : {so_no_ano}")

# ------------------------------------------------------------
# 3. COMPARAÇÃO DE TIPOS DE DADOS
# Objetivo: detectar se o mesmo campo tem tipo diferente
# entre anos — problema comum em bases públicas anuais
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("BLOCO 2 — COMPARAÇÃO DE TIPOS DE DADOS")
print("=" * 60)

# Colunas presentes em todos os anos
colunas_comuns = ref_cols.copy()
for ano in anos[1:]:
    colunas_comuns &= set(bases[ano]["df"].columns)

print(f"\n  Colunas presentes em todos os anos: {len(colunas_comuns)}")

divergencias_tipo = []

for col in sorted(colunas_comuns):
    tipos = {ano: bases[ano]["df"][col].dtype for ano in anos}
    tipos_unicos = set(str(v) for v in tipos.values())
    if len(tipos_unicos) > 1:
        divergencias_tipo.append(col)
        print(f"\n  ⚠️  Coluna com tipo divergente: {col}")
        for ano, tipo in tipos.items():
            print(f"     {ano}: {tipo}")

if not divergencias_tipo:
    print("\n  ✅ Todos os tipos de dados são consistentes entre os anos")

# ------------------------------------------------------------
# 4. COMPARAÇÃO DE VOLUME POR ANO
# Objetivo: detectar anos com volume muito diferente do
# esperado — pode indicar arquivo incompleto ou corrompido
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("BLOCO 3 — VOLUME DE REGISTROS POR ANO")
print("=" * 60)

volumes = {ano: bases[ano]["df"].shape[0] for ano in anos}
media_vol = sum(volumes.values()) / len(volumes)

print(f"\n  {'Ano':<8} {'Registros':>12} {'vs Média':>12} {'Status':>12}")
print("  " + "-" * 48)

for ano, vol in sorted(volumes.items()):
    variacao = ((vol - media_vol) / media_vol) * 100
    if abs(variacao) > 50:
        status = "⚠️  VERIFICAR"
    else:
        status = "✅ OK"
    print(f"  {ano:<8} {vol:>12,} {variacao:>+11.1f}% {status:>12}")

# ------------------------------------------------------------
# 5. COMPARAÇÃO DE NULOS POR COLUNA E POR ANO
# Objetivo: identificar se algum ano tem campo crítico
# com alto percentual de nulos
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("BLOCO 4 — NULOS EM CAMPOS CRÍTICOS POR ANO")
print("=" * 60)

# Campos mais relevantes para o dashboard
campos_criticos = [
    "preco_total", "preco_unitario", "quantidade",
    "uf", "municipio", "nome_fantasia_fornecedor",
    "descricao_produto", "modalidade_compra",
    "data_compra", "nome_instituicao"
]

# Filtra apenas os que existem nas bases
campos_verificar = [
    c for c in campos_criticos
    if any(c in bases[ano]["df"].columns for ano in anos)
]

print(f"\n  {'Campo':<35}", end="")
for ano in anos:
    print(f"  {ano:>6}", end="")
print()
print("  " + "-" * (35 + 8 * len(anos)))

for campo in campos_verificar:
    print(f"  {campo:<35}", end="")
    for ano in anos:
        df = bases[ano]["df"]
        if campo in df.columns:
            pct = df[campo].isna().mean() * 100
            print(f"  {pct:>5.1f}%", end="")
        else:
            print(f"  {'N/A':>6}", end="")
    print()

# ------------------------------------------------------------
# 6. COMPARAÇÃO DE VALORES ÚNICOS EM CAMPOS CATEGÓRICOS
# Objetivo: verificar se as categorias são consistentes
# entre os anos (ex: estados, modalidades)
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("BLOCO 5 — VALORES ÚNICOS EM CAMPOS CATEGÓRICOS")
print("=" * 60)

campos_cat = ["uf", "modalidade_compra"]

for campo in campos_cat:
    anos_com_campo = [a for a in anos if campo in bases[a]["df"].columns]
    if not anos_com_campo:
        continue

    print(f"\n  Campo: {campo}")
    todos_valores = set()
    valores_por_ano = {}
    for ano in anos_com_campo:
        vals = set(bases[ano]["df"][campo].dropna().unique())
        valores_por_ano[ano] = vals
        todos_valores |= vals

    for ano in anos_com_campo:
        ausentes = todos_valores - valores_por_ano[ano]
        print(f"    {ano}: {len(valores_por_ano[ano]):>3} valores únicos", end="")
        if ausentes:
            print(f" | ⚠️  ausentes em relação ao total: {sorted(ausentes)}")
        else:
            print(" ✅")

# ------------------------------------------------------------
# 7. RELATÓRIO FINAL DE COMPATIBILIDADE
# ------------------------------------------------------------

print("\n" + "=" * 60)
print("RELATÓRIO FINAL — COMPATIBILIDADE ENTRE BASES")
print("=" * 60)

bases_identicas    = all(r["identicas"] for r in resultado_colunas.values())
sem_div_tipo       = len(divergencias_tipo) == 0
anos_incompletos   = [
    ano for ano, vol in volumes.items()
    if abs((vol - media_vol) / media_vol) > 0.5
]

print(f"""
  Estrutura de colunas idêntica entre todos os anos : {'✅ SIM' if bases_identicas else '⚠️  NÃO — ver Bloco 1'}
  Tipos de dados consistentes                       : {'✅ SIM' if sem_div_tipo else '⚠️  NÃO — ver Bloco 2'}
  Anos com volume atípico                           : {anos_incompletos if anos_incompletos else '✅ Nenhum'}

  CONCLUSÃO:
""")

if bases_identicas and sem_div_tipo and not anos_incompletos:
    print("  ✅ As bases são COMPATÍVEIS para concatenação direta.")
    print("     Pode prosseguir com o script consolidar_bps.py")
else:
    print("  ⚠️  As bases apresentam DIVERGÊNCIAS.")
    print("     Revise os pontos acima antes de concatenar.")
    print("     Documente as decisões de tratamento no README.md")

# ------------------------------------------------------------
# 8. EXPORTAR RELATÓRIO EM CSV PARA DOCUMENTAÇÃO
# ------------------------------------------------------------

linhas_relatorio = []
for ano, r in resultado_colunas.items():
    linhas_relatorio.append({
        "ano"               : ano,
        "total_colunas"     : r["total"],
        "colunas_em_comum"  : r["em_comum"],
        "estrutura_identica": r["identicas"],
        "colunas_ausentes"  : str(r["so_na_ref"]),
        "colunas_extras"    : str(r["so_no_ano"]),
        "registros"         : volumes[ano]
    })

df_relatorio = pd.DataFrame(linhas_relatorio)
caminho_rel  = os.path.join(OUT_DIR, "relatorio_comparacao_bases.csv")
df_relatorio.to_csv(caminho_rel, index=False, encoding="utf-8-sig", sep=";")

print(f"\n  ✅ Relatório exportado: {caminho_rel}")
print("\n" + "=" * 60)
print("COMPARAÇÃO CONCLUÍDA")
print("=" * 60)