import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ==========================================
# CHOOSE MODE
# ==========================================

# "single"  - one file, one pair of traces
# "compare" - two files, two pairs, side-by-side reflection
# "cross"   - compare any traces across any files
# "box"     - all traces of one file vs reference, organized in subfolders
# "full"    - just plot the full spectrum of a file

#MODE = "single"
#MODE = "compare"
MODE = "cross"
#MODE = "box"
#MODE = "full"

# ==========================================
# COMMON SETTINGS
# ==========================================

# Paths are relative to the location of this script
SCRIPT_DIR   = Path(__file__).resolve().parent

# CHANGE THIS to your data folder name
DATA_DIR     = SCRIPT_DIR / "data" / "reflection" / "RES_TEST"

# Results folder (auto-created)
RESULTS_BASE = SCRIPT_DIR / "results" / "reflection"


# ==========================================
# SINGLE MODE SETTINGS
# ==========================================

# CHANGE THIS to the file you want to analyze
FILE            = DATA_DIR / "YOUR_FILE_HERE.csv"

# CHANGE THESE to the traces you want
TRACE_SOURCE    = "A"
TRACE_REFLECTED = "E"

# Set to True if you also want to compare two extra traces
COMPARE_TRACES  = True
TRACE_COMPARE_1 = "D"
TRACE_COMPARE_2 = "E"


# ==========================================
# COMPARE MODE SETTINGS
# ==========================================

# CHANGE THESE: two files and their source/reflected traces
FILE_1            = DATA_DIR / "YOUR_FIRST_FILE.csv"
TRACE_SOURCE_1    = "A"
TRACE_REFLECTED_1 = "D"

FILE_2            = DATA_DIR / "YOUR_SECOND_FILE.csv"
TRACE_SOURCE_2    = "A"
TRACE_REFLECTED_2 = "E"


# ==========================================
# CROSS MODE SETTINGS
# ==========================================

# CHANGE THESE to your two file names (without .csv)
FILE_1     = "YOUR_FIRST_FILE_NAME"
FILE_2     = "YOUR_SECOND_FILE_NAME"

# CHANGE THIS to the fiber type label you want in the plot
FIBER_TYPE = "FIBER_TYPE_NAME"

# Auto-extract the box name from the first file name
BOX = Path(f"{FILE_1}.csv").stem.split("_")[0]

# CHANGE these (file, trace, label) entries to compare what you want
CROSS_TRACES = [
    (DATA_DIR / f"{FILE_1}.csv", "C", f"{FIBER_TYPE}_0.05 - in->out"),
    (DATA_DIR / f"{FILE_2}.csv", "B", f"{FIBER_TYPE}_0.05 - out->in"),
    (DATA_DIR / f"{FILE_1}.csv", "B", f"{FIBER_TYPE}_0.5 - in->out"),
    (DATA_DIR / f"{FILE_2}.csv", "C", f"{FIBER_TYPE}_0.5 - out->in"),
]


# ==========================================
# BOX MODE SETTINGS
# ==========================================

# CHANGE THIS to the file you want to analyze
BOX_FILE = DATA_DIR / "YOUR_BOX_FILE.csv"

# CHANGE THIS to the reference trace
BOX_REFERENCE_TRACE = "A"

# CHANGE these (trace_letter, custom_name) entries
BOX_TRACES = [
    ("D", "Fiber1-0.500"),
    ("E", "Fiber1-0.050"),
    ("F", "Fiber2-0.050"),
    ("G", "Fiber2-0.500"),
]


# ==========================================
# FULL MODE SETTINGS
# ==========================================

# CHANGE THIS to the file you want
FULL_FILE = DATA_DIR / "YOUR_FULL_FILE.csv"

# Remove the traces you don't want (leave [] to keep everything)
FULL_EXCLUDE = ["F", "G"]


