import Channel, { ChannelImpl } from "./channel";
import Clock from "./utils/clock";
import { RTT, RTTCalculator } from "./utils/rtt";
import Message from "./message";
import { TokenServerAddress } from "./token";
import hrtime from "./utils/hrtime";
import Payload, { PayloadPool } from "./utils/payload";
import Signal from "./utils/signal";
import Pool from "./utils/pool";
import { Statistic } from "./statistic";
import { ChannelMode, ConnectResult } from "./enums";


/* -------------------------------------------------------------------------- */
/*                                Interface                                   */
/* -------------------------------------------------------------------------- */

const CLIENT_CHANNEL_PREFIX = "client-channel-";
const SERVER_CHANNEL_PREFIX = "server-channel-";
const SYSTEM_CHANNEL_LABEL = "system";


/**
 * The connected session
 */
export default interface Session {
    /**
     * The session ID
     */
    readonly id: bigint;

    /**
     * The channels of session
     */
    readonly channels: Channel[];

    /**
     * The custom data for session
     */
    data?: any;

    /**
     * Send message to the peer connected by this session
     * @param channelIndex The channel to send
     * @param message The message to send
     * @returns Returns false if session is disconnected
     */
    send(channelIndex: number, message: Message): boolean;

    /**
     * Set mode for specific channel of a session
     * This is equivalent to getting channel and setting channel mode.
     * @param channelIndex Index of channel
     * @param mode Channel mode
     */
    setChannelMode(channelIndex: number, mode: ChannelMode): boolean;

    /**
     * Get the channel mode of a channel by index
     * @param channelIndex Channel index
     * @returns Mode of channel
     */
    getChannelMode(channelIndex: number): ChannelMode;
    
    /**
     * Disconnect this session.
     * @returns Returns false if session is disconnected
     */
    disconnect(): boolean;

    /**
     * Get the round trip time information of session
     */
    rtt(): RTT;
}


/* -------------------------------------------------------------------------- */
/*                             Implementation                                 */
/* -------------------------------------------------------------------------- */

const OPCODE_AUTH = "AUTH";
const OPCODE_DESCRIPTION = "DESC";
const OPCODE_CANDIDATE = "CAND";
const OPCODE_READY = "READY";
const OPCODE_CONNECTED = "CONN";

const MESSAGE_SEPARATOR = "|";

const AUTH_RESULT_OK = "OK";

const SYS_OPCODE_PING = 0;
const SYS_OPCODE_PONG = 1;

// 1 byte for meta + max 8 bytes for sequence
const PING_PONG_MESSAGE_CAPACITY = 9;

const PING_INTERVAL_MS = 100;

const RTCChannelOptions: RTCDataChannelInit[] = [
    { maxRetransmits: 0, ordered: false },  // UNRELIABLE
    { maxRetransmits: 0, ordered: true },   // SEQUENCED
    { ordered: true }                       // RELIABLE
];


class ReadyFlags {
    /**
     * All channels opened flag
     */
    allChannelsOpened = false;

    /**
     * Ready signal received flag
     */
    readySignalReceived = false;

    /**
     * Check if all flags are fulfill
     */
    areFulfill(): boolean {
        return this.allChannelsOpened && this.readySignalReceived;
    }
};


const IncomingPingPongPool = new PayloadPool();
const OutgoingPingPongPool = new PayloadPool(PING_PONG_MESSAGE_CAPACITY);


/**
 * Incoming message
 */
class IncomingMessage extends Message {
    setData(buffer: ArrayBuffer) {
        this.payload.prepare(buffer);
    }
}


/**
 * Incoming messages pool
 */
class IncomingMessagePool extends Pool<IncomingMessage> {
    /**
     * Instance of incoming message pool
     */
    static readonly instance = new IncomingMessagePool();

    protected create(): IncomingMessage {
        return new IncomingMessage();
    }
}


/**
 * Implementation of session
 */
export class SessionImpl implements Session {
    data?: any = null;

    id: bigint = -1n;

