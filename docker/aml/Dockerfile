FROM eclipse-temurin:17-jre-alpine
WORKDIR /opt/aml
RUN printf  'echo "AML placeholder: alignment simulated"' > /usr/local/bin/aml && chmod +x /usr/local/bin/aml
ENTRYPOINT ["/usr/local/bin/aml"]
