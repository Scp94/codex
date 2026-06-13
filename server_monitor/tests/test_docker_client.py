from monitor_platform.docker_client import normalize_container, normalize_stats


def test_normalize_container_flattens_docker_payload():
    item = normalize_container(
        {
            "Id": "abcdef1234567890",
            "Names": ["/api"],
            "Image": "example/api:latest",
            "ImageID": "sha256:abc",
            "Command": "uvicorn app:app",
            "Created": 123,
            "State": "running",
            "Status": "Up 3 minutes",
            "Ports": [{"PrivatePort": 8000, "PublicPort": 8080, "Type": "tcp"}],
            "Labels": {
                "com.docker.compose.project": "demo",
                "com.docker.compose.service": "api",
            },
        }
    )

    assert item["short_id"] == "abcdef123456"
    assert item["name"] == "api"
    assert item["ports"] == ["8080:8000/tcp"]
    assert item["compose_project"] == "demo"


def test_normalize_stats_calculates_cpu_memory_and_io():
    stats = normalize_stats(
        {
            "read": "2026-06-13T00:00:00Z",
            "cpu_stats": {
                "online_cpus": 2,
                "system_cpu_usage": 2000,
                "cpu_usage": {"total_usage": 150},
            },
            "precpu_stats": {
                "system_cpu_usage": 1000,
                "cpu_usage": {"total_usage": 100},
            },
            "memory_stats": {
                "usage": 1024,
                "limit": 4096,
                "stats": {"cache": 128},
            },
            "networks": {"eth0": {"rx_bytes": 10, "tx_bytes": 20}},
            "blkio_stats": {
                "io_service_bytes_recursive": [
                    {"op": "Read", "value": 30},
                    {"op": "Write", "value": 40},
                ]
            },
        }
    )

    assert stats["cpu_percent"] == 10.0
    assert stats["memory"]["usage"] == 896
    assert stats["memory"]["percent"] == 21.88
    assert stats["network"] == {"rx_bytes": 10, "tx_bytes": 20}
    assert stats["block_io"] == {"read_bytes": 30, "write_bytes": 40}