# ==========================================
# PARSER
# ==========================================
def parse_osa_wide(filepath):
    traces = {}
    in_data = False
    col_map = {}

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if "[TRACE DATA]" in line:
                in_data = True
                continue
            if not in_data or not line:
                continue

            parts = [p.strip().strip('"') for p in line.split(",")]

            if not col_map and any("Tr" in p for p in parts):
                for i, p in enumerate(parts):
                    m = re.match(r"Tr\s+([A-G])\((WL|LEVEL)", p)
                    if m:
                        letter = m.group(1)
                        kind   = "wl" if m.group(2) == "WL" else "pwr"
                        col_map[i] = (letter, kind)
                        if letter not in traces:
                            traces[letter] = {"wl": [], "pwr": []}
                continue

            for i, (letter, kind) in col_map.items():
                try:
                    val = float(parts[i])
                    traces[letter][kind].append(val)
                except (ValueError, IndexError):
                    pass

    clean = {}
    for letter, data in traces.items():
        df = pd.DataFrame({"wl": data["wl"], "pwr": data["pwr"]})
        df = df[df["pwr"] > -200].dropna().reset_index(drop=True)
        if not df.empty:
            clean[letter] = df
    return clean


# Cache so we don't re-parse the same file
_file_cache = {}

def load_file(filepath):
    key = str(filepath)
    if key not in _file_cache:
        _file_cache[key] = parse_osa_wide(filepath)
    return _file_cache[key]


def calc_reflection(data, trace_src, trace_refl):
    src  = data[trace_src].sort_values("wl").reset_index(drop=True)
    refl = data[trace_refl].sort_values("wl").reset_index(drop=True)

    refl_interp    = np.interp(src['wl'], refl['wl'], refl['pwr'])
    reflection_dB  = refl_interp - src['pwr'].to_numpy()
    return_loss_dB = -reflection_dB

    return pd.DataFrame({
        'wavelength_nm':  src['wl'],
        'source_dBm':     src['pwr'],
        'reflected_dBm':  refl_interp,
        'reflection_dB':  reflection_dB,
        'return_loss_dB': return_loss_dB
    })


def print_summary(results, label, trace_src, trace_refl):
    print(f"\n{'='*60}")
    print(f"  SUMMARY -- {label}")
    print(f"{'='*60}")
    print(f"  Source: Tr {trace_src}  |  Reflected: Tr {trace_refl}")
    print(f"  Min reflection : {results['reflection_dB'].min():.3f} dB  "
          f"@ {results.loc[results['reflection_dB'].idxmin(), 'wavelength_nm']:.2f} nm")
    print(f"  Max reflection : {results['reflection_dB'].max():.3f} dB  "
          f"@ {results.loc[results['reflection_dB'].idxmax(), 'wavelength_nm']:.2f} nm")
    print(f"  Mean reflection: {results['reflection_dB'].mean():.3f} dB")
    print(f"  Min RL : {results['return_loss_dB'].min():.3f} dB")
    print(f"  Max RL : {results['return_loss_dB'].max():.3f} dB")
    print(f"  Mean RL: {results['return_loss_dB'].mean():.3f} dB")
    print(f"{'='*60}")


