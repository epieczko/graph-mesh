FROM eclipse-temurin:17-jre-alpine
WORKDIR /opt/logmap
RUN printf  'echo "LogMap placeholder: alignment simulated"' > /usr/local/bin/logmap && chmod +x /usr/local/bin/logmap
ENTRYPOINT ["/usr/local/bin/logmap"]
