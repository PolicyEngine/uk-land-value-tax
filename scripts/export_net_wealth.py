"""Export net wealth per household_id for the LVT blog analysis (interim bridge).

Imputes mortgage and consumer debt onto the enhanced FRS with the WAS-trained
QRF and writes household_id -> net_wealth (and components) to a parquet the LVT
pipeline joins on. This is a bridge until net_wealth ships in a released
policyengine-uk + dataset, after which the pipeline can request it directly.

Run from the policyengine-uk-data venv:
  uv run --no-sync python export_net_wealth.py <out.parquet>
"""
import sys
import numpy as np
import pandas as pd
from policyengine_uk import Microsimulation
from policyengine_uk.data import UKSingleYearDataset
from policyengine_uk_data.datasets.imputations.wealth import create_wealth_model
from policyengine_uk_data.storage import STORAGE_FOLDER

OUT = sys.argv[1] if len(sys.argv) > 1 else "net_wealth_by_household.csv"
# Compute on the EXACT dataset the consumer uses (household_ids must match).
DATASET = sys.argv[2] if len(sys.argv) > 2 else str(STORAGE_FOLDER / "enhanced_frs_2023_24.h5")
YEAR = 2026

model = create_wealth_model(overwrite_existing=False)
ds = UKSingleYearDataset(DATASET)
sim = Microsimulation(dataset=ds)

input_df = sim.calculate_dataframe(model.input_columns, map_to="household")
input_df["region"] = input_df["region"].replace("NORTHERN_IRELAND", "WALES")
out = model.predict(input_df)
mortgage_debt = np.clip(out["mortgage_debt"].values, 0, None)
consumer_debt = np.clip(out["consumer_debt"].values, 0, None)

total_wealth = sim.calculate("total_wealth", YEAR).values
student_loan = sim.calculate("student_loan_balance", YEAR, map_to="household").values
net_wealth = total_wealth - mortgage_debt - consumer_debt - student_loan
household_id = sim.calculate("household_id", YEAR).values

df = pd.DataFrame(
    {
        "household_id": household_id.astype(np.int64),
        "net_wealth": net_wealth,
        "mortgage_debt": mortgage_debt,
        "consumer_debt": consumer_debt,
        "student_loan_balance": student_loan,
        "total_wealth": total_wealth,
    }
)
df.to_csv(OUT, index=False)
print(f"wrote {len(df):,} households to {OUT}")
print(f"household_id sample: {sorted(df.household_id)[:5]} ... {sorted(df.household_id)[-3:]}")
print(f"net_wealth < 0 share (unweighted): {(net_wealth < 0).mean():.1%}")
