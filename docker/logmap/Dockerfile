FROM eclipse-temurin:17-jre-alpine
WORKDIR /opt/logmap

# create the placeholder script *inside* the image to ensure proper LF endings
RUN printf '#!/bin/sh\n' > /usr/local/bin/logmap && \
    printf 'echo "LogMap placeholder: alignment simulated"\n' >> /usr/local/bin/logmap && \
    chmod +x /usr/local/bin/logmap

ENTRYPOINT ["/usr/local/bin/logmap"]
