# Rail Network Search — Iteration 1

Implements the SOEN 342 Iteration 1 requirements.
here I implemeted the build of a small software system ,
See `app.py` for CLI and `rail_network.py` for the engine.
Handles indirect connections:

If there’s no direct route between two cities, find 1-stop and 2-stop routes.

Include transfer time between train , If there’s no direct A → C route:

Find any A → B → C (1-stop) or A → B → D → C (2-stops) combinations. 
What I did : 

A working software system (in any language) that:

Loads the data.

Lets the user search.

Displays results (direct + indirect).

Allows sorting.


Examples:

python3 app.py --csv eu_rail_network.csv --from "Paris" --to "Berlin" --sort duration --class second --max-stops 2 --min-transfer 20

python3 app.py --csv eu_rail_network.csv --from "Paris" --to "Berlin" --match contains --max-stops 2 --format table


```
