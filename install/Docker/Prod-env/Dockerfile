FROM ubuntu:xenial
ADD requirements.txt /tmp/
ADD apt_requirements.txt /tmp/
ADD application.ini /root/
ADD Docker/init_container.sh /root/

ENV WEBHOST 'lviv.resela.eu'
ENV CONTROLLER_IP '10.0.2.11'
ENV MIKROTIK_IP '10.0.2.1'
ENV BRANCH 'test'

RUN sed -i -E "s/<CIP>/$CONTROLLER_IP/" /root/init_container.sh
RUN sed -i -E "s/<MIP>/$MIKROTIK_IP/" /root/init_container.sh

RUN apt-get update
RUN apt-get -y install $(cat /tmp/apt_requirements.txt)
RUN apt-get -y install apache2

RUN ["/bin/bash", "-c", "debconf-set-selections <<< \"postfix postfix/mailname string $WEBHOST\""]
RUN ["/bin/bash", "-c", "debconf-set-selections <<< \"postfix postfix/main_mailer_type string 'Internet Site'\""]
RUN apt-get -y install postfix

RUN pip3 install --upgrade pip
RUN pip3 install -r /tmp/requirements.txt

WORKDIR /var/www
RUN git clone -b $BRANCH https://github.com/kafedra-bit/resela-plus.git resela
RUN cp /root/application.ini resela/resela/config/application.ini
RUN resela/install/setupResela.sh

WORKDIR /root
ENTRYPOINT ./init_container.sh
