import multiprocessing
import subprocess
import json
import logging
import cpuminer_driver
import os

def run(nicehash_algorithms,maxthreads):
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)

    logging.info('BENCHMARKING...')

    ## Read the list of algorithms the miner supports ##

    f = open('algorithms.txt')
    miner_algorithms = f.readlines()

    f = open('algorithms_opt.txt')
    opt_algorithms = f.readlines()

    for i in range(len(miner_algorithms)):
        algorithm = miner_algorithms[i]
        end = algorithm.find('\n')
        if algorithm.find(' ') > 0:
            end = min(end, algorithm.find(' '))
        if end > 0:
            miner_algorithms[i] = algorithm[: end]

    for i in range(len(opt_algorithms)):
        algorithm = opt_algorithms[i]
        end = algorithm.find('\n')
        if algorithm.find(' ') > 0:
            end = min(end, algorithm.find(' '))
        if end > 0:
            opt_algorithms[i] = algorithm[: end]

    benchtime=23
    ## Do the actual benchmark and find the optimal number of threads

    benchmarked_algorithms = {}
    #max_nof_threads = (multiprocessing.cpu_count()-2)
    if maxthreads > multiprocessing.cpu_count():
        maxthreads=multiprocessing.cpu_count()
    max_nof_threads = int(multiprocessing.cpu_count()/2+1)
    print("maxthreads"+str(maxthreads))
    if maxthreads > max_nof_threads or maxthreads < max_nof_threads:
        max_nof_threads=maxthreads
    print("max_nof_threads"+str(max_nof_threads))    
    min_threads=1
    if multiprocessing.cpu_count() > 1:
         min_threads=2
    counter = 0
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms or algorithm in opt_algorithms :
            counter=counter+1
    logging.info('testing '+str(counter)+" matching algos")
    #min_threads=int(multiprocessing.cpu_count()/2)
    benchmark_str = 'Benchmark: '
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms or algorithm in opt_algorithms :
          algofile=cpuminer_driver.STOREDIR+"/"+algorithm+".json"
          if not os.path.isfile(algofile):
#            bash_command = './cpuminer --benchmark --time-limit=13 -a ' + algorithm
            bash_command = 'cpuminer --benchmark --time-limit='+str(benchtime)+' -a ' + algorithm
            if not algorithm in miner_algorithms and algorithm in opt_algorithms:
                f = open(cpuminer_driver.STOREDIR+"/opt_"+algorithm, "w")
                f.write("cpuminer-opt")
                f.close()
                bash_command = 'cpuminer-opt --benchmark --time-limit='+str(benchtime)+' -a ' + algorithm
            optimal_nof_threads = 0
            optimal_hash_rate = 0
