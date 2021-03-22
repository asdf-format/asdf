# Troubleshooting asdf tests on S390X architecture

1. Build the Docker image:

```
docker build -t asdf-s390x .
```

2. Run the container, which starts in the asdf repository root:

```
docker run -it asdf-s390x
```

Alternatively, bind-mount a checkout with local changes:

```
docker run -it --mount type=bind,source=/path/to/asdf,target=/root/asdf asdf-s390x
```

3. Run pytest:

```
pytest
```
