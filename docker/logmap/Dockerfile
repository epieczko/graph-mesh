FROM openjdk:17-jre-slim
LABEL org.opencontainers.image.source="https://github.com/example/graph-mesh"

RUN useradd -ms /bin/bash runner
WORKDIR /opt/logmap

COPY logmap-distribution/ /opt/logmap/

USER runner
ENTRYPOINT ["java", "-jar", "/opt/logmap/logmap.jar"]
