# Changelog

## [2.0.0](https://github.com/andersondanilo/cloudrun-benchmark/compare/cloudrun-benchmark-v1.1.0...cloudrun-benchmark-v2.0.0) (2026-10-15)


### ⚠ BREAKING CHANGES

* the Redis layout changed from the single key benchmark:data to benchmark:data:0..19, so scripts/setup.py must be re-run. Pulumi now requires the goImage config value and results are not comparable with the previous 100 KiB benchmark.

### Features

* serve 20 random-size payloads and add a go fasthttp api ([71cf49b](https://github.com/andersondanilo/cloudrun-benchmark/commit/71cf49bed3dddd0420d8c47cf53f98d4c66ec719))
* use e2-highcpu-4 vms and add benchmark results ([9123902](https://github.com/andersondanilo/cloudrun-benchmark/commit/912390244436bb578027969f08b0a7eebc3b21a8))


### Bug Fixes

* **ci:** refresh pulumi state before deploying ([2e4fa82](https://github.com/andersondanilo/cloudrun-benchmark/commit/2e4fa825cf6db867111303078e616c1a852f842f))
* retry the redis connection on startup in go and rust apis ([afc0ffa](https://github.com/andersondanilo/cloudrun-benchmark/commit/afc0ffa6a725cb6fcf9ba924c22c059900244092))

## [1.1.0](https://github.com/andersondanilo/cloudrun-benchmark/compare/cloudrun-benchmark-v1.0.0...cloudrun-benchmark-v1.1.0) (2026-10-14)


### Features

* replace upstash with a self-hosted redis vm ([ef8614a](https://github.com/andersondanilo/cloudrun-benchmark/commit/ef8614aed7504dc544836ca1eca1effaf4e5c200))


### Bug Fixes

* include cloud run benchmark results in the release ([4222372](https://github.com/andersondanilo/cloudrun-benchmark/commit/422237284410618993a65ee3cea1824e55f1ab70))
* use sendall in setup.py so large payloads are fully written ([68003fb](https://github.com/andersondanilo/cloudrun-benchmark/commit/68003fbb9611c8cc57e3ddc1e1f44dd40998a96f))

## 1.0.0 (2026-10-13)


### Features

* add node/rust redis benchmark with pulumi infra and deploy workflows ([a22d019](https://github.com/andersondanilo/cloudrun-benchmark/commit/a22d0198ecab2a3071d2b06c81fb077e4ba2712f))
* preconfigure upstash REDIS_URL on the benchmark vm ([5de56aa](https://github.com/andersondanilo/cloudrun-benchmark/commit/5de56aabe9d175e6c3e73b239fc2f2acf0b3befb))
