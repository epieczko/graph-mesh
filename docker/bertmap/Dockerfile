FROM python:3.10-slim
WORKDIR /opt/bertmap
RUN printf  'echo "BERTMap placeholder: alignment simulated"' > /usr/local/bin/bertmap && chmod +x /usr/local/bin/bertmap
ENTRYPOINT ["/usr/local/bin/bertmap"]
