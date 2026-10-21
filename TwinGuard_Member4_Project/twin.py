import numpy as np

# ---------- 1. PLANT: the "real" system (hidden from the twin) ----------
def simulate_plant(seed, n=200, load=1.0, ambient=25.0, fault=None, fault_start=100):
    r = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    v0 = 4.10 + r.normal(0, 0.02)                    # unit-to-unit variation
    k = 0.004 * load * (1 + r.normal(0, 0.05))
    volt = v0 - k * t - 2e-6 * t**2 * load            # unmodelled curvature
    temp = ambient + 8 * load * (1 - np.exp(-t / 45)) + 0.5 * np.sin(t / 30)
    volt = volt + r.normal(0, 0.01, n)                # sensor noise
    temp = temp + r.normal(0, 0.3, n)
    post = t >= fault_start
    if fault == "sensor_drift":
        temp = temp + np.where(post, 0.06 * (t - fault_start), 0)
    elif fault == "battery_degradation":
        volt = volt - np.where(post, 0.004 * (t - fault_start), 0)
    elif fault == "config_mismatch":
        volt = volt + np.where(post, -0.12, 0)
    elif fault == "comm_loss":
        volt = np.where(post, np.nan, volt); temp = np.where(post, np.nan, temp)
    return dict(t=t, volt=volt, temp=temp, load=load, ambient=ambient)

# ---------- 2. TWIN: deliberately simpler model, fitted on baseline ----------
class Twin:
    TAU = 45.0
    def fit(self, runs):
        A, y = [], []
        for r in runs:
            A.append(np.column_stack([np.ones_like(r["t"]), r["load"] * r["t"]]))
            y.append(r["volt"])
        self.vc, *_ = np.linalg.lstsq(np.vstack(A), np.concatenate(y), rcond=None)
        X, y = [], []
        for r in runs:
            X.append(r["load"] * (1 - np.exp(-r["t"] / self.TAU)))
            y.append(r["temp"] - r["ambient"])
        X, y = np.concatenate(X), np.concatenate(y)
        self.tc = float(X @ y / (X @ X))
        # residual spread + validated operating range
        rv = np.concatenate([r["volt"] - self.pred_v(r) for r in runs])
        rt = np.concatenate([r["temp"] - self.pred_t(r) for r in runs])
        self.sv, self.st = rv.std(), rt.std()
        self.load_rng = (min(r["load"] for r in runs), max(r["load"] for r in runs))
        self.amb_rng = (min(r["ambient"] for r in runs), max(r["ambient"] for r in runs))
        return self
    def pred_v(self, r): return self.vc[0] + self.vc[1] * r["load"] * r["t"]
    def pred_t(self, r): return r["ambient"] + self.tc * r["load"] * (1 - np.exp(-r["t"] / self.TAU))

    def assess(self, r, end, window=15):
        s = slice(max(0, end - window), end)
        v, t = r["volt"][s], r["temp"][s]
        if np.isnan(v).any() or np.isnan(t).any():
            return dict(confidence=0.0, status="Untrusted", reason="Missing sensor data")
        zv = (v - self.pred_v(r)[s]) / self.sv
        zt = (t - self.pred_t(r)[s]) / self.st
        z_rms = float(np.sqrt(np.mean(np.concatenate([zv, zt]) ** 2)))
        conf = float(np.clip(100 * (1 - (z_rms - 1) / 4), 0, 100))
        reason = f"Prediction error z_rms={z_rms:.2f}"
        in_rng = (self.load_rng[0] - .05 <= r["load"] <= self.load_rng[1] + .05 and
                  self.amb_rng[0] - 2 <= r["ambient"] <= self.amb_rng[1] + 2)
        if not in_rng:
            conf = min(conf, 40.0); reason += "; outside validated operating range"
        return dict(confidence=conf, status=self.classify(conf), reason=reason)

    hi, lo = 80.0, 50.0
    def classify(self, c): return "Trusted" if c >= self.hi else "Degraded" if c >= self.lo else "Untrusted"

    def calibrate(self, runs, pct=2):
        # set the Trusted threshold from fault-free, held-out runs
        cs = [self.assess(r, e)["confidence"] for r in runs for e in range(30, len(r["t"]), 5)]
        self.hi = float(np.percentile(cs, pct)); self.lo = self.hi - 30

# ---------- 3. EVALUATION ----------
if __name__ == "__main__":
    loads = [0.8, 1.0, 1.2]
    train = [simulate_plant(s, load=l, ambient=a) for s in range(10) for l, a in zip(loads, [20, 25, 30])]
    calib = [simulate_plant(100 + s, load=l, ambient=25) for s in range(10) for l in loads]
    twin = Twin().fit(train); twin.calibrate(calib)
    print(f"thresholds: Trusted>={twin.hi:.1f}  Untrusted<{twin.lo:.1f}")
    test_clean = [simulate_plant(500 + s, load=l) for s in range(20) for l in loads]
    fa = np.mean([twin.assess(r, e)["status"] != "Trusted" for r in test_clean for e in range(30, 200, 5)])
    print(f"false-alarm rate (clean, held-out): {fa:.1%}")
    for f in ["sensor_drift", "battery_degradation", "config_mismatch", "comm_loss"]:
        det = []
        for s in range(20):
            r = simulate_plant(900 + s, load=1.0, fault=f)
            det.append(any(twin.assess(r, e)["status"] != "Trusted" for e in range(100, 200, 2)))
        print(f"{f:20s} detection: {np.mean(det):.0%}")
    r = simulate_plant(1, load=2.0); print("out-of-range load ->", twin.assess(r, 150))
