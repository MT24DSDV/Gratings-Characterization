import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ============================================================
# OUTPUT DIRECTORY
# ============================================================

# Paths are relative to the location of this script
SCRIPT_DIR  = Path(__file__).resolve().parent

# Results folder (auto-created)
RESULTS_DIR = SCRIPT_DIR / "results" / "tmm"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# GRATING PARAMETERS
# ============================================================

# Effective refractive index of the fiber (SMF-28 ~ 1.4682)
n_eff = 1.4682

# CHANGE THESE to set the grating parameters
lambda_B   = 1550e-9    # Bragg wavelength (m)
delta_n    = 1e-4       # Index modulation
L          = 10e-3      # Grating length (m)
N_layers   = 500        # Number of layers for TMM

# Photoelastic coefficient (typical for silica ~ 0.22)
p_e = 0.22

# CHANGE THESE to set the strain values to simulate (absolute strain)
strain_values = [0, 500e-6, 1000e-6, 2000e-6]

# Wavelength span around lambda_B (in meters)
lambda_span     = 5e-9
N_wavelengths   = 1000

# CHANGE THIS to choose the apodization type:
# "uniform", "gaussian", or "raised_cosine"
apodization = 'gaussian'
apod_fwhm   = 0.5

# Save options
SAVE_CSV  = True
SAVE_PLOT = True


# ============================================================
# FUNCTIONS
# ============================================================

def get_apodization(z, L, apod_type, fwhm_frac=0.5):
    if apod_type == 'uniform':
        return np.ones_like(z)
    elif apod_type == 'gaussian':
        sigma = (fwhm_frac * L) / (2 * np.sqrt(2 * np.log(2)))
        return np.exp(-((z - L/2)**2) / (2 * sigma**2))
    elif apod_type == 'raised_cosine':
        return 0.5 * (1 + np.cos(2 * np.pi * (z - L/2) / L))
    else:
        return np.ones_like(z)


def bragg_wavelength_shift(lambda_B, p_e, strain):
    """
    Bragg wavelength shift due to strain:
    delta_lambda / lambda = (1 - p_e) * strain
    """
    return lambda_B * (1 + (1 - p_e) * strain)


def interface_matrix(n_i, n_next):
    """
    Interface matrix between layer i and layer i+1.
    """
    I = (1 / (2 * n_next)) * np.array([
        [n_i + n_next,   n_next - n_i],
        [n_next - n_i,   n_i + n_next]
    ], dtype=complex)
    return I


def propagation_matrix(n_i, k, d_i):
    """
    Propagation (transfer) matrix for layer i.
    """
    phase = n_i * k * d_i
    T = np.array([
        [np.exp(-1j * phase),  0               ],
        [0,                    np.exp(1j * phase)]
    ], dtype=complex)
    return T


def scattering_from_transfer(M):
    """
    Extract reflection R and transmission T from total transfer matrix M.
    """
    A = M[0, 0]
    B = M[0, 1]
    C = M[1, 0]
    D = M[1, 1]

    det_M = A * D - B * C

    r = -C / D
    t = det_M / D

    R = np.abs(r)**2
    T = np.abs(t)**2

    return R, T, r, t


def transfer_matrix_fbg(wavelengths, n_eff, lambda_B_shifted,
                        delta_n, L, N_layers, apod_profile):
    """
    Transfer Matrix Method for an FBG.
    """
    dz = L / N_layers
    Lambda = lambda_B_shifted / (2 * n_eff)

    R_spec = np.zeros(len(wavelengths))
    T_spec = np.zeros(len(wavelengths))

    for wi, lam in enumerate(wavelengths):
        k = 2 * np.pi / lam

        n_profile = np.zeros(N_layers)
        for j in range(N_layers):
            z_j = (j + 0.5) * dz
            n_profile[j] = (n_eff
                            + delta_n * apod_profile[j]
                            * np.cos(2 * np.pi * z_j / Lambda))

        n_all = np.concatenate(([n_eff], n_profile, [n_eff]))
        d_all = np.concatenate(([0], np.full(N_layers, dz), [0]))

        M = np.eye(2, dtype=complex)

        for j in range(len(n_all) - 1):
            n_i    = n_all[j]
            n_next = n_all[j + 1]
            d_i    = d_all[j]

            I_j = interface_matrix(n_i, n_next)

            if d_i > 0:
                T_j = propagation_matrix(n_i, k, d_i)
                M = I_j @ T_j @ M
            else:
                M = I_j @ M

        R_spec[wi], T_spec[wi], _, _ = scattering_from_transfer(M)

    return R_spec, T_spec


def find_peak_wavelength(wavelengths, R):
    idx = np.argmax(R)
    return wavelengths[idx]


# ============================================================
# MAIN SIMULATION
# ============================================================

print("=" * 60)
print(" Transfer Matrix Simulation")
print("=" * 60)

z_positions  = np.linspace(0, L, N_layers)
apod_profile = get_apodization(z_positions, L, apodization, apod_fwhm)

all_results      = {}
peak_wavelengths = []

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

colors = plt.cm.viridis(np.linspace(0, 0.9, len(strain_values)))

