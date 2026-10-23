# Reproducibility check

The results in this folder were produced by `docker run ... fndt-sim all` at commit
`f422822` (see `manifest.json`).

As an independent check, the repository was cloned fresh from that commit, a new
Docker image was built, and the confirmatory suite (11 scenarios × 30 seeds × 9
strategies = 2,970 runs) was executed again.

| | Committed `raw/main.csv` | Fresh-clone rerun |
|---|---|---|
| Rows × columns (excluding wall-clock `runtime_s`) | 2970 × 30 | 2970 × 30 |
| SHA-256 of the data (first 16 hex digits) | `c2a91997e48b586d` | `c2a91997e48b586d` |
| Maximum absolute difference in any value | — | 0.0 |

The outputs are identical value for value. Only the wall-clock runtime column differs,
as expected.

To repeat the check:

```bash
git clone <repo> && cd <repo> && git checkout f422822
docker build -t fndt-sim .
docker run --rm -v "$PWD/rerun:/app/results" fndt-sim main
```

Then compare `rerun/raw/main.csv` with `results/raw/main.csv`, ignoring the `runtime_s`
column.
