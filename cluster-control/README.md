<h1 style="text-align:center;">Cluster-Control Service</h1>

## API Reference

```sh
curl http://localhost:8000/health
```

### Node registration
```sh
MAC_ADDR="$(tr -d '\n' < $(cat /sys/class/net/eth0/address))"; curl -sS -X POST "http://localhost:8000/register/node" -H "Content-Type: application/json" -d "{\"mac_address\":\"${MAC_ADDR}\"}"
```

## Contributing
### Linting
This projects uses `ruff` and `mypy` as part of the CI.

Berfore commiting the code, consider running:
```python
ruff check cluster_control
mypy check cluster_control
```