#            for t in range(1, max_nof_threads + 1):
##only benchmark from 1/2(see min_threads) -> (ncores-1)
            #for t in range(min_threads, max_nof_threads,2 ):
            myrange=[min_threads]
            threadstep=min_threads*2
            while threadstep < max_nof_threads :
                 myrange.append(threadstep)
                 threadstep=threadstep*2
                 
            if (threadstep/2) < max_nof_threads:
                myrange.append(max_nof_threads)
            #for t in [min_threads,int(multiprocessing.cpu_count()/2)]:
            logging.info('Benchmarking ' + algorithm + ' ... steps'+json.dumps(myrange))
            for t in myrange:
                logging.info('with ' + str(t) + ' thread(s)')
                aoutput=""
                try:
					
                    aoutput = subprocess.check_output(['bash', '-c', bash_command + ' -t ' + str(t)]).decode("utf-8")
                    logging.info(algorithm+"→1")
                    logging.info(algorithm+"→2")
                    if "Benchmark: 0.00 H/s" in aoutput or "Benchmark: 0.0 H/s" in aoutput:
                        logging.info(algorithm+"→3a1")
                        ## catch e.g. qubit errors when there are single cpu results but the sum is wrongly shown as 0
                        combined_rate=0
                        #for thr_id in range(0,t-1):
                        #    logging.info(algorithm+"→3a2.1")
                        #    searchstr="CPU #"+thr_id+": "
                        #    if searchstr in aoutput:
                        #        logging.info(algorithm+"→3a2.2")
                        #        searchouta= aoutput[aoutput.rfind(searchstr) + len(searchstr) : ]
                        #        searchoutb= searchouta[ : searchouta.find('H/s')]
                        #        single_rate=cpuminer_driver._convert_to_float(searchoutb)
                        #        if single_rate >0:
                        #            combined_rate=single_rate+combined_rate
                        #    else:
                        #        logging.info("no result for CPU #"+thr_id)
                        logging.info(algorithm+"→3a2.1")
                        cpures= [0] * t
                        logging.info(algorithm+"→3a2.2")
                        cpucount=1
                        for line in aoutput.split('\n'):
                            if "CPU #" in line:
                                print(line)
                                searchstr="CPU #"
                                searchouta= line[line.rfind(searchstr) + len(searchstr) : ]
                                #cpunumres=searchouta.split(" ")[0]
                                #print("srch cpunum in:"+searchouta)
                                cpunum=searchouta.split(":")[0]
                                #print("cpu:"+str(cpunum))
                                targetstring=searchouta.split(":")[1]
                                cpustr= targetstring[ : targetstring.find('H/s')]
                                cpustr=cpustr.strip()
                                cpuid=int(cpunum)+1
                                if cpucount < cpuid :
                                    cpucount=cpuid
                                #print(cpustr)
                                single_rate=cpuminer_driver._convert_to_float(cpustr)
                                print("cpu"+cpunum+" rate: "+str(single_rate))
                                cpures[int(cpunum)]=single_rate
                        print(cpures)
                        combined_rate=sum(cpures)
                        
                        logging.info(algorithm+"→3a3")
                        hash_rate=0
                        if combined_rate>0:
                            hash_rate=combined_rate
                        logging.info("corrected sum for "+algorithm+" used , res: "+str(combined_rate))
                        if hash_rate > optimal_hash_rate:
                            optimal_hash_rate = hash_rate
                            optimal_nof_threads = cpucount
                        if hash_rate == 0:
                           logging.info(aoutput)
                    else:
                        if "Benchmark:" in aoutput:
                            logging.info(algorithm+"→3b1")
                            boutput = aoutput[aoutput.rfind(benchmark_str) + len(benchmark_str) : ]
                            output = boutput[ : boutput.find('H/s')]
                            logging.info(algorithm+"→3b2")
                            print(output)
                            hash_rate = cpuminer_driver._convert_to_float(output)
                            #print(hash_rate)
                            logging.info(algorithm+"→3b3")
                            if hash_rate > optimal_hash_rate:
                                optimal_hash_rate = hash_rate
                                optimal_nof_threads = t
                            logging.info(algorithm+"→3b4")
                            if hash_rate == 0:
                               logging.info(aoutput)
                        else:
                            logging.info("failed finding search string")
                    #logging.info(algorithm+"→DONE_RATE_DETECT")
                    #print(hash_rate)
                    #logging.info("rate returned: "+int(hash_rate))


                except:
                    output=""
                    hash_rate=0
                    try:
                        logging.info("FAILED 2 BENCH:"+algorithm)
                        logging.info(aoutput)
                    except:
                        foo="bar"
            if optimal_hash_rate > 0:
                benchmarked_algorithms[algorithm] = {
                    'hash_rate' : optimal_hash_rate,
                    'nof_threads' : optimal_nof_threads
                }
                logging.info('Benchmarked ' + algorithm + ' with selected parameters: ' + str(benchmarked_algorithms[algorithm]))
                #json.dump(benchmarked_algorithms, open(cpuminer_driver.BENCHMARKS_FILE, 'w'),indent=4)
                json.dump(benchmarked_algorithms[algorithm], open(algofile, 'w'),indent=4)
                

            else:
                logging.info('algorithm ' + algorithm + ' not added because the hash rate was 0 ')

    useable_algo={}
    for algorithm in nicehash_algorithms:
        if algorithm in miner_algorithms or algorithm in opt_algorithms :
          algofile=cpuminer_driver.STOREDIR+"/"+algorithm+".json"
          if os.path.isfile(algofile):
              useable_algo[algorithm]=json.load(open(algofile))
              
    benchmarked_algorithms=useable_algo
    ## logging.info the results
    
    logging.info('Final results: ')
    logging.info(json.dumps(benchmarked_algorithms,indent=4))
    json.dump(benchmarked_algorithms, open(cpuminer_driver.BENCHMARKS_FILE, 'w'))


if __name__ == '__main__':
    paying, ports = cpuminer_driver.nicehash_multialgo_info()
    run(paying.keys())