    readonly channels: ChannelImpl[];

    /**
     * Authenticating result signal
     */
    readonly onConnectResult = new Signal<(result: ConnectResult) => void>();

    /**
     * Closed signal
     */
    readonly onClosed = new Signal<() => void>();
    
    /**
     * Signal message
     */
    readonly onMessage = new Signal<(message: Message) => void>();

    /**
     * WebSocket connection
     */
    private ws: WebSocket;

    /**
     * RTC connection
     */
    private pc: RTCPeerConnection;

    /**
     * Round trip time calculator
     */
    private rttCalc = new RTTCalculator();

    /**
     * Clock
     */
    private clock = new Clock(this.rttCalc);

    /**
     * Active flag
     */
    private active = true;

    /**
     * System channel. TODO: Convert this channel as logic channel
     */
    private systemChannel: ChannelImpl | null = null;

    /**
     * Ping inteval
     */
    private pingInterval: any = null;

    /**
     * Connect timeout scheduler
     */
    private connectTimeout: any = null;

    /**
     * Flags of session
     */
    private readyFlags = new ReadyFlags();

    /**
     * Connected state
     */
    private connected = false;

    constructor(
        channelModes: ChannelMode[],
        connectToken: string,
        address: TokenServerAddress,
        statistic: Statistic,
        timeout: number,
        rtcConfig: RTCConfiguration = {}
    ) {
        this.ws = new WebSocket(`ws://${address.host}:${address.port}`);
        this.ws.onopen = () => this.sendWS(OPCODE_AUTH, connectToken);
        this.ws.onclose = () => this.close();
        this.ws.onerror = (event) => console.error("WS error", event);
        this.ws.onmessage = (event) => this.handleWSMessage(event);
        this.pc = new RTCPeerConnection(rtcConfig);

        // Include the system channel
        const totalChannels = channelModes.length + 1;
        let openedChannels = 0;
        this.channels = channelModes.map((mode, index) => {
            const name = CLIENT_CHANNEL_PREFIX + index;
            const dc = this.pc.createDataChannel(name, RTCChannelOptions[mode]);
            const channel = new ChannelImpl(mode, dc, statistic);
            channel.onClosed.connect(() => this.close());
            channel.onData.connect(buffer => {
                const message = IncomingMessagePool.instance.acquire();
                message.setData(buffer);
                this.onMessage.emit(message);
                IncomingMessagePool.instance.release(message);
            });
            channel.onOpened.connect(() => {
                if (++openedChannels === totalChannels) {
                    this.handleAllChannelsOpened();
                }
            });
            return channel;
        });

        this.pc.onicecandidate = ({ candidate }) => {
            if (!candidate) return;
            const mid = candidate.sdpMid || "";
            this.sendWS(OPCODE_CANDIDATE, mid, candidate.candidate);
        }
        this.pc.onconnectionstatechange = () => {
            switch (this.pc.connectionState) {
                case "disconnected":
                case "failed":
                    this.pc.close();
                    break;
                
                case "closed":
                    this.close();
                    break;
            }
        }
        this.pc.ondatachannel = (event) => {
            const dc = event.channel;
            const label = dc.label;
            if (label === SYSTEM_CHANNEL_LABEL) {
                // Create system channel
                if (this.systemChannel) return;
                this.systemChannel = new ChannelImpl(
                    ChannelMode.UNRELIABLE, // System channel is unreliable
                    dc,
                    statistic
                );
                // Set incoming data channel the same as outgoing channel
                this.systemChannel.setIncomingDataChannel(dc);
                this.systemChannel.onData.connect((data) => {
                    this.handleSystemMessage(data, hrtime());
                });
                this.systemChannel.onClosed.connect(() => this.close());
                if (++openedChannels === totalChannels) {
                    this.handleAllChannelsOpened();
                }
                return;
            }

            if (!label.startsWith(SERVER_CHANNEL_PREFIX)) return;
            const channelIndex = parseInt(
                label.substring(SERVER_CHANNEL_PREFIX.length)
            );
            this.channels[channelIndex]?.setIncomingDataChannel(dc);
        }

        if (timeout > 0) {
            this.connectTimeout = setTimeout(() => {
                this.close();
                this.onConnectResult.emit(ConnectResult.TIMED_OUT);
            }, timeout * 1000);
        } else {
            console.warn("Timeout is not positive: " + timeout);
        }
    }

