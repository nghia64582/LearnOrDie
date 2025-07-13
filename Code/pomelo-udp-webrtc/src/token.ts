import { POMELO_ADDRESS_IPV4, POMELO_ADDRESS_IPV6, POMELO_CONNECT_TOKEN_NONCE_BYTES, POMELO_ENCRYPTED_PRIVATE_CONNECT_TOKEN_BYTES, POMELO_KEY_BYTES } from "./constants";
import Payload, { PayloadPool } from "./utils/payload";

/**
 * Server address of token
 * <for each server address>
 *  {
 *      [address_type] (uint8) // value of 1 = IPv4 address, 2 = IPv6 address.
 *      <if IPV4 address>
 *      {
 *          // for a given IPv4 address: a.b.c.d:port
 *          [a] (uint8)
 *          [b] (uint8)
 *          [c] (uint8)
 *          [d] (uint8)
 *          [port] (uint16)
 *      }
 *      <else IPv6 address>
 *      {
 *          // for a given IPv6 address: [a:b:c:d:e:f:g:h]:port
 *          [a] (uint16)
 *          [b] (uint16)
 *          [c] (uint16)
 *          [d] (uint16)
 *          [e] (uint16)
 *          [f] (uint16)
 *          [g] (uint16)
 *          [h] (uint16)
 *          [port] (uint16)
 *      }
 *  }
 */
export interface TokenServerAddress {
    host: string,
    port: number
}


/**
 * Information of public portion of connect token
 */
export interface TokenPublicInfo {
    versionInfo: string, // string
    protocolID: bigint,  // uint64
    createTimestamp: bigint, // uint64
    expireTimestamp: bigint, // uint64
    connectTokenNonce: Uint8Array, // 24 bytes
    timeout: number, // int32
    encryptedPrivateConnectTokenData: Uint8Array, // 1024 bytes
    // num_server_addresses: uint32,
    serverAddresses: TokenServerAddress[], // array[1-32]
    clientToServerKey: Uint8Array, // 32 bytes
    serverToClientKey: Uint8Array  // 32 bytes
}

/**
 * Decode server address IPv4
 */
function decodeServerAddressIPv4(payload: Payload): TokenServerAddress {
    const host = [
        payload.readUint8(),
        payload.readUint8(),
        payload.readUint8(),
        payload.readUint8()
    ];

    const port = payload.readUint16();
    return {
        host: host.join('.'),
        port: port
    };
}

/**
 * Decode server address IPv6
 */
function decodeServerAddressIPv6(payload: Payload): TokenServerAddress {
    const host = [
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16(),
        payload.readUint16()
    ];
    const port = payload.readUint16();
    return {
        host: host.map(e => e.toString(16).padStart(2, "0")).join(":"),
        port: port
    };
}

/**
 * Decode server addresses
 */
function decodeServerAddresses(payload: Payload): TokenServerAddress[] {
    const naddresses = payload.readUint32();
    const addresses: TokenServerAddress[] = [];
    for (let i = 0; i < naddresses; i++) {
        const type = payload.readUint8();
        switch (type) {
            case POMELO_ADDRESS_IPV4:
                addresses.push(decodeServerAddressIPv4(payload));
                break;
            case POMELO_ADDRESS_IPV6:
                addresses.push(decodeServerAddressIPv6(payload));
                break;
        }
    }
    return addresses;
}

const TokenPayloadPool = new PayloadPool();

/**
 * Decode public portion of connect token
 * @param connectToken Connect token
 * @returns Info of public portion of connect token
 */
export function decodeTokenPublic(connectToken: Uint8Array): TokenPublicInfo {
    const payload = TokenPayloadPool.acquire();
    payload.prepare(connectToken);
    const versionInfo = payload.readString();
    const protocolID = payload.readUint64();
    const createTimestamp = payload.readUint64();
    const expireTimestamp = payload.readUint64();
    const connectTokenNonce = payload.read(POMELO_CONNECT_TOKEN_NONCE_BYTES);
    const encryptedPrivateConnectTokenData =
        payload.read(POMELO_ENCRYPTED_PRIVATE_CONNECT_TOKEN_BYTES);
    const timeout = payload.readInt32();
    const serverAddresses = decodeServerAddresses(payload);
    const clientToServerKey = payload.read(POMELO_KEY_BYTES);
    const serverToClientKey = payload.read(POMELO_KEY_BYTES);
    payload.release();

    return {
        versionInfo,
        protocolID,
        createTimestamp,
        expireTimestamp,
        connectTokenNonce,
        timeout,
        encryptedPrivateConnectTokenData,
        serverAddresses,
        clientToServerKey,
        serverToClientKey
    };
}
