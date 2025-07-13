/**
 * Default maximum number of elements
 */
const DEFAULT_POOL_MAX_ELEMENTS = 100;


/**
 * Pool
 */
export default abstract class Pool<T> {
    /**
     * Array of elements in pool
     */
    private elements: T[];
    
    /**
     * Current available index
     */
    private index = -1;

    constructor(maxElements: number = DEFAULT_POOL_MAX_ELEMENTS) {
        this.elements = new Array(maxElements);
    }

    /**
     * Acquire element from pool
     */
    acquire(): T {
        if (this.index < 0) {
            return this.create();
        } else {
            return this.elements[this.index--];
        }
    }

    /**
     * Release element
     */
    release(element: T) {
        if (this.index == this.elements.length) {
            this.destroy(element);
            return; // Discard
        }
        this.elements[++this.index] = element;
    }

    /**
     * Create new instance
     */
    protected abstract create(): T;

    /**
     * Destroy an instance
     */
    protected destroy(element: T): void {}
}
