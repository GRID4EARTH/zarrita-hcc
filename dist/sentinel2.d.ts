/** Digital number reserved for no-data cells. */
export declare const NODATA_DN = 0;
/** Configuration keys the two codecs share, as written in `zarr.json`. */
export interface THccSentinel2Configuration {
    quantification_value?: number;
    add_offset?: number;
    effort?: number;
}
export interface TQuantisation {
    /** `Q` of the product metadata. */
    q: number;
    /** `O` of the product metadata. */
    o: number;
}
export declare function readQuantisation(configuration: THccSentinel2Configuration | undefined): TQuantisation;
export type TFloatDataType = "float32" | "float64";
export type TFloatArray = Float32Array | Float64Array;
export declare function isFloatDataType(dataType: string): dataType is TFloatDataType;
export declare function allocate(dataType: TFloatDataType, size: number): TFloatArray;
/** Row-major strides of a C-ordered array of `shape`. */
export declare function cStrides(shape: number[]): number[];
/**
 * Decode a chunk written row by row along its last axis
 * (`hcc.compression.sentinel2.decode_rows`): a 1-D chunk is one codestream;
 * a chunk with leading axes is the little-endian uint64 byte length of each
 * row's codestream, rows in C order, followed by the codestreams.
 *
 * A chunk with a single row (a leading axis of length 1, e.g. a pass or time
 * axis of chunk size 1) is also read as the bare codestream of a 1-D chunk
 * when the length header does not fit the data: the chunk objects of 1-D
 * arrays can then be read through such an array as they are. A codestream
 * cannot be taken for a framed row by accident (read as a length, its first
 * 8 bytes are far larger than the chunk).
 */
export declare function decodeRows(data: Uint8Array, shape: number[], decodeRow: (stream: Uint8Array, out: TFloatArray, offset: number) => Promise<void>, out: TFloatArray): Promise<void>;
/** The depth of a row of `size` cells, or an error for sizes that are not powers of four. */
export declare function rowDepth(size: number, codec: string): number;
/**
 * Decode one lossless codestream into `out[offset : offset + 4**delta]`, in
 * nested order.
 */
export declare function decodeLosslessRow(stream: Uint8Array, { q, o }: TQuantisation, out: TFloatArray, offset: number, size: number): Promise<void>;
