/** The part of zarrita's codec registry this package needs. */
interface TRegistry {
    set(name: string, factory: () => Promise<any>): unknown;
}
export declare function registerHcc(registry: TRegistry): void;
export { HCC_SENTINEL2, HCC_SENTINEL2_PYRAMID } from "./names.ts";
export { setJxlWasmSource } from "./jxl.ts";
