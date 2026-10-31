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
import { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.js";
export function registerHcc(registry) {
    registry.set(HCC_SENTINEL2_PYRAMID, () => import("./codecs.js").then((m) => m.HccSentinel2PyramidCodec));
    registry.set(HCC_SENTINEL2, () => import("./codecs.js").then((m) => m.HccSentinel2Codec));
}
export { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.js";
export { setJxlWasmSource } from "./jxl.js";
