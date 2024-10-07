#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Cross-platform controller for ZPOOL CPU"""

# Example usage:
#   $ sleep 5
#   $ python3 cpuminer-driver.py WORKER WALLET PAYOUTMETHOD

#__author__ = "Ryan Young"
#__email__ = "rayoung@utexas.edu"
__license__ = "public domain"

import json
import logging
import signal
import socket
import sys
import urllib.error
import urllib.request
from time import sleep, time
import os.path
import os, errno
import subprocess
import threading
import numpy as np


STOREDIR=os.environ.get('HOME', '/etc')+ "/.zpool"
if os.geteuid() != 0:
    STOREDIR=os.environ.get('HOME', '/tmp')+ "/.zpool"
else:
    STOREDIR="/etc/.zpool"
try:
    os.makedirs(STOREDIR)
except OSError as e:
    if e.errno != errno.EEXIST:
        print("could not create config dir")
        raise

WALLET  =  os.environ.get('WALLET',  'XoVozBiwEveoLk87JAZHHR3bX1TzH2geVs') 
WORKER  =  os.environ.get('WORKER',  'worker1') 
PAYMETH =  os.environ.get('PAYMETH', 'DASH') 
WAITTIME = int(os.environ.get('WAITTIME', 240))
## the factor for how long the thingy will stay on on a a successfull algo is calculated with WAITTIME*WAIT_FURTER
WAIT_FURTHER = 1.5

REGION = os.environ.get('REGION', 'eu')  # eu, usa, hk, jp, in, br
BENCHMARKS_FILE = STOREDIR+'/benchmarks.json'
MAXTHREADS=999

PROFIT_SWITCH_THRESHOLD = 0.01
UPDATE_INTERVAL = 42

# artificailly increase profit if it hasn't been updated ever or in the past 24h
PROFIT_INCREASE_TIME = 24 * 60 * 60    # s

# number of hashes needed to compute the actual measured hash rate
NOF_HASHES_BEFORE_UPDATE = 10000

EXCAVATOR_TIMEOUT = 10
NICEHASH_TIMEOUT = 20

## time after a failed algo is re-considered (should be n(algos)*WAITTIME + 1   )
RESTORETIME=2350

class MinerThread(threading.Thread):
    def __init__(self, cmd, nof_threads):
        self.cmd = cmd
        self.hash_sum = np.zeros((nof_threads,))
        self.nof_hashes = np.zeros((nof_threads,))

        self.fail_count = 0
        self.last_fail_time = 0
        self.start_time = time()
        self.time_running=0
        self.shares_found=0
        self.last_share=0
        self.auth_fail='no'
        
        self.process = None
        threading.Thread.__init__(self)

    def run(self):
