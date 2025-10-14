FROM eclipse-temurin:17-jre
LABEL org.opencontainers.image.source="https://github.com/example/graph-mesh"

RUN useradd -ms /bin/bash runner
WORKDIR /opt/aml

COPY aml-distribution/ /opt/aml/

USER runner
ENTRYPOINT ["java", "-jar", "/opt/aml/aml.jar"]