# ==========================================
# SINGLE MODE
# ==========================================
def run_single():
    date_tag = FILE.stem.split("_")[-1]
    file_tag = FILE.stem.split("_")[0]
    res_tag  = DATA_DIR.name

    OUTPUT_DIR = RESULTS_BASE / date_tag / res_tag
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    SAVE_CSV   = OUTPUT_DIR / f"reflection_analysis_{file_tag}_{date_tag}.csv"
    SAVE_PLOT1 = OUTPUT_DIR / f"full_spectrum_{file_tag}_{date_tag}.png"
    SAVE_PLOT2 = OUTPUT_DIR / f"source_vs_reflected_{file_tag}_{date_tag}.png"

    print(f"\n{'='*60}")
    print(f"  SINGLE MODE")
    print(f"  File:       {FILE.name}")
    print(f"  Source:     Trace {TRACE_SOURCE}")
    print(f"  Reflected:  Trace {TRACE_REFLECTED}")
    if COMPARE_TRACES:
        print(f"  Compare:    Trace {TRACE_COMPARE_1} vs Trace {TRACE_COMPARE_2}")
    print(f"{'='*60}")

    data = load_file(FILE)

    print(f"\nFound traces: {', '.join(sorted(data.keys()))}")
    for name, df in sorted(data.items()):
        print(f"  Trace {name}: {len(df)} pts | "
              f"{df['wl'].min():.2f}-{df['wl'].max():.2f} nm")

    if TRACE_SOURCE not in data:
        raise KeyError(f"Trace {TRACE_SOURCE} not found.")
    if TRACE_REFLECTED not in data:
        raise KeyError(f"Trace {TRACE_REFLECTED} not found.")

    results = calc_reflection(data, TRACE_SOURCE, TRACE_REFLECTED)
    results.to_csv(SAVE_CSV, index=False)
    print(f"\nSaved: {SAVE_CSV}")

    # Figure 1: Full Spectrum
    fig1, ax1 = plt.subplots(figsize=(11, 6))
    colors = ['C0','C1','C2','C3','C4','C5','C6']
    for i, (name, df) in enumerate(sorted(data.items())):
        ax1.plot(df['wl'], df['pwr'],
                 label=f"Trace {name}",
                 color=colors[i % len(colors)],
                 linewidth=1.2)
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Power (dBm)")
    ax1.set_title(f"Full Spectrum -- {FILE.stem}")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    fig1.savefig(SAVE_PLOT1, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT1}")

    # Figure 2: Source vs Reflected + Reflection
    src  = data[TRACE_SOURCE].sort_values("wl").reset_index(drop=True)
    refl = data[TRACE_REFLECTED].sort_values("wl").reset_index(drop=True)

    fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    ax2a.plot(src['wl'], src['pwr'],
              label=f"Source -- Tr {TRACE_SOURCE}",
              color='C0', linewidth=1.5)
    ax2a.plot(refl['wl'], refl['pwr'],
              label=f"Reflected -- Tr {TRACE_REFLECTED}",
              color='C1', linewidth=1.5)
    ax2a.set_ylabel("Power (dBm)")
    ax2a.set_title("Source vs Reflected Power")
    ax2a.legend(loc="upper right", fontsize=9)
    ax2a.grid(True, alpha=0.3)

    ax2b.plot(results['wavelength_nm'], results['reflection_dB'],
              color='red', linewidth=1.5, label="Reflection (dB)")
    ax2b.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax2b.set_ylabel("Reflection (dB)")
    ax2b.set_xlabel("Wavelength (nm)")
    ax2b.set_title(f"Reflection = Tr {TRACE_REFLECTED} - Tr {TRACE_SOURCE}")
    ax2b.legend(loc="upper right", fontsize=9)
    ax2b.grid(True, alpha=0.3)

    fig2.suptitle(f"Reflection Analysis -- {FILE.stem}",
                  fontsize=13, fontweight='bold')
    fig2.tight_layout()
    fig2.savefig(SAVE_PLOT2, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT2}")

    # Figure 3 (optional): Compare two traces
    if COMPARE_TRACES:
        if TRACE_COMPARE_1 not in data:
            raise KeyError(f"Trace {TRACE_COMPARE_1} not found.")
        if TRACE_COMPARE_2 not in data:
            raise KeyError(f"Trace {TRACE_COMPARE_2} not found.")

        SAVE_PLOT3 = OUTPUT_DIR / f"comparison_{file_tag}_{date_tag}.png"

        tr1 = data[TRACE_COMPARE_1].sort_values("wl").reset_index(drop=True)
        tr2 = data[TRACE_COMPARE_2].sort_values("wl").reset_index(drop=True)

        fig3, (ax3a, ax3b, ax3c) = plt.subplots(3, 1, figsize=(11, 12), sharex=True)

        ax3a.plot(tr1['wl'], tr1['pwr'],
                  label=f"Trace {TRACE_COMPARE_1}",
                  color='C0', linewidth=1.5)
        ax3a.plot(tr2['wl'], tr2['pwr'],
                  label=f"Trace {TRACE_COMPARE_2}",
                  color='C3', linewidth=1.5)
        ax3a.set_ylabel("Power (dBm)")
        ax3a.set_title(f"Comparison -- Tr {TRACE_COMPARE_1} vs Tr {TRACE_COMPARE_2}")
        ax3a.legend(loc="upper right", fontsize=9)
        ax3a.grid(True, alpha=0.3)

        ax3b.plot(tr1['wl'], tr1['pwr'], color='C0', linewidth=1.5)
        ax3b.set_ylabel("Power (dBm)")
        ax3b.set_title(f"Trace {TRACE_COMPARE_1} -- Isolated")
        ax3b.grid(True, alpha=0.3)

        ax3c.plot(tr2['wl'], tr2['pwr'], color='C3', linewidth=1.5)
        ax3c.set_ylabel("Power (dBm)")
        ax3c.set_xlabel("Wavelength (nm)")
        ax3c.set_title(f"Trace {TRACE_COMPARE_2} -- Isolated")
        ax3c.grid(True, alpha=0.3)

        fig3.suptitle(f"Trace Comparison -- {FILE.stem}",
                      fontsize=13, fontweight='bold')
        fig3.tight_layout()
        fig3.savefig(SAVE_PLOT3, dpi=200, bbox_inches='tight')
        print(f"Saved: {SAVE_PLOT3}")

    plt.show()
    print_summary(results, FILE.stem, TRACE_SOURCE, TRACE_REFLECTED)


