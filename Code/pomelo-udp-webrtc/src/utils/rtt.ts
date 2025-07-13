import SampleSet from "./sampling";


const POMELO_RTT_SAMPLE_SET_SIZE = 10n;
const POMELO_RTT_ENTRY_BUFFER_SIZE = 20n;
const POMELO_RTT_MAX_SEQUENCE = 0xFFFFn;

/**
 * Round trip time
 */
export interface RTT {
    /**
     * The mean of round trip time
     */
    mean: bigint;

    /**
     * The variance of round trip time
     */
    variance: bigint;
}



/**
 * An entry of RTT
 */
export interface RTTEntry {
    /**
     * Sent time
     */
    time: bigint;

    /**
     * Valid flag
     */
    valid: boolean;

    /**
     * Sequence number of this entry
     */
    sequence: bigint;
}

/**
 * Round trip time calculator
 */
export class RTTCalculator implements RTT {
    /**
     * Mean of RTT
     */
    mean = 0n;

    /**
     * Variance
     */
    variance = 0n;

    /**
     * Current sequence of latest entry
     */
    private entrySequence = 0n;

    /**
     * RTT entries
     */
    private entries: RTTEntry[] = [];

    /**
     * RTT sample set
     */
    private sample = new SampleSet(POMELO_RTT_SAMPLE_SET_SIZE);

    constructor() {
        for (let i = 0n; i < POMELO_RTT_ENTRY_BUFFER_SIZE; i++) {
            this.entries.push({ time: 0n, valid: false, sequence: 0n });
        }
    }

    /**
     * Find entry
     * @param sequence 
     */
    entry(sequence: bigint): RTTEntry | null {
        const index = sequence % POMELO_RTT_ENTRY_BUFFER_SIZE;
        const entry = this.entries[Number(index)];

        if (!entry.valid || entry.sequence !== sequence) {
            return null;
        }

        return entry;
    }

    /**
     * Submit sequence
     * @param sequence 
     */
    submit(entry: RTTEntry, recvTime: bigint, deltaTime: bigint) {
        if (!entry.valid) {
            return; // Discard
        }
        entry.valid = false;

        this.sample.submit(recvTime - entry.time - deltaTime);
        const result = this.sample.calc();
        this.mean = result.mean;
        this.variance = result.variance;
    }

    /**
     * Generate next sequence number
     */
    next(time: bigint): RTTEntry {
        const sequence = this.entrySequence++;
        if (this.entrySequence > POMELO_RTT_MAX_SEQUENCE) {
            this.entrySequence = 0n; // Reset sequence
        }

        const index = sequence % POMELO_RTT_ENTRY_BUFFER_SIZE;
        const entry = this.entries[Number(index)];

        entry.valid = true;
        entry.sequence = sequence;
        entry.time = time;

        return entry;
    }
}
