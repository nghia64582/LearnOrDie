import { POMELO_MESSAGE_CAPACITY } from "./constants";
import Payload from "./utils/payload";
import Pool from "./utils/pool";


/**
 * Pool of messages
 */
export class MessagePool extends Pool<Message> {
    /**
     * Instance of message pool
     */
    static readonly instance = new MessagePool();

    protected create(): Message {
        return new Message();
    }
}


/**
 * Message for sending and receiving.
 * No releasing messages will NOT cause memory leak.
 * But it is highly recommended to release messages to take avantage of pool.
 * This helps GC to have less works to do.
 */
export default class Message {
    /**
     * Payload of message
     */
    protected readonly payload = new Payload();

    /**
     * Acquire a message from pool to send
     */
    static acquire(): Message {
        const message = MessagePool.instance.acquire();
        message.payload.prepare(POMELO_MESSAGE_CAPACITY);
        return message;
    }

    /**
     * Release message to pool
     */
    static release(message: Message): void {
        MessagePool.instance.release(message);
    }

    /**
     * Get the size of message
     */
    size(): number {
        return this.payload.capacity;
    }

    /**
     * Write data to the buffer
     * @param value The uint8 typed array to write
     */
    write(value: Uint8Array): void {
        this.payload.write(value);
    }

    /**
     * Write Uint8 value to buffer
     * @param value Value to write
     */
    writeUint8(value: number | bigint): void {
        this.payload.writeUint8(value);
    }

    /**
     * Write Uint16 value to buffer
     * @param value Value to write
     */
    writeUint16(value: number | bigint): void {
        this.payload.writeUint16(value);
    }

    /**
     * Write Uint32 value to buffer
     * @param value Value to write
     */
    writeUint32(value: number | bigint): void {
        this.payload.writeUint32(value);
    }

    /**
     * Write Uint64 value to buffer
     * @param value Value to write
     */
    writeUint64(value: number | bigint): void {
        this.payload.writeUint64(value);
    }

    /**
     * Write Int8 value to buffer
     * @param value Value to write
     */
    writeInt8(value: number | bigint): void {
        this.payload.writeInt8(value);
    }

    /**
     * Write Int16 value to buffer
     * @param value Value to write
     */
    writeInt16(value: number | bigint): void {
        this.payload.writeInt16(value);
    }

    /**
     * Write Int32 value to buffer
     * @param value Value to write
     */
    writeInt32(value: number | bigint): void {
        this.payload.writeInt32(value);
    }

    /**
     * Write Int64 to buffer
     * @param value Value to write
     */
    writeInt64(value: number | bigint): void {
        this.payload.writeInt64(value);
    }

    /**
     * Write Float64 to buffer
     * @param value Value to write
     */
    writeFloat32(value: number | bigint): void {
        this.payload.writeFloat32(value);
    }

    /**
     * Write Float64 to buffer
     * @param value Value to write
     */
    writeFloat64(value: number | bigint): void {
        this.payload.writeFloat64(value);
    }

    /**
     * Read the message with specific length
     * @param length Length to read
     */
    read(length: number | bigint): Uint8Array {
        return this.payload.read(length);
    }

    /**
     * Read Uint8 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint8(): number {
        return this.payload.readUint8();
    }

    /**
     * Read Uint16 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint16(): number {
        return this.payload.readUint16();
    }

    /**
     * Read Uint32 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint32(): number {
        return this.payload.readUint32();
    }

    /**
     * Read Uint64 value from buffer
     * @returns Retrieved value from buffer
     */
    readUint64(): bigint {
        return this.payload.readUint64();
    }

    /**
     * Read Int8 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt8(): number {
        return this.payload.readInt8();
    }

    /**
     * Read Int16 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt16(): number {
        return this.payload.readInt16();
    }

    /**
     * Read Int32 value from buffer
     * @returns Retrieved value from buffer
     */
    readInt32(): number {
        return this.payload.readInt32();
    }

    /**
     * Read Int64 from buffer
     * @returns Retrieved value from buffer
     */
    readInt64(): bigint {
        return this.payload.readInt64();
    }

    /**
     * Read the Float32 from buffer
     * @returns Retrieved value from buffer
     */
    readFloat32(): number {
        return this.payload.readFloat32();
    }

    /**
     * Read Float64 from buffer
     * @returns Retrieved value from buffer
     */
    readFloat64(): number {
        return this.payload.readFloat64();
    }
}
