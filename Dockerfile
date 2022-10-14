FROM python:3.8

LABEL maintainer="Mauve Mailorder Software GmbH & Co. KG"

VOLUME /data

# base OS packages
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y autoremove && \
    apt-get install -y -q \
        git \
        curl \
        libjpeg-turbo-progs \
        graphicsmagick \
        libgraphicsmagick++3 \
        libgraphicsmagick++1-dev \
        libgraphicsmagick-q16-3 \
        zlib1g-dev \
        libboost-python-dev \
        gifsicle \
        ffmpeg && \
    apt-get clean

ENV HOME /app
ENV SHELL bash
ENV WORKON_HOME /app
WORKDIR /app

RUN mkdir /etc/circus.d /data
ADD docker/conf/circus.ini /etc/
COPY docker/conf/thumbor.conf.tpl /app/thumbor.conf.tpl
ADD docker/conf/thumbor-circus.ini.tpl /etc/circus.d/
COPY docker/requirements.txt /app/requirements.txt

ADD ./ /opt/thumbor
RUN chown www-data -R /etc/circus.d /app /data && \
    cd /opt/thumbor && \
    python3 setup.py build && \
    python3 setup.py install && \
    cd /app && \
    rm -R /opt/thumbor && \
    pip3 install --trusted-host None --no-cache-dir -r /app/requirements.txt

COPY docker/docker-entrypoint.sh /
USER www-data
ENTRYPOINT ["/docker-entrypoint.sh"]

# running thumbor multiprocess via circus by default
# to override and run thumbor solo, set THUMBOR_NUM_PROCESSES=1 or unset it
CMD ["circus"]

EXPOSE 80 8888
