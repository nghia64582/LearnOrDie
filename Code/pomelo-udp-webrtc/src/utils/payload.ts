import Pool from "./pool";
import { decodeString } from "./string";


const BUFFER_OVERFLOW_ERR_MSG = "BufferOverflow";
const BUFFER_UNDERFLOW_ERR_MSG = "BufferUnderflow";


/**
 * Payload
 */
export default class Payload {
    /**
     * Internal data of payload
     */
    data: Uint8Array;

    /**
     * Current position of payload
     */
    position = 0;

    /**
     * Capacity of payload
     */
    capacity: number;

    /**
     * Next payload in pool
     */
    next: Payload | null = null;

    /**
     * Pool source
     */
    readonly pool: PayloadPool | null = null;

    /**
     * Data view of payload
     */
    private view: DataView;

    constructor(
        data: ArrayBuffer | Uint8Array | number = 0,
        pool: PayloadPool | null = null
    ) {
        if (data instanceof ArrayBuffer) {
            this.data = new Uint8Array(data);
        } else if (data instanceof Uint8Array) {
            this.data = data;
        } else {
            this.data = new Uint8Array(data);
        }
        this.view = new DataView(
            this.data.buffer,
            this.data.byteOffset,
            this.data.byteLength
        );
        this.capacity = this.data.byteLength;
        this.pool = pool;
    }

    /**
     * Prepare payload for reading or writing
     */
    prepare(dataOrCapacity: ArrayBuffer | Uint8Array | number) {
        if (dataOrCapacity instanceof Uint8Array) {
            this.data = dataOrCapacity;
        } else if (dataOrCapacity instanceof ArrayBuffer) {
            this.data = new Uint8Array(dataOrCapacity);
        } else {
            if (this.data.byteLength < dataOrCapacity) {
                this.data = new Uint8Array(dataOrCapacity);
            }
        }

        this.view = new DataView(
            this.data.buffer,
            this.data.byteOffset,
            this.data.byteLength
        );

        this.capacity = this.data.byteLength;
        this.position = 0;
    }

    /**
     * Release payload to pool
     */
    release() {
        this.pool?.release(this);
    }

    /**
     * Calculate number of bytes to write packed uint64 value
     */
    static calcPackedUint64Bytes(value: bigint): number {
        if (value & 0xFFFFFFFF00000000n) {
            // Need > 4 bytes
            if (value & 0xFFFF000000000000n) {
                // Need > 6 bytes
                if (value & 0xFF000000000000n) {
                    return 8; // Need 8 bytes
                } else {
                    return 7; // Need 7 bytes
                }
            } else {
                // Need <= 6 bytes
                if (value & 0xFFFFFF0000000000n) {
                    return 6; // Need 6 bytes
                } else {
                    return 5; // Need 5 bytes
                }
            }
        } else {
            // Need <= 4 bytes
            if (value & 0xFFFF0000n) {
                // Need > 2 bytes
                if (value & 0xFF000000n) {
                    return 4; // Need 4 bytes
                } else {
                    return 3; // Need 3 bytes
                }
            } else {
                // Need <= 2 bytes
                if (value & 0xFF00n) {
                    return 2; // Need 2 bytes
                } else {
                    return 1; // Need 1 byte
                }
            }
        }
    }

    /**
     * Pack the data as an view to fit the capacity
     */
    pack(): Uint8Array {
        return this.data.subarray(0, this.position);
    }

    /**
     * Reset payload
     */
    reset() {
        this.position = 0;
    }

    /**
     * Write data to the buffer
     * @param value The uint8 typed array to write
     */
    write(value: Uint8Array): void {
        if (this.position + value.byteLength > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }

        for (let i = 0; i < value.length; i++) {
            this.view.setUint8(this.position++, value[i]);
        }
    }