    send(channelIndex: number, message: Message): boolean {
        const channel = this.channels[channelIndex];
        if (!channel) return false;
        return channel.send(message);
    }

    setChannelMode(channelIndex: number, mode: ChannelMode): boolean {
        const channel = this.channels[channelIndex];
        if (!channel) {
            return false;
        }

        return true;
    }

    getChannelMode(channelIndex: number): ChannelMode {
        const channel = this.channels[channelIndex];
        if (!channel) {
            return ChannelMode.UNRELIABLE;
        }
        return channel.mode;
    }

    disconnect(): boolean {
        return this.close();
    }

    rtt(): RTT {
        return this.rttCalc;
    }

    offset(): bigint {
        return this.clock.offset;
    }

    /**
     * Close the connection
     */
    private close(): boolean {
        if (!this.active) return false; // Session has been deactivated

        this.active = false;
        this.channels.forEach(channel => channel?.close());
        this.pc.close();
        this.ws.close();
        if (this.pingInterval !== null) {
            // Stop pinging
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }

        this.onClosed.emit();

        return true;
    }

    private sendWS(...params: string[]) {
        this.ws.send(params.join(MESSAGE_SEPARATOR));
    }

    /**
     * Handle message event
     * @param event 
     */
    private async handleWSMessage(event: MessageEvent) {
        const data = event.data as Blob;
        const message = await data.text();
        const fields = message.split(MESSAGE_SEPARATOR);
        const opcode = fields[0];
        console.log("Handle opcode:", opcode);
        switch (opcode) {
            case OPCODE_AUTH:
                this.handleAuthMessage(fields);
                break;
            
            case OPCODE_DESCRIPTION:
                if (fields.length == 3) {
                    this.handleRemoteDescription(fields[1], fields[2]);
                }
                break;
            
            case OPCODE_CANDIDATE:
                if (fields.length == 3) {
                    this.handleRemoteCandidate(fields[1], fields[2]);
                }
                break;
            
            case OPCODE_READY:
                if (this.readyFlags.readySignalReceived) {
                    break; // Already received
                }
                this.readyFlags.readySignalReceived = true;
                if (this.readyFlags.areFulfill()) {
                    this.processReady();
                }
                break;

            case OPCODE_CONNECTED:
                if (this.connected) {
                    break; // Already received connected
                }
                this.connected = true;
                // Emit signal
                this.onConnectResult.emit(ConnectResult.SUCCESS);
                break;
        }
    }

    /**
     * Handle auth message
     */
    private handleAuthMessage(fields: string[]) {
        if (fields.length < 2) return; // Invalid auth message

        if (fields[1] !== AUTH_RESULT_OK) {
            // Failed
            this.onConnectResult.emit(ConnectResult.DENIED);
            return;
        }

        if (fields.length !== 4) return; // Invalid auth response
        
        let id: bigint;
        try {
            id = BigInt(fields[2]);
        } catch (ex) {
            return; // Failed to parse ID
        }

        // Include sys-channel
        this.id = id;
        let time: bigint;
        try {
            time = BigInt(fields[3]);
        } catch (ex) {
            return; // Failed to parse time
        }
        this.clock.set(time);
    }

    /**
     * Handle remote description
     */
    private async handleRemoteDescription(type: string, sdp: string) {
        // Set remote offer and create answer.
        await this.pc.setRemoteDescription({ sdp, type: type as RTCSdpType });
        await this.pc.setLocalDescription();
        const description = this.pc.localDescription;
        if (!description) {
            return;
        }
        // Send local description
        this.sendWS(OPCODE_DESCRIPTION, description.type, description.sdp);
    }

