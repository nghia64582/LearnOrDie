/**
 * The base handler
 */
type BaseHandler = (...args: any[]) => any;


/**
 * Signal connection
 */
export interface SignalConnection {
    /**
     * Disconnect the connection
     */
    disconnect(): void;
}


class SignalConnectionList<Handler extends BaseHandler> {
    head: SignalConnectionImpl<Handler> | null = null;
    tail: SignalConnectionImpl<Handler> | null = null;

    /**
     * Link the connection
     */
    link(connection: SignalConnectionImpl<Handler>) {
        if (!this.head) {
            this.head = connection;
            this.tail = connection;
        } else {
            connection.prev = this.tail;
            this.tail!.next = connection;
            this.tail = connection;
        }
        connection.list = this;
    }

    /**
     * Unlink the connection
     */
    unlink(connection: SignalConnectionImpl<Handler>) {
        if (connection.list !== this) {
            return;
        }

        if (connection === this.head) {
            this.head = connection.next;
            if (this.head) {
                this.head.prev = null;
            } else {
                this.tail = null;
            }
        } else if (connection === this.tail) {
            this.tail = connection.prev;
            this.tail!.next = null;
        } else {
            const prev = connection.prev!;
            const next = connection.next!;
            prev.next = next;
            next.prev = prev;
        }

        connection.list = null;
        connection.next = null;
        connection.prev = null;
    }
}


class SignalConnectionImpl<Handler extends BaseHandler>
    implements SignalConnection
{
    next: SignalConnectionImpl<Handler> | null = null;
    prev: SignalConnectionImpl<Handler> | null = null;
    list: SignalConnectionList<Handler> | null = null;

    private callback: Handler;
    private once: boolean

    constructor(callback: Handler, once: boolean = false) {
        this.callback = callback;
        this.once = once;
    }

    /**
     * Emit the signal
     * @param args 
     */
    emit(...args: Parameters<Handler>) {
        this.callback.apply(null, args);
        if (this.once) {
            this.disconnect();
        }
    }

    /**
     * Disconnect the connection
     */
    disconnect(): void {
        this.list?.unlink(this);
    }
}


/**
 * Signal
 */
export default class Signal<Handler extends BaseHandler> {
    private connections = new SignalConnectionList<Handler>();

    /**
     * Connect the signal
     */
    connect(callback: Handler): SignalConnection {
        const connection = new SignalConnectionImpl(callback);
        this.connections.link(connection);
        return connection;
    }

    /**
     * Connect the signal and only emit once
     */
    once(): Promise<Parameters<Handler>[0]>;
    once(callback: Handler): SignalConnection;
    once(cb?: Handler): SignalConnection | Promise<Parameters<Handler>[0]> {
        if (!cb) {
            return new Promise(resolve => {
                this.connections.link(
                    new SignalConnectionImpl(resolve as Handler, true)
                );
            });
        }

        const connection = new SignalConnectionImpl(cb, true);
        this.connections.link(connection);
        return connection;
    }

    /**
     * Emit the signal
     */
    emit(...args: Parameters<Handler>) {
        let connection = this.connections.head;
        while (connection) {
            connection.emit(...args);
            connection = connection.next;
        }
    }
}
