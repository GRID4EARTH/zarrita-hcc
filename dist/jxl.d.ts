/**
 * Lossless 16-bit grayscale JPEG XL decoding through jxl-oxide-wasm.
 *
 * The WASM module is loaded on first use only, so datasets that do not use
 * the hcc codecs never pay for it. jxl-oxide-wasm renders to PNG (16-bit when
 * `forceSrgb` is off and the image is deeper than 8 bits), which
 * {@link decodePngGray16} unpacks; for lossless integer images the samples
 * come back unchanged.
 */
import { type TGray16Image } from "./png16.ts";
type TJxlModule = typeof import("jxl-oxide-wasm");
type TInitInput = Parameters<TJxlModule["default"]>[0];
/**
 * Where to load the WASM binary from. By default jxl-oxide-wasm fetches the
 * `.wasm` file next to its module (`new URL(..., import.meta.url)`, which
 * bundlers rewrite); under Node, whose `fetch` cannot read `file:` URLs, pass
 * the file's bytes. Call it before the first decode: jxl-oxide-wasm ignores a
 * second initialisation.
 */
export declare function setJxlWasmSource(source: TInitInput): void;
/** Decode a lossless 16-bit grayscale JPEG XL codestream. */
export declare function decodeJxlGray16(stream: Uint8Array): Promise<TGray16Image>;
export {};
