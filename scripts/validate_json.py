import json
from pathlib import Path
from jsonschema import validate

BASE = Path(__file__).resolve().parents[1]
intake_schema = json.loads((BASE / "schemas" / "intake.schema.json").read_text(encoding="utf-8"))
output_schema = json.loads((BASE / "schemas" / "output.schema.json").read_text(encoding="utf-8"))

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--schema", choices=["intake","output"], required=True)
    p.add_argument("--file", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    schema = intake_schema if args.schema == "intake" else output_schema
    validate(instance=data, schema=schema)
    print("OK")

if __name__ == "__main__":
    main()
