/**
 * Get high-resolution time
 */
export default function hrtime(): bigint {
    return BigInt(Math.floor(performance.now() * 1000)) * 1000n;
}
