/**
 * Lossless 16-bit grayscale JPEG XL decoding through jxl-oxide-wasm.
 *
 * The WASM module is loaded on first use only, so datasets that do not use
 * the hcc codecs never pay for it. jxl-oxide-wasm renders to PNG (16-bit when
 * `forceSrgb` is off and the image is deeper than 8 bits), which
 * {@link decodePngGray16} unpacks; for lossless integer images the samples
 * come back unchanged.
 */
import { decodePngGray16, type TGray16Image } from "./png16.ts";

type TJxlModule = typeof import("jxl-oxide-wasm");
type TInitInput = Parameters<TJxlModule["default"]>[0];

let wasmSource: TInitInput | undefined = undefined;
let modulePromise: Promise<TJxlModule> | null = null;

/**
 * Where to load the WASM binary from. By default jxl-oxide-wasm fetches the
 * `.wasm` file next to its module (`new URL(..., import.meta.url)`, which
 * bundlers rewrite); under Node, whose `fetch` cannot read `file:` URLs, pass
 * the file's bytes. Call it before the first decode: jxl-oxide-wasm ignores a
 * second initialisation.
 */
export function setJxlWasmSource(source: TInitInput) {
  if (modulePromise) {
    throw new Error(
      "setJxlWasmSource must be called before the first JPEG XL decode"
    );
  }
  wasmSource = source;
}

function loadJxl(): Promise<TJxlModule> {
  if (!modulePromise) {
    modulePromise = (async () => {
      const mod = await import("jxl-oxide-wasm");
      await mod.default(
        wasmSource === undefined ? undefined : { module_or_path: wasmSource }
      );
      return mod;
    })();
    modulePromise.catch(() => {
      modulePromise = null;
    });
  }
  return modulePromise;
}

/** Decode a lossless 16-bit grayscale JPEG XL codestream. */
export async function decodeJxlGray16(
  stream: Uint8Array
): Promise<TGray16Image> {
  const { JxlImage } = await loadJxl();
  const image = new JxlImage();
  let png: Uint8Array;
  try {
    // 16-bit output, whatever the browser's HDR support (Firefox is forced
    // to 8-bit sRGB by default)
    image.forceSrgb = false;
    image.feedBytes(stream);
    if (!image.tryInit()) {
      throw new Error("truncated JPEG XL codestream");
    }
    // encodeToPng consumes the RenderResult, which frees the frame
    png = image.render().encodeToPng();
  } finally {
    image.free();
  }
  return decodePngGray16(png);
}
