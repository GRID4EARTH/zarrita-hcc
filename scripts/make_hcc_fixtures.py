#!/usr/bin/env python3
"""Generate test vectors for the zarrita-hcc decoders of the healpix-compress
Sentinel-2 codecs (``hcc-sentinel2-pyramid`` and ``hcc-sentinel2``).

Run from a Python environment where ``hcc`` (healpix-compress with the
Sentinel-2 codecs) and ``imagecodecs`` are installed::

    python scripts/make_hcc_fixtures.py tests/__fixtures__

Without ``--store`` nothing is fetched: the real chunks already in the output
directory, as listed by its ``manifest.json``, are decoded again, and the
level-12 nodes and their manifest entries are kept as they are, so that the
real cases stay in the tests.

With ``--store`` the real chunks (``real_*``) and the level-12 nodes
(``store_L12``) are read again from a Sentinel-2 L2A HEALPix store written
with ``hcc-sentinel2-pyramid`` (the ``measurements/reflectance`` group, with
one group per level), which also needs ``fsspec``, ``zarr`` and, for an S3
store, ``s3fs``::

    python scripts/make_hcc_fixtures.py tests/__fixtures__ \
        --store s3://<bucket>/<product>.zarr/measurements/reflectance \
        --endpoint-url https://<s3 endpoint> --profile <aws profile>

Only chunk keys relative to the store are recorded in the manifest.

Every case is written as a codestream (``<name>.stream``), the expected decoded
cells as little-endian float64 (``<name>.expected.f64``, or float32 in
``<name>.expected.f32`` for chunks of more than 65536 cells) and, for the
pyramid codec, the two JPEG XL layers as decoded by the reference
implementation (``<name>.base.u16``, ``<name>.detail.u16``, little-endian
uint16; one-dimensional chunks of at most 65536 cells only). The manifest
``manifest.json`` lists the cases with the codec configuration and chunk shape
the Zarr metadata would carry.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

from hcc.compression import sentinel2, sentinel2_pyramid
from hcc.compression.zorder import expand_tile, flatten_tile

PYRAMID = "hcc-sentinel2-pyramid"
LOSSLESS = "hcc-sentinel2"

def pyramid_config(**overrides) -> dict:
    cfg = dict(
        relative_step=sentinel2_pyramid.DEFAULT_RELATIVE_STEP,
        min_step=1.0,
        predictor_size=5,
        quantification_value=sentinel2.DEFAULT_QUANTIFICATION_VALUE,
        add_offset=sentinel2.DEFAULT_ADD_OFFSET,
        effort=7,
    )
    cfg.update(overrides)
    return cfg


def lossless_config(**overrides) -> dict:
    cfg = dict(
        quantification_value=sentinel2.DEFAULT_QUANTIFICATION_VALUE,
        add_offset=sentinel2.DEFAULT_ADD_OFFSET,
        effort=7,
    )
    cfg.update(overrides)
    return cfg


def encode_rows(cells: np.ndarray, encode_row) -> bytes:
    """The chunk container of healpix-compress (``hcc.compression.sentinel2.encode_rows``).

    A 1-D chunk is the codestream of its single row. A chunk with leading axes
    is the little-endian uint64 byte length of each row's codestream, rows in C
    order, followed by the codestreams. Reproduced here so that the script also
    runs with an ``hcc`` that predates the leading-axes support.
    """
    if cells.ndim == 1:
        return encode_row(cells)
    streams = [encode_row(row) for row in cells.reshape(-1, cells.shape[-1])]
    lengths = np.array([len(s) for s in streams], dtype="<u8")
    return lengths.tobytes() + b"".join(streams)


def decode_rows(data: bytes, shape: tuple, decode_row) -> np.ndarray:
    """Inverse of :func:`encode_rows` (``hcc.compression.sentinel2.decode_rows``)."""
    if len(shape) == 1:
        return decode_row(data)
    n_rows = int(np.prod(shape[:-1]))
    header = 8 * n_rows
    lengths = np.frombuffer(data[:header], dtype="<u8").astype(np.int64)
    assert header + int(lengths.sum()) == len(data)
    ends = header + np.cumsum(lengths)
    rows = [decode_row(data[end - size : end]) for end, size in zip(ends, lengths)]
    return np.stack(rows).reshape(shape)


def encode_chunk(codec: str, cells: np.ndarray, cfg: dict) -> bytes:
    if codec == PYRAMID:
        row = lambda c: sentinel2_pyramid.encode(c, **cfg)  # noqa: E731
    else:
        row = lambda c: sentinel2.encode(c, **cfg)  # noqa: E731
    return encode_rows(cells, row)


def decode_chunk(codec: str, stream: bytes, shape: tuple, cfg: dict, dtype) -> np.ndarray:
    kw = dict(
        quantification_value=cfg["quantification_value"],
        add_offset=cfg["add_offset"],
        dtype=dtype,
    )
    if codec == PYRAMID:
        row = lambda s: sentinel2_pyramid.decode(s, **kw)  # noqa: E731
    else:
        row = lambda s: sentinel2.decode(s, **kw)  # noqa: E731
    return decode_rows(stream, shape, row)


def pyramid_layers(stream: bytes) -> dict:
    """The two JPEG XL layers of a single pyramid codestream, as the reference decodes them."""
    info = sentinel2_pyramid.stream_info(stream)
    pos = sentinel2_pyramid._HEADER.size + info["coefficient_bytes"]
    jxl = sentinel2._jpegxl()
    base = np.asarray(jxl.jpegxl_decode(stream[pos : pos + info["base_bytes"]]))
    pos += info["base_bytes"]
    detail = np.asarray(jxl.jpegxl_decode(stream[pos : pos + info["detail_bytes"]]))
    assert base.dtype == np.uint16 and detail.dtype == np.uint16
    return dict(info=info, base=base, detail=detail)


class Writer:
    def __init__(self, out: Path):
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.cases: list[dict] = []

    def add(
        self,
        name: str,
        codec: str,
        cfg: dict,
        cells: np.ndarray | None = None,
        *,
        stream: bytes | None = None,
        shape: tuple | None = None,
        data_type: str = "float64",
        note: str = "",
    ):
        dtype = np.dtype(data_type)
        if stream is None:
            assert cells is not None
            shape = tuple(cells.shape)
            stream = encode_chunk(codec, cells, cfg)
        assert shape is not None
        expected = decode_chunk(codec, stream, shape, cfg, dtype)
        assert expected.shape == shape, (expected.shape, shape)
        (self.out / f"{name}.stream").write_bytes(stream)
        # large chunks keep the repository small: float32 expectations (still far
        # below the 1e-6 tolerance of the tests) and no per-layer dumps
        large = expected.size > 65536
        exp_dtype, exp_ext = ("<f4", "f32") if large else ("<f8", "f64")
        (self.out / f"{name}.expected.{exp_ext}").write_bytes(
            np.ascontiguousarray(expected, dtype=exp_dtype).tobytes()
        )
        case = dict(
            name=name,
            codec=codec,
            configuration=cfg,
            shape=list(shape),
            data_type=data_type,
            stream=f"{name}.stream",
            expected=f"{name}.expected.{exp_ext}",
            expected_dtype="float32" if large else "float64",
            note=note,
        )
        if codec == PYRAMID and len(shape) == 1 and not large:
            layers = pyramid_layers(stream)
            (self.out / f"{name}.base.u16").write_bytes(
                np.ascontiguousarray(layers["base"], dtype="<u2").tobytes()
            )
            (self.out / f"{name}.detail.u16").write_bytes(
                np.ascontiguousarray(layers["detail"], dtype="<u2").tobytes()
            )
            case["pyramid"] = dict(
                **layers["info"],
                base=f"{name}.base.u16",
                base_shape=list(layers["base"].shape),
                detail=f"{name}.detail.u16",
                detail_shape=list(layers["detail"].shape),
            )
        if cells is not None:
            # the error budget of the lossy codec, for the tests' own information
            err = np.abs(expected.astype(np.float64) - cells)
            case["max_abs_error_vs_input"] = float(np.nanmax(err)) if np.isfinite(err).any() else 0.0
        self.cases.append(case)
        print(f"{name}: {len(stream)} bytes, shape {shape}")

    def finish(self, extra: dict):
        manifest = dict(
            description=(
                "Test vectors for the zarrita-hcc decoders of the healpix-compress "
                "Sentinel-2 codecs, generated by scripts/make_hcc_fixtures.py with "
                "the reference Python implementation."
            ),
            **extra,
            cases=self.cases,
        )
        (self.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


def synthetic(w: Writer):
    rng = np.random.default_rng(20261016)

    # smallest chunk: one parent, four children
    w.add("pyr_delta1", PYRAMID, pyramid_config(), np.array([0.1, 0.12, 0.11, 0.13]),
          note="delta=1, the 1x1 base is edge-padded for the 5x5 predictor")

    # a smooth field, default parameters
    n = 4**3
    w.add("pyr_smooth_delta3", PYRAMID, pyramid_config(),
          np.linspace(0.05, 0.4, n) + 0.01 * np.sin(np.arange(n) / 3.0))

    # noisy field with a no-data region whose border cuts through parents (mask flag set)
    delta = 4
    side = 2**delta
    raster = 0.2 + 0.05 * rng.standard_normal((side, side)) + np.linspace(0, 0.1, side)[None, :]
    raster[:5, :7] = np.nan  # odd sizes: parents on the border are partially valid
    raster[9, 3] = np.nan  # an isolated no-data child
    cells = flatten_tile(raster)
    assert np.isnan(cells).any()
    w.add("pyr_nodata_mask_delta4", PYRAMID, pyramid_config(), cells,
          note="NaN region with partially valid parents: FLAG_MASK set")

    # a no-data region aligned on parents only (no mask needed)
    raster = 0.3 + 0.02 * rng.standard_normal((side, side))
    raster[:4, :] = np.nan
    w.add("pyr_nodata_aligned_delta4", PYRAMID, pyramid_config(), flatten_tile(raster),
          note="NaN parents only: no mask, no-data comes from base DN 0")

    # the lossless preset (relative_step = 0 -> step = min_step = 1 DN)
    w.add("pyr_lossless_preset_delta4", PYRAMID, pyramid_config(relative_step=0.0),
          flatten_tile(0.25 + 0.03 * rng.standard_normal((side, side))),
          note="relative_step=0: step 1 DN")

    # non-default Q/O and predictor size, and a float32 array
    w.add("pyr_q1e4_o0_k3_delta3", PYRAMID,
          pyramid_config(quantification_value=10000.0, add_offset=0.0, predictor_size=3),
          0.5 + 0.1 * rng.standard_normal(4**3), data_type="float32",
          note="add_offset=0, predictor_size=3, float32 array")

    # predictor_size 1 (pure replication), coarse step
    w.add("pyr_k1_step2_delta3", PYRAMID,
          pyramid_config(predictor_size=1, relative_step=2.0, min_step=2.0),
          0.3 + 0.1 * rng.standard_normal(4**3), note="predictor_size=1, min_step=2")

    # all no-data
    w.add("pyr_all_nan_delta2", PYRAMID, pyramid_config(), np.full(4**2, np.nan))

    # values hitting the DN clip bounds
    w.add("pyr_clip_delta2", PYRAMID, pyramid_config(),
          np.array([-0.5, -0.1, 0.0, 0.1, 6.5, 7.0, 0.2, 0.3] + [0.25] * 8),
          note="reflectances below (DN+O)/Q of DN 1 and above DN 65535 are clipped at encoding")

    # leading axes: (2, 3, 64) chunk = 6 rows, one of them all NaN
    rows = 0.2 + 0.05 * rng.standard_normal((2, 3, 4**3))
    rows[1, 2] = np.nan
    rows[0, 1, :10] = np.nan
    w.add("pyr_rows_2x3_delta3", PYRAMID, pyramid_config(), rows,
          note="chunk with leading axes: uint64 lengths header then one codestream per row")

    # lossless variant
    cells = 0.2 + 0.05 * rng.standard_normal(4**3)
    cells[[0, 5, 17, 63]] = np.nan
    w.add("ll_delta3", LOSSLESS, lossless_config(), cells, note="lossless, NaN cells")
    w.add("ll_delta1_f32", LOSSLESS, lossless_config(add_offset=0.0),
          np.array([0.0, 0.1234, np.nan, 1.0]), data_type="float32")
    w.add("ll_rows_2x16", LOSSLESS, lossless_config(),
          0.3 + 0.1 * rng.standard_normal((2, 4**2)), note="leading axis, lossless")
    w.add("ll_delta4", LOSSLESS, lossless_config(),
          flatten_tile(np.clip(0.2 + 0.05 * rng.standard_normal((16, 16)), 0, None)))


def real_chunks(w: Writer, store: str, storage_options: dict) -> dict:
    import fsspec

    fs, root = fsspec.core.url_to_fs(store, **storage_options)
    root = root.rstrip("/")
    picked = []
    for level, band, chunk in [("12", "b04", "c/0"), ("16", "b8a", "c/1"), ("20", "b04", "c/0")]:
        arr = f"{root}/{level}/{band}"
        meta = json.loads(fs.cat(f"{arr}/zarr.json"))
        (codec,) = meta["codecs"]
        assert codec["name"] == PYRAMID, codec
        keys = sorted(fs.ls(f"{arr}/c"))
        key = f"{arr}/{chunk}"
        if key not in keys:
            key = keys[0]
        stream = fs.cat(key)
        shape = tuple(meta["chunk_grid"]["configuration"]["chunk_shape"])
        name = f"real_L{level}_{band}_{key.rsplit('/', 1)[-1]}"
        w.add(name, PYRAMID, codec["configuration"], stream=stream, shape=shape,
              data_type=meta["data_type"],
              note=f"chunk {key[len(root) + 1:]} of a Sentinel-2 L2A store")
        picked.append(dict(level=level, band=band, key=key[len(root) + 1:]))

    # the level-12 arrays as Zarr nodes (metadata + first chunk), for an
    # end-to-end test through zarrita's own pipeline: b04 (hcc-sentinel2-pyramid)
    # and cell_ids (numcodecs.delta + bytes + zstd)
    import zarr

    store_dir = w.out / "store_L12"
    for name in ["zarr.json", "b04/zarr.json", "b04/c/0", "cell_ids/zarr.json", "cell_ids/c/0", "crs/zarr.json", "crs/c"]:
        src = f"{root}/12/{name}"
        if fs.exists(src):
            dst = store_dir / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(fs.cat(src))
    cell_ids = zarr.open_array(store=zarr.storage.LocalStore(str(store_dir)), path="cell_ids", mode="r")[:]
    (w.out / "store_L12_cell_ids.expected.json").write_text(
        json.dumps([int(v) for v in cell_ids]) + "\n"
    )
    return dict(real_chunks=picked,
                store_L12=dict(path="store_L12", cell_ids_expected="store_L12_cell_ids.expected.json",
                               b04_expected="real_L12_b04_0.expected.f64"))


def reuse_real_chunks(w: Writer, previous: dict) -> dict:
    """Without ``--store``: decode again the real chunks of the last run that read a store.

    Their codestreams and the level-12 nodes stay as fetched then; only the
    expected cells (and layers) come from the installed ``hcc``.
    """
    real = [case for case in previous.get("cases", []) if case["name"].startswith("real_")]
    if not real:
        print(f"warning: no real chunks listed in {w.out / 'manifest.json'}; "
              "run once with --store to fetch them", file=sys.stderr)
    for case in real:
        w.add(case["name"], case["codec"], case["configuration"],
              stream=(w.out / case["stream"]).read_bytes(), shape=tuple(case["shape"]),
              data_type=case["data_type"], note=case["note"])
    keep = ("real_chunks", "store_L12")
    return {key: previous[key] for key in keep if key in previous}


def main(argv: list[str]):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", type=Path, help="fixture directory (tests/__fixtures__)")
    parser.add_argument("--store", help="reflectance group of a store to read the real chunks from")
    parser.add_argument("--endpoint-url", help="S3 endpoint of --store")
    parser.add_argument("--profile", help="AWS profile for --store")
    args = parser.parse_args(argv[1:])
    out = args.out
    manifest = out / "manifest.json"
    previous = json.loads(manifest.read_text()) if manifest.exists() else {}
    w = Writer(out)
    synthetic(w)
    if args.store:
        storage_options = {}
        if args.profile:
            storage_options["profile"] = args.profile
        if args.endpoint_url:
            storage_options["client_kwargs"] = {"endpoint_url": args.endpoint_url}
        extra = real_chunks(w, args.store, storage_options)
    else:
        extra = reuse_real_chunks(w, previous)
    extra["hcc_source"] = (
        "healpix-compress, branch sentinel2-jpegxl at commit 331686d "
        "(decodes bit-identically to the released format of v0.2.0)"
    )
    w.finish(extra)
    print(f"{len(w.cases)} cases in {out}")


if __name__ == "__main__":
    main(sys.argv)