    /**
     * Write Uint8 value to buffer
     * @param value Value to write
     */
    writeUint8(value: number | bigint): void {
        if (this.position + 1 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setUint8(this.position++, Number(value));
    }

    /**
     * Write Uint16 value to buffer
     * @param value Value to write
     */
    writeUint16(value: number | bigint): void {
        if (this.position + 2 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setUint16(this.position, Number(value), true);
        this.position += 2;
    }

    /**
     * Write Uint32 value to buffer
     * @param value Value to write
     */
    writeUint32(value: number | bigint): void {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setUint32(this.position, Number(value), true);
        this.position += 4;
    }

    /**
     * Write Uint64 value to buffer
     * @param value Value to write
     */
    writeUint64(value: number | bigint): void {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setBigUint64(this.position, BigInt(value), true);
        this.position += 8;
    }

    /**
     * Write Int8 value to buffer
     * @param value Value to write
     */
    writeInt8(value: number | bigint): void {
        if (this.position + 1 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setInt8(this.position++, Number(value));
    }

    /**
     * Write Int16 value to buffer
     * @param value Value to write
     */
    writeInt16(value: number | bigint): void {
        if (this.position + 2 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setInt16(this.position, Number(value), true);
        this.position += 2;
    }

    /**
     * Write Int32 value to buffer
     * @param value Value to write
     */
    writeInt32(value: number | bigint): void {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setInt32(this.position, Number(value), true);
        this.position += 4;
    }

    /**
     * Write Int64 to buffer
     * @param value Value to write
     */
    writeInt64(value: number | bigint): void {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setBigInt64(this.position, BigInt(value), true);
        this.position += 8;
    }

    /**
     * Write Float64 to buffer
     * @param value Value to write
     */
    writeFloat32(value: number | bigint): void {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setFloat32(this.position, Number(value), true);
        this.position += 4;
    }

    /**
     * Write Float64 to buffer
     * @param value Value to write
     */
    writeFloat64(value: number | bigint): void {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_OVERFLOW_ERR_MSG);
        }
        this.view.setFloat64(this.position, Number(value), true);
        this.position += 8;
    }

    /**
     * Read the message with specific length
     * @param length Length to read
     */
    read(length: number | bigint): Uint8Array {
        if (this.position + Number(length) > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }

        const begin = this.position;
        this.position += Number(length);
        return this.data.subarray(begin, this.position);
    }

    /**
     * Read Uint8 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint8(): number {
        if (this.position + 1 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        return this.view.getUint8(this.position++);
    }

    /**
     * Read Uint16 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint16(): number {
        if (this.position + 2 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getUint16(this.position, true);
        this.position += 2;
        return value;
    }

    /**
     * Read Uint32 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint32(): number {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getUint32(this.position, true);
        this.position += 4;
        return value;
    }

    /**
     * Read Uint64 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint64(): bigint {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getBigUint64(this.position, true);
        this.position += 8;
        return value;
    }

    /**
     * Read Int8 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt8(): number {
        if (this.position + 1 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        return this.view.getInt8(this.position++);
    }

    /**
     * Read Int16 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt16(): number {
        if (this.position + 2 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getInt16(this.position, true);
        this.position += 2;
        return value;
    }

    /**
     * Read Int32 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt32(): number {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getInt32(this.position, true);
        this.position += 4;
        return value;
    }

    /**
     * Read Int64 from buffer
     * @returns Retrieved value from buffer
     */
    readInt64(): bigint {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }
        const value = this.view.getBigInt64(this.position, true);
        this.position += 8;
        return value;
    }

    /**
     * Read the Float32 from buffer
     * @returns Retrieved value from buffer
     */
    readFloat32(): number {
        if (this.position + 4 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }

        const value = this.view.getFloat32(this.position, true);
        this.position += 4;
        return value;
    }

    /**
     * Read Float64 from buffer
     * @returns Retrieved value from buffer
     */
    readFloat64(): number {
        if (this.position + 8 > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }

        const value = this.view.getFloat64(this.position, true);
        this.position += 8;
        return value;
    }

    /**
     * Read packed uint64 value
     */
    readPackedUint64(bytes: number): bigint {
        if (this.position + bytes > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }

        let value = 0n;
        for (let i = 0n; i < bytes; i++) {
            const byte = BigInt(this.readUint8());
            value |= (byte << (i * 8n));
        }

        return value;
    }

    /**
     * Write packed uint64 value
     */
    writePackedUint64(bytes: number, value: bigint) {
        if (this.position + bytes > this.capacity) {
            throw new Error(BUFFER_UNDERFLOW_ERR_MSG);
        }

        for (let i = 0; i < bytes; i++) {
            this.writeUint8(Number(value & 0xFFn));
            value >>= 8n;
        }
    }

    /**
     * Read string from payload (Until NULL terminated character)
     */
    readString(): string {
        // Find index of zero
        let zeroIndex = -1;
        for (let i = this.position; i < this.data.length; i++) {
            if (this.data[i] === 0) {
                zeroIndex = i;
                break;
            }
        }

        if (zeroIndex === -1) {
            return "";
        }

        const data = this.data.subarray(this.position, zeroIndex);
        const text = decodeString(data);

        this.position += (zeroIndex + 1); // Ignore zero
        return text;
    }
}


/**
 * Payloads pool
 */
export class PayloadPool extends Pool<Payload> {
    /**
     * Capacity of each payload
     */
    private capacity: number;

    constructor(capacity: number = 0) {
        super();
        this.capacity = capacity;
    }

    protected create(): Payload {
        return new Payload(this.capacity);
    }
}
