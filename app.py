#!/usr/bin/env python3
import argparse
import json
from rail_network import RailNetwork

def to_rows(itineraries, travel_class):
    return [it.to_row(travel_class=travel_class) for it in itineraries]

def print_table(rows):
    if not rows:
        print("No results.")
        return
    cols = ["origin","destination","depart","arrive","stops","trip_duration(min)","transfer_time(min)","total_price_second","legs"]
    if any("total_price_first" in r for r in rows):
        cols = ["origin","destination","depart","arrive","stops","trip_duration(min)","transfer_time(min)","total_price_first","legs"]
    widths = {c: max(len(c), *(len(str(r.get(c,""))) for r in rows)) for c in cols}
    sep = " | "
    print(sep.join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-"*widths[c] for c in cols))
    for r in rows:
        print(sep.join(str(r.get(c,"")).ljust(widths[c]) for c in cols))

def main():
    p = argparse.ArgumentParser(description="Rail Network Search CLI")
    p.add_argument("--csv", required=True)
    p.add_argument("--from", dest="dep")
    p.add_argument("--to", dest="arr")
    p.add_argument("--train-type", dest="train_type")
    p.add_argument("--day", dest="day_contains")
    p.add_argument("--max-stops", type=int, default=2)
    p.add_argument("--min-transfer", type=int, default=15)
    p.add_argument("--class", dest="travel_class", default="second")
    p.add_argument("--sort", dest="sort_by", default="duration", choices=["duration","price"])
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--format", dest="fmt", default="json", choices=["json","table","csv"], help="Output format")
    p.add_argument("--out", dest="out_path", help="Write output to file (CSV or JSONL)")

    args = p.parse_args()

    rn = RailNetwork.from_csv(args.csv)
    its = rn.search(
        departure_city=args.dep,
        arrival_city=args.arr,
        train_type=args.train_type,
        day_contains=args.day_contains,
        max_stops=args.max_stops,
        min_transfer_minutes=args.min_transfer,
        travel_class=args.travel_class,
        sort_by=args.sort_by,
    )

    rows = to_rows(its, args.travel_class)
    if args.limit > 0:
        rows = rows[:args.limit]

    if args.out_path:
        if args.fmt == "csv":
            import csv
            if rows:
                cols = sorted({k for r in rows for k in r.keys()})
                with open(args.out_path,"w",newline="",encoding="utf-8") as f:
                    w = csv.DictWriter(f,fieldnames=cols)
                    w.writeheader()
                    for r in rows: w.writerow(r)
            print(f"Wrote CSV: {args.out_path}")
        elif args.fmt == "json":
            with open(args.out_path,"w",encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r,ensure_ascii=False)+"\n")
            print(f"Wrote JSONL: {args.out_path}")
        return

    if args.fmt == "json":
        for r in rows: print(json.dumps(r,ensure_ascii=False))
    elif args.fmt == "table":
        print_table(rows)
    else:
        if rows:
            cols = sorted({k for r in rows for k in r.keys()})
            print(",".join(cols))
            for r in rows:
                print(",".join(str(r.get(c,"")) for c in cols))

if __name__ == "__main__":
    main()
