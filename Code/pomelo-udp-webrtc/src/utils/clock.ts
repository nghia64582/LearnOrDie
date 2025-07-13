import hrtime from "./hrtime";
import SampleSet from "./sampling";
import { RTTCalculator } from "./rtt";

const POMELO_PROTOCOL_CLOCK_RECENT_OFFSETS_SIZE = 10;

function SQR(value: bigint): bigint {
    return value * value;
}

const POMELO_TIME_CONDITION_RTT_VAR_HIGH   = SQR(10000000n)     // 10 ms
const POMELO_TIME_CONDITION_RTT_VAR_MEDIUM = SQR(5000000n)      // 5 ms
const POMELO_TIME_CONDITION_RTT_VAR_LOW    = SQR(5000000n)      // 5 ms

const POMELO_TIME_HIGH_MIN_TIMES_OF_PING   = 20
const POMELO_TIME_HIGH_THRESHOLD_RTT_VAR   = SQR(5000000n)      // 5ms

const POMELO_TIME_HIGH_MIN_DELTA_OFFSET    = 5000000n            // 5ms

const POMELO_TIME_MEDIUM_THRESHOLD_RECENT_OFFSETS_VAR = SQR(5000000n) // 5ms
const POMELO_TIME_MEDIUM_MIN_DELTA_OFFSET = 10000000n            // 10ms

const POMELO_TIME_LOW_MIN_DELTA_MEAN_RECENT_OFFSETS = 10000000n  // 10ms

function calcDeltaOffset(first: bigint, second: bigint) {
    return (first > second) ? (first - second) : (second - first);
}

/**
 * Sync level
 */
enum ClockSyncLevel {
    HIGH,
    MEDIUM,
    LOW
}

/**
 * Clock of socket
 */
export default class Clock {
    /**
     * RTT
     */
    private rtt: RTTCalculator;

    /**
     * Current sync level
     */
    private level = ClockSyncLevel.HIGH;

    /**
     * Recent offsets
     */
    private recentOffsets =
        new SampleSet(POMELO_PROTOCOL_CLOCK_RECENT_OFFSETS_SIZE);

    /**
     * High sync count
     */
    private highSyncCount = 0;

    /**
     * Current clock offset
     */
    offset = 0n;

    constructor(rtt: RTTCalculator) {
        this.rtt = rtt;
    }

    /**
     * Set clock value
     */
    set(value: bigint) {
        this.offset = value - hrtime();
    }

    /**
     * Synchronize clock
     */
    sync(
        reqSendTime: bigint,
        reqRecvTime: bigint,
        resSendTime: bigint,
        resRecvTime: bigint
    ): boolean {
        const offset = (
            (reqRecvTime - reqSendTime) +
            (resSendTime - resRecvTime)
        ) / 2n;

        this.recentOffsets.submit(offset);
        switch (this.level) {
            case ClockSyncLevel.HIGH:
                return this.syncHigh(offset);

            case ClockSyncLevel.MEDIUM:
                return this.syncMedium(offset);

            case ClockSyncLevel.LOW:
                return this.syncLow(offset);
        }
    }

    private syncHigh(offset: bigint): boolean {
        const rttVar = this.rtt.variance;
        if (rttVar > POMELO_TIME_CONDITION_RTT_VAR_HIGH) {
            return false;
        }
    
        if (this.highSyncCount < POMELO_TIME_HIGH_MIN_TIMES_OF_PING) {
            this.highSyncCount++;
        } else if (rttVar < POMELO_TIME_HIGH_THRESHOLD_RTT_VAR) {
            // More stable, downgrade level
            this.level = ClockSyncLevel.MEDIUM;
        }
    
        const deltaOffset = calcDeltaOffset(offset, this.offset);
        if (deltaOffset > POMELO_TIME_HIGH_MIN_DELTA_OFFSET) {
            this.offset = offset;
            return true;
        }
    
        return false;
    }

    private syncMedium(offset: bigint): boolean {
        const rttVar = this.rtt.variance;
        if (rttVar > POMELO_TIME_CONDITION_RTT_VAR_MEDIUM) {
            return false;
        }
    
        const variance = this.recentOffsets.calc().variance;
        if (variance < POMELO_TIME_MEDIUM_THRESHOLD_RECENT_OFFSETS_VAR) {
            this.level = ClockSyncLevel.LOW;
        }
    
        const deltaOffset = calcDeltaOffset(offset, this.offset);
        if (deltaOffset > POMELO_TIME_MEDIUM_MIN_DELTA_OFFSET) {
            this.offset = offset;
            return true;
        }
    
        return false;
    }

    private syncLow(offset: bigint): boolean {
        const rttVar = this.rtt.variance;
        if (rttVar > POMELO_TIME_CONDITION_RTT_VAR_LOW) {
            return false;
        }
    
        const mean = this.recentOffsets.calc().mean;
        const deltaOffset = calcDeltaOffset(mean, offset);
        if (deltaOffset > POMELO_TIME_LOW_MIN_DELTA_MEAN_RECENT_OFFSETS) {
            this.offset = mean;
            return true;
        }
    
        return false;
    }
}
