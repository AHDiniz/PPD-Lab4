python3 ./miner/main.py &
for run in {1..9};
    do python3 ./miner/main.py &>/dev/null &
done