#       self.shares_found=0
#       self.time_running=0
        self.start_time = time()
        with subprocess.Popen(self.cmd, stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) as self.process:
            for line in self.process.stdout:
                self.time_running= time() - self.start_time
                if 'yay' in line or 'Accepted' in line or 'yes!' in line:
                    self.shares_found  = self.shares_found + 1
                    self.last_share=time()
                if 'Stratum authentication failed' in line:
                        self.auth_fail='fail'
               ##log but show share time and count after cpu line
                #if 'CPU #' in line:
                ## only first cpu (spam)
                if 'CPU #' in line:
                    if 'CPU #0' in line:
                        laststring="never"
                        if self.last_share != 0:
                            laststring=str(int(time()-self.last_share)) + ' s ago '
                        logging.info(str( line[ : line.rfind('\n') ]) + '\trunning since: ' + '{:.3f}'.format(self.time_running) + 's\t| shares found: ' + str(self.shares_found) + '\t| last: ' + laststring )
                else:
                    logging.info(line[ : line.rfind('\n')])

                if 'CPU #' in line:
                    # find hash rate
                    line = line[ : line.rfind('H/s')]

                    #logging.info('parsing:')
                    rate=line[line.rfind(': ') + 2 : ]
                    #rate=rate.replace(" ","")
                    #logging.info(rate)
                    #rate=rate + '.0'
                    ##parser expects "1111 k" OR "1234 M" OR "1.23 G"
                    hash_rate = _convert_to_float(rate)


                    #hash_rate = _convert_to_float(line[line.rfind(', ') + 2 : ])

                    # find nof hashes
                    line = line[ : line.rfind('H, ')]
                    nof_hashes = _convert_to_float(line[line[ : -2].rfind(': ') + 2 : ])
                    # find core number
                    core_nr = int(line[line.rfind('#') + 1 : line.rfind(': ')])
                    # update
                    self.hash_sum[core_nr] += hash_rate * nof_hashes
                    self.nof_hashes[core_nr] += nof_hashes
                elif 'Net hash rate (est)' in line:
                    line = line[ : line.rfind('H/s')]
                    #logging.info('parsing:')
                    rate=line[line.rfind(') ') + 2 : ]
                    print("cpuminer_opt_rate:"+rate)
                    hash_rate = _convert_to_float(rate)
                    
                #'Net hash rate (est) 76.82 Mh/s'
                elif 'stratum_recv_line failed' in line:
                    if time() - self.last_fail_time > 20:
                        # too long ago so reset
                        self.fail_count = 1
                    else:
                        self.fail_count += 1
                    self.last_fail_time = time()


    def join(self):
        self.process.terminate()
        super().join()


'''
Assumes output is of the form '45.3 ' or '456.9 M'
'''
def _convert_to_float(output):
    hash_rate = float(output[ : output.rfind(' ')])
    if output[-1] == 'k':
        hash_rate *= 1000
    elif output[-1] == 'M':
        hash_rate *= 1000000
    elif output[-1] == 'G':
        hash_rate *= 1000000000
    elif output[-1] != ' ':
        raise(NotImplementedError('The following unit is not yet supported: ' + output[-1] + ' or there is something wrong with the output: ' + output))
    return hash_rate

from urllib.request import Request, urlopen

def nicehash_multialgo_info():
    """Retrieves pay rates and connection ports for every algorithm from the ZPOOL API."""
    req = Request('https://www.zpool.ca/api/status',headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req,None,NICEHASH_TIMEOUT)
    query = json.loads(response.read().decode('ascii'))
    paying = {}
    ports = {}
    for akey in dict.keys(query):
        algorithm=query[akey]
        name = algorithm['name']
        paying[name] = float(algorithm['estimate_current'])
        ports[name] = int(algorithm['port'])
    return paying, ports

'''
Compute the expected revenue for each algorithm.

For algorithms that haven't been used before or that haven't been used in the past 24h the hash rate is increased by 20%.
This is to increase the likelyhood that an almost as profitable algorithm is selected so that the hash rates will be updated to the actual hash rate.
'''
def nicehash_mbtc_per_day(benchmarks, paying):
    """Calculates the BTC/day amount for every algorithm.
    device -- excavator device id for benchmarks
    paying -- algorithm pay information from ZPOOL
    """
    revenue = {}
    RESTORETIME=int(WAITTIME) * len(benchmarks)
    for algorithm in benchmarks:
        # ignore revenue if the algorithm fails a lot
        """logging.info('set restoretime to ' + str(RESTORETIME) )"""
        if 'last_fail_time' in benchmarks[algorithm] and time() - benchmarks[algorithm]['last_fail_time'] < RESTORETIME:
            revenue[algorithm] = 0
            continue

        # compute expected revenue
        if algorithm in paying:
            revenue[algorithm] = compute_revenue(paying[algorithm], benchmarks[algorithm]['hash_rate'])
		    
            # increase revenue by 20% if the algortihm hasn't been updated ever or if it has been more than 24h
            if 'last_updated' not in benchmarks[algorithm]:
                revenue[algorithm] *= 1.2
            elif time() - benchmarks[algorithm]['last_updated'] > PROFIT_INCREASE_TIME:
                nof_days_since_update = (time() - benchmarks[algorithm]['last_updated']) / PROFIT_INCREASE_TIME
                revenue_multiplier = 1 + nof_days_since_update * 2 / 100
                revenue[algorithm] *= min(1.2, revenue_multiplier)
        else:
            revenue[algorithm]=0
    return revenue

