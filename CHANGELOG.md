# Changelog

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
