FROM maven:3.9-eclipse-temurin-17-alpine AS builder

# Install git for cloning Ontmalizer repository
RUN apk add --no-cache git

# Clone Ontmalizer repository
WORKDIR /build
RUN git clone https://github.com/srdc/ontmalizer.git

# Build Ontmalizer
WORKDIR /build/ontmalizer
RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:17-jre-alpine

# Install required runtime dependencies
RUN apk add --no-cache bash

# Copy built JAR from builder stage
COPY --from=builder /build/ontmalizer/target/ontmalizer-*.jar /app/ontmalizer.jar

# Create directories for input/output
RUN mkdir -p /input /output /artifacts

WORKDIR /app

# Create wrapper script for easier usage
RUN echo '#!/bin/bash' > /app/run.sh && \
    echo 'java -jar /app/ontmalizer.jar "$@"' >> /app/run.sh && \
    chmod +x /app/run.sh

# Default command shows help
ENTRYPOINT ["/app/run.sh"]
CMD ["--help"]
