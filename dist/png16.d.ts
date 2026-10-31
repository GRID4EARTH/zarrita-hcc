/**
 * Minimal PNG reader for the 16-bit grayscale images that jxl-oxide-wasm
 * produces: the WASM build exposes no raw pixel buffer, only `encodeToPng()`,
 * so the JPEG XL samples come back through a PNG container. Only what that
 * path produces is supported (colour type 0, bit depth 16, no interlace).
 */
export interface TGray16Image {
    width: number;
    height: number;
    /** Row-major samples. */
    samples: Uint16Array;
}
/** zlib-wrapped deflate, as in PNG IDAT and in the codec's validity mask. */
export declare function inflateZlib(data: Uint8Array): Promise<Uint8Array>;
export declare function decodePngGray16(png: Uint8Array): Promise<TGray16Image>;
