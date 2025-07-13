import Message from "./message";
import Signal from "./utils/signal";
import { Statistic } from "./statistic";
import { ChannelMode } from "./enums";
import Payload from "./utils/payload";


/* -------------------------------------------------------------------------- */
/*                                Interface                                   */
/* -------------------------------------------------------------------------- */


/**
 * Channel
 */
export default interface Channel {
    /**
     * The channel mode
     */
    mode: ChannelMode;

    /**
     * Send message by specific channel
     * @param message The message to send
     */
    send(message: Message): boolean;
}


/* -------------------------------------------------------------------------- */
/*                             Implementation                                 */
/* -------------------------------------------------------------------------- */

// Just a trick to access payload of message
interface OutgoingMessage {
    payload: Payload;
};


/**
 * Implement of channel
 */
export class ChannelImpl implements Channel {
    /**
     * Outgoing data channel
     */
    private outgoingDataChannel: RTCDataChannel;

    /**
     * Incoming data channel
     */
    private incomingDataChannel: RTCDataChannel | null = null;

    /**
     * Opened signal
     */
    readonly onOpened = new Signal<() => void>();

    /**
     * Closed signal
     */
    readonly onClosed = new Signal<() => void>();

    /**
     * Message signal
     */
    readonly onData = new Signal<(message: ArrayBuffer) => void>();

    /**
     * Statistic
     */
    private statistic: Statistic;

    /**
     * Active flag
     */
    private active = true;

    /**
     * Current channel mode
     */
    private channelMode: ChannelMode;

    constructor(
        mode: ChannelMode,
        outgoingDataChannel: RTCDataChannel,
        statistic: Statistic
    ) {
        this.channelMode = mode;
        this.outgoingDataChannel = outgoingDataChannel;
        outgoingDataChannel.onopen = () => this.onOpened.emit();
        outgoingDataChannel.onclose = () => this.close();
        this.statistic = statistic;
    }

    /**
     * Set incoming data channel
     */
    setIncomingDataChannel(incomingDataChannel: RTCDataChannel) {
        const statistic = this.statistic;
        incomingDataChannel.onclose = () => this.close();
        incomingDataChannel.onmessage = (event) => {
            const data = event.data;
            if (data instanceof ArrayBuffer) {
                statistic.webrtc.totalRecvBytes += BigInt(data.byteLength);
                this.onData.emit(data);
            }
        }
        this.incomingDataChannel = incomingDataChannel;
    }

    send(message: Message | ArrayBufferView): boolean {
        if (!this.active) return false;

        if (message instanceof Message) {
            const buffer = (<unknown>message as OutgoingMessage).payload.pack();
            this.outgoingDataChannel.send(buffer);
            this.statistic.webrtc.totalSentBytes += BigInt(buffer.byteLength);
        } else {
            this.outgoingDataChannel.send(message);
            this.statistic.webrtc.totalSentBytes += BigInt(message.byteLength);
        }

        return true;
    }

    /**
     * Close the channel
     * @returns 
     */
    close(): void {
        if (!this.active) return;
        this.active = false;
        this.outgoingDataChannel.close();
        this.incomingDataChannel?.close();
        this.onClosed.emit();
    }

    set mode(channelMode: ChannelMode) {
        throw new Error("Method not implemented");
    }

    get mode() {
        return this.channelMode;
    }
}
