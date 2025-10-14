FROM python:3.10-slim
WORKDIR /opt/bertmap

# Create placeholder script inside image to guarantee LF endings
RUN printf '#!/bin/sh\n' > /usr/local/bin/bertmap && \
    printf 'echo "BERTMap placeholder: alignment simulated"\n' >> /usr/local/bin/bertmap && \
    chmod +x /usr/local/bin/bertmap

ENTRYPOINT ["/usr/local/bin/bertmap"]