# ==========================================
# COMPARE MODE
# ==========================================
def run_compare():
    date_tag_1 = FILE_1.stem.split("_")[-1]
    file_tag_1 = FILE_1.stem.split("_")[0]
    date_tag_2 = FILE_2.stem.split("_")[-1]
    file_tag_2 = FILE_2.stem.split("_")[0]
    res_tag    = DATA_DIR.name

    OUTPUT_DIR = RESULTS_BASE / "comparison" / res_tag
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    SAVE_CSV_1 = OUTPUT_DIR / f"reflection_{file_tag_1}_{date_tag_1}.csv"
    SAVE_CSV_2 = OUTPUT_DIR / f"reflection_{file_tag_2}_{date_tag_2}.csv"
    SAVE_PLOT1 = OUTPUT_DIR / f"full_spectrum_{file_tag_1}_{date_tag_1}.png"
    SAVE_PLOT2 = OUTPUT_DIR / f"full_spectrum_{file_tag_2}_{date_tag_2}.png"
    SAVE_PLOT3 = OUTPUT_DIR / f"comparison_{file_tag_1}_vs_{file_tag_2}_{date_tag_1}.png"

    print(f"\n{'='*60}")
    print(f"  COMPARE MODE")
    print(f"  File 1: {FILE_1.name}  (Src: Tr {TRACE_SOURCE_1}, Refl: Tr {TRACE_REFLECTED_1})")
    print(f"  File 2: {FILE_2.name}  (Src: Tr {TRACE_SOURCE_2}, Refl: Tr {TRACE_REFLECTED_2})")
    print(f"{'='*60}")

    data_1 = load_file(FILE_1)
    data_2 = load_file(FILE_2)

    print(f"\n{FILE_1.name} traces: {', '.join(sorted(data_1.keys()))}")
    print(f"{FILE_2.name} traces: {', '.join(sorted(data_2.keys()))}")

    if TRACE_SOURCE_1 not in data_1:
        raise KeyError(f"Trace {TRACE_SOURCE_1} not found in {FILE_1.name}")
    if TRACE_REFLECTED_1 not in data_1:
        raise KeyError(f"Trace {TRACE_REFLECTED_1} not found in {FILE_1.name}")
    if TRACE_SOURCE_2 not in data_2:
        raise KeyError(f"Trace {TRACE_SOURCE_2} not found in {FILE_2.name}")
    if TRACE_REFLECTED_2 not in data_2:
        raise KeyError(f"Trace {TRACE_REFLECTED_2} not found in {FILE_2.name}")

    results_1 = calc_reflection(data_1, TRACE_SOURCE_1, TRACE_REFLECTED_1)
    results_2 = calc_reflection(data_2, TRACE_SOURCE_2, TRACE_REFLECTED_2)

    results_1.to_csv(SAVE_CSV_1, index=False)
    results_2.to_csv(SAVE_CSV_2, index=False)
    print(f"\nSaved: {SAVE_CSV_1}")
    print(f"Saved: {SAVE_CSV_2}")

    colors = ['C0','C1','C2','C3','C4','C5','C6']

    fig1, ax1 = plt.subplots(figsize=(11, 6))
    for i, (name, df) in enumerate(sorted(data_1.items())):
        ax1.plot(df['wl'], df['pwr'],
                 label=f"Trace {name}",
                 color=colors[i % len(colors)],
                 linewidth=1.2)
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("Power (dBm)")
    ax1.set_title(f"Full Spectrum -- {FILE_1.stem}")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    fig1.savefig(SAVE_PLOT1, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT1}")

    fig2, ax2 = plt.subplots(figsize=(11, 6))
    for i, (name, df) in enumerate(sorted(data_2.items())):
        ax2.plot(df['wl'], df['pwr'],
                 label=f"Trace {name}",
                 color=colors[i % len(colors)],
                 linewidth=1.2)
    ax2.set_xlabel("Wavelength (nm)")
    ax2.set_ylabel("Power (dBm)")
    ax2.set_title(f"Full Spectrum -- {FILE_2.stem}")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(SAVE_PLOT2, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT2}")

    src_1  = data_1[TRACE_SOURCE_1].sort_values("wl").reset_index(drop=True)
    refl_1 = data_1[TRACE_REFLECTED_1].sort_values("wl").reset_index(drop=True)
    src_2  = data_2[TRACE_SOURCE_2].sort_values("wl").reset_index(drop=True)
    refl_2 = data_2[TRACE_REFLECTED_2].sort_values("wl").reset_index(drop=True)

    fig3, axes = plt.subplots(3, 2, figsize=(16, 14), sharex=True)

    axes[0, 0].plot(src_1['wl'], src_1['pwr'],
                    label=f"Source -- Tr {TRACE_SOURCE_1}",
                    color='C0', linewidth=1.5)
    axes[0, 0].plot(refl_1['wl'], refl_1['pwr'],
                    label=f"Reflected -- Tr {TRACE_REFLECTED_1}",
                    color='C3', linewidth=1.5)
    axes[0, 0].set_ylabel("Power (dBm)")
    axes[0, 0].set_title(f"{FILE_1.stem}\nSrc (Tr {TRACE_SOURCE_1}) vs Refl (Tr {TRACE_REFLECTED_1})")
    axes[0, 0].legend(loc="upper right", fontsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(src_2['wl'], src_2['pwr'],
                    label=f"Source -- Tr {TRACE_SOURCE_2}",
                    color='C0', linewidth=1.5)
    axes[0, 1].plot(refl_2['wl'], refl_2['pwr'],
                    label=f"Reflected -- Tr {TRACE_REFLECTED_2}",
                    color='C3', linewidth=1.5)
    axes[0, 1].set_ylabel("Power (dBm)")
    axes[0, 1].set_title(f"{FILE_2.stem}\nSrc (Tr {TRACE_SOURCE_2}) vs Refl (Tr {TRACE_REFLECTED_2})")
    axes[0, 1].legend(loc="upper right", fontsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(src_1['wl'], src_1['pwr'], color='C0', linewidth=1.5)
    axes[1, 0].set_ylabel("Power (dBm)")
    axes[1, 0].set_title(f"{file_tag_1} -- Source (Tr {TRACE_SOURCE_1})")
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(src_2['wl'], src_2['pwr'], color='C0', linewidth=1.5)
    axes[1, 1].set_ylabel("Power (dBm)")
    axes[1, 1].set_title(f"{file_tag_2} -- Source (Tr {TRACE_SOURCE_2})")
    axes[1, 1].grid(True, alpha=0.3)

    axes[2, 0].plot(refl_1['wl'], refl_1['pwr'], color='C3', linewidth=1.5)
    axes[2, 0].set_ylabel("Power (dBm)")
    axes[2, 0].set_xlabel("Wavelength (nm)")
    axes[2, 0].set_title(f"{file_tag_1} -- Reflected (Tr {TRACE_REFLECTED_1})")
    axes[2, 0].grid(True, alpha=0.3)

    axes[2, 1].plot(refl_2['wl'], refl_2['pwr'], color='C3', linewidth=1.5)
    axes[2, 1].set_ylabel("Power (dBm)")
    axes[2, 1].set_xlabel("Wavelength (nm)")
    axes[2, 1].set_title(f"{file_tag_2} -- Reflected (Tr {TRACE_REFLECTED_2})")
    axes[2, 1].grid(True, alpha=0.3)

    fig3.suptitle(f"Comparison: {FILE_1.stem}  vs  {FILE_2.stem}",
                  fontsize=14, fontweight='bold')
    fig3.tight_layout()
    fig3.savefig(SAVE_PLOT3, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT3}")

    plt.show()

    print_summary(results_1, FILE_1.stem, TRACE_SOURCE_1, TRACE_REFLECTED_1)
    print_summary(results_2, FILE_2.stem, TRACE_SOURCE_2, TRACE_REFLECTED_2)


# ==========================================
# CROSS MODE
# ==========================================
def run_cross():
    res_tag = DATA_DIR.name

    OUTPUT_DIR = RESULTS_BASE / "cross" / res_tag
    (OUTPUT_DIR / BOX).mkdir(parents=True, exist_ok=True)

    n_traces = len(CROSS_TRACES)

    print(f"\n{'='*60}")
    print(f"  CROSS-FILE MODE -- {n_traces} traces")
    print(f"{'='*60}")
    for i, (fp, tr, lbl) in enumerate(CROSS_TRACES):
        print(f"  [{i+1}] {lbl}  ({fp.name}, Tr {tr})")
    print(f"{'='*60}")

    loaded_traces = []
    for fp, tr, lbl in CROSS_TRACES:
        data = load_file(fp)
        if tr not in data:
            raise KeyError(f"Trace {tr} not found in {fp.name}")
        df = data[tr].sort_values("wl").reset_index(drop=True)
        loaded_traces.append((df, lbl))
        print(f"  Loaded: {lbl} -- {len(df)} pts | "
              f"{df['wl'].min():.2f}-{df['wl'].max():.2f} nm")

    in_out_traces = [(df, lbl) for df, lbl in loaded_traces if "in->out" in lbl]
    out_in_traces = [(df, lbl) for df, lbl in loaded_traces if "out->in" in lbl]

    SAVE_PLOT_IN_OUT   = OUTPUT_DIR / BOX / f"cross_overlay_in_out_{FIBER_TYPE}.png"
    SAVE_PLOT_OUT_IN   = OUTPUT_DIR / BOX / f"cross_overlay_out_in_{FIBER_TYPE}.png"
    SAVE_PLOT_ISOLATED = OUTPUT_DIR / BOX / f"cross_isolated_{FIBER_TYPE}.png"

    cross_colors = ['C0', 'C3', 'C2', 'C1', 'C4', 'C5', 'C6', 'C7']

    if in_out_traces:
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        for i, (df, lbl) in enumerate(in_out_traces):
            ax1.plot(df['wl'], df['pwr'],
                     label=lbl,
                     color=cross_colors[i % len(cross_colors)],
                     linewidth=1.5)
        ax1.set_xlabel("Wavelength (nm)")
        ax1.set_ylabel("Power (dBm)")
        ax1.set_title(f"Cross-File Comparison -- in->out ({FIBER_TYPE})")
        ax1.legend(loc="upper right", fontsize=9)
        ax1.grid(True, alpha=0.3)
        fig1.tight_layout()
        fig1.savefig(SAVE_PLOT_IN_OUT, dpi=200, bbox_inches='tight')
        print(f"\nSaved: {SAVE_PLOT_IN_OUT}")

    if out_in_traces:
        fig2, ax2 = plt.subplots(figsize=(12, 6))
        for i, (df, lbl) in enumerate(out_in_traces):
            ax2.plot(df['wl'], df['pwr'],
                     label=lbl,
                     color=cross_colors[i % len(cross_colors)],
                     linewidth=1.5)
        ax2.set_xlabel("Wavelength (nm)")
        ax2.set_ylabel("Power (dBm)")
        ax2.set_title(f"Cross-File Comparison -- out->in ({FIBER_TYPE})")
        ax2.legend(loc="upper right", fontsize=9)
        ax2.grid(True, alpha=0.3)
        fig2.tight_layout()
        fig2.savefig(SAVE_PLOT_OUT_IN, dpi=200, bbox_inches='tight')
        print(f"Saved: {SAVE_PLOT_OUT_IN}")

    fig3, axes = plt.subplots(n_traces, 1,
                              figsize=(12, 4 * n_traces),
                              sharex=True)

    if n_traces == 1:
        axes = [axes]

    for i, (df, lbl) in enumerate(loaded_traces):
        axes[i].plot(df['wl'], df['pwr'],
                     color=cross_colors[i % len(cross_colors)],
                     linewidth=1.5)
        axes[i].set_ylabel("Power (dBm)")
        axes[i].set_title(lbl)
        axes[i].grid(True, alpha=0.3)

    axes[-1].set_xlabel("Wavelength (nm)")
    fig3.tight_layout()
    fig3.savefig(SAVE_PLOT_ISOLATED, dpi=200, bbox_inches='tight')
    print(f"Saved: {SAVE_PLOT_ISOLATED}")

    plt.show()

    print(f"\n{'='*60}")
    print(f"  CROSS-FILE SUMMARY")
    print(f"{'='*60}")
    for i, (df, lbl) in enumerate(loaded_traces):
        print(f"\n  [{i+1}] {lbl}")
        print(f"      Points:    {len(df)}")
        print(f"      WL range:  {df['wl'].min():.2f} - {df['wl'].max():.2f} nm")
        print(f"      Min power: {df['pwr'].min():.3f} dBm "
              f"@ {df.loc[df['pwr'].idxmin(), 'wl']:.2f} nm")
        print(f"      Max power: {df['pwr'].max():.3f} dBm "
              f"@ {df.loc[df['pwr'].idxmax(), 'wl']:.2f} nm")
    print(f"{'='*60}")


# ==========================================
# BOX MODE
# ==========================================
def run_box():
    file_tag = BOX_FILE.stem
    res_tag  = DATA_DIR.name

    OUTPUT_BASE = RESULTS_BASE / "box" / res_tag / file_tag
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  BOX MODE")
    print(f"  File:       {BOX_FILE.name}")
    print(f"  Reference:  Trace {BOX_REFERENCE_TRACE}")
    print(f"  Traces:     {[t for t,_ in BOX_TRACES]}")
    print(f"{'='*60}")

    data = load_file(BOX_FILE)

    if BOX_REFERENCE_TRACE not in data:
        raise KeyError(f"Reference trace {BOX_REFERENCE_TRACE} not found")

    src = data[BOX_REFERENCE_TRACE].sort_values("wl").reset_index(drop=True)

    for trace_letter, trace_name in BOX_TRACES:
        if trace_letter not in data:
            print(f"Skipping {trace_name}: Trace {trace_letter} not found")
            continue

        subfolder = OUTPUT_BASE / trace_name
        subfolder.mkdir(parents=True, exist_ok=True)

        results = calc_reflection(data, BOX_REFERENCE_TRACE, trace_letter)

        save_csv  = subfolder / f"{trace_name}_reflection.csv"
        save_plot = subfolder / f"{trace_name}_reflection.png"

        results.to_csv(save_csv, index=False)

        refl = data[trace_letter].sort_values("wl").reset_index(drop=True)

        fig, (axa, axb) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

        axa.plot(src['wl'], src['pwr'],
                 label=f"Reference (Tr {BOX_REFERENCE_TRACE})",
                 color='C0', linewidth=1.5)
        axa.plot(refl['wl'], refl['pwr'],
                 label=f"{trace_name} (Tr {trace_letter})",
                 color='C3', linewidth=1.5)
        axa.set_ylabel("Power (dBm)")
        axa.set_title(f"Reference vs {trace_name}")
        axa.legend(loc="upper right", fontsize=9)
        axa.grid(True, alpha=0.3)

        axb.plot(results['wavelength_nm'], results['reflection_dB'],
                 color='red', linewidth=1.5, label="Reflection (dB)")
        axb.axhline(0, color='black', linewidth=0.8, linestyle='--')
        axb.set_xlabel("Wavelength (nm)")
        axb.set_ylabel("Reflection (dB)")
        axb.set_title(f"Reflection = Tr {trace_letter} - Tr {BOX_REFERENCE_TRACE}")
        axb.legend(loc="upper right", fontsize=9)
        axb.grid(True, alpha=0.3)

        fig.suptitle(f"{file_tag} -- {trace_name}",
                     fontsize=13, fontweight='bold')
        fig.tight_layout()
        fig.savefig(save_plot, dpi=200, bbox_inches='tight')
        plt.close(fig)

        print_summary(results, trace_name, BOX_REFERENCE_TRACE, trace_letter)
        print(f"  Saved: {save_csv}")
        print(f"  Saved: {save_plot}")


# ==========================================
# FULL MODE
# ==========================================
def run_full():
    file_tag = FULL_FILE.stem
    res_tag  = DATA_DIR.name

    OUTPUT_DIR = RESULTS_BASE / "full" / res_tag
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  FULL MODE")
    print(f"  File: {FULL_FILE.name}")
    if FULL_EXCLUDE:
        print(f"  Exclude: {FULL_EXCLUDE}")
    print(f"{'='*60}")

    data = load_file(FULL_FILE)

    selected = {k: v for k, v in data.items() if k not in FULL_EXCLUDE}

    if not selected:
        raise ValueError("No traces left after applying exclude filter.")

    print(f"\nPlotting traces: {', '.join(sorted(selected.keys()))}")
    for name, df in sorted(selected.items()):
        print(f"  Trace {name}: {len(df)} pts | "
              f"{df['wl'].min():.2f}-{df['wl'].max():.2f} nm | "
              f"Power: {df['pwr'].min():.2f} to {df['pwr'].max():.2f} dBm")

    SAVE_PLOT = OUTPUT_DIR / f"full_spectrum_{file_tag}.png"

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = ['C0','C1','C2','C3','C4','C5','C6']
    for i, (name, df) in enumerate(sorted(selected.items())):
        ax.plot(df['wl'], df['pwr'],
                label=f"Trace {name}",
                color=colors[i % len(colors)],
                linewidth=1.2)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Power (dBm)")
    ax.set_title(f"Full Spectrum -- {file_tag}")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(SAVE_PLOT, dpi=200, bbox_inches='tight')
    print(f"\nSaved: {SAVE_PLOT}")

    plt.show()


# ==========================================
# RUN
# ==========================================
if MODE == "single":
    run_single()
elif MODE == "compare":
    run_compare()
elif MODE == "cross":
    run_cross()
elif MODE == "box":
    run_box()
elif MODE == "full":
    run_full()
else:
    raise ValueError(f"Unknown MODE: '{MODE}'. Use 'single', 'compare', 'cross', 'box', or 'full'.")