# Performance benchmarks

**Environment:** Windows x64, Python 3.13.9, pandas 2.3.3, NumPy 2.3.5, openpyxl 3.1.5.  
**Workloads:** Deterministic synthetic monthly business data. No customer dataset was used.

Run `python -m scripts.benchmark_workloads` to repeat the measurements. The script checks 1,000, 10,000, and 100,000 rows across six columns (maximum 600,000 cells), within the configured parser limit. It times CSV parsing, dataset profile, monthly trend, period variance, robust anomaly scoring, a forecast baseline, and Excel report export.

## Results

| Rows | CSV MiB | Ingest ms | Profile ms | Trend ms | Variance ms | Anomaly ms | Forecast ms | XLSX export ms | XLSX MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 0.04 | 25.84 | 87.29 | 321.13 | 61.38 | 15.73 | 13.64 | 2,462.28 | 0.05 |
| 10,000 | 0.42 | 157.09 | 96.68 | 57.98 | 81.83 | 24.79 | 3.37 | 8,290.11 | 0.31 |
| 100,000 | 4.17 | 1,040.74 | 600.63 | 253.20 | 284.24 | 65.08 | 2.68 | 65,445.16 | 2.87 |

The script records uninstrumented, single-run wall time to avoid `tracemalloc` distortions on large workbook writes. Timings are comparative checkpoints, not typical latency promises. Peak process RSS and native allocations are not captured. Results vary with thermal state, filesystem, Python build, and background processes. The workbook export is subject to the one-million-cell cap.

On this Windows workstation, exporting 100,000 rows × 6 columns took about 65 seconds. That is a noticeable wait for large reports; production deployments should profile on their target CPU and may need a lower export row cap or background export job before serving concurrent users.

## Interpretation and limits

These measurements cover serial, single-user in-process workloads only. They do not measure concurrent sessions, browser rendering, uploaded workbook worst cases, Render CPU/memory, or network latency. Increase deployment capacity only after measuring the actual workload and platform. The 100,000-row case is a practical mid-range checkpoint, not a guarantee for every 250,000-row upload. Use the app's row/cell limits and an identity-aware deployment boundary until hosting behavior is measured.
