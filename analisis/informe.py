"""Ejecuta las consultas de sql/ sobre los datos recogidos y genera los gráficos del informe.

Uso:
    git worktree add ../valenbisi-datos datos      # los datos viven en la rama `datos`
    pip install -r requirements-analisis.txt
    python analisis/informe.py ../valenbisi-datos/datos

Salidas:
    resultados/*.csv   una tabla por consulta
    docs/img/*.png     los gráficos del README
"""
import math
import re
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql"
RESULTADOS = RAIZ / "resultados"
IMG = RAIZ / "docs" / "img"

# Paleta validada (comprobación de daltonismo y contraste): rojo = se vacía, azul = se llena.
ROJO, AZUL, GRIS = "#e34948", "#2a78d6", "#a8a7a2"
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e6e5e0"
FRANJAS = ["00-06", "06-10", "10-14", "14-17", "17-21", "21-24"]

# Supuesto operativo para la ruta: una furgoneta lleva hasta 20 bicis por viaje.
CAPACIDAD_FURGONETA = 20


def consultas(fichero):
    """Divide un fichero .sql en sentencias, quitando comentarios."""
    texto = re.sub(r"--[^\n]*", "", fichero.read_text(encoding="utf-8"))
    return [s.strip() for s in texto.split(";") if s.strip()]


def ejecutar(con, datos):
    """Ejecuta los ficheros de sql/ en orden y guarda cada SELECT en resultados/."""
    RESULTADOS.mkdir(exist_ok=True)
    for fichero in sorted(SQL.glob("*.sql")):
        selects = 0
        for sentencia in consultas(fichero):
            sentencia = sentencia.replace("{{DATOS}}", datos)
            if sentencia.upper().startswith(("SELECT", "WITH")):
                selects += 1
                df = con.sql(sentencia).df()
                nombre = f"{fichero.stem}_{selects}.csv"
                df.to_csv(RESULTADOS / nombre, index=False)
                print(f"\n== {fichero.name} · consulta {selects}\n{df.to_string(index=False)}")
            else:
                con.sql(sentencia)


def emparejar(con):
    """Reparte las bicis sobrantes hacia las estaciones que las necesitan, empezando por los
    pares más cercanos (algoritmo voraz). Devuelve una lista de traslados."""
    dar = {r[0]: -r[1] for r in con.sql(
        "SELECT estacion_id, bicis_a_mover FROM necesidad WHERE bicis_a_mover < 0").fetchall()}
    recibir = {r[0]: r[1] for r in con.sql(
        "SELECT estacion_id, bicis_a_mover FROM necesidad WHERE bicis_a_mover > 0").fetchall()}
    nombres = dict(con.sql("SELECT estacion_id, nombre FROM necesidad").fetchall())
    traslados = []
    for origen, destino, metros in con.sql(
            "SELECT origen, destino, metros FROM distancias ORDER BY metros").fetchall():
        n = min(dar[origen], recibir[destino])
        if n > 0:
            dar[origen] -= n
            recibir[destino] -= n
            traslados.append((nombres[origen], nombres[destino], int(n), int(metros)))
    return traslados


def estilo(ax, titulo, ylabel):
    ax.set_title(titulo, loc="left", fontsize=12, color=TINTA, pad=12)
    ax.set_ylabel(ylabel, color=TINTA_2)
    ax.grid(axis="y", color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(GRIS)
    ax.tick_params(colors=TINTA_2, length=0)


def grafico_pendulo(con):
    """Ocupación media por franja de las estaciones que se vacían y de las que se llenan."""
    df = con.sql("SELECT * FROM read_csv(?)", params=[str(RESULTADOS / "04_zonas_1.csv")]).df()
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    for grupo, color in (("tiende a llenarse", AZUL), ("tiende a vaciarse", ROJO)):
        serie = df[df.grupo == grupo].set_index("franja").reindex(FRANJAS)
        ax.plot(FRANJAS, serie.ocupacion_media, color=color, linewidth=2,
                marker="o", markersize=7, markeredgecolor="white", markeredgewidth=2, label=grupo)
        etiqueta = ("Camins al Grau y Marítim" if grupo == "tiende a llenarse"
                    else "Centro histórico y universidades")
        ax.annotate(etiqueta, (FRANJAS[-1], serie.ocupacion_media.iloc[-1]),
                    xytext=(10, 0), textcoords="offset points", va="center", color=TINTA, fontsize=9)
    estilo(ax, "Las bicis pasan el día en el centro y la noche junto al mar (laborables)",
           "Ocupación media (% de anclajes con bici)")
    ax.set_ylim(0, 100)
    ax.set_xlabel("Franja horaria", color=TINTA_2)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2,
              labelcolor=TINTA_2, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / "pendulo.png", facecolor="white")
    plt.close(fig)


