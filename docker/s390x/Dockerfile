FROM s390x/debian:buster

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -q -y

RUN apt-get install -q -y git \
                          python3 \
                          python3-astropy \
                          python3-lz4 \
                          python3-numpy \
                          python3-venv \
                          python3-wheel

WORKDIR /root

RUN python3 -m venv --system-site-packages asdf-env

RUN . /root/asdf-env/bin/activate && \
    pip3 install --upgrade pip setuptools gwcs==0.9.1 pytest==5.4.3 pytest-doctestplus==0.8.0

RUN git clone https://github.com/asdf-format/asdf.git

WORKDIR /root/asdf

RUN . /root/asdf-env/bin/activate &&\
    git submodule init && \
    git submodule update && \
    pip3 install -e .[all,tests]

RUN echo ". /root/asdf-env/bin/activate" >> /root/.bashrc

CMD [ "/bin/bash" ]
