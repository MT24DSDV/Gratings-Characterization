# **Gratings Characterization Toolkit**

This repository contains a set of Python tools developed during my 2026 research internship for the spectral characterization of fiber Bragg gratings (FBGs).  
It includes:

- Reflection spectrum analysis  
- Transmission spectrum analysis  
- Transfer Matrix Method (TMM) simulation  

The project is still evolving and may expand with additional analysis tools.

---

## **1. Required Input Files**

All analysis scripts (`reflection_analysis.py` and `transmission_analysis.py`) expect `.csv` files exported directly from an Optical Spectrum Analyzer (OSA).

The parser is designed for the standard OSA format containing:

```
[TRACE DATA]
```

with traces labeled **A–G**.

---

## **2. Recommended Repository Structure**

```
Grating-research/
├── reflection_analysis.py
├── transmission_analysis.py
├── tmm.py
├── data/
│   ├── reflection/
│   ├── transmission/
│   └── Example/
│       ├── comparison/
│       ├── cross/
│       └── full/
└── results/
    ├── reflection/
    ├── transmission/
    └── tmm/
```

All scripts use **relative paths**, so the toolkit works on any machine without modification.

---

## **3. File Naming Convention**

Measurement files follow this pattern:

```
SAMPLENAME_DD-MM-YY.csv
```

Examples:

```
BOX2_IN_OUT_10-06-26.csv
BOX1_0.050_10-06-26.csv
```

### Why this convention?

- The **sample name** appears first for quick identification.  
- The **date at the end** keeps files chronologically sorted.  
- Scripts automatically extract the date for labeling plots and outputs.  

If you use a different naming scheme, simply update the file name variables (`FILE`, `FILE_1`, etc.).  
The scripts do **not** depend on the date format.

### About the “box” terminology

In the original experiment, fibers were grouped into physical containers (“boxes”), and each OSA file contained multiple traces (A–G) corresponding to fibers in that box.

This is **only a naming convention**.  
You can replace it with:

- `Sample1`  
- `Setup_A`  
- `Test01`  
- anything that fits your workflow  

The scripts only rely on the file name you provide.

---

# **4. reflection_analysis.py**

Analyzes reflection spectra from OSA measurements.  
Supports five modes:

### **Modes Overview**

- **single** — Analyze one file using a source and reflected trace  
- **compare** — Compare two files side-by-side  
- **cross** — Overlay selected traces across multiple files  
- **box** — Compare all traces in one file against a reference  
- **full** — Plot the full spectrum of a file  

### **When to use each mode**

- Compare the same fiber at different OSA resolutions  
- Compare measurements taken at different times  
- Compare forward vs backward measurements  
- Compare fibers from different groups  
- Validate measurement repeatability  

### **Example Outputs (included in repo)**

```
data/Example/
├── comparison/
│   └── comparison_BOX1_vs_BOX2.png
├── cross/
│   ├── cross_isolated_FiberName.png
│   ├── cross_overlay_in_out_FiberName.png
│   └── cross_overlay_out_in_FiberName.png
└── full/
    └── full_spectrum_BOX1.png
```

Reflection results are saved in:

```
results/reflection/
```

---

# **5. transmission_analysis.py**

Analyzes transmission spectra and computes insertion loss.

### **Outputs**

- Full spectrum plot  
- Source vs transmitted comparison  
- Transmission and insertion loss curves  
- CSV file with computed values  
- Console summary (min/max/mean transmission)  

Example output:

```
results/transmission/Example/
├── transmission_Test_data_transmission_DATE.csv
└── transmission_Test_data_transmission_DATE.png
```

---

# **6. tmm.py**

Simulates theoretical FBG spectra using the Transfer Matrix Method.

### **Features**

- Reflection (linear and dB)  
- Transmission (dB)  
- Bragg wavelength shift vs strain  
- CSV export of spectra  
- CSV export of peak wavelength vs strain  
- Sensitivity calculation  

Results are saved in:

```
results/tmm/
```

---

## **7. Requirements**

- Python 3.10+  
- numpy  
- pandas  
- matplotlib  

Install dependencies:

```
pip install -r requirements.txt
```

---

## **8. Notes**

- All scripts use relative paths for portability.  
- Input files must be OSA-exported `.csv` files.  
- Example folders illustrate expected outputs.  
- Naming conventions are flexible — adjust to your workflow.  
- The project is actively evolving.

