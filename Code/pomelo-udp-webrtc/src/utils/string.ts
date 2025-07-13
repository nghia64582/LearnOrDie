/**
 * Encode binary data to base64
 */
export function encodeBase64(data: Uint8Array): string {
    return btoa(String.fromCharCode.apply(null, <unknown>data as number[]));
}


/**
 * Decode base64 to binary data
 */
export function decodeBase64(data: string): Uint8Array {
    return new Uint8Array(atob(data.replace(/_/g, '/').replace(/-/g, '+'))
        .split("")
        .map(c => c.charCodeAt(0)));
}


/**
 * Decode binary array to string
 */
export function decodeString(data: Uint8Array): string {
    return String.fromCharCode.apply(null, <unknown>data as number[])
}