for idx, strain in enumerate(strain_values):

    lambda_B_shifted = bragg_wavelength_shift(lambda_B, p_e, strain)

    wavelengths = np.linspace(
        lambda_B_shifted - lambda_span,
        lambda_B_shifted + lambda_span,
        N_wavelengths
    )

    R, T = transfer_matrix_fbg(
        wavelengths, n_eff, lambda_B_shifted,
        delta_n, L, N_layers, apod_profile
    )

    peak_wl = find_peak_wavelength(wavelengths, R)
    peak_wavelengths.append((strain, peak_wl))

    strain_label = f"{strain*1e6:.0f} ue"
    all_results[strain_label] = {
        'wavelength_nm': wavelengths * 1e9,
        'R':             R,
        'T':             T,
        'R_dB':          10 * np.log10(R + 1e-10),
        'T_dB':          10 * np.log10(T + 1e-10),
        'peak_nm':       peak_wl * 1e9
    }

    print(f"Strain: {strain*1e6:7.1f} ue  ->  "
          f"lambda_B = {lambda_B_shifted*1e9:.4f} nm  |  "
          f"Peak = {peak_wl*1e9:.4f} nm")

    axes[0, 0].plot(wavelengths * 1e9, R,
                    label=strain_label, color=colors[idx], linewidth=1.5)

    axes[0, 1].plot(wavelengths * 1e9, 10 * np.log10(R + 1e-10),
                    label=strain_label, color=colors[idx], linewidth=1.5)

    axes[1, 0].plot(wavelengths * 1e9, 10 * np.log10(T + 1e-10),
                    label=strain_label, color=colors[idx], linewidth=1.5)

strains_plot = [s * 1e6 for s, _ in peak_wavelengths]
peaks_plot   = [p * 1e9 for _, p in peak_wavelengths]

axes[1, 1].plot(strains_plot, peaks_plot,
                'o-', color='C3', linewidth=2, markersize=8)
axes[1, 1].set_xlabel("Strain (ue)", fontsize=11)
axes[1, 1].set_ylabel("Peak Wavelength (nm)", fontsize=11)
axes[1, 1].set_title("Bragg Wavelength Shift vs Strain", fontsize=12)
axes[1, 1].grid(True, alpha=0.3)

sensitivity = None
if len(peak_wavelengths) > 1:
    strain_arr  = np.array([s for s, _ in peak_wavelengths])
    peak_arr    = np.array([p * 1e9 for _, p in peak_wavelengths])
    sensitivity = np.polyfit(strain_arr * 1e6, peak_arr, 1)[0]
    axes[1, 1].text(
        0.05, 0.95,
        f"Sensitivity: {sensitivity*1000:.2f} pm/ue",
        transform=axes[1, 1].transAxes,
        fontsize=11, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    )

axes[0, 0].set_xlabel("Wavelength (nm)", fontsize=11)
axes[0, 0].set_ylabel("Reflectivity", fontsize=11)
axes[0, 0].set_title("Reflection Spectrum (Linear)", fontsize=12)
axes[0, 0].legend(loc='upper right', fontsize=9)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_ylim([0, 1.05])

axes[0, 1].set_xlabel("Wavelength (nm)", fontsize=11)
axes[0, 1].set_ylabel("Reflectivity (dB)", fontsize=11)
axes[0, 1].set_title("Reflection Spectrum (dB)", fontsize=12)
axes[0, 1].legend(loc='upper right', fontsize=9)
axes[0, 1].grid(True, alpha=0.3)

axes[1, 0].set_xlabel("Wavelength (nm)", fontsize=11)
axes[1, 0].set_ylabel("Transmissivity (dB)", fontsize=11)
axes[1, 0].set_title("Transmission Spectrum (dB)", fontsize=12)
axes[1, 0].legend(loc='lower right', fontsize=9)
axes[1, 0].grid(True, alpha=0.3)

plt.suptitle(
    f"FBG | L = {L*1e3:.1f} mm | dn = {delta_n:.1e} | Apodization: {apodization}",
    fontsize=13, fontweight='bold'
)
plt.tight_layout()


# ============================================================
# SAVE FIGURE
# ============================================================

if SAVE_PLOT:
    fig_path = RESULTS_DIR / "fbg_spectrum_strain.png"
    plt.savefig(fig_path, dpi=200, bbox_inches='tight')
    print(f"\nSaved plot: {fig_path}")

plt.show()


# ============================================================
# SAVE CSV FILES
# ============================================================

if SAVE_CSV:
    for strain_label, data in all_results.items():
        df = pd.DataFrame({
            'wavelength_nm':     data['wavelength_nm'],
            'reflectivity':      data['R'],
            'transmissivity':    data['T'],
            'reflectivity_dB':   data['R_dB'],
            'transmissivity_dB': data['T_dB']
        })
        fname = RESULTS_DIR / f"fbg_spectrum_{strain_label.replace(' ', '_')}.csv"
        df.to_csv(fname, index=False)
        print(f"Saved: {fname}")

    df_peaks = pd.DataFrame({
        'strain_microstrain':  [s * 1e6 for s, _ in peak_wavelengths],
        'peak_wavelength_nm':  [p * 1e9 for _, p in peak_wavelengths]
    })
    peaks_path = RESULTS_DIR / "fbg_peak_vs_strain.csv"
    df_peaks.to_csv(peaks_path, index=False)
    print(f"Saved: {peaks_path}")


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Bragg wavelength (unstrained): {lambda_B * 1e9:.4f} nm")
print(f"Grating length:                {L * 1e3:.2f} mm")
print(f"Index modulation:              {delta_n:.2e}")
print(f"Photoelastic coefficient:      {p_e}")
print(f"Apodization:                   {apodization}")
if sensitivity is not None:
    print(f"\nTheoretical sensitivity: "
          f"{lambda_B * 1e9 * (1 - p_e) * 1e3:.2f} pm/ue")
    print(f"Simulated sensitivity:   {sensitivity * 1000:.2f} pm/ue")
print("=" * 60)