def compute_revenue(paying, hash_rate):
    return paying * hash_rate * (24*3600) * 1e-11

def main():
    """Main program."""
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)

    ## benchmark if necessary
    #print("loading "+BENCHMARKS_FILE)
    #if not os.path.isfile(BENCHMARKS_FILE):
    #    import benchmark
    #    paying, ports = nicehash_multialgo_info()
    #    benchmark.run(paying.keys())
    ## ALWAYS BENCHMARK
    import benchmark
    paying, ports = nicehash_multialgo_info()
    benchmark.run(paying.keys(),int(MAXTHREADS))
    
    # load benchmarks
    benchmarks = json.load(open(BENCHMARKS_FILE))
    RESTORETIME=int(WAITTIME) * len(benchmarks)

    running_algorithm = None
    cpuminer_thread = None

    def profitinfo():
        printpayrates = nicehash_mbtc_per_day(benchmarks, paying)
        AllRatesEmpty=True
        for key, value in dict(printpayrates).items():
            if value != 0:
                AllRatesEmpty=False
        if AllRatesEmpty == True:
            logging.info('all profits on 0 ..resetting last_fail_time')
            for key, value in dict(benchmarks).items():
                benchmarks[key]['last_fail_time']=0
        logging.info('# $$$ ##########################################')
        logging.info('# $$$ #:    profit table: (ascending) ## $$$  :#')
        logging.info('# $$$ #----------------------------------------#')
        printpayrates = nicehash_mbtc_per_day(benchmarks, paying)
        for key, value in dict(printpayrates).items():
            if value == 0:
                del printpayrates[key]
        #logging.info(printpayrates)
        for key, value in sorted(dict(printpayrates).items(), key=lambda x: x[1], reverse=False):
            logging.info('# $$$ # ¢ = ' + key.rjust(10 , ' ') + ':\t{:0.16f}'.format(value)  + '   #' )
        logging.info('# $$$ ##########################################')


    while True:
        try:
            paying, ports = nicehash_multialgo_info()

        except urllib.error.URLError as err:
            logging.warning('failed to retrieve ZPOOL stats: %s' % err.reason)
        except urllib.error.HTTPError as err:
            logging.warning('server error retrieving ZPOOL stats: %s %s'
                            % (err.code, err.reason))
        except socket.timeout:
            logging.warning('failed to retrieve ZPOOL stats: timed out')
        except (json.decoder.JSONDecodeError, KeyError):
            logging.warning('failed to parse ZPOOL stats')
        else:
            # Compute payout and get best algorithm
            payrates = nicehash_mbtc_per_day(benchmarks, paying)
            RESTORETIME=int(WAITTIME) * len(payrates)

            best_algorithm = max(payrates.keys(), key=lambda algo: payrates[algo])
            if cpuminer_thread != None:
                cpuminer_thread.time_running=time() - cpuminer_thread.start_time
            # Update hash rate if enough accepted hashes have been seen
                if np.min(cpuminer_thread.nof_hashes) > NOF_HASHES_BEFORE_UPDATE:
                    benchmarks[running_algorithm]['hash_rate'] = np.sum(cpuminer_thread.hash_sum / cpuminer_thread.nof_hashes)
                    benchmarks[running_algorithm]['last_updated'] = time()
                    json.dump(benchmarks, open(BENCHMARKS_FILE, 'w'))
                    logging.info('UPDATED HASH RATE OF ' + running_algorithm + ' TO: ' + str(benchmarks[running_algorithm]['hash_rate']))
            # Remove payrate if the algorithm is not working
                if cpuminer_thread.fail_count > 5 and time() - cpuminer_thread.last_fail_time < 60:
                    payrates[running_algorithm] = 0
                    benchmarks[running_algorithm]['last_fail_time'] = cpuminer_thread.last_fail_time
                    json.dump(benchmarks, open(BENCHMARKS_FILE, 'w'))
                    logging.error(running_algorithm + ' FAILS MORE THAN ALLOWED SO IGNORING IT FOR NOW!')
            ### zero payrate if we get no shares for WAITTIME
                #logging.info('checking ' + str(WAITTIME) + 'against' + cpuminer_thread.time_running + ' and sharecount ' + cpuminer_thread.shares_found
                reset_payrate=False
                if cpuminer_thread.time_running > int(WAITTIME) and cpuminer_thread.shares_found == 0:
                    reset_payrate=True
                ## difficulty may change and we want to keep track when we find no further shares but found at least one
                if cpuminer_thread.time_running > int(WAITTIME) and cpuminer_thread.shares_found > 0 and ( (time() - cpuminer_thread.last_share ) > (int(WAITTIME)* WAIT_FURTHER) ):
                    reset_payrate=True
                if reset_payrate:
                    payrates[running_algorithm] = 0
                    benchmarks[running_algorithm]['last_fail_time'] = time()
                    json.dump(benchmarks, open(BENCHMARKS_FILE, 'w'))
                    logging.error(running_algorithm + ' HAS NO SHARES after ' + '{:6.3f}'.format(cpuminer_thread.time_running) + ' .. DISABLING FOR' + str(RESTORETIME) + ' seconds' )

            killswitch='no'
            algoswitch=False
            payrateswitch=False
            if cpuminer_thread != None and cpuminer_thread.auth_fail == 'fail':
                algoswitch=True
                logging.info("auth_fail detected")
                killswitch='engaged'
            # Switch algorithm if it's worth while
            if running_algorithm == None or running_algorithm != best_algorithm:
                algoswitch=True
            if running_algorithm != None:
                if payrates[running_algorithm] == 0:
                    payrateswitch=True
                    logging.info("switching due to payrate 0")
                    killswitch='engaged'
                    #profitinfo()
                else:
                    if payrates[best_algorithm]/payrates[running_algorithm] >= 1.0 + PROFIT_SWITCH_THRESHOLD:
                        payrateswitch=True
                        logging.info("switching due to profitability from "+running_algorithm+" to "+best_algorithm)
                        killswitch='engaged'
                        profitinfo()
            if algoswitch == True or payrateswitch == True:
                killswitch='engaged'
            if  killswitch == 'engaged':
                # kill previous miner
                if cpuminer_thread != None:
                    cpuminer_thread.join()
                    logging.info('killswitch-killed process running ' + running_algorithm)
                    #running_algorithm=None
                    cpuminer_thread = None
                    #profitinfo()

