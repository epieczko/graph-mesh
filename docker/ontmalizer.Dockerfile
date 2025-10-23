# Dockerfile for Ontmalizer XSD to OWL converter
# Ontmalizer is a Java-based tool for converting XML Schema to OWL
FROM openjdk:11-jre-slim

LABEL maintainer="graph-mesh"
LABEL description="Ontmalizer XSD to OWL converter service"

WORKDIR /app

# Install required tools
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download Ontmalizer JAR from GitHub releases
# Using version 2.1 - adjust if a newer version is available
RUN wget -O ontmalizer.jar https://github.com/TheOntologist/ontmalizer/releases/download/v2.1/ontmalizer-2.1.jar || \
    wget -O ontmalizer.jar https://raw.githubusercontent.com/TheOntologist/ontmalizer/master/lib/ontmalizer.jar || \
    (echo "Downloading from alternative source..." && \
     wget -O ontmalizer.jar https://protegewiki.stanford.edu/images/9/9e/Ontmalizer.jar)

# Create input/output directories
RUN mkdir -p /input /output

# Verify JAR was downloaded
RUN test -f ontmalizer.jar || (echo "ERROR: Failed to download Ontmalizer JAR" && exit 1)

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
INPUT_FILE="${1:-/input/schema.xsd}"\n\
OUTPUT_FILE="${2:-/output/ontology.owl}"\n\
\n\
if [ ! -f "$INPUT_FILE" ]; then\n\
    echo "ERROR: Input file not found: $INPUT_FILE"\n\
    exit 1\n\
fi\n\
\n\
echo "Converting XSD to OWL..."\n\
echo "Input: $INPUT_FILE"\n\
echo "Output: $OUTPUT_FILE"\n\
\n\
# Run Ontmalizer\n\
java -jar /app/ontmalizer.jar -xsd "$INPUT_FILE" -owl "$OUTPUT_FILE"\n\
\n\
if [ ! -f "$OUTPUT_FILE" ]; then\n\
    echo "ERROR: Conversion failed - output file not created"\n\
    exit 1\n\
fi\n\
\n\
echo "Conversion completed successfully"\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
