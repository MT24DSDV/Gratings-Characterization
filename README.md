# Grating Characterization Python Toolkit

This repository contains a set of Python scripts developed during my research internship in the summer of 2026, focused on the spectral characterization of fiber Bragg gratings (FBGs).

At the moment, the toolkit includes scripts for **reflection analysis**, **transmission analysis**, and a **Transfer Matrix Method (TMM)** simulation. Since the internship is still ongoing, more tools and features may be added later as the project progresses.

## Input Files

All analysis scripts (`reflection_analysis.py` and `transmission_analysis.py`) require `.csv` files **exported directly from the Optical Spectrum Analyzer (OSA)**. The parser is designed to read the standard OSA trace format containing the `[TRACE DATA]` section with multiple traces (A to G).

## Repository Structure
The structure that follow is the recommended structure to make sure the code works correctly. As I only reach the reflection and transmission.

```
Grating-research/
├── reflection_analysis.py
├── transmission_analysis.py
├── tmm.py
├── data/
│   ├── reflection/
│   └── transmission/
└── results/
    ├── reflection/
    ├── transmission/
    └── tmm/
```


All scripts use **relative paths**, so they work on any computer without modification.

---

## 1. `reflection_analysis.py`

Analyzes reflection spectra from OSA `.csv` files. The script supports five different operating modes selected through the `MODE` variable.

### About the "box" concept

During the experiment, the fibers were not all measured at the same time. They had to be grouped and stored into different physical components, which I refer to as "boxes". Each box could contain several fibers, and the OSA file for that box would store each fiber as a separate trace (A, B, C, etc.).

This naming is only a default convention I used for organization. If you do not work with boxes, or if you want to use a different label, you can simply replace the file names and the `BOX` variable with anything that fits your own workflow (e.g., `Sample1`, `Setup_A`, `Test01`, etc.). The scripts do not depend on the word "box" itself — only on the file naming pattern.

### Common Settings

| Variable | Description |
|----------|-------------|
| `DATA_DIR` | Path to the folder containing the reflection `.csv` files |
| `RESULTS_BASE` | Output folder for plots and CSVs (auto-created) |

### Modes

#### `single`
Analyze one file using a source trace and a reflected trace.

| Variable | Description |
|----------|-------------|
| `FILE` | The `.csv` file to analyze |
| `TRACE_SOURCE` | Reference trace letter |
| `TRACE_REFLECTED` | Reflected trace letter |
| `COMPARE_TRACES` | If True, also compares two additional traces |
| `TRACE_COMPARE_1`, `TRACE_COMPARE_2` | Traces to compare |

#### `compare`
Compare two different files side-by-side, each with its own source and reflected trace.

| Variable | Description |
|----------|-------------|
| `FILE_1`, `FILE_2` | Two CSV files to compare |
| `TRACE_SOURCE_1`, `TRACE_REFLECTED_1` | Trace pair for File 1 |
| `TRACE_SOURCE_2`, `TRACE_REFLECTED_2` | Trace pair for File 2 |

#### `cross`
Compare specific traces across multiple files (any number).

I originally used this mode to test how the **same fiber** behaved at different OSA **resolutions** and at different points in time (for example, measuring the same fiber once at 0.05 nm and once at 0.5 nm resolution, in different files). The mode is built to be flexible, so each entry is a `(file, trace, label)` tuple that you can mix freely.

| Variable | Description |
|----------|-------------|
| `FILE_1`, `FILE_2` | File names (without `.csv`) |
| `FIBER_TYPE` | Label used in output plots and filenames |
| `CROSS_TRACES` | List of `(file, trace, label)` entries to overlay |

Outputs are saved per box (or your equivalent grouping), automatically detected from the file name.

### Example applications

- Compare the **same fiber** measured at **different OSA resolutions**
- Compare the **same fiber** measured at **different times** (e.g., before/after a treatment)
- Compare **forward (in→out)** vs **backward (out→in)** measurements of the same fiber
- Compare the **same fiber** under different conditions (e.g., temperature, strain, environment)
- Compare two fibers from different boxes that should theoretically behave the same
- Validate measurement repeatability across multiple acquisitions

#### `box`
Analyze every trace from one file against a single reference trace.
Useful when one OSA file contains several fibers measured together. Outputs are organized into one subfolder per trace.

| Variable | Description |
|----------|-------------|
| `BOX_FILE` | File containing all traces |
| `BOX_REFERENCE_TRACE` | Reference trace |
| `BOX_TRACES` | List of `(trace_letter, custom_name)` pairs |

#### `full`
Plot the full spectrum of a single file with all traces.

| Variable | Description |
|----------|-------------|
| `FULL_FILE` | File to plot |
| `FULL_EXCLUDE` | List of traces to exclude (e.g., `["F", "G"]`) |

---

## 2. `transmission_analysis.py`

Analyzes the transmission spectrum of a fiber from OSA `.csv` measurements.
The script automatically locates the file corresponding to the selected box.

### Settings to Change

| Variable | Description |
|----------|-------------|
| `BOX` | Selects which box (or sample group) to analyze (e.g., `"Box1"`, `"SampleA"`) |
| `TRACE_SOURCE` | Trace used as the reference / input |
| `TRACE_TRANSMITTED` | Trace corresponding to the transmitted signal |
| `DATA_DIR` | Folder containing the transmission `.csv` files |
| `OUTPUT_DIR` | Folder where outputs are saved (auto-created) |

As mentioned earlier, the `BOX` variable is only a default label used for file organization. You can rename it to match your own naming scheme — the script only relies on the file name pattern, not the word "box" itself.

### Output

The script produces:

- A 3-panel figure containing:
  1. Full spectrum (all traces)
  2. Source vs Transmitted
  3. Transmission and Insertion Loss curves
- A CSV file with the calculated transmission values
- A text summary in the console with min/max/mean transmission and insertion loss

---

## 3. `tmm.py`

Simulates the theoretical reflection and transmission spectra of an FBG using the Transfer Matrix Method (TMM). The script also computes the Bragg wavelength shift under different strain values.

### Grating Parameters

| Variable | Description |
|----------|-------------|
| `n_eff` | Effective refractive index of the fiber |
| `lambda_B` | Bragg wavelength (m) |
| `delta_n` | Index modulation amplitude |
| `L` | Grating length (m) |
| `N_layers` | Number of layers used in the TMM computation |

### Strain Parameters

| Variable | Description |
|----------|-------------|
| `p_e` | Photoelastic coefficient (~ 0.22 for silica) |
| `strain_values` | List of strain levels to simulate |

### Spectrum Settings

| Variable | Description |
|----------|-------------|
| `lambda_span` | Wavelength range simulated around `lambda_B` |
| `N_wavelengths` | Spectral resolution of the simulation |
| `apodization` | `"uniform"`, `"gaussian"`, or `"raised_cosine"` |
| `apod_fwhm` | Width of the apodization profile |

### Output

The script generates:

- A 2x2 figure with reflection (linear and dB), transmission, and Bragg shift vs strain
- A CSV file per strain value containing the simulated spectra
- A CSV file summarizing the peak wavelength as a function of strain
- A console summary including theoretical and simulated strain sensitivity

---

## Requirements

- Python 3.10 or higher
- numpy
- pandas
- matplotlib

Install dependencies:

pip install -r requirements.txt


## Notes

- All scripts read and write files relative to their own location.
- Place your raw OSA `.csv` measurement files inside the appropriate `data/` subfolder.
- All generated plots and CSVs are automatically saved in the `results/` subfolders.
- The "box" terminology is only a default naming convention; rename it freely.
- More analysis tools may be added later as the internship progresses.
