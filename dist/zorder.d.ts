/**
 * Morton (Z-order) index of a nested HEALPix chunk, as in
 * `hcc.compression.zorder` of healpix-compress: cell `c` of a chunk of
 * `4**delta` cells sits at row `x` (the even bits of `c`) and column `y` (the
 * odd bits of `c`) of a `2**delta` square raster.
 */
/** Raster offset `x * side + y` of every cell of a chunk of `4**delta` cells. */
export declare function rasterOffsets(delta: number): Uint32Array;
/** `delta` such that `size === 4**delta`, or -1 when `size` is not a power of four. */
export declare function chunkDepth(size: number): number;
