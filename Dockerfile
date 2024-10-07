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
#####################     \
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


#FROM 80x86/cpuminer-multi:latest
#RUN apk add python3  py3-numpy bash curl 
FROM ubuntu:22.04 as builder
RUN apt-get update && apt-get -y --no-install-recommends install git wget bash build-essential libssl-dev zlib1g-dev libgmp-dev libcurl4-openssl-dev libjansson-dev libpthread-stubs0-dev automake &&  apt-get install -y --reinstall ca-certificates && rm -rf /var/lib/apt/lists/* && apt-get clean all && (mkdir -p /usr/local/share/ca-certificates/cacert.org || true) &&  wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt && update-ca-certificates
RUN git clone https://github.com/JayDDee/cpuminer-opt.git /cpuminer-opt && cd /cpuminer-opt && bash autogen.sh && ./configure --with-crypto --with-curl && bash -c 'make -j $(nproc)'
RUN git clone https://github.com/tpruvot/cpuminer-multi.git /cpuminer  && cd /cpuminer && bash autogen.sh && ./configure --with-crypto --with-curl && bash -c 'make -j $(nproc)'

FROM ubuntu:22.04
RUN apt-get update && apt-get install -y libcurl4 libjansson4 python3 python3-numpy && 	rm -rf /var/lib/apt/lists/
COPY --from=builder /cpuminer-opt/cpuminer /usr/bin/cpuminer-opt
COPY --from=builder /cpuminer/cpuminer /usr/bin/cpuminer

ARG WALLET=MTemuJQsCQsQ639nRBTDKnwJu2M4eyv9Tg
ENV WALLET $WALLET

ARG PAYMETH=LTC
ENV PAYMETH $PAYMETH

ENTRYPOINT /configureAndMine.sh

COPY configureAndMine.sh algorithms.txt algorithms_opt.txt cpuminer_driver.py benchmark.py /

RUN chmod +x configureAndMine.sh

