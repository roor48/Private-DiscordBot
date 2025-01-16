if ! docker image inspect "disbot:latest" > /dev/null 2>&1; then
	echo "disbot:latest not found. start build"
	docker build -t disbot:latest .
fi
docker run -t --rm -v "$(realpath "$(dirname "$0")"):/app:ro" disbot