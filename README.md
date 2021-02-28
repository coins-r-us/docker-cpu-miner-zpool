# Autoswitching ZPOOL CPU Miner

Thisone is a 2021 fork/rewrite from the below sources

 https://github.com/Xuno/docker-cpu-miner-zpool.git  forked from https://github.com/pbutenee/docker-cpu-miner Docker image for running an autoswitching CPU miner for ZPOOL. The code is based on the cpu-miner-opt by JayDDee
https://github.com/JayDDee/cpuminer-opt

![docker-cpuminer-zpool-screenshot](./screen.jpg "live zpool profitability changing benchmark")
## Usage

You can use thefollowing environment variables:
* `WALLET`
* `WORKERNAME`
* `PAYMETH`
* `WAITTIME`
configure which wallet to mine to and to set the worker name that will be passed along. Use the '-v' to point the container to a folder where the benchmark results can be stored, for example the current folder.

`docker run --restart unless-stopped -v $(pwd)/host_files:/host_files/ --rm -it -e WALLET=MTemuJQsCQsQ639nRBTDKnwJu2M4eyv9Tg -e WAITTIME=180 -e MAXTHREADS=2  -e WORKERNAME=worker1 -e PAYMETH=LTC -v $(pwd):/host_files/ coinsrus/docker-cpu-miner-zpool`

This will first run a benchmark afther which it will start mining and it will save the `benchmarks.json` file locally so that it can be used with new versions of the container without the need to rerun the benchmarks. To force the benchmark again just remove the `benchmarks.json` file.

While running, the script will update the hash rates based on the actual hash rates of the algorithm. So small mistakes in the benchmark will be corrected while running. The optimal number of threads however is never updated and benchmark mistakes that are more than 20% will most likely not be corrected.
