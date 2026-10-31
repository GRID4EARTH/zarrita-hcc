import { type TFloatArray, type THccSentinel2Configuration, type TQuantisation } from "./sentinel2.ts";
/** Configuration keys of `hcc-sentinel2-pyramid`; only `Q` and `O` matter for decoding. */
export interface THccSentinel2PyramidConfiguration extends THccSentinel2Configuration {
    relative_step?: number;
    min_step?: number;
    predictor_size?: number;
}
export interface TPyramidStreamInfo {
    delta: number;
    predictorSize: number;
    /** Detail step, in digital numbers. */
    step: number;
    offset: number;
    hasMask: boolean;
    coefficientBytes: number;
    baseBytes: number;
    detailBytes: number;
    maskBytes: number;
}
/** Parse the codestream header (`hcc.compression.sentinel2_pyramid.stream_info`). */
export declare function streamInfo(stream: Uint8Array): TPyramidStreamInfo;
/**
 * Decode one pyramid codestream into `out[offset : offset + 4**delta]`, in
 * nested order, `NaN` for no-data cells.
 */
export declare function decodePyramidRow(stream: Uint8Array, quantisation: TQuantisation, out: TFloatArray, offset: number, size: number): Promise<void>;
