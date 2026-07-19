#!/usr/bin/env python
"""Z -> mumu peak position from the CMS 2012 DoubleMuParked Open Data skim.

Runs the full analysis end-to-end and writes results/results.json and
figures/dimuon_mass.pdf. Deterministic: no random numbers are used.

Usage:
    python analysis.py [--data PATH] [--outdir DIR]
"""

import argparse
import json
from pathlib import Path

import awkward as ak
import matplotlib
import numpy as np
import uproot
from hist import Hist
from scipy.optimize import curve_fit
from scipy.special import voigt_profile

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_DATA = (
    "/Users/ketchum/REPOS/fisicai/src/fisicai/hepabench/data/"
    "opendata_zmumu/zmumu_skim.root"
)

# Selection
PT_MIN = 20.0  # GeV
ETA_MAX = 2.4

# Mass window and binning of the spectrum
M_LO, M_HI = 60.0, 120.0
N_BINS = 120  # 0.5 GeV bins

# Nominal fit range (core of the peak; the low-mass FSR tail is excluded) and
# the alternative ranges used to assess the fit-range systematic
FIT_LO, FIT_HI = 85.0, 97.0
FIT_RANGE_VARIATIONS = [(80.0, 100.0), (83.0, 99.0), (86.0, 96.0)]

# External comparison values (PDG 2024, quoted in the note as comparisons only)
M_Z_PDG = 91.1880  # GeV
M_Z_PDG_ERR = 0.0020  # GeV
GAMMA_Z_PDG = 2.4955  # GeV, fixed in the fit


def load_muons(path):
    tree = uproot.open(path)["Events"]
    return tree.arrays(
        ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge"]
    )


def select_dimuon_mass(events):
    """Apply the selection and return (masses, cutflow) with raw event counts."""
    cutflow = [("all events", len(events))]

    good = (events.Muon_pt > PT_MIN) & (abs(events.Muon_eta) < ETA_MAX)
    mu = events[ak.num(events.Muon_pt[good]) == 2]
    good = (mu.Muon_pt > PT_MIN) & (abs(mu.Muon_eta) < ETA_MAX)
    pt, eta, phi, mass, charge = (
        mu.Muon_pt[good], mu.Muon_eta[good], mu.Muon_phi[good],
        mu.Muon_mass[good], mu.Muon_charge[good],
    )
    cutflow.append(("exactly 2 muons, pt>20, |eta|<2.4", len(pt)))

    os_pair = ak.sum(charge, axis=1) == 0
    pt, eta, phi, mass = pt[os_pair], eta[os_pair], phi[os_pair], mass[os_pair]
    cutflow.append(("opposite charge", len(pt)))

    px = pt * np.cos(phi)
    py = pt * np.sin(phi)
    pz = pt * np.sinh(eta)
    e = np.sqrt(mass**2 + px**2 + py**2 + pz**2)
    m2 = (
        (ak.sum(e, axis=1)) ** 2
        - (ak.sum(px, axis=1)) ** 2
        - (ak.sum(py, axis=1)) ** 2
        - (ak.sum(pz, axis=1)) ** 2
    )
    m_mumu = ak.to_numpy(np.sqrt(np.maximum(m2, 0.0)))

    in_window = m_mumu[(m_mumu >= M_LO) & (m_mumu < M_HI)]
    cutflow.append((f"{M_LO:.0f} <= m < {M_HI:.0f} GeV", len(in_window)))
    return in_window, cutflow


def make_model(fit_lo, fit_hi):
    """Expected counts per bin: Voigtian signal + falling exponential background.

    The Breit-Wigner width is fixed to the PDG Z width; sigma absorbs the
    detector resolution. Both components are normalized over the fit range so
    n_sig and n_bkg are yields in that range.
    """
    bin_width = (M_HI - M_LO) / N_BINS

    def model(m, n_sig, mu, sigma, n_bkg, slope):
        sig = voigt_profile(m - mu, sigma, GAMMA_Z_PDG / 2.0)
        bkg_norm = (
            np.exp(-slope * (fit_lo - M_LO)) - np.exp(-slope * (fit_hi - M_LO))
        ) / slope
        bkg = np.exp(-slope * (m - M_LO)) / bkg_norm
        return bin_width * (n_sig * sig + n_bkg * bkg)

    return model


def run_fit(counts, centers, fit_lo, fit_hi):
    sel = (centers > fit_lo) & (centers < fit_hi)
    c, x = counts[sel], centers[sel]
    errors = np.sqrt(np.maximum(c, 1.0))
    model = make_model(fit_lo, fit_hi)
    p0 = [c.sum() * 0.95, 91.0, 1.5, c.sum() * 0.05, 0.02]
    popt, pcov = curve_fit(
        model, x, c, p0=p0, sigma=errors, absolute_sigma=True,
        bounds=([0, 85, 0.1, 0, 1e-4], [np.inf, 95, 5, np.inf, 1]),
    )
    perr = np.sqrt(np.diag(pcov))
    resid = (c - model(x, *popt)) / errors
    chi2 = float(np.sum(resid**2))
    ndf = len(c) - len(popt)
    return popt, perr, chi2, ndf


