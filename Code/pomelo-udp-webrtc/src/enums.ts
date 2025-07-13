/**
 * Channel mode
 */
export enum ChannelMode {
    UNRELIABLE = 0,
    SEQUENCED = 1,
    RELIABLE = 2
};

/**
 * Connect result of socket
 */
export enum ConnectResult {
    SUCCESS = 0,
    DENIED = -1,
    TIMED_OUT = -2
};
