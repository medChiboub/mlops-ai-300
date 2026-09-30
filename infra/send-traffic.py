"""Send test traffic to the lab 07 endpoint so model monitoring has data.

Not part of the Microsoft lab: a helper for kb/mechanics/monitoring.md.
Rows come from data/test-data/diabetes-test.csv (held-out, same distribution
as the training data). One request per row, so each is collected as a line.

  python infra/send-traffic.py baseline          # realistic rows (expect ~0 drift)
  python infra/send-traffic.py shifted           # PlasmaGlucose +40, BMI x1.3 (expect drift)
  python infra/send-traffic.py shifted --n 300 --dry-run

Needs `az login` with access to the lab resource group. The endpoint key is
read with `az` and never printed.
"""
import argparse
import collections
import csv
import json
import random
import subprocess
import urllib.error
import urllib.request

COLUMNS = ["Pregnancies", "PlasmaGlucose", "DiastolicBloodPressure", "TricepsThickness",
           "SerumInsulin", "BMI", "DiabetesPedigree", "Age"]
INTS = {"Pregnancies", "PlasmaGlucose", "DiastolicBloodPressure", "TricepsThickness",
        "SerumInsulin", "Age"}


def az(*args):
    return subprocess.run(["az", *args, "-o", "tsv"], check=True,
                          capture_output=True, text=True).stdout.strip()


def detect():
    # Same naming as .github/workflows/deploy-prod.yml
    rg = az("group", "list", "--query", "[?starts_with(name,'rg-ai300-l')].name | [0]")
    ws = "mlw-ai300-l" + rg.removeprefix("rg-ai300-l")
    endpoint = "diabetes-endpoint-" + rg.removeprefix("rg-ai300-l")[:8]
    return rg, ws, endpoint


def make_row(r, mode):
    row = {c: int(r[c]) if c in INTS else float(r[c]) for c in COLUMNS}
    if mode == "shifted":
        row["PlasmaGlucose"] += 40
        row["BMI"] = round(row["BMI"] * 1.3, 8)
    return [row[c] for c in COLUMNS]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["baseline", "shifted"])
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    rows = list(csv.DictReader(open("data/test-data/diabetes-test.csv")))
    sample = random.Random(a.seed).sample(rows, a.n)
    payloads = [{"input_data": {"columns": COLUMNS, "index": [0], "data": [make_row(r, a.mode)]}}
                for r in sample]
    if a.dry_run:
        print(json.dumps(payloads[0]))
        return

    rg, ws, endpoint = detect()
    base = ["-n", endpoint, "-g", rg, "-w", ws]
    uri = az("ml", "online-endpoint", "show", *base, "--query", "scoring_uri")
    key = az("ml", "online-endpoint", "get-credentials", *base, "--query", "primaryKey")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key,
               "azureml-model-deployment": "blue"}

    codes, preds = collections.Counter(), collections.Counter()
    for body in payloads:
        req = urllib.request.Request(uri, json.dumps(body).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                codes[resp.status] += 1
                preds[resp.read().decode()] += 1
        except urllib.error.HTTPError as e:
            codes[e.code] += 1
    print(f"{a.mode} x{a.n} → {endpoint}: status {dict(codes)}, predictions {dict(preds)}")


if __name__ == "__main__":
    main()
