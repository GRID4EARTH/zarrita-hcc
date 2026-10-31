/**
 * zarrita codecs for the healpix-compress Sentinel-2 serializers
 * `hcc-sentinel2-pyramid` (lossy: lossless parent level, predicted and
 * quantised children) and `hcc-sentinel2` (lossless digital numbers), both
 * JPEG XL based, decode-only. `registerHcc` (`index.ts`) registers them.
 *
 * Reference implementation: https://github.com/GRID4EARTH/healpix-compress
 * (`hcc/compression/sentinel2_pyramid.py`, `hcc/compression/sentinel2.py`).
 */
import type { Chunk, DataType } from "zarrita";
import { type TFloatArray, type TFloatDataType, type THccSentinel2Configuration, type TQuantisation } from "./sentinel2.ts";
import { type THccSentinel2PyramidConfiguration } from "./sentinel2Pyramid.ts";
/**
 * What zarrita hands to `fromConfig` (its `ChunkMetadata`, not exported):
 * the array's data type and chunk shape are all the codecs need.
 */
export interface TCodecMeta {
    dataType: DataType;
    shape: number[];
}
type TRowDecoder = (stream: Uint8Array, quantisation: TQuantisation, out: TFloatArray, offset: number, size: number) => Promise<void>;
/** What both codecs share: the chunk shape, the output dtype and the row container. */
declare abstract class HccSentinel2Base {
    protected readonly decodeRow: TRowDecoder;
    readonly kind = "array_to_bytes";
    protected readonly shape: number[];
    protected readonly dataType: TFloatDataType;
    protected readonly quantisation: TQuantisation;
    constructor(name: string, configuration: THccSentinel2Configuration | undefined, meta: TCodecMeta, decodeRow: TRowDecoder);
    decode(bytes: Uint8Array): Promise<Chunk<TFloatDataType>>;
    encode(): never;
}
export declare class HccSentinel2PyramidCodec extends HccSentinel2Base {
    static fromConfig(configuration: unknown, meta: TCodecMeta): HccSentinel2PyramidCodec;
    constructor(configuration: THccSentinel2PyramidConfiguration | undefined, meta: TCodecMeta);
}
export declare class HccSentinel2Codec extends HccSentinel2Base {
    static fromConfig(configuration: unknown, meta: TCodecMeta): HccSentinel2Codec;
    constructor(configuration: THccSentinel2Configuration | undefined, meta: TCodecMeta);
}
export {};
