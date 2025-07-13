export interface SampleSetResult {
    mean: bigint;
    variance: bigint;
}

export default class SampleSet {
    /**
     * Initialized flag of sample
     */
    private initialized = false;

    /**
     * Current active index in sample
     */
    private index = 0;

    /**
     * Sample set
     */
    private values: bigint[] = [];

    /**
     * Sum of all elements in sample set
     */
    private sum = 0n;

    /**
     * Sum of all squared elements in sample set
     */
    private sumSquared = 0n;

    readonly size: bigint;

    constructor(size: bigint | number) {
        this.size = BigInt(size);

        for (let i = 0n; i < this.size; i++) {
            this.values.push(0n);
        }
    }

    /**
     * Submit new value to sample set
     */
    submit(value: bigint) {
        if (!this.initialized) {
            this.values.fill(value);
            this.sum = value * this.size;
            this.sumSquared = this.sum * value;
            this.initialized = true;
            return;
        }

        // Update sums
        const prevVal = this.values[this.index];
        this.sum = this.sum + value - prevVal;
        this.sumSquared = this.sumSquared + value * value - prevVal * prevVal;

        // Update the value and increase the index
        this.values[this.index] = value;
        this.index = (this.index + 1) % this.values.length;
    }

    /**
     * Calculate mean and variance
     */
    calc(): SampleSetResult {
        const mean = this.sum / this.size;
        // Var(X) = E(X^2) - E(X)^2
        const variance = this.sumSquared / this.size - mean * mean;
        return { mean, variance };
    }
}
