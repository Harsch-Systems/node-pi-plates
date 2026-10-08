const vasync = require('vasync');
const readline = require('readline');
const { spawn } = require('child_process');
const assert = require('assert');
const EventEmitter = require('events');

// Respawn delay after a co-process crash doubles on each consecutive crash,
// up to the max, and resets once a co-process has stayed up for STABLE_MS.
const RESPAWN_MIN_MS = 1000;
const RESPAWN_MAX_MS = 60000;
const RESPAWN_STABLE_MS = 60000;

// Emits 'start' each time a new co-process is spawned.
class PlateIO extends EventEmitter {
    constructor () {
        super();
        // one 'start' listener per plate awaiting verification
        this.setMaxListeners(0);
        this.exec_count = 0;
        this.stopped = false;
        this.respawn_timer = null;
        this.respawn_delay = RESPAWN_MIN_MS;

        this.create_process();
    }

    create_process () {
        this.respawn_timer = null;
        this.process = spawn(__dirname + '/env/bin/python3', ['-u', __dirname + '/plate_io.py']);
        this.exec_count++;

        const proc = this.process;
        const started = Date.now();
        let ended = false;

        console.log(`Starting pi-plates python co-process (count ${this.exec_count})`);

        // 'error' and 'exit' can both fire for one failure, and a process
        // replaced after shutdown() can exit late: act once, and only on
        // the current process.
        const on_end = () => {
            if (ended)
                return;
            ended = true;

            if (proc !== this.process)
                return;
            this.queue.close();
            if (!this.stopped)
                this.schedule_respawn(Date.now() - started);
        };

        this.process.on('error', (err) => {
            console.log('child error: ' + err);
            on_end();
        });

        this.process.on('exit', (code, signal) => {
            console.log(`pi-plates python co-process exited with code: ${code} and signal: ${signal}`);
            on_end();
        });

        this.process.stderr.on('data', (data) => {
            console.log('stderr: ' + data);
        });

        // e.g. EPIPE from writing to a co-process that has just died
        this.process.stdin.on('error', (err) => {
            console.log('error writing to pi-plates python co-process: ' + err);
        });

        // I/O state for this particular co-process. Tasks queued against it
        // stay bound to it, so if it dies they fail rather than hang.
        const io = {
            process: this.process,
            rl: readline.createInterface({ input: this.process.stdout }),
            closed: false
        };
        io.rl.on('close', () => { io.closed = true; });

        this.queue = vasync.queue((task, cb) => this.do_cmd(io, task, cb), 1);

        this.emit('start');
    }

    schedule_respawn (uptime) {
        if (uptime >= RESPAWN_STABLE_MS)
            this.respawn_delay = RESPAWN_MIN_MS;

        const delay = this.respawn_delay;
        this.respawn_delay = Math.min(delay * 2, RESPAWN_MAX_MS);

        console.log(`Restarting pi-plates python co-process in ${delay / 1000}s`);
        this.respawn_timer = setTimeout(() => this.create_process(), delay);
    }

    get_execution_count () {
        return this.exec_count;
    }

    is_running () {
        return !this.queue.closed;
    }

    // Stop the co-process without respawning it. It is restarted on demand
    // by the next plate created or command sent (see ensure_running).
    kill () {
        this.stopped = true;
        clearTimeout(this.respawn_timer);
        this.respawn_timer = null;
        this.queue.close();
        this.process.kill();
    }

    ensure_running () {
        if (this.stopped) {
            this.stopped = false;
            this.create_process();
        }
    }

    // Every path must call cb exactly once, or the queue stalls forever.
    // Failures are reported as a reply of the form {error: <message>}.
    do_cmd (io, task, cb) {
        if (io.closed) {
            cb({error: 'pi-plates python co-process is not running'});
            return;
        }

        const on_line = (line) => {
            io.rl.removeListener('close', on_close);
            let reply;
            try {
                reply = JSON.parse(line);
            } catch (e) {
                console.log('invalid json received from pi-plates python co-process: ' + line);
                reply = {error: 'invalid reply from pi-plates python co-process'};
            }
            cb(reply);
        };
        const on_close = () => {
            io.rl.removeListener('line', on_line);
            cb({error: 'pi-plates python co-process exited before replying'});
        };

        assert.equal(io.rl.listenerCount('line'), 0);
        io.rl.once('line', on_line);
        io.rl.once('close', on_close);
        io.process.stdin.write(JSON.stringify(task) + '\n');
    }
}

let plate_io = new PlateIO();

class BASEplate {
    constructor (addr, plate_type) {
        this.addr = addr;
        this.plate_type = plate_type;

        /* plate_status stores information about whether or not this plate can currently
         * be used, or if there is an issue:
         * 0 = no error
         * 1 = plate not found
         * 2 = missing python dependencies
         * 3 = unknown python error
         * 4 = unknown state
         */
        this.plate_status = 4;

        plate_io.ensure_running();
        this.update_status();
    }

    // Updates this.plate_status.
    update_status () {
        if (!plate_io.is_running()) {
            // co-process is restarting: verify once it's back
            this.plate_status = 4;
            plate_io.once('start', () => this.update_status());
            return;
        }

        const verifier = {cmd: "VERIFY", args: {}};

        this.send(verifier, (reply) => {
            if (reply.error) {
                if (/^(ModuleNotFoundError|ImportError)\b/.test(reply.error))
                    this.plate_status = 2;
                else
                    this.plate_status = 3;
                return;
            }

            // If the plate was invalid and now works, the piplates library
            // needs that update as well. So, we activate the piplate:
            if (this.plate_status == 1 && !reply.state) {
                const update = {cmd: "ACTIVATE", args: {}};

                this.send(update, (reply) => {});
            }

            this.plate_status = reply.state;
        });
    }

    send (obj, receive_cb) {
        // send a request to this plate using the form:
        // {cmd: <pi-plate command>, args: {<command-specific args>}
        // e.g. {cmd: "relayTOGGLE", args: { relay: 4}}

        obj['plate_type'] = this.plate_type;
        obj['addr'] = this.addr;

        plate_io.ensure_running();
        if (plate_io.queue.closed) {
            // co-process is restarting
            setImmediate(() => receive_cb({error: 'pi-plates python co-process is not running'}));
        } else {
            plate_io.queue.push(obj, receive_cb);
        }
    }

    shutdown () {
        plate_io.kill();
    }
}

module.exports = BASEplate;