    /**
     * Handle remote candidate
     */
    private async handleRemoteCandidate(mid: string, cand: string) {
        this.pc.addIceCandidate({ candidate: cand, sdpMid: (mid || null) });
    }

    /**
     * Handle system message
     */
    private handleSystemMessage(buffer: ArrayBuffer, recvTime: bigint) {
        if (buffer.byteLength < 1) {
            return; // Invalid message
        }
        
        const data = new Uint8Array(buffer);
        const opcode = (data[0] >> 6);
        switch (opcode) {
            case SYS_OPCODE_PING:
                this.handlePingMessage(data, recvTime);
                break;

            case SYS_OPCODE_PONG:
                this.handlePongMessage(data, recvTime);
                break;
        }
    }

    /**
     * Process ping message
     */
    private handlePingMessage(buffer: Uint8Array, recvTime: bigint) {
        const payload = IncomingPingPongPool.acquire();
        payload.prepare(buffer);
        const header = payload.readUint8();
        const sequenceBytes = ((header >> 3) & 0x07) + 1;
        const sequence = payload.readPackedUint64(sequenceBytes);
        this.replyPongMessage(sequence, recvTime);
        payload.release();
    }

    /**
     * Process pong message
     */
    private handlePongMessage(buffer: Uint8Array, recvTime: bigint) {
        const payload = IncomingPingPongPool.acquire();
        payload.prepare(buffer);
        const header = payload.readUint8();
        const sequenceBytes = ((header >> 3) & 0x07) + 1;
        const socketTimeBytes = (header & 0x07) + 1;

        const sequence = payload.readPackedUint64(sequenceBytes);
        const socketTime = payload.readPackedUint64(socketTimeBytes);
        payload.release();

        const entry = this.rttCalc.entry(sequence);
        if (!entry) {
            return;
        }
        const sendTime = entry.time;
        this.rttCalc.submit(entry, recvTime, 0n);
        this.clock.sync(
            sendTime,
            socketTime,
            socketTime,
            recvTime
        );
    }

    /**
     * Reply pong message
     */
    private replyPongMessage(sequence: bigint, recvTime: bigint) {
        const payload = OutgoingPingPongPool.acquire();
        const sequenceBytes = Payload.calcPackedUint64Bytes(sequence);

        const header = (
            (SYS_OPCODE_PONG << 6) |
            (((sequenceBytes - 1) & 0x07) << 3)
        );
        payload.writeUint8(header);
        payload.writePackedUint64(sequenceBytes, sequence);
        // Socket time is ignored here, so no need to pack it.

        const buffer = payload.pack();
        this.systemChannel?.send(buffer);
        payload.release();
    }

    /**
     * All channels have opened
     */
    private handleAllChannelsOpened() {
        // Send ready message
        this.sendWS(OPCODE_READY);

        // Start pinging
        this.pingInterval =
            setInterval(() => this.sendPingMessage(), PING_INTERVAL_MS);
        
        this.readyFlags.allChannelsOpened = true;
        if (this.readyFlags.areFulfill()) {
            this.processReady();
        }
    }

    /**
     * Process ready state
     */
    private processReady() {
        // Clear timeout signal
        if (this.connectTimeout !== null) {
            clearTimeout(this.connectTimeout);
            this.connectTimeout = null;
        }
    }

    /**
     * Send ping message
     */
    private sendPingMessage() {
        const payload = OutgoingPingPongPool.acquire();
        const entry = this.rttCalc.next(hrtime());
        const sequence = entry.sequence;
        const sequenceBytes = Payload.calcPackedUint64Bytes(sequence);

        const header = (
            (SYS_OPCODE_PING << 6) |
            (((sequenceBytes - 1) & 0x07) << 3)
        );
        payload.writeUint8(header);
        payload.writePackedUint64(sequenceBytes, sequence);

        this.systemChannel?.send(payload.pack());
        payload.release();
    }
}