### boot thread
            #re-Calculate rates
            payrates = nicehash_mbtc_per_day(benchmarks, paying)
            best_algorithm = max(payrates.keys(), key=lambda algo: payrates[algo])
            best_rate=0
            best_algo_aux=None
            for key, value in sorted(dict(payrates).items(), key=lambda x: x[1], reverse=False):
                if(value > best_rate):
                    best_algo_aux=key
            logging.info('best_algo (payrates): ' + str(best_algorithm) + ' | best_algo aux: ' + str(best_algo_aux) )
            if cpuminer_thread == None or killswitch == 'engaged':
                profitinfo()
                # start miner
                cpucount=benchmarks[best_algorithm]['nof_threads']
                if int(MAXTHREADS) > 0 and int(MAXTHREADS) < benchmarks[best_algorithm]['nof_threads']:
                    cpucount=int(MAXTHREADS)
                minerbin="cpuminer"
                #STOREDIR+"/opt_"+best_algorithm
                if os.path.isfile(STOREDIR+"/opt_"+best_algorithm):
                    with open(STOREDIR+"/opt_"+best_algorithm, 'r') as file:
                        minerbin = file.read().replace('\n', '')
                minerobj=[minerbin, '-u', WALLET , '-p', WORKER + ',c='+ PAYMETH,
                    '-o', 'stratum+tcp://' + best_algorithm + '.' + 'mine.zpool.ca:' + str(ports[best_algorithm]),
                    '-a', best_algorithm, "--api-bind" , "127.0.0.1:4049" ,'-t', str(cpucount)]
                if "MINER_SOCKS" in os.environ:
                    minerobj.append("--proxy")
                    minerobj.append(os.environ.get("MINER_SOCKS"))
                logging.info('starting mining using ' + best_algorithm + ' using ' + str(cpucount) + ' threads')
                #cpuminer_thread = MinerThread(['./cpuminer', '-u', WALLET , '-p', WORKER + ',c=BTC',
                #logging.info(minerobj)
                cpuminer_thread = MinerThread(minerobj, cpucount)
                cpuminer_thread.start()
                running_algorithm = best_algorithm
                killswitch='no'

        def printHashRateAndPayRate():
            if cpuminer_thread != None:
              if running_algorithm is not None:
                cpuminer_thread.time_running=time() - cpuminer_thread.start_time
                logline=running_algorithm + ' FOUND ' + str(cpuminer_thread.shares_found) +' shares after ' + '{:6.3f}'.format(time() - cpuminer_thread.start_time) + ' s '
                if cpuminer_thread.shares_found == 0:
                    logline=logline + '.. disabling(temporary) if no shares found within ' + '{:6.3f}'.format(int(WAITTIME) - ( time() - cpuminer_thread.start_time ) ) + ' sec ..'
                    if (int(WAITTIME) - ( time() - cpuminer_thread.start_time ) ) < 1 :
                        logline=logline + ' -> Killing from payrate calc'
                        cpuminer_thread.join()
                if cpuminer_thread.time_running > 1:
                    logging.info(logline)
                if (np.sum(cpuminer_thread.nof_hashes) > 0) :
                    hash_rate = np.sum(cpuminer_thread.hash_sum / cpuminer_thread.nof_hashes)
                    #logging.info('Current average hashrate is %f H/s' % hash_rate)
                    current_payrate = compute_revenue(paying[running_algorithm], hash_rate)
                    loginfo='at avg. cur. hashrate of ' + '{:.3f}'.format(hash_rate) + ' H/s'
                    expectinfo= running_algorithm + ' is currently expected to generate %f mBTC/day or %f mBTC/month '   % (current_payrate, current_payrate * 365.25 / 12 )
                    longloginfo= expectinfo + loginfo
                    logging.info(longloginfo)

        printHashRateAndPayRate()
        sleep(UPDATE_INTERVAL / 2)
        if cpuminer_thread.shares_found != 0:
            printHashRateAndPayRate()
            sleep(UPDATE_INTERVAL / 2)

if __name__ == '__main__':

    if sys.argv[0] == 'cpuminer_driver.py':
       sys.argv.pop(0)
    print( ' have ' + str(len(sys.argv))  +  ' arguments :'  )
    print(sys.argv)
    if len(sys.argv) > 0:
        WALLET = sys.argv[0]
        os.environ['WALLET'] = str(sys.argv[0])
    if len(sys.argv) > 1:
        PAYMETH = sys.argv[1]
        os.environ['PAYMETH'] = str(sys.argv[1])
    if len(sys.argv) > 2:
        WORKER = sys.argv[2]
        os.environ['WORKER'] = str(sys.argv[2])
    if len(sys.argv) > 3:
        MAXTHREADS = sys.argv[3]
        os.environ['MAXTHREADS'] = str(sys.argv[3])
    if len(sys.argv) > 4:
        WAITTIME = int(sys.argv[4])
        os.environ['WAITTIME'] = str(sys.argv[4])
    main()
