#!/usr/bin/env python
"""Z -> mumu peak position from the CMS 2012 DoubleMuParked Open Data skim.

Runs the full analysis end-to-end and writes results/results.json and the
figures/ directory (spectrum + fit with pulls, muon kinematics, log-scale
spectrum, fit-range scan). Deterministic: no random numbers are used.

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
import mplhep

from fisicai.hepabench import DATA_DIR  # noqa: E402  (skim ships with the package)

DEFAULT_DATA = str(DATA_DIR / "opendata_zmumu" / "zmumu_skim.root")

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

# Cross-check binning (half the nominal bin width; not a systematic)
N_BINS_CHECK = 240

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
    """Apply the selection; return (masses, cutflow, kinematics of selected muons)."""
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

    window = (m_mumu >= M_LO) & (m_mumu < M_HI)
    in_window = m_mumu[window]
    cutflow.append((f"{M_LO:.0f} <= m < {M_HI:.0f} GeV", len(in_window)))

    pt_win = ak.to_numpy(pt[window])
    kin = {
        "pt_lead": np.max(pt_win, axis=1),
        "pt_sublead": np.min(pt_win, axis=1),
        "eta": ak.to_numpy(ak.flatten(eta[window])),
    }
    return in_window, cutflow, kin


def make_model(fit_lo, fit_hi, bin_width):
    """Expected counts per bin: Voigtian signal + falling exponential background.

    The Breit-Wigner width is fixed to the PDG Z width; sigma absorbs the
    detector resolution. Both components are normalized over the fit range so
    n_sig and n_bkg are yields in that range.
    """

    def model(m, n_sig, mu, sigma, n_bkg, slope):
        sig = voigt_profile(m - mu, sigma, GAMMA_Z_PDG / 2.0)
        bkg_norm = (
            np.exp(-slope * (fit_lo - M_LO)) - np.exp(-slope * (fit_hi - M_LO))
        ) / slope
        bkg = np.exp(-slope * (m - M_LO)) / bkg_norm
        return bin_width * (n_sig * sig + n_bkg * bkg)

    return model


def run_fit(counts, centers, fit_lo, fit_hi, bin_width):
    sel = (centers > fit_lo) & (centers < fit_hi)
    c, x = counts[sel], centers[sel]
    errors = np.sqrt(np.maximum(c, 1.0))
    model = make_model(fit_lo, fit_hi, bin_width)
    p0 = [c.sum() * 0.95, 91.0, 1.5, c.sum() * 0.05, 0.02]
    popt, pcov = curve_fit(
        model, x, c, p0=p0, sigma=errors, absolute_sigma=True,
        bounds=([0, 85, 0.1, 0, 1e-4], [np.inf, 95, 5, np.inf, 1]),
    )
    perr = np.sqrt(np.diag(pcov))
    pulls = (c - model(x, *popt)) / errors
    chi2 = float(np.sum(pulls**2))
    ndf = len(c) - len(popt)
    return popt, perr, chi2, ndf, pulls


def _cms_label(ax):
    mplhep.cms.label("Open Data", data=True, rlabel="2012 (8 TeV)", ax=ax)


def make_fit_figure(h, popt, pulls, outpath):
    """Spectrum with the fit overlaid and a pull panel underneath."""
    plt.style.use(mplhep.style.CMS)
    counts = h.values()
    centers = h.axes[0].centers
    errors = np.sqrt(counts)
    bin_width = (M_HI - M_LO) / N_BINS
    model = make_model(FIT_LO, FIT_HI, bin_width)

    fig, (ax, axp) = plt.subplots(
        2, 1, sharex=True, height_ratios=[3, 1],
        gridspec_kw={"hspace": 0.06},
    )
    m_fine = np.linspace(FIT_LO, FIT_HI, 400)
    ax.plot(
        m_fine, model(m_fine, *popt), color="#e42536", lw=2,
        label="Voigtian + exp. fit", zorder=2,
    )
    bkg_only = model(m_fine, 0.0, popt[1], popt[2], popt[3], popt[4])
    ax.plot(
        m_fine, bkg_only, color="#5790fc", lw=2, ls="--",
        label="Background component", zorder=1,
    )
    ax.errorbar(
        centers, counts, yerr=errors, fmt="o", color="black", ms=5, lw=1.2,
        label="Data", zorder=3,
    )
    ax.set_ylabel(f"Events / {bin_width:.1f} GeV")
    ax.set_xlim(M_LO, M_HI)
    ax.set_ylim(bottom=0)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(name) for name in
             ("Data", "Voigtian + exp. fit", "Background component")]
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc="upper left")
    _cms_label(ax)

    fit_centers = centers[(centers > FIT_LO) & (centers < FIT_HI)]
    axp.axhline(0.0, color="black", lw=1)
    for y in (-2.0, 2.0):
        axp.axhline(y, color="gray", lw=1, ls=":")
    axp.errorbar(
        fit_centers, pulls, yerr=np.ones_like(pulls), fmt="o",
        color="black", ms=4, lw=1.2,
    )
    axp.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
    axp.set_ylabel("Pull", fontsize="small")
    axp.set_ylim(-4, 4)

    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def make_log_figure(h, popt, outpath):
    """Full-window spectrum on a log scale, fit range indicated."""
    plt.style.use(mplhep.style.CMS)
    counts = h.values()
    centers = h.axes[0].centers
    errors = np.sqrt(counts)
    bin_width = (M_HI - M_LO) / N_BINS
    model = make_model(FIT_LO, FIT_HI, bin_width)

    fig, ax = plt.subplots()
    ax.axvspan(FIT_LO, FIT_HI, color="#f5c518", alpha=0.18, lw=0,
               label=f"Fit range {FIT_LO:.0f}–{FIT_HI:.0f} GeV")
    m_fine = np.linspace(FIT_LO, FIT_HI, 400)
    ax.plot(m_fine, model(m_fine, *popt), color="#e42536", lw=2,
            label="Voigtian + exp. fit", zorder=2)
    ax.errorbar(centers, counts, yerr=errors, fmt="o", color="black",
                ms=4, lw=1.2, label="Data", zorder=3)
    ax.annotate(
        "FSR tail", xy=(83.0, 180.0), xytext=(70.5, 700.0),
        arrowprops={"arrowstyle": "->", "lw": 1.2}, fontsize="small",
    )
    ax.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
    ax.set_ylabel(f"Events / {bin_width:.1f} GeV")
    ax.set_xlim(M_LO, M_HI)
    ax.set_yscale("log")
    ax.set_ylim(5, 3e4)
    handles, labels = ax.get_legend_handles_labels()
    order = [labels.index(name) for name in
             ("Data", "Voigtian + exp. fit", f"Fit range {FIT_LO:.0f}–{FIT_HI:.0f} GeV")]
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc="upper right")
    _cms_label(ax)
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def make_kinematics_figure(kin, outpath):
    """pt of the leading/subleading muon and eta of both, after full selection."""
    plt.style.use(mplhep.style.CMS)
    fig, (ax_pt, ax_eta) = plt.subplots(1, 2, figsize=(20, 8))

    pt_bins = np.linspace(20.0, 120.0, 50)
    ax_pt.hist(kin["pt_lead"], bins=pt_bins, histtype="step", lw=2,
               color="#e42536", label="Leading muon")
    ax_pt.hist(kin["pt_sublead"], bins=pt_bins, histtype="step", lw=2,
               color="#5790fc", label="Subleading muon")
    ax_pt.set_xlabel(r"$p_{\mathrm{T}}^{\mu}$ [GeV]")
    ax_pt.set_ylabel("Events / 2 GeV")
    ax_pt.set_xlim(20.0, 120.0)
    ax_pt.legend()
    _cms_label(ax_pt)

    eta_bins = np.linspace(-ETA_MAX, ETA_MAX, 48)
    ax_eta.hist(kin["eta"], bins=eta_bins, histtype="step", lw=2,
                color="black", label="All selected muons")
    ax_eta.set_xlabel(r"$\eta^{\mu}$")
    ax_eta.set_ylabel("Muons / 0.1")
    ax_eta.set_xlim(-ETA_MAX, ETA_MAX)
    ax_eta.set_ylim(bottom=0)
    ax_eta.legend(loc="lower center")
    _cms_label(ax_eta)

    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)


def make_scan_figure(variations, nominal_peak, nominal_err, syst, outpath):
    """Fitted peak for the nominal and alternative fit ranges, with the assigned band."""
    plt.style.use(mplhep.style.CMS)
    fig, ax = plt.subplots()

    labels = [f"{FIT_LO:.0f}–{FIT_HI:.0f}\n(nominal)"] + [
        f"{lo:.0f}–{hi:.0f}" for lo, hi, _, _ in variations
    ]
    peaks = [nominal_peak] + [p for _, _, p, _ in variations]
    errs = [nominal_err] + [e for _, _, _, e in variations]
    x = np.arange(len(peaks))

    ax.axhspan(nominal_peak - syst, nominal_peak + syst, color="#f5c518",
               alpha=0.35, lw=0, label="Assigned fit-range syst.")
    ax.axhline(nominal_peak, color="#e42536", lw=1.5, ls="--", label="Nominal fit")
    ax.axhline(M_Z_PDG, color="gray", lw=1.5, ls=":",
               label=r"$m_{\mathrm{Z}}$ (PDG)")
    ax.errorbar(x, peaks, yerr=errs, fmt="o", color="black", ms=7, lw=1.5,
                label="Fitted peak (stat.)", zorder=3)

    ax.set_xticks(x, labels)
    ax.set_xlim(-0.6, len(peaks) - 0.4)
    ax.set_ylim(90.80, 91.35)
    ax.set_xlabel("Fit range [GeV]")
    ax.set_ylabel(r"$m_{\mu\mu}^{\mathrm{peak}}$ [GeV]")
    handles, labels_ = ax.get_legend_handles_labels()
    order = [labels_.index(name) for name in
             ("Fitted peak (stat.)", "Nominal fit", "Assigned fit-range syst.",
              r"$m_{\mathrm{Z}}$ (PDG)")]
    ax.legend([handles[i] for i in order], [labels_[i] for i in order],
              loc="upper right", fontsize="small")
    _cms_label(ax)
    fig.savefig(outpath, bbox_inches="tight")
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
    masses, cutflow, kin = select_dimuon_mass(events)
    for name, n in cutflow:
        print(f"{name:40s} {n:8d}")

    bin_width = (M_HI - M_LO) / N_BINS
    h = Hist.new.Reg(N_BINS, M_LO, M_HI, name="m").Double().fill(masses)
    counts, centers = h.values(), h.axes[0].centers

    popt, perr, chi2, ndf, pulls = run_fit(counts, centers, FIT_LO, FIT_HI, bin_width)
    n_sig, m_peak, sigma, n_bkg, slope = popt
    max_abs_pull = float(np.max(np.abs(pulls)))

    # Fit-range variations: the assigned systematic is the largest peak shift
    variations = []
    for lo, hi in FIT_RANGE_VARIATIONS:
        popt_v, perr_v, chi2_v, ndf_v, _ = run_fit(counts, centers, lo, hi, bin_width)
        variations.append((lo, hi, popt_v[1], perr_v[1], chi2_v / ndf_v))
        print(f"variation [{lo:.0f},{hi:.0f}]: peak={popt_v[1]:.3f} "
              f"(shift {popt_v[1] - m_peak:+.3f}), chi2/ndf={chi2_v / ndf_v:.2f}")
    syst_range = float(np.max([abs(p - m_peak) for _, _, p, _, _ in variations]))

    # Binning cross-check (half bin width, nominal range): not a systematic,
    # reported to show the peak is stable against the histogramming choice
    bin_width_check = (M_HI - M_LO) / N_BINS_CHECK
    h_check = Hist.new.Reg(N_BINS_CHECK, M_LO, M_HI, name="m").Double().fill(masses)
    popt_c, _, _, _, _ = run_fit(
        h_check.values(), h_check.axes[0].centers, FIT_LO, FIT_HI, bin_width_check
    )
    binning_shift_mev = (popt_c[1] - m_peak) * 1000.0
    print(f"binning check ({N_BINS_CHECK} bins): peak={popt_c[1]:.3f} "
          f"(shift {binning_shift_mev:+.0f} MeV)")

    make_fit_figure(h, popt, pulls, outdir / "figures" / "dimuon_mass.pdf")
    make_log_figure(h, popt, outdir / "figures" / "dimuon_mass_log.pdf")
    make_kinematics_figure(kin, outdir / "figures" / "muon_kinematics.pdf")
    make_scan_figure(
        [(lo, hi, p, e) for lo, hi, p, e, _ in variations],
        m_peak, perr[1], syst_range,
        outdir / "figures" / "fit_range_scan.pdf",
    )

    delta = m_peak - M_Z_PDG
    var_results = {}
    for name, (lo, hi, p, e, c2n) in zip("abc", variations):
        var_results[f"var_{name}"] = {
            "lo": f"{lo:.0f}",
            "hi": f"{hi:.0f}",
            "peak": f"{p:.3f}",
            "peak_stat": f"{e:.3f}",
            "shift_mev": f"{(p - m_peak) * 1000:+.0f}",
            "chi2_ndf": f"{c2n:.2f}",
        }

    results = {
        "n_events_total": cutflow[0][1],
        "n_events_two_muons": cutflow[1][1],
        "n_events_opposite_charge": cutflow[2][1],
        "n_events_mass_window": cutflow[3][1],
        "bin_width_gev": f"{bin_width:.1f}",
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
        "max_abs_pull": f"{max_abs_pull:.1f}",
        "n_bins_check": N_BINS_CHECK,
        "binning_check_shift_mev": f"{binning_shift_mev:+.0f}",
        **var_results,
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
    print(f"chi2/ndf = {chi2:.1f}/{ndf}, max |pull| = {max_abs_pull:.1f}")
    print(f"wrote {outdir / 'results' / 'results.json'}")


if __name__ == "__main__":
    main()
