ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Build arugments
ARG BUILD_DATE
ARG BUILD_REF
ARG BUILD_VERSION
ARG BUILD_ARCH

# Labels
LABEL \
    io.hass.name="TTLockToMqtt - Integration of TTlock Cloud API and Home Assistant instance via MQTT" \
    io.hass.description="Integration of TTlock Cloud API and Home Assistant instance via MQTT" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="tonyldo <tonyldo@gmail.com>" \
    org.label-schema.description="Integration of TTlock Cloud API and Home Assistant instance via MQTT" \
    org.label-schema.build-date=${BUILD_DATE} \
    org.label-schema.name="TTLockToMqtt" \
    org.label-schema.schema-version="0.1" \
    org.label-schema.url="https://github.com/tonyldo/TTLockToMQTT" \
    org.label-schema.usage="https://github.com/tonyldo/TTLockToMQTT/blob/master/ttlocktomqtt/README.md" \
    org.label-schema.vcs-ref=${BUILD_REF} \
    org.label-schema.vcs-url="https://github.com/tonyldo/TTLockToMQTT" \
    org.label-schema.vendor="TTLockToMQTT Hass.io Add-on"


COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

COPY src/ttlock_adapter.py /

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
