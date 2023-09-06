#!/bin/bash

# Read the version from version.txt
version=$(cat version.txt)

# Check if the version is empty
if [[ -z "$version" ]]; then
  echo "Error: version.txt is empty or missing."
  exit 1
fi

# Export VERSION as environment variable
export VERSION=$version

# Build and tag all services
docker-compose build
docker-compose push
