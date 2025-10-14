FROM eclipse-temurin:17-jre-alpine
WORKDIR /opt/aml

# create placeholder script inside the container (guaranteed LF endings)
RUN printf '#!/bin/sh\n' > /usr/local/bin/aml && \
    printf 'echo "AML placeholder: alignment simulated"\n' >> /usr/local/bin/aml && \
    chmod +x /usr/local/bin/aml

ENTRYPOINT ["/usr/local/bin/aml"]
