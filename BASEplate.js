const vasync = require('vasync');
const readline = require('readline');
const { spawn } = require('child_process');
const assert = require('assert');

class PlateIO {
    constructor () {
        this.statuses = [];

        this.create_process();
    }

    create_process () {
        this.process = spawn(__dirname + '/env/bin/python3', ['-u', __dirname + '/plate_io.py']);
        this.statuses.push(0);

        let exec_count = this.get_execution_count();

        console.log(`Starting pi-plates python co-process (count ${exec_count})`);

        this.process.on('error', (err) => {
            console.log('child error: ' + err);

            this.queue.close();
            setTimeout(() => this.create_process(), 1000);
        });

        this.process.on('exit', (code, signal) => {
            console.log(`pi-plates python co-process exited with code: ${code} and signal: ${signal}`);
            this.statuses[this.statuses.length - 1] = code;

            this.queue.close();
            setTimeout(() => this.create_process(), 1000);
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
    }

    get_execution_count () {
        return this.statuses.length;
    }

    get_status () {
        return this.statuses[this.statuses.length - 1];
    }

    kill () {
        this.process.kill();
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

        this.update_status();
    }

    // Updates this.plate_status.
    update_status () {
        let child_status = plate_io.get_status();
        if (child_status) {
            this.plate_status = child_status;
        } else {
            const verifier = {cmd: "VERIFY", args: {}};

            this.send(verifier, (reply) => {
                // If the plate was invalid and now works, the piplates library
                // needs that update as well. So, we activate the piplate:

                if (reply.error) {
                    this.plate_status = 3;
                    return;
                }

                if (this.plate_status == 1 && !reply.state) {
                    const update = {cmd: "ACTIVATE", args: {}};

                    this.send(update, (reply) => {});
                }

                this.plate_status = reply.state;
            });
        }
    }

    send (obj, receive_cb) {
        // send a request to this plate using the form:
        // {cmd: <pi-plate command>, args: {<command-specific args>}
        // e.g. {cmd: "relayTOGGLE", args: { relay: 4}}

        obj['plate_type'] = this.plate_type;
        obj['addr'] = this.addr;

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
