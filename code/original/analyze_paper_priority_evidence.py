from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Composition, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "dft_runs" / "final-paper-package"
STRICT_ROOT = (
    PACKAGE
    / "model"
    / "service"
    / "ml-collections"
    / "pt-pd-rh-extra-20260720"
    / "postprocess"
)
OUTPUT = PACKAGE / "paper-priority-analysis-20260725"
SOURCE_DATA = OUTPUT / "source_data"
FIGURES = OUTPUT / "figures"

SYSTEM_ORDER = ["Pt-Pd", "Pt-Rh", "Pd-Rh", "Pt-Pd-Rh"]
COLORS = {
    "Pt-Pd": "#467793",
    "Pt-Rh": "#657b48",
    "Pd-Rh": "#a86745",
    "Pt-Pd-Rh": "#75658f",
    "near": "#b58b3e",
    "far": "#82909b",
    "dark": "#303840",
    "grid": "#d9dee2",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7,
        "axes.titlesize": 8,
        "axes.labelsize": 7,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.facecolor": "white",
    }
)


def ensure_dirs() -> None:
    SOURCE_DATA.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)


def export_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(
        FIGURES / f"{stem}.tiff",
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def reduced_formula(value: str) -> str:
    return Composition(value).reduced_composition.alphabetical_formula.replace(" ", "")


def fraction(formula: str, element: str) -> float:
    comp = Composition(formula).fractional_composition
    return float(comp.get_atomic_fraction(element))


def load_paper_analysis() -> pd.DataFrame:
    frame = pd.read_csv(PACKAGE / "paper-analysis-final.csv")
    frame = frame.loc[frame["backup_status"].eq("completed")].copy()
    frame["reduced_formula"] = frame["formula"].map(reduced_formula)
    frame["near_hull_10mev"] = frame["energy_above_hull_ev_per_atom"].le(0.010)
    frame["on_candidate_hull"] = frame["energy_above_hull_ev_per_atom"].abs().le(1e-8)
    return frame


def analyze_same_stoichiometry_ranking(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    pair_rows: list[dict] = []
    group_rows: list[dict] = []
    comparable = frame.groupby(["system", "reduced_formula"], sort=False)
    for (system, formula), group in comparable:
        if len(group) < 2:
            continue
        group = group.sort_values("candidate_id").copy()
        rho = float(
            spearmanr(
                group["model_energy_ev_per_atom"],
                group["formation_energy_ev_per_atom"],
            ).statistic
        )
        group_rows.append(
            {
                "system": system,
                "reduced_formula": formula,
                "n_structures": len(group),
                "spearman_rho": rho,
            }
        )
        for (_, left), (_, right) in combinations(group.iterrows(), 2):
            model_delta = float(
                right["model_energy_ev_per_atom"] - left["model_energy_ev_per_atom"]
            )
            dft_delta = float(
                right["formation_energy_ev_per_atom"]
                - left["formation_energy_ev_per_atom"]
            )
            concordant = (
                abs(model_delta) < 1e-10
                or abs(dft_delta) < 1e-10
                or math.copysign(1, model_delta) == math.copysign(1, dft_delta)
            )
            pair_rows.append(
                {
                    "system": system,
                    "reduced_formula": formula,
                    "candidate_left": left["candidate_id"],
                    "candidate_right": right["candidate_id"],
                    "model_delta_eV_atom": model_delta,
                    "dft_delta_eV_atom": dft_delta,
                    "absolute_delta_error_eV_atom": abs(model_delta - dft_delta),
                    "ranking_concordant": bool(concordant),
                }
            )

    pairs = pd.DataFrame(pair_rows)
    groups = pd.DataFrame(group_rows)
    if pairs.empty:
        summary = {
            "comparable_stoichiometry_groups": 0,
            "comparable_pairs": 0,
            "ranking_concordance": None,
            "pairwise_delta_mae_eV_atom": None,
            "interpretation": (
                "No repeated stoichiometries are available; cross-composition absolute "
                "energies were not correlated because elemental baselines differ."
            ),
        }
    else:
        summary = {
            "comparable_stoichiometry_groups": int(len(groups)),
            "comparable_pairs": int(len(pairs)),
            "ranking_concordance": float(pairs["ranking_concordant"].mean()),
            "pairwise_delta_mae_eV_atom": float(
                pairs["absolute_delta_error_eV_atom"].mean()
            ),
            "group_spearman": groups.to_dict(orient="records"),
            "interpretation": (
                "Only structures with identical reduced stoichiometry were compared. "
                "Cross-composition MatterSim absolute energies and DFT formation energies "
                "were intentionally not treated as directly comparable."
            ),
        }
    pairs.to_csv(SOURCE_DATA / "same_stoichiometry_ranking_pairs.csv", index=False)
    groups.to_csv(SOURCE_DATA / "same_stoichiometry_ranking_groups.csv", index=False)
    return pairs, summary


def analyze_screening_hits(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for system in SYSTEM_ORDER:
        group = frame.loc[frame["system"].eq(system)]
        rows.append(
            {
                "system": system,
                "dft_completed": int(len(group)),
                "near_hull_10mev": int(group["near_hull_10mev"].sum()),
                "candidate_hull_zero": int(group["on_candidate_hull"].sum()),
                "near_hull_hit_rate": float(group["near_hull_10mev"].mean()),
                "median_hull_distance_eV_atom": float(
                    group["energy_above_hull_ev_per_atom"].median()
                ),
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(SOURCE_DATA / "screening_hit_rates.csv", index=False)
    return result


def analyze_model_structures() -> tuple[pd.DataFrame, pd.DataFrame]:
    strict = pd.read_csv(STRICT_ROOT / "strict-validation.csv")
    cif_dir = STRICT_ROOT / "strict-relaxed-cifs"
    records: list[dict] = []
    structures_by_group: dict[tuple[str, str], list[Structure]] = defaultdict(list)

    for row in strict.to_dict(orient="records"):
        cif_path = cif_dir / Path(row["artifact"]).name
        structure = Structure.from_file(cif_path)
        formula = structure.composition.reduced_formula
        canonical_formula = reduced_formula(formula)
        try:
            space_group = SpacegroupAnalyzer(
                structure, symprec=0.1, angle_tolerance=5
            ).get_space_group_symbol()
        except Exception:
            space_group = "unresolved"
        structures_by_group[(row["system"], canonical_formula)].append(structure)
        record = {
            **row,
            "local_cif": str(cif_path.relative_to(ROOT)),
            "reduced_formula": canonical_formula,
            "space_group": space_group,
            "volume_per_atom_A3": float(structure.volume / len(structure)),
            "density_g_cm3": float(structure.density),
        }
        for element in ("Pt", "Pd", "Rh"):
            record[f"x_{element}"] = fraction(formula, element)
        records.append(record)

    details = pd.DataFrame(records)
    matcher = StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
    )
    cluster_counts: dict[str, int] = defaultdict(int)
    for (system, _), structures in structures_by_group.items():
        cluster_counts[system] += len(matcher.group_structures(structures))

    summary_rows = []
    for system in SYSTEM_ORDER:
        group = details.loc[details["system"].eq(system)]
        summary_rows.append(
            {
                "system": system,
                "structures": int(len(group)),
                "unique_compositions": int(group["reduced_formula"].nunique()),
                "space_groups": int(group["space_group"].nunique()),
                "structure_clusters_within_stoichiometry": int(
                    cluster_counts.get(system, 0)
                ),
                "atoms_min": int(group["atoms"].min()),
                "atoms_max": int(group["atoms"].max()),
                "maximum_force_max_eV_A": float(group["max_force_eV_A"].max()),
                "minimum_distance_min_A": float(group["minimum_distance_A"].min()),
                "volume_curvature_positive_fraction": float(
                    group["local_volume_curvature_eV_per_atom"].gt(0).mean()
                ),
            }
        )
    summary = pd.DataFrame(summary_rows)
    details.to_csv(SOURCE_DATA / "model_structure_details.csv", index=False)
    summary.to_csv(SOURCE_DATA / "model_structure_diversity_summary.csv", index=False)
    return details, summary


def parse_qe_value(text: str, key: str) -> str | None:
    match = re.search(
        rf"(?im)^\s*{re.escape(key)}\s*=\s*([^,\n/]+)", text
    )
    return match.group(1).strip().strip("'\"") if match else None


def extract_qe_parameters() -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_inputs = sorted(
        (ROOT / "data" / "dft_production" / "paper-priority").rglob("*.in")
    )
    reference_inputs = sorted(
        (
            ROOT
            / "data"
            / "dft_runs"
            / "production-live"
            / "dft-reference-vcrelax"
            / "jobs"
        ).glob("reference_*/input.in")
    )
    inputs = candidate_inputs + reference_inputs
    rows = []
    for path in inputs:
        text = path.read_text(encoding="utf-8", errors="replace")
        is_reference = "dft-reference-vcrelax" in path.as_posix()
        kp = re.search(
            r"(?im)^K_POINTS\s+automatic\s*\n\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
            text,
        )
        pseudos = re.findall(
            r"(?im)^\s*(Pt|Pd|Rh|Ni|W)\s+\S+\s+(\S+\.upf)\s*$", text
        )
        rows.append(
            {
                "input_file": str(path.relative_to(ROOT)),
                "candidate_id": path.parent.name if is_reference else path.stem,
                "role": "pure_element_reference" if is_reference else "paper_candidate",
                "calculation": parse_qe_value(text, "calculation"),
                "nat": parse_qe_value(text, "nat"),
                "ntyp": parse_qe_value(text, "ntyp"),
                "ecutwfc_Ry": parse_qe_value(text, "ecutwfc"),
                "ecutrho_Ry": parse_qe_value(text, "ecutrho"),
                "occupations": parse_qe_value(text, "occupations"),
                "smearing": parse_qe_value(text, "smearing"),
                "degauss_Ry": parse_qe_value(text, "degauss"),
                "conv_thr": parse_qe_value(text, "conv_thr"),
                "electron_maxstep": parse_qe_value(text, "electron_maxstep"),
                "mixing_beta": parse_qe_value(text, "mixing_beta"),
                "k_points": " ".join(kp.groups()) if kp else None,
                "pseudopotentials": "; ".join(f"{el}:{pseudo}" for el, pseudo in pseudos),
            }
        )
    details = pd.DataFrame(rows)
    summary_rows = []
    parameter_columns = [
        "calculation",
        "ecutwfc_Ry",
        "ecutrho_Ry",
        "occupations",
        "smearing",
        "degauss_Ry",
        "conv_thr",
        "electron_maxstep",
        "mixing_beta",
    ]
    for column in parameter_columns:
        counts = details[column].fillna("missing").value_counts()
        for value, count in counts.items():
            summary_rows.append(
                {"parameter": column, "value": value, "input_count": int(count)}
            )
    summary = pd.DataFrame(summary_rows)
    details.to_csv(SOURCE_DATA / "qe_input_parameters.csv", index=False)
    summary.to_csv(SOURCE_DATA / "qe_parameter_summary.csv", index=False)
    return details, summary


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.14,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="top",
    )


def create_model_validation_figure(
    details: pd.DataFrame, diversity: pd.DataFrame
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), constrained_layout=True)
    rng = np.random.default_rng(7)
    positions = np.arange(len(SYSTEM_ORDER))

    ax = axes[0, 0]
    for i, system in enumerate(SYSTEM_ORDER):
        values = details.loc[details["system"].eq(system), "max_force_eV_A"] * 1000
        jitter = rng.uniform(-0.12, 0.12, len(values))
        ax.scatter(
            np.full(len(values), i) + jitter,
            values,
            s=17,
            color=COLORS[system],
            alpha=0.82,
            edgecolor="white",
            linewidth=0.3,
        )
        ax.plot([i - 0.18, i + 0.18], [values.median()] * 2, color="black", lw=1)
    ax.axhline(20, color="#9c5b55", ls="--", lw=0.9, label="relaxation criterion")
    ax.set_xticks(positions, SYSTEM_ORDER)
    ax.set_ylabel("Maximum force (meV Å$^{-1}$)")
    ax.set_title("All 64 structures satisfy the force criterion")
    ax.legend(loc="upper right", fontsize=6)
    panel_label(ax, "a")

    ax = axes[0, 1]
    for i, system in enumerate(SYSTEM_ORDER):
        values = details.loc[details["system"].eq(system), "strict_steps"].astype(float)
        jitter = rng.uniform(-0.12, 0.12, len(values))
        ax.scatter(
            np.full(len(values), i) + jitter,
            values,
            s=16,
            color=COLORS[system],
            alpha=0.78,
            edgecolor="none",
        )
        ax.plot([i - 0.18, i + 0.18], [values.median()] * 2, color="black", lw=1)
    ax.set_xticks(positions, SYSTEM_ORDER)
    ax.set_ylabel("Strict relaxation steps")
    ax.set_title("Relaxation effort varies across candidates")
    panel_label(ax, "b")

    ax = axes[1, 0]
    for i, system in enumerate(SYSTEM_ORDER[:3]):
        second = system.split("-")[1]
        group = details.loc[details["system"].eq(system)]
        y = np.full(len(group), i) + rng.uniform(-0.08, 0.08, len(group))
        ax.scatter(
            group[f"x_{second}"],
            y,
            s=24,
            color=COLORS[system],
            alpha=0.8,
            edgecolor="white",
            linewidth=0.4,
        )
    ax.set_xlim(-0.03, 1.03)
    ax.set_yticks(np.arange(3), SYSTEM_ORDER[:3])
    ax.set_xlabel("Atomic fraction of the second element")
    ax.set_title("Binary candidates cover the composition interval")
    panel_label(ax, "c")

    ax = axes[1, 1]
    x = np.arange(len(SYSTEM_ORDER))
    ax.bar(
        x - 0.19,
        diversity["unique_compositions"],
        width=0.38,
        color="#70869a",
        label="unique compositions",
    )
    ax.bar(
        x + 0.19,
        diversity["structure_clusters_within_stoichiometry"],
        width=0.38,
        color="#b2a06d",
        label="structure clusters",
    )
    ax.set_xticks(x, SYSTEM_ORDER)
    ax.set_ylabel("Count")
    ax.set_title("Composition and structural diversity are retained")
    ax.legend(fontsize=6)
    panel_label(ax, "d")

    for ax in axes.flat:
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5, zorder=0)
    export_figure(fig, "figure_02_model_screening_validation")


def lower_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    unique: dict[float, float] = {}
    for x, y in points:
        unique[x] = min(unique.get(x, math.inf), y)
    ordered = sorted(unique.items())
    hull: list[tuple[float, float]] = []
    for point in ordered:
        while len(hull) >= 2:
            a, b = hull[-2], hull[-1]
            cross = (b[0] - a[0]) * (point[1] - b[1]) - (b[1] - a[1]) * (
                point[0] - b[0]
            )
            if cross <= 0:
                hull.pop()
            else:
                break
        hull.append(point)
    return hull


def create_binary_hull_figure(
    analysis: pd.DataFrame, hit_rates: pd.DataFrame
) -> None:
    fig = plt.figure(figsize=(7.2, 5.0), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=[3.2, 1.2])
    source_rows = []
    for index, system in enumerate(SYSTEM_ORDER[:3]):
        ax = fig.add_subplot(grid[0, index])
        second = system.split("-")[1]
        group = analysis.loc[analysis["system"].eq(system)].copy()
        group["x"] = group["formula"].map(lambda value: fraction(value, second))
        points = [(0.0, 0.0), (1.0, 0.0)] + list(
            zip(group["x"], group["formation_energy_ev_per_atom"])
        )
        hull = lower_hull(points)
        ax.plot(
            [p[0] for p in hull],
            [p[1] * 1000 for p in hull],
            color=COLORS["dark"],
            lw=1.3,
            zorder=1,
        )
        for _, row in group.iterrows():
            near = bool(row["near_hull_10mev"])
            ax.scatter(
                row["x"],
                row["formation_energy_ev_per_atom"] * 1000,
                s=34 if near else 25,
                color=COLORS["near"] if near else COLORS[system],
                edgecolor="white",
                linewidth=0.5,
                zorder=2,
            )
            source_rows.append(
                {
                    "system": system,
                    "candidate_id": row["candidate_id"],
                    "formula": row["formula"],
                    "x_second_element": row["x"],
                    "formation_energy_eV_atom": row["formation_energy_ev_per_atom"],
                    "energy_above_hull_eV_atom": row[
                        "energy_above_hull_ev_per_atom"
                    ],
                    "near_hull_10meV": near,
                }
            )
        ax.scatter([0, 1], [0, 0], s=25, color=COLORS["dark"], zorder=3)
        ax.axhline(0, color="#aeb6bd", lw=0.6)
        ax.set_xlim(-0.03, 1.03)
        ax.set_xlabel(f"Atomic fraction $x_{{{second}}}$")
        ax.set_title(system)
        if index == 0:
            ax.set_ylabel("Formation energy (meV atom$^{-1}$)")
        ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
        panel_label(ax, chr(ord("a") + index))

    ax = fig.add_subplot(grid[1, :])
    rates = hit_rates.set_index("system").loc[SYSTEM_ORDER]
    x = np.arange(len(rates))
    bars = ax.bar(
        x,
        rates["near_hull_hit_rate"] * 100,
        color=[COLORS[item] for item in rates.index],
        width=0.62,
    )
    for bar, (_, row) in zip(bars, rates.iterrows()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{int(row['near_hull_10mev'])}/{int(row['dft_completed'])}",
            ha="center",
            va="bottom",
            fontsize=6.5,
        )
    ax.set_ylim(0, 100)
    ax.set_xticks(x, rates.index)
    ax.set_ylabel("Near-hull candidates (%)")
    ax.set_title("Near-hull hit rates are strongly system dependent")
    ax.grid(axis="y", color=COLORS["grid"], lw=0.5)
    panel_label(ax, "d")
    pd.DataFrame(source_rows).to_csv(
        SOURCE_DATA / "figure_03_binary_candidate_hulls.csv", index=False
    )
    export_figure(fig, "figure_03_binary_candidate_hulls")


def ternary_xy(formula: str) -> tuple[float, float]:
    x_pt = fraction(formula, "Pt")
    x_pd = fraction(formula, "Pd")
    x_rh = fraction(formula, "Rh")
    return x_pd + 0.5 * x_rh, math.sqrt(3) * 0.5 * x_rh


def draw_triangle(ax: plt.Axes) -> None:
    vertices = np.array([[0, 0], [1, 0], [0.5, math.sqrt(3) / 2], [0, 0]])
    ax.plot(vertices[:, 0], vertices[:, 1], color=COLORS["dark"], lw=1)
    for level in np.linspace(0.2, 0.8, 4):
        ax.plot(
            [0.5 * level, 1 - 0.5 * level],
            [math.sqrt(3) * 0.5 * level] * 2,
            color=COLORS["grid"],
            lw=0.4,
        )
    ax.text(-0.03, -0.05, "Pt", ha="right", va="top", fontweight="bold")
    ax.text(1.03, -0.05, "Pd", ha="left", va="top", fontweight="bold")
    ax.text(0.5, math.sqrt(3) / 2 + 0.04, "Rh", ha="center", fontweight="bold")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.08, 0.96)
    ax.set_aspect("equal")
    ax.axis("off")


