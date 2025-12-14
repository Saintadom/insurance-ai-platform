import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

def require_columns(df, cols, name):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns: {missing}")

def assert_no_nulls(df, cols, name):
    bad = df[cols].isna().sum()
    bad = bad[bad > 0]
    if len(bad) > 0:
        raise ValueError(f"{name}: nulls found:\n{bad}")

def main():
    policies  = pd.read_csv(RAW / "policies.csv", parse_dates=["inception_date","expiry_date"])
    exposures = pd.read_csv(RAW / "exposures.csv", parse_dates=["exposure_month"])
    claims    = pd.read_csv(RAW / "claims.csv", parse_dates=["loss_date","report_date"])
    payments  = pd.read_csv(RAW / "payments.csv", parse_dates=["payment_date"])

    # ---- Contracts ----
    require_columns(policies,
        ["policy_id","customer_id","product","inception_date","expiry_date","region","sum_insured","base_premium"],
        "policies"
    )
    require_columns(exposures,
        ["policy_id","exposure_month","exposure_fraction","earned_premium"],
        "exposures"
    )
    require_columns(claims,
        ["claim_id","policy_id","loss_date","report_date","claim_type","status"],
        "claims"
    )
    require_columns(payments,
        ["claim_id","payment_date","payment_amount"],
        "payments"
    )

    # ---- Basic integrity ----
    assert_no_nulls(policies, ["policy_id","inception_date","expiry_date","product"], "policies")
    assert_no_nulls(exposures, ["policy_id","exposure_month"], "exposures")
    assert_no_nulls(claims, ["claim_id","policy_id","loss_date","report_date"], "claims")
    assert_no_nulls(payments, ["claim_id","payment_date","payment_amount"], "payments")

    # Unique keys
    if policies["policy_id"].duplicated().any():
        raise ValueError("policies: duplicate policy_id found")
    if claims["claim_id"].duplicated().any():
        raise ValueError("claims: duplicate claim_id found")

    # Date logic
    bad_policy_dates = policies[policies["expiry_date"] <= policies["inception_date"]]
    if len(bad_policy_dates) > 0:
        raise ValueError(f"policies: expiry_date must be after inception_date (bad rows={len(bad_policy_dates)})")

    bad_claim_dates = claims[claims["report_date"] < claims["loss_date"]]
    if len(bad_claim_dates) > 0:
        raise ValueError(f"claims: report_date cannot be before loss_date (bad rows={len(bad_claim_dates)})")

    # Referential integrity
    missing_policy_for_exposure = exposures.loc[~exposures["policy_id"].isin(policies["policy_id"]), "policy_id"].nunique()
    if missing_policy_for_exposure > 0:
        raise ValueError(f"exposures: {missing_policy_for_exposure} policy_id values not found in policies")

    missing_policy_for_claim = claims.loc[~claims["policy_id"].isin(policies["policy_id"]), "policy_id"].nunique()
    if missing_policy_for_claim > 0:
        raise ValueError(f"claims: {missing_policy_for_claim} policy_id values not found in policies")

    missing_claim_for_payment = payments.loc[~payments["claim_id"].isin(claims["claim_id"]), "claim_id"].nunique()
    if missing_claim_for_payment > 0:
        raise ValueError(f"payments: {missing_claim_for_payment} claim_id values not found in claims")

    # Numeric sanity
    if (policies["base_premium"] <= 0).any():
        raise ValueError("policies: base_premium must be > 0")
    if (policies["sum_insured"] <= 0).any():
        raise ValueError("policies: sum_insured must be > 0")
    if (payments["payment_amount"] < 0).any():
        raise ValueError("payments: payment_amount cannot be negative")

    print("✅ Validation PASSED")
    print(f"policies:  {len(policies):,}")
    print(f"exposures: {len(exposures):,}")
    print(f"claims:    {len(claims):,}")
    print(f"payments:  {len(payments):,}")

if __name__ == "__main__":
    main()
