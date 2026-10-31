/**
 * zarrita codecs for the healpix-compress Sentinel-2 serializers, registered
 * lazily: the codec module and the JPEG XL WASM are only loaded when an array
 * uses them.
 *
 * ```ts
 * import { registry } from "zarrita";
 * import { registerHcc } from "zarrita-hcc";
 * registerHcc(registry);
 * ```
 */
import { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.ts";

/** The part of zarrita's codec registry this package needs. */
interface TRegistry {
  // zarrita types its registry after numcodecs' bytes-to-bytes codecs,
  // while these are array_to_bytes codecs
  set(name: string, factory: () => Promise<any>): unknown;
}

export function registerHcc(registry: TRegistry): void {
  registry.set(HCC_SENTINEL2_PYRAMID, () =>
    import("./codecs.ts").then((m) => m.HccSentinel2PyramidCodec)
  );
  registry.set(HCC_SENTINEL2, () =>
    import("./codecs.ts").then((m) => m.HccSentinel2Codec)
  );
}

export { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.ts";
export { setJxlWasmSource } from "./jxl.ts";