def make_figure(h, popt, m_peak, outpath):
    counts = h.values()
    centers = h.axes[0].centers
    errors = np.sqrt(counts)
    model = make_model(FIT_LO, FIT_HI)

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.errorbar(
        centers, counts, yerr=errors, fmt="o", ms=3, lw=1, color="black",
        label="Data", zorder=3,
    )
    m_fine = np.linspace(FIT_LO, FIT_HI, 400)
    ax.plot(
        m_fine, model(m_fine, *popt), color="#2c7fb8", lw=2,
        label="Voigtian + exp. fit", zorder=2,
    )
    bkg_only = model(m_fine, 0.0, popt[1], popt[2], popt[3], popt[4])
    ax.plot(
        m_fine, bkg_only, color="#999999", lw=1.5, ls="--",
        label="Background component", zorder=1,
    )
    ax.axvline(m_peak, color="#d95f0e", lw=1.5, ls=":", zorder=1)
    ax.annotate(
        f"peak = {m_peak:.2f} GeV",
        xy=(m_peak, ax.get_ylim()[1] * 0.72),
        xytext=(m_peak + 7, ax.get_ylim()[1] * 0.8),
        arrowprops=dict(arrowstyle="->", color="#d95f0e"),
        color="#d95f0e", fontsize=10,
    )
    ax.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
    ax.set_ylabel(f"Events / {(M_HI - M_LO) / N_BINS:.1f} GeV")
    ax.set_xlim(M_LO, M_HI)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, lw=0.5)
    ax.set_title("CMS Open Data 2012, DoubleMuParked skim", fontsize=11)
    fig.tight_layout()
    fig.savefig(outpath)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", default=DEFAULT_DATA, help="Input ROOT skim")
    parser.add_argument(
        "--outdir", default=str(Path(__file__).parent),
        help="Bundle directory (results/ and figures/ are created inside)",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    (outdir / "results").mkdir(exist_ok=True)
    (outdir / "figures").mkdir(exist_ok=True)

    events = load_muons(args.data)
    masses, cutflow = select_dimuon_mass(events)
    for name, n in cutflow:
        print(f"{name:40s} {n:8d}")

    h = Hist.new.Reg(N_BINS, M_LO, M_HI, name="m").Double().fill(masses)
    counts, centers = h.values(), h.axes[0].centers

    popt, perr, chi2, ndf = run_fit(counts, centers, FIT_LO, FIT_HI)
    n_sig, m_peak, sigma, n_bkg, slope = popt

    shifts = []
    for lo, hi in FIT_RANGE_VARIATIONS:
        popt_v, _, chi2_v, ndf_v = run_fit(counts, centers, lo, hi)
        shifts.append(popt_v[1] - m_peak)
        print(f"variation [{lo:.0f},{hi:.0f}]: peak={popt_v[1]:.3f} "
              f"(shift {popt_v[1] - m_peak:+.3f}), chi2/ndf={chi2_v / ndf_v:.2f}")
    syst_range = float(np.max(np.abs(shifts)))

    make_figure(h, popt, m_peak, outdir / "figures" / "dimuon_mass.pdf")

    delta = m_peak - M_Z_PDG
    results = {
        "n_events_total": cutflow[0][1],
        "n_events_two_muons": cutflow[1][1],
        "n_events_opposite_charge": cutflow[2][1],
        "n_events_mass_window": cutflow[3][1],
        "bin_width_gev": f"{(M_HI - M_LO) / N_BINS:.1f}",
        "mass_window_lo": f"{M_LO:.0f}",
        "mass_window_hi": f"{M_HI:.0f}",
        "fit_lo": f"{FIT_LO:.0f}",
        "fit_hi": f"{FIT_HI:.0f}",
        "pt_min": f"{PT_MIN:.0f}",
        "eta_max": f"{ETA_MAX:.1f}",
        "m_z_peak": f"{m_peak:.3f}",
        "m_z_peak_stat": f"{perr[1]:.3f}",
        "m_z_peak_syst_range": f"{syst_range:.3f}",
        "sigma_res": f"{sigma:.2f}",
        "sigma_res_stat": f"{perr[2]:.2f}",
        "n_sig_fit": f"{n_sig:.0f}",
        "n_sig_fit_stat": f"{perr[0]:.0f}",
        "n_bkg_fit": f"{n_bkg:.0f}",
        "chi2": f"{chi2:.1f}",
        "ndf": ndf,
        "chi2_ndf": f"{chi2 / ndf:.2f}",
        "gamma_z_pdg": f"{GAMMA_Z_PDG:.4f}",
        "m_z_pdg": f"{M_Z_PDG:.4f}",
        "m_z_pdg_err": f"{M_Z_PDG_ERR:.4f}",
        "peak_minus_pdg_mev": f"{delta * 1000:.0f}",
        "peak_minus_pdg_permille": f"{abs(delta) / M_Z_PDG * 1000:.1f}",
    }
    with open(outdir / "results" / "results.json", "w") as f:
        json.dump(results, f, indent=2)
        f.write("\n")

    print(f"\npeak = {m_peak:.3f} +/- {perr[1]:.3f} (stat) "
          f"+/- {syst_range:.3f} (fit range) GeV  (PDG: {M_Z_PDG} GeV)")
    print(f"chi2/ndf = {chi2:.1f}/{ndf}")
    print(f"wrote {outdir / 'results' / 'results.json'}")


if __name__ == "__main__":
    main()
