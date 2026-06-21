import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ==========================================
# SETTINGS
# ==========================================

# CHANGE THIS to select the box you want to analyze
BOX = "Box2"

# CHANGE THESE to select the traces you want to compare
TRACE_SOURCE      = "A"   # reference / input
TRACE_TRANSMITTED = "B"   # fiber grating to analyze


# ==========================================
# DIRECTORIES
# ==========================================

# Paths are relative to the location of this script
SCRIPT_DIR = Path(__file__).resolve().parent

# CHANGE THIS to your data folder name
DATA_DIR   = SCRIPT_DIR / "data" / "transmission"

# Results folder (auto-created)
OUTPUT_DIR = SCRIPT_DIR / "results" / "transmission"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# AUTO-FIND FILE FOR SELECTED BOX
# ==========================================

matches = list(DATA_DIR.glob(f"{BOX}_*.csv"))
if not matches:
    raise FileNotFoundError(f"No CSV file found for {BOX} in {DATA_DIR}")
if len(matches) > 1:
    print(f"Multiple files found for {BOX}:")
    for i, f in enumerate(matches):
        print(f"  [{i}] {f.name}")
    choice = int(input("Choose file number: "))
    FILE = matches[choice]
else:
    FILE = matches[0]

# Auto-name output files
parts    = FILE.stem.split("_")
box_tag  = parts[0]
date_tag = parts[-1]

SAVE_CSV  = OUTPUT_DIR / f"transmission_{box_tag}_{date_tag}.csv"
SAVE_PLOT = OUTPUT_DIR / f"transmission_{box_tag}_{date_tag}.png"

print(f"\n{'='*60}")
print(f"  Box:         {BOX}")
print(f"  File:        {FILE.name}")
print(f"  Source:      Trace {TRACE_SOURCE}")
print(f"  Transmitted: Trace {TRACE_TRANSMITTED}")
print(f"{'='*60}")


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


# ==========================================
# LOAD
# ==========================================
print(f"\nReading: {FILE.name}")
data = parse_osa_wide(FILE)

print(f"\nFound traces: {', '.join(sorted(data.keys()))}")
for name, df in sorted(data.items()):
    print(
        f"  Trace {name}: {len(df)} pts | "
        f"{df['wl'].min():.2f}-{df['wl'].max():.2f} nm | "
        f"Power: {df['pwr'].min():.2f} to {df['pwr'].max():.2f} dBm"
    )

if TRACE_SOURCE not in data:
    raise KeyError(f"Trace {TRACE_SOURCE} not found. Available: {list(data.keys())}")
if TRACE_TRANSMITTED not in data:
    raise KeyError(f"Trace {TRACE_TRANSMITTED} not found. Available: {list(data.keys())}")


# ==========================================
# CALCULATE
# ==========================================
src  = data[TRACE_SOURCE]
trns = data[TRACE_TRANSMITTED]

trns_interp       = np.interp(src['wl'], trns['wl'], trns['pwr'])
transmission_dB   = trns_interp - src['pwr'].to_numpy()
insertion_loss_dB = -transmission_dB

results = pd.DataFrame({
    'wavelength_nm':     src['wl'],
    'source_dBm':        src['pwr'],
    'transmitted_dBm':   trns_interp,
    'transmission_dB':   transmission_dB,
    'insertion_loss_dB': insertion_loss_dB
})
results.to_csv(SAVE_CSV, index=False)
print(f"\nSaved: {SAVE_CSV}")


# ==========================================
# PLOT
# ==========================================
fig, axes = plt.subplots(3, 1, figsize=(11, 12), sharex=True)

# Panel 1: Full Spectrum
colors = ['C0','C1','C2','C3','C4','C5','C6']
for i, (name, df) in enumerate(sorted(data.items())):
    axes[0].plot(df['wl'], df['pwr'],
                 label=f"Trace {name}",
                 color=colors[i % len(colors)],
                 linewidth=1.2)
axes[0].set_ylabel("Power (dBm)")
axes[0].set_title(f"Full Spectrum - All Traces ({box_tag})")
axes[0].legend(loc="upper right", fontsize=8)
axes[0].grid(True, alpha=0.3)

# Panel 2: Source vs Transmitted
axes[1].plot(src['wl'], src['pwr'],
             label=f"Source - Trace {TRACE_SOURCE}",
             color='C0', linewidth=1.5)
axes[1].plot(trns['wl'], trns['pwr'],
             label=f"Transmitted - Trace {TRACE_TRANSMITTED}",
             color='C2', linewidth=1.5)
axes[1].set_ylabel("Power (dBm)")
axes[1].set_title("Source vs Transmitted Power")
axes[1].legend(loc="upper right", fontsize=9)
axes[1].grid(True, alpha=0.3)

# Panel 3: Transmission + Insertion Loss
axes[2].plot(results['wavelength_nm'], results['transmission_dB'],
             color='blue', linewidth=1.5, label="Transmission (dB)")
axes[2].plot(results['wavelength_nm'], results['insertion_loss_dB'],
             color='orange', linewidth=1.5, linestyle='--',
             label="Insertion Loss (dB)")
axes[2].axhline(0, color='black', linewidth=0.8, linestyle='--')
axes[2].set_ylabel("dB")
axes[2].set_xlabel("Wavelength (nm)")
axes[2].set_title(
    f"Transmission = Trace {TRACE_TRANSMITTED} - Trace {TRACE_SOURCE}"
)
axes[2].legend(loc="upper right", fontsize=9)
axes[2].grid(True, alpha=0.3)

plt.suptitle(f"Transmission Analysis - {box_tag} ({date_tag})",
             fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(SAVE_PLOT, dpi=200, bbox_inches='tight')
plt.show()
print(f"Saved: {SAVE_PLOT}")


# ==========================================
# SUMMARY
# ==========================================
print(f"\n{'='*60}")
print(f"  TRANSMISSION SUMMARY - {box_tag}")
print(f"{'='*60}")
print(f"  Source trace:      {TRACE_SOURCE}")
print(f"  Transmitted trace: {TRACE_TRANSMITTED}")
print(f"  Min transmission : {results['transmission_dB'].min():.3f} dB  "
      f"@ {results.loc[results['transmission_dB'].idxmin(), 'wavelength_nm']:.2f} nm")
print(f"  Max transmission : {results['transmission_dB'].max():.3f} dB  "
      f"@ {results.loc[results['transmission_dB'].idxmax(), 'wavelength_nm']:.2f} nm")
print(f"  Mean transmission: {results['transmission_dB'].mean():.3f} dB")
print(f"\n  Min IL : {results['insertion_loss_dB'].min():.3f} dB")
print(f"  Max IL : {results['insertion_loss_dB'].max():.3f} dB")
print(f"  Mean IL: {results['insertion_loss_dB'].mean():.3f} dB")
print(f"{'='*60}")