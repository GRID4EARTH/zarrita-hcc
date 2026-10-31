import { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.js";
import { allocate, cStrides, decodeLosslessRow, decodeRows, isFloatDataType, readQuantisation, rowDepth, } from "./sentinel2.js";
import { decodePyramidRow, } from "./sentinel2Pyramid.js";
/** What both codecs share: the chunk shape, the output dtype and the row container. */
class HccSentinel2Base {
    decodeRow;
    kind = "array_to_bytes";
    shape;
    dataType;
    quantisation;
    constructor(name, configuration, meta, decodeRow) {
        this.decodeRow = decodeRow;
        if (!isFloatDataType(meta.dataType)) {
            throw new Error(`${name} stores reflectances as float32 or float64, got ${meta.dataType}`);
        }
        if (meta.shape.length === 0) {
            throw new Error(`${name}: expected a chunk with at least one axis`);
        }
        rowDepth(meta.shape[meta.shape.length - 1], name);
        this.shape = [...meta.shape];
        this.dataType = meta.dataType;
        this.quantisation = readQuantisation(configuration);
    }
    async decode(bytes) {
        const size = this.shape.reduce((a, b) => a * b, 1);
        const data = allocate(this.dataType, size);
        const rowSize = this.shape[this.shape.length - 1];
        await decodeRows(bytes, this.shape, (stream, out, offset) => this.decodeRow(stream, this.quantisation, out, offset, rowSize), data);
        return { data, shape: this.shape, stride: cStrides(this.shape) };
    }
    encode() {
        throw new Error("the hcc Sentinel-2 codecs are decode-only");
    }
}
export class HccSentinel2PyramidCodec extends HccSentinel2Base {
    static fromConfig(configuration, meta) {
        return new HccSentinel2PyramidCodec(configuration, meta);
    }
    constructor(configuration, meta) {
        super(HCC_SENTINEL2_PYRAMID, configuration, meta, decodePyramidRow);
    }
}
export class HccSentinel2Codec extends HccSentinel2Base {
    static fromConfig(configuration, meta) {
        return new HccSentinel2Codec(configuration, meta);
    }
    constructor(configuration, meta) {
        super(HCC_SENTINEL2, configuration, meta, decodeLosslessRow);
    }
}
