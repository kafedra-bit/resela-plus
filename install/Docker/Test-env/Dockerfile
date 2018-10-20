FROM ubuntu:xenial
ADD requirements.txt /tmp/
ADD apt_requirements.txt /tmp/

RUN apt-get update
RUN apt-get -y install $(cat /tmp/apt_requirements.txt)

RUN pip3 install --upgrade pip
RUN pip3 install -r /tmp/requirements.txt

RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN npm update -g
RUN npm install -g \
    npm \
    jslint
