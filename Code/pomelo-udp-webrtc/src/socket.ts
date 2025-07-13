import { ChannelMode, ConnectResult } from "./enums";
import { POMELO_CONNECT_TOKEN_BYTES } from "./constants";
import Message, { MessagePool } from "./message";
import Session, { SessionImpl } from "./session";
import { Statistic } from "./statistic";
import { decodeTokenPublic } from "./token";
import hrtime from "./utils/hrtime";
import { decodeBase64, encodeBase64 } from "./utils/string";


/**
 * Socket listener
 */
export interface SocketListener {
    /**
     * Peer connected callback.
     * @param session Created session
     */
    onConnected(session: Session): void;

    /**
     * Peer disconected callback
     * @param session 
     */
    onDisconnected(session: Session): void;

    /**
     * This callback is called when a message has been arrived to this peer.
     * The message WILL BE INVALID after this callback.
     * @param session The sender
     * @param message The incoming message
     */
    onReceived(session: Session, message: Message): void;
}

/**
 * Default listener
 */
const DefaultListener: SocketListener = {
    onConnected: function() {},
    onDisconnected: function() {},
    onReceived: function() {}
}


/**
 * Socket
 */
export default class Socket {
    /**
     * The current listener
     */
    private listener = DefaultListener;

    /**
     * The current session
     */
    private session: SessionImpl | null = null;

    /**
     * Statistic of socket
     */
    private socketStatistic: Statistic = {
        webrtc: {
            totalRecvBytes: 0n,
            totalSentBytes: 0n
        }
    };

    /**
     * Channel modes
     */
    private channelModes: ChannelMode[];

    constructor(channelModes: ChannelMode[]) {
        this.channelModes = channelModes;
    }

    /**
     * Set the socket listener
     * @param listener Socket listener
     */
    setListener(listener: SocketListener) {
        this.listener = listener;
    }

    /**
     * Start the socket as a client.
     * @param connectToken The connect token
     * @returns Return a project which will resolve the connection result and
     * reject on error
     */
    async connect(connectToken: Uint8Array | string): Promise<ConnectResult> {
        let token: Uint8Array;
        let tokenB64: string
        if (typeof connectToken === "string") {
            tokenB64 = connectToken;
            token = decodeBase64(connectToken);
        } else {
            tokenB64 = encodeBase64(connectToken);
            token = connectToken;
        }

        if (token.byteLength !== POMELO_CONNECT_TOKEN_BYTES) {
            throw new Error(
                `Invalid connect token: Length = ${token.byteLength}`
            );
        }
        
        const info = decodeTokenPublic(token);
        const statistic = this.socketStatistic;
        const modes = this.channelModes;

        // Try each address to connect
        let result = ConnectResult.DENIED;
        for (let i = 0; i < info.serverAddresses.length; i++) {
            const address = info.serverAddresses[i];
            const session = new SessionImpl(
                modes, tokenB64, address, statistic, info.timeout
            );
            session.onClosed.connect(() => {
                this.listener.onDisconnected(session)
            });
            session.onMessage.connect(message => {
                this.listener.onReceived(session, message)
            });
            result = await session.onConnectResult.once();
            if (result === ConnectResult.SUCCESS) {
                this.session = session;
                this.listener.onConnected(session);
                return ConnectResult.SUCCESS;
            }
        }

        return result;
    }

    /**
     * Stop the socket
     * @returns Returns a promise which resolves when the socket stops
     * completely.
     */
    stop(): Promise<void> {
        this.session?.disconnect();
        this.session = null;
        return Promise.resolve();
    }

    /**
     * Send a message to multiple recipients
     * @param chanelIndex The sending channel index
     * @param message The message
     * @param recipients List of recipients
     */
    send(
        channelIndex: number,
        message: Message,
        recipients: Session[]
    ): number {
        const result = recipients.reduce((sum, recipient) => {
            if (recipient.send(channelIndex, message)) {
                return sum + 1;
            }
            return sum;
        }, 0);
        MessagePool.instance.release(message);
        return result;
    }

    /**
     * Get the socket statistic
     */
    statistic(): Statistic {
        return this.socketStatistic;
    }

    /**
     * Get synchronized socket time
     */
    time(): bigint {
        return hrtime() + (this.session ? this.session.offset() : 0n);
    }
}