def grafico_franjas(con):
    """Porcentaje de estaciones vacías y llenas por franja, laborables."""
    df = con.sql("SELECT * FROM read_csv(?)", params=[str(RESULTADOS / "03_franjas_1.csv")]).df()
    df = df[df.dia == "laborable"].set_index("franja").reindex(FRANJAS)
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    x = range(len(FRANJAS))
    ancho = 0.38
    ax.bar([i - ancho / 2 - 0.01 for i in x], df.pct_vacias, ancho, color=ROJO, label="sin bicis")
    ax.bar([i + ancho / 2 + 0.01 for i in x], df.pct_llenas, ancho, color=AZUL, label="sin anclajes libres")
    ax.set_xticks(list(x), FRANJAS)
    estilo(ax, "La red está más desequilibrada de madrugada (laborables)", "% de estaciones")
    ax.set_xlabel("Franja horaria", color=TINTA_2)
    ax.legend(frameon=False, labelcolor=TINTA_2, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / "franjas.png", facecolor="white")
    plt.close(fig)


def grafico_mapa(con, traslados):
    """Mapa de estaciones coloreadas por grupo, con los traslados propuestos."""
    est = con.sql("SELECT nombre, latitud, longitud, grupo, capacidad FROM estaciones").df()
    pos = {r.nombre: (r.longitud, r.latitud) for r in est.itertuples()}
    fig, ax = plt.subplots(figsize=(8, 7.5), dpi=150)
    for origen, destino, n, _ in traslados:
        (x0, y0), (x1, y1) = pos[origen], pos[destino]
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(
            arrowstyle="-|>", color=TINTA_2, lw=0.6 + n / 12, alpha=0.55, shrinkA=4, shrinkB=4))
    for grupo, color, z in (("equilibrada", GRIS, 1), ("tiende a llenarse", AZUL, 3),
                            ("tiende a vaciarse", ROJO, 3)):
        g = est[est.grupo == grupo]
        ax.scatter(g.longitud, g.latitud, s=12 + g.capacidad * (1.6 if z > 1 else 0.6), color=color,
                   edgecolor="white", linewidth=1, zorder=z, label=f"{grupo} ({len(g)})")
    for texto, lon, lat, dy in (("Pl. de l'Ajuntament", -0.3763, 39.4699, -26),
                                ("Universitats (Tarongers)", -0.3440, 39.4800, 16),
                                ("Camins al Grau · Marítim", -0.3320, 39.4600, -20)):
        ax.annotate(texto, (lon, lat), color=TINTA, fontsize=9, ha="center",
                    xytext=(0, dy), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    ax.set_title("Dónde se vacían y se llenan las estaciones, y traslados nocturnos propuestos",
                 loc="left", fontsize=12, color=TINTA, pad=12)
    ax.set_aspect(1 / math.cos(math.radians(39.47)))
    ax.set_xticks([])
    ax.set_yticks([])
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.legend(frameon=False, loc="lower left", labelcolor=TINTA_2, fontsize=9)
    fig.tight_layout()
    fig.savefig(IMG / "mapa.png", facecolor="white")
    plt.close(fig)


def main():
    datos = sys.argv[1] if len(sys.argv) > 1 else "datos"
    if not list(Path(datos).glob("*/*.csv.gz")):
        sys.exit(f"No hay capturas en {datos}/AAAA-MM-DD/*.csv.gz. "
                 "Crea un worktree de la rama `datos` (ver el README).")
    IMG.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(config={"threads": 2, "memory_limit": "1GB"})
    ejecutar(con, Path(datos).as_posix())

    traslados = emparejar(con)
    con.sql("CREATE TABLE traslados (origen VARCHAR, destino VARCHAR, bicis INT, metros INT)")
    con.executemany("INSERT INTO traslados VALUES (?, ?, ?, ?)", traslados)
    tabla = con.sql("SELECT * FROM traslados ORDER BY bicis DESC").df()
    tabla.to_csv(RESULTADOS / "05_redistribucion_traslados.csv", index=False)
    total = int(tabla.bicis.sum())
    viajes = math.ceil(total / CAPACIDAD_FURGONETA)
    faltan = con.sql("SELECT sum(bicis_a_mover) FROM necesidad WHERE bicis_a_mover > 0").fetchall()[0][0]
    print(f"\n== Traslados propuestos: {len(tabla)}, {total} bicis "
          f"(unas {viajes} cargas de furgoneta de {CAPACIDAD_FURGONETA}), "
          f"distancia media {tabla.metros.mean():.0f} m. "
          f"Quedan {int(faltan) - total} bicis por cubrir desde otras estaciones o el almacén."
          f"\n{tabla.to_string(index=False)}")

    grafico_pendulo(con)
    grafico_franjas(con)
    grafico_mapa(con, traslados)
    print(f"\nGráficos en {IMG.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
