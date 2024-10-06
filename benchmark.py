import multiprocessing
import subprocess
import json
import logging
import cpuminer_driver
import os

def run(nicehash_algorithms):
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)

    logging.info('BENCHMARKING...')

    ## Read the list of algorithms the miner supports ##

    f = open('algorithms.txt')
    miner_algorithms = f.readlines()

    for i in range(len(miner_algorithms)):
        algorithm = miner_algorithms[i]
        end = algorithm.find('\n')
        if algorithm.find(' ') > 0:
            end = min(end, algorithm.find(' '))
        if end > 0:
            miner_algorithms[i] = algorithm[: end]


    ## Do the actual benchmark and find the optimal number of threads

    benchmarked_algorithms = {}
    #max_nof_threads = (multiprocessing.cpu_count()-2)

    max_nof_threads = int(multiprocessing.cpu_count()/2+1)
    min_threads=1
    if multiprocessing.cpu_count() > 1:
         min_threads=2
    counter = 0
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms:
            counter=counter+1
    logging.info('testing '+str(counter)+" matching algos")
    #min_threads=int(multiprocessing.cpu_count()/2)
    benchmark_str = 'Benchmark: '
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms:
          algofile=cpuminer_driver.STOREDIR+"/"+algorithm+".json"
          if not os.path.isfile(algofile):
#            bash_command = './cpuminer --benchmark --time-limit=13 -a ' + algorithm
            bash_command = 'cpuminer --benchmark --time-limit=42 -a ' + algorithm
            optimal_nof_threads = 0
            optimal_hash_rate = 0
            logging.info('Benchmarking ' + algorithm + ' ...')
#            for t in range(1, max_nof_threads + 1):
##only benchmark from 1/2(see min_threads) -> (ncores-1)
            #for t in range(min_threads, max_nof_threads,2 ):
            for t in [min_threads,int(multiprocessing.cpu_count()/2)]:
                logging.info('with ' + str(t) + ' thread(s)')
                output = subprocess.check_output(['bash', '-c', bash_command + ' -t ' + str(t)]).decode("utf-8")
                output = output[output.rfind(benchmark_str) + len(benchmark_str) : ]
                output = output[ : output.find('H/s')]
                hash_rate = cpuminer_driver._convert_to_float(output)
                if hash_rate > optimal_hash_rate:
                    optimal_hash_rate = hash_rate
                    optimal_nof_threads = t
            if optimal_hash_rate > 0:
                benchmarked_algorithms[algorithm] = {
                    'hash_rate' : optimal_hash_rate,
                    'nof_threads' : optimal_nof_threads
                }
                logging.info('Benchmarked ' + algorithm + ' with selected parameters: ' + str(benchmarked_algorithms[algorithm]))
                #json.dump(benchmarked_algorithms, open(cpuminer_driver.BENCHMARKS_FILE, 'w'),indent=4)
                json.dump(benchmarked_algorithms, open(algofile, 'w'),indent=4)
                

            else:
                logging.info('algorithm ' + algorithm + ' not added because the hash rate was 0.')

    #json.dump(benchmarked_algorithms, open(cpuminer_driver.BENCHMARKS_FILE, 'w'))
    useable_algo=[]
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms:
          algofile=cpuminer_driver.STOREDIR+"/"+algorithm+".json"
          if os.path.isfile(algofile):
              useable_algo[algorithm]=json.load(open(algofile))
    benchmarked_algorithms=useable_algo
    ## logging.info the results
    
    logging.info('Final results: ' + str(benchmarked_algorithms))
    logging.info('Done! The results are stored in benchmarks.json')


if __name__ == '__main__':
    paying, ports = cpuminer_driver.nicehash_multialgo_info()
    run(paying.keys())
