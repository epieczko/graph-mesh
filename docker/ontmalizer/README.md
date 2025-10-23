# Ontmalizer Docker Container

This Docker container packages [Ontmalizer](https://github.com/srdc/ontmalizer), a tool for converting XSD schemas to OWL ontologies.

## Building the Image

```bash
docker build -t graph-mesh/ontmalizer:latest -f docker/ontmalizer/Dockerfile docker/ontmalizer
```

## Usage

### Basic Usage

Convert an XSD file to OWL:

```bash
docker run --rm \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  graph-mesh/ontmalizer:latest \
  -xsd /input/schema.xsd \
  -owl /output/ontology.owl
```

### With Artifacts Directory

```bash
docker run --rm \
  -v $(pwd)/artifacts:/artifacts \
  graph-mesh/ontmalizer:latest \
  -xsd /artifacts/source.xsd \
  -owl /artifacts/converted.owl
```

## Integration with Graph-Mesh

The Ontmalizer container is integrated into the Graph-Mesh pipeline via docker-compose:

```yaml
ontmalizer:
  image: graph-mesh/ontmalizer:latest
  volumes:
    - ./artifacts:/artifacts
```

## Options

Ontmalizer supports various command-line options:

- `-xsd <file>`: Input XSD schema file
- `-owl <file>`: Output OWL ontology file
- `-namespace <uri>`: Target namespace for the ontology
- `-name <name>`: Name for the ontology

For full options, run:

```bash
docker run --rm graph-mesh/ontmalizer:latest --help
```

## Notes

- The container uses Eclipse Temurin JRE 17 on Alpine Linux for minimal size
- Build stage uses Maven to compile Ontmalizer from source
- Runtime stage only includes the JAR and JRE for reduced image size
