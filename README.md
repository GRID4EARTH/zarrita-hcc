# zarrita-hcc

[zarrita](https://github.com/manzt/zarrita.js) codecs for the two Zarr v3
serializers of [healpix-compress](https://github.com/GRID4EARTH/healpix-compress)
that store Sentinel-2 reflectances, decode-only:

- `hcc-sentinel2-pyramid` (lossy: the parent level as lossless digital
  numbers, the children predicted from it plus a quantised detail, all JPEG XL
  coded);
- `hcc-sentinel2` (lossless digital numbers in JPEG XL).

Chunks decode to `float32` or `float64` reflectances, with no-data cells as
`NaN`. JPEG XL is decoded by
[jxl-oxide-wasm](https://github.com/tirr-c/jxl-oxide).

## Use

```sh
npm install github:GRID4EARTH/zarrita-hcc#v0.1.0
```

```ts
import { registry } from "zarrita";
import { registerHcc } from "zarrita-hcc";

registerHcc(registry);
```

`registerHcc` registers both codec names lazily: the codec code and the JPEG
XL WASM (1.7 MB, 616 kB gzipped) are only loaded the first time an array uses
them. In the browser the WASM is fetched from next to the jxl-oxide-wasm
module (`new URL(..., import.meta.url)`, which bundlers such as Vite rewrite
into an asset URL). Under Node, hand the bytes over first:

```ts
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { setJxlWasmSource } from "zarrita-hcc";

const require = createRequire(import.meta.url);
const jxlDir = dirname(require.resolve("jxl-oxide-wasm/package.json"));
setJxlWasmSource(readFileSync(join(jxlDir, "jxl_oxide_wasm_bg.wasm")));
```

## Develop

```sh
npm install
npm test
npm run typecheck
npm run build # writes dist/, which is committed
```

`dist/` is committed so that the package can be installed straight from
GitHub; rebuild it with every change to `src/`.

The decoders are tested against vectors produced by the Python reference
implementation. `scripts/make_hcc_fixtures.py` regenerates them into
`tests/__fixtures__/` from a Python environment where `hcc` (healpix-compress)
and `imagecodecs` are installed; see its docstring. Without `--store` it
fetches nothing and decodes the real chunks already in the fixtures again.

## License

Apache-2.0, like healpix-compress.
