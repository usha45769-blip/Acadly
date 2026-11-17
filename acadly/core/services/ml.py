"""Future attendance prediction (Pandas + NumPy + Scikit-learn).

For one student and one subject:
  * past classes -> DataFrame with features: weekday, start hour, running attendance rate
  * LogisticRegression learns P(present) for a class
  * every remaining class on the timetable is scored, and the expected number
    attended is added to what the student already has
With fewer than MIN_ROWS logged classes (or only one outcome so far) the model falls
back to the student's current rate, so the prediction never claims more than the data supports.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

MIN_ROWS = 12


def _history_frame(history, base_held, base_attended):
    """history: list of dicts {date, hour, present}. Adds running-rate feature."""
    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date", "hour"]).reset_index(drop=True)
    held = base_held + np.arange(len(df))
    attended = base_attended + df["present"].cumsum().shift(fill_value=0).to_numpy()
    df["prior_rate"] = np.where(held > 0, attended / np.maximum(held, 1), 1.0)
    df["weekday"] = df["date"].dt.weekday
    return df


def predict_attendance(history, base_held, base_attended, future, threshold=85):
    """future: list of dicts {weekday, hour} for each remaining class.

    Returns dict with projected final %, expected attended, and the target needed.
    """
    now_held = base_held + len(history)
    now_att = base_attended + sum(h["present"] for h in history)
    rate_now = now_att / now_held if now_held else 0.8   # weak prior when nothing is known
    n_future = len(future)
    model_used = "current-rate"
    probs = np.full(n_future, rate_now)

    if len(history) >= MIN_ROWS and n_future:
        df = _history_frame(history, base_held, base_attended)
        if df["present"].nunique() == 2:
            X = df[["weekday", "hour", "prior_rate"]].to_numpy(dtype=float)
            clf = LogisticRegression(max_iter=500).fit(X, df["present"])
            Xf = np.array([[f["weekday"], f["hour"], rate_now] for f in future], dtype=float)
            probs = clf.predict_proba(Xf)[:, 1]
            # blend with the plain rate so a small sample cannot swing the result wildly
            w = min(1.0, len(history) / 40)
            probs = w * probs + (1 - w) * rate_now
            model_used = "logistic-regression"

    expected = now_att + float(probs.sum())
    total = now_held + n_future
    projected = round(expected * 100 / total, 1) if total else 0.0
    # classes that must be attended out of the remaining ones to finish at the threshold
    need = max(0, int(np.ceil(threshold / 100 * total - now_att)))
    return {
        "projected_pct": projected,
        "expected_attended": round(expected, 1),
        "remaining_classes": n_future,
        "must_attend": need,
        "reachable": need <= n_future,
        "model": model_used,
        "will_meet": projected >= threshold,
    }
