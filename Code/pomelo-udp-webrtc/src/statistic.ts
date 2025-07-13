/**
 * Statistic information of socket
 */
export interface Statistic {
    /**
     * Statistic of webrtc
     */
    webrtc: {
        /**
         * Total sent bytes
         */
        totalSentBytes: bigint;

        /**
         * Total received bytes
         */
        totalRecvBytes: bigint;
    };
}
