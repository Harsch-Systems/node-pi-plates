const vasync = require('vasync');
const readline = require('readline');
const { spawn } = require('child_process');
const assert = require('assert');

let child = spawn('python3', ['-u', __dirname + '/plate_io.py']);

child.on('error', (err) => {
    console.log('child error: ' + err);
});

child.on('exit', (code, signal) => {
    console.log(`code: ${code} signal: ${signal}`);
});

child.stderr.on('data', (data) => {
    console.log('stderr: ' + data);
});

const rl = readline.createInterface({
    input: child.stdout
});

function do_cmd(task, cb) {
    const cmd_str = JSON.stringify(task) + '\n';
    child.stdin.write(cmd_str);
    assert.equal(rl.listenerCount('line'), 0);
    rl.once('line', (line) => {
        const reply = JSON.parse(line);
        cb(reply);
    });
}

const queue = vasync.queue(do_cmd, 1);

class BASEplate {
    constructor (addr, plate_type) {
        this.addr = addr;
        this.plate_type = plate_type;
        this.queue = queue;
    }
    send (obj, receive_cb) {
        // send a request to this plate using the form:
        // {cmd: <pi-plate command>, args: {<command-specific args>}
        // e.g. {cmd: "relayTOGGLE", args: { relay: 4}}

        obj['plate_type'] = this.plate_type;
        obj['addr'] = this.addr;

        this.queue.push(obj, receive_cb);
    }
    shutdown () {
        child.kill();
    }
}

module.exports = BASEplate;