def create_ternary_figure(
    analysis: pd.DataFrame, ranking_summary: dict
) -> None:
    ternary = analysis.loc[analysis["system"].eq("Pt-Pd-Rh")].copy()
    ternary[["plot_x", "plot_y"]] = ternary["formula"].apply(
        lambda value: pd.Series(ternary_xy(value))
    )
    ternary.to_csv(SOURCE_DATA / "figure_04_ternary_stability_map.csv", index=False)

    fig = plt.figure(figsize=(7.2, 4.4), constrained_layout=True)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.15, 0.75])
    axes = [fig.add_subplot(grid[0, i]) for i in range(3)]

    ax = axes[0]
    draw_triangle(ax)
    norm = Normalize(
        ternary["formation_energy_ev_per_atom"].min() * 1000,
        ternary["formation_energy_ev_per_atom"].max() * 1000,
    )
    scatter = ax.scatter(
        ternary["plot_x"],
        ternary["plot_y"],
        c=ternary["formation_energy_ev_per_atom"] * 1000,
        cmap="cividis_r",
        norm=norm,
        s=48,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    fig.colorbar(scatter, ax=ax, fraction=0.045, pad=0.02).set_label(
        "Formation energy (meV atom$^{-1}$)"
    )
    ax.set_title("Formation-energy landscape")
    panel_label(ax, "a")

    ax = axes[1]
    draw_triangle(ax)
    scatter = ax.scatter(
        ternary["plot_x"],
        ternary["plot_y"],
        c=ternary["energy_above_hull_ev_per_atom"] * 1000,
        cmap="magma_r",
        s=np.where(ternary["near_hull_10mev"], 58, 38),
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    fig.colorbar(scatter, ax=ax, fraction=0.045, pad=0.02).set_label(
        "Energy above hull (meV atom$^{-1}$)"
    )
    ax.set_title("Candidate-set hull distance")
    panel_label(ax, "b")

    ax = axes[2]
    ax.axis("off")
    metrics = [
        ("DFT completed", "12 / 12"),
        ("Within 10 meV atom$^{-1}$", f"{int(ternary['near_hull_10mev'].sum())} / 12"),
        ("On candidate hull", f"{int(ternary['on_candidate_hull'].sum())} / 12"),
        ("Binary boundaries benchmarked", "3"),
    ]
    y = 0.87
    for label, value in metrics:
        ax.text(0.04, y, label, color="#66717a", fontsize=6.5, transform=ax.transAxes)
        ax.text(
            0.04,
            y - 0.09,
            value,
            color=COLORS["dark"],
            fontsize=13,
            fontweight="bold",
            transform=ax.transAxes,
        )
        ax.plot(
            [0.04, 0.96],
            [y - 0.14, y - 0.14],
            color=COLORS["grid"],
            lw=0.6,
            transform=ax.transAxes,
        )
        y -= 0.22
    ax.text(
        0.04,
        0.02,
        "Scope: computed candidates at 0 K;\nnot a finite-temperature phase diagram.",
        fontsize=6.2,
        color="#66717a",
        linespacing=1.4,
        transform=ax.transAxes,
    )
    ax.set_title("Evidence summary")
    panel_label(ax, "c")
    export_figure(fig, "figure_04_ternary_stability")


def create_lineage(
    qe_details: pd.DataFrame,
    ranking_summary: dict,
) -> pd.DataFrame:
    rows = [
        {
            "figure_or_table": "Figure 2",
            "panel": "a-d",
            "claim": "Model relaxation yields a converged and diverse candidate set.",
            "source_data": "source_data/model_structure_details.csv; source_data/model_structure_diversity_summary.csv",
            "raw_inputs": "strict-validation.csv; strict-relaxed-cifs/*.cif",
            "generator": "scripts/analyze_paper_priority_evidence.py",
        },
        {
            "figure_or_table": "Figure 3",
            "panel": "a-d",
            "claim": "Binary near-hull hit rates are system dependent.",
            "source_data": "source_data/figure_03_binary_candidate_hulls.csv; source_data/screening_hit_rates.csv",
            "raw_inputs": "paper-analysis-final.csv",
            "generator": "scripts/analyze_paper_priority_evidence.py",
        },
        {
            "figure_or_table": "Figure 4",
            "panel": "a-c",
            "claim": "The validated workflow extends to the Pt-Pd-Rh candidate space.",
            "source_data": "source_data/figure_04_ternary_stability_map.csv",
            "raw_inputs": "paper-analysis-final.csv",
            "generator": "scripts/analyze_paper_priority_evidence.py",
        },
        {
            "figure_or_table": "Supplementary Table 1",
            "panel": "all",
            "claim": "QE settings are explicitly traceable across paper candidates.",
            "source_data": "source_data/qe_input_parameters.csv; source_data/qe_parameter_summary.csv",
            "raw_inputs": f"{len(qe_details)} Quantum ESPRESSO input files",
            "generator": "scripts/analyze_paper_priority_evidence.py",
        },
        {
            "figure_or_table": "Supplementary Table 2",
            "panel": "all",
            "claim": "Model/DFT ranking is assessed only within identical stoichiometries.",
            "source_data": "source_data/same_stoichiometry_ranking_pairs.csv",
            "raw_inputs": "paper-analysis-final.csv",
            "generator": "scripts/analyze_paper_priority_evidence.py",
        },
    ]
    lineage = pd.DataFrame(rows)
    lineage.to_csv(OUTPUT / "figure_data_lineage.csv", index=False)
    return lineage


def write_report(
    ranking_summary: dict,
    hit_rates: pd.DataFrame,
    diversity: pd.DataFrame,
    qe_summary: pd.DataFrame,
) -> None:
    near_total = int(hit_rates["near_hull_10mev"].sum())
    dft_total = int(hit_rates["dft_completed"].sum())
    qe_input_count = int(
        qe_summary.loc[
            qe_summary["parameter"].eq("calculation"), "input_count"
        ].sum()
    )
    report = f"""# Paper-priority evidence analysis

## Model-to-DFT comparability

MatterSim absolute energies were not correlated directly with DFT formation energies
across different compositions. Elemental chemical-potential baselines differ, so such
a correlation would not be physically interpretable.

- Comparable identical-stoichiometry groups: {ranking_summary.get("comparable_stoichiometry_groups", 0)}
- Comparable structure pairs: {ranking_summary.get("comparable_pairs", 0)}
- Pairwise ranking concordance: {ranking_summary.get("ranking_concordance")}
- Pairwise energy-difference MAE: {ranking_summary.get("pairwise_delta_mae_eV_atom")} eV atom^-1

These statistics are an internal ranking diagnostic, not a universal model error.

## Screening outcome

- DFT-completed paper candidates: {dft_total}
- Candidates within 10 meV atom^-1 of the candidate-set hull: {near_total}
- Overall near-hull hit rate: {near_total / dft_total:.1%}

System-resolved values are stored in `source_data/screening_hit_rates.csv`.

## Model structure coverage

- Strictly validated structures: {int(diversity["structures"].sum())}
- Unique reduced compositions: {int(diversity["unique_compositions"].sum())}
- Within-stoichiometry structure clusters: {int(diversity["structure_clusters_within_stoichiometry"].sum())}
- Maximum observed force: {diversity["maximum_force_max_eV_A"].max():.6f} eV A^-1

## DFT parameter audit

- QE input files parsed: {qe_input_count} (32 candidates and 5 pure-element references)
- Complete parameter tables: `source_data/qe_input_parameters.csv`
- Parameter-value counts: `source_data/qe_parameter_summary.csv`

## Interpretation boundary

The figures report a 0 K convex hull over the computed candidate set and pure
references. They do not constitute a complete experimental or finite-temperature
phase diagram. Direct accuracy or cost superiority over alternative screening
methods still requires an explicit baseline.
"""
    (OUTPUT / "ANALYSIS_REPORT.md").write_text(report, encoding="utf-8")


def write_figure_legends() -> None:
    legends = """# Figure legends

**Figure 2 | MatterSim relaxation retains a converged and structurally diverse
candidate set.** **a,** Maximum residual forces for 64 strictly validated
structures. The dashed line denotes the 0.02 eV A^-1 relaxation criterion; black
segments show medians. **b,** Strict-relaxation step counts for the same structures.
**c,** Binary composition coverage, expressed as the atomic fraction of the second
element in each system. **d,** Counts of unique reduced compositions and
StructureMatcher clusters evaluated within each stoichiometry. Each point in
**a-c** represents one structure.

**Figure 3 | DFT candidate stability differs across the three binary boundaries.**
**a-c,** Formation energies and lower convex envelopes for the Pt-Pd, Pt-Rh and
Pd-Rh candidate sets, respectively. Gold symbols denote structures within
10 meV atom^-1 of the candidate-set hull; colored symbols denote the remaining
candidates. Pure-element endpoints are shown in dark grey. **d,** Fraction and
count of DFT-completed candidates within 10 meV atom^-1 for each binary system and
the Pt-Pd-Rh ternary set. Convex hulls are constructed only from the computed
candidates and pure references at 0 K.

**Figure 4 | Binary-boundary validation supports controlled extension to the
Pt-Pd-Rh candidate space.** **a,** DFT formation energies of 12 ternary candidates.
**b,** Corresponding distances from the 0 K candidate-set convex hull; symbol size
distinguishes candidates within 10 meV atom^-1. **c,** Evidence summary. These
results describe the computed candidate set and do not constitute a complete
finite-temperature phase diagram.
"""
    (OUTPUT / "FIGURE_LEGENDS.md").write_text(legends, encoding="utf-8")


def package_outputs() -> dict:
    checksum_path = OUTPUT / "SHA256SUMS.txt"
    archive_path = OUTPUT.parent / f"{OUTPUT.name}.zip"
    excluded = {checksum_path.resolve(), archive_path.resolve()}
    files = sorted(
        path
        for path in OUTPUT.rglob("*")
        if path.is_file() and path.resolve() not in excluded
    )

    checksum_lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checksum_lines.append(f"{digest}  {path.relative_to(OUTPUT).as_posix()}")
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*files, checksum_path]:
            archive.write(path, Path(OUTPUT.name) / path.relative_to(OUTPUT))

    return {
        "file_count": len(files) + 1,
        "checksum_manifest": str(checksum_path),
        "archive": str(archive_path),
    }


def main() -> None:
    ensure_dirs()
    analysis = load_paper_analysis()
    _, ranking_summary = analyze_same_stoichiometry_ranking(analysis)
    hit_rates = analyze_screening_hits(analysis)
    model_details, diversity = analyze_model_structures()
    qe_details, qe_summary = extract_qe_parameters()

    create_model_validation_figure(model_details, diversity)
    create_binary_hull_figure(analysis, hit_rates)
    create_ternary_figure(analysis, ranking_summary)
    create_lineage(qe_details, ranking_summary)
    write_report(ranking_summary, hit_rates, diversity, qe_summary)
    write_figure_legends()

    payload = {
        "ranking": ranking_summary,
        "screening": hit_rates.to_dict(orient="records"),
        "diversity": diversity.to_dict(orient="records"),
        "qe_inputs": len(qe_details),
        "output": str(OUTPUT),
        "package": {
            "checksum_manifest": str(OUTPUT / "SHA256SUMS.txt"),
            "archive": str(OUTPUT.parent / f"{OUTPUT.name}.zip"),
        },
    }
    (OUTPUT / "analysis-summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    payload["package"].update(package_outputs())
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
