####################### BUILD ###
####################
#####################FROM ubuntu:16.04 as builder#####
####################
##################### Download miner
#####################ADD https://github.com/JayDDee/cpuminer-opt/archive/v3.7.10.zip /v3.7.10.zip
####################
##################### Install build components
#####################RUN apt-get update && \
#####################    apt-get install -y build-essential libssl-dev libgmp-dev libcurl4-openssl-dev libjansson-dev automake unzip && \
#####################    rm -rf /var/lib/apt/lists/* && \
####################
##################### Build cpu miner
#####################    unzip v3.7.10.zip && \
#####################	rm v3.7.10.zip && \
#####################	mv cpuminer-opt-3.7.10 cpuminer-opt && \
#####################	cd /cpuminer-opt &#& \
#####################	./build.sh
####################
####################
####################### APP ###
####################
#####################FROM ubuntu:16.04
#####################COPY --from=builder /cpuminer-opt/cpuminer .
#####################RUN apt-get update && \
#####################    apt-get install -y libcurl3 libjansson4 python3 python3-numpy && \
#####################	rm -rf /var/lib/apt/lists/* && \
#####################	chmod +x configureAndMine.sh
####################
#####################COPY configureAndMine.sh .
#####################COPY cpuminer_driver.py .
#####################COPY benchmark.py .
#####################COPY algorithms.txt .


FROM 80x86/cpuminer-multi:latest


RUN apk add python3  py3-numpy bash curl 
ARG WALLET=MTemuJQsCQsQ639nRBTDKnwJu2M4eyv9Tg
ENV WALLET $WALLET

ARG PAYMETH=LTC
ENV PAYMETH $PAYMETH

ENTRYPOINT /configureAndMine.sh

COPY configureAndMine.sh  algorithms.txt /

RUN chmod +x configureAndMine.sh

COPY cpuminer_driver.py benchmark.py /



